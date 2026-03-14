from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "poly_panic.db"
# URL публичного Gamma API для списка рынков.
DEFAULT_GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"
# Таймаут одного HTTP-запроса к Polymarket в секундах.
DEFAULT_REQUEST_TIMEOUT_SECONDS = 20
# Пауза между циклами опроса API в секундах.
DEFAULT_POLL_INTERVAL_SECONDS = 300
# Размер одной страницы при пагинации списка рынков.
DEFAULT_MARKETS_PAGE_LIMIT = 100

# Фильтрация рынков
# Минимальный общий объем рынка, ниже которого рынок игнорируется.
DEFAULT_MIN_VOLUME_NUM = 1000000.0
# Минимальное изменение отслеживаемого исхода, которое считаем резким движением.
DEFAULT_PRICE_CHANGE_THRESHOLD = 0.20
# Окно в минутах для сравнения текущей цены с более старым снапшотом.
DEFAULT_PRICE_CHANGE_LOOKBACK_MINUTES = 60
# Минимальный прирост объема в долларах для триггера "whale_fight".
DEFAULT_WHALE_VOLUME_DELTA = 100000.0
# Окно в минутах, внутри которого измеряем прирост объема.
DEFAULT_WHALE_VOLUME_WINDOW_MINUTES = 15
# Предыдущее значение отслеживаемого исхода, от которого рынок считаем "почти решенным".
DEFAULT_GHOST_PREVIOUS_THRESHOLD = 0.99
# Текущее значение отслеживаемого исхода, ниже которого считаем, что рынок "рухнул".
DEFAULT_GHOST_CURRENT_THRESHOLD = 0.50
# Защита от повторных алертов по одному и тому же рынку и триггеру.
DEFAULT_ALERT_COOLDOWN_MINUTES = 180
# Категории, где ищем "абсурдные" новые рынки.
DEFAULT_ABSURD_CATEGORIES = ["Pop Culture", "Science", "Business"]
# Ключевые слова для поиска странных или мемных новых рынков.
DEFAULT_ABSURD_KEYWORDS = ["Elon Musk", "Aliens", "GTA 6", "Kanye", "Meme"]
# Если True, то рынки со спортивными признаками исключаются из мониторинга.
DEFAULT_EXCLUDE_SPORT_MARKETS = True
# Белый список категорий. Пустой список означает "брать все категории".
DEFAULT_INCLUDE_CATEGORIES: list[str] = []
# Черный список категорий. Если категория совпала, рынок пропускаем.
DEFAULT_EXCLUDE_CATEGORIES: list[str] = []
# Ключевые слова, которые обязательно должны быть в вопросе/slug/outcomes.
DEFAULT_REQUIRED_KEYWORDS = ["trump", "fed", "elon", "bitcoin", "election", "iran", "china", "musk", "ai", "crypto", "russia", "ukraine", "jesus", "apocalypse", "policy"]
# Ключевые слова, по которым рынок исключается.
DEFAULT_EXCLUDED_KEYWORDS = ["weather"]
# Уровень логирования приложения: DEBUG, INFO, WARNING, ERROR.
DEFAULT_LOG_LEVEL = "INFO"
# Файл, куда дублируются логи для последующего разбора.
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "poly_panic.log"


def _split_csv(value: str, default: list[str]) -> list[str]:
    if not value.strip():
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    exclude_sport_markets: bool = DEFAULT_EXCLUDE_SPORT_MARKETS
    include_categories: list[str] = field(
        default_factory=lambda: list(DEFAULT_INCLUDE_CATEGORIES)
    )
    exclude_categories: list[str] = field(
        default_factory=lambda: list(DEFAULT_EXCLUDE_CATEGORIES)
    )
    required_keywords: list[str] = field(
        default_factory=lambda: list(DEFAULT_REQUIRED_KEYWORDS)
    )
    excluded_keywords: list[str] = field(
        default_factory=lambda: list(DEFAULT_EXCLUDED_KEYWORDS)
    )
    log_level: str = DEFAULT_LOG_LEVEL
    log_file: Path = DEFAULT_LOG_FILE


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
        exclude_sport_markets=_to_bool(
            os.getenv("EXCLUDE_SPORT_MARKETS"),
            DEFAULT_EXCLUDE_SPORT_MARKETS,
        ),
        include_categories=_split_csv(
            os.getenv("INCLUDE_CATEGORIES", ""),
            DEFAULT_INCLUDE_CATEGORIES,
        ),
        exclude_categories=_split_csv(
            os.getenv("EXCLUDE_CATEGORIES", ""),
            DEFAULT_EXCLUDE_CATEGORIES,
        ),
        required_keywords=_split_csv(
            os.getenv("REQUIRED_KEYWORDS", ""),
            DEFAULT_REQUIRED_KEYWORDS,
        ),
        excluded_keywords=_split_csv(
            os.getenv("EXCLUDED_KEYWORDS", ""),
            DEFAULT_EXCLUDED_KEYWORDS,
        ),
        log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip().upper(),
        log_file=Path(os.getenv("LOG_FILE", str(DEFAULT_LOG_FILE))),
    )
