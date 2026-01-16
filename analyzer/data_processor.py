"""
Модуль загрузки и предобработки данных торговых сессий.

Обеспечивает выбор файлов, фильтрацию по типам активов (OTC), валютную конвертацию
и расчет динамики баланса.
"""

import sys
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from colorama import Fore, Style
from dateutil import parser

from analyzer.config import config

# Глобальный кэш курсов валют для минимизации сетевых запросов
# Формат: {(base, target): (rate, timestamp)}
_exchange_rate_cache: dict[tuple[str, str], tuple[float, datetime]] = {}
_CACHE_TTL = timedelta(minutes=5)


def select_files() -> list[Path]:
    """
    Организует интерактивный выбор XLSX-файлов из папки 'trades'.

    Returns:
        Список путей Path к выбранным файлам.

    Raises:
        SystemExit: Если папка пуста или файлы не найдены.

    """
    trades_folder = Path("trades")
    files = []

    if trades_folder.exists():
        # Сортируем по времени изменения (свежие сверху) и ограничиваем количество
        files = sorted(trades_folder.glob("*.xlsx"), key=lambda x: x.stat().st_mtime, reverse=True)[
            : config.getint("analysis_settings", "max_files_to_show")
        ]

    if not files:
        print(f"{Fore.RED}Нет xlsx файлов в папке trades!{Style.RESET_ALL}")
        sys.exit()

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
            selected_indices = _parse_selection(selection, files)
            break
        except ValueError as e:
            print(f"{Fore.RED}Ошибка: {e}.{Style.RESET_ALL}")

    return [files[i] for i in selected_indices]


def _parse_selection(selection: str, files: list[Path]) -> list[int]:
    """
    Парсит строку пользовательского ввода в список индексов файлов.

    Args:
        selection: Строка ввода (например, '1, 3').
        files: Доступный список файлов для проверки границ.

    Returns:
        Список валидных индексов.

    """
    selected_indices = []
    for x in selection.replace(" ", "").split(","):
        if not x:
            msg = "Некорректный формат выбора файлов"
            raise ValueError(msg)
        idx = int(x)
        if idx < 1 or idx > len(files):
            msg = f"Номер {idx} вне диапазона 1-{len(files)}"
            raise ValueError(msg)

        file_index = idx - 1
        if file_index in selected_indices:
            msg = f"Номер {idx} повторяется"
            raise ValueError(msg)
        selected_indices.append(file_index)
    return selected_indices


def choose_otc_filter() -> str:
    """Спрашивает у пользователя фильтр по OTC и возвращает выбор: '1', '2' или '3'."""
    while True:
        print("\nФильтр активов:")
        print("[1] Только OTC")
        print("[2] Только не-OTC")
        print("[3] Всё вместе")
        filter_choice = input("→ ").strip()
        if filter_choice in ["1", "2", "3"]:
            return filter_choice
        print(f"{Fore.RED}Ошибка: Введите 1, 2 или 3.{Style.RESET_ALL}")


def load_data(selected_files: list[Path]) -> pd.DataFrame:
    """Загружает и объединяет несколько Excel-файлов в единый DataFrame."""
    df_list = []
    for file in selected_files:
        temp_df = pd.read_excel(file)
        # Удаляем лишние пробелы в названиях колонок (защита от неправильного экспорта)
        temp_df.columns = temp_df.columns.str.strip()
        df_list.append(temp_df)

    return pd.concat(df_list, ignore_index=True)


def apply_otc_filter(df: pd.DataFrame, filter_choice: str) -> pd.DataFrame:
    """Применяет выбранный OTC-фильтр."""
    if filter_choice == "1":
        return df[df["Актив"].str.contains("OTC", na=False)]
    if filter_choice == "2":
        return df[~df["Актив"].str.contains("OTC", na=False)]
    return df


def get_current_balance() -> float:
    """Запрашивает текущий баланс у пользователя."""
    while True:
        user_input = input("\nВведите ваш текущий баланс: ").strip().replace(",", ".")
        try:
            balance = float(user_input)
            if balance > 0:
                return balance
            print(f"{Fore.RED}Ошибка: Число должно быть больше 0.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Ошибка: Введите корректное число.{Style.RESET_ALL}")


