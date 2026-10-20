"""Explicit Rules authority across policy, plugin and actual IPC/runtime mapping."""
from dataclasses import replace
import json

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.rules_authority_policy import (
    CORPUS, RULESET, LOOKUP_RULES, RulesCapabilityV1, LookupRulesArguments, rules_capability, rules_tool_definition,
)
from apps.live_control_server.services.agent_runtime import AgentCapabilityPolicy, AgentContextPacket
from apps.live_control_server.services.hermes_agent_runtime import HermesAgentRuntimeAdapter, map_invocation_to_hermes_request
from apps.live_control_server.services.hermes_graph_agent_contract import (
    serialize_capability_policy, deserialize_capability_policy,
    serialize_hermes_graph_agent_turn_request, deserialize_hermes_graph_agent_turn_request,
    HermesGraphAgentTurnResult,
)
from apps.live_control_server.services.hermes_graph_agent_host import _rules_operation_permitted
from apps.live_control_server.services.hermes_graph_agent import _build_ephemeral_system_prompt
from graph_memory import hermes_graph_plugin as plugin
from tests.test_hermes_agent_runtime import _invocation
from tests.test_hermes_graph_agent_contract import _budget


def invocation(graph=False):
    base = _invocation()
    capability = rules_capability(graph=graph)
    packet = replace(base.context_packet, rules_capability=capability) if graph else AgentContextPacket(
        world_scope=None, rules_capability=capability)
    return replace(base, message="Can I end my move in an occupied space?", context_packet=packet,
        capability_policy=AgentCapabilityPolicy(policy_id=capability.policy_id))


def guarded_request(graph=False):
    request = map_invocation_to_hermes_request(invocation(graph))
    return replace(request, provider_authorization_required=True, parent_graph_broker_required=True,
        request_budget=_budget())


@pytest.mark.parametrize("graph", [False, True])
def test_capability_metadata_has_fixed_source_tool_hash_and_no_claim_authority(graph):
    cap = rules_capability(graph=graph)
    wire = cap.model_dump(mode="json", by_alias=True)
    assert cap.corpus_sha256 == CORPUS and cap.ruleset_id == RULESET
    assert len(cap.policy_sha256) == 64 and "execution_id" not in wire and "world_id" not in wire
    assert RulesCapabilityV1.model_validate_json(json.dumps(wire)) == cap
    wire["tool_contract_sha256"] = "a" * 64
    with pytest.raises(ValidationError):
        RulesCapabilityV1.model_validate_json(json.dumps(wire))


@pytest.mark.parametrize("graph", [False, True])
def test_explicit_policy_and_request_round_trip_separate_both_domains(graph):
    request = guarded_request(graph)
    policy = request.capability_policy
    assert plugin.validate_capability_policy_structure(policy) is None
    decoded = deserialize_capability_policy(serialize_capability_policy(policy))
    assert decoded == policy
    roundtrip = deserialize_hermes_graph_agent_turn_request(serialize_hermes_graph_agent_turn_request(request))
    assert roundtrip.capability_policy == policy
    assert (roundtrip.world_id is not None) is graph
    assert (roundtrip.retrieval_session_id is not None) is graph
    assert (policy.graph_scope is not None) is graph
    assert LOOKUP_RULES in policy.enabled_tool_names
    rule = policy.rule_for(LOOKUP_RULES)
    assert rule.require_rules_authority and not rule.require_graph_scope and rule.allowed_effects == frozenset({"read"})
    if not graph:
        assert policy.enabled_tool_names == (LOOKUP_RULES,)
        prompt = _build_ephemeral_system_prompt(policy, request, retrieval_session_packet=None)
        assert "occupancy section" in prompt and "Turn capability policy" not in prompt


