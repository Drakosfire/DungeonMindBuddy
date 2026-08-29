"""Commit prepared Graph Review edits through DungeonMind World Graph authority."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.live_control_server.services.graph_authoring_overlay_projection import (
    authored_object_node_id,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    GraphAuthoringOverlayStore,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringCommitResponse,
    GraphObjectAuthoringError,
    authoring_prepare_request_from_write,
    authored_world_id,
    build_assertions_from_proposals,
    classify_graph_review_expressibility,
    decode_publication_intent,
    contribution_binding_digest,
    graph_review_actor,
    proposed_assertions_digest,
    prove_or_admit_graph_review_source,
    resolve_graph_review_source,
    translate_assertions_to_contribution,
    validate_authoring_campaign_scope,
    _blocking_assertion_diagnostics,
)


def _resolve_store(corpus_root: Path | None) -> GraphAuthoringOverlayStore:
    if corpus_root is None:
        from src.live_play.recap_stage_paths import corpus_root as default_corpus_root

        return GraphAuthoringOverlayStore(default_corpus_root())
    return GraphAuthoringOverlayStore(corpus_root)


def _created_node_ids_for_assertions(
    assertions: list,
    local_proposal_id_by_assertion_id: dict[str, str],
) -> dict[str, str]:
    created: dict[str, str] = {}
    for assertion in assertions:
        if assertion.assertion_kind != "object":
            continue
        local_proposal_id = local_proposal_id_by_assertion_id.get(assertion.assertion_id)
        if not local_proposal_id:
            continue
        created[local_proposal_id] = authored_object_node_id(assertion.assertion_id)
    return created


def _authority_error(exc: Exception) -> GraphObjectAuthoringError:
    from apps.live_control_server.ports.world_graph_authority import WorldGraphAuthorityError

    if isinstance(exc, WorldGraphAuthorityError):
        reason = str(exc.details.get("reason") or "").strip()
        message = f"{exc}{f': {reason}' if reason else ''}"
        if exc.code == "stale_parent":
            return GraphObjectAuthoringError(message, code="stale_parent", status_code=409)
        if exc.code == "inexpressible":
            return GraphObjectAuthoringError(
                message,
                code="governed_write_inexpressible",
                status_code=409,
            )
        if exc.code == "authority_unavailable":
            return GraphObjectAuthoringError(
                message,
                code="authority_unavailable",
                status_code=503,
            )
        return GraphObjectAuthoringError(
            message,
            code="authority_unavailable",
            status_code=502,
        )
    return GraphObjectAuthoringError(str(exc), code="authority_unavailable", status_code=503)


def commit_graph_object_authoring_write(
    request: GraphObjectAuthoringCommitRequest,
    *,
    corpus_root: Path | None = None,
    repo_root_override: Path | None = None,
    authority: Any | None = None,
    resolved_source: Any | None = None,
) -> GraphObjectAuthoringCommitResponse:
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        graph_review_authority_operation_id,
    )
    from apps.live_control_server.ports.world_graph_authority import (
        WorldGraphAuthorityError,
        WorldGraphPublishRequest,
    )
    from apps.live_control_server.ports.world_graph_authority_access import (
        get_world_graph_authority,
    )

    del repo_root_override  # Graph Review confirm must not union-materialize.

    if not request.proposals:
        raise GraphObjectAuthoringError(
            "At least one staged proposal is required to commit.",
            code="empty_proposals",
        )
    if request.merge_into_union is False:
        raise GraphObjectAuthoringError(
            "Overlay-only Graph Review confirmation is no longer supported.",
            code="governed_write_inexpressible",
            status_code=409,
        )

    validate_authoring_campaign_scope(request.campaign_id, request.campaign_rel)
    intent = decode_publication_intent(request.confirm_token)
    if str(intent.get("expressibility") or "") == "INEXPRESSIBLE":
        raise GraphObjectAuthoringError(
            "merge_objects and unknown Graph Review operations cannot be published.",
            code="governed_write_inexpressible",
            status_code=409,
        )

    prepare_request = authoring_prepare_request_from_write(request)
    assertions, assertion_diagnostics = build_assertions_from_proposals(prepare_request)
    blocking = _blocking_assertion_diagnostics(assertion_diagnostics)
    if blocking:
        raise GraphObjectAuthoringError(blocking[0].message, code=blocking[0].code)
    if not assertions:
        raise GraphObjectAuthoringError("No valid assertions could be built.", code="empty_proposals")

    expressibility = classify_graph_review_expressibility(request.proposals)
    if expressibility == "INEXPRESSIBLE":
        raise GraphObjectAuthoringError(
            "merge_objects and unknown Graph Review operations cannot be published.",
            code="governed_write_inexpressible",
            status_code=409,
        )

    world_id = authored_world_id(request)
    actor = graph_review_actor(request.campaign_id)
    assertions_digest = proposed_assertions_digest(assertions)
    if str(intent.get("world_id") or "") != world_id:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )
    if str(intent.get("campaign_id") or "") != request.campaign_id:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )
    if intent.get("campaign_rel") != request.campaign_rel:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )
    if (intent.get("source_run_id") or None) != (request.source_run_id or None):
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )
    if str(intent.get("assertions_digest") or "") != assertions_digest:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )
    if str(intent.get("actor") or "") != actor:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )

    sealed_parent = str(intent.get("expected_parent_revision_id") or "")
    sealed_operation = str(intent.get("authority_operation_id") or "")
    source_artifact_id = str(intent.get("source_artifact_id") or "")
    source_revision_id = str(intent.get("source_revision_id") or "")
    sealed_contribution_digest = str(intent.get("contribution_digest") or "")
    if (
        not sealed_parent
        or not sealed_operation
        or not source_artifact_id
        or not source_revision_id
        or not sealed_contribution_digest
    ):
        raise GraphObjectAuthoringError(
            "Prepared confirmation is missing DungeonMind publication bindings.",
            code="confirmation_invalid",
            status_code=409,
        )

    resolved = resolve_graph_review_source(
        request,
        authored_world=world_id,
        resolved_source=resolved_source,
    )
    mounted = authority or get_world_graph_authority()

    buddy_artifact_id = str(getattr(resolved, "source_artifact_id"))
    buddy_revision_id = str(getattr(resolved, "source_revision_id"))
    admitted_artifact, admitted_revision = prove_or_admit_graph_review_source(
        world_id=world_id,
        source_artifact_id=buddy_artifact_id,
        source_revision_id=buddy_revision_id,
        authority=mounted,
    )
    if admitted_artifact != source_artifact_id or admitted_revision != source_revision_id:
        raise GraphObjectAuthoringError(
            "Admitted source pair drifted from the prepared binding.",
            code="source_inadmissible",
            status_code=409,
        )

    operation_id = graph_review_authority_operation_id(
        world_id=world_id,
        campaign_id=request.campaign_id,
        campaign_rel=request.campaign_rel,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        sealed_proposal_digest=assertions_digest,
        expected_parent_revision_id=sealed_parent,
    )
    if operation_id != sealed_operation:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )

    contribution = translate_assertions_to_contribution(
        world_id=world_id,
        campaign_id=request.campaign_id,
        actor=actor,
        source_artifact_id=buddy_artifact_id,
        source_revision_id=buddy_revision_id,
        assertions=assertions,
    )
    if contribution_binding_digest(contribution) != sealed_contribution_digest:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared DungeonMind contribution.",
            code="confirmation_invalid",
            status_code=409,
        )

    try:
        recovered = mounted.recover(
            world_id,
            operation_id,
            expected_parent_revision_id=sealed_parent,
            contribution=contribution,
            actor=actor,
            operation_namespace="worldbuilding",
        )
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc

    receipt = recovered
    if recovered is None:
        try:
            head = mounted.current_head(world_id)
        except WorldGraphAuthorityError as exc:
            raise _authority_error(exc) from exc
        if head.revision_id != sealed_parent:
            raise GraphObjectAuthoringError(
                "expected parent revision is not the current World Graph head",
                code="stale_parent",
                status_code=409,
            )
        publish_request = WorldGraphPublishRequest(
            world_id=world_id,
            expected_parent_revision_id=sealed_parent,
            authority_operation_id=operation_id,
            actor=actor,
            contribution=contribution,
            operation_namespace="worldbuilding",
        )
        try:
            receipt = mounted.publish(publish_request)
        except WorldGraphAuthorityError as exc:
            try:
                recovered = mounted.recover(
                    world_id,
                    operation_id,
                    expected_parent_revision_id=sealed_parent,
                    contribution=contribution,
                    actor=actor,
                    operation_namespace="worldbuilding",
                )
            except WorldGraphAuthorityError as recover_exc:
                raise _authority_error(recover_exc) from recover_exc
            if recovered is None:
                raise _authority_error(exc) from exc
            receipt = recovered

    assert receipt is not None
    local_proposal_ids = {
        assertion.assertion_id: proposal.local_proposal_id
        for assertion, proposal in zip(assertions, request.proposals, strict=False)
    }
    store = _resolve_store(corpus_root)
    overlay_path = store.overlay_path(request.campaign_id, campaign_rel=request.campaign_rel)
    events_path = store.events_path(request.campaign_id, campaign_rel=request.campaign_rel)
    idempotency = "already_applied" if receipt.outcome == "already_applied" else "published"
    return GraphObjectAuthoringCommitResponse(
        committed=True,
        campaign_id=request.campaign_id,
        overlay_path=str(overlay_path),
        event_log_path=str(events_path),
        backup_path=None,
        assertion_count=len(assertions),
        event_count=0,
        new_overlay_token=None,
        diagnostics=[],
        no_mutation_guarantees=[
            "Published through DungeonMind World Graph authority.",
            "Authored overlay was not the graph authority.",
            "UnionSupergraph was not mutated.",
            "Source markdown was not mutated.",
        ],
        union_store_materialization=None,
        created_node_ids=_created_node_ids_for_assertions(assertions, local_proposal_ids),
        world_id=world_id,
        parent_revision_id=receipt.parent_revision_id,
        published_revision_id=receipt.published_revision_id,
        operation_id=operation_id,
        result=idempotency,
        idempotency_status=idempotency,
        audit_status="skipped",
    )
