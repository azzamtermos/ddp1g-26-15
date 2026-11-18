# Smart File Organizer

Aplikasi desktop berbasis **Python** dan **PyQt6** untuk merapikan folder yang berantakan secara otomatis, mendeteksi file kembar (duplikat) dengan aman, menandai installer usang, serta menyediakan fitur **1-Click Undo** untuk mengembalikan perubahan kapan saja.

---

## 1. Latar Belakang Masalah

Banyak pengguna komputer—khususnya pengajar, pelajar, dan staf administrasi—sering menumpuk ratusan dokumen (`RPP`, `Silabus`, `Rekap Nilai`, `Materi`, `Soal`, foto dokumentasi, hingga file installer) di dalam satu folder seperti *Downloads* atau *Documents*. Masalah yang sering muncul meliputi:
- **Sulit mencari dokumen penting** karena nama file tidak seragam dan bercampur di satu tempat.
- **Penyimpanan penuh tanpa disadari** akibat banyaknya file duplikat yang terunduh berulang kali serta file installer lama yang tidak lagi terpakai.
- **Kekhawatiran kehilangan file** saat menggunakan aplikasi pembersih otomatis yang menghapus file secara permanen tanpa fitur pembatalan (*Undo*).

**Smart File Organizer** hadir dengan pendekatan **Aman & Ramah Pengguna**:
1. **Pratinjau Otomatis (*Auto-Scan Preview*):** Begitu folder dipilih atau ditarik (*drag-and-drop*), aplikasi langsung menampilkan rencana pengelompokan file beserta estimasi ruang penyimpanan yang bisa dihemat sebelum memindahkan apa pun.
2. **Karantina Duplikat & 100% Undo-able:** File kembar tidak langsung dihapus, melainkan dipindahkan ke subfolder `_Karantina_Duplikat/` dan dicatat ke log transaksi lokal sehingga 100% file dapat dikembalikan ke posisi semula lewat tombol **"Batalkan (Undo)"**.
3. **Pembersihan Aman ke Sampah (*Recycle Bin*):** Dilarang keras menghapus file secara permanen (`os.remove` / `shutil.rmtree`). Pembersihan isi karantina menggunakan `send2trash` agar tetap masuk ke *Recycle Bin* / *Trash* sistem operasi.

---

## 2. Struktur Folder Proyek

```text
ddp1g-26-15/
├── .gitignore                   # Mengabaikan data/undo_history.json, .env, __pycache__/, .venv/
├── main.py                      # Entry point aplikasi: inisialisasi QApplication, muat styles.qss, buka MainWindow
├── requirements.txt             # Daftar dependensi proyek
├── README.md                    # Dokumentasi utama proyek
├── docs/                        # Dokumen proposal arsitektur & rencana kerja
│   ├── proposal_0_1.md
│   └── proposal_0_2.md
├── ui/                          # Paket Antarmuka Pengguna (PyQt6, QThread, & QSS)
│   ├── __init__.py
│   ├── main_window.py           # Jendela utama (MainWindow) & integrasi alur auto-scan
│   ├── widgets.py               # Komponen kustom: DropZoneWidget & PreviewTableWidget
│   ├── worker.py                # Background worker (ScanWorker & OrganizeWorker berbasis QThread)
│   └── styles.qss               # Lembar gaya terpusat (palet warna modern & tipografi)
├── core/                        # Paket Logika Bisnis & Manipulasi File (pathlib.Path & send2trash)
│   ├── __init__.py
│   ├── models.py                # Kontrak dataclass (FilePlanItem & TransactionRecord)
│   ├── scanner.py               # Pemindai folder, kategorisasi pintar, & AI Hybrid Smart Renaming
│   ├── duplicate_finder.py      # Pendeteksi duplikat (SHA-256), installer usang, & kalkulator ruang hemat
│   └── organizer.py             # Eksekutor pemindahan, karantina duplikat, send2trash, & 1-Click Undo
├── data/                        # Penyimpanan aturan kategori & riwayat transaksi
│   ├── .gitkeep
│   ├── default_rules.json       # Aturan pengelompokan kategori default
│   └── (undo_history.json)      # Dibuat otomatis saat runtime (diabaikan oleh Git)
└── tests/                       # Paket pengujian unit (pytest)
    ├── __init__.py
    ├── test_scanner.py
    ├── test_duplicate_finder.py
    └── test_organizer.py
```

