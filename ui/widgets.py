"""Komponen visual kustom untuk antarmuka Rapihin Aja (Windows 11 Fluent + Notion).

Seluruh komponen di modul ini bersifat murni antarmuka (UI) tanpa impor modul
sistem berkas (`os`, `pathlib`, `shutil`). Mencakup checkbox kustom (`FluentCheckBox`),
area drag-and-drop adaptif (`CollapsibleDropZoneWidget`), indikator progres tipis
(`FluentProgressStrip`), tab filter pill (`FilterBarWidget`), banner persetujuan
usulan nama (`RenameBannerWidget`), badge status pill (`StatusBadgeWidget`), serta
tabel pratinjau (`PreviewTableWidget`).
"""

from PyQt6.QtCore import QFileInfo, QPoint, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QResizeEvent,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.models import FilePlanItem


def _format_file_size(size_bytes: int) -> str:
    """Mengonversi ukuran bytes menjadi teks yang mudah dibaca tanpa modul sistem berkas."""
    safe_size = max(0, int(size_bytes))
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(safe_size)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{safe_size} B"


def _repolish_widget(widget: QWidget) -> None:
    """Menyegarkan gaya QSS widget setelah properti dinamisnya diubah."""
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)


class ElidedLabel(QLabel):
    """Label satu baris yang otomatis memotong teks panjang dengan elipsis (`...`).

    Menyimpan teks lengkap di memori internal agar tidak memaksa lebar tata letak
    melebar melebihi ukuran jendela, sambil tetap mempertahankan tooltip penuh.
    """

    def __init__(
        self,
        text: str = "",
        elide_mode: Qt.TextElideMode = Qt.TextElideMode.ElideRight,
        parent: QWidget | None = None,
    ) -> None:
        """Menginisialisasi label dengan mode pemotongan elipsis yang dipilih."""
        super().__init__(parent)
        self._full_text: str = text
        self._elide_mode: Qt.TextElideMode = elide_mode
        self.setWordWrap(False)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.update_elision()

    def fullText(self) -> str:
        """Mengembalikan teks asli lengkap sebelum dipotong elipsis."""
        return self._full_text

    def setText(self, a0: str | None) -> None:  # noqa: N802
        """Memperbarui teks lengkap label lalu menghitung ulang pemotongan elipsis."""
        self._full_text = a0 or ""
        self.update_elision()

    def setFont(self, a0: QFont) -> None:  # noqa: N802
        """Memperbarui font label lalu menyesuaikan ulang lebar elipsis."""
        super().setFont(a0)
        self.update_elision()

    def update_elision(self) -> None:
        """Memotong teks agar pas di dalam lebar konten label saat ini."""
        available_width = self.contentsRect().width()
        if available_width <= 20:
            super().setText(self._full_text)
            return
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, self._elide_mode, available_width)
        super().setText(elided)

    def resizeEvent(self, a0: QResizeEvent | None) -> None:  # noqa: N802
        """Menghitung ulang pemotongan teks ketika lebar widget berubah."""
        super().resizeEvent(a0)
        self.update_elision()

    def showEvent(self, a0: QShowEvent | None) -> None:  # noqa: N802
        """Menghitung ulang pemotongan teks saat widget pertama kali tampil."""
        super().showEvent(a0)
        self.update_elision()


ElidedPathLabel = ElidedLabel


