"""Trusted GM confirmation of an independently reviewed sealed extract package.

The caller supplies already trusted bytes. This service does not load paths from
HTTP input or manufacture a reviewer, review time, or a new proposal seal.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from apps.live_control_server.models.extract_promote import ExtractPromoteConfirmRequest
from apps.live_control_server.models.reviewed_extract_confirmation import (
    PinnedExtractSemanticReview,
    ReviewedExtractBinding,
    TrustedGMExtractContext,
)

SERVICE_PRINCIPAL = "service:buddy:reviewed-extract"


class ReviewedExtractConfirmationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _fail(code: str, message: str) -> None:
    raise ReviewedExtractConfirmationError(code, message)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _admit_gm_confirm(context: TrustedGMExtractContext, policy: Any) -> None:
    from dungeonmind.contracts.capability import CapabilityEffect
    from dungeonmind.contracts.contribution_review_v2 import FINALIZE_REVIEW_V2_TOOL
    from dungeonmind.contracts.projection import Admissibility
    from dungeonmind.domain.capability import evaluate_capability

    try:
        evaluate_capability(
            policy, tool_name=FINALIZE_REVIEW_V2_TOOL, effect=CapabilityEffect.COMMIT
        )
    except Exception as exc:
        _fail(
            "confirm_capability_denied",
            f"GM confirm capability denied: {type(exc).__name__}",
        )
    scope = policy.graph_scope
    if (
        scope is None
        or scope.admissibility is not Admissibility.GM
        or scope.world_id != context.native_world_id
        or scope.campaign_id != context.campaign_id
        or scope.revision_pin != context.expected_parent_revision_id
    ):
        _fail("gm_scope_required", "confirm requires the exact selected GM graph scope")


def _read_review_and_package(
    *,
    context: TrustedGMExtractContext,
    artifact_bytes: bytes,
    artifact_sha256: str,
    sealed_package_bytes: bytes,
) -> tuple[PinnedExtractSemanticReview, dict[str, Any], ReviewedExtractBinding]:
    if not isinstance(artifact_bytes, bytes) or _sha(artifact_bytes) != artifact_sha256:
        _fail(
            "review_digest_drift",
            "semantic review bytes differ from their pinned digest",
        )
    try:
        review = PinnedExtractSemanticReview.model_validate_json(artifact_bytes)
        package = json.loads(sealed_package_bytes)
    except (ValidationError, ValueError, TypeError) as exc:
        _fail("review_invalid", f"review or proposal is invalid: {type(exc).__name__}")
    if (
        not isinstance(package, dict)
        or _sha(sealed_package_bytes) != review.prepared_package_sha256
    ):
        _fail(
            "proposal_digest_drift",
            "sealed proposal bytes differ from the reviewed package",
        )
    effect = package.get("effect")
    if not isinstance(effect, dict):
        _fail("proposal_invalid", "sealed proposal has no effect")
    admission = effect.get("candidate_admission") or {}
    source = effect.get("source_admission") or {}
    meta = effect.get("contribution_meta") or {}
    if (
        package.get("proposal_id") != review.proposal_id
        or package.get("proposal_digest") != review.proposal_digest
        or effect.get("world_id") != context.native_world_id
        or effect.get("parent_revision_id") != context.expected_parent_revision_id
        or effect.get("source_artifact_id") != review.source_artifact_id
        or effect.get("source_revision_id") != review.source_revision_id
        or source.get("content_sha256") != review.source_body_sha256
        or admission.get("candidate_digest") != review.candidate_admission_digest
        or meta.get("campaign_scope") != context.campaign_id
        or review.expected_parent_revision_id != context.expected_parent_revision_id
    ):
        _fail(
            "review_binding_mismatch",
            "review, proposal, source, or GM scope pins differ",
        )
    accepted = effect.get("accepted_proposals")
    if not isinstance(accepted, list):
        _fail("proposal_invalid", "sealed proposal has no accepted assertions")
    accepted_ids = [
        item.get("assertion_id") for item in accepted if isinstance(item, dict)
    ]
    decision_ids = [item.assertion_id for item in review.decisions]
    if (
        len(accepted_ids) != len(accepted)
        or len(set(accepted_ids)) != len(accepted_ids)
        or sorted(accepted_ids) != decision_ids
        or any(item.get("acceptance_state") != "accepted" for item in accepted)
    ):
        _fail(
            "review_coverage_mismatch",
            "review must cover exactly the sealed accepted assertions",
        )
    if any(item not in accepted_ids for item in review.selected_assertion_ids):
        _fail("review_selection_invalid", "selection contains an unsealed assertion")
    binding = ReviewedExtractBinding(
        artifact_sha256=artifact_sha256,
        prepared_package_sha256=review.prepared_package_sha256,
        semantic_reviewer_kind=review.semantic_reviewer_kind,
        semantic_reviewer_id=review.semantic_reviewer_id,
        reviewed_at=review.reviewed_at,
        service_principal=SERVICE_PRINCIPAL,
        proposal_id=review.proposal_id,
        proposal_digest=review.proposal_digest,
        source_artifact_id=review.source_artifact_id,
        source_revision_id=review.source_revision_id,
        source_body_sha256=review.source_body_sha256,
        source_span_index_sha256=review.source_span_index_sha256,
        candidate_graph_sha256=review.candidate_graph_sha256,
        candidate_admission_digest=review.candidate_admission_digest,
        expected_parent_revision_id=review.expected_parent_revision_id,
        expected_parent_payload_sha256=review.expected_parent_payload_sha256,
        selected_assertion_ids=review.selected_assertion_ids,
    )
    return review, package, binding


def _verify_run_bytes(
    review: PinnedExtractSemanticReview,
    package: dict[str, Any],
    *,
    context: TrustedGMExtractContext,
    repo_root: Path,
) -> dict[str, Any]:
    from apps.live_control_server.services.promotable_ingest_run import load_bound_extraction_run
    from apps.live_control_server.services.candidate_graph_admission import canonical_candidate_digest
    try:
        data = load_bound_extraction_run(package, root=repo_root)
        source_bytes, candidate_bytes, span_bytes = data.source_bytes, data.candidate_bytes, data.span_bytes
        candidate, index = json.loads(candidate_bytes), data.span_index
    except Exception as exc:
        _fail("source_unavailable", f"run-pinned source proof failed: {type(exc).__name__}")
    if (
        data.run.run_id != review.source_run_id
        or data.run.source_artifact_id != review.source_artifact_id
        or data.source_artifact.world_id != context.native_world_id
        or "sha256:" + (data.source_artifact.content_sha256 or "").removeprefix("sha256:") != review.source_revision_id
        or (data.run.campaign_id or "") != package["effect"]["contribution_meta"]["campaign_scope"]
        or _sha(source_bytes) != review.source_body_sha256
        or _sha(candidate_bytes) != review.candidate_graph_sha256
        or _sha(span_bytes) != review.source_span_index_sha256
        or canonical_candidate_digest(candidate) != review.candidate_admission_digest
    ):
        _fail("source_digest_drift", "source, candidate, span, or run component drifted")
    span_ids = {item.source_span_id for item in index.spans}
    accepted = {
        item["assertion_id"]: item for item in package["effect"]["accepted_proposals"]
    }
    for assertion_id in review.selected_assertion_ids:
        refs = accepted[assertion_id].get("value", {}).get("evidence", [])
        if not refs or any(
            item.get("source_span_ref_id") not in span_ids
            or item.get("source_artifact_id") != review.source_artifact_id
            for item in refs
        ):
            _fail(
                "source_span_drift", "selected assertion lacks the pinned source span"
            )
    return candidate


def confirm_reviewed_extract(
    *,
    context: TrustedGMExtractContext,
    artifact_bytes: bytes,
    artifact_sha256: str,
    sealed_package_bytes: bytes,
    gm_capability_policy: Any,
    database_url: str,
    repo_root: Path,
) -> dict[str, Any]:
    """Confirm one exact accepted selection through existing Core authority."""
    from apps.live_control_server.services import extract_promote
    from apps.live_control_server.services.candidate_graph_admission import (
        confirm_candidate_graph_admission,
    )
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    _admit_gm_confirm(context, gm_capability_policy)
    review, package, binding = _read_review_and_package(
        context=context,
        artifact_bytes=artifact_bytes,
        artifact_sha256=artifact_sha256,
        sealed_package_bytes=sealed_package_bytes,
    )
    target = extract_promote._assert_current_publication_target(package)
    if (
        target.managed_world_id != context.managed_world_id
        or target.native_world_id != context.native_world_id
    ):
        _fail(
            "world_binding_mismatch",
            "selected managed World binding differs from review",
        )
    recap_context = package["effect"].get(extract_promote._RECAP_CONTEXT_KEY)
    if isinstance(recap_context, dict):
        extract_promote._assert_current_recap_ingest_context(
            recap_context,
            managed_world_id=context.managed_world_id,
            campaign_id=context.campaign_id,
        )
    candidate = _verify_run_bytes(review, package, context=context, repo_root=repo_root)
    request = ExtractPromoteConfirmRequest(
        review_package=package, assertion_ids=review.selected_assertion_ids
    )

    def governed_confirm() -> dict[str, Any]:
        extract_promote._assert_recap_semantics_at_confirm(package)
        extract_promote._assert_current_publication_target(package)
        return world_graph_writes.confirm_extract_promote_via_dungeonmind(
            request,
            database_url=database_url,
            confirming_principal=SERVICE_PRINCIPAL,
            assertion_ids=tuple(review.selected_assertion_ids),
            repo_root=repo_root,
            semantic_binding=binding,
            semantic_gm_policy=gm_capability_policy,
            candidate_graph=candidate,
        )

    return confirm_candidate_graph_admission(
        review_package=package,
        candidate_graph=candidate,
        governed_confirm=governed_confirm,
    )
