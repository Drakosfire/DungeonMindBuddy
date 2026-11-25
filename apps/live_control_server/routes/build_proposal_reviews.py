"""Authenticated author review; no provider call or source writer is reachable."""

from functools import partial
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from application_state.build_proposal.graph_reference_review import (
    BuildGraphReferenceAuthorizeSave,
    BuildGraphReferenceCommand,
    BuildGraphReferenceConfirm,
    BuildGraphReferencePrepare,
    BuildGraphReferenceReviewService,
)
from application_state.build_proposal.review import (
    BuildReviewCommand,
    BuildProposalReview,
    BuildProposalReviewService,
)
from application_state.errors import ApplicationStateError, ApplicationStateNotFoundError
from apps.live_control_server.services import hosted_auth
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm

router = APIRouter()


def _review_response(service, review):
    if isinstance(review, BuildProposalReview):
        original = service.original_editor_json(review)
        if original is not None:
            return {**review.model_dump(mode="json"), "original_editor_json": original}
    return review


def scope(world_id, request):
    from .agent import _verified_world_id

    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(422, detail="Review accepts no query selectors")
    return verified


@router.get("/worlds/{world_id}/build-proposals/{action_id}/review")
def get_review(world_id: str, action_id: UUID, request: Request):
    world = scope(world_id, request)
    try:
        try:
            from .agent import _guest_proposal_options
            service = BuildProposalReviewService(**_guest_proposal_options(request))
            review = _review_response(service, service.get(world, action_id))
        except ApplicationStateNotFoundError:
            if getattr(request.state, "guest_conversation_world", None) is not None:
                raise
            review = BuildGraphReferenceReviewService().get(world, action_id)
        if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
            scope(world_id, request)
        return review
    except ApplicationStateError as exc:
        raise HTTPException(
            exc.status_code, detail={"code": "proposal_review_unavailable"}
        ) from exc


@router.post("/worlds/{world_id}/build-proposals/{action_id}/review")
def change_review(
    world_id: str, action_id: UUID, body: BuildReviewCommand | BuildGraphReferenceCommand, request: Request
):
    world = scope(world_id, request)
    try:
        if not isinstance(body, BuildReviewCommand):
            if getattr(request.state, "guest_conversation_world", None) is not None:
                raise HTTPException(403, detail="Guest Graph reference review is unavailable")
            result = _change_graph_reference_review(world, action_id, body, request)
            if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
                scope(world_id, request)
            return result
        from apps.live_control_server.services.build_document_proposal import _source, BuildComposeError
        def validate_source(capability):
            try:
                _source(capability)
            except BuildComposeError as exc:
                from application_state.errors import ApplicationStateConflictError
                raise ApplicationStateConflictError(str(exc)) from exc
        authorize_world = None
        hosted = hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS
        guest = getattr(request.state, "guest_conversation_world", None) is not None
        if hosted and not guest:
            authorize_world = partial(scope, world_id, request)
        from .agent import _guest_proposal_options
        service = BuildProposalReviewService(validate_source=validate_source, **_guest_proposal_options(request))
        review = service.execute(world, action_id, body, authorize_world=authorize_world)
        if body.operation == "open":
            review = _review_response(service, review)
        if hosted:
            scope(world_id, request)
        return review
    except ApplicationStateError as exc:
        raise HTTPException(
            exc.status_code,
            detail={"code": "proposal_review_changed", "message": str(exc)},
        ) from exc


def _change_graph_reference_review(world, action_id, body, request):
    from apps.live_control_server.services.build_graph_reference import (
        authorize_graph_reference_prepare,
        authorize_graph_reference_save,
        observe_graph_reference_save,
    )
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    service = BuildGraphReferenceReviewService()
    authorize_world = partial(scope, world, request)
    if isinstance(body, BuildGraphReferencePrepare):
        principal = conversation_graph_principal(request, world, authorize_local=enforce_native_graph_gm)

        def authorize_prepare(review, receipt):
            authorize_graph_reference_prepare(review, body, principal)
            authorize_world()

        return service.prepare(
            world, action_id, body.expected_revision, body.apply,
            body.editor_json, body.draft_markdown, body.after_editor_json, body.after_draft_markdown,
            authorize_prepare=authorize_prepare,
        )
    if isinstance(body, BuildGraphReferenceAuthorizeSave):
        principal = conversation_graph_principal(request, world, authorize_local=enforce_native_graph_gm)

        def authorize_save(review):
            authorize_graph_reference_save(review, principal)
            authorize_world()

        return service.authorize_save(world, action_id, body.apply_id, authorize=authorize_save)
    if isinstance(body, BuildGraphReferenceConfirm):
        def observe_save(review):
            revision = observe_graph_reference_save(review)
            authorize_world()
            return revision

        return service.confirm(world, action_id, body.apply_id, observe_save=observe_save)
    return service.discard(world, action_id, body.expected_revision, authorize_discard=authorize_world)
