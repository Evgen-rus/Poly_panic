from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

from requests import RequestException

from poly_panic.config import load_settings
from poly_panic.console import (
    print_alert,
    print_no_alerts,
    print_run_header,
    print_top_markets,
)
from poly_panic.detectors import detect_alerts
from poly_panic.polymarket import PolymarketGammaClient
from poly_panic.storage import Storage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poly Panic console monitor")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Сделать один проход и завершиться",
    )
    parser.add_argument(
        "--top",
        action="store_true",
        help="После прохода показать топ волатильных рынков",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings()
    storage = Storage(settings.db_path)
    client = PolymarketGammaClient(
        base_url=settings.gamma_api_url,
        request_timeout_seconds=settings.request_timeout_seconds,
        page_limit=settings.markets_page_limit,
    )

    try:
        if args.once:
            run_cycle(client, storage, settings, show_top=args.top)
            return 0

        while True:
            run_cycle(client, storage, settings, show_top=args.top)
            time.sleep(settings.poll_interval_seconds)
    except KeyboardInterrupt:
        print("Остановлено пользователем.")
        return 0
    finally:
        storage.close()


def run_cycle(
    client: PolymarketGammaClient,
    storage: Storage,
    settings,
    show_top: bool,
) -> None:
    observed_at = datetime.now(timezone.utc)
    try:
        markets = client.fetch_active_markets(settings.min_volume_num)
    except RequestException as exc:
        print(f"[{observed_at.isoformat()}] Ошибка запроса к Polymarket: {exc}")
        return
    except ValueError as exc:
        print(f"[{observed_at.isoformat()}] Ошибка разбора ответа Polymarket: {exc}")
        return

    new_markets_count = 0
    emitted_alerts = []

    for market in markets:
        is_new_market = not storage.market_exists(market.market_id)
        if is_new_market:
            new_markets_count += 1

        alerts = detect_alerts(
            market=market,
            storage=storage,
            settings=settings,
            observed_at=observed_at,
            is_new_market=is_new_market,
        )

        storage.upsert_market(market, observed_at)
        storage.insert_snapshot(market, observed_at)

        for alert in alerts:
            if storage.recently_sent_alert(
                market_id=alert.market_id,
                trigger_type=alert.trigger_type,
                now=observed_at,
                cooldown_minutes=settings.alert_cooldown_minutes,
            ):
                continue
            storage.record_alert(
                market_id=alert.market_id,
                trigger_type=alert.trigger_type,
                summary=alert.summary,
                sent_at=observed_at,
            )
            emitted_alerts.append(alert)

    storage.commit()

    print_run_header(observed_at, len(markets), new_markets_count)
    if emitted_alerts:
        for alert in emitted_alerts:
            print_alert(alert)
    else:
        print_no_alerts()

    if show_top:
        top_markets = storage.get_top_movers(
            now=observed_at,
            lookback_minutes=settings.price_change_lookback_minutes,
            limit=5,
        )
        print_top_markets(top_markets)

    print()
