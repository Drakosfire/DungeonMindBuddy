from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_family_gate.json"
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "recap_ingestion_source_artifacts_minimal.json"
EXPECTED_SCHEMA = "dmb_recap_ingestion_source_artifact_fixture_v0"
EXPECTED_ARTIFACT_IDS = {
    "normalized_recap_markdown",
    "breadcrumbed_recap_markdown",
    "frontmatter_seed_markdown",
    "session_memory_jsonl_meta",
    "corpus_impact_proof",
}
SEMANTIC_FIELDS = ("canon_state", "lifecycle_state", "evidence_role", "authority_state", "visibility_state")
REQUIRED_ARTIFACT_FIELDS = {
    "artifact_id", "admitted_artifact_id", "artifact_kind", "source_layer", "label",
    *SEMANTIC_FIELDS, "locator", "anchors", "units", "forbidden_interpretations",
}
REQUIRED_ANCHOR_FIELDS = {"source_anchor_id", "anchor_kind", "label", "locator"}
REQUIRED_UNIT_FIELDS = {
    "source_unit_id", "source_anchor_id", "unit_kind", "label", "display_summary",
    "source_ref", "provenance", *SEMANTIC_FIELDS,
}
FULL_TEXT_FIELDS = {"lexical_plain", "full_text", "markdown_body", "raw_text", "recap_text"}
RAW_INTERNAL_FIELD_NAMES = {"_normalized", "_breadcrumbed", ".records_meta.jsonl", "corpus_impact"}
FORBIDDEN_UNIT_KINDS = {"entity_fact", "relationship_fact", "alias_merge", "promotion_record"}
ABSOLUTE_PATH_RE = re.compile(r"(^|[\s:])(/(?:home|workspace|tmp|var|Users|mnt|etc)/|[A-Za-z]:\\)")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    _require(path.is_file(), f"{label} missing")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _require(isinstance(data, dict), f"{label} must be a JSON object")
    return data


