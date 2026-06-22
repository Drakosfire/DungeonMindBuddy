from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from src.graph_memory.recap_ingestion_materialize import (
    CREATED_BY,
    SCHEMA as MATERIALIZER_SCHEMA,
    SOURCE_FAMILY,
    RecapIngestionMaterialization,
    recap_ingestion_materialization_to_dict,
)

REPORT_SCHEMA = "dmb_recap_ingestion_source_artifact_materializer_report_v0"
REPORT_VERSION = "0.1"
ADAPTER_FIELDS = {"payload_kind", "source_unit_projection", "projection_card", "surface_owned_projection_kind", "plan_chip", "agent_interaction_payload"}
FORBIDDEN_UNIT_PARTS = ("entity_fact", "relationship_fact", "alias", "promotion", "identity_merge")
FULL_TEXT_FIELDS = {"full_text", "text", "content", "raw_content", "raw_text", "file_contents"}
ABSOLUTE_PATH_TOKENS = ("/workspace/", "/home/", "/mnt/", "C:\\")
KNOWN_ARTIFACT_FAMILIES = {
    "normalized_recap_markdown",
    "breadcrumbed_recap_markdown",
    "frontmatter_seed_markdown",
    "session_memory_jsonl_meta",
    "corpus_impact_proof",
}
EXPECTED_DEFAULTS = {
    "normalized_recap_markdown": ("source_evidence", "played_canon", "ingested", "system_derived", "gm_private"),
    "breadcrumbed_recap_markdown": ("navigation_hint", "played_canon", "indexed", "system_derived", "gm_private"),
    "frontmatter_seed_markdown": ("not_evidence", "planning_scaffold", "candidate", "system_derived", "internal_diagnostic"),
    "session_memory_jsonl_meta": ("diagnostic_only", "candidate_extraction", "candidate", "system_derived", "internal_diagnostic"),
    "corpus_impact_proof": ("diagnostic_only", "diagnostic_only", "diagnostic", "diagnostic", "internal_diagnostic"),
}


@dataclass(frozen=True)
class RecapIngestionMaterializerReportIssue:
    severity: str
    code: str
    message: str
    artifact_id: str | None = None
    unit_id: str | None = None
    field: str | None = None


@dataclass(frozen=True)
class RecapIngestionArtifactReportRow:
    admitted_artifact_id: str
    artifact_kind: str
    source_layer: str
    artifact_id: str
    anchor_count: int
    unit_count: int
    evidence_role: str
    canon_state: str
    lifecycle_state: str
    authority_state: str
    visibility_state: str
    diagnostic_count: int
    issue_count: int


@dataclass(frozen=True)
class RecapIngestionMaterializerReport:
    schema: str
    version: str
    source_family: str
    materializer_schema: str
    materializer_created_by: str
    total_artifacts: int
    total_anchors: int
    total_units: int
    total_source_refs: int
    total_provenance_records: int
    total_diagnostics: int
    artifact_rows: tuple[RecapIngestionArtifactReportRow, ...]
    state_counts: dict[str, dict[str, int]]
    structural_coverage: dict[str, int | bool]
    issue_counts: dict[str, int]
    issues: tuple[RecapIngestionMaterializerReportIssue, ...]


def _has_key(obj: Any, keys: set[str]) -> bool:
    if isinstance(obj, dict):
        return any(key in keys or _has_key(value, keys) for key, value in obj.items())
    if isinstance(obj, (list, tuple)):
        return any(_has_key(item, keys) for item in obj)
    return False


def _count_keys(obj: Any, keys: set[str]) -> int:
    if isinstance(obj, dict):
        return sum(1 for key in obj if key in keys) + sum(_count_keys(value, keys) for value in obj.values())
    if isinstance(obj, (list, tuple)):
        return sum(_count_keys(item, keys) for item in obj)
    return 0


def _contains_absolute_path(obj: Any) -> bool:
    output = json.dumps(obj, sort_keys=True)
    return any(token in output for token in ABSOLUTE_PATH_TOKENS)


def _add(issues: list[RecapIngestionMaterializerReportIssue], severity: str, code: str, message: str, artifact_id: str | None = None, unit_id: str | None = None, field: str | None = None) -> None:
    issues.append(RecapIngestionMaterializerReportIssue(severity, code, message, artifact_id, unit_id, field))


