"""Graph preview read API for /plan toolbox projection."""

from __future__ import annotations

from apps.live_control_server.services.native_recap_source_admission import public_run

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from uuid import UUID
from apps.live_control_server.models.build_recap_launch import BuildRecapLaunchRequest
from apps.live_control_server.models.saved_recap_runs import SavedRecapRunsResponse, SavedRecapSourceResponse
from fastapi.responses import JSONResponse

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.exact_run_candidate_projection import (
    ExactRunCandidateProjection,
)
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


@router.get("/extraction-runs/{run_id}")
def get_extraction_run_by_id(run_id: str, request: Request = None) -> dict[str, Any]:
    """Exact ExtractionRun reload. Source-domain neutral; never substitutes latest.

    Works for recap and worldbuilding runs. Build-specific workspace lineage lives
    on ``GET /extraction-runs/{run_id}/build-context``.
    """
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import read_hosted_exact_extraction

    if request is not None and hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        return read_hosted_exact_extraction(request, run_id)

    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_extraction_run,
    )

    try:
        run = get_extraction_run(run_id)
    except GraphRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return public_run(run)


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
    "/extraction-runs/{run_id}/candidate-projection",
    response_model=ExactRunCandidateProjection,
)
def get_extraction_run_candidate_projection(
    run_id: str,
    request: Request,
):
    """Read exact frozen candidate prose; never admit or publish domain data."""
    from apps.live_control_server.services.hosted_native_graph_access import require_saved_recap_access
    require_saved_recap_access(request, request.query_params.get("managed_world_id", ""))
    if set(request.query_params) != {"managed_world_id"} or len(
        request.query_params.getlist("managed_world_id")
    ) != 1:
        raise HTTPException(
            status_code=422,
            detail="One managed_world_id selector is required; no other selectors are accepted.",
        )
    managed = request.query_params["managed_world_id"]
    if not managed or managed != managed.strip():
        raise HTTPException(
            status_code=422, detail="managed_world_id must be nonblank and trimmed."
        )
    from apps.live_control_server.services.exact_run_candidate_projection import (
        CandidateProjectionError,
        build_exact_run_candidate_projection,
    )

    try:
        result = build_exact_run_candidate_projection(repo_root(), run_id, managed)
    except CandidateProjectionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return JSONResponse(
        result.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
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
    """Retired visualization; saved source/candidate and receipt APIs remain."""
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
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import require_saved_recap_access

    hosted = hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT
    if hosted:
        require_saved_recap_access(request, managed_world_id or "")
    raise HTTPException(
        status_code=410,
        detail={
            "code": "exact_run_graph_retired",
            "message": "Historical graph visualization is retired. Open the saved source or extracted candidates.",
        },
    )


@router.get("/extraction-runs/{run_id}/build-context")
async def read_extraction_run_build_context(run_id: str, request: Request) -> dict[str, Any]:
    from starlette.concurrency import run_in_threadpool

    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import read_hosted_extraction_build_context

    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return await run_in_threadpool(get_extraction_run_build_context, run_id)
    return await read_hosted_extraction_build_context(request, run_id, _build_extraction_context)


def get_extraction_run_build_context(run_id: str) -> dict[str, Any]:
    """Build-only exact-run envelope with server-resolved workspace lineage.

    Requires SourceArtifact workspace_document_id/revision/content_sha256.
    Recap runs without that lineage fail explicitly; generic exact GET remains usable.
    Never substitutes latest.
    """
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_extraction_run,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        get_source_artifact,
    )

    try:
        run = get_extraction_run(run_id)
    except GraphRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    try:
        artifact = get_source_artifact(run.source_artifact_id)
    except SourceArtifactRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return _build_extraction_context(run, artifact)


def _build_extraction_context(run, artifact) -> dict[str, Any]:
    document_id = artifact.workspace_document_id
    document_revision = artifact.workspace_document_revision
    content_sha256 = artifact.content_sha256
    if not document_id or document_revision is None or not content_sha256:
        raise HTTPException(
            status_code=422,
            detail=(
                "Build context requires workspace document lineage; "
                "this exact run is not applicable to Build "
                f"(source_domain={run.source_domain})"
            ),
        )

    handoff = {
        "href": (
            "/build"
            f"?extractionRunId={run.run_id}"
            f"&sourceArtifactId={artifact.source_artifact_id}"
            f"&documentId={document_id}"
            f"&revision={document_revision}"
        ),
        "extraction_run_id": run.run_id,
        "source_artifact_id": artifact.source_artifact_id,
        "document_id": document_id,
        "document_revision": document_revision,
    }
    return {
        "schema_version": "dmb_extraction_run_status_v1",
        "run": public_run(run),
        "source_artifact_id": artifact.source_artifact_id,
        "document_id": document_id,
        "document_revision": document_revision,
        "source_content_sha256": content_sha256,
        "graph_review_handoff": handoff,
    }


