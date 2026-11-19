"""Komponen visual kustom untuk antarmuka Smart File Organizer.

Berisi DropZoneWidget untuk menerima input folder (melalui drag-and-drop maupun
dialog pemilihan folder), RenameBannerWidget untuk persetujuan massal usulan
penamaan ulang, serta PreviewTableWidget untuk menampilkan rencana perapian file
beserta checkbox per baris dan kontrol inline usulan rename.
"""

import html

from PyQt6.QtCore import QFileInfo, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QDragEnterEvent, QDragLeaveEvent, QDropEvent, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.models import FilePlanItem


class DropZoneWidget(QFrame):
    """Area fokus utama untuk memilih atau menarik (drag-and-drop) folder berantakan.

    Memancarkan sinyal `folder_selected(str)` segera setelah pengguna menjatuhkan
    folder atau memilih folder melalui tombol dialog.
    """

    folder_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi tampilan area drag-and-drop beserta tombol pilih folder."""
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setProperty("dragActive", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("Tarik & Lepas Folder Berantakan ke Sini")
        self.title_label.setObjectName("DropZoneTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hint_label = QLabel(
            "Atau klik tombol di bawah untuk memilih folder yang ingin dirapikan secara otomatis"
        )
        self.hint_label.setObjectName("DropZoneHintLabel")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button_row = QHBoxLayout()
        button_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.browse_button = QPushButton("Pilih Folder Berantakan")
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(self._on_browse_clicked)
        button_row.addWidget(self.browse_button)

        self.selected_folder_label = QLabel("Belum ada folder yang dipilih")
        self.selected_folder_label.setObjectName("SelectedFolderLabel")
        self.selected_folder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.title_label)
        layout.addWidget(self.hint_label)
        layout.addLayout(button_row)
        layout.addWidget(self.selected_folder_label)

    def set_selected_folder_text(self, folder_path: str) -> None:
        """Memperbarui teks indikator alamat folder yang sedang aktif."""
        if not folder_path:
            self.selected_folder_label.setText("Belum ada folder yang dipilih")
            return
        self.selected_folder_label.setText(f"Folder aktif: {folder_path}")

    def _on_browse_clicked(self) -> None:
        """Membuka dialog pemilihan folder dan memancarkan sinyal jika folder dipilih."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Pilih Folder Berantakan",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder_path:
            self.folder_selected.emit(folder_path)

    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        """Memvalidasi apakah item yang ditarik ke dalam area adalah folder lokal."""
        if event is None:
            return

        mime_data = event.mimeData()
        if mime_data is not None and mime_data.hasUrls():
            for url in mime_data.urls():
                local_path = url.toLocalFile()
                if local_path and QFileInfo(local_path).isDir():
                    self._set_drag_highlight(True)
                    event.acceptProposedAction()
                    return

        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent | None) -> None:
        """Mengembalikan tampilan normal ketika kursor drag keluar dari area."""
        self._set_drag_highlight(False)
        if event is not None:
            super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent | None) -> None:
        """Menerima folder yang dijatuhkan pengguna dan memancarkan sinyal folder_selected."""
        self._set_drag_highlight(False)
        if event is None:
            return

        mime_data = event.mimeData()
        if mime_data is not None and mime_data.hasUrls():
            for url in mime_data.urls():
                local_path = url.toLocalFile()
                if local_path and QFileInfo(local_path).isDir():
                    event.acceptProposedAction()
                    self.folder_selected.emit(local_path)
                    return

        event.ignore()

    def _set_drag_highlight(self, active: bool) -> None:
        """Memperbarui properti dinamis QSS saat folder sedang ditarik di atas widget."""
        self.setProperty("dragActive", active)
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)


