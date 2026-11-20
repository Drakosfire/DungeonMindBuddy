"""Original manual-packet correspondence over immutable terminal history.

These pure reconstruction steps never consult current source bodies, admission,
endpoint kinds, identity ledgers or the current head. Reading a valid Core receipt
alone does not establish that it belongs to the signed Buddy request.
"""

from __future__ import annotations

import json
from dataclasses import fields
from types import SimpleNamespace
from typing import Any

from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringError,
    VerifiedGraphReviewSpan,
    contribution_binding_digest,
    graph_review_source_evidence_ref_id,
    translate_assertions_to_contribution,
)


def _mismatch(reason: str) -> GraphObjectAuthoringError:
    return GraphObjectAuthoringError(
        f"Historical publication does not match the original confirmation: {reason}.",
        code="authority_integrity", status_code=500,
    )


def reconstruct_original_contribution(
    *,
    candidate: Any,
    assertions: list[Any],
    world_id: str,
    campaign_scope: str | None,
    actor: str,
    sealed_artifact_id: str,
    sealed_contribution_digest: str,
) -> Any:
    """Authenticate recorded Buddy spans through the original HMAC-bound digest.

    Typed Core evidence uses the admitted revision; the embedded span row retains
    the distinct original Buddy revision. Never substitute one for the other.
    Full candidate comparison is a separate required step after reconstruction.
    """
    expected_ids = {assertion.assertion_id for assertion in assertions}
    if len(expected_ids) != len(assertions) or not expected_ids:
        raise _mismatch("original assertion coverage")
    spans: dict[str, VerifiedGraphReviewSpan] = {}
    row_fields = {field.name for field in fields(VerifiedGraphReviewSpan)}
    for assertion in candidate.assertions:
        try:
            value = json.loads(assertion.value)
        except (TypeError, ValueError) as exc:
            raise _mismatch("recorded assertion value") from exc
        rows = value.get("evidence") if isinstance(value, dict) else None
        if (not isinstance(rows, list) or len(rows) != 1
                or not isinstance(rows[0], dict) or set(rows[0]) != row_fields):
            raise _mismatch("unsupported or incomplete recorded span recipe")
        row = rows[0]
        if any(not isinstance(value, str) for key, value in row.items()
               if key != "span_index_sha256"):
            raise _mismatch("recorded span types")
        if row["span_index_sha256"] is not None and not isinstance(row["span_index_sha256"], str):
            raise _mismatch("recorded span index type")
        span = VerifiedGraphReviewSpan(**row)
        if (span.assertion_id not in expected_ids or span.assertion_id in spans
                or span.source_artifact_id != sealed_artifact_id
                or span.evidence_ref_id != graph_review_source_evidence_ref_id(
                    span.source_artifact_id, span.assertion_id)):
            raise _mismatch("recorded span identity or coverage")
        spans[span.assertion_id] = span
    pairs = {(span.source_artifact_id, span.source_revision_id) for span in spans.values()}
    if set(spans) != expected_ids or len(pairs) != 1:
        raise _mismatch("recorded source pair or assertion coverage")
    artifact_id, buddy_revision_id = next(iter(pairs))
    original = translate_assertions_to_contribution(
        world_id=world_id, campaign_id=campaign_scope, actor=actor,
        source_artifact_id=artifact_id, source_revision_id=buddy_revision_id,
        assertions=assertions, verified_spans=spans,
    )
    if contribution_binding_digest(original) != sealed_contribution_digest:
        raise _mismatch("signed original contribution digest")
    return original


