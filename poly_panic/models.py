from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class MarketRecord:
    market_id: str
    question: str
    slug: str | None
    category: str | None
    tag_labels: list[str]
    tag_slugs: list[str]
    yes_price: float | None
    tracked_outcome_label: str | None
    outcomes: list[str]
    volume_num: float
    clob_token_ids: list[str]
    sports_market_type: str | None = None
    series_slug: str | None = None
    fee_type: str | None = None


@dataclass(slots=True)
class Snapshot:
    market_id: str
    observed_at: datetime
    yes_price: float | None
    volume_num: float


@dataclass(slots=True)
class Alert:
    trigger_type: str
    market_id: str
    question: str
    summary: str
    observed_at: datetime
    yes_price: float | None = None
    outcome_label: str | None = None
    delta_price: float | None = None
    delta_volume: float | None = None
    total_volume: float | None = None
    category: str | None = None
    slug: str | None = None
