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
    assert response.answer.text == ("Frank believes the western gate is haunted.\n"
        "This answer uses partial retrieval and does not establish corpus completeness.")
    assert reads == {"graph": 1, "source": 1} and len(writer.calls) == 1
    service = AgentConversationService()
    turn = service.list_turns("elderwyld", service.get_world_pointer("elderwyld").active_conversation_id)[0]
    execution = turn.graph_context_execution
    assert isinstance(execution.policy, ledger.BuildJointSupportActionControllerWriterPolicyV1)
    assert execution.policy.support_policy == "combined_relevant_evidence_support_v1"
    assert isinstance(execution.policy, ledger.BuildReadBatchActionControllerWriterPolicyV1)
    assert execution.policy.acquisition_policy == "jointly_judged_independent_reads_v1"
    assert isinstance(execution.policy, ledger.BuildWriterBudgetActionControllerWriterPolicyV1)
    assert execution.policy.writer_context_budget.context_limit_tokens == 128000
    assert turn.graph_context_receipt.assembled_input.context_window_limit == 64000
    assert execution.policy.controller_continuation_accounting.model_dump() == accounting.descriptor
    authorizations = [e for e in execution.events if isinstance(e, ledger.ProviderAttemptAuthorizedEventV1)]
    assert authorizations[0].input_accounting_kind == "estimated_token_count"
    assert authorizations[-1].input_accounting_kind == "conservative_upper_bound"
    assert isinstance(execution.policy, ledger.BuildInitialEstimatedSelectedSourcePolicyV1)
    assert authorizations[0].input_tokens == turn.graph_context_receipt.assembled_input.provider_envelope_input_tokens
    assert json.loads(decisions.calls[0].content)["state"]["context_accounting"] == accounting.descriptor
    for event, request in zip(authorizations[:-1], decisions.calls, strict=True):
        body = json.loads(request.content)
        assert event.input_accounting_kind == "estimated_token_count"
        assert event.input_estimator == accounting.descriptor["policy"]
        assert event.input_tokens == accounting.estimate(body)
        assert body["state"]["context_accounting"] == accounting.descriptor
        if body["state"].get("decision", {}).get("phase") == "assess":
            assert body["questions"]["joint_support"]["type"] == "noul"
            assert "support" not in body["questions"]
        assert "contained_passage_slices_v1" not in body["state"].get("decision", {}).get("state", {})
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
    with pytest.raises(ValueError, match="context mode differs"):
        ledger.PlanWorldGraphExecutionV3.model_validate(changed)
    selected["input_tokens"] = authorizations[1].input_tokens
    selected["model"] = "another-controller-model"
    with pytest.raises(ValueError, match="role"):
        ledger.PlanWorldGraphExecutionV3.model_validate(changed)
    # APP retains independent writer and controller limits after reload.
    boundary = json.loads(json.dumps(original))
    writer_event = next(e for e in boundary["events"] if e["event_id"] == str(authorizations[-1].event_id))
    writer_event["input_tokens"] = 128000 - 4096
    ledger.PlanWorldGraphExecutionV3.model_validate(boundary)
    writer_event["input_tokens"] += 1
    with pytest.raises(ValueError, match="writer envelope"):
        ledger.PlanWorldGraphExecutionV3.model_validate(boundary)
    writer_event["input_tokens"] -= 1
    writer_event["output_token_reserve"] = 0
    with pytest.raises(ValueError, match="writer envelope"):
        ledger.PlanWorldGraphExecutionV3.model_validate(boundary)
    for event, kind, estimator in [
        (authorizations[0], "conservative_upper_bound", execution.policy.provider_input_accounting.estimator),
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


def test_writer_runtime_budget_drift_cannot_expand_frozen_policy(build_case, monkeypatch, tmp_path):
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter

    original = _PolicyExecutionAdapter.authorize_prepared_build_writer

    def changed_runtime_budget(adapter, prepared):
        adapter.budget["buildJevActions"]["writer_context_budget"]["context_limit_tokens"] = 256000
        return original(adapter, prepared)

    monkeypatch.setattr(_PolicyExecutionAdapter, "authorize_prepared_build_writer", changed_runtime_budget)
    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()
    with pytest.raises(Exception, match="could not complete safely"):
        execute(case, tmp_path, BuildJevHarness(decision_transport=decisions,
            writer_transport=writer, accounting=counter()))
    assert len(decisions.calls) == 5 and writer.calls == []


def test_selection_capacity_refusal_reopens_in_debug_without_a_fake_call(build_case, monkeypatch, tmp_path):
    from apps.live_control_server.services import build_jev_writer_selection as selecting
    from apps.live_control_server.services.build_jev_accounting import DecisionCapacityError
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    from tests.test_build_writer_selection import SelectionWire

    case, _ = ordinary_case(build_case, monkeypatch)
    original = selecting.prepared_driver_view
    def refuse_capacity(*args, **kwargs):
        original(*args, **kwargs)
        raise DecisionCapacityError("Decision request context exceeds experimental estimate",
            code="decision_request_capacity_exceeded")
    monkeypatch.setattr(selecting, "prepared_driver_view", refuse_capacity)
    decisions, writer = SelectionWire("saved_only"), WriterWire()
    harness = BuildJevHarness(decision_transport=decisions, writer_transport=writer,
        accounting=counter(), world_context=True, named_citations=True)
    with pytest.raises(AgentTurnServiceError) as refusal:
        execute(case, tmp_path, harness)
    assert refusal.value.code == "provider_envelope_over_budget"
    assert not writer.calls
    assert decisions.calls and not any(json.loads(call.content)["state"].get("writer_selection_policy") for call in decisions.calls)
    service = AgentConversationService()
    turn, = service.list_turns("elderwyld", service.get_world_pointer("elderwyld").active_conversation_id)
    assert turn.status == "interrupted" and turn.completion is None
    traces = service.list_context_trace_attempts(world_id="elderwyld", turn_id=turn.turn_id)
    assert any(event.kind == "failure" and event.phase == "context_build"
        and event.code == "decision_request_capacity_exceeded" for trace in traces for event in trace.observations)
    authorizations = [event for event in turn.graph_context_execution.events if isinstance(event, ledger.ProviderAttemptAuthorizedEventV1)]
    assert len(authorizations) == len(decisions.calls) == len(harness.calls)
    assert all(call["status"] == "ok" for call in harness.calls)


def test_app_context_append_requires_exact_proof_and_keeps_failed_writes_atomic(build_case,monkeypatch,tmp_path,application_state_dsn):
    from application_state.errors import ApplicationStateValidationError
    original=AgentConversationService.authorize_provider_attempt_v2
    inspected=[]
    def guarded(self,world_id,conversation_id,turn_id,**kwargs):
        event=kwargs["provider_attempt_event"]
        if isinstance(event,ledger.ProviderAttemptAuthorizedEventV5) and not inspected:
            before=[row.model_dump_json(by_alias=True) for row in self.list_turns(world_id,conversation_id)]
            raw=kwargs["prepared_decision_json"]
            for bad in [None,raw+" "]:
                with pytest.raises(ApplicationStateValidationError):
                    original(self,world_id,conversation_id,turn_id,**{**kwargs,"prepared_decision_json":bad})
                assert [row.model_dump_json(by_alias=True) for row in self.list_turns(world_id,conversation_id)]==before
            inspected.append(True)
        return original(self,world_id,conversation_id,turn_id,**kwargs)
    monkeypatch.setattr(AgentConversationService,"authorize_provider_attempt_v2",guarded)
    case,_=ordinary_case(build_case,monkeypatch)
    decisions,writer=DecisionWire(),WriterWire()
    response=execute(case,tmp_path,BuildJevHarness(decision_transport=decisions,writer_transport=writer,accounting=counter()))
    assert inspected and response.answer.status=="ok"
    service=AgentConversationService()
    turn,=service.list_turns("elderwyld",service.get_world_pointer("elderwyld").active_conversation_id)
    controller=[event for event in turn.graph_context_execution.events if isinstance(event,ledger.ProviderAttemptAuthorizedEventV5)]
    assert len(controller)==len(decisions.calls)
    assert all(event.context_mode=="default" for event in controller)

    # The metadata fence changes reader eligibility, not any retained table row.
    import psycopg
    from psycopg import sql
    from alembic import command
    from application_state.cli import alembic_config
    def fingerprints():
        with psycopg.connect(application_state_dsn) as conn:
            tables=conn.execute("SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') AND tablename!='alembic_version' ORDER BY 1,2").fetchall()
            return {(schema,name):conn.execute(sql.SQL("SELECT to_jsonb(row)::text FROM {} row ORDER BY to_jsonb(row)::text").format(sql.Identifier(schema,name))).fetchall() for schema,name in tables}
    before=fingerprints()
    command.stamp(alembic_config(),"20261027_0081")
    command.upgrade(alembic_config(),"head")
    assert fingerprints()==before
    with pytest.raises(RuntimeError,match="Mode-bound Build decisions require recovery forward"):
        command.downgrade(alembic_config(),"20261027_0081")
    assert fingerprints()==before
