from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer import DEFAULT_INPUTS
from src.graph_memory.recap_ingestion_materialize import SCHEMA as MATERIALIZER_SCHEMA, SOURCE_FAMILY, RecapIngestionMaterializerInput, RecapIngestionMaterialization, materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import analyze_recap_ingestion_materializer_output
from src.graph_memory.recap_ingestion_projection_readiness import READINESS_SCHEMA, assess_recap_ingestion_projection_readiness

SCHEMA = "dmb_recap_ingestion_projection_payload_fixture_v0"
VERSION = "0.1"
FIXTURE_ID = "example:recap-ingestion-projection-payload:minimal"
CREATED_BY = "recap_ingestion_projection_payload_fixture_v0"
FIXTURE_PATH = Path(__file__).resolve().parent / "examples" / "recap_ingestion_projection_payload_minimal.json"


def _digest_from_id(identifier: str) -> str:
    return identifier.rsplit(":", 1)[-1]


def _artifact_kind_by_id(materialization: RecapIngestionMaterialization) -> dict[str, str]:
    return {artifact.admitted_artifact_id: artifact.artifact_kind for artifact in materialization.artifacts}


def build_projection_payload_fixture() -> dict[str, Any]:
    materialization = materialize_recap_ingestion_source_artifacts([RecapIngestionMaterializerInput(k, v) for k, v in DEFAULT_INPUTS.items()])
    materializer_report = analyze_recap_ingestion_materializer_output(materialization)
    readiness = assess_recap_ingestion_projection_readiness(materialization, materializer_report)
    if readiness.readiness_status != "ready":
        raise ValueError(f"recap-ingestion projection readiness must be ready, got {readiness.readiness_status}")

    artifact_kind = _artifact_kind_by_id(materialization)
    payload_units: list[dict[str, Any]] = []
    for unit in materialization.units:
        source_ref_id = str(unit.source_ref["source_ref_id"])
        admitted_artifact_id = str(unit.provenance[0]["admitted_artifact_id"])
        digest = _digest_from_id(source_ref_id)
        locator = unit.source_ref.get("locator", {})
        handle_value = "explicit-input://recap-ingestion/" + admitted_artifact_id + "/opaque-" + digest
        if isinstance(locator, dict) and locator.get("scheme") == "explicit-input":
            handle_value = f"explicit-input://recap-ingestion/{admitted_artifact_id}/opaque-{digest}"
        payload_units.append(
            {
                "payload_unit_id": f"projection-unit:{admitted_artifact_id}:{digest}",
                "source_unit_id": unit.source_unit_id,
                "source_ref_id": source_ref_id,
                "admitted_artifact_id": admitted_artifact_id,
                "artifact_kind": artifact_kind[admitted_artifact_id],
                "projection_kind": "source_reference",
                "display_label": f"{artifact_kind[admitted_artifact_id]} explicit input",
                "display_summary": unit.display_summary,
                "semantic_state": {
                    "canon_state": unit.canon_state,
                    "lifecycle_state": unit.lifecycle_state,
                    "evidence_role": unit.evidence_role,
                    "authority_state": unit.authority_state,
                    "visibility_state": unit.visibility_state,
                },
                "source_handle": {
                    "handle_id": f"opaque-source-handle:{digest}",
                    "scheme": "explicit-input",
                    "value": handle_value,
                },
                "provenance": {
                    "source_ref_id": source_ref_id,
                    "created_by": str(unit.provenance[0]["created_by"]),
                    "input_mode": str(unit.provenance[0]["input_mode"]),
                },
                "safety": {
                    "display_summary_is_evidence": False,
                    "raw_text_included": False,
                    "absolute_path_included": False,
                    "adapter_payload": False,
                    "plan_payload": False,
                    "agent_interaction_payload": False,
                    "runtime_payload": False,
                },
            }
        )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "fixture_id": FIXTURE_ID,
        "source_family": SOURCE_FAMILY,
        "created_by": CREATED_BY,
        "projection_mode": "diagnostic_fixture_only",
        "projection_status": "fixture_ready",
        "source": {
            "materializer_schema": MATERIALIZER_SCHEMA,
            "readiness_schema": READINESS_SCHEMA,
            "requires_source_ref_id": True,
            "requires_provenance_source_ref_linkage": True,
        },
        "payload_units": payload_units,
        "diagnostics": {
            "display_summary_is_evidence": False,
            "production_adapter_payload": False,
            "plan_payload": False,
            "agent_interaction_payload": False,
            "runtime_payload": False,
            "raw_text_included": False,
            "absolute_paths_included": False,
        },
    }


def main() -> int:
    print(json.dumps(build_projection_payload_fixture(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
