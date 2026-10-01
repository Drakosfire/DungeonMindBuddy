from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from types import SimpleNamespace

from fastapi import FastAPI
import httpx
import pytest

from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.routes.live import router as live_router
from apps.live_control_server.services.agent_runtime import (
    AgentRuntimeDescriptor,
    AgentRuntimeResult,
)


class FakeRuntime:
    descriptor = AgentRuntimeDescriptor("fake", "fake", "test", "conversation")

    def __init__(self) -> None:
        self.invocations: list[Any] = []

    def run(self, invocation: Any) -> AgentRuntimeResult:
        self.invocations.append(invocation)
        return AgentRuntimeResult(
            status="ok", final_text="A simple answer.", runtime_session_id="runtime-1"
        )


def _payload() -> dict[str, Any]:
    return {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "thread-no-scope",
        "turn_id": "turn-no-scope",
        "surface": {"surface_id": "index", "instance_id": "index-home"},
        "owner_scope": None,
        "primary_work": None,
        "client_work_state": "none",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "message": "What can you help me with?",
    }


def test_no_scope_route_does_not_load_packet_and_registers_exactly_once(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.routes import live as live_route

    runtime = FakeRuntime()
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "session-dir")
    monkeypatch.setattr(agent_route, "_owner_resolver", lambda _body: None)
    monkeypatch.setattr(agent_route, "_work_resolver", lambda _body, _owner: None)

    def forbidden_packet_load(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("generic no-scope route loaded a live session packet")

    monkeypatch.setattr(live_route, "load_session", forbidden_packet_load)
    app = FastAPI()
    app.include_router(live_router)
    app.state.agent_turn_runtime = runtime
    matches = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/live/agent/turn"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(matches) == 1
    legacy_matches = [
        route
        for route in live_router.routes
        if getattr(route, "path", None) == "/api/live/query"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(legacy_matches) == 1
    response = agent_route.post_agent_turn(
        AgentTurnRequest.model_validate(_payload()),
        SimpleNamespace(app=app),
    )
    body = response
    assert body["answer"]["text"] == "A simple answer."
    assert body["answer"]["graph_grounded"] is False
    assert body["graph"]["status"] == "not_requested"
    assert len(runtime.invocations) == 1
    assert runtime.invocations[0].context_packet.world_scope is None
    assert runtime.invocations[0].context_packet.retrieval_session is None
    assert (tmp_path / "session-dir" / "hermes_thread_pointers.json").is_file()


def test_request_validation_rejects_unknown_or_contradictory_fields() -> None:
    from apps.live_control_server.models.agent_turn import AgentTurnRequest

    payload = _payload()
    saved_work = {
        **payload,
        "primary_work": {
            "kind": "plan",
            "document_id": "plan-1",
            "expected_revision": 1,
        },
        "client_work_state": "saved_clean",
    }
    for invalid in (
        {**payload, "untrusted_resolved_scope": "world:fake"},
        {**payload, "graph_selection": {"node_id": "node:stacy"}},
        {**payload, "message": " " * 8_001},
        {**payload, "message": " \t\n "},
        {
            **saved_work,
            "primary_work": {**saved_work["primary_work"], "expected_revision": 0},
        },
        {
            **saved_work,
            "primary_work": {**saved_work["primary_work"], "expected_revision": "1"},
        },
        {**payload, "client_work_state": "saved_clean"},
        {
            **payload,
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 1,
            },
            "client_work_state": "saved_clean",
        },
        {
            **payload,
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 1,
                "expected_revision_n": 2,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_clean",
            "graph_request": {
                "mode": "world",
                "world_id": "world-1",
                "campaign_id": None,
                "revision_pin": None,
                "focus": {"kind": "none", "session_id": None, "campaign_id": None},
            },
        },
        {
            **payload,
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 1,
                "expected_revision_n": 2,
                "expected_content_sha256": "b" * 63,
            },
            "client_work_state": "saved_clean",
        },
    ):
        try:
            AgentTurnRequest.model_validate(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid turn request was accepted")


def test_plan_resolver_reads_exact_committed_world_revision_and_returns_basis(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.routes import agent as agent_route

    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    basis = {
        "world_id": "world-1",
        "document_id": "plan-1",
        "object_revision": 4,
        "work_revision_id": "work-revision-8",
        "revision_n": 8,
        "markdown": "# Saved plan\n\nThe sealed phrase is amber lantern.\n",
        "content_sha256": "b" * 64,
        "committed_status": "committed",
        "has_divergent_working_copy": True,
    }
    observed: dict[str, Any] = {}

    def read_exact(document_id: str, **kwargs: Any) -> Any:
        observed["document_id"] = document_id
        observed.update(kwargs)
        return SimpleNamespace(**basis)

    monkeypatch.setattr(agent_route, "get_current_world_plan_revision", read_exact)
    monkeypatch.setattr(
        agent_route,
        "get_workspace_document",
        lambda *_args: pytest.fail(
            "pinned Plan turns must use the atomic Content read"
        ),
    )
    monkeypatch.setattr(
        agent_route,
        "get_committed_playable_revision",
        lambda *_args, **_kwargs: pytest.fail(
            "pinned Plan turns must not mix revision reads"
        ),
    )
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 4,
                "expected_revision_n": 8,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_dirty",
        }
    )
    work = agent_route._work_resolver(request, {"kind": "world", "id": "world-1"})
    assert work is not None
    assert work.revision == 4
    assert work.changed_since_expected is False
    assert work.surface_context.current_work.object_revision == 4
    assert work.plan_markdown == basis["markdown"]
    assert work.content_basis.model_dump() == {
        key: value for key, value in basis.items() if key != "markdown"
    }
    assert observed == {
        "document_id": "plan-1",
        "expected_world_id": "world-1",
        "expected_revision": 4,
        "expected_revision_n": 8,
        "expected_content_sha256": "b" * 64,
    }


