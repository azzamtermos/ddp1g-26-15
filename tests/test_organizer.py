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
