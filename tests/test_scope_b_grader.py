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


def _recap_write_guard_blocked_excerpt(path: str) -> str:
    return (
        f"Error: recap-write skill blocked read_corpus_file for path {path!r}: not in "
        f"recent_recaps ∪ prep_doc_path. Use only paths returned by `get_recap_context`."
    )


def test_guard_caught_staging_read_with_recovery_is_soft(tmp_path: Path) -> None:
    """Dispatch guard blocks direct staging read; model recovers via ``assemble_recap_draft``."""
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
            "tool": "read_corpus_file",
            "arguments": {"path": ing},
            "output_excerpt": _recap_write_guard_blocked_excerpt(ing),
        }
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

    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_payload(),
        last_response_id="r1",
        tool_trace=trace,
    )
    v = collect_scope_b_recap_ingest_violations(_scenario(), detail, tmp_path)
    assert v == {}, v
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario(), detail, tmp_path, recap_context_snapshot=ctx
    )
    soft = extras.get("read_allowlist_soft_observations", [])
    assert len(soft) == 1, soft
    assert "read_allowlist_soft" in soft[0]
    assert ing in soft[0]


def test_guard_missed_staging_read_is_hard(tmp_path: Path) -> None:
    """Unguarded read returns real bytes — hard allowlist violation (possible leak)."""
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
            "tool": "read_corpus_file",
            "arguments": {"path": ing},
            "output_excerpt": json.dumps(
                {"path": ing, "content": "# Session 20 raw\n\nGM notes here.\n"}
            ),
        }
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

    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_payload(),
        last_response_id="r1",
        tool_trace=trace,
    )
    v = collect_scope_b_recap_ingest_violations(_scenario(), detail, tmp_path)
    assert "scope_b_tool" in v
    assert any("not in allowlist" in msg for msg in v["scope_b_tool"])
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario(), detail, tmp_path, recap_context_snapshot=ctx
    )
    assert extras.get("read_allowlist_soft_observations") == []


def test_guard_caught_staging_read_without_recovery_is_hard(tmp_path: Path) -> None:
    """Blocked read with no later ``assemble_recap_draft`` — model did not recover."""
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
            "tool": "read_corpus_file",
            "arguments": {"path": ing},
            "output_excerpt": _recap_write_guard_blocked_excerpt(ing),
        }
    )

    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_payload(),
        last_response_id="r1",
        tool_trace=trace,
    )
    v = collect_scope_b_recap_ingest_violations(_scenario(), detail, tmp_path)
    msgs = v.get("scope_b_tool", [])
    assert any("did not recover" in m for m in msgs), msgs
    assert any("assemble_recap_draft must be called exactly once" in m for m in msgs)
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario(), detail, tmp_path, recap_context_snapshot=ctx
    )
    assert extras.get("read_allowlist_soft_observations") == []


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
            "output_excerpt": json.dumps(_committed_response()),
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


def _write_call_with_response(
    *, dry_run: bool | None, response: str | dict | None
) -> dict:
    """Like :func:`_write_call` but also stamps the trace row's ``output_excerpt``.

    Used by the BACKLOG §1.0 commit-success gate tests, which need to assert
    behavior based on what the *server* returned (success vs. ``ok=false``
    vs. plain ``Error: ...`` rejection vs. truncated/unparseable). ``dict``
    responses are JSON-serialized; ``str`` is passed through (covers the
    ``Error: ...`` and truncated-JSON cases); ``None`` omits the field.
    """
    row = _write_call(dry_run=dry_run)
    if response is None:
        return row
    if isinstance(response, dict):
        excerpt = json.dumps(response, ensure_ascii=False)
    else:
        excerpt = response
    row["output_excerpt"] = excerpt
    row["output_chars"] = len(excerpt)
    return row


