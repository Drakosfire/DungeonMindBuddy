from __future__ import annotations

import json
import re
import sys
from typing import Any

from evals.graph_memory_layer.build_recap_ingestion_projection_payload_fixture import FIXTURE_PATH, SCHEMA, VERSION
from evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer import DEFAULT_INPUTS
from src.graph_memory.recap_ingestion_materialize import SOURCE_FAMILY, RecapIngestionMaterializerInput, materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import analyze_recap_ingestion_materializer_output
from src.graph_memory.recap_ingestion_projection_readiness import assess_recap_ingestion_projection_readiness

EXPECTED_ARTIFACTS = {"normalized_recap_markdown", "breadcrumbed_recap_markdown", "frontmatter_seed_markdown", "session_memory_jsonl_meta", "corpus_impact_proof"}
REQUIRED_FIELDS = {"payload_unit_id", "source_unit_id", "source_ref_id", "admitted_artifact_id", "artifact_kind", "projection_kind", "display_label", "display_summary", "semantic_state", "source_handle", "provenance", "safety"}
SEMANTIC_FIELDS = {"canon_state", "lifecycle_state", "evidence_role", "authority_state", "visibility_state"}
FULL_TEXT_FIELDS = {"full_text", "text", "content", "raw_content", "raw_text", "file_contents"}
RAW_PATH_FIELDS = {"path", "input_path", "raw_path", "file_path", "internal_path"}
FORBIDDEN_FIELDS = FULL_TEXT_FIELDS | RAW_PATH_FIELDS | {"payload_kind", "source_unit_projection", "projection_card", "plan_chip", "plan_card", "plan_items", "agent_payload", "agent_interaction", "surface_owned_projection_kind", "reference_chip", "runtime_ui_payload", "ui_payload", "entity", "entities", "alias", "aliases", "relationship", "relationships", "fact", "facts", "canon_promotion", "fact_promotion", "identity_merge"}
ABSOLUTE_PATH_RE = re.compile(r"(/workspace/|/home/|/mnt/|\b[A-Za-z]:\\)")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _walk_keys(obj: Any) -> list[str]:
    if isinstance(obj, dict):
        return [str(k) for k in obj] + [key for value in obj.values() for key in _walk_keys(value)]
    if isinstance(obj, list):
        return [key for value in obj for key in _walk_keys(value)]
    return []


def _load_fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _require(isinstance(data, dict), "fixture must be a JSON object")
    return data


def validate_fixture() -> dict[str, Any]:
    materialization = materialize_recap_ingestion_source_artifacts([RecapIngestionMaterializerInput(k, v) for k, v in DEFAULT_INPUTS.items()])
    materializer_report = analyze_recap_ingestion_materializer_output(materialization)
    readiness = assess_recap_ingestion_projection_readiness(materialization, materializer_report)
    _require(readiness.readiness_status == "ready", "projection-readiness must be ready")
    fixture = _load_fixture()
    _require(fixture.get("schema") == SCHEMA and fixture.get("version") == VERSION, "bad schema/version")
    _require(fixture.get("source_family") == SOURCE_FAMILY, "bad source family")
    units = fixture.get("payload_units")
    _require(isinstance(units, list) and len(units) == 5, "payload_units must contain five entries")
    _require({unit.get("admitted_artifact_id") for unit in units} == EXPECTED_ARTIFACTS, "artifact coverage mismatch")
    source_ref_ids = {str(unit.source_ref.get("source_ref_id")) for unit in materialization.units}
    for unit in units:
        _require(isinstance(unit, dict), "payload unit must be object")
        _require(REQUIRED_FIELDS.issubset(unit), "payload unit missing required fields")
        _require(unit["source_ref_id"] in source_ref_ids, "payload source_ref_id missing in materializer output")
        _require(unit["provenance"].get("source_ref_id") == unit["source_ref_id"], "provenance source_ref_id mismatch")
        _require(SEMANTIC_FIELDS.issubset(unit["semantic_state"]), "semantic envelope missing fields")
        _require(unit["display_summary"] and unit["safety"].get("display_summary_is_evidence") is False, "display summary boundary failed")
        handle = unit["source_handle"]
        _require(str(handle.get("handle_id", "")).startswith("opaque-source-handle:"), "source handle is not opaque")
        _require(handle.get("scheme") == "explicit-input", "source handle scheme mismatch")
        _require(not ABSOLUTE_PATH_RE.search(json.dumps(handle, sort_keys=True)), "source handle leaks absolute path")
        for flag in ("raw_text_included", "absolute_path_included", "adapter_payload", "plan_payload", "agent_interaction_payload", "runtime_payload"):
            _require(unit["safety"].get(flag) is False, f"safety flag must be false: {flag}")
    serialized = json.dumps(fixture, sort_keys=True)
    for path in DEFAULT_INPUTS.values():
        _require(path.read_text(encoding="utf-8").strip() not in serialized, f"raw fixture contents leaked: {path.name}")
    _require(not ABSOLUTE_PATH_RE.search(serialized), "absolute path leaked")
    _require(not (set(_walk_keys(fixture)) & FORBIDDEN_FIELDS), "forbidden payload/internal fields leaked")
    diagnostics = fixture.get("diagnostics", {})
    for flag in ("production_adapter_payload", "plan_payload", "agent_interaction_payload", "runtime_payload", "raw_text_included", "absolute_paths_included"):
        _require(diagnostics.get(flag) is False, f"diagnostic flag must be false: {flag}")
    return fixture


def main() -> int:
    print("Graph Memory recap-ingestion projection payload fixture validation")
    materialization = materialize_recap_ingestion_source_artifacts([RecapIngestionMaterializerInput(k, v) for k, v in DEFAULT_INPUTS.items()])
    print("- materializer: ready")
    materializer_report = analyze_recap_ingestion_materializer_output(materialization)
    print("- materializer report: ready")
    readiness = assess_recap_ingestion_projection_readiness(materialization, materializer_report)
    _require(readiness.readiness_status == "ready", "projection-readiness must be ready")
    print("- projection-readiness: ready")
    _require(FIXTURE_PATH.is_file(), "projection payload fixture missing")
    print("- projection payload fixture: found")
    fixture = validate_fixture()
    print(f"- schema: {fixture['schema']}")
    for label in ("artifact coverage", "payload units", "source_ref_id linkage", "provenance linkage", "semantic state envelope", "opaque source handles", "display summary boundary", "no full text leakage", "no absolute path leakage", "no adapter/runtime payload leakage"):
        print(f"- {label}: ready")
    print("- recap-ingestion projection payload fixture: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError, ValueError) as exc:
        print(f"- recap-ingestion projection payload fixture: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
