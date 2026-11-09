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
    with pytest.raises(ValueError, match="Retained native completion differs from its actual producing owner"):
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


@pytest.mark.parametrize('surface', ['build', 'plan', 'play'])
@pytest.mark.parametrize('entry', ['constructor', 'instance', 'copy', 'json', 'mapping'])
def test_native_turn_construction_owns_fresh_components(surface, entry):
    original = retained(submission(surface))
    before = original.model_dump(mode='json', by_alias=True)
    if entry == 'constructor':
        restored = t.Turn(**{name: getattr(original, name) for name in t.Turn.model_fields})
    elif entry == 'mapping':
        from collections import UserDict
        restored = t.Turn.model_validate(UserDict({name: getattr(original, name) for name in t.Turn.model_fields}))
    elif entry == 'instance':
        restored = t.Turn.model_validate(original)
    elif entry == 'copy':
        restored = t.Turn.model_validate(original.model_copy())
    else:
        restored = t.Turn.model_validate_json(original.model_dump_json(by_alias=True))
    assert restored.model_dump(mode='json', by_alias=True) == before
    assert restored is not original
    assert restored.graph_context_receipt is not original.graph_context_receipt
    assert restored.graph_context_execution is not original.graph_context_execution
    assert restored.provenance is not original.provenance
    assert restored.graph_context_execution.policy is not original.graph_context_execution.policy


@pytest.mark.parametrize('surface', ['build', 'plan', 'play'])
@pytest.mark.parametrize('entry', ['constructor', 'instance', 'copy'])
@pytest.mark.parametrize('change', ['provenance', 'execution', 'context', 'context_family', 'execution_family'])
def test_native_turn_reconstruction_refuses_mutated_components(surface, entry, change):
    original = retained(submission(surface))
    if change == 'provenance':
        original.provenance.world_id = 'foreign'
    elif change == 'execution':
        object.__setattr__(original.graph_context_execution.policy, 'source_authority_sha256', '0' * 64)
    elif change == 'context':
        object.__setattr__(original.graph_context_receipt, 'provenance_sha256', '0' * 64)
    elif change == 'context_family':
        object.__setattr__(original.graph_context_receipt, 'schema_', 'dmb_plan_source_context_receipt_v1')
    else:
        object.__setattr__(original.graph_context_execution, 'schema_', 'dmb_plan_source_execution_v1')
    with pytest.raises(ValidationError):
        if entry == 'constructor':
            t.Turn(**{name: getattr(original, name) for name in t.Turn.model_fields})
        else:
            t.Turn.model_validate(original if entry == 'instance' else original.model_copy())


@pytest.mark.parametrize('surface', ['build', 'plan', 'play'])
@pytest.mark.parametrize('alias', ['schema', 'schema_'])
@pytest.mark.parametrize('corrupt', [False, True])
def test_native_turn_mapping_discriminators_reconstruct_nested_models(surface, alias, corrupt):
    from collections import UserDict
    original = retained(submission(surface))
    values = {name: getattr(original, name) for name in t.Turn.model_fields}
    for slot in ('graph_context_receipt', 'graph_context_execution'):
        component = values[slot]
        mapping = {name: getattr(component, name) for name in type(component).model_fields}
        mapping[alias] = mapping.pop('schema_')
        values[slot] = UserDict(mapping)
    if corrupt:
        object.__setattr__(original.graph_context_execution.policy, 'source_authority_sha256', '0' * 64)
        with pytest.raises(ValidationError):
            t.Turn.model_validate(UserDict(values))
    else:
        fresh = t.Turn.model_validate(UserDict(values))
        assert fresh.model_dump(mode='json', by_alias=True) == original.model_dump(mode='json', by_alias=True)
        assert fresh.graph_context_receipt.work_context is not original.graph_context_receipt.work_context
        assert fresh.graph_context_execution.policy is not original.graph_context_execution.policy


@pytest.mark.parametrize('surface', ['build', 'plan', 'play'])
@pytest.mark.parametrize('change', ['provenance', 'fingerprint'])
def test_standalone_turn_fields_keeps_request_commitment_checks(surface, change):
    from application_state.agent_conversation.native_execution import validate_turn_fields
    turn = retained(submission(surface))
    provenance = turn.provenance
    fingerprint = turn.submitted_intent_fingerprint_v2
    if change == 'provenance':
        provenance = provenance.model_copy(update={'surface_instance_id': 'foreign'})
    else:
        fingerprint = '0' * 64
    with pytest.raises(ValueError, match='request or provenance'):
        validate_turn_fields(turn.graph_context_receipt, turn.graph_context_execution,
                             provenance, fingerprint, None, None)


@pytest.mark.parametrize('surface', ['build', 'plan', 'play'])
def test_native_turn_json_keeps_nested_adapter_and_schema_references(surface):
    from pydantic import BaseModel, TypeAdapter

    class Pair(BaseModel):
        left: t.Turn
        right: t.Turn

    turn = retained(submission(surface))
    wire = turn.model_dump(mode='json', by_alias=True)
    pair = Pair.model_validate_json(json.dumps({'left': wire, 'right': wire}))
    assert pair.left == turn == pair.right
    assert TypeAdapter(list[t.Turn]).validate_json(json.dumps([wire])) == [turn]
    import warnings
    from pydantic.json_schema import PydanticJsonSchemaWarning

    for mode in ('validation', 'serialization'):
        with warnings.catch_warnings():
            warnings.simplefilter('error', PydanticJsonSchemaWarning)
            schema = Pair.model_json_schema(mode=mode)

        def resolve(value):
            return schema['$defs'][value['$ref'].rsplit('/', 1)[1]] if '$ref' in value else value

        left = resolve(schema['properties']['left'])
        assert left == resolve(schema['properties']['right'])
        for field in ('graph_context_receipt', 'graph_context_execution'):
            assert 'discriminator' in left['properties'][field]['anyOf'][0]
    python_pair = Pair.model_validate({'left': turn, 'right': turn})
    assert python_pair.left is not turn and python_pair.right is not turn
    assert python_pair.left.graph_context_receipt is not turn.graph_context_receipt
    assert python_pair.right.graph_context_execution is not turn.graph_context_execution
    python_list = TypeAdapter(list[t.Turn]).validate_python([turn])
    assert python_list[0] is not turn
