from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from src.statblocks.v2_contract import (
    CombatDefaults,
    DraftProvenance,
    ReviewWarning,
    SourceRef,
    StatBlockDraftResponse,
)

StatblockLifecycleState = Literal[
    "description_requested",
    "description_drafted",
    "description_approved",
    "generation_requested",
    "live_draft",
    "needs_review",
    "reviewed",
    "stored_artifact",
    "promotion_previewed",
    "corpus_promoted",
    "indexed",
    "combat_ready",
]

StatblockReviewStatus = Literal[
    "needs_dm_review", "warnings", "failed", "approved", "rejected"
]
StatblockStorageStatus = Literal["not_stored", "stored_draft", "exported", "archived"]
StatblockCorpusStatus = Literal[
    "not_promoted",
    "promotion_previewed",
    "promotion_confirmed",
    "write_failed",
    "indexed",
    "retrievable",
]
StatblockCreatedBy = Literal["human", "agent", "planning_task", "combat_task"]


class StatblockBreadcrumb(BaseModel):
    label: str
    source: str | None = None
    target: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StatblockDraftArtifact(BaseModel):
    artifact_id: str
    draft_id: str
    title: str
    markdown: str
    structured_statblock: dict[str, Any]
    combat_defaults: CombatDefaults
    warnings: list[ReviewWarning]
    provenance: DraftProvenance
    review_status: StatblockReviewStatus
    lifecycle_state: StatblockLifecycleState
    storage_status: StatblockStorageStatus
    corpus_status: StatblockCorpusStatus
    source_refs: list[SourceRef]
    breadcrumbs: list[StatblockBreadcrumb]
    created_by: StatblockCreatedBy
    created_at: str
    updated_at: str


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _title_from_response(response: StatBlockDraftResponse) -> str:
    draft = response.draft
    if draft is None:
        raise ValueError("cannot derive title without draft")
    combat_name = (draft.combat_defaults.name or "").strip()
    if combat_name:
        return combat_name
    statblock_name = str(draft.statblock.get("name") or "").strip()
    if statblock_name:
        return statblock_name
    return draft.draft_id


def artifact_from_draft_response(
    response: StatBlockDraftResponse,
    *,
    created_by: StatblockCreatedBy,
    breadcrumbs: list[StatblockBreadcrumb] | None = None,
    now: Callable[[], datetime] | None = None,
    artifact_id_factory: Callable[[], str] | None = None,
) -> StatblockDraftArtifact:
    if not response.success or response.draft is None:
        raise ValueError(
            "only successful statblock draft responses can become draft artifacts"
        )

    draft = response.draft
    clock = now or _utc_now
    current_time = clock().astimezone(UTC).isoformat()
    artifact_id = (
        artifact_id_factory()
        if artifact_id_factory is not None
        else f"statblock-draft-{uuid4()}"
    )

    return StatblockDraftArtifact(
        artifact_id=artifact_id,
        draft_id=draft.draft_id,
        title=_title_from_response(response),
        markdown=draft.markdown,
        structured_statblock=draft.statblock,
        combat_defaults=draft.combat_defaults,
        warnings=draft.warnings,
        provenance=draft.provenance,
        review_status=draft.review_status,
        lifecycle_state="live_draft",
        storage_status="not_stored",
        corpus_status="not_promoted",
        source_refs=draft.provenance.source_refs,
        breadcrumbs=breadcrumbs or [],
        created_by=created_by,
        created_at=current_time,
        updated_at=current_time,
    )
