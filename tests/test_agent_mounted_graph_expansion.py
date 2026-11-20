"""Harness code/source paths must not select a retired Graph file store."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from apps.live_control_server.config import (
    WorldGraphAuthorityConfigurationError,
    require_mounted_dungeonmind_world_graph,
)
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.services.hermes_graph_interaction_tools import (
    execute_hermes_graph_interaction_tool_json,
)
from graph_memory.interaction.session import (
    GraphRetrievalSession, SessionSnapshot, SourceAnchorState,
)
from graph_memory.interaction.session_store import clear_sessions, create_session


@pytest.fixture
def mounted(monkeypatch, tmp_path):
    clear_sessions()
    code = tmp_path / "code"
    artifacts = tmp_path / "artifacts"
    graph = tmp_path / "graph"
    for path in (code, artifacts, graph):
        path.mkdir()
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY", "dungeonmind")
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(graph))
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(artifacts))
    session = create_session(GraphRetrievalSession(
        snapshot=SessionSnapshot(world_id="native:world", campaign_id="",
            revision_id="rev:frozen", scope_mode="world"),
        question="How are the council concerns connected?",
        source_anchors=[SourceAnchorState(anchor_id="anchor:source", readable=True)],
    ))
    services = object()
    def resolve(world_id):
        assert world_id == "native:world"
        return services
    monkeypatch.setattr(direct, "direct_services_from_config", resolve)
    yield SimpleNamespace(code=code, artifacts=artifacts, graph=graph,
        session=session, services=services)
    clear_sessions()


@pytest.mark.parametrize(("operation", "adapter"), [
    ("search", "search_world_graph_direct"),
    ("object", "get_object_with_reviewed_sources_direct"),
    ("neighborhood", "get_neighborhood_direct"),
    ("support", "get_evidence_direct"),
])
def test_harness_expands_mounted_graph_with_distinct_code_root(mounted, monkeypatch, operation, adapter):
    calls = []
    def native_read(services, request):
        assert services is mounted.services
        assert request.world_id == "native:world"
        assert request.revision_pin == "rev:frozen"
        assert request.scope_mode == "world"
        calls.append(request)
        view = SimpleNamespace(model_dump=lambda **_: {
            "schema": "dmb_world_graph_retrieval_result_v1", "outcome": "enough",
            "nodes": [], "sourceAnchors": [], "diagnostics": [],
        })
        return (view, [], [], []) if operation == "object" else view
    monkeypatch.setattr(direct, adapter, native_read)
    result = json.loads(execute_hermes_graph_interaction_tool_json(
        "expand_graph_retrieval", {
            "retrievalSessionId": mounted.session.id, "operation": operation,
            "targets": [{"kind": "node", "id": "node:council"}],
            "queryText": "council concerns",
        }, root=mounted.code,
    ))
    assert result.get("outcome") == "enough", result
    assert len(calls) == 1
    assert mounted.session.operations[-1].operation == operation


def test_harness_reads_source_from_artifacts_without_selecting_graph_root(mounted, monkeypatch):
    calls = []
    def read(services, request, *, repo_root):
        assert services is mounted.services
        assert request.world_id == "native:world"
        assert request.revision_pin == "rev:frozen"
        assert repo_root == mounted.artifacts
        calls.append(request)
        return SimpleNamespace(model_dump=lambda **_: {
            "schema": "dmb_world_graph_source_anchor_read_result_v1",
            "outcome": "enough", "content": "The council represents the city.",
            "anchorId": "anchor:source", "diagnostics": [],
        })
    monkeypatch.setattr(direct, "read_source_anchor_direct", read)
    result = json.loads(execute_hermes_graph_interaction_tool_json(
        "read_graph_source", {"retrievalSessionId": mounted.session.id,
            "anchorIds": ["anchor:source"]}, root=mounted.code,
    ))
    assert result.get("outcome") == "enough", result
    assert len(calls) == 1
    assert mounted.session.source_anchors[0].opened


def test_explicit_alternate_graph_store_still_rejected(mounted):
    with pytest.raises(WorldGraphAuthorityConfigurationError, match="alternate world_root"):
        require_mounted_dungeonmind_world_graph(world_root=mounted.code)


def test_harness_does_not_restore_retired_file_authority(mounted, monkeypatch):
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY", "buddy_files")
    result = json.loads(execute_hermes_graph_interaction_tool_json(
        "expand_graph_retrieval", {"retrievalSessionId": mounted.session.id,
            "operation": "search", "queryText": "council"}, root=mounted.code,
    ))
    assert result["code"] == "world_graph_authority_configuration_invalid"
