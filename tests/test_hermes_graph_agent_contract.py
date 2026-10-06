from __future__ import annotations

from dataclasses import replace

import pytest

from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnRequest,
    decode_turn_request_wire,
    deserialize_hermes_graph_agent_turn_request,
    encode_turn_request_wire,
    serialize_hermes_graph_agent_turn_request,
)


def _budget() -> dict[str, object]:
    return {
        "schema": "dmb_hermes_request_budget_policy_v1",
        "provider": "openai-api",
        "model": "synthetic-model",
        "apiMode": "chat_completions",
        "estimator": "utf8_json_bytes_plus_64_per_node_v1",
        "contextLimitTokens": 32768,
        "outputReserveTokens": 2048,
    }


def _request(
    *, request_budget=None, provider_authorization_required=False,
    parent_graph_broker_required=False, retrieval_session_id=None,
    retrieval_session=None,
) -> HermesGraphAgentTurnRequest:
    return HermesGraphAgentTurnRequest(
        question="synthetic question",
        world_id="world-1",
        campaign_id="",
        scope_mode="world",
        request_budget=request_budget,
        provider_authorization_required=provider_authorization_required,
        parent_graph_broker_required=parent_graph_broker_required,
        retrieval_session_id=retrieval_session_id,
        retrieval_session=retrieval_session,
    )


def test_request_budget_policy_round_trips_strictly():
    payload = serialize_hermes_graph_agent_turn_request(
        _request(request_budget=_budget())
    )
    assert payload["requestBudget"] == _budget()

    restored = deserialize_hermes_graph_agent_turn_request(payload)
    assert restored.request_budget == _budget()


def test_legacy_request_omits_budget_field_byte_for_byte():
    payload = serialize_hermes_graph_agent_turn_request(_request())
    assert "requestBudget" not in payload
    assert "providerAuthorizationRequired" not in payload
    assert "parentGraphBrokerRequired" not in payload


def test_exact_committed_plan_message_survives_host_round_trip() -> None:
    markdown = "# Committed Plan\n" + "x" * 50_000
    message = markdown
    request = _request(request_budget=_budget())
    request = replace(request, question=message, plan_continuity_turn=True)
    payload = serialize_hermes_graph_agent_turn_request(request)
    assert payload["question"] == message
    assert deserialize_hermes_graph_agent_turn_request(payload).question == message
    assert decode_turn_request_wire(encode_turn_request_wire(request)).question == message

    with pytest.raises(ValueError, match="question"):
        serialize_hermes_graph_agent_turn_request(
            replace(request, plan_continuity_turn=False)
        )
    with pytest.raises(ValueError, match="question"):
        deserialize_hermes_graph_agent_turn_request(
            {**payload, "planContinuityTurn": False}
        )


