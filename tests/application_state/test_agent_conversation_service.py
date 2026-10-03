from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
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
    assert submitted_turn_intent_fingerprint_v1(
        plan_intent.model_copy(
            update={
                "primary_work": plan_intent.primary_work.model_copy(
                    update={"expected_revision_n": 4}
                )
            }
        )
    ) != plan_fingerprint
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
        "20261003_0014",
        "20261003_0014",
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
