"""Modul resolusi alamat sumber daya (read-only) dan direktori data pengguna (writable).

Mendukung dua mode eksekusi secara mulus:
1. Mode pengembangan (development) langsung dari repositori proyek.
2. Mode terpaket (PyInstaller `--onedir` / frozen) melalui `sys._MEIPASS` untuk aset
   read-only serta folder AppData / XDG `~/.local/share/rapihin-aja` untuk penyimpanan
   riwayat transaksi Undo yang membutuhkan izin tulis.
"""

import os
from pathlib import Path
import sys

APP_DISPLAY_NAME: str = "Rapihin Aja"
APP_PACKAGE_NAME: str = "rapihin-aja"


def get_base_dir() -> Path:
    """Mengembalikan direktori dasar proyek atau folder bundle PyInstaller (`_MEIPASS`)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def get_resource_path(relative_path: str) -> Path:
    """Meresolusi alamat file aset read-only (JSON aturan, QSS, ikon) lintas mode.

    Args:
        relative_path: Alamat relatif dari root proyek (misal: `'data/default_rules.json'`).

    Returns:
        Objek `pathlib.Path` menuju sumber daya target.
    """
    raw_path = Path(relative_path)
    if raw_path.is_absolute():
        return raw_path

    base_dir = get_base_dir()
    candidate = base_dir / raw_path

    if getattr(sys, "frozen", False):
        return candidate

    if candidate.exists():
        return candidate
    if raw_path.exists():
        return raw_path
    return candidate


def get_user_data_dir(app_name: str = APP_PACKAGE_NAME) -> Path:
    """Mengembalikan dan membuat folder data pengguna yang memiliki izin tulis.

    Lokasi per sistem operasi:
    - Windows: `%APPDATA%\\<app_name>`
    - macOS: `~/Library/Application Support/<app_name>`
    - Linux: `$XDG_DATA_HOME/<app_name>` atau `~/.local/share/<app_name>`

    Args:
        app_name: Nama folder data aplikasi (default: `'rapihin-aja'`).

    Returns:
        Objek `pathlib.Path` direktori data pengguna yang dipastikan sudah tersedia.
    """
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA", "").strip()
        base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME", "").strip()
        base_dir = Path(xdg_data) if xdg_data else Path.home() / ".local" / "share"

    data_dir = base_dir / app_name
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_default_undo_log_path(app_name: str = APP_PACKAGE_NAME) -> Path:
    """Mengembalikan alamat default file `undo_history.json` di folder data pengguna."""
    return get_user_data_dir(app_name) / "undo_history.json"


def load_stylesheet_text(relative_path: str = "ui/styles.qss") -> str:
    """Membaca teks stylesheet QSS dari aset aplikasi secara aman.

    Returns:
        Isi file QSS dalam bentuk string UTF-8, atau string kosong jika gagal dibaca.
    """
    qss_path = get_resource_path(relative_path)
    if qss_path.exists() and qss_path.is_file():
        try:
            return qss_path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


def get_icon_path(relative_path: str = "assets/icon.png") -> str:
    """Mengembalikan alamat file ikon aplikasi sebagai string agar layer `ui/` bebas `pathlib`."""
    icon_path = get_resource_path(relative_path)
    if icon_path.exists() and icon_path.is_file():
        return str(icon_path)
    return ""
