"""Hermes adapter for the DungeonBuddy AgentRuntime port.

Translates ``AgentRuntimeInvocation`` onto the existing process-isolated
Hermes host and maps the host result back. Does not resolve World scope,
create retrieval sessions, validate grounding, or finalize A0 traces.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from apps.live_control_server.services.agent_runtime import (
    HERMES_RUNTIME_DESCRIPTOR,
    UNSUPPORTED_CAPABILITY_POLICY,
    WORLD_GRAPH_READ_POLICY_ID,
    AgentRuntimeDescriptor,
    AgentRuntimeInvocation,
    AgentRuntimeResult,
    AgentRuntimeToolEvent,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnRequest,
    HermesGraphAgentTurnResult,
    HermesGraphToolEvent,
)
from apps.live_control_server.services.hermes_graph_agent_host import (
    HermesGraphAgentHost,
    get_hermes_graph_agent_host,
)
from graph_memory.hermes_graph_plugin import (
    HermesGraphScope,
    default_graph_only_capability_policy,
)

HostFactory = Callable[[], HermesGraphAgentHost]


def _api_focus_to_host_focus(focus: Mapping[str, Any] | None) -> dict[str, str | None]:
    if focus is None:
        return {"kind": "none", "sessionId": None, "campaignId": None}
    kind = str(focus.get("kind") or "none")
    session_id = focus.get("session_id", focus.get("sessionId"))
    if session_id is not None:
        session_id = str(session_id)
    campaign_id = focus.get("campaign_id", focus.get("campaignId"))
    if campaign_id is not None:
        campaign_id = str(campaign_id)
    return {"kind": kind, "sessionId": session_id, "campaignId": campaign_id}


def _host_worker_pid(host: HermesGraphAgentHost) -> int | None:
    worker_pid = getattr(host, "worker_pid", None)
    if callable(worker_pid):
        pid = worker_pid()
        return pid if isinstance(pid, int) else None
    return worker_pid if isinstance(worker_pid, int) else None


def _map_tool_event(event: HermesGraphToolEvent) -> AgentRuntimeToolEvent:
    focus = event.focus
    attributes: dict[str, Any] = {
        "world_id": event.world_id,
        "campaign_id": event.campaign_id,
        "focus": None if focus is None else dict(focus),
        "admissibility": event.admissibility,
        "revision_pin": event.revision_pin,
        "bounded_ids": dict(event.bounded_ids),
        "retrieval_schema": event.retrieval_schema,
        "outcome": event.outcome,
        "matched_node_ids": list(event.matched_node_ids),
        "relationship_ids": list(event.relationship_ids),
        "source_anchor_ids": list(event.source_anchor_ids),
        "diagnostic_codes": list(event.diagnostic_codes),
    }
    return AgentRuntimeToolEvent(
        tool_name=event.tool_name,
        state=event.state,
        duration_ms=event.duration_ms,
        attributes=attributes,
    )


def _unsupported_policy_result(policy_id: str) -> AgentRuntimeResult:
    return AgentRuntimeResult(
        status="error",
        error_code=UNSUPPORTED_CAPABILITY_POLICY,
        error_message=(
            f"Unsupported Agent capability policy {policy_id!r}; "
            f"expected {WORLD_GRAPH_READ_POLICY_ID!r}."
        ),
        runtime_metadata={"process_isolation": "process_exclusive"},
    )


def map_invocation_to_hermes_request(
    invocation: AgentRuntimeInvocation,
) -> HermesGraphAgentTurnRequest:
    world_scope = invocation.context_packet.world_scope
    host_focus = _api_focus_to_host_focus(world_scope.focus)
    graph_scope = HermesGraphScope(
        world_id=world_scope.world_id,
        campaign_id=world_scope.campaign_id,
        focus=host_focus,
        admissibility=world_scope.admissibility,
        revision_pin=world_scope.revision_id,
    )
    retrieval = invocation.context_packet.retrieval_session
    history = (
        [{"role": item["role"], "content": item["content"]} for item in invocation.conversation_history]
        if invocation.conversation_history
        else None
    )
    execution_root = invocation.run_options.execution_root
    root = execution_root.resolve() if isinstance(execution_root, Path) else execution_root
    return HermesGraphAgentTurnRequest(
        question=invocation.message,
        world_id=world_scope.world_id,
        campaign_id=world_scope.campaign_id,
        focus=host_focus,
        admissibility=world_scope.admissibility,
        revision_pin=world_scope.revision_id,
        conversation_history=history,
        session_id=invocation.run_options.runtime_session_id,
        root=root,
        capability_policy=default_graph_only_capability_policy(graph_scope),
        retrieval_session_id=None if retrieval is None else retrieval.session_id,
        retrieval_session=None if retrieval is None else retrieval.packet,
    )


def map_hermes_result_to_runtime_result(
    result: HermesGraphAgentTurnResult,
    *,
    worker_pid: int | None = None,
) -> AgentRuntimeResult:
    context_updates: dict[str, Any] = {}
    if result.retrieval_session_id:
        context_updates["retrieval_session_id"] = result.retrieval_session_id
    if result.retrieval_session is not None:
        context_updates["retrieval_session"] = dict(result.retrieval_session)
    runtime_metadata: dict[str, Any] = {
        "process_isolation": result.process_isolation,
    }
    if worker_pid is not None:
        runtime_metadata["worker_pid"] = worker_pid
    session_id = str(result.hermes_session_id or "").strip() or None
    return AgentRuntimeResult(
        status=result.status,
        final_text=result.final_response,
        messages=list(result.messages),
        runtime_session_id=session_id,
        answer_scope=result.answer_scope,
        tool_events=[_map_tool_event(event) for event in result.tool_events],
        model_calls=list(result.model_calls),
        telemetry_warnings=list(result.telemetry_warnings),
        observed_model_call_count=result.observed_model_call_count,
        context_updates=context_updates,
        runtime_metadata=runtime_metadata,
        error_code=result.error_code,
        error_message=result.error_message,
    )


class HermesAgentRuntimeAdapter:
    """Thin translation boundary around ``HermesGraphAgentHost.execute``."""

    def __init__(self, *, host_factory: HostFactory | None = None) -> None:
        self._host_factory = host_factory or get_hermes_graph_agent_host
        self.descriptor: AgentRuntimeDescriptor = HERMES_RUNTIME_DESCRIPTOR

    def run(self, invocation: AgentRuntimeInvocation) -> AgentRuntimeResult:
        policy_id = invocation.capability_policy.policy_id
        if policy_id != WORLD_GRAPH_READ_POLICY_ID:
            return _unsupported_policy_result(policy_id)
        request = map_invocation_to_hermes_request(invocation)
        host = self._host_factory()
        result = host.execute(request)
        return map_hermes_result_to_runtime_result(
            result,
            worker_pid=_host_worker_pid(host),
        )


def default_hermes_agent_runtime() -> HermesAgentRuntimeAdapter:
    return HermesAgentRuntimeAdapter()
