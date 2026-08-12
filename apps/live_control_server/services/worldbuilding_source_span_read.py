"""Registry-backed exact worldbuilding SourceSpan reads for Hermes/graph retrieval.

Composes SourceArtifact + SourceSpanIndex integrity (same rules as Build
source-navigation) into a content-bearing World Graph source-anchor read.
Does not call the Build /source-navigation route or accept caller path authority.
"""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    get_source_artifact,
    load_source_span_index,
)
from graph_memory.kernel.world_retrieval import WorldGraphRetrievalError
from graph_memory.retrieval.models import (
    WorldGraphRetrievalDiagnostic,
    WorldGraphRetrievalSnapshot,
    WorldGraphRetrievalTrustBoundary,
    WorldGraphSourceAnchorReadResult,
)
from graph_memory.retrieval.source_reader import (
    SourceReadError,
    parse_repo_uri,
    read_repo_line_span_text,
)
from graph_memory.source_span import SourceSpanIndexEntry


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
) -> WorldGraphSourceAnchorReadResult:
    """Return exact admitted worldbuilding S text when current bytes still match A."""
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

    relative_path = parse_repo_uri(artifact.uri)
    if relative_path is None:
        _raise(
            "Worldbuilding SourceArtifact URI must be repo:// relative.",
            code="unsupported_locator",
            status_code=422,
        )

    try:
        read_outcome = read_repo_line_span_text(
            repo_root=root,
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
