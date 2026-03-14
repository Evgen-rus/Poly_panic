from __future__ import annotations

import json
from typing import Any

import requests

from poly_panic.models import MarketRecord


class PolymarketGammaClient:
    def __init__(
        self,
        base_url: str,
        request_timeout_seconds: int,
        page_limit: int,
    ) -> None:
        self.base_url = base_url
        self.request_timeout_seconds = request_timeout_seconds
        self.page_limit = page_limit
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "poly-panic/0.1"})

    def fetch_active_markets(self, min_volume_num: float) -> list[MarketRecord]:
        markets: list[MarketRecord] = []
        offset = 0

        while True:
            response = self.session.get(
                self.base_url,
                params={
                    "active": "true",
                    "closed": "false",
                    "archived": "false",
                    "limit": self.page_limit,
                    "offset": offset,
                },
                timeout=self.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Unexpected Gamma API response shape: expected list")

            normalized_batch: list[MarketRecord] = []
            for raw_market in payload:
                normalized_market = self._normalize_market(raw_market)
                if normalized_market is not None:
                    normalized_batch.append(normalized_market)

            filtered_batch = [
                market
                for market in normalized_batch
                if market.volume_num >= min_volume_num
            ]
            markets.extend(filtered_batch)

            if len(payload) < self.page_limit:
                break
            offset += self.page_limit

        return markets

    def _normalize_market(self, raw_market: dict[str, Any]) -> MarketRecord | None:
        market_id = str(raw_market.get("id") or "").strip()
        question = str(raw_market.get("question") or "").strip()
        if not market_id or not question:
            return None

        outcomes = self._parse_jsonish_list(raw_market.get("outcomes"))
        outcome_prices = self._parse_jsonish_list(raw_market.get("outcomePrices"))
        clob_token_ids = self._parse_jsonish_list(raw_market.get("clobTokenIds"))
        tracked_outcome_label, tracked_price = self._pick_tracked_outcome(
            outcomes,
            outcome_prices,
        )
        volume_num = self._to_float(raw_market.get("volumeNum") or raw_market.get("volume"))

        return MarketRecord(
            market_id=market_id,
            question=question,
            slug=self._clean_optional_str(raw_market.get("slug")),
            category=self._clean_optional_str(raw_market.get("category")),
            yes_price=tracked_price,
            tracked_outcome_label=tracked_outcome_label,
            outcomes=outcomes,
            volume_num=volume_num,
            clob_token_ids=clob_token_ids,
            sports_market_type=self._clean_optional_str(raw_market.get("sportsMarketType")),
            series_slug=self._extract_series_slug(raw_market.get("events")),
            fee_type=self._clean_optional_str(raw_market.get("feeType")),
        )

    @staticmethod
    def _clean_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _parse_jsonish_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return [item.strip() for item in text.split(",") if item.strip()]
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        return []

    def _pick_tracked_outcome(
        self,
        outcomes: list[str],
        outcome_prices: list[str],
    ) -> tuple[str | None, float | None]:
        if not outcomes or not outcome_prices:
            return None, None

        tracked_index = self._find_yes_index(outcomes)
        if tracked_index is None:
            tracked_index = 0

        if tracked_index >= len(outcome_prices):
            tracked_index = 0
        if tracked_index >= len(outcomes):
            return None, None

        return outcomes[tracked_index], self._to_optional_float(outcome_prices[tracked_index])

    @staticmethod
    def _find_yes_index(outcomes: list[str]) -> int | None:
        for index, outcome in enumerate(outcomes):
            if outcome.lower() == "yes":
                return index
        return None

    @staticmethod
    def _extract_series_slug(events: Any) -> str | None:
        if not isinstance(events, list) or not events:
            return None

        first_event = events[0]
        if not isinstance(first_event, dict):
            return None

        series_slug = first_event.get("seriesSlug")
        if series_slug:
            return str(series_slug).strip() or None

        series = first_event.get("series")
        if isinstance(series, list) and series:
            first_series = series[0]
            if isinstance(first_series, dict):
                slug = first_series.get("slug")
                if slug:
                    return str(slug).strip() or None

        return None

    @staticmethod
    def _to_optional_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
