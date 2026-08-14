"""Model-visible graph interaction + Threat hydration + canvas proposal tools."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from apps.live_control_server.models.threat_query_hydration import (
    ThreatQueryHydrationRequestV1,
)
from apps.live_control_server.services.canvas_block_proposal import (
    PROPOSE_CANVAS_BLOCK_TOOL_NAME,
    execute_propose_canvas_block,
)
from apps.live_control_server.services.threat_query_hydration import (
    ThreatQueryHydrationError,
    query_threats_with_hydration,
)
from graph_memory.interaction.expansion_executor import (
    ExpandGraphRetrievalRequest,
    ReadGraphSourceRequest,
    execute_expand_graph_retrieval,
    execute_read_graph_source,
)

DECLARE_CONVERSATION_CONTEXT_TOOL_NAME = "declare_conversation_context"
QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME = "query_threat_mechanics_hydration"

ORDERED_INTERACTION_TOOL_NAMES: tuple[str, ...] = (
    "expand_graph_retrieval",
    "read_graph_source",
    QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME,
    PROPOSE_CANVAS_BLOCK_TOOL_NAME,
)

ORDERED_MODEL_VISIBLE_TOOL_NAMES: tuple[str, ...] = (
    DECLARE_CONVERSATION_CONTEXT_TOOL_NAME,
    *ORDERED_INTERACTION_TOOL_NAMES,
)

HERMES_GRAPH_INTERACTION_TOOL_NAMES = frozenset(ORDERED_INTERACTION_TOOL_NAMES)
HERMES_ANSWER_SCOPE_TOOL_NAMES = frozenset({DECLARE_CONVERSATION_CONTEXT_TOOL_NAME})

DECLARE_CONVERSATION_CONTEXT_ACK_SCHEMA = "dmb_hermes_answer_scope_v1"


def declare_conversation_context_tool_definition() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": DECLARE_CONVERSATION_CONTEXT_TOOL_NAME,
            "description": (
                "Declare that this turn answers from the visible conversation "
                "history only, not from campaign World Graph facts. Call exactly "
                "once before summarizing when the question is about this chat "
                "itself. Do not call graph retrieval tools in the same turn."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    }


def query_threat_mechanics_hydration_tool_definition() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME,
            "description": (
                "Query published Threats in the exact campaign graph revision for "
                "this turn and hydrate every typed uses_statblock binding from its "
                "exact immutable DungeonMind revision. Server injects world, "
                "campaign, and revisionPin — do not invent them. "
                "Return value carries exact Threat node IDs, binding/resource/"
                "statblock/revision/digest locators when present, relationship "
                "edge IDs for malformed edges, and per-binding hydration status "
                "(available|unavailable|exact_revision_missing|integrity_failure|"
                "not_requested). "
                "Do not claim mechanics are hydrated when status is unavailable, "
                "exact_revision_missing, integrity_failure, or not_requested. "
                "Null binding/statblock/revision/digest means the locator is "
                "absent — never invent those IDs from an edge ID. "
                "Do not choose among multiple bindings unless the user supplies an "
                "exact binding ID. Do not treat evidence scores as identity. "
                "Zero/one/many Threat hits and bindings remain explicit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "queryText": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Caller/Hermes query text for Threat search.",
                    },
                    "focusNodeIds": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 8,
                        "description": "Optional exact context anchor node IDs.",
                    },
                    "relationshipPredicates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 16,
                    },
                    "maxHits": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 64,
                        "default": 16,
                    },
                    "includeMechanics": {
                        "type": "boolean",
                        "default": True,
                    },
                },
                "required": ["queryText"],
                "additionalProperties": False,
            },
        },
    }


def propose_canvas_block_tool_definition() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": PROPOSE_CANVAS_BLOCK_TOOL_NAME,
            "description": (
                "Propose a typed callout block for the open Canvas document "
                "(Plan prep markdown). Server injects documentId, surfaceId, and "
                "expectedContentSha256 — do not invent them. This tool NEVER writes "
                "files; it returns a proposal the GM must Approve in chat. "
                "Use when the GM asks for a GM note, read-aloud, rules, or warning "
                "to add to the open document (for example: features to call out, "
                "metal leaves on the tree). Prefer kind=gm-note for GM-only callouts; "
                "kind=read-aloud only for player-facing boxed text. "
                "op=insert_callout with locator.afterHeading is the default; "
                "op=replace_callout requires locator.oldText. "
                "Body is callout prose only — do not wrap with > [!MARKER]."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": ["insert_callout", "replace_callout"],
                    },
                    "kind": {
                        "type": "string",
                        "enum": ["read-aloud", "gm-note", "rules", "warning"],
                    },
                    "body": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Callout body prose (no > [!…] wrapper).",
                    },
                    "locator": {
                        "type": "object",
                        "properties": {
                            "afterHeading": {
                                "type": "string",
                                "description": "Insert after this heading text.",
                            },
                            "oldText": {
                                "type": "string",
                                "description": "Unique span to replace (replace_callout).",
                            },
                        },
                        "additionalProperties": False,
                    },
                    "provenanceRefs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 16,
                        "description": "Graph/source ids already in this turn's session.",
                    },
                },
                "required": ["op", "kind", "body", "locator"],
                "additionalProperties": False,
            },
        },
    }


def hermes_graph_interaction_tool_definitions() -> list[dict[str, Any]]:
    expand_schema = ExpandGraphRetrievalRequest.model_json_schema(
        by_alias=True,
        mode="validation",
    )
    read_schema = ReadGraphSourceRequest.model_json_schema(
        by_alias=True,
        mode="validation",
    )
    return [
        {
            "type": "function",
            "function": {
                "name": "expand_graph_retrieval",
                "description": (
                    "Expand the current shared GraphRetrievalSession with a bounded "
                    "graph operation (object, neighborhood, search, or support). "
                    "Always pass the retrievalSessionId "
                    "that was provided for this turn. Scope/revision are server-enforced. "
                    "object/support require exactly one node target; neighborhood requires "
                    "1–8 seeds (no silent search fallback); search allows 0–8 seed nodes. "
                    "For relationship or multi-entity questions, prefer neighborhood with "
                    "1–8 seeds. Call object or support separately for each single node. "
                    "Use this instead of rediscovering objects independently. "
                    "Do not open Markdown or corpus files directly on a graph gap."
                ),
                "parameters": expand_schema,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_graph_source",
                "description": (
                    "Read one or more source anchors already admitted in the current "
                    "GraphRetrievalSession, including exact admitted worldbuilding "
                    "evidence spans when the graph provenance names them. Creates a "
                    "source citation only after a successful integrity-checked read. "
                    "Pass retrievalSessionId and anchorIds from the session ledger. "
                    "When the GM asks to describe, talk about, prep, or draft notes on "
                    "a matched object, call this on readable anchors before answering — "
                    "do not stop because some sibling anchors are unreadable. "
                    "Never supply filesystem paths, artifact IDs, or span IDs as "
                    "caller authority."
                ),
                "parameters": read_schema,
            },
        },
        query_threat_mechanics_hydration_tool_definition(),
        propose_canvas_block_tool_definition(),
    ]


def hermes_model_visible_tool_definitions() -> list[dict[str, Any]]:
    return [
        declare_conversation_context_tool_definition(),
        *hermes_graph_interaction_tool_definitions(),
    ]


def execute_declare_conversation_context(
    _arguments: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    del _arguments
    return {
        "schema": DECLARE_CONVERSATION_CONTEXT_ACK_SCHEMA,
        "scope": "conversation_context",
    }


def execute_query_threat_mechanics_hydration(
    arguments: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    world_id = str(arguments.get("worldId") or arguments.get("world_id") or "").strip()
    campaign_id = str(
        arguments.get("campaignId") or arguments.get("campaign_id") or ""
    ).strip()
    revision_pin = str(
        arguments.get("revisionPin") or arguments.get("revision_pin") or ""
    ).strip()
    query_text = str(
        arguments.get("queryText") or arguments.get("query_text") or ""
    ).strip()
    if not world_id or not campaign_id or not revision_pin:
        return {
            "schema": "dmb_threat_query_hydration_error_v1",
            "resultLabel": "threat_query_hydration_unavailable",
            "message": (
                "exact worldId, campaignId, and revisionPin are required "
                "(server-injected from turn scope)"
            ),
            "diagnostics": ["missing_exact_scope"],
        }
    if not query_text:
        return {
            "schema": "dmb_threat_query_hydration_error_v1",
            "resultLabel": "threat_query_hydration_unavailable",
            "message": "queryText is required",
            "diagnostics": ["missing_query_text"],
        }
    focus_raw = arguments.get("focusNodeIds", arguments.get("focus_node_ids", []))
    predicates_raw = arguments.get(
        "relationshipPredicates", arguments.get("relationship_predicates", [])
    )
    max_hits = arguments.get("maxHits", arguments.get("max_hits", 16))
    include_mechanics = arguments.get(
        "includeMechanics", arguments.get("include_mechanics", True)
    )
    request = ThreatQueryHydrationRequestV1(
        schema="dmb_threat_query_hydration_request_v1",
        world_id=world_id,
        campaign_id=campaign_id,
        revision_pin=revision_pin,
        query_text=query_text,
        focus_node_ids=list(focus_raw or []),
        relationship_predicates=list(predicates_raw or []),
        max_hits=int(max_hits),
        include_mechanics=bool(include_mechanics),
    )
    try:
        response = query_threats_with_hydration(request, root=root)
    except ThreatQueryHydrationError as exc:
        return {
            "schema": "dmb_threat_query_hydration_error_v1",
            "resultLabel": exc.result_label,
            "message": str(exc),
            "diagnostics": exc.diagnostics,
        }
    return response.model_dump(mode="json", by_alias=True)


def execute_propose_canvas_block_tool(arguments: Mapping[str, Any]) -> dict[str, Any]:
    return execute_propose_canvas_block(arguments)


def execute_hermes_graph_interaction_tool_json(
    tool_name: str,
    arguments: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> str:
    try:
        if tool_name == "expand_graph_retrieval":
            result = execute_expand_graph_retrieval(arguments, root=root)
        elif tool_name == "read_graph_source":
            result = execute_read_graph_source(arguments, root=root)
        elif tool_name == QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME:
            result = execute_query_threat_mechanics_hydration(arguments, root=root)
        elif tool_name == PROPOSE_CANVAS_BLOCK_TOOL_NAME:
            result = execute_propose_canvas_block_tool(arguments)
        elif tool_name == DECLARE_CONVERSATION_CONTEXT_TOOL_NAME:
            result = execute_declare_conversation_context(arguments)
        else:
            result = {
                "schema": "dmb_world_graph_retrieval_error_v1",
                "code": "unknown_tool",
                "message": f"Unknown interaction tool: {tool_name}",
                "statusCode": 404,
                "diagnostics": [],
            }
        return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    except Exception as exc:
        return json.dumps(
            {
                "schema": "dmb_world_graph_retrieval_error_v1",
                "code": "hermes_graph_interaction_tool_error",
                "message": f"Hermes graph interaction tool failed: {exc}",
                "statusCode": 500,
                "diagnostics": [],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )


__all__ = [
    "DECLARE_CONVERSATION_CONTEXT_ACK_SCHEMA",
    "DECLARE_CONVERSATION_CONTEXT_TOOL_NAME",
    "HERMES_ANSWER_SCOPE_TOOL_NAMES",
    "HERMES_GRAPH_INTERACTION_TOOL_NAMES",
    "ORDERED_INTERACTION_TOOL_NAMES",
    "ORDERED_MODEL_VISIBLE_TOOL_NAMES",
    "PROPOSE_CANVAS_BLOCK_TOOL_NAME",
    "QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME",
    "declare_conversation_context_tool_definition",
    "execute_declare_conversation_context",
    "execute_hermes_graph_interaction_tool_json",
    "execute_propose_canvas_block_tool",
    "execute_query_threat_mechanics_hydration",
    "hermes_graph_interaction_tool_definitions",
    "hermes_model_visible_tool_definitions",
    "propose_canvas_block_tool_definition",
    "query_threat_mechanics_hydration_tool_definition",
]
