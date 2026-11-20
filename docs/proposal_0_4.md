# Proposal Desain UI/UX v0.4 — Rapihin Aja (Windows 11 Fluent + Notion Minimalist)

Dokumen ini menjadi acuan desain untuk pemolesan antarmuka desktop **Rapihin Aja** (`ui/`) agar tampil seperti aplikasi utilitas Windows resmi yang tenang, ringan, bersih, dan langsung dipercaya oleh guru serta pengguna awam.

---

## 1. Tujuan & Prinsip Desain

1. **Progressive Disclosure (2 Fase Tampilan):**
   - **Welcome State** (sebelum folder dipilih) hanya menampilkan kanvas fokus untuk memilih/menarik folder, sinyal kepercayaan, dan tautan/tombol *Undo* terakhir — tanpa tabel kosong atau tombol nonaktif yang membebani mata.
   - **Active State** (setelah folder dipilih) otomatis menyusutkan area drag-and-drop menjadi 1 baris toolbar kompak agar **lebih dari 65% tinggi jendela** didedikasikan untuk pratinjau file.
2. **Hierarki Aksi Tunggal:** Hanya ada **1 tombol CTA biru dominan** (`Rapikan Sekarang (N)`); seluruh aksi sekunder (`Ganti Folder`, `Pindai Ulang`, `Batalkan (Undo)`, `Bersihkan Karantina ke Sampah`) memakai gaya netral agar tidak bersaing perhatian.
3. **Tenang & Bebas Kebisingan Visual:** Progres bar tipis (`4px`) hanya muncul saat proses latar belakang berjalan, status tabel memakai *pill badge* lembut, dan warna peringatan hangat pada tombol karantina muncul hanya saat *hover*.
4. **Ruang Lingkup Ketat:** Perubahan **hanya** dilakukan pada berkas di dalam `ui/` (`styles.qss`, `widgets.py`, `main_window.py`, `__init__.py`) dan dokumen ini, tanpa menyentuh `core/`, `data/`, `scripts/`, `main.py`, maupun `tests/`.

---

## 2. Arsitektur 2 Fase Tampilan

### A. Welcome State (`current_folder == ""`)

```text
+------------------------------------------------------------------------+
|  Rapihin Aja                                                           |
|  Rapikan folder berantakan, amankan file kembar, dan batalkan 1 klik.  |
|                                                                        |
|                        ( ruang napas lega )                            |
|                                                                        |
|      + - - - - - - - - - - - - - - - - - - - - - - - - - - - - +       |
|      |      Tarik & Lepas Folder Berantakan ke Sini            |       |
|      |  Atau klik tombol di bawah untuk memilih folder         |       |
|      |                                                         |       |
|      |             [ Pilih Folder Berantakan ]                 |       |
|      |                                                         |       |
|      |  100% Offline  •  Subfolder Aman  •  Bisa Dibatalkan    |       |
|      + - - - - - - - - - - - - - - - - - - - - - - - - - - - - +       |
|                                                                        |
|                        ( ruang napas lega )                            |
|                                                                        |
|  [ Batalkan Perapian Terakhir (Undo) ]                                 |
+------------------------------------------------------------------------+
```

### B. Active State (`current_folder != ""`)

```text
+------------------------------------------------------------------------+
|  Rapihin Aja                                                           |
|  Rapikan folder berantakan, amankan file kembar, dan batalkan 1 klik.  |
|                                                                        |
|  +------------------------------------------------------------------+  |
|  | [Folder Aktif]  /home/guru/Downloads/...       [ Ganti Folder ]  |  |
|  +------------------------------------------------------------------+  |
|  (Saat scan/proses berjalan: Strip progres 4px + label status tipis)   |
|                                                                        |
|  [Kartu Ringkasan]  12 siap dirapikan • 2 duplikat • Hemat 14.2 MB     |
|                                                                        |
|  [Semua (15)]  [Usulan Nama (3)]  [Duplikat (2)]  [Cek Manual (1)]     |
|  +------------------------------------------------------------------+  |
|  | [Usulan Nama] 3 usulan nama baru otomatis (3 disetujui) [✓] [✕]  |  |
|  +------------------------------------------------------------------+  |
|  +------------------------------------------------------------------+  |
|  | Pilih | Nama File & Usulan Nama Baru    | Folder Tujuan | Status |  |
|  |-------|---------------------------------|---------------|--------|  |
|  |  [✓]  | DOC-20261118-WA0004.pdf         | Soal_dan_     | (pill) |  |
|  |       | -> Soal_PTS_Ganjil.pdf  [✓][✕]  | Ujian         |        |  |
|  |  [✓]  | modul_ipa_bab2.pdf              | Materi_dan... | (pill) |  |
|  +------------------------------------------------------------------+  |
|                                                                        |
|  [Pindai Ulang] [Batalkan (Undo)] [Bersihkan Karantina] [Rapikan (14)] |
+------------------------------------------------------------------------+
```

