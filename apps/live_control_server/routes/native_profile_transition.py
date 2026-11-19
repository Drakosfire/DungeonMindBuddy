"""Explicit authenticated native profile transition; never an access side effect."""

from fastapi import APIRouter, Depends, HTTPException
from dungeonmind.application.vnext.errors import (
    KnowledgePublicationIdempotencyConflictError,
    KnowledgePublicationOutcomeUnknownError,
    KnowledgeStaleParentRevisionError,
    KnowledgeProfileTransitionIntegrityError,
)
from dungeonmind.domain.errors import (
    ImmutableRevisionConflictError,
    PersistenceIntegrityError,
    PersistenceUnavailableError,
)
from apps.live_control_server.models.native_profile_transition import (
    ProfileTransitionConfirm,
    ProfileTransitionPrepare,
)
from apps.live_control_server.routes.strict_json import StrictJSONRoute
from apps.live_control_server.services import native_profile_transition as service
from apps.live_control_server.services.hosted_native_graph_access import (
    native_graph_explorer_dependency,
)
from graph_memory.vnext.domain_runtime import DungeonBuddyDescriptorError
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringError,
)

router = APIRouter(
    prefix="/api/live/graph-authoring/native-profile-transition",
    route_class=StrictJSONRoute,
)


def _call(fn, body, principal):
    try:
        return fn(body, principal)
    except (
        GraphObjectAuthoringError,
        WorldGraphProjectionServiceError,
        service.TransitionRefused,
        DungeonBuddyDescriptorError,
        KnowledgeProfileTransitionIntegrityError,
        KnowledgePublicationIdempotencyConflictError,
        KnowledgeStaleParentRevisionError,
        PersistenceIntegrityError,
        KnowledgePublicationOutcomeUnknownError,
        PersistenceUnavailableError,
        ImmutableRevisionConflictError,
        ValueError,
    ) as exc:
        unknown = isinstance(exc, KnowledgePublicationOutcomeUnknownError)
        unavailable = isinstance(exc, PersistenceUnavailableError) or (
            isinstance(
                exc, (GraphObjectAuthoringError, WorldGraphProjectionServiceError)
            )
            and exc.status_code == 503
        )
        code = getattr(
            exc,
            "code",
            "profile_transition_unavailable"
            if unavailable
            else "profile_transition_integrity_error",
        )
        raise HTTPException(
            503 if unknown or unavailable else getattr(exc, "status_code", 409),
            detail={
                "code": code,
                "outcome_unknown": unknown,
                "retry_original_packet": isinstance(body, ProfileTransitionConfirm)
                and (unknown or unavailable),
                "message": "The exact profile transition could not be completed.",
            },
        ) from None


@router.post("/prepare")
def prepare(
    body: ProfileTransitionPrepare, principal=Depends(native_graph_explorer_dependency)
):
    return _call(service.prepare, body, principal)


@router.post("/confirm")
def confirm(
    body: ProfileTransitionConfirm, principal=Depends(native_graph_explorer_dependency)
):
    return _call(service.confirm, body, principal)
