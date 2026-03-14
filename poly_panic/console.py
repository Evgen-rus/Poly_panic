from __future__ import annotations

from datetime import datetime

from poly_panic.models import Alert


TRIGGER_TITLES = {
    "whale_fight": "Всплеск объема",
    "price_explosion": "Резкое движение цены",
    "ghost_market": "Обвал почти решенного рынка",
    "absurd_new_market": "Странный новый рынок",
}


def print_run_header(
    observed_at: datetime,
    markets_count: int,
    new_markets_count: int,
    active_filters: list[str] | None = None,
) -> None:
    print("=" * 80)
    print(
        f"[{observed_at.isoformat()}] Проверено рынков: {markets_count} | "
        f"новых: {new_markets_count}"
    )
    if active_filters:
        print(f"Активные фильтры: {' | '.join(active_filters)}")
    else:
        print("Активные фильтры: нет")


def print_alert(alert: Alert) -> None:
    print("-" * 80)
    print(f"Сигнал: {_get_trigger_title(alert.trigger_type)}")
    print(f"Рынок: {alert.question}")
    if alert.category:
        print(f"Категория: {alert.category}")
    if alert.yes_price is not None:
        label = alert.outcome_label or "tracked outcome"
        print(f"Текущий исход: {label} = {alert.yes_price * 100:.1f}%")

    if alert.delta_price is not None:
        direction = "рост" if alert.delta_price > 0 else "падение"
        print(f"Движение цены: {direction} на {abs(alert.delta_price) * 100:.1f} п.п.")
    if alert.delta_volume is not None:
        print(f"Прирост объема: ${alert.delta_volume:,.0f}")
    if alert.total_volume is not None:
        print(f"Текущий общий объем: ${alert.total_volume:,.0f}")

    print(f"Что произошло: {alert.summary}")
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


def _get_trigger_title(trigger_type: str) -> str:
    return TRIGGER_TITLES.get(trigger_type, trigger_type)
