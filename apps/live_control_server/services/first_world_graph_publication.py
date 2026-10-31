"""Mounted first-world prepare → confirm (CUTOVER D.2C2).

Product code talks only to ``WorldGraphInitializationAuthority``. Native
confirm does not open Buddy World Graph files. Native reviewed initialization
and verified reservation activation are the only mounted creation path.
"""

from __future__ import annotations

import json
import hashlib

from apps.live_control_server import config as live_config
from apps.live_control_server.models.extract_promote import (
    PRODUCT_CONFIRM_ALLOW_LIVE_WORLD,
    SERVER_CONFIRMING_PRINCIPAL,
    FirstWorldConfirmNonapplication,
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
    _diagnostic,
    _load_worldbuilding_publication_input,
    _promotable_run_error,
)
from apps.live_control_server.services.first_world_graph import (
    FIRST_WORLD_PLAN_SCHEMA,
    FirstWorldLineage,
    first_world_native_target,
    cross_check_workspace_lineage,
    materialize_first_world_plan,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    resolve_promotable_ingest_run,
)
from apps.live_control_server.services.source_artifact_registry import (
    get_source_artifact,
)
from apps.live_control_server.models.world_graph_contributions import (
    compute_contribution_payload_sha256,
)
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


def _preflight_failure_details(exc: WorldGraphInitializationError, plan: FirstWorldGraphPlan) -> dict:
    details = dict(exc.details)
    effect_map = plan.reviewed_effect.get("candidate_effect_map", {})
    details["candidate_assertion_ids"] = [
        candidate_id for candidate_id, assertion_ids in effect_map.items()
        if details.get("assertion_id") in assertion_ids
    ]
    return details


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
        target = first_world_native_target(live_config.repo_root(), world_id)
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc
    try:
        probed = get_world_graph_initialization_authority(
            world_root=live_config.world_graph_root()
        ).probe(target.native_world_id)
    except WorldGraphInitializationError as exc:
        raise _initialization_error(exc) from exc
    from apps.live_control_server.services.world_container_registry import get_world_container, NativeGraphProvisioningRecord
    record = get_world_container(live_config.managed_world_data_root(live_config.repo_root()), world_id)
    recovering = isinstance(record.native_graph_binding, NativeGraphProvisioningRecord) and probed.initialization_id == target.provisioning_id
    if record.native_graph_binding.status == "active" or (probed.state == "initialized" and not recovering):
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


