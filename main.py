import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import configparser
import warnings
from colorama import Fore, Style, init
warnings.filterwarnings("ignore")

# Инициализация colorama для Windows
init(autoreset=True)

__version__ = "1.0.0"
__app_name__ = "Binary Options Winrate Analyzer"

print(f"{Fore.CYAN}{__app_name__}{Style.RESET_ALL} {Fore.YELLOW}v{__version__}{Style.RESET_ALL}")

# Функции для цветного вывода
def color_profit(value):
    if value > 0:
        return f"{Fore.GREEN}{value:+.2f}{Style.RESET_ALL}"
    elif value < 0:
        return f"{Fore.RED}{value:.2f}{Style.RESET_ALL}"
    else:
        return f"{Fore.YELLOW}{value:.2f}{Style.RESET_ALL}"

def color_winrate(value):
    if value >= 50:
        return f"{Fore.GREEN}{value:.2f}%{Style.RESET_ALL}"
    else:
        return f"{Fore.RED}{value:.2f}%{Style.RESET_ALL}"

# ====================== ЗАГРУЗКА КОНФИГУРАЦИИ ======================
CONFIG_FILE = 'analyzer_config.ini'

config = configparser.ConfigParser()
try:
    config.read(CONFIG_FILE, encoding='utf-8')
    if not config.sections():
        raise FileNotFoundError
except:
    print(f"Файл конфигурации {CONFIG_FILE} не найден. Используются настройки по умолчанию.")
    config['graph_settings'] = {
        'figure_width': '14', 'figure_height': '9', 'background_color': '#1e1e1e',
        'plot_background': '#2b2b2b', 'grid_alpha': '0.5', 'font_size': '11'
    }
    config['colors'] = {
        'win': '#00ff88', 'loss': '#ff4444', 'line': '#00d4ff',
        'threshold': '#ffaa00', 'week_progress': '#ff8800'
    }
    config['analysis_settings'] = {
        'rolling_window_percent': '10', 'top_assets_count': '10', 'max_files_to_show': '5'
    }

# Настройка стиля графиков
plt.style.use('dark_background')
plt.rcParams['figure.figsize'] = (config.getint('graph_settings', 'figure_width'), config.getint('graph_settings', 'figure_height'))
plt.rcParams['figure.facecolor'] = config.get('graph_settings', 'background_color')
plt.rcParams['axes.facecolor'] = config.get('graph_settings', 'plot_background')
plt.rcParams['axes.edgecolor'] = '#555555'
plt.rcParams['axes.linewidth'] = 1.5
plt.rcParams['grid.alpha'] = config.getfloat('graph_settings', 'grid_alpha')
plt.rcParams['grid.color'] = '#444444'
plt.rcParams['text.color'] = 'white'
plt.rcParams['axes.labelcolor'] = 'white'
plt.rcParams['xtick.color'] = 'white'
plt.rcParams['ytick.color'] = 'white'
plt.rcParams['font.size'] = config.getint('graph_settings', 'font_size')

# ====================== ВЫБОР ФАЙЛОВ ======================
# Ищем файлы в папке trades и в текущей директории
trades_folder = Path('trades')
current_folder = Path('.')

files_trades = []
files_current = []

if trades_folder.exists():
    files_trades = sorted([f for f in trades_folder.glob('*.xlsx')], key=lambda x: x.stat().st_mtime, reverse=True)[:config.getint('analysis_settings', 'max_files_to_show')]

files_current = sorted([f for f in current_folder.glob('*.xlsx') if f.parent == current_folder], key=lambda x: x.stat().st_mtime, reverse=True)[:config.getint('analysis_settings', 'max_files_to_show')]

files = files_trades + files_current
files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:config.getint('analysis_settings', 'max_files_to_show')]

if not files:
    print("Нет xlsx файлов ни в папке trades, ни в текущей директории!")
    exit()

print(f"Найдено файлов: {len(files_trades)} в папке trades, {len(files_current)} в текущей директории")
print("\nДоступные файлы (последние 5):")
for i, f in enumerate(files, 1):
    location = "[trades]" if f in files_trades else "[текущая]"
    print(f"[{i}] {location} {f.name}")

