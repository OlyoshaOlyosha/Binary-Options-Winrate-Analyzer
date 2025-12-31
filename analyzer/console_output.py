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


def print_all_statistics(df: pd.DataFrame, main_metrics: dict, day_stats: pd.DataFrame, asset_stats: pd.DataFrame):
    """Главная функция — выводит всю консольную статистику"""
    print_general_statistics(df, main_metrics)
    print_day_statistics(day_stats)
    print_asset_statistics(asset_stats)
    print_hour_statistics(df)