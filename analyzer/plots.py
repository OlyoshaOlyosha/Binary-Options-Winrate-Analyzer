"""
Модуль графической визуализации результатов анализа.

Отвечает за генерацию многопанельных отчетов (фигур) Matplotlib,
отрисовку скользящих винрейтов, распределения прибыли и истории баланса.
"""

from datetime import datetime, timezone
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from colorama import Fore, Style
from matplotlib.figure import Figure
from matplotlib.ticker import AutoLocator

from analyzer.config import apply_plot_style, config

# Порог винрейта для цветовой индикации (зеленый/красный)
WINRATE_THRESHOLD = 50


def show_all_charts(  # noqa: PLR0913
    df: pd.DataFrame,
    df_sorted: pd.DataFrame,
    day_stats: pd.DataFrame,
    asset_stats: pd.DataFrame,
    current_balance: float,
    *,
    save_graph: bool = False,
) -> None:
    """
    Создает и отображает комплексное окно с 9 аналитическими графиками.

    Формирует сетку 3x3, настраивает стили, временные оси и опционально
    сохраняет результат в PNG.
    """
    print("\n" + "=" * 60)
    print(f"{Fore.YELLOW}ОТКРЫВАЮ ОКНО С ГРАФИКАМИ...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Дополнительная визуализация данных в графическом виде.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Закройте окно с графиками, чтобы завершить программу.{Style.RESET_ALL}")
    print("=" * 60 + "\n")

    apply_plot_style()

    # Сортировка данных по времени для корректности временных рядов
    df_plot = df.sort_values("Время открытия").reset_index(drop=True)
    dates = sorted(day_stats.index)

    # Централизованное управление цветами из конфигурации
    colors = {
        "win": config.get("colors", "win"),
        "loss": config.get("colors", "loss"),
        "line": config.get("colors", "line"),
        "threshold": config.get("colors", "threshold"),
        "week": config.get("colors", "week_progress"),
    }

    fig = plt.figure(figsize=(18, 12))

    # Отрисовка сетки графиков по рядам
    _draw_top_row(df_plot, asset_stats, dates, day_stats, colors)
    _draw_middle_row(df_plot, colors)
    _draw_bottom_row(df_sorted, dates, day_stats, current_balance, colors)

    # Финализация внешнего вида: настройка дат и отступов
    plt.tight_layout(pad=2.0)
    for ax in fig.get_axes():
        if ax.get_xlabel() == "Дата":
            ax.set_xticks(range(len(dates)))
            # Форматируем даты для читаемости на оси X
            ax.set_xticklabels([d.strftime("%d %b.") for d in dates])
            ax.xaxis.set_major_locator(AutoLocator())
            plt.setp(ax.get_xticklabels(), rotation=45, ha="center")

    if save_graph:
        _save_figure(fig)

    plt.show()


def _draw_top_row(
    df_plot: pd.DataFrame, asset_stats: pd.DataFrame, dates: list[Any], day_stats: pd.DataFrame, colors: dict[str, str]
) -> None:
    """Рисует верхний ряд: Винрейт по дням, Скользящий винрейт и Топ активов."""
    # 1. Линейный график винрейта по дням
    plt.subplot(3, 3, 1)
    plt.plot(range(len(dates)), day_stats["Винрейт"].loc[dates], marker="o", color=colors["win"], linewidth=3)
    plt.axhline(y=WINRATE_THRESHOLD, color=colors["threshold"], linestyle="--", label="50% порог")
    plt.title("Винрейт по дням", fontsize=15, fontweight="bold", pad=15)
    plt.ylim(0, 100)
    plt.legend(fontsize=10)

    # 2. Скользящее среднее винрейта для выявления трендов
    plt.subplot(3, 3, 2)
    df_plot["Win_binary"] = (df_plot["Результат"] == "Win").astype(int)
    roll_pct = config.getint("analysis_settings", "rolling_window_percent")
    rolling_window = max(int(len(df_plot) * roll_pct / 100), 1)
    df_plot["Rolling_WR"] = df_plot["Win_binary"].rolling(window=rolling_window, min_periods=1).mean() * 100

    plt.plot(range(len(df_plot)), df_plot["Rolling_WR"], color=colors["line"], linewidth=3)
    plt.axhline(y=WINRATE_THRESHOLD, color=colors["threshold"], linestyle="--")
    plt.title(f"Скользящий винрейт (окно {roll_pct}%)", fontweight="bold")
    plt.ylim(0, 100)

    # 3. Горизонтальный столбчатый график лучших активов
    plt.subplot(3, 3, 3)
    top_n = config.getint("analysis_settings", "top_assets_count")
    top_assets = asset_stats.head(top_n)[::-1]
    c_list = [colors["win"] if x >= WINRATE_THRESHOLD else colors["loss"] for x in top_assets["Винрейт"]]

    plt.barh(range(len(top_assets)), top_assets["Винрейт"], color=c_list)
    plt.yticks(range(len(top_assets)), list(top_assets.index.astype(str)), fontsize=10)
    plt.axvline(x=WINRATE_THRESHOLD, color=colors["threshold"], linestyle="--")
    plt.title(f"Топ-{top_n} активов", fontweight="bold")


