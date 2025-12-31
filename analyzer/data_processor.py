import pandas as pd
from pathlib import Path
from colorama import Fore, Style

from analyzer.config import config

def select_files() -> list[Path]:
    """Ищет XLSX-файлы в папке trades и позволяет пользователю выбрать нужные"""
    trades_folder = Path('trades')
    files = []

    if trades_folder.exists():
        files = sorted(
            [f for f in trades_folder.glob('*.xlsx')],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:config.getint('analysis_settings', 'max_files_to_show')]

    if not files:
        print(f"{Fore.RED}Нет xlsx файлов в папке trades!{Style.RESET_ALL}")
        exit()

    print(f"Найдено файлов: {len(files)} в папке trades")
    print("\nДоступные файлы (последние несколько):")
    for i, f in enumerate(files, 1):
        print(f"[{i}] {f.name}")

    while True:
        selection = input("\nВыберите файлы (например: 1 или 1,2,3): ").strip()
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
            error_msg = str(e) if any(msg in str(e) for msg in ["вне диапазона", "повторяется", "Некорректный"]) \
                else f"Введите числа от 1 до {len(files)}, разделённые запятой"
            print(f"{Fore.RED}Ошибка: {error_msg}.{Style.RESET_ALL}")

    return [files[i] for i in selected_indices]

def choose_otc_filter() -> str:
    """Спрашивает у пользователя фильтр по OTC и возвращает выбор: '1', '2' или '3'"""
    while True:
        print("\nФильтр активов:")
        print("[1] Только OTC")
        print("[2] Только не-OTC")
        print("[3] Всё вместе")
        filter_choice = input("→ ").strip()
        if filter_choice in ['1', '2', '3']:
            return filter_choice
        else:
            print(f"{Fore.RED}Ошибка: Введите 1, 2 или 3.{Style.RESET_ALL}")

def load_data(selected_files: list[Path]) -> pd.DataFrame:
    """Загружает выбранные XLSX-файлы и объединяет в один DataFrame"""
    df_list = []
    for file in selected_files:
        temp_df = pd.read_excel(file)
        temp_df.columns = temp_df.columns.str.strip()
        df_list.append(temp_df)

    df = pd.concat(df_list, ignore_index=True)
    return df

def apply_otc_filter(df: pd.DataFrame, filter_choice: str) -> pd.DataFrame:
    """Применяет выбранный OTC-фильтр"""
    if filter_choice == '1':
        return df[df['Актив'].str.contains('OTC', na=False)]
    elif filter_choice == '2':
        return df[~df['Актив'].str.contains('OTC', na=False)]
    else:
        return df

def get_current_balance() -> float:
    """Запрашивает текущий баланс у пользователя"""
    while True:
        try:
            balance = float(input("\nВведите ваш текущий баланс: ").strip().replace(',', '.'))
            if balance <= 0:
                raise ValueError("Баланс должен быть положительным")
            return balance
        except ValueError:
            print(f"{Fore.RED}Ошибка: Введите число больше 0.{Style.RESET_ALL}")

def preprocess_data(df: pd.DataFrame, current_balance: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Добавляет необходимые колонки и рассчитывает прогресс баланса
    Возвращает: (df с новыми колонками, df_sorted для графиков баланса)
    """
    df['Время открытия'] = pd.to_datetime(df['Время открытия'])
    df['Дата'] = df['Время открытия'].dt.date
    df['Час'] = df['Время открытия'].dt.hour
    df['Результат'] = df['Прибыль'].apply(lambda x: 'Win' if x > 0 else 'Loss')
    df['Прибыль числом'] = df['Прибыль'].astype(float)
    df['Экспирация_сек'] = df['Экспирация'].str.slice(start=1).astype(int)

    # Расчёт прогресса баланса от текущего значения назад
    df_sorted = df.sort_values('Время открытия', ascending=False).reset_index(drop=True)
    df_sorted['Кумулятивная прибыль'] = df_sorted['Прибыль числом'].cumsum()
    df_sorted['Баланс'] = current_balance - df_sorted['Кумулятивная прибыль']
    df_sorted = df_sorted.sort_values('Время открытия').reset_index(drop=True)

    return df, df_sorted

def choose_expiration_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Простой фильтр по экспирации.
    Пользователь вводит секунды или нажимает Enter → всё.
    Возвращает отфильтрованный df.
    """
    while True:
        user_input = input("\nФильтр по экспирации (введите секунды, например 60, или Enter = всё): ").strip()
        
        if user_input == "":  # Enter = всё
            print(f"{Fore.CYAN}→ Экспирация: все{Style.RESET_ALL}")
            return df
        
        try:
            seconds = int(user_input)
            if seconds <= 0:
                raise ValueError
            filtered_df = df[df['Экспирация_сек'] == seconds]
            if len(filtered_df) == 0:
                print(f"{Fore.YELLOW}Предупреждение: Нет сделок с экспирацией {seconds} сек. Попробуйте снова.{Style.RESET_ALL}")
                continue
            print(f"{Fore.CYAN}→ Экспирация: {seconds} секунд ({len(filtered_df)} сделок){Style.RESET_ALL}")
            return filtered_df
        except ValueError:
            print(f"{Fore.RED}Ошибка: Введите положительное число секунд или просто нажмите Enter.{Style.RESET_ALL}")