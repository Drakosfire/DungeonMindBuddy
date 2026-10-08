from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    ArchiveCommand,
    ConversationCommand,
    DraftSave,
    DraftSubmit,
    HistoricalReference,
    LegacyImport,
    LegacyTurn,
    ReopenCommand,
    SubmittedGraphFocusIntentV1,
    SubmittedGraphRequestIntentV1,
    SubmittedGraphSelectionIntentV1,
    SubmittedPlanPlayableTargetV1,
    SubmittedPrimaryWorkIntentV1,
    SubmittedTurnIntentV1,
    TurnFailure,
    TurnProvenance,
    TurnResult,
    TurnSubmission,
    submitted_turn_intent_fingerprint_v1,
)
from application_state.config import APPLICATION_STATE_DSN_ENV
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateUnavailableError,
    ApplicationStateValidationError,
)


def _ref(
    kind: str, object_id: str, revision: str, digest: str | None = None
) -> HistoricalReference:
    return HistoricalReference(
        resolution="resolved",
        kind=kind,
        object_id=object_id,
        revision=revision,
        content_sha256=digest,
    )


def _provenance(
    world_id: str = "world-one", *, run_id: str = "run-1"
) -> TurnProvenance:
    return TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="play",
        primary_work=_ref("play_run", run_id, "run-rev-7"),
        supporting_work=[
            _ref("runbook", "runbook-1", "revision-4", "a" * 64),
            _ref("beat", "beat-2", "beat-rev-3"),
        ],
        selected_object=_ref("scene", "scene-9", "scene-rev-2"),
    )


def _submitted_intent(
    world_id: str,
    message: str,
    *,
    client_thread_id: str = "client-thread-1",
    surface_id: str = "play",
    surface_instance_id: str = "play-main",
    graph_selection: str | None = None,
) -> SubmittedTurnIntentV1:
    return SubmittedTurnIntentV1(
        world_id=world_id,
        client_thread_id=client_thread_id,
        message=message,
        surface_id=surface_id,
        surface_instance_id=surface_instance_id,
        client_work_state="none",
        primary_work=None,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=(
            None
            if graph_selection is None
            else SubmittedGraphSelectionIntentV1(node_id=graph_selection)
        ),
    )


