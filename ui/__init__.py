"""Paket antarmuka pengguna (UI) berbasis PyQt6 untuk Rapihin Aja.

Seluruh komponen di dalam paket ini hanya menangani tampilan visual,
interaksi pengguna, dan worker thread (QThread) tanpa mengimpor modul
manipulasi file seperti os, shutil, atau pathlib.
"""

from ui.main_window import MainWindow
from ui.widgets import (
    CollapsibleDropZoneWidget,
    DropZoneWidget,
    ElidedLabel,
    ElidedPathLabel,
    EmptyStateWidget,
    FilterBarWidget,
    FluentCheckBox,
    FluentProgressStrip,
    PreviewTableWidget,
    RenameBannerWidget,
    StatusBadgeWidget,
)
from ui.worker import OrganizeWorker, ScanWorker

__all__ = [
    "CollapsibleDropZoneWidget",
    "DropZoneWidget",
    "ElidedLabel",
    "ElidedPathLabel",
    "EmptyStateWidget",
    "FilterBarWidget",
    "FluentCheckBox",
    "FluentProgressStrip",
    "MainWindow",
    "OrganizeWorker",
    "PreviewTableWidget",
    "RenameBannerWidget",
    "ScanWorker",
    "StatusBadgeWidget",
]
