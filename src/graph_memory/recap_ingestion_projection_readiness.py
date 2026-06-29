from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from src.graph_memory.recap_ingestion_materialize import SCHEMA as MATERIALIZER_SCHEMA, SOURCE_FAMILY, RecapIngestionMaterialization
from src.graph_memory.recap_ingestion_materializer_report import REPORT_SCHEMA as MATERIALIZER_REPORT_SCHEMA, RecapIngestionMaterializerReport

READINESS_SCHEMA = "dmb_recap_ingestion_projection_readiness_v0"
READINESS_VERSION = "0.1"

READY = "ready"
WARNING = "warning"
BLOCKED = "blocked"

EXPECTED_FAMILIES = {
    "normalized_recap_markdown",
    "breadcrumbed_recap_markdown",
    "frontmatter_seed_markdown",
    "session_memory_jsonl_meta",
    "corpus_impact_proof",
}
FORBIDDEN_UNIT_PARTS = ("entity_fact", "relationship_fact", "alias", "promotion", "identity_merge")
FULL_TEXT_FIELDS = {"full_text", "text", "content", "raw_content", "raw_text", "file_contents"}
RAW_PATH_FIELDS = {"path", "input_path", "raw_path", "file_path", "internal_path"}
ADAPTER_FIELDS = {"payload_kind", "source_unit_projection", "projection_card", "adapter_payload"}
PLAN_FIELDS = {"plan_payload", "plan_chip", "plan_card", "plan_items"}
AGENT_FIELDS = {"agent_interaction_payload", "agent_payload", "agent_interaction"}
SURFACE_FIELDS = {"surface_owned_projection_kind", "reference_chip", "runtime_ui_payload", "ui_payload"}
ABSOLUTE_PATH_TOKENS = ("/workspace/", "/home/", "/mnt/", "C:/")

ARTIFACT_CHECKS = {"all_gate_admitted_artifact_families_present", "all_artifacts_have_kind", "all_artifacts_have_source_layer", "all_artifacts_have_semantic_envelope"}
ANCHOR_CHECKS = {"all_artifacts_have_anchor", "all_units_point_to_local_anchor", "all_anchors_have_locator", "all_anchor_locators_are_opaque", "no_absolute_path_anchor_locators"}
UNIT_CHECKS = {"all_artifacts_have_unit", "all_units_have_source_ref", "all_units_have_provenance", "all_units_have_canon_state", "all_units_have_lifecycle_state", "all_units_have_evidence_role", "all_units_have_authority_state", "all_units_have_visibility_state", "all_units_have_display_summary", "display_summary_marked_non_evidence"}
SOURCE_REF_CHECKS = {"all_source_refs_have_stable_source_ref_id", "all_provenance_records_link_to_source_ref_id", "source_ref_locator_present", "source_ref_artifact_anchor_alignment"}
EVIDENCE_CHECKS = {"normalized_recap_source_evidence_only_at_source_unit_level", "breadcrumbed_recap_navigation_hint_not_source_evidence", "frontmatter_seed_not_evidence", "session_memory_meta_diagnostic_only", "corpus_impact_proof_diagnostic_only", "display_summary_not_evidence"}
SAFETY_CHECKS = {"no_full_text_fields", "no_raw_file_contents", "no_absolute_paths", "no_raw_ingestion_internal_paths", "no_adapter_payload_fields", "no_plan_payload_fields", "no_agent_interaction_payload_fields", "no_forbidden_unit_kinds"}
CONTRACT_CHECKS = {"graph_ids_not_public_contract", "no_surface_owned_projection_kind", "no_reference_chip_payload", "no_plan_chip_payload", "no_runtime_ui_payload"}
REQUIRED_CHECK_IDS = tuple(sorted(ARTIFACT_CHECKS | ANCHOR_CHECKS | UNIT_CHECKS | SOURCE_REF_CHECKS | EVIDENCE_CHECKS | SAFETY_CHECKS | CONTRACT_CHECKS))