while True:
    selection = input("\nВыбери файлы (например: 1 или 1,2,3): ").strip()
    if not selection:
        print(f"{Fore.RED}Ошибка: Ввод не может быть пустым.{Style.RESET_ALL}")
        continue
    
    try:
        selected_indices = []
        for x in selection.replace(" ", "").split(','):
            if not x:
                raise ValueError("Некорректный формат")
            idx = int(x)
            if idx < 1 or idx > len(files):
                raise ValueError(f"Номер {idx} вне диапазона 1-{len(files)}")
            file_index = idx - 1
            if file_index in selected_indices:
                raise ValueError(f"Номер {idx} повторяется")
            selected_indices.append(file_index)
        break
    except ValueError as e:
        error_msg = str(e) if "вне диапазона" in str(e) or "повторяется" in str(e) or "Некорректный" in str(e) else f"Введите числа от 1 до {len(files)}, разделённые запятой"
        print(f"{Fore.RED}Ошибка: {error_msg}.{Style.RESET_ALL}")

selected_files = [files[i] for i in selected_indices]

while True:
    print("\nФильтр активов:")
    print("[1] Только OTC")
    print("[2] Только не-OTC")
    print("[3] Всё вместе")
    filter_choice = input("→ ").strip()
    if filter_choice in ['1', '2', '3']:
        break
    else:
        print(f"{Fore.RED}Ошибка: Введите 1, 2 или 3.{Style.RESET_ALL}")

# ====================== ЗАГРУЗКА ДАННЫХ ======================
df_list = []
for file in selected_files:
    temp_df = pd.read_excel(file)
    temp_df.columns = temp_df.columns.str.strip()
    df_list.append(temp_df)

df = pd.concat(df_list, ignore_index=True)

# Фильтр OTC
if filter_choice == '1':
    df = df[df['Актив'].str.contains('OTC', na=False)]
elif filter_choice == '2':
    df = df[~df['Актив'].str.contains('OTC', na=False)]

print(f"\nЗагружено сделок: {len(df)}")

# ====================== ПРЕДОБРАБОТКА ======================
df['Время открытия'] = pd.to_datetime(df['Время открытия'])
df['Дата'] = df['Время открытия'].dt.date
df['Час'] = df['Время открытия'].dt.hour
df['Результат'] = df['Прибыль'].apply(lambda x: 'Win' if x > 0 else 'Loss')
df['Прибыль числом'] = df['Прибыль'].astype(float)

# ====================== ОСНОВНЫЕ МЕТРИКИ ======================
total_trades = len(df)
wins = len(df[df['Результат'] == 'Win'])
winrate = wins / total_trades * 100
profit_factor = df[df['Прибыль числом'] > 0]['Прибыль числом'].sum() / abs(df[df['Прибыль числом'] < 0]['Прибыль числом'].sum()) if len(df[df['Прибыль числом'] < 0]) > 0 else float('inf')
avg_win = df[df['Прибыль числом'] > 0]['Прибыль числом'].mean()
avg_loss = abs(df[df['Прибыль числом'] < 0]['Прибыль числом'].mean())
total_profit = df['Прибыль числом'].sum()

print("\n" + "="*70)
print(" "*25 + "ОБЩАЯ СТАТИСТИКА")
print("="*70)
print(f"Всего сделок:       {total_trades}")
print(f"Винрейт:            {color_winrate(winrate)}")
print(f"Общая прибыль:      {color_profit(total_profit)} {df['Валюта'].iloc[0]}")
print(f"Профит-фактор:      {profit_factor:.2f}")
print(f"Средний вин:        {Fore.GREEN}+{avg_win:.2f}{Style.RESET_ALL}")
print(f"Средний лосс:       {Fore.RED}-{avg_loss:.2f}{Style.RESET_ALL}")
print(f"Макс. серия вин:    {Fore.GREEN}{max((df['Результат'] == 'Win').astype(int).groupby((df['Результат'] != 'Win').cumsum()).sum())}{Style.RESET_ALL}")
print(f"Макс. серия лоссов: {Fore.RED}{max((df['Результат'] == 'Loss').astype(int).groupby((df['Результат'] != 'Loss').cumsum()).sum())}{Style.RESET_ALL}")

# ====================== ВИНРЕЙТ ПО ДНЯМ ======================
print("\n" + "="*70)
print(" "*25 + "ВИНРЕЙТ ПО ДНЯМ")
print("="*70)
day_stats = df.groupby('Дата').agg(
    Сделок=('Результат', 'count'),
    Винрейт=('Результат', lambda x: (x=='Win').mean()*100),
    Прибыль=('Прибыль числом', 'sum')
).round(2)

