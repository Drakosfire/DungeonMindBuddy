"""File-backed opaque workspace document registry for /plan authoring."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

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
    kind: Literal["plan", "runbook"]
    target_relpath: str | None = None
    status: Literal["active", "discarded"] = "active"
    content_status: Literal["draft", "committed"] = "draft"
    revision: int = 1
    created_at: str
    updated_at: str


class WorkspaceDocumentRegistryDocument(BaseModel):
    schema_version: Literal["dmb_workspace_document_registry_v1"] = REGISTRY_SCHEMA
    records: list[WorkspaceDocumentRecord] = Field(default_factory=list)


class WorkspaceDocumentsListResponse(BaseModel):
    schema_version: Literal["dmb_workspace_document_registry_v1"] = REGISTRY_SCHEMA
    records: list[WorkspaceDocumentRecord] = Field(default_factory=list)


class CreateWorkspaceDocumentRequest(BaseModel):
    title: str
    campaign_id: str
    kind: Literal["plan", "runbook"]
    target_session: int | None = None
    target_relpath: str | None = None


class UpdateWorkspaceDocumentMetadataRequest(BaseModel):
    title: str | None = None
    target_session: int | None = None
    target_relpath: str | None = None
    expected_revision: int | None = None


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


def _load_registry_document(root: Path) -> WorkspaceDocumentRegistryDocument:
    path = workspace_documents_path(root)
    if not path.is_file():
        return WorkspaceDocumentRegistryDocument()
    payload = load_json(path)
    return WorkspaceDocumentRegistryDocument.model_validate(payload)


def _save_registry_document(root: Path, document: WorkspaceDocumentRegistryDocument) -> Path:
    path = workspace_documents_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, document.model_dump(mode="json"))
    return path


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
    kind: Literal["plan", "runbook"] | None = None,
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


def create_workspace_document(
    root: Path,
    *,
    title: str,
    campaign_id: str,
    kind: Literal["plan", "runbook"],
    target_session: int | None = None,
    target_relpath: str | None = None,
) -> WorkspaceDocumentRecord:
    cleaned_title = _validate_title(title)
    cleaned_campaign = campaign_id.strip()
    if not cleaned_campaign:
        raise WorkspaceDocumentRegistryError("campaign_id is required", status_code=422)

    document = _load_registry_document(root)
    now = _utc_now_iso()
    record = WorkspaceDocumentRecord(
        document_id=str(uuid.uuid4()),
        title=cleaned_title,
        campaign_id=cleaned_campaign,
        target_session=target_session,
        kind=kind,
        target_relpath=target_relpath,
        created_at=now,
        updated_at=now,
    )
    document.records.append(record)
    _save_registry_document(root, document)
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
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    document = _load_registry_document(root)
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
        updates["target_relpath"] = target_relpath
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
    document.records = [
        updated if r.document_id == updated.document_id else r for r in document.records
    ]
    _save_registry_document(root, document)
    return updated


def discard_workspace_document(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    return _set_workspace_document_status(
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
    return _set_workspace_document_status(
        root,
        document_id,
        status="active",
        expected_revision=expected_revision,
    )


def mark_workspace_document_committed(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    document = _load_registry_document(root)
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
    document.records = [
        updated if r.document_id == updated.document_id else r for r in document.records
    ]
    _save_registry_document(root, document)
    return updated


def _set_workspace_document_status(
    root: Path,
    document_id: str,
    *,
    status: Literal["active", "discarded"],
    expected_revision: int | None,
) -> WorkspaceDocumentRecord:
    document = _load_registry_document(root)
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
    document.records = [
        updated if r.document_id == updated.document_id else r for r in document.records
    ]
    _save_registry_document(root, document)
    return updated
