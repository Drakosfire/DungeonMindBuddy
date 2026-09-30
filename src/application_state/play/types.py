"""Play Runtime storage types. Public Playable grammar stays in the Play adapters."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class PlayRun(BaseModel):
    run_id: UUID
    campaign_id: str | None
    world_id: str | None = None
    playable_work_object_id: UUID
    playable_revision_n: int
    playable_work_revision_id: UUID
    playable_content_sha256: str
    run_revision: int
    progress: dict[str, Any]
    rebased_from_run_revision: int | None = None
    created_at: datetime
    updated_at: datetime


class PlayRunManifest(BaseModel):
    run_id: UUID
    playable_work_object_id: UUID
    playable_revision_n: int
    playable_work_revision_id: UUID
    playable_content_sha256: str
    manifest: dict[str, Any]
    sealed_at: datetime


class PlayRunAggregate(BaseModel):
    run: PlayRun
    manifest: PlayRunManifest


class WorldPlayRunAggregate(BaseModel):
    """A PlayRun whose World was resolved from its exact pinned revision."""

    run: PlayRun
    manifest: PlayRunManifest
    world_id: str


class PlayActiveRun(BaseModel):
    run_id: UUID
    selected_at: datetime
