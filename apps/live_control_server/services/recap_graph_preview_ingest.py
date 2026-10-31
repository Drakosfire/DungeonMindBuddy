"""Recap Process and status over canonical saved ExtractionRuns."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from apps.live_control_server import config
from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.services.ingest_run_catalog import (
    IngestRunCatalogError,
    inspect_recap_extraction_status,
    project_recap_extraction_run,
    reusable_recap_extraction,
)
from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_world_binding,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from apps.live_control_server.services.recap_ingest_context import CONTEXT_SCHEMA
from apps.live_control_server.services.graph_ingest_run_registry import (
    UNUSABLE_SOURCE_RECAP_DIGEST,
)
from apps.live_control_server.services.graph_preview_runner import (
    DEEPSEEK_MODEL,
    run_recap_production_extraction,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    resolve_legacy_graph_extraction_profile,
)


def inspect_recap_graph_preview_status(
    *,
    repo_root: Path,
    campaign_id: str,
    session: int,
    normalized_recap_path: str | None,
    managed_world_id: str | None = None,
) -> dict[str, Any]:
    """Return scoped database status without consulting operational run files."""
    if not managed_world_id:
        return {
            "status": "missing",
            "next_actions": [],
            "blocked_reason": "Select a World to inspect saved extraction work.",
        }
    try:
        binding = resolve_managed_world_binding(
            managed_world_id, root=config.managed_world_data_root(repo_root)
        )
    except (WorldGraphProjectionServiceError, config.ManagedWorldDataRootError) as exc:
        raise IngestRunCatalogError(
            "The selected World binding is unavailable.",
            code=getattr(exc, "code", "managed_world_unavailable"),
            status_code=getattr(exc, "status_code", 503),
        ) from exc
    context = {
        "schema": CONTEXT_SCHEMA,
        "managed_world_id": binding.managed_world_id,
        "native_world_id": binding.native_world_id,
        "binding_version": binding.binding_version,
        "campaign_id": campaign_id,
    }
    digest = _normalized_recap_digest(normalized_recap_path)
    if digest == UNUSABLE_SOURCE_RECAP_DIGEST:
        return {
            "status": "source_unverified",
            "source_match_mode": "unusable",
            "next_actions": ["repair_or_load_verified_source"],
            "blocked_reason": "The selected recap could not be read. Repair or load the source.",
        }
    status = inspect_recap_extraction_status(
        root=repo_root,
        campaign_id=campaign_id,
        session_id=f"session-{session}",
        context=context,
        source_content_sha256=digest,
    )
    if status is not None:
        return status
    return {
        "status": "missing",
        "node_count": 0,
        "edge_count": 0,
        "source_match_mode": "content_digest" if digest else "retained_database",
        "next_actions": ["generate_recap_memory"],
        "blocked_reason": "No saved extraction matches this World and source.",
    }


def extract_recap(
    *,
    repo_root: Path,
    campaign_id: str,
    session: int,
    normalized_recap_path: str,
    force_graph_run: bool = False,
    graph_model_id: str | None = None,
    ingest_context: Any,
    supplemental_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run or reuse extraction; return the exact saved result without repackaging."""
    root = artifact_data_root(repo_root)
    normalized = _resolve_existing_readable_path(
        normalized_recap_path, field_name="normalized_recap_path"
    )
    digest = _normalized_recap_digest(normalized_recap_path)
    if not digest or digest == UNUSABLE_SOURCE_RECAP_DIGEST:
        raise ValueError("The normalized recap could not be verified for extraction")
    context = ingest_context.as_lineage()
    if not force_graph_run:
        profile_id, version = resolve_legacy_graph_extraction_profile(None)
        reused = reusable_recap_extraction(
            root=root,
            campaign_id=campaign_id,
            session_id=f"session-{session}",
            context=context,
            source_content_sha256=digest,
            profile_id=f"{profile_id}@{version}",
            model_id=graph_model_id or DEEPSEEK_MODEL,
            supplemental_evidence=supplemental_evidence,
        )
        if reused is not None:
            return reused
    production = run_recap_production_extraction(
        repo_root=root,
        campaign_id=campaign_id,
        session_id=f"session-{session}",
        recap_path=normalized,
        model_id=graph_model_id,
        allow_llm=True,
        ingest_context=ingest_context,
        supplemental_evidence=supplemental_evidence,
    )
    status = project_recap_extraction_run(
        root=root,
        run=production.run,
        context=context,
        source_content_sha256=digest,
    )
    if status is None:
        raise IngestRunCatalogError(
            "The saved extraction does not match the requested source.",
            code="ingest_run_catalog_integrity_error",
            status_code=409,
        )
    return status


def _normalized_recap_digest(value: str | None) -> str | None:
    """Hash current import bytes with the source owner's normalization.

    An absent import permits retained database inspection. An existing invalid
    import must never downgrade to a missing digest or path-only identity.
    """
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        _normalize_source_text,
    )

    if not value:
        return None
    try:
        path = _resolve_existing_readable_path(
            value, field_name="normalized_recap_path"
        )
    except (FileNotFoundError, ValueError):
        return None
    try:
        text = _normalize_source_text(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SourceArtifactRegistryError):
        return UNUSABLE_SOURCE_RECAP_DIGEST
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _resolve_existing_readable_path(value: str | None, *, field_name: str) -> Path:
    if not value:
        raise ValueError(f"{field_name} is required")
    if value.startswith("file:"):
        raise ValueError(f"{field_name} must be a filesystem path, not a file URI")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = artifact_data_root(Path.cwd()) / path
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"{field_name} does not exist: {value}")
    if not path.is_file():
        raise ValueError(f"{field_name} must be a file: {value}")
    return path
