"""World Graph → focus-session recap projection contracts (PR380A / PR #412).

Pure models and deterministic mention helpers. Nested node views reuse the
generic ``WorldGraphProjectionNodeView`` directly — no parallel class tree and
no field-by-field adapters. No corpus I/O, no registry enrichment, no
world-scope widening, no synthetic graph facts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from graph_memory.projection.markdown_mentions import (
    AMBIGUOUS_MENTION_DIAGNOSTIC,
    MentionBinding,
    project_markdown_mentions,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionTrustBoundary,
    _ProjectionModel,
)

RECAP_PROJECTION_RESPONSE_SCHEMA = "dmb_world_graph_recap_projection_v1"


class WorldGraphRecapFocusOverlay(_ProjectionModel):
    focus_session_id: str | None = None
    focused_evidence_ref_ids: list[str] = Field(default_factory=list)
    focused_edge_ids: list[str] = Field(default_factory=list)
    focused_node_ids: list[str] = Field(default_factory=list)


class WorldGraphRecapMention(_ProjectionModel):
    mention_id: str
    node_id: str
    label: str
    start_offset: int | None = None
    end_offset: int | None = None
    # v1 mentions are navigation-only; never copy graph evidence authority.
    evidence_ref_ids: list[str] = Field(default_factory=list)


class WorldGraphRecapSourceSpan(_ProjectionModel):
    """Placeholder span shape; v1 always returns an empty list."""

    span_id: str
    source_artifact_id: str | None = None
    text_excerpt: str | None = None


class WorldGraphRecapProjection(_ProjectionModel):
    schema_: Literal["dmb_world_graph_recap_projection_v1"] = Field(
        alias="schema",
        default=RECAP_PROJECTION_RESPONSE_SCHEMA,
    )
    campaign_id: str
    session_id: str
    graph_id: str
    snapshot: WorldGraphProjectionSnapshot
    markdown: str
    focus: WorldGraphRecapFocusOverlay
    node_views: dict[str, WorldGraphProjectionNodeView] = Field(default_factory=dict)
    mentions: list[WorldGraphRecapMention] = Field(default_factory=list)
    source_spans: list[WorldGraphRecapSourceSpan] = Field(default_factory=list)
    diagnostics: list[WorldGraphProjectionDiagnostic] = Field(default_factory=list)
    trust_boundary: WorldGraphProjectionTrustBoundary


def focus_overlay_from_world(
    projection: WorldGraphProjection,
    *,
    session_id: str,
) -> WorldGraphRecapFocusOverlay:
    focused_evidence = sorted(
        evidence.evidence_ref_id
        for evidence in projection.evidence
        if evidence.session_id == session_id
    )
    focused_edges = sorted(
        rel.edge_id
        for rel in projection.relationships
        if session_id in rel.session_ids
    )
    focused_nodes = sorted(
        node.node_id for node in projection.nodes if node.anchored_to_focus_session
    )
    return WorldGraphRecapFocusOverlay(
        focus_session_id=session_id,
        focused_evidence_ref_ids=focused_evidence,
        focused_edge_ids=focused_edges,
        focused_node_ids=focused_nodes,
    )


def recap_projection_trust_boundary() -> WorldGraphProjectionTrustBoundary:
    return WorldGraphProjectionTrustBoundary(
        can_trust=[
            "snapshot identifies the exact graph read",
            "node_views and graph mention targets come from that snapshot",
            "markdown body comes from the requested canonical normalized recap",
            "graph_id equals snapshot.revision_id",
        ],
        cannot_trust=[
            "mention spans are evidence bindings",
            "source highlighting is available",
            "absent nodes were searched in other campaigns or world scope",
            "label/alias coverage is semantically complete",
            "recap prose has been promoted merely because it is displayed beside graph nodes",
        ],
    )


def project_world_markdown_mentions(
    markdown: str,
    nodes: list[WorldGraphProjectionNodeView],
) -> tuple[str, list[WorldGraphRecapMention], list[WorldGraphProjectionDiagnostic]]:
    """Splice unique label/alias surfaces into ``dmb-node:`` links.

    Thin recap adapter over :func:`project_markdown_mentions`. Binding order is
    the contract: surfaces are emitted in node-iteration order, label before
    aliases, with duplicates preserved, because the neutral linker quotes the
    first matching surface (original casing) in its ambiguity diagnostic.
    """
    bindings = [
        MentionBinding(surface=raw or "", node_id=node.node_id)
        for node in nodes
        for raw in (node.label, *node.aliases)
    ]
    projected, mentions, diagnostics = project_markdown_mentions(markdown, bindings)
    return (
        projected,
        [
            WorldGraphRecapMention(
                mention_id=mention.mention_id,
                node_id=mention.node_id,
                label=mention.label,
                start_offset=mention.start_offset,
                end_offset=mention.end_offset,
                evidence_ref_ids=[],
            )
            for mention in mentions
        ],
        [
            WorldGraphProjectionDiagnostic(
                code=diagnostic.code,
                message=diagnostic.message,
                severity=diagnostic.severity,
            )
            for diagnostic in diagnostics
        ],
    )


__all__ = [
    "AMBIGUOUS_MENTION_DIAGNOSTIC",
    "RECAP_PROJECTION_RESPONSE_SCHEMA",
    "WorldGraphRecapFocusOverlay",
    "WorldGraphRecapMention",
    "WorldGraphRecapProjection",
    "WorldGraphRecapSourceSpan",
    "focus_overlay_from_world",
    "project_world_markdown_mentions",
    "recap_projection_trust_boundary",
]