def test_plan_resolver_fails_stale_pin_before_agent_dispatch(monkeypatch: Any) -> None:
    from apps.live_control_server.routes import agent as agent_route

    def stale_read(*_args: Any, **_kwargs: Any) -> Any:
        raise agent_route.WorkspaceDocumentRegistryError(
            "World Plan current revision does not match the requested pin",
            status_code=409,
        )

    monkeypatch.setattr(agent_route, "get_current_world_plan_revision", stale_read)
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 4,
                "expected_revision_n": 8,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_dirty",
        }
    )

    with pytest.raises(agent_route.AgentTurnServiceError) as exc_info:
        agent_route._work_resolver(request, {"kind": "world", "id": "world-1"})

    assert exc_info.value.code == "plan_revision_changed"
    assert exc_info.value.status_code == 409


def test_plan_agent_route_dispatches_only_atomic_committed_content(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import json

    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    managed_world = create_world_container(tmp_path, name="Plan Ask World")
    markdown = "# Saved Plan\n\nThe keeper waits below the black arch.\n"
    basis = {
        "world_id": managed_world.world_id,
        "document_id": "plan-1",
        "object_revision": 7,
        "work_revision_id": "work-revision-4",
        "revision_n": 4,
        "markdown": markdown,
        "content_sha256": "b" * 64,
        "committed_status": "committed",
        "has_divergent_working_copy": True,
    }
    observed: dict[str, Any] = {}

    def read_atomic(document_id: str, **kwargs: Any) -> Any:
        observed["document_id"] = document_id
        observed.update(kwargs)
        return SimpleNamespace(**basis)

    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(agent_route, "get_current_world_plan_revision", read_atomic)
    monkeypatch.setattr(
        agent_route,
        "get_workspace_document",
        lambda *_args: pytest.fail(
            "Plan Ask must not perform a separate metadata read"
        ),
    )
    monkeypatch.setattr(
        agent_route,
        "get_committed_playable_revision",
        lambda *_args, **_kwargs: pytest.fail(
            "Plan Ask must use the atomic current Content read"
        ),
    )
    runtime = FakeRuntime()
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 7,
                "expected_revision_n": 4,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_dirty",
            "message": "What is beneath the black arch?",
        }
    )
    app = SimpleNamespace(state=SimpleNamespace(agent_turn_runtime=runtime))

    response = agent_route.post_agent_turn(request, SimpleNamespace(app=app))

    assert observed == {
        "document_id": "plan-1",
        "expected_world_id": managed_world.world_id,
        "expected_revision": 7,
        "expected_revision_n": 4,
        "expected_content_sha256": "b" * 64,
    }
    assert len(runtime.invocations) == 1
    _prefix, payload = runtime.invocations[0].message.split("\n", maxsplit=1)
    assert json.loads(payload) == {
        "committed_plan_markdown": markdown,
        "user_question": "What is beneath the black arch?",
    }
    assert response["graph"]["status"] == "not_requested"
    assert response["primary_work"]["content_basis"] == {
        key: value for key, value in basis.items() if key != "markdown"
    }
    assert markdown not in json.dumps(response)


