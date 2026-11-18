"""Modul eksekutor pemindahan file aman, karantina duplikat, dan 1-Click Undo.

Mematuhi aturan keamanan manipulasi file (`safe-file-ops`):
- Seluruh manipulasi path wajib menggunakan `pathlib.Path`.
- Dilarang keras menggunakan `os.remove()`, `os.unlink()`, atau `shutil.rmtree()`.
- File duplikat dipindahkan ke subfolder `_Karantina_Duplikat/` agar 100% Undo-able.
- Pembersihan folder karantina ke Recycle Bin menggunakan `send2trash`.
"""

from collections.abc import Callable
from datetime import datetime
import json
from pathlib import Path

from send2trash import send2trash

from core.models import FilePlanItem, TransactionRecord


class SafeFileOrganizer:
    """Kelas untuk mengeksekusi rencana perapian file dengan jaminan keamanan dan Undo.

    Attributes:
        undo_log_path: Objek `pathlib.Path` menuju file JSON riwayat transaksi Undo.
    """

    QUARANTINE_FOLDER: str = "_Karantina_Duplikat"

    def __init__(self, undo_log_path: str = "data/undo_history.json") -> None:
        """Menyiapkan alamat penyimpanan log Undo dan memastikan file JSON tersedia.

        Args:
            undo_log_path: Alamat relatif atau absolut menuju file log transaksi JSON.
        """
        raw_path = Path(undo_log_path)
        if not raw_path.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            self.undo_log_path: Path = project_root / raw_path
        else:
            self.undo_log_path = raw_path
        self._ensure_undo_log_exists()

    def _ensure_undo_log_exists(self) -> None:
        """Membuat folder `data/` dan file `undo_history.json` berisi `[]` jika belum ada."""
        try:
            self.undo_log_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.undo_log_path.exists():
                self.undo_log_path.write_text("[]", encoding="utf-8")
        except OSError:
            pass

    def resolve_conflict_path(self, target_path: Path) -> Path:
        """Menghasilkan path tujuan baru dengan penomoran otomatis jika nama file sudah ada.

        Mencegah penimpaan (*overwrite*) file lama dengan menambahkan akhiran `_1`, `_2`,
        dan seterusnya sebelum ekstensi file.

        Args:
            target_path: Objek `pathlib.Path` tujuan awal yang ingin diperiksa.

        Returns:
            Objek `pathlib.Path` yang dijamin unik dan belum terpakai di folder tujuan.
        """
        if not target_path.exists():
            return target_path

        parent = target_path.parent
        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1

        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def save_undo_log(
        self,
        transactions: list[dict[str, str]],
        created_dirs: list[str] | None = None,
    ) -> None:
        """Menyimpan daftar catatan transaksi dan folder baru ke `data/undo_history.json`.

        Args:
            transactions: Daftar dictionary berisi `old_path`, `new_path`, dan `timestamp`.
            created_dirs: Daftar alamat folder yang baru dibuat saat eksekusi (opsional).
        """
        self._ensure_undo_log_exists()
        try:
            payload = {
                "transactions": transactions,
                "created_dirs": created_dirs or [],
            }
            content = json.dumps(payload, indent=2, ensure_ascii=False)
            self.undo_log_path.write_text(content, encoding="utf-8")
        except OSError:
            pass

    def execute_plan(
        self,
        items: list[FilePlanItem],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> tuple[int, list[str]]:
        """Mengeksekusi pemindahan file ke folder kategori dan karantina duplikat.

        Seluruh perpindahan file (termasuk file duplikat yang masuk ke `_Karantina_Duplikat/`)
        dilakukan dengan `pathlib.Path.rename()` dan dicatat ke `data/undo_history.json`
        beserta daftar folder baru (`created_dirs`) sehingga 100% dapat dipulihkan lewat Undo.

        Args:
            items: Daftar `FilePlanItem` yang akan dipindahkan.
            progress_callback: Fungsi callback opsional `callback(persen, pesan)`
                untuk memperbarui progres di UI.

        Returns:
            Tuple berisi `(jumlah_berhasil, daftar_pesan_error)`.
        """
        if not items:
            return 0, []

        total_items = len(items)
        success_count = 0
        errors: list[str] = []
        transactions: list[dict[str, str]] = []
        created_dirs: list[str] = []
        timestamp_now = datetime.now().isoformat(timespec="seconds")

        for index, item in enumerate(items, start=1):
            source_path = Path(item.source_path)
            if not source_path.exists():
                errors.append(f"File tidak ditemukan: {item.file_name}")
                continue

            desired_target = Path(item.proposed_path)
            target_dir = desired_target.parent
            try:
                if not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_dir_str = str(target_dir)
                    if target_dir_str not in created_dirs:
                        created_dirs.append(target_dir_str)

                final_target = self.resolve_conflict_path(desired_target)
                source_path.rename(final_target)

                record = TransactionRecord(
                    old_path=str(source_path),
                    new_path=str(final_target),
                    timestamp=timestamp_now,
                )
                transactions.append(record.to_dict())
                success_count += 1
            except PermissionError:
                errors.append(
                    f"Gagal memindahkan '{item.file_name}' karena sedang dibuka di aplikasi lain."
                )
            except OSError as exc:
                errors.append(f"Gagal memindahkan '{item.file_name}': {exc}")

            if progress_callback is not None:
                percent = int((index / total_items) * 100)
                progress_callback(
                    percent,
                    f"Merapikan file ({index}/{total_items}): {item.file_name}",
                )

        if transactions:
            self.save_undo_log(transactions, created_dirs=created_dirs)

        return success_count, errors

    def undo_last_operation(self) -> tuple[int, list[str]]:
        """Mengembalikan seluruh file dari transaksi terakhir ke lokasi dan nama aslinya.

        Membaca catatan dari `data/undo_history.json` (mendukung format objek baru maupun
        list lama), memulihkan file dari `new_path` ke `old_path` secara terbalik (LIFO)
        menggunakan `pathlib.Path.rename()`, serta menghapus folder di `created_dirs`
        yang benar-benar kosong menggunakan `Path.rmdir()`.

        Returns:
            Tuple berisi `(jumlah_dipulihkan, daftar_pesan_error)`.
        """
        self._ensure_undo_log_exists()
        try:
            raw_content = self.undo_log_path.read_text(encoding="utf-8")
            parsed_data = json.loads(raw_content)
        except (OSError, json.JSONDecodeError):
            return 0, ["Gagal membaca file riwayat Undo."]

        if isinstance(parsed_data, dict):
            transactions: list[dict[str, str]] = parsed_data.get("transactions", [])
            created_dirs: list[str] = parsed_data.get("created_dirs", [])
        elif isinstance(parsed_data, list):
            transactions = parsed_data
            created_dirs = []
        else:
            transactions = []
            created_dirs = []

        if not transactions:
            return 0, ["Tidak ada riwayat perapian yang dapat dibatalkan."]

        restored_count = 0
        errors: list[str] = []
        remaining_transactions: list[dict[str, str]] = []

        for entry in reversed(transactions):
            old_path = Path(entry.get("old_path", ""))
            new_path = Path(entry.get("new_path", ""))

            if not new_path.exists():
                errors.append(f"File '{new_path.name}' sudah dipindahkan atau dihapus dari lokasi tujuan.")
                continue

            try:
                old_path.parent.mkdir(parents=True, exist_ok=True)
                restore_target = self.resolve_conflict_path(old_path)
                new_path.rename(restore_target)
                restored_count += 1
            except PermissionError:
                errors.append(
                    f"Gagal mengembalikan '{new_path.name}' karena sedang dibuka di aplikasi lain."
                )
                remaining_transactions.append(entry)
            except OSError as exc:
                errors.append(f"Gagal mengembalikan '{new_path.name}': {exc}")
                remaining_transactions.append(entry)

        # Bersihkan folder yang baru dibuat jika sudah benar-benar kosong (terdalam ke terpendek)
        remaining_dirs: list[str] = []
        for dir_str in sorted(
            created_dirs,
            key=lambda p: (len(Path(p).parts), len(p)),
            reverse=True,
        ):
            dir_path = Path(dir_str)
            try:
                if dir_path.exists() and dir_path.is_dir():
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                    else:
                        remaining_dirs.append(dir_str)
            except OSError:
                remaining_dirs.append(dir_str)

        self.save_undo_log(
            list(reversed(remaining_transactions)),
            created_dirs=remaining_dirs if remaining_transactions else [],
        )
        return restored_count, errors

    def empty_quarantine_to_trash(self, base_folder_path: str) -> tuple[int, list[str]]:
        """Memindahkan seluruh isi folder `_Karantina_Duplikat/` ke Recycle Bin / Trash OS.

        Mematuhi aturan `safe-file-ops` dengan menggunakan `send2trash` dan tidak pernah
        menghapus file secara permanen (`os.remove` / `shutil.rmtree` dilarang keras).

        Args:
            base_folder_path: Alamat folder utama tempat `_Karantina_Duplikat/` berada.

        Returns:
            Tuple berisi `(jumlah_dibersihkan, daftar_pesan_error)`.
        """
        quarantine_dir = Path(base_folder_path) / self.QUARANTINE_FOLDER
        if not quarantine_dir.exists() or not quarantine_dir.is_dir():
            return 0, ["Folder _Karantina_Duplikat tidak ditemukan atau sudah kosong."]

        trashed_count = 0
        errors: list[str] = []

        try:
            entries = list(quarantine_dir.iterdir())
        except OSError as exc:
            return 0, [f"Gagal mengakses folder karantina: {exc}"]

        if not entries:
            return 0, ["Folder _Karantina_Duplikat sudah kosong."]

        for entry in entries:
            try:
                send2trash(str(entry))
                trashed_count += 1
            except PermissionError:
                errors.append(
                    f"Gagal membuang '{entry.name}' ke Sampah karena sedang dibuka di aplikasi lain."
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Gagal membuang '{entry.name}' ke Sampah: {exc}")

        return trashed_count, errors
