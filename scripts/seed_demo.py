"""Skrip pembuat folder simulasi (demo_sandbox/) untuk pengujian Smart File Organizer.

Membuat 15 file dummy realistis (PDF 1.4 biner valid, DOCX valid via zipfile/XML,
file media, arsip, installer usang 45 hari, dan pasangan file duplikat identik)
serta 1 subfolder terlindungi untuk menguji seluruh fitur Tahap 1 secara menyeluruh.
"""

import os
from pathlib import Path
import random
import shutil
import time
from xml.sax.saxutils import escape as xml_escape
import zipfile


def _build_pdf_bytes(lines: list[str]) -> bytes:
    """Membangun byte file PDF 1.4 valid menggunakan font standar /Helvetica."""
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
    return bytes(buffer)


def _write_docx(file_path: Path, paragraphs: list[str]) -> None:
    """Membuat file .docx valid menggunakan modul standar zipfile dan XML."""
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


def seed_demo_sandbox() -> Path:
    """Mereset dan mengisi `demo_sandbox/` dengan skenario uji realistis Tahap 1."""
    project_root = Path(__file__).resolve().parent.parent
    sandbox_dir = project_root / "demo_sandbox"

    if (
        sandbox_dir.exists()
        and sandbox_dir.name == "demo_sandbox"
        and sandbox_dir.parent == project_root
    ):
        shutil.rmtree(sandbox_dir)

    sandbox_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(2026)

    # 1. Smart Rename PDF dengan Kop Surat Teks -> target Soal_dan_Ujian/
    (sandbox_dir / "DOC-20261118-WA0004.pdf").write_bytes(
        _build_pdf_bytes(
            [
                "PEMERINTAH PROVINSI DKI JAKARTA",
                "DINAS PENDIDIKAN",
                "Jl. Raya Jagakarsa No. 10, Telp 021-123456",
                "SOAL PENILAIAN TENGAH SEMESTER GANJIL",
            ]
        )
    )

    # 2. Smart Rename PDF dengan Kop Gambar (Aturan A Whitelist) -> target Administrasi_dan_Nilai/
    (sandbox_dir / "CamScanner_20261119_0815.pdf").write_bytes(
        _build_pdf_bytes(
            [
                "SURAT KEPUTUSAN KEPALA SMA NEGERI 1",
                "Tentang Pembagian Tugas Guru Semester Ganjil",
            ]
        )
    )

    # 3. PDF Gambar/Scan Kosong tanpa lapisan teks -> is_skipped=True
    (sandbox_dir / "scan_dokumen.pdf").write_bytes(_build_pdf_bytes([]))

    # 4. File scan berkonteks (dilarang di-rename) -> target Administrasi_dan_Nilai/
    (sandbox_dir / "scan_ktp.pdf").write_bytes(
        _build_pdf_bytes(["KARTU TANDA PENDUDUK"])
    )

    # 5. Smart Rename DOCX (zipfile + XML) -> target Materi_dan_Bahan_Ajar/
    _write_docx(
        sandbox_dir / "Document (1).docx",
        [
            "MODUL AJAR MATEMATIKA KELAS X",
            "Materi Pembelajaran Semester Ganjil Kurikulum Merdeka",
        ],
    )

    # 6. Pasangan Duplikat SHA-256 #1 (RPP_Matematika_Kelas_10.pdf wajib menang)
    dup_rpp_bytes = _build_pdf_bytes(
        [
            "RENCANA PELAKSANAAN PEMBELAJARAN",
            "Matematika Kelas X Semester Ganjil",
        ]
    )
    (sandbox_dir / "DOC-20261118-WA0099.pdf").write_bytes(dup_rpp_bytes)
    (sandbox_dir / "RPP_Matematika_Kelas_10.pdf").write_bytes(dup_rpp_bytes)

    # 7. Pasangan Duplikat SHA-256 #2 (Soal_UAS_Biologi.pdf wajib menang)
    dup_soal_bytes = _build_pdf_bytes(
        [
            "SOAL UJIAN AKHIR SEMESTER BIOLOGI",
            "Kelas XI IPA",
        ]
    )
    (sandbox_dir / "Soal_UAS_Biologi.pdf").write_bytes(dup_soal_bytes)
    (sandbox_dir / "Soal_UAS_Biologi (1).pdf").write_bytes(dup_soal_bytes)

    # 8. Perwakilan Kategori Lainnya
    other_files: dict[str, bytes] = {
        "Rekap_Nilai_Semester_Ganjil.xlsx": b"PK\x03\x04Rekap Nilai Siswa Semester Ganjil\n"
        + bytes(rng.getrandbits(8) for _ in range(4096)),
        "Materi_Presentasi_Bab1.pptx": b"PK\x03\x04Slide Presentasi Materi Bab 1\n"
        + bytes(rng.getrandbits(8) for _ in range(6144)),
        "Foto_Kegiatan_Upacara.jpg": b"\xff\xd8\xff\xe0Foto Kegiatan Sekolah\n"
        + bytes(rng.getrandbits(8) for _ in range(8192)),
        "Rekaman_Pembelajaran_Kelas.mp4": b"\x00\x00\x00\x18ftypmp42Rekaman Video Kelas\n"
        + bytes(rng.getrandbits(8) for _ in range(12288)),
        "Arsip_Backup_Soal_Lama.zip": b"PK\x03\x04Arsip Soal Tahun Lalu\n"
        + bytes(rng.getrandbits(8) for _ in range(5120)),
    }
    for filename, payload in other_files.items():
        (sandbox_dir / filename).write_bytes(payload)

    # File installer usang (45 hari) -> Installer_Aplikasi & Installer Usang
    installer_path = sandbox_dir / "ZoomInstaller.exe"
    installer_path.write_bytes(
        b"MZ\x90\x00Installer Aplikasi Zoom\n"
        + bytes(rng.getrandbits(8) for _ in range(16384))
    )
    past_timestamp = time.time() - (45 * 86400)
    os.utime(installer_path, (past_timestamp, past_timestamp))

    # 9. Subfolder Terlindungi (tidak boleh disentuh oleh pemindaian aplikasi)
    protected_dir = sandbox_dir / "Folder_Pribadi_Jangan_Disentuh"
    protected_dir.mkdir(parents=True, exist_ok=True)
    (protected_dir / "catatan_penting.txt").write_text(
        "Catatan pribadi guru di dalam subfolder — jangan dipindahkan atau diubah oleh aplikasi.\n",
        encoding="utf-8",
    )

    return sandbox_dir


if __name__ == "__main__":
    created_dir = seed_demo_sandbox()
    top_files = sum(1 for p in created_dir.iterdir() if p.is_file())
    subfolders = sum(1 for p in created_dir.iterdir() if p.is_dir())
    print(
        f"Berhasil menyiapkan {top_files} file simulasi dan {subfolders} subfolder terlindungi di: {created_dir}"
    )