def _source_evidence_commitment(review, *, source_prose, span_index, source_artifact_id):
    from graph_memory.source_span import source_span_index_to_dict
    source_sha = hashlib.sha256(source_prose.encode("utf-8")).hexdigest()
    if source_sha != span_index.content_sha256.removeprefix("sha256:") or span_index.source_artifact_id != source_artifact_id:
        raise ExtractPromoteError("Frozen source bytes do not match the reviewed span index.", code="run_not_promotable", status_code=422)
    payload = {
        "schema": "dmb_first_world_source_evidence_v1",
        "source_artifact_id": source_artifact_id,
        "source_content_sha256": source_sha,
        "frozen_span_index_sha256": hashlib.sha256(json.dumps(
            source_span_index_to_dict(span_index), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")).hexdigest(),
        "reviewed_assertions": [{
            "assertion_id": row.assertion_id,
            "kind": row.kind,
            "evidence": [{
                "source_artifact_id": ref.source_artifact_id,
                "source_span_ref_id": ref.source_span_ref_id,
                "anchor_quotes": list(ref.anchor_quotes),
            } for ref in row.evidence],
        } for row in review],
    }
    return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _assert_materialized_evidence_matches_review(materialized, review):
    expected = {row.assertion_id: row for row in review}
    mapping = materialized.effect["candidate_effect_map"]
    assertions = {row.assertion_id: row for row in [
        *materialized.contribution.accepted_assertions, *materialized.contribution.rejected_assertions,
    ]}
    if set(mapping) != set(expected) or {identifier for ids in mapping.values() for identifier in ids} != set(assertions):
        raise ExtractPromoteError("Materialized source evidence does not match the reviewed candidates.", code="plan_verification_failed", status_code=409)
    for candidate_id, ids in mapping.items():
        approved = {(ref.source_artifact_id, ref.source_span_ref_id) for ref in expected[candidate_id].evidence}
        for identifier in ids:
            assertion = assertions[identifier]
            rows = (assertion.value or {}).get("evidence", [])
            actual = {(row.get("source_artifact_id"), row.get("source_span_ref_id")) for row in rows}
            if actual != approved or any(row.get("source_domain") != "worldbuilding" for row in rows):
                raise ExtractPromoteError("Materialized source spans changed after review.", code="plan_verification_failed", status_code=409)


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

    publication_input = _load_worldbuilding_publication_input(
        resolved, allow_gazetteer=False
    )
    reviewed_evidence = publication_input.reviewed_assertions
    source_prose = publication_input.source_prose
    span_index = publication_input.span_index

    evidence_commitment = _source_evidence_commitment(
        reviewed_evidence, source_prose=source_prose, span_index=span_index,
        source_artifact_id=resolved.source_artifact_id,
    )

    _world_id, lineage = _require_first_world_admission(resolved)
    native_target = first_world_native_target(live_config.repo_root(), lineage.world_id)

    try:
        materialized = materialize_first_world_plan(
            preview=publication_input.preview,
            world_id=lineage.world_id,
            native_target=native_target,
            run_id=resolved.run_id,
            source_artifact_id=lineage.source_artifact_id,
            source_revision_id=lineage.source_revision_id,
            source_uri=resolved.sealed_source_uri,
            source_evidence_sha256=evidence_commitment,
            extraction_profile=publication_input.profile_id,
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

    _assert_materialized_evidence_matches_review(materialized, reviewed_evidence)
    plan = FirstWorldGraphPlan(
        source_evidence_sha256=evidence_commitment,
        plan_id=materialized.plan_id,
        plan_digest=materialized.plan_digest,
        decision_digest=materialized.decision_digest,
        world_id=lineage.world_id,
        native_target=native_target,
        run_id=resolved.run_id,
        source_artifact_id=lineage.source_artifact_id,
        source_revision_id=lineage.source_revision_id,
        workspace_document_id=lineage.workspace_document_id,
        workspace_document_revision=lineage.workspace_document_revision,
        campaign_scope=lineage.campaign_scope,
        session_scope=None,
        extraction_profile=publication_input.profile_id,  # type: ignore[arg-type]
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
    authority = get_world_graph_initialization_authority(world_root=live_config.world_graph_root())
    try:
        authority.preflight(_initialization_request(plan=plan, rematerialized=materialized, resolved=resolved))
    except WorldGraphInitializationError as exc:
        diagnostic = _initialization_error(exc)
        if exc.code == "inexpressible":
            diagnostic.failure_payload = {
                "schema": "dmb_first_world_preflight_failure_v1",
                "validationMessage": str(exc),
                "failure": _preflight_failure_details(exc, plan),
            }
        raise diagnostic from exc
    return plan


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
        world_id=plan.native_target.native_world_id,
        campaign_id=None,
        initialization_id=plan.native_target.provisioning_id,
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
    if plan.schema_ != FIRST_WORLD_PLAN_SCHEMA:
        raise ExtractPromoteError("This review plan is out of date. Prepare and review the source again.", code="stale_review_plan", status_code=409)
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

    publication_input = _load_worldbuilding_publication_input(
        resolved, allow_gazetteer=False
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
        target = first_world_native_target(live_config.repo_root(), plan.world_id)
        if target != plan.native_target:
            raise WorldbuildingWritePlanError(
                "World provisioning identity changed after review.",
                code="native_graph_binding_changed", status_code=409,
            )
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

    reviewed_evidence = publication_input.reviewed_assertions
    source_prose = publication_input.source_prose
    span_index = publication_input.span_index

    evidence_commitment = _source_evidence_commitment(
        reviewed_evidence, source_prose=source_prose, span_index=span_index,
        source_artifact_id=resolved.source_artifact_id,
    )
    if plan.source_evidence_sha256 != evidence_commitment:
        raise ExtractPromoteError("Reviewed source evidence changed. Prepare and review it again.", code="plan_verification_failed", status_code=409)

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
            preview=publication_input.preview,
            world_id=plan.world_id,
            native_target=target,
            run_id=plan.run_id,
            source_artifact_id=plan.source_artifact_id,
            source_revision_id=plan.source_revision_id,
            source_uri=resolved.sealed_source_uri,
            source_evidence_sha256=evidence_commitment,
            extraction_profile=publication_input.profile_id,
            campaign_scope=plan.campaign_scope,
            workspace_document_id=plan.workspace_document_id,
            workspace_document_revision=plan.workspace_document_revision,
            dispositions=dispositions,
        )
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc

    _assert_materialized_evidence_matches_review(rematerialized, reviewed_evidence)
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
        probed = authority.probe(target.native_world_id)
    except WorldGraphInitializationError as exc:
        raise _initialization_error(exc) from exc
    from apps.live_control_server.services.world_container_registry import get_world_container
    current_binding = get_world_container(
        live_config.managed_world_data_root(live_config.repo_root()), plan.world_id,
    ).native_graph_binding
    if current_binding.status == "active" and (
        probed.state != "initialized" or probed.initialization_id != target.provisioning_id
        or probed.published_revision_id != current_binding.initialization_revision_id
    ):
        raise ExtractPromoteError("Active World initialization proof changed.",
                                  code="native_graph_binding_changed", status_code=409)
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

    initialization_request = _initialization_request(
        plan=plan, rematerialized=rematerialized, resolved=resolved,
    )
    if probed.world_id != target.native_world_id:
        raise ExtractPromoteError("Initialization state belongs to another World.",
                                  code="native_graph_binding_changed", status_code=409)
    if probed.state == "uninitialized":
        if probed.initialization_id is not None or probed.published_revision_id is not None:
            raise ExtractPromoteError("Uninitialized state carries contradictory receipt data.",
                                      code="first_world_initialization_failed", status_code=409)
        try:
            authority.preflight(initialization_request)
        except WorldGraphInitializationError as exc:
            if exc.code != "inexpressible":
                raise _initialization_error(exc) from exc
            proof = FirstWorldConfirmNonapplication(
                world_id=plan.world_id, native_world_id=target.native_world_id,
                initialization_id=target.provisioning_id, plan_id=plan.plan_id,
                plan_digest=plan.plan_digest, validation_message=str(exc), failure=_preflight_failure_details(exc, plan),
            )
            raise ExtractPromoteError(
                "This confirm did not invoke initialization. Review the rejected relationship choices.",
                code="first_world_confirm_not_invoked", status_code=409,
                diagnostics=[_diagnostic("first_world_preflight_inexpressible", str(exc))],
                failure_payload=proof.model_dump(mode="json", by_alias=True),
            ) from exc
    # Anything after this point may have reached initialization. No exception from
    # initialize can be converted into a nonapplication proof.
    try:
        port_receipt = authority.initialize(initialization_request)
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
    from apps.live_control_server.services.world_graph_binding import (
        activate_reviewed_native_graph, WorldGraphBindingError,
    )
    try:
        activate_reviewed_native_graph(
            live_config.managed_world_data_root(live_config.repo_root()), plan.world_id,
            target=target, receipt=port_receipt,
            plan_id=plan.plan_id, plan_digest=plan.plan_digest,
        )
    except WorldGraphBindingError as exc:
        raise ExtractPromoteError(
            str(exc), code="native_graph_activation_pending", status_code=exc.status_code,
        ) from exc
    return _first_world_confirm_receipt(
        outcome=outcome,
        plan=plan,
        rematerialized=rematerialized,
        port_receipt=port_receipt,
    )