def test_large_plan_reaches_offline_real_worker_provider_gate(
    tmp_path, monkeypatch
) -> None:
    import json

    from apps.live_control_server.services.agent_turn_service import (
        _json_node_count,
        _plan_message,
        _policy_request_budget,
    )
    from apps.live_control_server.services.hermes_graph_agent_host import (
        HermesGraphAgentHost,
    )
    from graph_memory.hermes_graph_plugin import (
        HermesGraphScope,
        parent_brokered_graph_expansion_policy,
    )
    from graph_memory.retrieval.models import WorldGraphRetrievalResult
    from tests.test_hermes_graph_agent_host import _tool_using_aiagent_host_worker

    witness = tmp_path / "offline-worker-witness.json"
    monkeypatch.setenv("DMB_HERMES_HOST_OFFLINE_WITNESS", str(witness))
    monkeypatch.setenv("DUNGEONMIND_HERMES_GRAPH_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-key")
    budget = _policy_request_budget()
    assert budget["contextLimitTokens"] == 1_050_000
    markdown = "# Committed Plan\n" + "x" * 50_000
    message = _plan_message("Where is Tripod?", markdown)
    scope = HermesGraphScope(
        world_id="world:eldyrwild",
        campaign_id="",
        focus={"kind": "none", "sessionId": None},
        admissibility="gm",
        revision_pin="revision:test",
        scope_mode="world",
    )
    request = HermesGraphAgentTurnRequest(
        question=message,
        world_id=scope.world_id,
        campaign_id="",
        scope_mode="world",
        focus=dict(scope.focus),
        admissibility="gm",
        revision_pin=scope.revision_pin,
        root=tmp_path / "graph",
        capability_policy=parent_brokered_graph_expansion_policy(scope),
        retrieval_session_id="sess:SPOOF",
        retrieval_session={
            "retrieval_session_id": "sess:SPOOF",
            "candidates": [],
            "claim_ledger": [],
            "intent_hint": None,
            "available_expansions": ["search"],
        },
        request_budget=budget,
        provider_authorization_required=True,
        parent_graph_broker_required=True,
        plan_continuity_turn=True,
    )
    authorized = []

    def authorize(view):
        authorized.append(view)
        assert "x" * 50_000 in view["payloadJson"]
        body = json.loads(view["payloadJson"])
        upper_bound = view["payloadUtf8Bytes"] + 64 * (1 + _json_node_count(body))
        assert upper_bound + budget["outputReserveTokens"] <= budget["contextLimitTokens"]
        return True

    def broker(_operation):
        result = WorldGraphRetrievalResult(
            operation="search", outcome="enough", matched_node_ids=[]
        )
        return {
            "resultJson": result.model_dump_json(by_alias=True),
            "retrievalSession": request.retrieval_session,
        }

    host = HermesGraphAgentHost(
        worker_target=_tool_using_aiagent_host_worker,
        turn_timeout_s=120.0,
        ready_timeout_s=90.0,
        accept_timeout_s=30.0,
        session_profiles_root=tmp_path / "profiles",
    )
    try:
        result = host.execute(
            request,
            on_provider_authorization=authorize,
            on_provider_lifecycle=lambda _event: True,
            on_graph_operation=broker,
        )
        assert result.status == "ok", (result.error_code, result.error_message)
    finally:
        host.shutdown()
    assert len(authorized) == 2
    offline = json.loads(witness.read_text(encoding="utf-8"))
    assert offline["network_attempts"] == []
    assert offline["responses_stub_calls"] == 2
    for view, body in zip(
        authorized, offline["provider_request_bodies"][0], strict=True
    ):
        assert json.loads(view["payloadJson"]) == body


