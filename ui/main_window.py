"""Jendela utama (MainWindow) untuk aplikasi Rapihin Aja.

Menyatukan fase Welcome dan Active dalam gaya Windows 11 Fluent + Notion Minimalist:
area pemilihan folder adaptif (`CollapsibleDropZoneWidget`), strip progres tipis
(`FluentProgressStrip`), ringkasan dinamis, tab filter pill (`FilterBarWidget`),
persetujuan rename (`RenameBannerWidget`), dan tabel pratinjau (`PreviewTableWidget`).
"""

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.models import FilePlanItem
from core.paths import get_icon_path
from core.safety import validate_target_directory
from ui.widgets import (
    CollapsibleDropZoneWidget,
    EmptyStateWidget,
    FilterBarWidget,
    FluentProgressStrip,
    PreviewTableWidget,
    RenameBannerWidget,
)
from ui.worker import OrganizeWorker, ScanWorker


class MainWindow(QMainWindow):
    """Jendela utama aplikasi Rapihin Aja dengan progresif disclosure Welcome dan Active."""

    def __init__(self) -> None:
        """Menginisialisasi tata letak antarmuka, sinyal, dan status awal Welcome State."""
        super().__init__()
        self.setWindowTitle("Rapihin Aja")
        self.setMinimumSize(940, 660)

        icon_path = get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self.current_folder: str = ""
        self.current_items: list[FilePlanItem] = []
        self._last_wasted_space_info: dict[str, Any] = {}
        self._last_organize_summary: dict[str, int] = {}
        self._is_busy: bool = False
        self.scan_worker: ScanWorker | None = None
        self.organize_worker: OrganizeWorker | None = None

        self._setup_ui()
        self._connect_signals()
        self._set_workspace_active(False)

    def _setup_ui(self) -> None:
        """Menyusun komponen visual utama dengan margin lega dan hierarki fokus bersih."""
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(12)

        # 1. Header Judul Aplikasi
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 2)
        header_layout.setSpacing(3)

        self.title_label = QLabel("Rapihin Aja", self)
        self.title_label.setObjectName("AppTitleLabel")

        self.subtitle_label = QLabel(
            "Rapikan folder berantakan, amankan file kembar ke karantina, dan batalkan kapan saja dengan 1 klik.",
            self,
        )
        self.subtitle_label.setObjectName("AppSubtitleLabel")

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        main_layout.addLayout(header_layout)

        # Spacer Welcome Atas (aktif hanya saat Welcome State)
        self.welcome_top_spacer = QWidget(self)
        self.welcome_top_spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        main_layout.addWidget(self.welcome_top_spacer, stretch=1)

        # 2. Area Drag-and-Drop Adaptif (Hero saat Welcome -> Toolbar Kompak saat Active)
        self.drop_zone = CollapsibleDropZoneWidget(self)
        main_layout.addWidget(self.drop_zone)

        # 3. Strip Progres Tipis (Kontekstual, tersembunyi ketika tidak ada operasi)
        self.progress_strip = FluentProgressStrip(self)
        main_layout.addWidget(self.progress_strip)

        # 4. Kontainer Workspace Aktif (Ringkasan, Filter Tab, Banner Rename, Tabel)
        self.workspace_container = QWidget(self)
        workspace_layout = QVBoxLayout(self.workspace_container)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(10)

        self.summary_card = QFrame(self.workspace_container)
        self.summary_card.setObjectName("SummaryCard")
        summary_layout = QHBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(14, 10, 14, 10)
        summary_layout.setSpacing(8)

        self.summary_info_label = QLabel(
            "Memeriksa isi folder...",
            self.summary_card,
        )
        self.summary_info_label.setObjectName("SummaryInfoLabel")
        self.summary_info_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_info_label, stretch=1)
        workspace_layout.addWidget(self.summary_card)

        self.filter_bar = FilterBarWidget(self.workspace_container)
        workspace_layout.addWidget(self.filter_bar)

        self.rename_banner = RenameBannerWidget(self.workspace_container)
        workspace_layout.addWidget(self.rename_banner)

        self.content_stack = QStackedWidget(self.workspace_container)
        self.preview_table = PreviewTableWidget(self)
        self.empty_state_widget = EmptyStateWidget(self)
        self.content_stack.addWidget(self.preview_table)
        self.content_stack.addWidget(self.empty_state_widget)
        self.content_stack.setCurrentIndex(0)
        workspace_layout.addWidget(self.content_stack, stretch=1)

        main_layout.addWidget(self.workspace_container, stretch=1)

        # Spacer Welcome Bawah (aktif hanya saat Welcome State)
        self.welcome_bottom_spacer = QWidget(self)
        self.welcome_bottom_spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        main_layout.addWidget(self.welcome_bottom_spacer, stretch=2)

        # 5. Footer Tindakan (Hanya 1 Tombol CTA Biru Dominan di Kanan)
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 2, 0, 0)
        action_layout.setSpacing(10)

        self.refresh_button = QPushButton("Pindai Ulang", self)
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.setEnabled(False)

        self.undo_button = QPushButton("Batalkan Perapian Terakhir (Undo)", self)
        self.undo_button.setObjectName("SecondaryButton")
        self.undo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_button.setEnabled(True)

        self.empty_quarantine_button = QPushButton("Bersihkan Karantina ke Sampah", self)
        self.empty_quarantine_button.setObjectName("QuarantineButton")
        self.empty_quarantine_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_quarantine_button.setEnabled(False)

        self.organize_button = QPushButton("Rapikan Sekarang", self)
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
        self.filter_bar.filter_changed.connect(self.preview_table.set_filter_mode)
        self.rename_banner.accept_all_clicked.connect(
            lambda: self.preview_table.set_all_renames_approved(True)
        )
        self.rename_banner.reject_all_clicked.connect(
            lambda: self.preview_table.set_all_renames_approved(False)
        )
        self.preview_table.rename_approval_changed.connect(self._sync_rename_banner)
        self.preview_table.selection_changed.connect(self._on_selection_changed)
        self.refresh_button.clicked.connect(self.start_scan)
        self.organize_button.clicked.connect(self.start_organize)
        self.undo_button.clicked.connect(self.start_undo)
        self.empty_quarantine_button.clicked.connect(self.start_empty_quarantine)

    def _set_workspace_active(self, active: bool) -> None:
        """Mengatur transisi antarmuka antara Welcome State dan Active State."""
        self.welcome_top_spacer.setVisible(not active)
        self.welcome_bottom_spacer.setVisible(not active)
        self.workspace_container.setVisible(active)
        self.drop_zone.set_compact(active)

        self.refresh_button.setVisible(active)
        self.empty_quarantine_button.setVisible(active)
        self.organize_button.setVisible(active)
        self.undo_button.setText(
            "Batalkan (Undo)" if active else "Batalkan Perapian Terakhir (Undo)"
        )

    def _on_folder_selected(self, folder_path: str) -> None:
        """Memvalidasi keamanan folder terpilih lalu langsung memindai jika aman."""
        is_safe, warning_message = validate_target_directory(folder_path)
        if not is_safe:
            QMessageBox.warning(self, "Folder Tidak Dapat Dipilih", warning_message)
            self.drop_zone.set_selected_folder_text(self.current_folder)
            return

        self.current_folder = folder_path
        self.drop_zone.set_selected_folder_text(folder_path)
        self._set_workspace_active(True)
        self.refresh_button.setEnabled(True)
        self.empty_quarantine_button.setEnabled(True)
        self.start_scan()

    def _sync_rename_banner(self) -> None:
        """Menyelaraskan informasi dan visibilitas banner massal usulan nama baru."""
        total, approved = self.preview_table.get_rename_suggestion_counts()
        self.rename_banner.update_counts(total, approved)

    def _on_selection_changed(self) -> None:
        """Memperbarui ringkasan dinamis dan status tombol eksekusi saat centang berubah."""
        self._update_dynamic_summary()
        self._sync_organize_button_state()

    def _update_dynamic_summary(self) -> None:
        """Menyusun teks ringkasan ramah pengguna yang selalu sinkron di seluruh tab."""
        if not self.current_folder:
            return

        summary = self.preview_table.get_selection_summary()
        if summary["total_files"] == 0:
            self.summary_info_label.setText(
                "Tidak ada file di tingkat utama folder ini yang perlu dirapikan."
            )
            return

        if summary["selected_total"] == 0:
            parts = [
                "0 file dipilih untuk dirapikan",
                "Centang minimal 1 file untuk melanjutkan",
            ]
            if summary["manual_check_count"] > 0:
                parts.append(f"{summary['manual_check_count']} perlu cek manual")
            self.summary_info_label.setText("  •  ".join(parts))
            return

        parts: list[str] = []
        if summary["selected_ready"] > 0:
            parts.append(f"{summary['selected_ready']} file siap dirapikan")
        if summary["selected_obsolete"] > 0:
            parts.append(f"{summary['selected_obsolete']} installer usang")
        if summary["selected_duplicates"] > 0:
            parts.append(f"{summary['selected_duplicates']} duplikat diamankan")
        if summary["manual_check_count"] > 0:
            parts.append(f"{summary['manual_check_count']} perlu cek manual")
        if summary["unchecked_count"] > 0:
            parts.append(f"{summary['unchecked_count']} dikecualikan")

        total_bytes = self._last_wasted_space_info.get("total_bytes", 0)
        formatted_size = self._last_wasted_space_info.get("formatted_size", "0 B")
        if isinstance(total_bytes, int) and total_bytes > 0:
            parts.append(f"Potensi hemat ruang: {formatted_size}")

        self.summary_info_label.setText("  •  ".join(parts))

    def _sync_organize_button_state(self) -> None:
        """Menyelaraskan teks penghitung (N) dan status tombol eksekusi lintas semua tab."""
        selected_count = len(self.preview_table.get_selected_items())
        if selected_count > 0:
            self.organize_button.setText(f"Rapikan Sekarang ({selected_count})")
        else:
            self.organize_button.setText("Rapikan Sekarang")

        scan_busy = self.scan_worker is not None and self.scan_worker.isRunning()
        org_busy = self.organize_worker is not None and self.organize_worker.isRunning()
        if self._is_busy or scan_busy or org_busy:
            self.organize_button.setEnabled(False)
            return
        self.organize_button.setEnabled(selected_count > 0)

    def _set_controls_busy(self, busy: bool) -> None:
        """Mengatur status aktif/nonaktif kontrol selama proses di latar belakang berjalan."""
        self._is_busy = busy
        self.drop_zone.set_controls_enabled(not busy)
        self.refresh_button.setEnabled(not busy and bool(self.current_folder))
        self.undo_button.setEnabled(not busy)
        self.empty_quarantine_button.setEnabled(not busy and bool(self.current_folder))
        self.rename_banner.set_buttons_enabled(not busy)
        self._sync_organize_button_state()

    def start_scan(self) -> None:
        """Memulai ScanWorker di latar belakang untuk memeriksa folder yang sedang aktif."""
        if not self.current_folder:
            return
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return

        self.rename_banner.setVisible(False)
        self.summary_info_label.setText("Sedang memeriksa isi folder...")
        self._set_controls_busy(True)
        self.progress_strip.start_progress("Sedang memeriksa isi folder...", 0)

        self.scan_worker = ScanWorker(folder_path=self.current_folder, parent=self)
        self.scan_worker.progress_updated.connect(self._on_worker_progress)
        self.scan_worker.scan_finished.connect(self._on_scan_finished)
        self.scan_worker.error_occurred.connect(self._on_worker_error)
        self.scan_worker.start()

    def _on_worker_progress(self, percent: int, message: str) -> None:
        """Memperbarui strip progres kontekstual secara langsung selama worker berjalan."""
        self.progress_strip.update_progress(percent, message)

    def _on_scan_finished(
        self,
        items: list[FilePlanItem],
        wasted_space_info: dict[str, Any],
    ) -> None:
        """Menampilkan hasil pemeriksaan ke tabel pratinjau, tab filter, dan ringkasan dinamis."""
        self.progress_strip.finish_progress()
        self.current_items = items
        self._last_wasted_space_info = wasted_space_info or {}

        self.preview_table.populate_items(items)
        filter_counts = self.preview_table.get_filter_counts()
        self.filter_bar.set_active_filter("all", emit_signal=False)
        self.filter_bar.update_counts(
            total=filter_counts["total"],
            rename=filter_counts["rename"],
            duplicate=filter_counts["duplicate"],
            manual=filter_counts["manual"],
            obsolete=filter_counts["obsolete"],
        )
        self.filter_bar.setVisible(bool(items))

        self._sync_rename_banner()
        self._update_dynamic_summary()

        self.content_stack.setCurrentIndex(1 if not items else 0)
        self._set_controls_busy(False)

    def start_organize(self) -> None:
        """Memulai OrganizeWorker untuk merapikan seluruh file tercentang di semua tab."""
        selected_items = self.preview_table.get_selected_items()
        if not selected_items:
            return
        if self.organize_worker is not None and self.organize_worker.isRunning():
            return

        planned_duplicates = sum(1 for item in selected_items if item.is_duplicate)
        planned_normal = len(selected_items) - planned_duplicates
        planned_renamed = sum(
            1
            for item in selected_items
            if not item.is_duplicate
            and item.is_rename_approved
            and item.suggested_name
            and item.suggested_name.strip()
        )
        left_untouched = max(0, len(self.current_items) - len(selected_items))

        self._last_organize_summary = {
            "planned_normal": planned_normal,
            "planned_duplicates": planned_duplicates,
            "planned_renamed": planned_renamed,
            "left_untouched": left_untouched,
        }

        self._set_controls_busy(True)
        self.progress_strip.start_progress("Sedang merapikan file...", 0)
        self.organize_worker = OrganizeWorker(
            mode="organize",
            items=selected_items,
            base_folder_path=self.current_folder,
            parent=self,
        )
        self.organize_worker.progress_updated.connect(self._on_worker_progress)
        self.organize_worker.operation_finished.connect(self._on_organize_finished)
        self.organize_worker.error_occurred.connect(self._on_worker_error)
        self.organize_worker.start()

    def _on_organize_finished(self, success_count: int, errors: list[str]) -> None:
        """Menampilkan dialog ringkasan hasil yang menenangkan lalu memeriksa ulang isi folder."""
        self.progress_strip.finish_progress()
        self._set_controls_busy(False)
        snapshot = self._last_organize_summary
        planned_normal = snapshot.get("planned_normal", success_count)
        planned_duplicates = snapshot.get("planned_duplicates", 0)
        planned_renamed = snapshot.get("planned_renamed", 0)
        left_untouched = snapshot.get("left_untouched", 0)

        if not errors:
            lines = [f"Selesai! Sebanyak {success_count} file telah berhasil diproses:"]
            if planned_normal > 0:
                rename_note = (
                    f" ({planned_renamed} di antaranya diberi nama baru yang lebih rapi)"
                    if planned_renamed > 0
                    else ""
                )
                lines.append(
                    f"• {planned_normal} file dirapikan ke folder kategorinya{rename_note}."
                )
            if planned_duplicates > 0:
                lines.append(
                    f"• {planned_duplicates} file kembar diamankan ke folder '_Karantina_Duplikat'."
                )
            if left_untouched > 0:
                lines.append(
                    f"• {left_untouched} file sengaja dibiarkan tetap di folder asal."
                )
            lines.append(
                "\nJika ingin mengembalikan semuanya seperti semula, Anda dapat menekan "
                "tombol \"Batalkan (Undo)\" kapan saja."
            )
            QMessageBox.information(self, "Folder Berhasil Dirapikan", "\n".join(lines))
        else:
            detail = "\n".join(f"• {note}" for note in errors[:5])
            msg = (
                f"Sebanyak {success_count} file berhasil dirapikan.\n\n"
                f"Beberapa file belum dapat dipindahkan saat ini:\n{detail}\n\n"
                "Pastikan file tersebut tidak sedang dibuka di aplikasi lain, "
                "lalu Anda dapat menekan \"Pindai Ulang\" atau \"Batalkan (Undo)\" kapan saja."
            )
            QMessageBox.warning(self, "Perapian Selesai dengan Catatan", msg)

        if self.current_folder:
            self.start_scan()

    def start_undo(self) -> None:
        """Memulai OrganizeWorker dalam mode 'undo' untuk memulihkan transaksi terakhir."""
        if self.organize_worker is not None and self.organize_worker.isRunning():
            return

        self._set_controls_busy(True)
        self.progress_strip.start_progress(
            "Sedang mengembalikan file ke lokasi dan nama aslinya...", 20
        )
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
        """Menampilkan hasil pembatalan dengan bahasa tenang serta menangani catatan skip."""
        self.progress_strip.finish_progress()
        self._set_controls_busy(False)
        if restored_count > 0:
            base_msg = (
                f"Sebanyak {restored_count} file beserta nama aslinya telah berhasil "
                "dikembalikan ke folder semula."
            )
            if errors:
                detail = "\n".join(f"• {note}" for note in errors[:5])
                QMessageBox.information(
                    self,
                    "Pembatalan Selesai",
                    f"{base_msg}\n\nCatatan tambahan:\n{detail}",
                )
            else:
                QMessageBox.information(self, "Pembatalan Berhasil", base_msg)
        else:
            info_text = (
                "\n".join(errors[:5])
                if errors
                else "Belum ada riwayat perapian yang dapat dibatalkan."
            )
            QMessageBox.information(self, "Informasi Pembatalan", info_text)

        if self.current_folder:
            self.start_scan()

    def start_empty_quarantine(self) -> None:
        """Memindahkan isi folder _Karantina_Duplikat ke Tempat Sampah setelah konfirmasi."""
        if not self.current_folder:
            return
        if self.organize_worker is not None and self.organize_worker.isRunning():
            return

        reply = QMessageBox.question(
            self,
            "Konfirmasi Bersihkan Karantina",
            "Apakah Anda yakin ingin memindahkan seluruh file di dalam folder "
            "'_Karantina_Duplikat' ke Tempat Sampah (Recycle Bin)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._set_controls_busy(True)
        self.progress_strip.start_progress(
            "Sedang memindahkan file karantina ke Tempat Sampah...", 20
        )
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
        self.progress_strip.finish_progress()
        self._set_controls_busy(False)
        if trashed_count > 0:
            msg = (
                f"Sebanyak {trashed_count} file dari karantina berhasil dipindahkan "
                "ke Tempat Sampah (Recycle Bin)."
            )
            if errors:
                detail = "\n".join(f"• {note}" for note in errors[:5])
                QMessageBox.warning(
                    self,
                    "Pembersihan Selesai dengan Catatan",
                    f"{msg}\n\nCatatan:\n{detail}",
                )
            else:
                QMessageBox.information(self, "Karantina Dibersihkan", msg)
        else:
            info_text = "\n".join(errors[:5]) if errors else "Folder karantina sudah kosong."
            QMessageBox.information(self, "Informasi Karantina", info_text)

    def _on_worker_error(self, error_message: str) -> None:
        """Menampilkan pesan ramah pengguna apabila proses di latar belakang mengalami kendala."""
        self.progress_strip.finish_progress()
        self._set_controls_busy(False)
        if self.current_folder and not self.current_items:
            self.summary_info_label.setText("Pemeriksaan folder belum dapat diselesaikan.")
        QMessageBox.warning(self, "Proses Belum Dapat Dilanjutkan", error_message)
