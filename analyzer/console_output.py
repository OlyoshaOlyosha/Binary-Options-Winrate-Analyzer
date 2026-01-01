from datetime import datetime
from colorama import Fore, Style
import pandas as pd

from analyzer.utils import color_profit, color_winrate, calculate_max_streak

def print_general_statistics(df: pd.DataFrame, main_metrics: dict):
    """Выводит блок 'ОБЩАЯ СТАТИСТИКА'"""
    print("\n" + "="*70)
    print(" "*25 + "ОБЩАЯ СТАТИСТИКА")
    print("="*70)
    print(f"Всего сделок:       {main_metrics['total_trades']}")
    print(f"Винрейт:            {color_winrate(main_metrics['winrate'])}")
    print(f"Общая прибыль:      {color_profit(main_metrics['total_profit'])} {main_metrics['currency']}")
    print(f"Профит-фактор:      {main_metrics['profit_factor']:.2f}")
    print(f"Средний вин:        {Fore.GREEN}+{main_metrics['avg_win']:.2f}{Style.RESET_ALL}")
    print(f"Средний лосс:       {Fore.RED}-{main_metrics['avg_loss']:.2f}{Style.RESET_ALL}")
    print(f"Макс. серия вин:    {Fore.GREEN}{calculate_max_streak(df, 'Win')}{Style.RESET_ALL}")
    print(f"Макс. серия лоссов: {Fore.RED}{calculate_max_streak(df, 'Loss')}{Style.RESET_ALL}")


def print_day_statistics(day_stats: pd.DataFrame):
    """Выводит блок 'ВИНРЕЙТ ПО ДНЯМ'"""
    print("\n" + "="*70)
    print(" "*25 + "ВИНРЕЙТ ПО ДНЯМ")
    print("="*70)

    for date, row in day_stats.iterrows():
        wr_colored = color_winrate(row['Винрейт'])
        profit_colored = color_profit(row['Прибыль'])
        print(f"{date}  |  Сделок: {int(row['Сделок'])}  |  Винрейт: {wr_colored}  |  Прибыль: {profit_colored}")


def print_asset_statistics(asset_stats: pd.DataFrame):
    """Выводит блок 'ПО АКТИВАМ'"""
    print("\n" + "="*115)
    print(" "*50 + "ПО АКТИВАМ")
    print("="*115)

    for asset, row in asset_stats.iterrows():
        wr_colored = color_winrate(row['Винрейт'])
        profit_colored = color_profit(row['Прибыль'])
        print(f"{asset:20} | Сделок: {int(row['Сделок']):3} | Винрейт: {wr_colored:20} | Прибыль: {profit_colored:20} "
              f"| Серия_вин: {Fore.GREEN}{int(row['Серия_вин'])}{Style.RESET_ALL} | Серия_лосс: {Fore.RED}{int(row['Серия_лосс'])}{Style.RESET_ALL}")


def print_hour_statistics(df: pd.DataFrame):
    """Выводит блок 'ПО ЧАСАМ ДЛЯ КАЖДОГО ДНЯ'"""
    print("\n" + "="*70)
    print(" "*20 + "ПО ЧАСАМ ДЛЯ КАЖДОГО ДНЯ")
    print("="*70)

    for date in sorted(df['Дата'].unique()):
        day_df = df[df['Дата'] == date]
        print(f"\n{Fore.CYAN}{date}:{Style.RESET_ALL}")
        hour_stats = day_df.groupby('Час').agg(
            Сделок=('Результат', 'count'),
            Винрейт=('Результат', lambda x: (x=='Win').mean()*100),
            Прибыль=('Прибыль числом', 'sum')
        ).round(2)

        for hour, row in hour_stats.iterrows():
            wr_colored = color_winrate(row['Винрейт'])
            profit_colored = color_profit(row['Прибыль'])
            print(f"  Час {hour:2}  |  Сделок: {int(row['Сделок']):2}  |  Винрейт: {wr_colored:20}  |  Прибыль: {profit_colored}")


