"""Types for immutable, product-owned source Markdown."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceMarkdownRecord(BaseModel):
    """One exact source revision plus its stable source-artifact identity."""

    model_config = ConfigDict(extra="forbid")

    source_revision_id: UUID
    source_artifact_id: str
    source_domain: str
    campaign_id: str | None = None
    session_id: str | None = None
    world_id: str | None = None
    content_sha256: str
    media_type: str
    encoding: str
    markdown: str
    lineage: dict[str, Any]
    created_at: datetime
