from __future__ import annotations

from pathlib import Path
from typing import Any

from graph_memory.projection import RecapGraphProjection, build_recap_graph_projection
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)


def build_plan_union_supergraph_projection(
    *,
    session_id: str,
    store_path: Path | None = None,
) -> RecapGraphProjection:
    """Build a backend-neutral graph projection for a /plan session lens."""

    resolved_store_path = store_path or DEFAULT_FIXTURE_PATH
    store = load_union_supergraph_store(resolved_store_path)
    return build_recap_graph_projection(store, session_id=session_id)


def build_plan_union_supergraph_projection_payload(
    *,
    session_id: str,
    store_path: Path | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe projection payload for future API route integration."""

    projection = build_plan_union_supergraph_projection(
        session_id=session_id,
        store_path=store_path,
    )
    return projection.model_dump(mode="json")