def save_statistics_to_md(main_metrics: dict, day_stats: pd.DataFrame, asset_stats: pd.DataFrame, df: pd.DataFrame):
    """Сохраняет полную консольную статистику в Markdown файл в папку outputs"""
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"outputs/{timestamp} статистика.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 📊 Анализ сделок — {timestamp}\n\n")
        f.write(f"**Всего сделок:** {main_metrics['total_trades']}\n\n")
        
        f.write("## Общая статистика\n\n")
        f.write(f"- Винрейт: {main_metrics['winrate']:.2f}%\n")
        f.write(f"- Общая прибыль: {main_metrics['total_profit']:+.2f} {main_metrics['currency']}\n")
        f.write(f"- Профит-фактор: {main_metrics['profit_factor']:.2f}\n")
        f.write(f"- Средний выигрыш: +{main_metrics['avg_win']:.2f}\n")
        f.write(f"- Средний проигрыш: -{main_metrics['avg_loss']:.2f}\n")
        f.write(f"- Макс. серия выигрышей: {calculate_max_streak(df, 'Win')}\n")
        f.write(f"- Макс. серия проигрышей: {calculate_max_streak(df, 'Loss')}\n\n")
        
        f.write("## Винрейт по дням\n\n")
        f.write("| Дата       | Сделок | Винрейт | Прибыль    |\n")
        f.write("|------------|--------|---------|------------|\n")
        for date_val, row in day_stats.iterrows():
            profit_sign = "+" if row['Прибыль'] > 0 else ""
            f.write(f"| {date_val} | {int(row['Сделок'])}    | {row['Винрейт']:.2f}%   | {profit_sign}{row['Прибыль']:.2f} |\n")
        f.write("\n")
        
        f.write("## По активам\n\n")
        f.write("| Актив              | Сделок | Винрейт | Прибыль    | Серия вин | Серия лосс |\n")
        f.write("|--------------------|--------|---------|------------|-----------|------------|\n")
        for asset, row in asset_stats.iterrows():
            profit_sign = "+" if row['Прибыль'] > 0 else ""
            f.write(f"| {asset:18} | {int(row['Сделок']):6} | {row['Винрейт']:.2f}%   | {profit_sign}{row['Прибыль']:.2f} | {int(row['Серия_вин']):9} | {int(row['Серия_лосс']):10} |\n")
        f.write("\n")
        
        f.write("## По часам для каждого дня\n\n")
        for date_val in sorted(df['Дата'].unique()):
            day_df = df[df['Дата'] == date_val]
            f.write(f"### {date_val}\n\n")
            f.write("| Час | Сделок | Винрейт | Прибыль    |\n")
            f.write("|-----|--------|---------|------------|\n")
            hour_stats = day_df.groupby('Час').agg(
                Сделок=('Результат', 'count'),
                Винрейт=('Результат', lambda x: (x=='Win').mean()*100),
                Прибыль=('Прибыль числом', 'sum')
            ).round(2)
            for hour, row in hour_stats.iterrows():
                profit_sign = "+" if row['Прибыль'] > 0 else ""
                f.write(f"| {hour:3} | {int(row['Сделок']):6} | {row['Винрейт']:.2f}%   | {profit_sign}{row['Прибыль']:.2f} |\n")
            f.write("\n")
    
    print(f"{Fore.GREEN}📄 Статистика сохранена: {filename}{Style.RESET_ALL}")


def print_all_statistics(df: pd.DataFrame, main_metrics: dict, day_stats: pd.DataFrame, asset_stats: pd.DataFrame):
    """Главная функция — выводит всю консольную статистику"""
    print_general_statistics(df, main_metrics)
    print_day_statistics(day_stats)
    print_asset_statistics(asset_stats)
    print_hour_statistics(df)