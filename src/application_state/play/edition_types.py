"""Strict Play-owned content edition and command contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def canonical_uuid(value: str) -> str:
    if str(UUID(value)) != value:
        raise ValueError("expected a canonical UUID")
    return value


class EditionOrigin(StrictModel):
    playable_artifact_id: str
    playable_revision: int = Field(gt=0)
    playable_work_revision_id: str
    playable_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    _ids = field_validator("playable_artifact_id", "playable_work_revision_id")(
        canonical_uuid
    )


class ContentCommit(StrictModel):
    schema_version: Literal["dmb_world_play_run_content_commit_v1"]
    expected_origin: EditionOrigin
    expected_edition_revision: int = Field(ge=0)
    expected_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    markdown: str

    @field_validator("markdown")
    @classmethod
    def bounded_markdown(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 1048576:
            raise ValueError("Markdown exceeds 1 MiB UTF8")
        return value


class RunContent(StrictModel):
    schema_version: Literal["dmb_world_play_run_content_v1"] = (
        "dmb_world_play_run_content_v1"
    )
    world_id: str
    run_id: str
    origin: EditionOrigin
    source: Literal["pinned", "edition"]
    edition_revision: int
    edition_revision_id: str | None
    markdown: str
    content_sha256: str
    committed_at: datetime
    observed_run_revision: int
    structure_sha256: str


class ContentReceipt(StrictModel):
    schema_version: Literal["dmb_world_play_run_content_receipt_v1"] = (
        "dmb_world_play_run_content_receipt_v1"
    )
    world_id: str
    run_id: str
    command_id: str
    request_sha256: str
    origin: EditionOrigin
    expected_edition_revision: int
    expected_content_sha256: str
    accepted_edition_revision: int
    accepted_edition_revision_id: str
    accepted_content_sha256: str
    committed_at: datetime
    observed_run_revision: int
