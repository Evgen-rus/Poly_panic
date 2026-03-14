from __future__ import annotations

from datetime import datetime, timedelta

from poly_panic.config import Settings
from poly_panic.models import Alert, MarketRecord
from poly_panic.storage import Storage


def detect_alerts(
    market: MarketRecord,
    storage: Storage,
    settings: Settings,
    observed_at: datetime,
    is_new_market: bool,
) -> list[Alert]:
    alerts: list[Alert] = []

    if is_new_market:
        absurd_alert = _detect_absurd_new_market(market, settings, observed_at)
        if absurd_alert is not None:
            alerts.append(absurd_alert)

    price_alert = _detect_price_explosion(market, storage, settings, observed_at)
    if price_alert is not None:
        alerts.append(price_alert)

    whale_alert = _detect_whale_fight(market, storage, settings, observed_at)
    if whale_alert is not None:
        alerts.append(whale_alert)

    ghost_alert = _detect_ghost_market(market, storage, settings, observed_at)
    if ghost_alert is not None:
        alerts.append(ghost_alert)

    return alerts


def _detect_absurd_new_market(
    market: MarketRecord, settings: Settings, observed_at: datetime
) -> Alert | None:
    matched_group = _match_absurd_group(market, settings)
    if matched_group is None:
        return None

    searchable_text = " ".join(
        [
            market.question,
            market.slug or "",
            " ".join(market.outcomes),
            " ".join(market.tag_labels),
            " ".join(market.tag_slugs),
        ]
    ).lower()
    matched_keyword = next(
        (
            keyword
            for keyword in settings.absurd_keywords
            if keyword.lower() in searchable_text
        ),
        None,
    )
    if matched_keyword is None:
        return None

    return Alert(
        trigger_type="absurd_new_market",
        market_id=market.market_id,
        question=market.question,
        summary=(
            f"Новый рынок в группе '{matched_group}': найден ключ '{matched_keyword}'."
        ),
        observed_at=observed_at,
        yes_price=market.yes_price,
        outcome_label=market.tracked_outcome_label,
        total_volume=market.volume_num,
        category=market.category,
        slug=market.slug,
    )


def _match_absurd_group(market: MarketRecord, settings: Settings) -> str | None:
    market_tags = {
        value.lower(): value
        for value in [*market.tag_labels, *market.tag_slugs]
        if value.strip()
    }
    for group in settings.absurd_tags:
        if group.lower() in market_tags:
            return market_tags[group.lower()]

    if market.category:
        categories = {value.lower() for value in settings.absurd_categories}
        if market.category.lower() in categories:
            return market.category

    return None


def _detect_price_explosion(
    market: MarketRecord, storage: Storage, settings: Settings, observed_at: datetime
) -> Alert | None:
    if market.yes_price is None:
        return None

    reference_time = observed_at - timedelta(
        minutes=settings.price_change_lookback_minutes
    )
    previous_snapshot = storage.get_snapshot_before(market.market_id, reference_time)
    if previous_snapshot is None or previous_snapshot.yes_price is None:
        return None

    delta = market.yes_price - previous_snapshot.yes_price
    if abs(delta) < settings.price_change_threshold:
        return None

    direction = "вырос" if delta > 0 else "упал"
    return Alert(
        trigger_type="price_explosion",
        market_id=market.market_id,
        question=market.question,
        summary=(
            f"Исход {direction} на {abs(delta) * 100:.1f} п.п. "
            f"за {settings.price_change_lookback_minutes} минут."
        ),
        observed_at=observed_at,
        yes_price=market.yes_price,
        outcome_label=market.tracked_outcome_label,
        delta_price=delta,
        total_volume=market.volume_num,
        category=market.category,
        slug=market.slug,
    )


def _detect_whale_fight(
    market: MarketRecord, storage: Storage, settings: Settings, observed_at: datetime
) -> Alert | None:
    reference_time = observed_at - timedelta(minutes=settings.whale_volume_window_minutes)
    previous_snapshot = storage.get_snapshot_before(market.market_id, reference_time)
    if previous_snapshot is None:
        return None

    delta_volume = market.volume_num - previous_snapshot.volume_num
    if delta_volume < settings.whale_volume_delta:
        return None

    return Alert(
        trigger_type="whale_fight",
        market_id=market.market_id,
        question=market.question,
        summary=(
            f"Объем вырос на ${delta_volume:,.0f} "
            f"за {settings.whale_volume_window_minutes} минут."
        ),
        observed_at=observed_at,
        yes_price=market.yes_price,
        outcome_label=market.tracked_outcome_label,
        delta_volume=delta_volume,
        total_volume=market.volume_num,
        category=market.category,
        slug=market.slug,
    )


def _detect_ghost_market(
    market: MarketRecord, storage: Storage, settings: Settings, observed_at: datetime
) -> Alert | None:
    if market.yes_price is None:
        return None

    previous_snapshot = storage.get_latest_snapshot_before(market.market_id, observed_at)
    if previous_snapshot is None or previous_snapshot.yes_price is None:
        return None

    if (
        previous_snapshot.yes_price >= settings.ghost_previous_threshold
        and market.yes_price <= settings.ghost_current_threshold
    ):
        return Alert(
            trigger_type="ghost_market",
            market_id=market.market_id,
            question=market.question,
            summary=(
                f"Рынок рухнул с {previous_snapshot.yes_price * 100:.1f}% "
                f"до {market.yes_price * 100:.1f}%."
            ),
            observed_at=observed_at,
            yes_price=market.yes_price,
            outcome_label=market.tracked_outcome_label,
            delta_price=market.yes_price - previous_snapshot.yes_price,
            total_volume=market.volume_num,
            category=market.category,
            slug=market.slug,
        )

    return None
