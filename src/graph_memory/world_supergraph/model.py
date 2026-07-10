"""Models for World SuperGraph revisions, head, and integrity reporting.

This package is the durable per-``worldId`` storage seam (PR002). Preview-run
loaders and latest-ingest selectors are not production graph identity — they
remain temporary consumers until PR006–PR008 replacements land.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _WorldGraphModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class WorldGraphRevision(_WorldGraphModel):
    """Immutable published revision metadata for one World SuperGraph snapshot."""

    world_id: str
    revision_id: str
    parent_revision_id: str | None
    created_at: str
    operation_ids: list[str] = Field(default_factory=list)
    graph_schema: str
    graph_payload_sha256: str
    graph_payload_path: str
    status: Literal["published"] = "published"


class WorldGraphHead(_WorldGraphModel):
    """Atomic pointer to the current validated revision for a world."""

    world_id: str
    head_revision_id: str
    updated_at: str


class WorldGraphIntegrityReport(_WorldGraphModel):
    """Machine-readable stub health report for a world graph store (PR002)."""

    world_id: str
    head_revision_id: str | None
    parent_revision_id: str | None
    load_ok: bool
    validation_ok: bool
    revision_count: int
    graph_payload_sha256: str | None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WorldGraphPublishResult(_WorldGraphModel):
    """Result of publishing a new immutable revision and advancing the head."""

    head: WorldGraphHead
    revision: WorldGraphRevision
