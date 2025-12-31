import configparser
import matplotlib.pyplot as plt
import locale

__version__ = "1.1.0"
__app_name__ = "Binary Options Winrate Analyzer"

CONFIG_FILE = 'analyzer_config.ini'

config = configparser.ConfigParser()

try:
    config.read(CONFIG_FILE, encoding='utf-8')
    if not config.sections():
        raise FileNotFoundError
except Exception:
    print(f"Файл конфигурации {CONFIG_FILE} не найден или повреждён. Используются настройки по умолчанию.")
    # Настройки по умолчанию
    config['graph_settings'] = {
        'figure_width': '14', 'figure_height': '9', 'background_color': '#1e1e1e',
        'plot_background': '#2b2b2b', 'grid_alpha': '0.5', 'font_size': '11'
    }
    config['colors'] = {
        'win': '#00ff88', 'loss': '#ff4444', 'line': '#00d4ff',
        'threshold': '#ffaa00', 'week_progress': '#ff8800'
    }
    config['analysis_settings'] = {
        'rolling_window_percent': '10', 'top_assets_count': '10', 'max_files_to_show': '5'
    }

# Словарь цветов
COLORS = config['colors']

def apply_plot_style():
    """Применяет все стили Matplotlib из конфига"""
    plt.style.use('dark_background')

    # Локаль для русских дат
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Russian_Russia.1251')
        except locale.Error:
            pass

    plt.rcParams['figure.figsize'] = (config.getint('graph_settings', 'figure_width'),
                                     config.getint('graph_settings', 'figure_height'))
    plt.rcParams['figure.facecolor'] = config.get('graph_settings', 'background_color')
    plt.rcParams['axes.facecolor'] = config.get('graph_settings', 'plot_background')
    plt.rcParams['axes.edgecolor'] = '#555555'
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['grid.alpha'] = config.getfloat('graph_settings', 'grid_alpha')
    plt.rcParams['grid.color'] = '#444444'
    plt.rcParams['text.color'] = 'white'
    plt.rcParams['axes.labelcolor'] = 'white'
    plt.rcParams['xtick.color'] = 'white'
    plt.rcParams['ytick.color'] = 'white'
    plt.rcParams['font.size'] = config.getint('graph_settings', 'font_size')