def test_plan_sized_envelope_with_production_prompt_reaches_parent_gate(
    tmp_path, monkeypatch
) -> None:
    import json
    import socket

    from apps.live_control_server.services.agent_turn_service import (
        _json_node_count,
        _plan_message,
        _policy_request_budget,
    )
    from apps.live_control_server.services.hermes_graph_agent import (
        run_hermes_graph_agent_turn,
    )
    from graph_memory.hermes_graph_plugin import (
        HermesGraphScope,
        parent_brokered_graph_expansion_policy,
    )

    monkeypatch.setenv("DUNGEONMIND_HERMES_GRAPH_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-key")
    monkeypatch.setenv(
        "DMB_HERMES_GRAPH_AGENT_SESSION_PROFILES_ROOT", str(tmp_path / "profiles")
    )
    network_attempts = []

    def deny_network(*_args, **_kwargs):
        network_attempts.append(True)
        raise AssertionError("provider network must not be called")

    class Metadata:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": []}

    monkeypatch.setattr("requests.get", lambda *_args, **_kwargs: Metadata())
    monkeypatch.setattr(socket, "getaddrinfo", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket.socket, "connect", deny_network)
    scope = HermesGraphScope(
        world_id="world:eldyrwild", campaign_id="",
        focus={"kind": "none", "sessionId": None}, admissibility="gm",
        revision_pin="revision:test", scope_mode="world",
    )
    budget = _policy_request_budget()
    markdown = ('# Committed Plan\nA quoted "name".\n' * 1700)[:50_000]
    request = HermesGraphAgentTurnRequest(
        question=_plan_message("Where is Tripod?", markdown),
        world_id=scope.world_id, campaign_id="", scope_mode="world",
        focus=dict(scope.focus), admissibility="gm",
        revision_pin=scope.revision_pin, root=tmp_path / "graph",
        capability_policy=parent_brokered_graph_expansion_policy(scope),
        retrieval_session_id="sess:SPOOF",
        retrieval_session={
            "retrieval_session_id": "sess:SPOOF", "candidates": [],
            "claim_ledger": [], "intent_hint": None,
            "available_expansions": ["search"],
        },
        request_budget=budget, provider_authorization_required=True,
        parent_graph_broker_required=True, plan_continuity_turn=True,
    )
    observed = []

    def reject(view):
        body = json.loads(view.payload_json)
        upper_bound = view.payload_utf8_bytes + 64 * (1 + _json_node_count(body))
        observed.append((
            view.payload_sha256, view.payload_utf8_bytes, upper_bound,
            "committed_plan_markdown" in view.payload_json,
        ))
        return False

    result = run_hermes_graph_agent_turn(
        request, on_provider_authorization=reject,
        on_parent_graph_operation=lambda *_args: pytest.fail("provider gate not reached"),
    )
    assert result.status == "error"
    assert len(observed) == 1, (result.error_code, result.error_message)
    assert observed[0][2] + budget["outputReserveTokens"] <= budget["contextLimitTokens"]
    assert observed[0][3] is True
    assert network_attempts == []

    # An actually smaller provider window must still stop before the parent
    # permit or any SDK entry for the same production-shaped request.
    observed.clear()
    result = run_hermes_graph_agent_turn(
        replace(request, request_budget={**budget, "contextLimitTokens": 65_536}),
        on_provider_authorization=reject,
        on_parent_graph_operation=lambda *_args: pytest.fail("provider gate not reached"),
    )
    assert result.status == "error"
    assert result.error_code == "request_budget_exceeded"
    assert observed == []
    assert network_attempts == []


def test_provider_authorization_gate_is_opt_in_and_round_trips():
    legacy = serialize_hermes_graph_agent_turn_request(_request())
    assert "providerAuthorizationRequired" not in legacy

    request = _request(
        request_budget=_budget(), provider_authorization_required=True
    )
    payload = serialize_hermes_graph_agent_turn_request(request)
    assert payload["providerAuthorizationRequired"] is True
    restored = deserialize_hermes_graph_agent_turn_request(payload)
    assert restored.provider_authorization_required is True
    assert restored.request_budget == _budget()

    with pytest.raises(ValueError, match="explicit request budget"):
        serialize_hermes_graph_agent_turn_request(
            _request(provider_authorization_required=True)
        )


def test_parent_graph_broker_is_opt_in_and_requires_exact_retrieval_session():
    with pytest.raises(ValueError, match="retrieval session"):
        serialize_hermes_graph_agent_turn_request(
            _request(
                request_budget=_budget(),
                provider_authorization_required=True,
                parent_graph_broker_required=True,
            )
        )

    request = _request(
        request_budget=_budget(),
        provider_authorization_required=True,
        parent_graph_broker_required=True,
        retrieval_session_id="session-1",
        retrieval_session={"retrieval_session_id": "session-1"},
    )
    payload = serialize_hermes_graph_agent_turn_request(request)
    assert payload["parentGraphBrokerRequired"] is True
    restored = deserialize_hermes_graph_agent_turn_request(payload)
    assert restored.parent_graph_broker_required is True


@pytest.mark.parametrize(
    "mutate",
    [
        lambda policy: policy.update(schema="unknown"),
        lambda policy: policy.update(apiMode=""),
        lambda policy: policy.update(provider="openai"),
        lambda policy: policy.update(estimator="unknown"),
        lambda policy: policy.update(contextLimitTokens=True),
        lambda policy: policy.update(outputReserveTokens=32768),
        lambda policy: policy.update(unrecognized=True),
    ],
)
def test_invalid_request_budget_policy_is_rejected(mutate):
    policy = _budget()
    mutate(policy)
    with pytest.raises(ValueError):
        serialize_hermes_graph_agent_turn_request(_request(request_budget=policy))
