from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timezone

from requests import RequestException

from poly_panic.config import Settings, load_settings
from poly_panic.console import (
    print_alert,
    print_no_alerts,
    print_run_header,
    print_top_markets,
)
from poly_panic.detectors import detect_alerts
from poly_panic.filters import get_filter_reason, summarize_active_filters
from poly_panic.polymarket import PolymarketGammaClient
from poly_panic.storage import Storage


LOGGER = logging.getLogger("poly_panic")


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


def configure_logging(settings: Settings) -> None:
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    log_level = getattr(logging, settings.log_level, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(settings.log_file, encoding="utf-8"),
        ],
        force=True,
    )


def main() -> int:
    args = parse_args()
    settings = load_settings()
    configure_logging(settings)
    LOGGER.info(
        "Application started: db=%s, poll_interval=%ss, log_file=%s",
        settings.db_path,
        settings.poll_interval_seconds,
        settings.log_file,
    )
    LOGGER.info("Active filters: %s", summarize_active_filters(settings) or ["none"])
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
        LOGGER.info("Application stopped by user")
        print("Остановлено пользователем.")
        return 0
    finally:
        storage.close()


def run_cycle(
    client: PolymarketGammaClient,
    storage: Storage,
    settings: Settings,
    show_top: bool,
) -> None:
    observed_at = datetime.now(timezone.utc)
    LOGGER.info("Cycle started at %s", observed_at.isoformat())
    try:
        raw_markets = client.fetch_active_markets(settings.min_volume_num)
        LOGGER.info("Fetched %s markets from Gamma API", len(raw_markets))
        markets, filtered_out = apply_filters(raw_markets, settings)
        LOGGER.info(
            "Markets after filters: kept=%s, removed=%s, reasons=%s",
            len(markets),
            sum(filtered_out.values()),
            dict(filtered_out),
        )
    except RequestException as exc:
        LOGGER.exception("Polymarket request failed")
        print(f"[{observed_at.isoformat()}] Ошибка запроса к Polymarket: {exc}")
        return
    except ValueError as exc:
        LOGGER.exception("Polymarket response parsing failed")
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
    LOGGER.info(
        "Cycle stored: markets=%s, new=%s, alerts=%s",
        len(markets),
        new_markets_count,
        len(emitted_alerts),
    )

    print_run_header(
        observed_at,
        len(markets),
        new_markets_count,
        active_filters=summarize_active_filters(settings),
    )
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
        LOGGER.info("Top movers calculated: %s entries", len(top_markets))
        print_top_markets(top_markets)

    LOGGER.info("Cycle finished")
    print()


def apply_filters(markets, settings: Settings):
    kept_markets = []
    filtered_out = Counter()
    for market in markets:
        reason = get_filter_reason(market, settings)
        if reason is None:
            kept_markets.append(market)
        else:
            filtered_out[reason] += 1
    return kept_markets, filtered_out
