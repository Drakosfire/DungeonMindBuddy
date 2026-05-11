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
    """Deterministic route-equivalence edge for Phase B shadow mode.

    Note:
        `source_type="npc_registry"` denotes the current registry file contract
        (`_npc_registry.json` lineage), not a restriction that `entity_kind` must be `npc`.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="0.3.0")
    producer_registry_path: str = Field(default="pending", min_length=1)
    producer_registry_sha256: str = Field(default="0" * 64, min_length=64, max_length=64)
    route_equivalence_manifest_hash: str = Field(default="0" * 64, min_length=64, max_length=64)
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
