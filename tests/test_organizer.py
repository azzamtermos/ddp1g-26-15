"""Pengujian unit untuk modul core.organizer (SafeFileOrganizer).

Menguji skenario keamanan operasi file (`safe-file-ops`):
1. Penanganan konflik nama otomatis (`_1`, `_2`, dst.) tanpa menimpa file lama.
2. Eksekusi pemindahan file normal ke kategori dan file duplikat ke `_Karantina_Duplikat/`.
3. Pemulihan 100% file ke lokasi semula menggunakan `undo_last_operation()`.
4. Pembersihan folder karantina ke Recycle Bin via `empty_quarantine_to_trash()`
   dengan melakukan mocking pada `send2trash` agar tidak mengotori Recycle Bin asli.
"""

from pathlib import Path

import pytest

from core.models import FilePlanItem
from core.organizer import SafeFileOrganizer


def test_resolve_conflict_path_adds_incremental_suffix(tmp_path: Path) -> None:
    """Memastikan resolve_conflict_path menambahkan akhiran _1 dan _2 jika nama file sudah ada."""
    undo_log = tmp_path / "data" / "undo_history.json"
    organizer = SafeFileOrganizer(undo_log_path=str(undo_log))

    target_dir = tmp_path / "Dokumen_Ajar"
    target_dir.mkdir()

    existing_file = target_dir / "RPP.pdf"
    existing_file.write_text("Versi pertama", encoding="utf-8")

    resolved_1 = organizer.resolve_conflict_path(existing_file)
    assert resolved_1 == target_dir / "RPP_1.pdf"

    # Buat RPP_1.pdf lalu uji kembali agar menghasilkan RPP_2.pdf
    resolved_1.write_text("Versi kedua", encoding="utf-8")
    resolved_2 = organizer.resolve_conflict_path(existing_file)
    assert resolved_2 == target_dir / "RPP_2.pdf"


def test_execute_plan_and_undo_restores_all_files_including_quarantine(
    tmp_path: Path,
) -> None:
    """Menguji alur penuh execute_plan ke kategori & karantina, lalu 100% pulih saat Undo."""
    undo_log = tmp_path / "data" / "undo_history.json"
    organizer = SafeFileOrganizer(undo_log_path=str(undo_log))

    source_normal = tmp_path / "Silabus_Matematika.pdf"
    source_duplicate = tmp_path / "Silabus_Matematika_Copy.pdf"

    source_normal.write_text("Isi silabus", encoding="utf-8")
    source_duplicate.write_text("Isi silabus", encoding="utf-8")

    target_normal = tmp_path / "Dokumen_Ajar" / "Silabus_Matematika.pdf"
    target_quarantine = (
        tmp_path / "_Karantina_Duplikat" / "Silabus_Matematika_Copy.pdf"
    )

    items = [
        FilePlanItem(
            source_path=str(source_normal),
            file_name=source_normal.name,
            proposed_name=source_normal.name,
            file_size=11,
            category="Dokumen_Ajar",
            proposed_path=str(target_normal),
            is_duplicate=False,
        ),
        FilePlanItem(
            source_path=str(source_duplicate),
            file_name=source_duplicate.name,
            proposed_name=source_duplicate.name,
            file_size=11,
            category="_Karantina_Duplikat",
            proposed_path=str(target_quarantine),
            is_duplicate=True,
            status_label="File Duplikat",
        ),
    ]

    # 1. Jalankan execute_plan
    moved_count, errors = organizer.execute_plan(items)
    assert moved_count == 2
    assert errors == []
    assert not source_normal.exists()
    assert not source_duplicate.exists()
    assert target_normal.exists()
    assert target_quarantine.exists()

    # 2. Jalankan undo_last_operation dan pastikan 100% file kembali ke lokasi asal
    restored_count, undo_errors = organizer.undo_last_operation()
    assert restored_count == 2
    assert undo_errors == []
    assert source_normal.exists()
    assert source_duplicate.exists()
    assert not target_normal.exists()
    assert not target_quarantine.exists()


