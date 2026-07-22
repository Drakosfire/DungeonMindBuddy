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
    WorkspaceDocumentsListResponse,
    _UNSET,
    create_workspace_document,
    discard_workspace_document,
    get_workspace_document,
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
    records = list_workspace_documents(
        repo_root(),
        campaign_id=campaign_id,
        kind=kind,
        status=status,
    )
    return WorkspaceDocumentsListResponse(records=records).model_dump(mode="json")


@router.post("/workspace-documents", response_model=WorkspaceDocumentRecord)
def post_workspace_document(body: CreateWorkspaceDocumentRequest) -> dict[str, Any]:
    try:
        record = create_workspace_document(
            repo_root(),
            title=body.title,
            campaign_id=body.campaign_id,
            kind=body.kind,
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
