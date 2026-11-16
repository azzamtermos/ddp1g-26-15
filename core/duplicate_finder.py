"""Modul pendeteksi file duplikat (SHA-256), installer usang, dan kalkulator ruang penyimpanan.

Bertanggung jawab melakukan pengecekan duplikat dua tahap (ukuran file + hash SHA-256
per chunk), menandai file installer atau sementara yang sudah usang, serta menghitung
estimasi penghematan ruang penyimpanan.
"""

from collections.abc import Callable
import hashlib
from pathlib import Path
import time

from core.models import FilePlanItem


class DuplicateFinder:
    """Kelas untuk mendeteksi file duplikat, installer usang, dan potensi ruang hemat."""

    QUARANTINE_FOLDER: str = "_Karantina_Duplikat"
    OBSOLETE_EXTENSIONS: tuple[str, ...] = (
        ".exe",
        ".msi",
        ".dmg",
        ".deb",
        ".apk",
        ".tmp",
        ".crdownload",
        ".part",
    )

    def calculate_file_hash(self, file_path: Path, chunk_size: int = 65536) -> str:
        """Menghitung nilai hash SHA-256 dari isi file secara bertahap per chunk.

        Membaca file dalam potongan kecil (`chunk_size`) agar penggunaan memori (RAM)
        tetap ringan meskipun membaca file berukuran ratusan megabyte atau gigabyte.

        Args:
            file_path: Objek `pathlib.Path` menuju file yang akan dihitung hash-nya.
            chunk_size: Ukuran byte pembacaan per langkah (default 64 KB).

        Returns:
            String heksadesimal hash SHA-256, atau string kosong jika file gagal dibaca.
        """
        sha256_hash = hashlib.sha256()
        try:
            with file_path.open("rb") as f:
                while chunk := f.read(chunk_size):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except OSError:
            return ""

    def mark_duplicates(
        self,
        items: list[FilePlanItem],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[FilePlanItem]:
        """Menandai file duplikat menggunakan penyaringan ukuran file dan hash SHA-256.

        File yang terdeteksi memiliki isi identik dengan file sebelumnya akan ditandai:
        - `is_duplicate = True`
        - `category = "_Karantina_Duplikat"`
        - `proposed_path` diarahkan ke dalam subfolder `_Karantina_Duplikat/`
        - `status_label = "File Duplikat"`

        Args:
            items: Daftar `FilePlanItem` hasil pemindaian awal dari `FolderScanner`.
            progress_callback: Fungsi callback opsional `callback(persen, pesan)`
                untuk melaporkan progres pengecekan duplikat ke UI.

        Returns:
            Daftar `FilePlanItem` yang telah diperbarui status duplikatnya.
        """
        if not items:
            return items

        # Tahap 1: Kelompokkan item berdasarkan file_size (hanya ukuran > 0 yang berpotensi duplikat)
        size_groups: dict[int, list[FilePlanItem]] = {}
        for item in items:
            if item.file_size > 0:
                size_groups.setdefault(item.file_size, []).append(item)

        candidates: list[FilePlanItem] = [
            item
            for group in size_groups.values()
            if len(group) > 1
            for item in group
        ]

        total_candidates = len(candidates)
        if total_candidates == 0:
            if progress_callback is not None:
                progress_callback(100, "Tidak ditemukan kandidat ukuran file kembar.")
            return items

        # Tahap 2: Hitung hash SHA-256 hanya untuk kandidat yang ukurannya sama
        seen_hashes: dict[tuple[int, str], str] = {}

        for index, item in enumerate(candidates, start=1):
            source = Path(item.source_path)
            file_hash = self.calculate_file_hash(source)

            if file_hash:
                key = (item.file_size, file_hash)
                if key in seen_hashes:
                    item.is_duplicate = True
                    item.category = self.QUARANTINE_FOLDER
                    quarantine_target = source.parent / self.QUARANTINE_FOLDER / item.proposed_name
                    item.proposed_path = str(quarantine_target)
                    item.status_label = "File Duplikat"
                else:
                    seen_hashes[key] = item.source_path

            if progress_callback is not None:
                percent = int((index / total_candidates) * 100)
                progress_callback(
                    percent,
                    f"Memeriksa kemiripan isi file ({index}/{total_candidates}): {item.file_name}",
                )

        return items

    def detect_obsolete_installers(
        self,
        items: list[FilePlanItem],
        age_days: int = 30,
    ) -> list[FilePlanItem]:
        """Mendeteksi file installer atau file sementara yang usianya melebihi batas hari.

        File yang belum berstatus duplikat namun berekstensi installer/sementara
        dan berumur lebih tua dari `age_days` akan ditandai dengan
        `is_obsolete_temp = True` dan `status_label = "Installer Usang"`.

        Args:
            items: Daftar `FilePlanItem` yang akan diperiksa.
            age_days: Batas usia file dalam hari untuk dianggap usang (default: 30 hari).

        Returns:
            Daftar `FilePlanItem` yang telah diperbarui penanda installer usangnya.
        """
        now = time.time()
        age_threshold_seconds = age_days * 86400

        for item in items:
            if item.is_duplicate:
                continue

            source = Path(item.source_path)
            if source.suffix.lower() in self.OBSOLETE_EXTENSIONS:
                try:
                    mtime = source.stat().st_mtime
                    if (now - mtime) >= age_threshold_seconds:
                        item.is_obsolete_temp = True
                        item.status_label = "Installer Usang"
                except OSError:
                    continue

        return items

    def calculate_wasted_space(self, items: list[FilePlanItem]) -> dict[str, int | str]:
        """Menghitung total estimasi ruang penyimpanan yang bisa dihemat.

        Menjumlahkan ukuran file dari seluruh item yang terdeteksi sebagai duplikat
        (`is_duplicate`) maupun installer usang (`is_obsolete_temp`).

        Args:
            items: Daftar `FilePlanItem` hasil pemindaian dan analisis duplikat.

        Returns:
            Dictionary berisi:
            - `total_bytes` (int): Total ukuran byte yang dapat dihemat.
            - `duplicate_count` (int): Jumlah file duplikat.
            - `obsolete_count` (int): Jumlah file installer/sementara usang.
            - `formatted_size` (str): Teks ukuran ramah pengguna (misal: '12.4 MB').
        """
        duplicate_count = sum(1 for item in items if item.is_duplicate)
        obsolete_count = sum(1 for item in items if item.is_obsolete_temp and not item.is_duplicate)
        total_bytes = sum(
            item.file_size
            for item in items
            if item.is_duplicate or item.is_obsolete_temp
        )

        return {
            "total_bytes": total_bytes,
            "duplicate_count": duplicate_count,
            "obsolete_count": obsolete_count,
            "formatted_size": self._format_bytes(total_bytes),
        }

    @staticmethod
    def _format_bytes(size_in_bytes: int) -> str:
        """Mengonversi ukuran bytes menjadi teks satuan yang mudah dibaca manusia."""
        if size_in_bytes <= 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_in_bytes)
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} B"
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size_in_bytes} B"
