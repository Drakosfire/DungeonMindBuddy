"""Deterministic validation rules for synthetic Graph Memory Ontology IR bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.graph_memory.ontology_ir import (
    GraphBundle,
    GraphEdge,
    GraphNode,
    ProvenanceRef,
    SourceRef,
    TaxonomyRef,
)

ERROR_SEVERITIES = {"error", "fatal"}
NON_ADMISSIBLE_EVIDENCE_ROLES = {
    "diagnostic_only",
    "routing_hint",
    "derived_summary",
    "navigation_only",
    "not_admissible",
}
UNSAFE_PROMOTED_AUTHORITY_STATES = {
    "gm_prep",
    "rumor",
    "unreliable_claim",
    "candidate",
    "llm_inferred",
    "contradicted",
    "unknown",
}
PRIVATE_PROVENANCE_VISIBILITY_STATES = {
    "private_gm",
    "spoiler_sensitive",
    "internal_diagnostic",
}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    record_id: str | None = None
    field: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    issues: list[ValidationIssue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity in ERROR_SEVERITIES for issue in self.issues)


def load_taxonomy_registry(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        registry = json.load(handle)
    if not isinstance(registry, dict):
        raise ValueError("taxonomy registry must be a JSON object")
    return registry


def _terms_for(registry: dict[str, Any], vocabulary: str) -> set[str] | None:
    vocabularies = registry.get("vocabularies", {})
    if vocabulary not in vocabularies:
        return None
    values = vocabularies[vocabulary]
    if isinstance(values, dict):
        return set(values)
    return {str(value) for value in values}


def validate_taxonomy_ref(
    ref: TaxonomyRef,
    registry: dict[str, Any],
    field: str,
    record_id: str | None,
) -> list[ValidationIssue]:
    terms = _terms_for(registry, ref.vocabulary)
    if terms is None:
        return [
            ValidationIssue(
                severity="error",
                code="unknown_taxonomy_vocabulary",
                message=f"Unknown taxonomy vocabulary {ref.vocabulary!r}.",
                record_id=record_id,
                field=field,
            )
        ]
    if ref.term not in terms:
        return [
            ValidationIssue(
                severity="error",
                code="unknown_taxonomy_term",
                message=f"Unknown taxonomy term {ref.vocabulary}/{ref.term}.",
                record_id=record_id,
                field=field,
            )
        ]
    return []


def _expect_vocabulary(
    ref: TaxonomyRef,
    expected: str,
    code: str,
    field: str,
    record_id: str | None,
) -> list[ValidationIssue]:
    if ref.vocabulary == expected:
        return []
    return [
        ValidationIssue(
            severity="error",
            code=code,
            message=f"Expected {field} to use vocabulary {expected!r}; got {ref.vocabulary!r}.",
            record_id=record_id,
            field=field,
        )
    ]


def validate_source_ref(
    source_ref: SourceRef, registry: dict[str, Any], record_id: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(validate_taxonomy_ref(source_ref.source_kind, registry, "source_kind", record_id))
    issues.extend(_expect_vocabulary(source_ref.source_kind, "source_kind", "invalid_source_kind_ref", "source_kind", record_id))
    if source_ref.source_layer is not None:
        issues.extend(validate_taxonomy_ref(source_ref.source_layer, registry, "source_layer", record_id))
        issues.extend(_expect_vocabulary(source_ref.source_layer, "source_layer", "invalid_source_layer_ref", "source_layer", record_id))
    if source_ref.line_start is not None and source_ref.line_end is not None:
        if (
            not isinstance(source_ref.line_start, int)
            or not isinstance(source_ref.line_end, int)
            or source_ref.line_start <= 0
            or source_ref.line_end <= 0
            or source_ref.line_end < source_ref.line_start
        ):
            issues.append(ValidationIssue("error", "invalid_source_line_range", "Source line range must be positive and ordered.", record_id, "source_refs.line_range"))
    return issues


def validate_provenance_ref(
    provenance: ProvenanceRef, registry: dict[str, Any], record_id: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field, ref, expected, code in (
        ("evidence_role", provenance.evidence_role, "evidence_role", "invalid_evidence_role_ref"),
        ("authority_state", provenance.authority_state, "authority_state", "invalid_authority_state_ref"),
        ("visibility_state", provenance.visibility_state, "visibility_state", "invalid_visibility_state_ref"),
    ):
        issues.extend(validate_taxonomy_ref(ref, registry, field, record_id))
        issues.extend(_expect_vocabulary(ref, expected, code, field, record_id))
    if provenance.evidence_role.vocabulary == "evidence_role" and provenance.evidence_role.term == "source_evidence" and not provenance.source_refs:
        issues.append(ValidationIssue("error", "source_evidence_without_source_ref", "Source evidence provenance must include at least one source ref.", record_id, "provenance.source_refs"))
    if provenance.evidence_role.vocabulary == "evidence_role" and provenance.evidence_role.term in NON_ADMISSIBLE_EVIDENCE_ROLES:
        issues.append(ValidationIssue("info", "non_admissible_evidence_role", "Evidence role is not answer-supporting evidence.", record_id, "provenance.evidence_role"))
    for source_ref in provenance.source_refs:
        issues.extend(validate_source_ref(source_ref, registry, record_id))
    return issues


def _validate_record_common(record: GraphNode | GraphEdge, registry: dict[str, Any]) -> list[ValidationIssue]:
    record_id = record.node_id if isinstance(record, GraphNode) else record.edge_id
    issues: list[ValidationIssue] = []
    issues.extend(validate_taxonomy_ref(record.lifecycle_state, registry, "lifecycle_state", record_id))
    issues.extend(_expect_vocabulary(record.lifecycle_state, "lifecycle_state", "invalid_lifecycle_state_ref", "lifecycle_state", record_id))
    issues.extend(validate_taxonomy_ref(record.visibility_state, registry, "visibility_state", record_id))
    issues.extend(_expect_vocabulary(record.visibility_state, "visibility_state", "invalid_visibility_state_ref", "visibility_state", record_id))
    if record.validation_status is not None:
        issues.extend(validate_taxonomy_ref(record.validation_status.state, registry, "validation_status.state", record_id))
        issues.extend(_expect_vocabulary(record.validation_status.state, "lifecycle_state", "invalid_lifecycle_state_ref", "validation_status.state", record_id))
    for provenance in record.provenance:
        issues.extend(validate_provenance_ref(provenance, registry, record_id))
    if record.lifecycle_state.vocabulary == "lifecycle_state" and record.lifecycle_state.term == "promoted":
        if not record.provenance:
            issues.append(ValidationIssue("error", "promoted_record_without_provenance", "Promoted records require provenance.", record_id, "provenance"))
        elif not any(provenance.source_refs for provenance in record.provenance):
            issues.append(ValidationIssue("error", "promoted_record_without_source_grounding", "Promoted records require at least one source-grounded provenance ref.", record_id, "provenance.source_refs"))
        for provenance in record.provenance:
            if provenance.authority_state.vocabulary == "authority_state" and provenance.authority_state.term in UNSAFE_PROMOTED_AUTHORITY_STATES:
                issues.append(ValidationIssue("error", "unsafe_authority_promoted", "Unsafe authority states cannot be promoted.", record_id, "provenance.authority_state"))
    if record.visibility_state.vocabulary == "visibility_state" and record.visibility_state.term == "player_visible":
        for provenance in record.provenance:
            if provenance.visibility_state.vocabulary == "visibility_state" and provenance.visibility_state.term in PRIVATE_PROVENANCE_VISIBILITY_STATES:
                issues.append(ValidationIssue("error", "visibility_boundary_conflict", "Player-visible records cannot depend on private or spoiler-sensitive provenance.", record_id, "provenance.visibility_state"))
    return issues


def validate_bundle_against_taxonomy(bundle: GraphBundle, taxonomy_registry: dict[str, Any]) -> ValidationResult:
    issues: list[ValidationIssue] = []
    node_ids = {node.node_id for node in bundle.nodes}
    for node in bundle.nodes:
        issues.extend(validate_taxonomy_ref(node.kind, taxonomy_registry, "kind", node.node_id))
        issues.extend(_expect_vocabulary(node.kind, "entity_kind", "invalid_node_kind_ref", "kind", node.node_id))
        issues.extend(_validate_record_common(node, taxonomy_registry))
    for edge in bundle.edges:
        issues.extend(validate_taxonomy_ref(edge.predicate_family, taxonomy_registry, "predicate_family", edge.edge_id))
        issues.extend(_expect_vocabulary(edge.predicate_family, "relationship_predicate_family", "invalid_predicate_family_ref", "predicate_family", edge.edge_id))
        issues.extend(_validate_record_common(edge, taxonomy_registry))
        for field, endpoint in (("subject_node_id", edge.subject_node_id), ("object_node_id", edge.object_node_id)):
            if endpoint not in node_ids:
                issues.append(ValidationIssue("error", "edge_endpoint_missing", f"Edge endpoint {endpoint!r} is not present in bundle nodes.", edge.edge_id, field))
    return ValidationResult(issues=issues)
