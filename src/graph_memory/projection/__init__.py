"""World Graph projection contracts.

Recap/UnionSupergraph helpers live in ``graph_memory.projection.recap_projection``
and are not imported here so mounted product can load request/node contracts
without the retired UnionSupergraph package (CUTOVER D.3A).
"""

from __future__ import annotations

from graph_memory.projection.focus_overlay import (
    GraphFocusOverlay,
    GraphProjectionEvidenceBadge,
)
from graph_memory.projection.node_view import (
    GraphProjectionAdjacencyCandidate,
    GraphProjectionNodeView,
    GraphProjectionSuggestedExpansion,
    GraphProjectionTextHighlightSpan,
)
from graph_memory.projection.markdown_mentions import (
    AMBIGUOUS_MENTION_DIAGNOSTIC,
    MarkdownMention,
    MarkdownMentionDiagnostic,
    MentionBinding,
    project_markdown_mentions,
    splice_node_link_spans,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionErrorResponse,
    WorldGraphProjectionRequest,
    WorldGraphQueryContext,
    WorldGraphRelationshipDirection,
    normalize_world_graph_relationship_direction,
)
from graph_memory.projection.world_recap_projection import (
    WorldGraphRecapProjection,
    project_world_markdown_mentions,
)
from graph_memory.projection.recap_projection_contracts import (
    RecapGraphProjection,
    RecapProjectionMention,
    RecapProjectionSourceSpan,
)

__all__ = [
    "AMBIGUOUS_MENTION_DIAGNOSTIC",
    "GraphFocusOverlay",
    "GraphProjectionEvidenceBadge",
    "GraphProjectionAdjacencyCandidate",
    "GraphProjectionSuggestedExpansion",
    "GraphProjectionNodeView",
    "GraphProjectionTextHighlightSpan",
    "MarkdownMention",
    "MarkdownMentionDiagnostic",
    "MentionBinding",
    "WorldGraphRecapProjection",
    "RecapGraphProjection",
    "RecapProjectionMention",
    "RecapProjectionSourceSpan",
    "WorldGraphRelationshipDirection",
    "normalize_world_graph_relationship_direction",
    "project_markdown_mentions",
    "project_world_markdown_mentions",
    "splice_node_link_spans",
    "WorldGraphProjection",
    "WorldGraphProjectionErrorResponse",
    "WorldGraphProjectionRequest",
    "WorldGraphQueryContext",
]
