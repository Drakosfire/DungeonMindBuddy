"""Typed Content aggregates. Pages are not Playable WorkObjects."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

AdmittedKind = Literal["plan", "runbook"]
ObjectStatus = Literal["active", "discarded"]


def sha256_utf8(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def normalize_markdown(markdown: str) -> str:
    return markdown.replace("\r\n", "\n").replace("\r", "\n")


class _StoredDocument(BaseModel):
    work_object_id: UUID
    kind: str
    campaign_id: str | None
    world_id: str | None = None
    title: str
    target_session: int | None = None
    target_relpath: str | None = None
    status: ObjectStatus = "active"
    current_revision_id: UUID | None = None
    object_revision: int
    created_at: datetime
    updated_at: datetime


class WorkObject(_StoredDocument):
    kind: AdmittedKind

    @model_validator(mode="after")
    def validate_scope(self) -> "WorkObject":
        if self.world_id is None:
            if not self.campaign_id or not self.campaign_id.strip():
                raise ValueError("campaign-owned work objects require campaign_id")
            return self
        if self.campaign_id is not None:
            raise ValueError("World-owned content cannot also have campaign_id")
        if not self.world_id.strip():
            raise ValueError("World-owned content requires world_id")
        if self.target_session is not None:
            raise ValueError("World-owned content cannot have target_session")
        return self


class AuthoredPageObject(_StoredDocument):
    """World-owned editable page; never admitted by Plan/Runbook or Play APIs."""

    kind: Literal["worldbuilding_source"] = "worldbuilding_source"
    world_id: str
    campaign_id: None = None
    target_session: None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "AuthoredPageObject":
        if not self.world_id or self.world_id != self.world_id.strip():
            raise ValueError("authored pages require an exact World owner")
        return self


_StoredContentObject = WorkObject | AuthoredPageObject
_StoredKind = Literal["plan", "runbook", "worldbuilding_source"]


class WorkRevision(BaseModel):
    work_revision_id: UUID
    work_object_id: UUID
    world_id: str | None = None
    revision_n: int
    markdown: str
    content_sha256: str
    created_at: datetime


class WorkingCopy(BaseModel):
    work_object_id: UUID
    markdown: str
    content_sha256: str
    base_revision_id: UUID | None = None
    working_copy_revision: int
    updated_at: datetime


class ContentSnapshot(BaseModel):
    work_object: WorkObject
    markdown: str
    content_sha256: str
    loaded_revision: int
    from_working_copy: bool = False


class CommittedPlayableRevision(BaseModel):
    """Immutable committed Content revision. Play binds ``revision_n``, not object CAS."""

    work_object: WorkObject
    work_revision: WorkRevision
    has_divergent_working_copy: bool = False


class ImportReport(BaseModel):
    imported: int = 0
    noop: int = 0
    skipped_empty: int = 0
    work_object_ids: list[str] = Field(default_factory=list)
