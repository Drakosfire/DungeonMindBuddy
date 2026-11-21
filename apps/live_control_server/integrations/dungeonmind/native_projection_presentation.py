"""Pure presentation ranking shared by native and historical projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from graph_memory.projection.world_projection import (
    WorldGraphProjectionAdjacencyCandidate,
    WorldGraphProjectionSuggestedExpansion,
)


def _expansion_views(
    adjacency: Sequence[WorldGraphProjectionAdjacencyCandidate],
    *,
    degree_by_node: Mapping[str, int],
) -> list[WorldGraphProjectionSuggestedExpansion]:
    """Kernel parity: sort by (-focus, -evidence, -degree, label); rank 1..N."""

    def sort_key(candidate: WorldGraphProjectionAdjacencyCandidate) -> tuple[int, int, int, str]:
        return (
            -1 if candidate.anchored_to_focus_session else 0,
            -len(candidate.evidence_ref_ids),
            -degree_by_node.get(candidate.node_id, 0),
            candidate.label.lower(),
        )

    expansions: list[WorldGraphProjectionSuggestedExpansion] = []
    for index, candidate in enumerate(sorted(adjacency, key=sort_key), start=1):
        degree = degree_by_node.get(candidate.node_id, 0)
        if candidate.anchored_to_focus_session:
            reason = "current session"
        elif len(candidate.evidence_ref_ids) >= 2:
            reason = "more evidence"
        elif degree >= 3:
            reason = "connected hub"
        else:
            reason = "connected thread"
        expansions.append(
            WorldGraphProjectionSuggestedExpansion(
                **candidate.model_dump(),
                rank=index,
                rank_reason=reason,
            )
        )
    return expansions
