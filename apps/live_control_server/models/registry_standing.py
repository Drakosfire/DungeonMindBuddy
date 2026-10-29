"""Bounded C1 standing requests; clients never supply source paths or native DSNs."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceRequest(StrictRequest):
    schema_version: Literal["dmb_pc_standing_source_v1"] = "dmb_pc_standing_source_v1"
    managed_world_id: str = Field(min_length=1)
    campaign_id: Literal["longmont-c1"]
    roster_key: Literal["1"]
    operation_id: UUID
    created_at: AwareDatetime
    expected_parent_revision_id: str = Field(min_length=1)
    registry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dossier_sha256: dict[str, str]


class IdentityChoice(StrictRequest):
    slug: str = Field(pattern=r"^[a-z0-9_]+$")
    action: Literal["create", "use_existing"]
    entity_id: str | None = None

    @model_validator(mode="after")
    def valid_choice(self):
        if (self.action == "create" and self.entity_id is not None) or (
            self.action == "use_existing"
            and (
                not self.entity_id
                or self.entity_id != self.entity_id.strip()
                or not self.entity_id.startswith("ent:")
            )
        ):
            raise ValueError("use_existing requires an entity_id; create forbids one")
        return self


class PrepareRequest(StrictRequest):
    schema_version: Literal["dmb_pc_standing_prepare_v1"] = "dmb_pc_standing_prepare_v1"
    operation_id: UUID
    source_packet: dict[str, Any]
    source_token: str
    choices: list[IdentityChoice] = Field(min_length=6, max_length=6)


class ConfirmRequest(StrictRequest):
    schema_version: Literal["dmb_pc_standing_confirm_v1"] = "dmb_pc_standing_confirm_v1"
    envelope: dict[str, Any]
    token: str
    prepared: dict[str, Any]
