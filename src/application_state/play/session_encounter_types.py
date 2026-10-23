"""Closed current session creation and scene materialization intents."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from application_state.play.types import WorldPlayRunAggregate

class TemplatePin(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    encounter_id: UUID
    revision: int = Field(gt=0, strict=True)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

class SceneEncounterSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    scene_id: str = Field(pattern=r"^scene:[A-Za-z0-9][A-Za-z0-9._:-]*$")
    template: TemplatePin | None

class WorldSessionSourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    playable_artifact_id: UUID
    expected_playable_revision: int = Field(gt=0, strict=True)
    expected_playable_work_revision_id: UUID
    expected_playable_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

class WorldSessionCreateRequest(WorldSessionSourceRequest):
    schema_version: Literal["dmb_world_session_create_v1"]
    entry_scene_id: str | None
    encounters: list[SceneEncounterSelection]

    @model_validator(mode="after")
    def unique_scenes(self):
        ids=[item.scene_id for item in self.encounters]
        if len(ids)!=len(set(ids)):
            raise ValueError("Session scene selections must be unique")
        return self

class RunEncounterScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: UUID
    scene_id: str = Field(pattern=r"^scene:[A-Za-z0-9][A-Za-z0-9._:-]*$")

class MaterializeSceneEncounterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["dmb_scene_encounter_materialize_v1"]
    operation_id: UUID
    expected_preparation_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    template: TemplatePin
    initialization_policy: Literal["dmb_fresh_scene_encounter_v1"]
    preview_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

class WorldSessionCreationResult(BaseModel):
    aggregate: WorldPlayRunAggregate
    receipt: dict
