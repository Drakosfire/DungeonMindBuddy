from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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
    payload = build_payload(report=_single_report(), include_full_surface=False)
    assert payload["schema"] == PAYLOAD_SCHEMA
    assert payload["modeRows"][0]["strict_gold_ok"] == 1 or payload["modeRows"][0].get("rows_ok") == 1
    for key in ["summary", "modeRows", "questionRows", "questionCards", "guardrailRows", "modeGuide"]:
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
    payload = build_payload(report=mm, include_full_surface=False)
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
    payload = build_payload(report=mm, include_full_surface=False)
    assert payload["modeRows"]
    assert payload["questionRows"]
    assert payload["questionCards"]


def test_failing_rows_open_by_default():
    payload = build_payload(report=_single_report(ok=False), include_full_surface=False)
    assert payload["questionCards"][0]["open_by_default"] is True


def test_required_group_failures_are_visible():
    payload = build_payload(report=_single_report(ok=False), include_full_surface=False)
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
    payload = build_payload(report=report, include_full_surface=False)
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
    payload = build_payload(report=report, gold=gold, include_full_surface=False)
    assert payload["questionRows"][0]["known_gaps"] == "1/2"
def test_render_generated_block_has_markers_and_const():
    block = render_generated_block(build_payload(report=_single_report(), include_full_surface=False))
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
    payload = build_payload(report=_single_report(), include_full_surface=False)
    dumped = json.dumps(payload)
    for s in ["c1s4_oracle", "observed_c1s4", "oracle_text", "final_score"]:
        assert s not in dumped


def test_payload_is_projection_not_canonical_benchmark():
    payload = build_payload(report=_single_report(), report_path="/tmp/report.json", include_full_surface=False)
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


def test_canvas_payload_includes_rendered_context_packet():
    payload = build_payload(report=_single_report(), include_full_surface=False)
    assert "rendered_context_packet" in payload["questionRows"][0]
    assert payload["questionRows"][0]["rendered_context_packet"]["schema"] == "dmb_planner_context_render_v1"


def test_full_surface_payload_covers_all_planner_rows():
    payload = build_payload(report=_single_report(), include_full_surface=True)
    cards = payload["questionCards"]
    assert len(cards) >= 111
    planner = [c for c in cards if c.get("planner_facing") is not False and c.get("verdict") != "EVALUATOR"]
    assert len(planner) == 111
    for card in planner:
        assert card.get("rendered_context_packet", {}).get("schema") == "dmb_planner_context_render_v1"
        assert card.get("question")


def test_payload_includes_mode_guide():
    payload = build_payload(report=_single_report(), include_full_surface=True)
    guide = payload.get("modeGuide") or {}
    assert guide.get("modes")
    assert guide.get("verdict_legend")
    assert "111" in str(guide.get("scope") or "")
    assert "retrieval_terms" in str(guide)
    assert "planner affordances" in str(guide)


def test_payload_includes_support_field_policy_rank_diagnostics():
    payload = build_payload(report=_single_report(), include_full_surface=True)
    policy = payload.get("supportFieldPolicy") or {}
    assert policy.get("demo_mode") == "prior_plus_support_content_plus_lexical_hints"
    assert policy.get("ablation_mode") == "prior_plus_support_content_only"
    assert policy.get("rows")
    row = policy["rows"][0]
    for key in [
        "content_only_candidate_rank",
        "retrieval_terms_candidate_rank",
        "content_only_admitted_rank",
        "retrieval_terms_admitted_rank",
        "support_token_share_delta",
    ]:
        assert key in row


def test_payload_includes_pr66_planner_affordance_diagnostics():
    payload = build_payload(report=_single_report(), include_full_surface=True)
    diagnostics = payload.get("plannerAffordanceDiagnostics") or {}
    assert diagnostics.get("schema") == "dmb_c1s4_pr66_affordance_canvas_summary_v1"
    assert diagnostics.get("familyARows")
    counts = diagnostics.get("counts") or {}
    assert counts.get("family_a_support_rows") == 6
    assert counts.get("prior_only_policy_correct_suppression") >= 8
    row = diagnostics["familyARows"][0]
    assert "support_match_channels" in row
    assert "expected_support_refs_eval_only" in row


def test_payload_includes_planner_surface_coverage_section():
    payload = build_payload(report=_single_report(), include_full_surface=True)
    section = payload.get("plannerSurfaceCoverage") or {}
    assert section.get("schema") == "dmb_pr65_planner_surface_canvas_section_v1"
    assert section.get("rows")
    assert int((section.get("summary") or {}).get("planner_surface_rows") or 0) == 111
    assert section.get("failureSurfaceCounts")


def test_canvas_renderer_can_emit_expandable_context():
    block = render_generated_block(build_payload(report=_single_report(), include_full_surface=True))
    assert "rendered_context_packet" in block
    assert "sections" in block
    assert "Known Gaps and Safety Constraints" in block
    template = Path(
        "evals/c1s4_preplanning_vertical_slice/canvas_templates/c1s4_expected_context_benchmark.canvas.tsx"
    ).read_text(encoding="utf-8")
    assert 'from "cursor/canvas"' in template
    assert "Rendered LLM context" in template
    assert "ModeGuidePanel" in template
    assert "SupportFieldPolicyPanel" in template
    assert "PlannerAffordanceDiagnosticsPanel" in template
    assert "retrieval_terms" in template
    assert "full deep dive" in template
    assert 'className="' not in template


def test_payload_declares_canvas_ui_scope_boundary():
    payload = build_payload(report=_single_report(), include_full_surface=False)
    details = " ".join(r.get("detail", "") for r in payload.get("guardrailRows", []))
    assert "cursor/canvas" in details
    assert "generated data block" in details


def test_payload_includes_mode_filter_options():
    mm = {
        "reports_by_mode": {
            "prior_only": _single_report(),
            "prior_plus_support_content_only": _single_report(ok=False),
        },
        "mode_deltas": {},
    }
    payload = build_payload(report=mm, include_full_surface=False)
    opts = payload["summary"]["modeOptions"]
    assert opts[0]["value"] == "all"
    assert any(o["value"] == "prior_only" for o in opts)
    assert payload["questionCards"][0]["required_groups_label"] == "1/1"


def test_pr43_readme_explicitly_declares_external_canvas_ui_ownership():
    txt = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr43/README.md").read_text(encoding="utf-8")
    assert "does not" in txt and "accordion/details UI" in txt
    assert "external Cursor canvas shell/runtime" in txt


def test_canvas_payload_includes_pr67_admission_diagnostics():
    payload = build_payload(report=_single_report(), include_full_surface=True)
    admission = payload.get("admissionDecisionDiagnostics") or {}
    assert admission.get("schema") == "dmb_c1s4_pr67_admission_canvas_summary_v1"
    assert admission.get("tierAGroupRows")
    tier_a_cards = [
        card
        for card in payload.get("questionCards") or []
        if int(card.get("question_number") or 0) in {1, 3, 5}
    ]
    assert any(card.get("pr67_admission_diagnostics") for card in tier_a_cards)


def test_canvas_payload_carries_packet_quality_metrics():
    payload = build_payload(report=_single_report(), include_full_surface=False)
    assert "packet_quality_metrics" in payload["questionRows"][0]
    assert "packet_quality_metrics" in payload["questionCards"][0]
