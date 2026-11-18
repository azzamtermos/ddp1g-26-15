"""Pengujian unit untuk modul core.duplicate_finder (DuplicateFinder).

Menguji skenario deteksi file duplikat dan analisis penyimpanan:
1. Perhitungan nilai hash SHA-256 yang konsisten untuk isi file identik.
2. Penandaan file duplikat ke kategori `_Karantina_Duplikat` beserta perubahan status_label.
3. Deteksi file installer/sementara yang sudah usang (melebihi batas hari).
4. Kalkulasi estimasi ruang penyimpanan yang dihemat (`calculate_wasted_space`).
"""

from pathlib import Path

import pytest

from core.duplicate_finder import DuplicateFinder
from core.models import FilePlanItem


def test_calculate_file_hash_identical_and_different(tmp_path: Path) -> None:
    """Memastikan dua file dengan isi sama menghasilkan hash SHA-256 yang identik."""
    finder = DuplicateFinder()

    file_a = tmp_path / "dokumen_asli.pdf"
    file_b = tmp_path / "dokumen_salinan.pdf"
    file_c = tmp_path / "dokumen_berbeda.pdf"

    file_a.write_bytes(b"Konten Pembelajaran DDP1 Identik")
    file_b.write_bytes(b"Konten Pembelajaran DDP1 Identik")
    file_c.write_bytes(b"Konten yang berbeda sama sekali")

    hash_a = finder.calculate_file_hash(file_a)
    hash_b = finder.calculate_file_hash(file_b)
    hash_c = finder.calculate_file_hash(file_c)

    assert hash_a != ""
    assert hash_a == hash_b
    assert hash_a != hash_c


def test_mark_duplicates_routes_second_file_to_quarantine(tmp_path: Path) -> None:
    """Memastikan file kembar kedua ditandai sebagai duplikat dan diarahkan ke _Karantina_Duplikat."""
    finder = DuplicateFinder()

    content = b"Data Modul Praktikum Python"
    original_file = tmp_path / "modul_1.pdf"
    duplicate_file = tmp_path / "modul_1_copy.pdf"
    unique_file = tmp_path / "catatan_lain.txt"

    original_file.write_bytes(content)
    duplicate_file.write_bytes(content)
    unique_file.write_bytes(b"Catatan singkat")

    items = [
        FilePlanItem(
            source_path=str(original_file),
            file_name=original_file.name,
            proposed_name=original_file.name,
            file_size=len(content),
            category="Dokumen_Ajar",
            proposed_path=str(tmp_path / "Dokumen_Ajar" / original_file.name),
        ),
        FilePlanItem(
            source_path=str(duplicate_file),
            file_name=duplicate_file.name,
            proposed_name=duplicate_file.name,
            file_size=len(content),
            category="Dokumen_Ajar",
            proposed_path=str(tmp_path / "Dokumen_Ajar" / duplicate_file.name),
        ),
        FilePlanItem(
            source_path=str(unique_file),
            file_name=unique_file.name,
            proposed_name=unique_file.name,
            file_size=15,
            category="Dokumen_Ajar",
            proposed_path=str(tmp_path / "Dokumen_Ajar" / unique_file.name),
        ),
    ]

    result = finder.mark_duplicates(items)

    assert result[0].is_duplicate is False
    assert result[0].status_label == "Siap Dirapikan"

    assert result[1].is_duplicate is True
    assert result[1].category == "_Karantina_Duplikat"
    assert result[1].status_label == "File Duplikat"
    assert result[1].proposed_path == str(
        tmp_path / "_Karantina_Duplikat" / duplicate_file.name
    )

    assert result[2].is_duplicate is False


def test_detect_obsolete_installers_marks_old_installer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan file installer yang usianya melebihi age_days ditandai sebagai Installer Usang."""
    finder = DuplicateFinder()

    installer_file = tmp_path / "setup_zoom_lama.exe"
    installer_file.write_bytes(b"binary-installer-content")
    file_mtime = installer_file.stat().st_mtime

    # Simulasikan waktu saat ini 45 hari setelah file installer dibuat
    simulated_now = file_mtime + (45 * 86400)
    monkeypatch.setattr("core.duplicate_finder.time.time", lambda: simulated_now)

    item = FilePlanItem(
        source_path=str(installer_file),
        file_name=installer_file.name,
        proposed_name=installer_file.name,
        file_size=24,
        category="Installer_Aplikasi",
        proposed_path=str(tmp_path / "Installer_Aplikasi" / installer_file.name),
    )

    updated = finder.detect_obsolete_installers([item], age_days=30)

    assert updated[0].is_obsolete_temp is True
    assert updated[0].status_label == "Installer Usang"


def test_calculate_wasted_space_summary() -> None:
    """Menguji akurasi perhitungan total byte, jumlah duplikat, dan jumlah installer usang."""
    finder = DuplicateFinder()

    items = [
        FilePlanItem(
            source_path="/dummy/a.pdf",
            file_name="a.pdf",
            proposed_name="a.pdf",
            file_size=1024,
            category="Dokumen_Ajar",
            proposed_path="/dummy/Dokumen_Ajar/a.pdf",
            is_duplicate=False,
            is_obsolete_temp=False,
        ),
        FilePlanItem(
            source_path="/dummy/a_copy.pdf",
            file_name="a_copy.pdf",
            proposed_name="a_copy.pdf",
            file_size=1024,
            category="_Karantina_Duplikat",
            proposed_path="/dummy/_Karantina_Duplikat/a_copy.pdf",
            is_duplicate=True,
            is_obsolete_temp=False,
            status_label="File Duplikat",
        ),
        FilePlanItem(
            source_path="/dummy/old_setup.msi",
            file_name="old_setup.msi",
            proposed_name="old_setup.msi",
            file_size=2048,
            category="Installer_Aplikasi",
            proposed_path="/dummy/Installer_Aplikasi/old_setup.msi",
            is_duplicate=False,
            is_obsolete_temp=True,
            status_label="Installer Usang",
        ),
    ]

    summary = finder.calculate_wasted_space(items)

    assert summary["total_bytes"] == 3072
    assert summary["duplicate_count"] == 1
    assert summary["obsolete_count"] == 1
    assert summary["formatted_size"] == "3.0 KB"
