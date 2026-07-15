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

ORDERED_INTERACTION_TOOL_NAMES: tuple[str, ...] = (
    "expand_graph_retrieval",
    "read_graph_source",
)

HERMES_GRAPH_INTERACTION_TOOL_NAMES = frozenset(ORDERED_INTERACTION_TOOL_NAMES)


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
                    "graph operation (object, neighborhood, compare, path, timeline, "
                    "support, coverage, or search). Always pass the retrievalSessionId "
                    "that was provided for this turn. Scope/revision are server-enforced. "
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
    "HERMES_GRAPH_INTERACTION_TOOL_NAMES",
    "ORDERED_INTERACTION_TOOL_NAMES",
    "execute_hermes_graph_interaction_tool_json",
    "hermes_graph_interaction_tool_definitions",
]
