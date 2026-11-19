"""Pengujian unit untuk modul core.safety (validate_target_directory).

Memverifikasi pemblokiran direktori sistem operasi kritis dan root pengguna
lintas platform (Linux, macOS, Windows), sekaligus memastikan folder dokumen
biasa seperti Downloads, Documents, dan demo_sandbox tetap diizinkan.
"""

from pathlib import Path

from core.safety import validate_target_directory


def test_blocks_posix_critical_system_directories() -> None:
    """Memastikan direktori kritis sistem Linux dan macOS diblokir termasuk subfoldernya."""
    critical_paths = [
        "/",
        "/bin",
        "/boot",
        "/dev",
        "/etc",
        "/etc/nginx",
        "/lib",
        "/lib64",
        "/proc",
        "/run",
        "/sbin",
        "/sys",
        "/usr",
        "/usr/bin",
        "/usr/local",
        "/var",
        "/System",
        "/System/Library",
        "/Library",
        "/Applications",
        "/private",
    ]
    for path_str in critical_paths:
        is_safe, message = validate_target_directory(path_str)
        assert is_safe is False, f"Seharusnya memblokir: {path_str}"
        assert message != ""


def test_blocks_user_home_root_directories() -> None:
    """Memastikan direktori home utama secara langsung ikut diblokir."""
    home_roots = [
        "~",
        str(Path.home()),
        "/root",
        "/home",
        "/home/guru",
        "/Users",
        "/Users/guru",
    ]
    for path_str in home_roots:
        is_safe, message = validate_target_directory(path_str)
        assert is_safe is False, f"Seharusnya memblokir home root: {path_str}"
        assert message != ""


def test_blocks_windows_critical_and_root_directories() -> None:
    """Memastikan root drive, direktori sistem, dan profil utama Windows diblokir."""
    windows_blocked = [
        r"C:\\",
        r"D:\\",
        "C:",
        r"C:\Windows",
        r"C:\Windows\System32",
        r"C:\Program Files",
        r"C:\Program Files (x86)\App",
        r"C:\ProgramData",
        r"C:\Users",
        r"C:\Users\Guru",
    ]
    for path_str in windows_blocked:
        is_safe, message = validate_target_directory(path_str)
        assert is_safe is False, f"Seharusnya memblokir Windows path: {path_str}"
        assert message != ""


def test_allows_normal_user_subfolders_and_sandbox(tmp_path: Path) -> None:
    """Memastikan folder dokumen biasa, Downloads, dan demo_sandbox tetap diizinkan."""
    allowed_paths = [
        "~/Downloads",
        "/home/guru/Downloads",
        "/Users/guru/Documents",
        r"C:\Users\Guru\Downloads",
        r"C:\Users\Guru\Desktop\Tugas",
        str(tmp_path),
        str(Path(__file__).resolve().parent.parent / "demo_sandbox"),
    ]
    for path_str in allowed_paths:
        is_safe, message = validate_target_directory(path_str)
        assert is_safe is True, f"Seharusnya mengizinkan: {path_str}"
        assert message == ""


def test_empty_path_rejected_with_friendly_message() -> None:
    """Memastikan input kosong ditolak dan seluruh pesan peringatan bebas istilah teknis."""
    forbidden_jargon = ("exception", "traceback", "sha-256", "oserror")

    for empty_val in ("", "   "):
        is_safe, message = validate_target_directory(empty_val)
        assert is_safe is False
        assert message != ""
        assert not any(term in message.lower() for term in forbidden_jargon)

    for sample_blocked in ("/", "/etc", r"C:\Windows", "~"):
        _, message = validate_target_directory(sample_blocked)
        assert not any(term in message.lower() for term in forbidden_jargon)
