"""Exact historical recap projected onto the current DungeonMind World."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from graph_memory.projection.world_projection import (
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionTrustBoundary,
)
from graph_memory.projection.world_recap_projection import (
    WorldGraphRecapFocusOverlay,
    WorldGraphRecapMention,
    WorldGraphRecapSourceSpan,
)

HISTORICAL_RECAP_PROJECTION_SCHEMA = "dmb_historical_recap_world_projection_v1"
HistoricalProjectionStatus = Literal["available", "unavailable"]


class _HistoricalRecapProjectionModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class HistoricalRecapWorldProjectionResponse(_HistoricalRecapProjectionModel):
    """One exact run/source binding plus one governed current-World snapshot."""

    schema_: Literal["dmb_historical_recap_world_projection_v1"] = Field(
        default=HISTORICAL_RECAP_PROJECTION_SCHEMA,
        alias="schema",
    )
    run_id: str
    run_status: str
    source_domain: str
    source_artifact_id: str
    source_revision_id: str
    campaign_id: str
    session_id: str
    world_id: str
    source_sha256: str
    source_status: HistoricalProjectionStatus = "available"
    graph_status: HistoricalProjectionStatus = "available"
    graph_id: str
    snapshot: WorldGraphProjectionSnapshot
    markdown: str
    focus: WorldGraphRecapFocusOverlay
    node_views: dict[str, WorldGraphProjectionNodeView] = Field(default_factory=dict)
    mentions: list[WorldGraphRecapMention] = Field(default_factory=list)
    source_spans: list[WorldGraphRecapSourceSpan] = Field(default_factory=list)
    diagnostics: list[WorldGraphProjectionDiagnostic] = Field(default_factory=list)
    trust_boundary: WorldGraphProjectionTrustBoundary
