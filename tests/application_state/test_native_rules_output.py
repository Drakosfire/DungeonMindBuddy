"""APP joins native raw output to one exact final Graph+Rules producer."""

from types import SimpleNamespace
from hashlib import sha256
from uuid import uuid4
import json

import pytest

from application_state.agent_conversation.native_rules_output import (
    NativeRulesOutputProofV1,
    normalize_native_mixed_output,
    verify_native_output,
)
from application_state.agent_conversation.rules_authority_events import (
    RulesOutputRefV1,
    RulesProviderAuthorizedV1,
    RulesProviderIncludedV1,
    RulesNativeProviderOutcomeV1,
    RulesProviderOutcomeV1,
)
from application_state.agent_conversation.types import ProviderOutcomeEventV1
from tests.test_rules_build_input import append, execution as native_rules_execution
from tests.test_rules_lookup_broker import args, lookup as rules_lookup
from tests.test_play_graph_authority import native_provider
from tests.test_native_answer_output import plan_turn


def native_case(*, graph_turn=None, base_output=None):
    owner = native_rules_execution()
    attempt = uuid4()
    if graph_turn is not None:
        attempt = next(
            event.provider_attempt_id
            for event in graph_turn.graph_context_execution.events
            if hasattr(event, "envelope_sha256")
        )
        scope = owner.scope.model_copy(update={
            "world_id": graph_turn.world_id,
            "conversation_id": graph_turn.conversation_id,
            "turn_id": graph_turn.turn_id,
            "product_attempt": graph_turn.attempt,
        })
        owner = owner.model_copy(update={"scope": scope})
    owner, lookup = rules_lookup(owner)
    prepared_request_json = json.dumps({"messages": [
        {"role": "assistant", "tool_calls": [{
            "id": lookup.observation.call_id,
            "type": "function",
            "function": {
                "name": "lookup_rules",
                "arguments": json.dumps({
                    "question": args().question,
                    "ruleset_id": owner.scope.ruleset_id,
                }),
            },
        }]},
        {"role": "tool", "tool_call_id": lookup.observation.call_id,
         "content": lookup.raw_output},
    ]})
    request_sha = sha256(prepared_request_json.encode("utf-8")).hexdigest()
    refs = lookup.observation.support_refs
    outputs = (
        RulesOutputRefV1(
            call_id=lookup.observation.call_id,
            packet_sha256=lookup.observation.packet_sha256,
        ),
    )
    auth = RulesProviderAuthorizedV1(
        event_id=uuid4(),
        sequence=len(owner.events),
        execution_id=owner.scope.execution_id,
        kind="provider_authorized",
        provider_attempt_id=attempt,
        request_envelope_sha256=request_sha,
        matched_outputs=outputs,
        declared_support_refs=refs,
    )
    owner = append(owner, auth)
    included = RulesProviderIncludedV1(
        event_id=uuid4(),
        sequence=len(owner.events),
        execution_id=owner.scope.execution_id,
        kind="provider_included",
        provider_attempt_id=attempt,
        request_envelope_sha256=request_sha,
        matched_outputs=outputs,
        support_refs=refs,
    )
    owner = append(owner, included)
    ordered_refs = ([{"domain": "base", "segment_index": None}]
                    if base_output is not None else [])
    ordered_refs.append({"domain": "rules", "segment_index": 0})
    raw = json.dumps(
        {
            "schema": "dmb_rules_mixed_answer_v1",
            "base_output": base_output,
            "rules_segments": [
                {
                    "kind": "rules_claim",
                    "text": "The rule applies.",
                    "support_ids": [str(refs[0].support_id)],
                }
            ],
            "ordered_refs": ordered_refs,
        }
    )
    if graph_turn is None:
        graph_auth = native_provider().model_copy(
            update={"provider_attempt_id": attempt, "envelope_sha256": request_sha}
        )
        graph = SimpleNamespace(events=[
            graph_auth,
            ProviderOutcomeEventV1(
                event_id=uuid4(), sequence=1, kind="provider_outcome",
                provider_attempt_id=attempt, outcome="response_received",
            ),
        ])
    else:
        graph = graph_turn.graph_context_execution
        events = list(graph.events)
        graph_auth = next(
            event for event in events
            if getattr(event, "provider_attempt_id", None) == attempt
            and hasattr(event, "envelope_sha256")
        )
        graph_auth = graph_auth.model_copy(update={
            "envelope_sha256": request_sha,
            "api_mode": "codex_responses",
        })
        events[events.index(next(
            event for event in events
            if getattr(event, "provider_attempt_id", None) == attempt
            and hasattr(event, "envelope_sha256")
        ))] = graph_auth
        graph = graph.model_copy(update={"events": tuple(events)})
        graph_turn = graph_turn.model_copy(update={"graph_context_execution": graph})
    raw_bytes = raw.encode("utf-8")
    if graph_turn is None:
        graph_auth = graph_auth.model_copy(update={"api_mode": "codex_responses"})
        graph.events[0] = graph_auth
    capture = SimpleNamespace(
        authorization_id="host:1",
        api_request_id="api-request-1",
        provider=getattr(graph_auth, "provider", "synthetic"),
        model=getattr(graph_auth, "model", "synthetic"),
        api_mode=getattr(graph_auth, "api_mode", "codex_responses"),
        request_sha256=request_sha,
        status="answered",
        finish_reason="stop",
        text=raw,
        text_sha256=sha256(raw_bytes).hexdigest(),
        text_utf8_bytes=len(raw_bytes),
        tool_calls=(),
    )
    owner = append(
        owner,
        RulesNativeProviderOutcomeV1.from_capture(
            capture,
            event_id=uuid4(),
            sequence=len(owner.events),
            execution_id=owner.scope.execution_id,
            provider_attempt_id=attempt,
            request_envelope_sha256=request_sha,
        ),
    )
    proof = NativeRulesOutputProofV1.from_capture(
        capture,
        prepared_request_json=prepared_request_json,
        rules_execution_id=owner.scope.execution_id,
        producing_provider_attempt_id=attempt,
    )
    return graph, owner, proof, capture, raw, graph_turn


