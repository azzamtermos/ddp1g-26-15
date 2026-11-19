"""Modul pemindai direktori, kategorisasi pintar, dan AI Hybrid Smart Renaming.

Bertanggung jawab memindai folder berantakan, menentukan kategori tujuan
berdasarkan aturan berbasis data di `data/default_rules.json` dan `data/text_rules.json`,
serta menyiapkan kerangka ekstraksi teks dokumen dan usulan nama file pintar.
"""

from collections.abc import Callable
import json
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

from pypdf import PdfReader

from core.models import FilePlanItem


class FolderScanner:
    """Kelas untuk memindai folder dan menyusun rencana perapian file (FilePlanItem).

    Mematuhi aturan `data-driven-rules`: seluruh daftar kata kunci, ekstensi,
    dan pola regex dimuat satu kali saat inisialisasi dari file JSON di `data/`.

    Attributes:
        rules_path: Objek Path menuju file JSON aturan pengelompokan kategori.
        text_rules_path: Objek Path menuju file JSON aturan pola teks dan penamaan.
        rules_data: Dictionary mentah hasil pembacaan `default_rules.json`.
        text_rules_data: Dictionary mentah hasil pembacaan `text_rules.json`.
    """

    MAX_EXTRACT_FILE_SIZE_BYTES: int = 50 * 1024 * 1024
    CLASSIFICATION_TEXT_LIMIT: int = 400
    TITLE_SCAN_MAX_LINES: int = 15
    MIN_TITLE_WORDS: int = 2
    MAX_TITLE_WORDS: int = 7
    MAX_OUTPUT_TITLE_WORDS: int = 6

    def __init__(
        self,
        rules_path: str = "data/default_rules.json",
        text_rules_path: str = "data/text_rules.json",
    ) -> None:
        """Menginisialisasi pemindai folder serta memuat seluruh aturan JSON satu kali.

        Args:
            rules_path: Alamat relatif atau absolut menuju file konfigurasi kategori JSON.
            text_rules_path: Alamat relatif atau absolut menuju file pola teks JSON.
        """
        self.rules_path: Path = self._resolve_data_path(rules_path)
        self.text_rules_path: Path = self._resolve_data_path(text_rules_path)

        self.rules_data: dict[str, Any] = self._load_json(
            self.rules_path,
            fallback={
                "quarantine_folder": "_Karantina_Duplikat",
                "default_category": "Lainnya",
                "categories": {},
            },
        )
        self.text_rules_data: dict[str, Any] = self._load_json(
            self.text_rules_path,
            fallback={
                "generic_filename_patterns": [],
                "document_title_whitelist": [],
                "letterhead_filter_patterns": [],
                "duplicate_markers": [],
            },
        )

        # Pre-kompilasi aturan kategori ke set agar cepat saat iterasi file
        self.default_category: str = str(self.rules_data.get("default_category", "Lainnya"))
        self.quarantine_folder: str = str(
            self.rules_data.get("quarantine_folder", "_Karantina_Duplikat")
        )
        self._token_pattern: re.Pattern[str] = re.compile(r"[a-z0-9]+")
        self._sep_pattern: re.Pattern[str] = re.compile(r"[\s_-]+")

        self._compiled_categories: list[tuple[str, set[str], set[str], set[str]]] = []
        for category_name, rule in self.rules_data.get("categories", {}).items():
            if not isinstance(rule, dict):
                continue
            extensions = {str(e).lower() for e in rule.get("extensions", [])}
            exact_keywords = {str(kw).lower() for kw in rule.get("exact_keywords", [])}
            raw_partial = list(rule.get("partial_keywords", [])) + list(rule.get("keywords", []))
            partial_keywords = {
                self._sep_pattern.sub(" ", str(kw).lower()).strip()
                for kw in raw_partial
                if str(kw).strip()
            }
            self._compiled_categories.append(
                (str(category_name), extensions, exact_keywords, partial_keywords)
            )

        # Pre-kompilasi pola teks & regex satu kali di __init__
        self.generic_filename_patterns: list[re.Pattern[str]] = self._compile_patterns(
            self.text_rules_data.get("generic_filename_patterns", [])
        )
        self.letterhead_filter_patterns: list[re.Pattern[str]] = self._compile_patterns(
            self.text_rules_data.get("letterhead_filter_patterns", [])
        )
        self.document_title_whitelist: set[str] = {
            str(item).lower()
            for item in self.text_rules_data.get("document_title_whitelist", [])
        }
        self._compiled_title_whitelist: list[re.Pattern[str]] = []
        for term in self.document_title_whitelist:
            normalized_term = self._sep_pattern.sub(" ", term).strip()
            if normalized_term:
                self._compiled_title_whitelist.append(
                    re.compile(r"\b" + re.escape(normalized_term) + r"\b", re.IGNORECASE)
                )
        self._illegal_chars_pattern: re.Pattern[str] = re.compile(r'[<>:"/\\|?*]+')
        self._title_word_pattern: re.Pattern[str] = re.compile(r"[A-Za-z0-9]+")

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

            is_generic = self._is_generic_filename(file_path)
            doc_hint = self.extract_document_hint(file_path) if is_generic else None
            category = self.determine_category(file_path, doc_text=doc_hint)

            if category == self.default_category:
                is_skipped = True
                suggested_name: str | None = None
                proposed_name = file_path.name
                proposed_path = file_path
                status_label = "Dibiarkan (Perlu Cek Manual)"
            else:
                is_skipped = False
                smart_name = (
                    self.propose_smart_name(file_path, doc_hint=doc_hint)
                    if (is_generic and doc_hint)
                    else file_path.name
                )
                suggested_name = smart_name if smart_name != file_path.name else None
                proposed_name = suggested_name if suggested_name else file_path.name
                proposed_path = target_dir / category / proposed_name
                status_label = "Siap Dirapikan"

            item = FilePlanItem(
                source_path=str(file_path),
                file_name=file_path.name,
                proposed_name=proposed_name,
                file_size=file_size,
                category=category,
                proposed_path=str(proposed_path),
                is_duplicate=False,
                is_obsolete_temp=False,
                status_label=status_label,
                suggested_name=suggested_name,
                is_rename_approved=True,
                is_skipped=is_skipped,
            )
            plan_items.append(item)

            if progress_callback is not None:
                percent = int((index / total_files) * 100)
                progress_callback(percent, f"Memindai file ({index}/{total_files}): {file_path.name}")

        return plan_items

    def _is_generic_filename(self, file_path: Path) -> bool:
        """Memeriksa apakah nama file (tanpa ekstensi) tergolong generik tanpa konteks jelas."""
        stem = file_path.stem.strip()
        if not stem:
            return True
        return any(pattern.search(stem) for pattern in self.generic_filename_patterns)

    def _extract_pdf_first_page_text(self, file_path: Path) -> str:
        """Membaca teks halaman pertama file PDF secara aman tanpa crash pada file rusak/terkunci."""
        try:
            reader = PdfReader(str(file_path))
            if reader.is_encrypted and not reader.decrypt(""):
                return ""
            if not reader.pages:
                return ""
            return reader.pages[0].extract_text() or ""
        except Exception:  # noqa: BLE001
            return ""

    def _extract_docx_text(self, file_path: Path) -> str:
        """Membaca teks paragraf awal `.docx` dari `word/document.xml` menggunakan zipfile & xml."""
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                xml_bytes = zf.read("word/document.xml")
            root = ET.fromstring(xml_bytes)
        except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError):
            return ""

        paragraphs: list[str] = []
        for elem in root.iter():
            if elem.tag.endswith("}p") or elem.tag == "p":
                texts = [
                    child.text
                    for child in elem.iter()
                    if (child.tag.endswith("}t") or child.tag == "t") and child.text
                ]
                paragraph_text = "".join(texts).strip()
                if paragraph_text:
                    paragraphs.append(paragraph_text)
                    if len(paragraphs) >= 40:
                        break
        return "\n".join(paragraphs)

    def _clean_title_words(self, line: str) -> list[str]:
        """Membersihkan karakter ilegal dan memastikan panjang kata sesuai syarat judul (2-7 kata)."""
        cleaned = self._illegal_chars_pattern.sub(" ", line)
        words = self._title_word_pattern.findall(cleaned)
        if not (self.MIN_TITLE_WORDS <= len(words) <= self.MAX_TITLE_WORDS):
            return []
        if not any(any(c.isalpha() for c in w) and len(w) >= 2 for w in words):
            return []
        return words

    def _extract_clean_title(self, raw_text: str) -> str | None:
        """Menyaring kop surat dengan filter 2 lapis (Aturan A & B) dan menyusun judul rapi."""
        lines = [
            " ".join(line.split())
            for line in raw_text.splitlines()
            if line.strip()
        ][: self.TITLE_SCAN_MAX_LINES]

        tier1_clean_whitelist: list[list[str]] = []
        tier2_whitelist: list[list[str]] = []
        tier3_non_letterhead: list[list[str]] = []

        for line in lines:
            words = self._clean_title_words(line)
            if not words:
                continue

            normalized_line = self._sep_pattern.sub(" ", line).strip()
            matches_whitelist = any(
                p.search(normalized_line) for p in self._compiled_title_whitelist
            )
            matches_letterhead = any(
                p.search(line) for p in self.letterhead_filter_patterns
            )

            if matches_whitelist and not matches_letterhead:
                tier1_clean_whitelist.append(words)
            elif matches_whitelist:
                tier2_whitelist.append(words)
            elif not matches_letterhead:
                tier3_non_letterhead.append(words)

        chosen_words: list[str] | None = None
        if tier1_clean_whitelist:
            chosen_words = tier1_clean_whitelist[0]
        elif tier2_whitelist:
            chosen_words = tier2_whitelist[0]
        elif tier3_non_letterhead:
            chosen_words = tier3_non_letterhead[0]

        if not chosen_words:
            return None

        limited_words = chosen_words[: self.MAX_OUTPUT_TITLE_WORDS]
        return "_".join(word.capitalize() for word in limited_words)

    def determine_category(
        self,
        file_path: Path,
        doc_text: str | None = None,
    ) -> str:
        """Menentukan nama folder kategori tujuan berdasarkan ekstensi pasti, nama file, dan isi teks.

        Args:
            file_path: Objek `pathlib.Path` dari file yang diperiksa.
            doc_text: Teks hasil ekstraksi halaman/paragraf awal dokumen (opsional).

        Returns:
            Nama kategori tujuan (misal: 'Administrasi_dan_Nilai', 'Soal_dan_Ujian',
            'Materi_dan_Bahan_Ajar', atau 'Lainnya').
        """
        ext = file_path.suffix.lower()
        stem_lower = file_path.stem.lower()

        # Langkah 1: Kecocokan ekstensi pasti
        for category_name, extensions, _, _ in self._compiled_categories:
            if ext in extensions:
                return category_name

        # Langkah 2: Kecocokan kata kunci pada nama file
        tokens = set(self._token_pattern.findall(stem_lower))
        normalized_stem = self._sep_pattern.sub(" ", stem_lower).strip()
        for category_name, _, exact_keywords, partial_keywords in self._compiled_categories:
            if exact_keywords & tokens or any(kw in normalized_stem for kw in partial_keywords):
                return category_name

        # Langkah 3: Kecocokan kata kunci dari ~400 karakter pertama isi teks dokumen
        if doc_text:
            snippet = doc_text[: self.CLASSIFICATION_TEXT_LIMIT].lower()
            text_tokens = set(self._token_pattern.findall(snippet))
            normalized_text = self._sep_pattern.sub(" ", snippet).strip()
            for category_name, _, exact_keywords, partial_keywords in self._compiled_categories:
                if exact_keywords & text_tokens or any(
                    kw in normalized_text for kw in partial_keywords
                ):
                    return category_name

        return self.default_category

    def extract_document_hint(self, file_path: Path) -> str | None:
        """Mengekstrak teks awal halaman 1 PDF atau paragraf awal DOCX secara aman.

        Hanya memproses `.pdf` dan `.docx` yang berukuran di bawah batas aman (50 MB).
        Mengembalikan `None` apabila file bukan PDF/DOCX, rusak, terenkripsi, atau
        tidak memiliki teks terbaca (misalnya PDF gambar murni hasil scan).

        Args:
            file_path: Objek `pathlib.Path` dari file dokumen.

        Returns:
            String cuplikan teks dokumen jika berhasil diekstrak, atau `None`.
        """
        ext = file_path.suffix.lower()
        if ext not in {".pdf", ".docx"}:
            return None

        try:
            if not file_path.exists() or not file_path.is_file():
                return None
            file_size = file_path.stat().st_size
        except OSError:
            return None

        if file_size <= 0 or file_size > self.MAX_EXTRACT_FILE_SIZE_BYTES:
            return None

        extracted = (
            self._extract_pdf_first_page_text(file_path)
            if ext == ".pdf"
            else self._extract_docx_text(file_path)
        )
        if not extracted.strip():
            return None

        return extracted[:2000]

    def propose_smart_name(self, file_path: Path, doc_hint: str | None = None) -> str:
        """Mengusulkan nama file baru yang rapi berdasarkan cuplikan teks dokumen.

        Hanya mengusulkan nama baru apabila nama file asli terdeteksi generik dan
        ditemukan judul bersih (2-7 kata) yang lolos filter kop surat 2 lapis.
        Jika tidak memenuhi syarat, selalu fallback mengembalikan `file_path.name`.

        Args:
            file_path: Objek `pathlib.Path` dari file asli.
            doc_hint: Cuplikan isi dokumen dari `extract_document_hint` (opsional).

        Returns:
            Usulan nama file baru berformat `Title_Case_Dengan_Garis_Bawah` + ekstensi,
            atau `file_path.name` jika tidak memenuhi syarat.
        """
        if not doc_hint or not self._is_generic_filename(file_path):
            return file_path.name

        clean_title = self._extract_clean_title(doc_hint)
        if not clean_title:
            return file_path.name

        return f"{clean_title}{file_path.suffix}"
