"""Exact source/profile/model options for production category extraction."""

from __future__ import annotations

from dataclasses import dataclass

from src.graph_memory.extraction.extraction_profile import ExtractionProfile
from src.graph_memory.vocabulary.model import ContextVocabularyPacket
from typing import Any, Mapping


@dataclass(frozen=True)
class GraphExtractionOptions:
    """Source-domain-neutral options; session may be null when profile admits it."""

    campaign_id: str | None
    source_span_index: Mapping[str, Any]
    profile: ExtractionProfile
    model_id: str | None = None
    session_id: str | None = None
    session_number: int | None = None
    source_domain: str = "recap"
    enable_edge_vocabulary_packet: bool = False
    edge_vocabulary_packet: ContextVocabularyPacket | None = None
    enable_node_vocabulary_packet: bool = False
    node_vocabulary_packet: ContextVocabularyPacket | None = None
    enable_dynamic_node_vocabulary_packet: bool = False
    dynamic_node_vocabulary_nodes: tuple[Mapping[str, Any], ...] = ()
    enable_encounter_job_pass: bool = False
    enable_party_participation_attachment: bool = False
    enable_encounter_job_edge_guidance: bool = False
    enable_party_claimed_fill: bool = False

    @classmethod
    def from_profile(
        cls,
        *,
        profile: ExtractionProfile,
        campaign_id: str | None,
        source_span_index: Mapping[str, Any],
        session_id: str | None = None,
        session_number: int | None = None,
        source_domain: str = "recap",
        model_id: str | None = None,
        context_vocabulary_packet: ContextVocabularyPacket | None = None,
        enable_node_vocabulary_packet: bool = False,
        enable_edge_vocabulary_packet: bool = False,
    ) -> "GraphExtractionOptions":
        enable_node = enable_node_vocabulary_packet and context_vocabulary_packet is not None
        enable_edge = enable_edge_vocabulary_packet and context_vocabulary_packet is not None
        return cls(
            campaign_id=campaign_id,
            source_span_index=source_span_index,
            profile=profile,
            model_id=model_id,
            session_id=session_id,
            session_number=session_number,
            source_domain=source_domain,
            enable_node_vocabulary_packet=enable_node,
            node_vocabulary_packet=context_vocabulary_packet if enable_node else None,
            enable_edge_vocabulary_packet=enable_edge,
            edge_vocabulary_packet=context_vocabulary_packet if enable_edge else None,
            enable_dynamic_node_vocabulary_packet=profile.enable_dynamic_node_vocabulary_packet,
            enable_encounter_job_pass=profile.enable_encounter_job_pass,
            enable_party_participation_attachment=profile.enable_party_participation_attachment,
            enable_encounter_job_edge_guidance=profile.enable_encounter_job_edge_guidance,
            enable_party_claimed_fill=profile.enable_party_claimed_fill,
        )