def analyze_recap_ingestion_materializer_output(materialization: RecapIngestionMaterialization) -> RecapIngestionMaterializerReport:
    data = recap_ingestion_materialization_to_dict(materialization)
    anchors_by_artifact: dict[str, list[Any]] = {}
    for anchor in materialization.anchors:
        anchors_by_artifact.setdefault(anchor.source_artifact_id, []).append(anchor)
    units_by_artifact: dict[str, list[Any]] = {}
    for unit in materialization.units:
        units_by_artifact.setdefault(unit.source_artifact_id, []).append(unit)

    issues: list[RecapIngestionMaterializerReportIssue] = []
    anchor_ids = {anchor.source_anchor_id for anchor in materialization.anchors}
    for artifact in materialization.artifacts:
        if artifact.admitted_artifact_id not in KNOWN_ARTIFACT_FAMILIES:
            _add(issues, "warning", "unknown_artifact_family", "Artifact family is not recognized by report v0.", artifact.artifact_id)
        if not anchors_by_artifact.get(artifact.artifact_id):
            _add(issues, "error", "missing_artifact_anchor", "Artifact has no source anchor.", artifact.artifact_id, field="anchors")
        if not units_by_artifact.get(artifact.artifact_id):
            _add(issues, "error", "missing_artifact_unit", "Artifact has no source unit.", artifact.artifact_id, field="units")
        expected = EXPECTED_DEFAULTS.get(artifact.admitted_artifact_id)
        actual = (artifact.evidence_role, artifact.canon_state, artifact.lifecycle_state, artifact.authority_state, artifact.visibility_state)
        if expected and actual != expected:
            _add(issues, "warning", "semantic_default_mismatch", "Artifact semantic defaults differ from materializer gate expectations.", artifact.artifact_id)

    total_source_refs = 0
    total_provenance_records = 0
    source_ref_id_units = 0
    linked_provenance = 0
    display_non_evidence_units = 0
    forbidden_unit_kind_count = 0
    for unit in materialization.units:
        if unit.source_ref:
            total_source_refs += 1
        else:
            _add(issues, "error", "missing_unit_source_ref", "Unit is missing source_ref.", unit.source_artifact_id, unit.source_unit_id, "source_ref")
        total_provenance_records += len(unit.provenance)
        if not unit.provenance:
            _add(issues, "error", "missing_unit_provenance", "Unit is missing provenance.", unit.source_artifact_id, unit.source_unit_id, "provenance")
        if not unit.canon_state:
            _add(issues, "error", "missing_unit_canon_state", "Unit is missing canon_state.", unit.source_artifact_id, unit.source_unit_id, "canon_state")
        if unit.diagnostics.get("display_summary_is_evidence") is False:
            display_non_evidence_units += 1
        else:
            _add(issues, "error", "display_summary_evidence_boundary_missing", "Unit does not mark display_summary as non-evidence.", unit.source_artifact_id, unit.source_unit_id, "display_summary")
        if "source_ref_id" in unit.source_ref and unit.source_ref.get("source_ref_id"):
            source_ref_id_units += 1
        else:
            _add(issues, "warning", "missing_source_ref_id", "Unit source_ref lacks stable source_ref_id.", unit.source_artifact_id, unit.source_unit_id, "source_ref_id")
        for provenance in unit.provenance:
            if provenance.get("source_ref_id"):
                linked_provenance += 1
            else:
                _add(issues, "warning", "missing_provenance_source_ref_link", "Provenance record does not link to source_ref_id.", unit.source_artifact_id, unit.source_unit_id, "provenance.source_ref_id")
        if any(part in unit.unit_kind for part in FORBIDDEN_UNIT_PARTS):
            forbidden_unit_kind_count += 1
            _add(issues, "error", "forbidden_unit_kind", "Unit kind contains projection/entity/promotion vocabulary.", unit.source_artifact_id, unit.source_unit_id, "unit_kind")
        if unit.source_anchor_id not in anchor_ids:
            _add(issues, "error", "missing_artifact_anchor", "Unit points to an unknown source anchor.", unit.source_artifact_id, unit.source_unit_id, "source_anchor_id")

    full_text_field_count = _count_keys(data, FULL_TEXT_FIELDS)
    adapter_payload_field_count = _count_keys(data, ADAPTER_FIELDS)
    absolute_path_leak_count = int(_contains_absolute_path(data))
    for count, code, msg in (
        (full_text_field_count, "full_text_field_leak", "Full text field appears in materializer output."),
        (adapter_payload_field_count, "adapter_payload_field_leak", "Adapter payload field appears in materializer output."),
        (absolute_path_leak_count, "absolute_path_leak", "Absolute path appears in materializer output."),
    ):
        for _ in range(count):
            _add(issues, "error", code, msg)

    issue_by_artifact = Counter(issue.artifact_id for issue in issues if issue.artifact_id)
    artifact_rows = tuple(
        RecapIngestionArtifactReportRow(
            artifact.admitted_artifact_id,
            artifact.artifact_kind,
            artifact.source_layer,
            artifact.artifact_id,
            len(anchors_by_artifact.get(artifact.artifact_id, [])),
            len(units_by_artifact.get(artifact.artifact_id, [])),
            artifact.evidence_role,
            artifact.canon_state,
            artifact.lifecycle_state,
            artifact.authority_state,
            artifact.visibility_state,
            sum(1 for diagnostic in materialization.diagnostics if diagnostic.get("admitted_artifact_id") == artifact.admitted_artifact_id),
            issue_by_artifact[artifact.artifact_id],
        )
        for artifact in materialization.artifacts
    )
    state_counts = {
        "evidence_role": dict(Counter(artifact.evidence_role for artifact in materialization.artifacts)),
        "canon_state": dict(Counter(artifact.canon_state for artifact in materialization.artifacts)),
        "lifecycle_state": dict(Counter(artifact.lifecycle_state for artifact in materialization.artifacts)),
        "authority_state": dict(Counter(artifact.authority_state for artifact in materialization.artifacts)),
        "visibility_state": dict(Counter(artifact.visibility_state for artifact in materialization.artifacts)),
    }
    structural_coverage: dict[str, int | bool] = {
        "all_artifacts_have_anchor": all(row.anchor_count > 0 for row in artifact_rows),
        "all_artifacts_have_unit": all(row.unit_count > 0 for row in artifact_rows),
        "all_units_have_source_ref": total_source_refs == len(materialization.units),
        "all_units_have_provenance": all(bool(unit.provenance) for unit in materialization.units),
        "all_units_have_canon_state": all(bool(unit.canon_state) for unit in materialization.units),
        "all_units_have_display_summary": all(bool(unit.display_summary) for unit in materialization.units),
        "all_units_have_display_summary_marked_non_evidence": display_non_evidence_units == len(materialization.units),
        "all_units_have_source_ref_id": source_ref_id_units == len(materialization.units),
        "all_provenance_records_link_to_source_ref_id": linked_provenance == total_provenance_records,
        "absolute_path_leak_count": absolute_path_leak_count,
        "full_text_field_count": full_text_field_count,
        "adapter_payload_field_count": adapter_payload_field_count,
        "forbidden_unit_kind_count": forbidden_unit_kind_count,
    }
    return RecapIngestionMaterializerReport(
        REPORT_SCHEMA,
        REPORT_VERSION,
        materialization.source_family,
        materialization.schema,
        materialization.created_by,
        len(materialization.artifacts),
        len(materialization.anchors),
        len(materialization.units),
        total_source_refs,
        total_provenance_records,
        len(materialization.diagnostics),
        artifact_rows,
        state_counts,
        structural_coverage,
        dict(Counter(issue.code for issue in issues)),
        tuple(issues),
    )


