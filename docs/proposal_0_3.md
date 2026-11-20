# Proposal 0.3 — Smart Offline Organizer (Fase Lanjutan & Stabilitas Pengguna Awam)

## 1. Tujuan Utama
Meningkatkan aplikasi dari kerangka dasar (*working baseline*) menjadi alat perapi file **100% offline-first, non-destruktif, dan intuitif** bagi pengguna awam (khususnya guru). Fokus utama iterasi ini adalah akurasi klasifikasi dokumen sekolah, fitur usulan penamaan ulang otomatis (*Offline Smart Rename*) yang aman dari kesalahan baca kop surat, seleksi duplikat yang cerdas, serta antarmuka yang menenangkan sebelum eksekusi.

---

## 2. Prinsip Desain & Batasan Wajib (Guardrails)
Setiap perubahan kode wajib mematuhi aturan berikut:
1. **Data-Driven Rules (No Hardcoding):** Seluruh daftar kata kunci kategori, pola nama generik, whitelist judul, filter kop surat, dan penanda duplikat wajib disimpan di `data/default_rules.json` dan `data/text_rules.json` (dibaca & dikompilasi sekali saat inisialisasi).
2. **Jangan Pernah Sentuh Subfolder:** Pemindaian hanya memproses file pada tingkat terluar direktori target.
3. **Prinsip "Jika Ragu, Jangan Sentuh":** File yang tidak memiliki kata kunci yang jelas **dan** tidak memiliki teks yang terbaca (misalnya PDF hasil scan foto KTP/KK) **tidak boleh diubah namanya** dan **dibiarkan tetap di folder asal** (status: `Dibiarkan (Perlu Cek Manual)`).
4. **Tetap Single-Level Undo (Dilarang Multi-Undo):** Untuk menghindari konflik perubahan file manual oleh pengguna di luar aplikasi, Undo tetap 1 tingkat terakhir ("Undo Palugada"): mengembalikan lokasi file, mengembalikan nama asli sebelum *rename*, menghapus folder baru yang kosong via `Path.rmdir()`, dan melewati (*graceful skip*) file yang sudah diubah/dipindah secara manual tanpa *crash*.
5. **Tanpa Dependensi Berat Tambahan:** Ekstraksi teks PDF menggunakan `pypdf`, sedangkan ekstraksi teks `.docx` wajib menggunakan modul bawaan Python (`zipfile` + `xml.etree.ElementTree`). Tidak menggunakan OCR eksternal (seperti Tesseract) maupun API AI Cloud pada rilis inti ini.

---

## 3. Spesifikasi Fitur Baru

