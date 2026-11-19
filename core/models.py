"""Modul kontrak data utama untuk Smart File Organizer.

Menyediakan struktur dataclass yang digunakan bersama oleh modul ui/ dan core/
agar seluruh anggota tim dapat bekerja secara paralel tanpa merge conflict.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FilePlanItem:
    """Representasi rencana perapian untuk satu file yang dipindai.

    Attributes:
        source_path: Alamat lengkap file asli (string dari pathlib.Path).
        file_name: Nama file asli beserta ekstensinya (misal: 'IMG_001.pdf').
        proposed_name: Usulan nama file baru hasil aturan lokal atau AI Hybrid
            (fallback ke file_name jika tidak diubah).
        file_size: Ukuran file dalam satuan bytes.
        category: Nama folder kategori tujuan (misal: 'Administrasi_dan_Nilai' atau '_Karantina_Duplikat').
        proposed_path: Alamat lengkap tujuan file setelah dirapikan.
        is_duplicate: Penanda apakah file ini terdeteksi sebagai duplikat.
        is_obsolete_temp: Penanda apakah file ini merupakan installer/file sementara usang.
        status_label: Teks indikator status untuk ditampilkan pada badge tabel UI.
        suggested_name: Usulan nama baru dari Offline Smart Rename (opsional).
        is_rename_approved: Penanda persetujuan pengguna untuk menerapkan `suggested_name`.
        is_skipped: Penanda bahwa file dibiarkan tetap di folder asal (perlu cek manual).
    """

    source_path: str
    file_name: str
    proposed_name: str
    file_size: int
    category: str
    proposed_path: str
    is_duplicate: bool = False
    is_obsolete_temp: bool = False
    status_label: str = "Siap Dirapikan"
    suggested_name: Optional[str] = None
    is_rename_approved: bool = True
    is_skipped: bool = False

    @property
    def final_name(self) -> str:
        """Mengembalikan nama file akhir yang akan diterapkan saat eksekusi.

        Mengembalikan `suggested_name` jika `is_rename_approved` bernilai True
        dan `suggested_name` tidak kosong; selain itu mengembalikan `file_name`.
        """
        if self.is_rename_approved and self.suggested_name and self.suggested_name.strip():
            return self.suggested_name
        return self.file_name


FileItem = FilePlanItem


@dataclass
class TransactionRecord:
    """Catatan satu transaksi perpindahan file untuk mendukung fitur 1-Click Undo.

    Attributes:
        old_path: Alamat lengkap file sebelum dipindahkan/diubah namanya.
        new_path: Alamat lengkap file setelah dipindahkan/diubah namanya.
        timestamp: Waktu transaksi dalam format ISO-8601 (opsional).
    """

    old_path: str
    new_path: str
    timestamp: str = ""

    def to_dict(self) -> dict[str, str]:
        """Mengonversi catatan transaksi menjadi dictionary siap simpan ke JSON."""
        return {
            "old_path": self.old_path,
            "new_path": self.new_path,
            "timestamp": self.timestamp,
        }
