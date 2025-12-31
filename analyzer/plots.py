# analyzer/plots.py

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import AutoLocator

from analyzer.config import config, apply_plot_style

def show_all_charts(df: pd.DataFrame, df_sorted: pd.DataFrame, day_stats: pd.DataFrame, asset_stats: pd.DataFrame):
    """
    Рисует все 9 графиков в одном окне 3x3
    """
    # Применяем стили из конфига (тёмная тема, размеры, цвета)
    apply_plot_style()

    # Подготовка общих данных
    df_plot = df.sort_values('Время открытия').reset_index(drop=True)
    dates = sorted(day_stats.index)

    # Цвета из конфига
    COLOR_WIN = config.get('colors', 'win')
    COLOR_LOSS = config.get('colors', 'loss')
    COLOR_LINE = config.get('colors', 'line')
    COLOR_THRESHOLD = config.get('colors', 'threshold')
    COLOR_WEEK = config.get('colors', 'week_progress')

    fig = plt.figure(figsize=(18, 12))

    # 1. Винрейт по дням
    plt.subplot(3, 3, 1)
    plt.plot(range(len(dates)), day_stats['Винрейт'].loc[dates], marker='o', color=COLOR_WIN,
             linewidth=3, markersize=10, markeredgecolor='white', markeredgewidth=1.5)
    plt.axhline(y=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7, label='50% порог')
    plt.title('Винрейт по дням', fontsize=15, fontweight='bold', pad=15)
    plt.ylabel('Винрейт, %', fontsize=12)
    plt.xlabel('Дата', fontsize=12)
    plt.grid(True, alpha=0.5)
    plt.legend(fontsize=10)
    plt.ylim(0, 100)

    # 2. Скользящий винрейт
    plt.subplot(3, 3, 2)
    df_plot['Win_binary'] = (df_plot['Результат'] == 'Win').astype(int)
    rolling_window = max(int(len(df_plot) * config.getint('analysis_settings', 'rolling_window_percent') / 100), 1)
    df_plot['Rolling_WR'] = df_plot['Win_binary'].rolling(window=rolling_window, min_periods=1).mean() * 100
    plt.plot(range(len(df_plot)), df_plot['Rolling_WR'], color=COLOR_LINE, linewidth=3)
    plt.axhline(y=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
    plt.title(f'Скользящий винрейт (окно {config.getint("analysis_settings", "rolling_window_percent")}% = {rolling_window} сделок)',
              fontsize=15, fontweight='bold', pad=15)
    plt.ylabel('Винрейт, %', fontsize=12)
    plt.xlabel('Номер сделки', fontsize=12)
    plt.grid(True, alpha=0.5)
    plt.ylim(0, 100)

    # 3. Топ-N активов
    plt.subplot(3, 3, 3)
    top_n = config.getint('analysis_settings', 'top_assets_count')
    top_assets = asset_stats.head(top_n)[::-1]
    colors = [COLOR_WIN if x >= 50 else COLOR_LOSS for x in top_assets['Винрейт']]
    plt.barh(range(len(top_assets)), top_assets['Винрейт'], color=colors, edgecolor='white', linewidth=1.5)
    plt.yticks(range(len(top_assets)), top_assets.index, fontsize=10)
    plt.axvline(x=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
    plt.title(f'Топ-{top_n} активов по винрейту', fontsize=15, fontweight='bold', pad=15)
    plt.xlabel('Винрейт, %', fontsize=12)
    plt.xlim(0, 100)
    plt.grid(True, alpha=0.5, axis='x')

    # 4. Пирог Win/Loss
    plt.subplot(3, 3, 4)
    win_count = len(df_plot[df_plot['Результат'] == 'Win'])
    loss_count = len(df_plot[df_plot['Результат'] == 'Loss'])
    plt.pie([win_count, loss_count], labels=['Win', 'Loss'], autopct='%1.1f%%',
            colors=[COLOR_WIN, COLOR_LOSS], startangle=90,
            textprops={'fontsize': 13, 'weight': 'bold'},
            wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    plt.title(f'Распределение Win/Loss\n({win_count}W / {loss_count}L)', fontsize=15, fontweight='bold', pad=15)

    # 5. Винрейт по часам
    plt.subplot(3, 3, 5)
    hour_stats = df_plot.groupby('Час').agg(Винрейт=('Результат', lambda x: (x == 'Win').mean() * 100)) \
                        .reindex(range(24), fill_value=float('nan')).round(2)
    colors_hour = [COLOR_WIN if x >= 50 else COLOR_LOSS if not pd.isna(x) else '#333333' for x in hour_stats['Винрейт']]
    plt.bar(hour_stats.index, hour_stats['Винрейт'], color=colors_hour, edgecolor='white', linewidth=1.5)
    plt.axhline(y=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
    plt.title('Винрейт по часам дня', fontsize=15, fontweight='bold', pad=15)
    plt.xlabel('Час', fontsize=12)
    plt.ylabel('Винрейт, %', fontsize=12)
    plt.ylim(0, 100)
    plt.grid(True, alpha=0.5, axis='y')
    plt.xticks(range(24), [str(h) for h in range(24)])

    # 6. Прогресс по неделям
    plt.subplot(3, 3, 6)
    df_plot['Неделя'] = pd.to_datetime(df_plot['Дата']).dt.isocalendar().week
    week_order = df_plot.groupby('Неделя')['Дата'].min().sort_values()
    week_stats = df_plot.groupby('Неделя').agg(
        Винрейт=('Результат', lambda x: (x=='Win').mean()*100),
        Сделок=('Результат', 'count')
    ).round(2).loc[week_order.index]

    if len(week_stats) > 1:
        plt.plot(range(len(week_stats)), week_stats['Винрейт'], marker='o', color=COLOR_WEEK,
                 linewidth=4, markersize=12, markeredgecolor='white', markeredgewidth=2)
        plt.axhline(y=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
        for i, (week, row) in enumerate(week_stats.iterrows()):
            plt.text(i, row['Винрейт'] + 3, f"{row['Винрейт']:.1f}%\n({int(row['Сделок'])})",
                     ha='center', fontsize=10, color='white', weight='bold')
        plt.title('Прогресс по неделям', fontsize=15, fontweight='bold', pad=15)
        plt.ylabel('Винрейт, %', fontsize=12)
        plt.xlabel('Неделя', fontsize=12)
        plt.ylim(0, 100)
        plt.grid(True, alpha=0.5)
        plt.xticks(range(len(week_stats)), week_stats.index)
    else:
        plt.text(0.5, 0.5, 'Недостаточно данных\n(нужно >1 недели)',
                 ha='center', va='center', fontsize=14, color='#888888', weight='bold')
        plt.title('Прогресс по неделям', fontsize=15, fontweight='bold', pad=15)
        plt.xlim(0, 1)
        plt.ylim(0, 1)

    # 7. Прогресс баланса
    plt.subplot(3, 3, 7)
    daily_balance = df_sorted.groupby('Дата')['Баланс'].last()
    plt.axhline(y=df_sorted['Баланс'].iloc[0], color=COLOR_THRESHOLD, linestyle='--', linewidth=2,
                label=f'Текущий баланс: {df_sorted["Баланс"].iloc[0]:.2f}')
    plt.plot(range(len(dates)), daily_balance.loc[dates], marker='o', color=COLOR_LINE,
             linewidth=3, markersize=8, markeredgecolor='white', markeredgewidth=1.5)
    plt.title('Прогресс баланса', fontsize=15, fontweight='bold', pad=15)
    plt.ylabel('Баланс', fontsize=12)
    plt.xlabel('Дата', fontsize=12)
    plt.grid(True, alpha=0.5)
    plt.legend(fontsize=10)

    # 8. Кумулятивная прибыль
    plt.subplot(3, 3, 8)
    cumulative_daily_profit = df_sorted.groupby('Дата')['Прибыль числом'].sum().cumsum()
    plt.plot(range(len(dates)), cumulative_daily_profit.loc[dates], marker='o', color=COLOR_WIN,
             linewidth=3, markersize=8, markeredgecolor='white', markeredgewidth=1.5)
    plt.axhline(y=0, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
    plt.title('Кумулятивная прибыль', fontsize=15, fontweight='bold', pad=15)
    plt.ylabel('Прибыль', fontsize=12)
    plt.xlabel('Дата', fontsize=12)
    plt.grid(True, alpha=0.5)

    # 9. Прибыль по дням
    plt.subplot(3, 3, 9)
    colors_day_profit = [COLOR_WIN if x > 0 else COLOR_LOSS for x in day_stats['Прибыль'].loc[dates]]
    plt.bar(range(len(dates)), day_stats['Прибыль'].loc[dates], color=colors_day_profit,
            edgecolor='white', linewidth=1.5)
    plt.axhline(y=0, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
    plt.title('Прибыль по дням', fontsize=15, fontweight='bold', pad=15)
    plt.ylabel('Прибыль', fontsize=12)
    plt.xlabel('Дата', fontsize=12)
    plt.grid(True, alpha=0.5, axis='y')

    # Общие настройки осей с датами
    plt.tight_layout(pad=2.0)
    for ax in fig.get_axes():
        if ax.get_xlabel() == 'Дата':
            ax.set_xticks(range(len(dates)))
            ax.set_xticklabels([d.strftime('%d %b.') for d in dates])
            ax.xaxis.set_major_locator(AutoLocator())
            plt.setp(ax.get_xticklabels(), rotation=45, ha='center')

    plt.show()