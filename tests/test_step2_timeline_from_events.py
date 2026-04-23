"""Offline tests for the Step 2 (events-driven timeline pass) runner.

All tests are purely offline — no network calls, no model invocations.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run import (
    Step2RunSummary,
    _extract_beat_for_slug,
    _run_single_chained_cohort_iteration,
    build_stage_b_per_slug_user_message,
    filter_events_for_slug,
    ordered_stage_b_timeline_targets,
    run_stage_b_events_driven_chain,
    write_step2_multi_summary,
    write_step2_run_report,
)


# ---------------------------------------------------------------------------
# Test 1: per-slug user-message builder formats events correctly with 1+ events
# ---------------------------------------------------------------------------


def test_build_stage_b_per_slug_user_message_includes_events():
    """Message builder embeds the slug events as pretty-printed JSON."""
    events = [
        {
            "event_class": "combat",
            "participants": ["caelynn", "captain_lysandra_ironveil"],
            "location": "wagon camp",
            "outcomes": ["Caelynn administers antidote tea"],
            "time_scope": "scene",
            "certainty": "observed",
        }
    ]
    msg = build_stage_b_per_slug_user_message(
        timeline_rel="Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
        slug="caelynn",
        slug_events=events,
    )
    assert "caelynn" in msg
    assert "player character" in msg
    assert "wagon camp" in msg
    assert "antidote" in msg
    assert "append_timeline_row" in msg
    assert "```json" in msg
    # Verify the JSON in the message parses back to the original events
    json_start = msg.index("```json\n") + len("```json\n")
    json_end = msg.index("\n```", json_start)
    parsed = json.loads(msg[json_start:json_end])
    assert parsed == events


def test_build_stage_b_per_slug_user_message_contains_timeline_rel():
    """Message builder includes the timeline relative path and npc_slug."""
    timeline_rel = "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md"
    slug = "caelynn"
    events = [
        {
            "event_class": "ritual",
            "participants": ["caelynn"],
            "outcomes": ["used bracelet to diffuse aggression"],
            "time_scope": "scene",
            "certainty": "observed",
        }
    ]
    msg = build_stage_b_per_slug_user_message(timeline_rel, slug, events)
    assert f"`{timeline_rel}`" in msg
    assert f"`{slug}`" in msg
    assert "bracelet" in msg


def test_build_stage_b_per_slug_user_message_multiple_events():
    """Message builder correctly includes all events when there are multiple."""
    events = [
        {
            "event_class": "combat",
            "participants": ["karsemine", "ephanna"],
            "outcomes": ["used Zephyr Strike"],
            "time_scope": "scene",
            "certainty": "observed",
        },
        {
            "event_class": "travel",
            "participants": ["karsemine"],
            "outcomes": ["tracked Lysandra"],
            "time_scope": "scene",
            "certainty": "observed",
        },
    ]
    msg = build_stage_b_per_slug_user_message(
        "Longmont Campaign/Campaign 2/PCs/karsemine/timeline.md",
        "karsemine",
        events,
    )
    assert "Zephyr Strike" in msg
    assert "tracked Lysandra" in msg
    # Both events should appear in the JSON
    json_start = msg.index("```json\n") + len("```json\n")
    json_end = msg.index("\n```", json_start)
    parsed = json.loads(msg[json_start:json_end])
    assert len(parsed) == 2


# ---------------------------------------------------------------------------
# Test 2: per-slug filter skips slugs with zero matching events
# ---------------------------------------------------------------------------


def test_filter_events_for_slug_returns_all_matching():
    """filter_events_for_slug returns only events where slug is in participants."""
    events = [
        {"participants": ["caelynn", "captain_lysandra_ironveil"]},
        {"participants": ["karsemine"]},
        {"participants": ["caelynn", "ephanna"]},
    ]
    result = filter_events_for_slug(events, "caelynn")
    assert len(result) == 2
    for ev in result:
        assert "caelynn" in ev["participants"]


def test_filter_events_for_slug_returns_empty_when_slug_absent():
    """filter_events_for_slug returns [] when no events mention the slug.

    An empty return means the runner will skip the model call entirely and
    record per_slug_no_event_skip[slug] = True — no API cost incurred.
    """
    events = [
        {"participants": ["caelynn", "karsemine"]},
        {"participants": ["ephanna", "caelynn"]},
        {"participants": ["bonogo", "stacey", "stuart"]},
    ]
    result = filter_events_for_slug(events, "captain_lysandra_ironveil")
    assert result == [], (
        "captain_lysandra_ironveil not in any event participants — slug must be skipped"
    )


def test_filter_events_for_slug_exact_match_not_substring():
    """filter_events_for_slug matches exact slug strings, not substrings.

    This guards against 'Lysandra' matching 'captain_lysandra_ironveil'.
    """
    events = [
        {"participants": ["Lysandra"]},           # display name — wrong
        {"participants": ["Captain Lysandra"]},    # title + display name — wrong
        {"participants": ["captain_lysandra_ironveil"]},  # canonical slug — correct
    ]
    result = filter_events_for_slug(events, "captain_lysandra_ironveil")
    assert len(result) == 1
    assert result[0]["participants"] == ["captain_lysandra_ironveil"]


def test_filter_events_for_slug_returns_empty_list_for_zero_events():
    """When events list is empty, filter always returns empty — all slugs skipped."""
    assert filter_events_for_slug([], "caelynn") == []
    assert filter_events_for_slug([], "captain_lysandra_ironveil") == []


def test_ordered_stage_b_timeline_targets_custom_order():
    """C1 timeline-pass gold uses ``timeline_slug_order`` (not C2 _TIMELINE_PASS_SLUG_ORDER)."""
    grading = {
        "timeline_slug_order": ["zulu", "alpha"],
        "expected_appends": [
            {
                "npc_slug": "alpha",
                "timeline_relative_path": "Longmont Campaign/Campaign 1/PCs/alpha/timeline.md",
            },
            {
                "npc_slug": "zulu",
                "timeline_relative_path": "Longmont Campaign/Campaign 1/PCs/zulu/timeline.md",
            },
        ],
        "expected_skips": [],
    }
    targets = ordered_stage_b_timeline_targets(grading)
    assert [t["npc_slug"] for t in targets] == ["zulu", "alpha"]


# ---------------------------------------------------------------------------
# Test 3: Step2RunSummary round-trips through multi-summary markdown
# ---------------------------------------------------------------------------


def _make_summary(run_index: int, gates_passed: bool) -> Step2RunSummary:
    return Step2RunSummary(
        run_index=run_index,
        iso_utc=f"2026-04-22T03:47:{run_index:02d}Z",
        gates_passed=gates_passed,
        stage_a_cost_usd=0.0099,
        stage_b_cost_usd=0.0450,
        total_cost_usd=0.0549,
        stage_a_event_count=15,
        per_slug_no_event_skip={
            "captain_lysandra_ironveil": False,
            "dustwalker": True,
            "sara_mirathorn_operator": False,
            "thrin_branchborn": True,
            "torbin_jove": True,
            "caelynn": False,
            "karsemine": False,
            "ephanna": False,
        },
        violation_counts={} if gates_passed else {"timeline_pass_append": 2},
        per_gate_verdict={
            "TP1": "PASS" if gates_passed else "FAIL",
            "TP2": "PASS",
            "TP3": "PASS",
            "TP5": "PASS",
        },
        primary_md_path="/tmp/step2_run.md",
        sidecar_json_path="/tmp/step2_run.json",
    )


def test_step2_multi_summary_round_trips_key_fields():
    """write_step2_multi_summary markdown and JSON contain all required fields.

    Verifies that the summary writer doesn't silently drop TP1 pass rate,
    per-slug skip counts, cost breakdown, or run-level verdict.
    """
    summaries = [
        _make_summary(0, gates_passed=True),
        _make_summary(1, gates_passed=False),
        _make_summary(2, gates_passed=True),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        runs_root = Path(tmpdir) / "runs"
        md_path, json_path = write_step2_multi_summary(
            summaries,
            model_id="gpt-5.4-mini",
            scenario_id="timeline_pass_session20",
            runs_root=runs_root,
        )

        md_text = md_path.read_text(encoding="utf-8")
        payload = json.loads(json_path.read_text(encoding="utf-8"))

    # Headline TP1 pass rate
    assert "TP1 pass rate:" in md_text and "2/3" in md_text
    assert payload["per_gate_pass_counts"]["TP1"] == 2

    # Overall pass rate
    assert "overall pass rate:" in md_text and "2/3" in md_text
    assert payload["passed"] == 2
    assert payload["n"] == 3

    # Model and scenario
    assert "gpt-5.4-mini" in md_text
    assert "timeline_pass_session20" in md_text
    assert payload["model_id"] == "gpt-5.4-mini"
    assert payload["scenario_id"] == "timeline_pass_session20"

    # Per-slug skip counts (Stage A recall telemetry)
    assert "dustwalker" in md_text
    assert "torbin_jove" in md_text
    assert payload["per_slug_skip_counts_across_cohort"]["dustwalker"] == 3
    assert payload["per_slug_skip_counts_across_cohort"]["torbin_jove"] == 3
    assert payload["per_slug_skip_counts_across_cohort"]["captain_lysandra_ironveil"] == 0

    # Cost breakdown
    assert "stage_a_sum" in str(payload["cost_usd"])
    assert "stage_b_sum" in str(payload["cost_usd"])

    # Per-run data
    assert len(payload["runs"]) == 3
    assert payload["runs"][0]["gates_passed"] is True
    assert payload["runs"][1]["gates_passed"] is False
    assert payload["runs"][0]["per_gate_verdict"]["TP1"] == "PASS"
    assert payload["runs"][1]["per_gate_verdict"]["TP1"] == "FAIL"

    # Stage A event count preserved
    assert payload["runs"][0]["stage_a_event_count"] == 15

    # Schema field present
    assert payload["schema"] == "step2_timeline_from_events_multi_summary_v1"


def test_step2_run_report_writes_sidecar_with_all_fields():
    """write_step2_run_report sidecar JSON contains all required fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runs_root = Path(tmpdir) / "runs"
        _md, _json, summary = write_step2_run_report(
            run_index=0,
            cohort_size=5,
            gates_passed=True,
            per_gate_verdict_map={"TP1": "PASS", "TP2": "PASS", "TP3": "PASS", "TP5": "PASS"},
            violations={},
            grader_telemetry={"expected_append_slugs": ["caelynn"], "per_slug_new_row_count": {}},
            stage_a_event_count=14,
            per_slug_no_event_skip={"dustwalker": True, "caelynn": False},
            stage_a_cost_usd=0.0095,
            stage_b_cost_usd=0.0480,
            model_id="gpt-5.4-mini",
            scenario_id="timeline_pass_session20",
            runs_root=runs_root,
        )

    assert summary.gates_passed is True
    assert summary.stage_a_event_count == 14
    assert summary.per_slug_no_event_skip["dustwalker"] is True
    assert summary.per_slug_no_event_skip["caelynn"] is False
    assert summary.per_gate_verdict["TP1"] == "PASS"
    assert summary.total_cost_usd == pytest.approx(0.0575, abs=1e-6)


