"""Preview-only graph-ingest wiring for recap ingestion."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from apps.live_control_server.services.graph_ingest_run_registry import (
    GraphIngestRunSummary,
    discover_graph_ingest_runs,
    resolve_latest_preview_union_graph_ingest_run,
)
from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    run_graph_preview_extraction,
)
from graph_memory.ingestion.graph_ingest_run import GraphIngestRunStatus
from src.graph_memory.union_supergraph.preview_run_materialize import (
    PreviewUnionMaterializeOptions,
    materialize_preview_union_store_from_graph_ingest_run,
)

_MANIFEST_NAME = "graph_ingest_run_manifest.json"
_RUNS_ROOT = Path("out/graph_memory/runs")


def inspect_recap_graph_preview_status(
    *,
    repo_root: Path,
    campaign_id: str,
    session: int,
    normalized_recap_path: str | None,
) -> dict[str, Any]:
    """Return latest graph-ingest status for a recap session without writing files."""

    repo = repo_root.resolve()
    runs = discover_graph_ingest_runs(
        repo,
        campaign_id=campaign_id,
        session_id=f"session-{session}",
    )
    if not runs:
        return _missing_status(normalized_recap_path)
    return _status_from_summary(repo, runs[0], normalized_recap_path=normalized_recap_path)


def build_recap_graph_preview_bundle(
    *,
    repo_root: Path,
    campaign_id: str,
    session: int,
    normalized_recap_path: str,
    force_graph_run: bool = False,
    candidate_graph_path: str | None = None,
) -> dict[str, Any]:
    """Build a preview graph-ingest run from a normalized recap."""

    repo = repo_root.resolve()
    normalized = _resolve_existing_readable_path(normalized_recap_path, field_name="normalized_recap_path")
    candidate = (
        _resolve_existing_repo_path(repo, candidate_graph_path, field_name="candidate_graph_path")
        if candidate_graph_path
        else None
    )
    _reject_forbidden_candidate(candidate)

    desired_statuses = {
        GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value,
        GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value,
    } if candidate else {
        GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY.value,
        GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value,
        GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value,
    }
    if not force_graph_run:
        reusable = _latest_matching_run(repo, campaign_id, session, desired_statuses)
        if reusable is not None:
            return _status_from_summary(repo, reusable, normalized_recap_path=normalized_recap_path)

    run_dir = _new_run_dir(repo, campaign_id, session)
    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id=campaign_id,
            session_id=f"session-{session}",
            normalized_recap_path=normalized,
            output_dir=run_dir,
            source_label=f"{campaign_id} session {session} normalized recap",
            allow_llm=False,
            comparison_mode="none",
            candidate_graph_path=candidate,
        )
    )
    summary = _summary_for_manifest(repo, result.manifest_path)
    return _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)


def materialize_recap_preview_supergraph(
    *,
    repo_root: Path,
    campaign_id: str,
    session: int,
    normalized_recap_path: str | None = None,
    manifest_path: str | None = None,
    candidate_graph_path: str | None = None,
) -> dict[str, Any]:
    """Materialize a preview union supergraph from a recap graph-ingest run."""

    repo = repo_root.resolve()
    if candidate_graph_path:
        if not normalized_recap_path:
            raise ValueError("normalized recap is required when candidate_graph_path is supplied")
        build_recap_graph_preview_bundle(
            repo_root=repo,
            campaign_id=campaign_id,
            session=session,
            normalized_recap_path=normalized_recap_path,
            force_graph_run=True,
            candidate_graph_path=candidate_graph_path,
        )

    if manifest_path:
        manifest = _resolve_existing_repo_path(repo, manifest_path, field_name="manifest_path")
        summary = _summary_for_manifest(repo, manifest)
    else:
        runs = discover_graph_ingest_runs(repo, campaign_id=campaign_id, session_id=f"session-{session}")
        summary = runs[0] if runs else None

    if summary is None:
        return _missing_status(normalized_recap_path)
    if summary.status == GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value:
        return _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
    if summary.status != GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value:
        status = _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
        status["blocked_reason"] = "candidate graph required before preview union materialization"
        status["next_actions"] = ["supply candidate_graph_path", "build_graph_preview_bundle"]
        return status

    result = materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(
            manifest_path=(repo / summary.manifest_path).resolve(),
            repo_root=repo,
            update_manifest=True,
        )
    )
    updated = _summary_for_manifest(repo, result.manifest_path)
    return _status_from_summary(repo, updated, normalized_recap_path=normalized_recap_path)


def _latest_matching_run(
    repo: Path, campaign_id: str, session: int, statuses: set[str]
) -> GraphIngestRunSummary | None:
    for run in discover_graph_ingest_runs(repo, campaign_id=campaign_id, session_id=f"session-{session}"):
        if run.status in statuses:
            return run
    return None


def _summary_for_manifest(repo: Path, manifest_path: Path) -> GraphIngestRunSummary:
    run_dir = manifest_path.resolve().parent
    runs = discover_graph_ingest_runs(repo)
    rel_manifest = _repo_relative(manifest_path, repo)
    for run in runs:
        if run.manifest_path == rel_manifest or run.run_dir == _repo_relative(run_dir, repo):
            return run
    raise ValueError(f"graph-ingest manifest was not discoverable: {manifest_path}")


def _status_from_summary(
    repo: Path, summary: GraphIngestRunSummary, *, normalized_recap_path: str | None
) -> dict[str, Any]:
    manifest_path = (repo / summary.manifest_path).resolve()
    candidate_path = _candidate_graph_path(repo, manifest_path)
    status = {
        "status": summary.status,
        "run_dir": summary.run_dir,
        "manifest_path": summary.manifest_path,
        "candidate_graph_path": candidate_path,
        "preview_union_store_path": summary.preview_union_store_path,
        "preview_union_store_valid": summary.preview_union_store_valid,
        "node_count": summary.node_count,
        "edge_count": summary.edge_count,
        "evidence_ref_count": summary.evidence_ref_count,
        "next_actions": list(summary.next_actions),
        "can_open_union_graph": summary.status == GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value
        and bool(summary.preview_union_store_path),
        "blocked_reason": None,
        "normalized_recap_path": normalized_recap_path,
    }
    if summary.status == GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY.value:
        status["blocked_reason"] = "Graph source bundle ready. Candidate graph extraction is not wired yet."
    return status


def _missing_status(normalized_recap_path: str | None) -> dict[str, Any]:
    return {
        "status": "missing",
        "run_dir": None,
        "manifest_path": None,
        "candidate_graph_path": None,
        "preview_union_store_path": None,
        "preview_union_store_valid": None,
        "node_count": 0,
        "edge_count": 0,
        "evidence_ref_count": 0,
        "next_actions": ["build_graph_preview_bundle"] if normalized_recap_path else ["materialize_session_memory"],
        "can_open_union_graph": False,
        "blocked_reason": "normalized recap missing" if not normalized_recap_path else None,
        "normalized_recap_path": normalized_recap_path,
    }


def _candidate_graph_path(repo: Path, manifest_path: Path) -> str | None:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        uri = payload.get("artifacts", {}).get("candidate_graph", {}).get("uri")
        if not isinstance(uri, str):
            return None
        return _repo_relative((repo / uri).resolve(), repo)
    except Exception:
        return None


def _new_run_dir(repo: Path, campaign_id: str, session: int) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = _RUNS_ROOT / campaign_id / f"session-{session}" / timestamp
    path = base
    suffix = 1
    while path.exists():
        suffix += 1
        path = base.with_name(f"{base.name}-{suffix}")
    return path


def _resolve_existing_readable_path(value: str | None, *, field_name: str) -> Path:
    if not value:
        raise ValueError(f"{field_name} is required")
    if value.startswith("file:"):
        raise ValueError(f"{field_name} must be a filesystem path, not a file URI")
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"{field_name} does not exist: {value}")
    if not path.is_file():
        raise ValueError(f"{field_name} must be a file: {value}")
    return path


def _resolve_existing_repo_path(repo: Path, value: str | None, *, field_name: str) -> Path:
    if not value:
        raise ValueError(f"{field_name} is required")
    if value.startswith("file:"):
        raise ValueError(f"{field_name} must be repo-relative, not a file URI")
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        if ".." in PurePosixPath(path.as_posix()).parts:
            raise ValueError(f"{field_name} must not contain path traversal: {value}")
        resolved = (repo / path).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay under repo root: {value}") from exc
    if not resolved.exists():
        raise FileNotFoundError(f"{field_name} does not exist: {value}")
    return resolved


def _reject_forbidden_candidate(candidate: Path | None) -> None:
    if candidate is None:
        return
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    diagnostics = payload.get("diagnostics", {})
    if isinstance(payload.get("candidate_graph"), dict):
        diagnostics = payload["candidate_graph"].get("diagnostics", diagnostics)
    if not isinstance(diagnostics, dict):
        return
    for key in ("canon_promotion", "approved_memory_write", "corpus_mutation", "production_retrieval"):
        if diagnostics.get(key) is True:
            raise ValueError(f"candidate graph has forbidden lifecycle diagnostic: {key}")


def _repo_relative(path: Path, repo: Path) -> str:
    return path.resolve().relative_to(repo).as_posix()
