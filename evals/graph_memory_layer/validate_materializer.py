from __future__ import annotations

import sys
from pathlib import Path

from src.graph_memory.materialize import materialize_fixture_file
from src.graph_memory.validation_rules import load_taxonomy_registry, validate_bundle_against_taxonomy

REPO_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
MATERIALIZER_INPUT_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "materializer_input_minimal.json"


def _term(ref) -> str | None:
    return ref.term if ref is not None else None


def main() -> int:
    print("Graph Memory deterministic materializer validation")
    if not TAXONOMY_REGISTRY_PATH.is_file():
        print("- taxonomy registry: missing")
        return 1
    taxonomy_registry = load_taxonomy_registry(TAXONOMY_REGISTRY_PATH)
    print("- taxonomy registry: found")
    if not MATERIALIZER_INPUT_PATH.is_file():
        print("- materializer input: missing")
        return 1
    print("- materializer input: found")
    bundle = materialize_fixture_file(MATERIALIZER_INPUT_PATH)
    print("- graph bundle: materialized")
    result = validate_bundle_against_taxonomy(bundle, taxonomy_registry)
    errors = [issue for issue in result.issues if issue.severity in {"error", "fatal"}]
    if errors:
        print("- validation rules: blocked")
        for issue in errors:
            print(f"  {issue.severity}: {issue.code}: {issue.message}")
        return 1
    node_ids = {node.node_id for node in bundle.nodes}
    edge_ids = {edge.edge_id for edge in bundle.edges}
    expected_edge = "example:relationship:document-contains-unit"
    if len(bundle.nodes) != 2 or len(bundle.edges) != 1:
        print("- materializer: blocked (unexpected graph size)")
        return 1
    if {"example:source:document:alpha", "example:source-unit:alpha-1"} - node_ids or expected_edge not in edge_ids:
        print("- materializer: blocked (expected records missing)")
        return 1
    for record in [*bundle.nodes, *bundle.edges]:
        if _term(record.lifecycle_state) != "candidate" or _term(record.visibility_state) != "internal_diagnostic":
            print(f"- materializer: blocked (unsafe record state: {record})")
            return 1
        if not record.provenance or any(_term(prov.evidence_role) != "diagnostic_only" for prov in record.provenance):
            print(f"- materializer: blocked (unsafe provenance: {record})")
            return 1
    print(f"- nodes: {len(bundle.nodes)}")
    print(f"- edges: {len(bundle.edges)}")
    print("- validation rules: ready")
    print("- materializer: ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
