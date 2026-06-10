from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.statblock_corpus_preview import (
    CORPUS_ROOT_DISPLAY,
    StatblockPromotionWarning,
    build_statblock_corpus_promotion_preview,
)
from apps.live_control_server.services.statblock_draft_store import (
    StoredStatblockDraftRecord,
    read_statblock_draft,
    update_statblock_draft_record,
)
from apps.live_control_server.services.statblock_workbench import StatblockWorkbenchAction
from src.agent.corpus_writer import write_corpus_file

SCHEMA_VERSION_PREPARE = "dmb_statblock_corpus_write_prepare_v1"
SCHEMA_VERSION_COMMIT = "dmb_statblock_corpus_write_commit_v1"


class StatblockCorpusWriteError(ValueError):
    status_code = 422


class PreviewTokenMismatchError(StatblockCorpusWriteError):
    pass


class CorpusWriterCommitError(StatblockCorpusWriteError):
    status_code = 409


class StatblockCorpusWritePrepareRequest(BaseModel):
    preview_token: str | None = None


class StatblockCorpusWritePrepareResponse(BaseModel):
    schema_version: Literal["dmb_statblock_corpus_write_prepare_v1"] = (
        SCHEMA_VERSION_PREPARE
    )
    artifact_id: str
    draft_id: str
    title: str
    preview_token: str
    proposed_corpus_relpath: str
    proposed_corpus_display_path: str
    writer_ok: bool
    writer_phase: str | None = None
    writer_confirm_token: str | None = None
    writer_diff: str | None = None
    new_size_bytes: int | None = None
    warnings: list[StatblockPromotionWarning] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)


class StatblockCorpusWriteCommitRequest(BaseModel):
    preview_token: str
    writer_confirm_token: str


class StatblockCorpusWriteCommitResponse(BaseModel):
    schema_version: Literal["dmb_statblock_corpus_write_commit_v1"] = (
        SCHEMA_VERSION_COMMIT
    )
    artifact_id: str
    draft_id: str
    title: str
    preview_token: str
    proposed_corpus_relpath: str
    proposed_corpus_display_path: str
    writer_ok: bool
    writer_phase: str | None = None
    bytes_written: int | None = None
    new_corpus_fingerprint: str | None = None
    stored_record: StoredStatblockDraftRecord
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)


def corpus_root() -> Path:
    return repo_root() / "corpus" / "eldyrwild-markdown"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_actions(*, prepared: bool, committed: bool = False) -> list[StatblockWorkbenchAction]:
    return [
        StatblockWorkbenchAction(
            action_id="confirm_corpus_write",
            label="Confirm corpus write",
            enabled=prepared and not committed,
            disabled_reason=None if prepared and not committed else "Prepare corpus write first.",
        ),
        StatblockWorkbenchAction(
            action_id="ingest_to_semantic_layer",
            label="Ingest to Semantic Knowledge Layer",
            disabled_reason="Disabled until a future ingestion/retrieval PR.",
        ),
        StatblockWorkbenchAction(
            action_id="add_to_combat",
            label="Add to combat",
            disabled_reason="Disabled until corpus-backed Statblock View/combat integration exists.",
        ),
    ]


def _require_preview_token(actual: str, expected: str | None) -> None:
    if expected is not None and expected != actual:
        raise PreviewTokenMismatchError("preview token mismatch; rebuild corpus preview")