def recap_ingestion_materializer_report_to_dict(report: RecapIngestionMaterializerReport) -> dict[str, object]:
    return asdict(report)


def render_recap_ingestion_materializer_report(report: RecapIngestionMaterializerReport) -> str:
    lines = [
        "# Recap-Ingestion Source Artifact Materializer Diagnostics Report",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Source artifacts | {report.total_artifacts} |",
        f"| Source anchors | {report.total_anchors} |",
        f"| Source units | {report.total_units} |",
        f"| Source refs | {report.total_source_refs} |",
        f"| Provenance records | {report.total_provenance_records} |",
        f"| Diagnostics | {report.total_diagnostics} |",
        f"| Issues | {len(report.issues)} |",
        "",
        "## Artifact Rows",
        "",
        "| Artifact | Kind | Anchors | Units | Evidence | Canon | Lifecycle | Issues |",
        "|---|---|---:|---:|---|---|---|---:|",
    ]
    for row in report.artifact_rows:
        lines.append(f"| {row.admitted_artifact_id} | {row.artifact_kind} | {row.anchor_count} | {row.unit_count} | {row.evidence_role} | {row.canon_state} | {row.lifecycle_state} | {row.issue_count} |")
    lines.extend(["", "## State Counts", ""])
    headings = {"evidence_role": "Evidence Roles", "canon_state": "Canon States", "lifecycle_state": "Lifecycle States", "authority_state": "Authority States", "visibility_state": "Visibility States"}
    for key, heading in headings.items():
        lines.extend([f"### {heading}", "", "| State | Count |", "|---|---:|"])
        for state, count in sorted(report.state_counts.get(key, {}).items()):
            lines.append(f"| {state} | {count} |")
        lines.append("")
    lines.extend(["## Structural Coverage", "", "| Check | Status |", "|---|---|"])
    for check, value in report.structural_coverage.items():
        status = "ready" if value is True or value == 0 else "missing" if value is False else str(value)
        lines.append(f"| {check} | {status} |")
    lines.extend(["", "## Issues", ""])
    if not report.issues:
        lines.append("- No issues detected.")
    else:
        for issue in report.issues:
            target = f" ({issue.artifact_id or 'materialization'}{', ' + issue.unit_id if issue.unit_id else ''})"
            lines.append(f"- {issue.severity}: {issue.code}{target} — {issue.message}")
    lines.extend(["", "display_summary is not evidence.", "This report is diagnostic only and is not a production adapter payload."])
    return "\n".join(lines) + "\n"
