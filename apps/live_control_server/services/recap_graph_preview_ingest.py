"""Preview-only graph-ingest wiring for recap ingestion."""

# PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION:
# Retained until PR006/PR007 replaces live Graph Review preview materialization.

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
from apps.live_control_server.services.graph_preview_runner import (
    run_recap_production_extraction,
)
from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    normalize_graph_extraction_profile,
    run_graph_preview_extraction,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    resolve_legacy_graph_extraction_profile,
)
from src.graph_memory.vocabulary.model import ContextVocabularyPacket
from graph_memory.ingestion.extraction_run import ExtractionRunStatus
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


def _production_candidate_is_packageable(production: Any) -> bool:
    """Package a production candidate only when the ExtractionRun is reviewable."""
    run = getattr(production, "run", None)
    status = getattr(run, "status", None)
    return (
        getattr(production, "failure_kind", None) is None
        and getattr(production, "candidate_graph", None) is not None
        and status == ExtractionRunStatus.REVIEWABLE
    )


def _manifest_is_candidate_reusable(repo: Path, manifest_path: str | None) -> bool:
    """Candidate/preview-ready runs are reusable only with sidecar + production lineage."""
    return _manifest_has_known_entity_mentions(
        repo, manifest_path
    ) and _manifest_has_production_lineage(repo, manifest_path)


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
    category_client: Any | None = None,
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
    profile_id, profile_version = resolve_legacy_graph_extraction_profile(graph_extraction_profile)
    profile_sensitive_reuse = extract_graph or graph_extraction_profile is not None
    logger.info(
        "graph preview bundle requested campaign=%s session=session-%s normalized=%s "
        "source_recap_path=%s source_recap_sha256=%s force_graph_run=%s "
        "candidate_graph_path=%s extract_graph=%s model_id=%s graph_extraction_profile=%s "
        "profile_id=%s profile_version=%s",
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
        profile_id,
        profile_version,
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
            require_production_lineage=extract_graph,
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
    # Canonical ExtractionRun owns model extraction / refusal / failure / success.
    production = run_recap_production_extraction(
        repo_root=repo,
        campaign_id=campaign_id,
        session_id=f"session-{session}",
        recap_path=normalized,
        profile=graph_extraction_profile,
        model_id=graph_model_id,
        allow_llm=extract_graph,
        category_client=category_client,
        output_dir=run_dir / "extraction_run",
        context_vocabulary_packet=context_vocabulary_packet,
        enable_node_vocabulary_packet=enable_node_vocabulary_packet,
        enable_edge_vocabulary_packet=enable_edge_vocabulary_packet,
    )
    logger.info(
        "production extraction run_id=%s profile=%s status=%s failure_kind=%s",
        production.run.run_id,
        production.run.profile_id,
        production.run.status.value,
        production.failure_kind,
    )

    production_candidate: Path | None = None
    if extract_graph and _production_candidate_is_packageable(production):
        candidate_component = production.run.components.get("candidate_graph")
        if candidate_component is not None and str(candidate_component.uri).startswith("repo://"):
            production_candidate = (repo / str(candidate_component.uri).removeprefix("repo://")).resolve()
        else:
            production_candidate = (run_dir / "extraction_run" / "candidate_graph.json").resolve()
            production_candidate.parent.mkdir(parents=True, exist_ok=True)
            production_candidate.write_text(
                json.dumps(production.candidate_graph, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        if production.known_entity_mentions is not None:
            known_path = run_dir / "extraction_run" / "known_entity_mentions.json"
            known_path.parent.mkdir(parents=True, exist_ok=True)
            known_path.write_text(
                json.dumps(production.known_entity_mentions, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    elif extract_graph and production.candidate_graph is not None:
        logger.warning(
            "refusing to package non-reviewable production candidate run_id=%s status=%s failure_kind=%s",
            production.run.run_id,
            production.run.status.value,
            production.failure_kind,
        )

    # Legacy GraphIngest packaging only — never perform a second model call here.
    # When the production ExtractionRun is reviewable, its candidate is authoritative
    # over any manually supplied candidate_graph_path.
    legacy_candidate = production_candidate or candidate
    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id=campaign_id,
            session_id=f"session-{session}",
            normalized_recap_path=normalized,
            output_dir=run_dir,
            source_label=f"{campaign_id} session {session} normalized recap",
            allow_llm=False,
            model_id=graph_model_id,
            comparison_mode="none",
            candidate_graph_path=legacy_candidate,
            input_path_record=source_recap_path,
            graph_extraction_profile=requested_profile,
            context_vocabulary_packet=context_vocabulary_packet,
            enable_node_vocabulary_packet=enable_node_vocabulary_packet,
            enable_edge_vocabulary_packet=enable_edge_vocabulary_packet,
            source_span_index=(
                dict(production.source_span_index)
                if production.source_span_index is not None
                else None
            ),
            source_artifact_id=production.run.source_artifact_id,
        )
    )
    if (
        production.known_entity_mentions is not None
        and legacy_candidate is not None
        and result.output_dir.is_dir()
    ):
        known_out = result.output_dir / "known_entity_mentions.json"
        known_out.write_text(
            json.dumps(production.known_entity_mentions, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
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

    if extract_graph and not _production_candidate_is_packageable(production):
        # Persist llm_blocked on the GraphIngest manifest so materialize/status
        # reloads from disk still surface the production failure — including
        # typed-validation failures that still left a diagnostic candidate file.
        manifest_payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        diagnostics = dict(manifest_payload.get("diagnostics") or {})
        diagnostics["extraction_mode"] = "llm_blocked"
        diagnostics["extraction_run_id"] = production.run.run_id
        diagnostics["extraction_run_status"] = production.run.status.value
        diagnostics["failure_kind"] = production.failure_kind or "validation"
        diagnostics["source_artifact_id"] = production.run.source_artifact_id
        manifest_payload["diagnostics"] = diagnostics
        blocked_message = (
            production.diagnostics[0]
            if production.diagnostics
            else f"extraction failed: {production.failure_kind or production.run.status.value}"
        )
        manifest_payload["errors"] = list(production.diagnostics or [blocked_message])
        result.manifest_path.write_text(
            json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary = _summary_for_manifest(repo, result.manifest_path)

    if extract_graph and _production_candidate_is_packageable(production):
        manifest_payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        diagnostics = dict(manifest_payload.get("diagnostics") or {})
        diagnostics["extraction_mode"] = "category_decomposed"
        diagnostics["extraction_run_id"] = production.run.run_id
        diagnostics["extraction_run_status"] = production.run.status.value
        diagnostics["source_artifact_id"] = production.run.source_artifact_id
        manifest_payload["diagnostics"] = diagnostics
        health = dict(manifest_payload.get("health") or {})
        if production.model_id:
            health["model_id"] = production.model_id
        manifest_payload["health"] = health
        result.manifest_path.write_text(
            json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _assert_packaged_identity_matches_extraction_run(
            repo=repo,
            manifest_path=result.manifest_path,
            production_run=production.run,
        )
        summary = _summary_for_manifest(repo, result.manifest_path)

    status = _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
    status["extraction_run_id"] = production.run.run_id
    status["extraction_run_status"] = production.run.status.value
    status["source_artifact_id"] = production.run.source_artifact_id
    if extract_graph and _production_candidate_is_packageable(production):
        status["extraction_mode"] = "category_decomposed"
        if production.model_id:
            status["model_id"] = production.model_id
    elif extract_graph:
        status["extraction_mode"] = "llm_blocked"
        status["blocked_reason"] = (
            production.diagnostics[0]
            if production.diagnostics
            else f"extraction failed: {production.failure_kind or production.run.status.value}"
        )
    return status


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
                needs_extract = not _manifest_is_candidate_reusable(
                    repo, existing[0].manifest_path
                )
            else:
                needs_extract = (
                    not existing
                    or existing[0].status != GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value
                    or not _manifest_is_candidate_reusable(repo, existing[0].manifest_path)
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
        and (
            _manifest_is_candidate_reusable(repo, summary.manifest_path)
            if extract_graph
            else _manifest_has_known_entity_mentions(repo, summary.manifest_path)
        )
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
    if (
        summary.status == GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value
        and not force_graph_run
        and extract_graph
        and not _manifest_is_candidate_reusable(repo, summary.manifest_path)
    ):
        # Pre-migration / pre-repair extract-ready runs are not reusable.
        status = _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
        status["blocked_reason"] = (
            "existing preview-ready run is missing production ExtractionRun lineage "
            "or known_entity_mentions; re-run with force_graph_run or extract_graph to rebuild"
        )
        status["next_actions"] = ["force_graph_run", "extract_graph"]
        logger.warning(
            "preview union materialization refused pre-migration ready run campaign=%s session=session-%s manifest=%s",
            campaign_id,
            session,
            summary.manifest_path,
        )
        return status
    if (
        summary.status == GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value
        and not force_graph_run
        and not extract_graph
        and not _manifest_has_known_entity_mentions(repo, summary.manifest_path)
    ):
        status = _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
        status["blocked_reason"] = (
            "existing preview-ready run is missing known_entity_mentions; "
            "re-run with force_graph_run or extract_graph to rebuild"
        )
        status["next_actions"] = ["force_graph_run", "extract_graph"]
        return status
    if summary.status != GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value:
        status = _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
        if forced_build_status:
            for key in (
                "extraction_run_id",
                "extraction_run_status",
                "source_artifact_id",
                "extraction_mode",
                "blocked_reason",
                "model_id",
            ):
                if forced_build_status.get(key) is not None:
                    status[key] = forced_build_status[key]
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
    if not _manifest_has_known_entity_mentions(repo, summary.manifest_path):
        status = _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
        status["blocked_reason"] = (
            "candidate-ready run is missing known_entity_mentions; "
            "re-run with force_graph_run or extract_graph to rebuild"
        )
        status["next_actions"] = ["force_graph_run", "extract_graph"]
        return status
    if extract_graph and not _manifest_has_production_lineage(repo, summary.manifest_path):
        status = _status_from_summary(repo, summary, normalized_recap_path=normalized_recap_path)
        status["blocked_reason"] = (
            "candidate-ready run is missing production ExtractionRun lineage; "
            "re-run with force_graph_run or extract_graph to rebuild"
        )
        status["next_actions"] = ["force_graph_run", "extract_graph"]
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
    has_known_entity = _manifest_has_known_entity_mentions(repo, manifest_path)
    if isinstance(existing, dict) and existing.get("exists") is True:
        uri = existing.get("uri")
        if isinstance(uri, str):
            projection_path = _resolve_existing_repo_path(repo, uri, field_name="projection_payload")
            # Invalidate chipless pre-repair projections when the sidecar contract exists.
            if not has_known_entity or _projection_payload_is_known_entity_aware(projection_path):
                return projection_path

    projection_payload = build_plan_union_supergraph_projection_payload(
        session_id=session_id,
        graph_run_manifest_path=manifest_full,
    )
    if has_known_entity and isinstance(projection_payload, dict):
        projection_payload = {
            **projection_payload,
            "known_entity_mentions_contract": True,
        }
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


def _projection_payload_is_known_entity_aware(projection_path: Path) -> bool:
    try:
        payload = json.loads(projection_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("known_entity_mentions_contract") is True


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
    require_production_lineage: bool = False,
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
        # Extracted / preview-ready runs must carry the known-entity sidecar.
        # When extract_graph reuse is requested, also require production lineage so
        # pre-controller candidate-ready runs are rebuilt.
        if run.status in {
            GraphIngestRunStatus.CANDIDATE_VALIDATION_READY.value,
            GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value,
        }:
            if require_production_lineage:
                if not _manifest_is_candidate_reusable(repo, run.manifest_path):
                    logger.info(
                        "skipping reusable run missing production lineage or known_entity_mentions "
                        "campaign=%s session=session-%s status=%s manifest=%s",
                        campaign_id,
                        session,
                        run.status,
                        run.manifest_path,
                    )
                    continue
            elif not _manifest_has_known_entity_mentions(repo, run.manifest_path):
                logger.info(
                    "skipping reusable run missing known_entity_mentions campaign=%s session=session-%s "
                    "status=%s manifest=%s",
                    campaign_id,
                    session,
                    run.status,
                    run.manifest_path,
                )
                continue
        return run
    return None


def _load_extraction_run_record(repo: Path, run_id: str) -> Any | None:
    """Load one ExtractionRun registry record by id without re-validating all runs.

    The reuse gate needs the persisted claim (status, source artifact, component
    digests). Full SourceArtifact/evidence integrity was enforced when the run
    became REVIEWABLE; reloading every sibling record's evidence here would make
    lineage checks depend on unrelated registry state.
    """
    from apps.live_control_server.services.graph_run_registry import extraction_runs_path
    from graph_memory.ingestion.extraction_run import ExtractionRun

    path = extraction_runs_path(repo)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return None
    for row in records:
        if not isinstance(row, dict):
            continue
        if str(row.get("run_id") or "").strip() != run_id.strip():
            continue
        try:
            return ExtractionRun.model_validate(row)
        except Exception:  # noqa: BLE001 - malformed record is not reusable lineage
            return None
    return None


def _manifest_has_production_lineage(repo: Path, manifest_path: str | None) -> bool:
    """True when the run's ExtractionRun registry record proves reviewable lineage.

    Manifest diagnostics alone are insufficient: the referenced ExtractionRun must
    exist, be REVIEWABLE, match the packaged source artifact, and the packaged
    candidate (and preferably SourceSpanIndex) digests must equal the immutable
    ExtractionRun component digests.
    """
    from graph_memory.ingestion.extraction_run import (
        ExtractionRunComponentKind,
        normalize_content_digest,
    )

    if not manifest_path:
        return False
    try:
        manifest_full = (repo / manifest_path).resolve()
        payload = json.loads(manifest_full.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    if not isinstance(payload, dict):
        return False
    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    run_id = diagnostics.get("extraction_run_id")
    source_artifact_id = diagnostics.get("source_artifact_id")
    if not isinstance(run_id, str) or not run_id.strip():
        return False
    if not isinstance(source_artifact_id, str) or not source_artifact_id.strip():
        return False

    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    manifest_source_id = str(source.get("source_artifact_id") or "").strip()
    if not manifest_source_id or manifest_source_id != source_artifact_id.strip():
        return False

    run = _load_extraction_run_record(repo, run_id.strip())
    if run is None:
        return False
    if run.status != ExtractionRunStatus.REVIEWABLE:
        return False
    if run.source_artifact_id != source_artifact_id.strip():
        return False
    if run.source_artifact_id != manifest_source_id:
        return False

    candidate_component = run.components.get(ExtractionRunComponentKind.CANDIDATE_GRAPH.value)
    if candidate_component is None or not (candidate_component.sha256 or "").strip():
        return False

    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    candidate = artifacts.get(GraphIngestArtifactKind.CANDIDATE_GRAPH.value)
    if not isinstance(candidate, dict):
        return False
    uri = candidate.get("uri")
    if not isinstance(uri, str) or not uri.strip():
        return False
    candidate_path = (repo / uri).resolve() if not Path(uri).is_absolute() else Path(uri)
    try:
        candidate_path.relative_to(repo.resolve())
    except ValueError:
        return False
    if not candidate_path.is_file():
        return False

    packaged_bytes = candidate_path.read_bytes()
    packaged_digest = normalize_content_digest(
        candidate.get("sha256") or f"sha256:{hashlib.sha256(packaged_bytes).hexdigest()}"
    )
    component_digest = normalize_content_digest(candidate_component.sha256)
    if not packaged_digest or packaged_digest != component_digest:
        return False
    if packaged_digest != hashlib.sha256(packaged_bytes).hexdigest().lower():
        return False

    try:
        graph = json.loads(packaged_bytes.decode("utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(graph, dict):
        return False
    bound_ids = graph.get("source_artifact_ids") or []
    if not isinstance(bound_ids, list) or source_artifact_id not in bound_ids:
        return False

    span_component = run.components.get(ExtractionRunComponentKind.SOURCE_SPAN_INDEX.value)
    span_ref = artifacts.get(GraphIngestArtifactKind.SOURCE_SPAN_INDEX.value)
    if span_component is not None and (span_component.sha256 or "").strip() and isinstance(span_ref, dict):
        span_uri = span_ref.get("uri")
        if isinstance(span_uri, str) and span_uri.strip():
            span_path = (
                (repo / span_uri).resolve() if not Path(span_uri).is_absolute() else Path(span_uri)
            )
            try:
                span_path.relative_to(repo.resolve())
            except ValueError:
                return False
            if not span_path.is_file():
                return False
            span_bytes = span_path.read_bytes()
            packaged_span_digest = normalize_content_digest(
                span_ref.get("sha256") or f"sha256:{hashlib.sha256(span_bytes).hexdigest()}"
            )
            if packaged_span_digest != normalize_content_digest(span_component.sha256):
                return False
            if packaged_span_digest != hashlib.sha256(span_bytes).hexdigest().lower():
                return False

    return True


def _assert_packaged_identity_matches_extraction_run(
    *,
    repo: Path,
    manifest_path: Path,
    production_run: Any,
) -> None:
    """Assert GraphIngest packaging and ExtractionRun share one SourceArtifact ID."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = str(getattr(production_run, "source_artifact_id", "") or "").strip()
    if not expected:
        raise ValueError("ExtractionRun source_artifact_id is required")
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    if str(source.get("source_artifact_id") or "").strip() != expected:
        raise ValueError("GraphIngest source.source_artifact_id does not match ExtractionRun")
    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    if str(diagnostics.get("source_artifact_id") or "").strip() != expected:
        raise ValueError("GraphIngest diagnostics.source_artifact_id does not match ExtractionRun")

    span_uri = source.get("source_span_index_uri")
    if isinstance(span_uri, str) and span_uri.strip():
        span_path = (repo / span_uri).resolve()
        span_index = json.loads(span_path.read_text(encoding="utf-8"))
        if str(span_index.get("source_artifact_id") or "").strip() != expected:
            raise ValueError("packaged SourceSpanIndex source_artifact_id does not match ExtractionRun")

    provenance_uri = source.get("provenance_index_uri")
    if isinstance(provenance_uri, str) and provenance_uri.strip():
        provenance = json.loads((repo / provenance_uri).resolve().read_text(encoding="utf-8"))
        for row in provenance.get("source_artifacts") or []:
            if isinstance(row, dict) and str(row.get("artifact_id") or "").strip() != expected:
                raise ValueError("provenance_index artifact_id does not match ExtractionRun")

    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    candidate = artifacts.get(GraphIngestArtifactKind.CANDIDATE_GRAPH.value)
    if isinstance(candidate, dict):
        uri = candidate.get("uri")
        if isinstance(uri, str) and uri.strip():
            graph = json.loads((repo / uri).resolve().read_text(encoding="utf-8"))
            bound = graph.get("source_artifact_ids") or []
            if expected not in bound:
                raise ValueError("candidate_graph is not bound to ExtractionRun source_artifact_id")

def _manifest_has_known_entity_mentions(repo: Path, manifest_path: str | None) -> bool:
    """True when the run declares a readable known_entity_mentions artifact."""
    if not manifest_path:
        return False
    try:
        manifest_full = (repo / manifest_path).resolve()
        payload = json.loads(manifest_full.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
    if not isinstance(artifacts, dict):
        return False
    artifact = artifacts.get(GraphIngestArtifactKind.KNOWN_ENTITY_MENTIONS.value)
    if not isinstance(artifact, dict):
        return False
    uri = artifact.get("uri")
    if not isinstance(uri, str) or not uri.strip():
        return False
    sidecar_path = (repo / uri).resolve() if not Path(uri).is_absolute() else Path(uri)
    try:
        sidecar_path.relative_to(repo.resolve())
    except ValueError:
        return False
    return sidecar_path.is_file()


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


def _extracted_nodes_from_preview_union(
    repo: Path, preview_union_store_path: str | None
) -> list[dict[str, str]]:
    """Compact kind/label roster from the preview union store (for ingest diagnostics)."""

    if not preview_union_store_path:
        return []
    store_path = (repo / preview_union_store_path).resolve()
    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    raw_nodes = payload.get("nodes")
    if isinstance(raw_nodes, dict):
        node_iter = raw_nodes.values()
    elif isinstance(raw_nodes, list):
        node_iter = raw_nodes
    else:
        return []
    extracted: list[dict[str, str]] = []
    for node in node_iter:
        if not isinstance(node, dict):
            continue
        label = node.get("label") or node.get("name") or node.get("display_name")
        node_id = node.get("node_id") or node.get("id")
        kind = node.get("kind") or node.get("type") or node.get("node_type") or "unknown"
        if not label and not node_id:
            continue
        extracted.append(
            {
                "node_id": str(node_id or label),
                "kind": str(kind),
                "label": str(label or node_id),
            }
        )
    extracted.sort(key=lambda row: (row["kind"].lower(), row["label"].lower(), row["node_id"]))
    return extracted


def _status_from_summary(
    repo: Path, summary: GraphIngestRunSummary, *, normalized_recap_path: str | None
) -> dict[str, Any]:
    manifest_path = (repo / summary.manifest_path).resolve()
    candidate_path = _candidate_graph_path(repo, manifest_path)
    extracted_nodes = _extracted_nodes_from_preview_union(repo, summary.preview_union_store_path)
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
        "extracted_nodes": extracted_nodes,
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
    if diagnostics.get("extraction_run_id"):
        status["extraction_run_id"] = diagnostics.get("extraction_run_id")
    if diagnostics.get("extraction_run_status"):
        status["extraction_run_status"] = diagnostics.get("extraction_run_status")
    if diagnostics.get("source_artifact_id"):
        status["source_artifact_id"] = diagnostics.get("source_artifact_id")
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
        "extracted_nodes": [],
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
