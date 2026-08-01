"""SBW09c1: Threat publication proposal API (handoff §6F)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import validate_publication_operation_id
from apps.live_control_server.models.threat_publication_identity import validate_resolution_id
from apps.live_control_server.models.threat_publication_proposal import (
    PrepareThreatPublicationProposalRequestV1,
    ThreatPublicationProposalResultLabel,
    validate_proposal_id,
)
from apps.live_control_server.services.threat_publication_proposals import (
    ProposalOutcome,
    prepare_threat_publication_proposal,
    read_threat_publication_proposal,
)

router = APIRouter(prefix="/api/live/threat-drafts", tags=["threat-publication-proposals"])

_SUCCESS_LABELS: frozenset[ThreatPublicationProposalResultLabel] = frozenset(
    {
        "publication_proposal_ready",
        "publication_proposal_superseded",
    }
)
_CONFLICT_LABELS: frozenset[ThreatPublicationProposalResultLabel] = frozenset(
    {
        "publication_proposal_identity_refused",
        "publication_proposal_operation_not_ready",
        "publication_proposal_resolution_not_active",
        "publication_proposal_predecessor_mismatch",
        "publication_proposal_parent_mismatch",
        "publication_proposal_typed_collision",
        "publication_proposal_busy",
        "publication_proposal_input_conflict",
        "publication_proposal_history_full",
    }
)
_UNAVAILABLE_LABELS: frozenset[ThreatPublicationProposalResultLabel] = frozenset(
    {
        "publication_proposal_graph_unavailable",
        "publication_proposal_storage_unavailable",
    }
)


def _http_status(outcome: ProposalOutcome) -> int:
    label = outcome.response.result_label
    if outcome.created and label == "publication_proposal_ready":
        return 201
    if label in _SUCCESS_LABELS:
        return 200
    if label == "publication_proposal_not_found":
        return 404
    if label in _CONFLICT_LABELS:
        return 409
    if label in _UNAVAILABLE_LABELS:
        return 503
    if label == "publication_proposal_integrity_failure":
        return 500
    return 500


def _json(outcome: ProposalOutcome) -> JSONResponse:
    return JSONResponse(
        status_code=_http_status(outcome),
        content=outcome.response.model_dump(mode="json", by_alias=True),
    )


def _validated_draft_id(draft_id: str) -> str:
    try:
        return require_draft_id(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid draft_id") from exc


def _validated_operation_id(operation_id: str) -> str:
    try:
        return validate_publication_operation_id(operation_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid operation_id") from exc


def _validated_resolution_id(resolution_id: str) -> str:
    try:
        return validate_resolution_id(resolution_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid resolution_id") from exc


def _validated_proposal_id(proposal_id: str) -> str:
    try:
        return validate_proposal_id(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid proposal_id") from exc


@router.post(
    "/{draft_id}/publication-operations/{operation_id}/identity-resolutions/{resolution_id}/proposals"
)
def post_prepare_publication_proposal(
    draft_id: str,
    operation_id: str,
    resolution_id: str,
    body: PrepareThreatPublicationProposalRequestV1,
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    safe_resolution = _validated_resolution_id(resolution_id)
    outcome = prepare_threat_publication_proposal(
        repo_root(),
        safe_draft,
        safe_op,
        safe_resolution,
        body,
        world_root=world_graph_root(),
    )
    return _json(outcome)


@router.get(
    "/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}"
)
def get_publication_proposal(
    draft_id: str,
    operation_id: str,
    proposal_id: str,
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    safe_proposal = _validated_proposal_id(proposal_id)
    outcome = read_threat_publication_proposal(repo_root(), safe_draft, safe_op, safe_proposal)
    return _json(outcome)
