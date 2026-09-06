"""Graph preview read API for /plan toolbox projection."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_ingest_run_registry import (
    GraphIngestLatestRunResponse,
    GraphIngestRunRegistryError,
    GraphIngestRunsResponse,
    discover_graph_ingest_runs,
    resolve_latest_preview_union_graph_ingest_run,
)
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
from apps.live_control_server.services.graph_gold_authoring_prepare import (
    GraphGoldAuthoringPrepareRequest,
    GraphGoldAuthoringPrepareResponse,
    prepare_graph_gold_authoring_preview,
)
from apps.live_control_server.services.graph_gold_authoring_commit import (
    GraphGoldAuthoringCommitRequest,
    GraphGoldAuthoringCommitResponse,
    commit_graph_gold_authoring_preview,
)
from apps.live_control_server.services.graph_gold_authoring_verify import (
    GraphGoldAuthoringVerifyCommitRequest,
    GraphGoldAuthoringVerifyCommitResponse,
    verify_graph_gold_authoring_commit,
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


@router.get("/extraction-runs")
def get_extraction_runs_catalog() -> dict[str, Any]:
    """Canonical APP-STATE ExtractionRun catalog. File registry is not consulted."""
    from apps.live_control_server.services.ingest_run_catalog import (
        IngestRunCatalogError,
        list_canonical_extraction_runs,
    )

    try:
        return list_canonical_extraction_runs()
    except IngestRunCatalogError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/extraction-runs/{run_id}")
def get_extraction_run_by_id(run_id: str) -> dict[str, Any]:
    """Exact ExtractionRun reload. Source-domain neutral; never substitutes latest.

    Works for recap and worldbuilding runs. Build-specific workspace lineage lives
    on ``GET /extraction-runs/{run_id}/build-context``.
    """
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_extraction_run,
    )

    try:
        run = get_extraction_run(repo_root(), run_id)
    except GraphRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return run.model_dump(mode="json")


@router.get("/extraction-runs/{run_id}/recap-inspection")
def get_extraction_run_recap_inspection(run_id: str) -> dict[str, Any]:
    """Exact-run historical recap source inspection. Read-only; never substitutes latest."""
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_historical_recap_inspection,
    )

    try:
        response = get_historical_recap_inspection(repo_root(), run_id)
    except GraphRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json", by_alias=True)


@router.get("/extraction-runs/{run_id}/build-context")
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

    root = repo_root()
    try:
        run = get_extraction_run(root, run_id)
    except GraphRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    try:
        artifact = get_source_artifact(root, run.source_artifact_id)
    except SourceArtifactRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

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
            "/ingest"
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
        "run": run.model_dump(mode="json"),
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
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE_ID,
        WORLDBUILDING_PROFILE_VERSION,
    )
    from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
        WORLDBUILDING_PLUMBING_PROFILE_ID,
        WORLDBUILDING_PLUMBING_PROFILE_VERSION,
    )

    _ALLOWED_BUILD_PROFILES = {
        (WORLDBUILDING_PROFILE_ID, WORLDBUILDING_PROFILE_VERSION),
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
    if not record.target_relpath:
        raise HTTPException(status_code=422, detail="workspace document has no target_relpath")

    try:
        artifact = create_source_artifact_from_workspace_document(
            root,
            document_id=document_id,
            expected_revision=expected_revision,
            expected_content_sha256=expected_content_sha256,
        )
    except SourceArtifactRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    result = run_worldbuilding_production_extraction(
        repo_root=root,
        source_artifact_id=artifact.source_artifact_id,
        profile_id=profile_id,
        profile_version=profile_version,
        allow_llm=True,
        output_dir=root
        / "out"
        / "graph_memory"
        / "runs"
        / "extraction"
        / artifact.source_artifact_id.replace(":", "_"),
    )

    content_sha256 = artifact.content_sha256 or expected_content_sha256.removeprefix("sha256:").strip().lower()
    return {
        "schema_version": "dmb_extraction_run_launch_v1",
        "run": result.run.model_dump(mode="json"),
        "source_artifact_id": artifact.source_artifact_id,
        "document_id": record.document_id,
        "document_revision": record.revision,
        "source_content_sha256": content_sha256,
        "failure_kind": result.failure_kind,
        "diagnostics": result.diagnostics,
        "graph_review_handoff": {
            "href": (
                "/ingest"
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


@router.post("/gold-authoring/prepare", response_model=GraphGoldAuthoringPrepareResponse)
def post_gold_authoring_prepare(
    request: GraphGoldAuthoringPrepareRequest,
) -> dict[str, Any]:
    try:
        response = prepare_graph_gold_authoring_preview(request, root=repo_root())
    except GraphGoldReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.post("/gold-authoring/commit", response_model=GraphGoldAuthoringCommitResponse)
def post_gold_authoring_commit(
    request: GraphGoldAuthoringCommitRequest,
) -> dict[str, Any]:
    try:
        response = commit_graph_gold_authoring_preview(request, root=repo_root())
    except GraphGoldReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.post("/gold-authoring/verify-commit", response_model=GraphGoldAuthoringVerifyCommitResponse)
def post_gold_authoring_verify_commit(
    request: GraphGoldAuthoringVerifyCommitRequest,
) -> dict[str, Any]:
    try:
        response = verify_graph_gold_authoring_commit(request, root=repo_root())
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
