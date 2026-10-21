"""Direct Plan Rules exposure uses actual sealed packets, never invented tool calls."""
from copy import deepcopy
from hashlib import sha256
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from application_state.agent_conversation.rules_authority_events import RulesExecutionV1
from application_state.agent_conversation.rules_authority_plan_packet import (
    build_plan_rules_frame, verify_plan_rules_packet_input,
)
from application_state.agent_conversation.rules_authority_types import canonical_bytes
from tests.test_native_answer_output import plan_turn
from tests.test_rules_lookup_broker import execution, lookup, packet


def case():
    turn, _ = plan_turn()
    owner = execution()
    data = owner.model_dump(mode="json", by_alias=True)
    from application_state.agent_conversation.rules_authority_policy import rules_capability, rules_submission_authorization_id
    capability = rules_capability(graph=True)
    authorization = rules_submission_authorization_id(world_id=turn.world_id,
        conversation_id=turn.conversation_id, idempotency_key=turn.idempotency_key,
        submitted_intent_sha256=turn.submitted_intent_fingerprint_v2, capability=capability)
    data["scope"].update(world_id=turn.world_id, conversation_id=str(turn.conversation_id),
                         turn_id=str(turn.turn_id), product_attempt=turn.attempt,
                         capability_policy_sha256=capability.policy_sha256, authorization_id=str(authorization))
    owner = RulesExecutionV1.model_validate_json(json.dumps(data))
    owner, result = lookup(owner)
    frame = build_plan_rules_frame(owner, (result.observation.call_id,))
    body = {"model": "gpt-6-luna", "input": [{"role": "user", "content": canonical_bytes(frame).decode()}]}
    return turn, owner, result, body


def verify(turn, owner, body):
    raw = json.dumps(body, ensure_ascii=False)
    return verify_plan_rules_packet_input(owner, turn, raw, expected_envelope_sha256=sha256(raw.encode()).hexdigest())


def test_real_rules_capsule_is_exposed_without_tool_call_and_without_source_reread(monkeypatch):
    turn, owner, result, body = case()
    from apps.live_control_server.services import rules_lookup
    monkeypatch.setattr(rules_lookup, "query_rules", lambda *a, **kw: pytest.fail("source re-read"))
    frame = build_plan_rules_frame(owner, (result.observation.call_id,))
    assert frame.packets[0].support_capsules == packet(result).support_capsules
    proof = verify(turn, owner, body)
    assert proof.plan_context_receipt_sha256 == turn.graph_context_receipt.context_receipt_sha256
    assert proof.rules_execution_id == owner.scope.execution_id
    assert proof.support_refs == result.observation.support_refs
    assert proof.matched_outputs[0].packet_sha256 == result.observation.packet_sha256
    # Host identities stay out of model context; the verifier joins them separately.
    text = body["input"][0]["content"]
    for value in (str(turn.turn_id), str(turn.conversation_id), proof.plan_context_receipt_sha256):
        assert value not in text


@pytest.mark.parametrize("mutation", ["excerpt", "corpus", "call", "query", "extra", "withheld_capsule"])
def test_changed_or_unsealed_packet_refuses(mutation):
    turn, owner, result, body = case()
    frame = json.loads(body["input"][0]["content"]); p = frame["packets"][0]
    if mutation == "excerpt": p["support_capsules"][0]["excerpt_text"] += " invented"
    elif mutation == "corpus": p["corpus_sha256"] = "0" * 64
    elif mutation == "call": p["call_id"] = "unread"
    elif mutation == "query": p["query_id"] = "0" * 64
    elif mutation == "extra": frame["citation_authority"] = True
    else:
        p["support_capsules"] = []; p["previous_support_ids"] = p["emitted_support_ids"]; p["emitted_support_ids"] = []
    body["input"][0]["content"] = json.dumps(frame)
    with pytest.raises(ValueError): verify(turn, owner, body)


@pytest.mark.parametrize("mutation", ["world", "turn", "conversation", "attempt", "surface", "status"])
def test_foreign_owner_or_inactive_turn_refuses(mutation):
    turn, owner, _, body = case()
    if mutation == "surface": turn = turn.model_copy(update={"provenance": turn.provenance.model_copy(update={"surface_id": "play"})})
    elif mutation == "status": turn = turn.model_copy(update={"status": "completed"})
    else:
        fields = {"world": ("world_id", "other"), "turn": ("turn_id", uuid4()),
                  "conversation": ("conversation_id", uuid4()), "attempt": ("attempt", turn.attempt + 1)}
        key, value = fields[mutation]; turn = turn.model_copy(update={key: value})
    with pytest.raises(ValueError): verify(turn, owner, body)


