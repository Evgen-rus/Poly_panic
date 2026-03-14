from __future__ import annotations

from datetime import datetime

from poly_panic.models import Alert


def print_run_header(observed_at: datetime, markets_count: int, new_markets_count: int) -> None:
    print("=" * 80)
    print(
        f"[{observed_at.isoformat()}] Проверено рынков: {markets_count} | "
        f"новых: {new_markets_count}"
    )


def print_alert(alert: Alert) -> None:
    print("-" * 80)
    print(f"[{alert.trigger_type}] {alert.question}")
    if alert.category:
        print(f"Категория: {alert.category}")
    if alert.yes_price is not None:
        print(f"Текущая вероятность YES: {alert.yes_price * 100:.1f}%")
    print(alert.summary)
    if alert.slug:
        print(f"Slug: {alert.slug}")


def print_no_alerts() -> None:
    print("Аномалий не найдено.")


def print_top_markets(top_markets: list[tuple[str, float, float | None, float | None]]) -> None:
    if not top_markets:
        print("Недостаточно истории для топа волатильности.")
        return

    print("-" * 80)
    print("Топ волатильных рынков:")
    for index, (question, delta, current_price, old_price) in enumerate(top_markets, start=1):
        old_label = f"{old_price * 100:.1f}%" if old_price is not None else "n/a"
        current_label = f"{current_price * 100:.1f}%" if current_price is not None else "n/a"
        print(
            f"{index}. {question} | delta={delta * 100:.1f} п.п. | "
            f"{old_label} -> {current_label}"
        )
