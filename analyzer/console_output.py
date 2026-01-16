"""
Модуль для визуализации статистики в консоли и экспорта отчетов.

Содержит функции для форматированного вывода метрик, анализа активов
и сохранения результатов в формате Markdown.
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from colorama import Fore, Style

from analyzer.utils import calculate_max_streak, color_profit, color_winrate


def print_general_statistics(df: pd.DataFrame, main_metrics: dict) -> None:
    """Выводит в консоль блок сводных метрик по всем сделкам."""
    print("\n" + "=" * 70)
    print(" " * 25 + "ОБЩАЯ СТАТИСТИКА")
    print("=" * 70)
    print(f"Всего сделок:       {main_metrics['total_trades']}")
    print(f"Винрейт:            {color_winrate(main_metrics['winrate'])}")
    print(f"Общая прибыль:      {color_profit(main_metrics['total_profit'])} {main_metrics['currency']}")
    print(f"Профит-фактор:      {main_metrics['profit_factor']:.2f}")
    print(f"Средний вин:        {Fore.GREEN}+{main_metrics['avg_win']:.2f}{Style.RESET_ALL}")
    print(f"Средний лосс:       {Fore.RED}-{main_metrics['avg_loss']:.2f}{Style.RESET_ALL}")
    print(f"Макс. серия вин:    {Fore.GREEN}{calculate_max_streak(df, 'Win')}{Style.RESET_ALL}")
    print(f"Макс. серия лоссов: {Fore.RED}{calculate_max_streak(df, 'Loss')}{Style.RESET_ALL}")


def print_day_statistics(day_stats: pd.DataFrame) -> None:
    """Выводит таблицу эффективности торговли по календарным дням."""
    print("\n" + "=" * 70)
    print(" " * 25 + "ВИНРЕЙТ ПО ДНЯМ")
    print("=" * 70)

    for date, row in day_stats.iterrows():
        wr_colored = color_winrate(row["Винрейт"])
        profit_colored = color_profit(row["Прибыль"])
        print(f"{date}  |  Сделок: {int(row['Сделок'])}  |  Винрейт: {wr_colored}  |  Прибыль: {profit_colored}")


def print_asset_statistics(asset_stats: pd.DataFrame) -> None:
    """Выводит детальную статистику по каждому торговому активу."""
    print("\n" + "=" * 115)
    print(" " * 50 + "ПО АКТИВАМ")
    print("=" * 115)

    for asset, row in asset_stats.iterrows():
        wr_colored = color_winrate(row["Винрейт"])
        profit_colored = color_profit(row["Прибыль"])
        # Используем фиксированную ширину колонок для выравнивания таблицы в консоли
        print(
            f"{asset:20} | Сделок: {int(row['Сделок']):3} | Винрейт: {wr_colored:20} | Прибыль: {profit_colored:20} "
            f"| Серия_вин: {Fore.GREEN}{int(row['Серия_вин'])}{Style.RESET_ALL} | Серия_лосс: {Fore.RED}{int(row['Серия_лосс'])}{Style.RESET_ALL}"
        )


def print_hour_statistics(df: pd.DataFrame) -> None:
    """Выводит распределение торговых результатов по часам внутри каждого дня."""
    print("\n" + "=" * 70)
    print(" " * 20 + "ПО ЧАСАМ ДЛЯ КАЖДОГО ДНЯ")
    print("=" * 70)

    for date in sorted(df["Дата"].unique()):
        day_df = df[df["Дата"] == date]
        print(f"\n{Fore.CYAN}{date}:{Style.RESET_ALL}")
        # Группируем данные внутри дня для получения почасовой активности
        hour_stats = (
            day_df
            .groupby("Час")
            .agg(
                Сделок=("Результат", "count"),
                Винрейт=("Результат", lambda x: (x == "Win").mean() * 100),
                Прибыль=("Прибыль числом", "sum"),
            )
            .round(2)
        )

        for hour, row in hour_stats.iterrows():
            wr_colored = color_winrate(row["Винрейт"])
            profit_colored = color_profit(row["Прибыль"])
            print(
                f"  Час {hour:2}  |  Сделок: {int(row['Сделок']):2}  |  Винрейт: {wr_colored:20}  |  Прибыль: {profit_colored}"
            )


def save_statistics_to_md(
    main_metrics: dict, day_stats: pd.DataFrame, asset_stats: pd.DataFrame, df: pd.DataFrame, selected_files: list
) -> None:
    """
    Генерирует отчет в формате Markdown с полным анализом торговой сессии.

    Args:
        main_metrics: Словарь с ключевыми показателями (профит-фактор, винрейт и др.).
        day_stats: Сгруппированные данные по дням.
        asset_stats: Сгруппированные данные по активам.
        df: Полный датафрейм со всеми сделками.
        selected_files: Список путей к обработанным файлам.

    """
    now = datetime.now(timezone.utc).astimezone()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = Path(f"outputs/{timestamp} статистика.md")

    with filename.open("w", encoding="utf-8") as f:
        f.write(f"# 📊 Анализ сделок — {timestamp}\n\n")

        f.write("## Используемые файлы\n\n")
        for file in selected_files:
            # Очищаем путь от названий папок для компактности в отчете
            file_name = str(file).replace("trades\\", "").replace("trades/", "")
            f.write(f"- {file_name}\n")

        f.write(f"\n**Всего сделок:** {main_metrics['total_trades']}\n\n")

        f.write("## Общая статистика\n\n")
        f.write(f"- Винрейт: {main_metrics['winrate']:.2f}%\n")
        f.write(f"- Общая прибыль: {main_metrics['total_profit']:+.2f} {main_metrics['currency']}\n")
        f.write(f"- Профит-фактор: {main_metrics['profit_factor']:.2f}\n")
        f.write(f"- Средний выигрыш: +{main_metrics['avg_win']:.2f}\n")
        f.write(f"- Средний проигрыш: -{main_metrics['avg_loss']:.2f}\n")
        f.write(f"- Макс. серия выигрышей: {calculate_max_streak(df, 'Win')}\n")
        f.write(f"- Макс. серия проигрышей: {calculate_max_streak(df, 'Loss')}\n\n")

        # Формируем таблицы Markdown для каждого блока данных
        f.write("## Винрейт по дням\n\n")
        f.write("| Дата       | Сделок | Винрейт | Прибыль    |\n")
        f.write("|------------|--------|---------|------------|\n")
        for date_val, row in day_stats.iterrows():
            profit_sign = "+" if row["Прибыль"] > 0 else ""
            f.write(
                f"| {date_val} | {int(row['Сделок'])}    | {row['Винрейт']:.2f}%   | {profit_sign}{row['Прибыль']:.2f} |\n"
            )
        f.write("\n")

        f.write("## По активам\n\n")
        f.write("| Актив              | Сделок | Винрейт | Прибыль    | Серия вин | Серия лосс |\n")
        f.write("|--------------------|--------|---------|------------|-----------|------------|\n")
        for asset, row in asset_stats.iterrows():
            profit_sign = "+" if row["Прибыль"] > 0 else ""
            f.write(
                f"| {asset:18} | {int(row['Сделок']):6} | {row['Винрейт']:.2f}%   | {profit_sign}{row['Прибыль']:.2f} | {int(row['Серия_вин']):9} | {int(row['Серия_лосс']):10} |\n"
            )
        f.write("\n")

        f.write("## По часам для каждого дня\n\n")
        for date_val in sorted(df["Дата"].unique()):
            day_df = df[df["Дата"] == date_val]
            f.write(f"### {date_val}\n\n")
            f.write("| Час | Сделок | Винрейт | Прибыль    |\n")
            f.write("|-----|--------|---------|------------|\n")

            # Повторный расчет часовой статистики для записи в файл
            hour_stats_md = (
                day_df
                .groupby("Час")
                .agg(
                    Сделок=("Результат", "count"),
                    Винрейт=("Результат", lambda x: (x == "Win").mean() * 100),
                    Прибыль=("Прибыль числом", "sum"),
                )
                .round(2)
            )
            for hour, row in hour_stats_md.iterrows():
                p_sign = "+" if row["Прибыль"] > 0 else ""
                f.write(
                    f"| {hour:3} | {int(row['Сделок']):6} | {row['Винрейт']:.2f}%   | {p_sign}{row['Прибыль']:.2f} |\n"
                )
            f.write("\n")

    print(f"{Fore.GREEN}📄 Статистика сохранена: {filename}{Style.RESET_ALL}")


def print_all_statistics(
    df: pd.DataFrame, main_metrics: dict, day_stats: pd.DataFrame, asset_stats: pd.DataFrame
) -> None:
    """Выполняет последовательный вывод всех аналитических блоков в консоль."""
    print_general_statistics(df, main_metrics)
    print_day_statistics(day_stats)
    print_asset_statistics(asset_stats)
    print_hour_statistics(df)
