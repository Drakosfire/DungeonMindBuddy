"""Resolve exact database ingestion runs for governed promotion.

File manifests and directory discovery cannot create publication authority.
Canonical component readers are being cut over to their immutable byte owner.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apps.live_control_server.config import ArtifactDataRootError, artifact_data_root, repo_root

from apps.live_control_server.services import graph_run_registry as run_registry
from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    ReviewableExtractionData,
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
    data: ReviewableExtractionData
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
    # An undeclared World stays None; never invent DEFAULT_WORLD_ID.
    world_id: str | None = None
    # Presentation metadata only. Exact source/span bytes are carried in data.
    source_span_index_path: Path | None = None
    source_span_index_sha256: str | None = None
    # Immutable MIND membership/head observation captured before recap extraction.
    ingest_context: dict[str, Any] | None = None



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


def _resolve_extraction_component_path(repo: Path, uri: str) -> Path:
    """Inert display metadata; never resolve symlinks or inspect a directory."""
    return repo / uri.removeprefix("repo://")


def _resolve_promotable_extraction_run(
    repo: Path,
    run_id: str,
) -> PromotableIngestRun | None:
    """Resolve the sole live ExtractionRun promotion path."""
    try:
        data = run_registry.load_reviewable_extraction_data(repo, run_id)
        run, artifact = data.run, data.source_artifact
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

    candidate_path = _resolve_extraction_component_path(
        repo, run.components["candidate_graph"].uri
    )
    source_path = _resolve_extraction_component_path(
        repo, run.components["source_artifact"].uri
    )
    span_index_path = _resolve_extraction_component_path(
        repo, run.components["source_span_index"].uri
    )

    source_revision_id = _normalize_digest(artifact.content_sha256)
    if not source_revision_id:
        raise PromotableIngestRunError(
            "extraction run SourceArtifact is missing a content digest",
            code="run_not_promotable",
            status_code=422,
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
        data=data,
        normalized_recap_path=source_path,
        candidate_graph_path=candidate_path,
        preview_union_store_path=run_dir,
        manifest_path=run_dir / "extraction_run.json",
        run_dir=run_dir,
        registry_root=repo,
        sealed_source_uri=artifact.uri,
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


EXTRACTION_RUN_BINDING_KEY = "extraction_run"


def extraction_run_binding(data: ReviewableExtractionData) -> dict[str, Any]:
    """Pins inside the existing reviewed effect; no new receipt or authority."""
    run = data.run
    return {
        "run_id": run.run_id, "run_revision": run.revision,
        "profile_id": run.profile_id, "source_domain": run.source_domain,
        "campaign_id": run.campaign_id, "session_id": run.session_id,
        "world_id": data.source_artifact.world_id,
        "source_artifact_id": run.source_artifact_id,
        "source_revision_id": _normalize_digest(data.source_artifact.content_sha256),
        "components": {
            kind: _normalize_digest(run.components[kind].sha256)
            for kind in ("source_artifact", "candidate_graph", "source_span_index")
        },
    }


def seal_extraction_run(package: dict[str, Any], data: ReviewableExtractionData) -> dict[str, Any]:
    from graph_memory.extract_promote_proposal import compute_proposal_digest
    sealed = copy.deepcopy(package)
    effect = dict(sealed.get("effect") or {})
    effect[EXTRACTION_RUN_BINDING_KEY] = extraction_run_binding(data)
    sealed["effect"] = effect
    sealed["proposal_digest"] = compute_proposal_digest(effect)
    return sealed


def load_bound_extraction_run(package: dict[str, Any], *, root: Path) -> ReviewableExtractionData:
    """Reopen only the exact reviewed APP run; no locator discovery/fallback."""
    from graph_memory.extract_promote_proposal import compute_proposal_digest
    from apps.live_control_server.services.candidate_graph_admission import canonical_candidate_digest

    effect = package.get("effect") or {}
    binding = effect.get(EXTRACTION_RUN_BINDING_KEY)
    if (not isinstance(binding, dict) or not isinstance(binding.get("run_id"), str)
        or not binding["run_id"].strip()
        or package.get("proposal_digest") != compute_proposal_digest(effect)):
        raise PromotableIngestRunError(
            "Exact extraction run binding is required; prepare this review again.",
            code="candidate_binding_invalid", status_code=409,
        )
    try:
        data = run_registry.load_reviewable_extraction_data(root, binding["run_id"])
    except GraphRunRegistryError as exc:
        raise PromotableIngestRunError(str(exc), code="candidate_binding_invalid",
                                      status_code=exc.status_code) from exc
    admission = effect.get("candidate_admission") or {}
    if (binding != extraction_run_binding(data)
        or effect.get("source_artifact_id") != data.run.source_artifact_id
        or effect.get("source_revision_id") != _normalize_digest(data.source_artifact.content_sha256)
        or (data.source_artifact.world_id is not None and effect.get("world_id") != data.source_artifact.world_id)
        or (effect.get("contribution_meta") or {}).get("campaign_scope") != data.run.campaign_id
        or admission.get("candidate_digest") != canonical_candidate_digest(json.loads(data.candidate_bytes))):
        raise PromotableIngestRunError(
            "Reviewed extraction run or component pins changed; prepare again.",
            code="candidate_binding_invalid", status_code=409,
        )
    return data