def _committed_response(path_rel: str = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md") -> dict:
    return {
        "ok": True,
        "phase": "committed",
        "path": path_rel,
        "mode": "create",
        "bytes_written": 1234,
        "new_corpus_fingerprint": "deadbeef" * 4,
        "fingerprint_reminder": "Corpus changed; new fingerprint = ...",
    }


def _stale_token_response() -> dict:
    return {
        "ok": False,
        "error": (
            "stale confirm_token (file or content changed since dry_run). "
            "Re-run with dry_run=true to get a fresh token."
        ),
    }


def test_two_phase_commit_passes_with_preview_then_commit(tmp_path: Path) -> None:
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call(dry_run=True),
            _write_call_with_response(dry_run=False, response=_committed_response()),
        ],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    assert v == {}


def test_two_phase_commit_passes_when_preview_uses_default_dry_run(tmp_path: Path) -> None:
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call(dry_run=None),
            _write_call_with_response(dry_run=False, response=_committed_response()),
        ],
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


def test_report_extras_matches_violation_knobs_commit_only(tmp_path: Path) -> None:
    """``commit_required`` only implies ``preview_required`` in extras too (Tier-1 parity)."""
    sc = _scenario()
    sc["expected_tool_trace"] = {"commit_required": True}
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call(dry_run=True),
            _write_call_with_response(dry_run=False, response=_committed_response()),
        ],
    )
    extras = collect_scope_b_recap_ingest_report_extras(sc, detail)
    assert extras["preview_required"] is True
    assert extras["commit_required"] is True
    v = collect_scope_b_recap_ingest_violations(sc, detail, tmp_path)
    assert not v.get("scope_b_tool"), v


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


# ---------------------------------------------------------------------------
# Mechanical-payload comparison (BACKLOG §1.5 / option b) — soft signal.
#
# Cohort runner uses these to answer: "does invoking ``build_recap_write_payload``
# produce a mechanically-identical payload, or does the model edit it?" The
# signal is intentionally soft (``mechanical_fields_match`` ∈ {True, False, None})
# so we can measure adoption before deciding whether to convert it to a hard gate.
# ---------------------------------------------------------------------------


def _write_raw_notes(corpus_root: Path) -> None:
    rel = "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    p = corpus_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# Session 20 raw notes\n\nFirst paragraph.\n\nSecond paragraph.\n",
        encoding="utf-8",
    )


def _make_mechanical_aligned_payload(corpus_root: Path) -> dict:
    """Build a ``recap_write`` whose mechanical fields match the helper's output."""
    from src.agent.recap_ingest_helpers import assemble_recap
    from src.agent.recap_write_mechanical_payload import (
        build_recap_write_payload_from_ingest,
    )

    ctx = resolve_recap_context(corpus_root)
    raw = (
        corpus_root
        / "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    ).read_text(encoding="utf-8")
    _full, report = assemble_recap(
        raw_notes=raw,
        session=ctx.target_session,
        campaign_id=ctx.campaign_id,
        remove_duplicates=True,
    )
    expected = build_recap_write_payload_from_ingest(ctx, report)
    payload = _valid_payload()
    payload["recap_preview"]["path"] = expected["recap_preview"]["path"]
    payload["recap_preview"]["mode"] = expected["recap_preview"]["mode"]
    payload["duplicate_paragraphs"] = expected["duplicate_paragraphs"]
    payload["prep_pointer_proposal"] = expected["prep_pointer_proposal"]
    return payload


def _final_text_with_payload(payload: dict) -> str:
    return json.dumps(
        {
            "user_intent": "status_or_recap_request",
            "message": "ok",
            "unsure_queue": None,
            "recap_write": payload,
        }
    )


def test_extras_mechanical_match_when_payload_aligns_with_helper(
    tmp_path: Path,
) -> None:
    """Model emits a ``recap_write`` whose mechanical fields equal the helper's output."""
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_ref.md",
    )
    _write_raw_notes(tmp_path)
    snapshot = resolve_recap_context(tmp_path)
    payload = _make_mechanical_aligned_payload(tmp_path)
    detail = PlanningTurnDetail(
        final_text=_final_text_with_payload(payload),
        last_response_id="r1",
        tool_trace=[
            {"tool": "get_recap_context", "arguments": {}},
            {
                "tool": "build_recap_write_payload",
                "arguments": {
                    "raw_notes_path": (
                        "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
                    ),
                    "target_session": snapshot.target_session,
                    "campaign_id": snapshot.campaign_id,
                },
            },
        ],
    )
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario(), detail, tmp_path, recap_context_snapshot=snapshot
    )
    assert extras["build_recap_write_payload_called"] is True
    assert extras["mechanical_fields_match"] is True
    assert extras["mechanical_fields_diff"] == {}


