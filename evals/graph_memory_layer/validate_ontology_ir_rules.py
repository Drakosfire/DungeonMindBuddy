"""No-LLM validation CLI for Graph Memory Ontology IR policy rules."""
from __future__ import annotations

import json
from pathlib import Path

from src.graph_memory.ontology_ir import GraphBundle
from src.graph_memory.validation_rules import load_taxonomy_registry, validate_bundle_against_taxonomy

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
VALID_BUNDLE = ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_minimal_bundle.json"
INVALID_BUNDLE = ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_invalid_bundle.json"


def _load_bundle(path: Path) -> GraphBundle:
    return GraphBundle.from_dict(json.loads(path.read_text(encoding="utf-8")))


def main() -> int:
    print("Graph Memory ontology IR rule validation")
    if not REGISTRY.is_file():
        print("- taxonomy registry: missing")
        return 1
    registry = load_taxonomy_registry(REGISTRY)
    valid = validate_bundle_against_taxonomy(_load_bundle(VALID_BUNDLE), registry)
    invalid = validate_bundle_against_taxonomy(_load_bundle(INVALID_BUNDLE), registry)
    print("- taxonomy registry: found")
    print(f"- valid example bundle: {'ready' if valid.ok else 'blocked'}")
    print(f"- invalid example bundle: {'rejected' if not invalid.ok else 'not rejected'}")
    print(f"- validation issues observed: {len(invalid.issues)}")
    if valid.ok and not invalid.ok:
        print("- ontology IR rules: ready")
        return 0
    print("- ontology IR rules: blocked")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
