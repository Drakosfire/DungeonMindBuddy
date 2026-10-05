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


def _request(*, request_budget=None) -> HermesGraphAgentTurnRequest:
    return HermesGraphAgentTurnRequest(
        question="synthetic question",
        world_id="world-1",
        campaign_id="",
        scope_mode="world",
        request_budget=request_budget,
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
