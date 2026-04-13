"""Tests for corpus-grounded planner (manifest + safe paths)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agent.planner import (
    _MAX_FILE_CHARS,
    _function_calls_from_response,
    _read_corpus_file_impl,
    _resolve_safe_corpus_file,
    build_corpus_manifest,
)


def test_build_corpus_manifest_simple_tree(tmp_path: Path) -> None:
    (tmp_path / "Alpha").mkdir()
    (tmp_path / "Alpha" / "one.md").write_text("# one\n", encoding="utf-8")
    (tmp_path / "Beta.md").write_text("# beta\n", encoding="utf-8")
    (tmp_path / "skip.txt").write_text("no", encoding="utf-8")

    tree = build_corpus_manifest(tmp_path)
    assert "Alpha/" in tree
    assert "one.md" in tree
    assert "Beta.md" in tree
    assert "skip.txt" not in tree


def test_resolve_safe_rejects_parent_traversal(tmp_path: Path) -> None:
    (tmp_path / "safe.md").write_text("x", encoding="utf-8")
    assert _resolve_safe_corpus_file(tmp_path, "../safe.md") is None
    assert _resolve_safe_corpus_file(tmp_path, "safe.md/../evil.md") is None
    assert _resolve_safe_corpus_file(tmp_path, "safe.md") is not None


def test_read_corpus_file_truncates(tmp_path: Path) -> None:
    body = "x" * (_MAX_FILE_CHARS + 500)
    (tmp_path / "big.md").write_text(body, encoding="utf-8")
    out = _read_corpus_file_impl(tmp_path, "big.md")
    assert len(out) < len(body) + 50
    assert "Truncated" in out


def test_read_corpus_file_missing(tmp_path: Path) -> None:
    out = _read_corpus_file_impl(tmp_path, "nope.md")
    assert "Error" in out


def test_function_calls_from_response_filters_types() -> None:
    fc = SimpleNamespace(type="function_call", name="read_corpus_file", call_id="c1", arguments="{}")
    msg = SimpleNamespace(type="message")
    response = SimpleNamespace(output=[msg, fc])
    found = _function_calls_from_response(response)
    assert len(found) == 1
    assert found[0].call_id == "c1"


@pytest.mark.skipif(
    not Path("corpus/eldyrwild-markdown").resolve().exists(),
    reason="Elderwyld corpus not checked in",
)
def test_manifest_includes_migrating_forest_sample() -> None:
    root = Path("corpus/eldyrwild-markdown").resolve()
    text = build_corpus_manifest(root)
    assert "Migrating Forest" in text
    assert "the_migrating_forest_executive_dm_summary.md" in text
