"""Graph object authoring prepare/commit API routes."""

from __future__ import annotations

from typing import Any
from functools import partial
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.live_control_server.services.graph_document_relationship import (
    DocumentRelationshipRequest, relationship_request, prepare_reviewed_native_relationship,
    confirm_native_relationship,
)
from apps.live_control_server.config import repo_root
from dungeonmind.domain.errors import DungeonMindError
from apps.live_control_server.services.native_graph_inspection import InspectionUnavailable
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError
from apps.live_control_server.services.workspace_document_registry import WorkspaceDocumentRegistryError
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError

from apps.live_control_server.services.graph_object_authoring_commit import (
    commit_graph_object_authoring_write,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringCommitResponse,
    GraphObjectAuthoringError,
    GraphObjectAuthoringPrepareRequest,
    GraphObjectAuthoringPrepareResponse,
    prepare_graph_object_authoring_write,
    graph_review_supported_object_kinds,
)

from apps.live_control_server.services.hosted_native_graph_access import native_graph_explorer_dependency
from apps.live_control_server.models.native_manual_knowledge import (
    ManualContextRequest, ManualPrepareRequest, ManualConfirmRequest,
)

router = APIRouter(prefix="/api/live/graph-authoring", tags=["graph-authoring"])

_STORE_RETIRED = {
    "code": "graph_authoring_store_retired",
    "message": (
        "Graph authoring merge-reconciliation file materialization is retired. "
        "Use Graph Review prepare/commit on DungeonMind World Graph authority."
    ),
}


@router.get("/object-kinds")
def get_graph_object_authoring_kinds(request: Request = None, world_id: str | None = None) -> dict[str, Any]:
    from apps.live_control_server.services.hosted_native_graph_access import require_hosted_plan_world_context

    require_hosted_plan_world_context(request, world_id)
    return {"objectKinds": graph_review_supported_object_kinds()}


def _relationship_principal(request: Request, world_id: str):
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    return conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)


@router.post("/document-relationship/request")
def post_document_relationship_request(
    request: DocumentRelationshipRequest,
    request_context: Request,
) -> dict[str, Any]:
    principal = _relationship_principal(request_context, request.world_id)
    try:
        result = relationship_request(repo_root(), request, principal).model_dump(mode="json", by_alias=True)
        if principal.auth_method == "hosted_owner":
            _relationship_principal(request_context, request.world_id)
        return result
    except (InspectionUnavailable, DungeonMindError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": getattr(exc, "code", "native_inspection_unavailable"),
                    "message": "Current World identities are unavailable. Refresh and try again."},
        ) from exc
    except (GraphObjectAuthoringError, SourceArtifactRegistryError, WorkspaceDocumentRegistryError, WorldGraphProjectionServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": getattr(exc,"code","relationship_source_unavailable"), "message": str(exc)}) from exc


class NativeRelationshipPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review: DocumentRelationshipRequest
    operation_id: UUID


class NativeRelationshipConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review: DocumentRelationshipRequest
    prepared: dict[str, Any]
    confirm_token: str


@router.post("/document-relationship/native-prepare")
def post_native_relationship_prepare(
    body: NativeRelationshipPrepareRequest, request: Request,
):
    principal = _relationship_principal(request, body.review.world_id)
    try:
        result = prepare_reviewed_native_relationship(
            repo_root(), body.review, principal,
            operation_id=f"dmb-build-relationship:v1:{body.operation_id}",
        )
        if principal.auth_method == "hosted_owner":
            _relationship_principal(request, body.review.world_id)
        return result
    except (GraphObjectAuthoringError, DungeonMindError, ValueError) as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 409),
            detail={"code": getattr(exc, "code", "native_relationship_prepare_failed")},
        ) from exc


@router.post("/document-relationship/native-confirm")
def post_native_relationship_confirm(
    body: NativeRelationshipConfirmRequest, request: Request,
):
    principal = _relationship_principal(request, body.review.world_id)
    try:
        authorize_world = None
        if principal.auth_method == "hosted_owner":
            authorize_world = partial(_relationship_principal, request, body.review.world_id)
        result = confirm_native_relationship(
            repo_root(), body.review, body.prepared, body.confirm_token, principal,
            authorize_world=authorize_world,
        )
        if authorize_world is not None:
            authorize_world()
        return jsonable_encoder(result)
    except (GraphObjectAuthoringError, DungeonMindError, ValueError) as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 409),
            detail={"code": getattr(exc, "code", "native_relationship_confirm_failed")},
        ) from exc


