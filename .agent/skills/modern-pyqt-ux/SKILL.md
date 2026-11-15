---
name: modern-pyqt-ux
description: Panduan desain antarmuka modern dan ramah pengguna awam untuk PyQt6. Aktifkan setiap kali membuat komponen visual atau mengedit ui/styles.qss.
---

# Standar Desain UI/UX Modern (PyQt6)

1. **Tampilan Bersih & Modern (Anti-Kaku):**
   - Ganti warna abu-abu standar OS dengan palet lembut: latar belakang jendela `#F8FAFC`, permukaan kartu `#FFFFFF` dengan garis tepi tipis `#E2E8F0`, dan tombol utama biru `#2563EB` (hover `#1D4ED8`).
   - Gunakan sudut membulat (`border-radius: 8px` untuk tombol dan input, `12px` untuk area kartu).
2. **Tata Letak Lega:**
   - Berikan jarak antar elemen (`spacing` minimal `12px`) dan margin luar jendela minimal `24px` agar tampilan tidak penuh sesak.
   - Gunakan font sans-serif modern (`Segoe UI`, `Inter`, atau `Ubuntu`) dengan ukuran teks minimal `13px` dan judul `18px–20px` *bold*.
3. **Bahasa Manusiawi (Ramah Guru Gaptek):**
   - Hindari istilah teknis komputer pada tombol maupun label. Gunakan kata kerja yang jelas seperti **"Pilih Folder Berantakan"**, **"Lihat Rencana Rapikan"**, **"Rapikan Sekarang"**, dan **"Batalkan (Undo)"**.
4. **Fokus Visual & Umpan Balik Jelas:**
   - Tempatkan area *drag-and-drop* berukuran besar dengan garis tepi putus-putus (*dashed border*) di bagian atas sebagai fokus utama.
   - Pada tabel *preview*, gunakan indikator warna lembut yang mudah dibedakan (misal teks/badge hijau untuk file siap dirapikan, kuning/oranye untuk file duplikat) agar pengguna langsung yakin sebelum mengeksekusi perubahan.