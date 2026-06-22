from __future__ import annotations

import json

from evals.graph_memory_layer.build_recap_ingestion_projection_payload_fixture import FIXTURE_PATH


def _status(value: object) -> str:
    return "ready" if value is False else "blocked"


def main() -> int:
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    units = fixture["payload_units"]
    source_refs = {unit["source_ref_id"] for unit in units}
    families = {unit["admitted_artifact_id"] for unit in units}
    diagnostics = fixture["diagnostics"]
    print("# Recap-Ingestion Projection Payload Fixture Report\n")
    print("## Summary\n")
    print("| Metric | Count |")
    print("|---|---:|")
    print(f"| Payload units | {len(units)} |")
    print(f"| Source refs | {len(source_refs)} |")
    print(f"| Artifact families | {len(families)} |")
    print(f"| Diagnostics | {len(diagnostics)} |")
    print("\n## Payload Units\n")
    print("| Payload Unit | Artifact | Projection Kind | Evidence | Canon | Lifecycle |")
    print("|---|---|---|---|---|---|")
    for unit in units:
        semantic = unit["semantic_state"]
        print(f"| `{unit['payload_unit_id']}` | {unit['admitted_artifact_id']} | {unit['projection_kind']} | {semantic['evidence_role']} | {semantic['canon_state']} | {semantic['lifecycle_state']} |")
    print("\n## Safety\n")
    print("| Check | Status |")
    print("|---|---|")
    for key, value in diagnostics.items():
        print(f"| {key} | {_status(value)} |")
    print("\n## Boundary Statement\n")
    print("This is a diagnostic fixture only.")
    print("It is not a production adapter payload.")
    print("It does not connect `/plan`.")
    print("It does not connect Agent Interaction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
