"""Deterministic fixture-only materializer for Graph Memory v0.

This module converts an explicit synthetic fixture into Ontology IR records. It
never discovers files, scans campaign data, calls LLMs, or affects retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.graph_memory.ontology_ir import GraphBundle, GraphEdge, GraphNode, ProvenanceRef, SourceRef, TaxonomyRef, ValidationStatus
from src.graph_memory.validation_rules import validate_bundle_against_taxonomy

SCHEMA_VERSION = "0.1"
TAXONOMY_REGISTRY_VERSION = "0.1"
CREATED_BY = "deterministic_graph_materializer_v0"


def _ref(vocabulary: str, term: str) -> TaxonomyRef:
    return TaxonomyRef(vocabulary=vocabulary, term=term)


def _source_ref(document: dict[str, Any], unit: dict[str, Any] | None = None) -> SourceRef:
    return SourceRef(
        source_id=str(document["source_id"]),
        source_kind=_ref("source_kind", str(document["source_kind"])),
        source_layer=_ref("source_layer", str(document["source_layer"])),
        source_path=document.get("source_path"),
        source_reference=document.get("source_reference"),
        line_start=unit.get("line_start") if unit else None,
        line_end=unit.get("line_end") if unit else None,
        anchor=document.get("anchor"),
    )


def _provenance(document: dict[str, Any], unit: dict[str, Any] | None, record_id: str) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=f"{record_id}:provenance",
        source_refs=[_source_ref(document, unit)],
        authority_state=_ref("authority_state", str(unit.get("authority_state", "system_derived") if unit else "system_derived")),
        evidence_role=_ref("evidence_role", str(unit.get("evidence_role", "diagnostic_only") if unit else "diagnostic_only")),
        visibility_state=_ref("visibility_state", "internal_diagnostic"),
        notes="Synthetic fixture-bound materializer provenance.",
    )


def materialize_fixture_to_bundle(data: dict[str, Any]) -> GraphBundle:
    """Convert the explicit synthetic materializer fixture into a GraphBundle."""
    documents = data.get("source_documents", [])
    relationships = data.get("relationships", [])
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    documents_by_id: dict[str, dict[str, Any]] = {}
    units_by_id: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}

    for document in documents:
        documents_by_id[str(document["source_id"])] = document
        document_id = str(document["source_id"])
        nodes.append(
            GraphNode(
                node_id=document_id,
                kind=_ref("entity_kind", "source_document"),
                label=str(document.get("source_reference") or document_id),
                aliases=[],
                properties={"synthetic": True, "fixture_version": str(data.get("fixture_version", "0.1"))},
                provenance=[_provenance(document, None, document_id)],
                lifecycle_state=_ref("lifecycle_state", "candidate"),
                visibility_state=_ref("visibility_state", "internal_diagnostic"),
            )
        )
        for unit in document.get("units", []):
            unit_id = str(unit["unit_id"])
            units_by_id[unit_id] = (document, unit)
            nodes.append(
                GraphNode(
                    node_id=unit_id,
                    kind=_ref("entity_kind", "source_unit"),
                    label=str(unit["label"]),
                    aliases=[],
                    properties={"synthetic": True, "text": str(unit.get("text", ""))},
                    provenance=[_provenance(document, unit, unit_id)],
                    lifecycle_state=_ref("lifecycle_state", "candidate"),
                    visibility_state=_ref("visibility_state", str(unit.get("visibility_state", "internal_diagnostic"))),
                )
            )

    for relationship in relationships:
        subject_id = str(relationship["subject_unit_or_document_id"])
        object_id = str(relationship["object_unit_or_document_id"])
        source_document = documents_by_id.get(subject_id) or units_by_id.get(subject_id, (None, None))[0] or documents_by_id.get(object_id) or units_by_id.get(object_id, (None, None))[0]
        if source_document is None:
            raise ValueError(f"relationship has no synthetic source document: {relationship['relationship_id']}")
        edge_id = str(relationship["relationship_id"])
        edges.append(
            GraphEdge(
                edge_id=edge_id,
                subject_id=subject_id,
                object_id=object_id,
                predicate_family=_ref("relationship_predicate_family", str(relationship.get("predicate_family", "source_derivation"))),
                label=str(relationship["label"]),
                properties={"synthetic": True},
                provenance=[_provenance(source_document, None, edge_id)],
                lifecycle_state=_ref("lifecycle_state", "candidate"),
                visibility_state=_ref("visibility_state", "internal_diagnostic"),
            )
        )

    fixture_id = str(data["fixture_id"])
    return GraphBundle(
        bundle_id=f"{fixture_id}:graph-bundle",
        schema_version=SCHEMA_VERSION,
        taxonomy_registry_version=TAXONOMY_REGISTRY_VERSION,
        created_by=CREATED_BY,
        description=str(data.get("description", "Synthetic materializer graph bundle.")),
        nodes=nodes,
        edges=edges,
        validation=[
            ValidationStatus(
                state=_ref("lifecycle_state", "candidate"),
                severity=_ref("validation_severity", "info"),
                message="Materialized deterministically from a synthetic fixture.",
            )
        ],
    )


def materialize_fixture_file(path: Path) -> GraphBundle:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("materializer fixture must be a JSON object")
    return materialize_fixture_to_bundle(data)


def materialize_and_validate_fixture(fixture_path: Path, taxonomy_registry_path: Path) -> tuple[GraphBundle, Any]:
    bundle = materialize_fixture_file(fixture_path)
    with taxonomy_registry_path.open("r", encoding="utf-8") as handle:
        taxonomy_registry = json.load(handle)
    return bundle, validate_bundle_against_taxonomy(bundle, taxonomy_registry)
