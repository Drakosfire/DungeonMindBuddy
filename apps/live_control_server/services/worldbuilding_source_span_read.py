"""Registry-backed exact worldbuilding SourceSpan reads for Hermes/graph retrieval.

Composes SourceArtifact + SourceSpanIndex integrity (same rules as Build
source-navigation) into a content-bearing World Graph source-anchor read.
Does not call the Build /source-navigation route or accept caller path authority.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from application_state.errors import ApplicationStateError
from application_state.source import service as source_service
from apps.live_control_server.config import artifact_data_root, managed_world_data_root, ManagedWorldDataRootError

from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    get_source_artifact,
    load_source_span_index,
)
from apps.live_control_server.services.source_navigation import (
    SourceNavigationError,
    _require_worldbuilding_lineage,
    _validate_workspace_lineage,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    get_workspace_document,
    get_workspace_document_snapshot,
)
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
from graph_memory.retrieval.errors import WorldGraphRetrievalError
from graph_memory.retrieval.models import (
    WorldGraphRetrievalDiagnostic,
    WorldGraphRetrievalSnapshot,
    WorldGraphRetrievalTrustBoundary,
    WorldGraphSourceAnchorReadResult,
)
from graph_memory.retrieval.source_reader import (
    SourceReadError,
    SourceReadOutcome,
    parse_repo_uri,
    read_repo_line_span_text,
)
from graph_memory.source_span import (
    SourceSpanIndex,
    SourceSpanIndexEntry,
    build_source_span_index_for_text,
    validate_source_span_index,
)


def _normalize_sha256(value: str | None) -> str:
    return (value or "").removeprefix("sha256:").strip().lower()


def _diagnostic(code: str, message: str, *, severity: str = "error") -> WorldGraphRetrievalDiagnostic:
    return WorldGraphRetrievalDiagnostic(code=code, message=message, severity=severity)  # type: ignore[arg-type]


def _raise(
    message: str,
    *,
    code: str,
    status_code: int,
) -> None:
    raise WorldGraphRetrievalError(
        message,
        code=code,
        status_code=status_code,
        diagnostics=[_diagnostic(code, message)],
    )


def _find_span_entry(
    spans: tuple[SourceSpanIndexEntry, ...],
    source_span_ref_id: str,
) -> SourceSpanIndexEntry:
    cleaned = source_span_ref_id.strip()
    if not cleaned:
        _raise(
            "source_span_ref_id is required",
            code="missing_source_span",
            status_code=422,
        )
    for span in spans:
        if span.source_span_id == cleaned:
            return span
    _raise(
        f"source span not found for artifact: {cleaned}",
        code="source_span_not_found",
        status_code=404,
    )
    raise AssertionError("unreachable")


def _trust_boundary() -> WorldGraphRetrievalTrustBoundary:
    return WorldGraphRetrievalTrustBoundary(
        can_trust=["world_graph_revision", "source_artifact_digest"],
        cannot_trust=["caller_path", "caller_source_span", "mutable_workspace_bytes"],
    )


def _read_durable_source(
    *,
    artifact: GraphMemorySourceArtifact,
    expected_digest: str,
) -> tuple[str, SourceSpanIndex] | None:
    """Load the exact immutable APP-STATE revision and derive its stable spans."""
    try:
        source = source_service.get_source_markdown(
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=expected_digest,
        )
    except ApplicationStateError:
        # Existing exact file-backed reads remain available when APP-STATE is
        # temporarily unavailable. No latest-workspace fallback is introduced.
        return None
    if source is None:
        return None

    if (
        source.source_artifact_id != artifact.source_artifact_id
        or source.source_domain != str(artifact.source_domain)
        or source.campaign_id != artifact.campaign_id
        or source.session_id != artifact.session_id
        or source.world_id != artifact.world_id
        or source.media_type != "text/markdown"
        or source.encoding.lower() != "utf-8"
    ):
        _raise(
            "Durable source identity does not match the registered Worldbuilding artifact.",
            code="source_integrity_error",
            status_code=409,
        )

    actual_digest = hashlib.sha256(source.markdown.encode("utf-8")).hexdigest()
    if actual_digest != expected_digest or source.content_sha256 != expected_digest:
        _raise(
            "Durable source bytes do not match the admitted source digest.",
            code="source_integrity_error",
            status_code=409,
        )

    try:
        index = build_source_span_index_for_text(
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=expected_digest,
            text=source.markdown,
        )
        validate_source_span_index(
            index,
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=expected_digest,
        )
    except (TypeError, ValueError) as exc:
        _raise(
            f"Durable source spans could not be reconstructed: {exc}",
            code="source_span_index_error",
            status_code=409,
        )
    return source.markdown, index


class WorldbuildingSourceReadBatch:
    """Validated immutable bodies owned by one admitted anchor-read operation.

    Metadata/lineage/scope checks still run for every span. Including the complete
    artifact in the key prevents reusing a body validated under different lineage.
    Only this loader can populate entries; failed loads are never cached.
    """

    def __init__(self) -> None:
        self._sources: dict[tuple[str, str], tuple[str, SourceSpanIndex]] = {}

    def read(self, artifact: GraphMemorySourceArtifact, digest: str) -> tuple[str, SourceSpanIndex] | None:
        key = (artifact.model_dump_json(), digest)
        if key not in self._sources:
            loaded = _read_durable_source(artifact=artifact, expected_digest=digest)
            if loaded is None:
                return None
            self._sources[key] = loaded
        return self._sources[key]


def _read_text_line_span(
    *,
    text: str,
    expected_content_sha256: str,
    start_line: int,
    end_line: int,
    max_chars: int,
) -> SourceReadOutcome:
    """Read one digest-verified span from immutable Markdown already in memory."""
    raw_bytes = text.encode("utf-8")
    actual_digest = hashlib.sha256(raw_bytes).hexdigest()
    if actual_digest != expected_content_sha256:
        raise SourceReadError(
            "Durable source content does not match the admitted digest.",
            code="source_integrity_error",
        )
    if start_line < 1 or end_line < start_line:
        raise SourceReadError("Line-span bounds are invalid.", code="unsupported_locator")
    lines = text.splitlines()
    if end_line > len(lines):
        raise SourceReadError(
            "Line-span is outside the admitted source bounds.",
            code="source_unavailable",
        )
    section_text = "\n".join(lines[start_line - 1 : end_line])
    truncated = len(section_text) > max_chars
    bounded_text = section_text[:max_chars]
    if not bounded_text:
        line_start = None
        line_end = None
    elif not truncated:
        line_start = start_line
        line_end = end_line
    else:
        line_start = start_line
        line_end = start_line + bounded_text.count("\n")
    return SourceReadOutcome(
        content=bounded_text,
        media_type="text/markdown",
        content_sha256=actual_digest,
        line_start=line_start,
        line_end=line_end,
        truncated=truncated,
    )


def _map_navigation_error(exc: SourceNavigationError) -> None:
    _raise(str(exc), code=exc.code, status_code=exc.status_code)


def _reconcile_graph_registry_scope(
    *,
    root: Path,
    artifact: GraphMemorySourceArtifact,
    snapshot: WorldGraphRetrievalSnapshot | None,
    graph_artifact: GraphMemorySourceArtifact | None,
) -> None:
    """Fail closed when registry A is not the same scoped worldbuilding source."""
    artifact_world = (artifact.world_id or "").strip()
    artifact_campaign = (artifact.campaign_id or "").strip()
    if snapshot is not None:
        if not artifact_world:
            _raise(
                "Registry SourceArtifact is missing world_id lineage.",
                code="workspace_lineage_mismatch",
                status_code=422,
            )
        resolved_world = artifact_world
        if artifact_world != snapshot.world_id:
            from apps.live_control_server.services.managed_world_graph_projection import (
                resolve_managed_world_binding, WorldGraphProjectionServiceError,
            )
            try:
                resolved_world = resolve_managed_world_binding(
                    artifact_world, root=managed_world_data_root(root)
                ).native_world_id
            except (WorldGraphProjectionServiceError, ManagedWorldDataRootError):
                _raise("Managed World binding is unavailable for this graph source.",
                       code="workspace_lineage_mismatch", status_code=409)
        if resolved_world != snapshot.world_id:
            _raise(
                "Registry SourceArtifact world_id disagrees with the graph snapshot.",
                code="workspace_lineage_mismatch",
                status_code=409,
            )
        # Cross-campaign (world-scope) reads admit campaign-owned artifacts;
        # the campaign lineage check only applies to campaign-scoped reads.
        if (
            snapshot.scope_mode != "world"
            and artifact_campaign
            and artifact_campaign != snapshot.campaign_id
        ):
            _raise(
                "Registry SourceArtifact campaign_id disagrees with the graph snapshot.",
                code="workspace_lineage_mismatch",
                status_code=409,
            )
    if graph_artifact is None:
        return
    if graph_artifact.source_artifact_id != artifact.source_artifact_id:
        _raise(
            "Graph SourceArtifact id disagrees with registry SourceArtifact id.",
            code="source_integrity_error",
            status_code=409,
        )
    graph_digest = _normalize_sha256(graph_artifact.content_sha256)
    registry_digest = _normalize_sha256(artifact.content_sha256)
    if graph_digest and registry_digest and graph_digest != registry_digest:
        _raise(
            "Graph SourceArtifact digest disagrees with registry SourceArtifact.",
            code="source_integrity_error",
            status_code=409,
        )
    graph_campaign = (graph_artifact.campaign_id or "").strip()
    if graph_campaign and artifact_campaign and graph_campaign != artifact_campaign:
        _raise(
            "Graph SourceArtifact campaign_id disagrees with registry SourceArtifact.",
            code="workspace_lineage_mismatch",
            status_code=409,
        )
    graph_world = (graph_artifact.world_id or "").strip()
    if graph_world and artifact_world and graph_world != artifact_world:
        _raise(
            "Graph SourceArtifact world_id disagrees with registry SourceArtifact.",
            code="workspace_lineage_mismatch",
            status_code=409,
        )


def read_admitted_worldbuilding_span(
    *,
    root: Path,
    source_artifact_id: str,
    source_span_ref_id: str,
    graph_content_sha256: str | None,
    max_chars: int,
    anchor_id: str,
    evidence_ref_id: str | None = None,
    snapshot: WorldGraphRetrievalSnapshot | None = None,
    graph_artifact: GraphMemorySourceArtifact | None = None,
    _source_batch: WorldbuildingSourceReadBatch | None = None,
) -> WorldGraphSourceAnchorReadResult:
    """Return exact admitted worldbuilding source text for the registered artifact."""
    cleaned_artifact_id = source_artifact_id.strip()
    cleaned_span_id = source_span_ref_id.strip()
    if not cleaned_artifact_id:
        _raise(
            "source_artifact_id is required",
            code="missing_source_artifact",
            status_code=422,
        )
    if not cleaned_span_id:
        _raise(
            "source_span_ref_id is required",
            code="missing_source_span",
            status_code=422,
        )

    try:
        artifact = get_source_artifact(root, cleaned_artifact_id)
    except SourceArtifactRegistryError as exc:
        _raise(
            str(exc),
            code="source_artifact_not_found",
            status_code=exc.status_code,
        )

    if str(artifact.source_domain) != "worldbuilding":
        _raise(
            "worldbuilding source-span read requires a worldbuilding SourceArtifact",
            code="unsupported_source_domain",
            status_code=422,
        )

    try:
        document_id = _require_worldbuilding_lineage(artifact)
        # Validate durable document ownership from its registry metadata only.
        # Graph passage reads are pinned to the immutable SourceArtifact digest;
        # requiring the mutable Build target file here would make historical
        # citations unreadable after a workspace edit or local file loss.
        workspace_record = get_workspace_document(root, document_id)
        _validate_workspace_lineage(artifact, workspace_record)
    except SourceNavigationError as exc:
        _map_navigation_error(exc)
    except WorkspaceDocumentRegistryError as exc:
        _raise(
            str(exc),
            code="workspace_document_error",
            status_code=exc.status_code,
        )

    _reconcile_graph_registry_scope(
        root=root,
        artifact=artifact,
        snapshot=snapshot,
        graph_artifact=graph_artifact,
    )

    registry_digest = _normalize_sha256(artifact.content_sha256)
    graph_digest = _normalize_sha256(graph_content_sha256)
    if not registry_digest:
        _raise(
            "Registry SourceArtifact is missing a content digest.",
            code="source_integrity_error",
            status_code=409,
        )
    if graph_digest and graph_digest != registry_digest:
        _raise(
            "Graph SourceArtifact digest disagrees with registry SourceArtifact.",
            code="source_integrity_error",
            status_code=409,
        )
    if artifact.source_artifact_id != cleaned_artifact_id:
        _raise(
            "Registry SourceArtifact id disagrees with graph SourceArtifact id.",
            code="source_integrity_error",
            status_code=409,
        )

    durable_source = (_source_batch.read(artifact, registry_digest) if _source_batch is not None
                      else _read_durable_source(artifact=artifact, expected_digest=registry_digest))
    if durable_source is not None:
        durable_markdown, index = durable_source
    else:
        durable_markdown = None
        try:
            index = load_source_span_index(root, cleaned_artifact_id)
        except SourceArtifactRegistryError as exc:
            _raise(
                str(exc),
                code="source_span_index_error",
                status_code=exc.status_code,
            )

    span = _find_span_entry(index.spans, cleaned_span_id)
    if span.source_artifact_id != cleaned_artifact_id:
        _raise(
            "SourceSpan does not belong to the admitted SourceArtifact.",
            code="source_integrity_error",
            status_code=409,
        )
    span_digest = _normalize_sha256(span.content_sha256)
    if span_digest != registry_digest:
        _raise(
            "SourceSpan digest disagrees with admitted SourceArtifact digest.",
            code="source_integrity_error",
            status_code=409,
        )

    if durable_markdown is not None:
        try:
            read_outcome = _read_text_line_span(
                text=durable_markdown,
                expected_content_sha256=registry_digest,
                start_line=int(span.start_line),
                end_line=int(span.end_line),
                max_chars=max_chars,
            )
        except SourceReadError as exc:
            status = 409
            if exc.code == "source_unavailable":
                status = 404
            elif exc.code == "unsupported_locator":
                status = 422
            _raise(str(exc), code=exc.code, status_code=status)
    else:
        from apps.live_control_server.services.graph_run_registry import (
            GraphRunRegistryError, resolve_registered_source_snapshot,
        )

        # Preserve the older file-backed integrity checks only when this exact
        # immutable APP-STATE revision is unavailable.
        try:
            workspace = get_workspace_document_snapshot(root, document_id)
        except WorkspaceDocumentRegistryError as exc:
            _raise(
                str(exc),
                code="workspace_document_error",
                status_code=exc.status_code,
            )
        frozen_source = None
        if _normalize_sha256(workspace.content_sha256) != registry_digest or not workspace.file_exists:
            try:
                frozen_source = resolve_registered_source_snapshot(artifact_data_root(root), artifact)
            except GraphRunRegistryError as exc:
                _raise(str(exc), code="source_integrity_error", status_code=409)
        source_uri = artifact.uri
        if frozen_source is not None:
            source_uri = "repo://" + frozen_source.relative_to(artifact_data_root(root).resolve()).as_posix()
        relative_path = parse_repo_uri(source_uri)
        if relative_path is None:
            _raise(
                "Worldbuilding SourceArtifact URI must be repo:// relative.",
                code="unsupported_locator",
                status_code=422,
            )

        try:
            read_outcome = read_repo_line_span_text(
                repo_root=artifact_data_root(root),
                relative_path=relative_path,
                start_line=int(span.start_line),
                end_line=int(span.end_line),
                max_chars=max_chars,
                expected_content_sha256=registry_digest,
            )
        except SourceReadError as exc:
            status = 409
            if exc.code == "source_unavailable":
                status = 404
            elif exc.code in {"path_escape", "unsupported_locator"}:
                status = 422
            _raise(str(exc), code=exc.code, status_code=status)

    outcome = "truncated" if read_outcome.truncated else "enough"
    diagnostics: list[WorldGraphRetrievalDiagnostic] = []
    if read_outcome.truncated:
        diagnostics.append(
            _diagnostic(
                "content_truncated",
                f"Content truncated to {max_chars} characters.",
                severity="warning",
            )
        )

    return WorldGraphSourceAnchorReadResult(
        outcome=outcome,
        snapshot=snapshot,
        anchor_id=anchor_id,
        evidence_ref_id=evidence_ref_id,
        source_artifact_id=cleaned_artifact_id,
        source_name=workspace_record.title,
        source_domain="worldbuilding",
        source_span_ref_id=span.source_span_id,
        locator_kind="source_span",
        media_type=read_outcome.media_type,
        content=read_outcome.content,
        content_sha256=registry_digest,
        line_start=read_outcome.line_start,
        line_end=read_outcome.line_end,
        truncated=read_outcome.truncated,
        trust_boundary=_trust_boundary(),
        diagnostics=diagnostics,
    )


__all__ = [
    "read_admitted_worldbuilding_span",
]
