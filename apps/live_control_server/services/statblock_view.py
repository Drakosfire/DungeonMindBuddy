from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.services.statblock_draft_store import (
    StoredStatblockDraftRecord,
    read_statblock_draft,
)
from apps.live_control_server.services.statblock_workbench import StatblockWorkbenchAction
from src.live_play.live_store import load_json
from src.statblocks.lifecycle_artifact import StatblockBreadcrumb
from src.statblocks.v2_contract import CombatDefaults, ReviewWarning, SourceRef

SCHEMA_VERSION_LIST = "dmb_generated_statblock_list_v1"
SCHEMA_VERSION_DETAIL = "dmb_generated_statblock_detail_v1"
CORPUS_MARKDOWN_ROOT = Path("corpus") / "eldyrwild-markdown"


class StatblockViewError(RuntimeError):
    status_code = 500


class StatblockViewConflictError(StatblockViewError):
    status_code = 409


class GeneratedStatblockListItem(BaseModel):
    artifact_id: str
    draft_id: str
    title: str
    campaign_id: str
    session: int
    review_status: str
    lifecycle_state: str
    storage_status: str
    corpus_status: str
    retrieval_status: str | None = None
    corpus_relpath: str
    corpus_display_path: str
    corpus_written_at: str | None = None
    retrieval_verified_at: str | None = None
    armor_class: int | str | None = None
    hit_points: int | str | None = None
    challenge_rating: str | None = None
    creature_type: str | None = None
    primary_actions: list[str] = Field(default_factory=list)
    warning_count: int = 0


class GeneratedStatblockListResponse(BaseModel):
    schema_version: Literal["dmb_generated_statblock_list_v1"] = SCHEMA_VERSION_LIST
    statblocks: list[GeneratedStatblockListItem]
    diagnostics: list[str] = Field(default_factory=list)


class GeneratedStatblockDetailResponse(BaseModel):
    schema_version: Literal["dmb_generated_statblock_detail_v1"] = SCHEMA_VERSION_DETAIL
    artifact_id: str
    draft_id: str
    title: str
    stored_record: StoredStatblockDraftRecord
    corpus_relpath: str
    corpus_display_path: str
    corpus_markdown: str
    corpus_markdown_bytes: int
    corpus_file_fingerprint: str | None = None
    combat_defaults: CombatDefaults
    warnings: list[ReviewWarning]
    provenance: dict[str, Any]
    breadcrumbs: list[StatblockBreadcrumb]
    source_refs: list[SourceRef]
    retrieval: dict[str, Any]
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


def _drafts_dir(base: Path) -> Path:
    return base / "statblock_drafts"


def _is_promoted(record: StoredStatblockDraftRecord) -> bool:
    return record.artifact.corpus_status == "promotion_confirmed" and bool(
        record.corpus_relpath
    )


def _safe_corpus_file(*, root: Path, corpus_relpath: str) -> Path:
    rel = Path(corpus_relpath)
    if rel.is_absolute() or ".." in rel.parts:
        raise StatblockViewConflictError("statblock corpus path metadata is unsafe")
    corpus_root = (root / CORPUS_MARKDOWN_ROOT).resolve()
    path = (corpus_root / rel).resolve()
    try:
        path.relative_to(corpus_root)
    except ValueError as exc:
        raise StatblockViewConflictError("statblock corpus path metadata is unsafe") from exc
    return path


def _corpus_path_or_diagnostic(
    record: StoredStatblockDraftRecord, *, root: Path, diagnostics: list[str]
) -> Path | None:
    if not record.corpus_relpath:
        return None
    try:
        path = _safe_corpus_file(root=root, corpus_relpath=record.corpus_relpath)
    except StatblockViewConflictError:
        diagnostics.append(f"{record.artifact_id}: corpus path metadata is unsafe")
        return None
    if not path.is_file():
        diagnostics.append(f"{record.artifact_id}: corpus file is missing")
        return None
    return path


