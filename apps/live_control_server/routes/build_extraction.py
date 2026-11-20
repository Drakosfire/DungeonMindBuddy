"""Saved Build extraction routes shared by local and hosted Buddy."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.exact_run_candidate_projection import ExactRunCandidateProjection
from apps.live_control_server.services.native_recap_source_admission import public_run

router = APIRouter(tags=["build-extraction"])


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
def post_extraction_run(body: dict[str, Any], request: Request = None) -> dict[str, Any]:
    """Launch an exact extraction run for a committed worldbuilding source revision."""
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import require_hosted_build_native_source
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

    def authorize_world(world_id: str | None) -> None:
        require_hosted_build_native_source(request, world_id or "")

    hosted = hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT
    if hosted:
        authorize_world(record.world_id)
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
            authorize_world=authorize_world if hosted else None,
        )
    except SourceArtifactRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    if hosted:
        authorize_world(artifact.world_id)
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

    if hosted:
        authorize_world(artifact.world_id)
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
