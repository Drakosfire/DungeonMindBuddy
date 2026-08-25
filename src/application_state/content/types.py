"""Content-domain types. WorkObject is not a universal application object."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AdmittedKind = Literal["plan", "runbook"]
ObjectStatus = Literal["active", "discarded"]


def sha256_utf8(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def normalize_markdown(markdown: str) -> str:
    return markdown.replace("\r\n", "\n").replace("\r", "\n")


class WorkObject(BaseModel):
    work_object_id: UUID
    kind: AdmittedKind
    campaign_id: str
    world_id: str | None = None
    title: str
    target_session: int | None = None
    target_relpath: str | None = None
    status: ObjectStatus = "active"
    current_revision_id: UUID | None = None
    object_revision: int
    created_at: datetime
    updated_at: datetime


class WorkRevision(BaseModel):
    work_revision_id: UUID
    work_object_id: UUID
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
