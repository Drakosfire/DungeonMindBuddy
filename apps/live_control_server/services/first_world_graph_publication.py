"""Mounted first-world prepare → confirm (CUTOVER D.2C2).

Product code talks only to ``WorldGraphInitializationAuthority``. Native
confirm does not open Buddy World Graph files. Kernel/filesystem initialization
stays behind explicit buddy_files compatibility.
"""

from __future__ import annotations

import json

from apps.live_control_server import config as live_config
from apps.live_control_server.models.extract_promote import (
    PRODUCT_CONFIRM_ALLOW_LIVE_WORLD,
    SERVER_CONFIRMING_PRINCIPAL,
    FirstWorldGraphConfirmReceipt,
    FirstWorldGraphConfirmRequest,
    FirstWorldGraphPlan,
    FirstWorldGraphPlanSummary,
    FirstWorldGraphPrepareRequest,
)
from apps.live_control_server.ports.world_graph_initialization import (
    WorldGraphInitializationError,
    WorldGraphInitializationReceipt,
    WorldGraphInitializationRequest,
)
from apps.live_control_server.ports.world_graph_initialization_access import (
    get_world_graph_initialization_authority,
)
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    _assert_and_project_candidate_evidence,
    _diagnostic,
    _load_frozen_span_index_for_resolved_run,
    _load_typed_worldbuilding_preview_for_run,
    _promotable_run_error,
)
from apps.live_control_server.services.first_world_graph import (
    FIRST_WORLD_PLAN_SCHEMA,
    FirstWorldLineage,
    admit_managed_world,
    cross_check_workspace_lineage,
    first_world_initialization_id,
    materialize_first_world_plan,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    resolve_promotable_ingest_run,
)
from apps.live_control_server.services.source_artifact_registry import (
    get_source_artifact,
)
from graph_memory.kernel.contributions import compute_contribution_payload_sha256
from graph_memory.worldbuilding_write_plan import (
    WorldbuildingDispositionInput,
    WorldbuildingWritePlanError,
    _canonical_effect,
)

_PORT_ERROR_MAP: dict[str, tuple[str, int]] = {
    "authority_unavailable": ("authority_unavailable", 503),
    "integrity_failure": ("first_world_initialization_failed", 409),
    "already_initialized": ("world_already_initialized", 409),
    "idempotency_conflict": ("first_world_idempotency_conflict", 409),
    "inexpressible": ("dungeonmind_inexpressible", 409),
    "initialization_failed": ("first_world_initialization_failed", 500),
}


def _write_plan_error(exc: WorldbuildingWritePlanError) -> ExtractPromoteError:
    return ExtractPromoteError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=[_diagnostic(exc.code, str(exc))],
    )


def _initialization_error(exc: WorldGraphInitializationError) -> ExtractPromoteError:
    code, status = _PORT_ERROR_MAP.get(exc.code, ("first_world_initialization_failed", 500))
    return ExtractPromoteError(
        str(exc),
        code=code,
        status_code=status,
        diagnostics=[_diagnostic(code, str(exc))],
    )


def _require_first_world_admission(resolved) -> tuple[str, FirstWorldLineage]:
    """Resolve managed W + uninitialized (or matching-receipt) gate for prepare."""
    world_id = (getattr(resolved, "world_id", None) or "").strip()
    if not world_id:
        raise ExtractPromoteError(
            "first-world publish requires SourceArtifact world_id",
            code="world_id_required",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "world_id_required",
                    "exact SourceArtifact world_id is required for first-world publish",
                )
            ],
        )
    try:
        admit_managed_world(live_config.repo_root(), world_id)
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc
    try:
        probed = get_world_graph_initialization_authority(
            world_root=live_config.world_graph_root()
        ).probe(world_id)
    except WorldGraphInitializationError as exc:
        raise _initialization_error(exc) from exc
    if probed.state == "initialized":
        raise ExtractPromoteError(
            "World Graph already exists for this world",
            code="world_already_initialized",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "world_already_initialized",
                    f"world {world_id!r} already has a readable World Graph head",
                )
            ],
        )
    if probed.state == "unreadable":
        raise ExtractPromoteError(
            "World Graph storage exists but is unreadable",
            code="world_unreadable",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "world_unreadable",
                    f"world {world_id!r} storage exists but cannot be opened",
                )
            ],
        )
    try:
        lineage = cross_check_workspace_lineage(
            live_config.repo_root(),
            source_artifact_id=resolved.source_artifact_id,
            expected_world_id=world_id,
        )
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc
    return world_id, lineage


