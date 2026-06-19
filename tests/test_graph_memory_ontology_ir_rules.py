from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.validate_ontology_ir_rules import _load_bundle
from src.graph_memory.ontology_ir import GraphBundle, GraphEdge, GraphNode, ProvenanceRef, SourceRef, TaxonomyRef
from src.graph_memory.validation_rules import load_taxonomy_registry, validate_bundle_against_taxonomy

REPO_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
VALID_BUNDLE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_minimal_bundle.json"
INVALID_BUNDLE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_invalid_bundle.json"


def ref(vocabulary: str, term: str) -> TaxonomyRef:
    return TaxonomyRef(vocabulary=vocabulary, term=term)


def registry() -> dict[str, object]:
    return load_taxonomy_registry(TAXONOMY_REGISTRY_PATH)


def valid_source_ref() -> SourceRef:
    return SourceRef(
        source_id="example:source:synthetic",
        source_kind=ref("source_kind", "design_doc"),
        source_layer=ref("source_layer", "diagnostic_layer"),
        line_start=1,
        line_end=1,
    )


def provenance(
    *,
    authority_state: str = "human_confirmed",
    evidence_role: str = "source_evidence",
    visibility_state: str = "internal_diagnostic",
    source_refs: list[SourceRef] | None = None,
) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id="example:provenance:synthetic",
        source_refs=source_refs if source_refs is not None else [valid_source_ref()],
        authority_state=ref("authority_state", authority_state),
        evidence_role=ref("evidence_role", evidence_role),
        visibility_state=ref("visibility_state", visibility_state),
    )


def node(**overrides: object) -> GraphNode:
    values = {
        "node_id": "example:test:node",
        "kind": ref("entity_kind", "source_document"),
        "label": "Synthetic Test Node",
        "aliases": [],
        "properties": {"synthetic": True},
        "provenance": [],
        "lifecycle_state": ref("lifecycle_state", "candidate"),
        "visibility_state": ref("visibility_state", "internal_diagnostic"),
    }
    values.update(overrides)
    return GraphNode(**values)  # type: ignore[arg-type]


def bundle_with(nodes: list[GraphNode], edges: list[GraphEdge] | None = None) -> GraphBundle:
    return GraphBundle(
        bundle_id="example:test:bundle",
        schema_version="0.1",
        taxonomy_registry_version="0.1",
        created_by="test",
        description="Synthetic test bundle.",
        nodes=nodes,
        edges=edges or [],
        validation=[],
    )


def codes(result) -> set[str]:
    return {issue.code for issue in result.issues}


def test_valid_synthetic_bundle_passes_without_error_or_fatal_issues() -> None:
    with VALID_BUNDLE_PATH.open("r", encoding="utf-8") as handle:
        bundle = GraphBundle.from_dict(json.load(handle))
    result = validate_bundle_against_taxonomy(bundle, registry())
    assert result.ok
    assert not [issue for issue in result.issues if issue.severity in {"error", "fatal"}]


def test_invalid_synthetic_bundle_fails() -> None:
    bundle = _load_bundle(INVALID_BUNDLE_PATH, allow_missing_edge_endpoints=True)
    result = validate_bundle_against_taxonomy(bundle, registry())
    assert not result.ok


def test_unknown_taxonomy_vocabulary_is_detected() -> None:
    result = validate_bundle_against_taxonomy(bundle_with([node(kind=ref("missing_vocabulary", "source_document"))]), registry())
    assert "unknown_taxonomy_vocabulary" in codes(result)


def test_unknown_taxonomy_term_is_detected() -> None:
    result = validate_bundle_against_taxonomy(bundle_with([node(kind=ref("entity_kind", "missing_term"))]), registry())
    assert "unknown_taxonomy_term" in codes(result)


def test_source_evidence_without_source_refs_is_detected() -> None:
    result = validate_bundle_against_taxonomy(bundle_with([node(provenance=[provenance(source_refs=[])])]), registry())
    assert "source_evidence_without_source_ref" in codes(result)


def test_promoted_record_without_provenance_is_detected() -> None:
    result = validate_bundle_against_taxonomy(bundle_with([node(lifecycle_state=ref("lifecycle_state", "promoted"))]), registry())
    assert "promoted_record_without_provenance" in codes(result)


def test_promoted_record_without_source_grounding_is_detected() -> None:
    result = validate_bundle_against_taxonomy(
        bundle_with([
            node(
                lifecycle_state=ref("lifecycle_state", "promoted"),
                provenance=[provenance(evidence_role="supporting_context", source_refs=[])],
            )
        ]),
        registry(),
    )
    assert "promoted_record_without_source_grounding" in codes(result)


def test_unsafe_authority_promoted_is_detected() -> None:
    result = validate_bundle_against_taxonomy(
        bundle_with([node(lifecycle_state=ref("lifecycle_state", "promoted"), provenance=[provenance(authority_state="rumor")])]),
        registry(),
    )
    assert "unsafe_authority_promoted" in codes(result)


def test_visibility_boundary_conflict_is_detected() -> None:
    result = validate_bundle_against_taxonomy(
        bundle_with([node(visibility_state=ref("visibility_state", "player_visible"), provenance=[provenance(visibility_state="private_gm")])]),
        registry(),
    )
    assert "visibility_boundary_conflict" in codes(result)


def test_edge_endpoint_missing_is_detected() -> None:
    subject = node(node_id="example:test:subject")
    edge = GraphEdge(
        edge_id="example:test:edge:missing",
        subject_id="example:test:subject",
        object_id="example:test:missing",
        predicate_family=ref("relationship_predicate_family", "source_derivation"),
        label="synthetic missing endpoint",
        lifecycle_state=ref("lifecycle_state", "candidate"),
        visibility_state=ref("visibility_state", "internal_diagnostic"),
    )
    bundle = bundle_with([subject])
    bundle.edges.append(edge)
    result = validate_bundle_against_taxonomy(bundle, registry())
    assert "edge_endpoint_missing" in codes(result)


def test_validator_cli_exits_zero_when_valid_passes_and_invalid_fails() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_ontology_ir_rules"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- ontology IR rules: ready" in result.stdout
