from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from analyzer.console_output import print_asset_statistics, print_general_statistics, save_statistics_to_md


@pytest.fixture
def sample_metrics():
    """Возвращает словарь с базовыми метриками для тестирования вывода."""
    return {
        "total_trades": 10,
        "winrate": 60.0,
        "total_profit": 150.5,
        "currency": "USD",
        "profit_factor": 1.5,
        "avg_win": 20.0,
        "avg_loss": 10.0,
    }


@pytest.fixture
def sample_df():
    """Возвращает минимальный DataFrame для тестирования функций визуализации."""
    return pd.DataFrame({
        "Результат": ["Win", "Loss", "Win"],
        "Дата": [pd.Timestamp("2024-01-01").date()] * 3,
        "Прибыль числом": [20.0, -10.0, 20.0],
        "Час": [10, 11, 12],
    })


def test_print_general_statistics_output(capsys, sample_df, sample_metrics):
    """Проверяет наличие ключевых показателей в консольном выводе общей статистики."""
    print_general_statistics(sample_df, sample_metrics)
    captured = capsys.readouterr()

    assert "ОБЩАЯ СТАТИСТИКА" in captured.out
    assert "Винрейт:" in captured.out
    assert "60.00%" in captured.out
    assert "USD" in captured.out


def test_print_asset_statistics_alignment(capsys):
    """Проверяет корректность формирования таблицы статистики по активам."""
    asset_stats = pd.DataFrame(
        {
            "Сделок": [5],
            "Винрейт": [80.0],
            "Прибыль": [100.0],
            "Серия_вин": [3],
            "Серия_лосс": [1],
        },
        index=["EUR/USD"],
    )

    print_asset_statistics(asset_stats)
    captured = capsys.readouterr()

    assert "EUR/USD" in captured.out
    assert "ПО АКТИВАМ" in captured.out


def test_save_statistics_to_md_creates_file(tmp_path, sample_metrics, sample_df):
    """Проверяет генерацию отчета в формате Markdown и валидность его содержимого."""
    day_stats = pd.DataFrame({"Сделок": [3], "Винрейт": [66.6], "Прибыль": [30.0]}, index=["2024-01-01"])
    asset_stats = pd.DataFrame(
        {
            "Сделок": [3],
            "Винрейт": [66.6],
            "Прибыль": [30.0],
            "Серия_вин": [2],
            "Серия_лосс": [1],
        },
        index=["BTC/USD"],
    )
    selected_files = [Path("trades/test.xlsx")]

    # Патчим Path в целевом модуле для перенаправления записи во временную директорию
    with patch("analyzer.console_output.Path") as mock_path:
        fake_file = tmp_path / "test_report.md"
        mock_path.return_value = fake_file

        save_statistics_to_md(sample_metrics, day_stats, asset_stats, sample_df, selected_files)

        assert fake_file.exists()
        content = fake_file.read_text(encoding="utf-8")
        assert "# 📊 Анализ сделок" in content
        assert "BTC/USD" in content
