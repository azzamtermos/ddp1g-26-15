# Proposal Arsitektur & Rencana Kerja (Implementation Plan) — Versi 0.1
**Proyek Kelompok DDP 1: Smart File Organizer (Python & PyQt6)**

---

## Ringkasan Kepatuhan Standar Proyek (`.agent/skills/`)
Proposal ini dirancang dengan mematuhi seluruh aturan proyek di folder `.agent/skills/`:
1. **`pyqt6-architecture`**:
   - Pemisahan ketat antara antarmuka (`ui/`) dan logika manipulasi file (`core/`). Modul `ui/` sama sekali tidak mengimpor `os`, `shutil`, atau `pathlib` untuk operasi file.
   - Seluruh operasi berat (pemindaian folder, kalkulasi hash SHA-256, ekstraksi teks PDF, dan pemindahan file) dijalankan di *background thread* menggunakan `QThread` agar aplikasi bebas *freeze* (*Not Responding*).
   - Seluruh pengaturan warna, font, dan *padding* dipisahkan ke dalam `ui/styles.qss`.
   - Kode ramah tingkat DDP1 dengan *type hints* lengkap dan *docstring* berbahasa Indonesia pada setiap *class* serta *method* utama.
2. **`modern-pyqt-ux`**:
   - Palet warna lembut & modern: latar belakang `#F8FAFC`, permukaan kartu `#FFFFFF` dengan border `#E2E8F0`, tombol utama biru `#2563EB` (hover `#1D4ED8`).
   - Sudut membulat (`border-radius: 8px` untuk tombol/input, `12px` untuk kartu), jarak antar-elemen lega (`spacing >= 12px`, `margin >= 24px`), dan font modern (`Segoe UI`, `Inter`, `Ubuntu`) ukuran minimal `13px` (judul `18px–20px` *bold*).
   - Bahasa manusiawi yang ramah pengguna awam: **"Pilih Folder Berantakan"**, **"Lihat Rencana Rapikan"**, **"Rapikan Sekarang"**, dan **"Batalkan (Undo)"**.
   - Fokus visual berupa area *drag-and-drop* besar bergaris putus-putus (*dashed border*) di bagian atas dan tabel *preview* dengan indikator badge warna lembut (hijau untuk file siap dirapikan, kuning/oranye untuk file duplikat).
3. **`safe-file-ops`**:
   - Seluruh manipulasi path wajib menggunakan `pathlib.Path` (lintas platform Windows & Linux, tanpa penggabungan string `+`).
   - Dilarang menghapus file secara permanen (`os.remove`, `os.unlink`, `shutil.rmtree` dilarang keras); pembersihan file duplikat/sampah wajib menggunakan `send2trash` ke *Recycle Bin*.
   - Wajib mencatat riwayat transaksi ke `data/undo_history.json` (`{"old_path": "...", "new_path": "..."}`) sebelum memindahkan/mengubah nama file untuk mendukung fitur **1-Click Undo**.
   - Penanganan konflik nama otomatis dengan penomoran (`_1`, `_2`, dst.) tanpa menimpa file lama, serta penanganan `PermissionError` (misal saat file sedang dibuka di Word/PDF Reader) secara anggun tanpa membuat aplikasi *crash*.

---

## 1. Struktur Folder dan File Lengkap

```text
ddp1g-26-15/
├── main.py                      # Entry point aplikasi: inisialisasi QApplication, muat styles.qss, buka MainWindow
├── requirements.txt             # Daftar dependensi (PyQt6, Send2Trash, pypdf, pytest)
├── ui/                          # Paket Antarmuka Pengguna (HANYA tampilan & event UI, tanpa os/shutil/pathlib)
│   ├── __init__.py
│   ├── main_window.py           # Jendela utama (MainWindow) yang menyatukan seluruh komponen & mengatur QThread
│   ├── widgets.py               # Komponen visual kustom: DropZoneWidget (drag-and-drop) & PreviewTableWidget
│   ├── worker.py                # Subclass QThread untuk menjalankan proses core/ di background (anti-freeze)
│   └── styles.qss               # Lembar gaya terpusat (palet warna #F8FAFC, #2563EB, border-radius, font, padding)
├── core/                        # Paket Logika Bisnis & Manipulasi File (menggunakan pathlib.Path & send2trash)
│   ├── __init__.py
│   ├── models.py                # Dataclass kontrak data antar-modul (FilePlanItem, TransactionRecord)
│   ├── scanner.py               # Pemindai folder, kategorisasi ekstensi, & ekstraksi kata kunci dokumen/PDF
│   ├── duplicate_finder.py      # Pendeteksi file duplikat menggunakan hashing (SHA-256) bertahap
│   └── organizer.py             # Eksekutor pemindahan file, penomoran otomatis (_1, _2), send2trash, & Undo JSON
├── data/                        # Penyimpanan aturan & riwayat transaksi lokal
│   ├── .gitkeep                 # Menjaga folder tetap terlacak di Git
│   ├── default_rules.json       # Aturan pengelompokan kategori folder default (Dokumen Guru, Gambar, Arsip, dll.)
│   └── undo_history.json        # Log transaksi terakhir untuk fitur "Batalkan (Undo)" 1-klik
└── tests/                       # Paket pengujian unit (Unit Tests) untuk setiap modul core/
    ├── __init__.py
    ├── test_scanner.py
    ├── test_duplicate_finder.py
    └── test_organizer.py
```

