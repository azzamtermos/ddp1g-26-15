"""Skrip pembuat folder simulasi (demo_sandbox/) untuk pengujian Smart File Organizer.

Membuat sekitar 15 file dummy yang menyerupai folder Downloads guru yang berantakan,
lengkap dengan dokumen ajar, administrasi, pasangan file duplikat (identik secara byte),
serta file installer usang yang berumur 45 hari.
"""

import os
from pathlib import Path
import random
import time


def seed_demo_sandbox() -> Path:
    """Membuat folder `demo_sandbox/` beserta 15 file dummy siap uji."""
    project_root = Path(__file__).resolve().parent.parent
    sandbox_dir = project_root / "demo_sandbox"
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(2026)

    # 1. Dokumen ajar, administrasi, media, & arsip unik (9 file)
    unique_files: dict[str, bytes] = {
        "RPP_Kurikulum_Merdeka.pdf": b"%PDF-1.4\nDokumen RPP Kurikulum Merdeka Kelas X Semester Ganjil\n"
        + bytes(rng.getrandbits(8) for _ in range(4096)),
        "Silabus_Informatika_2026.docx": b"PK\x03\x04Silabus Pembelajaran Informatika SMA 2026\n"
        + bytes(rng.getrandbits(8) for _ in range(3072)),
        "LKPD_Algoritma_Pemrograman.pdf": b"%PDF-1.4\nLembar Kerja Peserta Didik Dasar Pemrograman\n"
        + bytes(rng.getrandbits(8) for _ in range(2048)),
        "Rekap_Nilai_Semester_Ganjil.xlsx": b"PK\x03\x04Rekap Nilai Siswa Kelas 10A-10D Semester Ganjil\n"
        + bytes(rng.getrandbits(8) for _ in range(5120)),
        "Daftar_Hadir_Guru_November.csv": (
            "No,Nama,Status\n1,Budi Santoso,Hadir\n2,Siti Aminah,Hadir\n" * 25
        ).encode("utf-8"),
        "Materi_Presentasi_Bab1.pptx": b"PK\x03\x04Slide Presentasi Pertemuan 1 Pengenalan Python\n"
        + bytes(rng.getrandbits(8) for _ in range(8192)),
        "Sertifikat_Workshop_Guru_Digital.png": b"\x89PNG\r\n\x1a\nSertifikat Pelatihan Nasional\n"
        + bytes(rng.getrandbits(8) for _ in range(6144)),
        "Rekaman_Pembelajaran_Zoom.mp4": b"\x00\x00\x00\x18ftypmp42Video Rekaman Mengajar Kelas\n"
        + bytes(rng.getrandbits(8) for _ in range(16384)),
        "Arsip_Backup_Soal_Lama.zip": b"PK\x03\x04Backup Kumpulan Soal Tahun Lalu\n"
        + bytes(rng.getrandbits(8) for _ in range(10240)),
    }

    for filename, payload in unique_files.items():
        (sandbox_dir / filename).write_bytes(payload)

    # 2. Dua pasang file duplikat dengan isi byte 100% identik (4 file)
    dup_pdf_bytes = (
        b"%PDF-1.4\nNaskah Soal Ujian Akhir Semester Ganjil 2026\n"
        + bytes(rng.getrandbits(8) for _ in range(12288))
    )
    (sandbox_dir / "Soal_Ujian_2026.pdf").write_bytes(dup_pdf_bytes)
    (sandbox_dir / "Document (12).pdf").write_bytes(dup_pdf_bytes)

    dup_jpg_bytes = (
        b"\xff\xd8\xff\xe0Foto Dokumentasi Kegiatan Upacara Sekolah 10 Nov 2026\n"
        + bytes(rng.getrandbits(8) for _ in range(14336))
    )
    (sandbox_dir / "IMG_20261110.jpg").write_bytes(dup_jpg_bytes)
    (sandbox_dir / "WhatsApp Image 2026-11-10.jpg").write_bytes(dup_jpg_bytes)

    # 3. Dua file installer usang dengan timestamp dimundurkan 45 hari (2 file)
    obsolete_files: dict[str, bytes] = {
        "ZoomInstaller.exe": b"MZ\x90\x00Installer Aplikasi Zoom Cloud Meetings\n"
        + bytes(rng.getrandbits(8) for _ in range(32768)),
        "paket_update.deb": b"!<arch>\ndebian-binary 2.0 Paket Update Aplikasi Sekolah\n"
        + bytes(rng.getrandbits(8) for _ in range(24576)),
    }

    past_timestamp = time.time() - (45 * 86400)
    for filename, payload in obsolete_files.items():
        file_path = sandbox_dir / filename
        file_path.write_bytes(payload)
        os.utime(file_path, (past_timestamp, past_timestamp))

    return sandbox_dir


if __name__ == "__main__":
    created_dir = seed_demo_sandbox()
    total = sum(1 for p in created_dir.iterdir() if p.is_file())
    print(f"Berhasil menyiapkan {total} file simulasi di: {created_dir}")
