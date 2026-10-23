"""Statblock candidate generate/read and definition validation API."""
from __future__ import annotations

from typing import Any,Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException

from apps.live_control_server.routes.statblock_storage import statblock_data_root
from apps.live_control_server.config import repo_root
from apps.live_control_server.models.statblock_candidate_workflow import (
    GenerateThreatDraftCandidateRequestV1,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptThreatDraftMechanicsRequestV1,
    AcceptThreatDraftMechanicsResponseV1,
    ReadAcceptanceOperationResponseV1,
)
from apps.live_control_server.models.statblock_candidate_revision import (
    ReviseCandidateFromEditedDefinitionRequestV1,
)
from apps.live_control_server.services.statblock_candidate_generation import (
    generate_candidate_from_draft,
    read_candidate,
)
from apps.live_control_server.services.statblock_candidate_revision import (
    ReviseCandidateRevisionError,
    revise_candidate_from_edited_definition,
)
from apps.live_control_server.services.statblock_mechanics_acceptance import (
    begin_or_resume_acceptance,
    read_acceptance_operation,
    recover_acceptance_operation,
)
from apps.live_control_server.services.statblock_definition_validation import (
    ValidateDefinitionBuddyRequestV1,
    ValidateDefinitionBuddyResponseV1,
    validate_definition,
)
from apps.live_control_server.services.statblock_revise_reconciliation import (
    ReviseReconciliationError,
)
from apps.live_control_server.services.threat_draft_store import ThreatDraftStoreError

router = APIRouter(prefix="/api/live", tags=["statblock-candidates"])


@router.post("/threat-drafts/{draft_id}/candidates:generate")
def post_generate_candidate(
    draft_id: str,
    body: GenerateThreatDraftCandidateRequestV1,
) -> dict[str, Any]:
    try:
        result = generate_candidate_from_draft(
            statblock_data_root(repo_root()),
            draft_id=draft_id,
            request=body,
        )
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return result.model_dump(mode="json", by_alias=True)


@router.post("/threat-drafts/{draft_id}/candidates:revise")
def post_revise_candidate_from_edited_definition(
    draft_id: str,
    body: ReviseCandidateFromEditedDefinitionRequestV1,
) -> dict[str, Any]:
    try:
        result = revise_candidate_from_edited_definition(
            statblock_data_root(repo_root()),
            draft_id=draft_id,
            request=body,
        )
    except ReviseCandidateRevisionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ReviseReconciliationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return result.model_dump(mode="json", by_alias=True)


@router.get("/statblock-candidates/{candidate_id}")
def get_statblock_candidate(candidate_id: str) -> dict[str, Any]:
    result = read_candidate(statblock_data_root(repo_root()), candidate_id=candidate_id)
    return result.model_dump(mode="json", by_alias=True)


@router.post("/statblock-definitions:validate")
def post_validate_definition(
    body: ValidateDefinitionBuddyRequestV1,
) -> ValidateDefinitionBuddyResponseV1:
    return validate_definition(definition=body.definition)


@router.post("/threat-drafts/{draft_id}/mechanics:accept")
def post_accept_mechanics(
    draft_id: str,
    body: AcceptThreatDraftMechanicsRequestV1,
) -> AcceptThreatDraftMechanicsResponseV1:
    try:
        return begin_or_resume_acceptance(
            statblock_data_root(repo_root()),
            draft_id=draft_id,
            request=body,
        )
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get(
    "/threat-drafts/{draft_id}/acceptance-operations/{operation_id}",
)
def get_acceptance_operation_route(
    draft_id: str,
    operation_id: str,
) -> ReadAcceptanceOperationResponseV1:
    return read_acceptance_operation(
        statblock_data_root(repo_root()),
        draft_id=draft_id,
        operation_id=operation_id,
    )


@router.post(
    "/threat-drafts/{draft_id}/acceptance-operations/{operation_id}:reconcile",
)
def post_reconcile_acceptance(
    draft_id: str,
    operation_id: str,
) -> AcceptThreatDraftMechanicsResponseV1:
    try:
        return recover_acceptance_operation(
            statblock_data_root(repo_root()),
            draft_id=draft_id,
            operation_id=operation_id,
        )
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


# Saved manual revisions have their own proof and recovery lifecycle. They do not
# replace the original first-acceptance reference or modify encounters.
from apps.live_control_server.models.statblock_saved_revision import SaveMechanicsRevisionRequest
from apps.live_control_server.services import statblock_saved_revision as saved_versions
from application_state.errors import ApplicationStateError,ApplicationStateConflictError,ApplicationStateIntegrityError
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import StatblockIntegrationError
from fastapi import Query,Depends
from apps.live_control_server.services.agent_graph_auth import native_graph_gm_dependency


def _revision_call(callback,**kwargs):
    try:return callback(statblock_data_root(repo_root()),**kwargs)
    except ThreatDraftStoreError as exc:raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc
    except ApplicationStateConflictError as exc:raise HTTPException(status_code=409,detail=str(exc)) from exc
    except ApplicationStateIntegrityError as exc:raise HTTPException(status_code=503,detail=str(exc)) from exc
    except ApplicationStateError as exc:raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc
    except StatblockIntegrationError as exc:raise HTTPException(status_code=503,detail="Saved mechanics provider is unavailable") from exc


@router.get('/threat-drafts/{draft_id}/mechanics-revisions',dependencies=[Depends(native_graph_gm_dependency)])
def list_saved_revisions(draft_id:str,world_id:str,limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0)):
    return _revision_call(saved_versions.list_versions,world_id=world_id,draft_id=draft_id,limit=limit,offset=offset)


@router.get('/threat-drafts/{draft_id}/mechanics-revisions/{revision_id}',dependencies=[Depends(native_graph_gm_dependency)])
def open_saved_revision(draft_id:str,revision_id:str,world_id:str):
    return _revision_call(saved_versions.open_version,world_id=world_id,draft_id=draft_id,revision_id=revision_id)


@router.post('/threat-drafts/{draft_id}/mechanics-revisions',dependencies=[Depends(native_graph_gm_dependency)])
def save_manual_revision(draft_id:str,body:SaveMechanicsRevisionRequest):
    return _revision_call(saved_versions.save,draft_id=draft_id,request=body)


@router.post('/threat-drafts/{draft_id}/mechanics-revision-operations/{operation_id}:recover',dependencies=[Depends(native_graph_gm_dependency)])
def recover_manual_revision(draft_id:UUID,operation_id:UUID,world_id:Annotated[str,Query(pattern=r'^[a-z][a-z0-9_-]{0,62}$')]):
    return _revision_call(saved_versions.recover,world_id=world_id,draft_id=draft_id,operation_id=operation_id)


@router.get('/threat-drafts/{draft_id}/mechanics-revision-operations/{operation_id}',dependencies=[Depends(native_graph_gm_dependency)])
def inspect_manual_revision(draft_id:UUID,operation_id:UUID,world_id:Annotated[str,Query(pattern=r'^[a-z][a-z0-9_-]{0,62}$')]):
    return _revision_call(saved_versions.inspect_operation,world_id=world_id,draft_id=draft_id,operation_id=operation_id)
