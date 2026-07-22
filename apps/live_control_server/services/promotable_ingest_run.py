"""Server-owned resolution of a graph-ingest run into promote inputs.

Product prepare must never accept browser-supplied source/candidate paths.
This module turns a ``run_id`` into validated artifact paths + digests from the
bounded graph-ingest run registry.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_MANIFEST_NAME,
    GraphIngestRunRegistryError,
    _graph_ingest_search_roots,
    _resolve_repo_contained_path,
)
from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestArtifactKind,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
)
from graph_memory.ingestion.graph_ingest_validate import (
    validate_graph_ingest_run_manifest,
)
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    load_typed_candidate_graph,
)

# run_id forms that embed campaign/session for cross-check against the manifest.
_RUN_ID_SCOPED = re.compile(
    r"^graph-ingest:(?P<campaign>[^:]+):(?P<session>[^:]+):.+$"
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


def ingest_runs_artifact_root(root: Path | None = None) -> Path:
    """Default repo-relative root for product ingest-run artifacts."""
    return ((root or repo_root()).resolve() / "out" / "graph_memory" / "runs").resolve()


def ingest_run_registry_roots(
    root: Path | None = None, *, include_eval_roots: bool = False
) -> list[Path]:
    """Configured registry search roots (honors ``DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT``)."""
    repo = (root or repo_root()).resolve()
    return list(
        _graph_ingest_search_roots(repo, include_eval_roots=include_eval_roots)
    )


def world_store_denied_roots(root: Path | None = None) -> list[Path]:
    """Durable world-graph trees that must never become evidentiary source.

    When ``world_graph_root()`` is the broad default ``<repo>/out``, only the
    worlds subtree is denied so configured ingest-run registry roots can remain
    registry-gated evidence. A more specific mutation root is denied wholesale.
    """
    repo = (root or repo_root()).resolve()
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


def assess_manifest_promotability(
    *,
    repo: Path,
    manifest_path: Path,
    payload: dict[str, Any],
    registry_root: Path,
    include_eval_roots: bool = False,
) -> tuple[bool, str | None]:
    """Server-owned promotability using the same seam as prepare.

    Runs the identical scope / artifact / containment validation as
    ``resolve_promotable_ingest_run`` for this manifest, plus duplicate
    ``run_id`` detection across the same search roots prepare uses.
    """
    run_id = str(payload.get("run_id") or "").strip()
    if not run_id:
        return False, "runId is missing"

    matches = _find_manifests_for_run_id(
        repo.resolve(), run_id, include_eval_roots=include_eval_roots
    )
    if len(matches) > 1:
        return False, "ambiguous graph-ingest runId"

    try:
        resolve_promotable_from_loaded_manifest(
            repo=repo.resolve(),
            manifest_path=manifest_path,
            payload=payload,
            registry_root=registry_root.resolve(),
            run_id=run_id,
        )
    except PromotableIngestRunError as exc:
        return False, str(exc)
    return True, None


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
    include_eval_roots: bool = False,
) -> PromotableIngestRun:
    """Resolve ``run_id`` to promote inputs; fail closed when not promotable."""
    text = (run_id or "").strip()
    if not text:
        raise PromotableIngestRunError(
            "runId is required",
            code="invalid_request",
            status_code=422,
        )

    repo = (root or repo_root()).resolve()
    matches = _find_manifests_for_run_id(
        repo, text, include_eval_roots=include_eval_roots
    )
    if matches:
        if len(matches) > 1:
            raise PromotableIngestRunError(
                f"ambiguous graph-ingest runId: {text}",
                code="run_ambiguous",
                status_code=409,
                diagnostics=[
                    "multiple manifests share this run_id",
                    *[str(path) for path, _, _ in matches],
                ],
            )
        manifest_path, payload, registry_root = matches[0]
        return resolve_promotable_from_loaded_manifest(
            repo=repo,
            manifest_path=manifest_path,
            payload=payload,
            registry_root=registry_root,
            run_id=text,
        )

    extraction = _resolve_promotable_extraction_run(repo, text)
    if extraction is not None:
        return extraction

    raise PromotableIngestRunError(
        f"unknown graph-ingest runId: {text}",
        code="run_not_found",
        status_code=404,
    )


def _resolve_repo_uri_path(repo: Path, uri: str) -> Path | None:
    text = (uri or "").strip()
    if not text or text.startswith("inline://"):
        return None
    if text.startswith("repo://"):
        text = text[len("repo://") :]
    path = Path(text)
    if not path.is_absolute():
        path = (repo / path).resolve()
    else:
        path = path.resolve()
    return path


def _materialize_sealed_source(
    repo: Path,
    *,
    run_dir: Path,
    candidates: list[Path],
) -> Path:
    """Return a readable source file under an allowlisted seal root."""
    for path in candidates:
        if not path.is_file():
            continue
        if is_under_ingest_runs(path, root=repo):
            return path
        # Workspace / other durable sources: copy into the run dir so prepare
        # seals a registry-owned evidence URI (never invents session scope).
        sealed = run_dir / "normalized_source.md"
        sealed.parent.mkdir(parents=True, exist_ok=True)
        sealed.write_bytes(path.read_bytes())
        return sealed
    raise PromotableIngestRunError(
        "extraction run source markdown is missing",
        code="run_not_promotable",
        status_code=422,
    )


def _resolve_promotable_extraction_run(
    repo: Path,
    run_id: str,
) -> PromotableIngestRun | None:
    """Resolve a canonical BLD-03 ExtractionRun when no graph-ingest manifest exists."""
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_extraction_run,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        get_source_artifact,
    )
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus

    try:
        run = get_extraction_run(repo, run_id)
    except GraphRunRegistryError:
        return None

    if run.status == ExtractionRunStatus.SUPERSEDED:
        raise PromotableIngestRunError(
            f"extraction run is superseded: {run_id}",
            code="run_not_promotable",
            status_code=422,
        )
    if run.status != ExtractionRunStatus.REVIEWABLE or not run.is_reviewable():
        raise PromotableIngestRunError(
            f"extraction run is not reviewable: {run_id}",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[f"status={run.status.value}"],
        )

    candidate = run.components.get("candidate_graph")
    source_span = run.components.get("source_span_index")
    source_component = run.components.get("source_artifact")
    if candidate is None or not candidate.exists or not candidate.uri:
        raise PromotableIngestRunError(
            "extraction run is missing candidate_graph component",
            code="run_not_promotable",
            status_code=422,
        )
    candidate_path = _resolve_repo_uri_path(repo, candidate.uri)
    if candidate_path is None or not candidate_path.is_file():
        raise PromotableIngestRunError(
            "candidate_graph path is missing",
            code="run_not_promotable",
            status_code=422,
        )

    run_dir = candidate_path.parent
    span_path = run_dir / "source_span_index.json"
    if source_span and source_span.uri:
        resolved_span = _resolve_repo_uri_path(repo, source_span.uri)
        if resolved_span is not None:
            span_path = resolved_span

    source_candidates: list[Path] = []
    if source_component and source_component.uri:
        resolved_source = _resolve_repo_uri_path(repo, source_component.uri)
        if resolved_source is not None:
            source_candidates.append(resolved_source)
    try:
        artifact = get_source_artifact(repo, run.source_artifact_id)
    except SourceArtifactRegistryError:
        artifact = None
    if artifact is not None and artifact.uri:
        resolved_artifact = _resolve_repo_uri_path(repo, artifact.uri)
        if resolved_artifact is not None:
            source_candidates.append(resolved_artifact)

    source_path = _materialize_sealed_source(
        repo, run_dir=run_dir, candidates=source_candidates
    )
    digest_raw = None
    if source_component is not None:
        digest_raw = source_component.sha256
    if not digest_raw and artifact is not None:
        digest_raw = artifact.content_sha256
    if not digest_raw:
        digest_raw = (run.lineage or {}).get("source_sha256")
    if not digest_raw:
        import hashlib

        digest_raw = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_revision_id = _normalize_digest(str(digest_raw))
    if not source_revision_id:
        raise PromotableIngestRunError(
            "extraction run is missing source content digest",
            code="run_not_promotable",
            status_code=422,
        )

    return PromotableIngestRun(
        run_id=run.run_id,
        campaign_id=(run.campaign_id or "").strip(),
        session_id=(run.session_id or "").strip(),
        status=run.status.value,
        extraction_profile=run.profile_id,
        source_artifact_id=run.source_artifact_id,
        source_revision_id=source_revision_id,
        normalized_recap_path=source_path,
        candidate_graph_path=candidate_path,
        preview_union_store_path=run_dir,
        manifest_path=run_dir / "extraction_run.json",
        run_dir=run_dir,
        registry_root=repo,
        sealed_source_uri=_seal_repo_uri(repo, source_path),
        diagnostics=[
            "resolved via canonical ExtractionRun registry",
            f"source_domain={run.source_domain}",
            f"session_scope={'null' if not (run.session_id or '').strip() else 'session'}",
        ],
        source_domain=(run.source_domain or "worldbuilding").strip() or "worldbuilding",
    )


def resolve_promotable_from_loaded_manifest(
    *,
    repo: Path,
    manifest_path: Path,
    payload: dict[str, Any],
    registry_root: Path,
    run_id: str,
) -> PromotableIngestRun:
    """Shared prepare/summary seam: validate one loaded manifest for promotion."""
    validation = validate_graph_ingest_run_manifest(payload)
    if validation.get("errors"):
        raise PromotableIngestRunError(
            "graph-ingest run manifest is invalid",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[str(item) for item in validation["errors"]],
        )

    try:
        manifest = GraphIngestRunManifest.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 — surface as promotability failure
        raise PromotableIngestRunError(
            "graph-ingest run manifest is invalid",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[str(exc)],
        ) from exc

    _assert_run_id_scope_matches(run_id, manifest)

    if manifest.status == GraphIngestRunStatus.FAILED:
        raise PromotableIngestRunError(
            "graph-ingest run status is failed",
            code="run_not_promotable",
            status_code=422,
        )
    if manifest.status != GraphIngestRunStatus.PREVIEW_UNION_STORE_READY:
        raise PromotableIngestRunError(
            "graph-ingest run is not preview_union_store_ready",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[f"status={manifest.status.value}"],
        )
    if manifest.health.candidate_graph_valid is not True:
        raise PromotableIngestRunError(
            "graph-ingest run candidate graph is not valid",
            code="run_not_promotable",
            status_code=422,
        )
    if manifest.health.preview_union_store_valid is not True:
        raise PromotableIngestRunError(
            "graph-ingest run preview union store is not valid",
            code="run_not_promotable",
            status_code=422,
        )

    run_dir = manifest_path.parent.resolve()
    normalized_path = _resolve_run_artifact_file(
        repo,
        run_dir,
        manifest,
        kind=GraphIngestArtifactKind.NORMALIZED_RECAP,
        fallback_uri=manifest.source.normalized_recap_path,
    )
    candidate_path = _resolve_run_artifact_file(
        repo,
        run_dir,
        manifest,
        kind=GraphIngestArtifactKind.CANDIDATE_GRAPH,
        fallback_uri=None,
    )
    preview_path = _resolve_run_artifact_file(
        repo,
        run_dir,
        manifest,
        kind=GraphIngestArtifactKind.PREVIEW_UNION_STORE,
        fallback_uri=None,
    )

    if is_under_world_store(normalized_path, root=repo):
        raise PromotableIngestRunError(
            "normalized recap must not reference the world graph store",
            code="run_not_promotable",
            status_code=422,
        )
    if is_under_world_store(candidate_path, root=repo):
        raise PromotableIngestRunError(
            "candidate graph must not reference the world graph store",
            code="run_not_promotable",
            status_code=422,
        )
    if is_under_world_store(preview_path, root=repo):
        raise PromotableIngestRunError(
            "preview union store must not reference the world graph store",
            code="run_not_promotable",
            status_code=422,
        )

    try:
        candidate_payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotableIngestRunError(
            "candidate graph could not be read as JSON",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[str(exc)],
        ) from exc
    if not isinstance(candidate_payload, dict):
        raise PromotableIngestRunError(
            "candidate graph root must be a JSON object",
            code="run_not_promotable",
            status_code=422,
        )
    # Prefer declared registry artifact when present; otherwise partition in-memory
    # so older runs that still embed heroes-party become promotable.
    from graph_memory.standing_context_partition import (
        partition_candidate_graph_by_provenance,
    )

    registry_kind = GraphIngestArtifactKind.REGISTRY_CONTEXT_GRAPH
    registry_declared = manifest.artifacts.get(registry_kind.value) is not None
    registry_context_graph_path: Path | None = None
    if registry_declared:
        try:
            registry_path = _resolve_run_artifact_file(
                repo,
                run_dir,
                manifest,
                kind=registry_kind,
                fallback_uri=None,
            )
            loaded_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except (PromotableIngestRunError, OSError, json.JSONDecodeError, TypeError) as exc:
            raise PromotableIngestRunError(
                "registry context graph is declared but unreadable or invalid",
                code="run_not_promotable",
                status_code=422,
                diagnostics=[str(exc)],
            ) from exc
        if not isinstance(loaded_registry, dict):
            raise PromotableIngestRunError(
                "registry context graph root must be a JSON object",
                code="run_not_promotable",
                status_code=422,
            )
        try:
            typed_registry = load_typed_candidate_graph(loaded_registry)
        except CandidateGraphMappingError as exc:
            raise PromotableIngestRunError(
                f"registry context graph is declared but not typed CandidateGraphPreview IR: {exc}",
                code="run_not_promotable",
                status_code=422,
                diagnostics=[str(exc)],
            ) from exc
        if not typed_registry.nodes:
            raise PromotableIngestRunError(
                "registry context graph must contain at least one node",
                code="run_not_promotable",
                status_code=422,
            )
        registry_campaign = str(typed_registry.campaign_id or "").strip()
        if not registry_campaign:
            raise PromotableIngestRunError(
                "registry context graph campaign_id is required",
                code="run_not_promotable",
                status_code=422,
                diagnostics=[f"manifest_campaign={manifest.campaign_id}"],
            )
        if registry_campaign != manifest.campaign_id:
            raise PromotableIngestRunError(
                "registry context graph campaign_id disagrees with run manifest",
                code="run_not_promotable",
                status_code=422,
                diagnostics=[
                    f"registry_campaign={registry_campaign}",
                    f"manifest_campaign={manifest.campaign_id}",
                ],
            )
        registry_context_graph_path = registry_path
    else:
        candidate_payload, _standing, _diag = partition_candidate_graph_by_provenance(
            candidate_payload
        )

    try:
        load_typed_candidate_graph(candidate_payload)
    except CandidateGraphMappingError as exc:
        raise PromotableIngestRunError(
            f"candidate graph is not typed CandidateGraphPreview IR: {exc}",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[str(exc)],
        ) from exc

    artifact_digest = None
    normalized_artifact = manifest.artifacts.get(
        GraphIngestArtifactKind.NORMALIZED_RECAP.value
    )
    if normalized_artifact is not None:
        artifact_digest = normalized_artifact.sha256
    source_revision_id = _normalize_digest(
        manifest.source.normalized_recap_sha256 or artifact_digest
    )
    if not source_revision_id:
        raise PromotableIngestRunError(
            "graph-ingest run is missing normalized_recap sha256",
            code="run_not_promotable",
            status_code=422,
        )

    source_artifact_id = (manifest.source.source_artifact_id or "").strip()
    if not source_artifact_id:
        raise PromotableIngestRunError(
            "graph-ingest run is missing source_artifact_id",
            code="run_not_promotable",
            status_code=422,
        )

    try:
        normalized_path.resolve().relative_to(registry_root.resolve())
        candidate_path.resolve().relative_to(registry_root.resolve())
        preview_path.resolve().relative_to(registry_root.resolve())
    except ValueError as exc:
        raise PromotableIngestRunError(
            "graph-ingest run artifacts escape the matched registry root",
            code="run_not_promotable",
            status_code=422,
        ) from exc

    sealed_source_uri = _seal_repo_uri(repo, normalized_path)
    extraction_profile = _extraction_profile(payload)
    diagnostics = [
        f"resolved_run_id:{manifest.run_id}",
        f"campaign_id:{manifest.campaign_id}",
        f"session_id:{manifest.session_id}",
        f"status:{manifest.status.value}",
        f"registry_root:{registry_root}",
    ]
    if registry_context_graph_path is not None:
        diagnostics.append(
            f"registry_context_graph_path:{registry_context_graph_path}"
        )

    return PromotableIngestRun(
        run_id=manifest.run_id,
        campaign_id=manifest.campaign_id,
        session_id=manifest.session_id,
        status=manifest.status.value,
        extraction_profile=extraction_profile,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        normalized_recap_path=normalized_path,
        candidate_graph_path=candidate_path,
        preview_union_store_path=preview_path,
        manifest_path=manifest_path,
        run_dir=run_dir,
        registry_root=registry_root.resolve(),
        sealed_source_uri=sealed_source_uri,
        registry_context_graph_path=registry_context_graph_path,
        diagnostics=diagnostics,
    )


def _find_manifests_for_run_id(
    repo: Path,
    run_id: str,
    *,
    include_eval_roots: bool,
) -> list[tuple[Path, dict[str, Any], Path]]:
    matches: list[tuple[Path, dict[str, Any], Path]] = []
    for search_root in _graph_ingest_search_roots(
        repo, include_eval_roots=include_eval_roots
    ):
        if not search_root.exists():
            continue
        for manifest_path in sorted(search_root.rglob(GRAPH_INGEST_MANIFEST_NAME)):
            try:
                safe = _resolve_repo_contained_path(manifest_path, repo)
                payload = json.loads(safe.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, GraphIngestRunRegistryError):
                continue
            if not isinstance(payload, dict):
                continue
            if str(payload.get("run_id") or "").strip() != run_id:
                continue
            matches.append((safe, payload, search_root.resolve()))
    return matches


def _assert_run_id_scope_matches(run_id: str, manifest: GraphIngestRunManifest) -> None:
    match = _RUN_ID_SCOPED.match(run_id)
    if match is None:
        return
    campaign = match.group("campaign")
    session = match.group("session")
    if campaign != manifest.campaign_id or session != manifest.session_id:
        raise PromotableIngestRunError(
            "runId campaign/session does not match the run manifest",
            code="run_scope_mismatch",
            status_code=422,
            diagnostics=[
                f"run_id_campaign={campaign}",
                f"run_id_session={session}",
                f"manifest_campaign={manifest.campaign_id}",
                f"manifest_session={manifest.session_id}",
            ],
        )


def _resolve_run_artifact_file(
    repo: Path,
    run_dir: Path,
    manifest: GraphIngestRunManifest,
    *,
    kind: GraphIngestArtifactKind,
    fallback_uri: str | None,
) -> Path:
    artifact = manifest.artifacts.get(kind.value)
    uri = None
    if artifact is not None and isinstance(artifact.uri, str) and artifact.uri.strip():
        uri = artifact.uri.strip()
    elif fallback_uri and fallback_uri.strip():
        uri = fallback_uri.strip()
    if not uri:
        raise PromotableIngestRunError(
            f"graph-ingest run is missing {kind.value} artifact",
            code="run_not_promotable",
            status_code=422,
        )
    try:
        path = _resolve_repo_contained_path(Path(uri), repo)
    except (GraphIngestRunRegistryError, FileNotFoundError) as exc:
        raise PromotableIngestRunError(
            f"graph-ingest run {kind.value} artifact is missing or unsafe",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[str(exc)],
        ) from exc
    if not path.is_file():
        raise PromotableIngestRunError(
            f"graph-ingest run {kind.value} artifact is not a file",
            code="run_not_promotable",
            status_code=422,
        )
    try:
        path.relative_to(run_dir)
    except ValueError as exc:
        raise PromotableIngestRunError(
            f"graph-ingest run {kind.value} artifact escapes the run directory",
            code="run_not_promotable",
            status_code=422,
        ) from exc
    return path


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


def _extraction_profile(payload: dict[str, Any]) -> str | None:
    for key_path in (
        ("extraction_profile",),
        ("metadata", "extraction_profile"),
        ("runner_options", "extraction_profile"),
        ("diagnostics", "graph_extraction_profile"),
        ("diagnostics", "extraction_profile"),
    ):
        value: Any = payload
        for key in key_path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
