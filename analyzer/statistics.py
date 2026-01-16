"""
Модуль статистических вычислений.

Обрабатывает агрегацию данных по торговым показателям, временным периодам
и отдельным активам.
"""

import pandas as pd

from analyzer.utils import calculate_asset_streaks


def calculate_main_metrics(df: pd.DataFrame) -> dict:
    """
    Рассчитывает ключевые показатели эффективности торговли.

    Вычисляет винрейт, профит-фактор (отношение валовой прибыли к валовому убытку)
    и средние значения сделок.

    Args:
        df: DataFrame с обработанными данными сделок.

    Returns:
        Словарь с метриками: total_trades, winrate, total_profit,
        profit_factor, avg_win, avg_loss, currency.

    """
    total_trades = len(df)
    wins = len(df[df["Результат"] == "Win"])
    winrate = wins / total_trades * 100 if total_trades > 0 else 0

    # Расчет валовой прибыли и убытка для профит-фактора
    pos_profits = df[df["Прибыль числом"] > 0]["Прибыль числом"]
    neg_profits = df[df["Прибыль числом"] < 0]["Прибыль числом"]

    profit_factor = pos_profits.sum() / abs(neg_profits.sum()) if not neg_profits.empty else float("inf")

    avg_win = pos_profits.mean() if not pos_profits.empty else 0
    avg_loss = abs(neg_profits.mean()) if not neg_profits.empty else 0
    total_profit = df["Прибыль числом"].sum()

    return {
        "total_trades": total_trades,
        "winrate": winrate,
        "total_profit": total_profit,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "currency": df["Валюта"].iloc[0] if total_trades > 0 else "USD",
    }


def calculate_day_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Группирует данные по датам и вычисляет ежедневную эффективность.

    Args:
        df: DataFrame с колонками 'Дата', 'Результат', 'Прибыль числом'.

    Returns:
        DataFrame с индексами-датами и агрегированными метриками.

    """
    return (
        df
        .groupby("Дата")
        .agg(
            Сделок=("Результат", "count"),
            Винрейт=("Результат", lambda x: (x == "Win").mean() * 100),
            Прибыль=("Прибыль числом", "sum"),
        )
        .round(2)
    )


def calculate_asset_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Анализирует результативность торговли по каждому активу отдельно.

    Использует функцию calculate_asset_streaks для расчета серий внутри групп.

    Args:
        df: DataFrame с данными сделок.

    Returns:
        DataFrame, отсортированный по убыванию винрейта.

    """
    # Применяем сложный расчет серий к каждой группе активов
    asset_stats = df.groupby("Актив").apply(calculate_asset_streaks)

    # Принудительное приведение типов для корректного отображения и исключения ошибок
    asset_stats["Сделок"] = asset_stats["Сделок"].astype(int)
    asset_stats["Серия_вин"] = asset_stats["Серия_вин"].astype(int)
    asset_stats["Серия_лосс"] = asset_stats["Серия_лосс"].astype(int)
    asset_stats["Винрейт"] = asset_stats["Винрейт"].round(2)
    asset_stats["Прибыль"] = asset_stats["Прибыль"].round(2)

    return asset_stats.sort_values("Винрейт", ascending=False)
