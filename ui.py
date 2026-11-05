"""
Модуль графического интерфейса (GUI)
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from PySide6.QtCore import (
    Qt, QMimeData, QSize, QPropertyAnimation, QEasingCurve, QTimer, QEvent,
    Signal, QRect, QUrl
)
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QIcon, QPixmap, QPainter, QColor,
    QLinearGradient, QBrush, QAction, QKeySequence, QDesktopServices,
    QFontMetrics
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QProgressBar,
    QPlainTextEdit, QMessageBox, QComboBox, QLineEdit, QFileDialog,
    QSplitter, QSizePolicy, QToolButton, QApplication, QStyle, QAbstractItemView
)

from ui_colors import AppColors, get_stylesheet
from extractor import (
    AudioExtractor, ExtractionThread, ConfigManager,
    SUPPORTED_EXT, normalize_path, check_ffmpeg_available,
    get_app_dir, resolve_app_icon_path,
)



class FileItemWidget(QFrame):
    """
    Кастомный виджет для одного файла в списке.
    Содержит: иконку, имя/путь файла, статус, кнопку удаления.
    """

    # Состояния файла
    STATE_PENDING = "pending"       # В очереди
    STATE_PROCESSING = "processing" # Обрабатывается
    STATE_SUCCESS = "success"       # Успешно
    STATE_ERROR = "error"           # Ошибка

    def __init__(self, file_path: str, on_delete=None, theme: str = "dark", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self._on_delete = on_delete
        self._state = self.STATE_PENDING
        self._info = ""
        self._theme = theme  # Текущая тема для цветов

        # Сохраняем оригинальные строки (до elide) — чтобы при ресайзе перестраивать
        p = Path(self.file_path)
        self._orig_name = p.name
        try:
            size_kb = p.stat().st_size / 1024 if p.exists() else 0
        except (OSError, PermissionError):
            size_kb = 0

        if size_kb >= 1024 * 1024:
            size_str = f"{size_kb / (1024 * 1024):.2f} ГБ"
        elif size_kb >= 1024:
            size_str = f"{size_kb / 1024:.2f} МБ"
        elif size_kb > 0:
            size_str = f"{size_kb:.1f} КБ"
        else:
            size_str = "размер неизвестен"

        try:
            parent_str = str(p.parent)
        except Exception:
            parent_str = ""

        self._orig_info = f"{parent_str}   •   {size_str}"
        self._orig_tooltip_info = f"{parent_str}\nРазмер: {size_str}"
        self._orig_status = "В очереди"

        self.setObjectName("FileItem")
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(78)

        self._build_ui()
        self._apply_state_style()


    def _build_ui(self):
        """Создаёт интерфейс элемента списка."""

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 4, 14, 14)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignVCenter)

        # Статус-иконка (левый цветной кружок)
        self.status_dot = QFrame()
        self.status_dot.setFixedSize(QSize(12, 12))
        self.status_dot.setStyleSheet("""
            QFrame {
                border-radius: 6px;
                background-color: #6B6B80;
            }
        """)
        root.addWidget(self.status_dot, 0, Qt.AlignVCenter)

        # Центральная часть (название + путь + статус)
        center_layout = QVBoxLayout()
        center_layout.setSpacing(2)
        center_layout.setContentsMargins(0, 0, 8, 0)
        center_layout.setAlignment(Qt.AlignVCenter)

        # Название файла (крупно) — с обрезкой, чтобы не наезжало
        self.lbl_name = QLabel(self._orig_name)
        self.lbl_name.setObjectName("FileNameLabel")
        self.lbl_name.setStyleSheet("font-size: 10.5pt; font-weight: 600;")
        self.lbl_name.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_name.setToolTip(self._orig_name)
        self.lbl_name.setContentsMargins(0, 0, 0, 0)
        self.lbl_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_name.setMinimumHeight(22)
        self.lbl_name.setMaximumHeight(22)
        self.lbl_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        center_layout.addWidget(self.lbl_name)

        # Путь к файлу + размер
        self.lbl_info = QLabel(self._orig_info)
        self.lbl_info.setObjectName("FileInfoLabel")
        self.lbl_info.setStyleSheet("font-size: 9pt;")
        self.lbl_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_info.setToolTip(self._orig_tooltip_info)
        self.lbl_info.setContentsMargins(0, 0, 0, 0)
        self.lbl_info.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_info.setMinimumHeight(18)
        self.lbl_info.setMaximumHeight(18)
        self.lbl_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        center_layout.addWidget(self.lbl_info)

        # Статус обработки
        self.lbl_status = QLabel("В очереди")
        self.lbl_status.setObjectName("FileStatusLabel")
        self.lbl_status.setStyleSheet("font-size: 9pt; font-style: italic;")
        self.lbl_status.setContentsMargins(0, 0, 0, 0)
        self.lbl_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_status.setMinimumHeight(18)
        self.lbl_status.setMaximumHeight(18)
        self.lbl_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        center_layout.addWidget(self.lbl_status)

        root.addLayout(center_layout, 1)

        # Кнопка удаления
        self.btn_delete = QPushButton("✕")
        self.btn_delete.setObjectName("IconButton")
        self.btn_delete.setProperty("class", "IconDelete")
        self.btn_delete.setToolTip("Удалить из списка")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFocusPolicy(Qt.NoFocus)
        self.btn_delete.clicked.connect(self._delete_clicked)
        root.addWidget(self.btn_delete, 0, Qt.AlignVCenter)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_elided_texts()


    def _apply_elided_texts(self):
        available = max(120, self.width() - 100)

        # Имя файла
        fm_name = QFontMetrics(self.lbl_name.font())
        elided_name = fm_name.elidedText(self._orig_name, Qt.ElideMiddle, available)
        if elided_name != self.lbl_name.text():
            self.lbl_name.setText(elided_name)

        # Путь+размер
        fm_info = QFontMetrics(self.lbl_info.font())
        elided_info = fm_info.elidedText(self._orig_info, Qt.ElideMiddle, available)
        if elided_info != self.lbl_info.text():
            self.lbl_info.setText(elided_info)

        # Статус (тоже обрезаем, если вдруг длинный)
        fm_status = QFontMetrics(self.lbl_status.font())
        cur_status = self.lbl_status.text()
        elided_status = fm_status.elidedText(cur_status, Qt.ElideRight, available)
        if elided_status != cur_status:
            self.lbl_status.setText(elided_status)


    @property
    def state(self) -> str:
        """Текущее состояние элемента (безопасный доступ к _state)."""
        return self._state


    def _delete_clicked(self):
        if self._on_delete:
            self._on_delete(self.file_path)


    def set_state(self, state: str, info: str = ""):
        """Установить состояние элемента (статус обработки)."""
        self._state = state
        self._info = info
        self._apply_state_style()


    def apply_theme(self, theme: str):
        """Применить новую тему (обновить цвета для PENDING-состояния)."""
        self._theme = theme
        # Перестилизовать себя, чтобы подхватились QSS-правила по objectName
        self.style().unpolish(self)
        self.style().polish(self)
        # Обновить стили статусной точки и лейбла статуса
        self._apply_state_style()


    def _apply_state_style(self):
        """Применить стили и текст согласно состоянию."""
        pal = AppColors.Dark if self._theme == "dark" else AppColors.Light
        colors = {
            self.STATE_PENDING:    (pal.TEXT_DISABLED, pal.TEXT_SECONDARY, "В очереди"),
            self.STATE_PROCESSING: ("#A855F7", "#C084FC", "Обработка…"),
            self.STATE_SUCCESS:    ("#22C55E", "#22C55E", "Готово"),
            self.STATE_ERROR:      ("#EF4444", "#EF4444", "Ошибка"),
        }
        dot_color, text_color, default_text = colors.get(
            self._state, colors[self.STATE_PENDING]
        )
        self.status_dot.setStyleSheet(f"""
            QFrame {{
                border-radius: 6px;
                background-color: {dot_color};
            }}
        """)
        # Для PENDING используем стиль без жёсткого цвета (цвет возьмётся из QSS),
        if self._state == self.STATE_PENDING:
            self.lbl_status.setStyleSheet("font-size: 9pt; font-weight: 500;")
        else:
            self.lbl_status.setStyleSheet(
                f"color: {text_color}; font-size: 9pt; font-weight: 500;"
            )
        if self._state == self.STATE_SUCCESS and self._info:
            status_text = f"✓ {self._info}"
        elif self._state == self.STATE_ERROR and self._info:
            status_text = f"✕ {self._info}"
        else:
            status_text = default_text
        self.lbl_status.setText(status_text)
        self.lbl_status.setToolTip(status_text)
        # Применить elide к новому статусу
        if self.width() > 0:
            self._apply_elided_texts()


class DragDropFrame(QFrame):
    """
    Зона, в которую можно перетащить видеофайлы мышью.
    Подсвечивается, когда над ней находится курсор с файлами.
    """
    filesDropped = Signal(list)  # Список путей к файлам

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DragDropFrame")
        self.setProperty("active", False)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self._build_ui()


    def _build_ui(self):
        """Разметка зоны drag-and-drop."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        # Иконка
        icon = QLabel("🎬")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 42pt;")
        layout.addWidget(icon)

        # Заголовок
        self.title = QLabel("Перетащите видеофайлы сюда")
        self.title.setObjectName("DragDropTitle")
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)

        # Подзаголовок
        self.subtitle = QLabel(
            "Поддерживаемые форматы: MP4 • MKV • MOV • AVI • WEBM • M4V"
        )
        self.subtitle.setObjectName("DragDropSubtitle")
        self.subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle)

        # Подсказка
        self.hint = QLabel("Можно перетащить сразу несколько файлов")
        self.hint.setObjectName("DragDropHint")
        self.hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.hint)


    def set_active(self, active: bool):
        """Включить/выключить подсветку зоны DnD."""
        self.setProperty("active", active)
        # Перестилизовать виджет после смены динамического свойства
        self.style().unpolish(self)
        self.style().polish(self)


    # Обработчики drag-and-drop событий

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # Проверяем, что хоть один URL — локальный файл поддерживаемого формата
            if any(self._is_supported(u) for u in event.mimeData().urls()):
                event.acceptProposedAction()
                self.set_active(True)
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.set_active(False)
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            if any(self._is_supported(u) for u in event.mimeData().urls()):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        self.set_active(False)
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        files: List[str] = []
        for url in event.mimeData().urls():
            if url.isLocalFile() and self._is_supported(url):
                files.append(url.toLocalFile())
        if files:
            event.acceptProposedAction()
            self.filesDropped.emit(files)
        else:
            event.ignore()


    @staticmethod
    def _is_supported(url: QUrl) -> bool:
        """Проверяет, что URL — локальный файл с поддерживаемым расширением."""
        if not url.isLocalFile():
            return False
        ext = Path(url.toLocalFile()).suffix.lower()
        return ext in SUPPORTED_EXT