# Цветной вывод таблицы
for date, row in day_stats.iterrows():
    wr_colored = color_winrate(row['Винрейт'])
    profit_colored = color_profit(row['Прибыль'])
    print(f"{date}  |  Сделок: {int(row['Сделок'])}  |  Винрейт: {wr_colored}  |  Прибыль: {profit_colored}")

# ====================== ПО АКТИВАМ ======================
print("\n" + "="*115)
print(" "*50 + "ПО АКТИВАМ")
print("="*115)

# Серии для каждого актива
def calc_streaks(group):
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

asset_stats = df.groupby('Актив').apply(calc_streaks).sort_values('Винрейт', ascending=False)
asset_stats['Сделок'] = asset_stats['Сделок'].astype(int)
asset_stats['Серия_вин'] = asset_stats['Серия_вин'].astype(int)
asset_stats['Серия_лосс'] = asset_stats['Серия_лосс'].astype(int)
asset_stats['Винрейт'] = asset_stats['Винрейт'].round(2)
asset_stats['Прибыль'] = asset_stats['Прибыль'].round(2)

# Цветной вывод таблицы активов
for asset, row in asset_stats.iterrows():
    wr_colored = color_winrate(row['Винрейт'])
    profit_colored = color_profit(row['Прибыль'])
    print(f"{asset:20} | Сделок: {int(row['Сделок']):3} | Винрейт: {wr_colored:20} | Прибыль: {profit_colored:20} | Серия_вин: {Fore.GREEN}{int(row['Серия_вин'])}{Style.RESET_ALL} | Серия_лосс: {Fore.RED}{int(row['Серия_лосс'])}{Style.RESET_ALL}")

# ====================== ПО ЧАСАМ ДЛЯ КАЖДОГО ДНЯ ======================
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
    
    # Цветной вывод по часам
    for hour, row in hour_stats.iterrows():
        wr_colored = color_winrate(row['Винрейт'])
        profit_colored = color_profit(row['Прибыль'])
        print(f"  Час {hour:2}  |  Сделок: {int(row['Сделок']):2}  |  Винрейт: {wr_colored:20}  |  Прибыль: {profit_colored}")

# ====================== ПЕРЕХОД К ГРАФИКАМ ======================
print("\n" + "="*60)
print(f"{Fore.YELLOW}📊 ОТКРЫВАЮ ОКНО С ГРАФИКАМИ...{Style.RESET_ALL}")
print(f"{Fore.CYAN}Дополнительная визуализация данных в графическом виде.{Style.RESET_ALL}")
print(f"{Fore.CYAN}Закрой окно с графиками, чтобы завершить программу.{Style.RESET_ALL}")
print("="*60 + "\n")

# ====================== ГРАФИКИ ======================
df = df.sort_values('Время открытия').reset_index(drop=True)
fig = plt.figure()

# Цвета из конфига
COLOR_WIN = config.get('colors', 'win')
COLOR_LOSS = config.get('colors', 'loss')
COLOR_LINE = config.get('colors', 'line')
COLOR_THRESHOLD = config.get('colors', 'threshold')

# 1. Винрейт по дням (линия прогресса)
plt.subplot(2, 3, 1)
plt.plot(day_stats.index, day_stats['Винрейт'], marker='o', color=COLOR_WIN, linewidth=3, markersize=10, markeredgecolor='white', markeredgewidth=1.5)
plt.axhline(y=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7, label='50% порог')
plt.title('Винрейт по дням', fontsize=15, fontweight='bold', pad=15)
plt.ylabel('Винрейт, %', fontsize=12)
plt.xlabel('Дата', fontsize=12)
plt.xticks(rotation=45)
plt.grid(True, alpha=0.5)
plt.legend(fontsize=10)
plt.ylim(0, 100)