@router.post("/prepare", response_model=GraphObjectAuthoringPrepareResponse)
def post_graph_object_authoring_prepare(
    request: GraphObjectAuthoringPrepareRequest, request_context: Request,
) -> dict[str, Any]:
    from apps.live_control_server.services.hosted_native_graph_access import manual_knowledge_actor

    authorize_world = partial(
        manual_knowledge_actor, request_context, world_id=request.world_id, run_id=request.source_run_id,
    )
    actor = authorize_world()
    try:
        response = prepare_graph_object_authoring_write(request, authenticated_actor=actor) if actor else prepare_graph_object_authoring_write(request)
    except GraphObjectAuthoringError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}
        ) from exc
    if actor:
        authorize_world()
    return response.model_dump(mode="json", by_alias=False)


@router.post("/commit", response_model=GraphObjectAuthoringCommitResponse)
def post_graph_object_authoring_commit(
    request: GraphObjectAuthoringCommitRequest, request_context: Request,
) -> dict[str, Any]:
    from apps.live_control_server.services.hosted_native_graph_access import manual_knowledge_actor

    authorize_world = partial(
        manual_knowledge_actor, request_context, world_id=request.world_id, run_id=request.source_run_id,
    )
    actor = authorize_world()
    try:
        if actor:
            response = commit_graph_object_authoring_write(
                request, authenticated_actor=actor, authorize_world=authorize_world,
            )
        else:
            response = commit_graph_object_authoring_write(request)
    except GraphObjectAuthoringError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}
        ) from exc
    if actor:
        authorize_world()
    return response.model_dump(mode="json", by_alias=False)


@router.post("/merge-reconciliation/prepare")
def post_graph_merge_reconciliation_prepare(
    _body: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(status_code=410, content={"detail": _STORE_RETIRED})


@router.post("/merge-reconciliation/apply")
def post_graph_merge_reconciliation_apply(
    _body: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(status_code=410, content={"detail": _STORE_RETIRED})


# Native manual authoring is an additive protocol; retained classic routes stay intact.
def _native_manual_call(fn, body, principal):
    from apps.live_control_server.services import native_manual_knowledge as manual
    from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError
    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import NativeWorldSourceAdmissionError
    from dungeonmind.application.vnext.errors import KnowledgePublicationOutcomeUnknownError
    from dungeonmind.domain.errors import PersistenceUnavailableError
    from application_state.errors import ApplicationStateError
    from graph_memory.vnext.domain_runtime import DungeonBuddyDescriptorError
    from apps.live_control_server.models.native_manual_knowledge import ManualConfirmRequest

    try:
        return fn(body, principal)
    except (manual.ManualRefused, manual.ManualOutcomeUnknown, InspectionUnavailable, ApplicationStateError, GraphObjectAuthoringError, GraphRunRegistryError,
            SourceArtifactRegistryError, WorkspaceDocumentRegistryError,
            WorldGraphProjectionServiceError, NativeWorldSourceAdmissionError,
            DungeonBuddyDescriptorError, DungeonMindError) as exc:
        unknown = isinstance(exc, (KnowledgePublicationOutcomeUnknownError, manual.ManualOutcomeUnknown))
        unavailable = isinstance(exc, PersistenceUnavailableError) or getattr(exc, 'status_code', None) == 503
        raise HTTPException(503 if unknown or unavailable else getattr(exc, 'status_code', 409), detail={
            'code': getattr(exc, 'code', 'manual_authority_unavailable' if unavailable else 'manual_integrity_error'),
            'outcome_unknown': unknown,
            'retry_original_packet': isinstance(body, ManualConfirmRequest) and (unknown or unavailable),
            'message': 'The exact manual review could not be completed.',
        }) from None


@router.post('/native-manual/context')
def native_manual_context(body: ManualContextRequest, principal=Depends(native_graph_explorer_dependency)):
    from apps.live_control_server.services.native_manual_knowledge import context
    return _native_manual_call(context, body, principal)


@router.post('/native-manual/prepare')
def native_manual_prepare(body: ManualPrepareRequest, principal=Depends(native_graph_explorer_dependency)):
    from apps.live_control_server.services.native_manual_knowledge import prepare
    return _native_manual_call(prepare, body, principal)


@router.post('/native-manual/confirm')
def native_manual_confirm(body: ManualConfirmRequest, principal=Depends(native_graph_explorer_dependency)):
    from apps.live_control_server.services.native_manual_knowledge import confirm
    return _native_manual_call(confirm, body, principal)
