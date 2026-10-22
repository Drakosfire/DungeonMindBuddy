"""Immutable association requests and durable verification receipts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImmutableModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WorldMechanicsTarget(ImmutableModel):
    managed_world_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,62}$")
    native_world_id: str = Field(min_length=1)
    binding_version: int = Field(gt=0)
    graph_revision_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    kind: str
    role: str
    campaign_scope: str | None


class MechanicsLocator(ImmutableModel):
    provider: Literal["dungeonmind"]
    statblock_id: str = Field(pattern=r"^sb_[a-z0-9]+$")
    revision_id: str = Field(pattern=r"^rev_[a-z0-9]+$")
    contract: Literal["dungeonmind.dungeonbuddy-statblocks"]
    contract_version: Literal["1.0.0"]
    definition_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class AssociateWorldMechanicsRequest(ImmutableModel):
    request_id: UUID
    draft_id: UUID
    expected_draft_version: int = Field(gt=0)
    target: WorldMechanicsTarget
    expected_version: int = Field(ge=0)

    @property
    def digest(self) -> str:
        body = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(body.encode()).hexdigest()


class AcceptedMechanicsProof(ImmutableModel):
    locator: MechanicsLocator
    acceptance_operation_id: str = Field(min_length=1)
    accepted_from_draft_version: int = Field(gt=0)
    accepted_from_candidate_id: str | None
    acceptance_request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class WorldMechanicsAssociation(ImmutableModel):
    association_id: UUID
    request: AssociateWorldMechanicsRequest
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    version: int = Field(gt=0)
    previous_association_id: UUID | None
    proof: AcceptedMechanicsProof
    actor: str = Field(min_length=1)
    created_at: datetime

    @model_validator(mode="after")
    def invariants(self):
        if self.request_digest != self.request.digest:
            raise ValueError("Association request digest is invalid")
        if self.version != self.request.expected_version + 1:
            raise ValueError("Association version does not follow its expected slot version")
        if (self.version == 1) != (self.previous_association_id is None):
            raise ValueError("Association predecessor does not match slot version")
        return self


class AssociateWorldMechanicsResponse(ImmutableModel):
    association: WorldMechanicsAssociation
    replayed: bool
