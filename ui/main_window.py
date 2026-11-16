"""Jendela utama (MainWindow) untuk aplikasi Smart File Organizer.

Menyatukan komponen DropZoneWidget, kartu progres dan estimasi ruang hemat,
PreviewTableWidget, serta tombol aksi dengan worker thread (QThread).
"""

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.models import FilePlanItem
from ui.widgets import DropZoneWidget, PreviewTableWidget
from ui.worker import OrganizeWorker, ScanWorker


class MainWindow(QMainWindow):
    """Jendela utama aplikasi Smart File Organizer dengan alur pemindaian otomatis."""

    def __init__(self) -> None:
        """Menginisialisasi tata letak antarmuka, sinyal, dan status awal komponen."""
        super().__init__()
        self.setWindowTitle("Smart File Organizer")
        self.setMinimumSize(920, 660)

        self.current_folder: str = ""
        self.current_items: list[FilePlanItem] = []
        self.scan_worker: ScanWorker | None = None
        self.organize_worker: OrganizeWorker | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Menyusun komponen visual utama dengan jarak (spacing) dan margin yang lega."""
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(14)

        # 1. Header Judul Aplikasi
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        self.title_label = QLabel("Smart File Organizer")
        self.title_label.setObjectName("AppTitleLabel")

        self.subtitle_label = QLabel(
            "Rapikan folder berantakan, amankan file kembar ke karantina, dan batalkan kapan saja dengan 1 klik."
        )
        self.subtitle_label.setObjectName("AppSubtitleLabel")

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        main_layout.addLayout(header_layout)

        # 2. Area Drag-and-Drop (Fokus Visual Utama)
        self.drop_zone = DropZoneWidget(self)
        main_layout.addWidget(self.drop_zone)

        # 3. Kartu Ringkasan & Bar Progres Real-Time
        self.summary_card = QFrame(self)
        self.summary_card.setObjectName("SummaryCard")
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        summary_layout.setSpacing(8)

        info_row = QHBoxLayout()
        self.summary_info_label = QLabel(
            "Ringkasan: 0 file ditemukan | Duplikat: 0 | Installer Usang: 0 | Potensi Ruang Hemat: 0 B"
        )
        self.summary_info_label.setObjectName("SummaryInfoLabel")

        self.status_progress_label = QLabel("Siap memindai folder.")
        self.status_progress_label.setObjectName("StatusProgressLabel")
        self.status_progress_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        info_row.addWidget(self.summary_info_label, stretch=3)
        info_row.addWidget(self.status_progress_label, stretch=2)

        self.progress_bar = QProgressBar(self.summary_card)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        summary_layout.addLayout(info_row)
        summary_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.summary_card)

        # 4. Tabel Pratinjau Rencana Perapian
        self.preview_table = PreviewTableWidget(self)
        main_layout.addWidget(self.preview_table, stretch=1)

        # 5. Bar Tombol Tindakan Ramah Pengguna
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)

        self.refresh_button = QPushButton("Pindai Ulang (Refresh)")
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.setEnabled(False)

        self.undo_button = QPushButton("Batalkan (Undo)")
        self.undo_button.setObjectName("SecondaryButton")
        self.undo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_button.setEnabled(True)

        self.empty_quarantine_button = QPushButton("Bersihkan Karantina ke Sampah")
        self.empty_quarantine_button.setObjectName("QuarantineButton")
        self.empty_quarantine_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_quarantine_button.setEnabled(False)

        self.organize_button = QPushButton("Rapikan Sekarang")
        self.organize_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.organize_button.setEnabled(False)

        action_layout.addWidget(self.refresh_button)
        action_layout.addWidget(self.undo_button)
        action_layout.addWidget(self.empty_quarantine_button)
        action_layout.addStretch(1)
        action_layout.addWidget(self.organize_button)

        main_layout.addLayout(action_layout)

    def _connect_signals(self) -> None:
        """Menghubungkan sinyal dari widget dan tombol ke slot penangan di MainWindow."""
        self.drop_zone.folder_selected.connect(self._on_folder_selected)
        self.refresh_button.clicked.connect(self.start_scan)
        self.organize_button.clicked.connect(self.start_organize)
        self.undo_button.clicked.connect(self.start_undo)
        self.empty_quarantine_button.clicked.connect(self.start_empty_quarantine)

    def _on_folder_selected(self, folder_path: str) -> None:
        """Menyimpan alamat folder terpilih dan langsung menjalankan pemindaian otomatis."""
        self.current_folder = folder_path
        self.refresh_button.setEnabled(True)
        self.empty_quarantine_button.setEnabled(True)
        self.start_scan()

    def _set_controls_busy(self, busy: bool) -> None:
        """Mengatur status aktif/nonaktif tombol selama proses background thread berjalan."""
        self.drop_zone.browse_button.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy and bool(self.current_folder))
        self.organize_button.setEnabled(not busy and bool(self.current_items))
        self.undo_button.setEnabled(not busy)
        self.empty_quarantine_button.setEnabled(not busy and bool(self.current_folder))

    def start_scan(self) -> None:
        """Memulai ScanWorker di background thread untuk memindai folder yang sedang aktif."""
        if not self.current_folder:
            return
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return

        self._set_controls_busy(True)
        self.progress_bar.setValue(0)
        self.status_progress_label.setText("Memindai folder...")

        self.scan_worker = ScanWorker(folder_path=self.current_folder, parent=self)
        self.scan_worker.progress_updated.connect(self._on_worker_progress)
        self.scan_worker.scan_finished.connect(self._on_scan_finished)
        self.scan_worker.error_occurred.connect(self._on_worker_error)
        self.scan_worker.start()

    def _on_worker_progress(self, percent: int, message: str) -> None:
        """Memperbarui nilai QProgressBar dan teks status secara real-time."""
        self.progress_bar.setValue(percent)
        self.status_progress_label.setText(message)

    def _on_scan_finished(
        self,
        items: list[FilePlanItem],
        wasted_space_info: dict[str, Any],
    ) -> None:
        """Menampilkan daftar hasil pemindaian ke tabel pratinjau dan ringkasan ruang hemat."""
        self.current_items = items
        self.preview_table.populate_items(items)

        dup_count = wasted_space_info.get("duplicate_count", 0)
        obs_count = wasted_space_info.get("obsolete_count", 0)
        formatted_size = wasted_space_info.get("formatted_size", "0 B")

        self.summary_info_label.setText(
            f"Ringkasan: {len(items)} file ditemukan | "
            f"Duplikat: {dup_count} | "
            f"Installer Usang: {obs_count} | "
            f"Potensi Ruang Hemat: {formatted_size}"
        )
        self._set_controls_busy(False)

    def start_organize(self) -> None:
        """Memulai OrganizeWorker untuk merapikan file ke kategori tujuan dan karantina."""
        if not self.current_items:
            return
        if self.organize_worker is not None and self.organize_worker.isRunning():
            return

        self._set_controls_busy(True)
        self.organize_worker = OrganizeWorker(
            mode="organize",
            items=self.current_items,
            base_folder_path=self.current_folder,
            parent=self,
        )
        self.organize_worker.progress_updated.connect(self._on_worker_progress)
        self.organize_worker.operation_finished.connect(self._on_organize_finished)
        self.organize_worker.error_occurred.connect(self._on_worker_error)
        self.organize_worker.start()

    def _on_organize_finished(self, success_count: int, errors: list[str]) -> None:
        """Menangani penyelesaian proses perapian dan memindai ulang isi folder."""
        self._set_controls_busy(False)
        msg = f"Berhasil merapikan {success_count} file."
        if errors:
            detail = "\n".join(errors[:5])
            QMessageBox.warning(
                self,
                "Perapian Selesai dengan Catatan",
                f"{msg}\n\nBeberapa file dilewati:\n{detail}",
            )
        else:
            QMessageBox.information(self, "Berhasil Dirapikan", msg)

        if self.current_folder:
            self.start_scan()

    def start_undo(self) -> None:
        """Memulai OrganizeWorker dalam mode 'undo' untuk memulihkan transaksi terakhir."""
        if self.organize_worker is not None and self.organize_worker.isRunning():
            return

        self._set_controls_busy(True)
        self.organize_worker = OrganizeWorker(
            mode="undo",
            base_folder_path=self.current_folder,
            parent=self,
        )
        self.organize_worker.progress_updated.connect(self._on_worker_progress)
        self.organize_worker.operation_finished.connect(self._on_undo_finished)
        self.organize_worker.error_occurred.connect(self._on_worker_error)
        self.organize_worker.start()

    def _on_undo_finished(self, restored_count: int, errors: list[str]) -> None:
        """Menangani penyelesaian proses Undo dan memperbarui tampilan tabel."""
        self._set_controls_busy(False)
        if restored_count > 0:
            msg = f"Berhasil mengembalikan {restored_count} file ke lokasi semula."
            if errors:
                detail = "\n".join(errors[:5])
                QMessageBox.warning(
                    self,
                    "Undo Selesai dengan Catatan",
                    f"{msg}\n\nCatatan:\n{detail}",
                )
            else:
                QMessageBox.information(self, "Undo Berhasil", msg)
        else:
            info_text = "\n".join(errors) if errors else "Tidak ada transaksi untuk dibatalkan."
            QMessageBox.information(self, "Informasi Undo", info_text)

        if self.current_folder:
            self.start_scan()

    def start_empty_quarantine(self) -> None:
        """Memindahkan isi folder _Karantina_Duplikat ke Sampah (Recycle Bin) setelah konfirmasi."""
        if not self.current_folder:
            return
        if self.organize_worker is not None and self.organize_worker.isRunning():
            return

        reply = QMessageBox.question(
            self,
            "Konfirmasi Bersihkan Karantina",
            "Apakah Anda yakin ingin memindahkan seluruh file di dalam folder "
            "'_Karantina_Duplikat' ke Sampah (Recycle Bin)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._set_controls_busy(True)
        self.organize_worker = OrganizeWorker(
            mode="empty_quarantine",
            base_folder_path=self.current_folder,
            parent=self,
        )
        self.organize_worker.progress_updated.connect(self._on_worker_progress)
        self.organize_worker.operation_finished.connect(self._on_empty_quarantine_finished)
        self.organize_worker.error_occurred.connect(self._on_worker_error)
        self.organize_worker.start()

    def _on_empty_quarantine_finished(self, trashed_count: int, errors: list[str]) -> None:
        """Menampilkan hasil pembersihan folder karantina ke pengguna."""
        self._set_controls_busy(False)
        if trashed_count > 0:
            msg = f"Berhasil memindahkan {trashed_count} file dari karantina ke Sampah (Recycle Bin)."
            if errors:
                detail = "\n".join(errors[:5])
                QMessageBox.warning(
                    self,
                    "Pembersihan Selesai dengan Catatan",
                    f"{msg}\n\nCatatan:\n{detail}",
                )
            else:
                QMessageBox.information(self, "Karantina Dibersihkan", msg)
        else:
            info_text = "\n".join(errors) if errors else "Folder karantina sudah kosong."
            QMessageBox.information(self, "Informasi Karantina", info_text)

    def _on_worker_error(self, error_message: str) -> None:
        """Menampilkan pesan error ramah pengguna apabila thread mengalami kendala."""
        self._set_controls_busy(False)
        self.status_progress_label.setText("Terjadi kendala.")
        QMessageBox.critical(self, "Kendala Proses", error_message)
