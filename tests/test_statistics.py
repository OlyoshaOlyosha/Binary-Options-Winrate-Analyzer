import pandas as pd
import pytest

from analyzer.statistics import calculate_day_stats, calculate_main_metrics


@pytest.fixture
def sample_df():
    """Подготавливает тестовый набор данных из трех сделок для проверки агрегации."""
    data = {
        "Результат": ["Win", "Loss", "Win"],
        "Прибыль числом": [10.0, -5.0, 10.0],
        "Валюта": ["USD", "USD", "USD"],
        "Дата": ["2024-01-01", "2024-01-01", "2024-01-02"],
    }
    return pd.DataFrame(data)


def test_calculate_main_metrics_logic(sample_df):
    """Проверяет корректность расчета базовых торговых метрик (винрейт, профит-фактор)."""
    metrics = calculate_main_metrics(sample_df)

    assert metrics["total_trades"] == 3
    assert metrics["winrate"] == pytest.approx(66.66, rel=1e-2)
    assert metrics["total_profit"] == 15.0
    # Профит-фактор рассчитывается как (Сумма Win) / abs(Сумма Loss)
    assert metrics["profit_factor"] == 4.0


def test_calculate_day_stats(sample_df):
    """Проверяет корректность группировки торговых данных по датам."""
    stats = calculate_day_stats(sample_df)

    # Проверка количества сделок в разрезе конкретных дней
    assert stats.loc["2024-01-01", "Сделок"] == 2
    assert stats.loc["2024-01-02", "Сделок"] == 1


def test_calculate_main_metrics_no_losses():
    """
    Проверяет расчет метрик при отсутствии убыточных сделок.

    Убеждается, что профит-фактор корректно возвращает бесконечность (inf)
    во избежание ошибки деления на ноль.
    """
    df = pd.DataFrame({
        "Результат": ["Win"],
        "Прибыль числом": [10.0],
        "Валюта": ["USD"],
    })
    metrics = calculate_main_metrics(df)
    assert metrics["profit_factor"] == float("inf")
