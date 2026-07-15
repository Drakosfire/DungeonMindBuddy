from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.live_control_server.config import repo_root, session_dir, world_graph_root
from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphQueryContextRequest,
    render_world_graph_prompt_block,
    resolve_agent_world_graph_query_context,
)
from apps.live_control_server.services.citation_freshness import build_evidence_snapshots
from apps.live_control_server.services.hermes_graph_query import (
    normalize_hermes_conversation_history,
    run_hermes_graph_query,
    validate_hermes_query_inputs,
)
from apps.live_control_server.session_store import (
    append_events_and_jobs,
    load_session,
    refresh_current_state,
)
from src.live_play.classify_live_turn import classify_live_turn
from src.live_play.live_query_context import run_context_lookup_turn
from src.live_play.live_turn import LiveTurnResult, handle_live_turn
from graph_memory.interaction.latest_recap import (
    is_latest_recap_change_question,
    resolve_latest_recap_change_context,
)

LIVE_QUERY_BACKENDS = frozenset({"live", "hermes"})


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_event_id() -> str:
    return f"evt-live-{uuid.uuid4().hex[:12]}"


def _new_agent_thread_id() -> str:
    return f"agent-thread-{uuid.uuid4().hex[:12]}"


def _new_turn_id() -> str:
    return f"agent-turn-{uuid.uuid4().hex[:12]}"


