"""Exact parent-side witnesses for native Rules tool dispatch."""

import json
from types import SimpleNamespace
from threading import RLock
from uuid import uuid4

import pytest

from apps.live_control_server.services.native_rules_capture import NativeToolReply
from apps.live_control_server.services.native_rules_runtime import (
    NativeRulesRuntime,
    _captured_lookup_call,
    _provider_lookup_arguments,
)
from application_state.agent_conversation.rules_authority_events import (
    RulesProviderAuthorizedV1,
    RulesProviderOutcomeV1,
    RulesQueryObservedV1,
    RulesToolAuthorizedV1,
    RulesBudgetUseV1,
)
from application_state.agent_conversation.rules_authority_policy import RULESET


class CapturedReply:
    status = "tool_calls"

    def __init__(self, *calls):
        self.tool_calls = calls


def call(call_id="call-1", name="lookup_rules", arguments=None):
    arguments = arguments or {"question": "Can a creature end its move here?", "ruleset_id": RULESET}
    return NativeToolReply(
        call_id=call_id,
        name=name,
        arguments_json=json.dumps(arguments, separators=(",", ":")),
        arguments_sha256="0" * 64,
    )


def arguments():
    return {"question": "Can a creature end its move here?", "ruleset_id": RULESET}


def test_parent_accepts_only_the_exact_captured_lookup_call():
    reply = CapturedReply(call())

    assert _captured_lookup_call(reply, "call-1", arguments()) == "call-1"


def test_parent_rejects_a_foreign_tool_call_id():
    reply = CapturedReply(call())

    try:
        _captured_lookup_call(reply, "forged-call", arguments())
    except ValueError as exc:
        assert "captured lookup_rules call" in str(exc)
    else:
        raise AssertionError("foreign call ID was accepted")


def test_parent_rejects_ambiguous_duplicate_call_identity():
    reply = CapturedReply(call(), call())

    try:
        _captured_lookup_call(reply, "call-1", arguments())
    except ValueError as exc:
        assert "captured lookup_rules call" in str(exc)
    else:
        raise AssertionError("duplicate captured call ID was accepted")


def test_parent_rejects_arguments_that_differ_from_the_captured_call():
    reply = CapturedReply(call())
    changed = {**arguments(), "question": "How fast can they travel?"}

    try:
        _captured_lookup_call(reply, "call-1", changed)
    except ValueError as exc:
        assert "differ from the captured provider reply" in str(exc)
    else:
        raise AssertionError("changed tool arguments were accepted")


def test_parent_rejects_duplicate_json_argument_keys():
    captured = NativeToolReply(
        call_id="call-1", name="lookup_rules",
        arguments_json='{"question":"first","question":"second","ruleset_id":"'
        + RULESET + '"}',
        arguments_sha256="0" * 64,
    )

    try:
        _captured_lookup_call(CapturedReply(captured), "call-1", arguments())
    except ValueError as exc:
        assert "duplicate JSON keys" in str(exc)
    else:
        raise AssertionError("duplicate argument key was accepted")


def test_provider_input_arguments_must_match_durable_authorized_query():
    question = arguments()["question"]
    scope = SimpleNamespace(ruleset_id=RULESET)
    authorization = SimpleNamespace(normalized_question=question.casefold())
    payload = json.dumps(arguments())

    assert _provider_lookup_arguments(payload, scope, authorization).question == question

    changed = json.dumps({**arguments(), "question": "How fast can they travel?"})
    try:
        _provider_lookup_arguments(changed, scope, authorization)
    except ValueError as exc:
        assert "differ from the authorized query" in str(exc)
    else:
        raise AssertionError("reused call ID with changed question was accepted")


def test_provider_input_rejects_duplicate_lookup_argument_keys():
    scope = SimpleNamespace(ruleset_id=RULESET)
    authorization = SimpleNamespace(
        normalized_question=arguments()["question"].casefold()
    )
    payload = '{"question":"Can a creature end its move here?",' \
        '"question":"How fast can they travel?","ruleset_id":"' + RULESET + '"}'

    try:
        _provider_lookup_arguments(payload, scope, authorization)
    except ValueError as exc:
        assert "duplicate JSON keys" in str(exc)
    else:
        raise AssertionError("duplicate provider argument key was accepted")


