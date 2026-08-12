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


def test_handle_dungeon_search_disabled_by_default(plugin, monkeypatch):
    monkeypatch.delenv("DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK", raising=False)
    raw = plugin.handle_dungeon_search({"query": "Lysandra"})
    data = json.loads(raw)
    assert data["success"] is False
    assert "dungeon_context_lookup" in data["error"]


def test_handle_dungeon_search_ignores_dungeonbuddy_managed_storage(
    tmp_path, monkeypatch, plugin
):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "note.md").write_text("# Session\nLysandra checks the wagon again.\n", encoding="utf-8")
    managed = corpus / "_dungeonbuddy" / "sources" / "doc-1" / "source.md"
    managed.parent.mkdir(parents=True)
    managed.write_text("# Managed\nZorbaxian uniqueterm managed only.\n", encoding="utf-8")
    monkeypatch.setenv("DUNGEONBUDDY_CORPUS_ROOT", str(corpus))
    monkeypatch.setenv("DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK", "1")

    raw = plugin.handle_dungeon_search({"query": "Zorbaxian uniqueterm", "top_k": 5})
    data = json.loads(raw)
    assert data["success"] is True
    assert data["match_count"] == 0

    raw_visible = plugin.handle_dungeon_search({"query": "Lysandra wagon", "top_k": 5})
    visible = json.loads(raw_visible)
    assert visible["success"] is True
    assert visible["match_count"] >= 1


def test_handle_dungeon_search_finds_term_when_fallback_enabled(tmp_path, monkeypatch, plugin):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "note.md").write_text("# Session\nLysandra checks the wagon again.\n", encoding="utf-8")
    monkeypatch.setenv("DUNGEONBUDDY_CORPUS_ROOT", str(corpus))
    monkeypatch.setenv("DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK", "1")

    raw = plugin.handle_dungeon_search({"query": "Lysandra wagon", "top_k": 5})
    data = json.loads(raw)
    assert data["success"] is True
    assert data["match_count"] >= 1
    m0 = data["matches"][0]
    assert m0["path"] == "note.md"
    assert "Lysandra" in m0["excerpt"] or "wagon" in m0["excerpt"].lower()


def test_handle_dungeon_get_document_blocks_path_escape(tmp_path, monkeypatch, plugin):
    corpus = tmp_path / "corpus" / "eldyrwild-markdown"
    corpus.mkdir(parents=True)
    monkeypatch.setenv("DUNGEONBUDDY_REPO", str(tmp_path))
    monkeypatch.setenv("DUNGEONBUDDY_ELDYRWILD_CORPUS", str(corpus))

    raw = plugin.handle_dungeon_get_document({"path": "../outside.md"})
    data = json.loads(raw)
    assert data["success"] is False


def test_handle_dungeon_get_document_reads_eldyrwild_relative(tmp_path, monkeypatch, plugin):
    repo = tmp_path
    eldyrwild = repo / "corpus" / "eldyrwild-markdown"
    eldyrwild.mkdir(parents=True)
    campaign_dir = eldyrwild / "Campaign"
    campaign_dir.mkdir(parents=True)
    note = campaign_dir / "note.md"
    note.write_text("# Title\nCanon line about Lysandro.\n", encoding="utf-8")
    monkeypatch.setenv("DUNGEONBUDDY_REPO", str(repo))

    raw = plugin.handle_dungeon_get_document({"path": "Campaign/note.md"})
    data = json.loads(raw)
    assert data["success"] is True
    assert data["path_kind"] == "eldyrwild_corpus_relative"
    assert "Lysandro" in data["content"]

    raw2 = plugin.handle_dungeon_get_document(
        {"path": "corpus/eldyrwild-markdown/Campaign/note.md"}
    )
    data2 = json.loads(raw2)
    assert data2["success"] is True
    assert "Lysandro" in data2["content"]


def test_handle_dungeon_manifest_index_lists_entries(plugin):
    raw = plugin.handle_dungeon_manifest_index({"limit": 5})
    data = json.loads(raw)
    assert data["success"] is True
    assert data["entry_count"] <= 5
    assert data["entries"]
    first = data["entries"][0]
    assert "route" in first
    assert "source_role" in first
    assert "session_scope" in first


def test_handle_dungeon_context_lookup_session22_end(plugin):
    raw = plugin.handle_dungeon_context_lookup(
        {"question": "What happened at the end of session 22?"}
    )
    data = json.loads(raw)
    assert data["success"] is True
    packet = data["context_packet"]
    summary = data["sufficiency_summary"]
    assert packet["schema"] == "dmb_enriched_planning_context_packet_v1"
    assert summary["admitted_count"] >= 1
    admitted = packet["admitted_evidence"]
    paths = [row["path"] for row in admitted]
    assert all("session 23" not in path.lower() for path in paths)
    for row in admitted:
        assert row.get("evidence_id", "").startswith("ev-")


def test_handle_dungeon_check_continuity_uses_context_lookup_by_default(plugin, monkeypatch):
    monkeypatch.delenv("DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK", raising=False)
    raw = plugin.handle_dungeon_check_continuity({"claim": "Lysandro at the end of session 22"})
    data = json.loads(raw)
    assert data["tool"] == "dungeon_check_continuity"
    assert data["status"] == "manifest_evidence_candidates"
    assert "continuity_warning" in data


def test_handle_dungeon_check_continuity_delegates_to_search_when_fallback_enabled(
    tmp_path, monkeypatch, plugin
):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.md").write_text("bugbear Stacey rumor only.\n", encoding="utf-8")
    monkeypatch.setenv("DUNGEONBUDDY_CORPUS_ROOT", str(corpus))
    monkeypatch.setenv("DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK", "1")

    raw = plugin.handle_dungeon_check_continuity({"claim": "Stacey bugbear", "top_k": 3})
    data = json.loads(raw)
    assert data["tool"] == "dungeon_check_continuity"
    assert data["status"] == "evidence_candidates_only"
    assert "continuity_warning" in data