@pytest.mark.parametrize("graph", [False, True])
def test_unguarded_rules_request_is_rejected_before_host_creation(graph):
    adapter = HermesAgentRuntimeAdapter(host_factory=lambda: pytest.fail("unguarded Rules constructed host"))
    result = adapter.run(invocation(graph))
    assert result.status == "error" and result.error_code == "rules_parent_authorization_required"
    request = map_invocation_to_hermes_request(invocation(graph))
    with pytest.raises(ValueError, match="authorization"):
        serialize_hermes_graph_agent_turn_request(request)


@pytest.mark.parametrize("graph", [False, True])
def test_guarded_runtime_advertises_exact_independently_admitted_tools(graph):
    captured = []
    class Host:
        worker_pid = 1
        def execute(self, request, **kwargs):
            captured.append(request)
            assert callable(kwargs["on_provider_authorization"]) and callable(kwargs["on_graph_operation"])
            serialize_hermes_graph_agent_turn_request(request)
            return HermesGraphAgentTurnResult(status="error", final_response=None, messages=[], hermes_session_id=None,
                tool_events=[], answer_scope=None, error_code="provider_authorization_denied")
    adapter = HermesAgentRuntimeAdapter(host_factory=Host)
    adapter.run_with_provider_authorization(invocation(graph), lambda _: False, request_budget=_budget(),
        on_graph_operation=lambda _: {}, source_read_enabled=graph)
    request = captured[0]
    assert request.capability_policy.enabled_tool_names == (("expand_graph_retrieval", "read_graph_source", LOOKUP_RULES) if graph else (LOOKUP_RULES,))
    assert _rules_operation_permitted(request, LOOKUP_RULES)
    assert _rules_operation_permitted(request, "expand_graph_retrieval") is graph


def test_conversation_only_stays_empty_and_cannot_carry_rules_metadata():
    plain = plugin.default_conversation_only_capability_policy()
    assert plain.enabled_tool_names == () and plugin.validate_capability_policy_structure(plain) is None
    bad = replace(plain, rules_capability=rules_capability(graph=False))
    assert plugin.validate_capability_policy_structure(bad) == "hermes_conversation_policy_has_capabilities"
    with pytest.raises(ValueError):
        serialize_capability_policy(bad)


@pytest.mark.parametrize("mutate", [
    lambda wire: wire.pop("mode"),
    lambda wire: wire.update(mode="unknown"),
    lambda wire: wire.update(rulesCapability=None),
    lambda wire: wire["rulesCapability"].update(corpus_sha256="a" * 64),
    lambda wire: wire["rulesCapability"].update(input_proof_policies=["opaque_json"]),
    lambda wire: wire["rulesCapability"].pop("output_proof_policy"),
    lambda wire: wire["rulesCapability"].update(output_proof_policy="plaintext"),
    lambda wire: wire["toolRules"][0].update(requireRulesAuthority=False),
    lambda wire: wire["toolRules"][0].update(requireRulesAuthority="yes"),
    lambda wire: wire["toolRules"][0].update(requireGraphScope=True),
    lambda wire: wire["toolRules"][0].update(allowedEffects=["write"]),
    lambda wire: wire.update(graphScope={}),
])
def test_unknown_stale_or_forged_policy_forms_fail_closed(mutate):
    wire = serialize_capability_policy(guarded_request().capability_policy)
    mutate(wire)
    with pytest.raises(ValueError):
        deserialize_capability_policy(wire)


def test_rules_only_cannot_acquire_a_retrieval_session_or_graph_source_profile():
    request = guarded_request()
    with pytest.raises(ValueError, match="graph scope or retrieval"):
        serialize_hermes_graph_agent_turn_request(replace(request, retrieval_session_id="foreign"))
    adapter = HermesAgentRuntimeAdapter(host_factory=lambda: pytest.fail("foreign source profile constructed host"))
    with pytest.raises(ValueError, match="Graph source"):
        adapter.run_with_provider_authorization(invocation(), lambda _: False, request_budget=_budget(),
            on_graph_operation=lambda _: {}, source_read_enabled=True)


