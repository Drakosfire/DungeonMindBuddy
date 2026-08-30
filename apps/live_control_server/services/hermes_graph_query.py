"""PR354: route one Hermes live-query turn through AgentRuntime.

Owns World scope, retrieval-session construction, grounding classification,
safe tool-event projection, abstention, and typed execution errors.
Harness execution crosses exactly one ``AgentRuntime.run(...)`` seam.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from apps.live_control_server.services.agent_context_assembler import (
    AgentContextAssembly,
    AgentContextAssemblyError,
    assemble_agent_graph_context,
)
from apps.live_control_server.services.agent_runtime import (
    HERMES_RUNTIME_DESCRIPTOR,
    AgentRuntime,
    AgentRuntimeDescriptor,
    AgentRuntimeInvocation,
    AgentRuntimeResult,
    AgentRuntimeToolEvent,
    descriptor_for_runtime,
)
from apps.live_control_server.services.agent_turn_trace import AgentTurnTraceBuilder
from apps.live_control_server.services.hermes_session_store import (
    HermesPointerResolution,
    HermesSessionPointerBinding,
    HermesSessionPointerError,
    HermesSessionPointerStore,
)
from apps.live_control_server.services.hermes_graph_interaction_tools import (
    HERMES_GRAPH_INTERACTION_TOOL_NAMES as HERMES_GRAPH_READ_TOOL_NAMES,
)
from graph_memory.interaction.answer_validator import (
    ABSTENTION_ANSWER as CLAIM_ABSTENTION_ANSWER,
    validate_structured_answer,
)
from graph_memory.interaction.forensic import (
    build_forensic_envelope,
    forensic_enabled,
)
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
    "conversation_context",
]

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
# Cardinality/request-shape failures: soft when the claim ledger already has facts.
RECOVERABLE_WHEN_CLAIMS_LANDED = frozenset({"too_many_targets", "ambiguous_target"})

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


def _new_query_id() -> str:
    return f"live-query-{uuid.uuid4().hex[:12]}"


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
    hermes_session_pointer: str | None = None,
    outer_campaign_id: str | None,
) -> None:
    """Reject Hermes-incompatible request fields before host access."""
    if world_graph_context is None:
        raise HermesGraphQueryRequestError(
            "Hermes queries require world_graph_context.",
            code="world_graph_context_required",
        )
    # Outer campaign binds the live packet; nested campaign_id is the graph lens
    # and may differ (Plan C2 packet + C1-only campaign lens is a supported path).
    _ = outer_campaign_id
    nested_scope_mode = getattr(world_graph_context, "scope_mode", None)
    if nested_scope_mode is None and isinstance(world_graph_context, Mapping):
        nested_scope_mode = world_graph_context.get("scope_mode")
    scope_mode = str(nested_scope_mode or "campaign").strip() or "campaign"
    if scope_mode not in {"campaign", "world"}:
        raise HermesGraphQueryRequestError(
            "world_graph_context.scope_mode must be 'campaign' or 'world'",
            code="invalid_request",
        )
    if request_manifest_path is not None:
        raise HermesGraphQueryRequestError(
            "Hermes graph queries do not accept legacy manifest_path.",
            code="legacy_manifest_not_supported",
        )
    if hermes_session_id is not None:
        raise HermesGraphQueryRequestError(
            "Hermes graph queries do not accept legacy hermes_session_id; "
            "use hermes_session_pointer.",
            code="hermes_continuity_not_supported",
        )
    if hermes_session_pointer is not None and not str(hermes_session_pointer).strip():
        raise HermesGraphQueryRequestError(
            "hermes_session_pointer must be a non-empty string when provided.",
            code="hermes_session_pointer_invalid",
        )


def _focus_for_grounding(focus: Mapping[str, Any] | None) -> dict[str, Any]:
    if focus is None:
        return {"kind": "none", "session_id": None, "campaign_id": None}
    return {
        "kind": str(focus.get("kind") or "none"),
        "session_id": focus.get("session_id"),
        "campaign_id": focus.get("campaign_id"),
    }


def _assemble_graph_turn(
    *,
    question: str,
    graph_envelope: Mapping[str, Any],
    root: Path | None = None,
    corpus_root: Path | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    retrieval_session: GraphRetrievalSession | None = None,
    continuity_session_id: str | None = None,
    thread_id: str | None = None,
    turn_id: str | None = None,
) -> tuple[AgentContextAssembly, _DispatchedScope]:
    """Neutral assembly + product scope, translating assembler errors."""
    try:
        assembly = assemble_agent_graph_context(
            question=question,
            graph_envelope=graph_envelope,
            root=root,
            corpus_root=corpus_root,
            conversation_history=conversation_history,
            retrieval_session=retrieval_session,
            runtime_session_id=continuity_session_id,
            thread_id=thread_id,
            turn_id=turn_id,
        )
    except AgentContextAssemblyError as exc:
        raise HermesGraphQueryRequestError(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
        ) from exc
    world_scope = assembly.invocation.context_packet.world_scope
    scope = _DispatchedScope(
        world_id=world_scope.world_id,
        campaign_id=world_scope.campaign_id,
        focus=dict(world_scope.focus),
        admissibility=world_scope.admissibility,
        revision_id=world_scope.revision_id,
    )
    return assembly, scope


def build_hermes_graph_turn_request(
    *,
    question: str,
    graph_envelope: Mapping[str, Any],
    root: Path | None = None,
    corpus_root: Path | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    retrieval_session: GraphRetrievalSession | None = None,
    continuity_session_id: str | None = None,
    thread_id: str | None = None,
    turn_id: str | None = None,
) -> tuple[AgentRuntimeInvocation, _DispatchedScope]:
    """Assemble one DMB AgentRuntime invocation from resolved World Graph context."""
    assembly, scope = _assemble_graph_turn(
        question=question,
        graph_envelope=graph_envelope,
        root=root,
        corpus_root=corpus_root,
        conversation_history=conversation_history,
        retrieval_session=retrieval_session,
        continuity_session_id=continuity_session_id,
        thread_id=thread_id,
        turn_id=turn_id,
    )
    return assembly.invocation, scope


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
    event: AgentRuntimeToolEvent,
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
    event: AgentRuntimeToolEvent,
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


def _normalized_outcome(event: AgentRuntimeToolEvent) -> str | None:
    raw = (event.outcome or "").strip().lower()
    if not raw:
        return None
    if raw not in CANONICAL_RETRIEVAL_OUTCOMES:
        return None
    return raw


def _is_evidence_bearing(
    event: AgentRuntimeToolEvent,
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
    if list(event.source_anchor_ids or []) or list(
        event.matched_node_ids or []
    ) or list(event.relationship_ids or []):
        return True
    return False


def _map_outcome_to_legacy_grounding(outcome: str) -> GroundingState:
    if outcome in {"graph_grounded", "source_verified"}:
        return "grounded"
    if outcome in {"partial_coverage", "inferred_from_graph", "conflicting_authority"}:
        return "partial"
    if outcome == "execution_error":
        return "error"
    if outcome == "conversation_context":
        return "conversation_context"
    if outcome in {"abstained", "unsupported"}:
        return "abstained"
    return "abstained"


def _project_tool_event(event: AgentRuntimeToolEvent) -> dict[str, Any]:
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
    events: Sequence[AgentRuntimeToolEvent],
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


def _unique_source_anchors(events: Sequence[AgentRuntimeToolEvent]) -> list[str]:
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
    tool_events: Sequence[AgentRuntimeToolEvent],
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
    events: Sequence[AgentRuntimeToolEvent],
    *,
    after_index: int,
    scope: _DispatchedScope,
) -> bool:
    for later in events[after_index + 1 :]:
        if _is_evidence_bearing(later, scope):
            return True
    return False


def _unrecovered_error_events(
    events: Sequence[AgentRuntimeToolEvent],
    scope: _DispatchedScope,
) -> list[AgentRuntimeToolEvent]:
    """Error-state tool events not followed by a later evidence-bearing completion."""
    unrecovered: list[AgentRuntimeToolEvent] = []
    for index, event in enumerate(events):
        if event.state != "error":
            continue
        if _tool_event_scope_contradicts(event, scope):
            continue
        if _later_evidence_recovers(events, after_index=index, scope=scope):
            continue
        unrecovered.append(event)
    return unrecovered


def _error_code_from_tool_events(events: Sequence[AgentRuntimeToolEvent]) -> tuple[str, list[str]]:
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


def _has_landed_factual_claims(session: GraphRetrievalSession) -> bool:
    return any(claim.may_state_as_campaign_fact() for claim in session.claims)


def _is_recoverable_tool_error(event: AgentRuntimeToolEvent) -> bool:
    code, _ = _error_code_from_tool_events([event])
    return code in RECOVERABLE_WHEN_CLAIMS_LANDED


def _hydrate_retrieval_session(
    result: AgentRuntimeResult,
    *,
    retrieval_session: GraphRetrievalSession | None = None,
) -> GraphRetrievalSession | None:
    session = retrieval_session
    packet = result.context_updates.get("retrieval_session")
    session_id = result.context_updates.get("retrieval_session_id")
    if session is None and isinstance(packet, Mapping):
        try:
            session = hydrate_session_from_packet(packet)
        except Exception:
            session = None
    if session is None and isinstance(session_id, str) and session_id:
        session = get_session(session_id)
    return session


def _graph_tool_event_count(events: Sequence[AgentRuntimeToolEvent]) -> int:
    return sum(1 for event in events if event.tool_name in HERMES_GRAPH_READ_TOOL_NAMES)


def _evidence_event_count(
    events: Sequence[AgentRuntimeToolEvent],
    scope: _DispatchedScope,
) -> int:
    return sum(1 for event in events if _is_evidence_bearing(event, scope))


def classify_hermes_graph_result(
    result: AgentRuntimeResult,
    *,
    scope: _DispatchedScope,
    projection_ok: bool | None = None,
    retrieval_session: GraphRetrievalSession | None = None,
    corpus_root: Path | None = None,
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

    # Hydrate before unrecovered-error short-circuit so cardinality failures can
    # soft-recover when the claim ledger already has factual claims.
    session = _hydrate_retrieval_session(result, retrieval_session=retrieval_session)

    unrecovered_errors = _unrecovered_error_events(result.tool_events, scope)
    recoverable_codes: list[str] = []
    if unrecovered_errors:
        if session is not None and _has_landed_factual_claims(session):
            fatal_errors = [
                event
                for event in unrecovered_errors
                if not _is_recoverable_tool_error(event)
            ]
            if not fatal_errors:
                _, recoverable_codes = _error_code_from_tool_events(unrecovered_errors)
                unrecovered_errors = []
            else:
                unrecovered_errors = fatal_errors
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

    if session is not None:
        explicit_scope = (
            "conversation_context"
            if result.answer_scope == "conversation_context"
            else None
        )
        validated = validate_structured_answer(
            session,
            None,
            model_prose=(result.final_text or "").strip() or None,
            execution_error=False,
            corpus_root=corpus_root,
            answer_scope=explicit_scope,
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
            "support_claim_ledger_text": validated.support_claim_ledger_text,
            "answer_authority": validated.answer_authority,
            "validator_path": validated.validator_path,
        }
        if validated.support_lag_text or validated.support_excerpt_text:
            acceptance["s1_support"] = {
                "lag_disclosure": validated.support_lag_text,
                "admitted_recap_excerpt": validated.support_excerpt_text,
            }
        warnings = list(validated.warnings)
        diagnostic_codes = list(
            dict.fromkeys([*validated.diagnostic_codes, *recoverable_codes])
        )
        for code in recoverable_codes:
            warning = (
                f"Recovered past expand cardinality error ({code}); "
                "answering from landed claims."
            )
            if warning not in warnings:
                warnings.append(warning)
        return (
            legacy_state,
            validated.answer_text,
            warnings,
            diagnostic_codes,
            None,
            acceptance,
        )

    # Fallback path without a retrieval session: prefer matched nodes over anchors.
    completions = [event for event in result.tool_events if event.state == "completion"]
    evidence = [event for event in completions if _is_evidence_bearing(event, scope)]
    final_response = (result.final_text or "").strip()
    if not evidence:
        return (
            "abstained",
            ABSTENTION_ANSWER,
            [],
            ["hermes_insufficient_evidence"],
            None,
            {
                "state": "abstained",
                "reason_codes": ["no_session_no_evidence"],
                "validator_path": "no_session_fallback",
            },
        )
    is_partial = any(_normalized_outcome(event) in PARTIAL_OUTCOMES for event in evidence)
    if is_partial:
        return (
            "partial",
            final_response or ABSTENTION_ANSWER,
            [PARTIAL_COVERAGE_WARNING],
            ["hermes_partial_coverage"],
            None,
            {
                "state": "partial_coverage",
                "reason_codes": ["legacy_partial"],
                "validator_path": "no_session_fallback",
            },
        )
    if not final_response:
        return (
            "abstained",
            ABSTENTION_ANSWER,
            [],
            ["hermes_insufficient_evidence"],
            None,
            {
                "state": "abstained",
                "reason_codes": ["empty_final_response"],
                "validator_path": "no_session_fallback",
            },
        )
    return (
        "grounded",
        final_response,
        [],
        [],
        None,
        {
            "state": "graph_grounded",
            "reason_codes": ["legacy_matched_ids"],
            "validator_path": "no_session_fallback",
        },
    )


def _grounding_block(
    *,
    state: GroundingState,
    scope: _DispatchedScope,
    tool_events: Sequence[AgentRuntimeToolEvent],
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


def _new_trace_builder(
    *,
    agent_thread_id: str | None,
    turn_id: str | None,
    trace_builder: AgentTurnTraceBuilder | None = None,
    descriptor: AgentRuntimeDescriptor | None = None,
) -> AgentTurnTraceBuilder:
    if trace_builder is not None:
        return trace_builder
    identity = descriptor or HERMES_RUNTIME_DESCRIPTOR
    return AgentTurnTraceBuilder(
        agent_thread_id=agent_thread_id,
        turn_id=turn_id,
        runtime=identity.trace_runtime,
        backend=identity.trace_backend,
        mode=identity.trace_mode,
    )


def _runtime_process_isolation(result: AgentRuntimeResult) -> str | None:
    value = result.runtime_metadata.get("process_isolation")
    return str(value) if value else None


def _runtime_worker_pid(result: AgentRuntimeResult) -> int | None:
    value = result.runtime_metadata.get("worker_pid")
    return value if isinstance(value, int) else None


def _runtime_retrieval_session_id(result: AgentRuntimeResult) -> str | None:
    value = result.context_updates.get("retrieval_session_id")
    return str(value) if isinstance(value, str) and value else None


def _agent_trace(
    *,
    state: GroundingState,
    result: AgentRuntimeResult,
    tool_events: Sequence[dict[str, Any]],
    warnings: Sequence[str],
    started_at: str,
    completed_at: str,
    elapsed_ms: int,
    scope: _DispatchedScope | None = None,
    validator_path: str | None = None,
    conversation_history: Sequence[Mapping[str, str]] | None = None,
    pointer_resolution: HermesPointerResolution | None = None,
    worker_pid_changed: bool = False,
    fresh_graph_revision_used: bool = True,
    trace_builder: AgentTurnTraceBuilder | None = None,
    agent_thread_id: str | None = None,
    turn_id: str | None = None,
) -> dict[str, Any]:
    status = {
        "grounded": "ok",
        "partial": "partial",
        "abstained": "abstained",
        "error": "error",
        "conversation_context": "ok",
    }[state]
    raw_events = list(result.tool_events)
    evidence_count = (
        _evidence_event_count(raw_events, scope)
        if scope is not None
        else 0
    )
    history_count = len(conversation_history or [])
    resolution = pointer_resolution or HermesPointerResolution(
        continuity_session_id=None,
        pointer_status="absent",
        pointer_in_request=False,
    )
    builder = _new_trace_builder(
        agent_thread_id=agent_thread_id,
        turn_id=turn_id,
        trace_builder=trace_builder,
    )
    if trace_builder is None:
        builder.started_at = started_at
    for warning in result.telemetry_warnings:
        builder.add_warning(warning)
    extra_warnings = list(warnings)
    if resolution.recovery_message:
        extra_warnings.append(resolution.recovery_message)
    # Terminal clock is the builder after response_projection, not a caller snapshot
    # captured before that span closes.
    _ = completed_at
    _ = elapsed_ms
    return builder.finalize_and_log(
        status=status,
        model_calls=list(result.model_calls),
        extra_warnings=extra_warnings,
        observed_model_call_count=result.observed_model_call_count,
        hermes_fields={
            "hermes_session_id": result.runtime_session_id or None,
            "process_isolation": _runtime_process_isolation(result),
            "tool_events": list(tool_events),
            "answer_scope": result.answer_scope,
            "tool_event_count": len(raw_events),
            "evidence_event_count": evidence_count,
            "final_response_present": bool((result.final_text or "").strip()),
            "validator_path": validator_path,
            "conversation_context": {
                "history_present": history_count > 0,
                "message_count": history_count,
                "pair_count": history_count // 2,
                "payload_shape": "role_content_only",
                "graph_metadata_in_history": False,
                "hermes_session_pointer_in_request": resolution.pointer_in_request,
                "hermes_session_pointer_status": resolution.pointer_status,
                "worker_pid_changed": worker_pid_changed,
                "fresh_graph_revision_used": fresh_graph_revision_used,
            },
        },
    )


def _top_level_status(state: GroundingState) -> str:
    if state in {"grounded", "conversation_context"}:
        return "ok"
    if state in {"partial", "abstained"}:
        return "partial"
    return "error"


def _hermes_session_handle(binding: HermesSessionPointerBinding | None) -> dict[str, Any] | None:
    if binding is None:
        return None
    return {
        "sessionId": binding.pointer_id,
        "runtime": RUNTIME,
        "title": None,
        "createdAt": binding.created_at,
        "updatedAt": binding.updated_at,
    }


def _continuity_campaign_id(packet: Mapping[str, Any]) -> str:
    """Campaign key for Hermes pointer continuity.

    Bound to the outer live packet / Plan thread identity — not the nested
    graph-lens campaign — so switching C2 → C1-only within one thread keeps
    the same opaque pointer.
    """
    campaign_id = str(packet.get("campaign_id") or "").strip()
    if not campaign_id:
        raise HermesGraphQueryRequestError(
            "Live packet is missing campaign_id for Hermes session continuity.",
            code="hermes_session_pointer_rejected",
        )
    return campaign_id


def _resolve_pointer_for_turn(
    store: HermesSessionPointerStore | None,
    *,
    campaign_id: str,
    agent_thread_id: str | None,
    hermes_session_pointer: str | None,
) -> HermesPointerResolution:
    if store is None:
        return HermesPointerResolution(
            continuity_session_id=None,
            pointer_status="absent",
            pointer_in_request=bool(str(hermes_session_pointer or "").strip()),
        )
    try:
        return store.resolve_for_request(
            campaign_id=campaign_id,
            agent_thread_id=agent_thread_id,
            pointer_id=hermes_session_pointer,
        )
    except HermesSessionPointerError as exc:
        raise HermesGraphQueryRequestError(str(exc), code=exc.code) from exc


def _persist_pointer_after_turn(
    store: HermesSessionPointerStore | None,
    *,
    campaign_id: str,
    agent_thread_id: str | None,
    hermes_session_id: str,
    worker_pid: int | None,
    existing_pointer_id: str | None,
) -> HermesSessionPointerBinding | None:
    if store is None or not agent_thread_id:
        return None
    normalized = str(hermes_session_id or "").strip()
    if not normalized:
        return None
    return store.upsert_after_turn(
        campaign_id=campaign_id,
        agent_thread_id=agent_thread_id,
        hermes_session_id=normalized,
        worker_pid=worker_pid,
        existing_pointer_id=existing_pointer_id,
    )


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
    conversation_history: Sequence[Mapping[str, str]] | None = None,
    trace_builder: AgentTurnTraceBuilder | None = None,
) -> dict[str, Any]:
    """Typed product error when the resolved graph is unavailable — no host call."""
    builder = _new_trace_builder(
        agent_thread_id=agent_thread_id,
        turn_id=turn_id,
        trace_builder=trace_builder,
    )
    started = started_at or builder.started_at
    completed = completed_at or _utc_now_z()
    measured = elapsed_ms if elapsed_ms else builder.elapsed_ms()
    builder.add_unavailable_phase(
        "harness_turn",
        attributes={"reason": WORLD_GRAPH_UNAVAILABLE_CODE},
    )
    scope = _scope_from_unavailable_envelope(graph_envelope)
    empty_result = AgentRuntimeResult(
        status="error",
        error_code=WORLD_GRAPH_UNAVAILABLE_CODE,
        error_message=UNAVAILABLE_ANSWER,
        runtime_metadata={"process_isolation": "process_exclusive"},
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
            "backend": builder.backend,
            "runtime": builder.runtime,
            "mode": builder.mode,
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
            elapsed_ms=measured,
            validator_path="no_session_fallback",
            conversation_history=conversation_history,
            trace_builder=builder,
            agent_thread_id=agent_thread_id,
            turn_id=turn_id,
        ),
        "agent_thread_id": agent_thread_id,
        "turn_id": turn_id,
        "hermes_session": None,
        "world_graph_context": dict(graph_envelope),
    }


def build_hermes_graph_product_response(
    *,
    packet: Mapping[str, Any],
    result: AgentRuntimeResult,
    scope: _DispatchedScope,
    agent_thread_id: str | None,
    turn_id: str | None,
    started_at: str,
    completed_at: str,
    elapsed_ms: int,
    world_graph_context: Mapping[str, Any] | None = None,
    retrieval_session: GraphRetrievalSession | None = None,
    corpus_root: Path | None = None,
    conversation_history: Sequence[Mapping[str, str]] | None = None,
    pointer_resolution: HermesPointerResolution | None = None,
    worker_pid_changed: bool = False,
    pointer_binding: HermesSessionPointerBinding | None = None,
    trace_builder: AgentTurnTraceBuilder | None = None,
) -> dict[str, Any]:
    builder = _new_trace_builder(
        agent_thread_id=agent_thread_id,
        turn_id=turn_id,
        trace_builder=trace_builder,
    )
    projection_span = builder.start_phase("response_projection")
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
        grounding_events: Sequence[AgentRuntimeToolEvent] = []
        acceptance = {"state": "execution_error", "reason_codes": ["projection_failed"]}
    else:
        state, answer, warnings, diagnostic_codes, error_code, acceptance = (
            classify_hermes_graph_result(
                result,
                scope=scope,
                projection_ok=True,
                retrieval_session=retrieval_session,
                corpus_root=corpus_root,
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
    if acceptance.get("support_claim_ledger_text"):
        grounding["support_claim_ledger_text"] = acceptance["support_claim_ledger_text"]
    if acceptance.get("answer_authority"):
        grounding["answer_authority"] = acceptance["answer_authority"]
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
            "backend": builder.backend,
            "runtime": builder.runtime,
            "mode": builder.mode,
            "process_isolation": _runtime_process_isolation(result),
        },
        "citations": citations,
        "graph_references": graph_refs,
        "source_citations": source_cites,
        "context_packet": None,
        "warnings": list(warnings),
        "mutations": [],
        "grounding": grounding,
        "agent_trace": None,
        "agent_thread_id": agent_thread_id,
        "turn_id": turn_id,
        "hermes_session": _hermes_session_handle(pointer_binding),
        "retrieval_session_id": _runtime_retrieval_session_id(result),
    }
    if latest_recap_change is not None:
        response["latest_recap_change"] = dict(latest_recap_change)
    s1_support = acceptance.get("s1_support")
    if isinstance(s1_support, Mapping):
        response["s1_support"] = dict(s1_support)
        if latest_recap_change is not None:
            merged = dict(latest_recap_change)
            for key, value in s1_support.items():
                if value is not None:
                    merged[str(key)] = value
            response["latest_recap_change"] = merged
    if world_graph_context is not None:
        response["world_graph_context"] = dict(world_graph_context)
    if forensic_enabled():
        preflight_ids: list[str] = []
        if isinstance(world_graph_context, Mapping):
            matched = world_graph_context.get("matched_node_ids") or []
            if isinstance(matched, list):
                preflight_ids = [str(item) for item in matched if item]
        response["forensic"] = build_forensic_envelope(
            retrieval_session_id=_runtime_retrieval_session_id(result),
            preflight_candidate_ids=preflight_ids,
            agent_seed_ids=list(acceptance.get("accepted_claim_ids") or []),
            tool_events=[_project_tool_event(event) for event in result.tool_events],
            acceptance=acceptance,
        )
    builder.complete_phase(projection_span)
    response["agent_trace"] = _agent_trace(
        state=state,
        result=result,
        tool_events=projected_events,
        warnings=warnings,
        started_at=started_at,
        completed_at=completed_at,
        elapsed_ms=elapsed_ms,
        scope=scope,
        validator_path=str(acceptance.get("validator_path") or "") or None,
        conversation_history=conversation_history,
        pointer_resolution=pointer_resolution,
        worker_pid_changed=worker_pid_changed,
        fresh_graph_revision_used=True,
        trace_builder=builder,
        agent_thread_id=agent_thread_id,
        turn_id=turn_id,
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
    corpus_root: Path | None = None,
    agent_runtime: AgentRuntime | None = None,
    conversation_history: Any | None = None,
    session_base: Path | None = None,
    hermes_session_pointer: str | None = None,
    trace_builder: AgentTurnTraceBuilder | None = None,
) -> dict[str, Any]:
    """Execute one authoritative Hermes graph turn and return a product envelope.

    Crosses ``AgentRuntime.run`` exactly once. Host-owned pre-accept retry remains
    inside the Hermes adapter/host; this product path never retries.

    ``root`` is the World Graph store root. ``corpus_root`` is the Buddy repo
    root used for registry-admitted recap reads; it must not default to the
    graph store root (``out/``), or S1 memory-lag sensemaking cannot open
    ``corpus/...`` paths.
    """
    from apps.live_control_server.config import repo_root as default_repo_root

    builder = _new_trace_builder(
        agent_thread_id=agent_thread_id,
        turn_id=turn_id,
        trace_builder=trace_builder,
        descriptor=descriptor_for_runtime(agent_runtime),
    )
    try:
        with builder.phase("request_validation"):
            normalized_history = normalize_hermes_conversation_history(
                conversation_history
            )

        if str(graph_envelope.get("status") or "") == "unavailable":
            builder.add_unavailable_phase(
                "world_context_resolution",
                attributes={"reason": WORLD_GRAPH_UNAVAILABLE_CODE},
            )
            return build_hermes_graph_unavailable_response(
                packet=packet,
                graph_envelope=graph_envelope,
                agent_thread_id=agent_thread_id,
                turn_id=turn_id,
                started_at=builder.started_at,
                completed_at=_utc_now_z(),
                elapsed_ms=builder.elapsed_ms(),
                conversation_history=normalized_history,
                trace_builder=builder,
            )

        resolved_corpus_root = (corpus_root or default_repo_root()).resolve()
        context_span_id = builder.start_phase("context_assembly")
        try:
            continuity_campaign_id = _continuity_campaign_id(packet)
            pointer_store = (
                HermesSessionPointerStore(session_base)
                if session_base is not None
                else None
            )
            prior_binding = (
                pointer_store.get_for_thread(
                    campaign_id=continuity_campaign_id,
                    agent_thread_id=agent_thread_id,
                )
                if pointer_store is not None and agent_thread_id
                else None
            )
            pointer_resolution = _resolve_pointer_for_turn(
                pointer_store,
                campaign_id=continuity_campaign_id,
                agent_thread_id=agent_thread_id,
                hermes_session_pointer=hermes_session_pointer,
            )
            assembly, scope = _assemble_graph_turn(
                question=text,
                graph_envelope=graph_envelope,
                root=root,
                corpus_root=resolved_corpus_root,
                conversation_history=normalized_history,
                continuity_session_id=pointer_resolution.continuity_session_id,
                thread_id=agent_thread_id,
                turn_id=turn_id,
            )
            invocation = assembly.invocation
            builder.context_summary = dict(assembly.trace_summary)
            if agent_runtime is None:
                from apps.live_control_server.services.hermes_agent_runtime import (
                    default_hermes_agent_runtime,
                )

                runtime = default_hermes_agent_runtime()
            else:
                runtime = agent_runtime
        except Exception:
            builder.complete_phase(context_span_id, status="error")
            raise
        else:
            builder.complete_phase(
                context_span_id,
                attributes=assembly.trace_summary,
            )

        with builder.phase("harness_turn"):
            result = runtime.run(invocation)
        harness_span = next(
            (
                span
                for span in reversed(builder.spans)
                if span.get("name") == "harness_turn"
            ),
            None,
        )
        if result.status == "error" and harness_span is not None:
            harness_span["status"] = "error"

        worker_pid = _runtime_worker_pid(result)
        worker_pid_changed = (
            pointer_store.worker_pid_changed(prior_binding, worker_pid)
            if pointer_store is not None
            else False
        )
        with builder.phase("continuity_persist"):
            if (
                pointer_store is not None
                and agent_thread_id
                and pointer_resolution.pointer_status == "recovered"
            ):
                pointer_store.clear_for_thread(
                    campaign_id=continuity_campaign_id,
                    agent_thread_id=agent_thread_id,
                )
            pointer_binding = _persist_pointer_after_turn(
                pointer_store,
                campaign_id=continuity_campaign_id,
                agent_thread_id=agent_thread_id,
                hermes_session_id=result.runtime_session_id or "",
                worker_pid=worker_pid,
                existing_pointer_id=(
                    prior_binding.pointer_id
                    if prior_binding is not None
                    and pointer_resolution.pointer_status == "accepted"
                    else None
                ),
            )

        return build_hermes_graph_product_response(
                packet=packet,
                result=result,
                scope=scope,
                agent_thread_id=agent_thread_id,
                turn_id=turn_id,
                started_at=builder.started_at,
                completed_at=_utc_now_z(),
                elapsed_ms=builder.elapsed_ms(),
                world_graph_context=graph_envelope,
                corpus_root=resolved_corpus_root,
                conversation_history=normalized_history,
                pointer_resolution=pointer_resolution,
                worker_pid_changed=worker_pid_changed,
                pointer_binding=pointer_binding,
                trace_builder=builder,
            )
    except HermesGraphQueryRequestError:
        if not builder.logged:
            builder.finalize_and_log(status="error")
        raise


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
