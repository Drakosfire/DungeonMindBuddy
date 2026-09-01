"""A8: shared Agent query service for Play Ask and live Hermes delegation."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import repo_root, session_dir, world_graph_root
from apps.live_control_server.services.agent_play_surface_context import (
    AgentPlayQueryScope,
    resolve_agent_play_query_scope,
)
from apps.live_control_server.services.agent_runtime import (
    AgentRuntime,
    descriptor_for_runtime,
)
from apps.live_control_server.services.agent_surface_context import (
    AgentSurfaceContextRequest,
    resolve_agent_surface_context,
)
from apps.live_control_server.services.agent_turn_trace import AgentTurnTraceBuilder
from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphQueryContextRequest,
)
from apps.live_control_server.services.hermes_graph_query import (
    HermesGraphQueryRequestError,
    normalize_hermes_conversation_history,
    run_hermes_graph_query,
    validate_hermes_query_inputs,
)
from graph_memory.interaction.latest_recap import (
    is_latest_recap_change_question,
    resolve_latest_recap_change_context,
)

AGENT_QUERY_REQUEST_SCHEMA = "dmb_agent_query_request_v1"
AGENT_QUERY_SCOPE_SUMMARY_SCHEMA = "dmb_agent_query_scope_summary_v1"


def resolve_agent_world_graph_query_context(*args: Any, **kwargs: Any) -> Any:
    """Resolve World context via live_agent_loop's bound symbol.

    Hermes HTTP tests historically monkeypatch
    ``live_agent_loop.resolve_agent_world_graph_query_context``. Keeping that
    single binding avoids a second silent resolver path after A8 extraction.
    """
    from apps.live_control_server.services import live_agent_loop as live_agent_loop_mod

    return live_agent_loop_mod.resolve_agent_world_graph_query_context(*args, **kwargs)


class AgentQueryRequestError(ValueError):
    """Agent query request validation failure — do not invoke the model."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 422,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code

    def response_body(self) -> dict[str, Any]:
        from apps.live_control_server.services.hermes_graph_query import (
            VALIDATION_ERROR_SCHEMA,
        )

        return {
            "schema": VALIDATION_ERROR_SCHEMA,
            "code": self.code,
            "message": str(self),
            "statusCode": self.status_code,
            "diagnostics": [
                {
                    "code": self.code,
                    "message": str(self),
                    "severity": "error",
                }
            ],
        }


class AgentQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_query_request_v1"] = Field(alias="schema")
    text: str = Field(min_length=1)
    agent_thread_id: str | None = None
    hermes_session_pointer: str | None = None
    trace_requested: bool | None = None
    world_graph_context: AgentWorldGraphQueryContextRequest
    conversation_history: Any | None = None
    surface_context: AgentSurfaceContextRequest


def _new_agent_thread_id() -> str:
    return f"agent-thread-{uuid.uuid4().hex[:12]}"


def _new_turn_id() -> str:
    return f"agent-turn-{uuid.uuid4().hex[:12]}"


def _validate_play_world_graph_context(
    world_graph_context: AgentWorldGraphQueryContextRequest,
    *,
    authoritative_campaign_id: str,
) -> None:
    if world_graph_context.campaign_id != authoritative_campaign_id:
        raise AgentQueryRequestError(
            "world_graph_context.campaign_id must match the authoritative Play Run campaign.",
            code="agent_query_world_campaign_mismatch",
        )
    if world_graph_context.scope_mode != "campaign":
        raise AgentQueryRequestError(
            "Play Agent query requires world_graph_context.scope_mode campaign.",
            code="agent_query_world_scope_rejected",
        )
    if world_graph_context.focus.kind != "none":
        raise AgentQueryRequestError(
            "Play Agent query requires world_graph_context.focus.kind none.",
            code="agent_query_world_focus_rejected",
        )
    if world_graph_context.admissibility != "gm":
        raise AgentQueryRequestError(
            "Play Agent query requires world_graph_context.admissibility gm.",
            code="agent_query_world_admissibility_rejected",
        )


def _scope_trace_summary(
    *,
    scope_status: Literal["resolved", "rejected", "unavailable"],
    campaign_id: str | None,
    run_scope_resolved: bool,
) -> dict[str, str | bool | None]:
    return {
        "scope_schema": AGENT_QUERY_SCOPE_SUMMARY_SCHEMA,
        "surface_id": "play",
        "scope_status": scope_status,
        "campaign_id": campaign_id,
        "session_number_present": False,
        "run_scope_resolved": run_scope_resolved,
    }


