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
from graph_memory.interaction.answer_validator import (
    ABSTENTION_ANSWER as CLAIM_ABSTENTION_ANSWER,
    validate_structured_answer,
)
from graph_memory.interaction.forensic import (
    build_forensic_envelope,
    forensic_enabled,
)
from graph_memory.interaction.initial_resolve import create_session_from_preflight
from graph_memory.interaction.session import GraphRetrievalSession
from graph_memory.interaction.session_hydrate import hydrate_session_from_packet
from graph_memory.interaction.session_store import get_session, replace_session

GroundingState = Literal[
    "grounded",
    "partial",
    "abstained",
    "error",
    "graph_grounded",
    "source_verified",
    "partial_coverage",
    "inferred_from_graph",
]
HostFactory = Callable[[], HermesGraphAgentHost]

GROUNDING_SCHEMA = "dmb_hermes_graph_grounding_v1"
CITATION_SCHEMA = "dmb_world_graph_anchor_citation_v1"
SOURCE_CITATION_SCHEMA = "dmb_source_citation_v1"
GRAPH_REFERENCE_SCHEMA = "dmb_graph_reference_v1"
LIVE_QUERY_SCHEMA = "dmb_live_query_response_v1"
VALIDATION_ERROR_SCHEMA = "dmb_live_query_validation_error_v1"
MODE = "hermes_graph_agent"
RUNTIME = "process_isolated"
BACKEND = "hermes"

ABSTENTION_ANSWER = CLAIM_ABSTENTION_ANSWER
EXECUTION_ERROR_ANSWER = (
    "DungeonBuddy could not complete this World Graph Hermes turn. "
    "No legacy retrieval fallback was used."
)
UNAVAILABLE_ANSWER = (
    "DungeonBuddy’s World Graph is currently unavailable for this query. "
    "No legacy retrieval fallback was used."
)
PARTIAL_COVERAGE_WARNING = (
    "Graph retrieval returned partial or truncated evidence; treat the answer as qualified."
)

# Canonical World Graph retrieval outcomes (PR010A / Rung 3).
CANONICAL_RETRIEVAL_OUTCOMES = frozenset(
    {"enough", "partial", "empty", "denied", "truncated", "unavailable"}
)
EVIDENCE_BEARING_OUTCOMES = frozenset({"enough", "partial", "truncated"})
PARTIAL_OUTCOMES = frozenset({"partial", "truncated"})
UNAVAILABLE_OUTCOME = "unavailable"
WORLD_GRAPH_UNAVAILABLE_CODE = "world_graph_unavailable"
GRAPH_TOOL_ERROR_CODE = "hermes_graph_tool_error"

MAX_HERMES_HISTORY_MESSAGES = 12
MAX_HERMES_HISTORY_MESSAGE_CHARS = 4000
MAX_HERMES_HISTORY_TOTAL_CHARS = 16000
_ALLOWED_HISTORY_ROLES = frozenset({"user", "assistant"})


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


def _usage_unavailable() -> dict[str, Any]:
    """Existing Plan TraceDetailsPanel requires usage.available."""
    return {
        "available": False,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }


def _history_invalid(message: str) -> HermesGraphQueryRequestError:
    return HermesGraphQueryRequestError(message, code="hermes_history_invalid")