def prepare_first_world(
    request: FirstWorldGraphPrepareRequest,
) -> FirstWorldGraphPlan:
    """Seal an inert first-world initialization plan (no production graph mutation)."""
    try:
        resolved = resolve_promotable_ingest_run(
            request.run_id, root=live_config.repo_root()
        )
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(
        resolved
    )
    try:
        source_prose = resolved.normalized_recap_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExtractPromoteError(
            "exact-run source prose could not be read",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("source_unreadable", str(exc))],
        ) from exc
    candidate_payload = json.loads(
        resolved.candidate_graph_path.read_text(encoding="utf-8")
    )
    span_index = _load_frozen_span_index_for_resolved_run(resolved)
    _assert_and_project_candidate_evidence(
        candidate_payload=candidate_payload,
        source_prose=source_prose,
        source_artifact_id=resolved.source_artifact_id,
        span_index=span_index,
    )

    _world_id, lineage = _require_first_world_admission(resolved)

    try:
        materialized = materialize_first_world_plan(
            preview=typed_preview,
            world_id=lineage.world_id,
            run_id=resolved.run_id,
            source_artifact_id=lineage.source_artifact_id,
            source_revision_id=lineage.source_revision_id,
            source_uri=resolved.sealed_source_uri,
            extraction_profile=expected_profile,
            campaign_scope=lineage.campaign_scope,
            workspace_document_id=lineage.workspace_document_id,
            workspace_document_revision=lineage.workspace_document_revision,
            dispositions=[
                WorldbuildingDispositionInput(
                    assertion_id=item.assertion_id,
                    decision=item.decision,
                    target_node_id=None,
                )
                for item in request.decisions
            ],
        )
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc

    return FirstWorldGraphPlan(
        plan_id=materialized.plan_id,
        plan_digest=materialized.plan_digest,
        decision_digest=materialized.decision_digest,
        world_id=lineage.world_id,
        run_id=resolved.run_id,
        source_artifact_id=lineage.source_artifact_id,
        source_revision_id=lineage.source_revision_id,
        workspace_document_id=lineage.workspace_document_id,
        workspace_document_revision=lineage.workspace_document_revision,
        campaign_scope=lineage.campaign_scope,
        session_scope=None,
        extraction_profile=expected_profile,  # type: ignore[arg-type]
        accepted_assertion_ids=list(materialized.accepted_assertion_ids),
        rejected_assertion_ids=list(materialized.rejected_assertion_ids),
        contribution_id=materialized.contribution.contribution_id,
        contribution_payload_sha256=compute_contribution_payload_sha256(
            materialized.contribution
        ),
        reviewed_effect=materialized.effect,
        summary=FirstWorldGraphPlanSummary.model_validate(materialized.summary),
        confirmable=materialized.confirmable,
        diagnostics=list(materialized.diagnostics),
    )


def _assert_rematerialized_first_world_plan_matches(
    plan: FirstWorldGraphPlan,
    rematerialized,
) -> None:
    """Browser-carried plan fields are evidence only; rematerialization is authority."""
    if not rematerialized.confirmable:
        raise ExtractPromoteError(
            "first-world plan is not confirmable (zero accepted assertions)",
            code="empty_first_world_contribution",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "empty_first_world_contribution",
                    "zero accepted assertions cannot initialize a World Graph",
                )
            ],
        )
    if plan.plan_id != rematerialized.plan_id:
        raise ExtractPromoteError(
            "sealed first-world planId failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "browser-carried planId disagrees with rematerialized plan",
                )
            ],
        )
    if plan.confirmable != rematerialized.confirmable:
        raise ExtractPromoteError(
            "sealed first-world confirmable flag failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "browser-carried confirmable disagrees with rematerialized plan",
                )
            ],
        )
    if list(plan.accepted_assertion_ids) != list(rematerialized.accepted_assertion_ids):
        raise ExtractPromoteError(
            "sealed first-world acceptedAssertionIds failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "browser-carried acceptedAssertionIds disagree with rematerialized plan",
                )
            ],
        )
    if list(plan.rejected_assertion_ids) != list(rematerialized.rejected_assertion_ids):
        raise ExtractPromoteError(
            "sealed first-world rejectedAssertionIds failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "browser-carried rejectedAssertionIds disagree with rematerialized plan",
                )
            ],
        )
    try:
        carried_effect = _canonical_effect(plan.reviewed_effect)
        expected_effect = _canonical_effect(rematerialized.effect)
    except WorldbuildingWritePlanError as exc:
        raise ExtractPromoteError(
            "sealed first-world reviewedEffect failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    f"reviewedEffect is not canonical sealed material: {exc}",
                )
            ],
        ) from exc
    if carried_effect != expected_effect:
        raise ExtractPromoteError(
            "sealed first-world reviewedEffect failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "browser-carried reviewedEffect disagrees with rematerialized plan",
                )
            ],
        )
    carried_summary = plan.summary.model_dump(mode="json")
    if carried_summary != dict(rematerialized.summary):
        raise ExtractPromoteError(
            "sealed first-world summary failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "browser-carried summary disagrees with rematerialized plan",
                )
            ],
        )


