"""SBW09c2b: Threat publication commit API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import validate_publication_operation_id
from apps.live_control_server.models.threat_publication_commit import (
    ConfirmThreatPublicationRequestV1,
    ThreatPublicationCommitResultLabel,
    validate_commit_id,
)
from apps.live_control_server.models.threat_publication_proposal import validate_proposal_id
from apps.live_control_server.services.threat_publication_commits import (
    CommitOutcome,
    confirm_threat_publication,
    read_threat_publication_commit,
)

router = APIRouter(prefix="/api/live/threat-drafts", tags=["threat-publication-commits"])

_SUCCESS_COMMITTED = frozenset(
    {
        "publication_commit_verified",
        "publication_commit_committed_unverified",
    }
)
_CONFLICT_LABELS = frozenset(
    {
        "publication_commit_uncommitted",
        "publication_commit_outcome_ambiguous",
        "publication_commit_proposal_not_active",
        "publication_commit_operation_not_ready",
        "publication_commit_resolution_not_active",
        "publication_commit_predecessor_mismatch",
        "publication_commit_parent_mismatch",
        "publication_commit_busy",
        "publication_commit_input_conflict",
    }
)
_UNAVAILABLE_LABELS = frozenset(
    {
        "publication_commit_recovery_pending",
        "publication_commit_graph_unavailable",
        "publication_commit_storage_unavailable",
    }
)


def _http_status(outcome: CommitOutcome) -> int:
    label: ThreatPublicationCommitResultLabel = outcome.response.result_label
    if outcome.created and label in _SUCCESS_COMMITTED:
        return 201
    if label in _SUCCESS_COMMITTED:
        return 200
    if label == "publication_commit_not_found":
        return 404
    if label in _CONFLICT_LABELS:
        return 409
    if label in _UNAVAILABLE_LABELS:
        return 503
    if label == "publication_commit_integrity_failure":
        return 500
    return 500


def _json(outcome: CommitOutcome) -> JSONResponse:
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


def _validated_proposal_id(proposal_id: str) -> str:
    try:
        return validate_proposal_id(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid proposal_id") from exc


def _validated_commit_id(commit_id: str) -> str:
    try:
        return validate_commit_id(commit_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid commit_id") from exc


@router.post(
    "/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}/commits"
)
def post_confirm_publication_commit(
    draft_id: str,
    operation_id: str,
    proposal_id: str,
    body: ConfirmThreatPublicationRequestV1,
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    safe_proposal = _validated_proposal_id(proposal_id)
    outcome = confirm_threat_publication(
        repo_root(),
        safe_draft,
        safe_op,
        safe_proposal,
        body,
        world_root=world_graph_root(),
    )
    return _json(outcome)


@router.get(
    "/{draft_id}/publication-operations/{operation_id}/commits/{commit_id}"
)
def get_publication_commit(
    draft_id: str,
    operation_id: str,
    commit_id: str,
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    safe_commit = _validated_commit_id(commit_id)
    outcome = read_threat_publication_commit(
        repo_root(), safe_draft, safe_op, safe_commit
    )
    return _json(outcome)
