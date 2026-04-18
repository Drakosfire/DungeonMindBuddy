"""Tests for Scope-B recap-ingest mechanical grader (tool trace + recap JSON payload)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from evals.session_recap_ingest_vertical_slice.scope_b_grader import (
    collect_scope_b_recap_ingest_violations,
)
from src.agent.planner import PlanningTurnDetail
from src.agent.recap_context import resolve_recap_context
from tests.test_recap_write_output_schema import _valid_payload


def _write_recap(
    corpus_root: Path,
    *,
    campaign_hub: str,
    filename: str,
    session: int,
    campaign_id: str,
) -> None:
    title = f"Session {session} - Recap"
    body = textwrap.dedent(
        f"""\
        ---
        title: "{title}"
        document_class: play
        canon_layer: campaign
        campaign_id: {campaign_id}
        temporal_scope: session_specific
        session: {session}
        origin_session: {session}
        last_updated_session: {session}
        source_class: observed_session_recap
        ---
        # {title}

        Body of session {session}.
        """
    )
    recaps_dir = corpus_root / campaign_hub / "Session Recaps"
    recaps_dir.mkdir(parents=True, exist_ok=True)
    (recaps_dir / filename).write_text(body, encoding="utf-8")


def _seed_campaign_2(root: Path) -> None:
    hub = "Longmont Campaign/Campaign 2"
    for n in (15, 16, 17, 18, 19):
        _write_recap(
            root,
            campaign_hub=hub,
            filename=f"Session {n} - Recap.md",
            session=n,
            campaign_id="longmont-c2",
        )


def _write_prep(root: Path, *, campaign_hub: str, filename: str) -> None:
    prep_dir = root / campaign_hub / "Session Prep"
    prep_dir.mkdir(parents=True, exist_ok=True)
    (prep_dir / filename).write_text("prep", encoding="utf-8")


def _scenario() -> dict:
    return {
        "schema": "session_recap_ingest_scope_b_v1",
        "scenario_id": "session_recap_ingest_session_20",
        "ingest_raw_notes_relpath": (
            "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
        ),
    }


def _final_text_with_recap_payload() -> str:
    payload = _valid_payload()
    msg = (
        "Summary for GM.\n\n```json\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n```\n"
    )
    return json.dumps(
        {"user_intent": "status_or_recap_request", "message": msg, "unsure_queue": None}
    )


def test_scope_b_grader_passes_with_valid_trace(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_ref.md",
    )
    ctx = resolve_recap_context(tmp_path)
    ing = "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    (tmp_path / ing).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ing).write_text("Notes.\n", encoding="utf-8")

    trace: list[dict] = [{"tool": "get_recap_context", "arguments": {}}]
    for e in ctx.recent_recaps:
        trace.append({"tool": "read_corpus_file", "arguments": {"path": e.path}})
    assert ctx.prep_doc_path
    trace.append({"tool": "read_corpus_file", "arguments": {"path": ctx.prep_doc_path}})
    trace.append(
        {
            "tool": "assemble_recap_draft",
            "arguments": {
                "raw_notes_path": ing,
                "target_session": 20,
                "campaign_id": "longmont-c2",
            },
        }
    )

    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_payload(),
        last_response_id="r1",
        tool_trace=trace,
    )
    assert collect_scope_b_recap_ingest_violations(_scenario(), detail, tmp_path) == {}


def test_scope_b_grader_rejects_read_outside_allowlist(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_ref.md",
    )
    ctx = resolve_recap_context(tmp_path)
    ing = "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    (tmp_path / ing).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ing).write_text("Notes.\n", encoding="utf-8")

    trace: list[dict] = [{"tool": "get_recap_context", "arguments": {}}]
    for e in ctx.recent_recaps:
        trace.append({"tool": "read_corpus_file", "arguments": {"path": e.path}})
    assert ctx.prep_doc_path
    trace.append({"tool": "read_corpus_file", "arguments": {"path": ctx.prep_doc_path}})
    bad = "Longmont Campaign/Campaign 2/Session Recaps/Session 15 - Recap.md"
    trace.append({"tool": "read_corpus_file", "arguments": {"path": bad}})
    trace.append(
        {
            "tool": "assemble_recap_draft",
            "arguments": {
                "raw_notes_path": ing,
                "target_session": 20,
                "campaign_id": "longmont-c2",
            },
        }
    )

    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_payload(),
        last_response_id="r1",
        tool_trace=trace,
    )
    v = collect_scope_b_recap_ingest_violations(_scenario(), detail, tmp_path)
    assert "scope_b" in v
    assert any("not in recent_recaps" in msg for msg in v["scope_b"])


def test_scope_b_grader_requires_unpinned_get_recap_context(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_ref.md",
    )
    ctx = resolve_recap_context(tmp_path)
    ing = "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    (tmp_path / ing).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ing).write_text("Notes.\n", encoding="utf-8")

    trace: list[dict] = [
        {
            "tool": "get_recap_context",
            "arguments": {"campaign_id": "longmont-c2"},
        }
    ]
    for e in ctx.recent_recaps:
        trace.append({"tool": "read_corpus_file", "arguments": {"path": e.path}})
    trace.append(
        {
            "tool": "assemble_recap_draft",
            "arguments": {
                "raw_notes_path": ing,
                "target_session": 20,
                "campaign_id": "longmont-c2",
            },
        }
    )

    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_payload(),
        last_response_id="r1",
        tool_trace=trace,
    )
    v = collect_scope_b_recap_ingest_violations(_scenario(), detail, tmp_path)
    assert any("no arguments" in msg for msg in v.get("scope_b", []))