class RenameBannerWidget(QFrame):
    """Banner aksi massal untuk menerima atau menolak seluruh usulan rename otomatis."""

    accept_all_clicked = pyqtSignal()
    reject_all_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi tampilan banner massal usulan rename dalam kondisi tersembunyi."""
        super().__init__(parent)
        self.setObjectName("RenameBanner")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self.info_label = QLabel("")
        self.info_label.setObjectName("RenameBannerLabel")

        self.accept_all_button = QPushButton("✓ Terima Semua")
        self.accept_all_button.setObjectName("BannerAcceptAllButton")
        self.accept_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accept_all_button.clicked.connect(self.accept_all_clicked.emit)

        self.reject_all_button = QPushButton("✕ Tolak Semua")
        self.reject_all_button.setObjectName("BannerRejectAllButton")
        self.reject_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reject_all_button.clicked.connect(self.reject_all_clicked.emit)

        layout.addWidget(self.info_label, stretch=1)
        layout.addWidget(self.accept_all_button)
        layout.addWidget(self.reject_all_button)

        self.setVisible(False)

    def update_counts(self, total_suggestions: int, approved_count: int) -> None:
        """Memperbarui ringkasan usulan rename dan visibilitas banner."""
        if total_suggestions <= 0:
            self.setVisible(False)
            return

        self.info_label.setText(
            f"Ditemukan {total_suggestions} usulan nama baru otomatis dari isi dokumen "
            f"({approved_count} disetujui)."
        )
        self.setVisible(True)

    def set_buttons_enabled(self, enabled: bool) -> None:
        """Mengatur status aktif tombol aksi massal ketika proses background berjalan."""
        self.accept_all_button.setEnabled(enabled)
        self.reject_all_button.setEnabled(enabled)


class PreviewTableWidget(QTableWidget):
    """Tabel untuk menampilkan pratinjau rencana perapian file sebelum dieksekusi."""

    selection_changed = pyqtSignal()
    rename_approval_changed = pyqtSignal()

    COLUMNS: tuple[str, ...] = (
        "Pilih",
        "Nama File & Usulan Nama Baru",
        "Folder Tujuan",
        "Status",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi kolom, header, dan perilaku tampilan tabel pratinjau."""
        super().__init__(0, len(self.COLUMNS), parent)
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self._items: list[FilePlanItem] = []
        self._row_checkboxes: list[QCheckBox] = []
        self._row_checkbox_containers: list[QWidget] = []
        self._rename_rows: dict[int, tuple[QWidget, QLabel, QPushButton, QPushButton]] = {}

        vertical_header = self.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
            vertical_header.setDefaultSectionSize(48)

        horizontal_header = self.horizontalHeader()
        if horizontal_header is not None:
            horizontal_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(0, 54)
            horizontal_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            horizontal_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            horizontal_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

    @staticmethod
    def _is_rename_eligible(item: FilePlanItem) -> bool:
        """Memeriksa apakah item memiliki usulan rename yang dapat disetujui/ditolak."""
        return bool(
            item.suggested_name
            and item.suggested_name.strip()
            and not item.is_skipped
            and not item.is_duplicate
        )

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        """Menyegarkan gaya QSS setelah properti dinamis widget diubah."""
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)

    def populate_items(self, items: list[FilePlanItem]) -> None:
        """Mengisi ulang baris tabel dengan daftar FilePlanItem, checkbox, dan kontrol rename.

        Args:
            items: Daftar objek `FilePlanItem` hasil pemindaian.
        """
        self._items = list(items)
        self._row_checkboxes.clear()
        self._row_checkbox_containers.clear()
        self._rename_rows.clear()

        self.setRowCount(0)
        self.setRowCount(len(self._items))

        bold_font = QFont()
        bold_font.setBold(True)

        italic_font = QFont()
        italic_font.setItalic(True)

        for row_idx, item in enumerate(self._items):
            # Kolom 0: Checkbox pengecualian file
            cb_container = QWidget(self)
            cb_container.setObjectName("CheckboxCellContainer")
            cb_container.setProperty("renameHighlighted", False)
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            checkbox = QCheckBox(cb_container)
            if item.is_skipped:
                checkbox.setChecked(False)
                checkbox.setEnabled(False)
            else:
                checkbox.setChecked(True)
                checkbox.setEnabled(True)
            checkbox.toggled.connect(lambda _checked: self.selection_changed.emit())
            cb_layout.addWidget(checkbox)

            self.setItem(row_idx, 0, QTableWidgetItem(""))
            self.setCellWidget(row_idx, 0, cb_container)
            self._row_checkboxes.append(checkbox)
            self._row_checkbox_containers.append(cb_container)

            # Kolom 1: Nama File atau Usulan Rename Inline ala Google Docs
            if self._is_rename_eligible(item):
                rename_container = QWidget(self)
                rename_container.setObjectName("RenameCellContainer")
                rename_container.setProperty("renameHighlighted", False)
                rename_layout = QHBoxLayout(rename_container)
                rename_layout.setContentsMargins(8, 4, 8, 4)
                rename_layout.setSpacing(8)

                name_label = QLabel(rename_container)
                name_label.setObjectName("RenameTextLabel")
                name_label.setTextFormat(Qt.TextFormat.RichText)

                accept_btn = QPushButton("✓", rename_container)
                accept_btn.setObjectName("RenameAcceptButton")
                accept_btn.setFixedSize(28, 28)
                accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                accept_btn.setToolTip("Terima usulan nama baru")
                accept_btn.clicked.connect(
                    lambda _checked=False, r=row_idx: self._set_row_rename_approved(r, True)
                )

                reject_btn = QPushButton("✕", rename_container)
                reject_btn.setObjectName("RenameRejectButton")
                reject_btn.setFixedSize(28, 28)
                reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                reject_btn.setToolTip("Tolak usulan (tetap gunakan nama asli)")
                reject_btn.clicked.connect(
                    lambda _checked=False, r=row_idx: self._set_row_rename_approved(r, False)
                )

                rename_layout.addWidget(name_label, stretch=1)
                rename_layout.addWidget(accept_btn)
                rename_layout.addWidget(reject_btn)

                self.setItem(row_idx, 1, QTableWidgetItem(""))
                self.setCellWidget(row_idx, 1, rename_container)
                self._rename_rows[row_idx] = (
                    rename_container,
                    name_label,
                    accept_btn,
                    reject_btn,
                )
            else:
                name_item = QTableWidgetItem(item.file_name)
                if item.is_skipped:
                    name_item.setForeground(QBrush(QColor("#64748B")))
                self.setItem(row_idx, 1, name_item)

            # Kolom 2: Folder Tujuan
            if item.is_skipped:
                category_item = QTableWidgetItem("(Tetap di Folder Ini)")
                category_item.setForeground(QBrush(QColor("#64748B")))
                category_item.setFont(italic_font)
            else:
                category_item = QTableWidgetItem(item.category)
            self.setItem(row_idx, 2, category_item)

            # Kolom 3: Badge Status
            if item.is_skipped:
                status_text = "Dibiarkan (Perlu Cek Manual)"
                status_item = QTableWidgetItem(status_text)
                status_item.setBackground(QBrush(QColor("#F1F5F9")))
                status_item.setForeground(QBrush(QColor("#64748B")))
            elif item.is_duplicate or item.is_obsolete_temp or item.status_label in (
                "File Duplikat",
                "Installer Usang",
            ):
                status_item = QTableWidgetItem(item.status_label)
                status_item.setBackground(QBrush(QColor("#FEF3C7")))
                status_item.setForeground(QBrush(QColor("#92400E")))
            else:
                status_item = QTableWidgetItem(item.status_label)
                status_item.setBackground(QBrush(QColor("#DCFCE7")))
                status_item.setForeground(QBrush(QColor("#166534")))

            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFont(bold_font)
            self.setItem(row_idx, 3, status_item)

            if row_idx in self._rename_rows:
                self._refresh_rename_row_visual(row_idx)

    def _set_row_rename_approved(self, row_idx: int, approved: bool) -> None:
        """Mengubah status persetujuan rename pada satu baris dan menyegarkan tampilannya."""
        if not (0 <= row_idx < len(self._items)) or row_idx not in self._rename_rows:
            return
        self._items[row_idx].is_rename_approved = approved
        self._refresh_rename_row_visual(row_idx)
        self.rename_approval_changed.emit()

    def _refresh_rename_row_visual(self, row_idx: int) -> None:
        """Memperbarui highlight baris, format teks `nama_lama ➔ nama_baru`, dan tombol aksi."""
        item = self._items[row_idx]
        container, label, accept_btn, reject_btn = self._rename_rows[row_idx]
        cb_container = self._row_checkbox_containers[row_idx]

        orig = html.escape(item.file_name)
        sugg = html.escape(item.suggested_name or "")

        if item.is_rename_approved:
            label.setText(
                f'<span style="color:#64748B;">{orig}</span> '
                f'<span style="color:#15803D; font-weight:bold;">➔</span> '
                f'<span style="color:#166534; font-weight:bold;">{sugg}</span>'
            )
            accept_btn.setProperty("active", True)
            reject_btn.setProperty("active", False)
            container.setProperty("renameHighlighted", True)
            cb_container.setProperty("renameHighlighted", True)

            highlight_brush = QBrush(QColor("#ECFDF5"))
            for col in (0, 1, 2):
                cell_item = self.item(row_idx, col)
                if cell_item is not None:
                    cell_item.setBackground(highlight_brush)
        else:
            label.setText(
                f'<span style="color:#0F172A;">{orig}</span> '
                f'<span style="color:#94A3B8; text-decoration:line-through;">{sugg}</span>'
            )
            accept_btn.setProperty("active", False)
            reject_btn.setProperty("active", True)
            container.setProperty("renameHighlighted", False)
            cb_container.setProperty("renameHighlighted", False)

            default_brush = QBrush()
            for col in (0, 1, 2):
                cell_item = self.item(row_idx, col)
                if cell_item is not None:
                    cell_item.setBackground(default_brush)

        self._repolish(container)
        self._repolish(cb_container)
        self._repolish(accept_btn)
        self._repolish(reject_btn)

    def set_all_renames_approved(self, approved: bool) -> None:
        """Menerima atau menolak seluruh usulan rename yang tampil di tabel sekaligus."""
        if not self._rename_rows:
            return
        for row_idx in self._rename_rows:
            self._items[row_idx].is_rename_approved = approved
            self._refresh_rename_row_visual(row_idx)
        self.rename_approval_changed.emit()

    def get_selected_items(self) -> list[FilePlanItem]:
        """Mengembalikan daftar FilePlanItem yang dicentang pengguna dan siap diproses."""
        return [
            item
            for item, cb in zip(self._items, self._row_checkboxes)
            if cb.isChecked() and not item.is_skipped
        ]

    def get_rename_suggestion_counts(self) -> tuple[int, int]:
        """Mengembalikan tuple (total_usulan_rename, jumlah_yang_disetujui)."""
        total = len(self._rename_rows)
        approved = sum(
            1 for row_idx in self._rename_rows if self._items[row_idx].is_rename_approved
        )
        return total, approved

    def get_selection_summary(self) -> dict[str, int]:
        """Menghitung ringkasan status seluruh baris berdasarkan pilihan centang saat ini."""
        selected_ready = 0
        selected_duplicates = 0
        manual_check_count = 0
        unchecked_count = 0

        for item, cb in zip(self._items, self._row_checkboxes):
            if item.is_skipped:
                manual_check_count += 1
            elif cb.isChecked():
                if item.is_duplicate:
                    selected_duplicates += 1
                else:
                    selected_ready += 1
            else:
                unchecked_count += 1

        return {
            "total_files": len(self._items),
            "selected_ready": selected_ready,
            "selected_duplicates": selected_duplicates,
            "manual_check_count": manual_check_count,
            "unchecked_count": unchecked_count,
            "selected_total": selected_ready + selected_duplicates,
        }


class EmptyStateWidget(QFrame):
    """Tampilan ramah saat folder yang dipilih kosong atau tidak memiliki file untuk dirapikan."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi kartu pesan kondisi kosong (empty state)."""
        super().__init__(parent)
        self.setObjectName("EmptyStateCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 48, 32, 48)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("Tidak Ada File yang Perlu Dirapikan")
        self.title_label.setObjectName("EmptyStateTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.desc_label = QLabel(
            "Folder ini kosong atau seluruh file sudah tersimpan rapi di dalam subfolder."
        )
        self.desc_label.setObjectName("EmptyStateDescLabel")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)
