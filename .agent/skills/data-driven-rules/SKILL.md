---
name: data-driven-rules
description: Standar pemisahan aturan kata kunci, pola regex, dan konfigurasi teks ke dalam file JSON di folder data/ tanpa hardcode di modul core/. Gunakan setiap kali mengubah atau menambah logika pemindaian, kategorisasi, penamaan pintar, atau deteksi duplikat.
---

# Skill: Data-Driven Rules (No Hardcoded Keywords)

## Aturan Utama
1. **Dilarang Hardcode Daftar Kata Kunci:** Seluruh daftar kata kunci kategori, pola nama file generik, whitelist penanda judul dokumen, pola filter kop surat, dan penanda duplikat WAJIB disimpan di file JSON dalam folder `data/` (`data/default_rules.json` dan `data/text_rules.json`), bukan ditulis langsung di dalam `core/scanner.py` atau `core/duplicate_finder.py`.
2. **Load Sekali di Inisialisasi:** Muat file JSON satu kali di `__init__()` (ubah ke `set` atau kompilasi `re.compile()` sekali saja) agar tidak membaca disk berulang kali saat iterasi file.
3. **Resolusi Path Aman:** Selalu resolusi path file JSON relatif terhadap root proyek (`Path(__file__).resolve().parent.parent / "data" / ...`) agar tetap terbaca saat `pytest` dijalankan dari direktori mana pun.
4. **Fallback Minimalis:** Jika file JSON tidak ditemukan atau rusak, sediakan struktur fallback kosong/aman di kode agar aplikasi tidak crash (*graceful degradation*).