class MainWindow(QMainWindow):
    """Главное окно Audio Track Extractor."""

    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config
        self.setWindowTitle("Audio Track Extractor")
        self.resize(860, 680)
        self._center_window()

        # Создаём экстрактор
        self.extractor = AudioExtractor(config, self)
        self._thread: Optional[ExtractionThread] = None

        # Множество уже добавленных файлов (нормализованные пути)
        self._added_files: Set[str] = set()
        # Путь -> item_widget для быстрого доступа
        self._item_map: Dict[str, FileItemWidget] = {}
        # Путь -> QListWidgetItem
        self._list_items: Dict[str, QListWidgetItem] = {}

        # Флаг защиты от рекурсии в eventFilter
        self._in_event_filter = False

        # Текущая тема (для обновления динамических цветов)
        self._current_theme = self.config.get("theme")

        # Таймер для моргания индикатора (пункт 7)
        self._indicator_timer: Optional[QTimer] = None
        self._indicator_toggle = False

        # Подключение сигналов экстрактора
        self._connect_extractor_signals()

        # Сборка интерфейса (сначала собираем виджеты)
        self._build_ui()
        self._build_menu()

        # Применяем тему (после того как все виджеты созданы)
        self._apply_theme(self._current_theme)

        # Проверка ffmpeg — пользовательский сценарий: показать сообщение
        ok, msg = check_ffmpeg_available()
        if not ok:
            QTimer.singleShot(200, lambda: self._show_ffmpeg_error(msg))


    def _build_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        # Делаем центральный виджет кликабельным — чтобы отжимать фокус с кнопок
        central.setFocusPolicy(Qt.StrongFocus)
        self.setCentralWidget(central)

        # Ставим eventFilter на центральный виджет и все его потомки,
        # чтобы клик по ЛЮБОЙ пустой области (даже внутри фреймов) сбрасывал фокус
        central.installEventFilter(self)

        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # Зона Drag-and-Drop
        self.dnd_frame = DragDropFrame(self)
        # Подключаем сигнал дропа файлов
        self.dnd_frame.filesDropped.connect(self.add_files)
        root.addWidget(self.dnd_frame)

        # Верхняя панель управления
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.lbl_files = QLabel("Файлы к обработке")
        self.lbl_files.setObjectName("FilesTitleLabel")
        self.lbl_files.setStyleSheet("font-size: 12pt; font-weight: 600;")
        self.lbl_files_count = QLabel("(0)")
        self.lbl_files_count.setStyleSheet("color: #A0A0B8; font-size: 11pt; font-weight: 500;")
        top_bar.addWidget(self.lbl_files)
        top_bar.addWidget(self.lbl_files_count)
        top_bar.addStretch(1)

        # Круглый индикатор
        self.status_indicator = QFrame()
        self.status_indicator.setFixedSize(QSize(12, 12))
        self._set_indicator_color("#6B6B80")
        self.status_indicator.setToolTip("Состояние: ожидание")
        top_bar.addWidget(self.status_indicator, 0, Qt.AlignVCenter)
        top_bar.addSpacing(4)

        self.btn_clear = QPushButton("🗑  Очистить список")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setToolTip("Удалить все файлы из списка")
        self.btn_clear.setFocusPolicy(Qt.NoFocus)
        self.btn_clear.clicked.connect(self._clear_list)
        top_bar.addWidget(self.btn_clear)

        self.btn_extract = QPushButton("🎵  Извлечь звук")
        self.btn_extract.setObjectName("PrimaryButton")
        self.btn_extract.setCursor(Qt.PointingHandCursor)
        self.btn_extract.setMinimumWidth(180)
        self.btn_extract.setToolTip("Запустить извлечение аудиодорожек для всех файлов")
        self.btn_extract.setFocusPolicy(Qt.NoFocus)
        self.btn_extract.clicked.connect(self._on_extract_clicked)
        top_bar.addWidget(self.btn_extract)

        root.addLayout(top_bar)


        self.list_widget = QListWidget()
        # Плавная прокрутка списка
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.verticalScrollBar().setSingleStep(8)
        self.list_widget.setSpacing(2)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setMinimumHeight(180)
        # Также снимаем фокусное выделение рамки
        self.list_widget.setFocusPolicy(Qt.NoFocus)
        # Поддержка удаления по Delete
        self.list_widget.installEventFilter(self)
        root.addWidget(self.list_widget, 2)


        self._build_settings_panel(root)


        # Прогресс-бар + счётчик + кнопка лога

        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Готово: %p%")
        self.progress_bar.setFocusPolicy(Qt.NoFocus)
        progress_layout.addWidget(self.progress_bar, 1)

        self.lbl_progress = QLabel("0 / 0")
        self.lbl_progress.setStyleSheet("color: #A0A0B8; font-weight: 500;")
        self.lbl_progress.setMinimumWidth(70)
        self.lbl_progress.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.lbl_progress)

        self.btn_open_log = QPushButton("📄  Лог")
        self.btn_open_log.setCursor(Qt.PointingHandCursor)
        self.btn_open_log.setFocusPolicy(Qt.NoFocus)
        self.btn_open_log.setToolTip("Открыть полный журнал работы")
        self.btn_open_log.clicked.connect(self._open_log_file)
        progress_layout.addWidget(self.btn_open_log)

        root.addLayout(progress_layout)

        self.statusBar().showMessage("")
        self.statusBar().setSizeGripEnabled(False)

        self._apply_title_colors()

    def _set_indicator_color(self, color_hex: str):
        """Установить цвет круглого индикатора."""
        self.status_indicator.setStyleSheet(f"""
            QFrame {{
                border-radius: 6px;
                background-color: {color_hex};
            }}
        """)

    def _start_indicator_blink(self):
        """Начать моргание индикатора (при обработке)."""
        self._indicator_toggle = False
        self._set_indicator_color("#C084FC")
        self.status_indicator.setToolTip("Состояние: идёт извлечение дорожек…")
        if self._indicator_timer is None:
            self._indicator_timer = QTimer(self)
            self._indicator_timer.timeout.connect(self._blink_tick)
        self._indicator_timer.start(100)

    def _stop_indicator_blink(self):
        """Остановить моргание, сделать статичным сиреневым (завершено/ожидание)."""
        if self._indicator_timer and self._indicator_timer.isActive():
            self._indicator_timer.stop()

        self._set_indicator_color("#A855F7")
        self._indicator_toggle = False
        self.status_indicator.setToolTip("Состояние: готово")

    def _reset_indicator(self):
        """Сбросить индикатор в исходное (серый)."""
        if self._indicator_timer and self._indicator_timer.isActive():
            self._indicator_timer.stop()
        self._set_indicator_color("#6B6B80")
        self._indicator_toggle = False
        self.status_indicator.setToolTip("Состояние: ожидание")

    def _blink_tick(self):
        """Тик таймера: переключить цвет индикатора."""
        self._indicator_toggle = not self._indicator_toggle
        if self._indicator_toggle:
            self._set_indicator_color("#7E22CE")   # тёмно-сиреневый
        else:
            self._set_indicator_color("#C084FC")   # светло-сиреневый


    def _apply_title_colors(self):
        """Применить цвета заголовков 'Файлы к обработке' и др.
        согласно текущей теме (вместо жёстко прошитого чёрного)."""
        pal = AppColors.Dark if self._current_theme == "dark" else AppColors.Light
        text_color = pal.TEXT_PRIMARY

        # lbl_files — основной заголовок (12pt)
        if getattr(self, "lbl_files", None) is not None:
            self.lbl_files.setStyleSheet(
                f"font-size: 12pt; font-weight: 600; color: {text_color};"
            )

        # lbl_files_count — счётчик файлов (вторичный цвет)
        if getattr(self, "lbl_files_count", None) is not None:
            self.lbl_files_count.setStyleSheet(
                f"color: {pal.TEXT_SECONDARY}; font-size: 11pt; font-weight: 500;"
            )

        # lbl_progress — счётчик прогресса (вторичный цвет)
        if getattr(self, "lbl_progress", None) is not None:
            self.lbl_progress.setStyleSheet(
                f"color: {pal.TEXT_SECONDARY}; font-weight: 500;"
            )


    def _build_settings_panel(self, parent_layout: QVBoxLayout):
        """Панель с настройками: тема, путь сохранения."""
        frame = QFrame()
        frame.setObjectName("SettingsPanel")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)

        # Заголовок
        title = QLabel("⚙  Настройки")
        title.setObjectName("SettingsTitle")
        lay.addWidget(title)


        row1 = QHBoxLayout()
        row1.setSpacing(10)
        lbl_theme = QLabel("Тема интерфейса:")
        lbl_theme.setObjectName("SettingsLabel")
        lbl_theme.setMinimumWidth(140)
        row1.addWidget(lbl_theme)

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItem("🌙  Тёмная", userData="dark")
        self.cmb_theme.addItem("☀  Светлая", userData="light")
        # Установить текущую
        current_theme = self.config.get("theme")
        idx = 0 if current_theme == "dark" else 1
        self.cmb_theme.setCurrentIndex(idx)
        self.cmb_theme.currentIndexChanged.connect(self._on_theme_changed)
        self.cmb_theme.setCursor(Qt.PointingHandCursor)
        self.cmb_theme.setFocusPolicy(Qt.NoFocus)
        row1.addWidget(self.cmb_theme, 1)
        lay.addLayout(row1)


        row2 = QHBoxLayout()
        row2.setSpacing(10)
        lbl_out = QLabel("Сохранять аудио:")
        lbl_out.setObjectName("SettingsLabel")
        lbl_out.setMinimumWidth(140)
        row2.addWidget(lbl_out)

        self.cmb_output_mode = QComboBox()
        self.cmb_output_mode.addItem("📁  Рядом с исходным видео",
                                     userData="source")
        self.cmb_output_mode.addItem("🗂  В пользовательской папке", userData="custom")
        curr_mode = self.config.get("output_mode")
        self.cmb_output_mode.setCurrentIndex(0 if curr_mode == "source" else 1)
        self.cmb_output_mode.currentIndexChanged.connect(self._on_output_mode_changed)
        self.cmb_output_mode.setCursor(Qt.PointingHandCursor)
        self.cmb_output_mode.setFocusPolicy(Qt.NoFocus)
        row2.addWidget(self.cmb_output_mode, 1)
        lay.addLayout(row2)


        row3 = QHBoxLayout()
        row3.setSpacing(8)
        lbl_path = QLabel("Папка для сохранения:")
        lbl_path.setObjectName("SettingsLabel")
        lbl_path.setMinimumWidth(140)
        row3.addWidget(lbl_path)

        self.edt_output_path = QLineEdit()
        self.edt_output_path.setPlaceholderText(
            "Выберите папку для аудио или оставьте по умолчанию"
        )
        curr_path = self.config.get("custom_output_path") or ""
        self.edt_output_path.setText(curr_path)
        self.edt_output_path.editingFinished.connect(self._on_path_edited)
        row3.addWidget(self.edt_output_path, 1)

        self.btn_browse = QPushButton("Обзор…")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setFocusPolicy(Qt.NoFocus)
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        row3.addWidget(self.btn_browse)

        self.btn_reset_path = QPushButton("↺  Сбросить")
        self.btn_reset_path.setCursor(Qt.PointingHandCursor)
        self.btn_reset_path.setToolTip("Вернуть режим «рядом с видео»")
        self.btn_reset_path.setFocusPolicy(Qt.NoFocus)
        self.btn_reset_path.clicked.connect(self._on_reset_path_clicked)
        row3.addWidget(self.btn_reset_path)
        lay.addLayout(row3)

        parent_layout.addWidget(frame)

        # Активность поля ввода пути
        self._update_path_controls_enabled()


    def _build_menu(self):
        """Меню приложения (File / Help)"""
        menu = self.menuBar()
        # Help
        act_about = QAction("Справка", self)
        act_about.triggered.connect(self._show_about)
        menu.addAction(act_about)


    def _center_window(self):
        """Расположить окно по центру экрана."""
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center() if self.screen() else None
        if cp:
            qr.moveCenter(cp)
            self.move(qr.topLeft())


    def _apply_theme(self, theme: str):
        """Применить тему (dark/light) ко всему приложению."""
        self._current_theme = theme
        stylesheet = get_stylesheet(theme)
        self.setStyleSheet(stylesheet)
        # Иконка окна (рисуем программно — сиреневый круг с буквой)
        self._set_app_icon()
        # Обновляем цвета заголовков (Файлы к обработке, Журнал работы)
        self._apply_title_colors()
        # Обновляем тему для всех существующих элементов списка файлов
        for widget in self._item_map.values():
            widget.apply_theme(theme)


    def _set_app_icon(self):
        """
        Установить иконку окна приложения.
        Приоритет: resolve_app_icon_path (Gengar.ico в Portable/) → fallback на программную отрисовку.
        """
        icon_path = resolve_app_icon_path()
        if icon_path is not None:
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                self.setWindowIcon(icon)
                return

        # Fallback: рисуем программно, если иконки нет
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        gradient = QLinearGradient(0, 0, 64, 64)
        gradient.setColorAt(0, QColor("#C084FC"))
        gradient.setColorAt(1, QColor("#7E22CE"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(2, 2, 60, 60, 18, 18)
        painter.setPen(QColor("#FFFFFF"))
        f = painter.font()
        f.setBold(True)
        f.setPointSize(24)
        painter.setFont(f)
        painter.drawText(pix.rect(), Qt.AlignCenter, "♪")
        painter.end()
        self.setWindowIcon(QIcon(pix))


    def _show_ffmpeg_error(self, msg: str):
        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Critical)
        dlg.setWindowTitle("Не найден FFmpeg")
        dlg.setText("Для работы приложения требуется FFmpeg.")
        dlg.setInformativeText(msg)
        dlg.exec()

    def _update_files_count(self):
        n = len(self._added_files)
        self.lbl_files_count.setText(f"({n})")
        self.btn_extract.setEnabled(n > 0 and not self.extractor.is_running())
        self.btn_clear.setEnabled(n > 0 and not self.extractor.is_running())

    def _update_path_controls_enabled(self):
        """Включать/отключать поле ввода пути в зависимости от режима."""
        mode = self.cmb_output_mode.currentData()
        custom = mode == "custom"
        self.edt_output_path.setEnabled(custom)
        self.btn_browse.setEnabled(custom)
        # Кнопка "По умолчанию" активна если не source или путь задан
        has_custom = bool(self.config.get("custom_output_path")) or custom
        self.btn_reset_path.setEnabled(mode == "custom" or has_custom)


    def add_files(self, file_paths: List[str]):
        """
        Добавить файлы в список.
        Дубликаты игнорируются молча (с учётом регистра).
        """
        added_count = 0
        for fp in file_paths:
            norm = normalize_path(fp)
            if norm in self._added_files:
                continue
            if not Path(fp).exists() or not Path(fp).is_file():
                self._append_log(f"[ПРЕДУПРЕЖДЕНИЕ] Файл не найден, пропускаем: {fp}")
                continue
            ext = Path(fp).suffix.lower()
            if ext not in SUPPORTED_EXT:
                self._append_log(
                    f"[ИГНОР] Неподдерживаемый формат {ext or '(без расширения)'}: {Path(fp).name}"
                )
                continue

            # Добавляем
            self._added_files.add(norm)

            # Создаём айтем в списке
            list_item = QListWidgetItem(self.list_widget)
            list_item.setFlags(list_item.flags() & ~Qt.ItemIsSelectable)

            widget = FileItemWidget(fp, on_delete=self._remove_file_by_path, theme=self._current_theme)
            list_item.setSizeHint(widget.sizeHint())

            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)

            self._item_map[fp] = widget
            self._list_items[fp] = list_item
            added_count += 1

        if added_count > 0:
            self._append_log(f"Добавлено файлов в очередь: {added_count}")
        self._update_files_count()


    def _remove_file_by_path(self, file_path: str):
        """Удалить файл из списка по абсолютному пути."""
        norm = normalize_path(file_path)
        if norm not in self._added_files:
            return
        self._added_files.discard(norm)

        # Удалить из списка
        list_item = self._list_items.pop(file_path, None)
        if list_item:
            row = self.list_widget.row(list_item)
            if row >= 0:
                self.list_widget.takeItem(row)
        self._item_map.pop(file_path, None)

        self._append_log(f"Удалён из списка: {Path(file_path).name}")
        self._update_files_count()


    def _clear_list(self):
        """Очистить весь список файлов (если обработка не идёт)."""
        if self.extractor.is_running():
            QMessageBox.information(
                self, "Обработка выполняется",
                "Сейчас идёт обработка. После её завершения можно очистить список."
            )
            return
        self.list_widget.clear()
        self._added_files.clear()
        self._item_map.clear()
        self._list_items.clear()
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("0 / 0")
        self._append_log("Список файлов очищен")
        # Сбрасываем индикатор обратно в серый (очередь пустая)
        self._reset_indicator()
        self._update_files_count()

    def _on_extract_clicked(self):
        """Нажатие на кнопку «Извлечь звук»."""
        if self.extractor.is_running():
            return
        if not self._added_files:
            QMessageBox.information(
                self, "Список пуст",
                "Добавьте хотя бы один видеофайл перетаскиванием."
            )
            return
        # Проверка ffmpeg перед стартом
        ok, msg = check_ffmpeg_available()
        if not ok:
            self._show_ffmpeg_error(msg)
            return

        # Сбросить статусы всех файлов на PENDING
        for w in self._item_map.values():
            w.set_state(FileItemWidget.STATE_PENDING)

        self.progress_bar.setValue(0)
        total = len(self._item_map)
        self.lbl_progress.setText(f"0 / {total}")
        self.btn_extract.setEnabled(False)
        self.btn_clear.setEnabled(False)
        # Старт индикатора: моргание сиреневым
        self._start_indicator_blink()

        # Список файлов в порядке добавления (порядок по row)
        ordered_files = list(self._item_map.keys())

        # Запускаем в отдельном потоке
        self._thread = ExtractionThread(self.extractor, ordered_files, self)
        self._thread.start()


    def _on_theme_changed(self, _idx: int):
        theme = self.cmb_theme.currentData()
        self.config.set("theme", theme)
        self._apply_theme(theme)


    def _on_output_mode_changed(self, _idx: int):
        mode = self.cmb_output_mode.currentData()
        self.config.set("output_mode", mode)
        self._update_path_controls_enabled()


    def _on_browse_clicked(self):
        start_dir = self.edt_output_path.text() or str(Path.home())
        d = QFileDialog.getExistingDirectory(
            self, "Выберите папку для сохранения аудио", start_dir
        )
        if d:
            self.edt_output_path.setText(d)
            self.config.set("custom_output_path", d)
            # Переключаемся в custom, если ещё не
            if self.cmb_output_mode.currentData() != "custom":
                self.cmb_output_mode.setCurrentIndex(1)  # "custom"
            self._update_path_controls_enabled()


    def _on_path_edited(self):
        text = self.edt_output_path.text().strip()
        self.config.set("custom_output_path", text)


    def _on_reset_path_clicked(self):
        """Вернуть расположение по умолчаню """
        self.config.set("output_mode", "source")
        self.config.set("custom_output_path", "")
        self.edt_output_path.setText("")
        self.cmb_output_mode.setCurrentIndex(0)
        self._update_path_controls_enabled()



    def _connect_extractor_signals(self):
        self.extractor.log.connect(self._append_log)
        self.extractor.progress.connect(self._on_progress)
        self.extractor.file_started.connect(self._on_file_started)
        self.extractor.file_finished.connect(self._on_file_finished)
        self.extractor.all_finished.connect(self._on_all_finished)
        self.extractor.critical_error.connect(self._on_critical_error)


    def _append_log(self, text: str):
        """Добавить строку в журнал (запись в файл идёт внутри extractor, мы тут только обновляем UI если надо)."""
        pass


    def _on_progress(self, percent: int):
        self.progress_bar.setValue(max(0, min(100, percent)))


    def _on_file_started(self, file_path: str):
        w = self._item_map.get(file_path)
        if w:
            w.set_state(FileItemWidget.STATE_PROCESSING)
        processed = sum(
            1 for v in self._item_map.values()
            if v.state in (v.STATE_SUCCESS, v.STATE_ERROR)
        )
        total = len(self._item_map)
        self.lbl_progress.setText(f"{processed} / {total}")

    def _on_file_finished(self, file_path: str, success: bool, info: str):
        w = self._item_map.get(file_path)
        if w:
            if success:
                w.set_state(FileItemWidget.STATE_SUCCESS, info)
            else:
                w.set_state(FileItemWidget.STATE_ERROR, info)
        processed = sum(
            1 for v in self._item_map.values()
            if v.state in (v.STATE_SUCCESS, v.STATE_ERROR)
        )
        total = len(self._item_map)
        self.lbl_progress.setText(f"{processed} / {total}")


    def _on_all_finished(self, results: Dict):
        ok = sum(1 for s, _ in results.values() if s)
        fail = sum(1 for s, _ in results.values() if not s)
        self.progress_bar.setValue(100)
        self.btn_extract.setEnabled(len(self._added_files) > 0)
        self.btn_clear.setEnabled(True)
        self.lbl_progress.setText(f"{len(results)} / {len(results)}")

        # Индикатор: остановить моргание, сделать статичным сиреневым
        self._stop_indicator_blink()


    def _on_critical_error(self, msg: str):
        QMessageBox.critical(
            self, "Критическая ошибка",
            f"Во время работы возникла критическая ошибка:\n\n{msg}"
        )





    def _open_log_file(self):
        lp = self.extractor.log_file_path()
        if not lp.exists():

            try:
                lp.parent.mkdir(parents=True, exist_ok=True)
                lp.touch(exist_ok=True)
            except Exception:
                pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(lp)))

    def _open_config_dir(self):
        d = get_app_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def _show_about(self):
        QMessageBox.about(
            self, "О программе",
            """
<h3 style='color:#A855F7'>Audio Track Extractor</h3>
<p>Программа для извлечения всех аудиодорожек из видеофайлов<br>
без перекодирования (с fallback в WAV при несовместимости кодеков).</p>
<p><b>Основано на:</b></p>
<ul>
  <li>Python 3.10+</li>
  <li>PySide6 (Qt)</li>
  <li>FFmpeg / ffprobe</li>
</ul>
<p>GitHub: https://github.com/bitdonor 💜</p>
            """
        )


    def eventFilter(self, obj, event):
        # Защита от рекурсии (если внутри eventFilter генерируются новые события)
        if self._in_event_filter:
            return super().eventFilter(obj, event)

        try:
            self._in_event_filter = True


            try:
                event_type = event.type()
                is_mouse_press = False
                try:
                    if event_type == QEvent.Type.MouseButtonPress:
                        is_mouse_press = True
                except Exception:
                    pass
                if not is_mouse_press:
                    try:
                        if event_type == getattr(QEvent, "MouseButtonPress", None):
                            is_mouse_press = True
                    except Exception:
                        pass

                if is_mouse_press:
                    try:
                        btn = event.button()
                    except Exception:
                        btn = None
                    left_btn = False
                    try:
                        left_btn = (btn == Qt.MouseButton.LeftButton)
                    except Exception:
                        try:
                            left_btn = (btn == getattr(Qt, "LeftButton", None))
                        except Exception:
                            pass

                    if left_btn:
                        # Узнаём, на какой виджет реально пришёлся клик
                        w = getattr(event, "widget", None)
                        if callable(w):
                            try:
                                target = w()
                            except Exception:
                                target = None
                        else:
                            # Пытаемся найти виджет по позиции через childAt
                            target = None
                            try:
                                gpos = event.globalPosition()
                                gpos_pt = gpos.toPoint()
                                target = QApplication.widgetAt(gpos_pt)
                            except Exception:
                                pass

                        # Если клик НЕ по кнопке и НЕ по полю ввода — сбрасываем фокус
                        interactive = (QPushButton, QComboBox, QLineEdit, QListWidget,
                                       QPlainTextEdit)
                        should_clear = False
                        if target is None:
                            should_clear = True
                        elif not isinstance(target, interactive):
                            # Также игнорируем children кнопок (если клик по внутреннему лейблу)
                            parent = target.parent()
                            while parent is not None:
                                if isinstance(parent, (QPushButton, QComboBox, QLineEdit)):
                                    should_clear = False
                                    break
                                parent = parent.parent()
                            else:
                                should_clear = True

                        if should_clear:
                            focused = self.focusWidget()
                            if focused is not None:
                                # QLineEdit оставляем с фокусом — пользователь явно мог хотеть печатать
                                if not isinstance(focused, QLineEdit):
                                    try:
                                        focused.clearFocus()
                                    except Exception:
                                        pass
            except Exception:
                pass




            if obj is self.list_widget:
                # Безопасно определяем тип события (совместимо с разными версиями PySide6)
                event_type = event.type()
                is_key = False
                try:
                    # PySide6 новый стиль
                    if event_type == QEvent.Type.KeyPress:
                        is_key = True
                except Exception:
                    pass
                if not is_key:
                    try:
                        # Старый стиль / alias
                        if event_type == getattr(QEvent, "KeyPress", None):
                            is_key = True
                    except Exception:
                        pass

                if is_key:
                    # Безопасно получаем код клавиши
                    try:
                        key_val = event.key()
                    except Exception:
                        key_val = -1

                    delete_keys = set()
                    try:
                        delete_keys.add(Qt.Key.Key_Delete)
                    except Exception:
                        pass
                    try:
                        delete_keys.add(Qt.Key.Key_Backspace)
                    except Exception:
                        pass
                    # Альтернативные старые имена для совместимости
                    try:
                        delete_keys.add(getattr(Qt.Key, "Delete", -1))
                    except Exception:
                        pass
                    try:
                        delete_keys.add(getattr(Qt.Key, "Backspace", -1))
                    except Exception:
                        pass

                    if key_val in delete_keys:
                        if self.extractor.is_running():
                            return True
                        # Удаляем выбранные
                        for li in list(self.list_widget.selectedItems()):
                            for path, item in list(self._list_items.items()):
                                if item is li:
                                    self._remove_file_by_path(path)
                                    break
                        return True
        except Exception:
            # Защита: при любой ошибке передаём событие выше
            pass
        finally:
            self._in_event_filter = False

        return super().eventFilter(obj, event)



    def mousePressEvent(self, event):
        # Если кликнули не по интерактивному виджету (а по пустому окну) —
        # снимаем фокус с текущего сфокусированного виджета (включая кнопки).
        # Это дублирование страховки на случай если eventFilter не сработал.
        focused = self.focusWidget()
        if focused is not None:
            if isinstance(focused, (QPushButton, QComboBox, QProgressBar, QListWidget,
                                    QPlainTextEdit)):
                focused.clearFocus()
        super().mousePressEvent(event)




    def closeEvent(self, event):
        if self.extractor.is_running():
            reply = QMessageBox.question(
                self, "Подтверждение выхода",
                "Сейчас идёт обработка файлов. Вы точно хотите выйти?\n"
                "Текущий прогресс будет потерян.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            # Пытаемся остановить
            self.extractor.stop()
            if self._thread:
                self._thread.quit()
                self._thread.wait(3000)
        # Сохранить настройки на всякий случай
        self.config.save()
        event.accept()