---

## 3. Daftar Modul & Cakupan File Eksklusif

Setiap modul dirancang terpisah agar pengembangan paralel bebas dari *merge conflict*:

| Modul | File Cakupan | Lingkup Fungsional |
| :--- | :--- | :--- |
| **UI/UX, QSS & Threading** | `main.py`, `ui/main_window.py`, `ui/widgets.py`, `ui/worker.py`, `ui/styles.qss` | Antarmuka PyQt6 modern, area *drag-and-drop* dengan *auto-scan*, `QProgressBar` *real-time*, tabel pratinjau ber-badge warna, dan integrasi `QThread`. |
| **Folder Scanner & Smart Categorizer** | `core/scanner.py`, `data/default_rules.json`, `tests/test_scanner.py` | Pemindaian direktori berbasis `pathlib.Path`, aturan pengelompokan kategori dokumen, ekstraksi teks PDF (`extract_document_hint`), dan penamaan pintar (`propose_smart_name`). |
| **Duplicate & Storage Analyzer** | `core/duplicate_finder.py`, `tests/test_duplicate_finder.py` | Deteksi file duplikat dua tahap (ukuran file + hash `SHA-256` per *chunk*), penandaan installer/file sementara usang (`detect_obsolete_installers`), dan kalkulasi ruang hemat (`calculate_wasted_space`). |
| **Safe File Organizer & 1-Click Undo** | `core/organizer.py`, `tests/test_organizer.py` | Inisialisasi otomatis `data/undo_history.json`, resolusi konflik nama (`_1`, `_2`), karantina duplikat ke `_Karantina_Duplikat/`, pemulihan 100% file via Undo, dan pembersihan karantina ke *Recycle Bin* via `send2trash`. |

---

## 4. Cara Instalasi & Menjalankan Aplikasi

### A. Persiapan Virtual Environment
```bash
# 1. Buat virtual environment Python
python3 -m venv .venv

# 2. Aktifkan virtual environment
# Untuk Linux / macOS:
source .venv/bin/activate
# Untuk Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. Instal seluruh dependensi
pip install -r requirements.txt
```

### B. Menjalankan Aplikasi
```bash
python3 main.py
```

### C. Menjalankan Pengujian Unit (*Unit Tests*)
```bash
pytest -v
```

---

## 5. Panduan Alur Kerja Git (*Git Branch Workflow*)

Agar riwayat repositori tetap rapi dan bebas konflik saat bekerja bersama:

1. **Selalu tarik perubahan terbaru dari `main` sebelum mulai bekerja:**
   ```bash
   git checkout main
   git pull origin main
   ```
2. **Buat *branch* fitur sesuai modul yang dikerjakan:**
   ```bash
   git checkout -b feat/nama-fitur
   # Contoh:
   # git checkout -b feat/scanner-smart-rename
   # git checkout -b feat/duplicate-analyzer
   # git checkout -b feat/safe-organizer-undo
   # git checkout -b feat/ui-filter-enhancements
   ```
3. **Pastikan seluruh pengujian `pytest` lulus sebelum melakukan *commit*:**
   ```bash
   pytest -v
   git add <file-yang-diubah>
   git commit -m "feat(modul): deskripsi singkat perubahan"
   ```
4. **Unggah *branch* ke GitHub dan buat *Pull Request* (PR) ke `main`:**
   ```bash
   git push -u origin feat/nama-fitur
   ```