# ---------------------------------------------------------------------------
# Test A.0: infrastructure error skips Stage B
# ---------------------------------------------------------------------------


def test_run_single_chained_cohort_iteration_skips_stage_b_on_stage_a_error():
    """When Stage A returns an error, Stage B must not be called.

    This is the A.0 requirement: infra errors are excluded from the denominator
    and Stage B is never invoked for that run.
    """
    stage_a_error_result = {
        "parsed_events": [],
        "violations": {"input": ["simulated transient API failure"]},
        "telemetry": {
            "event_count": 0,
            "participants_seen": [],
            "event_classes_seen": [],
            "expected_event_coverage_ratio": 0.0,
            "unmatched_expected_event_indices": [],
        },
        "per_gate": {"SE1": "FAIL", "SE2": "FAIL", "SE3": "FAIL", "SE4": "FAIL", "SE5": "FAIL"},
        "cost_usd": 0.0,
        "usage": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
        "cost_info": {},
        "raw_response_id": "",
        "gates_passed": False,
        "error": "simulated transient API failure",
    }

    with patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".run_session_events_extraction",
        return_value=stage_a_error_result,
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".run_stage_b_events_driven_chain",
    ) as mock_stage_b:
        result = _run_single_chained_cohort_iteration(
            client=MagicMock(),
            model_id="gpt-5.4-mini",
            stage_a_scenario={"input": {"recap_relative_path": "x", "user_message": "y"}},
            corpus_root=Path("/fake/corpus"),
            stage_b_gold={"grading": {}},
            quiet=True,
        )

    assert result["infrastructure_error"] is True
    assert "simulated transient API failure" in result["error"]
    mock_stage_b.assert_not_called()


