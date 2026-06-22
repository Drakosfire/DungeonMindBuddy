from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_family_gate.json"
EXPECTED_SCHEMA = "dmb_recap_ingestion_source_family_gate_v0"
EXPECTED_ARTIFACT_IDS = {
    "normalized_recap_markdown",
    "breadcrumbed_recap_markdown",
    "frontmatter_seed_markdown",
    "session_memory_jsonl_meta",
    "corpus_impact_proof",
}
REQUIRED_ARTIFACT_FIELDS = {
    "artifact_kind",
    "source_layer",
    "default_canon_state",
    "default_lifecycle_state",
    "default_evidence_role",
    "default_authority_state",
    "default_visibility_state",
    "allowed_shapes",
    "forbidden_shapes",
}
REQUIRED_SHARED_FIELDS = {
    "source_artifact",
    "source_anchor",
    "source_unit",
    "source_ref",
    "provenance",
    "evidence_role",
    "authority_state",
    "visibility_state",
    "lifecycle_state",
    "canon_state",
}
REQUIRED_GLOBAL_CONSTRAINTS = {
    "no_corpus_scanning",
    "no_corpus_mutation",
    "no_runtime_consumption",
    "no_plan_or_agent_interaction_changes",
    "no_entity_extraction",
    "no_alias_resolution",
    "no_relationship_inference",
    "no_fact_promotion",
    "display_summary_is_not_evidence",
}
REQUIRED_BLOCKED_SOURCE_FAMILIES = {
    "canonical_corpus_scan",
    "live_play_records",
    "manifest_context_query",
    "runtime_retrieval_results",
    "tiptap_documents",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_manifest() -> dict[str, Any]:
    _require(MANIFEST_PATH.is_file(), "gate manifest missing")
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _require(isinstance(data, dict), "gate manifest must be a JSON object")
    return data


def _artifacts_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = data.get("admitted_artifacts")
    _require(isinstance(artifacts, list), "admitted_artifacts must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        _require(isinstance(artifact, dict), "each admitted artifact must be an object")
        artifact_id = artifact.get("id")
        _require(isinstance(artifact_id, str), "each admitted artifact must have a string id")
        by_id[artifact_id] = artifact
    return by_id


def _require_contains(observed: set[str], expected: set[str], label: str) -> None:
    missing = sorted(expected - observed)
    _require(not missing, f"{label} missing required entries: {', '.join(missing)}")


def main() -> int:
    print("Graph Memory recap-ingestion source-family gate validation")
    data = _load_manifest()
    print("- gate manifest: found")

    _require(data.get("schema") == EXPECTED_SCHEMA, "bad schema")
    print(f"- schema: {EXPECTED_SCHEMA}")
    _require(data.get("version") == "0.1", "version must be 0.1")
    _require(data.get("status") == "active_gate", "status must be active_gate")
    _require(data.get("source_family") == "recap_ingestion_source_artifacts", "bad source family")
    _require(data.get("decision") == "admit_explicit_recap_ingestion_artifacts_as_source_artifacts_only", "bad decision")

    artifacts = _artifacts_by_id(data)
    _require_contains(set(artifacts), EXPECTED_ARTIFACT_IDS, "admitted artifacts")
    for artifact_id in EXPECTED_ARTIFACT_IDS:
        artifact = artifacts[artifact_id]
        _require_contains(set(artifact), REQUIRED_ARTIFACT_FIELDS, f"{artifact_id} fields")
        _require(isinstance(artifact["allowed_shapes"], list) and artifact["allowed_shapes"], f"{artifact_id} allowed_shapes must be non-empty")
        _require(isinstance(artifact["forbidden_shapes"], list) and artifact["forbidden_shapes"], f"{artifact_id} forbidden_shapes must be non-empty")
    print("- admitted artifacts: ready")

    _require_contains(set(data.get("required_shared_fields", [])), REQUIRED_SHARED_FIELDS, "required shared fields")
    print("- shared semantic envelope: ready")

    _require(artifacts["corpus_impact_proof"]["default_evidence_role"] == "diagnostic_only", "corpus_impact_proof must be diagnostic_only")
    _require(artifacts["frontmatter_seed_markdown"]["default_canon_state"] != "played_canon", "frontmatter seed must not default to played canon")
    _require(artifacts["breadcrumbed_recap_markdown"]["default_evidence_role"] == "navigation_hint", "breadcrumbed recap must default to navigation_hint")
    _require(artifacts["breadcrumbed_recap_markdown"]["default_evidence_role"] != "source_evidence", "breadcrumbed recap must not default to source_evidence")
    _require(artifacts["normalized_recap_markdown"]["default_evidence_role"] == "source_evidence", "normalized recap should carry source_evidence")
    normalized_allowed = set(artifacts["normalized_recap_markdown"]["allowed_shapes"])
    normalized_forbidden = set(artifacts["normalized_recap_markdown"]["forbidden_shapes"])
    _require({"SourceArtifact", "document_SourceAnchor", "section_SourceUnit_if_explicit"}.issubset(normalized_allowed), "normalized recap evidence must be artifact/document/section scoped")
    _require({"entity_fact", "relationship_fact", "alias_merge", "promotion_record"}.issubset(normalized_forbidden), "normalized recap must forbid extracted fact shapes")
    print("- lifecycle/canon/evidence defaults: ready")

    _require_contains(set(data.get("global_constraints", [])), REQUIRED_GLOBAL_CONSTRAINTS, "global constraints")
    for artifact_id in EXPECTED_ARTIFACT_IDS:
        _require(set(artifacts[artifact_id]["forbidden_shapes"]), f"{artifact_id} forbidden shapes missing")
    print("- forbidden shapes: ready")

    _require_contains(set(data.get("blocked_source_families", [])), REQUIRED_BLOCKED_SOURCE_FAMILIES, "blocked source families")
    print("- blocked source families: ready")
    print("- recap-ingestion source-family gate: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"- recap-ingestion source-family gate: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
