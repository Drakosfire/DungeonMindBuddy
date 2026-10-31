"""Authenticated selected source statements; no automatic corpus publication."""

from typing import Annotated
from uuid import UUID

from dungeonmind.application.vnext.errors import KnowledgePublicationOutcomeUnknownError
from dungeonmind.domain.errors import DungeonMindError
from fastapi import APIRouter, Depends, HTTPException
from worldkeeper.application.commit import (
    CommitAuthorityIntegrityFailure,
    CommittedChangeOutcomeUnknown,
    CommittedChangeVerificationIntegrityFailure,
    CommittedChangeVerificationUnavailable,
    PreparedChangeConflict,
    PreparedChangeIntegrityFailure,
    PreparedChangeStale,
)
from worldkeeper.application.preparation import InvalidWorldChange

from application_state.errors import ApplicationStateError
from apps.live_control_server.models.source_statement_proposals import (
    ProposalRequest,
    ProposalReview,
)
from apps.live_control_server.models.source_statements import (
    ConfirmStatement,
    ExtendSourceEvidence,
    StatementSelection,
)
from apps.live_control_server.routes.strict_json import StrictJSONRoute
from apps.live_control_server.services import source_statement_proposals as proposals
from apps.live_control_server.services import source_statements as service
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    authenticate_native_graph_principal,
    native_graph_gm_dependency,
)

router = APIRouter(prefix="/api/live/source-statements", tags=["source-statements"])


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (
        ValueError,
        DungeonMindError,
        InvalidWorldChange,
        PreparedChangeStale,
        PreparedChangeConflict,
        PreparedChangeIntegrityFailure,
        CommitAuthorityIntegrityFailure,
        CommittedChangeOutcomeUnknown,
        CommittedChangeVerificationUnavailable,
        CommittedChangeVerificationIntegrityFailure,
    ) as exc:
        detail = {
            "code": getattr(exc, "code", "source_statement_refused"),
            "message": str(exc),
            "retry_original_packet": bool(
                getattr(exc, "retry_original_packet", False)
                or getattr(exc, "retry_safe", False)
            ),
        }
        if isinstance(exc, KnowledgePublicationOutcomeUnknownError):
            detail["recovery"] = {
                "action": "retry_exact_request",
                "space_id": exc.space_id,
                "publication_id": exc.publication_id,
                "expected_published_revision_id": exc.expected_published_revision_id,
            }
        raise HTTPException(409, detail=detail) from exc



def prepare(
    body: StatementSelection,
    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
):
    return _call(service.prepare, body, principal)


def confirm(
    body: ConfirmStatement,
    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
):
    return _call(service.confirm, body, principal)


router.add_api_route(
    "/prepare", prepare, methods=["POST"], route_class_override=StrictJSONRoute
)
router.add_api_route(
    "/confirm", confirm, methods=["POST"], route_class_override=StrictJSONRoute
)


@router.get("/{managed_world_id}/subjects/{entity_id}")
def read_subject(
    managed_world_id: str,
    entity_id: str,
    campaign_id: str,
    revision_id: str,
    principal: NativeGraphPrincipal = Depends(authenticate_native_graph_principal),
):
    return _call(
        service.read_subject,
        managed_world_id=managed_world_id,
        entity_id=entity_id,
        campaign_id=campaign_id,
        revision_id=revision_id,
        principal=principal,
    )


# Static proposal routes precede no conflicting dynamic POST paths.


def _proposal_call(fn, *args, **kwargs):
    try:
        return _call(fn, *args, **kwargs)
    except ApplicationStateError as exc:
        raise HTTPException(exc.status_code, detail={"code": type(exc).__name__, "message": str(exc)}) from exc


async def produce_proposals(body: ProposalRequest, principal=Depends(native_graph_gm_dependency)):
    try:
        return await proposals.produce(body, principal)
    except ApplicationStateError as exc:
        raise HTTPException(exc.status_code, detail={"code": type(exc).__name__, "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(409, detail={"code": "proposal_source_refused", "message": str(exc)}) from exc


@router.get("/proposals/{operation_id}")
def read_proposals(operation_id: UUID, managed_world_id: str, principal=Depends(native_graph_gm_dependency)):
    return _proposal_call(proposals.get, operation_id, managed_world_id, principal)


def review_proposal(operation_id: UUID, managed_world_id: str, body: ProposalReview,
                    principal=Depends(native_graph_gm_dependency)):
    return _proposal_call(proposals.review, operation_id, managed_world_id, body, principal)

router.add_api_route("/proposals", produce_proposals, methods=["POST"], route_class_override=StrictJSONRoute)
router.add_api_route("/proposals/{operation_id}/review", review_proposal, methods=["POST"], route_class_override=StrictJSONRoute)


def extend_source_evidence(
    body: ExtendSourceEvidence,
    principal: Annotated[NativeGraphPrincipal, Depends(native_graph_gm_dependency)],
):
    return _call(service.extend_source_evidence, body, principal)


router.add_api_route(
    "/extend-evidence", extend_source_evidence, methods=["POST"],
    route_class_override=StrictJSONRoute,
)
