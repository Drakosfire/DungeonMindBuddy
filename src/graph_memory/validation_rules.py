"""Deterministic validation rules for Graph Memory Ontology IR bundles.

This module validates synthetic Ontology IR records against taxonomy and graph
memory safety guardrails. It does not materialize graph data, scan corpus files,
perform extraction, or affect retrieval.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.graph_memory.ontology_ir import GraphBundle, GraphEdge, GraphNode, ProvenanceRef, SourceRef, TaxonomyRef

ERROR_SEVERITIES = {"error", "fatal"}
NON_ADMISSIBLE_EVIDENCE_ROLES = {
    "diagnostic_only",
    "routing_hint",
    "derived_summary",
    "navigation_only",
    "not_admissible",
}
UNSAFE_AUTHORITY_STATES = {
    "gm_prep",
    "rumor",
    "unreliable_claim",
    "candidate",
    "llm_inferred",
    "contradicted",
    "unknown",
}
PRIVATE_PROVENANCE_VISIBILITY_STATES = {"private_gm", "spoiler_sensitive", "internal_diagnostic"}


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
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("taxonomy registry must be a JSON object")
    return data


def _terms_for_vocabulary(registry: dict[str, Any], vocabulary: str) -> set[str] | None:
    vocabularies = registry.get("vocabularies")
    if not isinstance(vocabularies, dict) or vocabulary not in vocabularies:
        return None
    terms = vocabularies[vocabulary].get("terms", [])
    return {term.get("id", "") for term in terms if isinstance(term, dict)}


def _issue(code: str, message: str, record_id: str | None, field: str | None, severity: str = "error") -> ValidationIssue:
    return ValidationIssue(severity=severity, code=code, message=message, record_id=record_id, field=field)


def validate_taxonomy_ref(ref: TaxonomyRef, registry: dict[str, Any], field: str, record_id: str | None) -> list[ValidationIssue]:
    terms = _terms_for_vocabulary(registry, ref.vocabulary)
    if terms is None:
        return [_issue("unknown_taxonomy_vocabulary", f"Unknown taxonomy vocabulary: {ref.vocabulary}", record_id, field)]
    if ref.term not in terms:
        return [_issue("unknown_taxonomy_term", f"Unknown taxonomy term: {ref.vocabulary}/{ref.term}", record_id, field)]
    return []


def _validate_expected_ref(
    ref: TaxonomyRef | None,
    registry: dict[str, Any],
    expected_vocabulary: str,
    code: str,
    field: str,
    record_id: str | None,
) -> list[ValidationIssue]:
    if ref is None:
        return []
    issues = validate_taxonomy_ref(ref, registry, field, record_id)
    if ref.vocabulary != expected_vocabulary:
        issues.append(_issue(code, f"{field} must use {expected_vocabulary}; got {ref.vocabulary}", record_id, field))
    return issues


def validate_source_ref(source_ref: SourceRef, registry: dict[str, Any], record_id: str | None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_validate_expected_ref(source_ref.source_kind, registry, "source_kind", "invalid_source_kind_ref", "source_kind", record_id))
    if source_ref.source_layer is not None:
        issues.extend(_validate_expected_ref(source_ref.source_layer, registry, "source_layer", "invalid_source_layer_ref", "source_layer", record_id))
    if source_ref.line_start is not None and source_ref.line_end is not None:
        if source_ref.line_start <= 0 or source_ref.line_end <= 0 or source_ref.line_end < source_ref.line_start:
            issues.append(_issue("invalid_source_line_range", "Source line range must be positive and ordered", record_id, "source_refs.line_range"))
    return issues


def validate_provenance_ref(provenance: ProvenanceRef, registry: dict[str, Any], record_id: str | None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_validate_expected_ref(provenance.authority_state, registry, "authority_state", "invalid_authority_state_ref", "authority_state", record_id))
    issues.extend(_validate_expected_ref(provenance.evidence_role, registry, "evidence_role", "invalid_evidence_role_ref", "evidence_role", record_id))
    if provenance.visibility_state is not None:
        issues.extend(_validate_expected_ref(provenance.visibility_state, registry, "visibility_state", "invalid_visibility_state_ref", "visibility_state", record_id))
    for source_ref in provenance.source_refs:
        issues.extend(validate_source_ref(source_ref, registry, record_id))
    if provenance.evidence_role.vocabulary == "evidence_role" and provenance.evidence_role.term == "source_evidence" and not provenance.source_refs:
        issues.append(_issue("source_evidence_without_source_ref", "Source evidence provenance requires at least one source ref", record_id, "provenance.source_refs"))
    if provenance.evidence_role.vocabulary == "evidence_role" and provenance.evidence_role.term in NON_ADMISSIBLE_EVIDENCE_ROLES:
        issues.append(_issue("non_admissible_evidence_role", "Evidence role is not answer-supporting evidence", record_id, "provenance.evidence_role", "info"))
    return issues


def _record_id(record: GraphNode | GraphEdge) -> str:
    return record.node_id if isinstance(record, GraphNode) else record.edge_id


def _validate_record_policy(record: GraphNode | GraphEdge, registry: dict[str, Any]) -> list[ValidationIssue]:
    record_id = _record_id(record)
    issues: list[ValidationIssue] = []
    issues.extend(_validate_expected_ref(record.lifecycle_state, registry, "lifecycle_state", "invalid_lifecycle_state_ref", "lifecycle_state", record_id))
    issues.extend(_validate_expected_ref(record.visibility_state, registry, "visibility_state", "invalid_visibility_state_ref", "visibility_state", record_id))
    for provenance in record.provenance:
        issues.extend(validate_provenance_ref(provenance, registry, record_id))
    promoted = record.lifecycle_state is not None and record.lifecycle_state.vocabulary == "lifecycle_state" and record.lifecycle_state.term == "promoted"
    player_visible = record.visibility_state is not None and record.visibility_state.vocabulary == "visibility_state" and record.visibility_state.term == "player_visible"
    if promoted and not record.provenance:
        issues.append(_issue("promoted_record_without_provenance", "Promoted records require provenance", record_id, "provenance"))
    if promoted and record.provenance and not any(provenance.source_refs for provenance in record.provenance):
        issues.append(_issue("promoted_record_without_source_grounding", "Promoted records require source-grounded provenance", record_id, "provenance.source_refs"))
    for provenance in record.provenance:
        if promoted and provenance.authority_state.vocabulary == "authority_state" and provenance.authority_state.term in UNSAFE_AUTHORITY_STATES:
            issues.append(_issue("unsafe_authority_promoted", "Promoted record uses an unsafe authority state", record_id, "provenance.authority_state"))
        if (
            player_visible
            and provenance.visibility_state is not None
            and provenance.visibility_state.vocabulary == "visibility_state"
            and provenance.visibility_state.term in PRIVATE_PROVENANCE_VISIBILITY_STATES
        ):
            issues.append(_issue("visibility_boundary_conflict", "Player-visible record has private or spoiler-sensitive provenance", record_id, "provenance.visibility_state"))
    return issues


def validate_bundle_against_taxonomy(bundle: GraphBundle, taxonomy_registry: dict[str, Any]) -> ValidationResult:
    issues: list[ValidationIssue] = []
    node_ids = {node.node_id for node in bundle.nodes}
    for node in bundle.nodes:
        issues.extend(_validate_expected_ref(node.kind, taxonomy_registry, "entity_kind", "invalid_node_kind_ref", "kind", node.node_id))
        issues.extend(_validate_record_policy(node, taxonomy_registry))
    for edge in bundle.edges:
        issues.extend(_validate_expected_ref(edge.predicate_family, taxonomy_registry, "relationship_predicate_family", "invalid_predicate_family_ref", "predicate_family", edge.edge_id))
        issues.extend(_validate_record_policy(edge, taxonomy_registry))
        if edge.subject_id not in node_ids:
            issues.append(_issue("edge_endpoint_missing", f"Edge subject_id is missing from bundle nodes: {edge.subject_id}", edge.edge_id, "subject_id"))
        if edge.object_id not in node_ids:
            issues.append(_issue("edge_endpoint_missing", f"Edge object_id is missing from bundle nodes: {edge.object_id}", edge.edge_id, "object_id"))
    for index, status in enumerate(bundle.validation):
        record_id = f"{bundle.bundle_id}:validation:{index}"
        issues.extend(_validate_expected_ref(status.state, taxonomy_registry, "lifecycle_state", "invalid_lifecycle_state_ref", "validation.state", record_id))
        if status.severity is not None:
            issues.extend(_validate_expected_ref(status.severity, taxonomy_registry, "validation_severity", "invalid_validation_severity_ref", "validation.severity", record_id))
    return ValidationResult(issues=issues)