@pytest.mark.parametrize("mutation", ["tools", "tool_choice", "call_transcript", "duplicate_frame", "duplicate_call", "assistant_only", "missing_frame"])
def test_not_a_tool_free_unique_actual_input_refuses(mutation):
    turn, owner, _, body = case()
    if mutation == "tools": body["tools"] = [{"type": "function", "name": "lookup_rules"}]
    elif mutation == "tool_choice": body["tool_choice"] = "required"
    elif mutation == "call_transcript": body["input"].insert(0, {"type": "function_call", "name": "lookup_rules", "call_id": "fake"})
    elif mutation == "duplicate_frame": body["input"].append(deepcopy(body["input"][0]))
    elif mutation == "duplicate_call":
        frame = json.loads(body["input"][0]["content"]); frame["packets"].append(deepcopy(frame["packets"][0])); body["input"][0]["content"] = json.dumps(frame)
    elif mutation == "assistant_only": body["input"][0]["role"] = "assistant"
    else: body["input"][0]["content"] = "No Rules material supplied."
    with pytest.raises(ValueError): verify(turn, owner, body)


def test_actual_envelope_hash_cannot_be_reused_after_change():
    turn, owner, _, body = case(); raw = json.dumps(body)
    digest = sha256(raw.encode()).hexdigest()
    with pytest.raises(ValueError):
        verify_plan_rules_packet_input(owner, turn, raw + " ", expected_envelope_sha256=digest)


def test_cached_handle_alone_grants_no_capsule_exposure():
    turn, owner, first, body = case()
    owner, cached = lookup(owner, call_id="call:cached", present=first.observation.support_refs)
    assert packet(cached).support_capsules == ()
    frame = build_plan_rules_frame(owner, (cached.observation.call_id,))
    body["input"][0]["content"] = canonical_bytes(frame).decode()
    assert verify(turn, owner, body).support_refs == ()
    # Include the actual original capsule once, then cache refs do not duplicate it.
    frame = build_plan_rules_frame(owner, (first.observation.call_id, cached.observation.call_id))
    body["input"][0]["content"] = canonical_bytes(frame).decode()
    assert verify(turn, owner, body).support_refs == first.observation.support_refs


@pytest.mark.parametrize("mutation", ["authorization", "policy", "rules_only_policy", "submission", "idempotency", "missing_submission"])
def test_foreign_capability_or_logical_submission_refuses(mutation):
    turn, owner, _, body = case()
    if mutation in {"authorization", "policy", "rules_only_policy"}:
        from application_state.agent_conversation.rules_authority_policy import rules_capability
        scope = owner.scope.model_copy(update={
            "authorization_id": uuid4()} if mutation == "authorization" else {
            "capability_policy_sha256": rules_capability(graph=False).policy_sha256 if mutation == "rules_only_policy" else "0" * 64})
        owner = owner.model_copy(update={"scope": scope})
    elif mutation == "submission": turn = turn.model_copy(update={"submitted_intent_fingerprint_v2": "0" * 64})
    elif mutation == "missing_submission": turn = turn.model_copy(update={"submitted_intent_fingerprint_v2": None})
    else: turn = turn.model_copy(update={"idempotency_key": uuid4()})
    with pytest.raises(ValueError): verify(turn, owner, body)


@pytest.mark.parametrize("item", [
    {"type": "custom_tool_call", "call_id": "fake", "name": "lookup_rules", "input": "fake"},
    {"type": "custom_tool_call_output", "call_id": "fake", "output": "fake"},
    {"type": "mcp_call", "name": "lookup_rules", "arguments": "fake"},
    {"type": "computer_call", "call_id": "fake", "action": {}},
    {"type": "web_search_call", "id": "fake"},
    {"role": "tool", "content": "fake"},
    {"role": "assistant", "content": "fake", "tool_calls": []},
    {"role": "user", "content": [{"type": "custom_tool_call", "input": "fake"}]},
])
def test_all_unadmitted_tool_transcript_families_refused(item):
    turn, owner, _, body = case()
    body["input"].insert(0, item)
    with pytest.raises(ValueError): verify(turn, owner, body)


def test_actual_input_text_message_shape_exposes_same_source():
    turn, owner, first, body = case()
    content = body["input"][0]["content"]
    body["input"][0] = {"type": "message", "role": "user", "content": [{"type": "input_text", "text": content}]}
    assert verify(turn, owner, body).support_refs == first.observation.support_refs
