"""Pengujian unit untuk modul core.scanner (FolderScanner).

Menguji skenario pemindaian direktori berbasis pathlib.Path:
1. Pengelompokan kategori berdasarkan ekstensi file.
2. Deteksi prioritas kata kunci pada nama file (misal: RPP, Nilai).
3. Pengabaian subfolder dan file tersembunyi (diawali titik) saat memindai.
4. Perilaku fallback aman pada propose_smart_name.
"""

from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
import zipfile

from core.scanner import FolderScanner


def _create_test_pdf(file_path: Path, lines: list[str]) -> None:
    """Membuat file PDF 1.4 valid secara programatik untuk keperluan unit test."""
    if lines:
        ops = ["BT", "/F1 12 Tf", "50 750 Td", "16 TL"]
        for idx, line in enumerate(lines):
            if idx > 0:
                ops.append("T*")
            escaped = (
                line.replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            ops.append(f"({escaped}) Tj")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
    else:
        stream = b""

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        ),
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        (
            f"5 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1")
            + stream
            + b"\nendstream endobj\n"
        ),
    ]

    buffer = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(buffer))
        buffer.extend(obj)

    xref_offset = len(buffer)
    buffer.extend(
        f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("latin-1")
    )
    for off in offsets[1:]:
        buffer.extend(f"{off:010d} 00000 n \n".encode("latin-1"))

    buffer.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "latin-1"
        )
    )
    file_path.write_bytes(bytes(buffer))


def _create_test_docx(file_path: Path, paragraphs: list[str]) -> None:
    """Membuat file DOCX valid secara programatik untuk keperluan unit test."""
    body_xml = "".join(
        f"<w:p><w:r><w:t>{xml_escape(text)}</w:t></w:r></w:p>"
        for text in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body_xml}</w:body>"
        "</w:document>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(file_path, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/document.xml", document_xml)


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


def test_smart_rename_pdf_with_text_letterhead(tmp_path: Path) -> None:
    """Memastikan PDF generik melewati kop surat teks dan mengekstrak judul utama."""
    scanner = FolderScanner(rules_path="data/default_rules.json")
    pdf_path = tmp_path / "DOC-20261118-WA0004.pdf"
    _create_test_pdf(
        pdf_path,
        [
            "PEMERINTAH KABUPATEN BOGOR",
            "DINAS PENDIDIKAN",
            "Jl. Merdeka No. 10 Telp. (0251) 123456",
            "Nomor: 012/SMAN1/2026",
            "UNDANGAN RAPAT WALI MURID",
        ],
    )

    items = scanner.scan_directory(str(tmp_path))

    assert len(items) == 1
    item = items[0]
    assert item.category == "Administrasi_dan_Nilai"
    assert item.is_skipped is False
    assert item.suggested_name == "Undangan_Rapat_Wali_Murid.pdf"
    assert item.final_name == "Undangan_Rapat_Wali_Murid.pdf"


def test_smart_rename_pdf_with_image_letterhead_rule_a_whitelist(
    tmp_path: Path,
) -> None:
    """Memastikan Aturan A (whitelist judul) menyelamatkan judul pada PDF kop gambar."""
    scanner = FolderScanner(rules_path="data/default_rules.json")
    pdf_path = tmp_path / "CamScanner 11-18-2026.pdf"
    _create_test_pdf(
        pdf_path,
        [
            "SURAT KEPUTUSAN KEPALA SMA NEGERI 1",
            "Tentang Pembagian Tugas Mengajar",
        ],
    )

    items = scanner.scan_directory(str(tmp_path))

    assert len(items) == 1
    item = items[0]
    assert item.category == "Administrasi_dan_Nilai"
    assert item.is_skipped is False
    assert item.suggested_name == "Surat_Keputusan_Kepala_Sma_Negeri_1.pdf"


def test_scan_blank_image_pdf_is_skipped(tmp_path: Path) -> None:
    """Memastikan PDF gambar tanpa teks dibiarkan di tempat asal (is_skipped=True)."""
    scanner = FolderScanner(rules_path="data/default_rules.json")
    pdf_path = tmp_path / "scan_dokumen.pdf"
    _create_test_pdf(pdf_path, [])

    items = scanner.scan_directory(str(tmp_path))

    assert len(items) == 1
    item = items[0]
    assert item.is_skipped is True
    assert item.suggested_name is None
    assert item.proposed_path == str(pdf_path)
    assert item.status_label == "Dibiarkan (Perlu Cek Manual)"


def test_contextual_scan_filename_not_renamed(tmp_path: Path) -> None:
    """Memastikan nama file berkonteks (scan_ktp.pdf) tidak di-rename walau berakhiran scan."""
    scanner = FolderScanner(rules_path="data/default_rules.json")
    pdf_path = tmp_path / "scan_ktp.pdf"
    _create_test_pdf(pdf_path, ["UNDANGAN RAPAT LAIN"])

    items = scanner.scan_directory(str(tmp_path))

    assert len(items) == 1
    item = items[0]
    assert item.category == "Administrasi_dan_Nilai"
    assert item.is_skipped is False
    assert item.suggested_name is None
    assert item.final_name == "scan_ktp.pdf"


def test_smart_rename_generic_docx_via_zipfile_xml(tmp_path: Path) -> None:
    """Memastikan file DOCX generik dibaca via zipfile/xml dan menghasilkan judul & kategori tepat."""
    scanner = FolderScanner(rules_path="data/default_rules.json")
    docx_path = tmp_path / "Document (1).docx"
    _create_test_docx(
        docx_path,
        [
            "PEMERINTAH PROVINSI JAWA BARAT",
            "Jl. Pendidikan No. 5",
            "Modul Ajar Algoritma Pemrograman",
            "Materi untuk kelas X semester ganjil.",
        ],
    )

    items = scanner.scan_directory(str(tmp_path))

    assert len(items) == 1
    item = items[0]
    assert item.category == "Materi_dan_Bahan_Ajar"
    assert item.is_skipped is False
    assert item.suggested_name == "Modul_Ajar_Algoritma_Pemrograman.docx"
