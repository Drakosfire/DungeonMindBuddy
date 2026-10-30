"""Resolve exact database ingestion runs for governed promotion.

File manifests and directory discovery cannot create publication authority.
Canonical component readers are being cut over to their immutable byte owner.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apps.live_control_server.config import ArtifactDataRootError, artifact_data_root, repo_root, world_graph_root
from apps.live_control_server.services.graph_ingest_run_registry import _graph_ingest_search_roots

from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    _resolve_repo_contained_uri,
)


class PromotableIngestRunError(ValueError):
    """Fail-closed resolution error suitable for API translation."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 422,
        diagnostics: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = list(diagnostics or [message])


def _artifact_root(root: Path | None = None) -> Path:
    try:
        return artifact_data_root(root if root is not None else repo_root())
    except ArtifactDataRootError as exc:
        raise PromotableIngestRunError(
            str(exc), code="artifact_data_root_unavailable", status_code=503
        ) from exc


@dataclass(frozen=True)
class PromotableIngestRun:
    """Resolved, promotable graph-ingest run."""

    run_id: str
    campaign_id: str
    session_id: str
    status: str
    extraction_profile: str | None
    source_artifact_id: str
    source_revision_id: str
    normalized_recap_path: Path
    candidate_graph_path: Path
    preview_union_store_path: Path
    manifest_path: Path
    run_dir: Path
    registry_root: Path
    sealed_source_uri: str
    registry_context_graph_path: Path | None = None
    diagnostics: list[str] = field(default_factory=list)
    source_domain: str = "recap"
    # Exact SourceArtifact world identity for canonical Build ExtractionRuns.
    # Legacy graph-ingest manifests leave this None; never invent DEFAULT_WORLD_ID.
    world_id: str | None = None
    # Exact ExtractionRun path: the run-pinned source_span_index component path.
    # Review/prepare must load this URI — never re-derive the registry canonical
    # index from source_artifact_id alone.
    source_span_index_path: Path | None = None
    source_span_index_sha256: str | None = None
    # Immutable MIND membership/head observation captured before recap extraction.
    ingest_context: dict[str, Any] | None = None



def ingest_run_registry_roots(
    root: Path | None = None, *, include_eval_roots: bool = False
) -> list[Path]:
    """Configured registry search roots (honors ``DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT``)."""
    repo = _artifact_root(root)
    return list(
        _graph_ingest_search_roots(repo, include_eval_roots=include_eval_roots)
    )


def world_store_denied_roots(root: Path | None = None) -> list[Path]:
    """Durable world-graph trees that must never become evidentiary source.

    When ``world_graph_root()`` is the broad default ``<repo>/out``, only the
    worlds subtree is denied so configured ingest-run registry roots can remain
    registry-gated evidence. A more specific mutation root is denied wholesale.
    """
    repo = _artifact_root(root)
    out_root = (repo / "out").resolve()
    worlds = (repo / "out" / "graph_memory" / "worlds").resolve()
    roots: list[Path] = [worlds]
    wgr = world_graph_root().resolve()
    if wgr != out_root:
        roots.append(wgr)
    seen: set[Path] = set()
    unique: list[Path] = []
    for item in roots:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def is_under_world_store(path: Path, *, root: Path | None = None) -> bool:
    resolved = path.resolve()
    for denied in world_store_denied_roots(root):
        try:
            resolved.relative_to(denied)
            return True
        except ValueError:
            continue
    return False



def is_under_ingest_runs(
    path: Path, *, root: Path | None = None, include_eval_roots: bool = False
) -> bool:
    """True when ``path`` sits under any configured ingest-run registry root."""
    resolved = path.resolve()
    for registry_root in ingest_run_registry_roots(
        root, include_eval_roots=include_eval_roots
    ):
        try:
            resolved.relative_to(registry_root.resolve())
            return True
        except ValueError:
            continue
    return False


def resolve_promotable_ingest_run(
    run_id: str,
    *,
    root: Path | None = None,
) -> PromotableIngestRun:
    """Resolve only the exact APP ExtractionRun; files cannot grant authority."""
    text = (run_id or "").strip()
    if not text:
        raise PromotableIngestRunError(
            "runId is required", code="invalid_request", status_code=422,
        )
    extraction = _resolve_promotable_extraction_run(_artifact_root(root), text)
    if extraction is None:
        raise PromotableIngestRunError(
            f"unknown extraction runId: {text}", code="run_not_found", status_code=404,
        )
    return extraction


def _resolve_extraction_component_path(repo: Path, uri: str, *, label: str) -> Path:
    """Resolve one ExtractionRun component URI under the registry's path contract."""
    try:
        path = _resolve_repo_contained_uri(repo, uri)
    except GraphRunRegistryError as exc:
        raise PromotableIngestRunError(
            f"extraction run {label} uri is unsafe or missing",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[str(exc)],
        ) from exc
    if not path.is_file():
        raise PromotableIngestRunError(
            f"extraction run {label} artifact is not a file",
            code="run_not_promotable",
            status_code=422,
        )
    if is_under_world_store(path, root=repo):
        raise PromotableIngestRunError(
            f"extraction run {label} must not reference the world graph store",
            code="run_not_promotable",
            status_code=422,
        )
    return path