def _initialization_request(
    *,
    plan: FirstWorldGraphPlan,
    rematerialized,
    resolved,
) -> WorldGraphInitializationRequest:
    artifact = get_source_artifact(
        live_config.repo_root(), plan.source_artifact_id
    )
    return WorldGraphInitializationRequest(
        world_id=plan.world_id,
        campaign_id=plan.world_id,
        initialization_id=first_world_initialization_id(
            plan.world_id, rematerialized.plan_id
        ),
        source_plan_schema=FIRST_WORLD_PLAN_SCHEMA,
        source_plan_id=rematerialized.plan_id,
        source_plan_sha256=rematerialized.plan_digest,
        actor=SERVER_CONFIRMING_PRINCIPAL,
        source_artifact=artifact,
        source_revision_token=plan.source_revision_id,
        source_uri=resolved.sealed_source_uri,
        reviewed_contribution=rematerialized.contribution,
        run_id=plan.run_id,
        workspace_document_id=plan.workspace_document_id,
        workspace_document_revision=plan.workspace_document_revision,
        decision_digest=rematerialized.decision_digest,
    )


def _first_world_confirm_receipt(
    *,
    outcome: str,
    plan: FirstWorldGraphPlan,
    rematerialized,
    port_receipt: WorldGraphInitializationReceipt,
) -> FirstWorldGraphConfirmReceipt:
    return FirstWorldGraphConfirmReceipt(
        outcome=outcome,  # type: ignore[arg-type]
        world_id=plan.world_id,
        plan_id=rematerialized.plan_id,
        plan_digest=rematerialized.plan_digest,
        decision_digest=rematerialized.decision_digest,
        source_artifact_id=plan.source_artifact_id,
        source_revision_id=plan.source_revision_id,
        contribution_id=rematerialized.contribution.contribution_id,
        baseline_revision_id=port_receipt.baseline_revision_id,
        committed_revision_id=port_receipt.published_revision_id,
        applied_assertion_count=len(rematerialized.accepted_assertion_ids),
        accepted_assertion_ids=list(rematerialized.accepted_assertion_ids),
        rejected_assertion_ids=list(rematerialized.rejected_assertion_ids),
        audit_status="ok",
        warnings=[],
    )