def reconstruct_candidate(
    original: Any, *, admitted_revision_id: str, reviewed_at: Any,
) -> Any:
    """Reproduce the typed-V3 manual producer without fresh endpoint admission."""
    from dungeonmind.contracts.contribution import AcceptanceState, ContributionStatus
    from dungeonmind.domain.canonical import canonical_json
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        CONNECTED_PLACE_OPERATION_V7_TARGET,
        CURRENT_V5_TARGET,
        resolve_buddy_predicate_mapping_v4,
    )
    from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
        map_graph_review_contribution_v3,
    )

    mapped = map_graph_review_contribution_v3(
        SimpleNamespace(evidence={}), original,
        {(original.source_artifact_id, original.source_revision_id): admitted_revision_id},
    )
    qualified = []
    for assertion in mapped.assertions:
        if assertion.acceptance_state is not AcceptanceState.ACCEPTED:
            raise _mismatch("manual assertion verdict")
        value = json.loads(assertion.value) if assertion.value else {}
        update: dict[str, Any] = {"acceptance_state": AcceptanceState.CANDIDATE}
        if assertion.assertion_kind == "node":
            kind = CURRENT_V5_TARGET.buddy_to_dm_kind.get(str(value.get("kind") or ""))
            if kind is None:
                raise _mismatch("unsupported historical node kind")
            update["value"] = canonical_json({**value, "dm_kind": kind})
        elif assertion.assertion_kind == "edge":
            target = (CONNECTED_PLACE_OPERATION_V7_TARGET
                      if assertion.predicate == "operates" else CURRENT_V5_TARGET)
            mapping = resolve_buddy_predicate_mapping_v4(str(assertion.predicate or ""), target=target)
            if mapping is None or not mapping[0]:
                raise _mismatch("unsupported historical predicate")
            predicate, reverse = mapping
            update["value"] = canonical_json({**value, "dm_predicate": predicate})
            if reverse:
                update.update(subject_object_id=assertion.object_object_id,
                              object_object_id=assertion.subject_object_id)
        elif assertion.assertion_kind != "alias":
            raise _mismatch("unsupported historical manual assertion kind")
        temporal = assertion.temporal_scope
        if (isinstance(temporal, dict) and set(temporal) == {"session_id"}
                and isinstance(temporal["session_id"], str)):
            update["temporal_scope"] = None
        qualified.append(assertion.model_copy(update=update))
    return mapped.model_copy(update={
        "assertions": qualified, "status": ContributionStatus.ACTIVE,
        "supersedes_contribution_id": None, "identity_decision_ids": [],
        "produced_at": reviewed_at,
    })