def test_run_single_chained_cohort_iteration_stage_b_called_on_success():
    """When Stage A succeeds, Stage B must be called (integration contract check)."""
    stage_a_ok_result = {
        "parsed_events": [
            {
                "event_class": "combat",
                "participants": ["caelynn"],
                "outcomes": ["healed Lysandra"],
                "time_scope": "scene",
                "certainty": "observed",
                "event_name": "Caelynn administers tea",
            }
        ],
        "violations": {},
        "telemetry": {},
        "per_gate": {"SE1": "PASS"},
        "cost_usd": 0.01,
        "usage": {},
        "cost_info": {},
        "raw_response_id": "resp_abc",
        "gates_passed": True,
        "error": None,
    }
    # Stage B returns minimal 5-tuple
    stage_b_return = ([], "", 0.01, {"caelynn": False}, {"caelynn": {"slug_events_sent": [], "slug_beat_written": None, "slug_model_message": None}})

    with patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".run_session_events_extraction",
        return_value=stage_a_ok_result,
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".run_stage_b_events_driven_chain",
        return_value=stage_b_return,
    ) as mock_stage_b, patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".build_pre_state_corpus",
        return_value=Path("/tmp/fake_corpus"),
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".collect_timeline_pass_violations",
        return_value=({}, {}),
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".tp_per_gate_verdict",
        return_value={"TP1": "PASS"},
    ):
        result = _run_single_chained_cohort_iteration(
            client=MagicMock(),
            model_id="gpt-5.4-mini",
            stage_a_scenario={"input": {"recap_relative_path": "x", "user_message": "y"}},
            corpus_root=Path("/fake/corpus"),
            stage_b_gold={"grading": {}},
            quiet=True,
        )

    assert result["infrastructure_error"] is False
    mock_stage_b.assert_called_once()