def process_agent_query(
    text: str,
    *,
    base: Path | None = None,
    root: Path | None = None,
    graph_root: Path | None = None,
    agent_thread_id: str | None = None,
    turn_id: str | None = None,
    hermes_session_pointer: str | None = None,
    trace_requested: bool | None = None,
    world_graph_context: AgentWorldGraphQueryContextRequest,
    conversation_history: Any | None = None,
    surface_context: AgentSurfaceContextRequest | None = None,
    agent_runtime: AgentRuntime | None = None,
    session_base: Path | None = None,
    live_packet: Mapping[str, Any] | None = None,
    outer_campaign_id: str | None = None,
    outer_session: int | None = None,
    request_manifest_path: str | None = None,
    hermes_session_id: str | None = None,
) -> dict[str, Any]:
    """Run one shared graph-Agent turn for Play Ask or live Hermes delegation."""
    repo = root or repo_root()
    resolved_graph_root = graph_root or world_graph_root()
    resolved_session_base = session_base or base or session_dir()
    resolved_agent_thread_id = agent_thread_id or _new_agent_thread_id()
    resolved_turn_id = turn_id or _new_turn_id()
    descriptor = descriptor_for_runtime(agent_runtime)
    builder = AgentTurnTraceBuilder(
        agent_thread_id=resolved_agent_thread_id,
        turn_id=resolved_turn_id,
        runtime=descriptor.trace_runtime,
        backend=descriptor.trace_backend,
        mode=descriptor.trace_mode,
    )
    _ = trace_requested

    play_scope: AgentPlayQueryScope | None = None
    packet: Mapping[str, Any] | None = live_packet
    product_campaign_id: str | None = None
    product_session_number: int | None = None

    try:
        if packet is not None:
            campaign_id = outer_campaign_id or str(packet.get("campaign_id") or "")
            session_number = int(packet["session"])
            with builder.phase("request_validation"):
                validate_hermes_query_inputs(
                    world_graph_context=world_graph_context,
                    request_manifest_path=request_manifest_path,
                    hermes_session_id=hermes_session_id,
                    hermes_session_pointer=hermes_session_pointer,
                    outer_campaign_id=campaign_id,
                )
                normalized_history = normalize_hermes_conversation_history(
                    conversation_history
                )
            product_campaign_id = None
            product_session_number = None
        else:
            if surface_context is None:
                raise AgentQueryRequestError(
                    "Agent query requires surface_context.",
                    code="surface_context_required",
                )
            if surface_context.surface_id.strip() != "play":
                raise AgentQueryRequestError(
                    "Agent query admits only surface_id play in A8.",
                    code="agent_query_surface_not_supported",
                )
            scope_span = builder.start_phase("agent_query_scope_resolution")
            try:
                play_scope = resolve_agent_play_query_scope(
                    surface_context,
                    root=repo,
                )
            except HermesGraphQueryRequestError as exc:
                builder.complete_phase(
                    scope_span,
                    status="error",
                    attributes=_scope_trace_summary(
                        scope_status="rejected",
                        campaign_id=None,
                        run_scope_resolved=False,
                    ),
                )
                raise AgentQueryRequestError(
                    str(exc),
                    code=exc.code,
                    status_code=exc.status_code,
                ) from exc
            else:
                builder.complete_phase(
                    scope_span,
                    attributes=_scope_trace_summary(
                        scope_status="resolved",
                        campaign_id=play_scope.campaign_id,
                        run_scope_resolved=True,
                    ),
                )
            campaign_id = play_scope.campaign_id
            session_number = None
            with builder.phase("request_validation"):
                _validate_play_world_graph_context(
                    world_graph_context,
                    authoritative_campaign_id=campaign_id,
                )
                if hermes_session_pointer is not None and not str(
                    hermes_session_pointer
                ).strip():
                    raise HermesGraphQueryRequestError(
                        "hermes_session_pointer must be a non-empty string when provided.",
                        code="hermes_session_pointer_invalid",
                    )
                normalized_history = normalize_hermes_conversation_history(
                    conversation_history
                )
            product_campaign_id = campaign_id
            product_session_number = None
            packet = None

        with builder.phase("world_context_resolution"):
            graph_envelope = resolve_agent_world_graph_query_context(
                world_graph_context,
                outer_text=text,
                outer_campaign_id=campaign_id,
                root=resolved_graph_root,
            )
        if is_latest_recap_change_question(text):
            with builder.phase("latest_recap_context"):
                world_id = str(graph_envelope.get("world_id") or "eldyrwild")
                if world_id.startswith("world:"):
                    world_id = world_id.removeprefix("world:")
                graph_revision_id = (
                    str(graph_envelope.get("revision_id"))
                    if graph_envelope.get("revision_id")
                    else None
                )
                latest_recap_context = resolve_latest_recap_change_context(
                    root=repo,
                    world_id=world_id,
                    campaign_id=campaign_id,
                    graph_revision_id=graph_revision_id,
                )
                graph_envelope = {
                    **graph_envelope,
                    "latest_recap_change": latest_recap_context.model_dump(
                        mode="json",
                        by_alias=True,
                    ),
                }

        span = builder.start_phase("surface_context_resolution")
        try:
            resolution = resolve_agent_surface_context(
                surface_context,
                root=repo,
                outer_campaign_id=campaign_id,
                outer_session=session_number if session_number is not None else 0,
            )
        except Exception:
            builder.complete_phase(span, status="error")
            raise
        else:
            builder.complete_phase(span, attributes=resolution.trace_summary)
            for code in resolution.warning_codes:
                builder.add_warning(code)

        return run_hermes_graph_query(
            text=text,
            packet=packet,
            product_campaign_id=product_campaign_id,
            product_session_number=product_session_number,
            graph_envelope=graph_envelope,
            agent_thread_id=resolved_agent_thread_id,
            turn_id=resolved_turn_id,
            root=resolved_graph_root,
            corpus_root=repo,
            conversation_history=normalized_history,
            session_base=resolved_session_base,
            hermes_session_pointer=hermes_session_pointer,
            trace_builder=builder,
            agent_runtime=agent_runtime,
            surface_context=resolution.context,
        )
    except Exception:
        if not builder.logged:
            builder.finalize_and_log(status="error")
        raise


__all__ = [
    "AGENT_QUERY_REQUEST_SCHEMA",
    "AgentQueryRequest",
    "AgentQueryRequestError",
    "process_agent_query",
]
