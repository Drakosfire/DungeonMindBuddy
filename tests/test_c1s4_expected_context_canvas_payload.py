from __future__ import annotations

import json
import subprocess
import sys

from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import (
    build_expected_context_report,
    build_multimode_expected_context_report,
    load_expected_context_gold,
)
from evals.c1s4_preplanning_vertical_slice.expected_context_canvas_payload import (
    PAYLOAD_SCHEMA,
    build_payload,
    render_generated_block,
    update_canvas_text,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary


def _single_report(ok: bool = True) -> dict:
    return {
        "retrieval_mode": "prior_only",
        "counts": {
            "questions_evaluated": 1,
            "rows_ok": 1 if ok else 0,
            "rows_failed": 0 if ok else 1,
            "required_context_groups": 1,
            "required_context_groups_hit": 1 if ok else 0,
            "forbidden_context_group_violations": 0,
            "known_gap_expectations": 1,
            "known_gap_expectations_hit": 1,
        },
        "metrics": {
            "macro_required_group_recall_at_k": 1.0 if ok else 0.0,
            "known_gap_recall": 1.0,
        },
        "results": [
            {
                "question_number": 5,
                "question_id": "q05",
                "retrieval_mode": "prior_only",
                "ok": ok,
                "required_context_groups": 1,
                "required_context_groups_hit": 1 if ok else 0,
                "matched_groups": [{"group_id": "g1", "ok": ok, "min_hits": 1, "hit_count": 1 if ok else 0, "matched_context_refs": []}],
                "missing_required_groups": [] if ok else ["g1"],
                "forbidden_context_groups_hit": [],
                "known_gap_expectations": 1,
                "known_gap_expectations_hit": ["gap1"],
                "authority_summary": {},
                "violations": [] if ok else ["missing_required_context_group"],
            }
        ],
    }


def test_build_payload_from_single_mode_report():
    payload = build_payload(report=_single_report())
    assert payload["schema"] == PAYLOAD_SCHEMA
    assert payload["modeRows"][0]["required_group_recall"] == "1.00"
    for key in ["summary", "modeRows", "questionRows", "questionCards", "guardrailRows"]:
        assert key in payload


def test_build_payload_from_multimode_report():
    mm = {
        "reports_by_mode": {
            "prior_only": _single_report(),
            "prior_plus_support_content_only": _single_report(),
            "prior_plus_support_content_plus_lexical_hints": _single_report(),
        },
        "mode_deltas": {"x": 1},
    }
    payload = build_payload(report=mm)
    assert len(payload["summary"]["modes"]) == 3
    assert payload["modeDeltas"] == {"x": 1}


def test_build_payload_from_real_multimode_report():
    gold = load_expected_context_gold()
    reports = {m: build_expected_context_report(packets=build_summary(mode=m)["packets"], gold=gold, retrieval_mode=m) for m in [
        "prior_only",
        "prior_plus_support_content_only",
        "prior_plus_support_content_plus_lexical_hints",
    ]}
    mm = build_multimode_expected_context_report(reports_by_mode=reports)
    payload = build_payload(report=mm)
    assert payload["modeRows"]
    assert payload["questionRows"]
    assert payload["questionCards"]


def test_failing_rows_open_by_default():
    payload = build_payload(report=_single_report(ok=False))
    assert payload["questionCards"][0]["open_by_default"] is True


def test_required_group_failures_are_visible():
    payload = build_payload(report=_single_report(ok=False))
    card = payload["questionCards"][0]
    assert card["missing_required_groups"]
    assert card["violations"]
    assert card["required_context_groups"]




def test_known_gap_ratio_not_misleading_without_gold_totals():
    report = _single_report(ok=False)
    row = report["results"][0]
    row["known_gap_expectations_hit"] = ["gap1"]
    row["violations"] = ["missing_expected_known_gap"]
    row.pop("known_gap_expectations", None)
    payload = build_payload(report=report)
    assert payload["questionRows"][0]["known_gaps"] == "1/?"


def test_known_gap_ratio_uses_gold_totals_when_available():
    report = _single_report(ok=False)
    row = report["results"][0]
    row["known_gap_expectations_hit"] = ["gap1"]
    row["violations"] = ["missing_expected_known_gap"]
    gold = {
        "questions": [
            {
                "question_number": 5,
                "question_id": "q05",
                "expectations_by_mode": {
                    "prior_only": {
                        "expected_known_gaps_contains_any": ["gap1", "gap2"]
                    }
                },
            }
        ]
    }
    payload = build_payload(report=report, gold=gold)
    assert payload["questionRows"][0]["known_gaps"] == "1/2"
def test_render_generated_block_has_markers_and_const():
    block = render_generated_block(build_payload(report=_single_report()))
    assert "BEGIN GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA" in block
    assert "END GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA" in block
    assert "const c1s4ExpectedContextCanvasData =" in block


def test_update_canvas_text_replaces_generated_region():
    old = "a\n// BEGIN GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA\nfoo\n// END GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA\nz"
    new = update_canvas_text(old, "// BEGIN GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA\nbar\n// END GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA")
    assert "bar" in new and "foo" not in new and new.startswith("a\n") and new.endswith("\nz")


def test_update_canvas_text_rejects_missing_markers():
    try:
        update_canvas_text("no markers", "x")
        assert False
    except ValueError:
        assert True


def test_payload_contains_no_full_oracle_text():
    payload = build_payload(report=_single_report())
    dumped = json.dumps(payload)
    for s in ["c1s4_oracle", "observed_c1s4", "oracle_text", "final_score"]:
        assert s not in dumped


def test_payload_is_projection_not_canonical_benchmark():
    payload = build_payload(report=_single_report(), report_path="/tmp/report.json")
    dumped = json.dumps(payload)
    assert payload["sources"]["report"] == "/tmp/report.json"
    assert "expectations_by_mode" not in dumped


def test_cli_check_mode_reports_stale_canvas(tmp_path):
    report = tmp_path / "r.json"
    report.write_text(json.dumps(_single_report()), encoding="utf-8")
    canvas = tmp_path / "c.canvas.tsx"
    canvas.write_text("// BEGIN GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA\nconst c1s4ExpectedContextCanvasData = {} as const;\n// END GENERATED C1S4_EXPECTED_CONTEXT_CANVAS_DATA\n", encoding="utf-8")
    proc = subprocess.run([
        sys.executable,
        "evals/c1s4_preplanning_vertical_slice/step2d_expected_context_canvas_emit.py",
        "--report",
        str(report),
        "--canvas-tsx",
        str(canvas),
        "--check",
    ], capture_output=True, text=True)
    assert proc.returncode == 1
