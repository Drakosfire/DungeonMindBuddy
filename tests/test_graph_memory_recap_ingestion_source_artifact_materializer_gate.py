from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FAMILY_GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_family_gate.json"
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "recap_ingestion_source_artifacts_minimal.json"
GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_artifact_materializer_gate.json"
REPORT_PATH = REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-RECAP-INGESTION-SOURCE-ARTIFACT-MATERIALIZER-GATE.md"
SEMANTIC_FIELDS = {"canon_state", "lifecycle_state", "evidence_role", "authority_state", "visibility_state"}


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def _gate() -> dict[str, Any]:
    return _load(GATE_PATH)


def _family_artifacts() -> dict[str, dict[str, Any]]:
    return {artifact["id"]: artifact for artifact in _load(FAMILY_GATE_PATH)["admitted_artifacts"]}


def _fixture_ids() -> set[str]:
    return {artifact["admitted_artifact_id"] for artifact in _load(FIXTURE_PATH)["artifacts"]}


def _allowed() -> dict[str, dict[str, Any]]:
    return {artifact["admitted_artifact_id"]: artifact for artifact in _gate()["allowed_input_artifacts"]}


def test_materializer_gate_manifest_exists() -> None:
    assert GATE_PATH.is_file()


def test_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer_gate"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- recap-ingestion source artifact materializer gate: ready" in result.stdout


def test_manifest_identity_fields_are_correct() -> None:
    gate = _gate()
    assert gate["schema"] == "dmb_recap_ingestion_source_artifact_materializer_gate_v0"
    assert gate["version"] == "0.1"
    assert gate["status"] == "active_gate"
    assert gate["source_family"] == "recap_ingestion_source_artifacts"
    assert gate["decision"] == "allow_future_explicit_input_materializer_only"


def test_dependencies_include_family_gate_and_fixture() -> None:
    assert {"dmb_recap_ingestion_source_family_gate_v0", "dmb_recap_ingestion_source_artifact_fixture_v0"}.issubset(set(_gate()["depends_on"]))


def test_all_allowed_inputs_are_admitted_by_source_family_gate() -> None:
    assert set(_allowed()).issubset(set(_family_artifacts()))


def test_all_allowed_inputs_are_represented_in_synthetic_fixture() -> None:
    assert set(_allowed()).issubset(_fixture_ids())


def test_semantic_defaults_match_source_family_gate() -> None:
    family = _family_artifacts()
    for artifact_id, artifact in _allowed().items():
        for field in SEMANTIC_FIELDS:
            assert artifact[f"default_{field}"] == family[artifact_id][f"default_{field}"]


def test_all_allowed_inputs_define_locator_schemes_and_output_shapes() -> None:
    for artifact in _allowed().values():
        assert artifact["allowed_locator_schemes"]
        assert artifact["allowed_output_shapes"]


def test_normalized_recap_forbids_extracted_fact_shapes() -> None:
    assert {"entity_fact", "relationship_fact", "alias_merge", "promotion_record"}.issubset(set(_allowed()["normalized_recap_markdown"]["must_not_emit"]))


def test_breadcrumbed_recap_remains_navigation_hint() -> None:
    assert _allowed()["breadcrumbed_recap_markdown"]["default_evidence_role"] == "navigation_hint"


def test_frontmatter_seed_is_not_played_canon() -> None:
    assert _allowed()["frontmatter_seed_markdown"]["default_canon_state"] != "played_canon"


def test_corpus_impact_proof_remains_diagnostic_only() -> None:
    artifact = _allowed()["corpus_impact_proof"]
    assert artifact["default_canon_state"] == "diagnostic_only"
    assert artifact["default_evidence_role"] == "diagnostic_only"


def test_input_policy_forbids_discovery_and_runtime_paths() -> None:
    policy = _gate()["future_materializer_input_policy"]
    assert policy["input_mode"] == "explicit_paths_only"
    for field in [
        "directory_scanning_allowed", "glob_expansion_allowed", "corpus_scanning_allowed",
        "manifest_context_query_allowed", "live_play_query_allowed", "runtime_retrieval_allowed",
        "absolute_path_output_allowed",
    ]:
        assert policy[field] is False


def test_output_policy_requires_canon_state_and_forbids_adapter_payloads() -> None:
    policy = _gate()["future_materializer_output_policy"]
    assert "canon_state" in policy["required_fields"]
    assert policy["display_summary_is_evidence"] is False
    assert policy["full_text_output_allowed"] is False
    assert policy["production_adapter_payload_allowed"] is False


def test_global_forbidden_behaviors_include_required_blocks() -> None:
    forbidden = set(_gate()["global_forbidden_behaviors"])
    assert "no_materializer_in_this_pr" in forbidden
    assert {
        "no_adapter", "no_plan_integration", "no_agent_interaction_integration",
        "no_graph_retrieval", "no_entity_extraction", "no_alias_resolution",
        "no_relationship_inference", "no_corpus_mutation",
    }.issubset(forbidden)


def test_report_doc_exists() -> None:
    assert REPORT_PATH.is_file()


def test_report_doc_states_gate_boundaries() -> None:
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert "It does not implement that materializer." in text
    assert "The future materializer must accept explicit inputs only." in text
    assert "Graph-backed `/plan` and Agent Interaction consumption remain blocked" in text
