"""Model-visible expand_graph_retrieval + read_graph_source tool catalog."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from graph_memory.interaction.expansion_executor import (
    ExpandGraphRetrievalRequest,
    ReadGraphSourceRequest,
    execute_expand_graph_retrieval,
    execute_read_graph_source,
)

DECLARE_CONVERSATION_CONTEXT_TOOL_NAME = "declare_conversation_context"

ORDERED_INTERACTION_TOOL_NAMES: tuple[str, ...] = (
    "expand_graph_retrieval",
    "read_graph_source",
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
                    "GraphRetrievalSession. Creates a source citation only after a "
                    "successful integrity-checked read. Pass retrievalSessionId and "
                    "anchorIds from the session ledger. Never supply filesystem paths."
                ),
                "parameters": read_schema,
            },
        },
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
    "declare_conversation_context_tool_definition",
    "execute_declare_conversation_context",
    "execute_hermes_graph_interaction_tool_json",
    "hermes_graph_interaction_tool_definitions",
    "hermes_model_visible_tool_definitions",
]
