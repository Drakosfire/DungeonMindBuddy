"""Model-facing Hermes graph-read tool catalog and JSON-string adapter (PR010B Rung 2).

Derives OpenAI/Hermes-compatible function definitions from the same Rung 1 registry
metadata used for execution, and serializes every call through that dispatcher into
an existing PR010A success or error JSON envelope. No LLM, session, plugin, or
legacy retrieval path.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from apps.live_control_server.services.hermes_graph_read_tools import (
    HERMES_GRAPH_READ_TOOL_NAMES,
    HermesGraphReadToolContractError,
    execute_hermes_graph_read_tool,
    hermes_graph_read_tool_request_models,
)
from apps.live_control_server.services.world_graph_retrieval import (
    WorldGraphRetrievalServiceError,
)
from graph_memory.retrieval.models import (
    RETRIEVAL_ERROR_SCHEMA,
    WorldGraphRetrievalErrorResponse,
    WorldGraphRetrievalResult,
    WorldGraphSourceAnchorReadResult,
)

_TOOL_DESCRIPTIONS: Mapping[str, str] = {
    "search_campaign_graph": (
        "Search one revision-pinned World Supergraph campaign for matched graph "
        "objects by natural-language query text and optional seed node IDs. "
        "Scope is limited to the supplied worldId, campaignId, focus, "
        "admissibility, and optional revisionPin. Use this when the durable "
        "object ID is unknown. A graph miss (empty/partial/unavailable) means "
        "the published graph lacks enough admitted material — do not search "
        "Markdown, manifests, corpus indexes, or arbitrary files elsewhere."
    ),
    "get_campaign_object": (
        "Load one campaign graph object by exact durable nodeId from a "
        "revision-pinned World Supergraph projection. Scope is limited to the "
        "supplied worldId, campaignId, focus, admissibility, and optional "
        "revisionPin. Use this when the durable ID is already known. Graph "
        "misses are not invitations to read Markdown or other document stores."
    ),
    "get_object_neighborhood": (
        "Traverse a bounded neighborhood around one or more seedNodeIds on a "
        "revision-pinned World Supergraph campaign projection. Scope is limited "
        "to the supplied worldId, campaignId, focus, admissibility, and optional "
        "revisionPin. Use this to discover connected prep-relevant objects and "
        "relationships already admitted in the graph. Do not consult another "
        "discovery plane when the neighborhood is empty or partial."
    ),
    "get_object_evidence": (
        "Return graph-admitted source anchors and evidence locators for a "
        "specific graph target (node, relationship, or attribute) on a "
        "revision-pinned campaign projection. Scope is limited to the supplied "
        "worldId, campaignId, focus, admissibility, and optional revisionPin. "
        "Evidence is only what the graph admits; absence of anchors is not "
        "permission to open repository Markdown or corpus paths directly."
    ),
    "read_source_anchor": (
        "Read a bounded excerpt for one opaque anchorId previously emitted by "
        "graph retrieval (search, object, neighborhood, or evidence) under the "
        "same revision-pinned World Supergraph scope (worldId, campaignId, "
        "focus, admissibility, optional revisionPin). Accepts only that opaque "
        "anchorId plus common graph context and optional maxChars — never a "
        "filesystem path, corpus selector, or Markdown locator. Use this solely "
        "to inspect graph-admitted evidence. Graph misses or denials do not "
        "authorize fallback document reads."
    ),
}


def _parameters_schema_for_request_model(request_model: type) -> dict[str, Any]:
    schema = request_model.model_json_schema(by_alias=True, mode="validation")
    # OpenAI function parameters are a single object schema. Keep $defs inline
    # on the same object when Pydantic emits them.
    if schema.get("type") != "object":
        raise RuntimeError(
            f"PR010A request model {request_model.__name__} did not emit an object schema"
        )
    return schema


def hermes_graph_read_tool_definitions() -> list[dict[str, Any]]:
    """Return a fresh ordered catalog of the five graph-only tool definitions."""
    registry = hermes_graph_read_tool_request_models()
    names = tuple(registry.keys())
    if set(names) != set(HERMES_GRAPH_READ_TOOL_NAMES) or len(names) != len(
        HERMES_GRAPH_READ_TOOL_NAMES
    ):
        raise RuntimeError("Rung 1 registry names drifted from HERMES_GRAPH_READ_TOOL_NAMES")

    definitions: list[dict[str, Any]] = []
    for name in names:
        request_model = registry[name]
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": _TOOL_DESCRIPTIONS[name],
                    "parameters": _parameters_schema_for_request_model(request_model),
                },
            }
        )
    # Fresh copies so caller mutation cannot alter later catalog reads.
    return copy.deepcopy(definitions)


def _serialize_model(
    model: WorldGraphRetrievalResult
    | WorldGraphSourceAnchorReadResult
    | WorldGraphRetrievalErrorResponse,
) -> str:
    return model.model_dump_json(by_alias=True)


def _contract_error_json(
    *,
    code: str,
    message: str,
    status_code: int,
) -> str:
    return _serialize_model(
        WorldGraphRetrievalErrorResponse(
            schema_=RETRIEVAL_ERROR_SCHEMA,
            code=code,
            message=message,
            status_code=status_code,
        )
    )


def _unexpected_adapter_error_json() -> str:
    return _contract_error_json(
        code="hermes_graph_read_tool_adapter_error",
        message="Hermes graph-read tool adapter failed unexpectedly.",
        status_code=500,
    )


def execute_hermes_graph_read_tool_json(
    tool_name: str,
    arguments: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> str:
    """Execute one Rung 1 graph-read tool and return PR010A success/error JSON."""
    try:
        result = execute_hermes_graph_read_tool(tool_name, arguments, root=root)
        return _serialize_model(result)
    except HermesGraphReadToolContractError as exc:
        if exc.code == "unknown_tool":
            return _contract_error_json(
                code="unknown_tool",
                message=str(exc),
                status_code=404,
            )
        if exc.code == "invalid_arguments":
            return _contract_error_json(
                code="invalid_arguments",
                message=str(exc),
                status_code=400,
            )
        return _unexpected_adapter_error_json()
    except WorldGraphRetrievalServiceError as exc:
        return _serialize_model(exc.response())
    except Exception:
        return _unexpected_adapter_error_json()


__all__ = [
    "execute_hermes_graph_read_tool_json",
    "hermes_graph_read_tool_definitions",
]