def verify_review_correspondence(
    *, original: Any, history: Any, parent: Any, operation_id: str,
    expected_parent_id: str, admitted_revision_id: str, actor: str,
) -> None:
    """Compare complete original producer output, including immutable parent time.

    ``history`` is the Core-verified terminal aggregate, and ``parent`` is the
    exact retained sealed parent, never the current head. This is host request
    equivalence, supplementary to Core's persistence-integrity verification.
    """
    from dungeonmind.contracts.contribution import AcceptanceState, ContributionStatus
    from dungeonmind.contracts.contribution_review import (
        ContributionAssertionVerdict, ContributionPlanRef,
        derive_confirmation_id, derive_review_id, derive_reviewed_contribution_id,
    )
    from dungeonmind.contracts.contribution_review_v3 import (
        ContributionReviewRecordV3, ContributionReviewStateV3,
        contribution_v3_payload_sha256, derive_review_intent_sha256_v3,
        reviewed_v3_identity_outcome,
    )
    from dungeonmind.domain.canonical import canonical_sha256
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        WORLDBUILDING_SOURCE_PLAN_SCHEMA, _build_identity_dispositions,
    )

    review, publication, child = history.review, history.publication, history.revision
    if (type(review) is not ContributionReviewStateV3
            or type(review.record) is not ContributionReviewRecordV3):
        raise GraphObjectAuthoringError(
            "This historical manual producer recipe is unsupported; retain the original request.",
            code="publication_history_unsupported", status_code=409,
        )
    record = review.record
    if parent is None:
        raise _mismatch("missing immutable parent")
    envelope = parent.revision
    if (envelope.world_id != original.world_id or envelope.revision_id != expected_parent_id
            or envelope.status != "published"
            or envelope.graph_schema != publication.graph_schema
            or envelope.graph_payload_sha256 != canonical_sha256(parent.graph_payload)
            or envelope.graph_payload_sha256 != publication.parent_graph_payload_sha256
            or parent.graph_payload.get("semantic_profile") != record.plan_ref.semantic_profile.model_dump(mode="json")
            or publication.expected_parent_revision_id != expected_parent_id):
        raise _mismatch("immutable parent correspondence")
    stamp = envelope.created_at
    if (record.reviewed_at != stamp or publication.published_at != stamp
            or child.created_at != stamp):
        raise _mismatch("original producer timestamp")
    candidate = reconstruct_candidate(
        original, admitted_revision_id=admitted_revision_id,
        reviewed_at=stamp,
    )
    stored = candidate.model_copy(update={"status": ContributionStatus.SUPERSEDED})
    if stored.model_dump(mode="json") != review.candidate_contribution.model_dump(mode="json"):
        raise _mismatch("complete candidate payload")
    proposals, verdicts = _build_identity_dispositions(
        candidate, {item.assertion_id: AcceptanceState.ACCEPTED for item in candidate.assertions},
    )
    assertion_verdicts = [ContributionAssertionVerdict(
        assertion_id=item.assertion_id, acceptance_state=AcceptanceState.ACCEPTED,
    ) for item in sorted(candidate.assertions, key=lambda item: item.assertion_id)]
    plan = ContributionPlanRef(
        source_plan_schema=WORLDBUILDING_SOURCE_PLAN_SCHEMA, source_plan_id=operation_id,
        source_plan_sha256=canonical_sha256({"operation_id": operation_id,
                                           "contribution_id": original.contribution_id}),
        source_input_sha256=canonical_sha256({"contribution_id": original.contribution_id}),
        preview_content_sha256=canonical_sha256({}),
        candidate_contribution_sha256=contribution_v3_payload_sha256(candidate),
        expected_parent_revision_id=expected_parent_id,
        base_graph_schema=envelope.graph_schema,
        base_graph_payload_sha256=envelope.graph_payload_sha256,
        semantic_profile=parent.graph_payload["semantic_profile"],
    )
    intent = derive_review_intent_sha256_v3(
        operation_id=operation_id, world_id=original.world_id,
        campaign_id=original.campaign_scope or None, plan_ref=plan,
        candidate_contribution=candidate, identity_proposals=proposals,
        identity_verdicts=verdicts, assertion_verdicts=assertion_verdicts,
        reviewer_id=actor, reviewed_at=stamp,
    )
    review_id = derive_review_id(operation_id=operation_id,
                                review_intent_sha256=intent, world_id=original.world_id)
    reviewed_id = derive_reviewed_contribution_id(
        review_id=review_id, candidate_contribution_id=candidate.contribution_id,
    )
    outcome_by_target = {item.target_object_id: reviewed_v3_identity_outcome(item.verdict)
                         for item in verdicts}
    accepted = [item.model_copy(update={
        "acceptance_state": AcceptanceState.ACCEPTED,
        **({"identity_resolution_outcome": outcome_by_target[item.subject_object_id]}
           if item.assertion_kind in {"node", "alias"} else {}),
    }) for item in candidate.assertions]
    reviewed = candidate.model_copy(update={
        "contribution_id": reviewed_id, "status": ContributionStatus.ACTIVE,
        "supersedes_contribution_id": candidate.contribution_id,
        "produced_at": stamp, "authored_by": actor, "assertions": accepted,
    })
    expected_record = ContributionReviewRecordV3(
        review_id=review_id, operation_id=operation_id, world_id=original.world_id,
        campaign_id=original.campaign_scope or None, plan_ref=plan,
        review_intent_sha256=intent, candidate_preview_sha256=contribution_v3_payload_sha256(candidate),
        stored_candidate_contribution_id=candidate.contribution_id,
        stored_candidate_sha256=contribution_v3_payload_sha256(stored),
        reviewed_contribution_id=reviewed_id,
        reviewed_contribution_sha256=contribution_v3_payload_sha256(reviewed),
        identity_proposals=proposals, identity_verdicts=verdicts,
        assertion_verdicts=assertion_verdicts, reviewer_id=actor, reviewed_at=stamp,
        confirmation_id=derive_confirmation_id(operation_id=operation_id,
            review_intent_sha256=intent, actor=actor, confirmed_at=stamp),
    )
    if (record.model_dump(mode="json") != expected_record.model_dump(mode="json")
            or review.reviewed_contribution.model_dump(mode="json") != reviewed.model_dump(mode="json")):
        raise _mismatch("complete review record or reviewed successor payload")



