"""Tests for hashing and deduplication utilities."""

import pytest

from app.utils.hashing import file_sha256, row_fingerprint


def test_row_fingerprint_deterministic():
    row = {"Plant": "1031", "Order Cost": "1500", "Notes": "abc"}
    h1 = row_fingerprint(row)
    h2 = row_fingerprint(row)
    assert h1 == h2


def test_row_fingerprint_order_independent():
    row1 = {"A": "1", "B": "2"}
    row2 = {"B": "2", "A": "1"}
    assert row_fingerprint(row1) == row_fingerprint(row2)


def test_row_fingerprint_different_data():
    row1 = {"A": "1", "B": "2"}
    row2 = {"A": "1", "B": "3"}
    assert row_fingerprint(row1) != row_fingerprint(row2)


def test_row_fingerprint_handles_none():
    row = {"A": None, "B": "2"}
    h = row_fingerprint(row)
    assert len(h) == 64  # SHA-256 hex length


def test_file_sha256(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    h1 = file_sha256(str(f))
    assert len(h1) == 64

    f2 = tmp_path / "test2.txt"
    f2.write_text("hello world")
    assert file_sha256(str(f2)) == h1

    f3 = tmp_path / "different.txt"
    f3.write_text("different content")
    assert file_sha256(str(f3)) != h1
