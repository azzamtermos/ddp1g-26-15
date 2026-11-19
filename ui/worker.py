"""Worker thread berbasis QThread untuk menjalankan operasi core/ di latar belakang.

Menjamin antarmuka PyQt6 tetap responsif saat memeriksa isi folder,
mendeteksi file duplikat, maupun memindahkan file.
"""

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from core.duplicate_finder import DuplicateFinder
from core.models import FilePlanItem
from core.organizer import SafeFileOrganizer
from core.scanner import FolderScanner


class ScanWorker(QThread):
    """Thread pekerja untuk menjalankan pemeriksaan folder dan deteksi duplikat.

    Signals:
        progress_updated (int, str): Persentase progres (0-100) dan pesan status.
        scan_finished (list, dict): Daftar `FilePlanItem` dan ringkasan penghematan ruang.
        error_occurred (str): Pesan ramah pengguna jika terjadi kendala.
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
        """Menyiapkan worker pemeriksaan untuk alamat folder target.

        Args:
            folder_path: Alamat folder yang akan diperiksa.
            rules_path: Alamat file konfigurasi aturan kategori JSON.
            parent: Objek induk QObject (opsional).
        """
        super().__init__(parent)
        self.folder_path: str = folder_path
        self.rules_path: str = rules_path

    def run(self) -> None:
        """Menjalankan tahapan pemeriksaan folder, cek duplikat, dan hitung penghematan ruang."""
        try:
            scanner = FolderScanner(rules_path=self.rules_path)
            duplicate_finder = DuplicateFinder()

            self.progress_updated.emit(0, "Sedang memeriksa isi folder...")
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
            if items:
                self.progress_updated.emit(
                    100, f"Pemeriksaan selesai ({len(items)} file ditemukan)."
                )
            else:
                self.progress_updated.emit(
                    100, "Folder sudah bersih, tidak ada file di tingkat utama."
                )
            self.scan_finished.emit(items, wasted_space_info)
        except Exception:  # noqa: BLE001
            self.error_occurred.emit(
                "Maaf, folder tidak dapat diperiksa saat ini. "
                "Pastikan folder masih tersedia dan dapat dibuka."
            )


class OrganizeWorker(QThread):
    """Thread pekerja untuk menjalankan perapian file, pembatalan (Undo), atau pembersihan karantina.

    Signals:
        progress_updated (int, str): Persentase progres (0-100) dan pesan status.
        operation_finished (int, list): Jumlah file berhasil diproses dan daftar catatan.
        error_occurred (str): Pesan ramah pengguna jika terjadi kendala.
    """

    progress_updated = pyqtSignal(int, str)
    operation_finished = pyqtSignal(int, list)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        mode: str = "organize",
        items: list[FilePlanItem] | None = None,
        base_folder_path: str = "",
        undo_log_path: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Menyiapkan worker untuk mode aksi 'organize', 'undo', atau 'empty_quarantine'.

        Args:
            mode: Jenis operasi ('organize', 'undo', atau 'empty_quarantine').
            items: Daftar `FilePlanItem` yang akan dieksekusi (untuk mode 'organize').
            base_folder_path: Alamat folder utama (untuk mode 'empty_quarantine').
            undo_log_path: Alamat file JSON riwayat transaksi Undo (opsional).
            parent: Objek induk QObject (opsional).
        """
        super().__init__(parent)
        self.mode: str = mode
        self.items: list[FilePlanItem] = items or []
        self.base_folder_path: str = base_folder_path
        self.undo_log_path: str | None = undo_log_path

    def run(self) -> None:
        """Menjalankan metode pada `SafeFileOrganizer` sesuai mode aksi yang dipilih."""
        try:
            organizer = SafeFileOrganizer(undo_log_path=self.undo_log_path)

            if self.mode == "organize":
                self.progress_updated.emit(0, "Sedang merapikan file...")
                count, errors = organizer.execute_plan(
                    self.items,
                    progress_callback=self.progress_updated.emit,
                )
                self.progress_updated.emit(100, "Perapian file selesai.")
                self.operation_finished.emit(count, errors)

            elif self.mode == "undo":
                self.progress_updated.emit(
                    30, "Sedang mengembalikan file ke lokasi dan nama aslinya..."
                )
                count, errors = organizer.undo_last_operation()
                self.progress_updated.emit(100, "Pembatalan selesai.")
                self.operation_finished.emit(count, errors)

            elif self.mode == "empty_quarantine":
                self.progress_updated.emit(
                    30, "Sedang memindahkan file karantina ke Tempat Sampah..."
                )
                count, errors = organizer.empty_quarantine_to_trash(self.base_folder_path)
                self.progress_updated.emit(100, "Pembersihan folder karantina selesai.")
                self.operation_finished.emit(count, errors)

            else:
                self.error_occurred.emit(
                    "Tindakan tidak dapat dijalankan. Silakan coba lagi."
                )
        except Exception:  # noqa: BLE001
            self.error_occurred.emit(
                "Maaf, terjadi kendala saat memproses file. "
                "Pastikan tidak ada file yang sedang terbuka di aplikasi lain."
            )
