"""PR008B: Agent Interaction World Graph query-context adapter.

Resolves one revision-pinned PR007A projection into a bounded Agent envelope.
Graph context is structured campaign memory/navigation — never citation authority.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjection,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
    WorldGraphQueryContext,
)

AGENT_REQUEST_SCHEMA = "dmb_agent_world_graph_query_context_request_v1"
AGENT_RESPONSE_SCHEMA = "dmb_agent_world_graph_query_context_v1"

AgentGraphStatus = Literal["ready", "empty", "unavailable"]
FocusKind = Literal["none", "session"]

WARNING_WORLD_GRAPH_UNAVAILABLE = "world_graph_unavailable"
WARNING_GRAPH_CONTEXT_EMPTY = "graph_context_empty"
WARNING_GRAPH_PROJECTION_TRUNCATED = "graph_projection_truncated"
WARNING_GRAPH_QUERY_TRUNCATED_NODES = "graph_query_truncated_nodes"
WARNING_GRAPH_QUERY_TRUNCATED_RELATIONSHIPS = "graph_query_truncated_relationships"
WARNING_GRAPH_QUERY_TRUNCATED_ATTRIBUTES = "graph_query_truncated_attributes"
WARNING_GRAPH_CONTEXT_NOT_CONFIGURED = "graph_context_not_configured"
WARNING_GRAPH_CONTEXT_DETAIL_NOT_PERSISTED = "graph_context_detail_not_persisted"

_DIAGNOSTIC_WARNING_CODE_MAP = {
    "search_truncated_nodes": WARNING_GRAPH_QUERY_TRUNCATED_NODES,
    "search_truncated_relationships": WARNING_GRAPH_QUERY_TRUNCATED_RELATIONSHIPS,
    "search_truncated_attributes": WARNING_GRAPH_QUERY_TRUNCATED_ATTRIBUTES,
}

TRUST_BOUNDARY = {
    "graph_role": "structured_campaign_memory_and_navigation",
    "citation_authority": "corpus_source_evidence",
    "graph_citations_permitted": False,
}

FATAL_PROJECTION_CODES = frozenset(
    {
        "revision_not_found",
        "invalid_request",
        "campaign_scope_mismatch",
        "unsupported_admissibility",
        "projection_integrity_error",
        "projection_internal_error",
    }
)


class AgentWorldGraphQueryContextError(ValueError):
    """Fatal graph preflight error — do not invoke an answer backend."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        diagnostics: list[WorldGraphProjectionDiagnostic] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = list(diagnostics or [])

    def response_body(self) -> dict[str, Any]:
        return {
            "schema": "dmb_world_graph_projection_error_v1",
            "code": self.code,
            "message": str(self),
            "statusCode": self.status_code,
            "diagnostics": [
                {
                    "code": item.code,
                    "message": item.message,
                    "severity": item.severity,
                }
                for item in self.diagnostics
            ],
        }


