from __future__ import annotations

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
