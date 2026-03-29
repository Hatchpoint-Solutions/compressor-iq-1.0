"""Tests for file discovery module."""

import os

import pytest

from app.services.ingestion.file_discovery import discover_files


def test_discover_xlsx(tmp_path):
    (tmp_path / "data.xlsx").write_bytes(b"PK")
    (tmp_path / "notes.txt").write_text("ignore me")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "more.csv").write_text("a,b,c")

    found = discover_files(str(tmp_path))
    names = {f.file_name for f in found}
    assert "data.xlsx" in names
    assert "more.csv" in names
    assert "notes.txt" not in names


def test_discover_skip_dirs(tmp_path):
    bad = tmp_path / "node_modules"
    bad.mkdir()
    (bad / "package.csv").write_text("a,b")
    (tmp_path / "good.csv").write_text("x,y")

    found = discover_files(str(tmp_path))
    assert len(found) == 1
    assert found[0].file_name == "good.csv"


def test_discover_empty_dir(tmp_path):
    found = discover_files(str(tmp_path))
    assert found == []


def test_file_type_detection(tmp_path):
    (tmp_path / "a.xlsx").write_bytes(b"PK")
    (tmp_path / "b.csv").write_text("a,b")
    (tmp_path / "c.tsv").write_text("a\tb")

    found = discover_files(str(tmp_path))
    types = {f.file_type for f in found}
    assert types == {"xlsx", "csv", "tsv"}
