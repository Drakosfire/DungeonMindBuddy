"""SBW10a: read-only exact Threat query + per-binding mechanics hydration models.

Derived reads only. Never durable authority. Never copies mechanics into World Graph.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ExactRevisionResourceV1,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRelationshipView,
)
from graph_memory.union_supergraph.statblock_binding import ThreatStatblockBindingV1

QUERY_REQUEST_SCHEMA = "dmb_threat_query_hydration_request_v1"
QUERY_RESPONSE_SCHEMA = "dmb_threat_query_hydration_response_v1"

ThreatQueryHydrationResultLabel = Literal[
    "threat_query_hydration_ok",
    "threat_query_hydration_partial",
    "threat_query_hydration_empty",
    "threat_query_hydration_unavailable",
    "threat_query_hydration_not_found",
    "threat_query_hydration_integrity_failure",
]

MechanicsDisposition = Literal[
    "no_binding",
    "hydrated",
    "partial",
    "unavailable",
    "integrity_failure",
    "not_requested",
]

BindingHydrationStatus = Literal[
    "available",
    "unavailable",
    "exact_revision_missing",
    "integrity_failure",
    "not_requested",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        alias_generator=to_camel,
    )


class ThreatQueryHydrationRequestV1(StrictModel):
    schema_: Literal["dmb_threat_query_hydration_request_v1"] = Field(
        default=QUERY_REQUEST_SCHEMA,
        alias="schema",
    )
    world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    revision_pin: str = Field(min_length=1)
    query_text: str = Field(min_length=1)
    focus_node_ids: list[str] = Field(default_factory=list, max_length=8)
    relationship_predicates: list[str] = Field(default_factory=list, max_length=16)
    max_hits: int = Field(default=16, ge=1, le=64)
    include_mechanics: bool = True

    @field_validator("world_id", "campaign_id", "revision_pin", "query_text", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("focus_node_ids", "relationship_predicates", mode="before")
    @classmethod
    def _strip_list(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("list entries must be strings")
            text = item.strip()
            if text:
                cleaned.append(text)
        return cleaned


class ThreatBindingHydrationV1(StrictModel):
    """Per-binding hydration result.

    Well-formed bindings carry exact immutable locators. Malformed
    ``uses_statblock`` edges carry ``relationship_edge_id`` and leave
    binding/statblock/revision/digest null — never fabricate those identities.
    """

    relationship_edge_id: str
    binding_id: str | None = None
    binding_role: str | None = None
    threat_node_id: str
    resource_node_id: str | None = None
    provider: Literal["dungeonmind"] = "dungeonmind"
    statblock_id: str | None = None
    revision_id: str | None = None
    definition_digest: str | None = None
    hydration_status: BindingHydrationStatus
    binding: ThreatStatblockBindingV1 | None = None
    revision: ExactRevisionResourceV1 | None = None
    message: str | None = None


class ThreatQueryHydrationHitV1(StrictModel):
    threat: WorldGraphProjectionNodeView
    match_reasons: list[str] = Field(default_factory=list)
    relationships: list[WorldGraphProjectionRelationshipView] = Field(
        default_factory=list
    )
    bindings: list[ThreatBindingHydrationV1] = Field(default_factory=list)
    mechanics_disposition: MechanicsDisposition


class ThreatQueryHydrationResponseV1(StrictModel):
    schema_: Literal["dmb_threat_query_hydration_response_v1"] = Field(
        default=QUERY_RESPONSE_SCHEMA,
        alias="schema",
    )
    world_id: str
    campaign_id: str
    revision_id: str
    query_text: str
    result_label: ThreatQueryHydrationResultLabel
    hits: list[ThreatQueryHydrationHitV1] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list, max_length=32)
    message: str | None = None


__all__ = [
    "BindingHydrationStatus",
    "MechanicsDisposition",
    "QUERY_REQUEST_SCHEMA",
    "QUERY_RESPONSE_SCHEMA",
    "ThreatBindingHydrationV1",
    "ThreatQueryHydrationHitV1",
    "ThreatQueryHydrationRequestV1",
    "ThreatQueryHydrationResponseV1",
    "ThreatQueryHydrationResultLabel",
]