def preprocess_data(df: pd.DataFrame, current_balance: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Рассчитывает производные метрики и историю баланса.

    Args:
        df: Исходный DataFrame со сделками.
        current_balance: Текущее значение баланса для расчета истории назад.

    Returns:
        Кортеж (обработанный df, отсортированный df с историей баланса).

    """
    df["Время открытия"] = pd.to_datetime(df["Время открытия"])
    df["Дата"] = df["Время открытия"].dt.date  # type: ignore[reportAttributeAccessIssue]
    df["Час"] = df["Время открытия"].dt.hour  # type: ignore[reportAttributeAccessIssue]
    df["Результат"] = df["Прибыль"].apply(lambda x: "Win" if x > 0 else "Loss")
    df["Прибыль числом"] = df["Прибыль"].astype(float)

    # Удаляем символ 's' и преобразуем время экспирации в секунды
    df["Экспирация_сек"] = df["Экспирация"].str.slice(start=1).astype(int)

    # Расчёт баланса: идем от текущего значения назад, вычитая прибыль каждой сделки
    df_sorted = df.sort_values("Время открытия", ascending=False).reset_index(drop=True)
    df_sorted["Кумулятивная прибыль"] = df_sorted["Прибыль числом"].cumsum()
    df_sorted["Баланс"] = current_balance - df_sorted["Кумулятивная прибыль"]

    # Снова сортируем по времени для правильного отображения графиков
    df_sorted = df_sorted.sort_values("Время открытия").reset_index(drop=True)

    return df, df_sorted


def choose_expiration_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Простой фильтр по экспирации.

    Пользователь вводит секунды или нажимает Enter → всё.
    Возвращает отфильтрованный df.
    """
    while True:
        user_input = input("\nФильтр по экспирации (введите секунды, например 60, или Enter = всё): ").strip()

        if not user_input:
            print(f"{Fore.CYAN}→ Экспирация: все{Style.RESET_ALL}")
            return df

        if user_input.isdigit():
            seconds = int(user_input)
            if seconds > 0:
                filtered_df = df[df["Экспирация_сек"] == seconds]
                if not filtered_df.empty:
                    print(f"{Fore.CYAN}→ Экспирация: {seconds} сек ({len(filtered_df)} сделок){Style.RESET_ALL}")
                    return filtered_df
                print(f"{Fore.YELLOW}Предупреждение: Нет сделок {seconds} сек.{Style.RESET_ALL}")
                continue

        print(f"{Fore.RED}Ошибка: Введите положительное число.{Style.RESET_ALL}")


def get_exchange_rate(base_currency: str, target_currency: str) -> float | None:
    """
    Запрашивает курс обмена валют через внешний API с использованием кэша.

    Args:
        base_currency: Исходная валюта (например, 'USD').
        target_currency: Целевая валюта (например, 'RUB').

    Returns:
        Курс (float) или None, если запрос не удался.

    """
    key = (base_currency.upper(), target_currency.upper())

    # Проверка актуальности данных в кэше
    if key in _exchange_rate_cache:
        rate, timestamp = _exchange_rate_cache[key]
        if datetime.now(timezone.utc) - timestamp < _CACHE_TTL:
            return rate

    url = f"https://api.exchangerate-api.com/v4/latest/{base_currency.upper()}"
    with suppress(Exception):
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = data["rates"].get(target_currency.upper())
        if rate is not None:
            _exchange_rate_cache[key] = (rate, datetime.now(timezone.utc))
            return rate
    return None


def handle_currency_conversion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Приводит все финансовые показатели в DataFrame к единой валюте.

    Анализирует колонку 'Валюта', запрашивает подтверждение курса
    и пересчитывает прибыль и размер сделки.
    """
    currencies = df["Валюта"].dropna().unique()
    if len(currencies) <= 1:
        return df

    currencies = list(df["Валюта"].dropna().unique())
    if len(currencies) <= 1:
        return df

    print(f"\n{Fore.YELLOW}Обнаружены разные валюты: {', '.join(currencies)}{Style.RESET_ALL}")
    target_currency = _ask_target_currency(currencies)
    print(f"\n{Fore.CYAN}→ Основная валюта: {target_currency}{Style.RESET_ALL}")

    rates = {}
    for curr in currencies:
        if curr == target_currency:
            rates[curr] = 1.0
            continue
        rates[curr] = _get_rate_for_currency(target_currency, curr)

    print(f"\n{Fore.CYAN}Конвертируем прибыли в {target_currency}...{Style.RESET_ALL}")

    def convert_profit(row: pd.Series) -> float:
        return row["Прибыль числом"] / rates.get(row["Валюта"], 1.0)

    df["Прибыль числом"] = df.apply(convert_profit, axis=1)
    df["Размер сделки"] = df["Размер сделки"].astype(float)
    df["Размер сделки"] = df.apply(lambda r: r["Размер сделки"] / rates.get(r["Валюта"], 1.0), axis=1)
    df["Валюта"] = target_currency

    print(f"{Fore.GREEN}→ Данные в {target_currency}{Style.RESET_ALL}")
    return df


def _ask_target_currency(currencies: list) -> str:
    print("\nВыберите основную валюту:")
    for i, curr in enumerate(currencies, 1):
        print(f"[{i}] {curr}")
    while True:
        with suppress(ValueError):
            idx = int(input("→ ").strip()) - 1
            if 0 <= idx < len(currencies):
                return currencies[idx]
        print(f"{Fore.RED}Введите номер от 1 до {len(currencies)}{Style.RESET_ALL}")


def _get_rate_for_currency(target_currency: str, curr: str) -> float:
    print(f"\nОпределяем курс: 1 {target_currency} = ? {curr}")
    rate_auto = get_exchange_rate(target_currency, curr)

    if rate_auto is not None:
        print(f"Текущий курс: 1 {target_currency} = {rate_auto:.4f} {curr}")
        answer = input("Согласны? (Enter=да, иначе введите свой): ").strip()
        rate = rate_auto if answer == "" else None
    else:
        print(f"{Fore.YELLOW}Не удалось получить курс автоматически.{Style.RESET_ALL}")
        rate = None

    while rate is None:
        manual_input = input(f"Введите курс (1 {target_currency} = сколько {curr}): ").strip().replace(",", ".")
        with suppress(ValueError):
            val = float(manual_input)
            if val > 0:
                return val
        print(f"{Fore.RED}Введите положительное число{Style.RESET_ALL}")
    return rate


def choose_time_period_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Интерактивный фильтр по диапазону дат и времени.

    Args:
        df: DataFrame для фильтрации.

    Returns:
        Отфильтрованный DataFrame.

    """
    if df.empty:
        return df

    min_date = pd.to_datetime(df["Время открытия"].min())
    now_dt = datetime.now(timezone.utc).astimezone()

    while True:
        print("\nФильтр по периоду (опционально):")
        from_input = input("От (Enter=с начала): ").strip()
        to_input = input("До (Enter=до текущего): ").strip()

        try:
            start_dt = _parse_date(from_input, min_date, now_dt, is_start=True) if from_input else None
            end_dt = _parse_date(to_input, now_dt, now_dt, is_start=False) if to_input else None
        except (ValueError, TypeError):
            print(f"{Fore.RED}Ошибка распознавания даты. Попробуйте снова.{Style.RESET_ALL}")
            continue

        filtered_df = df.copy()
        if start_dt:
            filtered_df = filtered_df[filtered_df["Время открытия"] >= start_dt]
        if end_dt:
            filtered_df = filtered_df[filtered_df["Время открытия"] <= end_dt]

        if filtered_df.empty:
            print(f"{Fore.YELLOW}Сделок не осталось. Смените диапазон.{Style.RESET_ALL}")
            continue

        if _confirm_period(start_dt, end_dt):
            return filtered_df


def _parse_date(inp: str, ref_date: datetime, today: datetime, *, is_start: bool) -> datetime:
    parsed = parser.parse(inp, dayfirst=True, yearfirst=True)
    if parsed.date() == today and parsed.time() != datetime.min.time():
        parsed = parsed.replace(year=ref_date.year, month=ref_date.month, day=ref_date.day)
    return parsed if is_start else parsed.replace(hour=23, minute=59, second=59)


def _confirm_period(start: datetime | None, end: datetime | None) -> bool:
    f_str = start.strftime("%Y-%m-%d %H:%M") if start else "с начала"
    t_str = end.strftime("%Y-%m-%d %H:%M") if end else "до текущего времени"
    print(f"\n{Fore.CYAN}→ Период: с {f_str} по {t_str}{Style.RESET_ALL}")
    return input("Верно? (Enter=да, любая клавиша=нет): ").strip() == ""
