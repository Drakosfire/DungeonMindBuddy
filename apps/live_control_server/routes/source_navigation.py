"""Read-only Build source-navigation resolver."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.source_navigation import BuildSourceNavigationResponse
from apps.live_control_server.services.source_navigation import (
    SourceNavigationError,
    resolve_build_source_navigation,
)

router = APIRouter(prefix="/api/live", tags=["source-navigation"])


@router.get("/source-navigation", response_model=BuildSourceNavigationResponse)
def get_source_navigation(
    source_artifact_id: Annotated[str, Query(min_length=1)],
    source_span_ref_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    try:
        result = resolve_build_source_navigation(
            repo_root(),
            source_artifact_id=source_artifact_id,
            source_span_ref_id=source_span_ref_id,
        )
    except SourceNavigationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return result.model_dump(mode="json", by_alias=True)