def test_plan_agent_route_rejects_stale_pin_before_runtime_dispatch(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from fastapi import HTTPException

    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    managed_world = create_world_container(tmp_path, name="Stale Plan Ask World")

    def stale_read(*_args: Any, **_kwargs: Any) -> Any:
        raise agent_route.WorkspaceDocumentRegistryError(
            "World Plan current revision does not match the requested pin",
            status_code=409,
        )

    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(agent_route, "get_current_world_plan_revision", stale_read)
    runtime = FakeRuntime()
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 7,
                "expected_revision_n": 4,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_clean",
        }
    )
    app = SimpleNamespace(state=SimpleNamespace(agent_turn_runtime=runtime))

    with pytest.raises(HTTPException) as exc_info:
        agent_route.post_agent_turn(request, SimpleNamespace(app=app))

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "plan_revision_changed"
    assert runtime.invocations == []
    assert not (tmp_path / "sessions" / "hermes_thread_pointers.json").exists()


def test_plan_agent_route_reads_actual_committed_content_and_excludes_divergent_draft(
    tmp_path: Path,
    monkeypatch: Any,
    application_state_dsn: str,
) -> None:
    import json

    from application_state.content.service import (
        autosave_plan,
        commit_plan,
        create_world_plan,
        read_current_world_plan_revision,
    )
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    assert application_state_dsn
    managed_world = create_world_container(tmp_path, name="Atomic Plan Ask World")
    created = create_world_plan(
        title="Atomic Plan Ask",
        world_id=managed_world.world_id,
    )
    markdown = "# Atomic Plan\n\nThe keeper waits below the black arch.\n"
    draft_markdown = "# Local draft\n\nThe draft says the arch is empty.\n"
    _committed_object, committed = commit_plan(
        str(created.work_object_id),
        markdown,
        expected_world_id=managed_world.world_id,
    )
    draft = autosave_plan(
        str(created.work_object_id),
        draft_markdown,
        expected_world_id=managed_world.world_id,
    )
    current = read_current_world_plan_revision(
        str(created.work_object_id),
        expected_world_id=managed_world.world_id,
        expected_revision=draft.object_revision,
        expected_revision_n=committed.revision_n,
        expected_content_sha256=committed.content_sha256,
    )
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    runtime = FakeRuntime()
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
            "primary_work": {
                "kind": "plan",
                "object_id": str(created.work_object_id),
                "expected_revision": current.object_revision,
                "expected_revision_n": current.revision_n,
                "expected_content_sha256": current.content_sha256,
            },
            "client_work_state": "saved_dirty",
            "message": "What is beneath the black arch?",
        }
    )
    app = SimpleNamespace(state=SimpleNamespace(agent_turn_runtime=runtime))

    response = agent_route.post_agent_turn(request, SimpleNamespace(app=app))

    assert len(runtime.invocations) == 1
    _prefix, payload = runtime.invocations[0].message.split("\n", maxsplit=1)
    assert json.loads(payload) == {
        "committed_plan_markdown": markdown,
        "user_question": "What is beneath the black arch?",
    }
    assert draft_markdown not in runtime.invocations[0].message
    assert response["primary_work"]["content_basis"] == {
        "world_id": managed_world.world_id,
        "document_id": str(created.work_object_id),
        "object_revision": current.object_revision,
        "work_revision_id": str(committed.work_revision_id),
        "revision_n": committed.revision_n,
        "content_sha256": committed.content_sha256,
        "committed_status": "committed",
        "has_divergent_working_copy": True,
    }
    assert markdown not in json.dumps(response)
    after = read_current_world_plan_revision(
        str(created.work_object_id),
        expected_world_id=managed_world.world_id,
        expected_revision=current.object_revision,
        expected_revision_n=current.revision_n,
        expected_content_sha256=current.content_sha256,
    )
    assert after.markdown == markdown
    assert after.has_divergent_working_copy is True


