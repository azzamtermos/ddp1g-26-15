"""Entry point utama aplikasi Rapihin Aja.

Menginisialisasi QApplication, memuat lembar gaya terpusat (ui/styles.qss),
memasang identitas & ikon aplikasi, dan menampilkan jendela utama (MainWindow).
"""

import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.paths import get_icon_path, load_stylesheet_text
from ui.main_window import MainWindow


def load_stylesheet(app: QApplication) -> None:
    """Memuat lembar gaya QSS dari `ui/styles.qss` (mendukung mode PyInstaller) ke aplikasi.

    Args:
        app: Instance `QApplication` yang sedang berjalan.
    """
    stylesheet = load_stylesheet_text("ui/styles.qss")
    if stylesheet:
        app.setStyleSheet(stylesheet)


def main() -> int:
    """Menjalankan event loop utama aplikasi PyQt6."""
    app = QApplication(sys.argv)
    app.setApplicationName("Rapihin Aja")
    app.setApplicationDisplayName("Rapihin Aja")
    app.setDesktopFileName("rapihin-aja")

    icon_path = get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    load_stylesheet(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
