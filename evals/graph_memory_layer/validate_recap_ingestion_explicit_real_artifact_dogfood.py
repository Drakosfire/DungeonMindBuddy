from __future__ import annotations

import json
import re
import sys
from typing import Any

from evals.graph_memory_layer.build_recap_ingestion_projection_payload_fixture import build_projection_payload_fixture_from_materialization
from evals.graph_memory_layer.recap_ingestion_real_artifact_dogfood import FIXTURE_ID, build_dogfood_materializer_inputs, load_dogfood_manifest, validate_dogfood_manifest
from src.graph_memory.recap_ingestion_materialize import materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import KNOWN_ARTIFACT_FAMILIES, analyze_recap_ingestion_materializer_output, recap_ingestion_materializer_report_to_dict
from src.graph_memory.recap_ingestion_projection_readiness import assess_recap_ingestion_projection_readiness, recap_ingestion_projection_readiness_to_dict

ABSOLUTE_PATH_RE = re.compile(r"(/workspace/|/home/|/mnt/|\b[A-Za-z]:\\)")
FORBIDDEN_FIELDS = {"full_text", "text", "content", "raw_content", "raw_text", "file_contents", "path", "input_path", "raw_path", "file_path", "internal_path", "payload_kind", "source_unit_projection", "projection_card", "plan_chip", "plan_card", "plan_items", "agent_payload", "agent_interaction", "runtime_ui_payload", "ui_payload", "entity", "entities", "alias", "aliases", "relationship", "relationships", "fact", "facts", "canon_promotion", "fact_promotion", "identity_merge"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _walk_keys(obj: Any) -> list[str]:
    if isinstance(obj, dict):
        return [str(k) for k in obj] + [key for value in obj.values() for key in _walk_keys(value)]
    if isinstance(obj, list):
        return [key for value in obj for key in _walk_keys(value)]
    return []


def build_dogfood_projection_payload() -> dict[str, Any]:
    materialization = materialize_recap_ingestion_source_artifacts(build_dogfood_materializer_inputs())
    return build_projection_payload_fixture_from_materialization(materialization, fixture_id=FIXTURE_ID, created_by="recap_ingestion_explicit_real_artifact_dogfood_v0")


def validate_dogfood() -> dict[str, Any]:
    manifest = load_dogfood_manifest()
    validate_dogfood_manifest(manifest)
    inputs = build_dogfood_materializer_inputs()
    _require(len(inputs) == 5 and {i.admitted_artifact_id for i in inputs} == KNOWN_ARTIFACT_FAMILIES, "explicit inputs must cover all five families")
    materialization = materialize_recap_ingestion_source_artifacts(inputs)
    _require(len(materialization.artifacts) == len(materialization.anchors) == len(materialization.units) == 5, "materializer must emit five artifacts/anchors/units")
    _require(materialization.diagnostics, "materializer diagnostics missing")
    report = analyze_recap_ingestion_materializer_output(materialization)
    readiness = assess_recap_ingestion_projection_readiness(materialization, report)
    _require(readiness.readiness_status == "ready", "projection-readiness must be ready")
    payload = build_projection_payload_fixture_from_materialization(materialization, fixture_id=FIXTURE_ID, created_by="recap_ingestion_explicit_real_artifact_dogfood_v0")
    _require(len(payload.get("payload_units", [])) == 5, "projection payload must contain five units")
    for unit in materialization.units:
        source_ref_id = unit.source_ref.get("source_ref_id")
        _require(bool(source_ref_id), "source ref missing source_ref_id")
        _require(all(p.get("source_ref_id") == source_ref_id for p in unit.provenance), "provenance linkage mismatch")
    serialized = json.dumps({"report": recap_ingestion_materializer_report_to_dict(report), "readiness": recap_ingestion_projection_readiness_to_dict(readiness), "payload": payload}, sort_keys=True)
    for explicit_input in inputs:
        _require(explicit_input.path.read_text(encoding="utf-8").strip() not in serialized, f"full raw input leaked: {explicit_input.path.name}")
    _require(not ABSOLUTE_PATH_RE.search(serialized), "absolute path leaked")
    _require(not (set(_walk_keys(payload)) & FORBIDDEN_FIELDS), "forbidden payload fields leaked")
    return payload


def main() -> int:
    print("Graph Memory recap-ingestion explicit real-artifact dogfood validation")
    validate_dogfood_manifest(load_dogfood_manifest()); print("- dogfood manifest: ready")
    inputs = build_dogfood_materializer_inputs(); print("- explicit inputs: ready")
    materialization = materialize_recap_ingestion_source_artifacts(inputs); print("- materializer: ready")
    report = analyze_recap_ingestion_materializer_output(materialization); print("- materializer report: ready")
    readiness = assess_recap_ingestion_projection_readiness(materialization, report)
    _require(readiness.readiness_status == "ready", "projection-readiness must be ready"); print("- projection-readiness: ready")
    validate_dogfood()
    for label in ("projection payload shape", "source_ref_id linkage", "provenance linkage", "semantic state envelope", "display summary boundary", "no full text leakage", "no absolute path leakage", "no adapter/runtime payload leakage"):
        print(f"- {label}: ready")
    print("- recap-ingestion explicit real-artifact dogfood: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, ValueError, json.JSONDecodeError) as exc:
        print(f"- recap-ingestion explicit real-artifact dogfood: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
