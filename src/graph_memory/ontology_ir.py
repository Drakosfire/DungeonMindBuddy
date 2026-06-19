"""Schema-only Ontology IR records for the Graph Memory ladder.

This module defines plain dataclass shapes for graph-memory records. It does
not materialize campaign data, perform extraction, or affect retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias


ScalarValue: TypeAlias = str | int | float | bool | None
ScalarProperties: TypeAlias = dict[str, ScalarValue]


class OntologyIRValidationError(ValueError):
    """Raised when schema-only Ontology IR shape validation fails."""


def _require_mapping(data: Any, label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise OntologyIRValidationError(f"{label} must be an object")
    return data


def _require_nonblank(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OntologyIRValidationError(f"{label} must be a nonblank string")
    return value


def _optional_taxonomy_ref(data: Any, label: str) -> TaxonomyRef | None:
    if data is None:
        return None
    return TaxonomyRef.from_dict(_require_mapping(data, label))


def validate_scalar_properties(properties: dict[str, Any], label: str = "properties") -> ScalarProperties:
    if not isinstance(properties, dict):
        raise OntologyIRValidationError(f"{label} must be an object")
    for key, value in properties.items():
        if not isinstance(key, str) or not key.strip():
            raise OntologyIRValidationError(f"{label} keys must be nonblank strings")
        if not (value is None or isinstance(value, str | int | float | bool)):
            raise OntologyIRValidationError(f"{label}.{key} must be scalar JSON-compatible value")
    return dict(properties)


@dataclass(frozen=True)
class TaxonomyRef:
    vocabulary: str
    term: str

    def __post_init__(self) -> None:
        _require_nonblank(self.vocabulary, "taxonomy vocabulary")
        _require_nonblank(self.term, "taxonomy term")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaxonomyRef":
        return cls(vocabulary=data.get("vocabulary", ""), term=data.get("term", ""))

    def to_dict(self) -> dict[str, str]:
        return {"vocabulary": self.vocabulary, "term": self.term}


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    source_kind: TaxonomyRef
    source_path: str | None = None
    source_layer: TaxonomyRef | None = None
    source_reference: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    anchor: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(self.source_id, "source_id")
        if self.line_start is not None and not isinstance(self.line_start, int):
            raise OntologyIRValidationError("line_start must be an integer when present")
        if self.line_end is not None and not isinstance(self.line_end, int):
            raise OntologyIRValidationError("line_end must be an integer when present")
        if self.line_start is not None and self.line_end is not None and self.line_end < self.line_start:
            raise OntologyIRValidationError("line_end must be greater than or equal to line_start")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceRef":
        return cls(
            source_id=data.get("source_id", ""),
            source_path=data.get("source_path"),
            source_kind=TaxonomyRef.from_dict(_require_mapping(data.get("source_kind"), "source_kind")),
            source_layer=_optional_taxonomy_ref(data.get("source_layer"), "source_layer"),
            source_reference=data.get("source_reference"),
            line_start=data.get("line_start"),
            line_end=data.get("line_end"),
            anchor=data.get("anchor"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_path": self.source_path,
            "source_kind": self.source_kind.to_dict(),
            "source_layer": self.source_layer.to_dict() if self.source_layer else None,
            "source_reference": self.source_reference,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "anchor": self.anchor,
        }


@dataclass(frozen=True)
class ProvenanceRef:
    provenance_id: str
    source_refs: list[SourceRef]
    authority_state: TaxonomyRef
    evidence_role: TaxonomyRef
    visibility_state: TaxonomyRef | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(self.provenance_id, "provenance_id")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvenanceRef":
        return cls(
            provenance_id=data.get("provenance_id", ""),
            source_refs=[SourceRef.from_dict(_require_mapping(item, "source_ref")) for item in data.get("source_refs", [])],
            authority_state=TaxonomyRef.from_dict(_require_mapping(data.get("authority_state"), "authority_state")),
            evidence_role=TaxonomyRef.from_dict(_require_mapping(data.get("evidence_role"), "evidence_role")),
            visibility_state=_optional_taxonomy_ref(data.get("visibility_state"), "visibility_state"),
            notes=data.get("notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance_id": self.provenance_id,
            "source_refs": [source_ref.to_dict() for source_ref in self.source_refs],
            "authority_state": self.authority_state.to_dict(),
            "evidence_role": self.evidence_role.to_dict(),
            "visibility_state": self.visibility_state.to_dict() if self.visibility_state else None,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ValidationStatus:
    state: TaxonomyRef
    severity: TaxonomyRef | None = None
    message: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationStatus":
        return cls(
            state=TaxonomyRef.from_dict(_require_mapping(data.get("state"), "state")),
            severity=_optional_taxonomy_ref(data.get("severity"), "severity"),
            message=data.get("message"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "severity": self.severity.to_dict() if self.severity else None,
            "message": self.message,
        }


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    kind: TaxonomyRef
    label: str
    aliases: list[str] = field(default_factory=list)
    properties: ScalarProperties = field(default_factory=dict)
    provenance: list[ProvenanceRef] = field(default_factory=list)
    lifecycle_state: TaxonomyRef | None = None
    visibility_state: TaxonomyRef | None = None

    def __post_init__(self) -> None:
        _require_nonblank(self.node_id, "node_id")
        _require_nonblank(self.label, "label")
        validate_scalar_properties(self.properties)
        if not all(isinstance(alias, str) for alias in self.aliases):
            raise OntologyIRValidationError("aliases must be strings")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphNode":
        aliases = data.get("aliases", [])
        if not isinstance(aliases, list):
            raise OntologyIRValidationError("aliases must be a list")
        return cls(
            node_id=data.get("node_id", ""),
            kind=TaxonomyRef.from_dict(_require_mapping(data.get("kind"), "kind")),
            label=data.get("label", ""),
            aliases=list(aliases),
            properties=validate_scalar_properties(data.get("properties", {})),
            provenance=[ProvenanceRef.from_dict(_require_mapping(item, "provenance")) for item in data.get("provenance", [])],
            lifecycle_state=_optional_taxonomy_ref(data.get("lifecycle_state"), "lifecycle_state"),
            visibility_state=_optional_taxonomy_ref(data.get("visibility_state"), "visibility_state"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind.to_dict(),
            "label": self.label,
            "aliases": list(self.aliases),
            "properties": dict(self.properties),
            "provenance": [provenance.to_dict() for provenance in self.provenance],
            "lifecycle_state": self.lifecycle_state.to_dict() if self.lifecycle_state else None,
            "visibility_state": self.visibility_state.to_dict() if self.visibility_state else None,
        }


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    subject_id: str
    object_id: str
    predicate_family: TaxonomyRef
    label: str
    properties: ScalarProperties = field(default_factory=dict)
    provenance: list[ProvenanceRef] = field(default_factory=list)
    lifecycle_state: TaxonomyRef | None = None
    visibility_state: TaxonomyRef | None = None

    def __post_init__(self) -> None:
        _require_nonblank(self.edge_id, "edge_id")
        _require_nonblank(self.subject_id, "subject_id")
        _require_nonblank(self.object_id, "object_id")
        _require_nonblank(self.label, "label")
        validate_scalar_properties(self.properties)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphEdge":
        return cls(
            edge_id=data.get("edge_id", ""),
            subject_id=data.get("subject_id", ""),
            object_id=data.get("object_id", ""),
            predicate_family=TaxonomyRef.from_dict(_require_mapping(data.get("predicate_family"), "predicate_family")),
            label=data.get("label", ""),
            properties=validate_scalar_properties(data.get("properties", {})),
            provenance=[ProvenanceRef.from_dict(_require_mapping(item, "provenance")) for item in data.get("provenance", [])],
            lifecycle_state=_optional_taxonomy_ref(data.get("lifecycle_state"), "lifecycle_state"),
            visibility_state=_optional_taxonomy_ref(data.get("visibility_state"), "visibility_state"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "subject_id": self.subject_id,
            "object_id": self.object_id,
            "predicate_family": self.predicate_family.to_dict(),
            "label": self.label,
            "properties": dict(self.properties),
            "provenance": [provenance.to_dict() for provenance in self.provenance],
            "lifecycle_state": self.lifecycle_state.to_dict() if self.lifecycle_state else None,
            "visibility_state": self.visibility_state.to_dict() if self.visibility_state else None,
        }


@dataclass(frozen=True)
class GraphBundle:
    bundle_id: str
    schema_version: str
    taxonomy_registry_version: str
    created_by: str
    description: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    validation: list[ValidationStatus] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_nonblank(self.bundle_id, "bundle_id")
        node_ids = [node.node_id for node in self.nodes]
        edge_ids = [edge.edge_id for edge in self.edges]
        if len(node_ids) != len(set(node_ids)):
            raise OntologyIRValidationError("node IDs must be unique")
        if len(edge_ids) != len(set(edge_ids)):
            raise OntologyIRValidationError("edge IDs must be unique")
        node_id_set = set(node_ids)
        for edge in self.edges:
            if edge.subject_id not in node_id_set or edge.object_id not in node_id_set:
                raise OntologyIRValidationError(f"edge endpoints must refer to bundle nodes: {edge.edge_id}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphBundle":
        return cls(
            bundle_id=data.get("bundle_id", ""),
            schema_version=data.get("schema_version", ""),
            taxonomy_registry_version=data.get("taxonomy_registry_version", ""),
            created_by=data.get("created_by", ""),
            description=data.get("description", ""),
            nodes=[GraphNode.from_dict(_require_mapping(item, "node")) for item in data.get("nodes", [])],
            edges=[GraphEdge.from_dict(_require_mapping(item, "edge")) for item in data.get("edges", [])],
            validation=[ValidationStatus.from_dict(_require_mapping(item, "validation")) for item in data.get("validation", [])],
        )

    @classmethod
    def from_dict_unchecked_endpoints(cls, data: dict[str, Any]) -> "GraphBundle":
        """Load a synthetic test bundle without enforcing edge endpoint integrity.

        This is only for invalid-fixture validation-rule tests that need to
        exercise endpoint-integrity findings. Production and materializer paths
        must use the strict ``from_dict`` constructor.
        """
        bundle = object.__new__(cls)
        object.__setattr__(bundle, "bundle_id", data.get("bundle_id", ""))
        object.__setattr__(bundle, "schema_version", data.get("schema_version", ""))
        object.__setattr__(bundle, "taxonomy_registry_version", data.get("taxonomy_registry_version", ""))
        object.__setattr__(bundle, "created_by", data.get("created_by", ""))
        object.__setattr__(bundle, "description", data.get("description", ""))
        object.__setattr__(bundle, "nodes", [GraphNode.from_dict(_require_mapping(item, "node")) for item in data.get("nodes", [])])
        object.__setattr__(bundle, "edges", [GraphEdge.from_dict(_require_mapping(item, "edge")) for item in data.get("edges", [])])
        object.__setattr__(bundle, "validation", [ValidationStatus.from_dict(_require_mapping(item, "validation")) for item in data.get("validation", [])])
        _require_nonblank(bundle.bundle_id, "bundle_id")
        node_ids = [node.node_id for node in bundle.nodes]
        edge_ids = [edge.edge_id for edge in bundle.edges]
        if len(node_ids) != len(set(node_ids)):
            raise OntologyIRValidationError("node IDs must be unique")
        if len(edge_ids) != len(set(edge_ids)):
            raise OntologyIRValidationError("edge IDs must be unique")
        return bundle

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "schema_version": self.schema_version,
            "taxonomy_registry_version": self.taxonomy_registry_version,
            "created_by": self.created_by,
            "description": self.description,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "validation": [status.to_dict() for status in self.validation],
        }
