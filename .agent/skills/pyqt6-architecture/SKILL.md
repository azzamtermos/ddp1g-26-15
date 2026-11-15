---
name: pyqt6-architecture
description: Standar arsitektur modular PyQt6 untuk proyek Smart File Organizer. Gunakan setiap kali membuat atau mengubah file di folder ui/, core/, atau main.py.
---

# Standar Arsitektur & Kode Tim (PyQt6)

1. **Pemisahan Ketat UI dan Logika:**
   - Dilarang menaruh logika manipulasi file (`os`, `shutil`, `pathlib`), hashing, atau pembacaan dokumen di dalam folder `ui/`.
   - Modul di `ui/` hanya bertugas menampilkan antarmuka dan memanggil fungsi/kelas dari folder `core/`.
2. **Anti-Freeze (Wajib Multithreading):**
   - Setiap proses yang memakan waktu (memindai isi folder, menghitung hash duplikat, ekstraksi teks PDF/OCR) wajib dijalankan di *background thread* menggunakan `QThread` atau `QRunnable` agar jendela aplikasi tidak *not responding*.
3. **Styling Terpisah:**
   - Simpan seluruh pengaturan warna, font, dan *padding* di file `ui/styles.qss`. Jangan menuliskan *inline stylesheet* panjang di dalam kode Python.
4. **Mudah Dipahami Anggota Tim (Standar DDP1):**
   - Hindari pola OOP yang terlalu abstrak atau *metaprogramming* yang rumit.
   - Wajib sertakan *type hints* pada parameter/return fungsi serta *docstring* singkat berbahasa Indonesia pada setiap *class* dan *method* utama agar mudah dipelajari seluruh anggota tim.