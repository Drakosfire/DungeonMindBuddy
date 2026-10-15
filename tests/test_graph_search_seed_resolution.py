"""Empty discovery searches must not be saturated by preflight context."""

import json
from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter
from apps.live_control_server.services.hermes_graph_interaction_tools import (
    execute_hermes_graph_interaction_tool_json,
)
from graph_memory.interaction.expansion_executor import (
    ExpandGraphRetrievalRequest,
    resolve_expansion_target_ids,
)
from tests import test_agent_mounted_graph_expansion as mounted_fixtures

mounted = mounted_fixtures.mounted

PREFLIGHT = [f"node:preflight-{i}" for i in range(8)]


def request(operation="search", targets=None):
    return ExpandGraphRetrievalRequest.model_validate(
        {
            "retrievalSessionId": "session:one",
            "operation": operation,
            "queryText": "keeper concerns",
            "targets": targets or [],
        }
    )


@pytest.mark.parametrize("selected", [[], ["node:selected"]])
@pytest.mark.parametrize("explicit", [[], [{"kind": "node", "id": "node:keeper"}]])
def test_search_uses_only_explicit_seeds(selected, explicit):
    session = SimpleNamespace(
        selected_referent_ids=lambda: selected, preflight_candidate_ids=PREFLIGHT
    )
    assert resolve_expansion_target_ids(request(targets=explicit), session) == [
        row["id"] for row in explicit
    ]


@pytest.mark.parametrize("operation", ["object", "neighborhood", "support"])
@pytest.mark.parametrize("selected", [[], ["node:selected"]])
def test_non_search_target_fallback_is_preserved(operation, selected):
    session = SimpleNamespace(
        selected_referent_ids=lambda: selected, preflight_candidate_ids=PREFLIGHT
    )
    assert resolve_expansion_target_ids(request(operation), session) == (
        selected or PREFLIGHT
    )
    explicit = [{"kind": "node", "id": "node:keeper"}]
    assert resolve_expansion_target_ids(request(operation, explicit), session) == [
        "node:keeper"
    ]


@pytest.mark.parametrize("explicit", [[], [{"kind": "node", "id": "node:keeper"}]])
def test_direct_native_search_receives_exact_empty_or_explicit_seeds(
    mounted, monkeypatch, explicit
):
    mounted.session.preflight_candidate_ids = list(PREFLIGHT)
    calls = []

    def native_search(services, native):
        assert services is mounted.services
        calls.append(native)
        return SimpleNamespace(
            model_dump=lambda **_: {
                "schema": "dmb_world_graph_retrieval_result_v1",
                "outcome": "empty",
                "nodes": [],
                "relationships": [],
                "attributes": [],
                "sourceAnchors": [],
                "diagnostics": [],
            }
        )

    monkeypatch.setattr(direct, "search_world_graph_direct", native_search)
    raw = execute_hermes_graph_interaction_tool_json(
        "expand_graph_retrieval",
        {
            "retrievalSessionId": mounted.session.id,
            "operation": "search",
            "queryText": "keeper concerns",
            "targets": explicit,
        },
        root=mounted.code,
    )
    assert json.loads(raw)["outcome"] == "empty"
    assert len(calls) == 1
    assert calls[0].seed_node_ids == [row["id"] for row in explicit]
    assert calls[0].revision_pin == "rev:frozen" and calls[0].world_id == "native:world"
    assert mounted.session.operations[-1].inputs["effective_targets"] == explicit


@pytest.mark.parametrize("selected", [[], ["node:selected"]])
@pytest.mark.parametrize("explicit", [[], [{"kind": "node", "id": "node:keeper"}]])
def test_parent_native_search_receives_exact_empty_or_explicit_seeds(
    monkeypatch, selected, explicit
):
    """Exercise parent request dispatch; stop before unrelated APP persistence."""
    session = SimpleNamespace(
        id="session:one",
        selected_referent_ids=lambda: selected,
        preflight_candidate_ids=PREFLIGHT,
    )
    execution = SimpleNamespace(
        events=[], policy=SimpleNamespace(max_graph_operations=8)
    )
    adapter = object.__new__(_PolicyExecutionAdapter)
    adapter.fence = SimpleNamespace(
        turn=SimpleNamespace(graph_context_execution=execution)
    )
    adapter.last_provider_attempt_id = "authorized:one"
    adapter.bootstrap = SimpleNamespace(
        retrieval_session=session,
        world_scope=SimpleNamespace(world_id="native:world", revision_id="rev:frozen"),
    )
    adapter._denied_tool_result = lambda *args, **kwargs: {
        "test_stopped_at_native_boundary": True
    }
    services = object()
    calls = []
    monkeypatch.setattr(
        direct,
        "direct_services_from_config",
        lambda world: (
            services if world == "native:world" else pytest.fail("foreign world")
        ),
    )

    def native_search(selected_services, native):
        assert selected_services is services
        calls.append(native)
        raise RuntimeError("test stops after observing the native request")

    monkeypatch.setattr(direct, "search_world_graph_direct", native_search)
    adapter.broker_graph_operation(
        {
            "toolName": "expand_graph_retrieval",
            "arguments": {
                "retrievalSessionId": session.id,
                "operation": "search",
                "queryText": "keeper concerns",
                "targets": explicit,
                "worldId": "forged",
                "revisionPin": "forged",
            },
        }
    )
    assert len(calls) == 1
    assert calls[0].seed_node_ids == [row["id"] for row in explicit]
    assert calls[0].revision_pin == "rev:frozen" and calls[0].world_id == "native:world"
    assert execution.events == []
