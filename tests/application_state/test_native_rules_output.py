"""APP joins native raw output to one exact final Graph+Rules producer."""

from types import SimpleNamespace
from hashlib import sha256
from uuid import uuid4
import json

import pytest

from application_state.agent_conversation.native_rules_output import (
    NativeRulesOutputProofV1,
    verify_native_output,
)
from application_state.agent_conversation.rules_authority_events import (
    RulesOutputRefV1,
    RulesProviderAuthorizedV1,
    RulesProviderIncludedV1,
    RulesProviderOutcomeV1,
)
from application_state.agent_conversation.types import ProviderOutcomeEventV1
from tests.test_rules_build_input import append, execution as native_rules_execution
from tests.test_rules_lookup_broker import args, lookup as rules_lookup
from tests.test_play_graph_authority import native_provider


def native_case():
    owner, lookup = rules_lookup(native_rules_execution())
    attempt = uuid4()
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
    owner = append(
        owner,
        RulesProviderOutcomeV1(
            event_id=uuid4(),
            sequence=len(owner.events),
            execution_id=owner.scope.execution_id,
            kind="provider_outcome",
            provider_attempt_id=attempt,
            request_envelope_sha256=request_sha,
            status="answered",
        ),
    )
    raw = json.dumps(
        {
            "schema": "dmb_rules_mixed_answer_v1",
            "base_output": None,
            "rules_segments": [
                {
                    "kind": "rules_claim",
                    "text": "The rule applies.",
                    "support_ids": [str(refs[0].support_id)],
                }
            ],
            "ordered_refs": [{"domain": "rules", "segment_index": 0}],
        }
    )
    graph_auth = native_provider().model_copy(
        update={
            "provider_attempt_id": attempt,
            "envelope_sha256": request_sha,
        }
    )
    graph = SimpleNamespace(
        events=[
            graph_auth,
            ProviderOutcomeEventV1(
                event_id=uuid4(),
                sequence=1,
                kind="provider_outcome",
                provider_attempt_id=attempt,
                outcome="response_received",
            ),
        ]
    )
    raw_bytes = raw.encode("utf-8")
    graph_auth = graph_auth.model_copy(update={"api_mode": "codex_responses"})
    graph.events[0] = graph_auth
    capture = SimpleNamespace(
        authorization_id="host:1",
        api_request_id="api-request-1",
        provider="synthetic",
        model="synthetic",
        api_mode="codex_responses",
        request_sha256=request_sha,
        status="answered",
        finish_reason="stop",
        text=raw,
        text_sha256=sha256(raw_bytes).hexdigest(),
        text_utf8_bytes=len(raw_bytes),
        tool_calls=(),
    )
    proof = NativeRulesOutputProofV1.from_capture(
        capture,
        prepared_request_json=prepared_request_json,
        rules_execution_id=owner.scope.execution_id,
        producing_provider_attempt_id=attempt,
    )
    return graph, owner, proof, capture, raw


def changed(value, **updates):
    return SimpleNamespace(**(vars(value) | updates))


def test_native_output_joins_actual_final_request_and_rules_supports():
    graph, rules, proof, capture, _ = native_case()
    answer = verify_native_output(graph, rules, proof, capture)
    assert answer.rules_segments[0].text == "The rule applies."
    assert answer.rules_segments[0].support_ids == tuple(
        str(item.support_id) for item in rules.events[-2].support_refs
    )


def test_native_output_rechecks_actual_rules_call_and_result_bytes():
    graph, rules, proof, capture, _ = native_case()
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
    graph, rules, proof, capture, raw = native_case()
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
    graph, rules, proof, capture, _ = native_case()
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
