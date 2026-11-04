"""Authenticated human source-only HTTP; actual pinned Core, no APP/DB/providers."""

import copy
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.live_control_server.routes.native_source_inspection import router
from apps.live_control_server.services import native_source_inspection as service
from apps.live_control_server.services import managed_world_graph_projection as owner
from apps.live_control_server.services.agent_graph_auth import (
    native_graph_gm_dependency,
)
from tests.test_native_corpus_source_access import lane as source_lane, admit, BODY  # noqa: F401

TOKEN = "synthetic-source-inspection-operator-token"
PATH = "/api/live/native-source-inspection"
SCOPE = {"managed_world_id": "managed", "scope_mode": "world", "campaign_id": None}


@pytest.fixture
def inspection(request, monkeypatch):
    lane = request.getfixturevalue("source_lane")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", TOKEN)

    def resolve(world, **kwargs):
        if world != "managed":
            raise ValueError("Foreign World")
        return copy.deepcopy(lane.bound)

    monkeypatch.setattr(owner, "resolve_managed_source_identity", resolve)
    monkeypatch.setattr(service.native, "read_repository", lambda: lane.repo)

    def graph_forbidden(*args, **kwargs):
        pytest.fail("Source inspection depended on active object Graph authority")

    monkeypatch.setattr(service.native, "binding", graph_forbidden)
    monkeypatch.setattr(service.native, "read_context", graph_forbidden)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(
        app, client=("127.0.0.1", 50000), headers={"Authorization": "Bearer " + TOKEN}
    )
    return SimpleNamespace(lane=lane, client=client, app=app)


def selection(case):
    response = case.client.post(PATH + "/catalog", json=SCOPE)
    assert response.status_code == 200
    packet = response.json()
    item = packet["catalogue"]["sources"][0]
    return {
        "scope": packet["scope"],
        "source_artifact_id": item["source_artifact"]["source_artifact_id"],
        "source_revision_id": item["source_revision"]["source_revision_id"],
        "evidence_ref_id": item["evidence_ref_ids"][0],
    }


def test_metadata_http_uses_source_only_owner_without_body_reads(
    inspection, monkeypatch
):
    receipt = admit(inspection.lane, multiple=True)
    head = inspection.lane.repo.get_head("world:test")
    view = inspection.lane.repo.open_native_source_view("world:test")

    def forbidden(*args, **kwargs):
        pytest.fail("Metadata browsing read source body bytes")

    monkeypatch.setattr(type(view), "get_native_text_source", forbidden)
    response = inspection.client.post(PATH + "/catalog", json=SCOPE)
    assert (
        response.status_code == 200 and response.headers["cache-control"] == "no-store"
    )
    packet = response.json()
    catalog = packet["catalogue"]
    assert packet["schema"] == "dmb_native_source_catalog_v1"
    assert packet["scope"]["revision_id"] == receipt.published_revision_id
    assert packet["scope"]["native_world_id"] == catalog["space_id"] == "world:test"
    assert catalog["complete"] and len(catalog["sources"]) == 1
    assert len(catalog["sources"][0]["evidence_ref_ids"]) == 2
    assert "body_text" not in response.text and BODY not in response.text
    assert inspection.lane.repo.get_head("world:test") == head


def test_exact_selected_source_http_preserves_native_body_and_span_proof(inspection):
    receipt = admit(inspection.lane)
    request = selection(inspection)
    response = inspection.client.post(PATH + "/read", json=request)
    assert (
        response.status_code == 200 and response.headers["cache-control"] == "no-store"
    )
    packet = response.json()
    source = packet["source"]
    assert packet["schema"] == "dmb_native_source_body_v1"
    assert packet["scope"] == request["scope"]
    assert source["source_artifact_id"] == receipt.source_artifact_id
    assert source["source_revision_id"] == receipt.source_revision_id
    assert (
        source["body_text"] == BODY
        and source["body_sha256"] == sha256(BODY.encode()).hexdigest()
    )
    assert source["span_start_byte"] == 0
    assert source["span_end_byte"] == len(BODY.splitlines(keepends=True)[0].encode())
    assert (
        source["span_sha256"]
        == sha256(BODY.encode()[: source["span_end_byte"]]).hexdigest()
    )


def test_selected_revision_survives_later_source_admission(inspection):
    first = admit(inspection.lane)
    request = selection(inspection)
    admit(inspection.lane, "later", body="A different source.\n")
    response = inspection.client.post(PATH + "/read", json=request)
    assert response.status_code == 200
    assert response.json()["scope"]["revision_id"] == first.published_revision_id
    assert response.json()["source"]["body_text"] == BODY


