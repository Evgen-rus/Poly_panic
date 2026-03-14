from __future__ import annotations

import logging
from typing import Iterable

import requests

from poly_panic.models import Alert


LOGGER = logging.getLogger("poly_panic.telegram")
MARKET_URL_TEMPLATE = "https://polymarket.com/event/{slug}"


class TelegramNotifier:
    def __init__(
        self,
        bot_token: str | None,
        chat_id: str | None,
        request_timeout_seconds: int,
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.request_timeout_seconds = request_timeout_seconds
        self.session = requests.Session()

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_alerts(self, alerts: Iterable[Alert]) -> int:
        if not self.enabled:
            return 0

        sent_count = 0
        for alert in alerts:
            self.send_alert(alert)
            sent_count += 1
        return sent_count

    def send_alert(self, alert: Alert) -> None:
        if not self.enabled:
            return

        self._send_text(format_alert_message(alert))

    def send_text(self, message: str) -> None:
        if not self.enabled:
            return

        self._send_text(message)

    def _send_text(self, message: str) -> None:
        response = self.session.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": message,
                "disable_web_page_preview": True,
            },
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()


def format_alert_message(alert: Alert) -> str:
    lines = [
        f"Сигнал: {_get_trigger_title(alert.trigger_type)}",
        f"Рынок: {alert.question}",
    ]

    if alert.outcome_label and alert.yes_price is not None:
        lines.append(
            f"Текущий исход: {alert.outcome_label} = {alert.yes_price * 100:.1f}%"
        )
    elif alert.yes_price is not None:
        lines.append(f"Текущая вероятность: {alert.yes_price * 100:.1f}%")

    if alert.delta_price is not None:
        direction = "рост" if alert.delta_price > 0 else "падение"
        lines.append(
            f"Движение цены: {direction} на {abs(alert.delta_price) * 100:.1f} п.п."
        )
    if alert.delta_volume is not None:
        lines.append(f"Прирост объема: ${alert.delta_volume:,.0f}")
    if alert.total_volume is not None:
        lines.append(f"Текущий общий объем: ${alert.total_volume:,.0f}")

    lines.append(f"Что произошло: {alert.summary}")
    if alert.slug:
        lines.append(MARKET_URL_TEMPLATE.format(slug=alert.slug))

    return "\n".join(lines)


def _get_trigger_title(trigger_type: str) -> str:
    return {
        "whale_fight": "Всплеск объема",
        "price_explosion": "Резкое движение цены",
        "ghost_market": "Обвал почти решенного рынка",
        "absurd_new_market": "Странный новый рынок",
    }.get(trigger_type, trigger_type)
