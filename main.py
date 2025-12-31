"""
Binary Options Winrate Analyzer
Мощный инструмент анализа сделок на Pocket Option.
"""

from colorama import Fore, Style, init

from analyzer.config import __app_name__, __version__
from analyzer.console_output import print_all_statistics
from analyzer.data_processor import (
    apply_otc_filter,
    choose_otc_filter,
    get_current_balance,
    load_data,
    preprocess_data,
    select_files,
    choose_expiration_filter,
)
from analyzer.plots import show_all_charts
from analyzer.statistics import (
    calculate_asset_stats,
    calculate_day_stats,
    calculate_main_metrics,
)

# Инициализация colorama (для цветного вывода в Windows)
init(autoreset=True)

def main() -> None:
    """Основная функция запуска анализа."""
    print(f"{Fore.CYAN}{__app_name__}{Style.RESET_ALL} {Fore.YELLOW}v{__version__}{Style.RESET_ALL}")

    # Загрузка и подготовка данных
    selected_files = select_files()
    filter_choice = choose_otc_filter()

    df = load_data(selected_files)
    df = apply_otc_filter(df, filter_choice)

    current_balance = get_current_balance()
    df, df_sorted = preprocess_data(df, current_balance)
    
    while True:
        df_filtered = choose_expiration_filter(df)
        
        if len(df_filtered) > 0:
            df = df_filtered
            break
        else:
            print(f"{Fore.YELLOW}После фильтра по экспирации не осталось сделок. Попробуйте другой вариант.{Style.RESET_ALL}")

    # Обновляем df_sorted под отфильтрованные данные
    df_sorted = df.sort_values('Время открытия', ascending=False).reset_index(drop=True)
    df_sorted['Кумулятивная прибыль'] = df_sorted['Прибыль числом'].cumsum()
    df_sorted['Баланс'] = current_balance - df_sorted['Кумулятивная прибыль']
    df_sorted = df_sorted.sort_values('Время открытия').reset_index(drop=True)

    print(f"\nИтого после всех фильтров загружено сделок: {len(df)}")

    # Расчёт статистики
    main_metrics = calculate_main_metrics(df)
    day_stats = calculate_day_stats(df)
    asset_stats = calculate_asset_stats(df)

    # Вывод результатов
    print_all_statistics(df, main_metrics, day_stats, asset_stats)

    # Переход к графикам
    print("\n" + "=" * 60)
    print(f"{Fore.YELLOW}📊 ОТКРЫВАЮ ОКНО С ГРАФИКАМИ...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Дополнительная визуализация данных в графическом виде.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Закройте окно с графиками, чтобы завершить программу.{Style.RESET_ALL}")
    print("=" * 60 + "\n")

    show_all_charts(df, df_sorted, day_stats, asset_stats)

    # Завершение
    print("\n" + "=" * 60)
    input("Анализ завершён! Нажмите Enter для завершения программы...")
    print("=" * 60)


if __name__ == "__main__":
    main()