import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont, QIcon


from extractor import (
    ConfigManager,
    check_ffmpeg_available,
    get_app_dir,
    resolve_app_icon_path,
)
from ui import MainWindow


def _set_app_icon(app: QApplication):

    icon_path = resolve_app_icon_path()

    if icon_path is not None:
        icon = QIcon(str(icon_path))

        if not icon.isNull():
            app.setWindowIcon(icon)
            return

    from PySide6.QtGui import (
        QPixmap,
        QPainter,
        QLinearGradient,
        QBrush,
        QColor,
        Qt,
    )

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

    app.setWindowIcon(QIcon(pix))


def main() -> int:
    # Создаём экземпляр Qt-приложения
    app = QApplication(sys.argv)

    app.setApplicationName("Audio Track Extractor")
    app.setOrganizationName("SnusScientist")

    if sys.platform.startswith("win"):
        try:
            import ctypes

            app_id = "SnusScientist.AudioTrackExtractor.v1"

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                app_id
            )
        except Exception:
            pass

    _set_app_icon(app)

    default_font = QFont()
    default_font.setPointSize(default_font.pointSize() + 1)
    app.setFont(default_font)

    config = ConfigManager()

    ok, _msg = check_ffmpeg_available()

    if not ok:
        pass


    window = MainWindow(config)
    window.show()
    screen = window.screen()

    if screen is None:
        screen = app.primaryScreen()

    if screen is not None:
        screen_geometry = screen.availableGeometry()
        window_geometry = window.frameGeometry()

        window_geometry.moveCenter(screen_geometry.center())
        window.move(window_geometry.topLeft())


    return app.exec()


if __name__ == "__main__":
    sys.exit(main())