"""Server-owned resolution and execution for the universal Agent turn API."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from apps.live_control_server.models.agent_turn import AgentTurnRequest, AgentTurnResponse
from apps.live_control_server.services.agent_context_assembler import (
    assemble_agent_conversation_context,
    assemble_agent_graph_context,
)
from apps.live_control_server.services.agent_runtime import (
    AgentRuntime,
    AgentCurrentOwnerContext,
    AgentSurfaceContext,
    AgentWorldScope,
    descriptor_for_runtime,
)
from apps.live_control_server.services.agent_turn_trace import AgentTurnTraceBuilder
from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphFocus,
    AgentWorldGraphQueryContextRequest,
    resolve_agent_world_graph_query_context,
)
from apps.live_control_server.services.hermes_agent_runtime import default_hermes_agent_runtime
from apps.live_control_server.services.hermes_session_store import (
    HermesSessionPointerStore,
    HermesStructuredPointerResolution,
)


class AgentTurnServiceError(ValueError):
    def __init__(self, message: str, *, code: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class AgentTurnResolvedWork:
    kind: str
    object_id: str
    revision: str | int
    changed_since_expected: bool
    owner_kind: str | None
    owner_id: str | None
    surface_context: Any = None
    campaign_id: str | None = None
    target_session: int | None = None
    session_id: str | None = None
    world_id: str | None = None


OwnerResolver = Callable[[AgentTurnRequest], Mapping[str, Any] | None]
WorkResolver = Callable[[AgentTurnRequest, Mapping[str, Any] | None], AgentTurnResolvedWork | None]
GraphResolver = Callable[
    [AgentTurnRequest, Mapping[str, Any] | None, AgentTurnResolvedWork | None],
    tuple[dict[str, Any], AgentWorldScope],
]


def _selection_found(envelope: Mapping[str, Any], selected_node_id: str | None) -> bool | None:
    if selected_node_id is None:
        return None
    ids = set(str(item) for item in (envelope.get("matched_node_ids") or []))
    ids.update(
        str(item.get("node_id"))
        for item in (envelope.get("nodes") or [])
        if isinstance(item, Mapping) and item.get("node_id") is not None
    )
    return selected_node_id in ids


def _surface_context_for_turn(
    request: AgentTurnRequest,
    owner: Mapping[str, Any] | None,
    work: AgentTurnResolvedWork | None,
) -> AgentSurfaceContext:
    """Carry the current surface and only server-resolved World identity to every turn."""
    resolved_owner = None
    if owner is not None and owner.get("kind") == "world":
        owner_id = owner.get("id")
        owner_name = owner.get("name")
        if isinstance(owner_id, str) and owner_id.strip() and isinstance(owner_name, str) and owner_name.strip():
            resolved_owner = AgentCurrentOwnerContext(
                kind="world",
                owner_id=owner_id.strip(),
                name=owner_name.strip(),
            )
    work_surface = None if work is None else work.surface_context
    return AgentSurfaceContext(
        surface_id=request.surface.surface_id,
        surface_instance_id=request.surface.instance_id,
        current_owner=resolved_owner,
        current_work=None if work_surface is None else work_surface.current_work,
        current_play=None if work_surface is None else work_surface.current_play,
    )


def execute_agent_turn(
    request: AgentTurnRequest,
    *,
    root: Path,
    pointer_store: HermesSessionPointerStore,
    owner_resolver: OwnerResolver,
    work_resolver: WorkResolver,
    graph_resolver: GraphResolver,
    runtime: AgentRuntime | None = None,
) -> AgentTurnResponse:
    """Resolve authority on each call, then execute one read-only conversation turn.

    Resolver callbacks are deliberately explicit: each identity channel has its own
    authority and cannot silently inherit a value from another request field.
    """
    selected_runtime = runtime or default_hermes_agent_runtime()
    try:
        owner = owner_resolver(request)
        work = work_resolver(request, owner)
    except AgentTurnServiceError:
        raise
    except Exception as exc:
        raise AgentTurnServiceError(
            "Could not resolve the supplied owner or saved-work identity.",
            code="authority_unavailable",
            status_code=503,
        ) from exc

    owner_kind = (
        str(owner.get("kind")) if owner is not None
        else (None if work is None else work.owner_kind)
    )
    owner_id = (
        str(owner.get("id")) if owner is not None
        else (None if work is None else work.owner_id)
    )
    work_kind = None if work is None else work.kind
    work_id = None if work is None else work.object_id
    plan_binding = work_kind == "plan"
    plan_continuity = plan_binding and request.surface.surface_id == "plan"
    surface_context = _surface_context_for_turn(request, owner, work)
    pointer = pointer_store.resolve_structured_for_request(
        owner_kind=owner_kind,
        owner_id=owner_id,
        work_kind=work_kind,
        work_id=work_id,
        agent_thread_id=request.client_thread_id,
        pointer_id=None,
    )
    if pointer.pointer_status == "rejected" and plan_continuity:
        raise AgentTurnServiceError(
            "Saved conversation continuity is unavailable or expired. "
            "Choose New conversation to start fresh; the saved work was not changed.",
            code="hermes_continuity_unavailable",
            status_code=409,
        )
    if pointer.pointer_status == "rejected" or (plan_binding and not plan_continuity):
        pointer = HermesStructuredPointerResolution(
            continuity_session_id=None,
            pointer_status="recovered",
            pointer_in_request=pointer.pointer_in_request,
            recovery_message=pointer.recovery_message,
        )

    graph_result: dict[str, Any]
    scope: AgentWorldScope | None = None
    graph_status = "not_requested"
    selected_node_id = (
        None if request.graph_selection is None else request.graph_selection.node_id
    )
    if request.graph_request.mode == "none":
        assembly = assemble_agent_conversation_context(
            question=request.message,
            runtime_session_id=pointer.continuity_session_id,
            thread_id=request.client_thread_id,
            turn_id=request.turn_id,
            surface_context=surface_context,
        )
        graph_result = {"status": "not_requested", "selection_found": None}
    else:
        try:
            envelope, scope = graph_resolver(request, owner, work)
        except AgentTurnServiceError:
            raise
        except Exception as exc:
            raise AgentTurnServiceError(
                "The requested World graph context could not be resolved.",
                code="graph_unavailable",
                status_code=503,
            ) from exc
        graph_status = str(envelope.get("status") or "unavailable")
        if graph_status == "unavailable":
            raise AgentTurnServiceError(
                "The requested World graph is unavailable.",
                code="graph_unavailable",
                status_code=503,
            )
        assembly = assemble_agent_graph_context(
            question=request.message,
            graph_envelope=envelope,
            root=root,
            thread_id=request.client_thread_id,
            turn_id=request.turn_id,
            runtime_session_id=pointer.continuity_session_id,
            surface_context=surface_context,
        )
        graph_result = {
            "status": graph_status,
            "world_id": scope.world_id,
            "campaign_id": scope.campaign_id,
            "scope_mode": scope.scope_mode,
            "revision_id": scope.revision_id,
            "focus": dict(scope.focus),
            "selection_node_id": selected_node_id,
            "selection_found": _selection_found(envelope, selected_node_id),
            "head_revision_id": envelope.get("head_revision_id"),
            "is_head": envelope.get("is_head"),
        }

    descriptor = descriptor_for_runtime(selected_runtime)
    trace = AgentTurnTraceBuilder(
        agent_thread_id=request.client_thread_id,
        turn_id=request.turn_id,
        runtime=descriptor.trace_runtime,
        backend=descriptor.trace_backend,
        mode=descriptor.trace_mode,
    )
    trace.context_summary = dict(assembly.trace_summary)
    with trace.phase("runtime_dispatch"):
        invocation = replace(assembly.invocation, plan_continuity_turn=plan_continuity)
        result = selected_runtime.run(invocation)
    final_trace = trace.finalize_and_log(
        status="ok" if result.status == "ok" else "error",
        model_calls=result.model_calls,
        extra_warnings=result.telemetry_warnings,
        hermes_fields={
            "tool_events": [
                {
                    "tool_name": event.tool_name,
                    "state": event.state,
                    "duration_ms": event.duration_ms,
                }
                for event in result.tool_events
            ],
            "hermes_session_id": result.runtime_session_id,
            "process_isolation": result.runtime_metadata.get("process_isolation"),
            "conversation_context": "structured" if pointer.continuity_session_id else "fresh",
        },
        observed_model_call_count=result.observed_model_call_count,
    )

    pointer_binding = None
    if plan_continuity and result.error_code == "hermes_continuity_unavailable":
        if pointer.continuity_session_id:
            pointer_store.revoke_structured_after_continuity_failure(
                owner_kind=owner_kind,
                owner_id=owner_id,
                work_kind=work_kind,
                work_id=work_id,
                agent_thread_id=request.client_thread_id,
                hermes_session_id=pointer.continuity_session_id,
            )
        raise AgentTurnServiceError(
            "Saved conversation continuity is unavailable or expired. "
            "Choose New conversation to start fresh; the saved work was not changed.",
            code="hermes_continuity_unavailable",
            status_code=409,
        )
    if plan_continuity and result.status == "ok":
        if not result.runtime_session_id:
            raise AgentTurnServiceError(
                "Hermes did not return a persistent conversation session. "
                "Choose New conversation to start fresh; the saved work was not changed.",
                code="hermes_continuity_unavailable",
                status_code=409,
            )
        if pointer.continuity_session_id and result.runtime_session_id != pointer.continuity_session_id:
            pointer_store.revoke_structured_after_continuity_failure(
                owner_kind=owner_kind,
                owner_id=owner_id,
                work_kind=work_kind,
                work_id=work_id,
                agent_thread_id=request.client_thread_id,
                hermes_session_id=pointer.continuity_session_id,
            )
            raise AgentTurnServiceError(
                "Hermes could not resume the saved conversation. "
                "Choose New conversation to start fresh; the saved work was not changed.",
                code="hermes_continuity_unavailable",
                status_code=409,
            )
    if (
        result.runtime_session_id
        and (not plan_binding or (plan_continuity and result.status == "ok"))
    ):
        pointer_binding = pointer_store.upsert_structured_after_turn(
            owner_kind=owner_kind,
            owner_id=owner_id,
            work_kind=work_kind,
            work_id=work_id,
            agent_thread_id=request.client_thread_id,
            hermes_session_id=result.runtime_session_id,
            require_new_thread=plan_continuity,
        )
    if result.status != "ok":
        answer = {
            "status": "error",
            "text": None,
            "code": result.error_code or "agent_runtime_error",
            "message": result.error_message,
            "graph_grounded": False,
        }
    else:
        answer = {
            "status": "ok",
            "text": result.final_text,
            "code": None,
            "message": None,
            "graph_grounded": False,
        }

    return AgentTurnResponse(
        client_thread_id=request.client_thread_id,
        turn_id=request.turn_id,
        surface={
            "surface_id": request.surface.surface_id,
            "instance_id": request.surface.instance_id,
            "status": "resolved",
        },
        owner_scope={
            "status": "absent" if owner is None else "resolved",
            "kind": None if owner is None else owner.get("kind"),
            "owner_id": None if owner is None else owner.get("id"),
            "name": None if owner is None else owner.get("name"),
        },
        primary_work={
            "status": "absent" if work is None else (
                "changed_since_expected" if work.changed_since_expected else "resolved"
            ),
            "kind": work_kind,
            "object_id": work_id,
            "revision_used": None if work is None else work.revision,
            "expected_revision": (
                None if request.primary_work is None else request.primary_work.expected_revision
            ),
        },
        client_work_state_reported=request.client_work_state,
        graph=graph_result,
        conversation={
            "client_thread_id": request.client_thread_id,
            "turn_id": request.turn_id,
            "pointer_status": (
                "reused" if pointer.continuity_session_id else pointer.pointer_status
            ),
            "pointer_id": None if pointer_binding is None else pointer_binding.pointer_id,
        },
        answer={**answer, "trace": final_trace},
    )


def build_existing_graph_context(
    request: AgentTurnRequest,
    *,
    root: Path,
    world_id: str,
    project_fn: Any | None = None,
) -> tuple[dict[str, Any], AgentWorldScope]:
    """Adapter to the existing revision-pinned graph projection boundary."""
    graph = request.graph_request
    if graph.mode == "none":
        raise AgentTurnServiceError("Graph was not requested.", code="graph_not_requested")
    campaign_id = (
        graph.campaign_id
        if graph.mode == "campaign"
        else (graph.campaign_id or "")
    )
    nested = AgentWorldGraphQueryContextRequest(
        world_id=world_id,
        campaign_id=campaign_id,
        scope_mode=graph.mode,
        revision_pin=graph.revision_pin,
        selected_node_id=(None if request.graph_selection is None else request.graph_selection.node_id),
        focus=AgentWorldGraphFocus(
            kind=graph.focus.kind,
            session_id=graph.focus.session_id,
            campaign_id=graph.focus.campaign_id,
        ),
    )
    envelope = resolve_agent_world_graph_query_context(
        nested,
        outer_text=request.message,
        outer_campaign_id=campaign_id,
        root=root,
        project_fn=project_fn,
    )
    return envelope, AgentWorldScope(
        world_id=world_id,
        campaign_id=campaign_id,
        focus=nested.focus.model_dump(mode="json"),
        admissibility="gm",
        revision_id=graph.revision_pin or str(envelope.get("revision_id") or ""),
        scope_mode=graph.mode,
    )
