"""Authenticate retained Worldbuilding requests before immutable receipt recovery.

Original producer output is reconstructed from authenticated retained effect, not
from a current preview or from recorded terminal answers. This module grants no
permission to publish when a terminal receipt is absent.
"""
from __future__ import annotations

from typing import Any

from apps.live_control_server.models.extract_promote import (
    WORLD_BUILDING_WRITE_PLAN_SCHEMA,
    WorldbuildingWritePlanResponse,
)
from apps.live_control_server.services.extract_promote import ExtractPromoteError


def _invalid(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Original Worldbuilding confirmation failed verification: {reason}.",
        code="plan_verification_failed", status_code=409,
    )


def _unsupported(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Historical Worldbuilding recipe is unsupported; retain the original request: {reason}.",
        code="publication_history_unsupported", status_code=409,
    )


def authenticate_original_plan(plan: WorldbuildingWritePlanResponse) -> dict[str, Any]:
    """Prove the full retained plan identity and original prepare signature.

    No current World/source/head/vocabulary service is consulted. The vocabulary
    references below name the historical versions explicitly. This authenticates
    an original request; it cannot replace complete terminal correspondence.
    """
    from graph_memory.worldbuilding_write_plan import (
        WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY, WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND,
        WorldbuildingWritePlanError, _canonical_effect, _digest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import _require_prepare_binding

    if plan.schema_ != WORLD_BUILDING_WRITE_PLAN_SCHEMA or plan.version != 2:
        raise _unsupported("plan generation")
    if (plan.effect.identity_authority is None or plan.publication_binding is None
            or plan.source_admission is None or plan.native_vocabulary_binding is None):
        raise _unsupported("missing original sealed bindings")
    try:
        effect = _canonical_effect(plan.effect.model_dump(mode="json", by_alias=True))
    except WorldbuildingWritePlanError as exc:
        raise _invalid("canonical effect") from exc
    identity = {
        "world_id": plan.world_id, "parent_revision_id": plan.parent_revision_id,
        "run_id": plan.run_id, "source_domain": plan.source_domain,
        "source_artifact_id": plan.source_artifact_id, "source_revision_id": plan.source_revision_id,
        "extraction_profile": plan.extraction_profile, "candidate_preview_id": plan.candidate_preview_id,
        "candidate_schema": plan.candidate_schema, "candidate_version": plan.candidate_version,
        "decision_snapshot": effect["decision_snapshot"], "effect": effect,
    }
    digest = _digest(identity)
    if (digest != plan.plan_digest
            or plan.plan_id != f"worldbuilding-write-plan:{digest.removeprefix('sha256:')[:24]}"
            or plan.decision_digest != _digest(effect["decision_snapshot"])):
        raise _invalid("original plan or decision digest")
    # Authenticate every binding before interpreting it or using it for I/O.
    _require_prepare_binding(plan, effect["identity_authority"])
    meta, admission, binding = effect["contribution_meta"], plan.source_admission, plan.publication_binding
    if (meta["source_kind"] != WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND
            or meta["authored_by"] != WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY
            or meta["source_artifact_id"] != plan.source_artifact_id
            or meta["source_revision_id"] != plan.source_revision_id
            or meta["extraction_profile"] != plan.extraction_profile
            or meta["campaign_scope"] is not None
            or binding.native_world_id != plan.world_id
            or binding.source_artifact_id != plan.source_artifact_id
            or admission.source_artifact_id != plan.source_artifact_id
            or admission.buddy_source_revision_id != plan.source_revision_id
            or admission.content_sha256 != binding.source_sha256):
        raise _invalid("original source, World or contribution bindings")
    from dungeonmind_dnd.application.world_object_vocabulary import builtin_world_object_v6_vocabulary_ref
    from dungeonmind_dnd.application.world_property_vocabulary import builtin_world_property_v4_vocabulary_ref

    vocabulary = plan.native_vocabulary_binding
    if (vocabulary.world_object_vocabulary != builtin_world_object_v6_vocabulary_ref().model_dump(mode="json")
            or vocabulary.world_property_vocabulary != builtin_world_property_v4_vocabulary_ref().model_dump(mode="json")):
        raise _unsupported("historical vocabulary pair")
    decisions = {item["assertion_id"]: item for item in effect["decision_snapshot"]}
    effect_map = effect["candidate_effect_map"]
    if set(decisions) != set(effect_map):
        raise _invalid("decision/effect coverage")
    accepted = {item["assertion_id"]: item for item in effect["accepted_proposals"]}
    rejected = {item["assertion_id"]: item for item in effect["rejected_assertions"]}
    mapped_ids = [identifier for ids in effect_map.values() for identifier in ids]
    if (len(mapped_ids) != len(set(mapped_ids))
            or len(accepted) != len(effect["accepted_proposals"])
            or len(rejected) != len(effect["rejected_assertions"]) or set(accepted) & set(rejected)
            or {identifier for ids in effect_map.values() for identifier in ids} != set(accepted) | set(rejected)):
        raise _invalid("assertion/effect coverage")
    deferred = {identifier for identifier, item in decisions.items() if item["decision"] == "defer"}
    if set(effect["deferred_candidate_ids"]) != deferred:
        raise _invalid("deferred decision coverage")
    node_decisions = {identifier: item for identifier, item in decisions.items()
                      if item["candidate_kind"] == "node" and item["decision"] in {"create_new", "bind_existing"}}
    expected_nodes = {identifier: identifier if item["decision"] == "create_new" else item["target_node_id"]
                      for identifier, item in node_decisions.items()}
    if effect["node_id_map"] != expected_nodes:
        raise _invalid("original node decision targets")
    outcomes = {"create_new": "created_new", "bind_existing": "human_override",
                "accept": "accepted_by_operator", "reject": "rejected_by_operator", "defer": "deferred_by_operator"}
    expected_outcomes = {identifier: outcomes[item["decision"]] for identifier, item in decisions.items()
                         if item["candidate_kind"] != "source_observation"}
    if effect["identity_outcome_snapshot"] != expected_outcomes:
        raise _invalid("identity disposition snapshot")
    for identifier, decision in decisions.items():
        ids, disposition = effect_map[identifier], decision["decision"]
        partition = rejected if disposition == "reject" else accepted
        if (disposition == "defer" and ids) or any(item not in partition for item in ids):
            raise _invalid("decision/assertion partition")
        kind = decision["candidate_kind"]
        if kind == "edge" and disposition != "defer":
            if (len(ids) != 1 or partition[ids[0]]["assertion_kind"] != "edge"
                    or not isinstance(partition[ids[0]]["value"], dict)
                    or partition[ids[0]]["value"].get("extract_edge_id") != identifier):
                raise _invalid("edge decision/effect ownership")
        if kind == "node" and disposition == "reject":
            if (len(ids) != 1 or rejected[ids[0]]["assertion_kind"] != "node"
                    or rejected[ids[0]]["subject_node_id"] != identifier):
                raise _invalid("rejected node decision/effect ownership")
        if kind == "source_observation" or disposition == "bind_existing":
            if any(partition[item]["assertion_kind"] not in {"attribute", "alias", "evidence_ref"} for item in ids):
                raise _invalid("support-only decision/effect ownership")
        if disposition == "create_new" and (len(ids) != 1 or accepted[ids[0]]["assertion_kind"] != "node"):
            raise _invalid("create-new node assertion coverage")
        if decision["candidate_kind"] == "node" and disposition in {"create_new", "bind_existing"}:
            target = effect["node_id_map"].get(identifier)
            if not target or any(accepted[item]["subject_node_id"] != target for item in ids):
                raise _invalid("node target correspondence")
    for assertion in [*accepted.values(), *rejected.values()]:
        if (assertion["source_artifact_id"] != meta["source_artifact_id"]
                or assertion["source_revision_id"] != meta["source_revision_id"]
                or assertion["campaign_scope"] != meta["campaign_scope"]):
            raise _invalid("assertion source correspondence")
    return effect



def reconstruct_original_mapping(plan: WorldbuildingWritePlanResponse) -> tuple[Any, Any]:
    """Reproduce the authenticated typed-V3 producer without current source reads.

    Returns the original Buddy contribution and the pre-review Core mapping.
    Full candidate/review/receipt equality remains a separate required proof.
    """
    import copy
    import json
    from types import SimpleNamespace
    from graph_memory.worldbuilding_write_plan import materialize_worldbuilding_contribution
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        CURRENT_WORLD_BUILDING_V6_TARGET, resolve_buddy_predicate_mapping_v4,
    )
    from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
        ContributionMappingError, map_worldbuilding_extraction_contribution_v3,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import _BuddyEvidenceRecord
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import _worldbuilding_expressible
    from apps.live_control_server.ports.world_graph_authority import WorldGraphAuthorityError

    effect = copy.deepcopy(authenticate_original_plan(plan))
    decisions = {item["assertion_id"]: item for item in effect["decision_snapshot"]}
    for assertion in effect["accepted_proposals"]:
        if assertion["assertion_kind"] != "edge" or assertion["predicate"] != "governs":
            continue
        value = assertion["value"]
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise _invalid("governs effect value") from exc
        value = dict(value) if isinstance(value, dict) else {}
        edge_id = str(value.get("extract_edge_id") or "").strip()
        decision = decisions.get(edge_id)
        if (decision is None or decision["candidate_kind"] != "edge" or decision["decision"] != "accept"
                or assertion["assertion_id"] not in effect["candidate_effect_map"].get(edge_id, [])):
            raise _invalid("governs decision/effect binding")
        mapping = resolve_buddy_predicate_mapping_v4("governs", target=CURRENT_WORLD_BUILDING_V6_TARGET)
        if mapping != ("dnd5e:governs", False):
            raise _unsupported("governs historical transformation")
        # The original producer's endpoint admission used the now-unavailable
        # preview. Reproduce its output from the signed effect, not that check.
        assertion["predicate"] = mapping[0]
        assertion["value"] = {**value, "buddy_predicate": "governs", "dm_predicate": mapping[0],
                              "native_vocabulary_binding": plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True)}
    contribution = materialize_worldbuilding_contribution(
        world_id=plan.world_id, plan_digest=plan.plan_digest, effect=effect,
    )
    try:
        wire_contribution = _worldbuilding_expressible(contribution)
    except WorldGraphAuthorityError as exc:
        raise _invalid("original identity outcome transport") from exc
    admission = plan.source_admission
    pair = (plan.source_artifact_id, plan.source_revision_id)
    locator = str(admission.source_locator or "").strip()
    if not locator:
        raise _invalid("sealed immutable source locator")
    records: dict[str, Any] = {}
    for assertion in [*contribution.accepted_assertions, *contribution.rejected_assertions]:
        rows = assertion.value.get("evidence") if isinstance(assertion.value, dict) else None
        ids = list(assertion.evidence_ref_ids)
        if (not ids or len(set(ids)) != len(ids) or any(not item.strip() for item in ids)
                or not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)):
            raise _invalid("typed extraction evidence recipe")
        by_id = {str(row.get("evidence_ref_id") or ""): row for row in rows}
        if len(by_id) != len(rows) or set(by_id) != set(ids):
            raise _invalid("typed extraction evidence coverage")
        for raw_id in ids:
            row = by_id[raw_id]
            span = str(row.get("source_span_ref_id") or "").strip()
            if (row.get("source_artifact_id") != pair[0]
                    or row.get("source_revision_id") not in (None, pair[1])
                    or row.get("source_content_sha256") not in (None, admission.content_sha256)
                    or row.get("source_domain") != "worldbuilding" or not span):
                raise _invalid("authenticated evidence source/span correspondence")
            record = _BuddyEvidenceRecord(
                evidence_ref_id=raw_id, source_artifact_id=pair[0], source_domain="worldbuilding",
                evidence_role="support", can_open_source=bool(locator), can_highlight_span=bool(span),
                locator=span or locator, uri=locator, source_span_ref_id=span,
            )
            if raw_id in records and records[raw_id] != record:
                raise _invalid("operation-wide evidence identity collision")
            records[raw_id] = record
    try:
        mapped = map_worldbuilding_extraction_contribution_v3(
            SimpleNamespace(evidence=records), wire_contribution, {pair: admission.source_revision_id},
        )
    except ContributionMappingError as exc:
        raise _invalid("typed extraction mapping") from exc
    return contribution, mapped



