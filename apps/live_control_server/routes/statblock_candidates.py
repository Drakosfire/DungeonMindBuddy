"""Statblock candidate generate/read and definition validation API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.statblock_candidate_workflow import (
    GenerateThreatDraftCandidateRequestV1,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptThreatDraftMechanicsRequestV1,
    AcceptThreatDraftMechanicsResponseV1,
    ReadAcceptanceOperationResponseV1,
)
from apps.live_control_server.services.statblock_candidate_generation import (
    generate_candidate_from_draft,
    read_candidate,
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
from apps.live_control_server.services.threat_draft_store import ThreatDraftStoreError

router = APIRouter(prefix="/api/live", tags=["statblock-candidates"])


@router.post("/threat-drafts/{draft_id}/candidates:generate")
def post_generate_candidate(
    draft_id: str,
    body: GenerateThreatDraftCandidateRequestV1,
) -> dict[str, Any]:
    try:
        result = generate_candidate_from_draft(
            repo_root(),
            draft_id=draft_id,
            request=body,
        )
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return result.model_dump(mode="json", by_alias=True)


@router.get("/statblock-candidates/{candidate_id}")
def get_statblock_candidate(candidate_id: str) -> dict[str, Any]:
    result = read_candidate(repo_root(), candidate_id=candidate_id)
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
            repo_root(),
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
        repo_root(),
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
            repo_root(),
            draft_id=draft_id,
            operation_id=operation_id,
        )
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
