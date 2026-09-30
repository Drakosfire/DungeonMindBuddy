from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services.agent_runtime import (
    CONVERSATION_ONLY_POLICY_ID,
    AgentRuntimeDescriptor,
    AgentRuntimeResult,
)
from apps.live_control_server.services.agent_turn_service import (
    AgentTurnServiceError,
    execute_agent_turn,
)
from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore


def _request(**updates: Any) -> AgentTurnRequest:
    payload: dict[str, Any] = {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "thread-1",
        "turn_id": "turn-1",
        "surface": {"surface_id": "index", "instance_id": "index-main"},
        "owner_scope": None,
        "primary_work": None,
        "client_work_state": "none",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "message": "Hello there",
    }
    payload.update(updates)
    return AgentTurnRequest.model_validate(payload)


class FakeRuntime:
    descriptor = AgentRuntimeDescriptor(
        runtime_id="fake", trace_backend="fake", trace_runtime="test", trace_mode="conversation"
    )

    def __init__(self) -> None:
        self.invocations = []

    def run(self, invocation: Any) -> AgentRuntimeResult:
        self.invocations.append(invocation)
        return AgentRuntimeResult(
            status="ok",
            final_text="Hello.",
            runtime_session_id="runtime-session-1",
        )


def test_no_graph_turn_uses_no_scope_runtime_and_only_structured_pointer_store(
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime()

    def unexpected_graph(*_args: Any) -> Any:
        raise AssertionError("no-graph turn must not resolve graph authority")

    response = execute_agent_turn(
        _request(),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointer-only"),
        owner_resolver=lambda _request: None,
        work_resolver=lambda _request, _owner: None,
        graph_resolver=unexpected_graph,
        runtime=runtime,
    )

    assert len(runtime.invocations) == 1
    invocation = runtime.invocations[0]
    assert invocation.context_packet.world_scope is None
    assert invocation.context_packet.retrieval_session is None
    assert invocation.capability_policy.policy_id == CONVERSATION_ONLY_POLICY_ID
    assert response.graph.status == "not_requested"
    assert response.answer.graph_grounded is False
    assert response.conversation.pointer_id
    pointer_path = tmp_path / "pointer-only" / "hermes_thread_pointers.json"
    assert pointer_path.is_file()


@pytest.mark.parametrize(
    ("surface_id", "label"),
    [
        ("index", "Index"),
        ("plan", "Plan"),
        ("play", "Play"),
        ("build", "Build"),
        ("ingest", "Ingest"),
        ("combat", "Combat Tracker"),
    ],
)
def test_no_work_turn_carries_surface_and_verified_world_through_real_adapters(
    tmp_path: Path, surface_id: str, label: str
) -> None:
    from apps.live_control_server.services.agent_surface_context import (
        render_agent_surface_context,
    )
    from apps.live_control_server.services.hermes_agent_runtime import (
        map_invocation_to_hermes_request,
    )
    from apps.live_control_server.services.hermes_graph_agent import (
        _build_ephemeral_system_prompt,
    )
    from apps.live_control_server.services.pydantic_ai_agent_runtime import (
        pydantic_ai_agent_instructions,
    )

    runtime = FakeRuntime()
    request = _request(
        surface={"surface_id": surface_id, "instance_id": f"{surface_id}-pane-1"},
        owner_scope={"kind": "world", "world_id": "world:one"},
    )
    execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: {
            "kind": "world",
            "id": "world:one",
            "name": "The Glass Orchard",
        },
        work_resolver=lambda _request, _owner: None,
        graph_resolver=lambda *_args: pytest.fail("no-graph turn resolved graph authority"),
        runtime=runtime,
    )

    invocation = runtime.invocations[0]
    context = invocation.context_packet.surface_context
    assert context is not None
    assert context.surface_id == surface_id
    assert context.surface_instance_id == f"{surface_id}-pane-1"
    assert context.current_owner is not None
    assert context.current_owner.owner_id == "world:one"
    assert invocation.context_packet.world_scope is None
    assert invocation.context_packet.retrieval_session is None
    rendered = render_agent_surface_context(context)
    assert rendered is not None
    assert label in rendered
    assert 'Current World: "The Glass Orchard"' in rendered
    assert "world:one" not in rendered

    hermes_request = map_invocation_to_hermes_request(invocation)
    assert hermes_request.world_id is None
    assert hermes_request.campaign_id is None
    assert hermes_request.retrieval_session is None
    assert hermes_request.capability_policy.mode == "conversation_only"
    assert hermes_request.capability_policy.graph_scope is None
    assert hermes_request.capability_policy.enabled_toolsets == ()
    hermes_prompt = _build_ephemeral_system_prompt(
        hermes_request.capability_policy,
        hermes_request,
        retrieval_session_packet=None,
    )
    assert label in hermes_prompt
    assert 'Current World: "The Glass Orchard"' in hermes_prompt

    pydantic_prompt = pydantic_ai_agent_instructions(invocation)
    assert label in pydantic_prompt
    assert 'Current World: "The Glass Orchard"' in pydantic_prompt
    assert "No graph retrieval is performed on this turn" in pydantic_prompt