def test_extras_mechanical_mismatch_records_diff(tmp_path: Path) -> None:
    """A wrong ``recap_preview.path`` surfaces as a diff entry; match is False."""
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_ref.md",
    )
    _write_raw_notes(tmp_path)
    snapshot = resolve_recap_context(tmp_path)
    payload = _make_mechanical_aligned_payload(tmp_path)
    payload["recap_preview"]["path"] = "WRONG/PATH/Session 20 - Recap.md"
    detail = PlanningTurnDetail(
        final_text=_final_text_with_payload(payload),
        last_response_id="r1",
        tool_trace=[],
    )
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario(), detail, tmp_path, recap_context_snapshot=snapshot
    )
    assert extras["build_recap_write_payload_called"] is False
    assert extras["mechanical_fields_match"] is False
    diffs = extras["mechanical_fields_diff"]
    assert "recap_preview" in diffs
    assert diffs["recap_preview"]["actual"]["path"] == "WRONG/PATH/Session 20 - Recap.md"


def test_extras_mechanical_not_applicable_without_corpus_path(tmp_path: Path) -> None:
    """Back-compat call site (no corpus_path) → mechanical signal is None, key omitted."""
    sc = _scenario()
    sc["expected_tool_trace"] = {"preview_required": False, "commit_required": False}
    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_field(),
        last_response_id="r1",
        tool_trace=[],
    )
    extras = collect_scope_b_recap_ingest_report_extras(sc, detail)
    assert extras["mechanical_fields_match"] is None
    assert "mechanical_fields_diff" not in extras
    assert extras["build_recap_write_payload_called"] is False


def test_extras_mechanical_not_applicable_when_recap_write_unparseable(
    tmp_path: Path,
) -> None:
    """Corpus + snapshot present, but model emitted junk → not applicable, no false signal."""
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_ref.md",
    )
    _write_raw_notes(tmp_path)
    snapshot = resolve_recap_context(tmp_path)
    detail = PlanningTurnDetail(
        final_text="not json at all",
        last_response_id="r1",
        tool_trace=[],
    )
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario(), detail, tmp_path, recap_context_snapshot=snapshot
    )
    assert extras["mechanical_fields_match"] is None
    assert "mechanical_fields_diff" not in extras


def test_extras_mechanical_not_applicable_when_raw_notes_missing(
    tmp_path: Path,
) -> None:
    """No raw notes on disk → helper returns None → mechanical signal is None."""
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_ref.md",
    )
    snapshot = resolve_recap_context(tmp_path)
    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_field(),
        last_response_id="r1",
        tool_trace=[],
    )
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario(), detail, tmp_path, recap_context_snapshot=snapshot
    )
    assert extras["mechanical_fields_match"] is None