def _draw_middle_row(df_plot: pd.DataFrame, colors: dict[str, str]) -> None:
    """Рисует средний ряд: Пирог Win/Loss, Активность по часам и Недельный прогресс."""
    # 4. Круговая диаграмма общего соотношения сделок
    plt.subplot(3, 3, 4)
    win_count = len(df_plot[df_plot["Результат"] == "Win"])
    loss_count = len(df_plot[df_plot["Результат"] == "Loss"])
    plt.pie(
        [win_count, loss_count],
        labels=["Win", "Loss"],
        autopct="%1.1f%%",
        colors=[colors["win"], colors["loss"]],
        startangle=90,
    )
    plt.title(f"Распределение Win/Loss\n({win_count}W / {loss_count}L)", fontweight="bold")

    # 5. Гистограмма эффективности по времени суток
    plt.subplot(3, 3, 5)
    hour_stats = df_plot.groupby("Час").agg(Винрейт=("Результат", lambda x: (x == "Win").mean() * 100))
    hour_stats = hour_stats.reindex(range(24), fill_value=float("nan"))
    c_h = [
        colors["win"] if x >= WINRATE_THRESHOLD else colors["loss"] if not pd.isna(x) else "#333333"
        for x in hour_stats["Винрейт"]
    ]
    plt.bar(hour_stats.index, hour_stats["Винрейт"], color=c_h)
    plt.axhline(y=WINRATE_THRESHOLD, color=colors["threshold"], linestyle="--")
    plt.title("Винрейт по часам дня", fontweight="bold")
    plt.xticks(range(24), [str(h) for h in range(24)])

    # 6. Динамика результатов по календарным неделям
    plt.subplot(3, 3, 6)
    df_plot["Неделя"] = pd.to_datetime(df_plot["Дата"]).dt.isocalendar().week
    week_order = df_plot.groupby("Неделя")["Дата"].min().sort_values()
    week_stats = (
        df_plot
        .groupby("Неделя")
        .agg(Винрейт=("Результат", lambda x: (x == "Win").mean() * 100), Сделок=("Результат", "count"))
        .loc[week_order.index]
    )

    if len(week_stats) > 1:
        plt.plot(range(len(week_stats)), week_stats["Винрейт"], marker="o", color=colors["week"], linewidth=4)
        for i, (_, row) in enumerate(week_stats.iterrows()):
            plt.text(i, row["Винрейт"] + 3, f"{row['Винрейт']:.1f}%\n({int(row['Сделок'])})", ha="center")
        plt.xticks(range(len(week_stats)), list(week_stats.index.astype(str)))
    plt.title("Прогресс по неделям", fontweight="bold")


def _draw_bottom_row(
    df_sorted: pd.DataFrame, dates: list[Any], day_stats: pd.DataFrame, current_balance: float, colors: dict[str, str]
) -> None:
    """Рисует нижний ряд: Баланс, Кумулятивная прибыль и Прибыль по дням."""
    # 7. История изменения баланса
    plt.subplot(3, 3, 7)
    daily_balance = df_sorted.groupby("Дата")["Баланс"].last()
    plt.axhline(y=current_balance, color=colors["threshold"], linestyle="--", label=f"Баланс: {current_balance:.0f}")
    plt.plot(range(len(dates)), daily_balance.loc[dates], marker="o", color=colors["line"], linewidth=3)
    plt.title("Прогресс баланса", fontweight="bold")
    plt.legend(fontsize=10)

    # 8. Накопительная кривая прибыли
    plt.subplot(3, 3, 8)
    cumulative_profit = df_sorted.groupby("Дата")["Прибыль числом"].sum().cumsum()
    plt.plot(range(len(dates)), cumulative_profit.loc[dates], marker="o", color=colors["win"], linewidth=3)
    plt.axhline(y=0, color=colors["threshold"], linestyle="--")
    plt.title("Кумулятивная прибыль", fontweight="bold")

    # 9. Столбчатый график ежедневного финансового результата
    plt.subplot(3, 3, 9)
    # Цветовая маркировка прибыльных и убыточных дней
    c_p = [colors["win"] if x > 0 else colors["loss"] for x in day_stats["Прибыль"].loc[dates]]
    plt.bar(range(len(dates)), day_stats["Прибыль"].loc[dates], color=c_p)
    plt.axhline(y=0, color=colors["threshold"], linestyle="--")
    plt.title("Прибыль по дням", fontweight="bold")


def _save_figure(fig: Figure) -> None:  # Теперь просто Figure без plt.
    """Вспомогательная функция для сохранения холста в файл."""
    # Получаем текущее время с учетом часового пояса (исправляет DIZ005)
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"outputs/{timestamp} график.png"

    # Сохраняем с высоким DPI для четкости
    fig.savefig(filename, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"{Fore.GREEN}График сохранён: {filename}{Style.RESET_ALL}")
