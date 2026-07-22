"""File-backed opaque workspace document registry for /plan authoring."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    registry_token,
    workspace_document_mutation_lock,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_REGISTRY_REL = "out/registries/workspace_documents.json"
REGISTRY_SCHEMA = "dmb_workspace_document_registry_v1"
RECORD_SCHEMA = "dmb_workspace_document_record_v1"

_UNSET: Any = object()


class WorkspaceDocumentRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class WorkspaceDocumentRecord(BaseModel):
    schema_version: Literal["dmb_workspace_document_record_v1"] = RECORD_SCHEMA
    document_id: str
    title: str
    campaign_id: str
    target_session: int | None = None
    kind: Literal["plan", "runbook", "worldbuilding_source"]
    target_relpath: str | None = None
    status: Literal["active", "discarded"] = "active"
    content_status: Literal["draft", "committed"] = "draft"
    revision: int = 1
    created_at: str
    updated_at: str
    # Worldbuilding-source metadata (null for plan/runbook).
    source_domain: Literal["worldbuilding"] | None = None
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None
    visibility_state: Literal["internal", "player_safe"] | None = None


class WorkspaceDocumentRegistryDocument(BaseModel):
    schema_version: Literal["dmb_workspace_document_registry_v1"] = REGISTRY_SCHEMA
    records: list[WorkspaceDocumentRecord] = Field(default_factory=list)


class WorkspaceDocumentsListResponse(BaseModel):
    schema_version: Literal["dmb_workspace_document_registry_v1"] = REGISTRY_SCHEMA
    records: list[WorkspaceDocumentRecord] = Field(default_factory=list)


class CreateWorkspaceDocumentRequest(BaseModel):
    title: str
    campaign_id: str
    kind: Literal["plan", "runbook", "worldbuilding_source"]
    target_session: int | None = None
    target_relpath: str | None = None
    source_domain: Literal["worldbuilding"] | None = None
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None
    visibility_state: Literal["internal", "player_safe"] | None = None


class UpdateWorkspaceDocumentMetadataRequest(BaseModel):
    title: str | None = None
    target_session: int | None = None
    target_relpath: str | None = None
    expected_revision: int | None = None
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None
    visibility_state: Literal["internal", "player_safe"] | None = None


class WorkspaceDocumentRevisionRequest(BaseModel):
    expected_revision: int | None = None


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def workspace_documents_path(root: Path) -> Path:
    return root / DEFAULT_REGISTRY_REL


def _validate_document_id(document_id: str) -> str:
    cleaned = document_id.strip()
    try:
        uuid.UUID(cleaned)
    except ValueError as exc:
        raise WorkspaceDocumentRegistryError(
            "invalid document_id: must be a UUID",
            status_code=422,
        ) from exc
    return cleaned


def _validate_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise WorkspaceDocumentRegistryError("title is required", status_code=422)
    return cleaned


def _load_unlocked(root: Path) -> tuple[WorkspaceDocumentRegistryDocument, str]:
    path = workspace_documents_path(root)
    token = registry_token(path)
    if not path.is_file():
        return WorkspaceDocumentRegistryDocument(), token
    try:
        document = WorkspaceDocumentRegistryDocument.model_validate(load_json(path))
    except (TypeError, ValueError) as exc:
        raise WorkspaceDocumentRegistryError(
            f"malformed workspace document registry: {exc}",
            status_code=500,
        ) from exc
    return document, token


def _load_registry_document(root: Path) -> WorkspaceDocumentRegistryDocument:
    document, _token = _load_unlocked(root)
    return document


def _save_cas(
    root: Path,
    document: WorkspaceDocumentRegistryDocument,
    *,
    expected_token: str,
) -> Path:
    path = workspace_documents_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = registry_token(path)
    if current != expected_token:
        raise WorkspaceDocumentRegistryError(
            "workspace document registry changed concurrently",
            status_code=409,
        )
    try:
        write_json(path, document.model_dump(mode="json"))
    except (OSError, TypeError, ValueError) as exc:
        raise WorkspaceDocumentRegistryError(
            f"failed to persist workspace document registry: {exc}",
            status_code=500,
        ) from exc
    return path


def _replace_record(
    document: WorkspaceDocumentRegistryDocument,
    updated: WorkspaceDocumentRecord,
) -> None:
    document.records = [
        updated if r.document_id == updated.document_id else r for r in document.records
    ]


def load_workspace_document_under_registry_lock(
    root: Path,
    document_id: str,
) -> WorkspaceDocumentRecord:
    """Load one record under the shared registry-file lock.

    Lock order: callers performing an isolated snapshot or mutation must hold
    ``workspace_document_mutation_lock(document_id)`` first, then this acquires
    the registry lock.
    """
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, _token = _load_unlocked(root)
        record = _find_record(document, document_id)
        if record is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        return record


def _find_record(
    document: WorkspaceDocumentRegistryDocument, document_id: str
) -> WorkspaceDocumentRecord | None:
    cleaned = _validate_document_id(document_id)
    return next((r for r in document.records if r.document_id == cleaned), None)


def _check_expected_revision(
    record: WorkspaceDocumentRecord, expected_revision: int | None
) -> None:
    if expected_revision is not None and record.revision != expected_revision:
        raise WorkspaceDocumentRegistryError(
            f"revision mismatch: expected {expected_revision}, current {record.revision}",
            status_code=409,
        )


def list_workspace_documents(
    root: Path,
    *,
    campaign_id: str | None = None,
    kind: Literal["plan", "runbook", "worldbuilding_source"] | None = None,
    status: Literal["active", "discarded"] | None = "active",
) -> list[WorkspaceDocumentRecord]:
    records = list(_load_registry_document(root).records)
    if status is not None:
        records = [r for r in records if r.status == status]
    if campaign_id is not None:
        records = [r for r in records if r.campaign_id == campaign_id]
    if kind is not None:
        records = [r for r in records if r.kind == kind]
    records.sort(key=lambda row: row.updated_at, reverse=True)
    return records


def _worldbuilding_target_relpath(document_id: str) -> str:
    return f"out/workspace/worldbuilding/{document_id}.md"


def _validate_worldbuilding_metadata(
    *,
    source_domain: Literal["worldbuilding"] | None,
    document_class: str | None,
    authority_state: Literal["draft", "reviewed", "canonical"] | None,
    visibility_state: Literal["internal", "player_safe"] | None,
) -> dict[str, Any]:
    if source_domain != "worldbuilding":
        raise WorkspaceDocumentRegistryError(
            "worldbuilding_source requires source_domain='worldbuilding'",
            status_code=422,
        )
    cleaned_class = (document_class or "").strip()
    if not cleaned_class:
        raise WorkspaceDocumentRegistryError(
            "worldbuilding_source requires document_class",
            status_code=422,
        )
    if authority_state is None:
        raise WorkspaceDocumentRegistryError(
            "worldbuilding_source requires authority_state",
            status_code=422,
        )
    if visibility_state is None:
        raise WorkspaceDocumentRegistryError(
            "worldbuilding_source requires visibility_state",
            status_code=422,
        )
    return {
        "source_domain": source_domain,
        "document_class": cleaned_class,
        "authority_state": authority_state,
        "visibility_state": visibility_state,
    }


def create_workspace_document(
    root: Path,
    *,
    title: str,
    campaign_id: str,
    kind: Literal["plan", "runbook", "worldbuilding_source"],
    target_session: int | None = None,
    target_relpath: str | None = None,
    source_domain: Literal["worldbuilding"] | None = None,
    document_class: str | None = None,
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None,
    visibility_state: Literal["internal", "player_safe"] | None = None,
) -> WorkspaceDocumentRecord:
    cleaned_title = _validate_title(title)
    cleaned_campaign = campaign_id.strip()
    if not cleaned_campaign:
        raise WorkspaceDocumentRegistryError("campaign_id is required", status_code=422)

    document_id = str(uuid.uuid4())
    worldbuilding_fields: dict[str, Any] = {
        "source_domain": None,
        "document_class": None,
        "authority_state": None,
        "visibility_state": None,
    }
    resolved_target = target_relpath

    if kind == "worldbuilding_source":
        if target_relpath is not None:
            raise WorkspaceDocumentRegistryError(
                "target_relpath is registry-owned for worldbuilding_source",
                status_code=422,
            )
        worldbuilding_fields = _validate_worldbuilding_metadata(
            source_domain=source_domain,
            document_class=document_class,
            authority_state=authority_state,
            visibility_state=visibility_state,
        )
        resolved_target = _worldbuilding_target_relpath(document_id)
    else:
        if source_domain is not None or document_class is not None or authority_state is not None or visibility_state is not None:
            raise WorkspaceDocumentRegistryError(
                "worldbuilding metadata is only valid for kind=worldbuilding_source",
                status_code=422,
            )

    now = _utc_now_iso()
    record = WorkspaceDocumentRecord(
        document_id=document_id,
        title=cleaned_title,
        campaign_id=cleaned_campaign,
        target_session=target_session,
        kind=kind,
        target_relpath=resolved_target,
        created_at=now,
        updated_at=now,
        **worldbuilding_fields,
    )
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        document.records.append(record)
        _save_cas(root, document, expected_token=token)
    return record


def get_workspace_document(root: Path, document_id: str) -> WorkspaceDocumentRecord:
    document = _load_registry_document(root)
    record = _find_record(document, document_id)
    if record is None:
        raise WorkspaceDocumentRegistryError(
            f"workspace document not found: {_validate_document_id(document_id)}",
            status_code=404,
        )
    return record


def update_workspace_document_metadata(
    root: Path,
    document_id: str,
    *,
    title: str | object = _UNSET,
    target_session: int | None | object = _UNSET,
    target_relpath: str | None | object = _UNSET,
    document_class: str | None | object = _UNSET,
    authority_state: Literal["draft", "reviewed", "canonical"] | None | object = _UNSET,
    visibility_state: Literal["internal", "player_safe"] | None | object = _UNSET,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    with workspace_document_mutation_lock(root, document_id):
        return _update_workspace_document_metadata_unlocked(
            root,
            document_id,
            title=title,
            target_session=target_session,
            target_relpath=target_relpath,
            document_class=document_class,
            authority_state=authority_state,
            visibility_state=visibility_state,
            expected_revision=expected_revision,
        )


def _update_workspace_document_metadata_unlocked(
    root: Path,
    document_id: str,
    *,
    title: str | object = _UNSET,
    target_session: int | None | object = _UNSET,
    target_relpath: str | None | object = _UNSET,
    document_class: str | None | object = _UNSET,
    authority_state: Literal["draft", "reviewed", "canonical"] | None | object = _UNSET,
    visibility_state: Literal["internal", "player_safe"] | None | object = _UNSET,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = _find_record(document, document_id)
        if existing is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        _check_expected_revision(existing, expected_revision)

        updates: dict[str, Any] = {}
        if title is not _UNSET:
            updates["title"] = _validate_title(str(title))
        if target_session is not _UNSET:
            updates["target_session"] = target_session
        if target_relpath is not _UNSET:
            if existing.kind == "worldbuilding_source":
                raise WorkspaceDocumentRegistryError(
                    "target_relpath is registry-owned for worldbuilding_source",
                    status_code=422,
                )
            updates["target_relpath"] = target_relpath
        if document_class is not _UNSET:
            if existing.kind != "worldbuilding_source":
                raise WorkspaceDocumentRegistryError(
                    "document_class is only valid for worldbuilding_source",
                    status_code=422,
                )
            cleaned_class = str(document_class or "").strip()
            if not cleaned_class:
                raise WorkspaceDocumentRegistryError(
                    "document_class must be non-empty",
                    status_code=422,
                )
            updates["document_class"] = cleaned_class
        if authority_state is not _UNSET:
            if existing.kind != "worldbuilding_source":
                raise WorkspaceDocumentRegistryError(
                    "authority_state is only valid for worldbuilding_source",
                    status_code=422,
                )
            if authority_state is None:
                raise WorkspaceDocumentRegistryError(
                    "authority_state is required for worldbuilding_source",
                    status_code=422,
                )
            updates["authority_state"] = authority_state
        if visibility_state is not _UNSET:
            if existing.kind != "worldbuilding_source":
                raise WorkspaceDocumentRegistryError(
                    "visibility_state is only valid for worldbuilding_source",
                    status_code=422,
                )
            if visibility_state is None:
                raise WorkspaceDocumentRegistryError(
                    "visibility_state is required for worldbuilding_source",
                    status_code=422,
                )
            updates["visibility_state"] = visibility_state
        if not updates:
            raise WorkspaceDocumentRegistryError(
                "at least one metadata field is required",
                status_code=422,
            )

        updated = existing.model_copy(
            update={
                **updates,
                "revision": existing.revision + 1,
                "updated_at": _utc_now_iso(),
            }
        )
        _replace_record(document, updated)
        _save_cas(root, document, expected_token=token)
        return updated


def discard_workspace_document(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    with workspace_document_mutation_lock(root, document_id):
        return _set_workspace_document_status_unlocked(
            root,
            document_id,
            status="discarded",
            expected_revision=expected_revision,
        )


def restore_workspace_document(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    with workspace_document_mutation_lock(root, document_id):
        return _set_workspace_document_status_unlocked(
            root,
            document_id,
            status="active",
            expected_revision=expected_revision,
        )


def mark_workspace_document_committed_unlocked(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    """Mark committed without acquiring the per-document mutation lock.

    Callers that already hold ``workspace_document_mutation_lock`` (Markdown commit)
    must use this form to avoid deadlock. Still acquires the registry-file lock and CAS.
    Lock order: document lock (caller) → registry lock (here).
    """
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = _find_record(document, document_id)
        if existing is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        _check_expected_revision(existing, expected_revision)

        updated = existing.model_copy(
            update={
                "content_status": "committed",
                "revision": existing.revision + 1,
                "updated_at": _utc_now_iso(),
            }
        )
        _replace_record(document, updated)
        _save_cas(root, document, expected_token=token)
        return updated


def mark_workspace_document_committed(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    with workspace_document_mutation_lock(root, document_id):
        return mark_workspace_document_committed_unlocked(
            root,
            document_id,
            expected_revision=expected_revision,
        )


def _set_workspace_document_status_unlocked(
    root: Path,
    document_id: str,
    *,
    status: Literal["active", "discarded"],
    expected_revision: int | None,
) -> WorkspaceDocumentRecord:
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = _find_record(document, document_id)
        if existing is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        _check_expected_revision(existing, expected_revision)

        updated = existing.model_copy(
            update={
                "status": status,
                "revision": existing.revision + 1,
                "updated_at": _utc_now_iso(),
            }
        )
        _replace_record(document, updated)
        _save_cas(root, document, expected_token=token)
        return updated
