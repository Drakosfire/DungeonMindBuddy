"""Statblock candidate generate/read and definition validation API."""
from __future__ import annotations

import os
from typing import Any,Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

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
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm,native_graph_gm_dependency


def _revision_call(callback,**kwargs):
    try:return callback(statblock_data_root(repo_root()),**kwargs)
    except ThreatDraftStoreError as exc:raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc
    except ApplicationStateConflictError as exc:raise HTTPException(status_code=409,detail=str(exc)) from exc
    except ApplicationStateIntegrityError as exc:raise HTTPException(status_code=503,detail=str(exc)) from exc
    except ApplicationStateError as exc:raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc
    except StatblockIntegrationError as exc:raise HTTPException(status_code=503,detail="Saved mechanics provider is unavailable") from exc


@router.get("/saved-statblocks/lookup")
def lookup_saved_statblock(
    request: Request,
    world_id: Annotated[str, Query(pattern=r"^[a-z][a-z0-9_-]{0,62}$")],
    name: Annotated[str, Query(min_length=1)],
):
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import require_hosted_plan_world_context

    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        enforce_native_graph_gm(request)
    else:
        require_hosted_plan_world_context(request, world_id)
    if not name.strip():
        raise HTTPException(status_code=422, detail="Statblock name is required")
    result = _revision_call(saved_versions.find_saved_version, world_id=world_id, name=name)
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        require_hosted_plan_world_context(request, world_id)
    return result


def _require_undeleted_revision_target(world_id: str, draft_id: str) -> None:
    from application_state.config import APPLICATION_STATE_DSN_ENV
    from application_state.mechanics_revisions import purge

    if not os.getenv(APPLICATION_STATE_DSN_ENV):
        return
    try:
        draft_key = UUID(draft_id)
    except ValueError:
        return
    try:
        receipt = purge.find_receipt(world_id=world_id, draft_id=draft_key)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if receipt is not None:
        _, complete = receipt
        if complete:
            raise HTTPException(status_code=410, detail="This statblock was permanently deleted.")
        raise HTTPException(status_code=409, detail="Deletion is in progress for this statblock.")


@router.get('/threat-drafts/{draft_id}/mechanics-revisions')
def list_saved_revisions(
    draft_id: str, world_id: str, request: Request,
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
):
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    _require_undeleted_revision_target(world_id, draft_id)
    return _revision_call(saved_versions.list_versions,world_id=world_id,draft_id=draft_id,limit=limit,offset=offset)


@router.get('/threat-drafts/{draft_id}/mechanics-revisions/{revision_id}')
def open_saved_revision(draft_id: str, revision_id: str, world_id: str, request: Request):
    from base64 import b64encode
    from application_state.config import APPLICATION_STATE_DSN_ENV
    from application_state.mechanics_revisions import pdf_portraits
    from application_state.mechanics_revisions.types import PDF_REVIEW_PROVENANCE
    from apps.live_control_server.routes.agent import get_pdf_statblock_review
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    _require_undeleted_revision_target(world_id, draft_id)
    packet = _revision_call(saved_versions.open_version, world_id=world_id, draft_id=draft_id, revision_id=revision_id)
    resource = packet["resource"]
    accepted_through = (resource.get("provenance") or {}).get("accepted_through") or {}
    source = accepted_through.get(PDF_REVIEW_PROVENANCE)
    if not isinstance(source, dict) or source.get("world_id") != world_id:
        return packet
    try:
        review_id = UUID(source["review_id"])
    except (KeyError, TypeError, ValueError):
        return packet
    if os.getenv(APPLICATION_STATE_DSN_ENV):
        portrait = _revision_call(
            lambda _root: pdf_portraits.read(
                statblock_id=resource["statblock_id"], world_id=world_id, draft_id=UUID(draft_id),
                review_id=review_id,
            ),
        )
        if portrait is not None:
            packet["pdf_portrait"] = b64encode(portrait).decode("ascii")
            require_build_pdf_access(request, world_id)
            return packet
    try:
        review = get_pdf_statblock_review(world_id, review_id, request)
    except HTTPException as exc:
        if exc.status_code not in {403, 404, 410, 503}:
            raise
        return packet
    if review["regions"] == source.get("regions") and review.get("artwork"):
        packet["pdf_portrait"] = review["artwork"]["jpeg_base64"]
    return packet


@router.post("/threat-drafts/{draft_id}/mechanics-revisions")
def save_manual_revision(draft_id: UUID, body: SaveMechanicsRevisionRequest, request: Request):
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import (
        hosted_world_media_owner, require_build_pdf_access,
    )

    authorize = None
    if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
        authorize = lambda: require_build_pdf_access(request, body.world_id)
        authorize()
        owner = hosted_world_media_owner(body.world_id)
    else:
        owner = enforce_native_graph_gm(request).subject
    return _revision_call(saved_versions.save, draft_id=str(draft_id), request=body, media_owner=owner, authorize=authorize)


@router.post("/threat-drafts/{draft_id}/mechanics-revision-operations/{operation_id}:recover")
def recover_manual_revision(draft_id: UUID, operation_id: UUID, world_id: Annotated[str, Query(pattern=r"^[a-z][a-z0-9_-]{0,62}$")], request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    return _revision_call(saved_versions.recover, world_id=world_id, draft_id=draft_id, operation_id=operation_id,
                          authorize=lambda: require_build_pdf_access(request, world_id))


@router.get("/threat-drafts/{draft_id}/mechanics-revision-operations/{operation_id}")
def inspect_manual_revision(draft_id: UUID, operation_id: UUID, world_id: Annotated[str, Query(pattern=r"^[a-z][a-z0-9_-]{0,62}$")], request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    return _revision_call(saved_versions.inspect_operation, world_id=world_id, draft_id=draft_id, operation_id=operation_id)
