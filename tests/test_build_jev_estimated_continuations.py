"""Ordinary SDK + real APP proofs for truthful, opt-in continuation estimates."""

import json

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as ledger
from apps.live_control_server.services.build_jev_accounting import ExperimentalAccounting
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire,
    WriterWire,
    ordinary_case,
    build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def counter():
    # Trusted synthetic counter; actual cached tokenizer is exercised separately.
    return ExperimentalAccounting("synthetic-test", lambda text: len(text.encode()) // 4)


def test_ordinary_estimates_survive_append_reload_and_reject_role_downgrades(
    build_case, monkeypatch, tmp_path
):
    case, reads = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()
    accounting = counter()
    response = execute(case, tmp_path, BuildJevHarness(
        decision_transport=decisions, writer_transport=writer, accounting=accounting,
    ))
    assert response.answer.text == "Frank believes the western gate is haunted."
    assert reads == {"graph": 1, "source": 1} and len(writer.calls) == 1
    service = AgentConversationService()
    turn = service.list_turns("elderwyld", service.get_world_pointer("elderwyld").active_conversation_id)[0]
    execution = turn.graph_context_execution
    assert isinstance(execution.policy, ledger.BuildEstimatedActionControllerWriterPolicyV1)
    assert execution.policy.controller_continuation_accounting.model_dump() == accounting.descriptor
    authorizations = [e for e in execution.events if isinstance(e, ledger.ProviderAttemptAuthorizedEventV1)]
    assert authorizations[0].input_accounting_kind == authorizations[-1].input_accounting_kind == "conservative_upper_bound"
    assert authorizations[0].input_tokens == turn.graph_context_receipt.assembled_input.provider_envelope_input_tokens
    for event, request in zip(authorizations[1:-1], decisions.calls[1:], strict=True):
        body = json.loads(request.content)
        assert event.input_accounting_kind == "estimated_token_count"
        assert event.input_estimator == accounting.descriptor["policy"]
        assert event.input_tokens == accounting.estimate(body)
        assert body["state"]["context_accounting"] == accounting.descriptor
        assert "contained_passage_slices_v1" not in body["state"]["decision"]["state"]
    # Historical accounting rejects an estimated event at its own boundary.
    legacy_policy = {k: v for k, v in execution.policy.model_dump(mode="json", by_alias=True).items()
        if k in ledger.GraphExecutionPolicyV1.model_fields}
    legacy_event = {k: v for k, v in authorizations[1].model_dump(mode="json", by_alias=True).items()
        if k in ledger.ProviderAttemptAuthorizedEventV1.model_fields}
    legacy_event.update(kind="provider_attempt_authorized", sequence=0)
    with pytest.raises(ValueError, match="accounting"):
        ledger.PlanWorldGraphExecutionV1.model_validate(dict(
            context_receipt_sha256=execution.context_receipt_sha256,
            policy=legacy_policy, events=[legacy_event]))
    original = execution.model_dump(mode="json", by_alias=True)
    assert ledger.PlanWorldGraphExecutionV3.model_validate(original).model_dump(mode="json", by_alias=True) == original
    changed = json.loads(json.dumps(original))
    selected = next(e for e in changed["events"] if e["event_id"] == str(authorizations[1].event_id))
    selected["input_tokens"] = 64001
    with pytest.raises(ValueError, match="estimate exceeds"):
        ledger.PlanWorldGraphExecutionV3.model_validate(changed)
    selected["input_tokens"] = authorizations[1].input_tokens
    selected["model"] = "another-controller-model"
    with pytest.raises(ValueError, match="role"):
        ledger.PlanWorldGraphExecutionV3.model_validate(changed)
    for event, kind, estimator in [
        (authorizations[0], "estimated_token_count", accounting.descriptor["policy"]),
        (authorizations[-1], "estimated_token_count", accounting.descriptor["policy"]),
        (authorizations[1], "conservative_upper_bound", execution.policy.provider_input_accounting.estimator),
        (authorizations[1], "estimated_token_count", "wrong-tokenizer"),
    ]:
        changed = json.loads(json.dumps(original))
        selected = next(e for e in changed["events"] if e["event_id"] == str(event.event_id))
        selected.update(input_accounting_kind=kind, input_estimator=estimator)
        with pytest.raises(ValueError, match="accounting"):
            ledger.PlanWorldGraphExecutionV3.model_validate(changed)


def test_counter_is_validated_before_any_provider_send(build_case, monkeypatch, tmp_path):
    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()

    def absent(text):
        raise ValueError("offline tokenizer unavailable")

    harness = BuildJevHarness(decision_transport=decisions, writer_transport=writer,
        accounting=ExperimentalAccounting("synthetic-test", absent))
    with pytest.raises(ValueError, match="offline tokenizer unavailable"):
        execute(case, tmp_path, harness)
    assert decisions.calls == writer.calls == []


def test_descriptor_is_required_and_historical_policy_fields_are_unchanged():
    assert "controller_continuation_accounting" not in ledger.BuildPhaseActionControllerWriterPolicyV1.model_fields
    assert "controller_continuation_accounting" not in ledger.BuildContainedActionControllerWriterPolicyV1.model_fields
    assert "estimated_token_count" not in str(ledger.GraphExecutionAccountingV1.model_fields["kind"].annotation)
    for key, value in [("multiplier", 1), ("guaranteed_upper_bound", True), ("question_limit_tokens", 64000)]:
        descriptor = counter().descriptor
        descriptor[key] = value
        with pytest.raises(ValueError):
            ledger.BuildControllerContinuationAccountingV1.model_validate(descriptor)


def test_changed_counter_descriptor_refuses_after_first_response(build_case, monkeypatch, tmp_path):
    case, _ = ordinary_case(build_case, monkeypatch)
    accounting = counter()

    class ChangedDescriptorWire(DecisionWire):
        async def handle_async_request(self, request):
            response = await super().handle_async_request(request)
            if len(self.calls) == 1:
                object.__setattr__(accounting, "tokenizer_version", "changed-after-freeze")
            return response

    decisions, writer = ChangedDescriptorWire(), WriterWire()
    with pytest.raises(Exception, match="could not complete safely"):
        execute(case, tmp_path, BuildJevHarness(decision_transport=decisions,
            writer_transport=writer, accounting=accounting))
    assert len(decisions.calls) == 1 and writer.calls == []
