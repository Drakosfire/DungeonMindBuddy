"""Strict Hermes graph-read tool dispatcher over PR010A service operations.

Internal in-process boundary only: exact tool name → existing request model →
existing live-control World Graph retrieval service. No LLM, session, HTTP,
plugin, or legacy retrieval path.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from pydantic import ValidationError

from apps.live_control_server.services import world_graph_retrieval as world_graph_retrieval_service
from graph_memory.retrieval.models import (
    WorldGraphEvidenceRequest,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalResult,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
    WorldGraphSourceAnchorReadResult,
)

HermesGraphReadRequestModel = type[
    WorldGraphSearchRequest
    | WorldGraphObjectRequest
    | WorldGraphNeighborhoodRequest
    | WorldGraphEvidenceRequest
    | WorldGraphSourceAnchorReadRequest
]

HermesGraphReadToolContractCode = Literal["unknown_tool", "invalid_arguments"]

HERMES_GRAPH_READ_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "search_campaign_graph",
        "get_campaign_object",
        "get_object_neighborhood",
        "get_object_evidence",
        "read_source_anchor",
    }
)


class HermesGraphReadToolContractError(ValueError):
    """Internal contract failure before PR010A service invocation."""

    def __init__(
        self,
        message: str,
        *,
        code: HermesGraphReadToolContractCode,
    ) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class _HermesGraphReadToolEntry:
    request_model: HermesGraphReadRequestModel
    service_name: str


_REGISTRY: dict[str, _HermesGraphReadToolEntry] = {
    "search_campaign_graph": _HermesGraphReadToolEntry(
        WorldGraphSearchRequest,
        "search_campaign_graph",
    ),
    "get_campaign_object": _HermesGraphReadToolEntry(
        WorldGraphObjectRequest,
        "get_campaign_object",
    ),
    "get_object_neighborhood": _HermesGraphReadToolEntry(
        WorldGraphNeighborhoodRequest,
        "get_object_neighborhood",
    ),
    "get_object_evidence": _HermesGraphReadToolEntry(
        WorldGraphEvidenceRequest,
        "get_object_evidence",
    ),
    "read_source_anchor": _HermesGraphReadToolEntry(
        WorldGraphSourceAnchorReadRequest,
        "read_source_anchor",
    ),
}


def hermes_graph_read_tool_request_models() -> Mapping[str, HermesGraphReadRequestModel]:
    """Read-only exact tool name → PR010A request model from the execution registry.

    Insertion order is the deterministic catalog order. Callers must not mutate
    the returned mapping; it is a ``MappingProxyType`` over registry metadata.
    """
    return MappingProxyType(
        {name: entry.request_model for name, entry in _REGISTRY.items()}
    )


def execute_hermes_graph_read_tool(
    tool_name: str,
    arguments: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult | WorldGraphSourceAnchorReadResult:
    """Validate arguments and dispatch exactly one PR010A graph-read operation."""
    entry = _REGISTRY.get(tool_name)
    if entry is None:
        raise HermesGraphReadToolContractError(
            f"Unknown Hermes graph-read tool: {tool_name!r}",
            code="unknown_tool",
        )
    if not isinstance(arguments, Mapping):
        raise HermesGraphReadToolContractError(
            "Hermes graph-read tool arguments must be a mapping",
            code="invalid_arguments",
        )
    try:
        # Materialize the mapping for Pydantic without dropping keys.
        request = entry.request_model.model_validate(dict(arguments))
    except ValidationError as exc:
        raise HermesGraphReadToolContractError(
            f"Invalid arguments for Hermes graph-read tool {tool_name!r}",
            code="invalid_arguments",
        ) from exc

    service_fn = getattr(world_graph_retrieval_service, entry.service_name)
    return service_fn(request, root=root)


__all__ = [
    "HERMES_GRAPH_READ_TOOL_NAMES",
    "HermesGraphReadRequestModel",
    "HermesGraphReadToolContractError",
    "execute_hermes_graph_read_tool",
    "hermes_graph_read_tool_request_models",
]
