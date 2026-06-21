"""Deterministic reporting for the synthetic Graph Memory materializer.

This module only inspects the explicit synthetic materializer fixture output. It
never scans campaign data, reads corpus/session-memory surfaces, calls LLMs, or
affects retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.graph_memory.materialize import materialize_fixture_file
from src.graph_memory.ontology_ir import GraphBundle, GraphEdge, GraphNode, ProvenanceRef, SourceRef
from src.graph_memory.validation_rules import ValidationIssue, load_taxonomy_registry, validate_bundle_against_taxonomy


@dataclass(frozen=True)
class GraphReport:
    bundle_id: str
    schema_version: str
    taxonomy_registry_version: str
    created_by: str
    node_count: int
    edge_count: int
    node_kinds: dict[str, int]
    edge_predicate_families: dict[str, int]
    lifecycle_states: dict[str, int]
    visibility_states: dict[str, int]
    evidence_roles: dict[str, int]
    authority_states: dict[str, int]
    source_ref_count: int
    provenance_ref_count: int
    validation_issue_count: int
    validation_issue_severities: dict[str, int]
    validation_issue_codes: dict[str, int]
    validation_issue_pairs: dict[str, int]


@dataclass(frozen=True)
class RecordSummary:
    record_id: str
    record_type: str
    label: str
    kind_or_predicate: str
    lifecycle_state: str | None
    visibility_state: str | None
    provenance_count: int
    source_ref_count: int


def _increment(counts: dict[str, int], key: str | None) -> None:
    counts[key or "<none>"] = counts.get(key or "<none>", 0) + 1


def _term(ref: Any) -> str | None:
    return ref.term if ref is not None else None


def _records(bundle: GraphBundle) -> list[GraphNode | GraphEdge]:
    return [*bundle.nodes, *bundle.edges]


def _source_ref_count(provenance: list[ProvenanceRef]) -> int:
    return sum(len(prov.source_refs) for prov in provenance)


def build_graph_report(bundle: GraphBundle, issues: list[ValidationIssue]) -> GraphReport:
    """Build a deterministic report summary for a materialized GraphBundle."""
    node_kinds: dict[str, int] = {}
    edge_predicate_families: dict[str, int] = {}
    lifecycle_states: dict[str, int] = {}
    visibility_states: dict[str, int] = {}
    evidence_roles: dict[str, int] = {}
    authority_states: dict[str, int] = {}
    validation_issue_severities: dict[str, int] = {}
    validation_issue_codes: dict[str, int] = {}
    validation_issue_pairs: dict[str, int] = {}

    for node in bundle.nodes:
        _increment(node_kinds, _term(node.kind))
    for edge in bundle.edges:
        _increment(edge_predicate_families, _term(edge.predicate_family))

    provenance_ref_count = 0
    source_ref_count = 0
    for record in _records(bundle):
        _increment(lifecycle_states, _term(record.lifecycle_state))
        _increment(visibility_states, _term(record.visibility_state))
        provenance_ref_count += len(record.provenance)
        source_ref_count += _source_ref_count(record.provenance)
        for provenance in record.provenance:
            _increment(evidence_roles, _term(provenance.evidence_role))
            _increment(authority_states, _term(provenance.authority_state))

    for issue in issues:
        _increment(validation_issue_severities, issue.severity)
        _increment(validation_issue_codes, issue.code)
        _increment(validation_issue_pairs, f"{issue.severity}/{issue.code}")

    return GraphReport(
        bundle_id=bundle.bundle_id,
        schema_version=bundle.schema_version,
        taxonomy_registry_version=bundle.taxonomy_registry_version,
        created_by=bundle.created_by,
        node_count=len(bundle.nodes),
        edge_count=len(bundle.edges),
        node_kinds=dict(sorted(node_kinds.items())),
        edge_predicate_families=dict(sorted(edge_predicate_families.items())),
        lifecycle_states=dict(sorted(lifecycle_states.items())),
        visibility_states=dict(sorted(visibility_states.items())),
        evidence_roles=dict(sorted(evidence_roles.items())),
        authority_states=dict(sorted(authority_states.items())),
        source_ref_count=source_ref_count,
        provenance_ref_count=provenance_ref_count,
        validation_issue_count=len(issues),
        validation_issue_severities=dict(sorted(validation_issue_severities.items())),
        validation_issue_codes=dict(sorted(validation_issue_codes.items())),
        validation_issue_pairs=dict(sorted(validation_issue_pairs.items())),
    )


def summarize_records(bundle: GraphBundle) -> list[RecordSummary]:
    """Return deterministic per-record summaries for nodes and edges."""
    summaries: list[RecordSummary] = []
    for node in bundle.nodes:
        summaries.append(
            RecordSummary(
                record_id=node.node_id,
                record_type="node",
                label=node.label,
                kind_or_predicate=node.kind.term,
                lifecycle_state=_term(node.lifecycle_state),
                visibility_state=_term(node.visibility_state),
                provenance_count=len(node.provenance),
                source_ref_count=_source_ref_count(node.provenance),
            )
        )
    for edge in bundle.edges:
        summaries.append(
            RecordSummary(
                record_id=edge.edge_id,
                record_type="edge",
                label=edge.label,
                kind_or_predicate=edge.predicate_family.term,
                lifecycle_state=_term(edge.lifecycle_state),
                visibility_state=_term(edge.visibility_state),
                provenance_count=len(edge.provenance),
                source_ref_count=_source_ref_count(edge.provenance),
            )
        )
    return sorted(summaries, key=lambda record: (record.record_type, record.record_id))


def _render_count_table(title: str, first_column: str, counts: dict[str, int]) -> list[str]:
    lines = [f"## {title}", "", f"| {first_column} | Count |", "|---|---:|"]
    if counts:
        lines.extend(f"| {key} | {counts[key]} |" for key in sorted(counts))
    else:
        lines.append("| None | 0 |")
    lines.append("")
    return lines


def _render_validation_issues(report: GraphReport) -> list[str]:
    lines = ["## Validation Issues", "", "| Severity | Code | Count |", "|---|---|---:|"]
    if report.validation_issue_pairs:
        for pair in sorted(report.validation_issue_pairs):
            severity, code = pair.split("/", 1)
            lines.append(f"| {severity} | {code} | {report.validation_issue_pairs[pair]} |")
    else:
        lines.append("| none | none | 0 |")
    lines.append("")
    return lines


def render_graph_report_markdown(report: GraphReport, records: list[RecordSummary]) -> str:
    """Render the graph report as stable, operator-readable Markdown."""
    lines = [
        "# Graph Memory Materializer Report",
        "",
        f"Bundle: `{report.bundle_id}`",
        "",
        f"Schema version: `{report.schema_version}`  ",
        f"Taxonomy registry version: `{report.taxonomy_registry_version}`  ",
        f"Created by: `{report.created_by}`",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Nodes | {report.node_count} |",
        f"| Edges | {report.edge_count} |",
        f"| Provenance refs | {report.provenance_ref_count} |",
        f"| Source refs | {report.source_ref_count} |",
        f"| Validation issues | {report.validation_issue_count} |",
        "",
    ]
    lines.extend(_render_count_table("Node Kinds", "Kind", report.node_kinds))
    lines.extend(_render_count_table("Edge Predicate Families", "Predicate family", report.edge_predicate_families))
    lines.extend(_render_count_table("Lifecycle States", "State", report.lifecycle_states))
    lines.extend(_render_count_table("Visibility States", "State", report.visibility_states))
    lines.extend(_render_count_table("Evidence Roles", "Role", report.evidence_roles))
    lines.extend(_render_count_table("Authority States", "State", report.authority_states))
    lines.extend(_render_validation_issues(report))
    lines.extend([
        "## Records",
        "",
        "| Type | ID | Label | Kind / Predicate | Lifecycle | Visibility | Provenance | Sources |",
        "|---|---|---|---|---|---|---:|---:|",
    ])
    for record in sorted(records, key=lambda item: (item.record_type, item.record_id)):
        lines.append(
            "| "
            + " | ".join(
                [
                    record.record_type,
                    record.record_id,
                    record.label,
                    record.kind_or_predicate,
                    record.lifecycle_state or "",
                    record.visibility_state or "",
                    str(record.provenance_count),
                    str(record.source_ref_count),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def materialize_validate_and_report(
    fixture_path: Path,
    taxonomy_registry_path: Path,
) -> tuple[GraphBundle, GraphReport, list[RecordSummary], list[ValidationIssue]]:
    """Materialize the synthetic fixture, validate it, and build report objects."""
    taxonomy_registry = load_taxonomy_registry(taxonomy_registry_path)
    bundle = materialize_fixture_file(fixture_path)
    result = validate_bundle_against_taxonomy(bundle, taxonomy_registry)
    report = build_graph_report(bundle, result.issues)
    records = summarize_records(bundle)
    return bundle, report, records, result.issues