def _text_value(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _structured(record: StoredStatblockDraftRecord, *keys: str) -> str | None:
    statblock = record.artifact.structured_statblock or {}
    for key in keys:
        value = _text_value(statblock.get(key))
        if value:
            return value
    return None


def _primary_actions(record: StoredStatblockDraftRecord) -> list[str]:
    defaults = record.artifact.combat_defaults
    actions = list(defaults.primary_actions or [])
    if actions:
        return actions
    raw_actions = record.artifact.structured_statblock.get("actions")
    if isinstance(raw_actions, list):
        names: list[str] = []
        for item in raw_actions:
            if isinstance(item, dict):
                name = _text_value(item.get("name"))
                if name:
                    names.append(name)
            elif isinstance(item, str) and item.strip():
                names.append(item.strip())
        return names[:5]
    return []


def _list_item(
    record: StoredStatblockDraftRecord, *, root: Path, diagnostics: list[str]
) -> GeneratedStatblockListItem:
    _corpus_path_or_diagnostic(record, root=root, diagnostics=diagnostics)
    defaults = record.artifact.combat_defaults
    return GeneratedStatblockListItem(
        artifact_id=record.artifact_id,
        draft_id=record.artifact.draft_id,
        title=record.title,
        campaign_id=record.campaign_id,
        session=record.session,
        review_status=record.artifact.review_status,
        lifecycle_state=record.artifact.lifecycle_state,
        storage_status=record.artifact.storage_status,
        corpus_status=record.artifact.corpus_status,
        retrieval_status=record.retrieval_status,
        corpus_relpath=record.corpus_relpath or "",
        corpus_display_path=record.corpus_display_path or f"corpus/eldyrwild-markdown/{record.corpus_relpath}",
        corpus_written_at=record.corpus_written_at,
        retrieval_verified_at=record.retrieval_verified_at,
        armor_class=defaults.armor_class,
        hit_points=defaults.hit_points,
        challenge_rating=_structured(record, "challenge_rating", "challenge", "cr"),
        creature_type=_structured(record, "creature_type", "type"),
        primary_actions=_primary_actions(record),
        warning_count=len(record.artifact.warnings),
    )


def list_generated_statblocks(*, base: Path, root: Path) -> GeneratedStatblockListResponse:
    diagnostics: list[str] = []
    items: list[GeneratedStatblockListItem] = []
    drafts_dir = _drafts_dir(base)
    if not drafts_dir.is_dir():
        return GeneratedStatblockListResponse(statblocks=[], diagnostics=[])
    for path in sorted(drafts_dir.glob("*.json")):
        try:
            record = StoredStatblockDraftRecord.model_validate(load_json(path))
        except Exception:
            diagnostics.append(f"{path.name}: stored statblock draft could not be read")
            continue
        if not _is_promoted(record):
            continue
        items.append(_list_item(record, root=root, diagnostics=diagnostics))
    items.sort(key=lambda item: item.title.lower())
    items.sort(
        key=lambda item: item.corpus_written_at or "",
        reverse=True,
    )
    return GeneratedStatblockListResponse(statblocks=items, diagnostics=diagnostics)


def _require_viewable(record: StoredStatblockDraftRecord, *, root: Path) -> Path:
    if record.artifact.corpus_status != "promotion_confirmed":
        raise StatblockViewConflictError("generated statblock is not corpus-promoted")
    if not record.corpus_relpath or not record.corpus_display_path:
        raise StatblockViewConflictError("generated statblock corpus path metadata is missing")
    path = _safe_corpus_file(root=root, corpus_relpath=record.corpus_relpath)
    if not path.is_file():
        raise StatblockViewConflictError("generated statblock corpus file is missing")
    return path


def _retrieval_metadata(record: StoredStatblockDraftRecord) -> dict[str, Any]:
    return {
        "status": record.retrieval_status,
        "manifest_path": record.retrieval_manifest_path,
        "activated_at": record.retrieval_activated_at,
        "verified_at": record.retrieval_verified_at,
        "query": record.retrieval_query,
        "evidence_path": record.retrieval_evidence_path,
        "evidence_score": record.retrieval_evidence_score,
    }


def _future_actions() -> list[StatblockWorkbenchAction]:
    return [
        StatblockWorkbenchAction(
            action_id="add_to_combat",
            label="Add to current combat",
            enabled=False,
            disabled_reason="Disabled until PR112 combat integration.",
        ),
        StatblockWorkbenchAction(
            action_id="create_encounter_copy",
            label="Create encounter copy",
            enabled=False,
            disabled_reason="Future read/write encounter workflow.",
        ),
        StatblockWorkbenchAction(
            action_id="refresh_retrieval_verification",
            label="Refresh retrieval verification",
            enabled=False,
            disabled_reason="Use the Workbench retrieval flow for now.",
        ),
        StatblockWorkbenchAction(
            action_id="edit_statblock",
            label="Edit statblock",
            enabled=False,
            disabled_reason="Statblock View is read-only.",
        ),
    ]


def read_generated_statblock(
    *, base: Path, root: Path, artifact_id: str
) -> GeneratedStatblockDetailResponse:
    record = read_statblock_draft(base=base, artifact_id=artifact_id)
    path = _require_viewable(record, root=root)
    try:
        corpus_markdown = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise StatblockViewConflictError("generated statblock corpus file is not UTF-8 readable") from exc
    markdown_bytes = corpus_markdown.encode("utf-8")
    fingerprint = hashlib.sha256(markdown_bytes).hexdigest()[:32]
    artifact = record.artifact
    return GeneratedStatblockDetailResponse(
        artifact_id=record.artifact_id,
        draft_id=artifact.draft_id,
        title=record.title,
        stored_record=record,
        corpus_relpath=record.corpus_relpath or "",
        corpus_display_path=record.corpus_display_path or "",
        corpus_markdown=corpus_markdown,
        corpus_markdown_bytes=len(markdown_bytes),
        corpus_file_fingerprint=fingerprint,
        combat_defaults=artifact.combat_defaults,
        warnings=artifact.warnings,
        provenance=artifact.provenance.model_dump(mode="json"),
        breadcrumbs=artifact.breadcrumbs,
        source_refs=artifact.source_refs,
        retrieval=_retrieval_metadata(record),
        available_actions=_future_actions(),
        diagnostics=[
            "read-only Statblock View response",
            "no corpus write, retrieval activation, event append, job queue append, or combat mutation occurred",
        ],
    )