def _gate_artifacts(gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = gate.get("admitted_artifacts")
    _require(isinstance(artifacts, list), "gate admitted_artifacts must be a list")
    return {artifact["id"]: artifact for artifact in artifacts if isinstance(artifact, dict) and isinstance(artifact.get("id"), str)}


def _walk(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _assert_no_unsafe_fields(fixture: dict[str, Any]) -> None:
    for key, value in _walk(fixture):
        _require(key not in FULL_TEXT_FIELDS, f"full text field present: {key}")
        _require(key not in RAW_INTERNAL_FIELD_NAMES, f"raw ingestion internal semantic field present: {key}")
        if isinstance(value, str):
            _require(not ABSOLUTE_PATH_RE.search(value), f"absolute filesystem path present in {key}")
            _require("_normalized/" not in value and "_breadcrumbed/" not in value, f"raw ingestion path internals present in {key}")
            _require(".records_meta.jsonl" not in value, f"raw meta filename present in {key}")


def main() -> int:
    print("Graph Memory recap-ingestion source artifact fixture validation")
    gate = _load_json(GATE_PATH, "gate manifest")
    print("- gate manifest: found")
    fixture = _load_json(FIXTURE_PATH, "fixture")
    print("- fixture: found")

    _require(fixture.get("schema") == EXPECTED_SCHEMA, "bad fixture schema")
    print(f"- schema: {EXPECTED_SCHEMA}")
    _require(fixture.get("version") == "0.1", "version must be 0.1")
    _require(fixture.get("source_family") == "recap_ingestion_source_artifacts", "bad source family")

    gate_by_id = _gate_artifacts(gate)
    _require(EXPECTED_ARTIFACT_IDS.issubset(gate_by_id), "gate missing expected admitted artifacts")
    artifacts = fixture.get("artifacts")
    _require(isinstance(artifacts, list) and artifacts, "fixture artifacts must be a non-empty list")
    fixture_ids = {artifact.get("admitted_artifact_id") for artifact in artifacts if isinstance(artifact, dict)}
    _require(EXPECTED_ARTIFACT_IDS.issubset(fixture_ids), "fixture missing admitted artifact coverage")
    _require(fixture_ids.issubset(gate_by_id), "fixture references non-admitted artifact IDs")
    print("- admitted artifact coverage: ready")

    for artifact in artifacts:
        _require(isinstance(artifact, dict), "artifact must be an object")
        _require(REQUIRED_ARTIFACT_FIELDS.issubset(artifact), f"artifact missing required fields: {artifact.get('admitted_artifact_id')}")
        admitted_id = artifact["admitted_artifact_id"]
        gate_artifact = gate_by_id[admitted_id]
        _require(artifact["artifact_kind"] == gate_artifact["artifact_kind"], f"{admitted_id} artifact_kind mismatch")
        _require(artifact["source_layer"] == gate_artifact["source_layer"], f"{admitted_id} source_layer mismatch")
        for field in SEMANTIC_FIELDS:
            _require(artifact[field] == gate_artifact[f"default_{field}"], f"{admitted_id} {field} mismatch")
        _require(isinstance(artifact["anchors"], list) and artifact["anchors"], f"{admitted_id} anchors missing")
        _require(isinstance(artifact["units"], list) and artifact["units"], f"{admitted_id} units missing")
        anchor_ids = set()
        for anchor in artifact["anchors"]:
            _require(isinstance(anchor, dict) and REQUIRED_ANCHOR_FIELDS.issubset(anchor), f"{admitted_id} anchor missing required fields")
            _require(isinstance(anchor["locator"], dict) and anchor["locator"], f"{admitted_id} anchor locator missing")
            anchor_ids.add(anchor["source_anchor_id"])
        for unit in artifact["units"]:
            _require(isinstance(unit, dict) and REQUIRED_UNIT_FIELDS.issubset(unit), f"{admitted_id} unit missing required fields")
            _require(unit["source_anchor_id"] in anchor_ids, f"{admitted_id} unit anchor must be local")
            _require(unit["unit_kind"] not in FORBIDDEN_UNIT_KINDS, f"{admitted_id} forbidden unit_kind")
            source_ref = unit["source_ref"]
            _require(isinstance(source_ref, dict), f"{admitted_id} source_ref must be object")
            _require(source_ref.get("source_artifact_id") == artifact["artifact_id"], f"{admitted_id} source_ref artifact mismatch")
            _require(source_ref.get("source_anchor_id") == unit["source_anchor_id"], f"{admitted_id} source_ref anchor mismatch")
            _require(isinstance(unit["provenance"], list) and unit["provenance"], f"{admitted_id} provenance missing")
            _require(unit["display_summary"] and unit["display_summary"] != unit["evidence_role"], f"{admitted_id} display_summary is not evidence")
            for field in SEMANTIC_FIELDS:
                _require(unit[field] == artifact[field], f"{admitted_id} unit {field} must match artifact")
        _require(set(gate_artifact["forbidden_shapes"]).issubset(set(artifact["forbidden_interpretations"])), f"{admitted_id} forbidden interpretations mismatch")
    print("- artifact semantic defaults: ready")
    print("- anchors: ready")
    print("- source units: ready")
    print("- source refs: ready")
    print("- provenance: ready")

    by_id = {artifact["admitted_artifact_id"]: artifact for artifact in artifacts}
    _require(by_id["corpus_impact_proof"]["evidence_role"] == "diagnostic_only" and by_id["corpus_impact_proof"]["canon_state"] == "diagnostic_only", "corpus_impact_proof must be diagnostic-only")
    _require(by_id["frontmatter_seed_markdown"]["canon_state"] != "played_canon", "frontmatter seed must not be played canon")
    _require(by_id["breadcrumbed_recap_markdown"]["evidence_role"] == "navigation_hint" and by_id["breadcrumbed_recap_markdown"]["evidence_role"] != "source_evidence", "breadcrumbed recap must be navigation_hint")
    _require(FORBIDDEN_UNIT_KINDS.issubset(set(by_id["normalized_recap_markdown"]["forbidden_interpretations"])), "normalized recap must forbid extracted fact shapes")
    print("- forbidden interpretations: ready")

    _assert_no_unsafe_fields(fixture)
    print("- raw ingestion internals: absent")
    print("- recap-ingestion source artifact fixture: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"- recap-ingestion source artifact fixture: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
