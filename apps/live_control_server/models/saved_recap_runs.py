"""Saved extraction read coordinates; never admission or publication authority."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class SavedRecapRun(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    run_id: str
    run_revision: int
    run_status: str
    source_artifact_id: str
    campaign_id: str | None
    session_id: str | None
    profile_id: str | None
    created_at: str | None
    updated_at: str | None
    source_revision_id: UUID | None = None
    source_sha256: str | None = None
    unavailable_reason: str | None = None


class SavedRecapRunsResponse(BaseModel):
    model_config = SavedRecapRun.model_config

    schema_: Literal["dmb_saved_recap_runs_v1"] = Field(
        default="dmb_saved_recap_runs_v1", alias="schema"
    )
    managed_world_id: str
    native_world_id: str
    binding_version: int
    runs: list[SavedRecapRun]


class SavedRecapSourceResponse(BaseModel):
    model_config = SavedRecapRun.model_config

    schema_: Literal["dmb_saved_recap_source_v1"] = Field(
        default="dmb_saved_recap_source_v1", alias="schema"
    )
    managed_world_id: str
    native_world_id: str
    binding_version: int
    run: SavedRecapRun
    source_prose: str
