from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_family_gate.json"
REPORT_PATH = REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-RECAP-INGESTION-SOURCE-FAMILY-GATE.md"
EXPECTED_ARTIFACT_IDS = {
    "normalized_recap_markdown",
    "breadcrumbed_recap_markdown",
    "frontmatter_seed_markdown",
    "session_memory_jsonl_meta",
    "corpus_impact_proof",
}


def _manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def _artifacts() -> dict[str, dict[str, Any]]:
    return {artifact["id"]: artifact for artifact in _manifest()["admitted_artifacts"]}


def test_gate_manifest_exists() -> None:
    assert MANIFEST_PATH.is_file()


def test_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_recap_ingestion_source_family_gate"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- recap-ingestion source-family gate: ready" in result.stdout


def test_manifest_identity_fields_are_correct() -> None:
    manifest = _manifest()
    assert manifest["schema"] == "dmb_recap_ingestion_source_family_gate_v0"
    assert manifest["version"] == "0.1"
    assert manifest["status"] == "active_gate"
    assert manifest["source_family"] == "recap_ingestion_source_artifacts"
    assert manifest["decision"] == "admit_explicit_recap_ingestion_artifacts_as_source_artifacts_only"


def test_admitted_artifact_ids_include_all_expected_artifacts() -> None:
    assert EXPECTED_ARTIFACT_IDS.issubset(set(_artifacts()))


def test_every_artifact_includes_default_semantic_states_and_shapes() -> None:
    required = {
        "default_canon_state",
        "default_lifecycle_state",
        "default_evidence_role",
        "default_authority_state",
        "default_visibility_state",
        "allowed_shapes",
        "forbidden_shapes",
    }
    for artifact in _artifacts().values():
        assert required.issubset(artifact)
        assert artifact["allowed_shapes"]
        assert artifact["forbidden_shapes"]


def test_required_shared_fields_include_canon_state() -> None:
    assert "canon_state" in set(_manifest()["required_shared_fields"])


def test_corpus_impact_proof_is_diagnostic_only() -> None:
    artifact = _artifacts()["corpus_impact_proof"]
    assert artifact["default_evidence_role"] == "diagnostic_only"
    assert artifact["default_canon_state"] == "diagnostic_only"


def test_frontmatter_seed_markdown_is_not_played_canon() -> None:
    assert _artifacts()["frontmatter_seed_markdown"]["default_canon_state"] != "played_canon"


def test_breadcrumbed_recap_markdown_is_navigation_hint_by_default() -> None:
    assert _artifacts()["breadcrumbed_recap_markdown"]["default_evidence_role"] == "navigation_hint"
    assert _artifacts()["breadcrumbed_recap_markdown"]["default_evidence_role"] != "source_evidence"


def test_normalized_recap_does_not_allow_extracted_fact_shapes() -> None:
    artifact = _artifacts()["normalized_recap_markdown"]
    assert artifact["default_evidence_role"] == "source_evidence"
    assert {"entity_fact", "relationship_fact", "alias_merge", "promotion_record"}.issubset(set(artifact["forbidden_shapes"]))
    assert not {"entity_fact", "relationship_fact", "alias_merge", "promotion_record"}.intersection(artifact["allowed_shapes"])


def test_global_constraints_forbid_runtime_and_fact_collapses() -> None:
    constraints = set(_manifest()["global_constraints"])
    assert {
        "no_corpus_scanning",
        "no_corpus_mutation",
        "no_runtime_consumption",
        "no_plan_or_agent_interaction_changes",
        "no_entity_extraction",
        "no_alias_resolution",
        "no_relationship_inference",
        "no_fact_promotion",
    }.issubset(constraints)


def test_blocked_source_families_include_required_families() -> None:
    assert {
        "canonical_corpus_scan",
        "live_play_records",
        "manifest_context_query",
        "runtime_retrieval_results",
        "tiptap_documents",
    }.issubset(set(_manifest()["blocked_source_families"]))


def test_report_doc_exists() -> None:
    assert REPORT_PATH.is_file()


def test_report_doc_states_no_adapter_runtime_or_ui_changes() -> None:
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert "No adapter/runtime/UI changes are made or authorized by this gate." in text
    assert "does not admit extracted campaign facts" in text
    assert "runtime consumption" in text


def test_report_doc_says_corpus_impact_is_not_narrative_truth() -> None:
    assert "`corpus_impact` is proof of ingestion behavior, not proof of narrative truth." in REPORT_PATH.read_text(encoding="utf-8")


def test_report_doc_says_frontmatter_seed_is_not_played_canon_by_default() -> None:
    assert "Frontmatter seed output is planning scaffold or candidate extraction metadata, not played canon by default." in REPORT_PATH.read_text(encoding="utf-8")


def test_report_doc_says_breadcrumbed_recap_is_not_blanket_source_evidence() -> None:
    assert "Breadcrumbed recap output is navigation/reference structure by default. It must not become blanket source evidence unless a specific source anchor supports the claim." in REPORT_PATH.read_text(encoding="utf-8")


def test_report_doc_says_normalized_recap_does_not_permit_inference() -> None:
    assert "Normalized recap markdown may be treated as source evidence for the recap artifact or anchored recap sections, but not as permission to infer entities, aliases, relationships, or promoted facts." in REPORT_PATH.read_text(encoding="utf-8")
