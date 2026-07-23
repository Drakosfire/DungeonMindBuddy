"""Statblock candidate generate/read and definition validation API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.statblock_candidate_workflow import (
    GenerateThreatDraftCandidateRequestV1,
)
from apps.live_control_server.services.statblock_candidate_generation import (
    generate_candidate_from_draft,
    read_candidate,
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