def reconstruct_candidate(mapped: Any, *, produced_at: Any) -> tuple[Any, dict[str, Any]]:
    """Reproduce review staging, without the producer's fresh endpoint admission."""
    import json
    from dungeonmind.contracts.contribution import AcceptanceState, ContributionStatus
    from dungeonmind.domain.canonical import canonical_json
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        CURRENT_V5_TARGET, resolve_buddy_predicate_mapping_v4,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _normalized_temporal_scope, _qualified_assertion_update,
    )

    qualified, states = [], {}
    for assertion in mapped.assertions:
        state = assertion.acceptance_state
        if state not in {AcceptanceState.ACCEPTED, AcceptanceState.REJECTED}:
            raise _invalid("unadjudicated original assertion")
        states[assertion.assertion_id] = state
        update: dict[str, Any] = {"acceptance_state": AcceptanceState.CANDIDATE}
        if state is AcceptanceState.ACCEPTED:
            update["temporal_scope"] = _normalized_temporal_scope(assertion.temporal_scope)
            if assertion.assertion_kind == "edge":
                value = json.loads(assertion.value) if assertion.value else {}
                value = value if isinstance(value, dict) else {}
                existing = value.get("dm_predicate")
                if assertion.predicate == "operates":
                    raise _unsupported("manual-only place operation")
                if not isinstance(existing, str) or not existing.strip():
                    mapping = resolve_buddy_predicate_mapping_v4(str(assertion.predicate or ""), target=CURRENT_V5_TARGET)
                    if mapping is None or not mapping[0]:
                        raise _unsupported("historical edge predicate")
                    predicate, reverse = mapping
                    update["value"] = canonical_json({**value, "dm_predicate": predicate})
                    if reverse:
                        update.update(subject_object_id=assertion.object_object_id,
                                      object_object_id=assertion.subject_object_id)
            else:
                # Only edge qualification consults parent endpoint kinds.
                # These existing node/attribute/alias/evidence transformations
                # are pure and preserve the original closed producer recipe.
                update.update(_qualified_assertion_update(assertion, endpoint_kinds={}))
        qualified.append(assertion.model_copy(update=update))
    return mapped.model_copy(update={
        "assertions": qualified, "status": ContributionStatus.ACTIVE,
        "supersedes_contribution_id": None, "identity_decision_ids": [], "produced_at": produced_at,
    }), states


