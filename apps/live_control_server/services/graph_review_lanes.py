"""Shared lane contract models for graph review workbench comparisons.

These models intentionally describe comparable review sources only. They do not
load artifacts, compute projection availability, or mutate graph/corpus state.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class _GraphReviewLaneModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        use_enum_values=True,
    )


class GraphReviewLaneRole(str, Enum):
    GOLD = "gold"
    LIVE = "live"
    VARIANT = "variant"
    REFERENCE = "reference"


class GraphReviewLaneSourceKind(str, Enum):
    GOLD_FIXTURE = "gold_fixture"
    GRAPH_INGEST_RUN = "graph_ingest_run"
    MANUAL_REVIEW_VARIANT = "manual_review_variant"
    PROJECTION_PAYLOAD = "projection_payload"


class GraphReviewLaneStatus(str, Enum):
    AVAILABLE = "available"
    MISSING_PROJECTION = "missing_projection"
    FAILED = "failed"
    STALE = "stale"
    UNKNOWN = "unknown"


class GraphReviewVocabularyMode(str, Enum):
    NONE = "none"
    NODE = "node"
    EDGE = "edge"
    NODE_AND_EDGE = "node_and_edge"
    DYNAMIC = "dynamic"
    UNKNOWN = "unknown"


class GraphReviewLaneCounts(_GraphReviewLaneModel):
    nodes: int = 0
    edges: int = 0
    beats: int | None = None
    evidence_refs: int | None = None


class GraphReviewLaneMetadata(_GraphReviewLaneModel):
    run_id: str | None = None
    generated_at: str | None = None
    model_id: str | None = None
    extraction_profile: str | None = None
    extraction_mode: str | None = None
    vocabulary_mode: GraphReviewVocabularyMode = GraphReviewVocabularyMode.UNKNOWN
    runner_options: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class GraphReviewLane(_GraphReviewLaneModel):
    lane_id: str
    role: GraphReviewLaneRole
    source_kind: GraphReviewLaneSourceKind
    label: str
    campaign_id: str
    session_id: str

    manifest_path: str | None = None
    artifact_path: str | None = None
    gold_path: str | None = None
    preview_union_path: str | None = None

    status: GraphReviewLaneStatus = GraphReviewLaneStatus.UNKNOWN

    counts: GraphReviewLaneCounts
    metadata: GraphReviewLaneMetadata