def test_campaign_id_equal_to_world_id_is_not_world_plan_ownership(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
        execute_agent_turn,
    )
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    managed_world = create_world_container(tmp_path, name="World Alias Test")
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        agent_route,
        "get_workspace_document",
        lambda _root, _document_id: SimpleNamespace(
            kind="plan",
            status="active",
            world_id=None,
            campaign_id=managed_world.world_id,
            target_session=None,
            document_id="plan-campaign-only",
            title="Campaign-only Plan",
        ),
    )
    monkeypatch.setattr(
        agent_route,
        "get_committed_playable_revision",
        lambda _document_id, **_kwargs: SimpleNamespace(
            status="active",
            document_id="plan-campaign-only",
            title="Campaign-only Plan",
            object_revision=1,
        ),
    )
    payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
        "primary_work": {
            "kind": "plan",
            "object_id": "plan-campaign-only",
            "expected_revision": 1,
        },
        "client_work_state": "saved_clean",
    }
    request = AgentTurnRequest.model_validate(payload)
    runtime = FakeRuntime()
    pointer_store = HermesSessionPointerStore(tmp_path / "pointer-store")

    with pytest.raises(AgentTurnServiceError) as exc_info:
        execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=agent_route._owner_resolver,
            work_resolver=agent_route._work_resolver,
            graph_resolver=lambda *_args: pytest.fail("no-graph turn resolved a graph"),
            runtime=runtime,
        )

    assert exc_info.value.code == "work_foreign"
    assert runtime.invocations == []
    assert not (tmp_path / "pointer-store" / "hermes_thread_pointers.json").exists()


def test_graph_focus_must_match_session_id_derived_from_saved_plan(
    monkeypatch: Any,
) -> None:
    from types import SimpleNamespace

    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    monkeypatch.setattr(agent_route, "repo_root", lambda: Path("/tmp"))
    monkeypatch.setattr(agent_route, "get_world_container", lambda *_args: object())
    monkeypatch.setattr(
        agent_route,
        "build_existing_graph_context",
        lambda *_args, **_kwargs: (
            {"status": "empty"},
            AgentWorldScope(
                world_id="world-1",
                campaign_id="campaign-1",
                focus={
                    "kind": "session",
                    "session_id": "session-23",
                    "campaign_id": "campaign-1",
                },
                admissibility="gm",
                revision_id="rev-1",
                scope_mode="world",
            ),
        ),
    )
    work = SimpleNamespace(
        owner_id="world-1",
        world_id="world-1",
        campaign_id="campaign-1",
        target_session=23,
        session_id="session-23",
    )
    request_payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": "world-1"},
        "primary_work": {
            "kind": "plan",
            "object_id": "plan-1",
            "expected_revision": 1,
        },
        "client_work_state": "saved_clean",
        "graph_request": {
            "mode": "world",
            "world_id": "world-1",
            "campaign_id": "campaign-1",
            "revision_pin": None,
            "focus": {
                "kind": "session",
                "session_id": "session-23",
                "campaign_id": "campaign-1",
            },
        },
    }
    request = AgentTurnRequest.model_validate(request_payload)
    _envelope, scope = agent_route._graph_resolver(
        request, {"kind": "world", "id": "world-1"}, work
    )
    assert scope.focus["session_id"] == "session-23"

    request_payload["graph_request"]["focus"]["session_id"] = "session-24"
    mismatched = AgentTurnRequest.model_validate(request_payload)
    try:
        agent_route._graph_resolver(
            mismatched, {"kind": "world", "id": "world-1"}, work
        )
    except AgentTurnServiceError as exc:
        assert exc.code == "graph_focus_rejected"
    else:
        raise AssertionError("mismatched session focus was accepted")


