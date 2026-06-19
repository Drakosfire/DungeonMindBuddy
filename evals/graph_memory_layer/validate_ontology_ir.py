from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

from src.graph_memory.ontology_ir import GraphBundle, TaxonomyRef, validate_scalar_properties


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_BUNDLE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_minimal_bundle.json"
EXPECTED_SCHEMA_VERSION = "0.1"


def iter_taxonomy_refs(bundle: GraphBundle) -> Iterable[TaxonomyRef]:
    for node in bundle.nodes:
        yield node.kind
        if node.lifecycle_state:
            yield node.lifecycle_state
        if node.visibility_state:
            yield node.visibility_state
        for provenance in node.provenance:
            yield provenance.authority_state
            yield provenance.evidence_role
            if provenance.visibility_state:
                yield provenance.visibility_state
            for source_ref in provenance.source_refs:
                yield source_ref.source_kind
                if source_ref.source_layer:
                    yield source_ref.source_layer
    for edge in bundle.edges:
        yield edge.predicate_family
        if edge.lifecycle_state:
            yield edge.lifecycle_state
        if edge.visibility_state:
            yield edge.visibility_state
        for provenance in edge.provenance:
            yield provenance.authority_state
            yield provenance.evidence_role
            if provenance.visibility_state:
                yield provenance.visibility_state
            for source_ref in provenance.source_refs:
                yield source_ref.source_kind
                if source_ref.source_layer:
                    yield source_ref.source_layer
    for status in bundle.validation:
        yield status.state
        if status.severity:
            yield status.severity


def validate_bundle(bundle: GraphBundle) -> None:
    if bundle.schema_version != EXPECTED_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {EXPECTED_SCHEMA_VERSION}; got {bundle.schema_version}")
    node_ids = [node.node_id for node in bundle.nodes]
    edge_ids = [edge.edge_id for edge in bundle.edges]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("node IDs must be unique")
    if len(edge_ids) != len(set(edge_ids)):
        raise ValueError("edge IDs must be unique")
    node_id_set = set(node_ids)
    for edge in bundle.edges:
        if edge.subject_id not in node_id_set or edge.object_id not in node_id_set:
            raise ValueError(f"edge endpoints must exist in bundle: {edge.edge_id}")
        validate_scalar_properties(edge.properties, f"edge {edge.edge_id} properties")
    for node in bundle.nodes:
        validate_scalar_properties(node.properties, f"node {node.node_id} properties")
    for taxonomy_ref in iter_taxonomy_refs(bundle):
        if not taxonomy_ref.vocabulary.strip() or not taxonomy_ref.term.strip():
            raise ValueError("taxonomy refs must have nonblank vocabulary and term")


def main() -> int:
    print("Graph Memory ontology IR validation")
    if not EXAMPLE_BUNDLE_PATH.is_file():
        print("- example bundle: missing")
        return 1
    print("- example bundle: found")
    try:
        with EXAMPLE_BUNDLE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        bundle = GraphBundle.from_dict(data)
        validate_bundle(bundle)
    except Exception as exc:  # validator CLI should report all schema failures compactly
        print(f"- ontology IR: blocked ({exc})")
        return 1
    print(f"- schema version: {bundle.schema_version}")
    print(f"- nodes: {len(bundle.nodes)}")
    print(f"- edges: {len(bundle.edges)}")
    print("- edge endpoints: ok")
    print("- taxonomy refs: ok")
    print("- ontology IR: ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
