"""Retired file forms refuse before storage, lookup or extraction."""

import pytest

from apps.live_control_server.routes import recap_ingest as route
from tests.test_live_recap_ingest_graph_preview_api import client_env as client_env
from tests.test_live_recap_ingest_graph_preview_api import process_body


@pytest.mark.parametrize(
    "change",
    [
        {"operation": "inspect_status"},
        {"operation":"materialize_preview_supergraph"},
        {"materialize_after_extract":True},
        {"materialize_after_extract":False},
        {"candidate_graph_path":"out/manual.json"},
        {"operation":"inspect_graph_preview"},
        {"operation": "reconcile_normalized_recap"},
        {"operation": "build_graph_preview_bundle"},
        {"raw_text": " "},
        {"include_graph_extraction": False},
        {"managed_world_id": None},
        {"session": 0},
        {"session":True},
        {"session":8.5},
        {"campaign_id": " "},
        {"slug": "old filename"},
        {"title": "old canonical title"},
        {"force_stage": True},
        {"force_recap": True},
        {"keep_basename": "old.md"},
        {"extract_graph": True},
    ],
)
def test_invalid_or_retired_process_forms_stop_before_owner(
    client_env, monkeypatch, change
):
    client, _ = client_env
    monkeypatch.setattr(
        route, "extract_recap", lambda **_: pytest.fail("source/provider reached")
    )
    reply = client.post("/api/live/recap-ingest", json=process_body(**change))
    assert reply.status_code == 422, reply.text


def test_missing_local_gm_stops_before_source_owner(client_env, monkeypatch):
    client, _ = client_env
    client.headers.pop("Authorization")
    monkeypatch.setattr(
        route, "extract_recap", lambda **_: pytest.fail("source/provider reached")
    )
    reply = client.post("/api/live/recap-ingest", json=process_body())
    assert reply.status_code in {401, 403}, reply.text


def test_hosted_resolver_does_not_admit_raw_process(client_env):
    import asyncio
    import json

    from starlette.requests import Request

    payload = json.dumps(process_body()).encode()

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/live/recap-ingest",
            "headers": [],
        },
        receive,
    )
    with pytest.raises(ValueError, match="outside source admission"):
        asyncio.run(route.resolve_native_recap_hosted_world(request))
