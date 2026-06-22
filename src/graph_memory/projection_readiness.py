"""Diagnostic projection-readiness report for materialized graph source units.

This module measures whether existing graph/source-unit records expose enough
metadata for a future projection-safe surface adapter. It does not implement an
adapter or produce runtime UI payloads.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import blake2s
from typing import Any

from src.graph_memory.ontology_ir import GraphBundle, GraphNode, ProvenanceRef, SourceRef
from src.graph_memory.session_memory_materialize import ADMITTED_SOURCE_FAMILY, CREATED_BY

SCHEMA = "dmb_projection_readiness_report_v0"
VERSION = "0.1"
ADAPTER_KEY = "session_memory_unit"
REQUIRED_FIELDS = (
    "adapter_key",
    "ref_id",
    "label",
    "source_anchor",
    "source_ref",
    "provenance",
    "evidence_role",
    "authority_state",
    "visibility_state",
    "lifecycle_state",
    "canon_state",
)
FORBIDDEN_TEXT_KEYS = {"lexical_plain", "full_text", "markdown_body", "raw_text", "recap_text"}
FORBIDDEN_INTERNAL_MARKERS = ("_normalized/", "_breadcrumbed/", ".records_meta.jsonl", "corpus_impact")


@dataclass(frozen=True)
class ProjectionReadinessIssue:
    severity: str
    code: str
    message: str
    node_id: str | None = None
    field: str | None = None


@dataclass(frozen=True)
class ProjectionReadinessRecord:
    node_id: str
    ready: bool
    readiness_state: str
    adapter_key: str
    ref_id: str
    label: str
    required_field_status: dict[str, bool]
    issues: tuple[ProjectionReadinessIssue, ...]
    diagnostics: dict[str, str | int | bool | None]


@dataclass(frozen=True)
class ProjectionReadinessReport:
    schema: str
    version: str
    source_family: str
    bundle_id: str
    total_source_units: int
    ready_count: int
    degraded_count: int
    blocked_count: int
    missing_field_counts: dict[str, int]
    issue_counts: dict[str, int]
    records: tuple[ProjectionReadinessRecord, ...]


def _term(value: Any) -> str | None:
    return getattr(value, "term", None) if value is not None else None


def _first_source_ref(provenance: list[ProvenanceRef]) -> SourceRef | None:
    for item in provenance:
        if item.source_refs:
            return item.source_refs[0]
    return None


def _safe_ref_id(bundle_id: str, node_id: str) -> str:
    digest = blake2s(f"{bundle_id}|{node_id}".encode("utf-8"), digest_size=8).hexdigest()
    return f"session-memory-unit:{digest}"


def _label(node: GraphNode) -> tuple[str, ProjectionReadinessIssue | None]:
    session_number = node.properties.get("session_number")
    unit_id = node.properties.get("unit_id")
    if isinstance(session_number, int) and isinstance(unit_id, str) and unit_id.strip():
        return f"Session {session_number} memory unit {unit_id}", None
    if isinstance(node.label, str) and node.label.strip():
        return node.label, ProjectionReadinessIssue("warning", "weak_label", "Only the graph node label is available; no narrative label is invented.", node.node_id, "label")
    return "", ProjectionReadinessIssue("error", "missing_required_field", "No safe label can be derived.", node.node_id, "label")


def _assess_node(bundle: GraphBundle, node: GraphNode) -> ProjectionReadinessRecord:
    issues: list[ProjectionReadinessIssue] = []
    status = dict.fromkeys(REQUIRED_FIELDS, False)
    if bundle.created_by == CREATED_BY:
        status["adapter_key"] = True
    ref_id = _safe_ref_id(bundle.bundle_id, node.node_id)
    status["ref_id"] = True
    label, label_issue = _label(node)
    status["label"] = bool(label)
    if label_issue:
        issues.append(label_issue)
    source_ref = _first_source_ref(node.provenance)
    status["source_ref"] = source_ref is not None
    status["source_anchor"] = source_ref is not None and bool(source_ref.anchor) and source_ref.line_start is not None
    status["provenance"] = bool(node.provenance)
    provenance = node.provenance[0] if node.provenance else None
    status["evidence_role"] = provenance is not None and _term(provenance.evidence_role) is not None
    status["authority_state"] = provenance is not None and _term(provenance.authority_state) is not None
    status["visibility_state"] = _term(node.visibility_state) is not None or (provenance is not None and _term(provenance.visibility_state) is not None)
    status["lifecycle_state"] = _term(node.lifecycle_state) is not None
    status["canon_state"] = "canon_state" in node.properties and isinstance(node.properties.get("canon_state"), str) and bool(str(node.properties.get("canon_state")).strip())

    for field, present in status.items():
        if not present:
            issues.append(ProjectionReadinessIssue("error", "missing_required_field", f"Required semantic-envelope field is missing or unsafe: {field}.", node.node_id, field))
    if status["evidence_role"] and _term(provenance.evidence_role) != "diagnostic_only":
        issues.append(ProjectionReadinessIssue("warning", "unexpected_evidence_role", "Evidence role is not the expected diagnostic-only role.", node.node_id, "evidence_role"))
    missing = [field for field, present in status.items() if not present]
    readiness_state = "blocked" if missing else ("degraded" if any(issue.severity == "warning" for issue in issues) else "ready")
    diagnostics = {
        "display_summary_status": "not_evidence",
        "diagnostics_status": "report_only",
        "evidence_role": _term(provenance.evidence_role) if provenance else None,
        "authority_state": _term(provenance.authority_state) if provenance else None,
        "visibility_state": _term(node.visibility_state) or (_term(provenance.visibility_state) if provenance else None),
        "lifecycle_state": _term(node.lifecycle_state),
        "canon_state": str(node.properties.get("canon_state")) if status["canon_state"] else None,
        "source_reference_present": source_ref is not None,
        "source_anchor_present": status["source_anchor"],
    }
    return ProjectionReadinessRecord(node.node_id, readiness_state == "ready", readiness_state, ADAPTER_KEY if status["adapter_key"] else "", ref_id, label, status, tuple(issues), diagnostics)


def assess_projection_readiness(bundle: GraphBundle) -> ProjectionReadinessReport:
    records = tuple(_assess_node(bundle, node) for node in bundle.nodes if node.kind.term == "source_unit")
    missing_counts = {field: sum(1 for record in records if not record.required_field_status[field]) for field in REQUIRED_FIELDS}
    issue_counts: dict[str, int] = {}
    for record in records:
        for issue in record.issues:
            issue_counts[issue.code] = issue_counts.get(issue.code, 0) + 1
    return ProjectionReadinessReport(
        schema=SCHEMA,
        version=VERSION,
        source_family=ADMITTED_SOURCE_FAMILY,
        bundle_id=bundle.bundle_id,
        total_source_units=len(records),
        ready_count=sum(1 for record in records if record.readiness_state == "ready"),
        degraded_count=sum(1 for record in records if record.readiness_state == "degraded"),
        blocked_count=sum(1 for record in records if record.readiness_state == "blocked"),
        missing_field_counts=missing_counts,
        issue_counts=issue_counts,
        records=records,
    )


def projection_readiness_report_to_dict(report: ProjectionReadinessReport) -> dict[str, object]:
    return asdict(report)


def render_projection_readiness_report(report: ProjectionReadinessReport) -> str:
    lines = [
        "# Projection Readiness Report",
        "",
        f"Bundle: `{report.bundle_id}`",
        f"Source family: `{report.source_family}`",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Total source units | {report.total_source_units} |",
        f"| Ready | {report.ready_count} |",
        f"| Degraded | {report.degraded_count} |",
        f"| Blocked | {report.blocked_count} |",
        "",
        "## Missing Field Counts",
        "",
        "| Field | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| {field} | {count} |" for field, count in report.missing_field_counts.items())
    lines.extend(["", "## Issue Counts", "", "| Code | Count |", "|---|---:|"])
    if report.issue_counts:
        lines.extend(f"| {code} | {count} |" for code, count in sorted(report.issue_counts.items()))
    else:
        lines.append("| none | 0 |")
    lines.extend(["", "## Records", "", "| Node ID | Readiness | Missing Fields | Evidence Role | Lifecycle | Canon | Notes |", "|---|---|---|---|---|---|---|"])
    for record in report.records:
        missing = ", ".join(field for field, present in record.required_field_status.items() if not present) or "none"
        notes = "; ".join(sorted({issue.message for issue in record.issues})) or "ok"
        lines.append(f"| `{record.node_id}` | {record.readiness_state} | {missing} | {record.diagnostics.get('evidence_role') or 'missing'} | {record.diagnostics.get('lifecycle_state') or 'missing'} | {record.diagnostics.get('canon_state') or 'missing'} | {notes} |")
    return "\n".join(lines) + "\n"