---

## 3. Komponen Kustom (`ui/widgets.py`)

| Komponen | Fungsi Utama |
| :--- | :--- |
| `FluentCheckBox` | Checkbox kustom via `QPainter` (`18x18`, radius `5px`, centang putih bersih di atas aksen `#0067C0`) tanpa dependensi aset eksternal. |
| `ElidedPathLabel` | Label alamat folder dengan pemotongan tengah (`ElideMiddle`) otomatis beserta tooltip alamat lengkap. |
| `CollapsibleDropZoneWidget` | DropZone 2 mode: *Hero Card* pada Welcome State dan *Compact Toolbar* 1 baris pada Active State; tetap menerima *drag-and-drop* di kedua mode. Alias `DropZoneWidget` dipertahankan. |
| `FluentProgressStrip` | Indikator progres tipis `4px` + pesan status yang otomatis tersembunyi ketika tidak ada operasi berjalan. |
| `FilterBarWidget` | Tab pill minimalis (`Semua`, `Usulan Nama`, `Duplikat`, `Cek Manual`) dengan hitungan langsung per kategori. |
| `RenameBannerWidget` | Banner aksi massal persetujuan *Smart Rename* dengan pill `Usulan Nama` tanpa emoji dan tombol `[✓ Terima Semua]` / `[✕ Tolak Semua]`. |
| `StatusBadgeWidget` | Pill status terpusat (`Siap Dipindahkan`, `File Duplikat`, `Installer Usang`, `Perlu Cek Manual`) di dalam kontainer transparan. |
| `PreviewTableWidget` | Tabel pratinjau Notion-style dengan pengurutan baris cerdas, baris usulan nama 2 tingkat (`62px`), tooltip detail & ukuran file, serta highlight `#F0FDF4`. |
| `EmptyStateWidget` | Kartu pesan kondisi kosong yang selaras dengan kanvas putih Fluent/Notion. |

---

## 4. Sistem Token Visual

- **Kanvas Jendela & Dialog:** `#F3F4F6` (abu-abu lembut Windows 11).
- **Permukaan Kartu & Tabel:** `#FFFFFF` dengan garis tepi tipis `1px solid #E2E8F0`.
- **Teks Utama & Sekunder:** `#18181B` (utama), `#334155` (ringkasan/folder tujuan), `#64748B` / `#94A3B8` (muted & teks ditolak).
- **Aksen Utama Tunggal:** `#0067C0` (`:hover` `#005A9E`, `:pressed` `#004578`).
- **Status Semantik:**
  - Siap / Disetujui: latar `#ECFDF5` / `#F0FDF4`, border `#BBF7D0`, teks `#166534`.
  - Duplikat / Installer Usang: latar `#FEF3C7`, border `#FDE68A`, teks `#92400E`.
  - Cek Manual (`is_skipped`): latar `#F1F5F9`, border `#E2E8F0`, teks `#64748B`.

---

## 5. Tiga Pengaman Teknis Implementasi

1. **Keamanan Seleksi File pada Filter Tab (`setRowHidden`):**
   - Perpindahan tab filter (`Semua`, `Usulan Nama`, `Duplikat`, `Cek Manual`) hanya memanggil `setRowHidden(row, hide)` — tidak pernah membuat ulang baris atau mengubah status centang dan `is_rename_approved`.
   - `get_selected_items()`, `get_selection_summary()`, dan penghitung pada tombol `"Rapikan Sekarang (N)"` selalu menghitung **seluruh item tercentang di semua tab**, termasuk baris yang sedang disembunyikan oleh filter.
2. **Proteksi Dark Mode OS pada QSS:**
   - Latar kanvas `#F3F4F6` hanya dikunci pada `QMainWindow`, `QWidget#CentralWidget`, `QDialog`, dan `QMessageBox` — **tidak pernah** pada selector global `QWidget`.
   - Seluruh kontainer sel di dalam tabel (`CheckboxCellContainer`, `RenameCellContainer`, `StatusCellContainer`) dikunci `background-color: transparent` (dan `#F0FDF4` hanya saat `[renameHighlighted="true"]`) agar tidak muncul kotak abu-abu di dalam baris tabel.
3. **Nol Emoji pada Teks Antarmuka:**
   - Seluruh label, tab, banner, dan tombol tidak memakai emoji (termasuk menghilangkan `✨`) agar rendering konsisten di Linux/X11 maupun Windows tanpa risiko kotak karakter hilang.
