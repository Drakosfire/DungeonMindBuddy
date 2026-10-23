"""Exact Plan-scene template identities; preparation is separate from live Combat."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from application_state.combat_encounters.types import CombatEncounterRecord, CreateCombatEncounterRequest, CombatEncounterDraft

class PlanScenePin(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_id: UUID
    scene_id: str = Field(pattern=r"^scene:[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    revision_n: int = Field(gt=0)
    work_revision_id: UUID
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

class CreateSceneTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["dmb_scene_template_create_v1"] = "dmb_scene_template_create_v1"
    operation_id: UUID
    pin: PlanScenePin
    encounter: CreateCombatEncounterRequest

    @model_validator(mode="after")
    def valid_title(self):
        CombatEncounterDraft(title=self.encounter.title)
        return self

class SceneTemplateBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["dmb_scene_template_binding_v1"] = "dmb_scene_template_binding_v1"
    world_id: str
    encounter_id: UUID
    origin: PlanScenePin
    operation_id: UUID
    request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    created_at: datetime

class TemplateVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    revision: int = Field(gt=0)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    saved_at: datetime

class SceneTemplateView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    binding: SceneTemplateBinding
    encounter: CombatEncounterRecord
    versions: list[TemplateVersion]
    scene_present: bool
