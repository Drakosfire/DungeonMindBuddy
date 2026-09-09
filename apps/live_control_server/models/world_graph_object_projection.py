"""Surface-neutral complete World-object projection contract (#697).

This is the product read for one selected World object at an exact revision.
Object truth is World-cross-campaign. Campaign/session on the request are
focus metadata only. Completeness is explicit and is never implied by the
bounded retrieval caps.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from graph_memory.projection.world_projection import (
    WorldGraphProjectionNodeView,
    WorldGraphProjectionSnapshot,
)
from graph_memory.retrieval.models import WorldGraphRetrievalFocus

OBJECT_PROJECTION_REQUEST_SCHEMA = "dmb_world_graph_object_projection_request_v1"
OBJECT_PROJECTION_RESPONSE_SCHEMA = "dmb_world_graph_object_projection_v1"
OBJECT_PROJECTION_ERROR_SCHEMA = "dmb_world_graph_object_projection_error_v1"

ObjectProjectionOrigin = Literal["ingest", "plan", "build", "play", "agent"]
ObjectProjectionCompletenessStatus = Literal["complete", "partial"]
ProvenanceStatus = Literal[
    "excerpt_ready",
    "no_source_span",
    "source_not_durable",
    "unsupported_source_media",
    "source_binding_unavailable",
    "span_unresolvable",
]
ObjectProjectionAssertionKind = Literal[
    "existence",
    "alias",
    "summary",
    "property",
    "aspect",
]


class _ObjectProjectionModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class _ObjectProjectionRequestModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=False,
        strict=True,
    )


class WorldGraphObjectProjectionRequest(_ObjectProjectionRequestModel):
    schema_: Literal[OBJECT_PROJECTION_REQUEST_SCHEMA] = Field(
        alias="schema"
    )
    world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    focus: WorldGraphRetrievalFocus = Field(default_factory=WorldGraphRetrievalFocus)
    admissibility: str = "gm"
    revision_pin: str | None = None
    origin_surface: ObjectProjectionOrigin | None = None

    @field_validator("world_id", "campaign_id", "node_id")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must be a non-empty string")
        return cleaned


class SelectedObjectCompletenessView(_ObjectProjectionModel):
    status: ObjectProjectionCompletenessStatus
    reason: str | None = None
    truncated_fields: list[str] = Field(default_factory=list)


class WorldGraphObjectProjectionAssertion(_ObjectProjectionModel):
    assertion_id: str
    subject_node_id: str
    assertion_kind: ObjectProjectionAssertionKind
    predicate: str | None = None
    label: str | None = None
    text_value: str | None = None
    value: dict[str, Any] = Field(default_factory=dict)
    alias: str | None = None
    summary: str | None = None
    aspect_key: str | None = None
    aspect_kind: str | None = None
    epistemic_kind: str | None = None
    visibility: str | None = None
    campaign_scope: str | None = None
    temporal_scope: dict[str, Any] | None = None
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)


class WorldGraphObjectProjectionRelationship(_ObjectProjectionModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    predicate: str
    label: str
    direction: Literal["outgoing", "incoming"]
    session_ids: list[str] = Field(default_factory=list)
    visibility: str | None = None
    campaign_scope: str | None = None
    epistemic_kind: str | None = None
    temporal_scope: dict[str, Any] | None = None
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)


class WorldGraphObjectProjectionSourceBinding(_ObjectProjectionModel):
    evidence_ref_id: str
    source_artifact_id: str
    source_revision_id: str | None = None
    content_sha256: str | None = None
    source_span_ref_id: str | None = None
    source_domain: str | None = None
    session_id: str | None = None
    provenance_status: ProvenanceStatus
    excerpt: str | None = None


class WorldGraphObjectProjectionTelemetry(_ObjectProjectionModel):
    world_read_ms: float | None = None
    source_batch_read_ms: float | None = None
    provenance_hydration_ms: float | None = None
    serialization_ms: float | None = None
    total_ms: float | None = None
    relationship_count: int = 0
    assertion_count: int = 0
    evidence_count: int = 0
    temporally_qualified_fact_count: int = 0
    distinct_source_binding_count: int = 0
    durable_source_hit_count: int = 0
    durable_source_miss_count: int = 0
    excerpt_count: int = 0
    completeness: ObjectProjectionCompletenessStatus = "complete"
    truncated_fields: list[str] = Field(default_factory=list)


class WorldGraphObjectProjectionResult(_ObjectProjectionModel):
    schema_: Literal[OBJECT_PROJECTION_RESPONSE_SCHEMA] = Field(
        alias="schema",
        default=OBJECT_PROJECTION_RESPONSE_SCHEMA,
    )
    found: bool
    completeness: SelectedObjectCompletenessView
    snapshot: WorldGraphProjectionSnapshot | None = None
    requested_node_id: str
    resolved_node_id: str | None = None
    node: WorldGraphProjectionNodeView | None = None
    related_nodes: list[WorldGraphProjectionNodeView] = Field(default_factory=list)
    relationships: list[WorldGraphObjectProjectionRelationship] = Field(
        default_factory=list
    )
    assertions: list[WorldGraphObjectProjectionAssertion] = Field(default_factory=list)
    source_bindings: list[WorldGraphObjectProjectionSourceBinding] = Field(
        default_factory=list
    )
    semantic_fingerprint: str | None = None
    telemetry: WorldGraphObjectProjectionTelemetry = Field(
        default_factory=WorldGraphObjectProjectionTelemetry
    )


class WorldGraphObjectProjectionError(_ObjectProjectionModel):
    schema_: Literal[OBJECT_PROJECTION_ERROR_SCHEMA] = Field(
        alias="schema",
        default=OBJECT_PROJECTION_ERROR_SCHEMA,
    )
    code: str
    message: str
    status_code: int


def object_projection_semantic_fingerprint(
    *,
    revision_id: str,
    node_id: str,
    admissibility: str,
    assertions: list[WorldGraphObjectProjectionAssertion],
    relationships: list[WorldGraphObjectProjectionRelationship],
    related_node_ids: list[str],
    source_bindings: list[WorldGraphObjectProjectionSourceBinding],
) -> str:
    """Deterministic fingerprint over World truth, not surface chrome."""
    payload = {
        "revision_id": revision_id,
        "node_id": node_id,
        "admissibility": admissibility,
        "assertions": [
            {
                "assertion_id": row.assertion_id,
                "kind": row.assertion_kind,
                "campaign_scope": row.campaign_scope,
                "temporal_scope": row.temporal_scope,
                "evidence_ref_ids": list(row.evidence_ref_ids),
            }
            for row in sorted(assertions, key=lambda item: item.assertion_id)
        ],
        "relationships": [
            {
                "edge_id": row.edge_id,
                "source_node_id": row.source_node_id,
                "target_node_id": row.target_node_id,
                "predicate": row.predicate,
                "direction": row.direction,
                "campaign_scope": row.campaign_scope,
                "temporal_scope": row.temporal_scope,
                "evidence_ref_ids": list(row.evidence_ref_ids),
            }
            for row in sorted(relationships, key=lambda item: item.edge_id)
        ],
        "related_node_ids": sorted(related_node_ids),
        "source_bindings": [
            {
                "evidence_ref_id": row.evidence_ref_id,
                "source_artifact_id": row.source_artifact_id,
                "source_revision_id": row.source_revision_id,
                "content_sha256": row.content_sha256,
                "provenance_status": row.provenance_status,
            }
            for row in sorted(source_bindings, key=lambda item: item.evidence_ref_id)
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
