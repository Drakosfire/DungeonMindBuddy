from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AuthorityEffect = Literal[
    "routing_only",
    "metadata_only",
    "answer_evidence_allowed",
    "answer_evidence_forbidden",
    "requires_policy",
]

EntityKind = Literal["npc", "location", "faction", "institution", "organization", "unknown"]


class RouteEquivalenceRecord(BaseModel):
    """Deterministic route-equivalence edge for Phase B shadow mode."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="0.2.0")
    record_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    entity_kind: EntityKind = "unknown"
    display_name: str = Field(min_length=1)
    from_route_id: str = Field(min_length=1)
    to_route_id: str = Field(min_length=1)
    edge_kind: Literal["setting_fallback"] = "setting_fallback"
    source_type: Literal["npc_registry"] = "npc_registry"
    authority_effect: AuthorityEffect = "routing_only"
    confidence: Literal["high", "medium", "low"] = "high"
