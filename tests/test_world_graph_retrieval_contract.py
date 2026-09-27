"""World-scope request validation across projection, Agent and retrieval boundaries."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphQueryContextRequest,
)
from graph_memory.projection.world_projection import WorldGraphProjectionRequest
from graph_memory.interaction.initial_resolve import create_session_from_preflight
from graph_memory.retrieval.models import WorldGraphSearchRequest


def _projection(**overrides: object) -> WorldGraphProjectionRequest:
    payload: dict[str, object] = {
        "schema": "dmb_world_graph_projection_request_v1",
        "worldId": "of-conks-j1-fresh-rehearsal",
        "campaignId": "",
        "scopeMode": "world",
    }
    payload.update(overrides)
    return WorldGraphProjectionRequest.model_validate(payload)


def _agent(**overrides: object) -> AgentWorldGraphQueryContextRequest:
    payload: dict[str, object] = {
        "schema": "dmb_agent_world_graph_query_context_request_v1",
        "world_id": "of-conks-j1-fresh-rehearsal",
        "campaign_id": "",
        "scope_mode": "world",
    }
    payload.update(overrides)
    return AgentWorldGraphQueryContextRequest.model_validate(payload)


def _search(**overrides: object) -> WorldGraphSearchRequest:
    payload: dict[str, object] = {
        "schema": "dmb_world_graph_search_request_v1",
        "worldId": "of-conks-j1-fresh-rehearsal",
        "campaignId": "",
        "scopeMode": "world",
        "queryText": "Hempholm",
    }
    payload.update(overrides)
    return WorldGraphSearchRequest.model_validate(payload)


@pytest.mark.parametrize("build", [_projection, _agent, _search])
def test_blank_campaign_is_valid_only_for_explicit_world_scope(build):
    world = build()
    assert world.campaign_id == ""
    assert world.scope_mode == "world"

    mode_key = "scope_mode" if build is _agent else "scopeMode"
    with pytest.raises(ValidationError):
        build(**{mode_key: "campaign"})
    with pytest.raises(ValidationError):
        build(**{mode_key: "invalid"})


@pytest.mark.parametrize("build", [_projection, _agent, _search])
def test_nonblank_narrative_campaign_remains_valid_in_world_scope(build):
    campaign_key = "campaign_id" if build is _agent else "campaignId"
    anchored = build(**{campaign_key: "longmont-c2"})
    assert anchored.campaign_id == "longmont-c2"
    assert anchored.scope_mode == "world"


def test_managed_world_retrieval_session_retains_blank_campaign_and_revision() -> None:
    envelope = {
        "world_id": "of-conks-j1-fresh-rehearsal",
        "campaign_id": "",
        "revision_id": "rev:22ef509825ee1048efc73a1a1aa4a60c",
        "matched_node_ids": ["node:hempholm"],
        "nodes": [{"node_id": "node:hempholm", "label": "Hempholm"}],
        "attributes": [],
        "focus": {"kind": "none"},
        "admissibility": "gm",
        "scope_mode": "world",
    }
    session = create_session_from_preflight(envelope, question="What is Hempholm?")
    assert session.snapshot.world_id == envelope["world_id"]
    assert session.snapshot.campaign_id == ""
    assert session.snapshot.scope_mode == "world"
    assert session.snapshot.revision_id == envelope["revision_id"]
    packet = session.project_for_hermes()
    assert packet["snapshot"]["scope_mode"] == "world"
    assert packet["snapshot"]["campaign_id"] == ""
