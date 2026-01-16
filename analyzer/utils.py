"""
Вспомогательные инструменты для расчетов и форматирования данных.

Содержит функции для цветовой стилизации вывода в консоль и алгоритмы
вычисления серий (streaks) побед и поражений.
"""

import pandas as pd
from colorama import Fore, Style


def color_profit(value: float) -> str:
    """Возвращает строку с прибылью, окрашенную в зависимости от значения."""
    if value > 0:
        return f"{Fore.GREEN}{value:+.2f}{Style.RESET_ALL}"
    if value < 0:
        return f"{Fore.RED}{value:.2f}{Style.RESET_ALL}"
    return f"{Fore.YELLOW}{value:.2f}{Style.RESET_ALL}"


def color_winrate(value: float) -> str:
    """Возвращает строку с винрейтом, окрашенную в зависимости от порога 50%."""
    if value >= 50:  # noqa: PLR2004
        return f"{Fore.GREEN}{value:.2f}%{Style.RESET_ALL}"
    return f"{Fore.RED}{value:.2f}%{Style.RESET_ALL}"


def calculate_max_streak(df: pd.DataFrame, result_type: str) -> int:
    """
    Вычисляет максимальную непрерывную серию побед или поражений.

    Args:
        df: DataFrame со сделками.
        result_type: Тип результата для поиска ('Win' или 'Loss').

    Returns:
        Максимальное количество повторений подряд.

    """
    is_target = (df["Результат"] == result_type).astype(int)

    # Сравниваем каждое значение с предыдущим: если они разные, создаем новую группу.
    # cumsum() присваивает каждой такой группе уникальный ID.
    changes = (df["Результат"] != df["Результат"].shift()).cumsum()

    # Считаем количество целевых исходов внутри каждой группы
    streaks = is_target.groupby(changes).sum()

    return int(streaks.max()) if not streaks.empty else 0


def calculate_asset_streaks(group: pd.DataFrame) -> pd.Series:
    """
    Рассчитывает расширенную статистику (винрейт, прибыль, серии) для группы сделок.

    Обычно вызывается через groupby.apply() при анализе отдельных активов.

    Args:
        group: Подмножество DataFrame (сделки по конкретному активу).

    Returns:
        Series с ключами: Сделок, Винрейт, Прибыль, Серия_вин, Серия_лосс.

    """
    # Сортировка важна для корректного вычисления серий
    group = group.sort_values("Время открытия").reset_index(drop=True)

    # Определяем границы серий через сравнение со сдвигом
    group["Группа"] = (group["Результат"] != group["Результат"].shift()).cumsum()
    streaks = group.groupby(["Группа", "Результат"]).size()

    # Извлекаем максимальные значения для Win и Loss серий отдельно
    win_streaks = streaks[streaks.index.get_level_values(1) == "Win"]
    loss_streaks = streaks[streaks.index.get_level_values(1) == "Loss"]

    return pd.Series({
        "Сделок": len(group),
        "Винрейт": float((group["Результат"] == "Win").mean() * 100),
        "Прибыль": float(group["Прибыль числом"].sum()),
        "Серия_вин": int(win_streaks.max()) if not win_streaks.empty else 0,
        "Серия_лосс": int(loss_streaks.max()) if not loss_streaks.empty else 0,
    })
