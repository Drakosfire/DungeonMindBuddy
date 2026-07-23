"""Minimal worldbuilding plumbing profile (no category quality claims)."""

from __future__ import annotations

from src.graph_memory.extraction.extraction_profile import (
    ExtractionPassSpec,
    ExtractionProfile,
    register_extraction_profile,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    DEFAULT_SEMANTIC_STATE,
    EVIDENCE_RULE,
)

WORLDBUILDING_PLUMBING_PROFILE_ID = "worldbuilding_plumbing_v0"
WORLDBUILDING_PLUMBING_PROFILE_VERSION = "0.1"

_NODE_PASSES: tuple[ExtractionPassSpec, ...] = (
    ExtractionPassSpec(
        pass_id="actor_pass",
        default_node_type="character",
        instruction="Extract named characters, NPCs, and creatures only.",
        progress_label="Extracting actors and NPCs",
    ),
    ExtractionPassSpec(
        pass_id="location_pass",
        default_node_type="location",
        instruction="Extract regions, settlements, and named places only.",
        progress_label="Extracting locations",
    ),
    ExtractionPassSpec(
        pass_id="object_pass",
        default_node_type="item",
        instruction="Extract notable items and artifacts only.",
        progress_label="Extracting notable objects",
    ),
)

_EDGE_PASS = ExtractionPassSpec(
    pass_id="edge_pass",
    default_node_type=None,
    instruction="Extract durable relationship edges among consolidated nodes.",
    progress_label="Extracting relationship edges",
    kind="edge",
)

WORLDBUILDING_PLUMBING_PROFILE = register_extraction_profile(
    ExtractionProfile(
        profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
        profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
        admitted_source_domains=frozenset({"worldbuilding"}),
        admitted_document_classes=frozenset({"lore", "gazetteer", "faction", "place"}),
        node_passes=_NODE_PASSES,
        beat_pass=None,
        encounter_job_pass=None,
        edge_pass=_EDGE_PASS,
        evidence_rule=EVIDENCE_RULE,
        default_semantic_state={
            **DEFAULT_SEMANTIC_STATE,
            "canon_state": "worldbuilding_draft",
        },
        enable_encounter_job_pass=False,
        enable_party_participation_attachment=False,
        enable_encounter_job_edge_guidance=False,
        enable_dynamic_node_vocabulary_packet=False,
        allow_null_session=True,
        schema_ids={
            "envelope": "dmb_live_extractor_candidate_envelope_v0",
            "candidate_graph": "dmb_candidate_graph_preview_v0",
        },
        vocabulary_policy={"mode": "none"},
        post_extraction_validation_policy={"require_evidence_refs": True},
    )
)
