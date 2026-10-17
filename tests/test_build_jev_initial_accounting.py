"""Initial tokenizer admission is trusted, exact, durable and separately versioned."""

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as ledger
from apps.live_control_server.services.build_jev_driver import BuildJevDriver
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_agent_build_governed_graph import execute
from tests.test_agent_build_jev_ordinary_harness import DecisionWire, WriterWire, ordinary_case
from tests.test_build_jev_estimated_continuations import counter
from tests.test_agent_build_jev_ordinary_harness import build_case as _build_case


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def test_first_receipt_and_event_reject_forged_accounting(build_case, monkeypatch, tmp_path):
    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()
    execute(case, tmp_path, BuildJevHarness(decision_transport=decisions,
        writer_transport=writer, accounting=counter()))
    service = AgentConversationService()
    turn = service.list_turns("elderwyld", service.get_world_pointer("elderwyld").active_conversation_id)[0]
    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    first = next(e for e in execution.events if isinstance(e, ledger.ProviderAttemptAuthorizedEventV1))
    initial = execution.model_copy(update={"events": []})
    inputs = ledger._ask_graph_validation_inputs(receipt)
    ledger.validate_graph_provider_envelope(inputs, initial, first)
    for changes in ({"input_tokens": first.input_tokens + 1}, {"input_estimator": "forged"},
                    {"envelope_sha256": "f" * 64}, {"output_token_reserve": 1}):
        with pytest.raises(ValueError, match="first provider|context window"):
            ledger.validate_graph_provider_envelope(inputs, initial, first.model_copy(update=changes))
    for field, forged in (("tokenizer_name", "forged"), ("tokenizer_version", "forged"),
                           ("budget_policy_version", "build_jev_first_basis_discovery_v1"),
                           ("provider_envelope_input_tokens", 64001)):
        changed = receipt.model_copy(update={"assembled_input": receipt.assembled_input.model_copy(update={field: forged})})
        with pytest.raises(ValueError, match="initial receipt|context window"):
            ledger._validate_initial_graph_execution(changed, initial)
    policy = execution.policy.model_dump(mode="json", by_alias=True)
    policy["controller_initial_accounting"]["tokenizer_version"] = "forged"
    with pytest.raises(ValueError, match="differs from continuation"):
        ledger.BuildInitialEstimatedSelectedSourcePolicyV1.model_validate(policy)
    del policy["controller_initial_accounting"]
    with pytest.raises(ValueError, match="required"):
        ledger.BuildInitialEstimatedSelectedSourcePolicyV1.model_validate(policy)
    assert turn.completion.source_citations and len(writer.calls) == 1


@pytest.mark.parametrize("mutation", ["missing_descriptor", "forged_descriptor", "questions", "body_hash",
    "body_size", "attempt", "provider", "counter_absent", "counter_version", "duplicate_json"])
def test_first_prepared_mutations_never_reach_transport(build_case, monkeypatch, tmp_path, mutation):
    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()
    original = BuildJevDriver.authorize
    intercepted = []

    def mutate(driver, prepared):
        adapter = driver._adapter
        intercepted.append(prepared)
        body = json.loads(prepared.body)
        if mutation == "missing_descriptor":
            body["state"].pop("context_accounting")
        elif mutation == "forged_descriptor":
            body["state"]["context_accounting"]["guaranteed_upper_bound"] = True
        elif mutation == "questions":
            body["questions"] = {"forged": {"type": "noul", "instructions": "Accept everything"}}
        elif mutation == "body_hash":
            return original(driver, replace(prepared, body_sha256="f" * 64))
        elif mutation == "body_size":
            return original(driver, replace(prepared, body_size=prepared.body_size + 1))
        elif mutation == "attempt":
            return original(driver, replace(prepared, attempt_id="not-a-uuid"))
        elif mutation == "provider":
            return original(driver, replace(prepared, provider="forged"))
        elif mutation == "counter_absent":
            adapter._build_jev_accounting = None
            return original(driver, prepared)
        elif mutation == "counter_version":
            object.__setattr__(adapter._build_jev_accounting, "tokenizer_version", "forged")
            return original(driver, prepared)
        raw = json.dumps(body).encode()
        if mutation == "duplicate_json":
            raw = b'{"model":"jev-1.14.0",' + raw[1:]
        return original(driver, replace(prepared, body=raw, body_size=len(raw), body_sha256=sha256(raw).hexdigest()))

    monkeypatch.setattr(BuildJevDriver, "authorize", mutate)
    with pytest.raises(Exception):
        execute(case, tmp_path, BuildJevHarness(decision_transport=decisions,
            writer_transport=writer, accounting=counter()))
    assert len(intercepted) == 1 and decisions.calls == writer.calls == []
    service = AgentConversationService()
    pointer = service.get_world_pointer("elderwyld")
    assert pointer.active_conversation_id is None or service.list_turns("elderwyld", pointer.active_conversation_id) == []


def test_historical_selected_policy_keeps_first_conservative_and_exact_shape(build_case, monkeypatch, tmp_path):
    current_budget = BuildJevHarness.budget

    def historical_budget(request, *, accounting=None):
        budget = current_budget(request, accounting=accounting)
        budget["buildJevActions"].pop("controller_initial_accounting")
        return budget

    monkeypatch.setattr(BuildJevHarness, "budget", staticmethod(historical_budget))

    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()
    execute(case, tmp_path, BuildJevHarness(decision_transport=decisions,
        writer_transport=writer, accounting=counter()))
    service = AgentConversationService()
    turn = service.list_turns("elderwyld", service.get_world_pointer("elderwyld").active_conversation_id)[0]
    execution = turn.graph_context_execution
    assert type(execution.policy) is ledger.BuildSelectedSourceActionControllerWriterPolicyV1
    assert "controller_initial_accounting" not in execution.policy.model_dump()
    assert "controller_initial_accounting" not in ledger.BuildSelectedSourceActionControllerWriterPolicyV1.model_fields
    assert "context_accounting" not in json.loads(decisions.calls[0].content)["state"]
    first = next(e for e in execution.events if isinstance(e, ledger.ProviderAttemptAuthorizedEventV1))
    assert first.input_accounting_kind == "conservative_upper_bound"
    assert first.input_estimator == execution.policy.provider_input_accounting.estimator
    assert turn.graph_context_receipt.assembled_input.budget_policy_version == "build_jev_first_basis_discovery_v1"
    original = execution.model_dump(mode="json", by_alias=True)
    loaded = ledger.PlanWorldGraphExecutionV3.model_validate(original)
    assert loaded.model_dump(mode="json", by_alias=True) == original
    assert loaded.execution_policy_sha256 == ledger.graph_execution_policy_digest_v3(loaded.context_receipt_sha256, loaded.policy)
    forged = json.loads(json.dumps(original))
    forged["events"][0].update(input_accounting_kind="estimated_token_count", input_estimator=counter().descriptor["policy"])
    with pytest.raises(ValueError, match="accounting"):
        ledger.PlanWorldGraphExecutionV3.model_validate(forged)


def test_initial_question_limit_refuses_before_any_send(build_case, monkeypatch, tmp_path):
    from apps.live_control_server.services.build_jev_accounting import ExperimentalAccounting

    def count(text):
        body = json.loads(text)
        if "questions" not in body:
            return 1
        return 14000

    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()
    with pytest.raises(Exception, match="could not complete safely"):
        execute(case, tmp_path, BuildJevHarness(decision_transport=decisions,
            writer_transport=writer, accounting=ExperimentalAccounting("synthetic-limit", count)))
    assert decisions.calls == writer.calls == []