def changed(value, **updates):
    return SimpleNamespace(**(vars(value) | updates))


def test_native_output_joins_actual_final_request_and_rules_supports():
    graph, rules, proof, capture, _, _ = native_case()
    answer = verify_native_output(graph, rules, proof, capture)
    assert answer.rules_segments[0].text == "The rule applies."
    assert answer.rules_segments[0].support_ids == tuple(
        str(item.support_id) for item in rules.events[-2].support_refs
    )


def test_native_mixed_output_normalizes_approved_plan_base_and_rules_partition():
    turn, _ = plan_turn()
    base = {
        "answer_context_status": "plan_only_insufficient_evidence",
        "answer_segments": [{"kind": "plan_claim", "text": "The party reaches Edge."}],
        "citation_map": None,
    }
    graph, rules, proof, capture, _, turn = native_case(
        graph_turn=turn, base_output=base
    )

    result = normalize_native_mixed_output(turn, graph, rules, proof, capture)

    assert result.base_completion.answer_segments[0].text == "The party reaches Edge."
    assert result.composition.base_disposition == "approved"
    assert [ref.domain for ref in result.composition.ordered_refs] == ["base", "rules"]
    assert result.assistant_text == "The party reaches Edge.\nThe rule applies."
    assert result.graph_used is False


def test_native_mixed_output_marks_unclaimed_plan_base_without_discarding_turn_graph():
    turn, _ = plan_turn()
    graph, rules, proof, capture, _, turn = native_case(graph_turn=turn)

    result = normalize_native_mixed_output(turn, graph, rules, proof, capture)

    assert result.base_completion is None
    assert result.composition.base_disposition == "unclaimed"
    assert result.assistant_text == "The rule applies."


def test_native_mixed_output_rejects_build_receipt_with_plan_graph_execution():
    from application_state.agent_conversation.types import BuildGraphContextReceiptV1

    turn, _ = plan_turn()
    graph, rules, proof, capture, _, turn = native_case(graph_turn=turn)
    build_receipt = BuildGraphContextReceiptV1.model_construct()
    forged_turn = turn.model_copy(update={"graph_context_receipt": build_receipt})

    with pytest.raises(ValueError, match="owning Plan or Play Graph pair"):
        normalize_native_mixed_output(forged_turn, graph, rules, proof, capture)


