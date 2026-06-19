"""No-LLM validator for the synthetic Graph Memory taxonomy registry."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
REQUIRED = {"validation_severity", "source_kind", "source_layer", "entity_kind", "evidence_role", "authority_state", "visibility_state", "lifecycle_state", "relationship_predicate_family"}


def main() -> int:
    print("Graph Memory taxonomy registry validation")
    if not REGISTRY.is_file():
        print("- taxonomy registry: missing")
        return 1
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    vocabularies = data.get("vocabularies", {})
    missing = sorted(REQUIRED - set(vocabularies))
    print("- taxonomy registry: found")
    print(f"- taxonomy_registry_version: {data.get('taxonomy_registry_version')}")
    if data.get("taxonomy_registry_version") != "0.1" or missing:
        for item in missing:
            print(f"  - missing vocabulary: {item}")
        return 1
    print("- taxonomy registry: ready")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
