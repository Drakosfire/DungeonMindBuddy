from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer import eval_only_extractor_harness as h
from evals.graph_memory_layer import static_extractor_output_comparison_report as r


def test_manifest_validates_and_paths_are_safe():
    m = r.load_manifest(); r.validate_manifest(m)
    assert m["schema"] == r.REPORT_MANIFEST_SCHEMA
    assert m["version"] == r.REPORT_VERSION
    assert m["report_fixture_id"] == r.REPORT_FIXTURE_ID
    assert m["campaign_id"] == "longmont-c2" and m["target_session"] == 23
    assert m["execution_mode"] == "static_report_fixture"
    assert m["source_harness_id"] == h.HARNESS_ID
    assert m["candidate_bundle_id"] == h.CANDIDATE_BUNDLE_ID
    assert m["gold_fixture_id"] == r.GOLD_FIXTURE_ID
    for k, v in m.items():
        if k.endswith("_path"):
            assert not Path(v).is_absolute(); assert ".." not in Path(v).parts
    assert all(v is (k == "static_report_fixture") for k, v in m["diagnostics"].items())


def test_dependencies_validate_and_expected_comparison_matches():
    h.validate_all()
    assert h.compare_candidate_to_gold(h.load_candidate_bundle()) == h.load_expected_comparison_report()


def test_json_report_shape_and_determinism():
    report = r.load_static_report_json(); r.validate_static_report_shape(report); r.validate_static_report_consistency(report)
    assert report == r.build_static_report_json()
    for key in ["verdict", "score_summary", "coverage_summary", "hard_failure_summary", "soft_miss_summary", "evidence_health", "high_risk_audit_summary", "proposed_write_summary", "gm_preview_readiness"]:
        assert key in report
    assert all(v is (k == "static_report_fixture") for k, v in report["diagnostics"].items())


def test_markdown_determinism_and_required_content():
    report = r.build_static_report_json(); markdown = r.load_static_report_markdown()
    assert markdown == r.build_static_report_markdown(report)
    for heading in ["# Static Extractor Output Comparison Report", "## Verdict", "## Safety Gate", "## Score Summary", "## Coverage Summary", "## Missing Gold Coverage", "## Soft Misses By Category", "## Hard Failures", "## Evidence Health", "## High-Risk Audit", "## Proposed Writes", "## GM Preview Readiness", "## Boundary Statement"]:
        assert heading in markdown
    assert "safe_but_incomplete" in markdown
    assert "not_ready_for_gm_preview" in markdown
    assert h.load_raw_recap() not in markdown


def test_verdict_scores_and_coverage_match_source_report():
    report = r.load_static_report_json(); comp = h.load_expected_comparison_report()
    assert report["verdict"]["status"] == "safe_but_incomplete"
    assert report["verdict"]["merge_gate"] == "pass"
    assert report["verdict"]["blocking_issue_count"] == 0
    assert report["verdict"]["soft_issue_count"] == len(comp["soft_misses"]) > 0
    assert report["score_summary"]["overall_safety"]["band"] == "pass"
    assert report["score_summary"]["coverage"]["node_recall"]["band"] == "good"
    assert report["score_summary"]["coverage"]["edge_recall"]["band"] == "weak"
    assert report["score_summary"]["coverage"]["beat_recall"]["band"] == "partial"
    assert report["score_summary"]["coverage"]["proposed_write_recall"]["band"] == "weak"
    for typ in ["nodes", "edges", "beats", "proposed_writes", "ignored_items", "deferred_items"]:
        c = report["coverage_summary"][typ]
        assert c["gold_total"] == comp["coverage"][f"gold_{typ}_total"]
        assert c["candidate_total"] == comp["coverage"][f"candidate_{typ}_total"]
        assert c["matched"] == len(comp["coverage"][f"matched_{typ}"])
        assert c["missing"] == len(comp["coverage"][f"missing_gold_{typ}"])
        assert c["extra"] == len(comp["coverage"][f"extra_candidate_{typ}"])


def test_soft_hard_evidence_high_risk_writes_and_preview_summaries():
    report = r.load_static_report_json()
    assert report["hard_failure_summary"] == {"total": 0, "by_issue": {}, "blocking": False, "reviewer_note": "No hard safety failures were found in the static sample candidate output."}
    soft = report["soft_miss_summary"]
    assert soft["total"] > 0
    for issue in ["missing_required_node", "missing_required_edge", "missing_required_beat", "missing_proposed_write"]:
        assert soft["by_issue"][issue]["count"] > 0
    e = report["evidence_health"]
    assert e["total_evidence_refs"] == e["resolved_evidence_refs"] == e["openable_evidence_refs"] == e["highlightable_evidence_refs"]
    assert e["warning_count"] == 0 and e["source_leakage_detected"] is False
    audit = report["high_risk_audit_summary"]
    assert audit["status"] == "pass"
    for oid in ["node:lysandro", "edge:lysandra-recognizes-lysandro", "node:heroes-party", "node:thread-remaining-approaching-horde"]:
        assert oid in audit["audited_objects"]
    writes = report["proposed_write_summary"]
    assert writes["pending_count"] == writes["candidate_total"]
    assert writes["approved_count"] == writes["promoted_count"] == writes["unsafe_status_count"] == 0
    gm = report["gm_preview_readiness"]
    assert gm["status"] == "not_ready_for_gm_preview"
    assert gm["safe_to_inspect"] is True and gm["safe_to_write"] is False and gm["sufficient_coverage_for_preview"] is False


def test_safety_boundary_no_runtime_leakage():
    text = json.dumps(r.load_static_report_json()) + r.load_static_report_markdown()
    for needle in ["llm_response", "model_response", "extractor_runtime", "graph_write_result", "runtime_payload", "plan_payload", "agent_interaction_payload", "query_execution_payload", "network_client"]:
        assert needle not in text
    r.validate_no_runtime_leakage(r.load_manifest(), r.load_static_report_json(), r.load_static_report_markdown())


def test_cli_outputs():
    validator = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_static_extractor_output_comparison_report"], text=True, capture_output=True, check=True)
    assert "static extractor output comparison report: ready" in validator.stdout
    report = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_static_extractor_output_comparison_report"], text=True, capture_output=True, check=True)
    assert report.stdout == r.load_static_report_markdown()
