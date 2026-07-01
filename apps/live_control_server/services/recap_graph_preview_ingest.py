"""Preview-only graph-ingest wiring for recap ingestion."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from apps.live_control_server.services.graph_ingest_run_registry import (
    GraphIngestRunSummary,
    discover_graph_ingest_runs,
)
from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    normalize_graph_extraction_profile,
    run_graph_preview_extraction,
)
from src.graph_memory.vocabulary.model import ContextVocabularyPacket
from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestArtifactKind,
    GraphIngestRunStatus,
)
from src.graph_memory.union_supergraph.preview_run_materialize import (
    PreviewUnionMaterializeOptions,
    materialize_preview_union_store_from_graph_ingest_run,
)

_MANIFEST_NAME = "graph_ingest_run_manifest.json"
_RUNS_ROOT = Path("out/graph_memory/runs")
logger = logging.getLogger(__name__)


def inspect_recap_graph_preview_status(
    *,
    repo_root: Path,
    campaign_id: str,
    session: int,
    normalized_recap_path: str | None,
) -> dict[str, Any]:
    """Return latest graph-ingest status for a recap session without writing files."""

    repo = repo_root.resolve()
    source_recap_path, source_recap_sha256 = _lineage_for_normalized_recap(
        repo, normalized_recap_path
    )
    runs = discover_graph_ingest_runs(
        repo,
        campaign_id=campaign_id,
        session_id=f"session-{session}",
        source_recap_path=source_recap_path,
        source_recap_sha256=source_recap_sha256,
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
    extract_graph: bool = False,
    graph_model_id: str | None = None,
    graph_extraction_profile: str | None = None,
    context_vocabulary_packet: ContextVocabularyPacket | None = None,
    enable_node_vocabulary_packet: bool = False,
    enable_edge_vocabulary_packet: bool = False,
) -> dict[str, Any]:
    """Build a preview graph-ingest run from a normalized recap."""

    repo = repo_root.resolve()
    normalized = _resolve_existing_readable_path(normalized_recap_path, field_name="normalized_recap_path")
    source_recap_path, source_recap_sha256 = _lineage_for_normalized_recap(
        repo, normalized_recap_path
    )
    candidate = (
        _resolve_existing_repo_path(repo, candidate_graph_path, field_name="candidate_graph_path")
        if candidate_graph_path
        else None
    )
    _reject_forbidden_candidate(candidate)
    requested_profile = normalize_graph_extraction_profile(graph_extraction_profile)
    profile_sensitive_reuse = extract_graph or graph_extraction_profile is not None
    logger.info(
        "graph preview bundle requested campaign=%s session=session-%s normalized=%s "
        "source_recap_path=%s source_recap_sha256=%s force_graph_run=%s "
        "candidate_graph_path=%s extract_graph=%s model_id=%s graph_extraction_profile=%s",
        campaign_id,
        session,
        normalized_recap_path,
        source_recap_path,
        source_recap_sha256,
        force_graph_run,
        candidate_graph_path,
        extract_graph,
        graph_model_id,
        graph_extraction_profile,
    )

    desired_statuses = {
        GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value,
        GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value,
    } if (candidate or extract_graph) else {
        GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY.value,
        GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value,
        GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value,
    }
    if not force_graph_run and candidate is None:
        reusable = _latest_matching_run(
            repo,
            campaign_id,
            session,
            desired_statuses,
            source_recap_path=source_recap_path,
            source_recap_sha256=source_recap_sha256,
            graph_extraction_profile=requested_profile if profile_sensitive_reuse else None,
        )
        if reusable is not None:
            logger.info(
                "graph preview bundle reusing run campaign=%s session=session-%s status=%s manifest=%s run_dir=%s",
                campaign_id,
                session,
                reusable.status,
                reusable.manifest_path,
                reusable.run_dir,
            )
            return _status_from_summary(repo, reusable, normalized_recap_path=normalized_recap_path)

    run_dir = _new_run_dir(repo, campaign_id, session)
    logger.info(
        "graph preview bundle starting extraction campaign=%s session=session-%s run_dir=%s allow_llm=%s",
        campaign_id,
        session,
        _repo_relative(run_dir, repo),
        extract_graph,
    )
    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id=campaign_id,
            session_id=f"session-{session}",
            normalized_recap_path=normalized,
            output_dir=run_dir,
            source_label=f"{campaign_id} session {session} normalized recap",
            allow_llm=extract_graph,
            model_id=graph_model_id,
            comparison_mode="none",
            candidate_graph_path=candidate,
            input_path_record=source_recap_path,
            graph_extraction_profile=requested_profile,
            context_vocabulary_packet=context_vocabulary_packet,
            enable_node_vocabulary_packet=enable_node_vocabulary_packet,
            enable_edge_vocabulary_packet=enable_edge_vocabulary_packet,
        )
    )
    summary = _summary_for_manifest(repo, result.manifest_path)
    logger.info(
        "graph preview bundle finished campaign=%s session=session-%s status=%s manifest=%s "
        "candidate_graph_path=%s validation_report_path=%s",
        campaign_id,
        session,
        summary.status,
        summary.manifest_path,
        _repo_relative(result.candidate_graph_path, repo) if result.candidate_graph_path else None,
        _repo_relative(result.validation_report_path, repo) if result.validation_report_path else None,
    )
    return _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)


def materialize_recap_preview_supergraph(
    *,
    repo_root: Path,
    campaign_id: str,
    session: int,
    normalized_recap_path: str | None = None,
    manifest_path: str | None = None,
    candidate_graph_path: str | None = None,
    extract_graph: bool = False,
    graph_model_id: str | None = None,
    force_graph_run: bool = False,
    graph_extraction_profile: str | None = None,
    context_vocabulary_packet: ContextVocabularyPacket | None = None,
    enable_node_vocabulary_packet: bool = False,
    enable_edge_vocabulary_packet: bool = False,
) -> dict[str, Any]:
    """Materialize a preview union supergraph from a recap graph-ingest run."""

    repo = repo_root.resolve()
    source_recap_path, source_recap_sha256 = _lineage_for_normalized_recap(
        repo, normalized_recap_path
    )
    logger.info(
        "preview union materialization requested campaign=%s session=session-%s normalized=%s "
        "source_recap_path=%s source_recap_sha256=%s manifest_path=%s candidate_graph_path=%s "
        "extract_graph=%s model_id=%s force_graph_run=%s graph_extraction_profile=%s",
        campaign_id,
        session,
        normalized_recap_path,
        source_recap_path,
        source_recap_sha256,
        manifest_path,
        candidate_graph_path,
        extract_graph,
        graph_model_id,
        force_graph_run,
        graph_extraction_profile,
    )
    forced_build_status: dict[str, Any] | None = None
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
            extract_graph=extract_graph,
            graph_model_id=graph_model_id,
            graph_extraction_profile=graph_extraction_profile,
            context_vocabulary_packet=context_vocabulary_packet,
            enable_node_vocabulary_packet=enable_node_vocabulary_packet,
            enable_edge_vocabulary_packet=enable_edge_vocabulary_packet,
        )

    if extract_graph and not candidate_graph_path and normalized_recap_path:
        needs_extract = force_graph_run
        if not needs_extract:
            existing = discover_graph_ingest_runs(
                repo,
                campaign_id=campaign_id,
                session_id=f"session-{session}",
                source_recap_path=source_recap_path,
                source_recap_sha256=source_recap_sha256,
            )
            logger.info(
                "preview union extract-then-materialize discovered runs campaign=%s session=session-%s statuses=%s",
                campaign_id,
                session,
                [run.status for run in existing[:5]],
            )
            if existing and existing[0].status == GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value:
                needs_extract = False
            else:
                needs_extract = (
                    not existing
                    or existing[0].status != GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value
                )
        if needs_extract:
            forced_build_status = build_recap_graph_preview_bundle(
                repo_root=repo,
                campaign_id=campaign_id,
                session=session,
                normalized_recap_path=normalized_recap_path,
                force_graph_run=True,
                extract_graph=True,
                graph_model_id=graph_model_id,
                graph_extraction_profile=graph_extraction_profile,
                context_vocabulary_packet=context_vocabulary_packet,
                enable_node_vocabulary_packet=enable_node_vocabulary_packet,
                enable_edge_vocabulary_packet=enable_edge_vocabulary_packet,
            )

    if manifest_path:
        manifest = _resolve_existing_repo_path(repo, manifest_path, field_name="manifest_path")
        summary = _summary_for_manifest(repo, manifest)
    elif forced_build_status and forced_build_status.get("manifest_path"):
        forced_manifest = _resolve_existing_repo_path(
            repo,
            forced_build_status["manifest_path"],
            field_name="manifest_path",
        )
        summary = _summary_for_manifest(repo, forced_manifest)
    else:
        runs = discover_graph_ingest_runs(
            repo,
            campaign_id=campaign_id,
            session_id=f"session-{session}",
            source_recap_path=source_recap_path,
            source_recap_sha256=source_recap_sha256,
        )
        summary = runs[0] if runs else None

    if summary is None:
        logger.warning(
            "preview union materialization missing graph run campaign=%s session=session-%s normalized=%s",
            campaign_id,
            session,
            normalized_recap_path,
        )
        return _missing_status(normalized_recap_path)
    if (
        summary.status == GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value
        and not force_graph_run
    ):
        ensure_graph_ingest_projection_payload(
            repo_root=repo,
            manifest_path=summary.manifest_path,
            session_id=f"session-{session}",
        )
        logger.info(
            "preview union materialization reused ready run campaign=%s session=session-%s manifest=%s union_store=%s",
            campaign_id,
            session,
            summary.manifest_path,
            summary.preview_union_store_path,
        )
        return _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
    if summary.status != GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value:
        status = _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
        status["blocked_reason"] = (
            status.get("blocked_reason")
            or "candidate graph required before preview union materialization"
        )
        status["next_actions"] = ["supply candidate_graph_path", "build_graph_preview_bundle"]
        logger.warning(
            "preview union materialization blocked campaign=%s session=session-%s status=%s "
            "manifest=%s extraction_mode=%s blocked_reason=%s next_actions=%s",
            campaign_id,
            session,
            summary.status,
            summary.manifest_path,
            status.get("extraction_mode"),
            status.get("blocked_reason"),
            status.get("next_actions"),
        )
        return status

    logger.info(
        "preview union materialization starting campaign=%s session=session-%s manifest=%s",
        campaign_id,
        session,
        summary.manifest_path,
    )
    result = materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(
            manifest_path=(repo / summary.manifest_path).resolve(),
            repo_root=repo,
            update_manifest=True,
        )
    )
    updated = _summary_for_manifest(repo, result.manifest_path)
    ensure_graph_ingest_projection_payload(
        repo_root=repo,
        manifest_path=_repo_relative(result.manifest_path, repo),
        session_id=f"session-{session}",
    )
    logger.info(
        "preview union materialization finished campaign=%s session=session-%s manifest=%s union_store=%s",
        campaign_id,
        session,
        updated.manifest_path,
        updated.preview_union_store_path,
    )
    return _status_from_summary(repo, updated, normalized_recap_path=normalized_recap_path)


def ensure_graph_ingest_projection_payload(
    *,
    repo_root: Path,
    manifest_path: str | None,
    session_id: str,
) -> Path | None:
    """Persist projection_payload.json on a preview_union_store_ready graph-ingest run."""

    if not manifest_path:
        return None
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        build_plan_union_supergraph_projection_payload,
    )

    repo = repo_root.resolve()
    manifest_full = _resolve_existing_repo_path(repo, manifest_path, field_name="manifest_path")
    payload_data = json.loads(manifest_full.read_text(encoding="utf-8"))
    artifacts = payload_data.get("artifacts") if isinstance(payload_data.get("artifacts"), dict) else {}
    existing = artifacts.get(GraphIngestArtifactKind.PROJECTION_PAYLOAD.value)
    if isinstance(existing, dict) and existing.get("exists") is True:
        uri = existing.get("uri")
        if isinstance(uri, str):
            return _resolve_existing_repo_path(repo, uri, field_name="projection_payload")

    projection_payload = build_plan_union_supergraph_projection_payload(
        session_id=session_id,
        graph_run_manifest_path=manifest_full,
    )
    projection_path = manifest_full.parent / "projection_payload.json"
    projection_path.write_text(
        json.dumps(projection_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts = dict(artifacts)
    artifacts[GraphIngestArtifactKind.PROJECTION_PAYLOAD.value] = {
        "kind": GraphIngestArtifactKind.PROJECTION_PAYLOAD.value,
        "uri": _repo_relative(projection_path, repo),
        "schema": "dmb_recap_graph_projection_v0",
        "exists": True,
        "preview_only": True,
    }
    payload_data["artifacts"] = artifacts
    manifest_full.write_text(json.dumps(payload_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return projection_path


def _lineage_for_normalized_recap(
    repo: Path, normalized_recap_path: str | None
) -> tuple[str | None, str | None]:
    if not normalized_recap_path:
        return None, None
    try:
        path = _resolve_existing_readable_path(normalized_recap_path, field_name="normalized_recap_path")
    except (FileNotFoundError, ValueError):
        if not Path(normalized_recap_path).is_absolute():
            return normalized_recap_path.replace("\\", "/"), None
        return None, None
    source_recap_sha256 = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
    try:
        source_recap_path = path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        if not Path(normalized_recap_path).is_absolute():
            source_recap_path = normalized_recap_path.replace("\\", "/")
        else:
            source_recap_path = None
    return source_recap_path, source_recap_sha256


def _latest_matching_run(
    repo: Path,
    campaign_id: str,
    session: int,
    statuses: set[str],
    *,
    source_recap_path: str | None = None,
    source_recap_sha256: str | None = None,
    graph_extraction_profile: str | None = None,
) -> GraphIngestRunSummary | None:
    for run in discover_graph_ingest_runs(
        repo,
        campaign_id=campaign_id,
        session_id=f"session-{session}",
        source_recap_path=source_recap_path,
        source_recap_sha256=source_recap_sha256,
    ):
        if run.status not in statuses:
            continue
        if graph_extraction_profile is not None and not _summary_matches_graph_extraction_profile(
            repo, run, graph_extraction_profile
        ):
            continue
        return run
    return None


def _summary_matches_graph_extraction_profile(
    repo: Path, summary: GraphIngestRunSummary, requested_profile: str
) -> bool:
    manifest_path = (repo / summary.manifest_path).resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    diagnostics = manifest.get("diagnostics") if isinstance(manifest, dict) else None
    manifest_profile = None
    if isinstance(diagnostics, dict):
        manifest_profile = diagnostics.get("graph_extraction_profile")
    if manifest_profile is None:
        manifest_profile = "current_default"
    return manifest_profile == requested_profile


def _summary_for_manifest(repo: Path, manifest_path: Path) -> GraphIngestRunSummary:
    run_dir = manifest_path.resolve().parent
    runs = discover_graph_ingest_runs(repo)
    rel_manifest = _repo_relative(manifest_path, repo)
    for run in runs:
        if run.manifest_path == rel_manifest or run.run_dir == _repo_relative(run_dir, repo):
            return run
    raise ValueError(f"graph-ingest manifest was not discoverable: {manifest_path}")


def _artifact_uri(repo: Path, artifact: dict[str, Any] | None) -> str | None:
    if not isinstance(artifact, dict):
        return None
    uri = artifact.get("uri")
    if not isinstance(uri, str):
        return None
    return _repo_relative((repo / uri).resolve(), repo)


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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    diagnostics = manifest.get("diagnostics", {})
    status["extraction_mode"] = diagnostics.get("extraction_mode")
    status["graph_extraction_profile"] = diagnostics.get("graph_extraction_profile")
    status["graph_extraction_profile_options"] = diagnostics.get("graph_extraction_profile_options")
    status["model_id"] = manifest.get("health", {}).get("model_id")
    status["candidate_node_count"] = manifest.get("health", {}).get("node_count", 0)
    status["candidate_edge_count"] = manifest.get("health", {}).get("edge_count", 0)
    status["candidate_beat_count"] = manifest.get("health", {}).get("beat_count", 0)
    status["estimated_cost_usd"] = manifest.get("health", {}).get("estimated_cost_usd")
    steps = manifest.get("steps") or []
    status["graph_steps"] = steps
    status["current_graph_step"] = next(
        (step for step in reversed(steps) if step.get("state") in {"running", "complete", "failed"}),
        None,
    )
    artifacts = manifest.get("artifacts") or {}
    status["pass_telemetry_path"] = _artifact_uri(repo, artifacts.get("pass_telemetry"))
    status["pass_outputs_path"] = _artifact_uri(repo, artifacts.get("pass_outputs"))
    status["consolidation_diagnostics_path"] = _artifact_uri(
        repo, artifacts.get("consolidation_diagnostics")
    )
    if summary.status == GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY.value:
        if manifest.get("errors") and manifest.get("diagnostics", {}).get("extraction_mode") == "llm_blocked":
            status["blocked_reason"] = manifest["errors"][0]
        else:
            status["blocked_reason"] = "Graph source bundle ready. Candidate graph extraction has not run yet."
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
        "next_actions": (
            ["build_graph_preview_bundle"]
            if normalized_recap_path
            else ["apply_normalize", "build_graph_preview_bundle"]
        ),
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