---

## 2. Rancangan Class, Method, dan Alur Signals & Slots (`ui/` ↔ `core/`)

### A. Kontrak Data (`core/models.py`)
Struktur data seragam untuk komunikasi antara modul `core/` dan `ui/`:

```python
from dataclasses import dataclass

@dataclass
class FilePlanItem:
    """Representasi rencana perapian untuk satu file yang dipindai."""
    source_path: str       # Path asli file (string dari pathlib.Path)
    file_name: str         # Nama file beserta ekstensinya
    file_size: int         # Ukuran file dalam bytes (untuk optimasi cek duplikat)
    category: str          # Kategori tujuan (misal: "Dokumen_Ajar", "Gambar", "Arsip")
    proposed_path: str     # Rencana path baru setelah dirapikan
    is_duplicate: bool = False
    status_label: str = "Siap Dirapikan"  # "Siap Dirapikan" (Hijau) atau "File Duplikat" (Oranye)
```

### B. Kerangka Modul Logika (`core/`)
Seluruh fungsi di `core/` dilengkapi *type hints* dan *docstring* Bahasa Indonesia yang jelas:

1. **`core/scanner.py` — `class FolderScanner`**
   - `__init__(self, rules_path: str = "data/default_rules.json") -> None`: Memuat aturan pengelompokan ekstensi dan kata kunci dari file JSON menggunakan `pathlib.Path`.
   - `scan_directory(self, folder_path: str) -> list[FilePlanItem]`: Memindai seluruh file tingkat pertama di dalam `folder_path` (mengabaikan subfolder yang sudah rapi dan file tersembunyi), lalu mengembalikan daftar `FilePlanItem`.
   - `determine_category(self, file_path: Path) -> str`: Menentukan kategori folder berdasarkan ekstensi dan kata kunci nama/isi file (misal: RPP, Silabus, Nilai, Soal).
   - `extract_document_hint(self, file_path: Path) -> str | None`: Membaca halaman pertama PDF/dokumen untuk mendeteksi kata kunci tambahan.

2. **`core/duplicate_finder.py` — `class DuplicateFinder`**
   - `calculate_file_hash(self, file_path: Path, chunk_size: int = 65536) -> str`: Menghitung nilai hash SHA-256 dari isi file secara bertahap per *chunk* agar aman untuk file berukuran besar.
   - `mark_duplicates(self, items: list[FilePlanItem]) -> list[FilePlanItem]`: Mengelompokkan item berdasarkan `file_size` terlebih dahulu, kemudian membandingkan hash SHA-256 hanya pada ukuran yang sama, lalu mengubah `is_duplicate = True` dan `status_label = "File Duplikat"` pada file kembar.

3. **`core/organizer.py` — `class SafeFileOrganizer`**
   - `__init__(self, undo_log_path: str = "data/undo_history.json") -> None`: Menyiapkan path penyimpanan log transaksi Undo.
   - `resolve_conflict_path(self, target_path: Path) -> Path`: Memeriksa apakah `target_path` sudah ada; jika sudah ada, menghasilkan nama baru dengan penomoran otomatis (`nama_1.pdf`, `nama_2.pdf`, dst.) tanpa menimpa file lama.
   - `save_undo_log(self, transactions: list[dict[str, str]]) -> None`: Menyimpan daftar transaksi `{"old_path": "...", "new_path": "..."}` ke `data/undo_history.json` sebelum atau saat pemindahan berlangsung.
   - `execute_plan(self, items: list[FilePlanItem], send_duplicates_to_trash: bool = False) -> tuple[int, list[str]]`: Mengeksekusi pemindahan file menggunakan `pathlib.Path.rename()` / `shutil.move()`, memindahkan duplikat ke *Recycle Bin* via `send2trash` (bila diaktifkan), mencatat log Undo, serta menangkap `PermissionError` agar aplikasi tidak *crash* dan mengembalikan `(jumlah_berhasil, daftar_pesan_error)`.
   - `undo_last_operation(self) -> tuple[int, list[str]]`: Membaca `data/undo_history.json` dan mengembalikan seluruh file dari `new_path` ke `old_path` secara aman.