@pytest.mark.parametrize(
    ("transition", "expected_status"),
    [("known_not_sent", "failed"), ("outcome_unknown", "unknown")],
)
def test_native_rules_lifecycle_records_only_uncaptured_terminal_outcomes(
    transition, expected_status,
):
    attempt_id = uuid4()
    execution_id = uuid4()
    authorization = RulesProviderAuthorizedV1(
        kind="provider_authorized", event_id=uuid4(), sequence=0,
        execution_id=execution_id, provider_attempt_id=attempt_id,
        request_envelope_sha256="a" * 64, matched_outputs=(),
        declared_support_refs=(),
    )
    execution = SimpleNamespace(
        events=(authorization,), scope=SimpleNamespace(execution_id=execution_id)
    )
    record = SimpleNamespace(execution=execution, revision=1)
    turn = SimpleNamespace(revision=4)

    class Service:
        def append_rules_provider_event(self, _scope, *, event, **_kwargs):
            nonlocal record
            record = SimpleNamespace(
                execution=SimpleNamespace(
                    events=(*record.execution.events, event),
                    scope=record.execution.scope,
                ),
                revision=record.revision + 1,
            )
            return record

    runtime = object.__new__(NativeRulesRuntime)
    runtime.record = record
    runtime.adapter = SimpleNamespace(
        last_provider_attempt_id=attempt_id,
        service=Service(),
        fence=SimpleNamespace(
            renewer=SimpleNamespace(_lock=RLock(), _turn=turn)
        ),
    )

    runtime.outcome(transition)

    outcome_events = [
        event for event in runtime.record.execution.events
        if isinstance(event, RulesProviderOutcomeV1)
    ]
    assert len(outcome_events) == 1
    assert outcome_events[0].status == expected_status


def test_native_rules_response_received_waits_for_exact_reply_capture():
    attempt_id = uuid4()
    execution_id = uuid4()
    authorization = RulesProviderAuthorizedV1(
        kind="provider_authorized", event_id=uuid4(), sequence=0,
        execution_id=execution_id, provider_attempt_id=attempt_id,
        request_envelope_sha256="a" * 64, matched_outputs=(),
        declared_support_refs=(),
    )
    record = SimpleNamespace(
        execution=SimpleNamespace(
            events=(authorization,), scope=SimpleNamespace(execution_id=execution_id)
        ),
        revision=1,
    )
    runtime = object.__new__(NativeRulesRuntime)
    runtime.record = record
    runtime.adapter = SimpleNamespace(
        last_provider_attempt_id=attempt_id,
        service=SimpleNamespace(
            append_rules_provider_event=lambda *_args, **_kwargs: pytest.fail(
                "generic response lifecycle must not decide the Rules reply kind"
            )
        ),
        fence=SimpleNamespace(renewer=SimpleNamespace(_lock=RLock())),
    )

    runtime.outcome("response_received")

    assert runtime.record is record
    assert len(runtime.record.execution.events) == 1


def test_no_rules_lookup_still_requires_actual_final_provider_reply():
    runtime = object.__new__(NativeRulesRuntime)
    runtime.record = SimpleNamespace(execution=SimpleNamespace(
        supports={}, budget_use=RulesBudgetUseV1(
            calls=0, distinct_questions=0, novel_excerpt_utf8=0,
            presentation_utf8=0, provider_requests=0,
        ),
    ))
    with pytest.raises(ValueError, match="actual final provider reply"):
        runtime.complete(SimpleNamespace(), None)


