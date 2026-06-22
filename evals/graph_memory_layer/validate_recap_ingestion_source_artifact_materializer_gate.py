from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_family_gate.json"
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "recap_ingestion_source_artifacts_minimal.json"
MATERIALIZER_GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_artifact_materializer_gate.json"
EXPECTED_SCHEMA = "dmb_recap_ingestion_source_artifact_materializer_gate_v0"
EXPECTED_DEPENDENCIES = {"dmb_recap_ingestion_source_family_gate_v0", "dmb_recap_ingestion_source_artifact_fixture_v0"}
SEMANTIC_FIELDS = ("canon_state", "lifecycle_state", "evidence_role", "authority_state", "visibility_state")
REQUIRED_INPUT_FIELDS = {
    "admitted_artifact_id", "artifact_kind", "input_contract", "allowed_locator_schemes",
    "default_canon_state", "default_lifecycle_state", "default_evidence_role",
    "default_authority_state", "default_visibility_state", "allowed_output_shapes", "must_not_emit",
}
FORBIDDEN_FALSE_POLICY_FIELDS = {
    "directory_scanning_allowed", "glob_expansion_allowed", "corpus_scanning_allowed",
    "manifest_context_query_allowed", "live_play_query_allowed", "runtime_retrieval_allowed",
    "absolute_path_output_allowed",
}
REQUIRED_OUTPUT_FIELDS = {
    "source_artifact", "source_anchor", "source_unit", "source_ref", "provenance",
    "evidence_role", "authority_state", "visibility_state", "lifecycle_state", "canon_state",
}
REQUIRED_FORBIDDEN_BEHAVIORS = {
    "no_materializer_in_this_pr", "no_adapter", "no_plan_integration",
    "no_agent_interaction_integration", "no_graph_retrieval", "no_shadow_retrieval",
    "no_entity_extraction", "no_alias_resolution", "no_identity_merge",
    "no_relationship_inference", "no_fact_promotion", "no_canon_promotion",
    "no_corpus_scanning", "no_corpus_mutation", "no_production_behavior_changes",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    _require(path.is_file(), f"{label} missing")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _require(isinstance(data, dict), f"{label} must be a JSON object")
    return data


def _family_artifacts(gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = gate.get("admitted_artifacts")
    _require(isinstance(artifacts, list), "source-family gate admitted_artifacts must be a list")
    return {artifact["id"]: artifact for artifact in artifacts if isinstance(artifact, dict) and isinstance(artifact.get("id"), str)}


def _fixture_artifact_ids(fixture: dict[str, Any]) -> set[str]:
    artifacts = fixture.get("artifacts")
    _require(isinstance(artifacts, list), "source artifact fixture artifacts must be a list")
    return {artifact.get("admitted_artifact_id") for artifact in artifacts if isinstance(artifact, dict)}


def main() -> int:
    print("Graph Memory recap-ingestion source artifact materializer gate validation")
    family_gate = _load_json(FAMILY_GATE_PATH, "source-family gate")
    print("- source-family gate: found")
    fixture = _load_json(FIXTURE_PATH, "source artifact fixture")
    print("- source artifact fixture: found")
    gate = _load_json(MATERIALIZER_GATE_PATH, "materializer gate")
    print("- materializer gate: found")

    _require(gate.get("schema") == EXPECTED_SCHEMA, "bad materializer gate schema")
    print(f"- schema: {EXPECTED_SCHEMA}")
    _require(gate.get("version") == "0.1", "version must be 0.1")
    _require(gate.get("status") == "active_gate", "status must be active_gate")
    _require(gate.get("source_family") == "recap_ingestion_source_artifacts", "bad source family")
    _require(gate.get("decision") == "allow_future_explicit_input_materializer_only", "bad gate decision")
    _require(EXPECTED_DEPENDENCIES.issubset(set(gate.get("depends_on", []))), "dependencies incomplete")
    print("- dependencies: ready")

    family_by_id = _family_artifacts(family_gate)
    fixture_ids = _fixture_artifact_ids(fixture)
    allowed = gate.get("allowed_input_artifacts")
    _require(isinstance(allowed, list) and allowed, "allowed_input_artifacts must be non-empty")
    for artifact in allowed:
        _require(isinstance(artifact, dict), "allowed input artifact must be an object")
        _require(REQUIRED_INPUT_FIELDS.issubset(artifact), f"allowed input artifact missing fields: {artifact.get('admitted_artifact_id')}")
        artifact_id = artifact["admitted_artifact_id"]
        _require(artifact_id in family_by_id, f"{artifact_id} not admitted by source-family gate")
        _require(artifact_id in fixture_ids, f"{artifact_id} not represented in source artifact fixture")
        _require(artifact["artifact_kind"] == family_by_id[artifact_id]["artifact_kind"], f"{artifact_id} artifact_kind mismatch")
        _require(isinstance(artifact["allowed_locator_schemes"], list) and artifact["allowed_locator_schemes"], f"{artifact_id} locator schemes missing")
        _require(isinstance(artifact["allowed_output_shapes"], list) and artifact["allowed_output_shapes"], f"{artifact_id} output shapes missing")
        for field in SEMANTIC_FIELDS:
            _require(artifact[f"default_{field}"] == family_by_id[artifact_id][f"default_{field}"], f"{artifact_id} default {field} mismatch")
        _require(set(family_by_id[artifact_id]["forbidden_shapes"]).issubset(set(artifact["must_not_emit"])), f"{artifact_id} forbidden shapes mismatch")
    print("- allowed input artifacts: ready")

    by_id = {artifact["admitted_artifact_id"]: artifact for artifact in allowed}
    _require({"entity_fact", "relationship_fact", "alias_merge", "promotion_record"}.issubset(set(by_id["normalized_recap_markdown"]["must_not_emit"])), "normalized recap must forbid extracted fact shapes")
    _require(by_id["breadcrumbed_recap_markdown"]["default_evidence_role"] == "navigation_hint", "breadcrumbed recap must default to navigation_hint")
    _require(by_id["frontmatter_seed_markdown"]["default_canon_state"] != "played_canon", "frontmatter seed must not be played canon")
    _require(by_id["corpus_impact_proof"]["default_canon_state"] == "diagnostic_only", "corpus_impact_proof must be diagnostic_only")
    print("- semantic defaults: ready")

    input_policy = gate.get("future_materializer_input_policy")
    _require(isinstance(input_policy, dict), "future_materializer_input_policy must be object")
    _require(input_policy.get("input_mode") == "explicit_paths_only", "input mode must be explicit_paths_only")
    _require(input_policy.get("minimum_required_inputs", 0) >= 1, "minimum required inputs must be at least 1")
    for field in FORBIDDEN_FALSE_POLICY_FIELDS:
        _require(input_policy.get(field) is False, f"{field} must be false")
    print("- explicit input policy: ready")

    output_policy = gate.get("future_materializer_output_policy")
    _require(isinstance(output_policy, dict), "future_materializer_output_policy must be object")
    _require(REQUIRED_OUTPUT_FIELDS.issubset(set(output_policy.get("required_fields", []))), "output policy missing required semantic envelope")
    _require(output_policy.get("display_summary_is_evidence") is False, "display_summary must not be evidence")
    _require(output_policy.get("full_text_output_allowed") is False, "full text output must not be allowed")
    _require(output_policy.get("graph_ids_public_contract") is False, "graph IDs must not be public contract")
    _require(output_policy.get("production_adapter_payload_allowed") is False, "production adapter payloads must not be allowed")
    print("- output policy: ready")

    _require(REQUIRED_FORBIDDEN_BEHAVIORS.issubset(set(gate.get("global_forbidden_behaviors", []))), "global forbidden behaviors incomplete")
    print("- forbidden behaviors: ready")
    print("- recap-ingestion source artifact materializer gate: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"- recap-ingestion source artifact materializer gate: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
