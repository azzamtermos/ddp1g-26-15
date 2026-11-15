"""Modul kontrak data utama untuk Smart File Organizer.

Menyediakan struktur dataclass yang digunakan bersama oleh modul ui/ dan core/
agar seluruh anggota tim dapat bekerja secara paralel tanpa merge conflict.
"""

from dataclasses import dataclass


@dataclass
class FilePlanItem:
    """Representasi rencana perapian untuk satu file yang dipindai.

    Attributes:
        source_path: Alamat lengkap file asli (string dari pathlib.Path).
        file_name: Nama file asli beserta ekstensinya (misal: 'IMG_001.pdf').
        proposed_name: Usulan nama file baru hasil aturan lokal atau AI Hybrid
            (fallback ke file_name jika tidak diubah).
        file_size: Ukuran file dalam satuan bytes.
        category: Nama folder kategori tujuan (misal: 'Dokumen_Ajar' atau '_Karantina_Duplikat').
        proposed_path: Alamat lengkap tujuan file setelah dirapikan.
        is_duplicate: Penanda apakah file ini terdeteksi sebagai duplikat.
        is_obsolete_temp: Penanda apakah file ini merupakan installer/file sementara usang.
        status_label: Teks indikator status untuk ditampilkan pada badge tabel UI.
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
