import pandas as pd
from colorama import Fore

from analyzer.utils import calculate_asset_streaks, calculate_max_streak, color_profit, color_winrate


def test_color_profit():
    """Проверяет корректность выбора цвета и форматирования числовой прибыли."""
    assert Fore.GREEN in color_profit(10.5)
    assert Fore.RED in color_profit(-5.2)
    assert Fore.YELLOW in color_profit(0.0)
    # Проверка обязательного наличия двух знаков после запятой
    assert "10.50" in color_profit(10.5)


def test_color_winrate():
    """Проверяет логику окрашивания винрейта относительно порогового значения 50%."""
    assert Fore.GREEN in color_winrate(50.0)
    assert Fore.GREEN in color_winrate(75.0)
    assert Fore.RED in color_winrate(49.99)


def test_calculate_max_streak_logic():
    """Проверяет алгоритм вычисления максимальной последовательности (Win/Loss)."""
    # Стандартный случай с чередованием
    df = pd.DataFrame({"Результат": ["Win", "Win", "Loss", "Win", "Win", "Win"]})
    assert calculate_max_streak(df, "Win") == 3
    assert calculate_max_streak(df, "Loss") == 1

    # Кейс: только победы
    df_all_wins = pd.DataFrame({"Результат": ["Win", "Win", "Win"]})
    assert calculate_max_streak(df_all_wins, "Win") == 3
    assert calculate_max_streak(df_all_wins, "Loss") == 0

    # Кейс: строгое чередование (серия не должна превышать 1)
    df_alt = pd.DataFrame({"Результат": ["Win", "Loss", "Win", "Loss"]})
    assert calculate_max_streak(df_alt, "Win") == 1


def test_calculate_max_streak_empty():
    """Проверяет устойчивость функции расчета серий к пустым входным данным."""
    df_empty = pd.DataFrame(columns=["Результат"])
    assert calculate_max_streak(df_empty, "Win") == 0


def test_calculate_asset_streaks_full_process():
    """Проверяет комплексный расчет статистики для конкретного торгового актива."""
    df_asset = pd.DataFrame({
        "Время открытия": ["2024-01-01 10:00", "2024-01-01 10:05", "2024-01-01 10:10", "2024-01-01 10:15"],
        "Результат": ["Win", "Win", "Loss", "Loss"],
        "Прибыль числом": [10.0, 10.0, -10.0, -10.0],
    })

    result = calculate_asset_streaks(df_asset)

    assert result["Сделок"] == 4
    assert result["Винрейт"] == 50.0
    assert result["Прибыль"] == 0.0
    assert result["Серия_вин"] == 2
    assert result["Серия_лосс"] == 2


def test_calculate_asset_streaks_unsorted():
    """
    Проверяет корректность работы при подаче неотсортированных данных.

    Убеждается, что функция внутри себя выполняет сортировку по времени перед
    расчетом серий, чтобы избежать некорректных результатов из-за порядка строк.
    """
    # Сделки расположены в обратном временном порядке
    df = pd.DataFrame({
        "Время открытия": ["2024-01-01 12:00", "2024-01-01 10:00"],
        "Результат": ["Loss", "Win"],
        "Прибыль числом": [-10.0, 10.0],
    })

    result = calculate_asset_streaks(df)
    assert result["Сделок"] == 2
    assert result["Винрейт"] == 50.0


def test_calculate_asset_streaks_single_row():
    """Проверяет расчет статистики для актива с единственной сделкой в истории."""
    df = pd.DataFrame({
        "Время открытия": ["2024-01-01 10:00"],
        "Результат": ["Win"],
        "Прибыль числом": [15.0],
    })
    result = calculate_asset_streaks(df)
    assert result["Серия_вин"] == 1
    assert result["Серия_лосс"] == 0