### A. 8 Folder Kategori Final & Prioritas Klasifikasi
1. **`Administrasi_dan_Nilai`** *(Prioritas Teks #1)* — Ekstensi pasti: `.xlsx`, `.xls`, `.csv`, `.ods`. Mencakup administrasi sekolah, nilai, rapor, surat, dan dokumen identitas/pribadi (`ktp`, `kk`, `ktm`, `sk`, `ijazah`, dll.).
2. **`Soal_dan_Ujian`** *(Prioritas Teks #2)* — Soal, ujian, ulangan, kuis, kisi-kisi, kunci jawaban, pembahasan, tryout, asesmen.
3. **`Materi_dan_Bahan_Ajar`** *(Prioritas Teks #3)* — Gabungan bahan ajar & presentasi (ekspor Canva PDF maupun PPTX). Ekstensi pasti: `.pptx`, `.ppt`, `.odp`, `.key`, `.epub`.
4. **`Foto_dan_Gambar`** — Ekstensi pasti: `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.gif`, `.bmp`, `.svg`, `.ico`, `.tiff`.
5. **`Video_dan_Audio`** — Ekstensi pasti: `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`.
6. **`Paket_File_ZIP`** — Ekstensi pasti: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.bz2`, `.xz`, `.iso`.
7. **`Installer_Aplikasi`** — Ekstensi pasti: `.exe`, `.msi`, `.dmg`, `.pkg`, `.deb`, `.rpm`, `.apk`, `.appimage`.
8. **`_Karantina_Duplikat`** — Penampung file kembar (SHA-256 identik) yang kalah dalam skor kualitas nama.

*Aturan Pencocokan Kata Kunci:*
- **Exact Keywords (Singkatan 2–3 huruf):** Seperti `sk`, `kk`, `uh`, `cp`, `tp`, `rpp`, `atp`, `to`, `us` wajib dicocokkan sebagai kata utuh (*word boundary*) agar tidak salah cocok sebagai *substring* (misal `sk` tidak cocok pada `desktop` atau `tugas_kelompok`).
- **Partial Keywords:** Frasa atau kata panjang seperti `daftar nilai`, `kisi-kisi`, `modul ajar`, `surat undangan`.
- File `.pdf` dan `.docx` **tidak boleh** langsung masuk kategori hanya dari ekstensinya; penentuan wajib melalui kata kunci nama file atau ekstraksi isi teks.

### B. Seleksi Pemenang Duplikat (SHA-256 + Filename Quality Score)
- Ketika ditemukan grup file dengan hash SHA-256 identik, sistem menilai kualitas nama setiap file:
  - Penalti untuk pola nama generik/mesin (`DOC-`, `WA00`, `IMG_`, `scan`, `Untitled`, angka acak) dan penanda salinan browser (`(1)`, `(2)`, `- Copy`, `_salinan`).
  - Nilai tambah untuk nama file yang bersih dan deskriptif.
- File dengan skor tertinggi dipertahankan sebagai file utama (masuk kategori); sisanya masuk `_Karantina_Duplikat/`.

### C. Offline Smart Rename (`.pdf` & `.docx`)
- **Selektif:** Hanya aktif jika nama file terdeteksi generik/tanpa konteks (misal `DOC-20261118-WA004.pdf`, `scan_dokumen.pdf`, `CamScanner...pdf`, `Document (1).docx`). File dengan nama berkonteks (seperti `scan_ktp.pdf` atau `RPP_Bab1.pdf`) **dilarang** di-rename.
- **Ekstraksi Konten:**
  - `.pdf`: Baca halaman 1 via `pypdf` (hanya untuk file di bawah batas ukuran aman, misal 50 MB).
  - `.docx`: Baca paragraf awal dari `word/document.xml` via `zipfile` + `xml.etree.ElementTree`.
- **Filter Anti-Kop Surat (2 Lapis):**
  - *Aturan A (Whitelist Menang):* Jika baris mengandung kata penanda dokumen (`surat`, `undangan`, `soal`, `ujian`, `rpp`, `modul`, `daftar nilai`, `rekap`, `sertifikat`, dll.), baris langsung diterima sebagai kandidat judul meskipun memuat nama instansi/sekolah.
  - *Aturan B (Skip Kop/Alamat Murni):* Lewati baris yang tidak lolos Aturan A dan berisi alamat/kontak (`jl.`, `telp`, `kode pos`, `npsn`, `email`, `http`), nama instansi berdiri sendiri (`pemerintah...`, `dinas...`, `kementerian...`), atau metadata surat (`nomor:`, `lampiran:`).
- **Format Nama Usulan:** Bersihkan karakter ilegal OS, ambil maksimal 6 kata utama, format `Title_Case_Dengan_Garis_Bawah` + ekstensi asli.
- **Pemisahan Klasifikasi vs Rename:** Gunakan ~400 karakter pertama untuk menentukan kategori folder, namun hanya usulkan *rename* jika ditemukan baris judul yang jelas (2–7 kata). Jika isi kosong (PDF gambar) dan nama generik ➔ biarkan di tempat asal.

### D. UI/UX Usulan Rename ala Google Docs & Kontrol Keamanan
- Menyatu di `PreviewTableWidget` (tidak membuat panel terpisah).
- **Default Aktif (`is_rename_approved = True`):** Jika pengguna langsung menekan tombol eksekusi utama tanpa mengklik apa pun, semua usulan rename yang tidak ditolak otomatis diterapkan.
- Baris dengan usulan rename diberi *highlight* visual (`nama_lama ➔ nama_baru`) beserta tombol aksi per baris: `[✓]` (Terima) dan `[✕]` (Tolak/kembalikan ke nama asli, namun tetap dipindahkan ke folder kategori).
- Banner otomatis di atas tabel (muncul hanya jika ada usulan rename): tombol massal `[✓ Terima Semua]` dan `[✕ Tolak Semua]`.
- Kotak centang (*checkbox*) per baris (default tercentang semua) untuk mengecualikan file tertentu sebelum eksekusi.
- Validasi keamanan direktori: menolak pemilihan folder kritis sistem operasi dengan pesan bahasa sehari-hari.

---

## 4. Partisi Pengerjaan & Titik Verifikasi (Checkpoints)

> **Aturan Eksekusi untuk Agen:** Kerjakan **maksimal 1 sub-partisi per sesi**. Setelah menyelesaikan 1 sub-partisi, WAJIB jalankan `pytest -v`, laporkan ringkasan perubahan, dan berhenti menunggu konfirmasi sebelum lanjut ke sub-partisi berikutnya.

### Tahap 1 — Core Logic & Offline Smart Rename (Branch: `feat/offline-smart-rename`)
- [x] **Partisi 1A — Pembaruan Data Aturan Modular (`data/`)**
  - Perbarui `data/default_rules.json` ke 7 kategori baru + urutan prioritas + pemisahan `exact_keywords` & `partial_keywords` + ekstensi pasti.
  - Lengkapi `data/text_rules.json` (pola nama generik, whitelist judul Aturan A, filter kop surat Aturan B, penanda duplikat).
  - *Checkpoint 1A:* JSON valid, tidak ada duplikasi/konflik kata kunci kritis, tes eksisting tetap jalan atau disesuaikan.
- [x] **Partisi 1B — Model Data & Skor Pemenang Duplikat (`core/models.py`, `core/duplicate_finder.py`)**
  - Tambahkan field pendukung rename & skip pada `FileItem` (`suggested_name`, `is_rename_approved`, properti `final_name`, status skip/unrecognized).
  - Terapkan `_score_filename_quality()` di `core/duplicate_finder.py` agar file dengan nama terbaik selalu menang dan tidak masuk `_Karantina_Duplikat`.
  - *Checkpoint 1B:* Tambahkan unit test di `tests/test_duplicate_finder.py` untuk menguji kasus `DOC-WA.pdf` vs `RPP_Matematika.pdf` dan `File.pdf` vs `File (1).pdf`. Semua `pytest -v` lulus.
- [x] **Partisi 1C — Mesin Smart Rename `.pdf`/`.docx` & Organizer Safe-Skip (`core/scanner.py`, `core/organizer.py`)**
  - Implementasi pencocokan `exact_keywords` (*word boundary*) + prioritas kategori.
  - Implementasi pembacaan teks `.pdf` (`pypdf`) dan `.docx` (`zipfile`/`xml`), filter kop surat Aturan A & B, serta logika *Smart Rename* selektif + status "Dibiarkan" untuk PDF gambar tanpa teks.
  - Pastikan `core/organizer.py` melewati file berstatus "Dibiarkan", mengeksekusi `final_name` saat pemindahan, dan mendukung *graceful skip* saat Undo jika ada file yang sudah berubah di luar aplikasi.
  - *Checkpoint 1C:* Tambahkan unit test komprehensif di `tests/test_scanner.py` dan `tests/test_organizer.py` (kop surat teks, kop surat gambar, PDF scan kosong, `.docx`, dan Undo mengembalikan nama asli). Semua `pytest -v` lulus.
- [x] **Partisi 1D — Generator Sandbox Realistis (`scripts/seed_demo.py`)**
  - Perbarui `scripts/seed_demo.py` agar membuat file `.pdf` biner valid (berisi teks kop surat + judul, serta 1 PDF kosong/tanpa teks untuk simulasi scan KTP) dan `.docx` valid menggunakan modul standar Python tanpa dependensi tambahan.
  - *Checkpoint 1D:* Jalankan `python scripts/seed_demo.py`, lalu uji manual lewat `python main.py` (scan -> rapikan -> undo) dan pastikan tidak ada error.

### Tahap 2 — UI/UX Polish & Kontrol Pengguna Awam (Branch: `feat/ui-ux-polish`)
*(Dimulai setelah Tahap 1 di-merge ke `main`)*
- [x] **Partisi 2A — Tampilan Usulan Rename ala Google Docs (`ui/widgets.py`, `ui/main_window.py`)**
  - Highlight baris yang memiliki usulan rename, tampilkan panah perubahan nama (`nama_lama ➔ nama_baru`) + tombol `[✓]` / `[✕]` per baris, dan banner massal `[✓ Terima Semua]` / `[✕ Tolak Semua]` (muncul hanya jika ada usulan).
  - Tampilkan status netral `"Dibiarkan (Perlu Cek Manual)"` untuk file yang tidak disentuh.
  - Tambahkan kotak centang (*checkbox*) per baris (default tercentang semua) agar pengguna tetap bisa mengecualikan file tertentu sebelum dieksekusi.
  - *Checkpoint 2A:* Uji interaksi klik `[✕]`, `[✓]`, Tolak/Terima Semua, dan uncheck file di `demo_sandbox/`, lalu verifikasi hasil eksekusi & Undo.
- [x] **Partisi 2B — Pengaman Folder & Bahasa Manusiawi (`ui/main_window.py`, `ui/styles.qss`)**
  - Blokir pemilihan folder kritis sistem operasi (root `/`, `C:\Windows`, `Program Files`, `/System`, dll.) dengan pesan peringatan bahasa sehari-hari.
  - Tambahkan kartu ringkasan singkat di atas tabel sebelum eksekusi (contoh: *"12 file siap dirapikan • 2 duplikat diamankan • 1 file perlu dicek manual"*) dan dialog ringkasan hasil setelah selesai.
  - Audit seluruh teks di antarmuka (tombol, label, pesan error) agar 100% menggunakan bahasa Indonesia yang ramah dan bebas istilah teknis (seperti "SHA-256", "exception", atau "path").
  - *Checkpoint 2B:* Uji coba skenario salah pilih folder sistem, folder kosong, dan folder penuh; pastikan tidak ada error mentah yang muncul ke layar.

### Tahap 3 — Packaging Mandiri (Windows & Debian/Ubuntu/Mint) & Uji Beta (Branch: `feat/beta-packaging`)
*(Dimulai setelah Tahap 2 di-merge ke `main`)*
- [x] **Partisi 3A — Build Aplikasi Mandiri (`PyInstaller` + Paket `.deb` & `.exe`)**
  - Siapkan konfigurasi `PyInstaller` beserta resolusi path *bundled* (`sys._MEIPASS` untuk membaca `data/default_rules.json` & `data/text_rules.json`, serta direktori user yang *writable* seperti `~/.local/share/` atau `%APPDATA%` untuk menyimpan `undo_history.json`).
  - Buat skrip otomatis `scripts/build_deb.sh` yang membungkus hasil *build* `PyInstaller` menjadi paket installer **`.deb`** (mendukung deteksi arsitektur otomatis `amd64` untuk Linux Mint/Ubuntu desktop dan `arm64` untuk Ubuntu tablet, lengkap dengan file `.desktop` dan ikon aplikasi).
  - Siapkan panduan/skrip *build* `.exe` untuk distribusi ke pengguna Windows.
  - *Checkpoint 3A:* Uji instalasi `.deb` via `sudo apt install ./dist/*.deb` di luar folder proyek, jalankan aplikasi dari menu sistem, lalu verifikasi fungsi scan, rename, dan Undo berjalan normal.
- [ ] **Partisi 3B — Uji Coba Pengguna Nyata (*Beta Test*)**
  - Uji aplikasi menggunakan salinan file dunia nyata (ekspor Canva PDF, dokumen Word, kiriman WhatsApp, dan hasil scan gambar) di laptop target.
  - Catat kata kunci sekolah yang masih terlewat untuk ditambahkan ke `data/default_rules.json` dan perbaiki kendala UX yang ditemui.

---

## 5. Backlog Opsional (Ditunda)
- Integrasi opsional API AI Cloud (BYOK / input API key mandiri) ditunda dari rilis inti agar aplikasi tetap bebas konfigurasi dan ramah bagi pengguna non-teknis.