def _seal_extraction_source(
    repo: Path,
    *,
    source_path: Path,
    source_revision_id: str,
) -> Path:
    """Return an allowlisted, content-addressed seal of the verified source bytes.

    Registry-owned source bytes (a committed workspace document) live outside the
    ingest-run seal roots, so prepare cannot reference them directly. The seal is
    keyed by the already-verified content digest, so it is immutable, idempotent,
    and never mutates the ExtractionRun's own artifact directory.
    """
    if is_under_ingest_runs(source_path, root=repo):
        return source_path

    digest_hex = source_revision_id.removeprefix("sha256:")
    seal_root = ingest_run_registry_roots(repo)[0]
    sealed = (seal_root / "promote_seals" / digest_hex / "normalized_source.md").resolve()
    if not sealed.is_relative_to(repo.resolve()):
        raise PromotableIngestRunError(
            "source seal escapes artifact repository", code="run_not_promotable", status_code=422
        )
    payload = source_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest_hex:
        raise PromotableIngestRunError(
            "extraction run source bytes disagree with the sealed content digest",
            code="run_not_promotable",
            status_code=422,
        )
    if not sealed.is_file() or hashlib.sha256(sealed.read_bytes()).hexdigest() != digest_hex:
        sealed.parent.mkdir(parents=True, exist_ok=True)
        sealed.write_bytes(payload)
    return sealed


def _resolve_promotable_extraction_run(
    repo: Path,
    run_id: str,
) -> PromotableIngestRun | None:
    """Resolve the sole live ExtractionRun promotion path."""
    from apps.live_control_server.services.graph_run_registry import (
        get_reviewable_extraction_run,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        get_source_artifact,
    )

    try:
        run = get_reviewable_extraction_run(repo, run_id)
    except GraphRunRegistryError as exc:
        if exc.status_code == 404:
            return None
        # Preserve the owner failure; no alternate pipeline can recover it.
        raise PromotableIngestRunError(
            str(exc),
            code="run_not_promotable",
            status_code=exc.status_code,
            diagnostics=[str(exc), f"status={run_id}"],
        ) from exc

    try:
        artifact = get_source_artifact(repo, run.source_artifact_id)
    except SourceArtifactRegistryError as exc:
        raise PromotableIngestRunError(
            str(exc),
            code="run_not_promotable",
            status_code=exc.status_code if exc.status_code >= 500 else 422,
            diagnostics=[str(exc)],
        ) from exc

    candidate_path = _resolve_extraction_component_path(
        repo, run.components["candidate_graph"].uri, label="candidate_graph"
    )
    source_path = _resolve_extraction_component_path(
        repo, run.components["source_artifact"].uri, label="source_artifact"
    )
    span_index_path = _resolve_extraction_component_path(
        repo, run.components["source_span_index"].uri, label="source_span_index"
    )

    source_revision_id = _normalize_digest(artifact.content_sha256)
    if not source_revision_id:
        raise PromotableIngestRunError(
            "extraction run SourceArtifact is missing a content digest",
            code="run_not_promotable",
            status_code=422,
        )

    sealed_source_path = _seal_extraction_source(
        repo, source_path=source_path, source_revision_id=source_revision_id
    )
    run_dir = candidate_path.parent
    artifact_world_id = (artifact.world_id or "").strip() or None

    return PromotableIngestRun(
        run_id=run.run_id,
        campaign_id=(run.campaign_id or "").strip(),
        session_id=(run.session_id or "").strip(),
        status=run.status.value,
        extraction_profile=run.profile_id,
        source_artifact_id=run.source_artifact_id,
        source_revision_id=source_revision_id,
        normalized_recap_path=sealed_source_path,
        candidate_graph_path=candidate_path,
        preview_union_store_path=run_dir,
        manifest_path=run_dir / "extraction_run.json",
        run_dir=run_dir,
        registry_root=repo,
        sealed_source_uri=_seal_repo_uri(repo, sealed_source_path),
        diagnostics=[
            "resolved via canonical ExtractionRun registry",
            f"source_domain={run.source_domain}",
            f"session_scope={'null' if not (run.session_id or '').strip() else 'session'}",
            f"world_id={artifact_world_id or 'null'}",
        ],
        source_domain=(run.source_domain or "worldbuilding").strip() or "worldbuilding",
        world_id=artifact_world_id,
        ingest_context=(
            dict(run.lineage.get("world_campaign_ingest_context"))
            if isinstance(run.lineage.get("world_campaign_ingest_context"), dict)
            else None
        ),
        source_span_index_path=span_index_path,
        source_span_index_sha256=run.components["source_span_index"].sha256,
    )


def _normalize_digest(raw: str | None) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return ""
    text = raw.strip()
    if text.startswith("sha256:"):
        text = text[len("sha256:") :]
    text = text.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        return ""
    return f"sha256:{text}"


def _seal_repo_uri(repo: Path, path: Path) -> str:
    rel = path.resolve().relative_to(repo.resolve()).as_posix()
    return f"repo://{rel}"
