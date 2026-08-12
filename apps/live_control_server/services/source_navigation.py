"""Resolve admitted graph evidence (A/S) to Build source navigation."""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.models.source_navigation import (
    BuildSourceNavigationResponse,
    SOURCE_NAVIGATION_SCHEMA,
)
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    get_source_artifact,
    load_source_span_index,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    WorkspaceDocumentRecord,
    get_workspace_document_snapshot,
)
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
from graph_memory.source_span import SourceSpanIndexEntry


class SourceNavigationError(ValueError):
    """Stable service error for source-navigation resolver boundaries."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "source_navigation_error",
        status_code: int = 404,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _normalize_sha256(value: str) -> str:
    return (value or "").removeprefix("sha256:").strip().lower()


def _require_worldbuilding_lineage(artifact: GraphMemorySourceArtifact) -> str:
    if str(artifact.source_domain) != "worldbuilding":
        raise SourceNavigationError(
            "source navigation requires a worldbuilding SourceArtifact",
            code="unsupported_source_domain",
            status_code=422,
        )
    document_id = (artifact.workspace_document_id or "").strip()
    if not document_id:
        raise SourceNavigationError(
            "SourceArtifact is missing workspace_document_id lineage",
            code="missing_workspace_lineage",
            status_code=422,
        )
    return document_id


def _find_span_entry(
    spans: tuple[SourceSpanIndexEntry, ...],
    source_span_ref_id: str,
) -> SourceSpanIndexEntry:
    cleaned = source_span_ref_id.strip()
    if not cleaned:
        raise SourceNavigationError(
            "source_span_ref_id is required",
            code="missing_source_span",
            status_code=422,
        )
    for span in spans:
        if span.source_span_id == cleaned:
            return span
    raise SourceNavigationError(
        f"source span not found for artifact: {cleaned}",
        code="source_span_not_found",
        status_code=404,
    )


def _validate_workspace_lineage(
    artifact: GraphMemorySourceArtifact,
    record: WorkspaceDocumentRecord,
) -> None:
    if record.kind != "worldbuilding_source":
        raise SourceNavigationError(
            "workspace document is not an active worldbuilding_source",
            code="workspace_lineage_mismatch",
            status_code=422,
        )
    if record.status != "active":
        raise SourceNavigationError(
            "workspace document is not active",
            code="workspace_lineage_mismatch",
            status_code=409,
        )

    artifact_world = (artifact.world_id or "").strip()
    artifact_campaign = (artifact.campaign_id or "").strip()
    if not artifact_world:
        raise SourceNavigationError(
            "SourceArtifact is missing world_id lineage",
            code="workspace_lineage_mismatch",
            status_code=422,
        )

    record_world = (record.world_id or "").strip()
    record_campaign = (record.campaign_id or "").strip()
    effective_record_world = record_world or record_campaign
    if artifact_world != effective_record_world:
        raise SourceNavigationError(
            "workspace document world_id disagrees with SourceArtifact world_id",
            code="workspace_lineage_mismatch",
            status_code=409,
        )
    if artifact_campaign and record_campaign and artifact_campaign != record_campaign:
        raise SourceNavigationError(
            "workspace document campaign_id disagrees with SourceArtifact campaign_id",
            code="workspace_lineage_mismatch",
            status_code=409,
        )


def resolve_build_source_navigation(
    root: Path,
    *,
    source_artifact_id: str,
    source_span_ref_id: str,
) -> BuildSourceNavigationResponse:
    """Re-resolve A/S server-side and classify exact vs stale Build landing."""
    cleaned_artifact_id = source_artifact_id.strip()
    if not cleaned_artifact_id:
        raise SourceNavigationError(
            "source_artifact_id is required",
            code="missing_source_artifact",
            status_code=422,
        )

    try:
        artifact = get_source_artifact(root, cleaned_artifact_id)
    except SourceArtifactRegistryError as exc:
        raise SourceNavigationError(
            str(exc),
            code="source_artifact_not_found",
            status_code=exc.status_code,
        ) from exc

    document_id = _require_worldbuilding_lineage(artifact)

    try:
        index = load_source_span_index(root, cleaned_artifact_id)
    except SourceArtifactRegistryError as exc:
        raise SourceNavigationError(
            str(exc),
            code="source_span_index_error",
            status_code=exc.status_code,
        ) from exc

    span = _find_span_entry(index.spans, source_span_ref_id)

    try:
        snapshot = get_workspace_document_snapshot(root, document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise SourceNavigationError(
            str(exc),
            code="workspace_document_error",
            status_code=exc.status_code,
        ) from exc

    _validate_workspace_lineage(artifact, snapshot.record)

    artifact_digest = _normalize_sha256(artifact.content_sha256 or "")
    current_digest = _normalize_sha256(snapshot.content_sha256)
    artifact_revision = int(artifact.workspace_document_revision or 0)
    current_revision = int(snapshot.loaded_revision)

    if artifact_digest and current_digest and artifact_digest == current_digest:
        status = "exact"
        can_highlight = True
        message = "Current saved source matches the admitted artifact revision."
        diagnostics = ["digest_match"]
    else:
        status = "stale"
        can_highlight = False
        message = (
            "Current saved source differs from the admitted artifact revision; "
            "highlight is disabled."
        )
        diagnostics = ["digest_mismatch"]

    return BuildSourceNavigationResponse(
        schema_=SOURCE_NAVIGATION_SCHEMA,
        status=status,
        source_artifact_id=artifact.source_artifact_id,
        source_span_ref_id=span.source_span_id,
        document_id=document_id,
        world_id=(artifact.world_id or "").strip(),
        campaign_id=(artifact.campaign_id or "").strip(),
        artifact_document_revision=artifact_revision,
        current_document_revision=current_revision,
        artifact_content_sha256=artifact_digest,
        current_content_sha256=current_digest,
        start_line=span.start_line,
        end_line=span.end_line,
        can_highlight=can_highlight,
        message=message,
        diagnostics=diagnostics,
    )
