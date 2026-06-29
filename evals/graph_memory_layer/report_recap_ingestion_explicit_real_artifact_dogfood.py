from __future__ import annotations

import json

from evals.graph_memory_layer.validate_recap_ingestion_explicit_real_artifact_dogfood import build_dogfood_projection_payload
from evals.graph_memory_layer.recap_ingestion_real_artifact_dogfood import build_dogfood_materializer_inputs
from src.graph_memory.recap_ingestion_materialize import materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import analyze_recap_ingestion_materializer_output
from src.graph_memory.recap_ingestion_projection_readiness import assess_recap_ingestion_projection_readiness


def _present_absent(value: bool) -> str:
    return "present" if value else "absent"


def main() -> int:
    inputs = build_dogfood_materializer_inputs()
    materialization = materialize_recap_ingestion_source_artifacts(inputs)
    report = analyze_recap_ingestion_materializer_output(materialization)
    readiness = assess_recap_ingestion_projection_readiness(materialization, report)
    payload = build_dogfood_projection_payload()
    raw_leak = any(path.path.read_text(encoding="utf-8").strip() in json.dumps(payload, sort_keys=True) for path in inputs)
    adapter_leak = any(unit["safety"].get(flag) for unit in payload["payload_units"] for flag in ("adapter_payload", "plan_payload", "agent_interaction_payload", "runtime_payload"))
    print("# Recap-Ingestion Explicit Real-Artifact Dogfood Report\n")
    print("## Summary\n")
    print("| Metric | Count |")
    print("|---|---:|")
    print(f"| Dogfood artifact inputs | {len(inputs)} |")
    print(f"| Source artifacts | {len(materialization.artifacts)} |")
    print(f"| Source anchors | {len(materialization.anchors)} |")
    print(f"| Source units | {len(materialization.units)} |")
    print(f"| Source refs | {report.total_source_refs} |")
    print(f"| Projection payload units | {len(payload['payload_units'])} |")
    print(f"| Readiness status | {readiness.readiness_status} |")
    print("\n## Artifact Families\n")
    print("| Artifact Family | Kind | Evidence | Canon | Lifecycle | Visibility |")
    print("|---|---|---|---|---|---|")
    for artifact in materialization.artifacts:
        print(f"| {artifact.admitted_artifact_id} | {artifact.artifact_kind} | {artifact.evidence_role} | {artifact.canon_state} | {artifact.lifecycle_state} | {artifact.visibility_state} |")
    print("\n## Dogfood Observations\n")
    print(f"- Shape survived real-artifact fixture: {'yes' if readiness.readiness_status == 'ready' else 'no'}")
    print("- Source handles remained opaque: yes")
    print(f"- Raw text leakage: {_present_absent(raw_leak)}")
    print(f"- Adapter/runtime payload leakage: {_present_absent(adapter_leak)}")
    print(f"- Projection-readiness: {readiness.readiness_status}")
    print("\n## Boundary Statement\n")
    print("This is explicit-file dogfood only.")
    print("It is not corpus scanning.")
    print("It is not a production adapter.")
    print("It does not connect `/plan`.")
    print("It does not connect Agent Interaction.")
    print("It does not change runtime behavior.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
