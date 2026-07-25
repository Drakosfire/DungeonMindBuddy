"""Live-control wiring for the production graph extraction controller."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    create_recap_source_artifact,
    load_registered_source_artifact_text,
    load_source_span_index,
)
from graph_memory.source_span import source_span_index_to_dict
from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    ProductionExtractionResult,
    run_production_extraction,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    resolve_legacy_graph_extraction_profile,
)
from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource
from src.graph_memory.extraction.worldbuilding_extraction_profile import (
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
)
from src.graph_memory.vocabulary.model import ContextVocabularyPacket


def _normalized_from_registered(
    root: Path,
    source_artifact_id: str,
) -> NormalizedExtractionSource:
    artifact, text = load_registered_source_artifact_text(root, source_artifact_id)
    index = load_source_span_index(root, source_artifact_id)
    return NormalizedExtractionSource(
        source_artifact_id=artifact.source_artifact_id,
        source_domain=str(artifact.source_domain),
        source_text=text,
        source_sha256=artifact.content_sha256 or "",
        source_uri=artifact.uri,
        campaign_id=artifact.campaign_id,
        session_id=artifact.session_id,
        document_class=artifact.document_class,
        source_span_index=source_span_index_to_dict(index),
    )


def run_recap_production_extraction(
    *,
    repo_root: Path,
    campaign_id: str,
    session_id: str,
    recap_path: Path,
    profile: str | None = None,
    model_id: str | None = None,
    allow_llm: bool = False,
    category_client: Any | None = None,
    output_dir: Path | None = None,
    context_vocabulary_packet: ContextVocabularyPacket | None = None,
    enable_node_vocabulary_packet: bool = False,
    enable_edge_vocabulary_packet: bool = False,
) -> ProductionExtractionResult:
    profile_id, profile_version = resolve_legacy_graph_extraction_profile(profile)
    artifact = create_recap_source_artifact(
        repo_root,
        campaign_id=campaign_id,
        session_id=session_id,
        recap_path=recap_path,
    )
    source = _normalized_from_registered(repo_root, artifact.source_artifact_id)
    return run_production_extraction(
        ProductionExtractionRequest(
            repo_root=repo_root,
            source=source,
            profile_id=profile_id,
            profile_version=profile_version,
            model_id=model_id,
            allow_llm=allow_llm,
            category_client=category_client,
            output_dir=output_dir,
            context_vocabulary_packet=context_vocabulary_packet,
            enable_node_vocabulary_packet=enable_node_vocabulary_packet,
            enable_edge_vocabulary_packet=enable_edge_vocabulary_packet,
        )
    )


def run_worldbuilding_production_extraction(
    *,
    repo_root: Path,
    source_artifact_id: str,
    profile_id: str = WORLDBUILDING_PROFILE_ID,
    profile_version: str = WORLDBUILDING_PROFILE_VERSION,
    model_id: str | None = None,
    allow_llm: bool = False,
    category_client: Any | None = None,
    output_dir: Path | None = None,
) -> ProductionExtractionResult:
    """Extract from an already-registered worldbuilding SourceArtifact only."""
    source = _normalized_from_registered(repo_root, source_artifact_id)
    if source.source_domain != "worldbuilding":
        raise SourceArtifactRegistryError(
            "worldbuilding extraction requires a worldbuilding SourceArtifact",
            status_code=422,
        )
    return run_production_extraction(
        ProductionExtractionRequest(
            repo_root=repo_root,
            source=source,
            profile_id=profile_id,
            profile_version=profile_version,
            model_id=model_id,
            allow_llm=allow_llm,
            category_client=category_client,
            output_dir=output_dir,
        )
    )
