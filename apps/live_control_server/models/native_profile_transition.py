"""Closed host-owned explicit profile transition review; no automatic adoption."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel
from dungeonmind.contracts.vnext.knowledge import MigrationOriginRef
from dungeonmind.contracts.vnext.profile_transition import KnowledgeProfileTransitionV1

Identifier = Annotated[
    str, Field(min_length=1, max_length=512, pattern=r"^\S(?:.*\S)?$")
]


class Closed(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, alias_generator=to_camel
    )


class ProfileTransitionPrepare(Closed):
    schema_: Literal["dmb_native_profile_transition_prepare_v1"] = Field(alias="schema")
    managed_world_id: Identifier
    expected_native_world_id: Identifier
    expected_binding_version: int = Field(ge=1, strict=True)
    expected_parent_revision_id: Identifier
    publication_id: Identifier


class ProfileTransitionContent(Closed):
    schema_: Literal["dmb_native_profile_transition_plan_v1"] = Field(
        default="dmb_native_profile_transition_plan_v1", alias="schema"
    )
    managed_world_id: Identifier
    native_world_id: Identifier
    binding_version: int = Field(ge=1, strict=True)
    request: KnowledgeProfileTransitionV1
    parent_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    migration_origin_ref: MigrationOriginRef | None
    prepared_by: Identifier
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def aware(cls, value):
        if value.utcoffset() is None:
            raise ValueError("expiry must be timezone-aware")
        return value

    @model_validator(mode="after")
    def correlated(self):
        if self.request.space_id != self.native_world_id:
            raise ValueError("transition space must match managed binding")
        if self.expires_at <= self.request.created_at:
            raise ValueError("expiry must follow preparation")
        return self


class SignedProfileTransition(ProfileTransitionContent):
    token: str = Field(min_length=1, max_length=65536)


class ProfileTransitionConfirm(Closed):
    schema_: Literal["dmb_native_profile_transition_confirm_v1"] = Field(alias="schema")
    plan: SignedProfileTransition