def test_graphless_followup_reuses_same_binding_without_current_graph_authority(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from apps.live_control_server.services.hermes_agent_runtime import (
        map_invocation_to_hermes_request,
    )
    from apps.live_control_server.services.hermes_graph_agent import (
        _build_ephemeral_system_prompt,
    )

    runtime = FakeRuntime()
    pointer_store = HermesSessionPointerStore(tmp_path / "pointers")
    def owner(_request):
        return {
            "kind": "world",
            "id": "world:one",
            "name": "The Glass Orchard",
        }

    def graph(_request, _owner, _work):
        return (
            {
                "status": "ready",
                "world_id": "world:one",
                "campaign_id": "",
                "scope_mode": "world",
                "revision_id": "revision-one",
                "head_revision_id": "revision-one",
                "is_head": True,
                "focus": {"kind": "none"},
                "matched_node_ids": ["node:one"],
                "nodes": [{"node_id": "node:one", "label": "The Glass Orchard"}],
            },
            AgentWorldScope(
                world_id="world:one",
                campaign_id="",
                focus={"kind": "none"},
                admissibility="gm",
                revision_id="revision-one",
                scope_mode="world",
            ),
        )

    first = _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
        graph_request={
            "mode": "world",
            "world_id": "world:one",
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        },
    )
    execute_agent_turn(
        first,
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=owner,
        work_resolver=lambda _request, _owner: None,
        graph_resolver=graph,
        runtime=runtime,
    )
    second = _request(
        turn_id="turn-2",
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
    )
    response = execute_agent_turn(
        second,
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=owner,
        work_resolver=lambda _request, _owner: None,
        graph_resolver=lambda *_args: pytest.fail("graphless follow-up must not retrieve"),
        runtime=runtime,
    )

    assert runtime.invocations[1].run_options.runtime_session_id == "runtime-session-1"
    assert runtime.invocations[1].context_packet.world_scope is None
    assert runtime.invocations[1].context_packet.retrieval_session is None
    assert response.graph.status == "not_requested"
    assert response.answer.graph_grounded is False
    assert response.conversation.pointer_status == "reused"
    hermes_request = map_invocation_to_hermes_request(runtime.invocations[1])
    prompt = _build_ephemeral_system_prompt(
        hermes_request.capability_policy,
        hermes_request,
        retrieval_session_packet=None,
    )
    assert "No graph retrieval is performed on this turn" in prompt
    assert "historical graph-derived statements" in prompt
    assert "not revalidated as current graph evidence" in prompt
    assert "request an explicit graph-retrieval turn" in prompt


def test_unresolvable_requested_graph_fails_before_runtime(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    request = _request(
        graph_request={
            "mode": "world",
            "world_id": "world-1",
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        }
    )

    def reject_graph(*_args: Any) -> Any:
        raise AgentTurnServiceError("foreign graph", code="graph_scope_rejected", status_code=403)

    with pytest.raises(AgentTurnServiceError, match="foreign graph"):
        execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
            owner_resolver=lambda _request: None,
            work_resolver=lambda _request, _owner: None,
            graph_resolver=reject_graph,
            runtime=runtime,
        )
    assert runtime.invocations == []


def test_successful_plan_turn_returns_one_sanitized_trace_event(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    prompt_secret = "plan-prompt-secret-6d3b"
    runtime = FakeRuntime()
    request = _request(
        message=prompt_secret,
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:plan"},
    )

    with caplog.at_level(logging.INFO, logger="dmb.agent.turn_trace"):
        response = execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
            owner_resolver=lambda _request: {
                "kind": "world",
                "id": "world:plan",
                "name": "Trace Test World",
            },
            work_resolver=lambda _request, _owner: None,
            graph_resolver=lambda *_args: pytest.fail(
                "graphless Plan turn must not resolve graph authority"
            ),
            runtime=runtime,
        )

    trace = response.answer.trace
    trace_events = [
        record.getMessage()
        for record in caplog.records
        if record.name == "dmb.agent.turn_trace"
        and record.getMessage().startswith("dmb_agent_turn_trace ")
    ]

    assert response.answer.status == "ok"
    assert trace["status"] == "ok"
    assert len(trace_events) == 1
    logged_trace = json.loads(trace_events[0].removeprefix("dmb_agent_turn_trace "))
    assert logged_trace["trace_id"] == trace["trace_id"]
    assert prompt_secret not in trace_events[0]
