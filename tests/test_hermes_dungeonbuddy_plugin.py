"""Unit tests for the Hermes spike plugin (tool handlers only; Hermes not required)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

PLUGIN_INIT = (
    Path(__file__).resolve().parents[1]
    / "integrations"
    / "hermes"
    / "plugins"
    / "dungeonbuddy"
    / "__init__.py"
)


def _load_plugin():
    spec = importlib.util.spec_from_file_location(
        "dungeonbuddy_hermes_plugin_v0", PLUGIN_INIT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def plugin():
    return _load_plugin()


def test_handle_dungeon_search_empty_query(plugin):
    raw = plugin.handle_dungeon_search({})
    data = json.loads(raw)
    assert data["success"] is False
    assert "query" in data["error"].lower()


def test_handle_dungeon_search_finds_term(tmp_path, monkeypatch, plugin):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "note.md").write_text("# Session\nLysandra checks the wagon again.\n", encoding="utf-8")
    monkeypatch.setenv("DUNGEONBUDDY_CORPUS_ROOT", str(corpus))

    raw = plugin.handle_dungeon_search({"query": "Lysandra wagon", "top_k": 5})
    data = json.loads(raw)
    assert data["success"] is True
    assert data["match_count"] >= 1
    m0 = data["matches"][0]
    assert m0["path"] == "note.md"
    assert "Lysandra" in m0["excerpt"] or "wagon" in m0["excerpt"].lower()


def test_handle_dungeon_get_document_blocks_path_escape(tmp_path, monkeypatch, plugin):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    monkeypatch.setenv("DUNGEONBUDDY_CORPUS_ROOT", str(corpus))

    raw = plugin.handle_dungeon_get_document({"path": "../outside.md"})
    data = json.loads(raw)
    assert data["success"] is False
    assert "escape" in data["error"].lower()


def test_handle_dungeon_check_continuity_delegates_to_search(tmp_path, monkeypatch, plugin):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.md").write_text("bugbear Stacey rumor only.\n", encoding="utf-8")
    monkeypatch.setenv("DUNGEONBUDDY_CORPUS_ROOT", str(corpus))

    raw = plugin.handle_dungeon_check_continuity({"claim": "Stacey bugbear", "top_k": 3})
    data = json.loads(raw)
    assert data["tool"] == "dungeon_check_continuity"
    assert data["status"] == "evidence_candidates_only"
    assert "continuity_warning" in data