class FluentCheckBox(QCheckBox):
    """Checkbox kustom bergaya Windows 11 Fluent dengan centang vektor QPainter.

    Digambar penuh dengan `QPainter` agar tanda centang selalu tajam di seluruh
    tema OS (Linux/Windows) tanpa bergantung pada gambar/SVG eksternal.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi ukuran kompak 20x20 dan mengaktifkan deteksi hover."""
        super().__init__(parent)
        self.setObjectName("FluentCheckBox")
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def sizeHint(self) -> QSize:  # noqa: N802
        """Mengembalikan ukuran tetap kotak checkbox agar posisi di sel tepat di tengah."""
        return QSize(20, 20)

    def hitButton(self, pos: QPoint) -> bool:  # noqa: N802
        """Menjadikan seluruh area kotak 20x20 responsif terhadap klik mouse."""
        return self.rect().contains(pos)

    def paintEvent(self, a0: QPaintEvent | None) -> None:  # noqa: N802
        """Menggambar kotak membulat dan ikon centang putih halus menggunakan QPainter."""
        del a0
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box_rect = QRectF(1.0, 1.0, 18.0, 18.0)
        is_checked = self.isChecked()
        is_enabled = self.isEnabled()
        is_hovered = self.underMouse()

        if not is_enabled:
            fill_color = QColor("#94A3B8") if is_checked else QColor("#E2E8F0")
            border_color = QColor("#94A3B8") if is_checked else QColor("#CBD5E1")
        elif is_checked:
            fill_color = QColor("#005A9E") if is_hovered else QColor("#0067C0")
            border_color = fill_color
        else:
            fill_color = QColor("#FFFFFF")
            border_color = QColor("#64748B") if is_hovered else QColor("#CBD5E1")

        painter.setBrush(QBrush(fill_color))
        painter.setPen(QPen(border_color, 1.25))
        painter.drawRoundedRect(box_rect, 5.0, 5.0)

        if is_checked:
            check_path = QPainterPath()
            check_path.moveTo(5.2, 10.2)
            check_path.lineTo(8.5, 13.5)
            check_path.lineTo(14.8, 6.8)

            check_pen = QPen(
                QColor("#FFFFFF"),
                2.0,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(check_pen)
            painter.drawPath(check_path)

        painter.end()


class CollapsibleDropZoneWidget(QFrame):
    """Area input folder adaptif dengan mode Hero (Welcome) dan Toolbar Kompak (Active).

    Kedua mode tetap mendukung penarikan folder langsung (drag-and-drop) dan
    memancarkan sinyal `folder_selected(str)` ketika folder valid dipilih.
    """

    folder_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi tampilan hero welcome dan baris kompak aktif."""
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setProperty("dragActive", False)
        self.setProperty("compact", False)
        self._is_compact: bool = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Mode Hero (Welcome State)
        self.hero_container = QWidget(self)
        self.hero_container.setObjectName("HeroContainer")
        hero_layout = QVBoxLayout(self.hero_container)
        hero_layout.setContentsMargins(32, 34, 32, 30)
        hero_layout.setSpacing(10)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("Tarik & Lepas Folder Berantakan ke Sini", self.hero_container)
        self.title_label.setObjectName("DropZoneTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hint_label = QLabel(
            "Atau klik tombol di bawah untuk memilih folder yang ingin dirapikan secara otomatis",
            self.hero_container,
        )
        self.hint_label.setObjectName("DropZoneHintLabel")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)

        browse_row = QHBoxLayout()
        browse_row.setContentsMargins(0, 6, 0, 6)
        browse_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.browse_button = QPushButton("Pilih Folder Berantakan", self.hero_container)
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(self._on_browse_clicked)
        browse_row.addWidget(self.browse_button)

        self.trust_label = QLabel(
            "100% Offline  •  Subfolder Aman  •  Bisa Dibatalkan (Undo)",
            self.hero_container,
        )
        self.trust_label.setObjectName("TrustSignalLabel")
        self.trust_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hero_layout.addWidget(self.title_label)
        hero_layout.addWidget(self.hint_label)
        hero_layout.addLayout(browse_row)
        hero_layout.addWidget(self.trust_label)

        # 2. Mode Kompak 1 Baris (Active State)
        self.compact_container = QWidget(self)
        self.compact_container.setObjectName("CompactContainer")
        compact_layout = QHBoxLayout(self.compact_container)
        compact_layout.setContentsMargins(14, 8, 12, 8)
        compact_layout.setSpacing(10)

        self.active_folder_badge = QLabel("Folder Aktif", self.compact_container)
        self.active_folder_badge.setObjectName("ActiveFolderBadge")

        self.selected_folder_label = ElidedLabel(
            "Belum ada folder yang dipilih",
            elide_mode=Qt.TextElideMode.ElideMiddle,
            parent=self.compact_container,
        )
        self.selected_folder_label.setObjectName("SelectedFolderLabel")

        self.change_folder_button = QPushButton("Ganti Folder", self.compact_container)
        self.change_folder_button.setObjectName("SecondaryButton")
        self.change_folder_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.change_folder_button.setToolTip(
            "Pilih folder lain atau tarik folder langsung ke baris ini"
        )
        self.change_folder_button.clicked.connect(self._on_browse_clicked)

        compact_layout.addWidget(self.active_folder_badge)
        compact_layout.addWidget(self.selected_folder_label, stretch=1)
        compact_layout.addWidget(self.change_folder_button)

        main_layout.addWidget(self.hero_container)
        main_layout.addWidget(self.compact_container)

        self.set_compact(False)

    def set_compact(self, compact: bool) -> None:
        """Beralih antara mode hero besar (Welcome) dan toolbar 1 baris (Active)."""
        self._is_compact = bool(compact)
        self.hero_container.setVisible(not self._is_compact)
        self.compact_container.setVisible(self._is_compact)

        if self._is_compact:
            self.setMinimumHeight(0)
            self.setMaximumHeight(68)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setMaximumHeight(16777215)
            self.setMinimumHeight(230)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.setProperty("compact", self._is_compact)
        _repolish_widget(self)

    def set_selected_folder_text(self, folder_path: str) -> None:
        """Memperbarui indikator alamat folder aktif sekaligus mengatur mode tampilan."""
        if not folder_path:
            self.selected_folder_label.setText("Belum ada folder yang dipilih")
            self.selected_folder_label.setToolTip("")
            self.set_compact(False)
            return

        self.selected_folder_label.setText(folder_path)
        self.selected_folder_label.setToolTip(
            f"Folder aktif: {folder_path}\nTarik folder lain ke baris ini untuk mengganti."
        )
        self.set_compact(True)

    def set_controls_enabled(self, enabled: bool) -> None:
        """Mengatur aktif/nonaktif tombol pemilihan folder dan penerimaan drag-and-drop."""
        self.browse_button.setEnabled(enabled)
        self.change_folder_button.setEnabled(enabled)
        self.setAcceptDrops(enabled)

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

    def dragEnterEvent(self, a0: QDragEnterEvent | None) -> None:  # noqa: N802
        """Memvalidasi apakah item yang ditarik ke dalam area adalah folder lokal."""
        if a0 is None:
            return

        mime_data = a0.mimeData()
        if mime_data is not None and mime_data.hasUrls():
            for url in mime_data.urls():
                local_path = url.toLocalFile()
                if local_path and QFileInfo(local_path).isDir():
                    self._set_drag_highlight(True)
                    a0.acceptProposedAction()
                    return

        a0.ignore()

    def dragLeaveEvent(self, a0: QDragLeaveEvent | None) -> None:  # noqa: N802
        """Mengembalikan tampilan normal ketika kursor drag keluar dari area."""
        self._set_drag_highlight(False)
        if a0 is not None:
            super().dragLeaveEvent(a0)

    def dropEvent(self, a0: QDropEvent | None) -> None:  # noqa: N802
        """Menerima folder yang dijatuhkan pengguna dan memancarkan sinyal folder_selected."""
        self._set_drag_highlight(False)
        if a0 is None:
            return

        mime_data = a0.mimeData()
        if mime_data is not None and mime_data.hasUrls():
            for url in mime_data.urls():
                local_path = url.toLocalFile()
                if local_path and QFileInfo(local_path).isDir():
                    a0.acceptProposedAction()
                    self.folder_selected.emit(local_path)
                    return

        a0.ignore()

    def _set_drag_highlight(self, active: bool) -> None:
        """Memperbarui properti dinamis QSS saat folder sedang ditarik di atas widget."""
        self.setProperty("dragActive", active)
        _repolish_widget(self)


DropZoneWidget = CollapsibleDropZoneWidget


class FluentProgressStrip(QWidget):
    """Strip indikator progres tipis gaya Windows 11 yang otomatis tersembunyi saat idle."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi label status tipis dan bar progres 4px dalam keadaan tersembunyi."""
        super().__init__(parent)
        self.setObjectName("ProgressStrip")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)

        text_row = QHBoxLayout()
        text_row.setContentsMargins(0, 0, 0, 0)
        text_row.setSpacing(8)

        self.status_label = ElidedLabel("", elide_mode=Qt.TextElideMode.ElideRight, parent=self)
        self.status_label.setObjectName("StatusProgressLabel")

        self.percent_label = QLabel("", self)
        self.percent_label.setObjectName("StatusProgressLabel")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        text_row.addWidget(self.status_label, stretch=1)
        text_row.addWidget(self.percent_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setObjectName("FluentProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)

        layout.addLayout(text_row)
        layout.addWidget(self.progress_bar)

        self.setVisible(False)

    def start_progress(self, message: str, percent: int = 0) -> None:
        """Menampilkan strip progres di awal pemindaian atau eksekusi."""
        self.update_progress(percent, message)
        self.setVisible(True)

    def update_progress(self, percent: int, message: str) -> None:
        """Memperbarui nilai persentase dan teks status selama worker berjalan."""
        clamped = max(0, min(100, int(percent)))
        self.progress_bar.setValue(clamped)
        self.status_label.setText(message)
        self.percent_label.setText(f"{clamped}%")

    def finish_progress(self) -> None:
        """Menyembunyikan kembali strip progres ketika operasi telah selesai."""
        self.progress_bar.setValue(0)
        self.status_label.setText("")
        self.percent_label.setText("")
        self.setVisible(False)


class FilterBarWidget(QWidget):
    """Barisan tab filter pill minimalis untuk menyaring tampilan baris tabel tanpa mengubah centang."""

    filter_changed = pyqtSignal(str)

    _TAB_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
        ("all", "Semua", "Tampilkan seluruh file yang terdeteksi"),
        ("rename", "Usulan Nama", "Tampilkan file yang mendapat usulan nama baru otomatis"),
        (
            "duplicate",
            "Duplikat",
            "Tampilkan file duplikat dan installer usang yang berpotensi menghemat ruang",
        ),
        ("manual", "Cek Manual", "Tampilkan file yang dibiarkan tetap di folder asal"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi empat tab pill filter beserta tombol interaktifnya."""
        super().__init__(parent)
        self.setObjectName("FilterBar")
        self._active_mode: str = "all"
        self._buttons: dict[str, QPushButton] = {}
        self._base_labels: dict[str, str] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for mode, label, tooltip in self._TAB_DEFINITIONS:
            btn = QPushButton(f"{label} (0)", self)
            btn.setObjectName("FilterTabButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setProperty("active", mode == "all")
            btn.clicked.connect(lambda _checked=False, m=mode: self.set_active_filter(m, True))
            self._buttons[mode] = btn
            self._base_labels[mode] = label
            layout.addWidget(btn)

        layout.addStretch(1)

    def active_filter(self) -> str:
        """Mengembalikan kunci mode filter yang sedang aktif saat ini."""
        return self._active_mode

    def set_active_filter(self, mode: str, emit_signal: bool = False) -> None:
        """Mengubah tab filter aktif dan memperbarui gaya pill QSS-nya."""
        if mode not in self._buttons:
            mode = "all"
        self._active_mode = mode
        for key, btn in self._buttons.items():
            btn.setProperty("active", key == mode)
            _repolish_widget(btn)
        if emit_signal:
            self.filter_changed.emit(mode)

    def update_counts(
        self,
        total: int,
        rename: int,
        duplicate: int,
        manual: int,
        obsolete: int = 0,
    ) -> None:
        """Memperbarui angka pada masing-masing tab filter dan menonaktifkan tab kosong."""
        counts = {
            "all": total,
            "rename": rename,
            "duplicate": duplicate,
            "manual": manual,
        }
        for key, btn in self._buttons.items():
            count = counts[key]
            label = "Duplikat & Usang" if key == "duplicate" and obsolete > 0 else self._base_labels[key]
            btn.setText(f"{label} ({count})")
            if key != "all":
                btn.setEnabled(count > 0)

        if self._active_mode != "all" and counts.get(self._active_mode, 0) == 0:
            self.set_active_filter("all", emit_signal=True)


class RenameBannerWidget(QFrame):
    """Banner aksi massal untuk menerima atau menolak seluruh usulan rename otomatis."""

    accept_all_clicked = pyqtSignal()
    reject_all_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi banner massal usulan nama tanpa emoji agar bersih lintas OS."""
        super().__init__(parent)
        self.setObjectName("RenameBanner")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(10)

        self.pill_label = QLabel("Usulan Nama", self)
        self.pill_label.setObjectName("RenameBannerPill")

        self.info_label = QLabel("", self)
        self.info_label.setObjectName("RenameBannerLabel")

        self.accept_all_button = QPushButton("✓ Terima Semua", self)
        self.accept_all_button.setObjectName("BannerAcceptAllButton")
        self.accept_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accept_all_button.clicked.connect(self.accept_all_clicked.emit)

        self.reject_all_button = QPushButton("✕ Tolak Semua", self)
        self.reject_all_button.setObjectName("BannerRejectAllButton")
        self.reject_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reject_all_button.clicked.connect(self.reject_all_clicked.emit)

        layout.addWidget(self.pill_label)
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


class StatusBadgeWidget(QWidget):
    """Kontainer transparan berisi pill status berwarna lembut untuk kolom status tabel."""

    def __init__(
        self,
        text: str,
        variant: str = "ready",
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Menginisialisasi pill status terpusat di dalam sel tabel."""
        super().__init__(parent)
        self.setObjectName("StatusCellContainer")
        self.setProperty("renameHighlighted", False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pill_label = QLabel(text, self)
        self.pill_label.setObjectName("StatusPill")
        self.pill_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pill_label.setProperty("variant", variant)
        if tooltip:
            self.setToolTip(tooltip)
            self.pill_label.setToolTip(tooltip)

        layout.addWidget(self.pill_label)

    def set_rename_highlighted(self, highlighted: bool) -> None:
        """Menyesuaikan latar kontainer agar menyatu dengan baris usulan nama yang disetujui."""
        self.setProperty("renameHighlighted", highlighted)
        _repolish_widget(self)


class PreviewTableWidget(QTableWidget):
    """Tabel Notion-style untuk menampilkan pratinjau rencana perapian file sebelum dieksekusi."""

    selection_changed = pyqtSignal()
    rename_approval_changed = pyqtSignal()

    COLUMNS: tuple[str, ...] = (
        "Pilih",
        "Nama File & Usulan Nama Baru",
        "Folder Tujuan",
        "Status",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        """Menginisialisasi kolom, header bersih, dan perilaku tampilan tabel pratinjau."""
        super().__init__(0, len(self.COLUMNS), parent)
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWordWrap(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self._items: list[FilePlanItem] = []
        self._row_checkboxes: list[FluentCheckBox] = []
        self._row_checkbox_containers: list[QWidget] = []
        self._row_status_widgets: list[StatusBadgeWidget] = []
        self._rename_rows: dict[
            int,
            tuple[QWidget, ElidedLabel, ElidedLabel, QPushButton, QPushButton],
        ] = {}
        self._current_filter_mode: str = "all"

        vertical_header = self.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
            vertical_header.setDefaultSectionSize(46)

        horizontal_header = self.horizontalHeader()
        if horizontal_header is not None:
            horizontal_header.setMinimumSectionSize(44)
            horizontal_header.setDefaultAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            horizontal_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(0, 52)
            horizontal_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            horizontal_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            horizontal_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(3, 176)

    @staticmethod
    def _is_rename_eligible(item: FilePlanItem) -> bool:
        """Memeriksa apakah item memiliki usulan rename yang dapat disetujui/ditolak."""
        return bool(
            item.suggested_name
            and item.suggested_name.strip()
            and not item.is_skipped
            and not item.is_duplicate
        )

    @classmethod
    def _sort_key(cls, item: FilePlanItem) -> tuple[int, str]:
        """Menentukan urutan visual baris: usulan nama -> siap -> duplikat/usang -> cek manual."""
        if cls._is_rename_eligible(item):
            tier = 0
        elif item.is_skipped:
            tier = 3
        elif item.is_duplicate or item.is_obsolete_temp:
            tier = 2
        else:
            tier = 1
        return (tier, item.file_name.lower())

    def populate_items(self, items: list[FilePlanItem]) -> None:
        """Mengisi tabel dengan FilePlanItem terurut cerdas, checkbox Fluent, dan kontrol rename."""
        self._items = sorted(items, key=self._sort_key)
        self._row_checkboxes.clear()
        self._row_checkbox_containers.clear()
        self._row_status_widgets.clear()
        self._rename_rows.clear()
        self._current_filter_mode = "all"

        self.setRowCount(0)
        self.setRowCount(len(self._items))

        italic_font = QFont()
        italic_font.setItalic(True)

        for row_idx, item in enumerate(self._items):
            size_text = _format_file_size(item.file_size)

            # Kolom 0: Checkbox kustom Fluent untuk pengecualian per file
            cb_container = QWidget(self)
            cb_container.setObjectName("CheckboxCellContainer")
            cb_container.setProperty("renameHighlighted", False)
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            checkbox = FluentCheckBox(cb_container)
            if item.is_skipped:
                checkbox.setChecked(False)
                checkbox.setEnabled(False)
                checkbox.setToolTip("File ini dibiarkan tetap di folder asal")
            else:
                checkbox.setChecked(True)
                checkbox.setEnabled(True)
                checkbox.setToolTip("Centang untuk menyertakan file ini saat dirapikan")
            checkbox.toggled.connect(lambda _checked: self.selection_changed.emit())
            cb_layout.addWidget(checkbox)

            self.setItem(row_idx, 0, QTableWidgetItem(""))
            self.setCellWidget(row_idx, 0, cb_container)
            self._row_checkboxes.append(checkbox)
            self._row_checkbox_containers.append(cb_container)

            # Kolom 1: Nama file normal atau kartu usulan nama baru 2 baris
            if self._is_rename_eligible(item):
                self.setRowHeight(row_idx, 62)
                rename_container = QWidget(self)
                rename_container.setObjectName("RenameCellContainer")
                rename_container.setProperty("renameHighlighted", False)

                rename_layout = QHBoxLayout(rename_container)
                rename_layout.setContentsMargins(10, 6, 10, 6)
                rename_layout.setSpacing(8)

                text_stack = QVBoxLayout()
                text_stack.setContentsMargins(0, 0, 0, 0)
                text_stack.setSpacing(2)

                orig_label = ElidedLabel(
                    item.file_name,
                    elide_mode=Qt.TextElideMode.ElideRight,
                    parent=rename_container,
                )
                orig_label.setObjectName("RenameOrigLabel")
                orig_label.setProperty("approved", True)

                sugg_label = ElidedLabel(
                    f"➔ {item.suggested_name or ''}",
                    elide_mode=Qt.TextElideMode.ElideRight,
                    parent=rename_container,
                )
                sugg_label.setObjectName("RenameSuggLabel")
                sugg_label.setProperty("approved", True)

                rename_tooltip = (
                    f"Nama asli: {item.file_name}\n"
                    f"Usulan nama baru: {item.suggested_name}\n"
                    f"Ukuran file: {size_text}"
                )
                rename_container.setToolTip(rename_tooltip)
                orig_label.setToolTip(rename_tooltip)
                sugg_label.setToolTip(rename_tooltip)

                text_stack.addWidget(orig_label)
                text_stack.addWidget(sugg_label)

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

                rename_layout.addLayout(text_stack, stretch=1)
                rename_layout.addWidget(accept_btn)
                rename_layout.addWidget(reject_btn)

                col1_item = QTableWidgetItem("")
                col1_item.setToolTip(rename_tooltip)
                self.setItem(row_idx, 1, col1_item)
                self.setCellWidget(row_idx, 1, rename_container)
                self._rename_rows[row_idx] = (
                    rename_container,
                    orig_label,
                    sugg_label,
                    accept_btn,
                    reject_btn,
                )
            else:
                self.setRowHeight(row_idx, 46)
                name_item = QTableWidgetItem(item.file_name)
                name_item.setToolTip(f"Nama file: {item.file_name}\nUkuran file: {size_text}")
                if item.is_skipped:
                    name_item.setForeground(QBrush(QColor("#64748B")))
                else:
                    name_item.setForeground(QBrush(QColor("#18181B")))
                self.setItem(row_idx, 1, name_item)

            # Kolom 2: Folder Tujuan
            if item.is_skipped:
                category_item = QTableWidgetItem("(Tetap di Folder Ini)")
                category_item.setForeground(QBrush(QColor("#64748B")))
                category_item.setFont(italic_font)
                category_item.setToolTip("File ini tidak dipindahkan dan tetap di folder asal.")
            else:
                category_item = QTableWidgetItem(item.category)
                category_item.setForeground(QBrush(QColor("#334155")))
                category_item.setToolTip(item.proposed_path or item.category)
            self.setItem(row_idx, 2, category_item)

            # Kolom 3: Pill Badge Status
            if item.is_skipped:
                status_text = "Perlu Cek Manual"
                status_variant = "muted"
                status_tooltip = (
                    "Dibiarkan di tempat asal karena kategori/isi perlu pengecekan manual."
                )
            elif item.is_obsolete_temp or item.status_label == "Installer Usang":
                status_text = item.status_label or "Installer Usang"
                status_variant = "warning"
                status_tooltip = "File installer atau arsip sementara yang sudah berumur lama."
            elif item.is_duplicate or item.status_label == "File Duplikat":
                status_text = item.status_label or "File Duplikat"
                status_variant = "warning"
                status_tooltip = (
                    "File kembar (isi identik SHA-256) yang akan diamankan ke _Karantina_Duplikat."
                )
            else:
                status_text = item.status_label or "Siap Dirapikan"
                status_variant = "ready"
                status_tooltip = f"Siap dipindahkan ke folder {item.category}."

            badge_widget = StatusBadgeWidget(
                text=status_text,
                variant=status_variant,
                tooltip=status_tooltip,
                parent=self,
            )
            self.setItem(row_idx, 3, QTableWidgetItem(""))
            self.setCellWidget(row_idx, 3, badge_widget)
            self._row_status_widgets.append(badge_widget)

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
        """Memperbarui highlight baris hijau lembut, format 2 baris, dan tombol `[✓][✕]`."""
        item = self._items[row_idx]
        approved = bool(item.is_rename_approved)
        container, orig_label, sugg_label, accept_btn, reject_btn = self._rename_rows[row_idx]
        cb_container = self._row_checkbox_containers[row_idx]
        status_badge = self._row_status_widgets[row_idx]

        orig_label.setProperty("approved", approved)
        sugg_label.setProperty("approved", approved)

        sugg_font = sugg_label.font()
        sugg_font.setStrikeOut(not approved)
        sugg_label.setFont(sugg_font)

        accept_btn.setProperty("active", approved)
        reject_btn.setProperty("active", not approved)
        container.setProperty("renameHighlighted", approved)
        cb_container.setProperty("renameHighlighted", approved)
        status_badge.set_rename_highlighted(approved)

        row_brush = QBrush(QColor("#F0FDF4")) if approved else QBrush()
        for col in (0, 1, 2, 3):
            cell_item = self.item(row_idx, col)
            if cell_item is not None:
                cell_item.setBackground(row_brush)

        for widget in (container, cb_container, orig_label, sugg_label, accept_btn, reject_btn):
            _repolish_widget(widget)

        orig_label.update_elision()
        sugg_label.update_elision()

    def set_all_renames_approved(self, approved: bool) -> None:
        """Menerima atau menolak seluruh usulan rename yang ada di tabel sekaligus."""
        if not self._rename_rows:
            return
        for row_idx in self._rename_rows:
            self._items[row_idx].is_rename_approved = approved
            self._refresh_rename_row_visual(row_idx)
        self.rename_approval_changed.emit()

    def set_filter_mode(self, mode: str) -> None:
        """Menyaring baris yang tampak menggunakan `setRowHidden` tanpa me-reset pilihan."""
        self._current_filter_mode = mode
        for row_idx, item in enumerate(self._items):
            if mode == "rename":
                visible = self._is_rename_eligible(item)
            elif mode == "duplicate":
                visible = bool(item.is_duplicate or item.is_obsolete_temp)
            elif mode == "manual":
                visible = bool(item.is_skipped)
            else:
                visible = True
            self.setRowHidden(row_idx, not visible)

    def get_filter_counts(self) -> dict[str, int]:
        """Menghitung jumlah item per kategori tab filter pada seluruh isi tabel."""
        rename_count = sum(1 for item in self._items if self._is_rename_eligible(item))
        obsolete_count = sum(
            1 for item in self._items if item.is_obsolete_temp and not item.is_duplicate
        )
        duplicate_count = sum(
            1 for item in self._items if item.is_duplicate or item.is_obsolete_temp
        )
        manual_count = sum(1 for item in self._items if item.is_skipped)
        return {
            "total": len(self._items),
            "rename": rename_count,
            "duplicate": duplicate_count,
            "obsolete": obsolete_count,
            "manual": manual_count,
        }

    def get_selected_items(self) -> list[FilePlanItem]:
        """Mengembalikan seluruh item tercentang di semua tab (termasuk baris tersembunyi)."""
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
        """Menghitung ringkasan pilihan di seluruh baris tanpa terpengaruh filter tab aktif."""
        selected_ready = 0
        selected_obsolete = 0
        selected_duplicates = 0
        manual_check_count = 0
        unchecked_count = 0

        for item, cb in zip(self._items, self._row_checkboxes):
            if item.is_skipped:
                manual_check_count += 1
            elif cb.isChecked():
                if item.is_duplicate:
                    selected_duplicates += 1
                elif item.is_obsolete_temp:
                    selected_obsolete += 1
                else:
                    selected_ready += 1
            else:
                unchecked_count += 1

        return {
            "total_files": len(self._items),
            "selected_ready": selected_ready,
            "selected_obsolete": selected_obsolete,
            "selected_duplicates": selected_duplicates,
            "manual_check_count": manual_check_count,
            "unchecked_count": unchecked_count,
            "selected_total": selected_ready + selected_obsolete + selected_duplicates,
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

        self.title_label = QLabel("Tidak Ada File yang Perlu Dirapikan", self)
        self.title_label.setObjectName("EmptyStateTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.desc_label = QLabel(
            "Folder ini kosong atau seluruh file sudah tersimpan rapi di dalam subfolder.",
            self,
        )
        self.desc_label.setObjectName("EmptyStateDescLabel")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)
