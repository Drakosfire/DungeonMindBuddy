"""Authenticated bounded dossier standing, using the ordinary native GM principal."""

from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.routing import APIRoute
from apps.live_control_server.models.registry_standing import (
    SourceRequest,
    PrepareRequest,
    ConfirmRequest,
)
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    native_graph_gm_dependency,
)
from apps.live_control_server.services import registry_standing as service


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class StrictJSONRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def strict(request: Request):
            try:
                json.loads(
                    await request.body(),
                    object_pairs_hook=_unique,
                    parse_constant=lambda _: (_ for _ in ()).throw(
                        ValueError("nonfinite JSON")
                    ),
                )
            except (ValueError, UnicodeDecodeError):
                raise HTTPException(
                    422, detail={"code": "invalid_standing_json"}
                ) from None
            return await handler(request)

        return strict


router = APIRouter(
    prefix="/api/live/extract-promote/registry-standing",
    tags=["registry-standing"],
    route_class=StrictJSONRoute,
)


def _call(fn, body, principal):
    try:
        return fn(body, principal)
    except Exception as exc:
        # Preserve framework auth failures; owner exceptions otherwise fail closed.
        if isinstance(exc, HTTPException):
            raise
        from apps.live_control_server.services.graph_object_authoring_prepare import (
            GraphObjectAuthoringError,
        )
        from dungeonmind.domain.errors import DungeonMindError
        from worldkeeper.application.commit import (
            PreparedChangeStale,
            PreparedChangeConflict,
            PreparedChangeIntegrityFailure,
            CommitAuthorityIntegrityFailure,
            CommittedChangeOutcomeUnknown,
            CommittedChangeVerificationUnavailable,
            CommittedChangeVerificationIntegrityFailure,
        )
        from worldkeeper.application.preparation import InvalidWorldChange
        from apps.live_control_server.services.world_graph_projection import (
            WorldGraphProjectionServiceError,
        )

        if isinstance(
            exc,
            (
                ValueError,
                DungeonMindError,
                GraphObjectAuthoringError,
                InvalidWorldChange,
                PreparedChangeStale,
                PreparedChangeConflict,
                PreparedChangeIntegrityFailure,
                CommitAuthorityIntegrityFailure,
                CommittedChangeOutcomeUnknown,
                CommittedChangeVerificationUnavailable,
                CommittedChangeVerificationIntegrityFailure,
                WorldGraphProjectionServiceError,
            ),
        ):
            raise HTTPException(
                getattr(exc, "status_code", 409),
                detail={
                    "code": getattr(exc, "code", "standing_refused"),
                    "message": str(exc),
                    "retry_original_packet": bool(getattr(exc, "committed", False)),
                },
            ) from exc
        raise


@router.post("/source")
def source(
    body: SourceRequest,
    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
):
    return _call(service.source, body, principal)


@router.post("/prepare")
def prepare(
    body: PrepareRequest,
    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
):
    return _call(service.prepare, body, principal)


@router.post("/confirm")
def confirm(
    body: ConfirmRequest,
    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
):
    return _call(service.confirm, body, principal)
