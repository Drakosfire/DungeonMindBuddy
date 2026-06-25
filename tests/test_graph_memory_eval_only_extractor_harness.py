from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer import eval_only_extractor_harness as h


def test_manifest_validates_and_paths_are_safe():
    m = h.load_harness_manifest()
    h.validate_harness_manifest(m)
    assert m["execution_mode"] == "eval_only_fixture"
    for k, v in m.items():
        if k.endswith("_path"):
            assert not Path(v).is_absolute()
            assert ".." not in Path(v).parts


def test_dependencies_validate():
    h.contract.validate_all()
    h.validate_manifest(h.load_manifest())
    h.validate_gold_candidate_graph()


def test_candidate_bundle_shape_and_pass_outputs():
    b = h.load_candidate_bundle()
    h.validate_candidate_bundle_shape(b)
    h.validate_candidate_pass_outputs(b)
    assert list(b["passes"]) == h.contract.PASS_ORDER
    assert b["generation_mode"] == "static_fixture"


def test_candidate_graph_preview_is_safe_and_pending():
    b = h.load_candidate_bundle()
    h.validate_candidate_graph(b)
    g = h.parse_candidate_graph(b)
    assert g.status == "preview"
    assert g.diagnostics.preview_only is True
    assert all(w.status == "pending" for w in g.proposed_writes)
    assert all(n.semantic_state.lifecycle_state != "promoted" for n in g.nodes)


def test_candidate_evidence_resolves_and_high_risk_audit_passes():
    b = h.load_candidate_bundle()
    h.validate_candidate_evidence(b)
    h.validate_candidate_high_risk_audit(b)
    text = json.dumps(b)
    for needle in ["Questionable Company", "second wave", "thread-monster-second-wave", "resolved battle outcome", "approved write", "promoted lifecycle"]:
        assert needle not in text


def test_comparison_report_is_deterministic_and_expected():
    b = h.load_candidate_bundle()
    report = h.compare_candidate_to_gold(b)
    assert report == h.load_expected_comparison_report()
    assert report["hard_failures"] == []
    assert report["scores"]["safety_gate_score"] == 1.0
    assert report["scores"]["evidence_alignment_score"] == 1.0
    assert report["scores"]["high_risk_audit_score"] == 1.0
    assert report["soft_misses"]
    assert report["coverage"]["missing_gold_nodes"]
    for key in ["node_recall", "edge_recall", "beat_recall"]:
        assert 0 <= report["scores"][key] <= 1


def test_safety_boundary_no_runtime_leakage():
    b = h.load_candidate_bundle()
    h.validate_no_runtime_leakage(h.load_harness_manifest(), b)
    text = json.dumps(b)
    for needle in ["llm_response", "model_response", "graph_write_result", "runtime_payload", "plan_payload", "agent_interaction_payload", "query_execution_payload"]:
        assert needle not in text


def test_validator_cli_exits_zero():
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_eval_only_extractor_harness"], text=True, capture_output=True, check=True)
    assert "eval-only extractor harness fixture: ready" in result.stdout


def test_report_cli_exits_zero_and_has_required_sections():
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_eval_only_extractor_harness"], text=True, capture_output=True, check=True)
    for section in ["## Pass Output Summary", "## Gold Comparison Scores", "## Hard Failures", "## Soft Misses", "## Boundary Statement"]:
        assert section in result.stdout
