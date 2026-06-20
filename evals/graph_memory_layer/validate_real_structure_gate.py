from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "real_structure_materialization_gate.json"
REQUIRED_GLOBAL_CONSTRAINTS = {
    "no_production_retrieval_changes",
    "no_corpus_mutation",
    "no_llm_calls",
    "no_entity_extraction",
    "no_alias_resolution",
    "no_relationship_inference",
    "no_promoted_records",
    "diagnostic_only_default",
    "must_run_validation_rules",
    "must_emit_report",
}
REQUIRED_ADMITTED_FIELDS = {
    "allowed_read_surfaces",
    "forbidden_read_surfaces",
    "allowed_graph_record_shapes",
    "forbidden_graph_record_shapes",
    "required_record_defaults",
    "required_reports",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_manifest() -> dict[str, Any]:
    _require(GATE_MANIFEST_PATH.is_file(), "gate manifest missing")
    with GATE_MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _require(isinstance(data, dict), "gate manifest must be a JSON object")
    return data


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def main() -> int:
    print("Graph Memory real-structure materialization gate validation")
    manifest = _load_manifest()
    print("- gate manifest: found")

    _require(manifest.get("version") == "0.1", "version must be 0.1")
    print("- version: 0.1")
    _require(manifest.get("status") == "active_gate", "status must be active_gate")
    print("- status: active_gate")

    gate_decision = manifest.get("gate_decision")
    _require(isinstance(gate_decision, dict), "gate_decision must be an object")
    admitted_source_family = gate_decision.get("admitted_source_family")
    _require(isinstance(admitted_source_family, str) and admitted_source_family.strip(), "admitted source family is required")
    print(f"- admitted source family: {admitted_source_family}")

    candidates = manifest.get("candidate_source_families")
    _require(isinstance(candidates, list) and candidates, "candidate_source_families must be a non-empty list")
    admitted_by_status = [candidate for candidate in candidates if candidate.get("status") == "admitted_next"]
    admitted_by_flag = [candidate for candidate in candidates if candidate.get("admitted_for_next_materializer") is True]
    _require(len(admitted_by_status) == 1, "exactly one candidate must have status admitted_next")
    _require(len(admitted_by_flag) == 1, "exactly one candidate must be admitted for next materializer")
    admitted = admitted_by_status[0]
    _require(admitted is admitted_by_flag[0], "admitted status and flag must identify the same candidate")
    _require(admitted.get("id") == admitted_source_family, "admitted candidate ID must match gate decision")
    print("- admitted candidates: 1")

    constraints = manifest.get("global_constraints")
    _require(isinstance(constraints, dict), "global_constraints must be an object")
    missing_constraints = sorted(name for name in REQUIRED_GLOBAL_CONSTRAINTS if constraints.get(name) is not True)
    _require(not missing_constraints, f"missing or false global constraints: {', '.join(missing_constraints)}")
    print("- global constraints: ready")

    missing_admitted_fields = sorted(field for field in REQUIRED_ADMITTED_FIELDS if field not in admitted)
    _require(not missing_admitted_fields, f"admitted candidate missing fields: {', '.join(missing_admitted_fields)}")
    for field in [
        "allowed_read_surfaces",
        "forbidden_read_surfaces",
        "allowed_graph_record_shapes",
        "forbidden_graph_record_shapes",
        "required_reports",
    ]:
        _require(_nonempty_list(admitted.get(field)), f"admitted candidate {field} must be a non-empty string list")
    defaults = admitted.get("required_record_defaults")
    _require(isinstance(defaults, dict) and defaults, "admitted candidate required_record_defaults must be non-empty")
    _require(defaults.get("lifecycle_state") == "candidate", "admitted records must default to candidate lifecycle")
    _require(defaults.get("visibility_state") == "internal_diagnostic", "admitted records must default to internal diagnostic visibility")
    _require(defaults.get("evidence_role_default") == "diagnostic_only", "admitted records must default to diagnostic-only evidence")
    print("- admitted source constraints: ready")

    for candidate in candidates:
        status = candidate.get("status")
        if status in {"blocked", "deferred"}:
            _require(candidate.get("admitted_for_next_materializer") is False, f"{candidate.get('id')} is {status} but admitted")

    print("- real-structure gate: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"- real-structure gate: blocked ({exc})")
        sys.exit(1)
