"""
Модуль с цветами и стилями интерфейса приложения.
Все цвета вынесены в константы для быстрой настройки.
"""

from PySide6.QtGui import QColor


# =============================================================================
#                        НАСТРОЙКА ЦВЕТОВ (ИЗМЕНЯЙТЕ ЗДЕСЬ)
# =============================================================================
class AppColors:
    """
    Основная палитра приложения.
    Для смены цветовой схемы достаточно редактировать значения ниже.
    """

    # -------------------------------------------------------------------------
    # АКЦЕНТНЫЙ ЦВЕТ (сиреневый — брендовый цвет приложения)
    # -------------------------------------------------------------------------
    ACCENT_PRIMARY = "#A855F7"       # Основной акцент (кнопки, прогресс)
    ACCENT_HOVER = "#9333EA"         # Акцент при наведении курсора
    ACCENT_PRESSED = "#7E22CE"       # Акцент при нажатии
    ACCENT_LIGHT = "#C084FC"         # Светлый оттенок акцента (обводки, подсветки)
    ACCENT_SOFT = "#3B0764"          # Приглушенный акцент (фон выделения)

    # -------------------------------------------------------------------------
    # СТАТУСНЫЕ ЦВЕТА
    # -------------------------------------------------------------------------
    SUCCESS = "#22C55E"              # Успех, готово
    ERROR = "#EF4444"                # Ошибка, критично
    WARNING = "#F59E0B"              # Предупреждение
    INFO = "#3B82F6"                 # Информация

    # -------------------------------------------------------------------------
    # ТЕМНАЯ ТЕМА
    # -------------------------------------------------------------------------
    class Dark:
        BG_MAIN = "#1E1E2E"          # Основной фон окна
        BG_WIDGET = "#27273A"        # Фон панелей и виджетов
        BG_SURFACE = "#1A1A29"       # Фон списков, полей ввода
        BG_ELEVATED = "#32324A"      # Фон при наведении/приподнятых элементах
        BORDER = "#3F3F5A"           # Цвет границ
        BORDER_HOVER = "#5A5A7A"     # Цвет границ при наведении
        TEXT_PRIMARY = "#E6E6F0"     # Основной текст
        TEXT_SECONDARY = "#A0A0B8"   # Второстепенный текст
        TEXT_DISABLED = "#6B6B80"    # Отключенный текст
        DRAG_ZONE_BG = "#20202E"     # Фон зоны drag-and-drop
        DRAG_ZONE_ACTIVE = "#4C1D95" # Фон зоны DnD когда перетаскиваем файл
        PROGRESS_BG = "#2A2A3C"      # Фон прогресс-бара
        LOG_BG = "#161621"           # Фон лога

    # -------------------------------------------------------------------------
    # СВЕТЛАЯ ТЕМА
    # -------------------------------------------------------------------------
    class Light:
        BG_MAIN = "#F5F5F7"
        BG_WIDGET = "#FFFFFF"
        BG_SURFACE = "#FAFAFC"
        BG_ELEVATED = "#EDEDF2"
        BORDER = "#D9D9E5"
        BORDER_HOVER = "#B8B8C8"
        TEXT_PRIMARY = "#1F1F2E"
        TEXT_SECONDARY = "#6B6B80"
        TEXT_DISABLED = "#9B9BAD"
        DRAG_ZONE_BG = "#FAFAFF"
        DRAG_ZONE_ACTIVE = "#EDE9FE"
        PROGRESS_BG = "#EAEAF0"
        LOG_BG = "#F0F0F5"


