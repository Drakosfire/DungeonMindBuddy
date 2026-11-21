"""Graph preview read API for /plan toolbox projection."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from uuid import UUID
from apps.live_control_server.models.build_recap_launch import BuildRecapLaunchRequest
from apps.live_control_server.models.saved_recap_runs import SavedRecapRunsResponse, SavedRecapSourceResponse
from fastapi.responses import JSONResponse

from apps.live_control_server.config import repo_root
from apps.live_control_server.routes.build_extraction import get_extraction_run_build_context, router as build_extraction_router
from apps.live_control_server.models.historical_recap_projection import (
    HistoricalRecapWorldProjectionResponse,
)
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm, native_graph_gm_dependency
from apps.live_control_server.services.graph_ingest_run_registry import (
    GraphIngestLatestRunResponse,
    GraphIngestRunRegistryError,
    GraphIngestRunsResponse,
    discover_graph_ingest_runs,
    resolve_latest_preview_union_graph_ingest_run,
)
from apps.live_control_server.services.graph_preview_surface import (
    GraphPreviewSurfaceResponse,
    RecapGraphPresentationResponse,
    build_graph_preview_surface,
    build_latest_graph_preview_surface,
    build_recap_graph_presentation,
    GraphPreviewSurfaceError,
)
from apps.live_control_server.services.graph_existing_object_resolver import (
    GraphReviewExistingObjectResolverRequest,
    GraphReviewExistingObjectResolverResponse,
    resolve_existing_object_candidates,
)
from apps.live_control_server.services.graph_gold_review import (
    GoldReviewCompareResponse,
    GoldReviewEvidenceDiffResponse,
    GoldReviewSessionsResponse,
    GraphGoldReviewError,
    GoldGraphProjectionResponse,
    VocabularyAblationDogfoodResponse,
    build_gold_review_evidence_diff,
    build_gold_graph_projection,
    compare_gold_review,
    discover_gold_review_sessions,
    load_vocabulary_ablation_dogfood,
)
from apps.live_control_server.services.graph_manual_review import (
    GraphManualReviewError,
    ManualReviewBedDetail,
    ManualReviewBedsResponse,
    discover_manual_review_beds,
    load_manual_review_bed,
)
from apps.live_control_server.services.recap_artifacts import (
    RecapArtifactRegistryError,
    RecapArtifactsListResponse,
    ensure_recap_artifacts_registry,
    list_recap_artifact_records,
)

router = APIRouter(prefix="/api/live/graph-preview", tags=["graph-preview"])


def _reject_query_params(request: Request) -> None:
    if request.query_params:
        names = ", ".join(sorted(request.query_params.keys()))
        raise HTTPException(
            status_code=422,
            detail=f"exact-run route does not accept query parameters: {names}",
        )


@router.get("/artifacts", response_model=RecapArtifactsListResponse)
def get_recap_artifacts(
    campaign_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    root = repo_root()
    ensure_recap_artifacts_registry(root)
    records = list_recap_artifact_records(root, campaign_id=campaign_id)
    return RecapArtifactsListResponse(records=records).model_dump(mode="json")


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
                from apps.live_control_server.services.recap_artifacts import (
                    resolve_recap_artifact_record,
                )

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


@router.get("/graph-ingest/runs", response_model=GraphIngestRunsResponse)
def get_graph_ingest_runs(
    campaign_id: Annotated[str | None, Query()] = None,
    session_id: Annotated[str | None, Query()] = None,
    source_recap_path: Annotated[str | None, Query()] = None,
    source_recap_sha256: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    require_preview_union_store: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    try:
        runs = discover_graph_ingest_runs(
            repo_root(),
            campaign_id=campaign_id,
            session_id=session_id,
            source_recap_path=source_recap_path,
            source_recap_sha256=source_recap_sha256,
            status=status,
            require_preview_union_store=require_preview_union_store,
        )
    except GraphIngestRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return GraphIngestRunsResponse(runs=runs).model_dump(mode="json")


def _saved_run_query(
    request: Request,
    required: set[str],
    optional: set[str] | frozenset[str] = frozenset(),
) -> None:
    keys = set(request.query_params)
    if (
        not required <= keys
        or not keys <= required | optional
        or any(
            len(request.query_params.getlist(key)) != 1
            or not request.query_params[key]
            or request.query_params[key] != request.query_params[key].strip()
            for key in keys
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="Exact saved-run selectors are required; duplicate or unknown selectors are not accepted.",
        )


@router.get("/extraction-runs", response_model=SavedRecapRunsResponse)
def get_saved_recap_runs(
    request: Request,
    managed_world_id: Annotated[str, Query(min_length=1)],
    campaign_id: Annotated[str | None, Query(min_length=1)] = None,
):
    from apps.live_control_server.services.ingest_run_catalog import list_saved_recap_runs
    from apps.live_control_server.services.hosted_native_graph_access import require_saved_recap_access

    require_saved_recap_access(request, managed_world_id)
    _saved_run_query(request, {"managed_world_id"}, {"campaign_id"})
    return _saved_run_response(
        lambda: list_saved_recap_runs(
            root=repo_root(),
            managed_world_id=managed_world_id,
            campaign_id=campaign_id,
        )
    )


def _saved_run_response(read):
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.ingest_run_catalog import (
        IngestRunCatalogError,
    )
    from apps.live_control_server.services.world_graph_projection import (
        WorldGraphProjectionServiceError,
    )

    try:
        result = read()
    except (
        ApplicationStateError,
        IngestRunCatalogError,
        WorldGraphProjectionServiceError,
    ) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return JSONResponse(
        result.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/extraction-runs/{run_id}/recap-inspection",
    response_model=SavedRecapSourceResponse,
)
def get_extraction_run_recap_inspection(
    run_id: str,
    request: Request,
    managed_world_id: Annotated[str, Query(min_length=1)],
    expected_run_revision: Annotated[int, Query(gt=0)],
    source_revision_id: Annotated[UUID, Query()],
):
    from apps.live_control_server.services.ingest_run_catalog import read_saved_recap_source
    from apps.live_control_server.services.hosted_native_graph_access import require_saved_recap_access

    require_saved_recap_access(request, managed_world_id)
    _saved_run_query(
        request, {"managed_world_id", "expected_run_revision", "source_revision_id"}
    )
    return _saved_run_response(
        lambda: read_saved_recap_source(
            root=repo_root(),
            run_id=run_id,
            managed_world_id=managed_world_id,
            expected_run_revision=expected_run_revision,
            source_revision_id=source_revision_id,
        )
    )


@router.get(
    "/extraction-runs/{run_id}/recap-projection",
    response_model=HistoricalRecapWorldProjectionResponse,
)
def get_extraction_run_recap_projection(
    run_id: str,
    request: Request,
    response_context: Response,
) -> dict[str, Any]:
    """Project exact durable recap text onto the current governed World.

    An optional managed_world_id constrains the current managed World selected
    by the caller. It never supplies native Graph authority.
    """
    allowed_query_names = {"managed_world_id"}
    unknown_query_names = sorted(set(request.query_params.keys()) - allowed_query_names)
    if unknown_query_names:
        names = ", ".join(unknown_query_names)
        raise HTTPException(
            status_code=422,
            detail=f"exact-run route does not accept query parameters: {names}",
        )
    managed_world_ids = request.query_params.getlist("managed_world_id")
    if len(managed_world_ids) > 1:
        raise HTTPException(
            status_code=422,
            detail="exact-run route accepts one managed_world_id selector",
        )
    managed_world_id = managed_world_ids[0] if managed_world_ids else None
    from apps.live_control_server.services.historical_recap_world_projection import (
        HistoricalRecapProjectionError,
        build_historical_recap_world_projection,
    )

    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import require_saved_recap_access

    hosted = hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT
    if hosted:
        require_saved_recap_access(request, managed_world_id or "")
    try:
        response = build_historical_recap_world_projection(
            repo_root(),
            run_id,
            managed_world_id=managed_world_id,
        )
    except HistoricalRecapProjectionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": str(exc),
                "diagnostics": [item.model_dump(mode="json") for item in exc.diagnostics],
            },
        ) from exc
    result = response.model_dump(mode="json", by_alias=True)
    if hosted:
        require_saved_recap_access(request, response.managed_world_id or "")
        response_context.headers["Cache-Control"] = "no-store"
    return result


@router.get("/graph-ingest/latest", response_model=GraphIngestLatestRunResponse)
def get_latest_graph_ingest_run(
    campaign_id: Annotated[str, Query()],
    session_id: Annotated[str, Query()],
    source_recap_path: Annotated[str | None, Query()] = None,
    source_recap_sha256: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        run = resolve_latest_preview_union_graph_ingest_run(
            repo_root(),
            campaign_id=campaign_id,
            session_id=session_id,
            source_recap_path=source_recap_path,
            source_recap_sha256=source_recap_sha256,
        )
    except GraphIngestRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return GraphIngestLatestRunResponse(run=run).model_dump(mode="json")


@router.get("/union-supergraph/projection")
def get_union_supergraph_projection(
    plan_id: Annotated[str | None, Query()] = None,
    campaign_rel: Annotated[str | None, Query()] = None,
    run_id: Annotated[str | None, Query()] = None,
    audience: Annotated[str | None, Query()] = None,
) -> JSONResponse:
    _ = (plan_id, campaign_rel, run_id, audience)
    return JSONResponse(
        status_code=410,
        content={
            "detail": {
                "code": "union_supergraph_preview_retired",
                "message": (
                    "UnionSupergraph store preview is retired. "
                    "Retained graph-preview extraction/gold/manual/recap routes remain."
                ),
            }
        },
    )

@router.post("/existing-object-resolver/candidates", response_model=GraphReviewExistingObjectResolverResponse)
def post_existing_object_resolver_candidates(
    request: GraphReviewExistingObjectResolverRequest,
) -> dict[str, Any]:
    try:
        response = resolve_existing_object_candidates(request, root=repo_root())
    except GraphGoldReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.get("/gold-review/sessions", response_model=GoldReviewSessionsResponse)
def get_gold_review_sessions() -> dict[str, Any]:
    sessions = discover_gold_review_sessions(repo_root())
    return GoldReviewSessionsResponse(sessions=sessions).model_dump(mode="json")


@router.get("/gold-review/compare", response_model=GoldReviewCompareResponse)
def get_gold_review_compare(
    campaign_id: Annotated[str, Query()],
    session_id: Annotated[str, Query()],
    manifest_path: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        response = compare_gold_review(
            campaign_id=campaign_id,
            session_id=session_id,
            manifest_path=manifest_path,
            root=repo_root(),
        )
    except GraphGoldReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.get("/gold-review/evidence", response_model=GoldReviewEvidenceDiffResponse)
def get_gold_review_evidence(
    campaign_id: Annotated[str, Query()],
    session_id: Annotated[str, Query()],
    object_kind: Annotated[str, Query()],
    object_id: Annotated[str, Query()],
    manifest_path: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        response = build_gold_review_evidence_diff(
            campaign_id=campaign_id,
            session_id=session_id,
            object_kind=object_kind,
            object_id=object_id,
            manifest_path=manifest_path,
            root=repo_root(),
        )
    except GraphGoldReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.get("/gold-review/projection", response_model=GoldGraphProjectionResponse)
def get_gold_review_projection(
    campaign_id: Annotated[str, Query()],
    session_id: Annotated[str, Query()],
    fixture_version: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        response = build_gold_graph_projection(
            campaign_id=campaign_id,
            session_id=session_id,
            fixture_version=fixture_version,
            root=repo_root(),
        )
    except GraphGoldReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.get("/gold-review/vocabulary-ablation", response_model=VocabularyAblationDogfoodResponse)
def get_gold_review_vocabulary_ablation(
    campaign_id: Annotated[str, Query()],
    session_id: Annotated[str, Query()],
) -> dict[str, Any]:
    try:
        response = load_vocabulary_ablation_dogfood(
            campaign_id=campaign_id,
            session_id=session_id,
            root=repo_root(),
        )
    except GraphGoldReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.get("/manual-review/beds", response_model=ManualReviewBedsResponse)
def get_manual_review_beds() -> dict[str, Any]:
    try:
        response = discover_manual_review_beds(repo_root())
    except GraphManualReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.get("/manual-review/beds/{bed_id}", response_model=ManualReviewBedDetail)
def get_manual_review_bed(bed_id: str) -> dict[str, Any]:
    try:
        response = load_manual_review_bed(repo_root(), bed_id)
    except GraphManualReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


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


@router.post("/build-recap-launches")
def post_build_recap_launch(request: Request, body: BuildRecapLaunchRequest) -> dict[str, Any]:
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    from apps.live_control_server.services.build_recap_launch import launch_build_recap
    from apps.live_control_server.services.hosted_native_graph_access import require_hosted_build_native_source

    hosted = hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS
    if hosted:
        if request.query_params:
            raise HTTPException(status_code=403, detail="Unexpected recap launch query")
        require_hosted_build_native_source(request, body.managed_world_id)
    else:
        enforce_native_graph_gm(request)
    def authorize() -> None:
        require_hosted_build_native_source(request, body.managed_world_id)

    try:
        run = launch_build_recap(repo_root(), body, authorize=authorize if hosted else None)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=getattr(exc,"status_code",503),detail=str(exc)) from exc
    context = get_extraction_run_build_context(run.run_id)
    if hosted:
        require_hosted_build_native_source(request, body.managed_world_id)
    return context


@router.get("/build-recap-launches/{request_id}")
def get_build_recap_launch(request: Request, request_id: UUID, document_id: UUID, managed_world_id: str) -> dict[str, Any]:
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import require_hosted_build_native_source
    from apps.live_control_server.services.build_recap_launch import recover_build_recap_launch

    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        enforce_native_graph_gm(request)
    else:
        require_hosted_build_native_source(request, managed_world_id)
    try:
        run = recover_build_recap_launch(repo_root(),request_id=request_id,document_id=document_id,managed_world_id=managed_world_id)
    except Exception as exc:
        raise HTTPException(status_code=getattr(exc,"status_code",503),detail=str(exc)) from exc
    context = get_extraction_run_build_context(run.run_id)
    if context["document_id"] != str(document_id):
        raise HTTPException(status_code=409, detail="Saved recap launch does not match this document")
    require_hosted_build_native_source(request, managed_world_id)
    return context


@router.get("/extraction-runs/{run_id}/usage")
def get_extraction_usage(run_id: str, request: Request,
    managed_world_id: Annotated[str, Query(min_length=1)],
    expected_run_revision: Annotated[int, Query(gt=0)]):
    from apps.live_control_server.services.extraction_usage import read_extraction_usage
    from apps.live_control_server.services.hosted_native_graph_access import require_saved_recap_access

    require_saved_recap_access(request, managed_world_id)
    _saved_run_query(request, {"managed_world_id", "expected_run_revision"})
    response = _saved_run_response(lambda: read_extraction_usage(root=repo_root(),run_id=run_id,
        managed_world_id=managed_world_id,expected_run_revision=expected_run_revision))
    require_saved_recap_access(request, managed_world_id)
    return response

router.include_router(build_extraction_router)
