"""Modul pemindai direktori, kategorisasi pintar, dan AI Hybrid Smart Renaming.

Bertanggung jawab memindai folder berantakan, menentukan kategori tujuan
berdasarkan aturan di data/default_rules.json, serta menyiapkan kerangka
ekstraksi teks dokumen dan usulan nama file pintar.
"""

from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

from core.models import FilePlanItem


class FolderScanner:
    """Kelas untuk memindai folder dan menyusun rencana perapian file (FilePlanItem).

    Attributes:
        rules_path: Objek Path menuju file JSON aturan pengelompokan kategori.
        rules_data: Dictionary berisi aturan kategori, ekstensi, dan kata kunci.
    """

    def __init__(self, rules_path: str = "data/default_rules.json") -> None:
        """Menginisialisasi pemindai folder dan memuat aturan kategori dari file JSON.

        Args:
            rules_path: Alamat relatif atau absolut menuju file konfigurasi JSON.
        """
        self.rules_path: Path = Path(rules_path)
        self.rules_data: dict[str, Any] = self._load_rules()

    def _load_rules(self) -> dict[str, Any]:
        """Memuat aturan kategori dari file JSON dengan fallback aman jika file tidak ditemukan.

        Returns:
            Dictionary berisi aturan pengelompokan kategori.
        """
        if self.rules_path.exists() and self.rules_path.is_file():
            try:
                content = self.rules_path.read_text(encoding="utf-8")
                return json.loads(content)
            except (OSError, json.JSONDecodeError):
                pass

        return {
            "quarantine_folder": "_Karantina_Duplikat",
            "default_category": "Lainnya",
            "categories": {},
        }

    def scan_directory(
        self,
        folder_path: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[FilePlanItem]:
        """Memindai seluruh file tingkat pertama di dalam folder target.

        Mengabaikan subfolder kategori dan folder `_Karantina_Duplikat/`,
        melaporkan progres secara berkala lewat `progress_callback`, serta
        mengembalikan daftar rencana perapian (`FilePlanItem`).

        Args:
            folder_path: Alamat folder yang akan dipindai.
            progress_callback: Fungsi callback opsional `callback(persen, pesan)`
                untuk memperbarui QProgressBar di antarmuka secara real-time.

        Returns:
            Daftar objek `FilePlanItem` hasil pemindaian.
        """
        target_dir = Path(folder_path)
        if not target_dir.exists() or not target_dir.is_dir():
            return []

        try:
            all_entries = [
                entry
                for entry in target_dir.iterdir()
                if entry.is_file() and not entry.name.startswith(".")
            ]
        except PermissionError:
            return []

        total_files = len(all_entries)
        if total_files == 0:
            if progress_callback is not None:
                progress_callback(100, "Folder kosong atau tidak ada file untuk dipindai.")
            return []

        plan_items: list[FilePlanItem] = []

        for index, file_path in enumerate(all_entries, start=1):
            try:
                file_size = file_path.stat().st_size
            except OSError:
                file_size = 0

            doc_hint = self.extract_document_hint(file_path)
            proposed_name = self.propose_smart_name(file_path, doc_hint=doc_hint)
            category = self.determine_category(file_path)
            proposed_path = target_dir / category / proposed_name

            item = FilePlanItem(
                source_path=str(file_path),
                file_name=file_path.name,
                proposed_name=proposed_name,
                file_size=file_size,
                category=category,
                proposed_path=str(proposed_path),
                is_duplicate=False,
                is_obsolete_temp=False,
                status_label="Siap Dirapikan",
            )
            plan_items.append(item)

            if progress_callback is not None:
                percent = int((index / total_files) * 100)
                progress_callback(percent, f"Memindai file ({index}/{total_files}): {file_path.name}")

        return plan_items

    def determine_category(self, file_path: Path) -> str:
        """Menentukan nama folder kategori tujuan berdasarkan kata kunci nama dan ekstensi file.

        Args:
            file_path: Objek `pathlib.Path` dari file yang diperiksa.

        Returns:
            Nama kategori tujuan (misal: 'Dokumen_Ajar', 'Administrasi_Nilai', atau 'Lainnya').
        """
        categories: dict[str, dict[str, list[str]]] = self.rules_data.get("categories", {})
        default_category: str = str(self.rules_data.get("default_category", "Lainnya"))

        ext = file_path.suffix.lower()
        stem_lower = file_path.stem.lower()

        # Prioritas 1: Kecocokan kata kunci pada nama file sekaligus ekstensi yang relevan
        for category_name, rule in categories.items():
            keywords = [kw.lower() for kw in rule.get("keywords", [])]
            extensions = [e.lower() for e in rule.get("extensions", [])]
            if ext in extensions and any(kw in stem_lower for kw in keywords):
                return category_name

        # Prioritas 2: Kecocokan berdasarkan ekstensi file
        for category_name, rule in categories.items():
            extensions = [e.lower() for e in rule.get("extensions", [])]
            if ext in extensions:
                return category_name

        return default_category

    def extract_document_hint(self, file_path: Path) -> str | None:
        """Mengekstrak cuplikan teks halaman pertama dokumen/PDF untuk membantu penamaan pintar.

        Saat ini berfungsi sebagai stub/placeholder aman yang mengembalikan `None`.
        Dapat dikembangkan menggunakan `pypdf.PdfReader` untuk membaca judul dari halaman pertama PDF.

        Args:
            file_path: Objek `pathlib.Path` dari file dokumen.

        Returns:
            String cuplikan teks/judul dokumen jika berhasil diekstrak, atau `None`.
        """
        _ = file_path
        return None

    def propose_smart_name(self, file_path: Path, doc_hint: str | None = None) -> str:
        """Mengusulkan nama file baru yang rapi dan deskriptif (Pipeline AI Hybrid / Lokal).

        Dapat diintegrasikan dengan API AI (seperti Qwen/OpenAI-compatible via
        konfigurasi `.env` dan `python-dotenv`) untuk merapikan nama file berantakan
        berdasarkan `doc_hint` atau nama asli, dengan fallback otomatis ke
        `file_path.name` apabila sedang offline atau API key tidak tersedia.

        Args:
            file_path: Objek `pathlib.Path` dari file asli.
            doc_hint: Cuplikan isi/judul dokumen dari `extract_document_hint` (opsional).

        Returns:
            Usulan nama file baru beserta ekstensinya (default fallback: `file_path.name`).
        """
        _ = doc_hint
        return file_path.name