@router.post("/extraction-runs")
def post_extraction_run(body: dict[str, Any]) -> dict[str, Any]:
    """Launch an exact extraction run for a committed worldbuilding source revision."""
    from apps.live_control_server.services.graph_preview_runner import (
        run_worldbuilding_production_extraction,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        create_source_artifact_from_workspace_document,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        WorkspaceDocumentRegistryError,
        get_workspace_document,
    )
    from graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE_ID,
        WORLDBUILDING_PROFILE_VERSION,
    )
    from graph_memory.extraction.worldbuilding_plumbing_profile import (
        WORLDBUILDING_PLUMBING_PROFILE_ID,
        WORLDBUILDING_PLUMBING_PROFILE_VERSION,
    )

    from graph_memory.extraction.worldbuilding_profile_catalog import PUBLISHABLE_WORLDBUILDING_PROFILES

    _ALLOWED_BUILD_PROFILES = {
        *(tuple(key.split("@")) for key in PUBLISHABLE_WORLDBUILDING_PROFILES),
        (WORLDBUILDING_PLUMBING_PROFILE_ID, WORLDBUILDING_PLUMBING_PROFILE_VERSION),
    }

    document_id = body.get("document_id")
    expected_revision = body.get("expected_revision")
    expected_content_sha256 = body.get("expected_content_sha256")
    # Build product default is the bounded BLD-08 profile; plumbing remains
    # explicitly selectable for compatibility.
    raw_profile_id = body.get("profile_id")
    raw_profile_version = body.get("profile_version")
    # Build launches always execute production extraction under server-owned
    # model policy. Any client-supplied allow_llm is ignored.
    if not isinstance(document_id, str) or not document_id.strip():
        raise HTTPException(status_code=422, detail="document_id is required")
    if not isinstance(expected_revision, int):
        raise HTTPException(status_code=422, detail="expected_revision must be an int")
    if not isinstance(expected_content_sha256, str) or not expected_content_sha256.strip():
        raise HTTPException(
            status_code=422,
            detail="expected_content_sha256 is required for Build extraction launch",
        )
    if raw_profile_id is None:
        profile_id = WORLDBUILDING_PROFILE_ID
    elif not isinstance(raw_profile_id, str) or not raw_profile_id.strip():
        raise HTTPException(
            status_code=422,
            detail="profile_id must be a non-empty string",
        )
    else:
        profile_id = raw_profile_id.strip()
    if raw_profile_version is None:
        profile_version = WORLDBUILDING_PROFILE_VERSION
    elif not isinstance(raw_profile_version, str) or not raw_profile_version.strip():
        raise HTTPException(
            status_code=422,
            detail="profile_version must be a non-empty string",
        )
    else:
        profile_version = raw_profile_version.strip()
    if (profile_id, profile_version) not in _ALLOWED_BUILD_PROFILES:
        allowed = ", ".join(
            f"{pid}@{pver}" for pid, pver in sorted(_ALLOWED_BUILD_PROFILES)
        )
        raise HTTPException(
            status_code=422,
            detail=(
                f"unsupported extraction profile {profile_id}@{profile_version}; "
                f"use one of: {allowed}"
            ),
        )

    root = repo_root()
    try:
        record = get_workspace_document(root, document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    if record.content_status != "committed":
        raise HTTPException(status_code=422, detail="source must be committed before extraction")
    if record.revision != expected_revision:
        raise HTTPException(
            status_code=409,
            detail=f"revision mismatch: expected {expected_revision}, current {record.revision}",
        )

    try:
        artifact = create_source_artifact_from_workspace_document(
            root,
            document_id=document_id,
            expected_revision=expected_revision,
            expected_content_sha256=expected_content_sha256,
        )
    except SourceArtifactRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    if (profile_id == "worldbuilding_gazetteer_v1"
            and profile_version in {"1.5", "1.6", "1.7", "1.8", "1.9", "1.10"}):
        from apps.live_control_server.services.worldbuilding_ge_execution import (
            WorldbuildingExecutionInputError,
            run_gazetteer_with_generation_engine,
        )

        try:
            result = run_gazetteer_with_generation_engine(
                repo_root=root,
                source_artifact_id=artifact.source_artifact_id,
                document_id=record.document_id,
                document_revision=record.revision,
                expected_content_sha256=expected_content_sha256,
                profile_version=profile_version,
            )
        except WorldbuildingExecutionInputError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    else:
        result = run_worldbuilding_production_extraction(
            repo_root=root,
            source_artifact_id=artifact.source_artifact_id,
            profile_id=profile_id,
            profile_version=profile_version,
            allow_llm=True,
        )

    content_sha256 = artifact.content_sha256 or expected_content_sha256.removeprefix("sha256:").strip().lower()
    return {
        "schema_version": "dmb_extraction_run_launch_v1",
        "run": public_run(result.run),
        "source_artifact_id": artifact.source_artifact_id,
        "document_id": record.document_id,
        "document_revision": record.revision,
        "source_content_sha256": content_sha256,
        "failure_kind": result.failure_kind,
        "diagnostics": result.diagnostics,
        "graph_review_handoff": {
            "href": (
                "/build"
                f"?extractionRunId={result.run.run_id}"
                f"&sourceArtifactId={artifact.source_artifact_id}"
                f"&documentId={record.document_id}"
                f"&revision={record.revision}"
            ),
            "extraction_run_id": result.run.run_id,
            "source_artifact_id": artifact.source_artifact_id,
            "document_id": record.document_id,
            "document_revision": record.revision,
        },
    }


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
