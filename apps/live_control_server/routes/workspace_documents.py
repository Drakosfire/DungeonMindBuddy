"""Workspace document registry API for opaque /plan authoring documents."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import repo_root
from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import (
    NativeWorldSourceAdmissionError,
    NativeWorldSourceAdmissionStatus,
    admit_native_world_source,
    get_native_world_source_status as read_native_world_source_status,
)
from apps.live_control_server.services.workspace_document_registry import (
    CreateWorkspaceDocumentRequest,
    UpdateWorkspaceDocumentMetadataRequest,
    WorkspaceDocumentRecord,
    WorkspaceDocumentRecordAny,
    WorkspaceDocumentRegistryError,
    WorkspaceDocumentRevisionRequest,
    WorkspaceDocumentSnapshotAny,
    CreateWorldOwnedPlanRequestV2,
    WorldOwnedPlanRecordV2,
    WorldOwnedPlansResponseV2,
    CreateWorldOwnedRunbookRequestV2,
    WorldOwnedRunbookRecordV2,
    WorldOwnedRunbooksResponseV2,
    WorkspaceCommittedRevisionAny,
    WorkspaceDocumentsListResponse,
    _UNSET,
    create_workspace_document,
    discard_workspace_document,
    get_committed_playable_revision,
    get_workspace_document,
    get_workspace_document_snapshot,
    list_workspace_documents,
    list_world_owned_plans_v2,
    create_world_owned_plan_v2,
    create_world_owned_runbook_v2,
    get_world_owned_runbook_v2,
    get_world_owned_runbook_snapshot_v2,
    list_world_owned_runbooks_v2,
    restore_workspace_document,
    update_workspace_document_metadata,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWriteCommitResponse,
    TiptapMarkdownWriteError,
    TiptapMarkdownWritePrepareRequest,
    TiptapMarkdownWritePrepareResponse,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)

router = APIRouter(prefix="/api/live", tags=["workspace-documents"])


class NativeWorldSourceAdmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    expected_body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _record_response(record: WorkspaceDocumentRecordAny) -> dict[str, Any]:
    return record.model_dump(mode="json")


@router.get("/workspace-documents", response_model=WorkspaceDocumentsListResponse)
def get_workspace_documents(
    campaign_id: Annotated[str | None, Query()] = None,
    kind: Annotated[
        Literal["plan", "runbook", "worldbuilding_source"] | None, Query()
    ] = None,
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


@router.get(
    "/workspace-documents/world-plans", response_model=WorldOwnedPlansResponseV2
)
def get_world_owned_plans(
    world_id: Annotated[str, Query(min_length=1)],
    request: Request,
) -> dict[str, Any]:
    unsupported = sorted(set(request.query_params.keys()) - {"world_id"})
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail=f"World Plan inventory accepts only world_id; unsupported selectors: {', '.join(unsupported)}",
        )
    try:
        return list_world_owned_plans_v2(repo_root(), world_id=world_id).model_dump(
            mode="json"
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/workspace-documents/world-plans", response_model=WorldOwnedPlanRecordV2)
def post_world_owned_plan(body: CreateWorldOwnedPlanRequestV2) -> dict[str, Any]:
    try:
        record = create_world_owned_plan_v2(
            repo_root(), world_id=body.world_id, title=body.title
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@router.get(
    "/workspace-documents/world-runbooks",
    response_model=WorldOwnedRunbooksResponseV2,
)
def get_world_owned_runbooks(
    world_id: Annotated[str, Query(min_length=1)],
    request: Request,
) -> dict[str, Any]:
    unsupported = sorted(set(request.query_params.keys()) - {"world_id"})
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail=f"World Runbook inventory accepts only world_id; unsupported selectors: {', '.join(unsupported)}",
        )
    try:
        return list_world_owned_runbooks_v2(
            repo_root(), world_id=world_id
        ).model_dump(mode="json")
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post(
    "/workspace-documents/world-runbooks",
    response_model=WorldOwnedRunbookRecordV2,
)
def post_world_owned_runbook(
    body: CreateWorldOwnedRunbookRequestV2,
) -> dict[str, Any]:
    try:
        record = create_world_owned_runbook_v2(
            repo_root(), world_id=body.world_id, title=body.title
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@router.get(
    "/workspace-documents/world-runbooks/{document_id}",
    response_model=WorldOwnedRunbookRecordV2,
)
def get_world_owned_runbook(
    document_id: str,
    world_id: Annotated[str, Query(min_length=1)],
    request: Request,
) -> dict[str, Any]:
    unsupported = sorted(set(request.query_params.keys()) - {"world_id"})
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail=f"World Runbook read accepts only world_id; unsupported selectors: {', '.join(unsupported)}",
        )
    try:
        record = get_world_owned_runbook_v2(
            repo_root(), world_id=world_id, document_id=document_id
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@router.get(
    "/workspace-documents/world-runbooks/{document_id}/snapshot",
    response_model=WorkspaceDocumentSnapshotAny,
)
def get_world_owned_runbook_snapshot(
    document_id: str,
    world_id: Annotated[str, Query(min_length=1)],
    request: Request,
) -> dict[str, Any]:
    unsupported = sorted(set(request.query_params.keys()) - {"world_id"})
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail=f"World Runbook snapshot accepts only world_id; unsupported selectors: {', '.join(unsupported)}",
        )
    try:
        snapshot = get_world_owned_runbook_snapshot_v2(
            repo_root(), world_id=world_id, document_id=document_id
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return snapshot.model_dump(mode="json")


@router.post(
    "/workspace-documents/world-runbooks/{document_id}/tiptap/prepare",
    response_model=TiptapMarkdownWritePrepareResponse,
)
def post_world_owned_runbook_tiptap_prepare(
    document_id: str,
    world_id: Annotated[str, Query(min_length=1)],
    body: TiptapMarkdownWritePrepareRequest,
) -> dict[str, Any]:
    if (
        body.document_id != document_id
        or body.schema_version != "dmb_tiptap_markdown_write_prepare_v2"
        or body.scope_mode != "world"
        or body.world_id != world_id
    ):
        raise HTTPException(
            status_code=422,
            detail="World Runbook prepare requires matching V2 World scope and document identity",
        )
    try:
        get_world_owned_runbook_v2(
            repo_root(), world_id=world_id, document_id=document_id
        )
        response = prepare_tiptap_markdown_write(root=repo_root(), request=body)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except TiptapMarkdownWriteError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.post(
    "/workspace-documents/world-runbooks/{document_id}/tiptap/commit",
    response_model=TiptapMarkdownWriteCommitResponse,
)
def post_world_owned_runbook_tiptap_commit(
    document_id: str,
    world_id: Annotated[str, Query(min_length=1)],
    body: TiptapMarkdownWriteCommitRequest,
) -> dict[str, Any]:
    if (
        body.document_id != document_id
        or body.schema_version != "dmb_tiptap_markdown_write_commit_v2"
        or body.scope_mode != "world"
        or body.world_id != world_id
    ):
        raise HTTPException(
            status_code=422,
            detail="World Runbook commit requires matching V2 World scope and document identity",
        )
    try:
        get_world_owned_runbook_v2(
            repo_root(), world_id=world_id, document_id=document_id
        )
        response = commit_tiptap_markdown_write(root=repo_root(), request=body)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except TiptapMarkdownWriteError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.get(
    "/workspace-documents/world-runbooks/{document_id}/committed-revision",
    response_model=WorkspaceCommittedRevisionAny,
)
def get_world_owned_runbook_current_revision(
    document_id: str,
    world_id: Annotated[str, Query(min_length=1)],
    request: Request,
) -> dict[str, Any]:
    unsupported = sorted(set(request.query_params.keys()) - {"world_id"})
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail=f"World Runbook revision read accepts only world_id; unsupported selectors: {', '.join(unsupported)}",
        )
    try:
        get_world_owned_runbook_v2(
            repo_root(), world_id=world_id, document_id=document_id
        )
        committed = get_committed_playable_revision(
            document_id, expected_world_id=world_id, kind="runbook"
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return committed.model_dump(mode="json")


@router.get(
    "/workspace-documents/world-runbooks/{document_id}/committed-revision/{revision_n}",
    response_model=WorkspaceCommittedRevisionAny,
)
def get_world_owned_runbook_exact_revision(
    document_id: str,
    revision_n: int,
    world_id: Annotated[str, Query(min_length=1)],
    expected_sha256: Annotated[
        str, Query(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    ],
    request: Request,
) -> dict[str, Any]:
    unsupported = sorted(
        set(request.query_params.keys()) - {"world_id", "expected_sha256"}
    )
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail=f"World Runbook revision read accepts only world_id and expected_sha256; unsupported selectors: {', '.join(unsupported)}",
        )
    try:
        get_world_owned_runbook_v2(
            repo_root(), world_id=world_id, document_id=document_id
        )
        committed = get_committed_playable_revision(
            document_id,
            revision_n=revision_n,
            expected_sha256=expected_sha256,
            expected_world_id=world_id,
            kind="runbook",
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return committed.model_dump(mode="json")


def _require_campaign_workspace_document(document_id: str) -> None:
    try:
        record = get_workspace_document(repo_root(), document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if isinstance(record, WorldOwnedRunbookRecordV2):
        raise HTTPException(
            status_code=404,
            detail="World-owned Runbooks require the World-scoped V2 route",
        )


@router.get(
    "/workspace-documents/{document_id}", response_model=WorkspaceDocumentRecordAny
)
def get_workspace_document_route(document_id: str) -> dict[str, Any]:
    try:
        record = get_workspace_document(repo_root(), document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if isinstance(record, WorldOwnedRunbookRecordV2):
        raise HTTPException(
            status_code=404,
            detail="World-owned Runbooks require the World-scoped V2 route",
        )
    return _record_response(record)


@router.get(
    "/workspace-documents/{document_id}/snapshot",
    response_model=WorkspaceDocumentSnapshotAny,
)
def get_workspace_document_snapshot_route(document_id: str) -> dict[str, Any]:
    try:
        snapshot = get_workspace_document_snapshot(repo_root(), document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if isinstance(snapshot.record, WorldOwnedRunbookRecordV2):
        raise HTTPException(
            status_code=404,
            detail="World-owned Runbooks require the World-scoped V2 route",
        )
    return snapshot.model_dump(mode="json")


@router.get(
    "/workspace-documents/{document_id}/committed-revision",
    response_model=WorkspaceCommittedRevisionAny,
)
def get_workspace_document_current_committed_revision(
    document_id: str,
) -> dict[str, Any]:
    try:
        committed = get_committed_playable_revision(document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return committed.model_dump(mode="json")


@router.get(
    "/workspace-documents/{document_id}/committed-revision/{revision_n}",
    response_model=WorkspaceCommittedRevisionAny,
)
def get_workspace_document_exact_committed_revision(
    document_id: str, revision_n: int
) -> dict[str, Any]:
    try:
        committed = get_committed_playable_revision(document_id, revision_n=revision_n)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return committed.model_dump(mode="json")


@router.patch(
    "/workspace-documents/{document_id}", response_model=WorkspaceDocumentRecordAny
)
def patch_workspace_document_metadata(
    document_id: str,
    body: UpdateWorkspaceDocumentMetadataRequest,
) -> dict[str, Any]:
    _require_campaign_workspace_document(document_id)
    fields_set = body.model_fields_set
    try:
        record = update_workspace_document_metadata(
            repo_root(),
            document_id,
            title=body.title if "title" in fields_set else _UNSET,
            target_session=body.target_session
            if "target_session" in fields_set
            else _UNSET,
            target_relpath=body.target_relpath
            if "target_relpath" in fields_set
            else _UNSET,
            document_class=body.document_class
            if "document_class" in fields_set
            else _UNSET,
            authority_state=body.authority_state
            if "authority_state" in fields_set
            else _UNSET,
            visibility_state=body.visibility_state
            if "visibility_state" in fields_set
            else _UNSET,
            expected_revision=body.expected_revision,
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.post(
    "/workspace-documents/{document_id}/discard", response_model=WorkspaceDocumentRecordAny
)
def post_workspace_document_discard(
    document_id: str,
    body: WorkspaceDocumentRevisionRequest | None = None,
) -> dict[str, Any]:
    _require_campaign_workspace_document(document_id)
    try:
        record = discard_workspace_document(
            repo_root(),
            document_id,
            expected_revision=None if body is None else body.expected_revision,
        )
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.post(
    "/workspace-documents/{document_id}/restore", response_model=WorkspaceDocumentRecordAny
)
def post_workspace_document_restore(
    document_id: str,
    body: WorkspaceDocumentRevisionRequest | None = None,
) -> dict[str, Any]:
    _require_campaign_workspace_document(document_id)
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
    if expected_content_sha256 is not None and not isinstance(
        expected_content_sha256, str
    ):
        raise HTTPException(
            status_code=422, detail="expected_content_sha256 must be a string"
        )
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


@router.get(
    "/workspace-documents/{document_id}/native-world-source",
    response_model=NativeWorldSourceAdmissionStatus,
)
def get_native_world_source_status(
    document_id: str,
    expected_revision: Annotated[int | None, Query(ge=1)] = None,
) -> dict[str, Any]:
    try:
        return read_native_world_source_status(
            repo_root(), document_id, expected_revision=expected_revision
        ).model_dump(mode="json")
    except NativeWorldSourceAdmissionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.post(
    "/workspace-documents/{document_id}/native-world-source",
    response_model=NativeWorldSourceAdmissionStatus,
)
def post_native_world_source_admission(
    document_id: str,
    body: NativeWorldSourceAdmissionRequest,
) -> dict[str, Any]:
    try:
        return admit_native_world_source(
            repo_root(),
            document_id,
            expected_revision=body.expected_revision,
            expected_body_sha256=body.expected_body_sha256,
        ).model_dump(mode="json")
    except NativeWorldSourceAdmissionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
