"""Standard-library Ontology IR containers for synthetic Graph Memory fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaxonomyRef:
    vocabulary: str
    term: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaxonomyRef":
        if not isinstance(data, dict):
            raise ValueError("taxonomy ref must be an object")
        return cls(vocabulary=str(data["vocabulary"]), term=str(data["term"]))

    def to_dict(self) -> dict[str, str]:
        return {"vocabulary": self.vocabulary, "term": self.term}


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    source_kind: TaxonomyRef
    source_layer: TaxonomyRef | None = None
    path: str | None = None
    line_start: int | None = None
    line_end: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceRef":
        return cls(
            source_id=str(data["source_id"]),
            source_kind=TaxonomyRef.from_dict(data["source_kind"]),
            source_layer=TaxonomyRef.from_dict(data["source_layer"]) if data.get("source_layer") is not None else None,
            path=data.get("path"),
            line_start=data.get("line_start"),
            line_end=data.get("line_end"),
        )


@dataclass(frozen=True)
class ProvenanceRef:
    provenance_id: str
    evidence_role: TaxonomyRef
    authority_state: TaxonomyRef
    visibility_state: TaxonomyRef
    source_refs: list[SourceRef] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvenanceRef":
        return cls(
            provenance_id=str(data["provenance_id"]),
            evidence_role=TaxonomyRef.from_dict(data["evidence_role"]),
            authority_state=TaxonomyRef.from_dict(data["authority_state"]),
            visibility_state=TaxonomyRef.from_dict(data["visibility_state"]),
            source_refs=[SourceRef.from_dict(item) for item in data.get("source_refs", [])],
        )


@dataclass(frozen=True)
class ValidationStatus:
    state: TaxonomyRef

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationStatus":
        return cls(state=TaxonomyRef.from_dict(data["state"]))


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    label: str
    kind: TaxonomyRef
    lifecycle_state: TaxonomyRef
    visibility_state: TaxonomyRef
    provenance: list[ProvenanceRef] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    validation_status: ValidationStatus | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphNode":
        aliases = data.get("aliases", [])
        if not isinstance(aliases, list):
            raise ValueError("GraphNode.aliases must be a list")
        return cls(
            node_id=str(data["node_id"]),
            label=str(data["label"]),
            kind=TaxonomyRef.from_dict(data["kind"]),
            lifecycle_state=TaxonomyRef.from_dict(data["lifecycle_state"]),
            visibility_state=TaxonomyRef.from_dict(data["visibility_state"]),
            provenance=[ProvenanceRef.from_dict(item) for item in data.get("provenance", [])],
            aliases=[str(alias) for alias in aliases],
            validation_status=ValidationStatus.from_dict(data["validation_status"]) if data.get("validation_status") else None,
        )


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    subject_node_id: str
    object_node_id: str
    predicate_family: TaxonomyRef
    lifecycle_state: TaxonomyRef
    visibility_state: TaxonomyRef
    provenance: list[ProvenanceRef] = field(default_factory=list)
    validation_status: ValidationStatus | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphEdge":
        return cls(
            edge_id=str(data["edge_id"]),
            subject_node_id=str(data["subject_node_id"]),
            object_node_id=str(data["object_node_id"]),
            predicate_family=TaxonomyRef.from_dict(data["predicate_family"]),
            lifecycle_state=TaxonomyRef.from_dict(data["lifecycle_state"]),
            visibility_state=TaxonomyRef.from_dict(data["visibility_state"]),
            provenance=[ProvenanceRef.from_dict(item) for item in data.get("provenance", [])],
            validation_status=ValidationStatus.from_dict(data["validation_status"]) if data.get("validation_status") else None,
        )


@dataclass(frozen=True)
class GraphBundle:
    bundle_id: str
    taxonomy_registry_version: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphBundle":
        return cls(
            bundle_id=str(data["bundle_id"]),
            taxonomy_registry_version=str(data["taxonomy_registry_version"]),
            nodes=[GraphNode.from_dict(item) for item in data.get("nodes", [])],
            edges=[GraphEdge.from_dict(item) for item in data.get("edges", [])],
        )
