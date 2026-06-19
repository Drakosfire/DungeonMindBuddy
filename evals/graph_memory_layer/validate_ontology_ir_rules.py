from __future__ import annotations

import json
import sys
from pathlib import Path

from src.graph_memory.ontology_ir import GraphBundle, GraphEdge, GraphNode, ValidationStatus, _require_mapping
from src.graph_memory.validation_rules import load_taxonomy_registry, validate_bundle_against_taxonomy

REPO_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
VALID_BUNDLE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_minimal_bundle.json"
INVALID_BUNDLE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_invalid_bundle.json"


def _load_bundle(path: Path, *, allow_missing_edge_endpoints: bool = False) -> GraphBundle:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not allow_missing_edge_endpoints:
        return GraphBundle.from_dict(data)
    nodes = [GraphNode.from_dict(_require_mapping(item, "node")) for item in data.get("nodes", [])]
    validation = [ValidationStatus.from_dict(_require_mapping(item, "validation")) for item in data.get("validation", [])]
    bundle = GraphBundle(
        bundle_id=data.get("bundle_id", ""),
        schema_version=data.get("schema_version", ""),
        taxonomy_registry_version=data.get("taxonomy_registry_version", ""),
        created_by=data.get("created_by", ""),
        description=data.get("description", ""),
        nodes=nodes,
        edges=[],
        validation=validation,
    )
    bundle.edges.extend(GraphEdge.from_dict(_require_mapping(item, "edge")) for item in data.get("edges", []))
    return bundle


def main() -> int:
    print("Graph Memory ontology IR rule validation")
    if not TAXONOMY_REGISTRY_PATH.is_file():
        print("- taxonomy registry: missing")
        return 1
    taxonomy_registry = load_taxonomy_registry(TAXONOMY_REGISTRY_PATH)
    print("- taxonomy registry: found")

    try:
        valid_bundle = _load_bundle(VALID_BUNDLE_PATH)
        valid_result = validate_bundle_against_taxonomy(valid_bundle, taxonomy_registry)
    except Exception as exc:
        print(f"- valid example bundle: blocked ({exc})")
        return 1
    if not valid_result.ok:
        print("- valid example bundle: rejected")
        for issue in valid_result.issues:
            print(f"  {issue.severity}: {issue.code}: {issue.message}")
        return 1
    print("- valid example bundle: ready")

    try:
        invalid_bundle = _load_bundle(INVALID_BUNDLE_PATH, allow_missing_edge_endpoints=True)
        invalid_result = validate_bundle_against_taxonomy(invalid_bundle, taxonomy_registry)
    except Exception as exc:
        print(f"- invalid example bundle: blocked ({exc})")
        return 1
    if invalid_result.ok:
        print("- invalid example bundle: unexpectedly accepted")
        return 1
    print("- invalid example bundle: rejected")
    print(f"- validation issues observed: {len(invalid_result.issues)}")
    print("- ontology IR rules: ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