def normalize_hermes_conversation_history(value: Any) -> list[dict[str, str]] | None:
    """Strict service/route normalizer for optional prior visible prose."""
    if value is None:
        return None
    if not isinstance(value, list):
        raise _history_invalid("conversation_history must be a list, null, or absent.")
    if len(value) == 0:
        return None
    if len(value) > MAX_HERMES_HISTORY_MESSAGES:
        raise _history_invalid("conversation_history exceeds maximum message count.")
    if len(value) % 2 != 0:
        raise _history_invalid(
            "conversation_history must contain complete user/assistant pairs."
        )

    normalized: list[dict[str, str]] = []
    total_chars = 0
    for index, item in enumerate(value):
        expected_role = "user" if index % 2 == 0 else "assistant"
        if not isinstance(item, Mapping) or isinstance(item, (str, bytes)):
            raise _history_invalid("conversation_history entries must be objects.")
        unknown = set(item.keys()) - {"role", "content"}
        if unknown:
            raise _history_invalid("conversation_history entries contain unknown keys.")
        role = item.get("role")
        if role not in _ALLOWED_HISTORY_ROLES:
            raise _history_invalid("conversation_history role must be user or assistant.")
        if role != expected_role:
            raise _history_invalid(
                "conversation_history messages must alternate user then assistant."
            )
        content_raw = item.get("content")
        if not isinstance(content_raw, str):
            raise _history_invalid("conversation_history content must be a string.")
        content = content_raw.strip()
        if not content:
            raise _history_invalid("conversation_history content must be non-empty.")
        if len(content) > MAX_HERMES_HISTORY_MESSAGE_CHARS:
            raise _history_invalid("conversation_history message exceeds maximum length.")
        total_chars += len(content)
        if total_chars > MAX_HERMES_HISTORY_TOTAL_CHARS:
            raise _history_invalid("conversation_history exceeds total content budget.")
        normalized.append({"role": role, "content": content})
    return normalized


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
    conversation_history: list[dict[str, str]] | None = None,
    retrieval_session: GraphRetrievalSession | None = None,
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
    history_copy = (
        [{"role": item["role"], "content": item["content"]} for item in conversation_history]
        if conversation_history
        else None
    )
    session = retrieval_session
    if session is None:
        session = create_session_from_preflight(graph_envelope, question=question)
    retrieval_session_packet = session.project_for_hermes()
    latest_recap_change = graph_envelope.get("latest_recap_change")
    if isinstance(latest_recap_change, Mapping):
        retrieval_session_packet["latest_recap_change"] = dict(latest_recap_change)
    request = HermesGraphAgentTurnRequest(
        question=question,
        world_id=world_id,
        campaign_id=campaign_id,
        focus=host_focus,
        admissibility=admissibility,
        revision_pin=revision_id,
        conversation_history=history_copy,
        session_id=None,
        root=graph_root,
        capability_policy=None,
        retrieval_session_id=session.id,
        retrieval_session=retrieval_session_packet,
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


def _tool_event_scope_contradicts(
    event: HermesGraphToolEvent,
    scope: _DispatchedScope,
) -> bool:
    """True when the event asserts a scope field that differs from dispatched.

    Missing fields are not contradictions; they fail the complete-match check
    used for evidence instead.
    """
    if event.world_id is not None and event.world_id != scope.world_id:
        return True
    if event.campaign_id is not None and event.campaign_id != scope.campaign_id:
        return True
    if event.admissibility is not None and event.admissibility != scope.admissibility:
        return True
    if event.revision_pin is not None and event.revision_pin != scope.revision_id:
        return True
    if event.focus is not None:
        event_focus = _normalize_focus_for_compare(event.focus)
        scope_focus = _normalize_focus_for_compare(scope.focus)
        if event_focus != scope_focus:
            return True
    return False


def _tool_event_scope_matches(
    event: HermesGraphToolEvent,
    scope: _DispatchedScope,
) -> bool:
    """Fail closed: every authoritative scope field must be present and equal."""
    if event.world_id is None or event.world_id != scope.world_id:
        return False
    if event.campaign_id is None or event.campaign_id != scope.campaign_id:
        return False
    if event.admissibility is None or event.admissibility != scope.admissibility:
        return False
    if event.revision_pin is None or event.revision_pin != scope.revision_id:
        return False
    if event.focus is None:
        return False
    event_focus = _normalize_focus_for_compare(event.focus)
    scope_focus = _normalize_focus_for_compare(scope.focus)
    return event_focus == scope_focus


def _normalized_outcome(event: HermesGraphToolEvent) -> str | None:
    raw = (event.outcome or "").strip().lower()
    if not raw:
        return None
    if raw not in CANONICAL_RETRIEVAL_OUTCOMES:
        return None
    return raw


def _is_evidence_bearing(
    event: HermesGraphToolEvent,
    scope: _DispatchedScope,
) -> bool:
    """Legacy helper retained for trace projection.

    Product acceptance no longer treats nonempty source_anchor_ids as grounding.
    Claim-class authority in validate_structured_answer owns acceptance.
    """
    if event.state != "completion":
        return False
    if not _tool_event_scope_matches(event, scope):
        return False
    outcome = _normalized_outcome(event)
    if outcome is None or outcome not in EVIDENCE_BEARING_OUTCOMES:
        return False
    # Accept completions that returned matched nodes/relationships even without anchors.
    if list(event.source_anchor_ids) or list(event.matched_node_ids) or list(event.relationship_ids):
        return True
    return False


def _map_outcome_to_legacy_grounding(outcome: str) -> GroundingState:
    if outcome in {"graph_grounded", "source_verified"}:
        return "grounded"
    if outcome in {"partial_coverage", "inferred_from_graph", "conflicting_authority"}:
        return "partial"
    if outcome == "execution_error":
        return "error"
    if outcome in {"abstained", "unsupported"}:
        return "abstained"
    return "abstained"


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


def _safe_projected_tool_events(
    events: Sequence[HermesGraphToolEvent],
    scope: _DispatchedScope,
) -> tuple[list[dict[str, Any]], bool, bool]:
    """Project in-scope events; drop contradictory (foreign) events entirely.

    Returns ``(projected, saw_mismatch, projection_ok)``. On any projection
    failure, returns an empty projected list and ``projection_ok=False`` so the
    product envelope can stay a typed grounding-contract error.
    """
    projected: list[dict[str, Any]] = []
    saw_mismatch = False
    try:
        for event in events:
            if _tool_event_scope_contradicts(event, scope):
                saw_mismatch = True
                continue
            projected.append(_project_tool_event(event))
    except Exception:
        return [], saw_mismatch, False
    return projected, saw_mismatch, True


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


def _graph_citations_from_evidence(
    *,
    state: GroundingState,
    scope: _DispatchedScope,
    tool_events: Sequence[HermesGraphToolEvent],
) -> list[dict[str, Any]]:
    """Legacy anchor citation projection — unused when claim acceptance is present.

    Kept for fallback paths without a retrieval session. Prefer
    ``_citations_from_acceptance`` which separates graph references from
    source citations created only after successful integrity-checked reads.
    """
    if state not in {"grounded", "partial"}:
        return []
    evidence = [event for event in tool_events if _is_evidence_bearing(event, scope)]
    anchors = _unique_source_anchors(evidence)
    focus = dict(scope.focus)
    return [
        {
            "schema": CITATION_SCHEMA,
            "kind": "world_graph_anchor",
            "anchor_id": anchor_id,
            "world_id": scope.world_id,
            "campaign_id": scope.campaign_id,
            "focus": focus,
            "admissibility": scope.admissibility,
            "revision_id": scope.revision_id,
        }
        for anchor_id in anchors
    ]


def _citations_from_acceptance(
    acceptance: Mapping[str, Any],
    *,
    scope: _DispatchedScope,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(legacy_citations, graph_references, source_citations)``."""
    graph_refs = [
        dict(item)
        for item in acceptance.get("graph_references") or []
        if isinstance(item, Mapping)
    ]
    source_cites = [
        dict(item)
        for item in acceptance.get("source_citations") or []
        if isinstance(item, Mapping)
    ]
    # Product citations array prefers successful source citations; otherwise
    # project graph references so the UI still has claim-level referents.
    focus = dict(scope.focus)
    if source_cites:
        legacy = [
            {
                "schema": SOURCE_CITATION_SCHEMA,
                "kind": "source_citation",
                "anchor_id": cite.get("anchorId") or cite.get("anchor_id"),
                "world_id": scope.world_id,
                "campaign_id": scope.campaign_id,
                "focus": focus,
                "admissibility": scope.admissibility,
                "revision_id": cite.get("revisionId") or cite.get("revision_id") or scope.revision_id,
                "source_artifact_id": cite.get("sourceArtifactId") or cite.get("source_artifact_id"),
                "content_sha256": cite.get("contentSha256") or cite.get("content_sha256"),
                "source_read_id": cite.get("sourceReadId") or cite.get("source_read_id"),
            }
            for cite in source_cites
        ]
    else:
        legacy = [
            {
                "schema": GRAPH_REFERENCE_SCHEMA,
                "kind": "graph_reference",
                "object_id": ref.get("objectId") or ref.get("object_id"),
                "object_kind": ref.get("objectKind") or ref.get("object_kind"),
                "claim_id": ref.get("claimId") or ref.get("claim_id"),
                "label": ref.get("label"),
                "world_id": scope.world_id,
                "campaign_id": scope.campaign_id,
                "focus": focus,
                "admissibility": scope.admissibility,
                "revision_id": ref.get("revisionId") or ref.get("revision_id") or scope.revision_id,
            }
            for ref in graph_refs
        ]
    return legacy, graph_refs, source_cites


def _later_evidence_recovers(
    events: Sequence[HermesGraphToolEvent],
    *,
    after_index: int,
    scope: _DispatchedScope,
) -> bool:
    for later in events[after_index + 1 :]:
        if _is_evidence_bearing(later, scope):
            return True
    return False


def _unrecovered_error_events(
    events: Sequence[HermesGraphToolEvent],
    scope: _DispatchedScope,
) -> list[HermesGraphToolEvent]:
    """Error-state tool events not followed by a later evidence-bearing completion."""
    unrecovered: list[HermesGraphToolEvent] = []
    for index, event in enumerate(events):
        if event.state != "error":
            continue
        if _tool_event_scope_contradicts(event, scope):
            continue
        if _later_evidence_recovers(events, after_index=index, scope=scope):
            continue
        unrecovered.append(event)
    return unrecovered


def _error_code_from_tool_events(events: Sequence[HermesGraphToolEvent]) -> tuple[str, list[str]]:
    codes: list[str] = []
    schemas: list[str] = []
    for event in events:
        codes.extend(str(code) for code in event.diagnostic_codes if code)
        if event.retrieval_schema:
            schemas.append(str(event.retrieval_schema))
    deduped = list(dict.fromkeys([*codes, *schemas]))
    if codes:
        return str(codes[0]), deduped
    if schemas:
        return GRAPH_TOOL_ERROR_CODE, deduped
    return GRAPH_TOOL_ERROR_CODE, [GRAPH_TOOL_ERROR_CODE]


def classify_hermes_graph_result(
    result: HermesGraphAgentTurnResult,
    *,
    scope: _DispatchedScope,
    projection_ok: bool | None = None,
    retrieval_session: GraphRetrievalSession | None = None,
) -> tuple[GroundingState, str, list[str], list[str], str | None, dict[str, Any]]:
    """Classify grounding from the shared claim ledger first.

    Returns
    ``(state, answer, warnings, diagnostic_codes, error_code, acceptance_detail)``.
    ``result.messages`` is intentionally ignored as factual authority.
    """
    _ = result.messages  # transcript is never factual authority

    if projection_ok is None:
        _, _, projection_ok = _safe_projected_tool_events(result.tool_events, scope)
    if not projection_ok:
        return (
            "error",
            EXECUTION_ERROR_ANSWER,
            [],
            ["hermes_grounding_contract_error"],
            "hermes_grounding_contract_error",
            {"state": "execution_error", "reason_codes": ["projection_failed"]},
        )

    for event in result.tool_events:
        if event.state in {"completion", "error"} and _tool_event_scope_contradicts(
            event, scope
        ):
            return (
                "error",
                EXECUTION_ERROR_ANSWER,
                [],
                ["hermes_tool_event_scope_mismatch"],
                "hermes_grounding_contract_error",
                {"state": "execution_error", "reason_codes": ["scope_mismatch"]},
            )

    if result.status == "error":
        error_code = result.error_code or "hermes_graph_agent_error"
        return (
            "error",
            EXECUTION_ERROR_ANSWER,
            [],
            [error_code],
            error_code,
            {"state": "execution_error", "reason_codes": [error_code]},
        )

    unrecovered_errors = _unrecovered_error_events(result.tool_events, scope)
    if unrecovered_errors:
        error_code, diagnostic_codes = _error_code_from_tool_events(unrecovered_errors)
        return (
            "error",
            EXECUTION_ERROR_ANSWER,
            [],
            diagnostic_codes,
            error_code,
            {"state": "execution_error", "reason_codes": diagnostic_codes},
        )

    session = retrieval_session
    if session is None and result.retrieval_session is not None:
        try:
            session = hydrate_session_from_packet(result.retrieval_session)
        except Exception:
            session = None
    if session is None and result.retrieval_session_id:
        session = get_session(result.retrieval_session_id)

    if session is not None:
        validated = validate_structured_answer(
            session,
            None,
            model_prose=(result.final_response or "").strip() or None,
            execution_error=False,
        )
        replace_session(session)
        legacy_state = _map_outcome_to_legacy_grounding(validated.outcome)
        acceptance = {
            "state": validated.outcome,
            "reason_codes": list(validated.reason_codes),
            "accepted_claim_ids": list(validated.accepted_claim_ids),
            "rejected_claim_ids": list(validated.rejected_claim_ids),
            "graph_references": [
                ref.model_dump(mode="json")
                for ref in validated.graph_references
            ],
            "source_citations": [
                cite.model_dump(mode="json")
                for cite in validated.source_citations
            ],
        }
        return (
            legacy_state,
            validated.answer_text,
            list(validated.warnings),
            list(validated.diagnostic_codes),
            None,
            acceptance,
        )

    # Fallback path without a retrieval session: prefer matched nodes over anchors.
    completions = [event for event in result.tool_events if event.state == "completion"]
    evidence = [event for event in completions if _is_evidence_bearing(event, scope)]
    final_response = (result.final_response or "").strip()
    if not evidence:
        return (
            "abstained",
            ABSTENTION_ANSWER,
            [],
            ["hermes_insufficient_evidence"],
            None,
            {"state": "abstained", "reason_codes": ["no_session_no_evidence"]},
        )
    is_partial = any(_normalized_outcome(event) in PARTIAL_OUTCOMES for event in evidence)
    if is_partial:
        return (
            "partial",
            final_response or ABSTENTION_ANSWER,
            [PARTIAL_COVERAGE_WARNING],
            ["hermes_partial_coverage"],
            None,
            {"state": "partial_coverage", "reason_codes": ["legacy_partial"]},
        )
    if not final_response:
        return (
            "abstained",
            ABSTENTION_ANSWER,
            [],
            ["hermes_insufficient_evidence"],
            None,
            {"state": "abstained", "reason_codes": ["empty_final_response"]},
        )
    return (
        "grounded",
        final_response,
        [],
        [],
        None,
        {"state": "graph_grounded", "reason_codes": ["legacy_matched_ids"]},
    )


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
        # Existing Plan TraceDetailsPanel contract (required shell fields).
        "usage": _usage_unavailable(),
        "steps": [],
        "context_summary": {},
        "artifact_refs": [],
        # Additive for PR355 graph-trace presentation.
        "tool_events": list(tool_events),
        "warnings": list(warnings),
    }


def _top_level_status(state: GroundingState) -> str:
    if state == "grounded":
        return "ok"
    if state in {"partial", "abstained"}:
        return "partial"
    return "error"


def _scope_from_unavailable_envelope(graph_envelope: Mapping[str, Any]) -> _DispatchedScope:
    focus_raw = graph_envelope.get("focus")
    focus_map = focus_raw if isinstance(focus_raw, Mapping) else None
    return _DispatchedScope(
        world_id=str(graph_envelope.get("world_id") or "").strip() or "world:unknown",
        campaign_id=str(graph_envelope.get("campaign_id") or "").strip() or "campaign:unknown",
        focus=_focus_for_grounding(focus_map),
        admissibility=str(graph_envelope.get("admissibility") or "gm"),
        revision_id="",
    )


def build_hermes_graph_unavailable_response(
    *,
    packet: Mapping[str, Any],
    graph_envelope: Mapping[str, Any],
    agent_thread_id: str | None,
    turn_id: str | None,
    started_at: str | None = None,
    completed_at: str | None = None,
    elapsed_ms: int = 0,
) -> dict[str, Any]:
    """Typed product error when the resolved graph is unavailable — no host call."""
    started = started_at or _utc_now_z()
    completed = completed_at or started
    scope = _scope_from_unavailable_envelope(graph_envelope)
    empty_result = HermesGraphAgentTurnResult(
        status="error",
        final_response=None,
        messages=[],
        hermes_session_id="",
        tool_events=[],
        error_code=WORLD_GRAPH_UNAVAILABLE_CODE,
        error_message=UNAVAILABLE_ANSWER,
        process_isolation="process_exclusive",
    )
    return {
        "schema": LIVE_QUERY_SCHEMA,
        "query_id": _new_query_id(),
        "session": int(packet["session"]),
        "mode": MODE,
        "status": "error",
        "answer": UNAVAILABLE_ANSWER,
        "classification": {
            "intent": MODE,
            "latency_mode": MODE,
            "event_type": MODE,
        },
        "events_written": [],
        "jobs_queued": [],
        "next_suggestions": [],
        "diagnostics": {"error_code": WORLD_GRAPH_UNAVAILABLE_CODE},
        "provenance": {
            "backend": BACKEND,
            "runtime": RUNTIME,
            "mode": MODE,
        },
        "citations": [],
        "context_packet": None,
        "warnings": [WORLD_GRAPH_UNAVAILABLE_CODE],
        "mutations": [],
        "grounding": {
            "schema": GROUNDING_SCHEMA,
            "state": "error",
            "world_id": scope.world_id,
            "campaign_id": scope.campaign_id,
            "focus": dict(scope.focus),
            "admissibility": scope.admissibility,
            "revision_id": None,
            "successful_tool_count": 0,
            "source_anchor_count": 0,
            "diagnostic_codes": [WORLD_GRAPH_UNAVAILABLE_CODE],
            "warnings": [WORLD_GRAPH_UNAVAILABLE_CODE],
        },
        "agent_trace": _agent_trace(
            state="error",
            result=empty_result,
            tool_events=[],
            warnings=[WORLD_GRAPH_UNAVAILABLE_CODE],
            started_at=started,
            completed_at=completed,
            elapsed_ms=elapsed_ms,
        ),
        "agent_thread_id": agent_thread_id,
        "turn_id": turn_id,
        "hermes_session": None,
        "world_graph_context": dict(graph_envelope),
    }


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
    retrieval_session: GraphRetrievalSession | None = None,
) -> dict[str, Any]:
    # Project once behind a safe boundary; reuse for classification and trace.
    projected_events, saw_mismatch, projection_ok = _safe_projected_tool_events(
        result.tool_events,
        scope,
    )
    acceptance: dict[str, Any] = {}
    if not projection_ok:
        state: GroundingState = "error"
        answer = EXECUTION_ERROR_ANSWER
        warnings: list[str] = []
        diagnostic_codes = ["hermes_grounding_contract_error"]
        error_code: str | None = "hermes_grounding_contract_error"
        projected_events = []
        grounding_events: Sequence[HermesGraphToolEvent] = []
        acceptance = {"state": "execution_error", "reason_codes": ["projection_failed"]}
    else:
        state, answer, warnings, diagnostic_codes, error_code, acceptance = (
            classify_hermes_graph_result(
                result,
                scope=scope,
                projection_ok=True,
                retrieval_session=retrieval_session,
            )
        )
        grounding_events = result.tool_events
        if saw_mismatch and "hermes_tool_event_scope_mismatch" not in diagnostic_codes:
            diagnostic_codes = [*diagnostic_codes, "hermes_tool_event_scope_mismatch"]

    graph_refs: list[dict[str, Any]] = []
    source_cites: list[dict[str, Any]] = []
    if acceptance.get("graph_references") is not None or acceptance.get("source_citations") is not None:
        citations, graph_refs, source_cites = _citations_from_acceptance(
            acceptance,
            scope=scope,
        )
    else:
        citations = _graph_citations_from_evidence(
            state=state,
            scope=scope,
            tool_events=grounding_events,
        )
    grounding = _grounding_block(
        state=state,
        scope=scope,
        tool_events=grounding_events,
        diagnostic_codes=diagnostic_codes,
        warnings=warnings,
    )
    latest_recap_change = (
        world_graph_context.get("latest_recap_change")
        if isinstance(world_graph_context, Mapping)
        and isinstance(world_graph_context.get("latest_recap_change"), Mapping)
        else None
    )
    if latest_recap_change is not None:
        grounding["latest_recap_change"] = dict(latest_recap_change)
    acceptance_state = str(acceptance.get("state") or state)
    grounding["acceptance_state"] = acceptance_state
    grounding["accepted_claim_ids"] = list(acceptance.get("accepted_claim_ids") or [])
    grounding["rejected_claim_ids"] = list(acceptance.get("rejected_claim_ids") or [])
    grounding["reason_codes"] = list(acceptance.get("reason_codes") or [])
    if state in {"grounded", "partial"}:
        grounding["source_anchor_count"] = len(source_cites) if source_cites else 0
        grounding["graph_reference_count"] = len(graph_refs)
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
            else {
                "grounding_state": state,
                "acceptance_state": acceptance_state,
            }
        ),
        "provenance": {
            "backend": BACKEND,
            "runtime": RUNTIME,
            "mode": MODE,
            "process_isolation": result.process_isolation,
        },
        "citations": citations,
        "graph_references": graph_refs,
        "source_citations": source_cites,
        "context_packet": None,
        "warnings": list(warnings),
        "mutations": [],
        "grounding": grounding,
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
        "retrieval_session_id": result.retrieval_session_id,
    }
    if latest_recap_change is not None:
        response["latest_recap_change"] = dict(latest_recap_change)
    if world_graph_context is not None:
        response["world_graph_context"] = dict(world_graph_context)
    if forensic_enabled():
        preflight_ids: list[str] = []
        if isinstance(world_graph_context, Mapping):
            matched = world_graph_context.get("matched_node_ids") or []
            if isinstance(matched, list):
                preflight_ids = [str(item) for item in matched if item]
        response["forensic"] = build_forensic_envelope(
            retrieval_session_id=result.retrieval_session_id,
            preflight_candidate_ids=preflight_ids,
            agent_seed_ids=list(acceptance.get("accepted_claim_ids") or []),
            tool_events=[_project_tool_event(event) for event in result.tool_events],
            acceptance=acceptance,
        )
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
    conversation_history: Any | None = None,
) -> dict[str, Any]:
    """Execute one authoritative Hermes graph turn and return a product envelope.

    Calls ``host.execute`` exactly once. Host-owned pre-accept retry remains
    inside the host; this adapter never retries.
    """
    # Fail closed on malformed history before unavailable short-circuit or host work.
    normalized_history = normalize_hermes_conversation_history(conversation_history)
    if str(graph_envelope.get("status") or "") == "unavailable":
        return build_hermes_graph_unavailable_response(
            packet=packet,
            graph_envelope=graph_envelope,
            agent_thread_id=agent_thread_id,
            turn_id=turn_id,
        )

    request, scope = build_hermes_graph_turn_request(
        question=text,
        graph_envelope=graph_envelope,
        root=root,
        conversation_history=normalized_history,
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
    "MAX_HERMES_HISTORY_MESSAGE_CHARS",
    "MAX_HERMES_HISTORY_MESSAGES",
    "MAX_HERMES_HISTORY_TOTAL_CHARS",
    "UNAVAILABLE_ANSWER",
    "HermesGraphQueryRequestError",
    "build_hermes_graph_product_response",
    "build_hermes_graph_turn_request",
    "build_hermes_graph_unavailable_response",
    "classify_hermes_graph_result",
    "normalize_hermes_conversation_history",
    "run_hermes_graph_query",
    "validate_hermes_query_inputs",
]
