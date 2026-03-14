from __future__ import annotations

import argparse
from collections import Counter
import sys
from typing import Any

import requests
from requests import RequestException

from poly_panic.config import load_settings


TAGS_API_URL = "https://gamma-api.polymarket.com/tags"
EVENTS_API_URL = "https://gamma-api.polymarket.com/events"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List Polymarket tags and optionally count active markets per tag"
    )
    parser.add_argument(
        "--with-market-counts",
        action="store_true",
        help="Посчитать, сколько активных рынков связано с каждым тегом",
    )
    parser.add_argument(
        "--min-volume",
        type=float,
        default=0.0,
        help="Минимальный объем рынка при подсчете market counts",
    )
    return parser.parse_args()


def main() -> int:
    _configure_stdout()
    args = parse_args()
    settings = load_settings()
    session = requests.Session()
    session.headers.update({"User-Agent": "poly-panic/0.1"})

    try:
        tags = fetch_all_tags(
            session=session,
            request_timeout_seconds=settings.request_timeout_seconds,
        )
        market_counts = {}
        if args.with_market_counts:
            market_counts = fetch_market_tag_counts(
                session=session,
                events_url=EVENTS_API_URL,
                request_timeout_seconds=settings.request_timeout_seconds,
                page_limit=settings.markets_page_limit,
                min_volume=args.min_volume,
            )
    except RequestException as exc:
        print(f"Ошибка запроса к Polymarket: {exc}")
        return 1
    except ValueError as exc:
        print(f"Ошибка разбора ответа Polymarket: {exc}")
        return 1

    print(f"Уникальных тегов: {len(tags)}")
    if args.with_market_counts:
        print(
            f"Режим market counts включен, минимальный объем рынка: {args.min_volume:.0f}"
        )
    print()

    sorted_tags = sorted(
        tags,
        key=lambda tag: (
            -market_counts.get(tag["id"], 0),
            (tag["label"] or tag["slug"] or "").lower(),
        ),
    )
    for tag in sorted_tags:
        label = tag["label"] or "UNLABELED"
        slug = tag["slug"] or "-"
        if args.with_market_counts:
            print(f"{label} | slug={slug} | id={tag['id']} | markets={market_counts.get(tag['id'], 0)}")
        else:
            print(f"{label} | slug={slug} | id={tag['id']}")

    return 0


def fetch_all_tags(
    session: requests.Session,
    request_timeout_seconds: int,
) -> list[dict[str, str | None]]:
    tags: list[dict[str, str | None]] = []
    offset = 0
    limit = 500

    while True:
        response = session.get(
            TAGS_API_URL,
            params={"limit": limit, "offset": offset},
            timeout=request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Unexpected tags response shape: expected list")

        for raw_tag in payload:
            if not isinstance(raw_tag, dict):
                continue
            tags.append(
                {
                    "id": _clean_optional_str(raw_tag.get("id")),
                    "label": _clean_optional_str(raw_tag.get("label")),
                    "slug": _clean_optional_str(raw_tag.get("slug")),
                }
            )

        if len(payload) < limit:
            break
        offset += limit

    return [tag for tag in tags if tag["id"]]


def fetch_market_tag_counts(
    session: requests.Session,
    events_url: str,
    request_timeout_seconds: int,
    page_limit: int,
    min_volume: float,
) -> Counter[str]:
    counts: Counter[str] = Counter()
    offset = 0

    while True:
        response = session.get(
            events_url,
            params={
                "active": "true",
                "closed": "false",
                "archived": "false",
                "limit": page_limit,
                "offset": offset,
            },
            timeout=request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Unexpected events response shape: expected list")

        for raw_event in payload:
            if not isinstance(raw_event, dict):
                continue
            tag_ids = _extract_tag_ids(raw_event.get("tags"))
            if not tag_ids:
                continue

            matched_markets = 0
            for raw_market in _extract_markets(raw_event.get("markets")):
                volume_num = _to_float(
                    raw_market.get("volumeNum") or raw_market.get("volume")
                )
                if volume_num >= min_volume:
                    matched_markets += 1

            if matched_markets == 0:
                continue

            for tag_id in tag_ids:
                counts[tag_id] += matched_markets

        if len(payload) < page_limit:
            break
        offset += page_limit

    return counts


def _extract_tag_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    tag_ids: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tag_id = _clean_optional_str(item.get("id"))
        if tag_id:
            tag_ids.append(tag_id)
    return tag_ids


def _extract_markets(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _clean_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    raise SystemExit(main())