def _integrity(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Historical Worldbuilding publication integrity failed: {reason}.",
        code="publication_integrity_failure", status_code=409,
    )


def verify_review_correspondence(
    plan: WorldbuildingWritePlanResponse, *, original: Any, mapped: Any,
    history: Any, parent: Any, operation_id: str,
) -> None:
    """Verify the COMPLETE original candidate, review and successor at parent time."""
    from dungeonmind.contracts.contribution import ContributionStatus
    from dungeonmind.contracts.contribution_review import (
        ContributionAssertionVerdict, ContributionPlanRef,
        derive_confirmation_id, derive_review_id, derive_reviewed_contribution_id,
    )
    from dungeonmind.contracts.contribution_review_v3 import (
        ContributionReviewRecordV3, ContributionReviewStateV3,
        contribution_v3_payload_sha256, derive_review_intent_sha256_v3, reviewed_v3_identity_outcome,
    )
    from dungeonmind.domain.canonical import canonical_sha256
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        WORLDBUILDING_SOURCE_PLAN_SCHEMA, _build_identity_dispositions,
    )

    review, publication, child = history.review, history.publication, history.revision
    if type(review) is not ContributionReviewStateV3 or type(review.record) is not ContributionReviewRecordV3:
        raise _unsupported("terminal review generation")
    if parent is None:
        raise _integrity("missing original parent")
    record, envelope = review.record, parent.revision
    if (envelope.world_id != plan.world_id or envelope.revision_id != plan.parent_revision_id
            or envelope.status != "published" or envelope.graph_schema != publication.graph_schema
            or envelope.graph_payload_sha256 != canonical_sha256(parent.graph_payload)
            or envelope.graph_payload_sha256 != publication.parent_graph_payload_sha256
            or parent.graph_payload.get("semantic_profile") != record.plan_ref.semantic_profile.model_dump(mode="json")
            or publication.expected_parent_revision_id != plan.parent_revision_id):
        raise _integrity("immutable parent correspondence")
    stamp, actor = envelope.created_at, str(plan.run_id)
    if record.reviewed_at != stamp or publication.published_at != stamp or child.created_at != stamp:
        raise _integrity("original producer timestamp")
    candidate, states = reconstruct_candidate(mapped, produced_at=stamp)
    stored = candidate.model_copy(update={"status": ContributionStatus.SUPERSEDED})
    if stored.model_dump(mode="json") != review.candidate_contribution.model_dump(mode="json"):
        raise _integrity("complete candidate payload")
    proposals, verdicts = _build_identity_dispositions(candidate, states)
    assertion_verdicts = [ContributionAssertionVerdict(
        assertion_id=item.assertion_id, acceptance_state=states[item.assertion_id],
    ) for item in sorted(candidate.assertions, key=lambda item: item.assertion_id)]
    plan_ref = ContributionPlanRef(
        source_plan_schema=WORLDBUILDING_SOURCE_PLAN_SCHEMA, source_plan_id=operation_id,
        source_plan_sha256=canonical_sha256({"operation_id": operation_id, "contribution_id": original.contribution_id}),
        source_input_sha256=canonical_sha256({"contribution_id": original.contribution_id}),
        preview_content_sha256=canonical_sha256({}), candidate_contribution_sha256=contribution_v3_payload_sha256(candidate),
        expected_parent_revision_id=plan.parent_revision_id, base_graph_schema=envelope.graph_schema,
        base_graph_payload_sha256=envelope.graph_payload_sha256, semantic_profile=parent.graph_payload["semantic_profile"],
    )
    intent = derive_review_intent_sha256_v3(
        operation_id=operation_id, world_id=plan.world_id, campaign_id=original.campaign_scope or None,
        plan_ref=plan_ref, candidate_contribution=candidate, identity_proposals=proposals,
        identity_verdicts=verdicts, assertion_verdicts=assertion_verdicts, reviewer_id=actor, reviewed_at=stamp,
    )
    review_id = derive_review_id(operation_id=operation_id, review_intent_sha256=intent, world_id=plan.world_id)
    reviewed_id = derive_reviewed_contribution_id(review_id=review_id, candidate_contribution_id=candidate.contribution_id)
    outcomes = {item.target_object_id: reviewed_v3_identity_outcome(item.verdict) for item in verdicts}
    assertions = []
    for item in candidate.assertions:
        update = {"acceptance_state": states[item.assertion_id]}
        if item.assertion_kind in {"node", "alias"} and item.subject_object_id in outcomes:
            update["identity_resolution_outcome"] = outcomes[item.subject_object_id]
        assertions.append(item.model_copy(update=update))
    reviewed = candidate.model_copy(update={
        "contribution_id": reviewed_id, "status": ContributionStatus.ACTIVE,
        "supersedes_contribution_id": candidate.contribution_id, "produced_at": stamp,
        "authored_by": actor, "assertions": assertions,
    })
    expected_record = ContributionReviewRecordV3(
        review_id=review_id, operation_id=operation_id, world_id=plan.world_id,
        campaign_id=original.campaign_scope or None, plan_ref=plan_ref, review_intent_sha256=intent,
        candidate_preview_sha256=contribution_v3_payload_sha256(candidate),
        stored_candidate_contribution_id=candidate.contribution_id, stored_candidate_sha256=contribution_v3_payload_sha256(stored),
        reviewed_contribution_id=reviewed_id, reviewed_contribution_sha256=contribution_v3_payload_sha256(reviewed),
        identity_proposals=proposals, identity_verdicts=verdicts, assertion_verdicts=assertion_verdicts,
        reviewer_id=actor, reviewed_at=stamp,
        confirmation_id=derive_confirmation_id(operation_id=operation_id, review_intent_sha256=intent,
                                                actor=actor, confirmed_at=stamp),
    )
    if (record.model_dump(mode="json") != expected_record.model_dump(mode="json")
            or review.reviewed_contribution.model_dump(mode="json") != reviewed.model_dump(mode="json")):
        raise _integrity("complete review record or reviewed successor payload")



