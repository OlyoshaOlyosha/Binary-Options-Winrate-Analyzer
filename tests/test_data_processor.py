from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analyzer.data_processor import _parse_selection, apply_otc_filter, get_exchange_rate, load_data, preprocess_data


def test_parse_selection_valid():
    """Проверяет корректность преобразования строкового ввода в индексы списка."""
    files = [Path("f1.xlsx"), Path("f2.xlsx"), Path("f3.xlsx")]
    assert _parse_selection("1, 3", files) == [0, 2]


@pytest.mark.parametrize(
    "invalid_input",
    [
        "0",  # Вне диапазона (снизу)
        "4",  # Вне диапазона (сверху)
        "1, 1",  # Повтор
        "abc",  # Не число
        "1,,2",  # Некорректный формат
    ],
)
def test_parse_selection_invalid(invalid_input):
    """Проверяет реакцию парсера на различные варианты некорректного ввода."""
    files = [Path("f1.xlsx"), Path("f2.xlsx")]
    with pytest.raises(ValueError):
        _parse_selection(invalid_input, files)


def test_apply_otc_filter():
    """Проверяет работу фильтрации активов по метке (OTC)."""
    df = pd.DataFrame({"Актив": ["EUR/USD", "GBP/JPY (OTC)", "AUD/USD"]})

    # Проверка режимов: 1 - только OTC, 2 - только рынок, 3 - все
    assert len(apply_otc_filter(df, "1")) == 1
    assert len(apply_otc_filter(df, "2")) == 2
    assert len(apply_otc_filter(df, "3")) == 3


def test_preprocess_data_balance_logic():
    """
    Проверяет математическую корректность расчета истории баланса в обратном порядке.

    Тест имитирует цепочку сделок и проверяет, что финальное значение баланса
    соответствует заданному пользователем значению current_balance.
    """
    df = pd.DataFrame({
        "Время открытия": ["2024-01-01 10:00", "2024-01-01 11:00"],
        "Прибыль": [10.0, -5.0],
        "Экспирация": ["s60", "s300"],
    })

    current_balance = 100.0
    _, df_sorted = preprocess_data(df, current_balance)

    # Последняя точка в отсортированных данных должна совпадать с текущим балансом
    assert df_sorted.iloc[-1]["Баланс"] == 100.0

    # Проверка промежуточного состояния баланса (расчет назад)
    assert df_sorted.iloc[0]["Баланс"] == 105.0


@patch("requests.get")
def test_get_exchange_rate_success(mock_get):
    """Проверяет успешное получение курса валют через внешний API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"rates": {"RUB": 90.0}}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    rate = get_exchange_rate("USD", "RUB")
    assert rate == 90.0


@patch("requests.get")
def test_get_exchange_rate_network_error(mock_get):
    """Проверяет поведение системы при отсутствии интернет-соединения или ошибке API."""
    from analyzer.data_processor import _exchange_rate_cache

    _exchange_rate_cache.clear()

    mock_get.side_effect = Exception("No internet")
    rate = get_exchange_rate("USD", "RUB")
    assert rate is None


def test_load_data_with_messy_columns(tmp_path):
    """Проверяет очистку имен колонок от лишних пробелов при загрузке из Excel."""
    file = tmp_path / "messy.xlsx"
    df = pd.DataFrame({"  Результат  ": ["Win"], " Прибыль ": [10]})
    df.to_excel(file, index=False)

    loaded_df = load_data([file])
    assert "Результат" in loaded_df.columns
    assert "Прибыль" in loaded_df.columns


def test_preprocess_data_empty_strings():
    """Проверяет устойчивость обработки данных к минимальным значениям экспирации."""
    df = pd.DataFrame({
        "Время открытия": ["2024-01-01 10:00"],
        "Прибыль": [10.0],
        "Экспирация": ["s0"],
    })
    # Ожидаем успешное выполнение без исключений
    preprocess_data(df, 100.0)
