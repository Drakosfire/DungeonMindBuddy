"""Tests for the Scope-B recap-ingest run report writer (single + multi-run)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from evals.lysandra_vertical_slice.step1_planner_trace import PlannerStep1Run
from evals.planner_slice.live_eval import LiveEvalResult
from evals.session_recap_ingest_vertical_slice.recap_ingest_run_report import (
    REPORT_SCHEMA_VERSION,
    SUMMARY_SCHEMA_VERSION,
    capture_and_write_recap_ingest_report,
    write_recap_ingest_multi_summary,
)
from src.agent.planner import PlanningTurnDetail


def _detail_with_payload(recap_write: dict | None, *, last_response_id: str = "resp_1") -> PlanningTurnDetail:
    envelope = {
        "user_intent": "status_or_recap_request",
        "message": "Drafted recap.",
        "unsure_queue": None,
    }
    if recap_write is not None:
        envelope["recap_write"] = recap_write
    return PlanningTurnDetail(
        final_text=json.dumps(envelope, ensure_ascii=False),
        last_response_id=last_response_id,
        tool_trace=[
            {"tool": "get_recap_context", "arguments": {}},
            {"tool": "read_corpus_file", "arguments": {"path": "x.md"}},
            {"tool": "assemble_recap_draft", "arguments": {}},
            {"tool": "write_corpus_file", "arguments": {}},
        ],
        steps=[],
        hit_tool_round_limit=False,
        telemetry_cost={
            "scenario_estimated_cost_usd": 0.041,
            "planner_estimated_cost_usd": 0.040,
        },
    )


def _make_run(
    *,
    sid: str = "session_recap_ingest_session_20",
    passed: bool = True,
    tool_ok: bool | None = True,
    payload_ok: bool | None = True,
    recap_write: dict | None = None,
    violations: dict[str, list[str]] | None = None,
) -> PlannerStep1Run:
    detail = _detail_with_payload(recap_write)
    result = LiveEvalResult(
        scenario_id=sid,
        passed=passed,
        violations=violations or {},
        estimated_cost_usd=0.041,
        corpus_fingerprint="fp123",
        tool_trace_gates_passed=tool_ok,
        payload_gates_passed=payload_ok,
    )
    return PlannerStep1Run(
        detail=detail,
        result=result,
        instructions="instr",
        user_line="user",
        corpus_fingerprint="fp123",
        scenario_key=sid,
    )


def _valid_recap_write_payload() -> dict:
    return {
        "schema_version": "recap_write_v1",
        "recap_preview": {
            "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "mode": "create",
            "confirm_token": "abc",
        },
        "duplicate_paragraphs": [],
        "npc_audit": {
            "timeline_append_candidates": [],
            "new_hub_proposals": [],
            "dismissed": [],
        },
        "plot_artifacts": [],
        "prep_pointer_proposal": None,
        "notes_for_gm": "",
    }


def _stub_print(**_kwargs) -> None:
    print("REVIEW BLOCK")
    print("scenario_id:      x")
    print("gates_passed:     True")


def test_single_run_writes_md_json_and_legacy(tmp_path: Path) -> None:
    run = _make_run(recap_write=_valid_recap_write_payload())
    when = datetime(2026, 4, 18, 13, 30, 0, tzinfo=timezone.utc)
    paths, summary = capture_and_write_recap_ingest_report(
        print_callable=_stub_print,
        print_kwargs={},
        run=run,
        corpus_dir=tmp_path,
        model_id="gpt-5.4-mini",
        runs_root=tmp_path / "runs",
        slice_dir=tmp_path,
        utc=when,
        echo_to_stdout=False,
    )
    assert paths.primary_md.exists()
    assert paths.sidecar_json.exists()
    assert paths.legacy_md.exists()
    assert paths.legacy_json.exists()

    md = paths.primary_md.read_text(encoding="utf-8")
    assert REPORT_SCHEMA_VERSION in md
    assert "REVIEW BLOCK" in md
    assert "## Sidecar JSON" in md

    payload = json.loads(paths.sidecar_json.read_text(encoding="utf-8"))
    assert payload["schema"] == REPORT_SCHEMA_VERSION
    assert payload["scenario_id"] == "session_recap_ingest_session_20"
    assert payload["gates_passed"] is True
    assert payload["tool_trace_gates_passed"] is True
    assert payload["payload_gates_passed"] is True
    assert payload["scenario_estimated_cost_usd"] == 0.041
    assert payload["recap_write_payload"] is not None
    assert payload["recap_write_payload_sha256_16"]
    assert payload["tool_trace_tools"] == [
        "get_recap_context",
        "read_corpus_file",
        "assemble_recap_draft",
        "write_corpus_file",
    ]
    assert payload["violation_counts"] == {}
    assert summary.gates_passed is True
    assert summary.recap_write_sha256_16 == payload["recap_write_payload_sha256_16"]


def test_failing_run_records_violation_counts_and_fail_filename(tmp_path: Path) -> None:
    run = _make_run(
        passed=False,
        tool_ok=False,
        payload_ok=True,
        recap_write=_valid_recap_write_payload(),
        violations={"scope_b_tool": ["off-allowlist read"], "scope_b": ["off-allowlist read"]},
    )
    when = datetime(2026, 4, 18, 14, 0, 0, tzinfo=timezone.utc)
    paths, summary = capture_and_write_recap_ingest_report(
        print_callable=_stub_print,
        print_kwargs={},
        run=run,
        corpus_dir=tmp_path,
        model_id="gpt-5.4-mini",
        runs_root=tmp_path / "runs",
        slice_dir=tmp_path,
        utc=when,
        echo_to_stdout=False,
    )
    assert "FAIL" in paths.primary_md.name
    payload = json.loads(paths.sidecar_json.read_text(encoding="utf-8"))
    assert payload["gates_passed"] is False
    assert payload["violation_counts"]["scope_b_tool"] == 1
    assert payload["violation_counts"]["scope_b"] == 1
    assert summary.violation_counts["scope_b_tool"] == 1


def test_multi_summary_aggregates_pass_rates_and_payload_diversity(tmp_path: Path) -> None:
    when = datetime(2026, 4, 18, 14, 30, 0, tzinfo=timezone.utc)
    summaries = []
    for i, (passed, tool_ok, recap) in enumerate(
        [
            (True, True, _valid_recap_write_payload()),
            (True, True, _valid_recap_write_payload()),
            (False, False, _valid_recap_write_payload()),
        ]
    ):
        rw = dict(recap)
        rw["notes_for_gm"] = f"variant {i}"
        run = _make_run(
            passed=passed,
            tool_ok=tool_ok,
            payload_ok=True,
            recap_write=rw,
            violations=({"scope_b_tool": ["bad"]} if not passed else {}),
        )
        _paths, summary = capture_and_write_recap_ingest_report(
            print_callable=_stub_print,
            print_kwargs={},
            run=run,
            corpus_dir=tmp_path,
            model_id="gpt-5.4-mini",
            runs_root=tmp_path / "runs",
            slice_dir=tmp_path,
            utc=when,
            run_index=i,
            cohort_size=3,
            echo_to_stdout=False,
        )
        summaries.append(summary)

    md_path, json_path = write_recap_ingest_multi_summary(
        summaries,
        model_id="gpt-5.4-mini",
        scenario_id="session_recap_ingest_session_20",
        runs_root=tmp_path / "runs",
        slice_dir=tmp_path,
        utc=when,
    )
    assert md_path.exists() and json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["schema"] == SUMMARY_SCHEMA_VERSION
    assert data["aggregate"]["gates_pass_rate"] == "2/3"
    assert data["aggregate"]["tool_trace_gates_pass_rate"] == "2/3"
    assert data["aggregate"]["payload_gates_pass_rate"] == "3/3"
    assert len(data["aggregate"]["distinct_recap_write_sha256_16"]) == 3
    assert data["aggregate"]["violation_counts_total"]["scope_b_tool"] == 1
    assert len(data["results"]) == 3

    md = md_path.read_text(encoding="utf-8")
    assert "Scope-B recap-ingest cohort summary (N=3)" in md
    assert "gates pass rate**: 2/3" in md
    assert "| run | gates | tool_trace | payload" in md


def test_no_recap_write_field_records_null(tmp_path: Path) -> None:
    run = _make_run(recap_write=None)
    paths, summary = capture_and_write_recap_ingest_report(
        print_callable=_stub_print,
        print_kwargs={},
        run=run,
        corpus_dir=tmp_path,
        model_id="gpt-5.4-mini",
        runs_root=tmp_path / "runs",
        slice_dir=tmp_path,
        utc=datetime(2026, 4, 18, 15, 0, 0, tzinfo=timezone.utc),
        echo_to_stdout=False,
    )
    payload = json.loads(paths.sidecar_json.read_text(encoding="utf-8"))
    assert payload["recap_write_payload"] is None
    assert payload["recap_write_payload_sha256_16"] is None
    assert summary.recap_write_sha256_16 is None
