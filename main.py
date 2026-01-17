"""
Binary Options Winrate Analyzer.

Основной модуль входа в приложение. Координирует процесс загрузки данных,
применения фильтров, расчета статистики и визуализации результатов.
"""

from colorama import Fore, Style, init

from analyzer.config import __app_name__, __version__, config
from analyzer.console_output import print_all_statistics, save_statistics_to_md
from analyzer.data_processor import (
    apply_otc_filter,
    choose_expiration_filter,
    choose_otc_filter,
    choose_time_period_filter,
    get_current_balance,
    handle_currency_conversion,
    load_data,
    preprocess_data,
    select_files,
)
from analyzer.plots import show_all_charts
from analyzer.statistics import (
    calculate_asset_stats,
    calculate_day_stats,
    calculate_main_metrics,
)

# Инициализация colorama для корректной работы ANSI-цветов в терминале Windows
init(autoreset=True)


def main() -> None:
    """Управляет жизненным циклом программы: от выбора файлов до вывода графиков."""
    print(f"{Fore.CYAN}{__app_name__}{Style.RESET_ALL} {Fore.YELLOW}v{__version__}{Style.RESET_ALL}")

    # --- 1. Загрузка и первичная обработка ---
    selected_files = select_files()
    filter_choice = choose_otc_filter()

    df = load_data(selected_files)
    df = apply_otc_filter(df, filter_choice)

    current_balance = get_current_balance()
    df, df_sorted = preprocess_data(df, current_balance)
    df = handle_currency_conversion(df)

    # --- 2. Интерактивная фильтрация ---
    while True:
        df_filtered = choose_expiration_filter(df)
        if not df_filtered.empty:
            df = df_filtered
            break
        print(f"{Fore.YELLOW}После фильтра по экспирации не осталось сделок.{Style.RESET_ALL}")

    df = choose_time_period_filter(df)

    # Пересчитываем прогресс баланса под финальный набор отфильтрованных данных
    _, df_sorted = preprocess_data(df, current_balance)

    print(f"\nИтого после всех фильтров загружено сделок: {len(df)}")

    # --- 3. Аналитический блок ---
    main_metrics = calculate_main_metrics(df)
    day_stats = calculate_day_stats(df)
    asset_stats = calculate_asset_stats(df)

    # Вывод сводной таблицы в консоль
    print_all_statistics(df, main_metrics, day_stats, asset_stats)

    # --- 4. Финализация и экспорт ---
    auto_save = config.getboolean("save_settings", "auto_save", fallback=False)
    should_save = auto_save

    if not auto_save:
        answer = input("\n💾 Сохранить отчёт (статистика + график)? (да/нет, Enter=нет): ").strip().lower()
        should_save = answer in ["да", "yes", "y", "д", "+"]

    if should_save:
        save_statistics_to_md(main_metrics, day_stats, asset_stats, df, selected_files)

    # Вызов графического окна (save_graph передает флаг сохранения PNG)
    show_all_charts(df, df_sorted, day_stats, asset_stats, current_balance, save_graph=should_save)

    print("\n" + "=" * 60)
    input("Анализ завершён! Нажмите Enter для завершения программы...")
    print("=" * 60)


if __name__ == "__main__":
    main()
