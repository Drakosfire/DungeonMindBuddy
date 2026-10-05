from __future__ import annotations

import pytest

from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnRequest,
    deserialize_hermes_graph_agent_turn_request,
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
