"""Entry point utama aplikasi Smart File Organizer.

Menginisialisasi QApplication, memuat lembar gaya terpusat (ui/styles.qss),
dan menampilkan jendela utama (MainWindow).
"""

from pathlib import Path
import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def load_stylesheet(app: QApplication) -> None:
    """Memuat file lembar gaya QSS dari `ui/styles.qss` dan menerapkannya ke aplikasi.

    Args:
        app: Instance `QApplication` yang sedang berjalan.
    """
    base_dir = Path(__file__).resolve().parent
    qss_path = base_dir / "ui" / "styles.qss"
    if qss_path.exists() and qss_path.is_file():
        try:
            stylesheet = qss_path.read_text(encoding="utf-8")
            app.setStyleSheet(stylesheet)
        except OSError:
            pass


def main() -> int:
    """Menjalankan event loop utama aplikasi PyQt6."""
    app = QApplication(sys.argv)
    app.setApplicationName("Smart File Organizer")
    load_stylesheet(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
