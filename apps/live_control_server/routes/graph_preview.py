"""Graph preview read API for /plan toolbox projection."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_preview_surface import (
    GraphPreviewRunsResponse,
    GraphPreviewSurfaceResponse,
    RecapGraphPresentationResponse,
    build_graph_preview_surface,
    build_latest_graph_preview_surface,
    build_recap_graph_presentation,
    discover_graph_preview_runs,
    GraphPreviewSurfaceError,
)
from apps.live_control_server.services.union_supergraph_projection_adapter import (
    build_plan_union_supergraph_projection_payload,
)
from apps.live_control_server.services.recap_artifacts import (
    RecapArtifactRegistryError,
    RecapArtifactsListResponse,
    ensure_recap_artifacts_registry,
    list_recap_artifact_records,
)

router = APIRouter(prefix="/api/live/graph-preview", tags=["graph-preview"])


@router.get("/artifacts", response_model=RecapArtifactsListResponse)
def get_recap_artifacts(
    campaign_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    root = repo_root()
    ensure_recap_artifacts_registry(root)
    records = list_recap_artifact_records(root, campaign_id=campaign_id)
    return RecapArtifactsListResponse(records=records).model_dump(mode="json")


@router.get("/runs", response_model=GraphPreviewRunsResponse)
def get_graph_preview_runs(
    artifact_id: Annotated[str | None, Query()] = None,
    campaign_id: Annotated[str | None, Query()] = None,
    session_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    runs = discover_graph_preview_runs(
        repo_root(),
        artifact_id=artifact_id,
        campaign_id=campaign_id,
        session_id=session_id,
    )
    return GraphPreviewRunsResponse(runs=runs).model_dump(mode="json")


@router.get("/latest", response_model=GraphPreviewSurfaceResponse)
def get_graph_preview_latest(
    run_dir: Annotated[str | None, Query()] = None,
    artifact_id: Annotated[str | None, Query()] = None,
    campaign_id: Annotated[str | None, Query()] = None,
    session_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        if run_dir:
            root = repo_root()
            ensure_recap_artifacts_registry(root)
            record = None
            if artifact_id or campaign_id or session_id:
                from apps.live_control_server.services.recap_artifacts import resolve_recap_artifact_record

                record = resolve_recap_artifact_record(
                    root,
                    artifact_id=artifact_id,
                    campaign_id=campaign_id,
                    session_id=session_id,
                )
            response = build_graph_preview_surface(
                root,
                run_dir,
                run_bundle_dir=root / record.run_bundle_uri if record else None,
                artifact_record=record,
            )
        else:
            response = build_latest_graph_preview_surface(
                repo_root(),
                artifact_id=artifact_id,
                campaign_id=campaign_id,
                session_id=session_id,
            )
    except (GraphPreviewSurfaceError, RecapArtifactRegistryError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.get("/union-supergraph/projection")
def get_union_supergraph_projection(
    session_id: Annotated[str, Query()],
    store_path: Annotated[str | None, Query()] = None,
    preview_source: Annotated[str | None, Query()] = None,
    graph_run_manifest_path: Annotated[str | None, Query()] = None,
    preview_union_store_path: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        return build_plan_union_supergraph_projection_payload(
            session_id=session_id,
            store_path=Path(store_path) if store_path else None,
            preview_source=preview_source,
            graph_run_manifest_path=(
                Path(graph_run_manifest_path) if graph_run_manifest_path else None
            ),
            preview_union_store_path=(
                Path(preview_union_store_path) if preview_union_store_path else None
            ),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recap", response_model=RecapGraphPresentationResponse)
def get_recap_graph_presentation(
    run_dir: Annotated[str | None, Query()] = None,
    artifact_id: Annotated[str | None, Query()] = None,
    campaign_id: Annotated[str | None, Query()] = None,
    session_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        response = build_recap_graph_presentation(
            repo_root(),
            run_dir,
            artifact_id=artifact_id,
            campaign_id=campaign_id,
            session_id=session_id,
        )
    except (GraphPreviewSurfaceError, RecapArtifactRegistryError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")