def test_extras_records_build_recap_write_payload_called_flag(tmp_path: Path) -> None:
    """The flag is True iff the trace contains at least one ``build_recap_write_payload`` row."""
    sc = _scenario()
    sc["expected_tool_trace"] = {"preview_required": False, "commit_required": False}
    detail_no_call = PlanningTurnDetail(
        final_text=_final_text_with_recap_field(),
        last_response_id="r1",
        tool_trace=[{"tool": "get_recap_context", "arguments": {}}],
    )
    extras_no = collect_scope_b_recap_ingest_report_extras(sc, detail_no_call)
    assert extras_no["build_recap_write_payload_called"] is False

    detail_with_call = PlanningTurnDetail(
        final_text=_final_text_with_recap_field(),
        last_response_id="r1",
        tool_trace=[
            {"tool": "get_recap_context", "arguments": {}},
            {
                "tool": "build_recap_write_payload",
                "arguments": {
                    "raw_notes_path": "x",
                    "target_session": 20,
                    "campaign_id": "longmont-c2",
                },
            },
        ],
    )
    extras_yes = collect_scope_b_recap_ingest_report_extras(sc, detail_with_call)
    assert extras_yes["build_recap_write_payload_called"] is True


# ---------------------------------------------------------------------------
# Commit-success gate (BACKLOG §1.0 fix).
#
# Until §1.0 was closed, ``commit_required`` only checked call shape. A run
# could attempt ``write_corpus_file(dry_run=false)``, the server could refuse
# (stale ``confirm_token``, allowlist rejection, disabled writes), and the
# grader would still report ``gates_passed=true`` because a ``dry_run=false``
# row existed. These tests pin the post-fix behavior: the gate now consults
# the server's response (``output_excerpt``) on the last commit attempt.
# ---------------------------------------------------------------------------


def test_commit_required_passes_when_server_returns_committed(tmp_path: Path) -> None:
    """Happy path: preview + commit, server returns ``ok=true, phase='committed'``."""
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call_with_response(dry_run=True, response=None),
            _write_call_with_response(
                dry_run=False, response=_committed_response()
            ),
        ],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    assert v == {}, v
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario_two_phase(), detail, tmp_path
    )
    outcome = extras["write_corpus_file_last_commit_outcome"]
    assert outcome == {
        "succeeded": True,
        "phase": "committed",
        "error": None,
    }


def test_commit_required_fails_when_server_returns_stale_token(
    tmp_path: Path,
) -> None:
    """The §1.0 regression case: model regenerated content, server refused.

    Pre-fix: this would have passed because there's a preview row and a commit
    row. Post-fix: the commit row's ``output_excerpt`` carries ``ok=false`` and
    a ``stale confirm_token`` error, which we now propagate to a hard
    violation."""
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call_with_response(dry_run=True, response=None),
            _write_call_with_response(
                dry_run=False, response=_stale_token_response()
            ),
        ],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    msgs = v.get("scope_b_tool", [])
    assert any("did not succeed" in m for m in msgs), msgs
    assert any("stale confirm_token" in m for m in msgs), msgs
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario_two_phase(), detail, tmp_path
    )
    outcome = extras["write_corpus_file_last_commit_outcome"]
    assert outcome["succeeded"] is False
    assert "stale confirm_token" in (outcome["error"] or "")


def test_commit_required_fails_on_plain_error_string_from_skill_guard(
    tmp_path: Path,
) -> None:
    """Skill-guard / disabled-writes responses are plain ``Error: ...`` strings.

    They aren't JSON, but they're still definitive proof the corpus wasn't
    written. The gate must treat them as commit failures, not as ambiguous
    'unknown' responses."""
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call_with_response(dry_run=True, response=None),
            _write_call_with_response(
                dry_run=False,
                response="Error: write_corpus_file is disabled (planner started "
                "with allow_corpus_writes=False).",
            ),
        ],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    msgs = v.get("scope_b_tool", [])
    assert any("did not succeed" in m for m in msgs), msgs
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario_two_phase(), detail, tmp_path
    )
    outcome = extras["write_corpus_file_last_commit_outcome"]
    assert outcome["succeeded"] is False
    assert "disabled" in (outcome["error"] or "")