def test_plugin_requires_parent_broker_and_never_executes_a_local_fallback(monkeypatch):
    policy = guarded_request().capability_policy
    token = plugin.set_active_capability_policy(policy)
    plugin.set_active_rules_call_id("call:1")
    monkeypatch.setattr(plugin, "execute_hermes_graph_interaction_tool_json", lambda *a, **kw: pytest.fail("Rules used Graph fallback"))
    broker_token = plugin.set_parent_graph_broker(None, required=False)
    try:
        raw = plugin._handler_for(LOOKUP_RULES)({"question": "occupancy", "ruleset_id": RULESET})
        assert json.loads(raw)["code"] == "rules_broker_unavailable"
    finally:
        plugin.reset_parent_graph_broker(broker_token)
    calls = []
    def broker(name, arguments):
        calls.append((name, arguments))
        from tests.test_rules_lookup_broker import execution, lookup
        _, prepared = lookup(execution(), arguments=LookupRulesArguments(question="occupancy", ruleset_id=RULESET))
        return prepared.raw_output, None
    broker_token = plugin.set_parent_graph_broker(broker, required=True)
    try:
        assert json.loads(plugin._handler_for(LOOKUP_RULES)({"question": "occupancy", "ruleset_id": RULESET}))["schema"] == "dmb_rules_packet_v1"
        assert calls == [(LOOKUP_RULES, {"question": "occupancy", "ruleset_id": RULESET})]
        raw = plugin._handler_for(LOOKUP_RULES)({"question": "occupancy", "ruleset_id": RULESET, "worldId": "forged"})
        assert json.loads(raw)["code"] == "rules_arguments_invalid" and len(calls) == 1
    finally:
        plugin.reset_parent_graph_broker(broker_token)
        plugin.reset_active_capability_policy(token)
        plugin.set_active_rules_call_id(None)


def test_plugin_registration_uses_current_shared_tool_schema_only_when_admitted():
    class Registry:
        def __init__(self): self.tools = {}
        def register_tool(self, **kw): self.tools[kw["name"]] = kw
    registry = Registry()
    token = plugin.set_active_capability_policy(guarded_request().capability_policy)
    try:
        plugin.register(registry)
    finally:
        plugin.reset_active_capability_policy(token)
    assert registry.tools[LOOKUP_RULES]["schema"] == rules_tool_definition()["function"]
    plain = Registry()
    token = plugin.set_active_capability_policy(plugin.default_conversation_only_capability_policy())
    try:
        plugin.register(plain)
    finally:
        plugin.reset_active_capability_policy(token)
    assert LOOKUP_RULES not in plain.tools


