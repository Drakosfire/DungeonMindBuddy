from __future__ import annotations

import json
import subprocess
import sys

from evals.graph_memory_layer import static_preview_graph_ui_prototype as p


def test_manifest_validates() -> None:
    m = p.load_manifest()
    p.validate_manifest(m)
    assert m["schema"] == p.PROTOTYPE_MANIFEST_SCHEMA
    assert m["prototype_id"] == p.PROTOTYPE_ID
    assert m["campaign_id"] == "longmont-c2"
    assert m["target_session"] == 23
    assert m["execution_mode"] == "static_fixture_prototype"


def test_dependencies_validate() -> None:
    p.report.validate_all()
    p.harness.validate_all()
    assert p.harness.load_candidate_bundle()["bundle_id"] == p.harness.CANDIDATE_BUNDLE_ID


def test_model_shape_and_determinism() -> None:
    model = p.load_prototype_model()
    p.validate_prototype_model_shape(model)
    assert p.build_prototype_model() == model
    for key in ["summary", "safety_gate", "coverage_cards", "evidence_health", "high_risk_audit", "candidate_explorer", "candidate_detail_examples", "proposed_writes", "missing_coverage", "hard_failures", "disabled_review_controls", "boundary_statement"]:
        assert key in model


def test_html_shape_and_determinism() -> None:
    model = p.load_prototype_model()
    html = p.load_prototype_html()
    assert p.render_prototype_html(p.build_prototype_model()) == html
    for needle in ["<main", "Static fixture prototype", "Session 23 Memory Preview", "Safe but incomplete", "Not ready", "Evidence Health", "High-Risk Audit", "Candidate Graph Explorer", "Candidate Detail", "Proposed Writes Queue", "Missing Coverage", "Hard Failures", "Disabled Review Controls"]:
        assert needle in html
    assert ("<script" + " src=") not in html
    assert ("<link" + " rel=") not in html


def test_preview_content() -> None:
    model = p.load_prototype_model(); html = p.load_prototype_html()
    assert model["summary"]["status"] == "safe_but_incomplete"
    assert model["summary"]["gm_preview_readiness"] == "not_ready_for_gm_preview"
    assert "206 / 206" in html
    assert "33 / 42" in html
    assert "8 / 23" in html
    assert "6 / 14" in html
    assert "6 pending" in html
    assert model["hard_failures"]["total"] == 0
    assert model["summary"]["soft_misses"] == 45
    assert "Approve disabled" in html


def test_candidate_explorer_examples() -> None:
    html = p.load_prototype_html()
    for needle in ["Lysandra", "Lysandro", "Orik Tane", "Brin Holloway", "Heroes / party", "Tripod meat monsters", "remaining approaching horde"]:
        assert needle in html


def test_high_risk_content() -> None:
    html = p.load_prototype_html()
    for needle in ["node:lysandro", "edge:lysandra-recognizes-lysandro", "node:heroes-party", "node:thread-remaining-approaching-horde", "Forbidden claims absent"]:
        assert needle in html
    assert "automatically trusted" in html


def test_proposed_writes_are_pending_and_disabled() -> None:
    model = p.load_prototype_model(); pw = model["proposed_writes"]
    assert all(w["status"] == "pending" for w in pw["items"])
    assert pw["summary"]["approved_count"] == 0
    assert pw["summary"]["promoted_count"] == 0
    assert pw["summary"]["unsafe_status_count"] == 0
    assert "Approval controls are disabled" in p.load_prototype_html()


def test_safety_boundary() -> None:
    p.validate_no_runtime_leakage(p.load_manifest(), p.load_prototype_model(), p.load_prototype_html())
    diagnostics = p.load_manifest()["diagnostics"]
    for key in ["runtime_ui_required", "react_required", "api_required", "approval_persistence_required", "graph_write_required", "query_execution_required", "corpus_scan_required", "corpus_mutation_required", "plan_connected", "agent_interaction_connected", "production_behavior_changed"]:
        assert diagnostics[key] is False


def test_cli_outputs() -> None:
    validator = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_static_preview_graph_ui_prototype"], check=True, text=True, capture_output=True)
    assert "static preview graph UI prototype: ready" in validator.stdout
    report = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_static_preview_graph_ui_prototype"], check=True, text=True, capture_output=True)
    assert p.PROTOTYPE_HTML_PATH in report.stdout
    assert "safe_but_incomplete" in report.stdout