def test_commit_required_unknown_response_is_now_hard_violation(tmp_path: Path) -> None:
    """After the §1.0 fix: truncated / non-JSON responses on the last commit attempt
    are a hard violation when ``commit_required=True`` because the protocol's success
    cannot be verified. The previous behavior (soft observation, no gate failure) was
    replaced so a run cannot report PASS when the write's outcome is unknown."""
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call_with_response(dry_run=True, response=None),
            _write_call_with_response(
                dry_run=False,
                response='{"ok": true, "phase": "committed", "diff": "--- a/foo',
            ),
        ],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    msgs = v.get("scope_b_tool", [])
    assert any("commit_outcome=unknown" in m for m in msgs), msgs
    assert any("cannot be verified" in m for m in msgs), msgs
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario_two_phase(), detail, tmp_path
    )
    outcome = extras["write_corpus_file_last_commit_outcome"]
    assert outcome["succeeded"] is None


def test_commit_required_passes_when_last_of_multiple_commits_succeeds(
    tmp_path: Path,
) -> None:
    """Stale-token retry is allowed: only the *last* commit attempt's outcome
    decides the gate. preview → failed-commit → preview → succeeded-commit
    means the corpus did get written, so the run should pass."""
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call_with_response(dry_run=True, response=None),
            _write_call_with_response(
                dry_run=False, response=_stale_token_response()
            ),
            _write_call_with_response(dry_run=True, response=None),
            _write_call_with_response(
                dry_run=False, response=_committed_response()
            ),
        ],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    assert v == {}, v
    extras = collect_scope_b_recap_ingest_report_extras(
        _scenario_two_phase(), detail, tmp_path
    )
    outcome = extras["write_corpus_file_last_commit_outcome"]
    assert outcome["succeeded"] is True
    assert outcome["phase"] == "committed"


def test_extras_last_commit_outcome_is_none_when_no_commit_attempted(
    tmp_path: Path,
) -> None:
    """Preview-only contracts shouldn't emit a phantom outcome dict."""
    sc = _scenario()
    sc["expected_tool_trace"] = {"preview_required": True, "commit_required": False}
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [_write_call_with_response(dry_run=True, response=None)],
    )
    extras = collect_scope_b_recap_ingest_report_extras(sc, detail, tmp_path)
    assert extras["write_corpus_file_last_commit_outcome"] is None


def test_unparseable_last_commit_response_with_commit_required_is_hard_violation(
    tmp_path: Path,
) -> None:
    """When ``commit_required=True``, an unparseable last-commit response is a hard
    violation: the grader cannot verify the protocol succeeded, so the run must fail.
    Uses a literal non-JSON string that is neither ``ok=true`` nor a plain
    ``Error: ...`` response to exercise the ``succeeded=None`` path."""
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call_with_response(dry_run=True, response=None),
            _write_call_with_response(dry_run=False, response="truncated\u2026"),
        ],
    )
    v = collect_scope_b_recap_ingest_violations(_scenario_two_phase(), detail, tmp_path)
    msgs = v.get("scope_b_tool", [])
    assert any("commit_outcome=unknown" in m for m in msgs), (
        f"Expected a hard violation mentioning commit_outcome=unknown; got {msgs!r}"
    )
    assert any("cannot be verified" in m for m in msgs), (
        f"Expected the violation to explain the run is failing because success cannot "
        f"be verified; got {msgs!r}"
    )


def test_unparseable_last_commit_response_without_commit_required_is_soft_only(
    tmp_path: Path,
) -> None:
    """When ``commit_required=False`` (HITL/preview-only contract), an unparseable
    response on a voluntarily-issued commit must not produce a hard violation.
    The model isn't required to commit; if it does and the response is garbled,
    that is informational, not a gate failure."""
    sc = _scenario()
    sc["expected_tool_trace"] = {"preview_required": True, "commit_required": False}
    detail = _build_passing_trace_with_writes(
        tmp_path,
        [
            _write_call_with_response(dry_run=True, response=None),
            _write_call_with_response(dry_run=False, response="<not json>"),
        ],
    )
    v = collect_scope_b_recap_ingest_violations(sc, detail, tmp_path)
    assert not v.get("scope_b_tool"), (
        f"Expected no hard violations for commit_required=False + unparseable commit; "
        f"got {v!r}"
    )
