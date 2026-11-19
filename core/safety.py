"""Modul validasi keamanan folder target untuk mencegah modifikasi direktori kritis OS.

Seluruh logika pemeriksaan path (lintas Linux, macOS, dan Windows) ditempatkan
di paket `core/` agar lapisan `ui/` tetap bebas dari impor `os`, `shutil`, atau `pathlib`.
"""

from pathlib import Path, PureWindowsPath
import re

SYSTEM_FOLDER_MSG: str = (
    "Folder ini berisi file penting milik sistem komputer. "
    "Demi keamanan, pilih folder dokumen biasa seperti Downloads atau Dokumen."
)

HOME_OR_DRIVE_MSG: str = (
    "Demi keamanan, jangan rapikan seluruh folder utama pengguna atau drive sekaligus. "
    "Pilih subfolder khusus seperti Downloads, Dokumen, atau folder tugas Anda."
)

_WINDOWS_PATH_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z]:([\\/]|$)")

_WINDOWS_SYSTEM_DIRS: set[str] = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "system volume information",
    "$recycle.bin",
    "recovery",
    "perflogs",
}

_POSIX_SYSTEM_DIRS: set[str] = {
    "bin",
    "boot",
    "dev",
    "etc",
    "lib",
    "lib64",
    "proc",
    "run",
    "sbin",
    "sys",
    "usr",
    "var",
    "system",
    "library",
    "applications",
    "private",
}


def validate_target_directory(folder_path: str) -> tuple[bool, str]:
    """Memvalidasi apakah alamat folder aman untuk dipindai dan dirapikan.

    Menolak direktori sistem operasi (root `/`, `/etc`, `/usr`, `C:\\Windows`,
    `Program Files`, dsb.), root drive (`C:\\`, `D:\\`), serta folder utama
    pengguna langsung (`~`, `/home/<user>`, `C:\\Users\\<user>`) untuk mencegah
    perapian tidak disengaja pada folder kritis.

    Args:
        folder_path: Alamat folder yang dipilih atau dijatuhkan pengguna.

    Returns:
        Tuple `(is_safe, pesan_peringatan)`. Jika aman, mengembalikan `(True, "")`.
    """
    cleaned = folder_path.strip() if folder_path else ""
    if not cleaned:
        return False, "Silakan pilih folder yang ingin dirapikan terlebih dahulu."

    # 1. Penanganan path bergaya Windows (lintas platform)
    if _WINDOWS_PATH_PATTERN.match(cleaned) or cleaned.startswith("\\\\"):
        win_path = PureWindowsPath(cleaned)
        parts = [p.lower().rstrip("\\/") for p in win_path.parts if p.strip()]
        if len(parts) <= 1:
            return False, HOME_OR_DRIVE_MSG

        top_dir = parts[1]
        if top_dir in _WINDOWS_SYSTEM_DIRS:
            return False, SYSTEM_FOLDER_MSG

        if top_dir == "users" and len(parts) in (2, 3):
            return False, HOME_OR_DRIVE_MSG

        return True, ""

    # 2. Penanganan path POSIX (Linux / macOS)
    try:
        resolved = Path(cleaned).expanduser().resolve()
    except OSError:
        return False, "Folder yang dipilih tidak dapat diakses saat ini."

    parts = [p.lower() for p in resolved.parts]
    if len(parts) <= 1:
        return False, SYSTEM_FOLDER_MSG

    top_dir = parts[1]
    if top_dir in _POSIX_SYSTEM_DIRS:
        return False, SYSTEM_FOLDER_MSG

    try:
        home_resolved = Path.home().resolve()
        if resolved == home_resolved:
            return False, HOME_OR_DRIVE_MSG
    except OSError:
        pass

    if len(parts) == 2 and top_dir in {"root", "home", "users"}:
        return False, HOME_OR_DRIVE_MSG

    if len(parts) == 3 and top_dir in {"home", "users"}:
        return False, HOME_OR_DRIVE_MSG

    return True, ""
