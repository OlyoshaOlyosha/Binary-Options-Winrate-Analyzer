"""
Модуль для визуализации статистики в консоли и экспорта отчетов.

Содержит функции для форматированного вывода метрик, анализа активов
и сохранения результатов в формате Markdown.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

import pandas as pd
from colorama import Fore, Style

from analyzer.utils import calculate_max_streak, color_profit, color_winrate


def print_general_statistics(df: pd.DataFrame, main_metrics: dict) -> None:
    """
    Выводит в консоль сводную таблицу ключевых метрик торговой сессии.

    Args:
        df: Полный датафрейм со всеми сделками.
        main_metrics: Словарь с рассчитанными показателями (винрейт, профит-фактор и др.).

    """
    width = 70
    print("\n" + "=" * width)
    print(f"{'ОБЩАЯ СТАТИСТИКА':^{width}}")
    print("=" * width)

    # Формируем список кортежей для итерации (Метка, Значение)
    stats = [
        ("Всего сделок:", f"{main_metrics['total_trades']}"),
        ("Винрейт:", f"{color_winrate(main_metrics['winrate'])}"),
        ("Общая прибыль:", f"{color_profit(main_metrics['total_profit'])} {main_metrics['currency']}"),
        ("Профит-фактор:", f"{main_metrics['profit_factor']:.2f}"),
        ("Средний вин:", f"{Fore.GREEN}+{main_metrics['avg_win']:.2f}{Style.RESET_ALL}"),
        ("Средний лосс:", f"{Fore.RED}-{main_metrics['avg_loss']:.2f}{Style.RESET_ALL}"),
        ("Макс. серия вин:", f"{Fore.GREEN}{calculate_max_streak(df, 'Win')}{Style.RESET_ALL}"),
        ("Макс. серия лоссов:", f"{Fore.RED}{calculate_max_streak(df, 'Loss')}{Style.RESET_ALL}"),
    ]

    for label, value in stats:
        print(f"{label:<25} {value}")


def print_day_statistics(day_stats: pd.DataFrame) -> None:
    """
    Выводит таблицу распределения результатов по дням.

    Args:
        day_stats: Сгруппированные данные по датам.

    """
    # Ширина колонок и расчет общей ширины таблицы
    w_date, w_trades, w_wr, w_profit = 12, 8, 12, 14
    color_offset = 9  # Длина ANSI-последовательностей Colorama
    total_w = w_date + w_trades + w_wr + w_profit + 13

    print("\n" + "=" * total_w)
    print(f"{'ВИНРЕЙТ ПО ДНЯМ':^{total_w}}")
    print("=" * total_w)

    header = f"| {'Дата':^{w_date}} | {'Сделок':^{w_trades}} | {'Винрейт':^{w_wr}} | {'Прибыль':^{w_profit}} |"
    print(header)
    print("-" * total_w)

    for date, row in day_stats.iterrows():
        d_str = str(date).center(w_date)
        t_str = str(int(row["Сделок"])).center(w_trades)

        # Выравнивание по точке: фиксируем длину текста до раскрашивания
        wr_raw = f"{row['Винрейт']:>7.2f}%"
        pr_raw = f"{row['Прибыль']:>+10.2f}"

        # Оборачиваем в цвета, сохраняя внутренние отступы
        wr_col = color_winrate(row["Винрейт"]).replace(f"{row['Винрейт']:.2f}%", wr_raw)
        pr_col = color_profit(row["Прибыль"]).replace(f"{row['Прибыль']:+.2f}", pr_raw)

        print(
            f"| {d_str} | {t_str} | {wr_col.center(w_wr + color_offset)} | {pr_col.center(w_profit + color_offset)} |"
        )


def print_asset_statistics(asset_stats: pd.DataFrame) -> None:
    """
    Выводит детальную таблицу результатов по торговым инструментам.

    Args:
        asset_stats: Сгруппированные данные по активам.

    """
    max_name = max(asset_stats.index.map(str).map(len).max(), 15)
    w_trades, w_wr, w_profit, w_streak = 8, 12, 14, 12
    color_offset = 9
    total_w = max_name + w_trades + w_wr + w_profit + (w_streak * 2) + 19

    print("\n" + "=" * total_w)
    print(f"{'ПО АКТИВАМ':^{total_w}}")
    print("=" * total_w)

    header = (
        f"| {'Актив':^{max_name}} | {'Сделок':^{w_trades}} | {'Винрейт':^{w_wr}} | "
        f"{'Прибыль':^{w_profit}} | {'Max Win':^{w_streak}} | {'Max Loss':^{w_streak}} |"
    )
    print(header)
    print("-" * total_w)

    for asset, row in asset_stats.iterrows():
        a_str = str(asset).center(max_name)
        t_str = str(int(row["Сделок"])).center(w_trades)

        wr_raw = f"{row['Винрейт']:>7.2f}%"
        pr_raw = f"{row['Прибыль']:>+10.2f}"

        wr_col = color_winrate(row["Винрейт"]).replace(f"{row['Винрейт']:.2f}%", wr_raw)
        pr_col = color_profit(row["Прибыль"]).replace(f"{row['Прибыль']:+.2f}", pr_raw)

        s_win = f"{Fore.GREEN}{int(row['Серия_вин'])!s:^{w_streak}}{Style.RESET_ALL}"
        s_loss = f"{Fore.RED}{int(row['Серия_лосс'])!s:^{w_streak}}{Style.RESET_ALL}"

        print(
            f"| {a_str} | {t_str} | {wr_col.center(w_wr + color_offset)} | "
            f"{pr_col.center(w_profit + color_offset)} | {s_win} | {s_loss} |"
        )


def print_hour_statistics(df: pd.DataFrame) -> None:
    """
    Анализирует и выводит почасовую активность для каждого дня торговой сессии.

    Args:
        df: Полный датафрейм со всеми сделками.

    """
    w_trades, w_wr, w_profit = 8, 12, 14
    color_offset = 9
    total_w = 44 + w_trades + w_wr + w_profit  # Адаптивная ширина под заголовок

    print("\n" + "=" * total_w)
    print(f"{'ПО ЧАСАМ ДЛЯ КАЖДОГО ДНЯ':^{total_w}}")
    print("=" * total_w)

    for date in sorted(df["Дата"].unique()):
        day_df = df[df["Дата"] == date]
        print(f"\n{Fore.CYAN}📅 {date}{Style.RESET_ALL}")

        header = f"| {'Час':^6} | {'Сделок':^{w_trades}} | {'Винрейт':^{w_wr}} | {'Прибыль':^{w_profit}} |"
        print(header)
        print("-" * len(header))

        h_stats = (
            day_df
            .groupby("Час")
            .agg(
                S=("Результат", "count"),
                W=("Результат", lambda x: (x == "Win").mean() * 100),
                P=("Прибыль числом", "sum"),
            )
            .round(2)
        )

        for hour, row in h_stats.iterrows():
            h_str = f"{hour:02d}".center(6)
            t_str = str(int(row["S"])).center(w_trades)
            wr_col = color_winrate(row["W"]).replace(f"{row['W']:.2f}%", f"{row['W']:>7.2f}%")
            pr_col = color_profit(row["P"]).replace(f"{row['P']:+.2f}", f"{row['P']:>+10.2f}")

            print(
                f"| {h_str} | {t_str} | {wr_col.center(w_wr + color_offset)} | "
                f"{pr_col.center(w_profit + color_offset)} |"
            )


def _write_section(f: TextIO, title: str, header: str, sep: str) -> None:
    """Записывает заголовок секции и шапку таблицы."""
    f.write(f"## {title}\n\n")
    f.write(header + "\n")
    f.write(sep + "\n")


def save_statistics_to_md(
    main_metrics: dict, day_stats: pd.DataFrame, asset_stats: pd.DataFrame, df: pd.DataFrame, selected_files: list[Path]
) -> None:
    """
    Формирует детализированный Markdown-отчет и сохраняет его в директорию outputs.

    Args:
        main_metrics: Словарь с ключевыми показателями стратегии.
        day_stats: Статистика, сгруппированная по дням.
        asset_stats: Статистика, сгруппированная по активам.
        df: Исходный датафрейм.
        selected_files: Список путей к обработанным CSV файлам.

    """
    now = datetime.now(timezone.utc).astimezone()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = Path(f"outputs/{timestamp} статистика.md")
    filename.parent.mkdir(parents=True, exist_ok=True)

    with filename.open("w", encoding="utf-8") as f:
        f.write(f"# 📊 Анализ сделок — {timestamp}\n\n")
        f.write("## Используемые файлы\n\n")
        for file in selected_files:
            # Очистка имени файла от путей для читаемости
            f.write(f"- {file.name}\n")

        f.write(f"\n**Всего сделок:** {main_metrics['total_trades']}\n\n")

        # 1. Сводная статистика
        f.write("## Общая статистика\n\n")
        stats_list = [
            ("Винрейт:", f"{main_metrics['winrate']:.2f}%"),
            ("Общая прибыль:", f"{main_metrics['total_profit']:+.2f} {main_metrics['currency']}"),
            ("Профит-фактор:", f"{main_metrics['profit_factor']:.2f}"),
            ("Средний выигрыш:", f"+{main_metrics['avg_win']:.2f}"),
            ("Средний проигрыш:", f"-{main_metrics['avg_loss']:.2f}"),
            ("Макс. серия выигрышей:", str(calculate_max_streak(df, "Win"))),
            ("Макс. серия проигрышей:", str(calculate_max_streak(df, "Loss"))),
        ]
        for label, val in stats_list:
            f.write(f"- {label:<25} **{val}**\n")
        f.write("\n")

        # Ширина колонок для MD таблиц
        w_date, w_asset, w_trades, w_wr, w_profit, w_streak = 12, 20, 8, 12, 14, 12

        # 2. Секция: По дням
        h_day = f"| {'Дата':^{w_date}} | {'Сделок':^{w_trades}} | {'Винрейт':^{w_wr}} | {'Прибыль':^{w_profit}} |"
        s_day = f"|{'-' * (w_date + 2)}|{'-' * (w_trades + 2)}|{'-' * (w_wr + 2)}|{'-' * (w_profit + 2)}|"
        _write_section(f, "Винрейт по дням", h_day, s_day)

        for date_val, row in day_stats.iterrows():
            d_s = str(date_val).center(w_date)
            t_s = str(int(row["Сделок"])).center(w_trades)
            w_v = f"{row['Винрейт']:>7.2f}%".center(w_wr)
            p_v = f"{row['Прибыль']:>+10.2f}".center(w_profit)
            f.write(f"| {d_s} | {t_s} | {w_v} | {p_v} |\n")
        f.write("\n")

        # 3. Секция: По активам
        h_as = (
            f"| {'Актив':^{w_asset}} | {'Сделок':^{w_trades}} | {'Винрейт':^{w_wr}} | "
            f"{'Прибыль':^{w_profit}} | {'Серия вин':^{w_streak}} | {'Серия лосс':^{w_streak}} |"
        )
        s_as = (
            f"|{'-' * (w_asset + 2)}|{'-' * (w_trades + 2)}|{'-' * (w_wr + 2)}|"
            f"{'-' * (w_profit + 2)}|{'-' * (w_streak + 2)}|{'-' * (w_streak + 2)}|"
        )
        _write_section(f, "По активам", h_as, s_as)

        for asset, row in asset_stats.iterrows():
            a_s = str(asset).center(w_asset)
            t_s = str(int(row["Сделок"])).center(w_trades)
            w_v = f"{row['Винрейт']:>7.2f}%".center(w_wr)
            p_v = f"{row['Прибыль']:>+10.2f}".center(w_profit)
            sw = str(int(row["Серия_вин"])).center(w_streak)
            sl = str(int(row["Серия_лосс"])).center(w_streak)
            f.write(f"| {a_s} | {t_s} | {w_v} | {p_v} | {sw} | {sl} |\n")
        f.write("\n")

        # 4. Секция: По часам
        f.write("## По часам для каждого дня\n\n")
        for date_val in sorted(df["Дата"].unique()):
            day_df = df[df["Дата"] == date_val]
            f.write(f"### {date_val}\n\n")
            h_st = (
                day_df
                .groupby("Час")
                .agg(
                    S=("Результат", "count"),
                    W=("Результат", lambda x: (x == "Win").mean() * 100),
                    P=("Прибыль числом", "sum"),
                )
                .round(2)
            )

            f.write(f"| {'Час':^6} | {'Сделок':^{w_trades}} | {'Винрейт':^{w_wr}} | {'Прибыль':^{w_profit}} |\n")
            f.write(f"|{'-' * 8}|{'-' * (w_trades + 2)}|{'-' * (w_wr + 2)}|{'-' * (w_profit + 2)}|\n")
            for hour, row in h_st.iterrows():
                h_s, t_s = str(hour).center(6), str(int(row["S"])).center(w_trades)
                w_v = f"{row['W']:>7.2f}%".center(w_wr)
                p_v = f"{row['P']:>+10.2f}".center(w_profit)
                f.write(f"| {h_s} | {t_s} | {w_v} | {p_v} |\n")
            f.write("\n")

    print(f"{Fore.GREEN}📄 Отчет сохранен: {filename}{Style.RESET_ALL}")


def print_all_statistics(
    df: pd.DataFrame, main_metrics: dict, day_stats: pd.DataFrame, asset_stats: pd.DataFrame
) -> None:
    """Запускает полный цикл вывода аналитической информации в терминал."""
    print_general_statistics(df, main_metrics)
    print_day_statistics(day_stats)
    print_asset_statistics(asset_stats)
    print_hour_statistics(df)