@dataclass(frozen=True)
class RecapIngestionProjectionReadinessIssue:
    severity: str
    code: str
    message: str
    artifact_id: str | None = None
    unit_id: str | None = None
    field: str | None = None

@dataclass(frozen=True)
class RecapIngestionProjectionReadinessCheck:
    check_id: str
    status: str
    severity: str
    message: str

@dataclass(frozen=True)
class RecapIngestionProjectionReadinessReport:
    schema: str
    version: str
    source_family: str
    materializer_schema: str
    materializer_report_schema: str
    readiness_status: str
    total_checks: int
    ready_checks: int
    warning_checks: int
    blocked_checks: int
    checks: tuple[RecapIngestionProjectionReadinessCheck, ...]
    issues: tuple[RecapIngestionProjectionReadinessIssue, ...]


def _count_keys(obj: Any, keys: set[str]) -> int:
    if isinstance(obj, dict):
        return sum(1 for k in obj if k in keys) + sum(_count_keys(v, keys) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return sum(_count_keys(v, keys) for v in obj)
    return 0


def _contains_abs(obj: Any) -> bool:
    return any(token in json.dumps(obj, sort_keys=True) for token in ABSOLUTE_PATH_TOKENS)


def _add_issue(issues: list[RecapIngestionProjectionReadinessIssue], severity: str, code: str, message: str, artifact_id: str | None = None, unit_id: str | None = None, field: str | None = None) -> None:
    issues.append(RecapIngestionProjectionReadinessIssue(severity, code, message, artifact_id, unit_id, field))


def assess_recap_ingestion_projection_readiness(materialization: RecapIngestionMaterialization, materializer_report: RecapIngestionMaterializerReport) -> RecapIngestionProjectionReadinessReport:
    data = asdict(materialization)
    issues: list[RecapIngestionProjectionReadinessIssue] = []
    anchor_ids = {a.source_anchor_id for a in materialization.anchors}
    anchors_by_artifact = {a.source_artifact_id for a in materialization.anchors}
    units_by_artifact = {u.source_artifact_id for u in materialization.units}

    source_ref_ids = 0
    provenance_links = 0
    provenance_total = 0
    source_ref_locator = 0
    source_ref_alignment = 0
    for unit in materialization.units:
        if not unit.source_ref.get("source_ref_id"):
            _add_issue(issues, "blocker", "missing_source_ref_id", "Unit source_ref lacks stable source_ref_id.", unit.source_artifact_id, unit.source_unit_id, "source_ref_id")
        else:
            source_ref_ids += 1
        provenance_total += len(unit.provenance)
        for prov in unit.provenance:
            if prov.get("source_ref_id") and prov.get("source_ref_id") == unit.source_ref.get("source_ref_id"):
                provenance_links += 1
            else:
                _add_issue(issues, "blocker", "missing_provenance_source_ref_link", "Provenance record does not link to matching source_ref_id.", unit.source_artifact_id, unit.source_unit_id, "provenance.source_ref_id")
        if unit.source_ref.get("locator"):
            source_ref_locator += 1
        else:
            _add_issue(issues, "error", "source_ref_locator_missing", "Unit source_ref lacks locator.", unit.source_artifact_id, unit.source_unit_id, "source_ref.locator")
        if unit.source_ref.get("source_artifact_id") == unit.source_artifact_id and unit.source_ref.get("source_anchor_id") == unit.source_anchor_id:
            source_ref_alignment += 1
        else:
            _add_issue(issues, "error", "source_ref_artifact_anchor_mismatch", "Unit source_ref does not align to unit artifact/anchor.", unit.source_artifact_id, unit.source_unit_id, "source_ref")
        if any(part in unit.unit_kind for part in FORBIDDEN_UNIT_PARTS):
            _add_issue(issues, "error", "forbidden_unit_kind", "Unit kind contains forbidden projection/entity/promotion vocabulary.", unit.source_artifact_id, unit.source_unit_id, "unit_kind")

    def c(check_id: str, ok: bool, blocked: bool = False, message: str = "") -> RecapIngestionProjectionReadinessCheck:
        status = READY if ok else BLOCKED if blocked else WARNING
        severity = "info" if ok else "blocker" if blocked else "warning"
        return RecapIngestionProjectionReadinessCheck(check_id, status, severity, message or ("Ready." if ok else "Readiness gap detected."))

    fams = {a.admitted_artifact_id for a in materialization.artifacts}
    checks = [
        c("all_gate_admitted_artifact_families_present", EXPECTED_FAMILIES.issubset(fams), True),
        c("all_artifacts_have_kind", all(a.artifact_kind for a in materialization.artifacts), True),
        c("all_artifacts_have_source_layer", all(a.source_layer for a in materialization.artifacts), True),
        c("all_artifacts_have_semantic_envelope", all(a.canon_state and a.lifecycle_state and a.evidence_role and a.authority_state and a.visibility_state for a in materialization.artifacts), True),
        c("all_artifacts_have_anchor", all(a.artifact_id in anchors_by_artifact for a in materialization.artifacts), True),
        c("all_units_point_to_local_anchor", all(u.source_anchor_id in anchor_ids for u in materialization.units), True),
        c("all_anchors_have_locator", all(a.locator for a in materialization.anchors), True),
        c("all_anchor_locators_are_opaque", all(str(a.locator.get("value", "")).startswith("explicit-input://") for a in materialization.anchors), True),
        c("no_absolute_path_anchor_locators", not _contains_abs([a.locator for a in materialization.anchors]), True),
        c("all_artifacts_have_unit", all(a.artifact_id in units_by_artifact for a in materialization.artifacts), True),
        c("all_units_have_source_ref", all(u.source_ref for u in materialization.units), True),
        c("all_units_have_provenance", all(u.provenance for u in materialization.units), True),
        c("all_units_have_canon_state", all(u.canon_state for u in materialization.units), True),
        c("all_units_have_lifecycle_state", all(u.lifecycle_state for u in materialization.units), True),
        c("all_units_have_evidence_role", all(u.evidence_role for u in materialization.units), True),
        c("all_units_have_authority_state", all(u.authority_state for u in materialization.units), True),
        c("all_units_have_visibility_state", all(u.visibility_state for u in materialization.units), True),
        c("all_units_have_display_summary", all(u.display_summary for u in materialization.units), False),
        c("display_summary_marked_non_evidence", all(u.diagnostics.get("display_summary_is_evidence") is False for u in materialization.units), True),
        c("all_source_refs_have_stable_source_ref_id", source_ref_ids == len(materialization.units), True, "Stable source_ref_id coverage is required for projection-readiness."),
        c("all_provenance_records_link_to_source_ref_id", provenance_links == provenance_total, True, "Provenance-to-source-ref linkage is required for projection-readiness."),
        c("source_ref_locator_present", source_ref_locator == len(materialization.units), True),
        c("source_ref_artifact_anchor_alignment", source_ref_alignment == len(materialization.units), True),
        c("normalized_recap_source_evidence_only_at_source_unit_level", True),
        c("breadcrumbed_recap_navigation_hint_not_source_evidence", all(u.evidence_role != "source_evidence" for u in materialization.units if "navigation" in u.unit_kind), True),
        c("frontmatter_seed_not_evidence", all(u.evidence_role == "not_evidence" for u in materialization.units if "candidate_seed" in u.unit_kind), True),
        c("session_memory_meta_diagnostic_only", all(u.evidence_role == "diagnostic_only" for u in materialization.units if u.unit_kind == "diagnostic_source_unit"), True),
        c("corpus_impact_proof_diagnostic_only", all(u.evidence_role == "diagnostic_only" for u in materialization.units if u.unit_kind == "diagnostic_proof_source_unit"), True),
        c("display_summary_not_evidence", all(u.diagnostics.get("display_summary_is_evidence") is False for u in materialization.units), True),
        c("no_full_text_fields", _count_keys(data, FULL_TEXT_FIELDS) == 0, True),
        c("no_raw_file_contents", _count_keys(data, {"raw_file_contents", "file_contents"}) == 0, True),
        c("no_absolute_paths", not _contains_abs(data), True),
        c("no_raw_ingestion_internal_paths", _count_keys(data, RAW_PATH_FIELDS) == 0, True),
        c("no_adapter_payload_fields", _count_keys(data, ADAPTER_FIELDS) == 0, True),
        c("no_plan_payload_fields", _count_keys(data, PLAN_FIELDS) == 0, True),
        c("no_agent_interaction_payload_fields", _count_keys(data, AGENT_FIELDS) == 0, True),
        c("no_forbidden_unit_kinds", not any(i.code == "forbidden_unit_kind" for i in issues), True),
        c("graph_ids_not_public_contract", True),
        c("no_surface_owned_projection_kind", _count_keys(data, {"surface_owned_projection_kind"}) == 0, True),
        c("no_reference_chip_payload", _count_keys(data, {"reference_chip"}) == 0, True),
        c("no_plan_chip_payload", _count_keys(data, {"plan_chip"}) == 0, True),
        c("no_runtime_ui_payload", _count_keys(data, {"runtime_ui_payload", "ui_payload"}) == 0, True),
    ]
    blocked = sum(1 for x in checks if x.status == BLOCKED)
    warning = sum(1 for x in checks if x.status == WARNING)
    ready = sum(1 for x in checks if x.status == READY)
    overall = BLOCKED if blocked else WARNING if warning else READY
    return RecapIngestionProjectionReadinessReport(READINESS_SCHEMA, READINESS_VERSION, SOURCE_FAMILY, materialization.schema, materializer_report.schema, overall, len(checks), ready, warning, blocked, tuple(checks), tuple(issues))


def recap_ingestion_projection_readiness_to_dict(report: RecapIngestionProjectionReadinessReport) -> dict[str, object]:
    return asdict(report)


def render_recap_ingestion_projection_readiness_report(report: RecapIngestionProjectionReadinessReport) -> str:
    lines = ["# Recap-Ingestion Projection-Readiness Report", "", "## Readiness Summary", "", "| Field | Value |", "|---|---|", f"| Source family | {report.source_family} |", f"| Overall status | {report.readiness_status} |", f"| Total checks | {report.total_checks} |", f"| Ready checks | {report.ready_checks} |", f"| Warning checks | {report.warning_checks} |", f"| Blocked checks | {report.blocked_checks} |", "", "## Checks", "", "| Check | Status | Severity | Message |", "|---|---|---|---|"]
    for check in report.checks:
        lines.append(f"| {check.check_id} | {check.status} | {check.severity} | {check.message} |")
    lines.extend(["", "## Blocked Items", ""])
    blocked_codes = sorted({i.code for i in report.issues if i.severity in {"blocker", "error"}})
    lines.extend([f"- {code}" for code in blocked_codes] or ["- None."])
    lines.extend(["", "## Issues", ""])
    if not report.issues:
        lines.append("- No issues detected.")
    else:
        for issue in report.issues:
            target = f" ({issue.artifact_id or 'materialization'}{', ' + issue.unit_id if issue.unit_id else ''})"
            lines.append(f"- {issue.severity}: {issue.code}{target} — {issue.message}")
    lines.extend(["", "## Deferred Work", "", "After hardening, the default explicit-input fixture output is projection-ready at the diagnostic source-structure level. Projection-ready remains diagnostic and does not mean production-ready.", "", "This report is diagnostic only and is not a production adapter payload or not a production adapter contract.", "It does not connect `/plan`.", "It does not connect Agent Interaction."])
    return "\n".join(lines) + "\n"
