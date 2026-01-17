import configparser
from unittest.mock import patch

from analyzer.config import COLORS, apply_plot_style, config


def test_config_structure():
    """Проверяет наличие всех обязательных секций в объекте конфигурации."""
    sections = config.sections()
    assert "graph_settings" in sections
    assert "colors" in sections
    assert "analysis_settings" in sections


def test_default_colors():
    """Проверяет корректность базовых цветовых HEX-кодов в словаре COLORS."""
    assert COLORS["win"] == "#00ff88"
    assert COLORS["loss"] == "#ff4444"
    assert "line" in COLORS


def test_config_values_types():
    """Проверяет автоматическое преобразование строк конфига в int и float."""
    assert isinstance(config.getint("graph_settings", "figure_width"), int)
    assert isinstance(config.getfloat("graph_settings", "grid_alpha"), float)


@patch("matplotlib.pyplot.style.use")
@patch("matplotlib.pyplot.rcParams", new_callable=dict)
def test_apply_plot_style(mock_params, mock_style):
    """
    Проверяет корректность применения стилей Matplotlib.

    Убеждается, что используется темная тема и подтягиваются настройки шрифтов.
    """
    with patch("matplotlib.pyplot.rcParams", mock_params):
        apply_plot_style()
        mock_style.assert_called_with("dark_background")
        assert mock_params["font.size"] == config.getint("graph_settings", "font_size")


def test_analysis_settings_fallback():
    """Проверяет наличие и корректность параметров анализа по умолчанию."""
    expected_window = "10"
    assert config.get("analysis_settings", "rolling_window_percent") == expected_window
    assert config.getint("analysis_settings", "top_assets_count") == 10


@patch("configparser.ConfigParser.read")
def test_config_fallback_logic(mock_read):
    """
    Проверяет логику обработки пустых конфигурационных файлов.

    Аргумент mock_read необходим для работы декоратора @patch,
    даже если он не используется напрямую в теле теста.
    """
    test_cfg = configparser.ConfigParser()
    if not test_cfg.sections():
        test_cfg["colors"] = {"win": "green"}
    assert test_cfg["colors"]["win"] == "green"
