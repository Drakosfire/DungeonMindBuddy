"""Workspace document registry API for opaque /plan authoring documents."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.workspace_document_registry import (
    CreateWorkspaceDocumentRequest,
    UpdateWorkspaceDocumentMetadataRequest,
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryError,
    WorkspaceDocumentRevisionRequest,
    WorkspaceDocumentSnapshot,
    WorkspaceCommittedRevision,
    WorkspaceDocumentsListResponse,
    _UNSET,
    create_workspace_document,
    discard_workspace_document,
    get_committed_playable_revision,
    get_workspace_document,
    get_workspace_document_snapshot,
    list_workspace_documents,
    restore_workspace_document,
    update_workspace_document_metadata,
)

router = APIRouter(prefix="/api/live", tags=["workspace-documents"])


def _record_response(record: WorkspaceDocumentRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


@router.get("/workspace-documents", response_model=WorkspaceDocumentsListResponse)
def get_workspace_documents(
    campaign_id: Annotated[str | None, Query()] = None,
    kind: Annotated[Literal["plan", "runbook", "worldbuilding_source"] | None, Query()] = None,
    status: Annotated[Literal["active", "discarded"] | None, Query()] = "active",
) -> dict[str, Any]:
    try:
        records = list_workspace_documents(
            repo_root(),
            campaign_id=campaign_id,
            kind=kind,
            status=status,
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorkspaceDocumentsListResponse(records=records).model_dump(mode="json")


@router.post("/workspace-documents", response_model=WorkspaceDocumentRecord)
def post_workspace_document(body: CreateWorkspaceDocumentRequest) -> dict[str, Any]:
    try:
        record = create_workspace_document(
            repo_root(),
            title=body.title,
            campaign_id=body.campaign_id,
            kind=body.kind,
            world_id=body.world_id,
            target_session=body.target_session,
            target_relpath=body.target_relpath,
            source_domain=body.source_domain,
            document_class=body.document_class,
            authority_state=body.authority_state,
            visibility_state=body.visibility_state,
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.get("/workspace-documents/{document_id}", response_model=WorkspaceDocumentRecord)
def get_workspace_document_route(document_id: str) -> dict[str, Any]:
    try:
        record = get_workspace_document(repo_root(), document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.get(
    "/workspace-documents/{document_id}/snapshot",
    response_model=WorkspaceDocumentSnapshot,
)
def get_workspace_document_snapshot_route(document_id: str) -> dict[str, Any]:
    try:
        snapshot = get_workspace_document_snapshot(repo_root(), document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return snapshot.model_dump(mode="json")


@router.get(
    "/workspace-documents/{document_id}/committed-revision",
    response_model=WorkspaceCommittedRevision,
)
def get_workspace_document_current_committed_revision(document_id: str) -> dict[str, Any]:
    try:
        committed = get_committed_playable_revision(document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return committed.model_dump(mode="json")


@router.get(
    "/workspace-documents/{document_id}/committed-revision/{revision_n}",
    response_model=WorkspaceCommittedRevision,
)
def get_workspace_document_exact_committed_revision(
    document_id: str, revision_n: int
) -> dict[str, Any]:
    try:
        committed = get_committed_playable_revision(
            document_id, revision_n=revision_n
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return committed.model_dump(mode="json")


@router.patch("/workspace-documents/{document_id}", response_model=WorkspaceDocumentRecord)
def patch_workspace_document_metadata(
    document_id: str,
    body: UpdateWorkspaceDocumentMetadataRequest,
) -> dict[str, Any]:
    fields_set = body.model_fields_set
    try:
        record = update_workspace_document_metadata(
            repo_root(),
            document_id,
            title=body.title if "title" in fields_set else _UNSET,
            target_session=body.target_session if "target_session" in fields_set else _UNSET,
            target_relpath=body.target_relpath if "target_relpath" in fields_set else _UNSET,
            document_class=body.document_class if "document_class" in fields_set else _UNSET,
            authority_state=body.authority_state if "authority_state" in fields_set else _UNSET,
            visibility_state=body.visibility_state if "visibility_state" in fields_set else _UNSET,
            expected_revision=body.expected_revision,
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.post("/workspace-documents/{document_id}/discard", response_model=WorkspaceDocumentRecord)
def post_workspace_document_discard(
    document_id: str,
    body: WorkspaceDocumentRevisionRequest | None = None,
) -> dict[str, Any]:
    try:
        record = discard_workspace_document(
            repo_root(),
            document_id,
            expected_revision=None if body is None else body.expected_revision,
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.post("/workspace-documents/{document_id}/restore", response_model=WorkspaceDocumentRecord)
def post_workspace_document_restore(
    document_id: str,
    body: WorkspaceDocumentRevisionRequest | None = None,
) -> dict[str, Any]:
    try:
        record = restore_workspace_document(
            repo_root(),
            document_id,
            expected_revision=None if body is None else body.expected_revision,
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.post("/workspace-documents/{document_id}/source-artifact", response_model=dict)
def post_workspace_document_source_artifact(
    document_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create an immutable SourceArtifact from a committed workspace revision.

    Source bytes are read from the committed BLD-02 target. Optional
    ``expected_content_sha256`` is an assertion only.
    """
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        create_source_artifact_from_workspace_document,
    )

    payload = body or {}
    if "markdown" in payload:
        raise HTTPException(
            status_code=422,
            detail="markdown is not accepted; source bytes are server-resolved from the committed target",
        )
    expected_revision = payload.get("expected_revision")
    if expected_revision is not None and not isinstance(expected_revision, int):
        raise HTTPException(status_code=422, detail="expected_revision must be an int")
    expected_content_sha256 = payload.get("expected_content_sha256")
    if expected_content_sha256 is not None and not isinstance(expected_content_sha256, str):
        raise HTTPException(status_code=422, detail="expected_content_sha256 must be a string")
    try:
        artifact = create_source_artifact_from_workspace_document(
            repo_root(),
            document_id=document_id,
            expected_revision=expected_revision,
            expected_content_sha256=expected_content_sha256,
        )
    except SourceArtifactRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return artifact.model_dump(mode="json")