@pytest.mark.parametrize("graph", [False, True])
def test_real_offline_worker_calls_rules_through_parent_channel_without_network(tmp_path, monkeypatch, graph):
    """Real Hermes/AIAgent with offline provider stub, not final APP authority."""
    from apps.live_control_server.services.hermes_graph_agent_host import HermesGraphAgentHost
    from tests.test_hermes_graph_agent_host import _tool_using_aiagent_host_worker
    from tests.test_rules_lookup_broker import execution, lookup
    witness = tmp_path / "rules-worker-witness.json"
    monkeypatch.setenv("DMB_HERMES_HOST_OFFLINE_WITNESS", str(witness))
    monkeypatch.setenv("DMB_HERMES_TEST_RULES_LOOKUP", "1")
    monkeypatch.setenv("DUNGEONMIND_HERMES_GRAPH_MODEL", "synthetic-model")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-key")
    monkeypatch.setenv("DMB_HERMES_TEST_FINAL_TEXT", "Fixture Rules response.")
    # This is a transport witness; durable admission/acceptance has separate
    # owning PostgreSQL tests and must be wired by the product parent later.
    _, prepared = lookup(execution(), call_id="call-graph-1")
    budget = {**_budget(), "apiMode": "codex_responses"}
    request = replace(guarded_request(graph), root=tmp_path / "graph", request_budget=budget)
    operations, authorizations = [], []
    def broker(message):
        operations.append(message)
        assert message["toolName"] == LOOKUP_RULES
        assert message["modelCallId"] == "call-graph-1"
        assert message["arguments"] == {"question": "Can I end my move in an occupied space?", "ruleset_id": RULESET}
        return {"resultJson": prepared.raw_output, "retrievalSession": None}
    host = HermesGraphAgentHost(worker_target=_tool_using_aiagent_host_worker,
        turn_timeout_s=45, ready_timeout_s=30, accept_timeout_s=10, session_profiles_root=tmp_path / "profiles")
    try:
        result = host.execute(request,
            on_provider_authorization=lambda view: authorizations.append(view) or True,
            on_provider_lifecycle=lambda _: True, on_graph_operation=broker)
        assert result.status == "ok", (result.error_code, result.error_message)
        assert result.final_response == "Fixture Rules response."
        if not graph:
            assert result.answer_scope != "graph"
            assert all(event.world_id is None for event in result.tool_events)
    finally:
        host.shutdown()
    assert len(operations) == 1 and len(authorizations) == 2
    bodies = [json.loads(view["payloadJson"]) for view in authorizations]
    names = [t.get("name", t.get("function", {}).get("name")) for t in bodies[0]["tools"]]
    assert LOOKUP_RULES in names
    actual_tool = next(tool for tool in bodies[0]["tools"] if tool.get("name", tool.get("function", {}).get("name")) == LOOKUP_RULES)
    actual_function = actual_tool.get("function", actual_tool)
    assert actual_function["parameters"] == rules_tool_definition()["function"]["parameters"]
    assert actual_function["description"] == rules_tool_definition()["function"]["description"]
    if not graph:
        assert names == [LOOKUP_RULES]
        assert request.retrieval_session is None and request.world_id is None
    outputs = [item for item in bodies[1]["input"] if isinstance(item, dict) and item.get("type") == "function_call_output"]
    assert len(outputs) == 1 and outputs[0]["output"] == prepared.raw_output
    evidence = json.loads(witness.read_text())
    assert evidence["network_attempts"] == []


def test_rules_and_graph_retire_independently_without_shared_read_counters():
    from types import SimpleNamespace
    from apps.live_control_server.services.hermes_graph_agent import _GraphOperationReservation
    from tests.test_rules_lookup_broker import execution, lookup
    _, prepared = lookup(execution())
    calls = []
    def broker(name, arguments):
        calls.append((name, arguments))
        return prepared.raw_output, None
    reservation = _GraphOperationReservation(1, broker, source_limit=1, context_limit=1,
        rules_limit=6, rules_question_limit=4)
    agent = SimpleNamespace(tools=[{"type": "function", "name": "expand_graph_retrieval"}, {"type": "function", "name": LOOKUP_RULES}])
    reservation.agents.append(agent)
    for _ in range(6):
        reservation(LOOKUP_RULES, {"question": "occupied space?", "ruleset_id": RULESET})
    assert reservation.count == reservation.source_count == reservation.context_count == 0
    assert reservation.rules_count == 6 and len(calls) == 6
    assert agent.tools == [{"type": "function", "name": "expand_graph_retrieval"}]
    with pytest.raises(ValueError, match="retired"):
        reservation(LOOKUP_RULES, {"question": "occupied space?", "ruleset_id": RULESET})
    assert len(calls) == 6
    agent.tools.append({"type": "function", "function": {"name": LOOKUP_RULES}})
    reservation._retire_tools()
    assert agent.tools == [{"type": "function", "function": {"name": LOOKUP_RULES}}]


def test_missing_actual_model_call_id_never_reaches_parent_broker():
    token = plugin.set_active_capability_policy(guarded_request().capability_policy)
    plugin.set_active_rules_call_id(None)
    broker_token = plugin.set_parent_graph_broker(lambda *a: pytest.fail("missing call ID reached parent"), required=True)
    try:
        result = json.loads(plugin._handler_for(LOOKUP_RULES)({"question": "occupied space?", "ruleset_id": RULESET}))
        assert result["code"] == "rules_call_identity_required"
    finally:
        plugin.reset_parent_graph_broker(broker_token)
        plugin.reset_active_capability_policy(token)