@pytest.mark.parametrize(
    "field", ["source_artifact_id", "source_revision_id", "evidence_ref_id"]
)
def test_foreign_selected_source_is_rejected_before_body_read(
    inspection, monkeypatch, field
):
    admit(inspection.lane)
    request = selection(inspection)
    request[field] = "foreign"
    monkeypatch.setattr(
        service,
        "open_admitted_native_text",
        lambda *args: pytest.fail("Foreign selection read a body"),
    )
    response = inspection.client.post(PATH + "/read", json=request)
    assert response.status_code == 409
    assert (
        response.json()["detail"]["code"]
        == "native_source_inspection_selection_unavailable"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("native_world_id", "foreign"),
        ("binding_version", 99),
        ("revision_id", "missing"),
    ],
)
def test_foreign_pin_fails_before_body_read(inspection, monkeypatch, field, value):
    admit(inspection.lane)
    request = selection(inspection)
    request["scope"][field] = value
    monkeypatch.setattr(
        service,
        "open_admitted_native_text",
        lambda *args: pytest.fail("Foreign pin read a body"),
    )
    assert inspection.client.post(PATH + "/read", json=request).status_code == 409


def test_source_inspection_rejects_foreign_world_and_campaign_scope(inspection):
    assert (
        inspection.client.post(
            PATH + "/catalog", json={**SCOPE, "managed_world_id": "foreign"}
        ).status_code
        == 409
    )
    assert (
        inspection.client.post(
            PATH + "/catalog",
            json={**SCOPE, "scope_mode": "campaign", "campaign_id": "c1"},
        ).status_code
        == 409
    )


def test_unauthenticated_and_player_requests_cannot_browse_sources(inspection):
    response = inspection.client.post(
        PATH + "/catalog", json=SCOPE, headers={"Authorization": "Bearer wrong"}
    )
    assert response.status_code == 401
    inspection.app.dependency_overrides[native_graph_gm_dependency] = lambda: (
        SimpleNamespace(role="player")
    )
    assert inspection.client.post(PATH + "/catalog", json=SCOPE).status_code == 409


def test_empty_metadata_is_complete_without_an_object_graph(inspection):
    response = inspection.client.post(PATH + "/catalog", json=SCOPE)
    assert response.status_code == 200
    assert (
        response.json()["catalogue"]["complete"]
        and response.json()["catalogue"]["sources"] == []
    )


def test_partial_core_metadata_is_preserved_without_inventing_success(
    inspection, monkeypatch
):
    admit(inspection.lane)
    actual = service.list_admitted_native_text_sources
    monkeypatch.setattr(
        service,
        "list_admitted_native_text_sources",
        lambda context: replace(actual(context), complete=False),
    )
    response = inspection.client.post(PATH + "/catalog", json=SCOPE)
    assert response.status_code == 200 and not response.json()["catalogue"]["complete"]


def test_source_owner_change_during_browsing_refuses_packet(inspection, monkeypatch):
    admit(inspection.lane)
    calls = 0

    def changed(world, **kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            **(
                vars(inspection.lane.bound)
                | ({"binding_version": 2} if calls >= 3 else {})
            )
        )

    monkeypatch.setattr(owner, "resolve_managed_source_identity", changed)
    response = inspection.client.post(PATH + "/catalog", json=SCOPE)
    assert response.status_code == 409
    assert (
        response.json()["detail"]["code"] == "native_source_inspection_binding_changed"
    )


def test_reader_refusal_stays_unavailable(inspection, monkeypatch):
    admit(inspection.lane)
    request = selection(inspection)
    monkeypatch.setattr(
        service,
        "open_admitted_native_text",
        lambda *args: SimpleNamespace(status="unavailable"),
    )
    response = inspection.client.post(PATH + "/read", json=request)
    assert response.status_code == 409
    assert (
        response.json()["detail"]["code"]
        == "native_source_inspection_source_unavailable"
    )


def test_unknown_fields_and_duplicate_json_are_rejected(inspection):
    assert (
        inspection.client.post(
            PATH + "/catalog", json={**SCOPE, "body_text": "invented"}
        ).status_code
        == 422
    )
    response = inspection.client.post(
        PATH + "/catalog",
        content='{"managed_world_id":"managed","managed_world_id":"foreign"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_core_integrity_failure_cannot_appear_as_empty_metadata(
    inspection, monkeypatch
):
    from dungeonmind.application.vnext.errors import (
        NativeTextSourceAccessIntegrityError,
    )

    def failed(context):
        raise NativeTextSourceAccessIntegrityError("Corrupt metadata")

    monkeypatch.setattr(service, "list_admitted_native_text_sources", failed)
    response = inspection.client.post(PATH + "/catalog", json=SCOPE)
    assert response.status_code == 409 and "catalogue" not in response.json()


def test_changed_source_owner_during_read_withholds_body(inspection, monkeypatch):
    admit(inspection.lane)
    request = selection(inspection)
    calls = 0

    def changed(world, **kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            **(
                vars(inspection.lane.bound)
                | ({"binding_version": 2} if calls >= 3 else {})
            )
        )

    monkeypatch.setattr(owner, "resolve_managed_source_identity", changed)
    response = inspection.client.post(PATH + "/read", json=request)
    assert response.status_code == 409 and BODY not in response.text
