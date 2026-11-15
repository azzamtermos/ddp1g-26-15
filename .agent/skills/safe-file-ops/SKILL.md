---
name: safe-file-ops
description: Aturan keamanan manipulasi file lokal, deteksi duplikat, dan pencatatan riwayat Undo. Gunakan setiap kali mengerjakan modul di folder core/.
---

# Standar Keamanan Operasi File

1. **Cross-Platform Path:**
   - Wajib menggunakan `pathlib.Path` untuk seluruh manipulasi alamat file dan folder agar berjalan mulus di Windows maupun Linux. Dilarang menggabungkan *path* menggunakan operator string (`+`).
2. **Dilarang Menghapus Permanen:**
   - Dilarang keras menggunakan `os.remove()`, `os.unlink()`, atau `shutil.rmtree()`.
   - Jika ada file sampah atau duplikat yang dibersihkan, wajib memindahkannya ke *Recycle Bin* menggunakan library `send2trash`.
3. **Wajib Log Transaksi (Fitur 1-Click Undo):**
   - Sebelum memindahkan atau mengubah nama file apa pun, program wajib menyimpan catatan transaksi ke file JSON di folder `data/` berisi daftar pasangan lokasi lama dan baru (`{"old_path": "...", "new_path": "..."}`).
   - Sediakan fungsi pemulihan yang membaca log JSON terakhir untuk mengembalikan seluruh file ke nama dan folder asalnya.
4. **Penanganan Error & Konflik Nama:**
   - Jika nama file tujuan sudah ada di folder target, tambahkan penomoran otomatis (misal `_1`, `_2`) alih-alih menimpa (*overwrite*) file lama.
   - Tangani *exception* seperti `PermissionError` (jika file sedang dibuka di Word/PDF Reader) secara anggun tanpa membuat aplikasi *crash*.