# ---------------------------------------------------------------------------
# Test A: diagnostic field capture helpers
# ---------------------------------------------------------------------------


def test_extract_beat_for_slug_returns_correct_beat():
    """_extract_beat_for_slug picks the right npc_slug's beat from a mixed tool trace."""
    tool_trace = [
        {"tool": "list_pc_hubs", "arguments": {}},
        {
            "tool": "append_timeline_row",
            "arguments": {
                "npc_slug": "caelynn",
                "beat": "Caelynn treated Lysandra with antidote tea at the wagon camp",
                "session": 20,
            },
        },
        {
            "tool": "append_timeline_row",
            "arguments": {
                "npc_slug": "karsemine",
                "beat": "Karsemine struck a final blow with her scimitar against the ambushers",
                "session": 20,
            },
        },
    ]
    assert (
        _extract_beat_for_slug(tool_trace, "caelynn")
        == "Caelynn treated Lysandra with antidote tea at the wagon camp"
    )
    assert (
        _extract_beat_for_slug(tool_trace, "karsemine")
        == "Karsemine struck a final blow with her scimitar against the ambushers"
    )
    assert _extract_beat_for_slug(tool_trace, "ephanna") is None


def test_extract_beat_for_slug_returns_none_on_empty_trace():
    """_extract_beat_for_slug returns None when tool trace is empty or has no append call."""
    assert _extract_beat_for_slug([], "caelynn") is None
    assert _extract_beat_for_slug([{"tool": "list_pc_hubs", "arguments": {}}], "caelynn") is None


def test_extract_beat_for_slug_returns_none_on_empty_beat():
    """_extract_beat_for_slug returns None when the beat arg is an empty string."""
    tool_trace = [
        {"tool": "append_timeline_row", "arguments": {"npc_slug": "caelynn", "beat": "", "session": 20}},
    ]
    assert _extract_beat_for_slug(tool_trace, "caelynn") is None