def authorize_original_binding(request: Any, intent: dict[str, Any], *, actor: str) -> tuple[str, str | None]:
    """Recheck only current World ownership binding, never historical Page/run state."""
    from apps.live_control_server.services.graph_object_authoring_prepare import authored_world_id
    from apps.live_control_server.services.managed_world_graph_projection import (
        WorldGraphProjectionServiceError, resolve_managed_world_binding,
    )

    managed_id = authored_world_id(request)
    binding = intent.get("publication_binding")
    if intent.get("actor") != actor:
        raise GraphObjectAuthoringError("Original confirmation actor differs.",
                                        code="confirmation_invalid", status_code=409)
    if binding is None:
        if actor.startswith("hosted_dms:") or intent.get("world_id") != managed_id:
            raise GraphObjectAuthoringError("Original World binding is missing.",
                                            code="world_binding_changed", status_code=409)
        return managed_id, request.campaign_id
    if (not isinstance(binding, dict) or binding.get("managed_world_id") != managed_id
            or request.world_id != managed_id or request.campaign_id != managed_id):
        raise GraphObjectAuthoringError("Original World binding differs.",
                                        code="world_binding_changed", status_code=409)
    try:
        current = resolve_managed_world_binding(managed_id)
    except WorldGraphProjectionServiceError as exc:
        raise GraphObjectAuthoringError(
            "Current World binding is unavailable.",
            code="authority_unavailable" if exc.status_code >= 500 else "world_binding_changed",
            status_code=503 if exc.status_code >= 500 else 409,
        ) from exc
    if (current.managed_world_id != managed_id
            or current.native_world_id != binding.get("native_world_id")
            or current.binding_version != binding.get("binding_version")
            or intent.get("world_id") != current.native_world_id):
        raise GraphObjectAuthoringError("Original World binding changed.",
                                        code="world_binding_changed", status_code=409)
    return current.native_world_id, None


def _bare_readers():
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase, PostgresFinalizedReviewPublicationRepository,
        PostgresWorldGraphRepository,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import _require_database_url

    database = PostgresDatabase(_require_database_url(None))
    return PostgresFinalizedReviewPublicationRepository(database), PostgresWorldGraphRepository(database)