### C. Rancangan Komponen Antarmuka & Worker Thread (`ui/`)
Sesuai dokumentasi resmi **PyQt6** (terverifikasi via Context7 `/websites/riverbankcomputing_static_pyqt6`), seluruh `pyqtSignal` dideklarasikan sebagai *class attribute* pada subclass `QObject` / `QThread`:

1. **`ui/widgets.py`**
   - `class DropZoneWidget(QFrame)`:
     - Signal: `folder_selected = pyqtSignal(str)`
     - Method: `dragEnterEvent`, `dropEvent`, `_on_browse_clicked()` (membuka `QFileDialog.getExistingDirectory` melalui tombol **"Pilih Folder Berantakan"**).
   - `class PreviewTableWidget(QTableWidget)`:
     - Method: `populate_items(self, items: list[FilePlanItem]) -> None` (menampilkan rencana perapian dengan badge warna hijau `#DCFCE7` / teks `#166534` untuk `"Siap Dirapikan"` dan kuning/oranye `#FEF3C7` / teks `#92400E` untuk `"File Duplikat"`).

2. **`ui/worker.py`**
   - `class ScanWorker(QThread)`:
     - Signals:
       - `progress_updated = pyqtSignal(int, str)`
       - `scan_finished = pyqtSignal(list)` *(mengirimkan `list[FilePlanItem]`)*
       - `error_occurred = pyqtSignal(str)`
     - Method: `run(self) -> None` (memanggil `FolderScanner.scan_directory` lalu `DuplicateFinder.mark_duplicates`).
   - `class OrganizeWorker(QThread)`:
     - Signals:
       - `progress_updated = pyqtSignal(int, str)`
       - `operation_finished = pyqtSignal(int, list)` *(mengirimkan `jumlah_berhasil` dan `daftar_error`)*
       - `error_occurred = pyqtSignal(str)`
     - Method: `run(self) -> None` (menjalankan `SafeFileOrganizer.execute_plan` atau `undo_last_operation` sesuai mode yang dipilih).

3. **`ui/main_window.py` — `class MainWindow(QMainWindow)`**
   - Mengintegrasikan `DropZoneWidget`, `PreviewTableWidget`, dan bar tombol tindakan dengan label ramah pengguna:
     - **"Pilih Folder Berantakan"**
     - **"Lihat Rencana Rapikan"**
     - **"Rapikan Sekarang"**
     - **"Batalkan (Undo)"**
   - Mengelola siklus hidup thread dan menonaktifkan tombol selama proses berjalan agar aman dari klik ganda.

---

## 3. Rincian Tugas dalam 4 Fase Pengerjaan

### Fase 1: Fondasi Proyek, Konfigurasi Data & Kontrak Model
- Menyiapkan daftar dependensi di `requirements.txt` (`PyQt6`, `Send2Trash`, `pypdf`, `pytest`).
- Membuat paket `core/__init__.py` dan kontrak data `core/models.py` (`FilePlanItem`, `TransactionRecord`).
- Menyiapkan folder `data/` beserta aturan pengelompokan kategori default di `data/default_rules.json`.

### Fase 2: Modul Logika `core/` (Scanner, Duplicate Finder & Safe Organizer)
- Membuat `core/scanner.py` (`FolderScanner`) untuk memindai direktori dengan `pathlib.Path`, menentukan kategori file, dan menyiapkan ekstraksi kata kunci dokumen/PDF.
- Membuat `core/duplicate_finder.py` (`DuplicateFinder`) untuk mendeteksi file duplikat menggunakan filter ukuran file dan hash SHA-256 per *chunk*.
- Membuat `core/organizer.py` (`SafeFileOrganizer`) untuk mengeksekusi pemindahan file, menangani konflik nama (`_1`, `_2`), mencatat dan memulihkan transaksi Undo (`data/undo_history.json`), serta menangani `PermissionError`.

### Fase 3: Antarmuka PyQt6 Modern, QSS & Background Worker (`ui/` & `main.py`)
- Membuat lembar gaya terpusat `ui/styles.qss` sesuai palet warna dan tipografi `modern-pyqt-ux`.
- Membuat komponen kustom `ui/widgets.py` (`DropZoneWidget` & `PreviewTableWidget`).
- Membuat worker thread `ui/worker.py` (`ScanWorker` & `OrganizeWorker` berbasis `QThread`).
- Membuat jendela utama `ui/main_window.py` (`MainWindow`) dan *entry point* aplikasi `main.py`.

### Fase 4: Pengujian Unit (`tests/`)
- Membuat paket pengujian `tests/__init__.py`.
- Membuat pengujian unit `tests/test_scanner.py`, `tests/test_duplicate_finder.py`, dan `tests/test_organizer.py` menggunakan `pytest` dan fixture direktori sementara (`tmp_path`).
