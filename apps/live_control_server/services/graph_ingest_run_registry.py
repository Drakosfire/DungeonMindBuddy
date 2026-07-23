"""Read-only discovery for graph-ingest preview runs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_review_lanes import (
    GraphReviewVocabularyMode,
)
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
# Sentinel digest for an existing source file that cannot produce a canonical digest
# (empty, whitespace-only, unreadable, or invalid UTF-8). Discovery must fail closed
# and never fall back to path-only matching for this value.
UNUSABLE_SOURCE_RECAP_DIGEST = "sha256:unusable"
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
    run_id: str | None = None
    run_label: str
    generated_at: str | None = None
    model_id: str | None = None
    model_provider: str | None = None
    extraction_profile: str | None = None
    extraction_mode: str | None = None
    vocabulary_mode: GraphReviewVocabularyMode = GraphReviewVocabularyMode.UNKNOWN
    runner_options_summary: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )
    diagnostics_summary: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )
    preview_union_available: bool = False
    # Server-owned product gate for Graph Review "Review & merge" (PR011A2).
    promotable: bool = False
    promotable_reason: str | None = None


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
    for search_root in _graph_ingest_search_roots(
        repo, include_eval_roots=include_eval_roots
    ):
        if not search_root.exists():
            continue
        for manifest_path in sorted(search_root.rglob(GRAPH_INGEST_MANIFEST_NAME)):
            summary = _summarize_manifest(
                repo,
                manifest_path,
                registry_root=search_root,
                include_eval_roots=include_eval_roots,
            )
            if summary is None:
                continue
            if campaign_id is not None and summary.campaign_id != campaign_id:
                continue
            if session_id is not None and summary.session_id != session_id:
                continue
            if (
                source_recap_path is not None or source_recap_sha256 is not None
            ) and not _manifest_matches_source_recap(
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
    include_eval_roots: bool = True,
) -> GraphIngestRunSummary:
    runs = discover_graph_ingest_runs(
        root,
        campaign_id=campaign_id,
        session_id=session_id,
        source_recap_path=source_recap_path,
        source_recap_sha256=source_recap_sha256,
        require_preview_union_store=True,
        include_eval_roots=include_eval_roots,
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
    """Match a GraphIngest run to the caller's current recap.

    When a content digest is available, require an exact full-digest match against
    the manifest or the SourceArtifact registry record's ``content_sha256``.
    Path equality is a fallback only when no digest was supplied (source missing
    or unresolved) — never when the caller marked the source unusable.
    """
    from graph_memory.ingestion.extraction_run import normalize_content_digest

    if source_recap_sha256 == UNUSABLE_SOURCE_RECAP_DIGEST:
        return False

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    requested_digest = normalize_content_digest(source_recap_sha256)
    if requested_digest:
        actual_hashes = [
            source.get("normalized_recap_sha256"),
            (payload.get("artifacts") or {}).get("normalized_recap", {}).get("sha256")
            if isinstance(payload.get("artifacts"), dict)
            else None,
        ]
        if any(
            normalize_content_digest(value) == requested_digest
            for value in actual_hashes
            if isinstance(value, str)
        ):
            return True
        # Older manifests may lack packaged digests — resolve the registered
        # SourceArtifact and compare its full content_sha256.
        artifact_id = str(source.get("source_artifact_id") or "").strip()
        if artifact_id:
            from apps.live_control_server.services.source_artifact_registry import (
                SourceArtifactRegistryError,
                get_source_artifact,
            )

            try:
                artifact = get_source_artifact(repo, artifact_id)
            except SourceArtifactRegistryError:
                return False
            if normalize_content_digest(artifact.content_sha256) == requested_digest:
                return True
        return False
    if not source_recap_path:
        return False
    raw_values = [
        source.get("normalized_recap_path"),
        source.get("input_path_record"),
    ]
    expected = _normalize_repo_path(repo, source_recap_path)
    return any(
        _normalize_repo_path(repo, value) == expected
        for value in raw_values
        if isinstance(value, str)
    )


def _normalize_repo_path(repo: Path, value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(repo).as_posix()
        except ValueError:
            return path.resolve().as_posix()
    return path.as_posix().lstrip("./")


def _graph_ingest_search_roots(
    repo: Path, *, include_eval_roots: bool = False
) -> list[Path]:
    env_root = os.environ.get(GRAPH_INGEST_RUNS_ENV)
    values = [env_root] if env_root else list(DEFAULT_GRAPH_INGEST_RUN_ROOTS)
    if include_eval_roots:
        values.extend(EVAL_GRAPH_INGEST_RUN_ROOTS)
    return [
        _resolve_repo_contained_path(Path(value), repo, must_exist=False)
        for value in values
    ]


def _summarize_manifest(
    repo: Path,
    manifest_path: Path,
    *,
    registry_root: Path,
    include_eval_roots: bool = False,
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

    metadata = _extract_graph_run_metadata(
        manifest, payload, safe_manifest_path, repo, preview_path
    )
    # Lazy import avoids circular dependency with promotable_ingest_run.
    from apps.live_control_server.services.promotable_ingest_run import (
        assess_manifest_promotability,
    )

    promotable, promotable_reason = assess_manifest_promotability(
        repo=repo,
        manifest_path=safe_manifest_path,
        payload=payload,
        registry_root=registry_root.resolve(),
        include_eval_roots=include_eval_roots,
    )
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
        promotable=promotable,
        promotable_reason=promotable_reason,
        **metadata,
    )


ScalarSummaryValue = str | int | float | bool | None
_SAFE_RUNNER_OPTION_KEYS = {
    "extraction_profile",
    "extraction_mode",
    "max_passes",
    "pass_count",
    "temperature",
    "model_id",
    "model_provider",
    "vocabulary_mode",
    "node_vocabulary",
    "edge_vocabulary",
    "dynamic_vocabulary",
    "include_eval_roots",
    "extract_graph",
    "force_graph_run",
    "graph_extraction_profile",
}
_DIAGNOSTICS_BOOLEAN_KEYS = (
    "preview_only",
    "candidate_extraction",
    "preview_import",
    "canon_promotion",
    "approved_memory_write",
    "corpus_mutation",
    "production_retrieval",
    "agent_interaction_connected",
    "runtime_projection_connected",
)
_HEALTH_SUMMARY_KEYS = (
    "candidate_graph_valid",
    "preview_union_store_valid",
    "node_count",
    "edge_count",
    "beat_count",
    "evidence_ref_count",
    "resolvable_evidence_ref_count",
    "openable_evidence_ref_count",
    "highlightable_evidence_ref_count",
    "estimated_cost_usd",
)


def _extract_graph_run_metadata(
    manifest: GraphIngestRunManifest,
    payload: dict[str, Any],
    safe_manifest_path: Path,
    repo: Path,
    preview_union_store_path: str | None,
) -> dict[str, Any]:
    extraction_profile = _first_scalar_string(
        payload,
        [
            ("extraction_profile",),
            ("metadata", "extraction_profile"),
            ("runner_options", "extraction_profile"),
            ("diagnostics", "extraction_profile"),
            ("source", "extraction_profile"),
            ("profile", "id"),
            ("profile", "name"),
        ],
    )
    extraction_mode = _first_scalar_string(
        payload,
        [
            ("extraction_mode",),
            ("metadata", "extraction_mode"),
            ("runner_options", "extraction_mode"),
            ("diagnostics", "extraction_mode"),
            ("extraction", "mode"),
            ("extraction", "kind"),
        ],
    ) or _infer_extraction_mode(manifest, payload)
    model_id = manifest.health.model_id or _first_scalar_string(
        payload,
        [
            ("model_id",),
            ("metadata", "model_id"),
            ("runner_options", "model_id"),
            ("diagnostics", "model_id"),
            ("extraction", "model_id"),
        ],
    )
    model_provider = _first_scalar_string(
        payload,
        [
            ("model_provider",),
            ("provider",),
            ("metadata", "model_provider"),
            ("metadata", "provider"),
            ("runner_options", "model_provider"),
            ("runner_options", "provider"),
            ("extraction", "model_provider"),
            ("extraction", "provider"),
        ],
    )
    vocabulary_mode = _extract_vocabulary_mode(payload)
    return {
        "run_id": manifest.run_id,
        "run_label": _build_run_label(
            safe_manifest_path,
            repo,
            manifest,
            extraction_profile,
            extraction_mode,
            vocabulary_mode,
            model_id,
        ),
        "generated_at": manifest.updated_at or manifest.created_at,
        "model_id": model_id,
        "model_provider": model_provider,
        "extraction_profile": extraction_profile,
        "extraction_mode": extraction_mode,
        "vocabulary_mode": vocabulary_mode,
        "runner_options_summary": _runner_options_summary(payload),
        "diagnostics_summary": _diagnostics_summary(manifest),
        "preview_union_available": preview_union_store_path is not None
        and manifest.health.preview_union_store_valid is True,
    }


def _first_scalar_string(
    payload: dict[str, Any], paths: list[tuple[str, ...]]
) -> str | None:
    for path in paths:
        value: Any = payload
        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _infer_extraction_mode(
    manifest: GraphIngestRunManifest, payload: dict[str, Any]
) -> str | None:
    if any(
        key in payload
        for key in ("category_passes", "pass_outputs", "pass_outputs_metadata")
    ):
        return "category"
    extraction = payload.get("extraction")
    if isinstance(extraction, dict) and any(
        key in extraction
        for key in ("category_passes", "pass_outputs", "pass_outputs_metadata")
    ):
        return "category"
    if manifest.diagnostics.candidate_extraction is False:
        return "none"
    return None


def _extract_vocabulary_mode(payload: dict[str, Any]) -> GraphReviewVocabularyMode:
    explicit = _first_scalar_string(
        payload,
        [
            ("vocabulary_mode",),
            ("metadata", "vocabulary_mode"),
            ("runner_options", "vocabulary_mode"),
            ("diagnostics", "vocabulary_mode"),
            ("vocabulary", "mode"),
        ],
    )
    if explicit in {mode.value for mode in GraphReviewVocabularyMode}:
        return GraphReviewVocabularyMode(explicit)
    scopes = [payload] + [
        payload.get(key)
        for key in ("metadata", "runner_options", "diagnostics", "vocabulary")
    ]

    def flag(names: tuple[str, ...]) -> bool | None:
        for scope in scopes:
            if isinstance(scope, dict):
                for name in names:
                    if isinstance(scope.get(name), bool):
                        return scope[name]
        return None

    if (
        flag(
            (
                "dynamic_vocabulary",
                "dynamic_vocabulary_enabled",
                "use_dynamic_vocabulary",
            )
        )
        is True
    ):
        return GraphReviewVocabularyMode.DYNAMIC
    node = (
        flag(("node_vocabulary", "node_vocabulary_enabled", "use_node_vocabulary"))
        is True
    )
    edge = (
        flag(("edge_vocabulary", "edge_vocabulary_enabled", "use_edge_vocabulary"))
        is True
    )
    if node and edge:
        return GraphReviewVocabularyMode.NODE_AND_EDGE
    if node:
        return GraphReviewVocabularyMode.NODE
    if edge:
        return GraphReviewVocabularyMode.EDGE
    if flag(("vocabulary_enabled", "use_vocabulary")) is False:
        return GraphReviewVocabularyMode.NONE
    return GraphReviewVocabularyMode.UNKNOWN


def _json_safe_scalar_summary(
    source: Any, *, safe_keys: set[str] | None = None
) -> dict[str, ScalarSummaryValue]:
    summary: dict[str, ScalarSummaryValue] = {}
    if not isinstance(source, dict):
        return summary
    for key, value in source.items():
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                flat_key = f"{key}.{child_key}"
                if (
                    safe_keys is not None
                    and child_key not in safe_keys
                    and flat_key not in safe_keys
                ):
                    continue
                if isinstance(child_value, str) and len(child_value) <= 240:
                    summary[flat_key] = child_value
                elif isinstance(child_value, (int, float, bool)) or child_value is None:
                    summary[flat_key] = child_value
            continue
        if safe_keys is not None and key not in safe_keys:
            continue
        if isinstance(value, str) and len(value) <= 240:
            summary[key] = value
        elif isinstance(value, (int, float, bool)) or value is None:
            summary[key] = value
    return summary


def _runner_options_summary(payload: dict[str, Any]) -> dict[str, ScalarSummaryValue]:
    summary: dict[str, ScalarSummaryValue] = {}
    sources = [
        payload.get(key) for key in ("runner_options", "options", "extraction_options")
    ]
    for parent in (payload.get("metadata"), payload.get("diagnostics")):
        if isinstance(parent, dict):
            sources.append(parent.get("runner_options"))
    for source in sources:
        summary.update(
            _json_safe_scalar_summary(source, safe_keys=_SAFE_RUNNER_OPTION_KEYS)
        )
    return summary


def _diagnostics_summary(
    manifest: GraphIngestRunManifest,
) -> dict[str, ScalarSummaryValue]:
    summary: dict[str, ScalarSummaryValue] = {}
    for key in _DIAGNOSTICS_BOOLEAN_KEYS:
        value = getattr(manifest.diagnostics, key, None)
        if isinstance(value, bool):
            summary[key] = value
    for key in _HEALTH_SUMMARY_KEYS:
        value = getattr(manifest.health, key, None)
        if isinstance(value, (str, int, float, bool)) or value is None:
            summary[key] = value
    summary["warnings_count"] = len(manifest.warnings)
    summary["errors_count"] = len(manifest.errors)
    summary["next_actions_count"] = len(manifest.next_actions)
    return summary


def _build_run_label(
    safe_manifest_path: Path,
    repo: Path,
    manifest: GraphIngestRunManifest,
    extraction_profile: str | None,
    extraction_mode: str | None,
    vocabulary_mode: GraphReviewVocabularyMode,
    model_id: str | None,
) -> str:
    parts: list[str] = []
    if manifest.source.source_label:
        parts.append(manifest.source.source_label)
    elif manifest.run_id:
        parts.append(manifest.run_id)
    else:
        parts.append(_repo_relative(safe_manifest_path.parent, repo).split("/")[-1])
    if extraction_profile:
        parts.append(extraction_profile)
    elif extraction_mode:
        parts.append(extraction_mode)
    if vocabulary_mode != GraphReviewVocabularyMode.UNKNOWN:
        parts.append(f"vocab:{vocabulary_mode.value}")
    if model_id:
        parts.append(model_id)
    parts.append(manifest.status.value)
    return " · ".join(part for part in parts if part)


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
