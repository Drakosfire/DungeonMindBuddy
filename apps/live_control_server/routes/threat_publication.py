"""SBW09a: durable Threat publication-operation API (handoff §9.1, §9.9).

Browser-safe typed API. No graph or DungeonMind mutation happens here or in
the service it calls; the only durable write is the draft-scoped publication
ledger.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import (
    BeginThreatPublicationOperationRequestV1,
    CancelThreatPublicationOperationRequestV1,
    RetryThreatPublicationOperationRequestV1,
    ThreatPublicationResultLabel,
    validate_publication_operation_id,
)
from apps.live_control_server.services.threat_publication_operations import (
    PublicationOperationOutcome,
    begin_publication_operation,
    cancel_publication_operation,
    read_publication_operation,
    refresh_publication_operation,
    retry_publication_operation,
)

router = APIRouter(prefix="/api/live/threat-drafts", tags=["threat-publication"])

_SUCCESS_LABELS: frozenset[ThreatPublicationResultLabel] = frozenset(
    {
        "publication_ready",
        "publication_stale",
        "publication_cancelled",
        "publication_superseded",
    }
)
_CONFLICT_LABELS: frozenset[ThreatPublicationResultLabel] = frozenset(
    {
        "publication_busy",
        "publication_input_conflict",
        "publication_parent_mismatch",
        "publication_source_mismatch",
        "publication_history_full",
        "publication_invalid_state",
    }
)
_UNAVAILABLE_LABELS: frozenset[ThreatPublicationResultLabel] = frozenset(
    {
        "publication_draft_unavailable",
        "publication_graph_unavailable",
        "publication_storage_unavailable",
    }
)


def _http_status(outcome: PublicationOperationOutcome) -> int:
    label = outcome.response.result_label
    if outcome.created and label == "publication_ready":
        return 201
    if label in _SUCCESS_LABELS:
        return 200
    if label == "publication_not_found":
        return 404
    if label in _CONFLICT_LABELS:
        return 409
    if label in _UNAVAILABLE_LABELS:
        return 503
    if label == "publication_integrity_failure":
        return 500
    return 500


def _json(outcome: PublicationOperationOutcome) -> JSONResponse:
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


@router.post("/{draft_id}/publication-operations")
def post_begin_publication_operation(
    draft_id: str, body: BeginThreatPublicationOperationRequestV1
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    outcome = begin_publication_operation(repo_root(), safe_draft, body)
    return _json(outcome)


@router.get("/{draft_id}/publication-operations/{operation_id}")
def get_publication_operation(draft_id: str, operation_id: str) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    outcome = read_publication_operation(repo_root(), safe_draft, safe_op)
    return _json(outcome)


@router.post("/{draft_id}/publication-operations/{operation_id}/refresh")
def post_refresh_publication_operation(draft_id: str, operation_id: str) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    outcome = refresh_publication_operation(repo_root(), safe_draft, safe_op)
    return _json(outcome)


@router.post("/{draft_id}/publication-operations/{operation_id}/cancel")
def post_cancel_publication_operation(
    draft_id: str, operation_id: str, body: CancelThreatPublicationOperationRequestV1
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    outcome = cancel_publication_operation(repo_root(), safe_draft, safe_op, body)
    return _json(outcome)


@router.post("/{draft_id}/publication-operations/{operation_id}/retry")
def post_retry_publication_operation(
    draft_id: str, operation_id: str, body: RetryThreatPublicationOperationRequestV1
) -> JSONResponse:
    safe_draft = _validated_draft_id(draft_id)
    safe_op = _validated_operation_id(operation_id)
    outcome = retry_publication_operation(repo_root(), safe_draft, safe_op, body)
    return _json(outcome)
