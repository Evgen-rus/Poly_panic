from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "poly_panic.db"
DEFAULT_GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 20
DEFAULT_POLL_INTERVAL_SECONDS = 300
DEFAULT_MARKETS_PAGE_LIMIT = 100
DEFAULT_MIN_VOLUME_NUM = 1.0
DEFAULT_PRICE_CHANGE_THRESHOLD = 0.30
DEFAULT_PRICE_CHANGE_LOOKBACK_MINUTES = 60
DEFAULT_WHALE_VOLUME_DELTA = 10000.0
DEFAULT_WHALE_VOLUME_WINDOW_MINUTES = 15
DEFAULT_GHOST_PREVIOUS_THRESHOLD = 0.99
DEFAULT_GHOST_CURRENT_THRESHOLD = 0.50
DEFAULT_ALERT_COOLDOWN_MINUTES = 180
DEFAULT_ABSURD_CATEGORIES = ["Pop Culture", "Science", "Business"]
DEFAULT_ABSURD_KEYWORDS = ["Elon Musk", "Aliens", "GTA 6", "Kanye", "Meme"]


def _split_csv(value: str, default: list[str]) -> list[str]:
    if not value.strip():
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class Settings:
    gamma_api_url: str = DEFAULT_GAMMA_API_URL
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS
    db_path: Path = DEFAULT_DB_PATH
    markets_page_limit: int = DEFAULT_MARKETS_PAGE_LIMIT
    min_volume_num: float = DEFAULT_MIN_VOLUME_NUM
    price_change_threshold: float = DEFAULT_PRICE_CHANGE_THRESHOLD
    price_change_lookback_minutes: int = DEFAULT_PRICE_CHANGE_LOOKBACK_MINUTES
    whale_volume_delta: float = DEFAULT_WHALE_VOLUME_DELTA
    whale_volume_window_minutes: int = DEFAULT_WHALE_VOLUME_WINDOW_MINUTES
    ghost_previous_threshold: float = DEFAULT_GHOST_PREVIOUS_THRESHOLD
    ghost_current_threshold: float = DEFAULT_GHOST_CURRENT_THRESHOLD
    alert_cooldown_minutes: int = DEFAULT_ALERT_COOLDOWN_MINUTES
    absurd_categories: list[str] = field(
        default_factory=lambda: list(DEFAULT_ABSURD_CATEGORIES)
    )
    absurd_keywords: list[str] = field(
        default_factory=lambda: list(DEFAULT_ABSURD_KEYWORDS)
    )


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        gamma_api_url=os.getenv("POLYMARKET_GAMMA_API_URL", DEFAULT_GAMMA_API_URL),
        request_timeout_seconds=int(
            os.getenv(
                "POLYMARKET_REQUEST_TIMEOUT_SECONDS",
                str(DEFAULT_REQUEST_TIMEOUT_SECONDS),
            )
        ),
        poll_interval_seconds=int(
            os.getenv("POLL_INTERVAL_SECONDS", str(DEFAULT_POLL_INTERVAL_SECONDS))
        ),
        db_path=Path(os.getenv("SQLITE_PATH", str(DEFAULT_DB_PATH))),
        markets_page_limit=int(
            os.getenv("MARKETS_PAGE_LIMIT", str(DEFAULT_MARKETS_PAGE_LIMIT))
        ),
        min_volume_num=float(os.getenv("MIN_VOLUME_NUM", str(DEFAULT_MIN_VOLUME_NUM))),
        price_change_threshold=float(
            os.getenv("PRICE_CHANGE_THRESHOLD", str(DEFAULT_PRICE_CHANGE_THRESHOLD))
        ),
        price_change_lookback_minutes=int(
            os.getenv(
                "PRICE_CHANGE_LOOKBACK_MINUTES",
                str(DEFAULT_PRICE_CHANGE_LOOKBACK_MINUTES),
            )
        ),
        whale_volume_delta=float(
            os.getenv("WHALE_VOLUME_DELTA", str(DEFAULT_WHALE_VOLUME_DELTA))
        ),
        whale_volume_window_minutes=int(
            os.getenv(
                "WHALE_VOLUME_WINDOW_MINUTES",
                str(DEFAULT_WHALE_VOLUME_WINDOW_MINUTES),
            )
        ),
        ghost_previous_threshold=float(
            os.getenv(
                "GHOST_PREVIOUS_THRESHOLD", str(DEFAULT_GHOST_PREVIOUS_THRESHOLD)
            )
        ),
        ghost_current_threshold=float(
            os.getenv("GHOST_CURRENT_THRESHOLD", str(DEFAULT_GHOST_CURRENT_THRESHOLD))
        ),
        alert_cooldown_minutes=int(
            os.getenv("ALERT_COOLDOWN_MINUTES", str(DEFAULT_ALERT_COOLDOWN_MINUTES))
        ),
        absurd_categories=_split_csv(
            os.getenv("ABSURD_CATEGORIES", ""),
            DEFAULT_ABSURD_CATEGORIES,
        ),
        absurd_keywords=_split_csv(
            os.getenv("ABSURD_KEYWORDS", ""),
            DEFAULT_ABSURD_KEYWORDS,
        ),
    )
