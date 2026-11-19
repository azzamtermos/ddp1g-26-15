"""Paket inti (core) Smart File Organizer.

Berisi model kontrak data, pemindai folder, pendeteksi duplikat,
dan eksekutor pemindahan file aman berbasis pathlib.Path dan send2trash.
"""

from core.models import FilePlanItem, TransactionRecord
from core.safety import validate_target_directory

__all__ = ["FilePlanItem", "TransactionRecord", "validate_target_directory"]
