"""Worker thread berbasis QThread untuk menjalankan operasi core/ di latar belakang.

Menjamin antarmuka PyQt6 tetap responsif (bebas Not Responding) saat memindai folder,
menghitung hash SHA-256, maupun memindahkan file.
"""

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from core.duplicate_finder import DuplicateFinder
from core.models import FilePlanItem
from core.organizer import SafeFileOrganizer
from core.scanner import FolderScanner


class ScanWorker(QThread):
    """Thread pekerja untuk menjalankan pemindaian folder dan deteksi duplikat.

    Signals:
        progress_updated (int, str): Persentase progres (0-100) dan pesan status.
        scan_finished (list, dict): Daftar `FilePlanItem` dan dictionary ringkasan ruang hemat.
        error_occurred (str): Pesan kesalahan jika terjadi kegagalan tak terduga.
    """

    progress_updated = pyqtSignal(int, str)
    scan_finished = pyqtSignal(list, dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        folder_path: str,
        rules_path: str = "data/default_rules.json",
        parent: QObject | None = None,
    ) -> None:
        """Menyiapkan worker pemindaian untuk alamat folder target.

        Args:
            folder_path: Alamat folder yang akan dipindai.
            rules_path: Alamat file konfigurasi aturan kategori JSON.
            parent: Objek induk QObject (opsional).
        """
        super().__init__(parent)
        self.folder_path: str = folder_path
        self.rules_path: str = rules_path

    def run(self) -> None:
        """Mengeksekusi tahapan pemindaian, cek duplikat, cek installer usang, dan hitung ruang."""
        try:
            scanner = FolderScanner(rules_path=self.rules_path)
            duplicate_finder = DuplicateFinder()

            self.progress_updated.emit(0, "Memulai pemindaian isi folder...")
            items = scanner.scan_directory(
                self.folder_path,
                progress_callback=self.progress_updated.emit,
            )

            if items:
                items = duplicate_finder.mark_duplicates(
                    items,
                    progress_callback=self.progress_updated.emit,
                )
                items = duplicate_finder.detect_obsolete_installers(items)

            wasted_space_info = duplicate_finder.calculate_wasted_space(items)
            self.progress_updated.emit(100, f"Pemindaian selesai ({len(items)} file ditemukan).")
            self.scan_finished.emit(items, wasted_space_info)
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(f"Terjadi kesalahan saat memindai folder: {exc}")


class OrganizeWorker(QThread):
    """Thread pekerja untuk mengeksekusi perapian file, Undo, atau pembersihan karantina.

    Signals:
        progress_updated (int, str): Persentase progres (0-100) dan pesan status.
        operation_finished (int, list): Jumlah file berhasil diproses dan daftar pesan error.
        error_occurred (str): Pesan kesalahan jika terjadi kegagalan tak terduga.
    """

    progress_updated = pyqtSignal(int, str)
    operation_finished = pyqtSignal(int, list)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        mode: str = "organize",
        items: list[FilePlanItem] | None = None,
        base_folder_path: str = "",
        undo_log_path: str = "data/undo_history.json",
        parent: QObject | None = None,
    ) -> None:
        """Menyiapkan worker untuk mode aksi 'organize', 'undo', atau 'empty_quarantine'.

        Args:
            mode: Jenis operasi ('organize', 'undo', atau 'empty_quarantine').
            items: Daftar `FilePlanItem` yang akan dieksekusi (untuk mode 'organize').
            base_folder_path: Alamat folder utama (untuk mode 'empty_quarantine').
            undo_log_path: Alamat file JSON riwayat transaksi Undo.
            parent: Objek induk QObject (opsional).
        """
        super().__init__(parent)
        self.mode: str = mode
        self.items: list[FilePlanItem] = items or []
        self.base_folder_path: str = base_folder_path
        self.undo_log_path: str = undo_log_path

    def run(self) -> None:
        """Menjalankan metode pada `SafeFileOrganizer` sesuai mode operasi yang dipilih."""
        try:
            organizer = SafeFileOrganizer(undo_log_path=self.undo_log_path)

            if self.mode == "organize":
                self.progress_updated.emit(0, "Memulai proses perapian file...")
                count, errors = organizer.execute_plan(
                    self.items,
                    progress_callback=self.progress_updated.emit,
                )
                self.progress_updated.emit(100, "Proses perapian selesai.")
                self.operation_finished.emit(count, errors)

            elif self.mode == "undo":
                self.progress_updated.emit(30, "Mengembalikan file ke posisi semula...")
                count, errors = organizer.undo_last_operation()
                self.progress_updated.emit(100, "Proses pembatalan (Undo) selesai.")
                self.operation_finished.emit(count, errors)

            elif self.mode == "empty_quarantine":
                self.progress_updated.emit(30, "Memindahkan isi karantina ke Sampah (Recycle Bin)...")
                count, errors = organizer.empty_quarantine_to_trash(self.base_folder_path)
                self.progress_updated.emit(100, "Pembersihan folder karantina selesai.")
                self.operation_finished.emit(count, errors)

            else:
                self.error_occurred.emit(f"Mode operasi tidak dikenal: {self.mode}")
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(f"Terjadi kesalahan saat memproses file: {exc}")