def test_rules_capability_agrees_with_actual_admitted_r1_source():
    from apps.live_control_server.services import rules_lookup
    bundle = rules_lookup.admitted_bundle(CORPUS)
    assert rules_lookup.SEED_DIGEST == CORPUS and bundle.ruleset_id == RULESET


def test_real_offline_two_lookup_batch_preserves_distinct_call_ids_and_one_excerpt(tmp_path, monkeypatch):
    from uuid import uuid4
    from hashlib import sha256
    from apps.live_control_server.services.hermes_graph_agent_host import HermesGraphAgentHost
    from tests.test_hermes_graph_agent_host import _tool_using_aiagent_host_worker
    from tests.test_rules_lookup_broker import execution, lookup
    from apps.live_control_server.services import rules_lookup as reader
    from application_state.agent_conversation.rules_authority_events import RulesProviderAuthorizedV1, RulesOutputRefV1
    from application_state.agent_conversation.rules_authority_input import verify_prepared_input
    reads = []
    actual = reader.query_rules
    def read(*a, **kw):
        reads.append(1)
        return actual(*a, **kw)
    monkeypatch.setattr(reader, "query_rules", read)
    owner, first = lookup(execution(), call_id="call-graph-1")
    owner, second = lookup(owner, call_id="call-rules-2", present=first.observation.support_refs)
    assert reads == [1] and second.observation.emitted_support_ids == ()
    results = {r.observation.call_id: r for r in (first, second)}
    witness = tmp_path / "two-rules-witness.json"
    monkeypatch.setenv("DMB_HERMES_HOST_OFFLINE_WITNESS", str(witness))
    monkeypatch.setenv("DMB_HERMES_TEST_RULES_LOOKUP", "1")
    monkeypatch.setenv("DMB_HERMES_TEST_RULES_LOOKUPS", "2")
    monkeypatch.setenv("DUNGEONMIND_HERMES_GRAPH_MODEL", "synthetic-model")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-key")
    request = replace(guarded_request(), root=tmp_path / "graph", request_budget={**_budget(), "apiMode": "codex_responses"})
    observed, authorized = [], []
    def broker(message):
        observed.append(message["modelCallId"])
        return {"resultJson": results[message["modelCallId"]].raw_output, "retrievalSession": None}
    host = HermesGraphAgentHost(worker_target=_tool_using_aiagent_host_worker, turn_timeout_s=45,
        ready_timeout_s=30, accept_timeout_s=10, session_profiles_root=tmp_path / "profiles")
    try:
        result = host.execute(request, on_provider_authorization=lambda view: authorized.append(view) or True,
            on_provider_lifecycle=lambda _: True, on_graph_operation=broker)
        assert result.status == "ok", (result.error_code, result.error_message)
    finally:
        host.shutdown()
    assert observed == ["call-graph-1", "call-rules-2"] and len(authorized) == 2
    final = authorized[-1]["payloadJson"]
    event = RulesProviderAuthorizedV1(kind="provider_authorized", event_id=uuid4(), sequence=len(owner.events),
        execution_id=owner.scope.execution_id, provider_attempt_id=uuid4(),
        request_envelope_sha256=sha256(final.encode()).hexdigest(),
        matched_outputs=tuple(RulesOutputRefV1(call_id=r.observation.call_id, packet_sha256=r.observation.packet_sha256) for r in (first, second)),
        declared_support_refs=first.observation.support_refs)
    verify_prepared_input(owner, event, final)
    outputs = [i for i in json.loads(final)["input"] if isinstance(i, dict) and i.get("type") == "function_call_output"]
    assert len(outputs) == 2
    assert sum(len(json.loads(i["output"])["support_capsules"]) for i in outputs) == 1
    assert json.loads(witness.read_text())["network_attempts"] == []