def _without_0012_fields(value):
    if isinstance(value, list):
        return [_without_0012_fields(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _without_0012_fields(item)
            for key, item in value.items()
            if not (
                key
                in {
                    "surface_instance_id",
                    "object_revision",
                    "work_revision_id",
                    "revision_n",
                }
                and item is None
            )
        }
    return value


def test_additive_null_provenance_fields_preserve_legacy_fingerprint_shape() -> None:
    from application_state.agent_conversation.types import (
        request_fingerprint,
        turn_idempotency_fingerprint,
    )

    provenance = _provenance("fingerprint-world")
    legacy_shape = _without_0012_fields(provenance.model_dump(mode="json"))
    payload = {
        "world_id": "fingerprint-world",
        "user_text": "stable retry",
        "provenance": legacy_shape,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    expected = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    assert (
        turn_idempotency_fingerprint("fingerprint-world", "stable retry", provenance)
        == expected
    )
    assert (
        request_fingerprint(provenance)
        == hashlib.sha256(
            json.dumps(
                legacy_shape, sort_keys=True, separators=(",", ":"), default=str
            ).encode("utf-8")
        ).hexdigest()
    )
    assert request_fingerprint(
        provenance.model_copy(update={"surface_instance_id": "plan-pane-2"})
    ) != request_fingerprint(provenance)


def test_graphless_turn_request_fingerprint_omits_new_null_policy_fields() -> None:
    from application_state.agent_conversation.types import request_fingerprint

    submission = TurnSubmission(
        world_id="fingerprint-graphless-world",
        conversation_id=uuid4(),
        idempotency_key=uuid4(),
        expected_conversation_revision=2,
        user_text="Keep the old request fingerprint shape.",
        provenance=_provenance("fingerprint-graphless-world"),
        submitted_intent_v1=_submitted_intent(
            "fingerprint-graphless-world", "Keep the old request fingerprint shape."
        ),
    )
    payload = _without_0012_fields(
        submission.model_dump(
            mode="json",
            exclude={
                "idempotency_key",
                "submitted_intent_v1",
                "submitted_intent_v2",
                "graph_context_receipt",
                "graph_context_execution",
            },
        )
    )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    expected = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    assert request_fingerprint(submission) == expected


def test_graph_execution_records_enforce_event_order_and_policy() -> None:
    from application_state.agent_conversation.types import (
        GraphExecutionAccountingV1,
        GraphExecutionPolicyV1,
        PlanWorldGraphExecutionV1,
        ValidatedGraphOperationEventV1,
    )

    policy = GraphExecutionPolicyV1(
        policy_version="test-v1",
        allowed_graph_operations=["search_assertions"],
        max_provider_attempts=2,
        max_graph_operations=2,
        max_results_per_operation=8,
        max_total_provider_input_tokens=100,
        max_total_provider_output_tokens=50,
        provider_input_accounting=GraphExecutionAccountingV1(
            kind="conservative_upper_bound",
            estimator="utf8_json_bytes_plus_64_per_node_v1",
        ),
        source_opened=False,
    )
    operation = ValidatedGraphOperationEventV1(
        event_id=uuid4(), sequence=1, kind="validated_graph_operation",
        operation_id=uuid4(), operation="search_assertions",
        request_arguments_sha256="a" * 64, graph_revision="revision-1",
        result_packet_sha256="b" * 64, assertion_ids=[], relationship_ids=[],
        evidence_ref_ids=[], evidence_sufficiency_status="insufficient",
        coverage_status="incomplete", truncated=False, source_opened=False,
    )
    with pytest.raises(ValidationError, match="contiguous sequence"):
        PlanWorldGraphExecutionV1(
            schema="dmb_agent_plan_world_graph_execution_v1",
            context_receipt_sha256="c" * 64,
            policy=policy,
            events=[operation],
        )
    with pytest.raises(ValidationError, match="max_provider_attempts"):
        GraphExecutionPolicyV1.model_validate(
            policy.model_dump() | {"max_provider_attempts": 0}
        )
    with pytest.raises(ValidationError, match="conservative provider input estimator"):
        GraphExecutionPolicyV1.model_validate(
            policy.model_dump()
            | {
                "provider_input_accounting": {
                    "kind": "conservative_upper_bound",
                    "estimator": "unrecognized-estimator",
                }
            }
        )
    oversized_events = [
        operation.model_dump() | {
            "event_id": uuid4(),
            "operation_id": uuid4(),
            "sequence": sequence,
        }
        for sequence in range(2049)
    ]
    with pytest.raises(ValidationError, match="at most 2048"):
        PlanWorldGraphExecutionV1.model_validate(
            {
                "schema": "dmb_agent_plan_world_graph_execution_v1",
                "context_receipt_sha256": "c" * 64,
                "policy": policy.model_dump(),
                "events": oversized_events,
            }
        )

    long_ids = [f"{'x' * 2048}{index:04d}" for index in range(512)]
    oversized_operation = ValidatedGraphOperationEventV1(
        event_id=uuid4(), sequence=0, kind="validated_graph_operation",
        operation_id=uuid4(), operation="search_assertions",
        request_arguments_sha256="a" * 64, graph_revision="revision-1",
        result_packet_sha256="b" * 64, assertion_ids=long_ids,
        relationship_ids=[], evidence_ref_ids=[],
        evidence_sufficiency_status="insufficient",
        coverage_status="incomplete", truncated=False, source_opened=False,
    )
    large_policy = GraphExecutionPolicyV1.model_validate(
        policy.model_dump() | {"max_results_per_operation": 4096}
    )
    with pytest.raises(ValidationError, match="storage size limit"):
        PlanWorldGraphExecutionV1(
            schema="dmb_agent_plan_world_graph_execution_v1",
            context_receipt_sha256="c" * 64,
            policy=large_policy,
            events=[oversized_operation],
        )


def test_content_reference_requires_complete_typed_revision_and_resolved_identity() -> (
    None
):
    from application_state.agent_conversation.types import HistoricalReference

    revision_id = uuid4()
    complete = HistoricalReference(
        resolution="resolved",
        kind="plan",
        object_id="plan-1",
        content_sha256="c" * 64,
        object_revision=4,
        work_revision_id=revision_id,
        revision_n=3,
    )
    assert complete.work_revision_id == revision_id

    for invalid in (
        {
            "resolution": "resolved",
            "kind": "plan",
            "object_id": "plan-1",
            "content_sha256": "c" * 64,
            "object_revision": 4,
            "work_revision_id": revision_id,
        },
        {
            "resolution": "resolved",
            "kind": "plan",
            "object_id": "plan-1",
            "object_revision": 4,
            "work_revision_id": revision_id,
            "revision_n": 3,
        },
        {
            "resolution": "resolved",
            "kind": "plan",
            "object_id": "plan-1",
            "content_sha256": "c" * 64,
            "object_revision": 0,
            "work_revision_id": revision_id,
            "revision_n": 3,
        },
        {
            "resolution": "resolved",
            "kind": "plan",
            "object_id": "plan-1",
            "content_sha256": "c" * 64,
            "object_revision": 4,
            "work_revision_id": revision_id,
            "revision_n": True,
        },
        {
            "resolution": "resolved",
            "kind": "plan",
            "object_id": "plan-1",
            "content_sha256": "c" * 64,
            "object_revision": True,
            "work_revision_id": revision_id,
            "revision_n": 3,
        },
        {
            "resolution": "resolved",
            "kind": "plan",
            "object_id": "plan-1",
            "content_sha256": "c" * 64,
            "object_revision": 4,
            "work_revision_id": "not-a-uuid",
            "revision_n": 3,
        },
        {
            "resolution": "absent",
            "object_revision": 4,
            "work_revision_id": revision_id,
            "revision_n": 3,
            "content_sha256": "c" * 64,
        },
    ):
        with pytest.raises(ValidationError):
            HistoricalReference.model_validate(invalid)


def test_submitted_turn_intent_v1_fingerprint_covers_replayable_semantics() -> None:
    intent = _submitted_intent("intent-world", "Where is the caravan?")
    fingerprint = submitted_turn_intent_fingerprint_v1(intent)

    assert len(fingerprint) == 64
    assert submitted_turn_intent_fingerprint_v1(intent) == fingerprint
    assert submitted_turn_intent_fingerprint_v1(
        intent.model_copy(update={"message": "Where is the caravan now?"})
    ) != fingerprint
    assert submitted_turn_intent_fingerprint_v1(
        intent.model_copy(update={"surface_instance_id": "play-side-panel"})
    ) != fingerprint
    assert submitted_turn_intent_fingerprint_v1(
        intent.model_copy(update={"client_thread_id": "client-thread-2"})
    ) == fingerprint
    assert submitted_turn_intent_fingerprint_v1(
        intent.model_copy(
            update={
                "graph_selection": SubmittedGraphSelectionIntentV1(
                    node_id="node-17"
                )
            }
        )
    ) != fingerprint
    plan_intent = intent.model_copy(
        update={
            "client_work_state": "saved_clean",
            "primary_work": SubmittedPrimaryWorkIntentV1(
                kind="plan",
                object_id="plan-4",
                expected_revision=9,
                expected_revision_n=3,
                expected_content_sha256="a" * 64,
            ),
        }
    )
    plan_fingerprint = submitted_turn_intent_fingerprint_v1(plan_intent)
    pre_target_payload = plan_intent.model_dump(
        mode="json", by_alias=True, exclude={"client_thread_id"}
    )
    pre_target_payload.pop("playable_target", None)
    assert plan_fingerprint == hashlib.sha256(
        json.dumps(pre_target_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert submitted_turn_intent_fingerprint_v1(
        plan_intent.model_copy(
            update={
                "primary_work": plan_intent.primary_work.model_copy(
                    update={"expected_revision_n": 4}
                )
            }
        )
    ) != plan_fingerprint
    targeted_intent = plan_intent.model_copy(update={
        "playable_target": SubmittedPlanPlayableTargetV1(
            schema="dmb_plan_playable_target_v1", kind="scene", id="scene:arrival"
        )
    })
    with pytest.raises(ValueError, match="graphless saved Plan turn"):
        SubmittedTurnIntentV1.model_validate({
            **targeted_intent.model_dump(mode="python", by_alias=True),
            "client_work_state": "new_unsaved",
            "primary_work": None,
        })
    targeted_fingerprint = submitted_turn_intent_fingerprint_v1(targeted_intent)
    assert targeted_fingerprint != plan_fingerprint
    assert submitted_turn_intent_fingerprint_v1(
        targeted_intent.model_copy(update={
            "playable_target": SubmittedPlanPlayableTargetV1(
                schema="dmb_plan_playable_target_v1", kind="scene", id="scene:departure"
            )
        })
    ) != targeted_fingerprint
    assert submitted_turn_intent_fingerprint_v1(
        targeted_intent.model_copy(update={
            "playable_target": SubmittedPlanPlayableTargetV1(
                schema="dmb_plan_playable_target_v1", kind="beat", id="beat:arrival"
            )
        })
    ) != targeted_fingerprint
    graph_intent = intent.model_copy(
        update={
            "graph_request": SubmittedGraphRequestIntentV1(
                mode="world",
                world_id="intent-world",
                revision_pin="graph-revision-8",
                focus=SubmittedGraphFocusIntentV1(kind="none"),
            )
        }
    )
    graph_fingerprint = submitted_turn_intent_fingerprint_v1(graph_intent)
    assert submitted_turn_intent_fingerprint_v1(
        graph_intent.model_copy(
            update={
                "graph_request": graph_intent.graph_request.model_copy(
                    update={"revision_pin": "graph-revision-9"}
                )
            }
        )
    ) != graph_fingerprint


def test_submitted_turn_intent_rejects_incomplete_plan_or_mismatched_graph_scope() -> None:
    with pytest.raises(ValidationError, match="exact committed content pin"):
        SubmittedTurnIntentV1(
            world_id="intent-world",
            client_thread_id="client-thread-1",
            message="Question?",
            surface_id="plan",
            surface_instance_id="plan-main",
            client_work_state="saved_clean",
            primary_work=SubmittedPrimaryWorkIntentV1(
                kind="plan", object_id="plan-1", expected_revision=2
            ),
            graph_request=SubmittedGraphRequestIntentV1(mode="none"),
            graph_selection=None,
        )
    with pytest.raises(ValidationError, match="must match submitted turn World"):
        SubmittedTurnIntentV1.model_validate(
            {
                **_submitted_intent("intent-world", "Question?").model_dump(
                    by_alias=True
                ),
                "graph_request": SubmittedGraphRequestIntentV1(
                    mode="world",
                    world_id="another-world",
                    focus=SubmittedGraphFocusIntentV1(kind="none"),
                ),
            }
        )
    with pytest.raises(ValidationError, match="requires a graph request"):
        SubmittedTurnIntentV1(
            world_id="intent-world",
            client_thread_id="client-thread-1",
            message="Question?",
            surface_id="play",
            surface_instance_id="play-main",
            client_work_state="none",
            primary_work=None,
            graph_request=SubmittedGraphRequestIntentV1(mode="none"),
            graph_selection=SubmittedGraphSelectionIntentV1(node_id="node-1"),
        )


def test_turn_receipt_reconciliation_survives_pointer_rotation_and_fails_closed(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    first = _new(service, "receipt-first-world", expected_revision=0)
    intent = _submitted_intent("receipt-first-world", "Original user question.")
    submission = TurnSubmission(
        world_id="receipt-first-world",
        conversation_id=first.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text=intent.message,
        provenance=_provenance("receipt-first-world"),
        submitted_intent_v1=intent,
    )

    assert service.reconcile_turn(
        "receipt-first-world", submission.idempotency_key, intent
    ) is None
    accepted = service.accept_turn(submission)
    next_conversation = _new(
        service,
        "receipt-first-world",
        expected_revision=first.pointer_revision,
        active_id=first.conversation_id,
    )

    replay = service.reconcile_turn(
        "receipt-first-world", submission.idempotency_key, intent
    )
    assert replay == accepted
    assert replay.conversation_id == first.conversation_id
    assert replay.conversation_id != next_conversation.conversation_id

    changed_client_thread_intent = intent.model_copy(
        update={"client_thread_id": "reloaded-browser-thread"}
    )
    assert service.reconcile_turn(
        "receipt-first-world",
        submission.idempotency_key,
        changed_client_thread_intent,
    ) == accepted

    stale_route_submission = TurnSubmission(
        world_id="receipt-first-world",
        conversation_id=next_conversation.conversation_id,
        idempotency_key=submission.idempotency_key,
        expected_conversation_revision=1,
        user_text=intent.message,
        provenance=_provenance("receipt-first-world", run_id="new-current-run"),
        submitted_intent_v1=changed_client_thread_intent,
    )
    assert service.accept_turn(stale_route_submission) == accepted

    changed_intent = intent.model_copy(update={"surface_instance_id": "other-pane"})
    with pytest.raises(ApplicationStateConflictError, match="different submitted intent"):
        service.reconcile_turn(
            "receipt-first-world", submission.idempotency_key, changed_intent
        )
    with pytest.raises(ApplicationStateConflictError, match="different submitted intent"):
        service.accept_turn(
            stale_route_submission.model_copy(update={"submitted_intent_v1": changed_intent})
        )


def test_legacy_turn_receipt_is_not_reconciled_from_resolved_provenance(
    application_state_dsn: str,
) -> None:
    import psycopg

    service = AgentConversationService()
    conversation = _new(service, "legacy-receipt-world", expected_revision=0)
    key = uuid4()
    intent = _submitted_intent(
        "legacy-receipt-world", "A historical turn without submitted intent."
    )
    legacy_submission = TurnSubmission(
        world_id="legacy-receipt-world",
        conversation_id=conversation.conversation_id,
        idempotency_key=key,
        expected_conversation_revision=1,
        user_text=intent.message,
        provenance=_provenance("legacy-receipt-world"),
        submitted_intent_v1=intent,
    )
    accepted = service.accept_turn(legacy_submission)
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        conn.execute(
            "UPDATE agent.turn SET submitted_intent_fingerprint_v1 = NULL WHERE turn_id = %s",
            (accepted.turn_id,),
        )

    with pytest.raises(ApplicationStateConflictError, match="legacy-receipt-unverifiable"):
        service.reconcile_turn("legacy-receipt-world", key, intent)
    with pytest.raises(ApplicationStateConflictError, match="legacy-receipt-unverifiable"):
        service.accept_turn(
            TurnSubmission(
                world_id="legacy-receipt-world",
                conversation_id=conversation.conversation_id,
                idempotency_key=key,
                expected_conversation_revision=2,
                user_text=intent.message,
                provenance=accepted.provenance,
                submitted_intent_v1=intent,
            )
        )
    with pytest.raises(ApplicationStateConflictError, match="legacy-receipt-unverifiable"):
        service.accept_turn(
            TurnSubmission(
                world_id="legacy-receipt-world",
                conversation_id=conversation.conversation_id,
                idempotency_key=key,
                expected_conversation_revision=2,
                user_text=intent.message,
                provenance=accepted.provenance,
            )
        )


def test_ordinary_accept_requires_submitted_intent_for_new_turns(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    conversation = _new(service, "intent-required-world", expected_revision=0)
    submission = TurnSubmission(
        world_id="intent-required-world",
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="Intent must precede ordinary acceptance.",
        provenance=_provenance("intent-required-world"),
    )

    with pytest.raises(ApplicationStateValidationError, match="submitted intent v1 is required"):
        service.accept_turn(submission)
    assert service.list_turns("intent-required-world", conversation.conversation_id) == []


def test_v1_accept_race_keeps_one_receipt_and_rejects_conflicting_intent(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()

    def race(first: TurnSubmission, second: TurnSubmission):
        barrier = Barrier(2)

        def submit(value: TurnSubmission):
            barrier.wait()
            try:
                return service.accept_turn(value)
            except ApplicationStateConflictError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(submit, (first, second)))

    same_conversation = _new(service, "same-intent-race-world", expected_revision=0)
    same_intent = _submitted_intent(
        "same-intent-race-world", "One exact racing request."
    )
    same_key = uuid4()
    same_submission = TurnSubmission(
        world_id="same-intent-race-world",
        conversation_id=same_conversation.conversation_id,
        idempotency_key=same_key,
        expected_conversation_revision=1,
        user_text=same_intent.message,
        provenance=_provenance("same-intent-race-world"),
        submitted_intent_v1=same_intent,
    )
    same_results = race(same_submission, same_submission)
    assert all(not isinstance(value, Exception) for value in same_results)
    assert same_results[0] == same_results[1]
    assert len(
        service.list_turns("same-intent-race-world", same_conversation.conversation_id)
    ) == 1

    conflict_conversation = _new(
        service, "conflicting-intent-race-world", expected_revision=0
    )
    first_intent = _submitted_intent(
        "conflicting-intent-race-world", "First racing request."
    )
    second_intent = _submitted_intent(
        "conflicting-intent-race-world", "Different racing request."
    )
    conflict_key = uuid4()
    first_submission = TurnSubmission(
        world_id="conflicting-intent-race-world",
        conversation_id=conflict_conversation.conversation_id,
        idempotency_key=conflict_key,
        expected_conversation_revision=1,
        user_text=first_intent.message,
        provenance=_provenance("conflicting-intent-race-world"),
        submitted_intent_v1=first_intent,
    )
    second_submission = first_submission.model_copy(
        update={
            "user_text": second_intent.message,
            "submitted_intent_v1": second_intent,
        }
    )
    conflict_results = race(first_submission, second_submission)
    assert sum(not isinstance(value, Exception) for value in conflict_results) == 1
    conflicts = [
        value for value in conflict_results if isinstance(value, ApplicationStateConflictError)
    ]
    assert len(conflicts) == 1
    assert "different submitted intent" in str(conflicts[0])
    assert len(
        service.list_turns(
            "conflicting-intent-race-world", conflict_conversation.conversation_id
        )
    ) == 1


def test_turn_claim_expiry_fences_old_worker_and_terminal_retries(
    application_state_dsn: str,
) -> None:
    import psycopg

    service = AgentConversationService()
    conversation = _new(service, "turn-claim-world", expected_revision=0)
    submission = TurnSubmission(
        world_id="turn-claim-world",
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="Recover this claimed turn.",
        provenance=_provenance("turn-claim-world"),
        submitted_intent_v1=_submitted_intent(
            "turn-claim-world", "Recover this claimed turn."
        ),
    )
    accepted = service.accept_turn(submission)
    first = service.claim_turn(
        "turn-claim-world",
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
        lease_seconds=60,
    )
    assert first.disposition == "claimed"
    assert first.turn.status == "running"
    assert first.turn.attempt == 1
    assert first.turn.claim_expires_at is not None

    live_retry = service.claim_turn(
        "turn-claim-world",
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=first.turn.revision,
        lease_seconds=60,
    )
    assert live_retry.disposition == "pending"
    assert live_retry.turn.revision == first.turn.revision
    assert live_retry.turn.attempt == first.turn.attempt

    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at = clock_timestamp() - interval '1 second' WHERE turn_id = %s",
            (accepted.turn_id,),
        )

    old_result = TurnResult(
        world_id="turn-claim-world",
        conversation_id=conversation.conversation_id,
        turn_id=accepted.turn_id,
        expected_revision=first.turn.revision,
        assistant_text="Same provider output.",
    )
    old_failure = TurnFailure(
        world_id="turn-claim-world",
        conversation_id=conversation.conversation_id,
        turn_id=accepted.turn_id,
        expected_revision=first.turn.revision,
        failure_code="provider_timeout",
    )
    with pytest.raises(ApplicationStateConflictError, match="claim expired"):
        service.complete_turn(old_result)
    with pytest.raises(ApplicationStateConflictError, match="claim expired"):
        service.fail_turn(old_failure)
    with pytest.raises(ApplicationStateConflictError, match="expired or fenced"):
        service.renew_turn_claim(
            "turn-claim-world",
            conversation.conversation_id,
            accepted.turn_id,
            expected_revision=first.turn.revision,
        )

    recovered_service = AgentConversationService()
    recovered = recovered_service.claim_turn(
        "turn-claim-world",
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=first.turn.revision,
        lease_seconds=60,
    )
    assert recovered.disposition == "claimed"
    assert recovered.turn.attempt == first.turn.attempt + 1
    assert recovered.turn.revision == first.turn.revision + 1

    with pytest.raises(ApplicationStateConflictError, match="revision or lifecycle"):
        recovered_service.complete_turn(old_result)
    with pytest.raises(ApplicationStateConflictError, match="revision or lifecycle"):
        recovered_service.fail_turn(old_failure)
    renewed = recovered_service.renew_turn_claim(
        "turn-claim-world",
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=recovered.turn.revision,
        lease_seconds=60,
    )
    assert renewed.revision == recovered.turn.revision + 1
    assert renewed.attempt == recovered.turn.attempt
    assert renewed.claim_expires_at > recovered.turn.claim_expires_at

    renewed_result = old_result.model_copy(update={"expected_revision": renewed.revision})
    completed = recovered_service.complete_turn(renewed_result)
    assert completed.status == "completed"
    assert completed.revision == renewed.revision + 1
    assert completed.claim_expires_at is None
    assert recovered_service.complete_turn(renewed_result) == completed
    with pytest.raises(
        ApplicationStateConflictError,
        match="different recorded result or a different claim fence",
    ):
        recovered_service.complete_turn(
            renewed_result.model_copy(update={"assistant_text": "Different output."})
        )
    completed_claim = recovered_service.claim_turn(
        "turn-claim-world",
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=completed.revision,
    )
    assert completed_claim.disposition == "completed"


def test_turn_claim_lease_bounds_are_validated_before_database_access() -> None:
    service = AgentConversationService()
    with pytest.raises(ApplicationStateValidationError, match="between 1 and"):
        service.claim_turn(
            "lease-validation-world",
            uuid4(),
            uuid4(),
            expected_revision=1,
            lease_seconds=0,
        )
    with pytest.raises(ApplicationStateValidationError, match="between 1 and"):
        service.renew_turn_claim(
            "lease-validation-world",
            uuid4(),
            uuid4(),
            expected_revision=1,
            lease_seconds=301,
        )


def test_claim_recovery_migration_preserves_completed_legacy_turn(
    application_state_dsn: str,
) -> None:
    import psycopg
    from alembic import command

    from application_state.cli import _current_and_head, alembic_config

    service = AgentConversationService()
    conversation = _new(service, "turn-claim-migration-world", expected_revision=0)
    submission = TurnSubmission(
        world_id="turn-claim-migration-world",
        conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="Preserve this pre-recovery receipt.",
        provenance=_provenance("turn-claim-migration-world"),
        submitted_intent_v1=_submitted_intent(
            "turn-claim-migration-world", "Preserve this pre-recovery receipt."
        ),
    )
    accepted = service.accept_turn(submission)
    claimed = service.claim_turn(
        "turn-claim-migration-world",
        conversation.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
    )
    completed = service.complete_turn(
        TurnResult(
            world_id="turn-claim-migration-world",
            conversation_id=conversation.conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=claimed.turn.revision,
            assistant_text="This completed result must survive migration.",
        )
    )
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        fingerprints_before = conn.execute(
            "SELECT request_fingerprint, idempotency_fingerprint FROM agent.turn WHERE turn_id = %s",
            (accepted.turn_id,),
        ).fetchone()

    command.downgrade(alembic_config(), "20261002_0012")
    command.upgrade(alembic_config(), "head")
    assert _current_and_head(application_state_dsn) == (
        "20261007_0018",
        "20261007_0018",
    )

    loaded = AgentConversationService().list_turns(
        "turn-claim-migration-world", conversation.conversation_id
    )[0]
    assert loaded.turn_id == completed.turn_id
    assert loaded.sequence == completed.sequence
    assert loaded.revision == completed.revision
    assert loaded.status == "completed"
    assert loaded.user_text == completed.user_text
    assert loaded.assistant_text == completed.assistant_text
    assert loaded.failure_code is None
    assert loaded.provenance == completed.provenance
    assert loaded.attempt == completed.attempt
    assert loaded.submitted_intent_fingerprint_v1 is None
    assert loaded.claim_expires_at is None
    assert submission.submitted_intent_v1 is not None
    with pytest.raises(ApplicationStateConflictError, match="legacy-receipt-unverifiable"):
        service.reconcile_turn(
            "turn-claim-migration-world",
            submission.idempotency_key,
            submission.submitted_intent_v1,
        )
    with pytest.raises(ApplicationStateConflictError, match="legacy-receipt-unverifiable"):
        service.accept_turn(submission)
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        assert (
            conn.execute(
                "SELECT request_fingerprint, idempotency_fingerprint FROM agent.turn WHERE turn_id = %s",
                (accepted.turn_id,),
            ).fetchone()
            == fingerprints_before
        )


def test_absent_surface_cannot_carry_instance_identity() -> None:
    with pytest.raises(ValidationError, match="surface instance identity"):
        TurnProvenance(
            world_id="world-one",
            surface_resolution="absent",
            surface_instance_id="plan-pane-1",
            primary_work=HistoricalReference(resolution="absent"),
            selected_object=HistoricalReference(resolution="absent"),
        )


def _new(
    service: AgentConversationService,
    world_id: str,
    *,
    expected_revision: int,
    active_id=None,
    command_id=None,
):
    return service.new_conversation(
        ConversationCommand(
            world_id=world_id,
            command_id=command_id or uuid4(),
            expected_pointer_revision=expected_revision,
            expected_active_conversation_id=active_id,
        )
    )


def test_world_identity_isolation_and_stable_conversation_ids(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    command_id = uuid4()
    one = _new(service, "world-one", expected_revision=0, command_id=command_id)
    two = _new(service, "world-two", expected_revision=0, command_id=command_id)

    assert one.conversation_id != two.conversation_id
    assert (
        service.get_active_conversation("world-one").conversation_id
        == one.conversation_id
    )
    assert (
        service.get_active_conversation("world-two").conversation_id
        == two.conversation_id
    )
    with pytest.raises(ApplicationStateNotFoundError):
        service.get_conversation("world-two", one.conversation_id)


def test_new_commands_use_pointer_cas_and_receipt_only_replay(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    first_command = ConversationCommand(
        world_id="new-retry-world",
        command_id=uuid4(),
        expected_pointer_revision=0,
        expected_active_conversation_id=None,
    )
    first = service.new_conversation(first_command)
    second = _new(
        service,
        "new-retry-world",
        expected_revision=first.pointer_revision,
        active_id=first.conversation_id,
    )
    assert (
        service.get_active_conversation("new-retry-world").conversation_id
        == second.conversation_id
    )

    replay = service.new_conversation(first_command)
    assert replay == first
    assert (
        service.get_active_conversation("new-retry-world").conversation_id
        == second.conversation_id
    )
    assert (
        service.get_conversation("new-retry-world", first.conversation_id).status
        == "archived"
    )

    stale_first_delivery_a = ConversationCommand(
        world_id="delayed-first-world",
        command_id=uuid4(),
        expected_pointer_revision=0,
        expected_active_conversation_id=None,
    )
    first_delivery_b = ConversationCommand(
        world_id="delayed-first-world",
        command_id=uuid4(),
        expected_pointer_revision=0,
        expected_active_conversation_id=None,
    )
    committed_b = service.new_conversation(first_delivery_b)
    with pytest.raises(
        ApplicationStateConflictError, match="active conversation changed"
    ):
        service.new_conversation(stale_first_delivery_a)
    conversations = service.list_conversations("delayed-first-world")
    assert [row.conversation_id for row in conversations] == [
        committed_b.conversation_id
    ]
    assert (
        service.get_active_conversation("delayed-first-world").conversation_id
        == committed_b.conversation_id
    )

    changed_binding = first_command.model_copy(update={"expected_pointer_revision": 1})
    with pytest.raises(ApplicationStateConflictError, match="different binding"):
        service.new_conversation(changed_binding)


def test_archive_and_reopen_retries_do_not_reapply_lifecycle_changes(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    first = _new(service, "archive-world", expected_revision=0)
    archive = ArchiveCommand(
        world_id="archive-world",
        command_id=uuid4(),
        expected_pointer_revision=first.pointer_revision,
        expected_active_conversation_id=first.conversation_id,
        conversation_id=first.conversation_id,
    )
    archived = service.archive_conversation(archive)
    assert service.get_world_pointer("archive-world").active_conversation_id is None
    service.archive_conversation(archive)
    next_conversation = _new(
        service,
        "archive-world",
        expected_revision=archived.pointer_revision,
        active_id=None,
    )
    service.archive_conversation(archive)
    assert (
        service.get_active_conversation("archive-world").conversation_id
        == next_conversation.conversation_id
    )

    reopen = ReopenCommand(
        world_id="archive-world",
        command_id=uuid4(),
        expected_pointer_revision=next_conversation.pointer_revision,
        expected_active_conversation_id=next_conversation.conversation_id,
        conversation_id=first.conversation_id,
    )
    reopened = service.reopen_conversation(reopen)
    later = _new(
        service,
        "archive-world",
        expected_revision=reopened.pointer_revision,
        active_id=first.conversation_id,
    )
    assert service.reopen_conversation(reopen) == reopened
    assert (
        service.get_active_conversation("archive-world").conversation_id
        == later.conversation_id
    )


def test_turn_idempotency_order_provenance_and_truthful_lifecycle(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    created = _new(service, "turn-world", expected_revision=0)
    submission = TurnSubmission(
        world_id="turn-world",
        conversation_id=created.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text="Where is the caravan?",
        provenance=_provenance("turn-world"),
        submitted_intent_v1=_submitted_intent("turn-world", "Where is the caravan?"),
    )
    accepted = service.accept_turn(submission)
    assert accepted.sequence == 1
    assert accepted.status == "accepted"
    assert service.accept_turn(submission) == accepted
    assert accepted.provenance.primary_work.object_id == "run-1"
    assert accepted.provenance.supporting_work[0].content_sha256 == "a" * 64
    assert accepted.provenance.supporting_work[1].kind == "beat"

    with pytest.raises(ApplicationStateConflictError, match="different submitted intent"):
        service.accept_turn(
            submission.model_copy(
                update={
                    "user_text": "Different text",
                    "submitted_intent_v1": _submitted_intent(
                        "turn-world", "Different text"
                    ),
                }
            )
        )
    running = service.begin_turn(
        "turn-world", created.conversation_id, accepted.turn_id, expected_revision=1
    )
    assert running.status == "running" and running.attempt == 1
    completed = service.complete_turn(
        TurnResult(
            world_id="turn-world",
            conversation_id=created.conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=running.revision,
            assistant_text="The caravan is east of the river.",
        )
    )
    assert completed.status == "completed"
    assert (
        service.complete_turn(
            TurnResult(
                world_id="turn-world",
                conversation_id=created.conversation_id,
                turn_id=accepted.turn_id,
                expected_revision=running.revision,
                assistant_text="The caravan is east of the river.",
            )
        )
        == completed
    )
    with pytest.raises(
        ApplicationStateConflictError, match="different recorded result"
    ):
        service.complete_turn(
            TurnResult(
                world_id="turn-world",
                conversation_id=created.conversation_id,
                turn_id=accepted.turn_id,
                expected_revision=running.revision,
                assistant_text="The caravan is west.",
            )
        )

    second = TurnSubmission(
        world_id="turn-world",
        conversation_id=created.conversation_id,
        idempotency_key=uuid4(),
        expected_conversation_revision=2,
        user_text="What did you find?",
        provenance=_provenance("turn-world"),
        submitted_intent_v1=_submitted_intent("turn-world", "What did you find?"),
    )
    accepted_second = service.accept_turn(second)
    running_second = service.begin_turn(
        "turn-world",
        created.conversation_id,
        accepted_second.turn_id,
        expected_revision=1,
    )
    failure = TurnFailure(
        world_id="turn-world",
        conversation_id=created.conversation_id,
        turn_id=accepted_second.turn_id,
        expected_revision=running_second.revision,
        failure_code="provider_timeout",
    )
    failed = service.fail_turn(failure)
    assert failed.status == "failed" and failed.assistant_text is None
    assert service.fail_turn(failure) == failed
    retried = service.begin_turn(
        "turn-world",
        created.conversation_id,
        accepted_second.turn_id,
        expected_revision=failed.revision,
    )
    assert retried.attempt == 2 and retried.status == "running"
    with pytest.raises(ApplicationStateConflictError, match="revision or lifecycle"):
        service.fail_turn(failure)


def test_concurrent_turn_writers_use_conversation_revision_cas(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    created = _new(service, "concurrent-turn-world", expected_revision=0)
    requests = [
        TurnSubmission(
            world_id="concurrent-turn-world",
            conversation_id=created.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=1,
            user_text=f"question {index}",
            provenance=_provenance("concurrent-turn-world"),
            submitted_intent_v1=_submitted_intent(
                "concurrent-turn-world", f"question {index}"
            ),
        )
        for index in range(2)
    ]

    def submit(request: TurnSubmission):
        try:
            return service.accept_turn(request)
        except ApplicationStateConflictError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(submit, requests))
    assert sum(not isinstance(value, Exception) for value in outcomes) == 1
    assert (
        sum(isinstance(value, ApplicationStateConflictError) for value in outcomes) == 1
    )
    assert (
        len(service.list_turns("concurrent-turn-world", created.conversation_id)) == 1
    )


def test_source_bound_draft_cas_submit_and_uncertain_retry(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    created = _new(service, "draft-world", expected_revision=0)
    draft_id = uuid4()
    initial = DraftSave(
        world_id="draft-world",
        conversation_id=created.conversation_id,
        draft_id=draft_id,
        expected_revision=0,
        body="Ask about the Runbook.",
        provenance=_provenance("draft-world"),
    )
    draft = service.save_draft(initial)
    assert draft.revision == 1
    assert service.save_draft(initial) == draft
    updated = service.save_draft(
        initial.model_copy(update={"expected_revision": 1, "body": "Ask about Beat 4."})
    )
    assert updated.revision == 2
    with pytest.raises(ApplicationStateConflictError, match="revision mismatch"):
        service.save_draft(initial.model_copy(update={"body": "stale overwrite"}))
    changed_source = _provenance("draft-world", run_id="run-2")
    with pytest.raises(ApplicationStateConflictError, match="source changed"):
        service.save_draft(
            DraftSave(
                world_id="draft-world",
                conversation_id=created.conversation_id,
                draft_id=draft_id,
                expected_revision=2,
                body=updated.body,
                provenance=changed_source,
            )
        )
    rebound = service.save_draft(
        DraftSave(
            world_id="draft-world",
            conversation_id=created.conversation_id,
            draft_id=draft_id,
            expected_revision=2,
            body=updated.body,
            provenance=changed_source,
            explicitly_revalidated_source=True,
        )
    )
    submit = DraftSubmit(
        world_id="draft-world",
        conversation_id=created.conversation_id,
        draft_id=draft_id,
        expected_draft_revision=rebound.revision,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        provenance=changed_source,
    )
    receipt = service.submit_draft(submit)
    assert receipt.turn.user_text == updated.body
    assert receipt.turn.sequence == 1
    assert receipt.retired_draft_revision == rebound.revision
    assert (
        service.get_draft("draft-world", created.conversation_id, draft_id).retired_at
        is not None
    )
    assert service.submit_draft(submit) == receipt
    assert len(service.list_turns("draft-world", created.conversation_id)) == 1


def test_submit_draft_rolls_back_turn_if_retirement_fails(
    application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import application_state.agent_conversation.service as service_module

    service = AgentConversationService()
    created = _new(service, "atomic-draft-world", expected_revision=0)
    draft = service.save_draft(
        DraftSave(
            world_id="atomic-draft-world",
            conversation_id=created.conversation_id,
            draft_id=uuid4(),
            expected_revision=0,
            body="atomic submission",
            provenance=_provenance("atomic-draft-world"),
        )
    )
    request = DraftSubmit(
        world_id="atomic-draft-world",
        conversation_id=created.conversation_id,
        draft_id=draft.draft_id,
        expected_draft_revision=draft.revision,
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        provenance=draft.provenance,
    )

    def fail_retirement(*args, **kwargs):
        return None

    with monkeypatch.context() as patcher:
        patcher.setattr(service_module.repo, "retire_draft", fail_retirement)
        with pytest.raises(
            ApplicationStateConflictError, match="changed during submission"
        ):
            service.submit_draft(request)
    assert service.list_turns("atomic-draft-world", created.conversation_id) == []
    retained = service.get_draft(
        "atomic-draft-world", created.conversation_id, draft.draft_id
    )
    assert retained.revision == draft.revision and retained.retired_at is None


def test_verified_legacy_import_is_bounded_exact_world_and_idempotent(
    application_state_dsn: str,
) -> None:
    service = AgentConversationService()
    legacy_turn = LegacyTurn(
        source_turn_id="legacy-turn-1",
        world_id="import-world",
        user_text="Where is the keep?",
        assistant_text="North of the river.",
        provenance=_provenance("import-world"),
    )
    request = LegacyImport(
        world_id="import-world",
        source_import_key="local:index:document-9:thread-3",
        source_thread_id="thread-3",
        expected_pointer_revision=0,
        expected_active_conversation_id=None,
        activate=True,
        turns=[legacy_turn],
    )
    imported = service.import_legacy_conversation(request)
    assert imported.imported_turn_count == 1
    assert service.import_legacy_conversation(request) == imported
    loaded = service.list_turns("import-world", imported.conversation_id)
    assert loaded[0].user_text == legacy_turn.user_text
    assert loaded[0].assistant_text == legacy_turn.assistant_text
    assert loaded[0].sequence == 1

    changed = request.model_copy(
        update={"turns": [legacy_turn.model_copy(update={"user_text": "different"})]}
    )
    with pytest.raises(ApplicationStateConflictError, match="different data"):
        service.import_legacy_conversation(changed)

    with pytest.raises(ValidationError, match="exact verified World ID"):
        LegacyImport(
            world_id="import-world",
            source_import_key="wrong-world-import",
            source_thread_id="thread-wrong",
            expected_pointer_revision=imported.pointer_revision,
            expected_active_conversation_id=imported.active_conversation_id,
            activate=False,
            turns=[legacy_turn.model_copy(update={"world_id": "other-world"})],
        )


def test_failed_import_does_not_leave_partial_conversation_or_turns(
    application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import application_state.agent_conversation.service as service_module

    service = AgentConversationService()
    request = LegacyImport(
        world_id="failed-import-world",
        source_import_key="failed-import-key",
        source_thread_id="thread-fail",
        expected_pointer_revision=0,
        expected_active_conversation_id=None,
        activate=True,
        turns=[
            LegacyTurn(
                source_turn_id="legacy-turn-1",
                world_id="failed-import-world",
                user_text="question",
                assistant_text="answer",
                provenance=_provenance("failed-import-world"),
            )
        ],
    )

    def fail_receipt(*args, **kwargs):
        raise RuntimeError("injected receipt write failure")

    with monkeypatch.context() as patcher:
        patcher.setattr(service_module.repo, "insert_import_receipt", fail_receipt)
        with pytest.raises(RuntimeError, match="receipt write"):
            service.import_legacy_conversation(request)
    assert service.get_world_pointer("failed-import-world").revision == 0
    assert service.list_conversations("failed-import-world") == []


def test_storage_boundary_requires_nonblank_world_and_fails_closed_when_db_is_down(
    application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = AgentConversationService()
    with pytest.raises(ValidationError, match="world_id is required"):
        ConversationCommand(
            world_id=" ",
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    monkeypatch.setenv(
        APPLICATION_STATE_DSN_ENV,
        "postgresql://app_state_agent_test:no-secret@127.0.0.1:55469/app_state_agent_unavailable",
    )
    with pytest.raises(
        ApplicationStateUnavailableError, match="PostgreSQL is unavailable"
    ):
        service.get_world_pointer("unavailable-world")


def _v2_graph_execution_fixture():
    from application_state.agent_conversation.types import (
        GraphExecutionAccountingV1,
        GraphExecutionPolicyV2,
        GraphSourceReadScopeV2,
        GraphSourceScopeAnchorV2,
        PlanWorldGraphExecutionV2,
        graph_execution_policy_digest_v2,
    )

    context_digest = "a" * 64
    scope = GraphSourceReadScopeV2(
        retrieval_session_id="retrieval-session-1",
        world_id="source-read-world",
        campaign_id=None,
        graph_revision="graph-revision-1",
        admitted_anchors=[
            GraphSourceScopeAnchorV2(
                anchor_id="anchor-1",
                evidence_ref_id="evidence-1",
                source_artifact_id="artifact-1",
                source_revision_id="source-revision-1",
            )
        ],
    )
    policy = GraphExecutionPolicyV2(
        policy_version="test-policy-v2",
        allowed_graph_operations=["search_assertions"],
        max_provider_attempts=2,
        max_graph_operations=2,
        max_results_per_operation=8,
        max_total_provider_input_tokens=100,
        max_total_provider_output_tokens=50,
        provider_input_accounting=GraphExecutionAccountingV1(
            kind="exact_token_count", estimator="synthetic-tokenizer"
        ),
        source_opened=False,
        source_read_scope=scope,
        max_source_read_calls=2,
        max_source_read_anchors=2,
        max_source_read_chars=24000,
        max_chars_per_source_read=12000,
    )
    policy_digest = graph_execution_policy_digest_v2(context_digest, policy)
    execution = PlanWorldGraphExecutionV2(
        schema="dmb_agent_plan_world_graph_execution_v2",
        context_receipt_sha256=context_digest,
        execution_policy_sha256=policy_digest,
        policy=policy,
        events=[],
    )
    return execution, scope, policy_digest


def _indexed_graph_completion_fixture(
    *,
    selection_policy: str = "parent_initial_retrieval_with_bounded_source_index_v1",
    include_read: bool = True,
    include_read_in_attempt: bool = True,
    cite_read: bool = True,
    read_outcome: str = "enough",
    read_truncated: bool = False,
    packet_coverage: str = "complete",
    packet_truncated: bool = False,
    read_anchor_id: str = "anchor-indexed",
    read_revision: str = "source-revision-indexed",
    graph_target: str = "assertion-1",
    graph_evidence_ref: str = "evidence-indexed",
):
    from application_state.agent_conversation.types import (
        GraphExecutionAccountingV1,
        GraphExecutionPolicyV2,
        GraphSourceReadScopeV2,
        GraphSourceScopeAnchorV2,
        PlanAskContextBasis,
        PlanContextPolicyV1,
        PlanWorldGraphAssembledInputV1,
        PlanWorldGraphAuthorityV1,
        PlanWorldGraphCitationMapV2,
        PlanWorldGraphCitationV2,
        PlanWorldGraphClaimSegmentV1,
        PlanWorldGraphCompletionV2,
        PlanWorldGraphContextReceiptV1,
        PlanWorldGraphPacketV1,
        PlanWorldGraphExecutionV2,
        ProviderAttemptAuthorizedEventV2,
        ProviderOutcomeEventV1,
        SourceReadAnchorReceiptV2,
        SourceReadAuthorizationEventV2,
        ValidatedGraphOperationEventV1,
        ValidatedSourceReadEventV2,
        plan_world_graph_context_receipt_digest,
        graph_execution_policy_digest_v2,
    )

    initial_ref = "evidence-initial"
    indexed_ref = "evidence-indexed"
    indexed_anchor = GraphSourceScopeAnchorV2(
        anchor_id="anchor-indexed",
        evidence_ref_id=indexed_ref,
        source_artifact_id="artifact-indexed",
        source_revision_id="source-revision-indexed",
    )
    packet = PlanWorldGraphPacketV1(
        packet_serializer_version="canonical-json-utf8-v1",
        selection_policy_version=selection_policy,
        evidence_sufficiency_policy_version="test-sufficiency-v1",
        retrieval_packet_sha256="a" * 64,
        candidate_assertion_ids=["assertion-1"],
        candidate_relationship_ids=[],
        candidate_evidence_ref_ids=sorted([initial_ref, indexed_ref]),
        retrieval_status="complete",
        evidence_sufficiency_status="sufficient",
        result_limit=8,
        coverage_status=packet_coverage,
        truncated=packet_truncated,
        omission_reasons=[],
    )
    assembled = PlanWorldGraphAssembledInputV1(
        assembler_version="test-assembler-v1",
        budget_policy_version="test-budget-v1",
        provider_model_name="test-model",
        provider_model_version="test-model-v1",
        tokenizer_name="test-tokenizer",
        tokenizer_version="test-tokenizer-v1",
        provider_envelope_input_tokens=10,
        output_token_reserve=10,
        context_window_limit=100,
        packet_disposition="included",
        dispatched_packet_sha256="b" * 64,
        dispatched_assertion_ids=["assertion-1"],
        dispatched_relationship_ids=[],
        dispatched_evidence_ref_ids=[initial_ref],
        source_token_accounting=[],
        included_history=[],
        assembled_input_sha256="c" * 64,
    )
    receipt_without_digest = PlanWorldGraphContextReceiptV1.model_construct(
        schema_="dmb_agent_plan_world_graph_context_receipt_v1",
        receipt_serializer_version="canonical-json-utf8-v1",
        context_receipt_sha256="0" * 64,
        plan_context_policy=PlanContextPolicyV1(policy="auto_plan_world"),
        plan_basis=PlanAskContextBasis(
            world_id="indexed-world",
            document_id="plan-main",
            object_revision=1,
            work_revision_id=uuid4(),
            revision_n=1,
            content_sha256="d" * 64,
        ),
        playable_target=None,
        graph_authority=PlanWorldGraphAuthorityV1(
            managed_world_id="indexed-world",
            native_world_id="native-indexed-world",
            binding_version=1,
            scope_mode="world",
            campaign_id=None,
            admissibility_version="test-admissibility-v1",
            graph_revision="graph-revision-1",
        ),
        graph_packet=packet,
        assembled_input=assembled,
        evidence_mode="metadata_only",
        source_opened=False,
    )
    receipt_digest = plan_world_graph_context_receipt_digest(receipt_without_digest)
    receipt = PlanWorldGraphContextReceiptV1.model_validate(
        receipt_without_digest.model_dump(mode="json", by_alias=True)
        | {"context_receipt_sha256": receipt_digest}
    )

    scope = GraphSourceReadScopeV2(
        retrieval_session_id="indexed-session",
        world_id="indexed-world",
        campaign_id=None,
        graph_revision="graph-revision-1",
        admitted_anchors=[indexed_anchor],
    )
    policy = GraphExecutionPolicyV2(
        policy_version="test-policy-v2",
        allowed_graph_operations=["search_assertions"],
        max_provider_attempts=1,
        max_graph_operations=1,
        max_results_per_operation=8,
        max_total_provider_input_tokens=100,
        max_total_provider_output_tokens=50,
        provider_input_accounting=GraphExecutionAccountingV1(
            kind="exact_token_count", estimator="synthetic-tokenizer"
        ),
        source_opened=False,
        source_read_scope=scope,
        max_source_read_calls=1,
        max_source_read_anchors=1,
        max_source_read_chars=12000,
        max_chars_per_source_read=12000,
    )
    policy_digest = graph_execution_policy_digest_v2(receipt_digest, policy)
    read_auth_id = uuid4()
    read_event_id = uuid4()
    graph_event_id = uuid4()
    attempt_id = uuid4()
    read_auth = SourceReadAuthorizationEventV2(
        event_id=read_auth_id,
        sequence=0,
        kind="source_read_authorized_v2",
        read_call_id=uuid4(),
        context_receipt_sha256=receipt_digest,
        execution_policy_sha256=policy_digest,
        retrieval_session_id=scope.retrieval_session_id,
        world_id=scope.world_id,
        campaign_id=None,
        graph_revision=scope.graph_revision,
        anchors=[indexed_anchor],
        max_chars=100,
    )
    read_event = ValidatedSourceReadEventV2(
        event_id=read_event_id,
        sequence=1,
        kind="validated_source_read_v2",
        read_call_id=read_auth.read_call_id,
        receipts=[SourceReadAnchorReceiptV2(
            source_read_id="indexed-read-1",
            anchor_id=read_anchor_id,
            evidence_ref_id=indexed_ref,
            source_artifact_id="artifact-indexed",
            source_revision_id=read_revision,
            outcome=read_outcome,
            content_sha256="e" * 64,
            line_start=1,
            line_end=2,
            returned_chars=20,
            truncated=read_truncated,
            evidence_sufficiency_status="sufficient",
        )],
    )
    graph_event = ValidatedGraphOperationEventV1(
        event_id=graph_event_id,
        sequence=2,
        kind="validated_graph_operation",
        operation_id=uuid4(),
        operation="search_assertions",
        request_arguments_sha256="f" * 64,
        graph_revision="graph-revision-1",
        result_packet_sha256="1" * 64,
        assertion_ids=[graph_target],
        relationship_ids=[],
        evidence_ref_ids=[graph_evidence_ref],
        evidence_sufficiency_status="sufficient",
        coverage_status="complete",
        truncated=False,
        source_opened=False,
    )
    attempt = ProviderAttemptAuthorizedEventV2(
        event_id=uuid4(),
        sequence=3,
        kind="provider_attempt_authorized_v2",
        provider_attempt_id=attempt_id,
        envelope_sha256="2" * 64,
        serializer_version="canonical-json-utf8-v1",
        provider="test-provider",
        model="test-model",
        api_mode="messages",
        tool_schema_sha256="3" * 64,
        input_accounting_kind="exact_token_count",
        input_estimator="synthetic-tokenizer",
        input_tokens=5,
        output_token_reserve=5,
        included_assertion_ids=["assertion-1"],
        included_relationship_ids=[],
        included_evidence_ref_ids=[],
        included_graph_event_ids=[graph_event_id],
        included_source_read_event_ids=(
            [read_event_id] if include_read and include_read_in_attempt else []
        ),
    )
    outcome = ProviderOutcomeEventV1(
        event_id=uuid4(),
        sequence=4,
        kind="provider_outcome",
        provider_attempt_id=attempt_id,
        outcome="sdk_entered",
    )
    response = ProviderOutcomeEventV1(
        event_id=uuid4(),
        sequence=5,
        kind="provider_outcome",
        provider_attempt_id=attempt_id,
        outcome="response_received",
        response_sha256="4" * 64,
    )
    execution_events = [read_auth, read_event, graph_event, attempt, outcome, response]
    if not include_read:
        execution_events.remove(read_auth)
        execution_events.remove(read_event)
        # Keep contiguous event numbering after removing the source read events.
        execution_events = [event.model_copy(update={"sequence": i}) for i, event in enumerate(execution_events)]
    execution = PlanWorldGraphExecutionV2(
        schema="dmb_agent_plan_world_graph_execution_v2",
        context_receipt_sha256=receipt_digest,
        execution_policy_sha256=policy_digest,
        policy=policy,
        events=execution_events,
    )
    claim = PlanWorldGraphClaimSegmentV1(
        kind="graph_claim",
        claim_id="claim-indexed",
        text="The indexed source supports this claim.",
        target_kind="assertion",
        target_id="assertion-1",
        graph_revision="graph-revision-1",
        evidence_ref_ids=[indexed_ref],
    )
    citation = PlanWorldGraphCitationV2(
        claim_id=claim.claim_id,
        target_kind=claim.target_kind,
        target_id=claim.target_id,
        graph_revision=claim.graph_revision,
        evidence_ref_ids=claim.evidence_ref_ids,
        source_read_ids=["indexed-read-1"] if cite_read else [],
        source_opened=cite_read,
    )
    completion = PlanWorldGraphCompletionV2(
        context_receipt_sha256=receipt_digest,
        answer_basis="committed_plan_plus_world_graph",
        answer_context_status="graph_grounded_partial",
        answer_segments=[claim],
        citation_map=PlanWorldGraphCitationMapV2(
            context_receipt_sha256=receipt_digest,
            entries=[citation],
        ),
    )
    return receipt, execution, completion, attempt_id, graph_event_id


def test_source_index_completion_requires_read_and_target_bound_graph_event() -> None:
    from application_state.agent_conversation.types import (
        GraphCompletionValidationError,
        PlanWorldGraphCitationMapV1,
        PlanWorldGraphCitationV1,
        PlanWorldGraphCompletionV1,
        validate_completion_against_receipt,
        validate_execution_completion,
    )

    receipt, execution, completion, attempt_id, graph_event_id = (
        _indexed_graph_completion_fixture()
    )
    assert validate_execution_completion(
        completion.model_copy(update={"answer_context_status": "graph_grounded"}),
        receipt,
        execution,
        attempt_id,
        {"claim-indexed": [graph_event_id]},
    ) is None
    with pytest.raises(GraphCompletionValidationError, match="lack included validated support"):
        validate_execution_completion(
            completion,
            receipt,
            execution,
            attempt_id,
            {"claim-indexed": []},
        )

    v1_completion = PlanWorldGraphCompletionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis="committed_plan_plus_world_graph",
        answer_context_status="graph_grounded",
        answer_segments=completion.answer_segments,
        citation_map=PlanWorldGraphCitationMapV1(
            context_receipt_sha256=receipt.context_receipt_sha256,
            entries=[PlanWorldGraphCitationV1(
                claim_id="claim-indexed",
                target_kind="assertion",
                target_id="assertion-1",
                graph_revision="graph-revision-1",
                evidence_ref_ids=["evidence-indexed"],
                source_opened=False,
            )],
        ),
    )
    with pytest.raises(GraphCompletionValidationError, match="producing execution envelope"):
        validate_completion_against_receipt(v1_completion, receipt)

    partial_receipt, partial_execution, partial_completion, partial_attempt, partial_graph = (
        _indexed_graph_completion_fixture(read_outcome="truncated", read_truncated=True)
    )
    assert validate_execution_completion(
        partial_completion,
        partial_receipt,
        partial_execution,
        partial_attempt,
        {"claim-indexed": [partial_graph]},
    ) is None
    with pytest.raises(GraphCompletionValidationError):
        validate_execution_completion(
            partial_completion.model_copy(update={"answer_context_status": "graph_grounded"}),
            partial_receipt,
            partial_execution,
            partial_attempt,
            {"claim-indexed": [partial_graph]},
        )

    incomplete_receipt, incomplete_execution, incomplete_completion, incomplete_attempt, incomplete_graph = (
        _indexed_graph_completion_fixture(packet_coverage="incomplete")
    )
    with pytest.raises(GraphCompletionValidationError):
        validate_execution_completion(
            incomplete_completion.model_copy(update={"answer_context_status": "graph_grounded"}),
            incomplete_receipt,
            incomplete_execution,
            incomplete_attempt,
            {"claim-indexed": [incomplete_graph]},
        )
    assert validate_execution_completion(
        incomplete_completion,
        incomplete_receipt,
        incomplete_execution,
        incomplete_attempt,
        {"claim-indexed": [incomplete_graph]},
    ) is None

    missing_read = _indexed_graph_completion_fixture(include_read=False, cite_read=False)
    with pytest.raises(GraphCompletionValidationError, match="indexed evidence requires sufficient content"):
        validate_execution_completion(
            missing_read[2], missing_read[0], missing_read[1], missing_read[3],
            {"claim-indexed": [missing_read[4]]},
        )

    nonproducing_read = _indexed_graph_completion_fixture(include_read_in_attempt=False)
    with pytest.raises(GraphCompletionValidationError, match="source-opened state"):
        validate_execution_completion(
            nonproducing_read[2], nonproducing_read[0], nonproducing_read[1], nonproducing_read[3],
            {"claim-indexed": [nonproducing_read[4]]},
        )

    wrong_target = _indexed_graph_completion_fixture(graph_target="assertion-other")
    with pytest.raises(GraphCompletionValidationError, match="does not support its claim"):
        validate_execution_completion(
            wrong_target[2], wrong_target[0], wrong_target[1], wrong_target[3],
            {"claim-indexed": [wrong_target[4]]},
        )

    wrong_ref = _indexed_graph_completion_fixture(graph_evidence_ref="evidence-other")
    with pytest.raises(GraphCompletionValidationError, match="does not support its claim"):
        validate_execution_completion(
            wrong_ref[2], wrong_ref[0], wrong_ref[1], wrong_ref[3],
            {"claim-indexed": [wrong_ref[4]]},
        )

    with pytest.raises(ValidationError, match="pins differ"):
        _indexed_graph_completion_fixture(read_anchor_id="anchor-other")
    with pytest.raises(ValidationError, match="source revision differs"):
        _indexed_graph_completion_fixture(read_revision="source-revision-other")

    unknown_policy = _indexed_graph_completion_fixture(selection_policy="future-policy-v9")
    with pytest.raises(GraphCompletionValidationError, match="does not support its claim"):
        validate_execution_completion(
            unknown_policy[2], unknown_policy[0], unknown_policy[1], unknown_policy[3],
            {"claim-indexed": [unknown_policy[4]]},
        )


def test_graph_execution_v2_source_read_scope_receipt_and_budget_are_strict() -> None:
    from application_state.agent_conversation.types import (
        PlanWorldGraphExecutionV2,
        SourceReadAnchorReceiptV2,
        SourceReadAuthorizationEventV2,
        ValidatedSourceReadEventV2,
    )

    execution, scope, policy_digest = _v2_graph_execution_fixture()
    auth = SourceReadAuthorizationEventV2(
        event_id=uuid4(), sequence=0, kind="source_read_authorized_v2",
        read_call_id=uuid4(), context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=policy_digest,
        retrieval_session_id=scope.retrieval_session_id,
        world_id=scope.world_id, campaign_id=scope.campaign_id,
        graph_revision=scope.graph_revision, anchors=scope.admitted_anchors,
        max_chars=12000,
    )
    result = ValidatedSourceReadEventV2(
        event_id=uuid4(), sequence=1, kind="validated_source_read_v2",
        read_call_id=auth.read_call_id,
        receipts=[SourceReadAnchorReceiptV2(
            source_read_id="source-read:one", anchor_id="anchor-1",
            evidence_ref_id="evidence-1", source_artifact_id="artifact-1",
            source_revision_id="source-revision-1", outcome="partial",
            content_sha256="b" * 64, line_start=2, line_end=4,
            returned_chars=17, truncated=False,
            evidence_sufficiency_status="insufficient",
        )],
    )
    stored = execution.model_copy(update={"events": [auth, result]})
    restored = PlanWorldGraphExecutionV2.model_validate(
        stored.model_dump(mode="json", by_alias=True)
    )
    assert restored == stored
    serialized_receipt = restored.model_dump(mode="json", by_alias=True)["events"][1]["receipts"][0]
    assert "content" not in serialized_receipt
    assert SourceReadAnchorReceiptV2(
        source_read_id="source-read:empty", anchor_id="anchor-1",
        evidence_ref_id="evidence-1", source_artifact_id="artifact-1",
        outcome="empty", returned_chars=0, truncated=False,
        evidence_sufficiency_status="insufficient",
    ).content_sha256 is None

    with pytest.raises(ValidationError, match="frozen source scope"):
        PlanWorldGraphExecutionV2.model_validate(
            execution.model_dump(mode="json", by_alias=True)
            | {"events": [auth.model_dump(mode="json", by_alias=True) | {"retrieval_session_id": "other-session"}]}
        )
    with pytest.raises(ValidationError, match="unadmitted or changed anchor"):
        PlanWorldGraphExecutionV2.model_validate(
            execution.model_dump(mode="json", by_alias=True)
            | {"events": [auth.model_dump(mode="json", by_alias=True) | {"anchors": [scope.admitted_anchors[0].model_dump(mode="json") | {"source_revision_id": "other-revision"}]}]}
        )
    with pytest.raises(ValidationError, match="frozen source scope"):
        PlanWorldGraphExecutionV2.model_validate(
            execution.model_dump(mode="json", by_alias=True)
            | {"events": [auth.model_dump(mode="json", by_alias=True) | {"graph_revision": "other-graph-revision"}]}
        )
    with pytest.raises(ValidationError, match="unadmitted or changed anchor"):
        PlanWorldGraphExecutionV2.model_validate(
            execution.model_dump(mode="json", by_alias=True)
            | {"events": [auth.model_dump(mode="json", by_alias=True) | {"anchors": [scope.admitted_anchors[0].model_dump(mode="json") | {"anchor_id": "not-admitted"}]}]}
        )
    with pytest.raises(ValidationError):
        PlanWorldGraphExecutionV2.model_validate(
            execution.model_dump(mode="json", by_alias=True)
            | {"events": [auth.model_dump(mode="json", by_alias=True) | {"max_chars": 12001}]}
        )
    with pytest.raises(ValidationError, match="trusted source revision"):
        SourceReadAnchorReceiptV2(
            source_read_id="source-read:missing-revision", anchor_id="anchor-1",
            evidence_ref_id="evidence-1", source_artifact_id="artifact-1",
            outcome="enough", content_sha256="c" * 64,
            line_start=1, line_end=1, returned_chars=1, truncated=False,
            evidence_sufficiency_status="sufficient",
        )


def test_graph_execution_v2_source_opened_requires_included_successful_read() -> None:
    from application_state.agent_conversation.types import (
        PlanWorldGraphCitationMapV2,
        PlanWorldGraphCitationV2,
        PlanWorldGraphClaimSegmentV1,
        PlanWorldGraphCompletionV2,
        PlanWorldGraphExecutionV2,
        ProviderAttemptAuthorizedEventV2,
        SourceReadAnchorReceiptV2,
        SourceReadAuthorizationEventV2,
        ValidatedSourceReadEventV2,
        _validate_v2_completion_source_reads,
    )

    execution, scope, policy_digest = _v2_graph_execution_fixture()
    auth = SourceReadAuthorizationEventV2(
        event_id=uuid4(), sequence=0, kind="source_read_authorized_v2",
        read_call_id=uuid4(), context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=policy_digest,
        retrieval_session_id=scope.retrieval_session_id, world_id=scope.world_id,
        campaign_id=None, graph_revision=scope.graph_revision,
        anchors=scope.admitted_anchors, max_chars=12000,
    )
    read_event = ValidatedSourceReadEventV2(
        event_id=uuid4(), sequence=1, kind="validated_source_read_v2",
        read_call_id=auth.read_call_id,
        receipts=[SourceReadAnchorReceiptV2(
            source_read_id="source-read:opened", anchor_id="anchor-1",
            evidence_ref_id="evidence-1", source_artifact_id="artifact-1",
            source_revision_id="source-revision-1", outcome="partial",
            content_sha256="d" * 64, line_start=1, line_end=2,
            returned_chars=20, truncated=True,
            evidence_sufficiency_status="insufficient",
        )],
    )
    attempt = ProviderAttemptAuthorizedEventV2(
        event_id=uuid4(), sequence=2, kind="provider_attempt_authorized_v2",
        provider_attempt_id=uuid4(), envelope_sha256="e" * 64,
        serializer_version="canonical-json-utf8-v1", provider="test-provider",
        model="test-model", api_mode="messages", tool_schema_sha256="f" * 64,
        input_accounting_kind="exact_token_count", input_estimator="synthetic-tokenizer",
        input_tokens=5, output_token_reserve=5, included_assertion_ids=[],
        included_relationship_ids=[], included_evidence_ref_ids=[],
        included_graph_event_ids=[], included_source_read_event_ids=[read_event.event_id],
    )
    stored = execution.model_copy(update={"events": [auth, read_event, attempt]})
    stored = PlanWorldGraphExecutionV2.model_validate(stored.model_dump(mode="json", by_alias=True))
    citation = PlanWorldGraphCitationV2(
        claim_id="claim-1", target_kind="assertion", target_id="assertion-1",
        graph_revision=scope.graph_revision, evidence_ref_ids=["evidence-1"],
        source_read_ids=["source-read:opened"], source_opened=True,
    )
    completion = PlanWorldGraphCompletionV2(
        context_receipt_sha256=execution.context_receipt_sha256,
        answer_basis="committed_plan_plus_world_graph",
        answer_context_status="graph_grounded_partial",
        answer_segments=[PlanWorldGraphClaimSegmentV1(
            kind="graph_claim", claim_id="claim-1", text="A supported claim.",
            target_kind="assertion", target_id="assertion-1",
            graph_revision=scope.graph_revision, evidence_ref_ids=["evidence-1"],
        )],
        citation_map=PlanWorldGraphCitationMapV2(
            context_receipt_sha256=execution.context_receipt_sha256, entries=[citation]
        ),
    )
    _validate_v2_completion_source_reads(completion, stored, attempt.provider_attempt_id)

    failed_read_event = ValidatedSourceReadEventV2(
        event_id=uuid4(), sequence=1, kind="validated_source_read_v2",
        read_call_id=auth.read_call_id, receipts=[SourceReadAnchorReceiptV2(
            source_read_id="source-read:empty", anchor_id="anchor-1",
            evidence_ref_id="evidence-1", source_artifact_id="artifact-1",
            outcome="empty", returned_chars=0, truncated=False,
            evidence_sufficiency_status="insufficient",
        )],
    )
    failed_attempt = attempt.model_copy(
        update={"sequence": 2, "included_source_read_event_ids": [failed_read_event.event_id]}
    )
    failed_execution = PlanWorldGraphExecutionV2.model_validate(
        execution.model_dump(mode="json", by_alias=True)
        | {"events": [
            auth.model_dump(mode="json", by_alias=True),
            failed_read_event.model_dump(mode="json", by_alias=True),
            failed_attempt.model_dump(mode="json", by_alias=True),
        ]}
    )
    closed_citation = PlanWorldGraphCitationV2(
        claim_id="claim-1", target_kind="assertion", target_id="assertion-1",
        graph_revision=scope.graph_revision, evidence_ref_ids=["evidence-1"],
        source_read_ids=[], source_opened=False,
    )
    closed_completion = PlanWorldGraphCompletionV2.model_validate(
        completion.model_dump(mode="json", by_alias=True)
        | {"citation_map": {
            "schema": "dmb_graph_citation_map_v2",
            "context_receipt_sha256": execution.context_receipt_sha256,
            "entries": [closed_citation.model_dump(mode="json", by_alias=True)],
        }}
    )
    _validate_v2_completion_source_reads(
        closed_completion, failed_execution, failed_attempt.provider_attempt_id
    )
    failed_citation = closed_citation.model_copy(
        update={"source_read_ids": ["source-read:empty"], "source_opened": True}
    )
    opened_failed_completion = PlanWorldGraphCompletionV2.model_validate(
        completion.model_dump(mode="json", by_alias=True)
        | {"citation_map": {
            "schema": "dmb_graph_citation_map_v2",
            "context_receipt_sha256": execution.context_receipt_sha256,
            "entries": [failed_citation.model_dump(mode="json", by_alias=True)],
        }}
    )
    with pytest.raises(ValueError, match="validated content"):
        _validate_v2_completion_source_reads(
            opened_failed_completion, failed_execution, failed_attempt.provider_attempt_id
        )
    with pytest.raises(ValidationError, match="derived from source read IDs"):
        PlanWorldGraphCitationV2(
            claim_id="claim-1", target_kind="assertion", target_id="assertion-1",
            graph_revision=scope.graph_revision, evidence_ref_ids=["evidence-1"],
            source_read_ids=[], source_opened=True,
        )


def test_graph_execution_v2_enforces_each_aggregate_source_budget() -> None:
    from application_state.agent_conversation.types import (
        GraphExecutionPolicyV2,
        PlanWorldGraphExecutionV2,
        SourceReadAuthorizationEventV2,
        graph_execution_policy_digest_v2,
    )

    base, scope, _ = _v2_graph_execution_fixture()
    base_policy = base.policy.model_dump(mode="json", by_alias=True)

    def make_auth(sequence: int, call_id):
        return SourceReadAuthorizationEventV2(
            event_id=uuid4(), sequence=sequence, kind="source_read_authorized_v2",
            read_call_id=call_id, context_receipt_sha256=base.context_receipt_sha256,
            execution_policy_sha256="0" * 64,
            retrieval_session_id=scope.retrieval_session_id, world_id=scope.world_id,
            campaign_id=None, graph_revision=scope.graph_revision,
            anchors=scope.admitted_anchors, max_chars=12000,
        )

    def execution_with(policy_fields, auths):
        policy = GraphExecutionPolicyV2.model_validate(base_policy | policy_fields)
        policy_digest = graph_execution_policy_digest_v2(base.context_receipt_sha256, policy)
        events = [
            auth.model_copy(update={"execution_policy_sha256": policy_digest})
            for auth in auths
        ]
        return PlanWorldGraphExecutionV2.model_validate({
            "schema": "dmb_agent_plan_world_graph_execution_v2",
            "context_receipt_sha256": base.context_receipt_sha256,
            "execution_policy_sha256": policy_digest,
            "policy": policy.model_dump(mode="json", by_alias=True),
            "events": [event.model_dump(mode="json", by_alias=True) for event in events],
        })

    with pytest.raises(ValidationError, match="call budget exceeded"):
        execution_with(
            {"max_source_read_calls": 1},
            [make_auth(0, uuid4()), make_auth(1, uuid4())],
        )
    with pytest.raises(ValidationError, match="anchor budget exceeded"):
        execution_with(
            {"max_source_read_anchors": 1},
            [make_auth(0, uuid4()), make_auth(1, uuid4())],
        )
    with pytest.raises(ValidationError, match="character budget exceeded"):
        execution_with(
            {"max_source_read_chars": 10000},
            [make_auth(0, uuid4())],
        )


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("corruption", [None, "missing", "nonproducing", "wrong_target", "wrong_ref", "excluded_ref"])
def test_historical_graph_operation_evidence_outside_initial_dispatch(
    version: int, corruption: str | None,
) -> None:
    from application_state.agent_conversation.types import (
        PlanWorldGraphCompletionV1, PlanWorldGraphExecutionV1, PlanWorldGraphExecutionV2,
        GraphCompletionValidationError, validate_execution_completion,
    )
    receipt, execution, completion, attempt_id, graph_event_id = _indexed_graph_completion_fixture(
        selection_policy="historical-graph-metadata-v1", include_read=False, cite_read=False,
        graph_target="assertion-other" if corruption == "wrong_target" else "assertion-1",
        graph_evidence_ref="evidence-other" if corruption == "wrong_ref" else "evidence-indexed",
    )
    payload = execution.model_dump(mode="json", by_alias=True)
    attempt = next(event for event in payload["events"] if event["kind"] == "provider_attempt_authorized_v2")
    attempt["included_evidence_ref_ids"] = [] if corruption == "excluded_ref" else ["evidence-indexed"]
    if corruption == "nonproducing":
        attempt["included_graph_event_ids"] = []
    if version == 1:
        payload["schema"] = "dmb_agent_plan_world_graph_execution_v1"
        for field in ["source_read_scope", "max_source_read_calls", "max_source_read_anchors", "max_source_read_chars", "max_chars_per_source_read"]:
            payload["policy"].pop(field)
        attempt["kind"] = "provider_attempt_authorized"
        attempt.pop("included_source_read_event_ids")
        payload.pop("execution_policy_sha256")
        execution = PlanWorldGraphExecutionV1.model_validate(payload)
        completion_payload = completion.model_dump(mode="json", by_alias=True)
        completion_payload["schema"] = "dmb_plan_world_graph_completion_v1"
        completion_payload["citation_map"]["schema"] = "dmb_graph_citation_map_v1"
        completion_payload["citation_map"]["entries"][0].pop("source_read_ids")
        completion = PlanWorldGraphCompletionV1.model_validate(completion_payload)
    else:
        execution = PlanWorldGraphExecutionV2.model_validate(payload)
    completion = completion.model_copy(update={"answer_context_status": "graph_grounded"})
    mapping = {"claim-indexed": [] if corruption == "missing" else [graph_event_id]}
    assert "evidence-indexed" not in receipt.assembled_input.dispatched_evidence_ref_ids
    assert completion.citation_map.entries[0].source_opened is False
    if corruption is None:
        assert validate_execution_completion(completion, receipt, execution, attempt_id, mapping) is None
    else:
        with pytest.raises(GraphCompletionValidationError):
            validate_execution_completion(completion, receipt, execution, attempt_id, mapping)


def test_reset_fingerprint_full_canonical_unicode_vector():
    from application_state.agent_conversation.types import request_fingerprint
    command = ConversationCommand(world_id="wörld😀", command_id=uuid4(), expected_pointer_revision=0, expected_active_conversation_id=None)
    encoded = json.dumps({"world_id": "wörld😀", "expected_pointer_revision": 0, "expected_active_conversation_id": None}, sort_keys=True, separators=(",", ":"))
    assert request_fingerprint(command) == hashlib.sha256(encoded.encode()).hexdigest()
    assert request_fingerprint(command.model_copy(update={"command_id": uuid4()})) == request_fingerprint(command)
    assert request_fingerprint(command.model_copy(update={"expected_pointer_revision": 1})) != request_fingerprint(command)
