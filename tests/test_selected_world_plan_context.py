from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from apps.live_control_server.routes import live
from apps.live_control_server.services.world_container_registry import create_world_container


def test_managed_plan_view_is_grounded_and_contains_no_c2_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = create_world_container(tmp_path, name="Of Conks")
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    body = live.get_live_plan_view(world_id=world.world_id)
    assert body["schema_version"] == "dmb_managed_world_plan_context_v1"
    assert body["campaign_id"] == world.world_id
    assert body["world_id"] == world.world_id
    assert body["session"] == 0
    assert body["timeline"] == []
    assert body["derived_from"] == ["managed_world_container"]


def test_unknown_managed_plan_world_fails_before_legacy_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "apps.live_control_server.routes.live.load_session",
        lambda _base: pytest.fail("legacy C2 packet was loaded"),
    )
    with pytest.raises(HTTPException) as error:
        live.get_live_plan_view(world_id="unknown-world")
    assert error.value.status_code == 404


def _managed_query(world_id: str, *, graph_world_id: str | None = None) -> dict:
    return {
        "campaign_id": world_id,
        "session": 1,
        "query_backend": "hermes",
        "text": "What do we know?",
        "world_graph_context": {
            "schema": "dmb_agent_world_graph_query_context_request_v1",
            "world_id": graph_world_id or world_id,
            "campaign_id": "",
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
            "scope_mode": "world",
        },
        "surface_context": {
            "schema": "dmb_agent_surface_context_request_v1",
            "surface_id": "plan",
            "campaign_id": world_id,
            "document_id": "11111111-1111-4111-8111-111111111111",
            "session_number": 1,
            "pointers": [],
        },
    }


def test_managed_ask_uses_exact_world_packet_not_c2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world_id = "of-conks-cons-demo"
    calls: list[dict] = []
    monkeypatch.setattr(live, "get_world_container", lambda _root, _id: SimpleNamespace(world_id=world_id))
    monkeypatch.setattr(
        live,
        "get_workspace_document",
        lambda _root, _id: SimpleNamespace(kind="plan", campaign_id=world_id, target_session=1),
    )
    monkeypatch.setattr(live, "load_session", lambda _base: pytest.fail("C2 packet was loaded"))
    monkeypatch.setattr(
        live,
        "process_live_query",
        lambda *_args, **kwargs: calls.append(kwargs) or {"status": "ok"},
    )
    response = live.post_live_query(live.LiveQueryRequest.model_validate(_managed_query(world_id)))
    assert response == {"status": "ok"}
    assert calls[0]["managed_world_packet"] == {"campaign_id": world_id, "session": 1}
    assert calls[0]["outer_campaign_id"] == world_id

    calls.clear()
    with pytest.raises(HTTPException) as error:
        live.post_live_query(live.LiveQueryRequest.model_validate(
            _managed_query(world_id, graph_world_id="eldyrwild")
        ))
    assert error.value.status_code == 422
    assert calls == []

    for nested_campaign, mode in ((world_id, "world"), (world_id, "campaign")):
        bad = _managed_query(world_id)
        bad["world_graph_context"]["campaign_id"] = nested_campaign
        bad["world_graph_context"]["scope_mode"] = mode
        with pytest.raises(HTTPException) as error:
            live.post_live_query(live.LiveQueryRequest.model_validate(bad))
        assert error.value.status_code == 422
        assert calls == []

    missing_campaign = _managed_query(world_id)
    missing_campaign["world_graph_context"]["scope_mode"] = "campaign"
    with pytest.raises(ValueError, match="campaign_id is required"):
        live.LiveQueryRequest.model_validate(missing_campaign)


def test_legacy_c2_query_does_not_require_managed_world_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        live,
        "get_world_container",
        lambda _root, _id: pytest.fail("legacy query consulted managed World registry"),
    )
    monkeypatch.setattr(
        live,
        "load_session",
        lambda _base: ({"campaign_id": "longmont-c2", "session": 1}, None, None, None),
    )
    calls: list[dict] = []
    monkeypatch.setattr(
        live,
        "process_live_query",
        lambda *_args, **kwargs: calls.append(kwargs) or {"status": "ok"},
    )
    response = live.post_live_query(live.LiveQueryRequest.model_validate(
        _managed_query("longmont-c2", graph_world_id="eldyrwild")
    ))
    assert response == {"status": "ok"}
    assert calls[0]["managed_world_packet"] is None


def test_managed_hermes_service_does_not_load_legacy_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services import live_agent_loop
    from apps.live_control_server.services.agent_surface_context import AgentSurfaceContextRequest
    from apps.live_control_server.services.agent_world_graph_query_context import (
        AgentWorldGraphQueryContextRequest,
    )

    world_id = "of-conks-cons-demo"
    request = _managed_query(world_id)
    monkeypatch.setattr(
        live_agent_loop,
        "load_session",
        lambda _base: pytest.fail("legacy C2 packet was loaded"),
    )
    monkeypatch.setattr(live_agent_loop, "validate_hermes_query_inputs", lambda **_kwargs: None)
    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *_args, **_kwargs: {"status": "unavailable", "world_id": world_id},
    )
    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_surface_context",
        lambda *_args, **_kwargs: SimpleNamespace(context=None, trace_summary={}, warning_codes=()),
    )
    monkeypatch.setattr(
        live_agent_loop,
        "run_hermes_graph_query",
        lambda **kwargs: {"packet": kwargs["packet"], "session_base": kwargs["session_base"]},
    )
    response = live_agent_loop.process_live_query(
        "What do we know?",
        base=tmp_path,
        query_backend="hermes",
        outer_campaign_id=world_id,
        managed_world_packet={"campaign_id": world_id, "session": 1},
        world_graph_context=AgentWorldGraphQueryContextRequest.model_validate(request["world_graph_context"]),
        surface_context=AgentSurfaceContextRequest.model_validate(request["surface_context"]),
    )
    assert response == {"packet": {"campaign_id": world_id, "session": 1}, "session_base": None}
