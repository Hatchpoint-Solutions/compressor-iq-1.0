"""Stage 1: File discovery.

Scans a directory tree for spreadsheet and CSV files that are likely
maintenance / service data sources.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_EXTENSIONS: set[str] = {".xlsx", ".xls", ".csv", ".tsv"}

SKIP_DIRS: set[str] = {
    "__pycache__", ".git", "node_modules", ".next", "venv", ".venv",
    "env", ".env", "data", "uploads",
}


@dataclass
class DiscoveredFile:
    file_name: str
    file_path: str
    file_type: str
    file_size_bytes: int


def discover_files(
    root_dir: str | Path,
    extensions: set[str] | None = None,
    skip_dirs: set[str] | None = None,
) -> list[DiscoveredFile]:
    """Walk *root_dir* and return spreadsheet/CSV files found.

    Parameters
    ----------
    root_dir : path
        Top-level directory to scan.
    extensions : set, optional
        File extensions to match.  Defaults to xlsx/xls/csv/tsv.
    skip_dirs : set, optional
        Directory names to skip when walking.
    """
    extensions = extensions or SUPPORTED_EXTENSIONS
    skip_dirs = skip_dirs or SKIP_DIRS
    root = Path(root_dir)

    results: list[DiscoveredFile] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]

        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in extensions:
                continue
            full_path = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0

            results.append(DiscoveredFile(
                file_name=fname,
                file_path=full_path,
                file_type=ext.lstrip("."),
                file_size_bytes=size,
            ))

    return results