def test_stage_b_chain_no_event_skip_captures_null_diagnostics():
    """run_stage_b_events_driven_chain: no-event-skip slug gets slug_events_sent=[] and nulls.

    This satisfies requirement A(ii): no-event-skip slug populates slug_events_sent: []
    and slug_beat_written / slug_model_message as null.
    """
    stage_b_scenario = {
        "grading": {
            "expected_appends": [
                {
                    "npc_slug": "caelynn",
                    "timeline_relative_path": "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
                }
            ],
            "expected_skips": [],
            "allowed_npc_slugs": ["caelynn"],
        }
    }
    # Zero events for any slug — caelynn should be skipped, not modeled
    stage_a_events: list[dict] = []

    with patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".load_or_build_planner_instructions",
        return_value=("mock instructions text", "fp_mock"),
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".build_corpus_path_ref_index",
        return_value={},
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".make_tool_dispatcher",
        return_value=MagicMock(),
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        "._planner_tools_responses",
        return_value=[],
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".run_planning_turn_detailed",
    ) as mock_turn:
        _, _, _, per_slug_skip, per_slug_diag = run_stage_b_events_driven_chain(
            corpus_dir=Path("/tmp"),
            client=MagicMock(),
            model_id="gpt-5.4-mini",
            stage_b_scenario=stage_b_scenario,
            stage_a_events=stage_a_events,
            allow_corpus_writes=False,
            quiet=True,
        )

    # No-event skip: model must not be called for caelynn
    mock_turn.assert_not_called()
    assert per_slug_skip.get("caelynn") is True

    # Diagnostic fields: events sent must be [], others null
    assert "caelynn" in per_slug_diag
    assert per_slug_diag["caelynn"]["slug_events_sent"] == []
    assert per_slug_diag["caelynn"]["slug_beat_written"] is None
    assert per_slug_diag["caelynn"]["slug_model_message"] is None