@pytest.mark.parametrize("wire_shape", ["responses", "chat"])
def test_parent_matches_provider_input_question_to_durable_lookup(monkeypatch, wire_shape):
    execution_id = uuid4()
    call_id = "call-1"
    question = arguments()["question"]
    packet = '{"schema":"dmb_rules_packet_v1","status":"no_evidence"}'
    authorization = RulesToolAuthorizedV1(
        kind="tool_authorized", event_id=uuid4(), sequence=0,
        execution_id=execution_id, call_id=call_id, query_id="a" * 64,
        normalized_question=question.casefold(), packet_limit=4,
    )
    observation = RulesQueryObservedV1(
        kind="query_observed", event_id=uuid4(), sequence=1,
        execution_id=execution_id, call_id=call_id, query_id=authorization.query_id,
        packet_sha256="b" * 64, presentation_utf8=len(packet.encode()),
        status="no_evidence", support_refs=(), emitted_support_ids=(),
    )
    execution = SimpleNamespace(
        events=(authorization, observation), scope=SimpleNamespace(ruleset_id=RULESET)
    )
    runtime = object.__new__(NativeRulesRuntime)
    runtime.record = SimpleNamespace(execution=execution)
    monkeypatch.setattr(
        "application_state.agent_conversation.rules_authority_runtime._replay",
        lambda *_args: SimpleNamespace(raw_output=packet),
    )

    def request_body(call_arguments):
        if wire_shape == "responses":
            return {"input": [
                {"type": "function_call", "call_id": call_id,
                 "name": "lookup_rules", "arguments": json.dumps(call_arguments)},
                {"type": "function_call_output", "call_id": call_id, "output": packet},
            ]}
        return {"messages": [
            {"role": "assistant", "tool_calls": [{
                "id": call_id, "type": "function",
                "function": {"name": "lookup_rules", "arguments": json.dumps(call_arguments)},
            }]},
            {"role": "tool", "tool_call_id": call_id, "content": packet},
        ]}

    output_refs, support_refs = runtime._actual_lookup_material(request_body(arguments()))
    assert len(output_refs) == 1
    assert output_refs[0].call_id == call_id
    assert output_refs[0].packet_sha256 == observation.packet_sha256
    assert support_refs == ()

    changed = {**arguments(), "question": "How fast can they travel?"}
    with pytest.raises(ValueError, match="differ from the authorized query"):
        runtime._actual_lookup_material(request_body(changed))


@pytest.mark.parametrize("unused", [True, False])
@pytest.mark.parametrize("capture_mode", ["enabled", "disabled", "fails"])
def test_native_completion_captures_validated_answer_before_closing_claim(unused, capture_mode):
    from tests.application_state.test_native_rules_output import native_case
    from tests.test_native_answer_output import plan_turn
    from application_state.errors import ApplicationStateConflictError
    turn, _ = plan_turn()
    base = {"answer_context_status": "plan_only_insufficient_evidence",
            "answer_segments": [{"kind": "plan_claim", "text": "The party reaches Edge."}], "citation_map": None}
    _, rules, proof, reply, _, turn = native_case(graph_turn=turn, base_output=base, unused=unused)
    calls = []
    state = {"running": True}
    def capture(text):
        assert state["running"], "trace cannot append after completion"
        calls.append(("capture", text))
        if capture_mode == "fails":
            raise ApplicationStateConflictError("trace capture was fenced")
    def complete(result, **kwargs):
        assert state["running"]
        calls.append(("complete", result.assistant_text))
        state["running"] = False
        return result
    runtime = object.__new__(NativeRulesRuntime)
    runtime.record = SimpleNamespace(execution=rules, revision=1)
    runtime.graph_enabled = True
    runtime.last_provider = {"providerAttemptId": str(proof.producing_provider_attempt_id)}
    runtime.last_prepared_json = proof.prepared_request_json
    runtime.adapter = SimpleNamespace(
        producing_provider_attempt_id=proof.producing_provider_attempt_id,
        operation_payloads={}, build_claim_evidence={},
        context_capture=None if capture_mode == "disabled" else SimpleNamespace(answer_context=capture),
        service=SimpleNamespace(complete_native_base_turn=complete, complete_mixed_turn=complete),
    )
    if capture_mode == "fails":
        with pytest.raises(ApplicationStateConflictError, match="trace capture was fenced"):
            runtime.complete(turn, reply)
        assert state["running"] and [kind for kind, _ in calls] == ["capture"]
    else:
        result = runtime.complete(turn, reply)
        expected = "The party reaches Edge." + ("" if unused else "\nThe rule applies.")
        assert result.assistant_text == expected
        assert [kind for kind, _ in calls] == (["complete"] if capture_mode == "disabled" else ["capture", "complete"])
        assert all(text == expected for _, text in calls)
