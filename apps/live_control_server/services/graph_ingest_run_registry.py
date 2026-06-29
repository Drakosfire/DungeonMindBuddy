"""Read-only discovery for graph-ingest preview runs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from apps.live_control_server.config import repo_root
from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestArtifactKind,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
)
from graph_memory.ingestion.graph_ingest_validate import (
    validate_graph_ingest_run_manifest,
)

GRAPH_INGEST_RUNS_ENV = "DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT"
GRAPH_INGEST_MANIFEST_NAME = "graph_ingest_run_manifest.json"
DEFAULT_GRAPH_INGEST_RUN_ROOTS = [
    "out/graph_memory/runs",
]
EVAL_GRAPH_INGEST_RUN_ROOTS = [
    "evals/graph_memory_layer/runs",
    "evals/graph_memory_layer/artifacts/graph_ingest_runs",
]
ALLOWED_STATUS_FILTERS = {status.value for status in GraphIngestRunStatus}


class GraphIngestRunRegistryError(ValueError):
    """User-actionable registry failure suitable for API translation."""

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class GraphIngestRunSummary(BaseModel):
    manifest_path: str
    run_dir: str
    campaign_id: str
    session_id: str
    status: str
    updated_at: str | None = None
    created_at: str | None = None
    preview_union_store_path: str | None = None
    preview_union_store_valid: bool | None = None
    node_count: int = 0
    edge_count: int = 0
    evidence_ref_count: int = 0
    next_actions: list[str] = Field(default_factory=list)


class GraphIngestRunsResponse(BaseModel):
    schema_version: Literal["dmb_graph_ingest_run_registry_v1"] = (
        "dmb_graph_ingest_run_registry_v1"
    )
    version: str = "0.1"
    runs: list[GraphIngestRunSummary] = Field(default_factory=list)


class GraphIngestLatestRunResponse(BaseModel):
    schema_version: Literal["dmb_graph_ingest_run_registry_v1"] = (
        "dmb_graph_ingest_run_registry_v1"
    )
    version: str = "0.1"
    run: GraphIngestRunSummary | None = None


def discover_graph_ingest_runs(
    root: Path | None = None,
    *,
    campaign_id: str | None = None,
    session_id: str | None = None,
    source_recap_path: str | None = None,
    source_recap_sha256: str | None = None,
    status: str | None = None,
    require_preview_union_store: bool = False,
    include_eval_roots: bool = False,
) -> list[GraphIngestRunSummary]:
    """Discover valid graph-ingest manifests from bounded roots."""

    repo = (root or repo_root()).resolve()
    if status is not None and status not in ALLOWED_STATUS_FILTERS:
        raise GraphIngestRunRegistryError(
            f"invalid status filter: {status}", status_code=422
        )

    summaries: list[tuple[GraphIngestRunSummary, float]] = []
    for search_root in _graph_ingest_search_roots(repo, include_eval_roots=include_eval_roots):
        if not search_root.exists():
            continue
        for manifest_path in sorted(search_root.rglob(GRAPH_INGEST_MANIFEST_NAME)):
            summary = _summarize_manifest(repo, manifest_path)
            if summary is None:
                continue
            if campaign_id is not None and summary.campaign_id != campaign_id:
                continue
            if session_id is not None and summary.session_id != session_id:
                continue
            if (source_recap_path is not None or source_recap_sha256 is not None) and not _manifest_matches_source_recap(
                repo,
                manifest_path,
                source_recap_path=source_recap_path,
                source_recap_sha256=source_recap_sha256,
            ):
                continue
            if status is not None and summary.status != status:
                continue
            if require_preview_union_store and not _has_ready_preview_union_store(
                summary
            ):
                continue
            summaries.append((summary, manifest_path.stat().st_mtime))

    summaries.sort(
        key=lambda item: (
            item[0].updated_at or "",
            item[0].created_at or "",
            item[1],
            _reverse_path_key(item[0].manifest_path),
        ),
        reverse=True,
    )
    return [summary for summary, _mtime in summaries]


def resolve_latest_preview_union_graph_ingest_run(
    root: Path | None = None,
    *,
    campaign_id: str,
    session_id: str,
    source_recap_path: str | None = None,
    source_recap_sha256: str | None = None,
) -> GraphIngestRunSummary:
    runs = discover_graph_ingest_runs(
        root,
        campaign_id=campaign_id,
        session_id=session_id,
        source_recap_path=source_recap_path,
        source_recap_sha256=source_recap_sha256,
        require_preview_union_store=True,
    )
    if not runs:
        raise GraphIngestRunRegistryError(
            "no preview_union_store_ready graph-ingest run found for "
            f"{campaign_id}/{session_id}",
            status_code=404,
        )
    return runs[0]


def _manifest_matches_source_recap(
    repo: Path,
    manifest_path: Path,
    *,
    source_recap_path: str | None,
    source_recap_sha256: str | None,
) -> bool:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    if source_recap_sha256:
        actual_hashes = [
            source.get("normalized_recap_sha256"),
            (payload.get("artifacts") or {}).get("normalized_recap", {}).get("sha256")
            if isinstance(payload.get("artifacts"), dict)
            else None,
        ]
        if any(value == source_recap_sha256 for value in actual_hashes if isinstance(value, str)):
            return True
    if not source_recap_path:
        return False
    raw_values = [
        source.get("normalized_recap_path"),
        source.get("input_path_record"),
    ]
    expected = _normalize_repo_path(repo, source_recap_path)
    return any(_normalize_repo_path(repo, value) == expected for value in raw_values if isinstance(value, str))


def _normalize_repo_path(repo: Path, value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(repo).as_posix()
        except ValueError:
            return path.resolve().as_posix()
    return path.as_posix().lstrip("./")


def _graph_ingest_search_roots(repo: Path, *, include_eval_roots: bool = False) -> list[Path]:
    env_root = os.environ.get(GRAPH_INGEST_RUNS_ENV)
    values = [env_root] if env_root else list(DEFAULT_GRAPH_INGEST_RUN_ROOTS)
    if include_eval_roots:
        values.extend(EVAL_GRAPH_INGEST_RUN_ROOTS)
    return [
        _resolve_repo_contained_path(Path(value), repo, must_exist=False)
        for value in values
    ]


def _summarize_manifest(
    repo: Path, manifest_path: Path
) -> GraphIngestRunSummary | None:
    try:
        safe_manifest_path = _resolve_repo_contained_path(manifest_path, repo)
        payload = json.loads(safe_manifest_path.read_text(encoding="utf-8"))
        manifest = GraphIngestRunManifest.model_validate(payload)
        validation = validate_graph_ingest_run_manifest(payload)
        if validation["errors"]:
            return None
        preview_path = _preview_union_store_path(repo, manifest)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError):
        return None

    return GraphIngestRunSummary(
        manifest_path=_repo_relative(safe_manifest_path, repo),
        run_dir=_repo_relative(safe_manifest_path.parent, repo),
        campaign_id=manifest.campaign_id,
        session_id=manifest.session_id,
        status=manifest.status.value,
        updated_at=manifest.updated_at,
        created_at=manifest.created_at,
        preview_union_store_path=preview_path,
        preview_union_store_valid=manifest.health.preview_union_store_valid,
        node_count=manifest.health.node_count,
        edge_count=manifest.health.edge_count,
        evidence_ref_count=manifest.health.evidence_ref_count,
        next_actions=list(manifest.next_actions),
    )


def _preview_union_store_path(
    repo: Path, manifest: GraphIngestRunManifest
) -> str | None:
    artifact = manifest.artifacts.get(GraphIngestArtifactKind.PREVIEW_UNION_STORE.value)
    if artifact is None:
        return None
    if artifact.preview_only is not True:
        raise ValueError("artifacts.preview_union_store must be preview_only")
    path = _resolve_repo_contained_path(Path(artifact.uri), repo)
    return _repo_relative(path, repo)


def _has_ready_preview_union_store(summary: GraphIngestRunSummary) -> bool:
    return (
        summary.status == GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value
        and summary.preview_union_store_path is not None
        and summary.preview_union_store_valid is True
    )


def _resolve_repo_contained_path(
    path: Path, repo: Path, *, must_exist: bool = True
) -> Path:
    value = str(path).replace("\\", "/")
    if value.startswith("file:") or ".." in Path(value).parts:
        raise GraphIngestRunRegistryError(
            "unsafe graph-ingest runs root", status_code=422
        )
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise GraphIngestRunRegistryError(
            "unsafe graph-ingest runs root", status_code=422
        ) from exc
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return resolved


def _repo_relative(path: Path, repo: Path) -> str:
    return path.resolve().relative_to(repo).as_posix()


def _reverse_path_key(value: str) -> tuple[int, ...]:
    # reverse=True would put z before a; invert codepoints for ascending stable tie-breaker.
    return tuple(-ord(char) for char in value)
