"""Tests for Scope-B recap-ingest mechanical grader (tool trace + recap JSON payload)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from evals.session_recap_ingest_vertical_slice.scope_b_grader import (
    collect_scope_b_recap_ingest_report_extras,
    collect_scope_b_recap_ingest_violations,
    summarize_write_corpus_phases,
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
    """Legacy shape: payload fenced inside ``message`` (universal envelope)."""
    payload = _valid_payload()
    msg = (
        "Summary for GM.\n\n```json\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n```\n"
    )
    return json.dumps(
        {"user_intent": "status_or_recap_request", "message": msg, "unsure_queue": None}
    )


def _final_text_with_recap_field() -> str:
    """New shape: payload as a dedicated top-level ``recap_write`` field (per-skill schema)."""
    return json.dumps(
        {
            "user_intent": "status_or_recap_request",
            "message": "Recap drafted; preview ready for review.",
            "unsure_queue": None,
            "recap_write": _valid_payload(),
        }
    )


def test_scope_b_grader_accepts_dedicated_recap_write_field(tmp_path: Path) -> None:
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
        final_text=_final_text_with_recap_field(),
        last_response_id="r1",
        tool_trace=trace,
    )
    assert collect_scope_b_recap_ingest_violations(_scenario(), detail, tmp_path) == {}


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
    assert "scope_b_tool" in v
    assert any("not in recent_recaps" in msg for msg in v["scope_b_tool"])
    assert "scope_b" in v


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
    assert any("no arguments" in msg for msg in v.get("scope_b_tool", []))


def test_scope_b_grader_uses_precomputed_snapshot_after_post_commit_corpus_drift(
    tmp_path: Path,
) -> None:
    """Regression: temporal-coupling bug where a turn-1 commit shifts ``max(session)``.

    Reproduces the failure mode observed in the first 2-turn cohort
    (``recap_ingest--…--FAIL--2turn--…--run00{1,2,3}.json`` on 2026-04-18):
    the model legitimately reads sessions 17/18/19 + the session-20 prep doc
    in turn 1, then commits ``Session 20 - Recap.md``. A grader that
    re-resolves ``recap_context`` post-commit sees ``max(session)=20``,
    returns ``target=21``, and falsely flags Session 17 + the session-20 prep
    as off-allowlist (and ``assemble_recap_draft.target_session want 21 got 20``).

    With the precomputed snapshot taken before turn 1, the grader uses the
    same view the model saw and the trace is clean.
    """
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_ref.md",
    )
    pre_turn_ctx = resolve_recap_context(tmp_path)
    assert pre_turn_ctx.target_session == 20
    assert pre_turn_ctx.prep_doc_path is not None

    ing = "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    (tmp_path / ing).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ing).write_text("Notes.\n", encoding="utf-8")

    trace: list[dict] = [{"tool": "get_recap_context", "arguments": {}}]
    for e in pre_turn_ctx.recent_recaps:
        trace.append({"tool": "read_corpus_file", "arguments": {"path": e.path}})
    trace.append(
        {"tool": "read_corpus_file", "arguments": {"path": pre_turn_ctx.prep_doc_path}}
    )
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
    trace.append(
        {
            "tool": "write_corpus_file",
            "arguments": {
                "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
                "mode": "create",
                "dry_run": True,
            },
        }
    )
    trace.append(
        {
            "tool": "write_corpus_file",
            "arguments": {
                "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
                "mode": "create",
                "dry_run": False,
            },
        }
    )

    # Simulate the post-commit corpus state the grader would otherwise see live:
    # writing the Session 20 recap file shifts ``max(session)`` from 19 → 20.
    _write_recap(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="Session 20 - Recap.md",
        session=20,
        campaign_id="longmont-c2",
    )

    scenario = {
        **_scenario(),
        "expected_tool_trace": {"two_phase_commit_required": True},
    }
    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_field(),
        last_response_id="r1",
        tool_trace=trace,
    )

    v_live = collect_scope_b_recap_ingest_violations(scenario, detail, tmp_path)
    assert "scope_b_tool" in v_live, (
        "Without the snapshot the grader must flag the post-commit shifted allowlist"
    )
    msgs = " | ".join(v_live["scope_b_tool"])
    assert "want 21 got 20" in msgs
    assert "Session 17" in msgs
    assert "session_20_ref.md" in msgs

    v_snapshot = collect_scope_b_recap_ingest_violations(
        scenario,
        detail,
        tmp_path,
        precomputed_recap_context=pre_turn_ctx,
    )
    assert v_snapshot == {}, (
        f"With the pre-turn snapshot the trace must pass cleanly; got {v_snapshot!r}"
    )


def _build_passing_trace_with_writes(
    tmp_path: Path, write_calls: list[dict]
) -> PlanningTurnDetail:
    """Helper: trace that passes every Scope-B check except (potentially) two-phase commit."""
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
    trace.extend(write_calls)
    return PlanningTurnDetail(
        final_text=_final_text_with_recap_field(),
        last_response_id="r1",
        tool_trace=trace,
    )


def _scenario_two_phase() -> dict:
    sc = _scenario()
    sc["expected_tool_trace"] = {"two_phase_commit_required": True}
    return sc


def _write_call(*, dry_run: bool | None) -> dict:
    args: dict = {"path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"}
    if dry_run is not None:
        args["dry_run"] = dry_run
    return {"tool": "write_corpus_file", "arguments": args}


def test_two_phase_commit_passes_with_preview_then_commit(tmp_path: Path) -> None:
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=True), _write_call(dry_run=False)],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    assert v == {}


def test_two_phase_commit_passes_when_preview_uses_default_dry_run(tmp_path: Path) -> None:
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=None), _write_call(dry_run=False)],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    assert v == {}


def test_two_phase_commit_fails_with_single_call(tmp_path: Path) -> None:
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=True)],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    assert any(
        "no write_corpus_file commit" in msg for msg in v.get("scope_b_tool", [])
    )


def test_two_phase_commit_fails_with_no_preview(tmp_path: Path) -> None:
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=False), _write_call(dry_run=False)],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    assert any(
        "no write_corpus_file preview" in msg for msg in v.get("scope_b_tool", [])
    )


def test_two_phase_commit_fails_with_no_commit(tmp_path: Path) -> None:
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=True), _write_call(dry_run=True)],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    assert any(
        "no write_corpus_file commit" in msg for msg in v.get("scope_b_tool", [])
    )


def test_two_phase_commit_fails_when_commit_precedes_preview(tmp_path: Path) -> None:
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=False), _write_call(dry_run=True)],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    msgs = v.get("scope_b_tool", [])
    assert any("preview must come first" in m for m in msgs)
    assert any("commit (dry_run=false) must follow" in m for m in msgs)


def test_two_phase_commit_off_when_scenario_does_not_require(tmp_path: Path) -> None:
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=True)],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario(), detail, tmp_path)
    assert v == {}


def test_two_phase_commit_grader_override_via_scope_b_grader_cfg(tmp_path: Path) -> None:
    sc = _scenario()
    sc["expected_tool_trace"] = {"two_phase_commit_required": True}
    sc["scope_b_grader"] = {"two_phase_commit_required": False}
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=True)],
    )
    v = collect_scope_b_recap_ingest_violations(sc, detail, tmp_path)
    assert v == {}


def test_preview_required_only_passes_with_preview_no_commit(tmp_path: Path) -> None:
    """``preview_required: true`` + ``commit_required: false`` (HITL contract):
    one preview call satisfies the hard gate; the missing commit is a soft signal."""
    sc = _scenario()
    sc["expected_tool_trace"] = {
        "preview_required": True,
        "commit_required": False,
    }
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=True)],
    )
    v = collect_scope_b_recap_ingest_violations(sc, detail, tmp_path)
    assert v == {}, v


def test_preview_required_fails_when_no_write_calls(tmp_path: Path) -> None:
    sc = _scenario()
    sc["expected_tool_trace"] = {"preview_required": True, "commit_required": False}
    detail = _build_passing_trace_with_writes(tmp_path, [])
    v = collect_scope_b_recap_ingest_violations(sc, detail, tmp_path)
    assert any(
        "preview_required" in msg and "never called" in msg
        for msg in v.get("scope_b_tool", [])
    ), v


def test_preview_required_fails_when_only_commits_no_preview(tmp_path: Path) -> None:
    sc = _scenario()
    sc["expected_tool_trace"] = {"preview_required": True, "commit_required": False}
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=False)],
    )
    v = collect_scope_b_recap_ingest_violations(sc, detail, tmp_path)
    assert any(
        "no write_corpus_file preview" in msg for msg in v.get("scope_b_tool", [])
    ), v


def test_commit_required_only_implies_preview_required(tmp_path: Path) -> None:
    """If only ``commit_required`` is set, the grader infers ``preview_required=True``
    so single dry_run=false calls (commit-without-preview) still fail."""
    sc = _scenario()
    sc["expected_tool_trace"] = {"commit_required": True}
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=False)],
    )
    v = collect_scope_b_recap_ingest_violations(sc, detail, tmp_path)
    assert any(
        "no write_corpus_file preview" in msg for msg in v.get("scope_b_tool", [])
    ), v


def test_summarize_write_corpus_phases_shapes() -> None:
    assert summarize_write_corpus_phases([]) == {
        "calls": 0, "previews": 0, "commits": 0, "phases": "none",
    }
    calls = [
        (3, {"dry_run": True}),
        (5, {"dry_run": False}),
    ]
    s = summarize_write_corpus_phases(calls)
    assert s == {"calls": 2, "previews": 1, "commits": 1, "phases": "preview→commit"}


def test_report_extras_records_phases_and_soft_observation_for_preview_only(
    tmp_path: Path,
) -> None:
    """When the model only previews under a preview-only contract, extras records
    the ``preview→preview…`` shape and a soft observation (no hard violation)."""
    sc = _scenario()
    sc["expected_tool_trace"] = {"preview_required": True, "commit_required": False}
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=True), _write_call(dry_run=True)],
    )
    extras = collect_scope_b_recap_ingest_report_extras(sc, detail)
    phases = extras["write_corpus_file_phases"]
    assert phases == {
        "calls": 2, "previews": 2, "commits": 0, "phases": "preview→preview",
    }
    soft = extras["write_corpus_file_soft_observations"]
    assert any("commit_observed=false" in s for s in soft), soft
    assert extras["preview_required"] is True
    assert extras["commit_required"] is False


def test_report_extras_records_clean_commit_no_soft_when_committed(
    tmp_path: Path,
) -> None:
    sc = _scenario()
    sc["expected_tool_trace"] = {"preview_required": True, "commit_required": False}
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call(dry_run=True), _write_call(dry_run=False)],
    )
    extras = collect_scope_b_recap_ingest_report_extras(sc, detail)
    assert extras["write_corpus_file_phases"]["phases"] == "preview→commit"
    assert extras["write_corpus_file_soft_observations"] == []
