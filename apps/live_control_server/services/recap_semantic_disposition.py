"""Exact-run semantic hold for operator-corrected recap evidence.

This is a SERVER interpretation of canonical APP-STATE run metadata. Evidence
validity and lifecycle REVIEWABLE do not imply semantic acceptance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from graph_memory.ingestion.extraction_run import (
    FROZEN_COMPONENT_STATUSES,
    ExtractionRun,
    ExtractionRunStatus,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    RECAP_PROFILE_ID,
    RECAP_PROFILE_VERSION,
)

DERIVATION = "operator_recap_literal_evidence_correction_v1"
CANDIDATE_DERIVATION = "operator_recap_semantic_candidate_correction_v1"
CANDIDATE_DERIVATION_V2 = "operator_recap_semantic_candidate_correction_v2"
CANDIDATE_DERIVATION_V3 = "operator_recap_semantic_candidate_correction_v3"
CANDIDATE_DERIVATION_V4 = "operator_recap_semantic_candidate_correction_v4"
CANDIDATE_DERIVATION_V5 = "operator_recap_semantic_candidate_correction_v5"
CANDIDATE_DERIVATION_V6 = "operator_recap_semantic_candidate_correction_v6"
MANIFEST_SCHEMA_V6 = "dmb_recap_semantic_candidate_manifest_v6"
MANIFEST_SCHEMA_V2 = "dmb_recap_semantic_candidate_manifest_v2"
MANIFEST_SCHEMA_V3 = "dmb_recap_semantic_candidate_manifest_v3"
MANIFEST_SCHEMA_V4 = "dmb_recap_semantic_candidate_manifest_v4"
MANIFEST_SCHEMA_V5 = "dmb_recap_semantic_candidate_manifest_v5"
DISPOSITION_VERSION = 1
EFFECT_KEY = "recap_semantic_disposition"
HOLD_REASON = "Corrected recap evidence awaits an explicit semantic review decision."
REJECTED_REASON = "Corrected recap evidence was rejected by semantic review."


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _sha(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.removeprefix("sha256:").lower()
    if len(cleaned) != 64 or any(char not in "0123456789abcdef" for char in cleaned):
        return None
    return cleaned


def is_recap_correction(run: ExtractionRun) -> bool:
    return run.lineage.get("derivation") in {
        DERIVATION,
        CANDIDATE_DERIVATION,
        CANDIDATE_DERIVATION_V2,
        CANDIDATE_DERIVATION_V3,
        CANDIDATE_DERIVATION_V4,
        CANDIDATE_DERIVATION_V5,
        CANDIDATE_DERIVATION_V6,
    }


@dataclass(frozen=True)
class RecapSemanticAssessment:
    marked: bool
    accepted: bool
    basis_sha256: str | None = None
    reason: str | None = None
    disposition: dict[str, Any] | None = None
    basis: dict[str, Any] | None = None


def assess_recap_semantics(
    run: ExtractionRun,
    *,
    parent: ExtractionRun | None,
    source_revision_id: str,
    root: Path | None = None,
) -> RecapSemanticAssessment:
    """Validate a marked child's canonical basis and recorded decision.

    A damaged or missing disposition stays held. Caller data never contributes
    to the basis; ``source_revision_id`` must come from registry resolution.
    """
    if not is_recap_correction(run):
        return RecapSemanticAssessment(marked=False, accepted=True)

    def held(
        reason: str = HOLD_REASON,
        basis_sha256: str | None = None,
        basis: dict[str, Any] | None = None,
    ) -> RecapSemanticAssessment:
        return RecapSemanticAssessment(True, False, basis_sha256, reason, None, basis)

    lineage = run.lineage
    if (
        parent is None
        or run.status != ExtractionRunStatus.REVIEWABLE
        or run.source_domain != "recap"
        or parent.source_domain != "recap"
        or parent.status not in FROZEN_COMPONENT_STATUSES
        or not parent.has_required_review_components()
        or parent.run_id != lineage.get("parent_run_id")
        or parent.run_id == run.run_id
        or not run.profile_id
        or run.profile_id != f"{RECAP_PROFILE_ID}@{RECAP_PROFILE_VERSION}"
        or run.profile_id != parent.profile_id
        or not run.campaign_id
        or not run.session_id
        or run.campaign_id != parent.campaign_id
        or run.session_id != parent.session_id
        or run.source_artifact_id != parent.source_artifact_id
    ):
        return held()
    profile_name, separator, profile_version = run.profile_id.rpartition("@")
    if not separator or not profile_name or not profile_version:
        return held()
    candidate = run.components.get("candidate_graph")
    parent_candidate = parent.components.get("candidate_graph")
    source = run.components.get("source_artifact")
    parent_source = parent.components.get("source_artifact")
    spans = run.components.get("source_span_index")
    parent_spans = parent.components.get("source_span_index")
    if not all(
        (candidate, parent_candidate, source, parent_source, spans, parent_spans)
    ):
        return held()
    child_sha = _sha(candidate.sha256)
    parent_sha = _sha(parent_candidate.sha256)
    source_sha = _sha(source.sha256)
    span_sha = _sha(spans.sha256)
    candidate_v3 = lineage.get("derivation") == CANDIDATE_DERIVATION_V3
    candidate_v4 = lineage.get("derivation") == CANDIDATE_DERIVATION_V4
    candidate_v6 = lineage.get("derivation") == CANDIDATE_DERIVATION_V6
    candidate_v5 = lineage.get("derivation") == CANDIDATE_DERIVATION_V5
    candidate_v2 = lineage.get("derivation") == CANDIDATE_DERIVATION_V2
    candidate_correction = lineage.get("derivation") in {
        CANDIDATE_DERIVATION,
        CANDIDATE_DERIVATION_V2,
        CANDIDATE_DERIVATION_V3,
        CANDIDATE_DERIVATION_V4,
        CANDIDATE_DERIVATION_V5,
        CANDIDATE_DERIVATION_V6,
    }
    candidate_manifest = lineage.get("semantic_candidate_manifest")
    expected_manifest_schema = MANIFEST_SCHEMA_V6 if candidate_v6 else MANIFEST_SCHEMA_V5 if candidate_v5 else MANIFEST_SCHEMA_V4 if candidate_v4 else MANIFEST_SCHEMA_V3 if candidate_v3 else MANIFEST_SCHEMA_V2
    if (candidate_v2 or candidate_v3 or candidate_v4 or candidate_v5 or candidate_v6) and (
        not isinstance(candidate_manifest, dict)
        or candidate_manifest.get("schema") != expected_manifest_schema
    ):
        return held()
    correction_sha = _sha(lineage.get("manifest_sha256" if candidate_correction else "correction_digest"))
    if (
        not all((child_sha, parent_sha, source_sha, span_sha, correction_sha))
        or _sha(lineage.get("parent_candidate_sha256")) != parent_sha
        or _sha(parent_source.sha256) != source_sha
        or _sha(parent_spans.sha256) != span_sha
        or source.uri != parent_source.uri
        or spans.uri != parent_spans.uri
        or _sha(source_revision_id) != source_sha
    ):
        return held()
    if candidate_correction:
        if root is None:
            return held()
        from apps.live_control_server.services.recap_semantic_candidate_correction import verify_child_replay

        if not verify_child_replay(run, parent, root):
            return held()
    basis_fields = {
        "schema": (
            "dmb_recap_semantic_basis_v7" if candidate_v6
            else "dmb_recap_semantic_basis_v6" if candidate_v5
            else "dmb_recap_semantic_basis_v5" if candidate_v4
            else "dmb_recap_semantic_basis_v4" if candidate_v3
            else "dmb_recap_semantic_basis_v3" if candidate_v2
            else "dmb_recap_semantic_basis_v2" if candidate_correction
            else "dmb_recap_semantic_basis_v1"
        ),
        "parent_run_id": parent.run_id,
        "parent_candidate_sha256": parent_sha,
        "child_run_id": run.run_id,
        "candidate_uri": candidate.uri,
        "candidate_sha256": child_sha,
        "source_artifact_id": run.source_artifact_id,
        "source_revision_sha256": source_sha,
        "source_uri": source.uri,
        "span_index_uri": spans.uri,
        "span_index_sha256": span_sha,
        "profile_id": run.profile_id,
        "profile_version": profile_version,
        "campaign_id": run.campaign_id,
        "session_id": run.session_id,
    }
    basis_fields["manifest_sha256" if candidate_correction else "correction_digest"] = correction_sha
    if candidate_v2:
        basis_fields["derivation"] = CANDIDATE_DERIVATION_V2
        basis_fields["manifest_schema"] = MANIFEST_SCHEMA_V2
    if candidate_v3:
        basis_fields["derivation"] = CANDIDATE_DERIVATION_V3
        basis_fields["manifest_schema"] = MANIFEST_SCHEMA_V3
    if candidate_v4:
        basis_fields["derivation"] = CANDIDATE_DERIVATION_V4
        basis_fields["manifest_schema"] = MANIFEST_SCHEMA_V4
    if candidate_v5:
        basis_fields["derivation"] = CANDIDATE_DERIVATION_V5
        basis_fields["manifest_schema"] = MANIFEST_SCHEMA_V5
    if candidate_v6:
        basis_fields["derivation"] = CANDIDATE_DERIVATION_V6
        basis_fields["manifest_schema"] = MANIFEST_SCHEMA_V6
    basis = _digest(basis_fields)
    raw = lineage.get("semantic_disposition")
    if (
        not isinstance(raw, Mapping)
        or type(raw.get("version")) is not int
        or raw.get("version") != DISPOSITION_VERSION
    ):
        return held(basis_sha256=basis, basis=basis_fields)
    disposition = dict(raw)
    if _sha(disposition.get("basis_sha256")) != basis:
        return held(basis_sha256=basis, basis=basis_fields)
    if disposition.get("state") not in {"accepted", "rejected"}:
        return held(basis_sha256=basis, basis=basis_fields)
    if not all(
        isinstance(disposition.get(key), str) and disposition[key].strip()
        for key in ("review_decision_ref", "reviewer_id", "decided_at")
    ):
        return held(basis_sha256=basis, basis=basis_fields)
    if disposition["state"] == "rejected":
        return RecapSemanticAssessment(
            True, False, basis, REJECTED_REASON, disposition, basis_fields
        )
    return RecapSemanticAssessment(True, True, basis, None, disposition, basis_fields)


def accepted_effect_binding(
    run: ExtractionRun, assessment: RecapSemanticAssessment
) -> dict[str, Any]:
    """Pin the accepted canonical child inside the proposal effect digest."""
    if (
        not assessment.marked
        or not assessment.accepted
        or assessment.disposition is None
    ):
        raise ValueError("recap semantic disposition is not accepted")
    candidate = run.components["candidate_graph"]
    source = run.components["source_artifact"]
    spans = run.components["source_span_index"]
    _, _, profile_version = run.profile_id.rpartition("@")
    binding = {
        "version": DISPOSITION_VERSION,
        "run_id": run.run_id,
        "run_revision": run.revision,
        "candidate_uri": candidate.uri,
        "candidate_sha256": _sha(candidate.sha256),
        "source_artifact_id": run.source_artifact_id,
        "source_uri": source.uri,
        "source_revision_sha256": _sha(source.sha256),
        "span_index_uri": spans.uri,
        "span_index_sha256": _sha(spans.sha256),
        "profile_id": run.profile_id,
        "profile_version": profile_version,
        "campaign_id": run.campaign_id,
        "session_id": run.session_id,
        "basis_sha256": assessment.basis_sha256,
        "disposition_sha256": _digest(assessment.disposition),
    }
    if run.lineage.get("derivation") == CANDIDATE_DERIVATION:
        binding["manifest_sha256"] = _sha(run.lineage.get("manifest_sha256"))
    if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V2:
        binding["manifest_sha256"] = _sha(run.lineage.get("manifest_sha256"))
        binding["derivation"] = CANDIDATE_DERIVATION_V2
        binding["manifest_schema"] = MANIFEST_SCHEMA_V2
    if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V3:
        binding["manifest_sha256"] = _sha(run.lineage.get("manifest_sha256"))
        binding["derivation"] = CANDIDATE_DERIVATION_V3
        binding["manifest_schema"] = MANIFEST_SCHEMA_V3
    if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V4:
        binding["manifest_sha256"] = _sha(run.lineage.get("manifest_sha256"))
        binding["derivation"] = CANDIDATE_DERIVATION_V4
        binding["manifest_schema"] = MANIFEST_SCHEMA_V4
    if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V5:
        binding["manifest_sha256"] = _sha(run.lineage.get("manifest_sha256"))
        binding["derivation"] = CANDIDATE_DERIVATION_V5
        binding["manifest_schema"] = MANIFEST_SCHEMA_V5
    if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V6:
        binding["manifest_sha256"] = _sha(run.lineage.get("manifest_sha256"))
        binding["derivation"] = CANDIDATE_DERIVATION_V6
        binding["manifest_schema"] = MANIFEST_SCHEMA_V6
    return binding


def assert_current_effect_binding(
    run: ExtractionRun,
    assessment: RecapSemanticAssessment,
    raw_binding: object,
) -> None:
    """Reject missing, stale, or forged pins against the current canonical run."""
    if not isinstance(raw_binding, Mapping) or dict(
        raw_binding
    ) != accepted_effect_binding(run, assessment):
        raise ValueError("recap semantic disposition binding is missing or stale")


__all__ = [
    "DERIVATION",
    "CANDIDATE_DERIVATION",
    "CANDIDATE_DERIVATION_V2",
    "CANDIDATE_DERIVATION_V3",
    "CANDIDATE_DERIVATION_V4",
    "CANDIDATE_DERIVATION_V5",
    "CANDIDATE_DERIVATION_V6",
    "MANIFEST_SCHEMA_V3",
    "MANIFEST_SCHEMA_V4",
    "MANIFEST_SCHEMA_V5",
    "MANIFEST_SCHEMA_V6",
    "DISPOSITION_VERSION",
    "EFFECT_KEY",
    "HOLD_REASON",
    "REJECTED_REASON",
    "RecapSemanticAssessment",
    "accepted_effect_binding",
    "assert_current_effect_binding",
    "assess_recap_semantics",
    "is_recap_correction",
]
