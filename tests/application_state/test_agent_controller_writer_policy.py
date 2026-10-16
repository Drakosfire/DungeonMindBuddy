"""Durable role/phase enforcement; synthetic fixtures and disposable APP only."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from tests.application_state.test_build_graph_turns import _submission, _completion
from tests.application_state.test_agent_conversation_postgres import _new, _provider_authorization_event


ROLES = {
    "controller": {"provider": "typesafe", "model": "jev-1.14.0", "api_mode": "typesafe_decision"},
    "writer": {"provider": "openai-api", "model": "gpt-6-luna", "api_mode": "codex_responses"},
}


def _fixture(conversation_id=None):
    submission = _submission(conversation_id)
    original = submission.graph_context_execution
    data = original.policy.model_dump(mode="json", by_alias=True)
    for field in ("max_source_read_calls", "max_source_read_anchors"):
        data.pop(field)
    data.update(source_read_accounting="settled_receipts_v1", provider_roles=ROLES,
        policy_version="world_graph_execution_uncapped_v1", max_provider_attempts=None,
        max_graph_operations=None, max_total_provider_input_tokens=None, max_total_provider_output_tokens=None)
    policy = t.ControllerWriterGraphExecutionPolicyV3.model_validate(data)
    execution = t.PlanWorldGraphExecutionV3(
        context_receipt_sha256=original.context_receipt_sha256,
        execution_policy_sha256=t.graph_execution_policy_digest_v3(original.context_receipt_sha256, policy),
        policy=policy, events=[],
    )
    return t.TurnSubmission.model_validate(submission.model_dump(mode="python", by_alias=True) | {"graph_context_execution": execution})


def _auth(role, sequence, **changes):
    event = _provider_authorization_event(attempt_id=uuid4(), sequence=sequence)
    return t.ProviderAttemptAuthorizedEventV3.model_validate(event.model_dump(mode="python") | {
        "kind": "provider_attempt_authorized_v3", "included_source_read_event_ids": [],
        **ROLES[role], **changes,
    })


def _outcome(event, sequence, outcome):
    return t.ProviderOutcomeEventV1(event_id=uuid4(), sequence=sequence,
        kind="provider_outcome", provider_attempt_id=event.provider_attempt_id, outcome=outcome)


def _complete(event, sequence):
    return t.CompletionBindingEventV1(event_id=uuid4(), sequence=sequence,
        kind="completion_binding", provider_attempt_id=event.provider_attempt_id,
        completion_sha256="a" * 64, claim_graph_event_ids={})


def _validate(events):
    execution = _fixture().graph_context_execution
    return t.PlanWorldGraphExecutionV3.model_validate(execution.model_dump(mode="python", by_alias=True) | {"events": events})


def _resolved_controller():
    controller = _auth("controller", 0)
    return controller, [controller, _outcome(controller, 1, "sdk_entered"), _outcome(controller, 2, "response_received")]


def test_new_policy_roundtrip_digest_and_historical_policy_bytes():
    original = _submission().graph_context_execution
    old_bytes = original.model_dump_json(by_alias=True)
    assert type(t.PlanWorldGraphExecutionV2.model_validate_json(old_bytes).policy) is t.GraphExecutionPolicyV2
    assert t.PlanWorldGraphExecutionV2.model_validate_json(old_bytes).model_dump_json(by_alias=True) == old_bytes
    from tests.application_state.test_agent_conversation_service import _source_admission_v3_fixture
    _, historical_v3, _, _ = _source_admission_v3_fixture()
    old_v3_bytes = historical_v3.model_dump_json(by_alias=True)
    assert t.PlanWorldGraphExecutionV3.model_validate_json(old_v3_bytes).model_dump_json(by_alias=True) == old_v3_bytes
    assert type(t.PlanWorldGraphExecutionV3.model_validate_json(old_v3_bytes).policy) is t.GraphExecutionPolicyV3
    execution = _fixture().graph_context_execution
    reloaded = t.PlanWorldGraphExecutionV3.model_validate_json(execution.model_dump_json(by_alias=True))
    assert isinstance(reloaded.policy, t.ControllerWriterGraphExecutionPolicyV3)
    assert reloaded == execution
    tampered = execution.model_dump(mode="json", by_alias=True)
    tampered["policy"]["provider_roles"]["controller"]["model"] = "another-model"
    with pytest.raises(ValidationError, match="policy digest"):
        t.PlanWorldGraphExecutionV3.model_validate(tampered)


@pytest.mark.parametrize("mutation", ["missing", "extra", "ambiguous", "blank"])
def test_role_policy_rejects_missing_extra_ambiguous_and_blank_targets(mutation):
    data = {key: dict(value) for key, value in ROLES.items()}
    if mutation == "missing":
        data.pop("writer")
    elif mutation == "extra":
        data["reviewer"] = data["writer"]
    elif mutation == "ambiguous":
        data["writer"] = data["controller"]
    else:
        data["controller"]["model"] = " "
    with pytest.raises(ValidationError):
        t.GraphControllerWriterRolesV1.model_validate(data)


def test_controller_then_one_writer_can_bind_completion():
    _, events = _resolved_controller()
    writer = _auth("writer", 3)
    events += [writer, _outcome(writer, 4, "sdk_entered"), _outcome(writer, 5, "response_received"), _complete(writer, 6)]
    assert _validate(events).events == events


def test_first_attempt_must_be_controller_and_full_identity_must_match():
    with pytest.raises(ValidationError, match="first provider"):
        _validate([_auth("writer", 0)])
    for field in ("provider", "model", "api_mode"):
        with pytest.raises(ValidationError, match="frozen controller/writer"):
            _validate([_auth("controller", 0, **{field: "forged"})])


@pytest.mark.parametrize("terminal", [None, "sdk_entered", "outcome_unknown"])
def test_unresolved_or_unknown_controller_cannot_be_replaced(terminal):
    controller = _auth("controller", 0)
    events = [controller]
    if terminal is not None:
        events.append(_outcome(controller, 1, terminal))
    with pytest.raises(ValidationError, match="resolved prior attempt"):
        _validate(events + [_auth("writer", len(events))])


def test_controller_known_not_sent_can_be_replaced_by_controller():
    controller = _auth("controller", 0)
    assert _validate([controller, _outcome(controller, 1, "known_not_sent"), _auth("controller", 2)])


@pytest.mark.parametrize("terminal", ["known_not_sent", "response_received", "outcome_unknown"])
def test_writer_cannot_be_reauthorized_or_return_to_controller(terminal):
    _, events = _resolved_controller()
    writer = _auth("writer", 3)
    events.append(writer)
    if terminal != "known_not_sent":
        events.append(_outcome(writer, len(events), "sdk_entered"))
    events.append(_outcome(writer, len(events), terminal))
    for role in ("controller", "writer"):
        with pytest.raises(ValidationError):
            _validate(events + [_auth(role, len(events))])


def test_controller_response_cannot_produce_completion():
    controller, events = _resolved_controller()
    with pytest.raises(ValidationError, match="authorized writer"):
        _validate(events + [_complete(controller, len(events))])
    writer = _auth("writer", 3)
    events += [writer, _outcome(writer, 4, "sdk_entered"), _outcome(writer, 5, "response_received")]
    with pytest.raises(ValidationError, match="authorized writer"):
        _validate(events + [_complete(controller, 6)])


@pytest.mark.parametrize("phase", ["controller_pending", "writer"])
def test_acquisition_cannot_continue_during_pending_controller_or_after_writer(phase):
    from tests.application_state.test_agent_conversation_service import _source_admission_v3_fixture
    _, _, origin, _ = _source_admission_v3_fixture()
    if phase == "controller_pending":
        events = [_auth("controller", 0)]
    else:
        _, events = _resolved_controller()
        events.append(_auth("writer", 3))
    origin = origin.model_copy(update={"sequence": len(events), "graph_revision": "graph-rev-11",
        "evidence_ref_ids": origin.evidence_ref_ids[:1], "returned_source_pins": origin.returned_source_pins[:1]})
    with pytest.raises(ValidationError, match="acquisition"):
        _validate(events + [origin])


def _append(service, turn, event):
    if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
        return service.authorize_provider_attempt_v2(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt, provider_attempt_event=event)[0]
    return service.record_provider_outcome(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, outcome=event)[0]


def test_real_build_role_policy_reopen_completion_cas_and_first_envelope(application_state_dsn):
    service = AgentConversationService()
    conversation = _new(service, "build-ledger-world")
    submission = _fixture(conversation.conversation_id)
    accepted = service.accept_turn(submission)
    turn = service.claim_turn(accepted.world_id, accepted.conversation_id, accepted.turn_id,
        expected_revision=accepted.revision, lease_seconds=60).turn
    controller = _auth("controller", 0)
    with pytest.raises(ApplicationStateValidationError):
        _append(service, turn, controller.model_copy(update={"envelope_sha256": "f" * 64}))
    before = turn
    turn = _append(service, turn, controller)
    with pytest.raises(ApplicationStateConflictError):
        _append(service, before, _auth("controller", 0))
    turn = _append(service, turn, _outcome(controller, 1, "sdk_entered"))
    turn = _append(service, turn, _outcome(controller, 2, "response_received"))
    with pytest.raises(ApplicationStateValidationError):
        service.complete_turn(t.TurnResult(world_id=turn.world_id, conversation_id=turn.conversation_id,
            turn_id=turn.turn_id, expected_revision=turn.revision, assistant_text="Mirathorn source.",
            completion=_completion(submission), producing_provider_attempt_id=controller.provider_attempt_id,
            claim_graph_event_ids={}))
    writer = _auth("writer", 3)
    turn = _append(service, turn, writer)
    turn = _append(service, turn, _outcome(writer, 4, "sdk_entered"))
    turn = _append(service, turn, _outcome(writer, 5, "response_received"))
    with pytest.raises(ApplicationStateValidationError):
        _append(service, turn, _auth("controller", 6))
    result = t.TurnResult(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=turn.turn_id, expected_revision=turn.revision, assistant_text="Mirathorn source.",
        completion=_completion(submission), producing_provider_attempt_id=writer.provider_attempt_id,
        claim_graph_event_ids={})
    completed = service.complete_turn(result)
    fresh = AgentConversationService()
    assert fresh.list_turns(turn.world_id, turn.conversation_id) == [completed]
    assert isinstance(completed.graph_context_execution.policy, t.ControllerWriterGraphExecutionPolicyV3)
    assert completed.graph_context_execution.events[-1].provider_attempt_id == writer.provider_attempt_id


def test_uncapped_controller_policy_adds_no_fixed_attempt_limit():
    events = []
    for _ in range(20):
        controller = _auth("controller", len(events))
        events.extend([controller, _outcome(controller, len(events) + 1, "sdk_entered"),
                       _outcome(controller, len(events) + 2, "response_received")])
    assert len(_validate(events).events) == 60


def test_concurrent_role_authorizations_are_serialized_by_real_app_fence(application_state_dsn):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    service = AgentConversationService()
    conversation = _new(service, "build-ledger-world")
    submission = _fixture(conversation.conversation_id)
    accepted = service.accept_turn(submission)
    turn = service.claim_turn(accepted.world_id, accepted.conversation_id, accepted.turn_id,
        expected_revision=accepted.revision, lease_seconds=60).turn
    controller = _auth("controller", 0)
    turn = _append(service, turn, controller)
    turn = _append(service, turn, _outcome(controller, 1, "sdk_entered"))
    turn = _append(service, turn, _outcome(controller, 2, "response_received"))
    with pytest.raises(ApplicationStateValidationError):
        _append(service, turn, _auth("writer", 3, included_evidence_ref_ids=["forged-evidence"]))
    barrier = Barrier(2)
    def race(role):
        barrier.wait(timeout=5)
        try:
            return _append(AgentConversationService(), turn, _auth(role, 3))
        except ApplicationStateConflictError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(race, ["controller", "writer"]))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    fresh = AgentConversationService().list_turns(turn.world_id, turn.conversation_id)[0]
    assert fresh == winners[0]
    assert len(fresh.graph_context_execution.events) == 4
