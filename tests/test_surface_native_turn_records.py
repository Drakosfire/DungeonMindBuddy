"""Actual shared Turn envelopes, without fake historical Graph authority."""

from datetime import UTC, datetime
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import types as t
from tests.test_surface_native_context import provenance_for
from tests.test_surface_native_execution import component, execution, controller


def submission(surface="build"):
    context, record = component(surface, unavailable=True)
    intent = record.policy.action.intent
    provenance = provenance_for(context.work_context).model_copy(
        update={"surface_instance_id": intent.surface_instance_id}
    )
    return t.TurnSubmission(
        world_id=intent.world_id,
        conversation_id=uuid4(),
        idempotency_key=uuid4(),
        expected_conversation_revision=1,
        user_text=intent.message,
        provenance=provenance,
        submitted_intent_v2=intent,
        graph_context_receipt=context,
        graph_context_execution=record,
        play_context_receipt=context.work_context.play_basis
        if surface == "play"
        else None,
    )


def retained(sub=None, **updates):
    sub = sub or submission()
    now = datetime.now(UTC)
    values = dict(
        turn_id=uuid4(),
        conversation_id=sub.conversation_id,
        world_id=sub.world_id,
        idempotency_key=sub.idempotency_key,
        sequence=1,
        revision=1,
        status="accepted",
        user_text=sub.user_text,
        assistant_text=None,
        failure_code=None,
        provenance=sub.provenance,
        submitted_intent_fingerprint_v1=None,
        submitted_intent_fingerprint_v2=t.submitted_turn_intent_fingerprint_v2(
            sub.submitted_intent_v2
        ),
        graph_context_receipt=sub.graph_context_receipt,
        graph_context_execution=sub.graph_context_execution,
        play_context_receipt=sub.play_context_receipt,
        completion=None,
        attempt=0,
        claim_expires_at=None,
        accepted_at=now,
        completed_at=None,
        updated_at=now,
    )
    return t.Turn(**(values | updates))


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_shared_submission_and_real_envelope_roundtrip(surface):
    sub = submission(surface)
    assert (
        t.TurnSubmission.model_validate_json(sub.model_dump_json(by_alias=True)) == sub
    )
    turn = retained(sub)
    assert t.Turn.model_validate_json(turn.model_dump_json(by_alias=True)) == turn
    assert turn.graph_context_execution.policy.action.intent == sub.submitted_intent_v2
    assert not hasattr(turn.graph_context_receipt, "graph_authority")


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
@pytest.mark.parametrize(
    "change",
    [
        "message",
        "intent",
        "surface_instance",
        "provenance",
        "execution",
        "receipt",
        "initial_event",
        "run",
    ],
)
def test_submission_rejects_crossed_native_records(surface, change):
    sub = submission(surface)
    data = sub.model_dump(mode="json", by_alias=True)
    if change == "message":
        data["user_text"] = "A different question"
    elif change == "intent":
        data["submitted_intent_v2"]["client_thread_id"] = "different"
    elif change == "surface_instance":
        data["provenance"]["surface_instance_id"] = "different"
    elif change == "provenance":
        data["provenance"]["world_id"] = "foreign"
    elif change == "execution":
        data["graph_context_execution"] = None
    elif change == "receipt":
        data["graph_context_receipt"] = None
    elif change == "initial_event":
        e = sub.graph_context_execution
        data["graph_context_execution"] = execution(
            e.context_receipt_sha256, e.policy, [controller(surface, e.policy)]
        ).model_dump(mode="json", by_alias=True)
    else:
        data["play_context_receipt"] = (
            None
            if surface == "play"
            else submission("play").play_context_receipt.model_dump(
                mode="json", by_alias=True
            )
        )
    with pytest.raises(ValidationError):
        t.TurnSubmission.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
@pytest.mark.parametrize(
    "change",
    [
        "world_id",
        "user_text",
        "submitted_intent_fingerprint_v2",
        "provenance",
        "play_context_receipt",
        "status",
    ],
)
def test_retained_native_envelope_keeps_actual_request_identity(surface, change):
    sub = submission(surface)
    replacement = {
        "world_id": "foreign",
        "user_text": "Changed",
        "submitted_intent_fingerprint_v2": "e" * 64,
        "provenance": sub.provenance.model_copy(
            update={"surface_instance_id": "different"}
        ),
        "play_context_receipt": None
        if surface == "play"
        else submission("play").play_context_receipt,
        "status": "completed",
    }[change]
    with pytest.raises(ValidationError):
        retained(sub, **{change: replacement})


def test_shared_records_cannot_accept_legacy_completion_without_actual_producer():
    sub = submission()
    # Cross-family typed status must never fall through legacy Graph validation.
    with pytest.raises(ValueError, match="locked producing-output owner"):
        t.validate_execution_completion(
            None, sub.graph_context_receipt, sub.graph_context_execution, uuid4(), {}
        )


def test_fresh_import_builds_public_turn_schemas():
    import subprocess
    import sys

    code = "from application_state.agent_conversation.types import TurnSubmission,Turn,TurnResult,TurnClaimReceipt,CompletedPlanAskPair; [x.model_json_schema() for x in (TurnSubmission,Turn,TurnResult,TurnClaimReceipt,CompletedPlanAskPair)]"
    subprocess.run(
        [sys.executable, "-B", "-c", code], check=True, capture_output=True, text=True
    )


@pytest.mark.parametrize(
    "change", ["message", "intent", "initial_events", "context_digest", "dictionary"]
)
def test_service_reparses_copied_native_submission_before_database_or_replay(
    monkeypatch, change
):
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation import service
    from application_state.errors import ApplicationStateValidationError

    sub = submission()
    if change == "message":
        sub = sub.model_copy(update={"user_text": "changed"})
    elif change == "intent":
        sub = sub.model_copy(
            update={
                "submitted_intent_v2": sub.submitted_intent_v2.model_copy(
                    update={"message": "changed"}
                )
            }
        )
    elif change == "initial_events":
        record = sub.graph_context_execution
        sub = sub.model_copy(
            update={
                "graph_context_execution": record.model_copy(
                    update={"events": [controller("build", record.policy)]}
                )
            }
        )
    elif change == "dictionary":
        data = sub.graph_context_receipt.model_dump(mode="json", by_alias=True)
        data["context_receipt_sha256"] = "f" * 64
        sub = sub.model_copy(update={"graph_context_receipt": data})
    else:
        sub = sub.model_copy(
            update={
                "graph_context_receipt": sub.graph_context_receipt.model_copy(
                    update={"context_receipt_sha256": "f" * 64}
                )
            }
        )
    monkeypatch.setattr(
        service,
        "_ready_dsn",
        lambda: pytest.fail("Invalid native submission reached the database"),
    )
    with pytest.raises(ApplicationStateValidationError):
        AgentConversationService().accept_turn(sub)


def test_http_unclaimed_model_resolves_registered_shared_receipt():
    from apps.live_control_server.models.agent_turn import AgentRulesUnclaimedContextV1
    assert AgentRulesUnclaimedContextV1.__pydantic_complete__
    assert 'SurfaceNativeContextReceiptV1' in AgentRulesUnclaimedContextV1.model_json_schema()['$defs']
