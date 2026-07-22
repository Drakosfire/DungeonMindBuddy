"""Live-control wiring for the production graph extraction controller."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    ProductionExtractionResult,
    run_production_extraction,
)
from src.graph_memory.extraction.recap_source_adapter import RecapSourceAdapter
from src.graph_memory.extraction.worldbuilding_source_adapter import WorldbuildingSourceAdapter
from src.graph_memory.extraction.recap_extraction_profile import (
    resolve_legacy_graph_extraction_profile,
)
from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
    WORLDBUILDING_PLUMBING_PROFILE_ID,
    WORLDBUILDING_PLUMBING_PROFILE_VERSION,
)
from src.graph_memory.vocabulary.model import ContextVocabularyPacket


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
    source = RecapSourceAdapter(
        campaign_id=campaign_id,
        session_id=session_id,
        recap_path=recap_path,
        source_uri=recap_path.as_posix(),
    ).normalize()
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
    source_path: Path | None = None,
    source_text: str | None = None,
    campaign_id: str | None = None,
    document_class: str | None = "lore",
    model_id: str | None = None,
    allow_llm: bool = False,
    category_client: Any | None = None,
    output_dir: Path | None = None,
) -> ProductionExtractionResult:
    source = WorldbuildingSourceAdapter(
        source_artifact_id=source_artifact_id,
        source_path=source_path,
        source_text=source_text,
        campaign_id=campaign_id,
        document_class=document_class,
        source_uri=source_path.as_posix() if source_path is not None else None,
    ).normalize()
    return run_production_extraction(
        ProductionExtractionRequest(
            repo_root=repo_root,
            source=source,
            profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
            profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
            model_id=model_id,
            allow_llm=allow_llm,
            category_client=category_client,
            output_dir=output_dir,
        )
    )
