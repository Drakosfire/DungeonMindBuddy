"""Explicit recap extraction profile preserving current category-pass semantics."""

from __future__ import annotations

from src.graph_memory.extraction.extraction_profile import (
    ExtractionPassSpec,
    ExtractionProfile,
    register_extraction_profile,
)

RECAP_PROFILE_ID = "recap_category_v1"
RECAP_PROFILE_VERSION = "1.0"

EVIDENCE_RULE = (
    "Every positive object MUST include evidence_refs as an array of objects with: "
    '{"source_span_ref_id": "<span id from source packet>", '
    '"anchor_quotes": ["<verbatim phrase copied from that paragraph>"]}. '
    "anchor_quotes must be literal substrings from the cited paragraph text block — "
    "not summaries, not your own node labels, not regex, not invented snippets. "
    "Copy exact words from the source packet."
)

DEFAULT_SEMANTIC_STATE = {
    "canon_state": "played_canon",
    "lifecycle_state": "candidate",
    "evidence_role": "source_evidence",
    "authority_state": "system_derived",
    "visibility_state": "gm_private",
}

_NODE_PASSES: tuple[ExtractionPassSpec, ...] = (
    ExtractionPassSpec(
        pass_id="actor_pass",
        default_node_type="character",
        instruction=(
            "Extract named NON-PARTY NPCs, characters, and creatures only. "
            "Do NOT extract player characters or traveling companion NPCs — those are supplied as party anchors."
        ),
        progress_label="Extracting actors and NPCs",
    ),
    ExtractionPassSpec(
        pass_id="location_pass",
        default_node_type="location",
        instruction=(
            "Extract regions, towns, cities, roads, routes, sublocations, and named travel zones only."
        ),
        progress_label="Extracting locations",
    ),
    ExtractionPassSpec(
        pass_id="collective_pass",
        default_node_type="faction",
        instruction=(
            "Extract factions, councils, guards, mercenary groups, organizations, and parties (as collectives) only. "
            "Use node_type faction, organization, or group as appropriate."
        ),
        progress_label="Extracting factions and collectives",
    ),
    ExtractionPassSpec(
        pass_id="object_pass",
        default_node_type="item",
        instruction=(
            "Extract notable items, devices, artifacts, and objects only — not table-mechanics noise."
        ),
        progress_label="Extracting notable objects",
    ),
    ExtractionPassSpec(
        pass_id="thread_pass",
        default_node_type="mystery",
        instruction=(
            "Extract mysteries, clues, warnings, events, unresolved phenomena, and threads. "
            "Also emit ignored_items and deferred_items when appropriate."
        ),
        progress_label="Extracting mysteries and threads",
        include_dispositions=True,
    ),
)

_BEAT_PASS = ExtractionPassSpec(
    pass_id="beat_pass",
    default_node_type=None,
    instruction="Extract source-local beats (scenes, topic shifts, durable claims).",
    progress_label="Extracting session beats",
    kind="beat",
)

_ENCOUNTER_JOB_PASS = ExtractionPassSpec(
    pass_id="encounter_job_pass",
    default_node_type=None,
    instruction="Extract encounters and quests.",
    progress_label="Extracting encounters and quests",
    kind="encounter_job",
    allowed_node_types=("combat_encounter", "quest"),
)

_EDGE_PASS = ExtractionPassSpec(
    pass_id="edge_pass",
    default_node_type=None,
    instruction="Extract durable relationship edges among consolidated nodes.",
    progress_label="Extracting relationship edges",
    kind="edge",
)


def _build_recap_profile(
    *,
    profile_id: str,
    profile_version: str,
    enable_encounter_job_pass: bool,
    enable_party_participation_attachment: bool,
    enable_encounter_job_edge_guidance: bool,
    enable_dynamic_node_vocabulary_packet: bool,
    enable_party_claimed_fill: bool = True,
) -> ExtractionProfile:
    return ExtractionProfile(
        profile_id=profile_id,
        profile_version=profile_version,
        admitted_source_domains=frozenset({"recap"}),
        admitted_document_classes=None,
        node_passes=_NODE_PASSES,
        beat_pass=_BEAT_PASS,
        encounter_job_pass=_ENCOUNTER_JOB_PASS if enable_encounter_job_pass else None,
        edge_pass=_EDGE_PASS,
        evidence_rule=EVIDENCE_RULE,
        default_semantic_state=DEFAULT_SEMANTIC_STATE,
        enable_encounter_job_pass=enable_encounter_job_pass,
        enable_party_participation_attachment=enable_party_participation_attachment,
        enable_encounter_job_edge_guidance=enable_encounter_job_edge_guidance,
        enable_dynamic_node_vocabulary_packet=enable_dynamic_node_vocabulary_packet,
        enable_party_claimed_fill=enable_party_claimed_fill,
        allow_null_session=False,
        schema_ids={
            "envelope": "dmb_live_extractor_candidate_envelope_v0",
            "candidate_graph": "dmb_candidate_graph_preview_v0",
        },
        vocabulary_policy={"mode": "optional_context_packet"},
        post_extraction_validation_policy={"require_evidence_refs": True},
    )


RECAP_EXTRACTION_PROFILE = register_extraction_profile(
    _build_recap_profile(
        profile_id=RECAP_PROFILE_ID,
        profile_version=RECAP_PROFILE_VERSION,
        enable_encounter_job_pass=False,
        enable_party_participation_attachment=False,
        enable_encounter_job_edge_guidance=False,
        enable_dynamic_node_vocabulary_packet=False,
        enable_party_claimed_fill=True,
    )
)

# Legacy graph_extraction_profile names map onto explicit recap profile variants.
LEGACY_RECAP_PROFILE_ALIASES: dict[str, tuple[str, str]] = {
    "current_default": (RECAP_PROFILE_ID, RECAP_PROFILE_VERSION),
    "category_baseline": (RECAP_PROFILE_ID, RECAP_PROFILE_VERSION),
    "category_encounter_job_preview": ("recap_category_encounter_job_preview", "1.0"),
}

register_extraction_profile(
    _build_recap_profile(
        profile_id="recap_category_encounter_job_preview",
        profile_version="1.0",
        enable_encounter_job_pass=True,
        enable_party_participation_attachment=True,
        enable_encounter_job_edge_guidance=True,
        enable_dynamic_node_vocabulary_packet=False,
    )
)


def resolve_legacy_graph_extraction_profile(value: str | None) -> tuple[str, str]:
    if value is None:
        return RECAP_PROFILE_ID, RECAP_PROFILE_VERSION
    if value in LEGACY_RECAP_PROFILE_ALIASES:
        return LEGACY_RECAP_PROFILE_ALIASES[value]
    if "@" in value:
        profile_id, profile_version = value.split("@", 1)
        return profile_id, profile_version
    raise ValueError(f"unsupported graph_extraction_profile: {value}")