def _with_conversation_fields(
    response: dict[str, Any],
    *,
    agent_thread_id: str | None,
    turn_id: str | None,
    hermes_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response["agent_thread_id"] = agent_thread_id
    response["turn_id"] = turn_id
    response["hermes_session"] = hermes_session
    return response


def build_retrieval_freshness_decision(
    *,
    context_packet: dict[str, Any] | None,
    hermes_session_id: str | None,
    agent_thread_id: str | None,
    prior_turn_count: int | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    packet = context_packet or {}
    admitted_evidence_count = len(list(packet.get("admitted_evidence") or []))
    rejected_evidence_count = len(list(packet.get("rejected_evidence") or []))
    known_prior_turn_count = prior_turn_count if isinstance(prior_turn_count, int) and prior_turn_count >= 0 else 0
    has_thread_basis = bool(hermes_session_id) or known_prior_turn_count > 0
    used_fresh_retrieval = admitted_evidence_count > 0
    used_thread_context = has_thread_basis and status != "error"
    warnings: list[str] = []

    if used_fresh_retrieval and used_thread_context:
        decision = "blended"
        reason = "Fresh corpus evidence was admitted, and an active Hermes session/thread handle was reused."
    elif used_fresh_retrieval:
        decision = "fresh_retrieval"
        reason = "Fresh corpus evidence was admitted for this turn; no reliable prior-turn basis was available server-side."
    elif used_thread_context:
        decision = "thread_context"
        reason = "The active Hermes session/thread handle was reused, but no fresh corpus evidence was admitted for this turn."
        warnings.append("No fresh corpus evidence was admitted for this turn.")
    else:
        decision = "insufficient_grounding"
        reason = "No admitted corpus evidence and no reliable thread/session basis were available for this turn."
        warnings.append("No admitted corpus evidence or reliable thread basis was available; answer may be under-grounded.")

    if hermes_session_id and prior_turn_count is None:
        reason += " Hermes session handle was reused, but server-side turn count is not available in this slice."

    return {
        "schema": "dmb_retrieval_freshness_decision_v1",
        "decision": decision,
        "used_fresh_retrieval": used_fresh_retrieval,
        "used_thread_context": used_thread_context,
        "admitted_evidence_count": admitted_evidence_count,
        "rejected_evidence_count": rejected_evidence_count,
        "prior_turn_count": known_prior_turn_count,
        "reason": reason,
        "warnings": warnings,
    }


def _should_route_context_lookup(text: str, event_type: str) -> bool:
    if event_type == "context_question":
        return True
    lowered = text.lower()
    if "?" not in lowered:
        return False
    return any(
        token in lowered
        for token in (
            "what ",
            "how ",
            "which ",
            "session ",
            "outcome",
            "prep",
            "context",
            "evidence",
            "ground",
            "canon",
        )
    )


def _attach_world_graph_context(
    response: dict[str, Any],
    world_graph_context: dict[str, Any] | None,
) -> dict[str, Any]:
    if world_graph_context is not None:
        response["world_graph_context"] = world_graph_context
        warning_codes = list(world_graph_context.get("warning_codes") or [])
        if warning_codes:
            existing = list(response.get("warnings") or [])
            for code in warning_codes:
                if code not in existing:
                    existing.append(code)
            response["warnings"] = existing
    return response


def process_live_query(
    text: str,
    *,
    base: Path | None = None,
    root: Path | None = None,
    request_manifest_path: str | None = None,
    query_backend: str = "live",
    agent_thread_id: str | None = None,
    hermes_session_id: str | None = None,
    trace_requested: bool | None = None,
    world_graph_context: AgentWorldGraphQueryContextRequest | None = None,
    outer_campaign_id: str | None = None,
    conversation_history: Any | None = None,
) -> dict[str, Any]:
    session_base = base or session_dir()
    resolved_agent_thread_id = agent_thread_id or _new_agent_thread_id()
    resolved_turn_id = _new_turn_id()
    repo = root or repo_root()
    packet, _layout, _events, _jobs = load_session(session_base)

    if query_backend == "hermes":
        # PR354: Hermes is graph-host only.
        _ = trace_requested  # accepted for API compatibility; unused in this slice
        campaign_id = outer_campaign_id or str(packet.get("campaign_id") or "")
        validate_hermes_query_inputs(
            world_graph_context=world_graph_context,
            request_manifest_path=request_manifest_path,
            hermes_session_id=hermes_session_id,
            outer_campaign_id=campaign_id,
        )
        assert world_graph_context is not None  # validated above
        # History must fail closed before graph resolution or host construction.
        normalized_history = normalize_hermes_conversation_history(conversation_history)
        graph_envelope = resolve_agent_world_graph_query_context(
            world_graph_context,
            outer_text=text,
            outer_campaign_id=campaign_id,
            root=world_graph_root(),
        )
        if is_latest_recap_change_question(text):
            world_id = str(graph_envelope.get("world_id") or "eldyrwild")
            if world_id.startswith("world:"):
                world_id = world_id.removeprefix("world:")
            latest_recap_context = resolve_latest_recap_change_context(
                root=repo,
                graph_root=world_graph_root(),
                world_id=world_id,
                campaign_id=campaign_id,
                graph_revision_id=(
                    str(graph_envelope.get("revision_id"))
                    if graph_envelope.get("revision_id")
                    else None
                ),
            )
            graph_envelope = {
                **graph_envelope,
                "latest_recap_change": latest_recap_context.model_dump(
                    mode="json",
                    by_alias=True,
                ),
            }
        return run_hermes_graph_query(
            text=text,
            packet=packet,
            graph_envelope=graph_envelope,
            agent_thread_id=resolved_agent_thread_id,
            turn_id=resolved_turn_id,
            root=world_graph_root(),
            conversation_history=normalized_history,
        )

    if query_backend not in LIVE_QUERY_BACKENDS:
        raise ValueError(f"unsupported query backend: {query_backend}")

    graph_envelope: dict[str, Any] | None = None
    if world_graph_context is not None:
        campaign_id = outer_campaign_id or str(packet.get("campaign_id") or "")
        graph_envelope = resolve_agent_world_graph_query_context(
            world_graph_context,
            outer_text=text,
            outer_campaign_id=campaign_id,
        )

    classification = classify_live_turn(text)
    if _should_route_context_lookup(text, classification.event_type):
        graph_prompt = (
            render_world_graph_prompt_block(graph_envelope)
            if graph_envelope is not None
            else None
        )
        context_result = run_context_lookup_turn(
            question=text,
            classification=classification,
            packet=packet,
            root=repo,
            session=int(packet["session"]),
            request_manifest_path=request_manifest_path,
            world_graph_prompt_block=graph_prompt,
        )
        response = dict(context_result.response)
        response["retrieval_freshness"] = build_retrieval_freshness_decision(
            context_packet=response.get("context_packet") if isinstance(response.get("context_packet"), dict) else None,
            hermes_session_id=hermes_session_id,
            agent_thread_id=resolved_agent_thread_id,
            status=str(response.get("status") or "ok"),
        )
        response = _with_evidence_snapshots(response)
        response = _with_conversation_fields(
            response,
            agent_thread_id=resolved_agent_thread_id,
            turn_id=resolved_turn_id,
        )
        return _attach_world_graph_context(response, graph_envelope)

    result: LiveTurnResult = handle_live_turn(
        packet,
        text,
        root=repo,
        created_at=_utc_now_z(),
        event_id_factory=_new_event_id,
    )

    append_events_and_jobs(session_base, result.events_to_write, result.jobs_to_queue)
    refresh_current_state(session_base)

    response = {
        "schema": "dmb_live_query_response_v1",
        "query_id": f"live-query-{uuid.uuid4().hex[:12]}",
        "session": int(packet["session"]),
        "mode": "live_turn",
        "status": "ok",
        "answer": result.answer,
        "classification": asdict(result.classification),
        "events_written": [event["id"] for event in result.events_to_write],
        "jobs_queued": [job["id"] for job in result.jobs_to_queue],
        "next_suggestions": result.next_suggestions,
        "diagnostics": result.diagnostics,
        "provenance": result.provenance,
        "citations": [],
        "context_packet": None,
        "warnings": [],
        "mutations": [],
    }
    response = _with_conversation_fields(
        response,
        agent_thread_id=resolved_agent_thread_id,
        turn_id=resolved_turn_id,
    )
    return _attach_world_graph_context(response, graph_envelope)


def _with_evidence_snapshots(response: dict[str, Any]) -> dict[str, Any]:
    citations = response.get("citations") if isinstance(response.get("citations"), list) else []
    response["evidence_snapshots"] = build_evidence_snapshots(repo_root(), citations)
    return response
