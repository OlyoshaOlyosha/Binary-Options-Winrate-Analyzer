from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analyzer.plots import _draw_top_row, show_all_charts


@pytest.fixture
def plot_data():
    """Подготавливает минимальный набор данных, необходимый для отрисовки графиков."""
    df = pd.DataFrame({
        "Время открытия": pd.to_datetime(["2024-01-01 10:00", "2024-01-01 11:00"]),
        "Результат": ["Win", "Loss"],
        "Прибыль числом": [10.0, -5.0],
        "Дата": [pd.Timestamp("2024-01-01").date()] * 2,
        "Час": [10, 11],
    })

    df_sorted = df.copy()
    df_sorted["Баланс"] = [95.0, 100.0]

    day_stats = pd.DataFrame(
        {"Винрейт": [50.0], "Прибыль": [5.0], "Сделок": [2]},
        index=[pd.Timestamp("2024-01-01").date()],
    )

    asset_stats = pd.DataFrame({"Винрейт": [50.0], "Сделок": [2]}, index=["EUR/USD"])

    return df, df_sorted, day_stats, asset_stats


@patch("matplotlib.pyplot.show")
@patch("analyzer.plots.apply_plot_style")
def test_show_all_charts_runs_without_error(mock_style, mock_show, plot_data):
    """Проверяет отсутствие исключений при выполнении полного цикла отрисовки всех графиков."""
    df, df_sorted, day_stats, asset_stats = plot_data

    try:
        show_all_charts(df, df_sorted, day_stats, asset_stats, 100.0, save_graph=False)
    except Exception as e:
        pytest.fail(f"show_all_charts упала с ошибкой: {e}")

    assert mock_show.called


def test_rolling_winrate_calculation(plot_data):
    """Проверяет корректность расчета колонок скользящего винрейта внутри визуализатора."""
    df, _, _, _ = plot_data
    colors = {"win": "g", "loss": "r", "line": "b", "threshold": "w"}
    dates = [pd.Timestamp("2024-01-01").date()]
    day_stats = pd.DataFrame({"Винрейт": [50.0]}, index=dates)
    asset_stats = pd.DataFrame({"Винрейт": [50.0]}, index=["EUR/USD"])

    with (
        patch("matplotlib.pyplot.subplot"),
        patch("matplotlib.pyplot.plot"),
        patch("matplotlib.pyplot.axhline"),
        patch("matplotlib.pyplot.barh"),
        patch("matplotlib.pyplot.title"),
        patch("matplotlib.pyplot.yticks"),
    ):
        _draw_top_row(df, asset_stats, dates, day_stats, colors)

        assert "Win_binary" in df.columns
        assert "Rolling_WR" in df.columns
        # При окне 10% (min=1) для первой сделки (Win) винрейт должен быть 100%
        assert df["Rolling_WR"].iloc[0] == 100.0


def test_save_figure_logic(tmp_path):
    """Проверяет логику формирования пути и вызова метода сохранения фигуры."""
    from analyzer.plots import _save_figure

    mock_fig = MagicMock()
    mock_fig.get_facecolor.return_value = "white"

    with patch("analyzer.plots.datetime") as mock_date:
        # Фиксация времени для проверки имени файла
        mock_date.now.return_value.astimezone.return_value.strftime.return_value = (
            "2026-01-17_12-00-00"
        )

        _save_figure(mock_fig)

        assert mock_fig.savefig.called
        args, _ = mock_fig.savefig.call_args  # kwargs заменены на '_' для Ruff
        assert "2026-01-17_12-00-00 график.png" in args[0]