def test_full_application_http_route_and_legacy_route_cardinality(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.main import create_app
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.routes import live as live_route

    runtime = FakeRuntime()
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(agent_route, "_owner_resolver", lambda _body: None)
    monkeypatch.setattr(agent_route, "_work_resolver", lambda _body, _owner: None)

    def forbidden_packet_load(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("no-graph HTTP turn loaded a legacy session packet")

    monkeypatch.setattr(live_route, "load_session", forbidden_packet_load)
    app = create_app()
    app.state.agent_turn_runtime = runtime
    agent_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/live/agent/turn"
        and "POST" in getattr(route, "methods", set())
    ]
    legacy_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/live/query"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(agent_routes) == 1
    assert len(legacy_routes) == 1

    async def post_turn() -> httpx.Response:
        # ASGITransport exercises the full HTTP app without starting its
        # provider-worker lifespan; this test injects a deterministic runtime.
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post("/api/live/agent/turn", json=_payload())

    response = asyncio.run(post_turn())

    assert response.status_code == 200
    body = response.json()
    assert body["surface"]["surface_id"] == "index"
    assert body["graph"]["status"] == "not_requested"
    assert body["answer"]["graph_grounded"] is False
    assert runtime.invocations[0].context_packet.surface_context.surface_id == "index"
    assert runtime.invocations[0].context_packet.world_scope is None
    assert runtime.invocations[0].context_packet.retrieval_session is None


def test_verified_world_projection_reaches_runtime_through_full_http_route(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.config import (
        WORLD_GRAPH_AUTHORITY_DUNGEONMIND,
        WORLD_GRAPH_AUTHORITY_ENV,
        WORLD_GRAPH_ROOT_ENV,
    )
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from apps.live_control_server.main import create_app
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.memory import (
        InMemorySourceRepository,
        InMemoryWorldGraphRepository,
    )
    from tests._cutover_direct_dungeonmind_read_helpers import (
        WORLD_ID as FIXTURE_WORLD_ID,
        NOW,
        _FakeBundle,
        _payload as direct_payload,
        _receipt,
        _seed_sources,
    )

    managed_world = create_world_container(tmp_path, name="Agent Projection Test World")
    world_root = tmp_path / "isolated-world-root"
    monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_ENV, WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setenv(WORLD_GRAPH_ROOT_ENV, str(world_root))
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(agent_route, "world_graph_root", lambda: world_root)

    def remap_fixture_ids(value: Any) -> Any:
        if value == FIXTURE_WORLD_ID:
            return managed_world.world_id
        if isinstance(value, dict):
            return {key: remap_fixture_ids(item) for key, item in value.items()}
        if isinstance(value, list):
            return [remap_fixture_ids(item) for item in value]
        return value

    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=managed_world.world_id,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:agent-real-projection"],
            graph_schema="dm_union_graph_v6",
            graph_payload=remap_fixture_ids(direct_payload()),
            created_at=NOW,
        )
    )
    seeded_sources = _seed_sources()
    sources = InMemorySourceRepository()
    for artifact_id in (
        "src:world-lore",
        "src:one-notes",
        "src:one-recap",
        "src:player-sign",
    ):
        artifact = seeded_sources.get_artifact(artifact_id)
        assert artifact is not None
        sources.put_artifact(
            artifact.model_copy(update={"world_id": managed_world.world_id})
        )
        revision = seeded_sources.get_revision(artifact.current_revision_id)
        assert revision is not None
        sources.put_revision(revision)
    services = direct.direct_services_from_bundle(
        _FakeBundle(
            world_graph,
            sources,
            _receipt(managed_world.world_id, published.revision_id),
        ),
        managed_world.world_id,
    )

    def direct_services_for_world(world_id: str) -> Any:
        assert world_id == managed_world.world_id
        return services

    monkeypatch.setattr(
        direct, "direct_services_from_config", direct_services_for_world
    )
    runtime = FakeRuntime()
    app = create_app()
    app.state.agent_turn_runtime = runtime
    payload = {
        **_payload(),
        "surface": {"surface_id": "plan", "instance_id": "world-plan-main"},
        "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
        "graph_request": {
            "mode": "world",
            "world_id": managed_world.world_id,
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        },
        "message": "Where is the tavern?",
    }

    async def post_turn() -> httpx.Response:
        # Keep the real application/router/HTTP path, but leave the external
        # agent-worker lifecycle outside this deterministic integration test.
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post("/api/live/agent/turn", json=payload)

    response = asyncio.run(post_turn())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["owner_scope"]["owner_id"] == managed_world.world_id
    assert body["graph"]["status"] == "ready"
    assert body["graph"]["revision_id"] == published.revision_id
    assert body["graph"]["head_revision_id"] == published.revision_id
    invocation = runtime.invocations[0]
    assert invocation.context_packet.world_scope is not None
    assert invocation.context_packet.world_scope.world_id == managed_world.world_id
    assert invocation.context_packet.world_scope.revision_id == published.revision_id
    assert invocation.context_packet.retrieval_session is not None
    packet_text = str(invocation.context_packet.retrieval_session.packet)
    assert "The Prancing Tavern" in packet_text
