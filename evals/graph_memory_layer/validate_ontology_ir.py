"""No-LLM shape validator for the synthetic Graph Memory Ontology IR bundle."""
from __future__ import annotations

import json
from pathlib import Path

from src.graph_memory.ontology_ir import GraphBundle

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_minimal_bundle.json"


def main() -> int:
    print("Graph Memory ontology IR validation")
    if not BUNDLE.is_file():
        print("- valid example bundle: missing")
        return 1
    bundle = GraphBundle.from_dict(json.loads(BUNDLE.read_text(encoding="utf-8")))
    print("- valid example bundle: found")
    if bundle.taxonomy_registry_version != "0.1":
        print(f"- taxonomy_registry_version: blocked ({bundle.taxonomy_registry_version})")
        return 1
    print("- ontology IR shape: ready")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