def recover_original_receipt(
    request: Any, *, intent: dict[str, Any], assertions: list[Any], actor: str,
    authorize_world: Any = None,
) -> Any:
    """Read and prove an already-committed manual request; absence never publishes."""
    from dungeonmind.application.compatibility import read_historical_finalized_publication
    from dungeonmind.domain.errors import (
        CapabilityDeniedError, PersistenceIntegrityError, PersistenceUnavailableError,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        WorldGraphWriteError, derive_authority_review_operation_id, graph_review_authority_operation_id,
    )
    from apps.live_control_server.services.graph_object_authoring_prepare import proposed_assertions_digest
    from apps.live_control_server.services.graph_authoring_ids import authored_object_node_id
    from apps.live_control_server.ports.world_graph_authority import WorldGraphPublicationReceipt

    if authorize_world is not None:
        authorize_world()
    world_id, campaign_scope = authorize_original_binding(request, intent, actor=actor)
    operation = graph_review_authority_operation_id(
        world_id=world_id, campaign_id=request.campaign_id, campaign_rel=request.campaign_rel,
        source_artifact_id=intent["source_artifact_id"], source_revision_id=intent["source_revision_id"],
        sealed_proposal_digest=proposed_assertions_digest(assertions),
        expected_parent_revision_id=intent["expected_parent_revision_id"],
    )
    if operation != intent["authority_operation_id"]:
        raise GraphObjectAuthoringError("Original operation seal differs.",
                                        code="confirmation_invalid", status_code=409)
    core_operation = derive_authority_review_operation_id(
        world_id=world_id, authority_operation_id=operation, operation_namespace="worldbuilding",
    )
    try:
        reader, graphs = _bare_readers()
        history = read_historical_finalized_publication(world_id, core_operation, reader=reader)
        if history is None:
            raise GraphObjectAuthoringError(
                "No authoritative publication receipt exists for this historical operation.",
                code="publication_receipt_unavailable", status_code=409,
            )
        # Reject older recipes before accessing any unsupported assertion shape.
        from dungeonmind.contracts.contribution_review_v3 import ContributionReviewRecordV3, ContributionReviewStateV3
        if (type(history.review) is not ContributionReviewStateV3
                or type(history.review.record) is not ContributionReviewRecordV3):
            raise GraphObjectAuthoringError(
                "Historical manual recipe is unsupported; retain the original request.",
                code="publication_history_unsupported", status_code=409,
            )
        original = reconstruct_original_contribution(
            candidate=history.review.candidate_contribution, assertions=assertions,
            world_id=world_id, campaign_scope=campaign_scope, actor=actor,
            sealed_artifact_id=intent["source_artifact_id"],
            sealed_contribution_digest=intent["contribution_digest"],
        )
        try:
            parent = graphs.get_revision(world_id, intent["expected_parent_revision_id"])
        except (TypeError, ValueError, KeyError) as exc:
            # Core's exact-parent decoder can encounter malformed JSON before
            # its domain integrity wrapper. Keep this conversion at that read.
            raise _mismatch("immutable parent decoding") from exc
        verify_review_correspondence(
            original=original, history=history, parent=parent, operation_id=core_operation,
            expected_parent_id=intent["expected_parent_revision_id"],
            admitted_revision_id=intent["source_revision_id"], actor=actor,
        )
    except PersistenceUnavailableError as exc:
        raise GraphObjectAuthoringError("Historical authority is unavailable.",
                                        code="authority_unavailable", status_code=503) from exc
    except PersistenceIntegrityError as exc:
        raise _mismatch("stored terminal integrity") from exc
    except CapabilityDeniedError as exc:
        raise GraphObjectAuthoringError("Historical receipt recipe is unsupported.",
                                        code="publication_history_unsupported", status_code=409) from exc
    except WorldGraphWriteError as exc:
        if exc.code != "authority_unavailable":
            raise _mismatch("historical producer reconstruction") from exc
        raise GraphObjectAuthoringError("Historical authority is unavailable.",
                                        code="authority_unavailable", status_code=503) from exc
    accepted = history.review.reviewed_contribution.assertions
    created = {item.subject_object_id for item in accepted if item.assertion_kind == "node"}
    if any(authored_object_node_id(item.assertion_id) not in created
           for item in assertions if item.assertion_kind == "object"):
        raise _mismatch("created-node response correspondence")
    if authorize_world is not None:
        authorize_world()
    if authorize_original_binding(request, intent, actor=actor) != (world_id, campaign_scope):
        raise _mismatch("late World binding correspondence")
    publication = history.publication
    return WorldGraphPublicationReceipt(
        world_id=world_id, authority_operation_id=operation,
        parent_revision_id=publication.expected_parent_revision_id,
        published_revision_id=publication.published_revision_id,
        reviewed_contribution_id=publication.reviewed_contribution_id,
        accepted_assertion_ids=tuple(item.assertion_id for item in accepted),
        published=True, outcome="already_applied",
        reviewed_contribution_sha256=publication.reviewed_contribution_sha256,
    )
