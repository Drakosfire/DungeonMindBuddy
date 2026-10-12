"""World-scope request validation across projection, Agent and retrieval boundaries."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphQueryContextRequest,
)
from graph_memory.projection.world_projection import WorldGraphProjectionRequest
from graph_memory.interaction.initial_resolve import create_session_from_preflight
from graph_memory.retrieval.models import WorldGraphSearchRequest, RecapContextIndexRequest, RecapContextReadRequest


def test_recap_context_wire_requires_exact_gm_pin_and_distinct_context_id() -> None:
    common = {"worldId": "eldyrwild", "campaignId": "longmont-c2", "scopeMode": "campaign", "revisionPin": "rev:fixed"}
    listed = RecapContextIndexRequest.model_validate({"schema":"dmb_recap_context_index_request_v1", **common})
    assert listed.max_entries == 512
    opened = RecapContextReadRequest.model_validate({"schema":"dmb_recap_context_read_request_v1", **common,
        "contextAnchorId":"dm-context-anchor:v1:exact"})
    assert opened.context_anchor_id.startswith("dm-context-anchor:")
    for bad in ({"revisionPin":None}, {"admissibility":"player"}, {"sourceUri":"repo://forged.md"}):
        with pytest.raises(ValidationError):
            RecapContextReadRequest.model_validate({"schema":"dmb_recap_context_read_request_v1", **common,
                "contextAnchorId":"dm-context-anchor:v1:exact", **bad})
    with pytest.raises(ValidationError):
        RecapContextReadRequest.model_validate({"schema":"dmb_recap_context_read_request_v1", **common,
            "contextAnchorId":"source-anchor:v1:old-evidence"})


def test_recap_context_routes_use_separate_service_operations(monkeypatch) -> None:
    from starlette.requests import Request
    from apps.live_control_server.routes import world_graph_retrieval as route
    from graph_memory.retrieval.models import RecapContextDescriptor, RecapContextIndexResult, RecapContextReadResult, WorldGraphRetrievalSnapshot
    snapshot = WorldGraphRetrievalSnapshot(world_id="eldyrwild", campaign_id="longmont-c2", revision_id="rev:fixed",
        head_revision_id="rev:fixed", is_head=True, focus={"kind":"none"}, admissibility="gm", scope_mode="campaign")
    descriptor = RecapContextDescriptor(context_anchor_id="dm-context-anchor:v1:exact", world_id="eldyrwild",
        campaign_id="longmont-c2", graph_revision_id="rev:fixed", source_artifact_id="artifact:s22",
        source_revision_id="sha256:"+"a"*64, source_uri="repo://s22.md", content_sha256="a"*64,
        expected_session_id="session-22", expected_heading="# Session 22 Recap")
    listed=[]
    opened=[]
    monkeypatch.setattr(route,"list_recap_context",lambda request: listed.append(request) or RecapContextIndexResult(
        snapshot=snapshot,status="complete",eligible_count=1,max_entries=512,entries=[descriptor]))
    monkeypatch.setattr(route,"read_recap_context",lambda request: opened.append(request) or RecapContextReadResult(
        outcome="enough",snapshot=snapshot,context_anchor_id=descriptor.context_anchor_id,context=descriptor,
        content="one line",media_type="text/markdown",heading_line=3,line_start=4,line_end=4,
        section_sha256="b"*64))
    empty=Request({"type":"http","query_string":b""})
    common={"worldId":"eldyrwild","campaignId":"longmont-c2","scopeMode":"campaign","revisionPin":"rev:fixed"}
    index=RecapContextIndexRequest.model_validate({"schema":"dmb_recap_context_index_request_v1",**common})
    read=RecapContextReadRequest.model_validate({"schema":"dmb_recap_context_read_request_v1",**common,
        "contextAnchorId":descriptor.context_anchor_id})
    assert route.post_recap_context_index(empty,index)["entries"][0]["contextAnchorId"]==descriptor.context_anchor_id
    assert route.post_recap_context_read(empty,read)["content"]=="one line"
    assert len(listed)==len(opened)==1


def test_mounted_recap_context_route_authenticates_before_service_and_preserves_error(monkeypatch) -> None:
    import json
    from fastapi import FastAPI
    from fastapi import HTTPException
    from fastapi.routing import APIRoute
    from starlette.requests import Request
    from apps.live_control_server.routes import world_graph_retrieval as route
    from apps.live_control_server.services.agent_graph_auth import (
        enforce_native_graph_gm, native_graph_gm_dependency,
    )
    from apps.live_control_server.services.world_graph_retrieval import WorldGraphRetrievalServiceError

    token = 'synthetic-recap-context-operator-token-32-chars'
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT', 'development')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN', token)
    calls = []

    def unavailable(request):
        calls.append(request)
        raise WorldGraphRetrievalServiceError('Source unavailable.', code='source_unavailable', status_code=409)

    monkeypatch.setattr(route, 'read_recap_context', unavailable)
    app = FastAPI()
    app.include_router(route.router)
    path = '/api/live/world-graph/retrieval/recap-context/read'
    mounted = next(row for row in app.routes if isinstance(row, APIRoute) and row.path == path)
    assert any(dependency.call is native_graph_gm_dependency for dependency in mounted.dependant.dependencies)
    empty = Request({'type': 'http', 'method': 'POST', 'path': path, 'query_string': b'',
                     'headers': [], 'client': ('127.0.0.1', 50000)})
    with pytest.raises(HTTPException) as denied:
        enforce_native_graph_gm(empty)
    assert denied.value.status_code == 401 and denied.value.detail['code'] == 'graph_auth_required'
    assert calls == []
    payload = {
        'schema': 'dmb_recap_context_read_request_v1', 'worldId': 'eldyrwild',
        'campaignId': '', 'scopeMode': 'world', 'revisionPin': 'rev:fixed',
        'contextAnchorId': 'dm-context-anchor:v1:exact',
    }
    request = RecapContextReadRequest.model_validate(payload)
    failed = mounted.endpoint(empty, request)
    assert failed.status_code == 409 and json.loads(failed.body)['code'] == 'source_unavailable'
    assert len(calls) == 1 and calls[0].scope_mode == 'world'


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


def _selected_native_fixture(*, unrelated=513, own=1, unavailable=False, claims=False, neighbor=False):
    import copy
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.memory import InMemoryWorldGraphRepository
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
    from tests._cutover_direct_dungeonmind_read_helpers import WORLD_ID, NOW, _payload, _seed_sources, _receipt, _FakeBundle
    payload = _payload()
    target = copy.deepcopy(next(obj for obj in payload["objects"] if obj["object_id"] == "obj:tavern"))
    evidence = copy.deepcopy(next(row for row in payload["evidence_refs"] if row["evidence_ref_id"] == "ev:tavern"))
    evidence["locator"] = "heading:The Prancing Tavern"
    if unavailable:
        evidence["can_open_source"] = False
    objects, refs = [target], []
    for index in range(own):
        refs.append({**evidence, "evidence_ref_id": f"ev:target:{index}", "locator": evidence["locator"] if own == 1 else f"paragraph:{index+1}"})
    target["assertion_metadata"]["evidence_ref_ids"] = [row["evidence_ref_id"] for row in refs]
    for index in range(unrelated):
        ref = {**evidence, "evidence_ref_id": f"ev:noise:{index}", "locator": f"heading:Unrelated stone {index}"}
        refs.append(ref)
        obj = copy.deepcopy(target)
        obj.update(object_id=f"obj:noise:{index}", label=f"Unrelated stone {index}")
        obj["assertion_metadata"].update(assertion_id=f"asrt:noise:{index}", evidence_ref_ids=[ref["evidence_ref_id"]])
        objects.append(obj)
    if claims:
        target["properties"] = [{"property_term":"dnd5e:population", "value":"bustling",
            "assertion_metadata":{**copy.deepcopy(target["assertion_metadata"]),"assertion_id":"asrt:target-population"}}]
    relationships = []
    if neighbor:
        assert unrelated > 1
        relationships = [{"relationship_id":"rel:neighbor", "source_object_id":"obj:tavern", "target_object_id":"obj:noise:0",
            "predicate":"dnd5e:located_in", "assertion_metadata":{**copy.deepcopy(target["assertion_metadata"]),"assertion_id":"asrt:neighbor"}}]
        relationships.append({"relationship_id":"rel:second-hop", "source_object_id":"obj:noise:0", "target_object_id":"obj:noise:1",
            "predicate":"dnd5e:located_in", "assertion_metadata":{**copy.deepcopy(target["assertion_metadata"]),"assertion_id":"asrt:second-hop","evidence_ref_ids":["ev:noise:0"]}})
    payload.update(objects=objects, relationships=relationships, evidence_refs=refs)
    graphs, sources = InMemoryWorldGraphRepository(), _seed_sources()
    published = graphs.publish_revision(PublishRevisionCommand(world_id=WORLD_ID, parent_revision_id=None,
        expected_parent_revision_id=None, operation_ids=["op:selected-fixture"], graph_schema="dm_union_graph_v6",
        graph_payload=payload, created_at=NOW))
    services = direct.direct_services_from_bundle(_FakeBundle(graphs, sources, _receipt(WORLD_ID, published.revision_id)), WORLD_ID)
    request = _search(worldId=WORLD_ID, queryText="The Prancing Tavern", revisionPin=published.revision_id)
    return services, request, published.revision_id


def test_selected_buddy_index_ignores_unrelated_global_overflow_and_tamper(monkeypatch):
    import copy
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
    from application_state.agent_conversation.types import GraphSelectedSourceReadScopeV2
    services, request, revision = _selected_native_fixture()
    search = direct.search_world_graph_direct_v2(services, request)
    assert len(search.native_targets) == 1 and search.native_targets[0].target_id == "obj:tavern"
    legacy = direct.list_source_anchor_index_direct_v2(services, request, revision_id=revision)
    assert legacy.status == "overflow" and legacy.eligible_count >= 513 and legacy.source_pins == ()
    selected = direct.list_selected_source_anchor_index_direct_v1(services, request, revision_id=revision, targets=search.native_targets)
    assert selected.status == "complete" and selected.eligible_count == 1
    assert selected.commitment["index_scope"] == "selected_targets"
    pins = [{key: value for key, value in vars(pin).items() if key != "graph_revision"} for pin in selected.source_pins]
    scope = GraphSelectedSourceReadScopeV2(retrieval_session_id="session", initial_claim_packet_sha256="0"*64, world_id="managed-world", campaign_id=None,
        graph_revision=revision, admitted_anchors=pins, selected_index_commitment=selected.commitment)
    assert scope.selected_index_commitment.requested_count == 1
    for field in ("selector_sha256", "index_sha256", "access_context_sha256"):
        changed = copy.deepcopy(selected.commitment)
        changed[field] = "0" * 64
        with pytest.raises(ValidationError):
            GraphSelectedSourceReadScopeV2(retrieval_session_id="session", initial_claim_packet_sha256="0"*64, world_id="managed-world", campaign_id=None,
                graph_revision=revision, admitted_anchors=pins, selected_index_commitment=changed)
    with pytest.raises(direct.DirectWorldGraphReadError):
        direct.list_selected_source_anchor_index_direct_v1(services, request, revision_id="stale", targets=search.native_targets)


def test_selected_own_overflow_and_unavailable_preserve_truthful_coverage():
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
    for options, expected in [({"unrelated": 0, "own": 513}, "overflow"), ({"unrelated": 0, "unavailable": True}, "unavailable")]:
        services, request, revision = _selected_native_fixture(**options)
        search = direct.search_world_graph_direct_v2(services, request)
        assert search.result.nodes and search.native_targets
        index = direct.list_selected_source_anchor_index_direct_v1(services, request, revision_id=revision, targets=search.native_targets)
        assert index.status == expected and index.source_pins == ()
        if expected == "unavailable":
            assert index.commitment["admitted_count"] == 1 and index.commitment["unavailable_binding_count"] > 0
            assert search.result.nodes[0].evidence_ref_ids