def test_empty_quarantine_to_trash_uses_send2trash_mock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan empty_quarantine_to_trash memanggil send2trash tanpa menghapus permanen."""
    undo_log = tmp_path / "data" / "undo_history.json"
    organizer = SafeFileOrganizer(undo_log_path=str(undo_log))

    quarantine_dir = tmp_path / "_Karantina_Duplikat"
    quarantine_dir.mkdir()

    dup_file_1 = quarantine_dir / "kembar_1.pdf"
    dup_file_2 = quarantine_dir / "kembar_2.jpg"
    dup_file_1.write_text("duplikat 1", encoding="utf-8")
    dup_file_2.write_text("duplikat 2", encoding="utf-8")

    trashed_paths: list[str] = []

    def fake_send2trash(path_str: str) -> None:
        trashed_paths.append(path_str)

    monkeypatch.setattr("core.organizer.send2trash", fake_send2trash)

    trashed_count, errors = organizer.empty_quarantine_to_trash(str(tmp_path))

    assert trashed_count == 2
    assert errors == []
    assert len(trashed_paths) == 2
    assert str(dup_file_1) in trashed_paths
    assert str(dup_file_2) in trashed_paths


def test_undo_removes_newly_created_empty_dirs_but_keeps_non_empty_dirs(
    tmp_path: Path,
) -> None:
    """Memastikan Undo menghapus folder kategori baru yang kosong namun mempertahankan folder yang masih berisi file."""
    undo_log = tmp_path / "data" / "undo_history.json"
    organizer = SafeFileOrganizer(undo_log_path=str(undo_log))

    file_a = tmp_path / "Materi_Python.pdf"
    file_b = tmp_path / "Rekap_Nilai.xlsx"
    file_a.write_text("Materi", encoding="utf-8")
    file_b.write_text("Nilai", encoding="utf-8")

    dir_dokumen = tmp_path / "Dokumen_Ajar"
    dir_nilai = tmp_path / "Administrasi_Nilai"

    items = [
        FilePlanItem(
            source_path=str(file_a),
            file_name=file_a.name,
            proposed_name=file_a.name,
            file_size=6,
            category="Dokumen_Ajar",
            proposed_path=str(dir_dokumen / file_a.name),
        ),
        FilePlanItem(
            source_path=str(file_b),
            file_name=file_b.name,
            proposed_name=file_b.name,
            file_size=5,
            category="Administrasi_Nilai",
            proposed_path=str(dir_nilai / file_b.name),
        ),
    ]

    moved_count, errors = organizer.execute_plan(items)
    assert moved_count == 2
    assert errors == []
    assert dir_dokumen.exists()
    assert dir_nilai.exists()

    # Tambahkan 1 file lain ke dalam Administrasi_Nilai agar folder tersebut tidak kosong saat Undo
    extra_file = dir_nilai / "File_Tambahan_Manual.xlsx"
    extra_file.write_text("Jangan dihapus", encoding="utf-8")

    restored_count, undo_errors = organizer.undo_last_operation()
    assert restored_count == 2
    assert undo_errors == []

    # (a) Folder Dokumen_Ajar harus ikut terhapus karena baru dibuat dan kini kosong
    assert not dir_dokumen.exists()

    # (b) Folder Administrasi_Nilai TIDAK boleh terhapus karena masih ada extra_file di dalamnya
    assert dir_nilai.exists()
    assert extra_file.exists()


def test_execute_plan_skips_items_marked_is_skipped(tmp_path: Path) -> None:
    """Memastikan file dengan is_skipped=True dibiarkan di folder asal dan tidak masuk log Undo."""
    undo_log = tmp_path / "data" / "undo_history.json"
    organizer = SafeFileOrganizer(undo_log_path=str(undo_log))

    skipped_file = tmp_path / "scan_dokumen.pdf"
    normal_file = tmp_path / "RPP_Bab1.pdf"
    skipped_file.write_bytes(b"%PDF-1.4")
    normal_file.write_bytes(b"RPP")

    items = [
        FilePlanItem(
            source_path=str(skipped_file),
            file_name=skipped_file.name,
            proposed_name=skipped_file.name,
            file_size=8,
            category="Lainnya",
            proposed_path=str(skipped_file),
            is_skipped=True,
            status_label="Dibiarkan (Perlu Cek Manual)",
        ),
        FilePlanItem(
            source_path=str(normal_file),
            file_name=normal_file.name,
            proposed_name=normal_file.name,
            file_size=3,
            category="Materi_dan_Bahan_Ajar",
            proposed_path=str(tmp_path / "Materi_dan_Bahan_Ajar" / normal_file.name),
            is_skipped=False,
        ),
    ]

    moved_count, errors = organizer.execute_plan(items)

    assert moved_count == 1
    assert errors == []
    assert skipped_file.exists()
    assert not normal_file.exists()
    assert (tmp_path / "Materi_dan_Bahan_Ajar" / "RPP_Bab1.pdf").exists()
    assert "scan_dokumen.pdf" not in undo_log.read_text(encoding="utf-8")


def test_execute_plan_applies_final_name_approval_and_undo_restores_original_name(
    tmp_path: Path,
) -> None:
    """Memastikan final_name diterapkan sesuai persetujuan rename dan Undo mengembalikan nama asli."""
    undo_log = tmp_path / "data" / "undo_history.json"
    organizer = SafeFileOrganizer(undo_log_path=str(undo_log))

    wa_pdf = tmp_path / "DOC-20261118-WA0004.pdf"
    doc_docx = tmp_path / "Document (2).docx"
    dup_pdf = tmp_path / "DOC-20261118-WA0005.pdf"

    wa_pdf.write_bytes(b"undangan")
    doc_docx.write_bytes(b"modul")
    dup_pdf.write_bytes(b"undangan")

    items = [
        FilePlanItem(
            source_path=str(wa_pdf),
            file_name=wa_pdf.name,
            proposed_name="Undangan_Rapat_Komite.pdf",
            file_size=8,
            category="Administrasi_dan_Nilai",
            proposed_path=str(
                tmp_path / "Administrasi_dan_Nilai" / "Undangan_Rapat_Komite.pdf"
            ),
            suggested_name="Undangan_Rapat_Komite.pdf",
            is_rename_approved=True,
        ),
        FilePlanItem(
            source_path=str(doc_docx),
            file_name=doc_docx.name,
            proposed_name="Modul_Ajar_Python.docx",
            file_size=5,
            category="Materi_dan_Bahan_Ajar",
            proposed_path=str(
                tmp_path / "Materi_dan_Bahan_Ajar" / "Modul_Ajar_Python.docx"
            ),
            suggested_name="Modul_Ajar_Python.docx",
            is_rename_approved=False,
        ),
        FilePlanItem(
            source_path=str(dup_pdf),
            file_name=dup_pdf.name,
            proposed_name=dup_pdf.name,
            file_size=8,
            category="_Karantina_Duplikat",
            proposed_path=str(tmp_path / "_Karantina_Duplikat" / dup_pdf.name),
            is_duplicate=True,
            suggested_name="Seharusnya_Diabaikan.pdf",
            is_rename_approved=True,
            status_label="File Duplikat",
        ),
    ]

    moved_count, errors = organizer.execute_plan(items)

    assert moved_count == 3
    assert errors == []
    assert (tmp_path / "Administrasi_dan_Nilai" / "Undangan_Rapat_Komite.pdf").exists()
    assert (tmp_path / "Materi_dan_Bahan_Ajar" / "Document (2).docx").exists()
    assert (tmp_path / "_Karantina_Duplikat" / "DOC-20261118-WA0005.pdf").exists()

    restored_count, undo_errors = organizer.undo_last_operation()

    assert restored_count == 3
    assert undo_errors == []
    assert wa_pdf.exists()
    assert doc_docx.exists()
    assert dup_pdf.exists()
    assert not (tmp_path / "Administrasi_dan_Nilai").exists()
    assert not (tmp_path / "Materi_dan_Bahan_Ajar").exists()
    assert not (tmp_path / "_Karantina_Duplikat").exists()


def test_undo_graceful_skip_when_file_modified_or_removed_externally(
    tmp_path: Path,
) -> None:
    """Memastikan Undo melewati file yang sudah dipindah manual di luar aplikasi tanpa crash."""
    undo_log = tmp_path / "data" / "undo_history.json"
    organizer = SafeFileOrganizer(undo_log_path=str(undo_log))

    file_1 = tmp_path / "DOC-1.pdf"
    file_2 = tmp_path / "Soal_UTS.pdf"
    file_1.write_bytes(b"edaran")
    file_2.write_bytes(b"soal")

    items = [
        FilePlanItem(
            source_path=str(file_1),
            file_name=file_1.name,
            proposed_name="Surat_Edaran_Sekolah.pdf",
            file_size=6,
            category="Administrasi_dan_Nilai",
            proposed_path=str(
                tmp_path / "Administrasi_dan_Nilai" / "Surat_Edaran_Sekolah.pdf"
            ),
            suggested_name="Surat_Edaran_Sekolah.pdf",
            is_rename_approved=True,
        ),
        FilePlanItem(
            source_path=str(file_2),
            file_name=file_2.name,
            proposed_name=file_2.name,
            file_size=4,
            category="Soal_dan_Ujian",
            proposed_path=str(tmp_path / "Soal_dan_Ujian" / file_2.name),
        ),
    ]

    moved_count, errors = organizer.execute_plan(items)
    assert moved_count == 2
    assert errors == []

    # Simulasi pengguna memindahkan file kedua secara manual di luar aplikasi
    moved_target = tmp_path / "Soal_dan_Ujian" / "Soal_UTS.pdf"
    moved_target.rename(tmp_path / "dipindah_manual.pdf")

    restored_count, notes = organizer.undo_last_operation()

    assert restored_count == 1
    assert file_1.exists()
    assert not (tmp_path / "Administrasi_dan_Nilai").exists()
    assert not (tmp_path / "Soal_dan_Ujian").exists()
    assert organizer.last_undo_skipped_count == 1
    assert any("1 file dilewati" in msg for msg in notes)