def prepare_statblock_corpus_write(
    *,
    base: Path,
    packet: dict[str, Any],
    artifact_id: str,
    expected_preview_token: str | None = None,
) -> StatblockCorpusWritePrepareResponse:
    # Read first to preserve normal unsafe-id/not-found errors before preview build.
    read_statblock_draft(base=base, artifact_id=artifact_id)
    preview = build_statblock_corpus_promotion_preview(
        base=base,
        packet=packet,
        artifact_id=artifact_id,
        include_writer_allowlist_check=True,
    )
    _require_preview_token(preview.preview_token, expected_preview_token)

    writer = write_corpus_file(
        corpus_root(),
        path=preview.proposed_corpus_relpath,
        mode="create",
        content=preview.full_markdown,
        dry_run=True,
    )
    writer_ok = bool(writer.get("ok"))
    diagnostics = [
        "corpus writer dry-run only; no corpus file was written",
        "no stored draft mutation, Semantic Knowledge Layer ingestion, event append, job queue append, or combat mutation occurred",
    ]
    if not writer_ok:
        diagnostics.append(f"corpus writer refused prepare: {writer.get('error', 'unknown error')}")

    return StatblockCorpusWritePrepareResponse(
        artifact_id=preview.artifact_id,
        draft_id=preview.draft_id,
        title=preview.title,
        preview_token=preview.preview_token,
        proposed_corpus_relpath=preview.proposed_corpus_relpath,
        proposed_corpus_display_path=preview.proposed_corpus_display_path,
        writer_ok=writer_ok,
        writer_phase=writer.get("phase"),
        writer_confirm_token=writer.get("confirm_token") if writer_ok else None,
        writer_diff=writer.get("diff") if writer_ok else None,
        new_size_bytes=writer.get("new_size_bytes") if writer_ok else None,
        warnings=preview.warnings,
        diagnostics=diagnostics,
        available_actions=_write_actions(prepared=writer_ok),
    )


def commit_statblock_corpus_write(
    *,
    base: Path,
    packet: dict[str, Any],
    artifact_id: str,
    preview_token: str,
    writer_confirm_token: str,
) -> StatblockCorpusWriteCommitResponse:
    record = read_statblock_draft(base=base, artifact_id=artifact_id)
    preview = build_statblock_corpus_promotion_preview(
        base=base,
        packet=packet,
        artifact_id=artifact_id,
        include_writer_allowlist_check=True,
    )
    _require_preview_token(preview.preview_token, preview_token)

    writer = write_corpus_file(
        corpus_root(),
        path=preview.proposed_corpus_relpath,
        mode="create",
        content=preview.full_markdown,
        dry_run=False,
        confirm_token=writer_confirm_token,
    )
    if not writer.get("ok"):
        message = str(writer.get("error") or "corpus writer commit failed")
        if "stale confirm_token" in message:
            message = "stale_writer_confirm_token: prepare corpus write again"
        raise CorpusWriterCommitError(message)

    timestamp = _utc_now()
    promoted_artifact = record.artifact.model_copy(
        update={
            "lifecycle_state": "corpus_promoted",
            "storage_status": "stored_draft",
            "corpus_status": "promotion_confirmed",
            "updated_at": timestamp,
        }
    )
    updated_record = record.model_copy(
        update={
            "updated_at": timestamp,
            "corpus_relpath": preview.proposed_corpus_relpath,
            "corpus_display_path": f"{CORPUS_ROOT_DISPLAY}/{preview.proposed_corpus_relpath}",
            "corpus_written_at": timestamp,
            "corpus_preview_token": preview.preview_token,
            "artifact": promoted_artifact,
        }
    )
    update_statblock_draft_record(base=base, record=updated_record)

    return StatblockCorpusWriteCommitResponse(
        artifact_id=preview.artifact_id,
        draft_id=preview.draft_id,
        title=preview.title,
        preview_token=preview.preview_token,
        proposed_corpus_relpath=preview.proposed_corpus_relpath,
        proposed_corpus_display_path=preview.proposed_corpus_display_path,
        writer_ok=True,
        writer_phase=writer.get("phase"),
        bytes_written=writer.get("bytes_written"),
        new_corpus_fingerprint=writer.get("new_corpus_fingerprint") or None,
        stored_record=updated_record,
        diagnostics=[
            "corpus markdown file written with corpus writer confirm_token",
            "stored draft marked promotion_confirmed",
            "no Semantic Knowledge Layer ingestion, event append, job queue append, or combat mutation occurred",
        ],
        available_actions=_write_actions(prepared=False, committed=True),
    )
