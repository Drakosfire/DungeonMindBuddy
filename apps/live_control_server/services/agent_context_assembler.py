"""Neutral DungeonBuddy graph-Agent context composition (A5).

Owns the accepted World-scope / retrieval-session / admitted-recap assembly that
previously lived inside ``hermes_graph_query.build_hermes_graph_turn_request``.

This is the product seam future QueryContext / ResolvedSurfaceContext /
WorldContext / InteractionContext work will enter. A5 preserves today's
model-facing payload exactly: rich typed product state is for deterministic
resolution; it is not automatically model-visible context. The current user
question remains the retrieval seed.

Does not select a runtime, open World projections, persist Interaction Memory,
or implement SurfaceContext / relevance weights / token budgeting.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.services.agent_runtime import (
    WORLD_GRAPH_READ_POLICY,
    AgentContextPacket,
    AgentRetrievalSession,
    AgentRunOptions,
    AgentRuntimeInvocation,
    AgentWorldScope,
)
from graph_memory.interaction.initial_resolve import create_session_from_preflight
from graph_memory.interaction.session import GraphRetrievalSession
from graph_memory.interaction.session_store import replace_session

CONTEXT_SUMMARY_SCHEMA = "dmb_agent_context_summary_v1"

CONTEXT_SUMMARY_KEYS = frozenset(
    {
        "context_schema",
        "world_id",
        "campaign_id",
        "revision_id",
        "focus_kind",
        "admissibility",
        "history_message_count",
        "history_char_count",
        "retrieval_session_id",
        "retrieval_candidate_count",
        "retrieval_claim_count",
        "latest_recap_change_present",
        "admitted_recap_excerpt_char_count",
        "runtime_continuity_present",
    }
)


class AgentContextAssemblyError(ValueError):
    """Neutral context-assembly failure — product callers translate to their errors."""

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


@dataclass(frozen=True, slots=True)
class AgentContextAssembly:
    invocation: AgentRuntimeInvocation
    trace_summary: Mapping[str, str | int | bool | None]


def _focus_for_product(focus: Mapping[str, Any] | None) -> dict[str, Any]:
    if focus is None:
        return {"kind": "none", "session_id": None, "campaign_id": None}
    return {
        "kind": str(focus.get("kind") or "none"),
        "session_id": focus.get("session_id"),
        "campaign_id": focus.get("campaign_id"),
    }


def _require_resolved_revision(graph_envelope: Mapping[str, Any]) -> str:
    revision_id = graph_envelope.get("revision_id")
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise AgentContextAssemblyError(
            "Hermes graph queries require a resolved revision_id before dispatch.",
            code="world_graph_context_invalid",
        )
    return revision_id.strip()


def _build_trace_summary(
    *,
    world_scope: AgentWorldScope,
    history_copy: list[dict[str, str]] | None,
    session: GraphRetrievalSession,
    retrieval_session_packet: Mapping[str, Any],
    runtime_session_id: str | None,
) -> dict[str, str | int | bool | None]:
    history = history_copy or []
    candidates = retrieval_session_packet.get("candidates")
    claims = retrieval_session_packet.get("claim_ledger")
    latest = session.latest_recap_change
    excerpt = ""
    if isinstance(latest, Mapping):
        raw_excerpt = latest.get("admitted_recap_excerpt")
        if isinstance(raw_excerpt, str):
            excerpt = raw_excerpt
    summary: dict[str, str | int | bool | None] = {
        "context_schema": CONTEXT_SUMMARY_SCHEMA,
        "world_id": world_scope.world_id,
        "campaign_id": world_scope.campaign_id,
        "revision_id": world_scope.revision_id,
        "focus_kind": str(world_scope.focus.get("kind") or "none"),
        "admissibility": world_scope.admissibility,
        "history_message_count": len(history),
        "history_char_count": sum(len(item.get("content") or "") for item in history),
        "retrieval_session_id": session.id,
        "retrieval_candidate_count": len(candidates) if isinstance(candidates, list) else 0,
        "retrieval_claim_count": len(claims) if isinstance(claims, list) else 0,
        "latest_recap_change_present": isinstance(latest, Mapping),
        "admitted_recap_excerpt_char_count": len(excerpt),
        "runtime_continuity_present": bool(runtime_session_id),
    }
    assert set(summary) == CONTEXT_SUMMARY_KEYS
    return summary


def assemble_agent_graph_context(
    *,
    question: str,
    graph_envelope: Mapping[str, Any],
    root: Path | None = None,
    corpus_root: Path | None = None,
    conversation_history: Sequence[Mapping[str, str]] | None = None,
    retrieval_session: GraphRetrievalSession | None = None,
    runtime_session_id: str | None = None,
    thread_id: str | None = None,
    turn_id: str | None = None,
) -> AgentContextAssembly:
    """Compose one AgentRuntimeInvocation plus content-free composition telemetry."""
    from apps.live_control_server.config import repo_root as default_repo_root
    from graph_memory.interaction.latest_recap import read_admitted_recap_excerpt

    revision_id = _require_resolved_revision(graph_envelope)
    world_id = str(graph_envelope.get("world_id") or "").strip()
    campaign_id = str(graph_envelope.get("campaign_id") or "").strip()
    if not world_id or not campaign_id:
        raise AgentContextAssemblyError(
            "Resolved world_graph_context is missing world_id or campaign_id.",
            code="world_graph_context_invalid",
        )
    focus_raw = graph_envelope.get("focus")
    focus_map = focus_raw if isinstance(focus_raw, Mapping) else None
    product_focus = _focus_for_product(focus_map)
    admissibility = str(graph_envelope.get("admissibility") or "gm")
    graph_root = (root or world_graph_root()).resolve()
    if not graph_root.is_absolute():
        raise AgentContextAssemblyError(
            "Server-selected graph root must be absolute.",
            code="world_graph_context_invalid",
        )
    history_copy = (
        [{"role": item["role"], "content": item["content"]} for item in conversation_history]
        if conversation_history
        else None
    )
    session = retrieval_session
    if session is None:
        session = create_session_from_preflight(graph_envelope, question=question)
    latest_recap_change = graph_envelope.get("latest_recap_change")
    if isinstance(latest_recap_change, Mapping) and session.latest_recap_change is None:
        # Preserve S1 context on the shared session object so host hydrate and
        # claim validation see the same server-owned comparison boundary.
        session.latest_recap_change = dict(latest_recap_change)
    if isinstance(session.latest_recap_change, dict):
        # Server-owned admitted-recap read for sensemaking (not a model path).
        latest = session.latest_recap_change.get("latest_recap")
        source_path = ""
        if isinstance(latest, Mapping):
            source_path = str(latest.get("source_recap_path") or "").strip()
        memory_lag = bool(session.latest_recap_change.get("memory_lag")) or (
            str(session.latest_recap_change.get("outcome") or "") == "memory_lag"
        )
        mutated = False
        if memory_lag and source_path and not session.latest_recap_change.get(
            "admitted_recap_excerpt"
        ):
            excerpt = read_admitted_recap_excerpt(
                root=(corpus_root or default_repo_root()).resolve(),
                source_recap_path=source_path,
            )
            if excerpt:
                session.latest_recap_change = {
                    **session.latest_recap_change,
                    "admitted_recap_excerpt": excerpt,
                }
                mutated = True
        if mutated or isinstance(latest_recap_change, Mapping):
            replace_session(session)
    # Compatibility debt: projection method remains Hermes-named (A3 proved
    # the packet is harness-neutral; renaming lives outside A5 / graph_memory).
    retrieval_session_packet = session.project_for_hermes()
    world_scope = AgentWorldScope(
        world_id=world_id,
        campaign_id=campaign_id,
        focus=product_focus,
        admissibility=admissibility,
        revision_id=revision_id,
    )
    continuity = runtime_session_id or None
    invocation = AgentRuntimeInvocation(
        thread_id=thread_id,
        turn_id=turn_id,
        message=question,
        conversation_history=history_copy,
        context_packet=AgentContextPacket(
            world_scope=world_scope,
            retrieval_session=AgentRetrievalSession(
                session_id=session.id,
                packet=retrieval_session_packet,
            ),
        ),
        capability_policy=WORLD_GRAPH_READ_POLICY,
        run_options=AgentRunOptions(
            runtime_session_id=continuity,
            execution_root=graph_root,
        ),
    )
    return AgentContextAssembly(
        invocation=invocation,
        trace_summary=_build_trace_summary(
            world_scope=world_scope,
            history_copy=history_copy,
            session=session,
            retrieval_session_packet=retrieval_session_packet,
            runtime_session_id=continuity,
        ),
    )


__all__ = [
    "CONTEXT_SUMMARY_KEYS",
    "CONTEXT_SUMMARY_SCHEMA",
    "AgentContextAssembly",
    "AgentContextAssemblyError",
    "assemble_agent_graph_context",
]