# =============================================================================
#                           ГЕНЕРАТОР QSS СТИЛЕЙ
# =============================================================================
def get_stylesheet(theme: str = "dark") -> str:
    """
    Возвращает готовую таблицу стилей (QSS) для выбранной темы.

    :param theme: "dark" или "light"
    :return: строка с QSS-стилями
    """
    pal = AppColors.Dark if theme.lower() == "dark" else AppColors.Light

    return f"""
    /* ================================================================
       ОСНОВНОЕ ОКНО И ГЛОБАЛЬНЫЕ НАСТРОЙКИ
       ================================================================ */
    QMainWindow, QWidget#CentralWidget {{
        background-color: {pal.BG_MAIN};
        color: {pal.TEXT_PRIMARY};
        font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
        font-size: 10pt;
    }}

    /* ================================================================
       ВСЕ КНОПКИ (с анимацией перехода)
       ================================================================ */
    QPushButton {{
        background-color: {pal.BG_WIDGET};
        color: {pal.TEXT_PRIMARY};
        border: 1px solid {pal.BORDER};
        border-radius: 8px;
        padding: 9px 20px;
        font-weight: 500;
        selection-background-color: {AppColors.ACCENT_SOFT};
        transition: all 0.15s ease-in-out;
        outline: 0;
    }}
    QPushButton:hover {{
        background-color: {pal.BG_ELEVATED};
        border-color: {pal.BORDER_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {pal.BG_SURFACE};
        border-color: {AppColors.ACCENT_LIGHT};
    }}
    QPushButton:disabled {{
        background-color: {pal.BG_SURFACE};
        color: {pal.TEXT_DISABLED};
        border-color: {pal.BORDER};
    }}
    QPushButton:focus {{
        border-color: {pal.BORDER};
        outline: 0;
    }}

    /* Кнопка с акцентным заливкой (Основное действие — Извлечь звук) */
    QPushButton#PrimaryButton {{
        background-color: {AppColors.ACCENT_PRIMARY};
        color: #FFFFFF;
        border: 1px solid {AppColors.ACCENT_PRIMARY};
        font-weight: 600;
        letter-spacing: 0.3px;
        outline: 0;
    }}
    QPushButton#PrimaryButton:hover {{
        background-color: {AppColors.ACCENT_HOVER};
        border-color: {AppColors.ACCENT_HOVER};
    }}
    QPushButton#PrimaryButton:pressed {{
        background-color: {AppColors.ACCENT_PRESSED};
        border-color: {AppColors.ACCENT_PRESSED};
    }}
    QPushButton#PrimaryButton:disabled {{
        background-color: {pal.BG_ELEVATED};
        color: {pal.TEXT_DISABLED};
        border-color: {pal.BORDER};
    }}
    QPushButton#PrimaryButton:focus {{
        border-color: {AppColors.ACCENT_PRIMARY};
        outline: 0;
    }}

    /* Кнопки с иконками в списке (маленькие, круглые) */
    QPushButton#IconButton {{
        background-color: transparent;
        color: {pal.TEXT_SECONDARY};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px 8px;
        min-width: 28px;
        min-height: 28px;
        max-width: 28px;
        max-height: 28px;
        outline: 0;
    }}
    QPushButton#IconButton:focus {{
        outline: 0;
        border: 1px solid transparent;
    }}
    QPushButton#IconButton:hover {{
        background-color: {pal.BG_ELEVATED};
        color: {pal.TEXT_PRIMARY};
        border-color: {pal.BORDER};
    }}
    QPushButton#IconButton:pressed {{
        background-color: {pal.BG_SURFACE};
        color: {AppColors.ACCENT_PRIMARY};
    }}
    QPushButton#IconDelete:hover {{
        color: {AppColors.ERROR};
        border-color: {AppColors.ERROR};
        background-color: #2D1B1B;
    }}

    /* ================================================================
       ЗОНА DRAG-AND-DROP
       ================================================================ */
    QFrame#DragDropFrame {{
        background-color: {pal.DRAG_ZONE_BG};
        border: 2px dashed {pal.BORDER};
        border-radius: 16px;
    }}
    QFrame#DragDropFrame[active="true"] {{
        background-color: {pal.DRAG_ZONE_ACTIVE};
        border: 2px dashed {AppColors.ACCENT_PRIMARY};
    }}
    QLabel#DragDropTitle {{
        color: {pal.TEXT_PRIMARY};
        font-size: 14pt;
        font-weight: 600;
    }}
    QLabel#DragDropSubtitle {{
        color: {pal.TEXT_SECONDARY};
        font-size: 10pt;
    }}
    QLabel#DragDropHint {{
        color: {pal.TEXT_SECONDARY};
        font-size: 9pt;
    }}

    /* ================================================================
       СПИСОК ФАЙЛОВ
       ================================================================ */
    QListWidget {{
        background-color: {pal.BG_SURFACE};
        color: {pal.TEXT_PRIMARY};
        border: 1px solid {pal.BORDER};
        border-radius: 12px;
        padding: 6px;
        outline: 0;
    }}
    QListWidget::item {{
        background-color: {pal.BG_WIDGET};
        color: {pal.TEXT_PRIMARY};
        border: 1px solid {pal.BORDER};
        border-radius: 10px;
        margin: 4px 2px;
        padding: 0;
    }}
    QListWidget::item:hover {{
        background-color: {pal.BG_ELEVATED};
        border-color: {pal.BORDER_HOVER};
    }}
    QListWidget::item:selected {{
        background-color: {pal.BG_ELEVATED};
        border-color: {AppColors.ACCENT_PRIMARY};
    }}

    /* Лейблы внутри элементов списка файлов */
    QLabel#FileNameLabel {{
        color: {pal.TEXT_PRIMARY};
    }}
    QLabel#FileInfoLabel {{
        color: {pal.TEXT_SECONDARY};
    }}
    QLabel#FileStatusLabel {{
        color: {pal.TEXT_SECONDARY};
    }}

    /* ================================================================
       ПРОГРЕСС-БАР
       ================================================================ */
    QProgressBar {{
        background-color: {pal.PROGRESS_BG};
        color: {pal.TEXT_PRIMARY};
        border: 1px solid {pal.BORDER};
        border-radius: 10px;
        text-align: center;
        min-height: 22px;
        font-weight: 600;
    }}
    QProgressBar::chunk {{
        background-color: {AppColors.ACCENT_PRIMARY};
        border-radius: 9px;
        transition: width 0.2s ease;
    }}

    /* ================================================================
       ЛОГ (текстовое поле)
       ================================================================ */
    QPlainTextEdit, QTextEdit {{
        background-color: {pal.LOG_BG};
        color: {pal.TEXT_PRIMARY};
        border: 1px solid {pal.BORDER};
        border-radius: 10px;
        padding: 10px;
        selection-background-color: {AppColors.ACCENT_SOFT};
        selection-color: #FFFFFF;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 9.5pt;
    }}

    /* ================================================================
       ПАНЕЛЬ НАСТРОЕК
       ================================================================ */
    QFrame#SettingsPanel {{
        background-color: {pal.BG_WIDGET};
        border: 1px solid {pal.BORDER};
        border-radius: 12px;
    }}
    QLabel#SettingsTitle {{
        color: {pal.TEXT_PRIMARY};
        font-size: 11pt;
        font-weight: 600;
    }}
    QLabel#SettingsLabel {{
        color: {pal.TEXT_SECONDARY};
        font-size: 10pt;
    }}

    /* ================================================================
       ПОЛЯ ВВОДА ПУТИ (QLineEdit)
       ================================================================ */
    QLineEdit {{
        background-color: {pal.BG_SURFACE};
        color: {pal.TEXT_PRIMARY};
        border: 1px solid {pal.BORDER};
        border-radius: 8px;
        padding: 7px 10px;
        selection-background-color: {AppColors.ACCENT_SOFT};
    }}
    QLineEdit:hover, QLineEdit:focus {{
        border-color: {AppColors.ACCENT_PRIMARY};
    }}

    /* ================================================================
       КОМБОБОКСЫ (ВЫПАДАЮЩИЕ СПИСКИ)
       ================================================================ */
    QComboBox {{
        background-color: {pal.BG_SURFACE};
        color: {pal.TEXT_PRIMARY};
        border: 1px solid {pal.BORDER};
        border-radius: 8px;
        padding: 6px 14px 6px 10px;
        min-height: 28px;
        outline: 0;
    }}
    QComboBox:hover {{
        border-color: {pal.BORDER_HOVER};
    }}
    QComboBox:focus {{
        border-color: {pal.BORDER};
        outline: 0;
    }}
    QComboBox::drop-down {{
    border: none;
    width: 30px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}}
    }}
    QComboBox::down-arrow {{
    image: none;
    width: 6px;
    height: 6px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {pal.TEXT_SECONDARY};
    subcontrol-origin: padding;
    subcontrol-position: center center;
}}
        
    }}
    QComboBox QAbstractItemView {{
        background-color: {pal.BG_WIDGET};
        color: {pal.TEXT_PRIMARY};
        border: 1px solid {pal.BORDER};
        border-radius: 8px;
        selection-background-color: {AppColors.ACCENT_SOFT};
        selection-color: {pal.TEXT_PRIMARY};
        padding: 4px;
        outline: 0;
    }}

    /* ================================================================
       РАЗДЕЛИТЕЛИ
       ================================================================ */
    QFrame[shape="HLine"] {{
        color: {pal.BORDER};
        max-height: 1px;
        min-height: 1px;
        background-color: {pal.BORDER};
    }}

    /* ================================================================
       SCROLLBAR (Полоса прокрутки)
       ================================================================ */
    QScrollBar:vertical {{
        background-color: {pal.BG_SURFACE};
        width: 10px;
        margin: 1px 0px 1px 0px;
        padding: 0px;
        border: none;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {pal.BORDER};
        min-height: 40px;
        margin: 0px;
        border: none;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {AppColors.ACCENT_LIGHT};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
        margin: 0px;
        padding: 0px;
        border: none;
        background: transparent;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
        border: none;
        margin: 0px;
        padding: 0px;
    }}
    QScrollBar:horizontal {{
        background-color: {pal.BG_SURFACE};
        height: 10px;
        margin: 0px 1px 0px 1px;
        border: none;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {pal.BORDER};
        min-width: 40px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {AppColors.ACCENT_LIGHT};
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
        margin: 0px;
        padding: 0px;
        border: none;
        background: transparent;
    }}
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: transparent;
        border: none;
        margin: 0px;
        padding: 0px;
    }}
    """
