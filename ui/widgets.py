"""Komponen visual kustom untuk antarmuka Smart File Organizer.

Berisi DropZoneWidget untuk menerima input folder (melalui drag-and-drop maupun
dialog pemilihan folder) dan PreviewTableWidget untuk menampilkan rencana
perapian file beserta indikator warna statusnya.
"""

from PyQt6.QtCore import QFileInfo, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QDragEnterEvent, QDragLeaveEvent, QDropEvent, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
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
            self.set_selected_folder_text(folder_path)
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
                    self.set_selected_folder_text(local_path)
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


class PreviewTableWidget(QTableWidget):
    """Tabel untuk menampilkan pratinjau rencana perapian file sebelum dieksekusi."""

    COLUMNS: tuple[str, ...] = (
        "Nama File Asli",
        "Usulan Nama Baru",
        "Kategori Tujuan",
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

        vertical_header = self.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
            vertical_header.setDefaultSectionSize(38)

        horizontal_header = self.horizontalHeader()
        if horizontal_header is not None:
            horizontal_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            horizontal_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            horizontal_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            horizontal_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

    def populate_items(self, items: list[FilePlanItem]) -> None:
        """Mengisi ulang baris tabel dengan daftar FilePlanItem dan memberi warna badge status.

        Args:
            items: Daftar objek `FilePlanItem` hasil pemindaian.
        """
        self.setRowCount(0)
        self.setRowCount(len(items))

        bold_font = QFont()
        bold_font.setBold(True)

        for row_idx, item in enumerate(items):
            original_name_item = QTableWidgetItem(item.file_name)
            proposed_name_item = QTableWidgetItem(item.proposed_name)
            category_item = QTableWidgetItem(item.category)
            status_item = QTableWidgetItem(item.status_label)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFont(bold_font)

            # Indikator warna lembut sesuai status_label (Hijau vs Kuning/Oranye)
            if item.is_duplicate or item.is_obsolete_temp or item.status_label in (
                "File Duplikat",
                "Installer Usang",
            ):
                status_item.setBackground(QBrush(QColor("#FEF3C7")))
                status_item.setForeground(QBrush(QColor("#92400E")))
            else:
                status_item.setBackground(QBrush(QColor("#DCFCE7")))
                status_item.setForeground(QBrush(QColor("#166534")))

            self.setItem(row_idx, 0, original_name_item)
            self.setItem(row_idx, 1, proposed_name_item)
            self.setItem(row_idx, 2, category_item)
            self.setItem(row_idx, 3, status_item)
