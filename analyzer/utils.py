import pandas as pd
from colorama import Fore, Style

def color_profit(value: float) -> str:
    """Возвращает значение прибыли с цветом: зелёный +, красный -, жёлтый 0"""
    if value > 0:
        return f"{Fore.GREEN}{value:+.2f}{Style.RESET_ALL}"
    elif value < 0:
        return f"{Fore.RED}{value:.2f}{Style.RESET_ALL}"
    else:
        return f"{Fore.YELLOW}{value:.2f}{Style.RESET_ALL}"

def color_winrate(value: float) -> str:
    """Возвращает винрейт с цветом: зелёный ≥50%, красный <50%"""
    if value >= 50:
        return f"{Fore.GREEN}{value:.2f}%{Style.RESET_ALL}"
    else:
        return f"{Fore.RED}{value:.2f}%{Style.RESET_ALL}"

def calculate_max_streak(df, result_type: str):
    """
    Вычисляет максимальную серию побед или поражений
    result_type: 'Win' или 'Loss'
    """
    is_target = (df['Результат'] == result_type).astype(int)
    changes = (df['Результат'] != df['Результат'].shift()).cumsum()
    streaks = is_target.groupby(changes).sum()
    return int(streaks.max()) if len(streaks) > 0 else 0

def calculate_asset_streaks(group):
    """
    Возвращает статистику по активу: сделки, винрейт, прибыль и максимальные серии
    Используется в groupby.apply()
    """
    group = group.sort_values('Время открытия').reset_index(drop=True)
    group['Группа'] = (group['Результат'] != group['Результат'].shift()).cumsum()
    streaks = group.groupby(['Группа', 'Результат']).size()

    win_streaks = streaks[streaks.index.get_level_values(1) == 'Win']
    loss_streaks = streaks[streaks.index.get_level_values(1) == 'Loss']

    return pd.Series({
        'Сделок': int(len(group)),
        'Винрейт': (group['Результат'] == 'Win').mean() * 100,
        'Прибыль': group['Прибыль числом'].sum(),
        'Серия_вин': int(win_streaks.max()) if len(win_streaks) > 0 else 0,
        'Серия_лосс': int(loss_streaks.max()) if len(loss_streaks) > 0 else 0
    })