class AgentWorldGraphFocus(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    kind: FocusKind = "none"
    session_id: str | None = None
    campaign_id: str | None = None

    @model_validator(mode="after")
    def _validate_session_id(self) -> AgentWorldGraphFocus:
        if self.kind == "session" and not self.session_id:
            raise ValueError("session_id is required when focus.kind is session")
        if self.kind == "none":
            if self.session_id is not None:
                raise ValueError("session_id must be null when focus.kind is none")
            if self.campaign_id is not None:
                raise ValueError("campaign_id must be null when focus.kind is none")
        return self


class AgentWorldGraphQueryContextRequest(BaseModel):
    """Nested Agent Interaction graph request (snake_case live-query wire)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_agent_world_graph_query_context_request_v1"] = Field(
        alias="schema",
        default=AGENT_REQUEST_SCHEMA,
    )
    world_id: str
    campaign_id: str
    focus: AgentWorldGraphFocus = Field(default_factory=AgentWorldGraphFocus)
    admissibility: Literal["gm"] = "gm"
    revision_pin: str | None = None
    # campaign: narrative campaign only. world: all campaigns in the same world.
    scope_mode: Literal["campaign", "world"] = "campaign"

    @field_validator("world_id", "campaign_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must be a non-empty string")
        return cleaned


def _diagnostic_dicts(
    diagnostics: list[WorldGraphProjectionDiagnostic],
) -> list[dict[str, Any]]:
    return [
        {"code": item.code, "message": item.message, "severity": item.severity}
        for item in diagnostics
    ]


def _warning_codes_from_diagnostics(
    diagnostics: list[WorldGraphProjectionDiagnostic],
    *,
    projection_truncated: bool,
    status: AgentGraphStatus,
) -> list[str]:
    codes: list[str] = []
    seen: set[str] = set()

    def _add(code: str) -> None:
        if code not in seen:
            seen.add(code)
            codes.append(code)

    if status == "unavailable":
        _add(WARNING_WORLD_GRAPH_UNAVAILABLE)
    if status == "empty":
        _add(WARNING_GRAPH_CONTEXT_EMPTY)
    if projection_truncated:
        _add(WARNING_GRAPH_PROJECTION_TRUNCATED)
    for item in diagnostics:
        mapped = _DIAGNOSTIC_WARNING_CODE_MAP.get(item.code)
        if mapped:
            _add(mapped)
    return codes


def _bounded_nodes(query_context: WorldGraphQueryContext) -> list[dict[str, Any]]:
    return [
        {
            "node_id": node.node_id,
            "label": node.label,
            "kind": node.kind,
            "role": node.role,
            "summary": node.summary,
            "anchored_to_focus_session": node.anchored_to_focus_session,
            "campaign_scope": node.campaign_scope,
        }
        for node in query_context.nodes
    ]


def _bounded_relationships(query_context: WorldGraphQueryContext) -> list[dict[str, Any]]:
    return [
        {
            "edge_id": edge.edge_id,
            "source_node_id": edge.source_node_id,
            "target_node_id": edge.target_node_id,
            "predicate": edge.predicate,
            "label": edge.label,
            "direction": edge.direction,
            "session_ids": list(edge.session_ids),
            "campaign_scope": edge.campaign_scope,
        }
        for edge in query_context.relationships
    ]


def _bounded_attributes(query_context: WorldGraphQueryContext) -> list[dict[str, Any]]:
    return [
        {
            "assertion_id": attribute.assertion_id,
            "subject_node_id": attribute.subject_node_id,
            "predicate": attribute.predicate,
            "label": attribute.label,
            "text_value": attribute.text_value,
            "campaign_scope": attribute.campaign_scope,
        }
        for attribute in query_context.attributes
    ]


def _unavailable_envelope(
    request: AgentWorldGraphQueryContextRequest,
    *,
    query_text: str,
    diagnostics: list[WorldGraphProjectionDiagnostic],
) -> dict[str, Any]:
    warning_codes = _warning_codes_from_diagnostics(
        diagnostics,
        projection_truncated=False,
        status="unavailable",
    )
    return {
        "schema": AGENT_RESPONSE_SCHEMA,
        "status": "unavailable",
        "world_id": request.world_id,
        "campaign_id": request.campaign_id,
        "revision_id": None,
        "head_revision_id": None,
        "is_head": None,
        "focus": {
            "kind": request.focus.kind,
            "session_id": request.focus.session_id,
            "campaign_id": request.focus.campaign_id,
        },
        "admissibility": request.admissibility,
        "scope_mode": request.scope_mode,
        "query_text": query_text,
        "matched_node_ids": [],
        "nodes": [],
        "relationships": [],
        "attributes": [],
        "projection_truncated": False,
        "diagnostics": _diagnostic_dicts(diagnostics),
        "warning_codes": warning_codes,
        "trust_boundary": dict(TRUST_BOUNDARY),
    }


def adapt_projection_to_agent_envelope(
    projection: WorldGraphProjection,
    *,
    query_text: str,
) -> dict[str, Any]:
    """Convert a successful PR007A projection into the Agent query-context envelope."""
    query_context = projection.query_context
    matched = list(query_context.matched_node_ids) if query_context is not None else []
    status: AgentGraphStatus = "ready" if matched else "empty"
    diagnostics = list(projection.diagnostics)
    if query_context is not None:
        diagnostics = diagnostics + list(query_context.diagnostics)

    nodes = _bounded_nodes(query_context) if query_context is not None else []
    relationships = (
        _bounded_relationships(query_context) if query_context is not None else []
    )
    attributes = _bounded_attributes(query_context) if query_context is not None else []
    truncated = bool(projection.summary.projection_truncated)
    warning_codes = _warning_codes_from_diagnostics(
        diagnostics,
        projection_truncated=truncated,
        status=status,
    )

    return {
        "schema": AGENT_RESPONSE_SCHEMA,
        "status": status,
        "world_id": projection.snapshot.world_id,
        "campaign_id": projection.snapshot.campaign_id,
        "revision_id": projection.snapshot.revision_id,
        "head_revision_id": projection.snapshot.head_revision_id,
        "is_head": projection.snapshot.is_head,
        "focus": {
            "kind": projection.snapshot.focus.kind,
            "session_id": projection.snapshot.focus.session_id,
            "campaign_id": projection.snapshot.focus.campaign_id,
        },
        "admissibility": projection.snapshot.admissibility,
        "scope_mode": getattr(projection.snapshot, "scope_mode", "campaign") or "campaign",
        "query_text": query_text,
        "matched_node_ids": matched,
        "nodes": nodes,
        "relationships": relationships,
        "attributes": attributes,
        "projection_truncated": truncated,
        "diagnostics": _diagnostic_dicts(diagnostics),
        "warning_codes": warning_codes,
        "trust_boundary": dict(TRUST_BOUNDARY),
    }


def build_projection_request(
    nested: AgentWorldGraphQueryContextRequest,
    *,
    query_text: str,
) -> WorldGraphProjectionRequest:
    focus_campaign = nested.focus.campaign_id or nested.campaign_id
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=nested.world_id,
        campaign_id=nested.campaign_id,
        focus=WorldGraphProjectionFocus(
            kind=nested.focus.kind,
            session_id=nested.focus.session_id,
            campaign_id=focus_campaign if nested.focus.kind == "session" else None,
        ),
        admissibility=nested.admissibility,
        revision_pin=nested.revision_pin,
        query_text=query_text,
        scope_mode=nested.scope_mode,
    )


def resolve_agent_world_graph_query_context(
    nested: AgentWorldGraphQueryContextRequest,
    *,
    outer_text: str,
    outer_campaign_id: str,
    root: Path | None = None,
    project_fn: Any | None = None,
) -> dict[str, Any]:
    """Resolve exactly one PR007A projection into the Agent envelope.

    ``world_graph_unavailable`` becomes nonfatal ``status: unavailable``.
    All other projection service errors remain fatal.

    When ``scope_mode=world``, nested ``campaign_id`` is the narrative/temporal
    anchor and may differ from the outer live-query campaign (same world).
    When ``scope_mode=campaign``, nested campaign must equal the outer campaign.
    """
    if nested.scope_mode == "campaign" and nested.campaign_id != outer_campaign_id:
        raise AgentWorldGraphQueryContextError(
            "world_graph_context.campaign_id must equal the outer live-query campaign_id",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="invalid_request",
                    message=(
                        "world_graph_context.campaign_id must equal the outer "
                        "live-query campaign_id when scope_mode is campaign"
                    ),
                    severity="error",
                )
            ],
        )

    query_text = outer_text
    projection_request = build_projection_request(nested, query_text=query_text)
    projector = project_fn or project_world_graph
    try:
        projection = projector(projection_request, root=root)
    except WorldGraphProjectionServiceError as exc:
        if exc.code == WARNING_WORLD_GRAPH_UNAVAILABLE:
            return _unavailable_envelope(
                nested,
                query_text=query_text,
                diagnostics=list(exc.diagnostics)
                or [
                    WorldGraphProjectionDiagnostic(
                        code=WARNING_WORLD_GRAPH_UNAVAILABLE,
                        message=str(exc),
                        severity="warning",
                    )
                ],
            )
        raise AgentWorldGraphQueryContextError(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
            diagnostics=list(exc.diagnostics),
        ) from None
    except AgentWorldGraphQueryContextError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise AgentWorldGraphQueryContextError(
            "World graph projection failed unexpectedly.",
            code="projection_internal_error",
            status_code=500,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="projection_internal_error",
                    message="World graph projection failed unexpectedly.",
                    severity="error",
                )
            ],
        ) from exc

    return adapt_projection_to_agent_envelope(projection, query_text=query_text)


def render_world_graph_prompt_block(envelope: dict[str, Any] | None) -> str:
    """Deterministic bounded graph prompt block for live and Hermes answer paths."""
    if not envelope:
        return (
            "WORLD GRAPH CONTEXT:\n"
            "(not configured)\n"
            f"Warning: {WARNING_GRAPH_CONTEXT_NOT_CONFIGURED}"
        )

    status = str(envelope.get("status") or "unavailable")
    lines: list[str] = [
        "WORLD GRAPH CONTEXT:",
        "Rules:",
        "- Graph context selects relevant campaign objects and relationships.",
        "- Graph summaries and attributes are not source quotations.",
        "- Factual claims still require admitted corpus/source evidence.",
        "- Graph IDs may be named as navigation context.",
        "- Graph material must not be cited with corpus evidence IDs.",
        "- If corpus evidence and graph context disagree, do not silently resolve "
        "the disagreement; preserve corpus evidence as citation authority and "
        "expose the graph discrepancy as context or uncertainty.",
        f"status: {status}",
        f"world_id: {envelope.get('world_id')}",
        f"campaign_id: {envelope.get('campaign_id')}",
        f"revision_id: {envelope.get('revision_id')}",
        f"head_revision_id: {envelope.get('head_revision_id')}",
        f"is_head: {envelope.get('is_head')}",
        (
            "focus: "
            f"{(envelope.get('focus') or {}).get('kind')}/"
            f"{(envelope.get('focus') or {}).get('session_id')}"
        ),
        f"admissibility: {envelope.get('admissibility')}",
        f"projection_truncated: {bool(envelope.get('projection_truncated'))}",
    ]

    if status == "unavailable":
        lines.append("Graph claims are forbidden for this turn.")
        for code in list(envelope.get("warning_codes") or []):
            lines.append(f"warning: {code}")
        return "\n".join(lines)

    matched = list(envelope.get("matched_node_ids") or [])
    lines.append("matched_node_ids: " + (", ".join(matched) if matched else "(none)"))

    nodes = list(envelope.get("nodes") or [])
    if nodes:
        lines.append("nodes:")
        for node in nodes:
            lines.append(
                "- "
                f"{node.get('node_id')} | {node.get('label')} | kind={node.get('kind')} | "
                f"role={node.get('role')} | focus_anchor={node.get('anchored_to_focus_session')} | "
                f"summary={node.get('summary') or ''}"
            )
    else:
        lines.append("nodes: (none)")

    relationships = list(envelope.get("relationships") or [])
    if relationships:
        lines.append("relationships:")
        for edge in relationships:
            lines.append(
                "- "
                f"{edge.get('edge_id')} | {edge.get('predicate')} | "
                f"{edge.get('source_node_id')} -> {edge.get('target_node_id')} | "
                f"direction={edge.get('direction')} | label={edge.get('label')}"
            )
    else:
        lines.append("relationships: (none)")

    attributes = list(envelope.get("attributes") or [])
    if attributes:
        lines.append("attributes:")
        for attribute in attributes:
            lines.append(
                "- "
                f"{attribute.get('assertion_id')} | subject={attribute.get('subject_node_id')} | "
                f"predicate={attribute.get('predicate')} | label={attribute.get('label')} | "
                f"text={attribute.get('text_value') or ''}"
            )
    else:
        lines.append("attributes: (none)")

    for code in list(envelope.get("warning_codes") or []):
        lines.append(f"warning: {code}")

    return "\n".join(lines)


def compact_persisted_summary(envelope: dict[str, Any] | None) -> dict[str, Any] | None:
    """Pointer-only summary safe for thread persistence (mirrors UI contract)."""
    if not envelope:
        return None
    status = envelope.get("status")
    if status not in {"ready", "empty", "unavailable"}:
        return None
    focus = envelope.get("focus") if isinstance(envelope.get("focus"), dict) else {}
    return {
        "schema": "dmb_agent_world_graph_context_summary_v1",
        "status": status,
        "world_id": envelope.get("world_id"),
        "campaign_id": envelope.get("campaign_id"),
        "revision_id": envelope.get("revision_id"),
        "is_head": envelope.get("is_head"),
        "focus": {
            "kind": focus.get("kind") or "none",
            "session_id": focus.get("session_id"),
            "campaign_id": focus.get("campaign_id"),
        },
        "admissibility": envelope.get("admissibility") or "gm",
        "scope_mode": envelope.get("scope_mode") or "campaign",
        "matched_node_ids": list(envelope.get("matched_node_ids") or []),
        "projection_truncated": bool(envelope.get("projection_truncated")),
        "warning_codes": list(envelope.get("warning_codes") or [])
        + (
            [WARNING_GRAPH_CONTEXT_DETAIL_NOT_PERSISTED]
            if WARNING_GRAPH_CONTEXT_DETAIL_NOT_PERSISTED
            not in list(envelope.get("warning_codes") or [])
            else []
        ),
    }


__all__ = [
    "AGENT_REQUEST_SCHEMA",
    "AGENT_RESPONSE_SCHEMA",
    "AgentWorldGraphFocus",
    "AgentWorldGraphQueryContextError",
    "AgentWorldGraphQueryContextRequest",
    "FATAL_PROJECTION_CODES",
    "TRUST_BOUNDARY",
    "adapt_projection_to_agent_envelope",
    "build_projection_request",
    "compact_persisted_summary",
    "render_world_graph_prompt_block",
    "resolve_agent_world_graph_query_context",
]