def confirm_first_world(
    request: FirstWorldGraphConfirmRequest,
) -> FirstWorldGraphConfirmReceipt:
    """Verify a sealed first-world plan and atomically initialize W."""
    plan = request.plan
    world_root = live_config.world_graph_root()
    if (
        world_root.resolve() == live_config.live_world_graph_root().resolve()
        and not PRODUCT_CONFIRM_ALLOW_LIVE_WORLD
    ):
        raise ExtractPromoteError(
            "refusing to mutate live world root without allow_live_world",
            code="live_world_refused",
            status_code=403,
            diagnostics=[_diagnostic("live_world_refused", "live world refused")],
        )

    if not plan.confirmable:
        raise ExtractPromoteError(
            "first-world plan is not confirmable (zero accepted assertions)",
            code="empty_first_world_contribution",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "empty_first_world_contribution",
                    "zero accepted assertions cannot initialize a World Graph",
                )
            ],
        )

    try:
        resolved = resolve_promotable_ingest_run(
            plan.run_id, root=live_config.repo_root()
        )
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(
        resolved
    )
    resolved_world = (getattr(resolved, "world_id", None) or "").strip()
    if resolved_world != plan.world_id:
        raise ExtractPromoteError(
            "resolved run world_id does not match sealed plan",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "resolved SourceArtifact world_id disagrees with sealed plan",
                )
            ],
        )
    if resolved.source_artifact_id != plan.source_artifact_id:
        raise ExtractPromoteError(
            "resolved source artifact does not match sealed plan",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "source_artifact_id mismatch",
                )
            ],
        )
    if resolved.source_revision_id != plan.source_revision_id:
        raise ExtractPromoteError(
            "resolved source revision does not match sealed plan",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "source_revision_id mismatch",
                )
            ],
        )

    try:
        admit_managed_world(live_config.repo_root(), plan.world_id)
        lineage = cross_check_workspace_lineage(
            live_config.repo_root(),
            source_artifact_id=resolved.source_artifact_id,
            expected_world_id=plan.world_id,
        )
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc

    if (
        lineage.workspace_document_id != plan.workspace_document_id
        or lineage.workspace_document_revision != plan.workspace_document_revision
    ):
        raise ExtractPromoteError(
            "workspace lineage disagrees with sealed plan",
            code="workspace_lineage_mismatch",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "workspace_lineage_mismatch",
                    "workspace document identity/revision mismatch",
                )
            ],
        )
    if (plan.campaign_scope or "").strip() != plan.world_id:
        raise ExtractPromoteError(
            "sealed first-world campaign_scope must equal world_id",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "campaign_scope must equal world_id for first-world publish",
                )
            ],
        )
    if lineage.campaign_scope != plan.world_id:
        raise ExtractPromoteError(
            "resolved lineage campaign_scope must equal world_id",
            code="workspace_lineage_mismatch",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "workspace_lineage_mismatch",
                    "campaign_id / campaign_scope must equal world_id",
                )
            ],
        )

    try:
        source_prose = resolved.normalized_recap_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExtractPromoteError(
            "exact-run source prose could not be read",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("source_unreadable", str(exc))],
        ) from exc
    candidate_payload = json.loads(
        resolved.candidate_graph_path.read_text(encoding="utf-8")
    )
    span_index = _load_frozen_span_index_for_resolved_run(resolved)
    _assert_and_project_candidate_evidence(
        candidate_payload=candidate_payload,
        source_prose=source_prose,
        source_artifact_id=resolved.source_artifact_id,
        span_index=span_index,
    )

    decision_snapshot = plan.reviewed_effect.get("decision_snapshot") or []
    dispositions = [
        WorldbuildingDispositionInput(
            assertion_id=str(item["assertion_id"]),
            decision=str(item["decision"]),  # type: ignore[arg-type]
            target_node_id=item.get("target_node_id"),
        )
        for item in decision_snapshot
    ]
    try:
        rematerialized = materialize_first_world_plan(
            preview=typed_preview,
            world_id=plan.world_id,
            run_id=plan.run_id,
            source_artifact_id=plan.source_artifact_id,
            source_revision_id=plan.source_revision_id,
            source_uri=resolved.sealed_source_uri,
            extraction_profile=expected_profile,
            campaign_scope=plan.campaign_scope,
            workspace_document_id=plan.workspace_document_id,
            workspace_document_revision=plan.workspace_document_revision,
            dispositions=dispositions,
        )
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc

    if rematerialized.plan_digest != plan.plan_digest:
        raise ExtractPromoteError(
            "sealed first-world plan digest failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "rebuilt plan_digest disagrees with sealed plan",
                )
            ],
        )
    if rematerialized.decision_digest != plan.decision_digest:
        raise ExtractPromoteError(
            "sealed first-world decision digest failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "rebuilt decision_digest disagrees with sealed plan",
                )
            ],
        )
    contribution = rematerialized.contribution
    actual_payload = compute_contribution_payload_sha256(contribution)
    if actual_payload != plan.contribution_payload_sha256.removeprefix("sha256:"):
        raise ExtractPromoteError(
            "sealed contribution payload digest failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "contribution_payload_sha256 mismatch",
                )
            ],
        )
    if contribution.contribution_id != plan.contribution_id:
        raise ExtractPromoteError(
            "sealed contribution id failed verification",
            code="plan_verification_failed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "plan_verification_failed",
                    "contribution_id mismatch",
                )
            ],
        )
    _assert_rematerialized_first_world_plan_matches(plan, rematerialized)

    authority = get_world_graph_initialization_authority(world_root=world_root)
    try:
        probed = authority.probe(plan.world_id)
    except WorldGraphInitializationError as exc:
        raise _initialization_error(exc) from exc
    if probed.state == "unreadable":
        raise ExtractPromoteError(
            "World Graph storage exists but is unreadable",
            code="world_unreadable",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "world_unreadable",
                    f"world {plan.world_id!r} storage exists but cannot be opened",
                )
            ],
        )

    try:
        port_receipt = authority.initialize(
            _initialization_request(
                plan=plan,
                rematerialized=rematerialized,
                resolved=resolved,
            )
        )
    except WorldGraphInitializationError as exc:
        raise _initialization_error(exc) from exc

    outcome = port_receipt.outcome
    if outcome not in {"initialized", "already_initialized"}:
        raise ExtractPromoteError(
            "first-world initialization did not publish",
            code="first_world_initialization_failed",
            status_code=500,
            diagnostics=[
                _diagnostic(
                    "first_world_initialization_failed",
                    f"outcome={outcome}",
                )
            ],
        )
    return _first_world_confirm_receipt(
        outcome=outcome,
        plan=plan,
        rematerialized=rematerialized,
        port_receipt=port_receipt,
    )
