from unittest.mock import patch

import pandas as pd
import pytest

from main import main


@patch("main.select_files")
@patch("main.choose_otc_filter")
@patch("main.load_data")
@patch("main.get_current_balance")
@patch("main.choose_expiration_filter")
@patch("main.choose_time_period_filter")
@patch("main.show_all_charts")
@patch("main.input", return_value="нет")
def test_main_execution_flow(
    mock_input, mock_charts, mock_time, mock_exp, mock_balance, mock_load, mock_otc_choice, mock_select
):
    """
    Проверяет полный цикл выполнения программы от загрузки до визуализации.

    Убеждается, что все ключевые модули координируются корректно и программа
    завершается без исключений при валидных входных данных.
    """
    # 1. Настройка имитационных данных
    mock_select.return_value = ["file1.csv"]
    mock_otc_choice.return_value = "Non-OTC"
    mock_balance.return_value = 1000.0

    # Создание минимального набора данных, проходящего через все этапы фильтрации
    df = pd.DataFrame({
        "Время открытия": pd.to_datetime(["2024-01-01 10:00"]),
        "Прибыль": [10.0],
        "Экспирация": ["s60"],
        "Прибыль числом": [10.0],
        "Результат": ["Win"],
        "Валюта": ["USD"],
        "Актив": ["EUR/USD"],
    })

    mock_load.return_value = df.copy()
    mock_exp.return_value = df.copy()
    mock_time.return_value = df.copy()

    # 2. Выполнение основной функции
    try:
        main()
    except Exception as e:
        pytest.fail(f"Функция main() завершилась с ошибкой: {e}")

    # 3. Верификация вызовов ключевых компонентов
    assert mock_load.called
    assert mock_charts.called
    assert mock_balance.called
