"""Hermes adapter for the DungeonBuddy AgentRuntime port.

Translates ``AgentRuntimeInvocation`` onto the existing process-isolated
Hermes host and maps the host result back. Does not resolve World scope,
create retrieval sessions, validate grounding, or finalize A0 traces.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from apps.live_control_server.services.agent_runtime import (
    CONVERSATION_ONLY_POLICY_ID,
    HERMES_RUNTIME_DESCRIPTOR,
    UNSUPPORTED_CAPABILITY_POLICY,
    WORLD_GRAPH_READ_POLICY_ID,
    AgentRuntimeDescriptor,
    AgentRuntimeInvocation,
    AgentRuntimeResult,
    AgentRuntimeToolEvent,
)
from apps.live_control_server.services.agent_surface_context import (
    render_agent_surface_context,
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
    default_conversation_only_capability_policy,
    default_graph_only_capability_policy,
    parent_brokered_graph_expansion_policy,
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
    if world_scope is None:
        if (
            invocation.capability_policy.policy_id != CONVERSATION_ONLY_POLICY_ID
            or invocation.context_packet.retrieval_session is not None
        ):
            raise ValueError(
                "no-scope turn requires conversation-only policy and no retrieval session"
            )
        host_focus = None
        capability_policy = default_conversation_only_capability_policy()
        world_id = campaign_id = scope_mode = admissibility = revision_pin = None
    else:
        if invocation.capability_policy.policy_id != WORLD_GRAPH_READ_POLICY_ID:
            raise ValueError("graph scope requires the graph-read capability policy")
        host_focus = _api_focus_to_host_focus(world_scope.focus)
        graph_scope = HermesGraphScope(
            world_id=world_scope.world_id,
            campaign_id=world_scope.campaign_id,
            scope_mode=world_scope.scope_mode,
            focus=host_focus,
            admissibility=world_scope.admissibility,
            revision_pin=world_scope.revision_id,
        )
        capability_policy = default_graph_only_capability_policy(graph_scope)
        world_id = world_scope.world_id
        campaign_id = world_scope.campaign_id
        scope_mode = world_scope.scope_mode
        admissibility = world_scope.admissibility
        revision_pin = world_scope.revision_id
    retrieval = invocation.context_packet.retrieval_session
    history = (
        [
            {"role": item["role"], "content": item["content"]}
            for item in invocation.conversation_history
        ]
        if invocation.conversation_history
        else None
    )
    execution_root = invocation.run_options.execution_root
    root = (
        execution_root.resolve() if isinstance(execution_root, Path) else execution_root
    )
    surface_context_block = render_agent_surface_context(
        invocation.context_packet.surface_context
    )
    return HermesGraphAgentTurnRequest(
        question=invocation.message,
        world_id=world_id,
        campaign_id=campaign_id,
        scope_mode=scope_mode,
        focus=host_focus,
        admissibility=admissibility,
        revision_pin=revision_pin,
        conversation_history=history,
        session_id=invocation.run_options.runtime_session_id,
        root=root,
        capability_policy=capability_policy,
        retrieval_session_id=None if retrieval is None else retrieval.session_id,
        retrieval_session=None if retrieval is None else retrieval.packet,
        surface_context_block=surface_context_block,
        plan_continuity_turn=invocation.plan_continuity_turn,
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
        return self._run(invocation)

    def run_with_provider_authorization(
        self,
        invocation: AgentRuntimeInvocation,
        authorize: Callable[[Mapping[str, Any]], bool],
        *,
        request_budget: Mapping[str, Any],
        on_graph_operation: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        on_provider_lifecycle: Callable[[Mapping[str, Any]], bool] | None = None,
    ) -> AgentRuntimeResult:
        """Use the existing Hermes host with a per-request parent authorization gate."""
        return self._run(
            invocation,
            authorize=authorize,
            request_budget=request_budget,
            on_graph_operation=on_graph_operation,
            on_provider_lifecycle=on_provider_lifecycle,
            require_authorization=True,
        )

    def _run(
        self,
        invocation: AgentRuntimeInvocation,
        *,
        authorize: Callable[[Mapping[str, Any]], bool] | None = None,
        request_budget: Mapping[str, Any] | None = None,
        on_graph_operation: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        on_provider_lifecycle: Callable[[Mapping[str, Any]], bool] | None = None,
        require_authorization: bool = False,
    ) -> AgentRuntimeResult:
        policy_id = invocation.capability_policy.policy_id
        world_scope = invocation.context_packet.world_scope
        expected_policy = (
            CONVERSATION_ONLY_POLICY_ID
            if world_scope is None
            else WORLD_GRAPH_READ_POLICY_ID
        )
        if policy_id != expected_policy:
            return _unsupported_policy_result(policy_id)
        request = map_invocation_to_hermes_request(invocation)
        if require_authorization:
            if request.capability_policy is None or request.capability_policy.graph_scope is None:
                raise ValueError("Plan Graph authorization requires a resolved World scope")
            if on_graph_operation is None:
                raise ValueError("Plan Graph authorization requires a parent broker")
            request = replace(
                request,
                provider_authorization_required=True,
                request_budget=request_budget,
                parent_graph_broker_required=True,
                capability_policy=parent_brokered_graph_expansion_policy(
                    request.capability_policy.graph_scope
                ),
            )
        host = self._host_factory()
        host_phase_spans: list[dict[str, Any]] = []

        def on_host_phase(span: dict[str, Any]) -> None:
            if len(host_phase_spans) < 24:
                host_phase_spans.append(dict(span))

        host_options: dict[str, Any] = {"on_host_phase": on_host_phase}
        if authorize is not None:
            host_options["on_provider_authorization"] = authorize
        if on_graph_operation is not None:
            host_options["on_graph_operation"] = on_graph_operation
        if on_provider_lifecycle is not None:
            host_options["on_provider_lifecycle"] = on_provider_lifecycle
        result = host.execute(request, **host_options)
        runtime_result = map_hermes_result_to_runtime_result(
            result,
            worker_pid=_host_worker_pid(host),
        )
        if host_phase_spans:
            runtime_result.runtime_metadata["host_phase_spans"] = host_phase_spans
        return runtime_result


def default_hermes_agent_runtime() -> HermesAgentRuntimeAdapter:
    return HermesAgentRuntimeAdapter()
