"""SBW09b: Threat publication identity-resolution API (handoff §9.1, §9.11)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import validate_publication_operation_id
from apps.live_control_server.models.threat_publication_identity import (
    CreateThreatIdentityResolutionRequestV1,
    PrepareThreatIdentityCandidatesRequestV1,
    ThreatPublicationIdentityResultLabel,
    validate_resolution_id,
)
from apps.live_control_server.services.threat_publication_identity import (
    IdentityResolutionOutcome,
    decide_identity_resolution,
    prepare_identity_candidates,
    read_identity_resolution,
)

router = APIRouter(prefix="/api/live/threat-drafts", tags=["threat-publication-identity"])

_SUCCESS_LABELS: frozenset[ThreatPublicationIdentityResultLabel] = frozenset(
    {
        "publication_identity_candidates_ready",
        "publication_identity_created_new",
        "publication_identity_connected_existing",
        "publication_identity_refused",
        "publication_identity_superseded",
    }
)
_CONFLICT_LABELS: frozenset[ThreatPublicationIdentityResultLabel] = frozenset(
    {
        "publication_identity_operation_not_ready",
        "publication_identity_candidate_overflow",
        "publication_identity_candidate_set_changed",
        "publication_identity_review_required",
        "publication_identity_target_invalid",
        "publication_identity_new_id_collision",
        "publication_identity_busy",
        "publication_identity_input_conflict",
        "publication_identity_history_full",
    }
)
_UNAVAILABLE_LABELS: frozenset[ThreatPublicationIdentityResultLabel] = frozenset(
    {
        "publication_identity_graph_unavailable",
        "publication_identity_storage_unavailable",
    }
)


def _http_status(outcome: IdentityResolutionOutcome) -> int:
    label = outcome.response.result_label
    if outcome.created and label in {
        "publication_identity_created_new",
        "publication_identity_connected_existing",
        "publication_identity_refused",
        "publication_identity_superseded",
    }:
        return 201
    if label in _SUCCESS_LABELS:
        return 200
    if label in {"publication_identity_not_found", "publication_identity_target_not_found"}:
        return 404
    if label in _CONFLICT_LABELS:
        return 409
    if label in _UNAVAILABLE_LABELS:
        return 503
    if label == "publication_identity_integrity_failure":
        return 500
    return 500


def _json(outcome: IdentityResolutionOutcome) -> JSONResponse:
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


@router.post(
    "/{draft_id}/publication-operations/{operation_id}/identity-candidates/prepare"
)
def post_prepare_identity_candidates(
    draft_id: str,
    operation_id: str,
    body: PrepareThreatIdentityCandidatesRequestV1,
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    outcome = prepare_identity_candidates(
        repo_root(), safe_draft, safe_op, body, world_root=world_graph_root()
    )
    return _json(outcome)


@router.post("/{draft_id}/publication-operations/{operation_id}/identity-resolutions")
def post_identity_resolution(
    draft_id: str,
    operation_id: str,
    body: CreateThreatIdentityResolutionRequestV1,
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    outcome = decide_identity_resolution(
        repo_root(), safe_draft, safe_op, body, world_root=world_graph_root()
    )
    return _json(outcome)


@router.get(
    "/{draft_id}/publication-operations/{operation_id}/identity-resolutions/{resolution_id}"
)
def get_identity_resolution(
    draft_id: str, operation_id: str, resolution_id: str
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    safe_resolution = _validated_resolution_id(resolution_id)
    outcome = read_identity_resolution(repo_root(), safe_draft, safe_op, safe_resolution)
    return _json(outcome)
