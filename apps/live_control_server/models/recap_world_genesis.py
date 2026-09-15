"""Storage-neutral prepare/confirm values for recap World genesis."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RECAP_WORLD_GENESIS_PLAN_SCHEMA = "dmb_recap_world_genesis_plan_v1"


class _GenesisModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RecapWorldGenesisPrepareRequest(_GenesisModel):
    world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    baseline_roster_key: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)


class RecapWorldGenesisPlan(_GenesisModel):
    schema_: Literal[RECAP_WORLD_GENESIS_PLAN_SCHEMA] = Field(
        default=RECAP_WORLD_GENESIS_PLAN_SCHEMA, alias="schema"
    )
    plan_id: str
    plan_digest: str
    initialization_id: str
    world_id: str
    campaign_id: str
    baseline_roster_key: str
    source_artifact_id: str
    source_revision_id: str
    source_uri: str
    contribution_id: str
    contribution_payload_sha256: str
    accepted_assertion_ids: tuple[str, ...]
    pc_object_ids: tuple[str, ...]
    pc_identity_keys: tuple[str, ...]
    confirmable: Literal[True] = True


class RecapWorldGenesisConfirmRequest(_GenesisModel):
    plan: RecapWorldGenesisPlan
    confirming_principal: str = Field(min_length=1)


class RecapWorldGenesisReceipt(_GenesisModel):
    world_id: str
    initialization_id: str
    plan_id: str
    plan_digest: str
    source_artifact_id: str
    source_revision_id: str
    contribution_id: str
    published_revision_id: str
    accepted_assertion_ids: tuple[str, ...]
    pc_object_ids: tuple[str, ...]
    outcome: Literal["initialized", "already_initialized"]
