from __future__ import annotations

import httpx
import pytest

from apps.live_control_server.services import recap_ingest_context as context_service


class _Binding:
    managed_world_id = "elderwyld"
    native_world_id = "world:elderwyld"
    binding_version = 7


def _payload(**updates):
    return {
        "schema_version": "dm_world_campaign_ingest_context_v1",
        "world_id": "world:elderwyld",
        "campaign_id": "longmont-c2",
        "membership": "member",
        "head_revision_id": "rev:head-1",
        "graph_schema": "dm_graph_v1",
        "graph_payload_sha256": "a" * 64,
        **updates,
    }


def _client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_context_read_resolves_managed_binding_and_pins_exact_native_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(context_service.BASE_URL_ENV, "https://mind.example")
    monkeypatch.setenv(context_service.TOKEN_ENV, "secret-token")
    monkeypatch.setattr(
        context_service,
        "resolve_managed_world_binding",
        lambda world_id: _Binding(),
    )
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json=_payload())

    with _client_for(handler) as client:
        result = context_service.read_recap_ingest_context(
            managed_world_id="elderwyld", campaign_id="longmont-c2", client=client
        )

    assert seen == {
        "url": "https://mind.example/v1/worlds/world%3Aelderwyld/campaigns/longmont-c2/ingest-context",
        "authorization": "Bearer secret-token",
    }
    assert result.as_lineage() == {
        "schema": "dm_world_campaign_ingest_context_v1",
        "managed_world_id": "elderwyld",
        "native_world_id": "world:elderwyld",
        "binding_version": 7,
        "campaign_id": "longmont-c2",
        "head_revision_id": "rev:head-1",
        "graph_schema": "dm_graph_v1",
        "graph_payload_sha256": "a" * 64,
    }


def test_context_read_rejects_membership_identity_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(context_service.BASE_URL_ENV, "https://mind.example")
    monkeypatch.setenv(context_service.TOKEN_ENV, "secret-token")
    monkeypatch.setattr(context_service, "resolve_managed_world_binding", lambda _id: _Binding())
    client = _client_for(lambda _request: httpx.Response(200, json=_payload(campaign_id="other")))
    with client, pytest.raises(context_service.RecapIngestContextError) as error:
        context_service.read_recap_ingest_context(
            managed_world_id="elderwyld", campaign_id="longmont-c2", client=client
        )
    assert error.value.code == "ingest_context_mismatch"
    assert error.value.status_code == 502


def test_uninitialized_graph_error_is_preserved_before_any_run_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(context_service.BASE_URL_ENV, "https://mind.example")
    monkeypatch.setenv(context_service.TOKEN_ENV, "secret-token")
    monkeypatch.setattr(context_service, "resolve_managed_world_binding", lambda _id: _Binding())
    client = _client_for(lambda _request: httpx.Response(
        409,
        json={"error": {"code": "world_graph_not_initialized", "message": "World Graph is not initialized."}},
    ))
    with client, pytest.raises(context_service.RecapIngestContextError) as error:
        context_service.read_recap_ingest_context(
            managed_world_id="elderwyld", campaign_id="longmont-c2", client=client
        )
    assert error.value.code == "world_graph_not_initialized"
    assert error.value.status_code == 409


def test_new_prepare_accepts_new_head_but_rejects_binding_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.live_control_server.services import extract_promote

    monkeypatch.setattr(
        context_service,
        "read_recap_ingest_context",
        lambda **_kwargs: type("Snapshot", (), {"as_lineage": lambda _self: _payload(
            schema="dm_world_campaign_ingest_context_v1",
            managed_world_id="elderwyld",
            native_world_id="world:elderwyld",
            binding_version=7,
            head_revision_id="rev:head-2",
            graph_payload_sha256="b" * 64,
        )})(),
    )
    expected = {
        **_payload(),
        "schema": "dm_world_campaign_ingest_context_v1",
        "managed_world_id": "elderwyld",
        "native_world_id": "world:elderwyld",
        "binding_version": 7,
    }
    current = extract_promote._assert_current_recap_ingest_context(
        expected, managed_world_id="elderwyld", campaign_id="longmont-c2"
    )
    assert current["head_revision_id"] == "rev:head-2"

    changed_binding = {
        **expected,
        "binding_version": 8,
    }
    with pytest.raises(extract_promote.ExtractPromoteError) as error:
        extract_promote._assert_current_recap_ingest_context(
            changed_binding, managed_world_id="elderwyld", campaign_id="longmont-c2"
        )
    assert error.value.code == "recap_ingest_context_changed"
    assert error.value.status_code == 409


def test_existing_extraction_can_be_reused_after_unrelated_world_publication() -> None:
    from apps.live_control_server.services.recap_graph_preview_ingest import (
        _same_recap_ingest_context_authority,
    )

    extracted = {
        "schema": "dm_world_campaign_ingest_context_v1",
        "managed_world_id": "elderwyld",
        "native_world_id": "world:elderwyld",
        "binding_version": 7,
        "campaign_id": "longmont-c2",
        "head_revision_id": "rev:before-other-publication",
        "graph_schema": "dm_graph_v1",
        "graph_payload_sha256": "a" * 64,
    }
    current = {
        **extracted,
        "head_revision_id": "rev:after-other-publication",
        "graph_payload_sha256": "b" * 64,
    }
    assert _same_recap_ingest_context_authority(extracted, current)
    assert not _same_recap_ingest_context_authority(
        {**extracted, "binding_version": 8}, current
    )
