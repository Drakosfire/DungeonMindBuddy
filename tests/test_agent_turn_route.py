from __future__ import annotations

from pathlib import Path
from typing import Any
from types import SimpleNamespace

from fastapi import FastAPI

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
        route for route in app.routes
        if getattr(route, "path", None) == "/api/live/agent/turn"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(matches) == 1
    legacy_matches = [
        route for route in live_router.routes
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
    ):
        try:
            AgentTurnRequest.model_validate(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid turn request was accepted")


def test_plan_resolver_reports_current_committed_revision_without_working_copy(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from types import SimpleNamespace
    from apps.live_control_server.routes import agent as agent_route

    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        agent_route,
        "get_workspace_document",
        lambda _root, _document_id: SimpleNamespace(
            kind="plan",
            status="active",
            world_id="world-1",
            campaign_id=None,
            target_session=23,
            document_id="plan-1",
            title="Saved plan",
            revision=4,
        ),
    )
    monkeypatch.setattr(
        agent_route,
        "get_committed_playable_revision",
        lambda _document_id, **_kwargs: SimpleNamespace(
            status="active",
            world_id="world-1",
            campaign_id=None,
            document_id="plan-1",
            title="Saved plan",
            object_revision=4,
            revision_n=8,
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
                "expected_revision": 3,
            },
            "client_work_state": "saved_dirty",
        }
    )
    work = agent_route._work_resolver(request, {"kind": "world", "id": "world-1"})
    assert work is not None
    assert work.revision == 4
    assert work.changed_since_expected is True
    assert work.surface_context.current_work.object_revision == 4
    assert work.session_id == "session-23"


def test_graph_focus_must_match_session_id_derived_from_saved_plan(monkeypatch: Any) -> None:
    from types import SimpleNamespace

    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError

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
                focus={"kind": "session", "session_id": "session-23", "campaign_id": "campaign-1"},
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
