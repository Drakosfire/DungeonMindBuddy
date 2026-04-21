"""Tests for corpus-grounded planner (manifest + safe paths)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agent.planner import (
    _MAX_FILE_CHARS,
    _function_calls_from_response,
    _read_corpus_file_impl,
    _resolve_safe_corpus_file,
    build_corpus_manifest,
    build_corpus_path_ref_index,
    make_tool_dispatcher,
    merge_planning_turn_details_chain,
    PlanningTurnDetail,
)


def test_build_corpus_manifest_simple_tree(tmp_path: Path) -> None:
    (tmp_path / "Alpha").mkdir()
    (tmp_path / "Alpha" / "one.md").write_text("# one\n", encoding="utf-8")
    (tmp_path / "Beta.md").write_text("# beta\n", encoding="utf-8")
    (tmp_path / "skip.txt").write_text("no", encoding="utf-8")

    tree = build_corpus_manifest(tmp_path)
    assert "Alpha/" in tree
    assert "one.md" in tree
    assert "  [c:" in tree
    assert "Beta.md" in tree
    assert "skip.txt" not in tree


def test_assemble_recap_draft_returns_recap_body(tmp_path: Path) -> None:
    rel = "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    notes_path = tmp_path / rel
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(
        "Session 20 Recap\n\nFirst para.\n\nFirst para.\n",
        encoding="utf-8",
    )
    idx = build_corpus_path_ref_index(tmp_path)
    dispatch = make_tool_dispatcher(
        tmp_path,
        object(),
        "gpt-mock",
        corpus_path_ref_index=idx,
        allow_corpus_writes=True,
    )
    out = dispatch(
        "assemble_recap_draft",
        json.dumps(
            {
                "raw_notes_path": rel,
                "target_session": 20,
                "campaign_id": "longmont-c2",
            }
        ),
    )
    assert "Error" not in out
    data = json.loads(out)
    assert "recap_body" in data
    assert data.get("duplicates_removed") == 1
    assert "longmont-c2" in data["recap_body"]
    assert "Session 20 Recap" in data["recap_body"]


def test_build_recap_write_payload_returns_recap_write_shape(tmp_path: Path) -> None:
    hub = tmp_path / "Longmont Campaign" / "Campaign 2"
    recaps = hub / "Session Recaps"
    prep = hub / "Session Prep"
    staging = hub / "_ingest_staging"
    recaps.mkdir(parents=True)
    prep.mkdir(parents=True)
    staging.mkdir(parents=True)
    for n in (17, 18, 19):
        (recaps / f"Session {n} - Recap.md").write_text(
            f"---\nsession: {n}\ncampaign_id: longmont-c2\ntitle: Session {n} - Recap\n---\n\nbody\n",
            encoding="utf-8",
        )
    (prep / "session_20_outline.md").write_text(
        "---\nsession: 20\ncampaign_id: longmont-c2\ntitle: Session 20 prep\n---\nprep body\n",
        encoding="utf-8",
    )
    rel = "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    (staging / "session_20_raw_notes.md").write_text(
        "Session 20 Recap\n\nHello world.\n\nHello world.\n",
        encoding="utf-8",
    )
    idx = build_corpus_path_ref_index(tmp_path)
    dispatch = make_tool_dispatcher(
        tmp_path,
        object(),
        "gpt-mock",
        corpus_path_ref_index=idx,
        allow_corpus_writes=True,
    )
    out = dispatch(
        "build_recap_write_payload",
        json.dumps(
            {
                "raw_notes_path": rel,
                "target_session": 20,
                "campaign_id": "longmont-c2",
            }
        ),
    )
    assert "Error" not in out
    data = json.loads(out)
    assert data["schema_version"] == "recap_write_v1"
    assert data["recap_preview"]["confirm_token"] == ""
    assert data["recap_preview"]["mode"] == "create"
    assert "Session Recaps/Session 20 - Recap.md" in data["recap_preview"]["path"]
    assert data["prep_pointer_proposal"] is not None
    assert data["npc_audit"]["timeline_append_candidates"] == []


def test_read_corpus_via_stable_ref_token(tmp_path: Path) -> None:
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "f.md").write_text("ok\n", encoding="utf-8")
    idx = build_corpus_path_ref_index(tmp_path)
    ref = next(r for r, rel in idx.items() if rel.endswith("d/f.md"))
    dispatch = make_tool_dispatcher(tmp_path, object(), "gpt-mock", corpus_path_ref_index=idx)
    out = dispatch("read_corpus_file", json.dumps({"path": f"c:{ref}"}))
    assert "ok" in out


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


def test_merge_planning_turn_details_chain_requires_non_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        merge_planning_turn_details_chain([])


def test_merge_planning_turn_details_chain_concatenates_traces() -> None:
    a = PlanningTurnDetail(
        final_text="first",
        last_response_id="id1",
        tool_trace=[{"tool": "read_corpus_file", "arguments": {"path": "a.md"}}],
        telemetry_cost={"planner_estimated_cost_usd": 0.01, "statblock_tool_estimated_cost_usd": 0.0},
    )
    b = PlanningTurnDetail(
        final_text="second",
        last_response_id="id2",
        tool_trace=[{"tool": "append_timeline_row", "arguments": {"npc_slug": "x"}}],
        telemetry_cost={"planner_estimated_cost_usd": 0.02, "statblock_tool_estimated_cost_usd": 0.0},
    )
    m = merge_planning_turn_details_chain([a, b])
    assert m.final_text == "second"
    assert m.last_response_id == "id2"
    assert len(m.tool_trace) == 2
    assert float(m.telemetry_cost["planner_estimated_cost_usd"]) == pytest.approx(0.03)
