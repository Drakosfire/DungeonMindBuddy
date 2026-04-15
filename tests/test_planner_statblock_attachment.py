"""``generate_statblock`` optional corpus baseline path (tool loads file; model names path)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.planner import (
    _read_optional_corpus_statblock_attachment,
    make_tool_dispatcher,
)

_CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "eldyrwild-markdown"
_LYS_CR4 = (
    "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/"
    "captain_lysandra_ironveil_statblock_cr4.md"
)


def test_read_optional_statblock_attachment_empty_means_no_attachment() -> None:
    err, body = _read_optional_corpus_statblock_attachment(_CORPUS, "   ")
    assert err is None and body is None


def test_read_optional_statblock_attachment_rejects_bad_path() -> None:
    err, body = _read_optional_corpus_statblock_attachment(_CORPUS, "../../../etc/passwd")
    assert err and "Error" in err
    assert body is None


@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus not present")
def test_read_optional_statblock_attachment_loads_lysandra_cr4() -> None:
    err, body = _read_optional_corpus_statblock_attachment(_CORPUS, _LYS_CR4)
    assert err is None and body is not None
    assert "CAPTAIN LYSANDRA IRONVEIL" in body
    assert "Challenge Rating" in body


@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus not present")
def test_dispatch_generate_statblock_stub_prefixes_when_baseline_path_set() -> None:
    class _Dummy:
        pass

    dispatch = make_tool_dispatcher(_CORPUS, _Dummy(), "gpt-mock", statblock_stub="STATBLOCK_STUB")
    raw = json.dumps(
        {
            "creature_name": "Test NPC",
            "description": "Bump CR; keep leadership theme.",
            "source_statblock_corpus_path": _LYS_CR4,
        }
    )
    out = dispatch("generate_statblock", raw)
    assert out.startswith("[Attached corpus statblock:")
    assert _LYS_CR4 in out
    assert "chars)" in out
    assert out.endswith("STATBLOCK_STUB")


@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus not present")
def test_dispatch_load_context_markdown_prefixes_body() -> None:
    class _Dummy:
        pass

    dispatch = make_tool_dispatcher(_CORPUS, _Dummy(), "gpt-mock")
    raw = json.dumps({"path": _LYS_CR4})
    out = dispatch("load_context_markdown", raw)
    assert out.startswith("[context attached:")
    assert _LYS_CR4 in out
    assert "CAPTAIN LYSANDRA IRONVEIL" in out


@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus not present")
def test_dispatch_generate_statblock_invalid_baseline_path_errors() -> None:
    class _Dummy:
        pass

    dispatch = make_tool_dispatcher(_CORPUS, _Dummy(), "gpt-mock", statblock_stub="STUB")
    raw = json.dumps(
        {
            "creature_name": "X",
            "description": "y",
            "source_statblock_corpus_path": "no/such/file_statblock.md",
        }
    )
    out = dispatch("generate_statblock", raw)
    assert out.startswith("Error:")
