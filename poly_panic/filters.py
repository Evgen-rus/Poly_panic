from __future__ import annotations

from poly_panic.config import Settings
from poly_panic.models import MarketRecord


def should_include_market(market: MarketRecord, settings: Settings) -> bool:
    return get_filter_reason(market, settings) is None


def get_filter_reason(market: MarketRecord, settings: Settings) -> str | None:
    category = (market.category or "").strip().lower()
    market_tags = {
        value.lower()
        for value in [*market.tag_labels, *market.tag_slugs]
        if value.strip()
    }
    searchable_text = _build_searchable_text(market)

    if settings.include_categories:
        allowed_categories = {value.lower() for value in settings.include_categories}
        if category not in allowed_categories:
            return "category_not_in_include"

    if settings.exclude_categories:
        blocked_categories = {value.lower() for value in settings.exclude_categories}
        if category in blocked_categories:
            return "category_excluded"

    if settings.include_tags:
        allowed_tags = {value.lower() for value in settings.include_tags}
        if not market_tags.intersection(allowed_tags):
            return "tag_not_in_include"

    if settings.exclude_tags:
        blocked_tags = {value.lower() for value in settings.exclude_tags}
        if market_tags.intersection(blocked_tags):
            return "tag_excluded"

    if settings.exclude_sport_markets and _looks_like_sport_market(market, searchable_text):
        return "sport_market"

    if settings.required_keywords:
        required = [keyword.lower() for keyword in settings.required_keywords]
        if not any(keyword in searchable_text for keyword in required):
            return "required_keyword_missing"

    if settings.excluded_keywords:
        blocked = [keyword.lower() for keyword in settings.excluded_keywords]
        if any(keyword in searchable_text for keyword in blocked):
            return "excluded_keyword"

    return None


def summarize_active_filters(settings: Settings) -> list[str]:
    filters: list[str] = []
    if settings.exclude_sport_markets:
        filters.append("без спорта")
    if settings.include_categories:
        filters.append(f"include categories: {', '.join(settings.include_categories)}")
    if settings.exclude_categories:
        filters.append(f"exclude categories: {', '.join(settings.exclude_categories)}")
    if settings.include_tags:
        filters.append(f"include tags: {', '.join(settings.include_tags)}")
    if settings.exclude_tags:
        filters.append(f"exclude tags: {', '.join(settings.exclude_tags)}")
    if settings.required_keywords:
        filters.append(f"must include: {', '.join(settings.required_keywords)}")
    if settings.excluded_keywords:
        filters.append(f"exclude keywords: {', '.join(settings.excluded_keywords)}")
    return filters


def _build_searchable_text(market: MarketRecord) -> str:
    parts = [
        market.question,
        market.slug or "",
        market.category or "",
        " ".join(market.tag_labels),
        " ".join(market.tag_slugs),
        market.tracked_outcome_label or "",
        market.series_slug or "",
        market.sports_market_type or "",
        market.fee_type or "",
        " ".join(market.outcomes),
    ]
    return " ".join(parts).lower()


def _looks_like_sport_market(market: MarketRecord, searchable_text: str) -> bool:
    if market.sports_market_type:
        return True

    if market.fee_type == "sports_fees":
        return True

    if market.series_slug:
        return True

    sport_markers = (
        " vs. ",
        " vs ",
        "spread:",
        " o/u ",
        "moneyline",
        "nba-",
        "nfl-",
        "nhl-",
        "mlb-",
        "cbb-",
        "ncaa",
        "ufc-",
        "atp-",
        "wta-",
        "f1-",
        "world cup",
        "stanley cup",
        "masters tournament",
    )
    return any(marker in searchable_text for marker in sport_markers)
