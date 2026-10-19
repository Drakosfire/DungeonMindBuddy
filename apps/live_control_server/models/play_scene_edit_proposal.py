"""Explicit saved-session scene edit input; the model never chooses its target."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from application_state.agent_conversation.types import PlayContentBasis


class PlaySceneEditProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = Field(default="dmb_play_scene_edit_request_v1", pattern="^dmb_play_scene_edit_request_v1$")
    run_revision: int = Field(strict=True, ge=1)
    content_basis: PlayContentBasis
    scene_id: str = Field(pattern=r"^scene:[a-z0-9][a-z0-9._-]{0,127}$")
    instruction: str = Field(min_length=1, max_length=8000)


    @field_validator("instruction")
    @classmethod
    def valid_instruction(cls, value: str) -> str:
        if not value.strip() or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("instruction must contain valid, non-empty Unicode text")
        return value


class GeneratedPlaySceneEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    replacement_markdown: str = Field(max_length=64000)
    summary: str = Field(max_length=1000)
    assumptions: list[str] = Field(max_length=8)
    cannot_complete_reason: str | None