def test_native_output_rechecks_actual_rules_call_and_result_bytes():
    graph, rules, proof, capture, _, _ = native_case()
    body = json.loads(proof.prepared_request_json)
    body["messages"][1]["content"] += " forged"
    prepared = json.dumps(body)
    digest = sha256(prepared.encode("utf-8")).hexdigest()
    proof = proof.model_copy(update={
        "prepared_request_json": prepared,
        "request_envelope_sha256": digest,
    })
    graph.events[0] = graph.events[0].model_copy(update={"envelope_sha256": digest})
    events = list(rules.events)
    for index, event in enumerate(events):
        if isinstance(event, (RulesProviderAuthorizedV1, RulesProviderIncludedV1,
                              RulesProviderOutcomeV1)):
            events[index] = event.model_copy(update={"request_envelope_sha256": digest})
    rules = rules.model_copy(update={"events": tuple(events)})
    capture = changed(capture, request_sha256=digest)
    with pytest.raises(ValueError, match="prepared input differs"):
        verify_native_output(graph, rules, proof, capture)


def test_native_output_rejects_rewritten_capture_and_proof_against_sealed_outcome():
    graph, rules, proof, capture, _, _ = native_case()
    raw = capture.text.replace("The rule applies.", "A forged rule applies.")
    raw_bytes = raw.encode("utf-8")
    forged_capture = changed(
        capture,
        text=raw,
        text_sha256=sha256(raw_bytes).hexdigest(),
        text_utf8_bytes=len(raw_bytes),
    )
    forged_proof = NativeRulesOutputProofV1.from_capture(
        forged_capture,
        prepared_request_json=proof.prepared_request_json,
        rules_execution_id=proof.rules_execution_id,
        producing_provider_attempt_id=proof.producing_provider_attempt_id,
    )

    with pytest.raises(ValueError, match="exact included Rules evidence"):
        verify_native_output(graph, rules, forged_proof, forged_capture)


@pytest.mark.parametrize(
    "mutation",
    [
        "request_hash",
        "provider",
        "model",
        "mode",
        "status",
        "finish",
        "tools",
        "raw",
        "proof_hash",
        "request_body",
        "missing_graph",
        "missing_rules_include",
        "not_final_rules_auth",
    ],
)
def test_native_output_rejects_capture_and_authority_mismatches(mutation):
    graph, rules, proof, capture, raw, _ = native_case()
    if mutation == "request_hash":
        capture = changed(capture, request_sha256="b" * 64)
    elif mutation == "provider":
        capture = changed(capture, provider="foreign")
    elif mutation == "model":
        capture = changed(capture, model="foreign")
    elif mutation == "mode":
        capture = changed(capture, api_mode="foreign")
    elif mutation == "status":
        capture = changed(capture, status="failed")
    elif mutation == "finish":
        capture = changed(capture, finish_reason="length")
    elif mutation == "tools":
        capture = changed(capture, tool_calls=(object(),))
    elif mutation == "raw":
        capture = changed(capture, text=raw + " ")
    elif mutation == "proof_hash":
        proof = proof.model_copy(update={"raw_output_sha256": "b" * 64})
    elif mutation == "request_body":
        proof = proof.model_copy(
            update={"prepared_request_json": '{"input":"changed"}'}
        )
    elif mutation == "missing_graph":
        graph = SimpleNamespace(events=[])
    elif mutation == "missing_rules_include":
        rules = rules.model_copy(update={"events": rules.events[:-2]})
    elif mutation == "not_final_rules_auth":
        # A second authorization after the captured producer invalidates finality.
        later = RulesProviderAuthorizedV1(
            event_id=uuid4(),
            sequence=len(rules.events),
            execution_id=rules.scope.execution_id,
            kind="provider_authorized",
            provider_attempt_id=uuid4(),
            request_envelope_sha256="c" * 64,
            matched_outputs=(),
            declared_support_refs=(),
        )
        rules = append(rules, later)
    with pytest.raises(ValueError):
        verify_native_output(graph, rules, proof, capture)


def test_native_proof_rejects_foreign_rules_scope_and_oversized_text():
    graph, rules, proof, capture, _, _ = native_case()
    foreign = proof.model_copy(update={"rules_execution_id": uuid4()})
    with pytest.raises(ValueError):
        verify_native_output(graph, rules, foreign, capture)
    oversized = changed(capture, text="x" * 262145)
    with pytest.raises(ValueError):
        NativeRulesOutputProofV1.from_capture(
            oversized,
            prepared_request_json=proof.prepared_request_json,
            rules_execution_id=rules.scope.execution_id,
            producing_provider_attempt_id=proof.producing_provider_attempt_id,
        )
