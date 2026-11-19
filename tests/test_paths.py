"""Pengujian unit untuk modul core.paths dan integrasi path bundled/user data.

Memverifikasi resolusi path aset read-only pada mode development maupun mode
frozen PyInstaller (`sys.frozen=True` + `sys._MEIPASS`), serta lokasi folder
data pengguna yang writable lintas Linux, macOS, dan Windows.
"""

from pathlib import Path
import sys

import pytest

from core.organizer import SafeFileOrganizer
from core.paths import (
    get_default_undo_log_path,
    get_icon_path,
    get_resource_path,
    get_user_data_dir,
    load_stylesheet_text,
)
from core.scanner import FolderScanner


def test_get_resource_path_development_mode() -> None:
    """Memastikan aset proyek teresolusi di mode development dan path absolut dipertahankan."""
    rules_path = get_resource_path("data/default_rules.json")
    qss_path = get_resource_path("ui/styles.qss")
    icon_path = get_resource_path("assets/icon.png")

    assert rules_path.exists() and rules_path.is_file()
    assert qss_path.exists() and qss_path.is_file()
    assert icon_path.exists() and icon_path.is_file()

    abs_example = rules_path.resolve()
    assert get_resource_path(str(abs_example)) == abs_example


def test_get_resource_path_and_helpers_in_frozen_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan mode PyInstaller membaca aset dari sys._MEIPASS."""
    (tmp_path / "data").mkdir()
    (tmp_path / "ui").mkdir()
    (tmp_path / "assets").mkdir()

    fake_rules = tmp_path / "data" / "default_rules.json"
    fake_rules.write_text('{"default_category": "Lainnya", "categories": {}}', encoding="utf-8")

    fake_qss = tmp_path / "ui" / "styles.qss"
    fake_qss.write_text("QMainWindow { background-color: #F8FAFC; }", encoding="utf-8")

    fake_icon = tmp_path / "assets" / "icon.png"
    fake_icon.write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert get_resource_path("data/default_rules.json") == fake_rules
    assert "background-color: #F8FAFC" in load_stylesheet_text()

    resolved_icon = get_icon_path()
    assert isinstance(resolved_icon, str)
    assert resolved_icon == str(fake_icon)


def test_get_user_data_dir_linux_xdg_and_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan direktori data Linux mengikuti XDG_DATA_HOME atau fallback ~/.local/share."""
    monkeypatch.setattr(sys, "platform", "linux")

    xdg_dir = tmp_path / "custom_xdg"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_dir))
    resolved_xdg = get_user_data_dir("rapihin-aja")
    assert resolved_xdg == xdg_dir / "rapihin-aja"
    assert resolved_xdg.exists() and resolved_xdg.is_dir()

    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    fake_home = tmp_path / "home_guru"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    resolved_default = get_user_data_dir("rapihin-aja")
    assert resolved_default == fake_home / ".local" / "share" / "rapihin-aja"
    assert resolved_default.exists() and resolved_default.is_dir()


def test_get_user_data_dir_windows_and_macos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan direktori data Windows (%APPDATA%) dan macOS (Application Support)."""
    fake_appdata = tmp_path / "AppData" / "Roaming"
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(fake_appdata))
    win_dir = get_user_data_dir("rapihin-aja")
    assert win_dir == fake_appdata / "rapihin-aja"
    assert win_dir.exists() and win_dir.is_dir()

    fake_mac_home = tmp_path / "mac_home"
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(Path, "home", lambda: fake_mac_home)
    mac_dir = get_user_data_dir("rapihin-aja")
    assert mac_dir == fake_mac_home / "Library" / "Application Support" / "rapihin-aja"
    assert mac_dir.exists() and mac_dir.is_dir()


def test_core_modules_respect_frozen_and_user_data_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan FolderScanner membaca _MEIPASS dan SafeFileOrganizer menulis ke user data dir."""
    bundle_dir = tmp_path / "bundle"
    (bundle_dir / "data").mkdir(parents=True)
    (bundle_dir / "data" / "default_rules.json").write_text(
        '{"default_category": "Arsip_Kustom", "categories": {}}',
        encoding="utf-8",
    )
    (bundle_dir / "data" / "text_rules.json").write_text("{}", encoding="utf-8")

    user_xdg = tmp_path / "xdg_data"
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(user_xdg))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    scanner = FolderScanner()
    assert scanner.default_category == "Arsip_Kustom"

    organizer = SafeFileOrganizer()
    expected_undo_path = get_default_undo_log_path("rapihin-aja")
    assert organizer.undo_log_path == expected_undo_path
    assert expected_undo_path.exists()
