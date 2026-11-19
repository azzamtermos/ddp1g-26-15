"""Pengujian unit untuk modul core.scanner (FolderScanner).

Menguji skenario pemindaian direktori berbasis pathlib.Path:
1. Pengelompokan kategori berdasarkan ekstensi file.
2. Deteksi prioritas kata kunci pada nama file (misal: RPP, Nilai).
3. Pengabaian subfolder dan file tersembunyi (diawali titik) saat memindai.
4. Perilaku fallback aman pada propose_smart_name.
"""

from pathlib import Path

from core.scanner import FolderScanner


def test_determine_category_by_extension(tmp_path: Path) -> None:
    """Menguji penentuan kategori berdasarkan ekstensi file umum."""
    scanner = FolderScanner(rules_path="data/default_rules.json")

    sample_image = tmp_path / "liburan_sekolah.png"
    sample_image.write_bytes(b"fake-png-bytes")

    sample_archive = tmp_path / "kumpulan_tugas.zip"
    sample_archive.write_bytes(b"fake-zip-bytes")

    assert scanner.determine_category(sample_image) == "Foto_dan_Gambar"
    assert scanner.determine_category(sample_archive) == "Paket_File_ZIP"


def test_determine_category_by_keyword_priority(tmp_path: Path) -> None:
    """Menguji deteksi kategori berdasarkan kata kunci spesifik dan word boundary."""
    scanner = FolderScanner(rules_path="data/default_rules.json")

    rpp_file = tmp_path / "RPP_Semester_Ganjil_2026.pdf"
    rpp_file.write_text("Isi dokumen RPP", encoding="utf-8")

    nilai_file = tmp_path / "Rekap_Nilai_Kelas_10A.xlsx"
    nilai_file.write_bytes(b"fake-excel-content")

    soal_file = tmp_path / "Soal_UAS_Matematika.pdf"
    soal_file.write_text("Isi soal UAS", encoding="utf-8")

    desktop_file = tmp_path / "desktop_biasa.pdf"
    desktop_file.write_text("Isi acak tanpa kata kunci", encoding="utf-8")

    generic_pdf = tmp_path / "Document (12).pdf"
    generic_pdf.write_text("Dokumen generik", encoding="utf-8")

    assert scanner.determine_category(rpp_file) == "Materi_dan_Bahan_Ajar"
    assert scanner.determine_category(nilai_file) == "Administrasi_dan_Nilai"
    assert scanner.determine_category(soal_file) == "Soal_dan_Ujian"
    assert scanner.determine_category(desktop_file) == "Lainnya"
    assert scanner.determine_category(generic_pdf) == "Lainnya"


def test_scan_directory_ignores_subfolders_and_hidden_files(tmp_path: Path) -> None:
    """Memastikan scan_directory hanya memindai file tingkat pertama dan mengabaikan subfolder."""
    # Buat file normal di tingkat pertama
    valid_doc = tmp_path / "Materi_Bab_1.pdf"
    valid_doc.write_text("Contoh materi pembelajaran", encoding="utf-8")

    # Buat file tersembunyi (diawali titik) yang harus diabaikan
    hidden_file = tmp_path / ".DS_Store"
    hidden_file.write_text("hidden metadata", encoding="utf-8")

    # Buat subfolder kategori & subfolder karantina yang harus diabaikan
    subfolder = tmp_path / "Materi_dan_Bahan_Ajar"
    subfolder.mkdir()
    (subfolder / "File_Lama.pdf").write_text("Sudah di dalam subfolder", encoding="utf-8")

    quarantine_dir = tmp_path / "_Karantina_Duplikat"
    quarantine_dir.mkdir()
    (quarantine_dir / "Duplikat.pdf").write_text("File karantina", encoding="utf-8")

    progress_records: list[tuple[int, str]] = []
    scanner = FolderScanner(rules_path="data/default_rules.json")
    items = scanner.scan_directory(
        str(tmp_path),
        progress_callback=lambda pct, msg: progress_records.append((pct, msg)),
    )

    assert len(items) == 1
    assert items[0].file_name == "Materi_Bab_1.pdf"
    assert items[0].category == "Materi_dan_Bahan_Ajar"
    assert len(progress_records) == 1
    assert progress_records[-1][0] == 100


def test_propose_smart_name_fallback(tmp_path: Path) -> None:
    """Memastikan propose_smart_name mengembalikan nama file asli sebagai fallback aman."""
    scanner = FolderScanner(rules_path="data/default_rules.json")
    sample_file = tmp_path / "Soal_Ujian_Akhir.docx"
    sample_file.write_text("Isi soal", encoding="utf-8")

    proposed = scanner.propose_smart_name(sample_file, doc_hint=None)
    assert proposed == "Soal_Ujian_Akhir.docx"


def test_determine_category_avoids_keyword_false_positives(tmp_path: Path) -> None:
    """Memastikan tidak ada false positive akibat tumpang tindih atau substring kata kunci."""
    scanner = FolderScanner(rules_path="data/default_rules.json")

    cases = {
        "RPP_Kurikulum_Merdeka.pdf": "Materi_dan_Bahan_Ajar",
        "Soal_Penilaian_Tengah_Semester.pdf": "Soal_dan_Ujian",
        "Materi_Struktur_Atom.pdf": "Materi_dan_Bahan_Ajar",
        "Materi_Fakta_dan_Opini.pdf": "Materi_dan_Bahan_Ajar",
        "Daftar_Nilai_UAS.pdf": "Administrasi_dan_Nilai",
        "Introduction_to_Python.pdf": "Lainnya",
    }

    for filename, expected_category in cases.items():
        file_path = tmp_path / filename
        file_path.write_text("konten uji", encoding="utf-8")
        assert scanner.determine_category(file_path) == expected_category
