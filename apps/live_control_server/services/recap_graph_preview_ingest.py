"""Recap Process from submitted text through existing APP source/run owners."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.services.graph_preview_runner import (
    DEEPSEEK_MODEL,
    run_recap_production_extraction,
)
from apps.live_control_server.services.ingest_run_catalog import (
    IngestRunCatalogError,
    project_recap_extraction_run,
    reusable_recap_extraction,
)
from apps.live_control_server.services.source_artifact_registry import (
    create_recap_source_artifact,
)
from graph_memory.ingestion.native_recap_source import SourceScope
from src.graph_memory.extraction.recap_extraction_profile import (
    resolve_legacy_graph_extraction_profile,
)


def extract_recap(
    *,
    repo_root: Path,
    campaign_id: str,
    session: int,
    recap_text: str,
    force_graph_run: bool = False,
    graph_model_id: str | None = None,
    ingest_context: Any,
    supplemental_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run or reuse extraction; return the exact saved result without repackaging."""
    root = artifact_data_root(repo_root)
    from apps.live_control_server.services.source_artifact_registry import (
        _normalize_source_text,
    )

    text = _normalize_source_text(recap_text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    context = SourceScope.model_validate(ingest_context.model_dump()).model_dump()
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
    artifact = create_recap_source_artifact(
        root,
        world_id=context["native_world_id"],
        campaign_id=campaign_id,
        session_id=f"session-{session}",
        recap_text=text,
        expected_content_sha256=digest,
    )
    production = run_recap_production_extraction(
        repo_root=root,
        campaign_id=campaign_id,
        session_id=f"session-{session}",
        source_artifact_id=artifact.source_artifact_id,
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
