from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer import DEFAULT_INPUTS
from src.graph_memory.recap_ingestion_materialize import (
    CREATED_BY,
    INPUT_MODE,
    SCHEMA,
    SOURCE_FAMILY,
    VERSION,
    materialize_recap_ingestion_source_artifacts,
    recap_ingestion_materialization_to_dict,
    RecapIngestionMaterializerInput,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_family_gate.json"
MATERIALIZER_GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_artifact_materializer_gate.json"
ADAPTER_FIELDS = {"payload_kind", "source_unit_projection", "projection_card", "surface_owned_projection_kind", "plan_chip", "agent_interaction_payload"}
FORBIDDEN_UNIT_PARTS = ("entity_fact", "relationship_fact", "alias", "promotion", "identity_merge")
RAW_INTERNALS = ("_normalized/", "_breadcrumbed/", ".records_meta.jsonl", "/workspace/", "/home/", "/mnt/", "C:\\")
ABSOLUTE_PATH_TOKENS = ("/workspace/", "/home/", "/mnt/", "C:\\")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    _require(path.is_file(), f"{label} missing")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _require(isinstance(data, dict), f"{label} must be JSON object")
    return data


def _contains_key(obj: Any, keys: set[str]) -> bool:
    if isinstance(obj, dict):
        return any(key in keys or _contains_key(value, keys) for key, value in obj.items())
    if isinstance(obj, list):
        return any(_contains_key(item, keys) for item in obj)
    return False


def main() -> int:
    print("Graph Memory recap-ingestion source artifact materializer validation")
    family_gate = _load_json(FAMILY_GATE_PATH, "source-family gate")
    print("- source-family gate: found")
    materializer_gate = _load_json(MATERIALIZER_GATE_PATH, "materializer gate")
    print("- materializer gate: found")
    for path in DEFAULT_INPUTS.values():
        _require(path.is_file(), f"fixture missing: {path.name}")
    print("- explicit input fixtures: found")
    inputs = [RecapIngestionMaterializerInput(artifact_id, path) for artifact_id, path in DEFAULT_INPUTS.items()]
    materialization = materialize_recap_ingestion_source_artifacts(inputs)
    data = recap_ingestion_materialization_to_dict(materialization)
    print("- materializer: ready")
    _require(data["schema"] == SCHEMA and data["version"] == VERSION, "bad schema/version")
    _require(data["source_family"] == SOURCE_FAMILY and data["created_by"] == CREATED_BY and data["input_mode"] == INPUT_MODE, "bad identity fields")
    print(f"- materialization schema: {SCHEMA}")
    family_by_id = {artifact["id"]: artifact for artifact in family_gate["admitted_artifacts"]}
    gate_by_id = {artifact["admitted_artifact_id"]: artifact for artifact in materializer_gate["allowed_input_artifacts"]}
    artifact_by_id = {artifact["admitted_artifact_id"]: artifact for artifact in data["artifacts"]}
    _require(set(DEFAULT_INPUTS) == set(artifact_by_id), "not all admitted artifacts materialized")
    print("- admitted artifacts: materialized")
    for artifact_id, artifact in artifact_by_id.items():
        family = family_by_id[artifact_id]
        gate = gate_by_id[artifact_id]
        for field in ("canon_state", "lifecycle_state", "evidence_role", "authority_state", "visibility_state"):
            _require(artifact[field] == family[f"default_{field}"] == gate[f"default_{field}"], f"{artifact_id} {field} mismatch")
    print("- semantic defaults: ready")
    anchors_by_artifact = {}
    for anchor in data["anchors"]:
        anchors_by_artifact.setdefault(anchor["source_artifact_id"], []).append(anchor)
    units_by_artifact = {}
    anchor_ids = {anchor["source_anchor_id"] for anchor in data["anchors"]}
    source_ref_ids = []
    for unit in data["units"]:
        units_by_artifact.setdefault(unit["source_artifact_id"], []).append(unit)
        _require(unit["source_anchor_id"] in anchor_ids, "unit points outside local anchors")
        _require(unit.get("source_ref"), "unit missing source_ref")
        source_ref_id = unit["source_ref"].get("source_ref_id")
        _require(isinstance(source_ref_id, str) and source_ref_id, "unit missing source_ref_id")
        _require(source_ref_id.startswith("source-ref:"), "source_ref_id prefix mismatch")
        _require(not any(token in source_ref_id for token in ABSOLUTE_PATH_TOKENS), "source_ref_id leaked absolute path")
        source_ref_ids.append(source_ref_id)
        _require(unit.get("provenance"), "unit missing provenance")
        for provenance in unit["provenance"]:
            _require(provenance.get("source_ref_id") == source_ref_id, "provenance source_ref_id mismatch")
        _require(unit.get("canon_state"), "unit missing canon_state")
        _require(unit.get("display_summary") and unit["display_summary"] not in ("source_evidence", "narrative_evidence"), "display_summary treated as evidence")
        _require(not any(part in unit["unit_kind"] for part in FORBIDDEN_UNIT_PARTS), "forbidden unit kind emitted")
    _require(len(source_ref_ids) == len(set(source_ref_ids)), "source_ref_id values are not unique")
    repeat = recap_ingestion_materialization_to_dict(materialize_recap_ingestion_source_artifacts(inputs))
    repeat_ids = [unit["source_ref"]["source_ref_id"] for unit in repeat["units"]]
    _require(source_ref_ids == repeat_ids, "source_ref_id values are not deterministic")
    for artifact in data["artifacts"]:
        _require(anchors_by_artifact.get(artifact["artifact_id"]), "artifact missing anchor")
        _require(units_by_artifact.get(artifact["artifact_id"]), "artifact missing unit")
    print("- anchors: ready")
    print("- source units: ready")
    print("- source refs: ready")
    print("- source ref ids: ready")
    print("- provenance: ready")
    print("- provenance source-ref linkage: ready")
    output = json.dumps(data, sort_keys=True)
    _require('"full_text"' not in output and '"text"' not in output and '"content"' not in output, "full text field emitted")
    for path in DEFAULT_INPUTS.values():
        raw = path.read_text(encoding="utf-8").strip()
        _require(raw not in output, f"raw file contents leaked: {path.name}")
    _require(not any(token in output for token in RAW_INTERNALS), "raw ingestion internals or absolute path leaked")
    _require(not _contains_key(data, ADAPTER_FIELDS), "adapter payload fields emitted")
    print("- explicit input policy: preserved")
    print("- full text leakage: absent")
    print("- raw ingestion internals: absent")
    print("- adapter payloads: absent")
    _require(artifact_by_id["normalized_recap_markdown"]["evidence_role"] == "source_evidence", "normalized recap not source evidence")
    _require(artifact_by_id["breadcrumbed_recap_markdown"]["evidence_role"] == "navigation_hint", "breadcrumbed recap not navigation hint")
    _require(artifact_by_id["frontmatter_seed_markdown"]["canon_state"] != "played_canon", "frontmatter seed is played canon")
    _require(artifact_by_id["corpus_impact_proof"]["canon_state"] == "diagnostic_only", "proof not diagnostic-only")
    print("- recap-ingestion source artifact materializer: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError, ValueError) as exc:
        print(f"- recap-ingestion source artifact materializer: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