# 2. Скользящий винрейт (по N% сделок)
plt.subplot(2, 3, 2)
df['Win_binary'] = (df['Результат'] == 'Win').astype(int)
rolling_window = max(int(len(df) * config.getint('analysis_settings', 'rolling_window_percent') / 100), 1)
df['Rolling_WR'] = df['Win_binary'].rolling(window=rolling_window, min_periods=1).mean() * 100
plt.plot(range(len(df)), df['Rolling_WR'], color=COLOR_LINE, linewidth=3)
plt.axhline(y=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
plt.title(f'Скользящий винрейт (окно {config.getint("analysis_settings", "rolling_window_percent")}% = {rolling_window} сделок)', fontsize=15, fontweight='bold', pad=15)
plt.ylabel('Винрейт, %', fontsize=12)
plt.xlabel('Номер сделки', fontsize=12)
plt.grid(True, alpha=0.5)
plt.ylim(0, 100)

# 3. Топ-N активов по винрейту
plt.subplot(2, 3, 3)
top_assets = asset_stats.head(config.getint('analysis_settings', 'top_assets_count'))[::-1]
colors = [COLOR_WIN if x >= 50 else COLOR_LOSS for x in top_assets['Винрейт']]
plt.barh(range(len(top_assets)), top_assets['Винрейт'], color=colors, edgecolor='white', linewidth=1.5)
plt.yticks(range(len(top_assets)), top_assets.index, fontsize=10)
plt.axvline(x=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
plt.title(f'Топ-{config.getint("analysis_settings", "top_assets_count")} активов по винрейту', fontsize=15, fontweight='bold', pad=15)
plt.xlabel('Винрейт, %', fontsize=12)
plt.xlim(0, 100)
plt.grid(True, alpha=0.5, axis='x')

# 4. Распределение Win/Loss
plt.subplot(2, 3, 4)
win_count = len(df[df['Результат'] == 'Win'])
loss_count = len(df[df['Результат'] == 'Loss'])
wedges, texts, autotexts = plt.pie([win_count, loss_count], labels=['Win', 'Loss'], autopct='%1.1f%%', 
        colors=[COLOR_WIN, COLOR_LOSS], startangle=90, textprops={'fontsize': 13, 'weight': 'bold'},
        wedgeprops={'edgecolor': 'white', 'linewidth': 2})
plt.title(f'Распределение Win/Loss\n({win_count}W / {loss_count}L)', fontsize=15, fontweight='bold', pad=15)

# 5. Винрейт по часам дня
plt.subplot(2, 3, 5)
hour_all_stats = df.groupby('Час').agg(
    Винрейт=('Результат', lambda x: (x=='Win').mean()*100)
).round(2)
colors_hour = [COLOR_WIN if x >= 50 else COLOR_LOSS for x in hour_all_stats['Винрейт']]
plt.bar(hour_all_stats.index, hour_all_stats['Винрейт'], color=colors_hour, edgecolor='white', linewidth=1.5)
plt.axhline(y=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
plt.title('Винрейт по часам дня', fontsize=15, fontweight='bold', pad=15)
plt.xlabel('Час', fontsize=12)
plt.ylabel('Винрейт, %', fontsize=12)
plt.ylim(0, 100)
plt.grid(True, alpha=0.5, axis='y')

# 6. Прогресс по неделям (если несколько недель)
plt.subplot(2, 3, 6)
df['Неделя'] = pd.to_datetime(df['Дата']).dt.isocalendar().week
week_stats = df.groupby('Неделя').agg(
    Винрейт=('Результат', lambda x: (x=='Win').mean()*100),
    Сделок=('Результат', 'count')
).round(2)
if len(week_stats) > 1:
    plt.plot(week_stats.index, week_stats['Винрейт'], marker='o', color=config.get('colors', 'week_progress'), linewidth=4, markersize=12, markeredgecolor='white', markeredgewidth=2)
    plt.axhline(y=50, color=COLOR_THRESHOLD, linestyle='--', linewidth=2, alpha=0.7)
    for i, (week, row) in enumerate(week_stats.iterrows()):
        plt.text(week, row['Винрейт'] + 3, f"{row['Винрейт']:.1f}%\n({int(row['Сделок'])})", 
                ha='center', fontsize=11, color='white', weight='bold')
    plt.title('Прогресс по неделям', fontsize=15, fontweight='bold', pad=15)
    plt.ylabel('Винрейт, %', fontsize=12)
    plt.xlabel('Неделя', fontsize=12)
    plt.ylim(0, 100)
    plt.grid(True, alpha=0.5)
else:
    plt.text(0.5, 0.5, 'Недостаточно данных\n(нужно >1 недели)', 
            ha='center', va='center', fontsize=14, color='#888888', weight='bold')
    plt.title('Прогресс по неделям', fontsize=15, fontweight='bold', pad=15)
    plt.xlim(0, 1)
    plt.ylim(0, 1)

plt.tight_layout(pad=2.0)
plt.show()

print("\n" + "="*60)
input("Анализ завершён! Нажмите Enter для завершения программы...")
print("="*60)