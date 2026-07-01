"""Graph preview read API for /plan toolbox projection."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

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
from apps.live_control_server.services.union_supergraph_projection_adapter import (
    build_recap_only_projection_payload,
    build_plan_union_supergraph_projection_payload,
)
from apps.live_control_server.services.graph_gold_review import (
    GoldReviewCompareResponse,
    GoldReviewEvidenceDiffResponse,
    GoldReviewSessionsResponse,
    GraphGoldReviewError,
    VocabularyAblationDogfoodResponse,
    build_gold_review_evidence_diff,
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
    session_id: Annotated[str, Query()],
    campaign_id: Annotated[str | None, Query()] = None,
    use_latest_graph_ingest: Annotated[bool, Query()] = False,
    allow_recap_only: Annotated[bool, Query()] = False,
    store_path: Annotated[str | None, Query()] = None,
    preview_source: Annotated[str | None, Query()] = None,
    graph_run_manifest_path: Annotated[str | None, Query()] = None,
    preview_union_store_path: Annotated[str | None, Query()] = None,
    source_recap_path: Annotated[str | None, Query()] = None,
    source_recap_sha256: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        if allow_recap_only:
            if campaign_id is None:
                raise ValueError("campaign_id is required when allow_recap_only=true")
            return build_recap_only_projection_payload(
                campaign_id=campaign_id,
                session_id=session_id,
            )
        resolved_manifest_path = graph_run_manifest_path
        if resolved_manifest_path is None and use_latest_graph_ingest:
            if campaign_id is None:
                raise ValueError(
                    "campaign_id is required when use_latest_graph_ingest=true"
                )
            latest = resolve_latest_preview_union_graph_ingest_run(
                repo_root(),
                campaign_id=campaign_id,
                session_id=session_id,
                source_recap_path=source_recap_path,
                source_recap_sha256=source_recap_sha256,
            )
            resolved_manifest_path = latest.manifest_path
        return build_plan_union_supergraph_projection_payload(
            session_id=session_id,
            store_path=Path(store_path) if store_path else None,
            preview_source=preview_source,
            graph_run_manifest_path=(
                Path(resolved_manifest_path) if resolved_manifest_path else None
            ),
            preview_union_store_path=(
                Path(preview_union_store_path) if preview_union_store_path else None
            ),
        )
    except GraphIngestRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
