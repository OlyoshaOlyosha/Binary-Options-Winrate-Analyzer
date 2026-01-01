import requests
from datetime import datetime, timedelta
from dateutil import parser
import pandas as pd
from pathlib import Path
from colorama import Fore, Style

from analyzer.config import config

# Кэш курсов: {(base, target): (rate, timestamp)}
_exchange_rate_cache = {}
_CACHE_TTL = timedelta(minutes=5)  # 5 минут

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

def get_exchange_rate(base_currency: str, target_currency: str) -> float | None:
    """
    Получает курс: сколько target_currency за 1 base_currency
    Использует кэш (5 минут)
    """
    key = (base_currency.upper(), target_currency.upper())
    
    # Проверяем кэш
    if key in _exchange_rate_cache:
        rate, timestamp = _exchange_rate_cache[key]
        if datetime.now() - timestamp < _CACHE_TTL:
            return rate

    url = f"https://api.exchangerate-api.com/v4/latest/{base_currency.upper()}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = data['rates'].get(target_currency.upper())
        if rate is not None:
            _exchange_rate_cache[key] = (rate, datetime.now())
            return rate
    except Exception:
        pass
    return None


def handle_currency_conversion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Обрабатывает разные валюты: предлагает выбрать основную и переводит всё в неё.
    Курс: 1 основная = N вторичная
    """
    currencies = df['Валюта'].dropna().unique()
    if len(currencies) <= 1:
        return df

    print(f"\n{Fore.YELLOW}Обнаружены разные валюты: {', '.join(currencies)}{Style.RESET_ALL}")

    # Выбор основной валюты
    print("\nВыберите основную валюту (всё будет переведено в неё):")
    for i, curr in enumerate(currencies, 1):
        print(f"[{i}] {curr}")
    
    while True:
        try:
            idx = int(input("→ ").strip()) - 1
            if 0 <= idx < len(currencies):
                target_currency = currencies[idx]
                break
        except ValueError:
            pass
        print(f"{Fore.RED}Введите номер от 1 до {len(currencies)}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}→ Основная валюта: {target_currency}{Style.RESET_ALL}")

    # Словарь курсов
    rates = {}

    for curr in currencies:
        if curr == target_currency:
            rates[curr] = 1.0
            continue

        print(f"\nОпределяем курс: 1 {target_currency} = ? {curr}")

        # Пытаемся получить автоматически (сколько curr за 1 target)
        rate_auto = get_exchange_rate(target_currency, curr)

        if rate_auto is not None:
            print(f"Текущий курс: 1 {target_currency} = {rate_auto:.4f} {curr}")
            answer = input("Согласны? (Enter=да, иначе введите свой): ").strip()
            if answer == "":
                rate = rate_auto
            else:
                rate = None
        else:
            print(f"{Fore.YELLOW}Не удалось получить курс автоматически.{Style.RESET_ALL}")
            rate = None

        # Ручной ввод
        while rate is None:
            manual_input = input(f"Введите курс (1 {target_currency} = сколько {curr}): ").strip().replace(',', '.')
            try:
                rate = float(manual_input)
                if rate <= 0:
                    raise ValueError
                print(f"→ Принято: 1 {target_currency} = {rate:.4f} {curr}")
            except ValueError:
                print(f"{Fore.RED}Введите положительное число{Style.RESET_ALL}")
                rate = None

        rates[curr] = rate

    # Конвертация
    print(f"\n{Fore.CYAN}Конвертируем прибыли в {target_currency}...{Style.RESET_ALL}")

    def convert_profit(row):
        original_curr = row['Валюта']
        profit = row['Прибыль числом']
        rate = rates.get(original_curr, 1.0)
        return profit / rate

    df['Прибыль числом'] = df.apply(convert_profit, axis=1)

    df['Размер сделки'] = df['Размер сделки'].astype(float)
    df['Размер сделки'] = df.apply(lambda row: row['Размер сделки'] / rates.get(row['Валюта'], 1.0), axis=1)

    # Обновляем валюту
    df['Валюта'] = target_currency

    print(f"{Fore.GREEN}→ Все данные переведены в {target_currency}{Style.RESET_ALL}")
    return df

def choose_time_period_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Фильтр по временному периоду с удобным вводом и подтверждением.
    Enter = без ограничения.
    Возвращает отфильтрованный df.
    """
    if len(df) == 0:
        return df

    # Минимальная и максимальная даты в данных
    min_date = df['Время открытия'].min()
    max_date = df['Время открытия'].max()

    while True:
        print("\nФильтр по периоду (опционально):")
        from_input = input("От (ГГГГ.ММ.ДД ЧЧ:ММ, или только дата/время, Enter=с начала): ").strip()
        to_input = input("До (аналогично, Enter=до текущего времени): ").strip()

        # Парсим ввод
        start_dt = None
        end_dt = None

        if from_input:
            try:
                parsed = parser.parse(from_input, dayfirst=True, yearfirst=True)
                # Если ввели только время — применяем к минимальной дате
                if parsed.date() == datetime.today().date() and parsed.time() != datetime.min.time():
                    parsed = parsed.replace(year=min_date.year, month=min_date.month, day=min_date.day)
                start_dt = parsed
            except Exception:
                print(f"{Fore.RED}Не удалось распознать 'От': {from_input}. Попробуйте снова.{Style.RESET_ALL}")
                continue

        if to_input:
            try:
                parsed = parser.parse(to_input, dayfirst=True, yearfirst=True)
                # Если только время — применяем к максимальной дате + конец дня
                if parsed.date() == datetime.today().date() and parsed.time() != datetime.min.time():
                    parsed = parsed.replace(year=max_date.year, month=max_date.month, day=max_date.day)
                # До конца дня
                end_dt = parsed.replace(hour=23, minute=59, second=59)
            except Exception:
                print(f"{Fore.RED}Не удалось распознать 'До': {to_input}. Попробуйте снова.{Style.RESET_ALL}")
                continue

        # Применяем фильтр
        filtered_df = df.copy()
        if start_dt:
            filtered_df = filtered_df[filtered_df['Время открытия'] >= start_dt]
        if end_dt:
            filtered_df = filtered_df[filtered_df['Время открытия'] <= end_dt]

        if len(filtered_df) == 0:
            print(f"{Fore.YELLOW}После фильтра по периоду не осталось сделок. Попробуйте другой диапазон.{Style.RESET_ALL}")
            continue

        # Формируем красивый вывод периода
        from_str = start_dt.strftime("%Y-%m-%d %H:%M") if start_dt else "с начала"
        to_str = end_dt.strftime("%Y-%m-%d %H:%M") if end_dt else "до текущего времени"

        print(f"\n{Fore.CYAN}→ Анализ за период: с {from_str} по {to_str}{Style.RESET_ALL}")
        confirm = input("Верно? (Enter=да, иначе введите новый диапазон в формате От;До): ").strip()

        if confirm == "":
            return filtered_df

        # Если не да — пытаемся распознать как "От;До"
        if ';' in confirm:
            parts = confirm.split(';', 1)
            from_input = parts[0].strip()
            to_input = parts[1].strip() if len(parts) > 1 else ""
        else:
            continue