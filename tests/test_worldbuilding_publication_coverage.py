"""Exact-run product coverage and authenticated mounted discovery route."""

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from apps.live_control_server.ports.world_graph_authority import (
    WorldGraphHead, WorldGraphAuthorityError, WorldbuildingPublishedFacet,
    WorldbuildingHistoricalPublication, WorldbuildingPublicationHistory,
)
from apps.live_control_server.services import worldbuilding_publication_coverage as service
from apps.live_control_server.services.extract_promote import ExtractPromoteError
from apps.live_control_server.routes import extract_promote as routes
from apps.live_control_server.services import agent_graph_auth as auth

TOKEN = "synthetic-operator-" + "x" * 40
URL = "/api/live/extract-promote/runs/run-test/worldbuilding-publication-coverage"


@pytest.fixture
def coverage_case(monkeypatch):
    resolved = SimpleNamespace(run_id="run-test", source_artifact_id="artifact-test",
                               source_revision_id="sha256:" + "a" * 64, sealed_source_uri="sealed-test")
    preview = SimpleNamespace(
        nodes=[SimpleNamespace(node_id="npc"), SimpleNamespace(node_id="city")],
        edges=[SimpleNamespace(edge_id="edge")], source_observations=[],
    )
    binding = SimpleNamespace(managed_world_id="managed", native_world_id="native", binding_version=1)
    publications = [WorldbuildingHistoricalPublication(
        "operation", "review", "parent", "child", "contribution", "b" * 64,
        (WorldbuildingPublishedFacet("npc", "node", "description", "assertion", "durable-npc", "accepted"),),
    )]
    history = WorldbuildingPublicationHistory(
        "native", "pin", "run-test", resolved.source_artifact_id,
        resolved.source_revision_id, tuple(publications), 3,
    )
    authority = SimpleNamespace(
        current_head=lambda world: WorldGraphHead(world, "pin"),
        discover_worldbuilding_publications=lambda request: history,
    )
    monkeypatch.setattr(service, "resolve_promotable_ingest_run", lambda *a, **k: resolved)
    monkeypatch.setattr(service, "_load_typed_worldbuilding_preview_for_run", lambda run: (preview, "profile"))
    monkeypatch.setattr(service, "_registered_publication_binding", lambda run: binding)
    monkeypatch.setattr(service, "_world_scoped_preview", lambda p, b: p)
    monkeypatch.setattr(service, "get_world_graph_authority", lambda: authority)
    return SimpleNamespace(resolved=resolved, binding=binding, history=history, authority=authority)


def test_bound_description_is_separate_from_existence_or_edge(coverage_case):
    result = service.get_worldbuilding_publication_coverage("run-test")
    assert result.status == "published"
    assert result.historical_only
    by_id = {item.candidate_id: item for item in result.candidates}
    assert by_id["npc"].status == "published_facts"
    assert [item.facet for item in by_id["npc"].facets] == ["description"]
    assert by_id["city"].status == by_id["edge"].status == "not_published"


def test_multiple_receipts_preserve_individual_fact_origins(coverage_case):
    prior = coverage_case.history.publications[0]
    second = replace(prior, native_operation_id="second", published_revision_id="later",
                     facets=(WorldbuildingPublishedFacet("npc", "node", "alias", "alias", "durable-npc", "accepted"),))
    coverage_case.authority.discover_worldbuilding_publications = lambda req: replace(
        coverage_case.history, publications=(second, prior),
    )
    result = service.get_worldbuilding_publication_coverage("run-test")
    assert len(result.publications) == 2
    assert {fact.facet for row in result.candidates for fact in row.facets} == {"alias", "description"}


def test_unmapped_native_facts_remain_visible_and_unknown(coverage_case):
    publication = replace(coverage_case.history.publications[0], unmapped_assertion_ids=("unmapped",))
    coverage_case.authority.discover_worldbuilding_publications = lambda req: replace(
        coverage_case.history, publications=(publication,),
    )
    result = service.get_worldbuilding_publication_coverage("run-test")
    assert result.status == "unknown"
    assert result.publications[0].unmapped_assertion_ids == ["unmapped"]
    assert next(row for row in result.candidates if row.candidate_id == "edge").status == "unknown"


@pytest.mark.parametrize("field,value", [
    ("world_id", "foreign"), ("revision_id", "foreign"), ("run_id", "foreign"),
    ("source_artifact_id", "foreign"), ("source_revision_id", "foreign"),
])
def test_foreign_history_echo_refuses(coverage_case, field, value):
    coverage_case.authority.discover_worldbuilding_publications = lambda req: replace(
        coverage_case.history, **{field: value},
    )
    with pytest.raises(ExtractPromoteError, match="binding disagrees"):
        service.get_worldbuilding_publication_coverage("run-test")


def test_binding_changed_during_read_refuses(coverage_case, monkeypatch):
    calls = iter([coverage_case.binding, SimpleNamespace(native_world_id="changed")])
    monkeypatch.setattr(service, "_registered_publication_binding", lambda run: next(calls))
    with pytest.raises(ExtractPromoteError) as failure:
        service.get_worldbuilding_publication_coverage("run-test")
    assert failure.value.code == "worldbuilding_source_binding_changed"


def test_unavailable_never_returns_zero_coverage(coverage_case):
    def unavailable(request):
        raise WorldGraphAuthorityError("Unavailable", code="authority_unavailable")
    coverage_case.authority.discover_worldbuilding_publications = unavailable
    with pytest.raises(ExtractPromoteError) as failure:
        service.get_worldbuilding_publication_coverage("run-test")
    assert failure.value.status_code == 503


def call(*, token=TOKEN, query="", peer="127.0.0.1"):
    app = FastAPI()
    app.include_router(routes.router)
    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=(peer, 1234)), base_url="http://test",
        ) as client:
            return await client.get(URL + query,
                headers={"Authorization": f"Bearer {token}"} if token else {})
    return asyncio.run(request())


@pytest.fixture
def authentication(monkeypatch):
    monkeypatch.setenv(auth.AUTH_MODE_ENV, "local_operator")
    monkeypatch.setenv(auth.AUTH_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(auth.LOCAL_OPERATOR_TOKEN_ENV, TOKEN)


def test_mounted_route_returns_exact_coverage(authentication, coverage_case):
    response = call()
    assert response.status_code == 200
    assert response.json()["schema"] == "dmb_worldbuilding_publication_coverage_v1"
    assert response.json()["managedWorldId"] == "managed"


@pytest.mark.parametrize("token", [None, "wrong"])
def test_route_requires_authentication(authentication, token):
    assert call(token=token).status_code == 401


def test_route_rejects_nonloopback_and_selectors(authentication, coverage_case):
    assert call(peer="192.0.2.1").status_code == 403
    assert call(query="?worldId=foreign").status_code == 422
