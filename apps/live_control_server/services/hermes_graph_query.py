"""PR354: route one Hermes live-query turn through the PR353 host.

Owns request translation, host invocation (once), grounding classification,
safe tool-event projection, abstention, and typed execution errors.
Does not redesign host lifecycle, IPC, retry, or transcript behavior.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnRequest,
    HermesGraphAgentTurnResult,
    HermesGraphToolEvent,
)
from apps.live_control_server.services.hermes_graph_agent_host import (
    HermesGraphAgentHost,
    get_hermes_graph_agent_host,
)

GroundingState = Literal["grounded", "partial", "abstained", "error"]
HostFactory = Callable[[], HermesGraphAgentHost]

GROUNDING_SCHEMA = "dmb_hermes_graph_grounding_v1"
LIVE_QUERY_SCHEMA = "dmb_live_query_response_v1"
VALIDATION_ERROR_SCHEMA = "dmb_live_query_validation_error_v1"
MODE = "hermes_graph_agent"
RUNTIME = "process_isolated"
BACKEND = "hermes"

ABSTENTION_ANSWER = (
    "DungeonBuddy’s World Graph does not currently contain enough admitted evidence "
    "to answer this question reliably."
)
EXECUTION_ERROR_ANSWER = (
    "DungeonBuddy could not complete this World Graph Hermes turn. "
    "No legacy retrieval fallback was used."
)
PARTIAL_COVERAGE_WARNING = (
    "Graph retrieval returned partial or truncated evidence; treat the answer as qualified."
)

EMPTY_DENIED_OUTCOMES = frozenset({"empty", "denied"})
PARTIAL_OUTCOMES = frozenset({"partial", "truncated"})
UNAVAILABLE_OUTCOME = "unavailable"
HOST_ERROR_CODES = frozenset(
    {
        "hermes_worker_lost",
        "hermes_worker_timeout",
        "hermes_worker_start_failed",
        "hermes_worker_protocol_error",
    }
)


class HermesGraphQueryRequestError(ValueError):
    """Hermes-only request validation failure — do not invoke the host."""

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


@dataclass(frozen=True, slots=True)
class _DispatchedScope:
    world_id: str
    campaign_id: str
    focus: dict[str, Any]
    admissibility: str
    revision_id: str


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_trace_id() -> str:
    return f"agent-trace-{uuid.uuid4().hex[:12]}"


def _new_query_id() -> str:
    return f"live-query-{uuid.uuid4().hex[:12]}"


def validate_hermes_query_inputs(
    *,
    world_graph_context: Any | None,
    request_manifest_path: str | None,
    hermes_session_id: str | None,
    outer_campaign_id: str | None,
) -> None:
    """Reject Hermes-incompatible request fields before host access."""
    if world_graph_context is None:
        raise HermesGraphQueryRequestError(
            "Hermes queries require world_graph_context.",
            code="world_graph_context_required",
        )
    nested_campaign = getattr(world_graph_context, "campaign_id", None)
    if nested_campaign is None and isinstance(world_graph_context, Mapping):
        nested_campaign = world_graph_context.get("campaign_id")
    if (
        outer_campaign_id is not None
        and nested_campaign is not None
        and str(nested_campaign) != str(outer_campaign_id)
    ):
        raise HermesGraphQueryRequestError(
            "world_graph_context.campaign_id must equal the outer live-query campaign_id",
            code="campaign_scope_mismatch",
        )
    if request_manifest_path is not None:
        raise HermesGraphQueryRequestError(
            "Hermes graph queries do not accept legacy manifest_path.",
            code="legacy_manifest_not_supported",
        )
    if hermes_session_id is not None:
        raise HermesGraphQueryRequestError(
            "Hermes continuity (hermes_session_id) is not supported in this slice.",
            code="hermes_continuity_not_supported",
        )


def _api_focus_to_host_focus(focus: Mapping[str, Any] | None) -> dict[str, str | None]:
    if focus is None:
        return {"kind": "none", "sessionId": None}
    kind = str(focus.get("kind") or "none")
    session_id = focus.get("session_id")
    if session_id is not None:
        session_id = str(session_id)
    return {"kind": kind, "sessionId": session_id}


def _focus_for_grounding(focus: Mapping[str, Any] | None) -> dict[str, Any]:
    if focus is None:
        return {"kind": "none", "session_id": None}
    return {
        "kind": str(focus.get("kind") or "none"),
        "session_id": focus.get("session_id"),
    }


def _require_resolved_revision(graph_envelope: Mapping[str, Any]) -> str:
    revision_id = graph_envelope.get("revision_id")
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise HermesGraphQueryRequestError(
            "Hermes graph queries require a resolved revision_id before dispatch.",
            code="world_graph_context_invalid",
        )
    return revision_id.strip()


def build_hermes_graph_turn_request(
    *,
    question: str,
    graph_envelope: Mapping[str, Any],
    root: Path | None = None,
) -> tuple[HermesGraphAgentTurnRequest, _DispatchedScope]:
    """Translate resolved World Graph context into one host turn request."""
    revision_id = _require_resolved_revision(graph_envelope)
    world_id = str(graph_envelope.get("world_id") or "").strip()
    campaign_id = str(graph_envelope.get("campaign_id") or "").strip()
    if not world_id or not campaign_id:
        raise HermesGraphQueryRequestError(
            "Resolved world_graph_context is missing world_id or campaign_id.",
            code="world_graph_context_invalid",
        )
    focus_raw = graph_envelope.get("focus")
    focus_map = focus_raw if isinstance(focus_raw, Mapping) else None
    host_focus = _api_focus_to_host_focus(focus_map)
    admissibility = str(graph_envelope.get("admissibility") or "gm")
    graph_root = (root or world_graph_root()).resolve()
    if not graph_root.is_absolute():
        raise HermesGraphQueryRequestError(
            "Server-selected graph root must be absolute.",
            code="world_graph_context_invalid",
        )
    request = HermesGraphAgentTurnRequest(
        question=question,
        world_id=world_id,
        campaign_id=campaign_id,
        focus=host_focus,
        admissibility=admissibility,
        revision_pin=revision_id,
        conversation_history=None,
        session_id=None,
        root=graph_root,
        capability_policy=None,
    )
    scope = _DispatchedScope(
        world_id=world_id,
        campaign_id=campaign_id,
        focus=_focus_for_grounding(focus_map),
        admissibility=admissibility,
        revision_id=revision_id,
    )
    return request, scope


def _normalize_focus_for_compare(focus: Mapping[str, Any] | None) -> dict[str, str | None]:
    if focus is None:
        return {"kind": "none", "session_id": None}
    kind = focus.get("kind")
    session_id = focus.get("session_id", focus.get("sessionId"))
    return {
        "kind": None if kind is None else str(kind),
        "session_id": None if session_id is None else str(session_id),
    }


def _tool_event_scope_matches(
    event: HermesGraphToolEvent,
    scope: _DispatchedScope,
) -> bool:
    if event.world_id is not None and event.world_id != scope.world_id:
        return False
    if event.campaign_id is not None and event.campaign_id != scope.campaign_id:
        return False
    if event.admissibility is not None and event.admissibility != scope.admissibility:
        return False
    if event.revision_pin is not None and event.revision_pin != scope.revision_id:
        return False
    if event.focus is not None:
        event_focus = _normalize_focus_for_compare(event.focus)
        scope_focus = _normalize_focus_for_compare(scope.focus)
        if event_focus != scope_focus:
            return False
    return True


def _is_evidence_bearing(
    event: HermesGraphToolEvent,
    scope: _DispatchedScope,
) -> bool:
    if event.state != "completion":
        return False
    if not _tool_event_scope_matches(event, scope):
        return False
    outcome = (event.outcome or "").strip().lower()
    if outcome in EMPTY_DENIED_OUTCOMES or outcome == UNAVAILABLE_OUTCOME:
        return False
    if not outcome:
        return False
    if not list(event.source_anchor_ids):
        return False
    return True


def _project_tool_event(event: HermesGraphToolEvent) -> dict[str, Any]:
    focus = None
    if event.focus is not None:
        focus = _normalize_focus_for_compare(event.focus)
    return {
        "tool_name": event.tool_name,
        "state": event.state,
        "duration_ms": event.duration_ms,
        "world_id": event.world_id,
        "campaign_id": event.campaign_id,
        "focus": focus,
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


def _unique_source_anchors(events: Sequence[HermesGraphToolEvent]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for event in events:
        for anchor_id in event.source_anchor_ids:
            if anchor_id in seen:
                continue
            seen.add(anchor_id)
            ordered.append(anchor_id)
    return ordered


def classify_hermes_graph_result(
    result: HermesGraphAgentTurnResult,
    *,
    scope: _DispatchedScope,
) -> tuple[GroundingState, str, list[str], list[str], str | None]:
    """Classify grounding from status + final_response + tool_events only.

    Returns ``(state, answer, warnings, diagnostic_codes, error_code)``.
    ``result.messages`` is intentionally ignored.
    """
    _ = result.messages  # transcript is never evidence for PR354

    projected_ok = True
    try:
        for event in result.tool_events:
            _project_tool_event(event)
    except Exception:
        projected_ok = False
    if not projected_ok:
        return (
            "error",
            EXECUTION_ERROR_ANSWER,
            [],
            ["hermes_grounding_contract_error"],
            "hermes_grounding_contract_error",
        )

    for event in result.tool_events:
        if event.state == "completion" and not _tool_event_scope_matches(event, scope):
            return (
                "error",
                EXECUTION_ERROR_ANSWER,
                [],
                ["hermes_tool_event_scope_mismatch"],
                "hermes_grounding_contract_error",
            )

    if result.status == "error":
        error_code = result.error_code or "hermes_graph_agent_error"
        return (
            "error",
            EXECUTION_ERROR_ANSWER,
            [],
            [error_code],
            error_code,
        )

    completions = [event for event in result.tool_events if event.state == "completion"]
    if any(
        (event.outcome or "").strip().lower() == UNAVAILABLE_OUTCOME
        for event in completions
    ) and not any(_is_evidence_bearing(event, scope) for event in completions):
        return (
            "error",
            EXECUTION_ERROR_ANSWER,
            [],
            ["hermes_graph_unavailable"],
            "hermes_graph_unavailable",
        )

    evidence = [event for event in completions if _is_evidence_bearing(event, scope)]
    final_response = (result.final_response or "").strip()

    if not evidence:
        return ("abstained", ABSTENTION_ANSWER, [], ["hermes_insufficient_evidence"], None)

    warnings: list[str] = []
    diagnostic_codes: list[str] = []
    for event in evidence:
        diagnostic_codes.extend(list(event.diagnostic_codes))
    is_partial = any(
        (event.outcome or "").strip().lower() in PARTIAL_OUTCOMES for event in evidence
    )
    if is_partial:
        warnings.append(PARTIAL_COVERAGE_WARNING)
        diagnostic_codes.append("hermes_partial_coverage")
        if not final_response:
            return ("abstained", ABSTENTION_ANSWER, warnings, diagnostic_codes, None)
        return ("partial", final_response, warnings, diagnostic_codes, None)

    if not final_response:
        return ("abstained", ABSTENTION_ANSWER, warnings, diagnostic_codes, None)
    return ("grounded", final_response, warnings, diagnostic_codes, None)


def _grounding_block(
    *,
    state: GroundingState,
    scope: _DispatchedScope,
    tool_events: Sequence[HermesGraphToolEvent],
    diagnostic_codes: Sequence[str],
    warnings: Sequence[str],
) -> dict[str, Any]:
    evidence = [event for event in tool_events if _is_evidence_bearing(event, scope)]
    anchors = _unique_source_anchors(evidence)
    return {
        "schema": GROUNDING_SCHEMA,
        "state": state,
        "world_id": scope.world_id,
        "campaign_id": scope.campaign_id,
        "focus": dict(scope.focus),
        "admissibility": scope.admissibility,
        "revision_id": scope.revision_id,
        "successful_tool_count": len(evidence),
        "source_anchor_count": len(anchors),
        "diagnostic_codes": list(dict.fromkeys(diagnostic_codes)),
        "warnings": list(warnings),
    }


def _agent_trace(
    *,
    state: GroundingState,
    result: HermesGraphAgentTurnResult,
    tool_events: Sequence[dict[str, Any]],
    warnings: Sequence[str],
    started_at: str,
    completed_at: str,
    elapsed_ms: int,
) -> dict[str, Any]:
    status = {
        "grounded": "ok",
        "partial": "partial",
        "abstained": "abstained",
        "error": "error",
    }[state]
    return {
        "trace_id": _new_trace_id(),
        "runtime": RUNTIME,
        "backend": BACKEND,
        "mode": MODE,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "elapsed_ms": elapsed_ms,
        "hermes_session_id": result.hermes_session_id or None,
        "process_isolation": result.process_isolation,
        "tool_events": list(tool_events),
        "warnings": list(warnings),
    }


def _top_level_status(state: GroundingState) -> str:
    if state == "grounded":
        return "ok"
    if state in {"partial", "abstained"}:
        return "partial"
    return "error"


def build_hermes_graph_product_response(
    *,
    packet: Mapping[str, Any],
    result: HermesGraphAgentTurnResult,
    scope: _DispatchedScope,
    agent_thread_id: str | None,
    turn_id: str | None,
    started_at: str,
    completed_at: str,
    elapsed_ms: int,
    world_graph_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state, answer, warnings, diagnostic_codes, error_code = classify_hermes_graph_result(
        result,
        scope=scope,
    )
    projected_events = [_project_tool_event(event) for event in result.tool_events]
    response: dict[str, Any] = {
        "schema": LIVE_QUERY_SCHEMA,
        "query_id": _new_query_id(),
        "session": int(packet["session"]),
        "mode": MODE,
        "status": _top_level_status(state),
        "answer": answer,
        "classification": {
            "intent": MODE,
            "latency_mode": MODE,
            "event_type": MODE,
        },
        "events_written": [],
        "jobs_queued": [],
        "next_suggestions": [],
        "diagnostics": (
            {"error_code": error_code}
            if error_code is not None
            else {"grounding_state": state}
        ),
        "provenance": {
            "backend": BACKEND,
            "runtime": RUNTIME,
            "mode": MODE,
            "process_isolation": result.process_isolation,
        },
        "citations": [],
        "context_packet": None,
        "warnings": list(warnings),
        "mutations": [],
        "grounding": _grounding_block(
            state=state,
            scope=scope,
            tool_events=result.tool_events,
            diagnostic_codes=diagnostic_codes,
            warnings=warnings,
        ),
        "agent_trace": _agent_trace(
            state=state,
            result=result,
            tool_events=projected_events,
            warnings=warnings,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_ms=elapsed_ms,
        ),
        "agent_thread_id": agent_thread_id,
        "turn_id": turn_id,
        "hermes_session": None,
    }
    if world_graph_context is not None:
        response["world_graph_context"] = dict(world_graph_context)
    return response


def run_hermes_graph_query(
    *,
    text: str,
    packet: Mapping[str, Any],
    graph_envelope: Mapping[str, Any],
    agent_thread_id: str | None,
    turn_id: str | None,
    root: Path | None = None,
    host_factory: HostFactory | None = None,
) -> dict[str, Any]:
    """Execute one authoritative Hermes graph turn and return a product envelope.

    Calls ``host.execute`` exactly once. Host-owned pre-accept retry remains
    inside the host; this adapter never retries.
    """
    request, scope = build_hermes_graph_turn_request(
        question=text,
        graph_envelope=graph_envelope,
        root=root,
    )
    factory = host_factory or get_hermes_graph_agent_host
    host = factory()
    started_at = _utc_now_z()
    started_mono = time.monotonic()
    result = host.execute(request)
    completed_at = _utc_now_z()
    elapsed_ms = max(0, int((time.monotonic() - started_mono) * 1000))
    return build_hermes_graph_product_response(
        packet=packet,
        result=result,
        scope=scope,
        agent_thread_id=agent_thread_id,
        turn_id=turn_id,
        started_at=started_at,
        completed_at=completed_at,
        elapsed_ms=elapsed_ms,
        world_graph_context=graph_envelope,
    )


__all__ = [
    "ABSTENTION_ANSWER",
    "EXECUTION_ERROR_ANSWER",
    "HermesGraphQueryRequestError",
    "build_hermes_graph_product_response",
    "build_hermes_graph_turn_request",
    "classify_hermes_graph_result",
    "run_hermes_graph_query",
    "validate_hermes_query_inputs",
]
