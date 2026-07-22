"""Server-owned SourceArtifact registry for committed workspace revisions."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryError,
    get_workspace_document,
)
from src.live_play.live_store import load_json, write_json
from graph_memory.evidence.source_artifact import (
    GraphMemorySourceArtifact,
    build_worldbuilding_source_artifact_id,
    validate_source_artifact_scope,
)

DEFAULT_SOURCE_ARTIFACT_REGISTRY_REL = "out/registries/source_artifacts.json"
SOURCE_ARTIFACT_REGISTRY_SCHEMA = "dmb_source_artifact_registry_v1"


class SourceArtifactRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class SourceArtifactRegistryDocument(BaseModel):
    schema_version: str = SOURCE_ARTIFACT_REGISTRY_SCHEMA
    records: list[GraphMemorySourceArtifact] = Field(default_factory=list)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def source_artifacts_path(root: Path) -> Path:
    return root / DEFAULT_SOURCE_ARTIFACT_REGISTRY_REL


def _load(root: Path) -> SourceArtifactRegistryDocument:
    path = source_artifacts_path(root)
    if not path.is_file():
        return SourceArtifactRegistryDocument()
    return SourceArtifactRegistryDocument.model_validate(load_json(path))


def _save(root: Path, document: SourceArtifactRegistryDocument) -> None:
    path = source_artifacts_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, document.model_dump(mode="json"))


def get_source_artifact(root: Path, source_artifact_id: str) -> GraphMemorySourceArtifact:
    document = _load(root)
    for record in document.records:
        if record.source_artifact_id == source_artifact_id:
            return record
    raise SourceArtifactRegistryError(
        f"source artifact not found: {source_artifact_id}",
        status_code=404,
    )


def create_source_artifact_from_workspace_document(
    root: Path,
    *,
    document_id: str,
    expected_revision: int | None = None,
    markdown: str,
) -> GraphMemorySourceArtifact:
    """Create an immutable SourceArtifact from a committed worldbuilding workspace revision."""
    try:
        record = get_workspace_document(root, document_id)
    except WorkspaceDocumentRegistryError as exc:
        err = SourceArtifactRegistryError(str(exc), status_code=exc.status_code)
        raise err from exc

    if record.kind != "worldbuilding_source":
        raise SourceArtifactRegistryError(
            "only worldbuilding_source documents can create worldbuilding SourceArtifacts",
            status_code=422,
        )
    if record.status != "active":
        raise SourceArtifactRegistryError(
            "discarded workspace documents cannot create SourceArtifacts",
            status_code=409,
        )
    if record.content_status != "committed":
        raise SourceArtifactRegistryError(
            "workspace document must be committed before SourceArtifact creation",
            status_code=422,
        )
    if expected_revision is not None and record.revision != expected_revision:
        raise SourceArtifactRegistryError(
            f"revision mismatch: expected {expected_revision}, current {record.revision}",
            status_code=409,
        )
    if not record.target_relpath:
        raise SourceArtifactRegistryError(
            "workspace document has no target_relpath",
            status_code=422,
        )

    content = markdown if markdown.endswith("\n") else f"{markdown}\n"
    content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    source_artifact_id = build_worldbuilding_source_artifact_id(
        workspace_document_id=record.document_id,
        workspace_document_revision=record.revision,
        content_sha256=content_sha256,
    )

    document = _load(root)
    existing = next(
        (row for row in document.records if row.source_artifact_id == source_artifact_id),
        None,
    )
    if existing is not None:
        return existing

    now = _utc_now_iso()
    artifact = GraphMemorySourceArtifact(
        source_artifact_id=source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=record.campaign_id,
        session_id=None,
        uri=f"repo://{record.target_relpath}",
        content_sha256=content_sha256,
        artifact_kind="worldbuilding_markdown",
        document_class=record.document_class,
        authority_state=record.authority_state,
        visibility_state=record.visibility_state,
        world_id=record.campaign_id,
        workspace_document_id=record.document_id,
        workspace_document_revision=record.revision,
        lineage={
            "workspace_document_id": record.document_id,
            "workspace_document_revision": record.revision,
        },
        created_at=now,
        updated_at=now,
    )
    try:
        validate_source_artifact_scope(artifact)
    except ValueError as exc:
        raise SourceArtifactRegistryError(str(exc), status_code=422) from exc

    document.records.append(artifact)
    _save(root, document)
    return artifact
