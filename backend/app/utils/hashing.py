"""Hashing utilities for file checksums and row fingerprints."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def file_sha256(path: str | Path, chunk_size: int = 8192) -> str:
    """Return the hex SHA-256 digest of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def row_fingerprint(data: dict) -> str:
    """Produce a stable SHA-256 fingerprint from a row dict.

    Keys are sorted, values are stringified.  This allows detection of
    duplicate rows across import batches.
    """
    canonical = json.dumps(
        {k: _normalize_value(v) for k, v in sorted(data.items())},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_value(v: object) -> str | None:
    """Convert a cell value to a stable string representation."""
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ("", "nan", "none", "nat"):
        return None
    return s
