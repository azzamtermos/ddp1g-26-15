"""Modul pendeteksi file duplikat (SHA-256), installer usang, dan kalkulator ruang penyimpanan.

Bertanggung jawab melakukan pengecekan duplikat dua tahap (ukuran file + hash SHA-256
per chunk), menandai file installer atau sementara yang sudah usang berdasarkan aturan
berbasis data di `data/default_rules.json` dan `data/text_rules.json`, serta menghitung
estimasi penghematan ruang penyimpanan.
"""

from collections.abc import Callable
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

from core.models import FilePlanItem


class DuplicateFinder:
    """Kelas untuk mendeteksi file duplikat, installer usang, dan potensi ruang hemat.

    Mematuhi aturan `data-driven-rules`: daftar ekstensi usang, batas hari, nama folder
    karantina, dan pola penanda duplikat dimuat satu kali di `__init__()` dari folder `data/`.
    """

    def __init__(
        self,
        rules_path: str = "data/default_rules.json",
        text_rules_path: str = "data/text_rules.json",
    ) -> None:
        """Menginisialisasi pendeteksi duplikat dan memuat aturan JSON satu kali.

        Args:
            rules_path: Alamat relatif atau absolut menuju `data/default_rules.json`.
            text_rules_path: Alamat relatif atau absolut menuju `data/text_rules.json`.
        """
        self.rules_path: Path = self._resolve_data_path(rules_path)
        self.text_rules_path: Path = self._resolve_data_path(text_rules_path)

        rules_data = self._load_json(
            self.rules_path,
            fallback={
                "quarantine_folder": "_Karantina_Duplikat",
                "obsolete_extensions": [],
                "obsolete_age_days": 30,
            },
        )
        text_rules_data = self._load_json(
            self.text_rules_path,
            fallback={
                "generic_filename_patterns": [],
                "duplicate_markers": [],
            },
        )

        self.quarantine_folder: str = str(
            rules_data.get("quarantine_folder", "_Karantina_Duplikat")
        )
        self.obsolete_extensions: set[str] = {
            str(ext).lower() for ext in rules_data.get("obsolete_extensions", [])
        }
        self.default_obsolete_age_days: int = int(rules_data.get("obsolete_age_days", 30))
        self.generic_filename_patterns: list[re.Pattern[str]] = self._compile_patterns(
            text_rules_data.get("generic_filename_patterns", [])
        )
        self.duplicate_markers: list[re.Pattern[str]] = self._compile_patterns(
            text_rules_data.get("duplicate_markers", [])
        )
        self._word_pattern: re.Pattern[str] = re.compile(r"[a-zA-Z]{2,}")
        self._non_alnum_pattern: re.Pattern[str] = re.compile(r"[^a-zA-Z0-9\s_-]")

    @staticmethod
    def _resolve_data_path(file_path: str) -> Path:
        """Meresolusi path relatif terhadap root proyek agar aman dijalankan dari mana pun."""
        raw_path = Path(file_path)
        if not raw_path.is_absolute() and not raw_path.exists():
            project_root = Path(__file__).resolve().parent.parent
            return project_root / raw_path
        return raw_path

    @staticmethod
    def _load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
        """Memuat file JSON dengan fallback minimalis yang aman jika file hilang atau rusak."""
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
            except (OSError, json.JSONDecodeError):
                pass
        return fallback

    @staticmethod
    def _compile_patterns(patterns: list[Any]) -> list[re.Pattern[str]]:
        """Mengompilasi daftar string regex secara aman (mengabaikan pola tidak valid)."""
        compiled: list[re.Pattern[str]] = []
        for raw_pattern in patterns:
            try:
                compiled.append(re.compile(str(raw_pattern), re.IGNORECASE))
            except re.error:
                continue
        return compiled

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

    def _score_filename_quality(self, filename: str) -> int:
        """Menilai kualitas nama file untuk menentukan file utama pada grup duplikat.

        Memberi penalti berat pada nama file generik (dari `generic_filename_patterns`),
        penalti pada penanda salinan/duplikat (dari `duplicate_markers`), serta nilai
        tambah untuk kata deskriptif yang bersih dan bermakna.

        Args:
            filename: Nama file beserta ekstensinya.

        Returns:
            Skor bilangan bulat; skor lebih tinggi menandakan nama file lebih baik.
        """
        stem = Path(filename).stem.strip()
        score = 0

        is_generic = any(p.search(stem) for p in self.generic_filename_patterns)
        if is_generic:
            score -= 50

        if any(p.search(stem) for p in self.duplicate_markers):
            score -= 30

        cleaned_stem = stem
        for pattern in self.duplicate_markers:
            cleaned_stem = pattern.sub("", cleaned_stem)

        if not is_generic:
            words = self._word_pattern.findall(cleaned_stem)
            score += 5 * min(len(words), 6)
            if len(words) >= 2:
                score += 5

        score -= 2 * len(self._non_alnum_pattern.findall(stem))
        return score

    def mark_duplicates(
        self,
        items: list[FilePlanItem],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[FilePlanItem]:
        """Menandai file duplikat menggunakan penyaringan ukuran file dan hash SHA-256.

        Pada setiap grup file dengan isi hash SHA-256 yang identik, file dengan skor
        kualitas nama tertinggi (`_score_filename_quality`) dipertahankan sebagai file
        utama, sedangkan sisanya ditandai:
        - `is_duplicate = True`
        - `category = "_Karantina_Duplikat"` (sesuai `quarantine_folder` di JSON)
        - `proposed_path` diarahkan ke dalam subfolder karantina
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

        # Tahap 1: Kelompokkan item beserta indeks aslinya berdasarkan file_size (> 0)
        size_groups: dict[int, list[tuple[int, FilePlanItem]]] = {}
        for idx, item in enumerate(items):
            if item.file_size > 0:
                size_groups.setdefault(item.file_size, []).append((idx, item))

        candidates: list[tuple[int, FilePlanItem]] = [
            pair
            for group in size_groups.values()
            if len(group) > 1
            for pair in group
        ]

        total_candidates = len(candidates)
        if total_candidates == 0:
            if progress_callback is not None:
                progress_callback(100, "Tidak ditemukan kandidat ukuran file kembar.")
            return items

        # Tahap 2: Hitung hash SHA-256 hanya untuk kandidat yang ukurannya sama
        hash_groups: dict[tuple[int, str], list[tuple[int, FilePlanItem]]] = {}

        for step, (idx, item) in enumerate(candidates, start=1):
            source = Path(item.source_path)
            file_hash = self.calculate_file_hash(source)

            if file_hash:
                key = (item.file_size, file_hash)
                hash_groups.setdefault(key, []).append((idx, item))

            if progress_callback is not None:
                percent = int((step / total_candidates) * 100)
                progress_callback(
                    percent,
                    f"Memeriksa kemiripan isi file ({step}/{total_candidates}): {item.file_name}",
                )

        # Tahap 3: Pilih satu file pemenang terbaik per grup hash identik
        for group in hash_groups.values():
            if len(group) <= 1:
                continue

            winner_idx, _ = min(
                group,
                key=lambda pair: (
                    -self._score_filename_quality(pair[1].file_name),
                    len(pair[1].file_name),
                    pair[1].file_name.lower(),
                    pair[0],
                ),
            )

            for idx, item in group:
                if idx == winner_idx:
                    continue
                source = Path(item.source_path)
                item.is_duplicate = True
                item.is_skipped = False
                item.suggested_name = None
                item.proposed_name = item.file_name
                item.category = self.quarantine_folder
                quarantine_target = (
                    source.parent / self.quarantine_folder / item.file_name
                )
                item.proposed_path = str(quarantine_target)
                item.status_label = "File Duplikat"

        return items

    def detect_obsolete_installers(
        self,
        items: list[FilePlanItem],
        age_days: int | None = None,
    ) -> list[FilePlanItem]:
        """Mendeteksi file installer atau file sementara yang usianya melebihi batas hari.

        File yang belum berstatus duplikat namun berekstensi installer/sementara
        (sesuai `obsolete_extensions` di `data/default_rules.json`) dan berumur lebih
        tua dari `age_days` akan ditandai dengan `is_obsolete_temp = True` dan
        `status_label = "Installer Usang"`.

        Args:
            items: Daftar `FilePlanItem` yang akan diperiksa.
            age_days: Batas usia file dalam hari untuk dianggap usang. Jika `None`,
                menggunakan nilai `obsolete_age_days` dari `data/default_rules.json`.

        Returns:
            Daftar `FilePlanItem` yang telah diperbarui penanda installer usangnya.
        """
        effective_age_days = (
            self.default_obsolete_age_days if age_days is None else age_days
        )
        now = time.time()
        age_threshold_seconds = effective_age_days * 86400

        for item in items:
            if item.is_duplicate:
                continue

            source = Path(item.source_path)
            if source.suffix.lower() in self.obsolete_extensions:
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
        obsolete_count = sum(
            1 for item in items if item.is_obsolete_temp and not item.is_duplicate
        )
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
