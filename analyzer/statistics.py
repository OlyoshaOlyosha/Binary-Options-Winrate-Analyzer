import pandas as pd

from analyzer.utils import calculate_asset_streaks

def calculate_main_metrics(df: pd.DataFrame) -> dict:
    """
    Рассчитывает основные общие метрики
    Возвращает словарь с метриками
    """
    total_trades = len(df)
    wins = len(df[df['Результат'] == 'Win'])
    winrate = wins / total_trades * 100 if total_trades > 0 else 0

    profit_positive = df[df['Прибыль числом'] > 0]['Прибыль числом'].sum()
    loss_negative = abs(df[df['Прибыль числом'] < 0]['Прибыль числом'].sum())
    profit_factor = profit_positive / loss_negative if loss_negative > 0 else float('inf')

    avg_win = df[df['Прибыль числом'] > 0]['Прибыль числом'].mean() if len(df[df['Прибыль числом'] > 0]) > 0 else 0
    avg_loss = abs(df[df['Прибыль числом'] < 0]['Прибыль числом'].mean()) if len(df[df['Прибыль числом'] < 0]) > 0 else 0
    total_profit = df['Прибыль числом'].sum()

    currency = df['Валюта'].iloc[0] if len(df) > 0 else 'USD'

    return {
        'total_trades': total_trades,
        'winrate': winrate,
        'total_profit': total_profit,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'currency': currency
    }

def calculate_day_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Винрейт и прибыль по дням"""
    return df.groupby('Дата').agg(
        Сделок=('Результат', 'count'),
        Винрейт=('Результат', lambda x: (x == 'Win').mean() * 100),
        Прибыль=('Прибыль числом', 'sum')
    ).round(2)

def calculate_asset_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Статистика по активам с сериями"""
    asset_stats = df.groupby('Актив').apply(calculate_asset_streaks)
    
    asset_stats['Сделок'] = asset_stats['Сделок'].astype(int)
    asset_stats['Серия_вин'] = asset_stats['Серия_вин'].astype(int)
    asset_stats['Серия_лосс'] = asset_stats['Серия_лосс'].astype(int)
    asset_stats['Винрейт'] = asset_stats['Винрейт'].round(2)
    asset_stats['Прибыль'] = asset_stats['Прибыль'].round(2)
    
    return asset_stats.sort_values('Винрейт', ascending=False)