def authorize_current_binding(plan: WorldbuildingWritePlanResponse) -> tuple[str, str, int]:
    """Current managed/native binding only; historical Page/run state is irrelevant."""
    from apps.live_control_server.services.managed_world_graph_projection import (
        WorldGraphProjectionServiceError, resolve_managed_world_binding,
    )
    binding = plan.publication_binding
    if binding is None:
        raise _unsupported("missing publication binding")
    try:
        current = resolve_managed_world_binding(binding.managed_world_id)
    except WorldGraphProjectionServiceError as exc:
        raise ExtractPromoteError(
            "Current World binding is unavailable.",
            code="authority_unavailable" if exc.status_code >= 500 else "worldbuilding_source_binding_changed",
            status_code=503 if exc.status_code >= 500 else 409,
        ) from exc
    if (current.managed_world_id != binding.managed_world_id or current.native_world_id != binding.native_world_id
            or current.binding_version != binding.binding_version or current.native_world_id != plan.world_id):
        raise ExtractPromoteError("Original World binding changed; retain the original request.",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    return current.managed_world_id, current.native_world_id, current.binding_version


def _bare_readers():
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase, PostgresFinalizedReviewPublicationRepository, PostgresWorldGraphRepository,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import _require_database_url

    database = PostgresDatabase(_require_database_url(None))
    return PostgresFinalizedReviewPublicationRepository(database), PostgresWorldGraphRepository(database)


def recover_original_publication(plan: WorldbuildingWritePlanResponse, *, authorize_write: Any = None) -> Any:
    """Return a fully proved original receipt, never permission for a new write."""
    from dungeonmind.application.compatibility import read_historical_finalized_publication
    from dungeonmind.contracts.contribution_review_v3 import ContributionReviewRecordV3, ContributionReviewStateV3
    from dungeonmind.domain.errors import CapabilityDeniedError, PersistenceIntegrityError, PersistenceUnavailableError
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        WorldGraphWriteError, derive_authority_review_operation_id, worldbuilding_authority_operation_id,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import _confirm_receipt

    authenticate_original_plan(plan)
    if authorize_write is not None:
        authorize_write()
    binding = authorize_current_binding(plan)
    operation = derive_authority_review_operation_id(
        world_id=plan.world_id, authority_operation_id=worldbuilding_authority_operation_id(
            world_id=plan.world_id, plan_id=plan.plan_id, plan_digest=plan.plan_digest),
        operation_namespace="worldbuilding",
    )
    try:
        reader, graph = _bare_readers()
        history = read_historical_finalized_publication(plan.world_id, operation, reader=reader)
        if history is None:
            raise ExtractPromoteError(
                "No authoritative publication receipt exists; retain the original request.",
                code="publication_receipt_unavailable", status_code=409,
            )
        if type(history.review) is not ContributionReviewStateV3 or type(history.review.record) is not ContributionReviewRecordV3:
            raise _unsupported("terminal review generation")
        original, mapped = reconstruct_original_mapping(plan)
        try:
            parent = graph.get_revision(plan.world_id, plan.parent_revision_id)
        except (TypeError, ValueError, KeyError) as exc:
            raise _integrity("immutable parent decoding") from exc
        verify_review_correspondence(plan, original=original, mapped=mapped, history=history,
                                     parent=parent, operation_id=operation)
    except PersistenceUnavailableError as exc:
        raise ExtractPromoteError("Historical Worldbuilding authority is unavailable.",
                                 code="authority_unavailable", status_code=503) from exc
    except PersistenceIntegrityError as exc:
        raise _integrity("stored terminal correspondence") from exc
    except CapabilityDeniedError as exc:
        raise _unsupported("receipt generation") from exc
    except WorldGraphWriteError as exc:
        if exc.code != "authority_unavailable":
            raise _integrity("original producer reconstruction") from exc
        raise ExtractPromoteError("Historical Worldbuilding authority is unavailable.",
                                 code="authority_unavailable", status_code=503) from exc
    if authorize_write is not None:
        authorize_write()
    if authorize_current_binding(plan) != binding:
        raise _integrity("late World binding correspondence")
    publication = history.publication
    # Preserve the original response's contribution ID and head_advanced meaning
    # (the recorded child differs from its parent, including on a replay).
    # audit_status reflects complete immutable correspondence, not source opening.
    return _confirm_receipt(
        outcome="already_applied", verified=plan.model_dump(mode="json"), contribution=original,
        parent_revision_id=plan.parent_revision_id, committed_revision_id=publication.published_revision_id,
        head_advanced=publication.published_revision_id != plan.parent_revision_id,
        accepted_assertion_ids=[item.assertion_id for item in original.accepted_assertions],
        rejected_assertion_ids=[item.assertion_id for item in original.rejected_assertions],
        audit_status="ok", warnings=[],
    )