def test_run_report_sidecar_contains_per_slug_diagnostics():
    """write_step2_run_report sidecar JSON preserves per_slug_diagnostics round-trip.

    Satisfies requirement A(iii): round-trip through Step2RunSummary → markdown →
    JSON sidecar preserves the diagnostic fields.
    """
    diag = {
        "caelynn": {
            "slug_events_sent": [
                {"event_class": "ritual", "participants": ["caelynn"], "outcomes": ["used bracelet"]}
            ],
            "slug_beat_written": "Caelynn used her bracelet to diffuse aggression",
            "slug_model_message": "Appended timeline row for caelynn.",
        },
        "dustwalker": {
            "slug_events_sent": [],
            "slug_beat_written": None,
            "slug_model_message": None,
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        runs_root = Path(tmpdir) / "runs"
        md_path, json_path, summary = write_step2_run_report(
            run_index=0,
            cohort_size=3,
            gates_passed=True,
            per_gate_verdict_map={"TP1": "PASS", "TP2": "PASS", "TP3": "PASS", "TP5": "PASS"},
            violations={},
            grader_telemetry={"expected_append_slugs": ["caelynn"], "per_slug_new_row_count": {}},
            stage_a_event_count=12,
            per_slug_no_event_skip={"caelynn": False, "dustwalker": True},
            stage_a_cost_usd=0.0095,
            stage_b_cost_usd=0.0400,
            model_id="gpt-5.4-mini",
            scenario_id="timeline_pass_session20",
            runs_root=runs_root,
            per_slug_diagnostics=diag,
        )

        sidecar = json.loads(json_path.read_text(encoding="utf-8"))
        md_text = md_path.read_text(encoding="utf-8")

    # Sidecar must contain the per_slug_diagnostics key
    assert "per_slug_diagnostics" in sidecar
    caelynn_diag = sidecar["per_slug_diagnostics"]["caelynn"]
    dustwalker_diag = sidecar["per_slug_diagnostics"]["dustwalker"]

    # caelynn: events sent + beat written + model message populated
    assert len(caelynn_diag["slug_events_sent"]) == 1
    assert caelynn_diag["slug_beat_written"] == "Caelynn used her bracelet to diffuse aggression"
    assert caelynn_diag["slug_model_message"] == "Appended timeline row for caelynn."

    # dustwalker: no-event skip — all nulls
    assert dustwalker_diag["slug_events_sent"] == []
    assert dustwalker_diag["slug_beat_written"] is None
    assert dustwalker_diag["slug_model_message"] is None

    # Markdown report must surface diagnostics
    assert "Per-slug diagnostics" in md_text
    assert "caelynn" in md_text
    assert "bracelet" in md_text

    # Step2RunSummary round-trip preserves diagnostics
    assert "caelynn" in summary.per_slug_diagnostics
    assert summary.per_slug_diagnostics["caelynn"]["slug_beat_written"] == (
        "Caelynn used her bracelet to diffuse aggression"
    )
    assert summary.per_slug_diagnostics["dustwalker"]["slug_events_sent"] == []


# ---------------------------------------------------------------------------
# Test PC-only scope: helpers + integration with grading filter
# ---------------------------------------------------------------------------


def test_is_pc_target_distinguishes_pcs_and_npcs():
    """_is_pc_target uses the /PCs/ vs /NPCs/ marker in timeline_relative_path."""
    from evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run import (
        _is_pc_target,
    )

    pc_spec = {
        "npc_slug": "caelynn",
        "timeline_relative_path": "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
    }
    npc_spec = {
        "npc_slug": "captain_lysandra_ironveil",
        "timeline_relative_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md",
    }
    missing_path = {"npc_slug": "x"}

    assert _is_pc_target(pc_spec) is True
    assert _is_pc_target(npc_spec) is False
    assert _is_pc_target(missing_path) is False


def test_filter_grading_to_pcs_drops_npc_entries():
    """_filter_grading_to_pcs drops NPC expected_appends/skips and tightens allowed_npc_slugs."""
    from evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run import (
        _filter_grading_to_pcs,
    )

    grading = {
        "expected_appends": [
            {
                "npc_slug": "caelynn",
                "timeline_relative_path": "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
            },
            {
                "npc_slug": "captain_lysandra_ironveil",
                "timeline_relative_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md",
            },
        ],
        "expected_skips": [
            {
                "npc_slug": "thrin_branchborn",
                "timeline_relative_path": "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/timeline.md",
            },
        ],
        "allowed_npc_slugs": ["caelynn", "captain_lysandra_ironveil", "thrin_branchborn"],
    }
    filtered = _filter_grading_to_pcs(grading)

    assert [s["npc_slug"] for s in filtered["expected_appends"]] == ["caelynn"]
    assert filtered["expected_skips"] == []
    assert filtered["allowed_npc_slugs"] == ["caelynn"]


def test_run_stage_b_chain_filters_targets_to_pcs():
    """run_stage_b_events_driven_chain only invokes the model for PC slugs.

    Even when the gold contains NPC expected_appends with non-empty event lists,
    the runner must skip them entirely (not record them as no-event skips, not
    invoke the model). PC slugs follow the existing per-slug pipeline.
    """
    from evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run import (
        run_stage_b_events_driven_chain,
    )

    stage_b_scenario = {
        "grading": {
            "expected_appends": [
                {
                    "npc_slug": "caelynn",
                    "timeline_relative_path": "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
                },
                {
                    "npc_slug": "captain_lysandra_ironveil",
                    "timeline_relative_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md",
                },
            ],
            "expected_skips": [
                {
                    "npc_slug": "thrin_branchborn",
                    "timeline_relative_path": "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/timeline.md",
                },
            ],
            "allowed_npc_slugs": ["caelynn", "captain_lysandra_ironveil", "thrin_branchborn"],
        }
    }
    # Both PCs and NPCs have events — but only PCs should reach the model.
    stage_a_events = [
        {"participants": ["caelynn"], "outcomes": ["healed Lysandra"]},
        {"participants": ["captain_lysandra_ironveil"], "outcomes": ["fell ill"]},
        {"participants": ["thrin_branchborn"], "outcomes": ["loosed an arrow"]},
    ]

    with patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".load_or_build_planner_instructions",
        return_value=("mock instructions text", "fp_mock"),
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".build_corpus_path_ref_index",
        return_value={},
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".make_tool_dispatcher",
        return_value=MagicMock(),
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        "._planner_tools_responses",
        return_value=[],
    ), patch(
        "evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run"
        ".run_planning_turn_detailed",
    ) as mock_turn:
        # Make the planner mock return a minimal detail object
        fake_detail = MagicMock()
        fake_detail.tool_trace = []
        fake_detail.final_text = "ok"
        fake_detail.last_response_id = "resp_x"
        fake_detail.telemetry_cost = {}
        mock_turn.return_value = fake_detail

        _, _, _, per_slug_skip, per_slug_diag = run_stage_b_events_driven_chain(
            corpus_dir=Path("/tmp"),
            client=MagicMock(),
            model_id="gpt-5.4-mini",
            stage_b_scenario=stage_b_scenario,
            stage_a_events=stage_a_events,
            allow_corpus_writes=False,
            quiet=True,
        )

    # Only caelynn (PC) should have triggered a model call
    assert mock_turn.call_count == 1
    # NPC slugs must not appear in skip-tracking or diagnostics — they are
    # filtered out before the per-slug loop, not recorded as no-event skips.
    assert "captain_lysandra_ironveil" not in per_slug_skip
    assert "thrin_branchborn" not in per_slug_skip
    assert "captain_lysandra_ironveil" not in per_slug_diag
    assert "thrin_branchborn" not in per_slug_diag
    # caelynn was modeled (not a no-event skip)
    assert per_slug_skip.get("caelynn") is False
