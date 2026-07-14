"""Packaged Hermes plugin: graph-only World Graph read tools (PR010B Rung 3).

Registers exactly five tools under toolset ``dungeonbuddy_graph``, deriving each
schema from the Rung 2 catalog and routing every handler to the Rung 2 JSON
adapter. No legacy retrieval path.
"""

from __future__ import annotations

import copy
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from apps.live_control_server.services.hermes_graph_read_tool_adapter import (
    execute_hermes_graph_read_tool_json,
    hermes_graph_read_tool_definitions,
)
from apps.live_control_server.services.hermes_graph_read_tools import (
    HERMES_GRAPH_READ_TOOL_NAMES,
)

TOOLSET_NAME = "dungeonbuddy_graph"

# Optional process-local graph root override for tests / embedded callers.
# Not part of the model-visible tool arguments.
_graph_root_override: ContextVar[Path | None] = ContextVar(
    "hermes_graph_plugin_root",
    default=None,
)


def set_graph_root_override(root: Path | None) -> Any:
    """Set the ContextVar token for an optional World Graph root override."""
    return _graph_root_override.set(root)


def reset_graph_root_override(token: Any) -> None:
    """Reset the ContextVar token from :func:`set_graph_root_override`."""
    _graph_root_override.reset(token)


def _handler_for(tool_name: str):
    def _handler(args: dict, **kwargs: Any) -> str:
        del kwargs
        try:
            payload = args if isinstance(args, dict) else {}
            return execute_hermes_graph_read_tool_json(
                tool_name,
                payload,
                root=_graph_root_override.get(),
            )
        except Exception:
            # Adapter already fail-closes; this is a last line of defense so
            # Hermes never sees a raised exception from a graph tool.
            return (
                '{"schema":"dmb_world_graph_retrieval_error_v1",'
                '"code":"hermes_graph_read_tool_adapter_error",'
                '"message":"Hermes graph-read tool adapter failed unexpectedly.",'
                '"statusCode":500,'
                '"diagnostics":[]}'
            )

    _handler.__name__ = f"handle_{tool_name}"
    _handler.__qualname__ = f"handle_{tool_name}"
    return _handler


def register(ctx: Any) -> None:
    """Register the five PR010A graph-read tools with Hermes."""
    definitions = hermes_graph_read_tool_definitions()
    names = [item["function"]["name"] for item in definitions]
    if set(names) != set(HERMES_GRAPH_READ_TOOL_NAMES) or len(names) != len(
        HERMES_GRAPH_READ_TOOL_NAMES
    ):
        raise RuntimeError(
            "Rung 2 catalog names drifted from HERMES_GRAPH_READ_TOOL_NAMES"
        )

    for item in definitions:
        function_schema = copy.deepcopy(item["function"])
        name = function_schema["name"]
        description = str(function_schema.get("description") or "")
        ctx.register_tool(
            name=name,
            toolset=TOOLSET_NAME,
            schema=function_schema,
            handler=_handler_for(name),
            description=description,
        )


__all__ = [
    "TOOLSET_NAME",
    "register",
    "reset_graph_root_override",
    "set_graph_root_override",
]
