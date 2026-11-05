"""Source-only Recap extraction; stored v1 runs retain their historical identity."""

from __future__ import annotations

from dataclasses import replace

from src.graph_memory.predicate_catalog import RECAP_SOURCE_ORDER, recap_predicate_meaning_guidance

from src.graph_memory.extraction.extraction_profile import (
    ExtractionPassSpec,
    ExtractionProfile,
    register_extraction_profile,
)

RECAP_PROFILE_ID = "recap_category_v2"
RECAP_PROFILE_VERSION = "2.0"

RECAP_READ_PROFILE_IDS = frozenset({
    "recap_category_v1@1.0",  # saved history only, never a registered generator
    "recap_category_v2@2.0",
    "recap_category_encounter_job_preview@2.0",
})

EVIDENCE_RULE = (
    "Every positive object MUST include evidence_refs as an array of objects with: "
    '{"source_span_ref_id": "<span id from source packet>", '
    '"anchor_quotes": ["<verbatim phrase copied from that paragraph>"]}. '
    "anchor_quotes must be literal substrings from the cited paragraph text block — "
    "not summaries, not your own node labels, not regex, not invented snippets. "
    "Copy exact words from the source packet."
)

_NODE_DESCRIPTION_COVERAGE = (
    "For each extracted node, use its description to retain the source-supported "
    "observations about that exact referent: its actions and experiences, states "
    "and properties, outcomes and changes, and the circumstances needed to "
    "understand them. Include explicit negative findings and descriptive details "
    "that contribute knowledge about the referent. Retain these observations even "
    "when they also belong in a scene or beat summary. Keep the observations "
    "within their supported referent and scene, using the existing evidence and "
    "source-faithfulness requirements. State the source-supported participants, "
    "actions, affected objects, and outcomes explicitly in the description. "
    "Do not leave a material detail only in an evidence quote, beat summary, "
    "or relationship label. Preserve source ambiguity rather than filling "
    "missing details by inference."
)

# These instructions belong to recap extraction only. Keep them out of the
# shared EVIDENCE_RULE, which is also used by Worldbuilding profiles.
_RECAP_SOURCE_FAITHFULNESS = (
    "Preserve the source's modality, attribution, time, and scope. Keep plans, "
    "intentions, proposals, possibilities, and reported beliefs distinct from "
    "events that actually occurred. Keep attribution and uncertainty in each prose "
    "assertion, including descriptions, summaries, titles, and labels. Carry the "
    "qualification when a claim is shortened to adjectives or repeated in another "
    "entity's description; do not rely on an evidence quote or another node to "
    "supply it. An uncertain actor attribution stays uncertain in every prose "
    "mention of that action. Retain the other supported details rather than "
    "dropping the whole entity. Do not treat similar names, spelling, "
    "possessives, topic proximity, or a shared location as proof that two "
    "mentions identify the same entity. Resolve references only as specifically "
    "as the source supports; do not add unstated membership, identity, or events. "
    "Distinguish in-world assertions from table presentation and rhetorical language. "
    "A table handout or figurative mention does not establish a physical object, "
    "character attribute, possession, or in-world event. Preserve supported table "
    "observations as such without promoting them into world facts. Parentheses "
    "alone do not determine authority: retain explicitly narrated in-world "
    "objects and actions even when parenthetical."
)

_PASS_SOURCE_FAITHFULNESS: dict[str, str] = {
    "actor_pass": (
        "Keep similarly named people and creatures as separate candidates unless "
        "the source explicitly establishes that they are the same entity."
    ),
    "location_pass": (
        "When coordinated place nouns name distinct buildings or sites, extract "
        "them separately instead of combining them into one composite location. "
        "Keep a compound name together when it refers to one place."
    ),
    "collective_pass": (
        "Include source-mentioned informal populations (for example, children, "
        "refugees, or townsfolk) when they function as meaningful participants "
        "or subjects. Do not invent a name, membership, origin, or continuity "
        "beyond what the source states. Repeated role labels in different scenes "
        "do not establish one continuing group. Keep each group's actions within "
        "its supported scene and participant scope. Do not attach actions from "
        "another scene to a specifically scoped group merely because the role "
        "labels match. Preserve continuity when the source supports that these "
        "are the same participants."
    ),
    "beat_pass": (
        "Describe what happened separately from what was intended or planned. "
        "An intended action is not a completed action; retain the source's "
        "attribution and uncertainty in the beat summary."
    ),
    "encounter_job_pass": (
        "Do not describe an intended or proposed encounter action as having "
        "occurred unless the source says it occurred."
    ),
    "edge_pass": (
        "Read each proposed edge as from_node_id → relationship_type → to_node_id. "
        "Evidence must support the relationship itself, including its direction "
        "and the predicate's meaning, not only the existence of its endpoints. "
        "A cautious label does not qualify the assertion made by the predicate: "
        "a promise or intention is not a completed action. If no catalog predicate "
        "faithfully expresses the source's modality, omit that edge rather than "
        "assert a completed relationship. Keep broad plural references broad "
        "unless the source directly identifies the specific listed node or "
        "subgroup. Do not bind an event to the nearest topically related node "
        "by proximity alone. Retain every supported edge whose listed endpoints "
        "and catalog predicate faithfully express the source."
    ),
}


def _with_recap_source_faithfulness(spec: ExtractionPassSpec) -> ExtractionPassSpec:
    pass_guidance = _PASS_SOURCE_FAITHFULNESS.get(spec.pass_id, "")
    coverage = f"{_NODE_DESCRIPTION_COVERAGE}\n\n" if spec.kind == "node" else ""
    if spec.pass_id == "edge_pass":
        pass_guidance = f"{pass_guidance}\n\n{recap_predicate_meaning_guidance(capabilities=spec.predicate_capabilities)}"
    return replace(
        spec,
        instruction=(
            f"{spec.instruction}\n\n"
            f"{coverage}"
            f"Source-faithfulness requirements: {_RECAP_SOURCE_FAITHFULNESS}"
            f"{' ' + pass_guidance if pass_guidance else ''}"
        ),
    )

DEFAULT_SEMANTIC_STATE = {
    "canon_state": "played_canon",
    "lifecycle_state": "candidate",
    "evidence_role": "source_evidence",
    "authority_state": "system_derived",
    "visibility_state": "gm_private",
}

_SOURCE_ORDER_OCCURRENCES = (
    "Retain specific occurred events needed to express source-supported before/after "
    "relationships as event nodes. These can be actual discoveries, discussions, "
    "decisions or planning acts; a proposed future outcome is a different occurrence. "
    "Bind each description to its source-supported episode, journey or situation so "
    "relative references remain understandable without paragraph or node order. "
    "Do not turn persistent people, places or topics into events. Keep concurrent "
    "or unresolved occurrences distinct without imposing an order."
)

_SOURCE_ORDER_EDGES = (
    "Retain explicit source-supported occurrence order using the adopted precedence "
    "predicate and event endpoints. Review linked events systematically, preserving "
    "attribution and uncertainty; do not derive order from paragraph position, infer "
    "causation or complete a total timeline. If two events precede a third, their "
    "relative order may remain unresolved. Supply evidence for each ordering claim "
    "itself; endpoint evidence cannot substitute."
)


_NODE_PASSES: tuple[ExtractionPassSpec, ...] = (
    ExtractionPassSpec(
        pass_id="actor_pass",
        allowed_node_types=("character", "creature"),
        default_node_type="character",
        instruction=(
            "Extract source-mentioned characters and creatures as source-local candidates. "
            "Do not infer player-character role, canonical identity or party membership; "
            "no external actors or party anchors are supplied."
        ),
        progress_label="Extracting actors and NPCs",
    ),
    ExtractionPassSpec(
        pass_id="location_pass",
        allowed_node_types=("location",),
        default_node_type="location",
        instruction=(
            "Extract regions, towns, cities, roads, routes, sublocations, and named travel zones only."
        ),
        progress_label="Extracting locations",
    ),
    ExtractionPassSpec(
        pass_id="collective_pass",
        allowed_node_types=("faction", "organization", "group"),
        default_node_type="group",
        instruction=(
            "Extract factions, councils, guards, mercenary groups, organizations, and parties (as collectives) only. "
            "Use node_type faction, organization, or group as appropriate."
        ),
        progress_label="Extracting factions and collectives",
    ),
    ExtractionPassSpec(
        pass_id="object_pass",
        allowed_node_types=("item",),
        default_node_type="item",
        instruction=(
            "Extract notable items, devices, and artifacts supported as in-world "
            "physical objects. A noun mentioned in the text is not sufficient. "
            "Fees, prices, promises, "
            "knowledge, and learned abilities are not items. People, creatures, and "
            "places belong to their own passes; do not emit a building again as an "
            "item merely because it is physical. A table handout, illustrative aid, "
            "metaphor, or rhetorical question alone does not establish a world object. "
            "When that world-object status is unsupported or ambiguous, omit the "
            "reference from observation_nodes rather than inventing an item to retain "
            "the phrase. Retain clearly non-world references in ignored_items when "
            "worth recording; use deferred_items when world-object status needs "
            "clarification, explaining the uncertainty and needed evidence. Do not "
            "also assert that same unresolved referent as an item. These dispositions "
            "record source observations, not world-object existence. "
            "Keep explicitly narrated world objects, including those "
            "mentioned parenthetically. A physical carrier of information or magic "
            "remains eligible; do not discard the carrier because its contents are "
            "knowledge or a spell. Preserve stated quantities, ownership, and "
            "condition; keep proposed exchanges distinct from completed transfers."
        ),
        progress_label="Extracting notable objects",
        include_dispositions=True,
    ),
    ExtractionPassSpec(
        pass_id="thread_pass",
        allowed_node_types=(
            "event", "clue", "thread", "mystery", "warning", "promise",
            "debt", "rumor", "unknown_important",
        ),
        default_node_type="mystery",
        instruction=(
            "Extract mysteries, clues, warnings, events, unresolved phenomena, and threads. "
            "Also emit ignored_items and deferred_items when appropriate. "
            + _SOURCE_ORDER_OCCURRENCES
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
    instruction="Extract durable relationship edges among consolidated nodes. " + _SOURCE_ORDER_EDGES,
    progress_label="Extracting relationship edges",
    kind="edge",
    predicate_capabilities=(RECAP_SOURCE_ORDER,),
)


def _build_recap_profile(
    *,
    profile_id: str,
    profile_version: str,
    enable_encounter_job_pass: bool,
    enable_encounter_job_edge_guidance: bool,
    enable_dynamic_node_vocabulary_packet: bool,
) -> ExtractionProfile:
    return ExtractionProfile(
        profile_id=profile_id,
        profile_version=profile_version,
        admitted_source_domains=frozenset({"recap"}),
        admitted_document_classes=None,
        node_passes=tuple(_with_recap_source_faithfulness(spec) for spec in _NODE_PASSES),
        beat_pass=_with_recap_source_faithfulness(_BEAT_PASS),
        encounter_job_pass=(
            _with_recap_source_faithfulness(_ENCOUNTER_JOB_PASS)
            if enable_encounter_job_pass
            else None
        ),
        edge_pass=_with_recap_source_faithfulness(_EDGE_PASS),
        evidence_rule=EVIDENCE_RULE,
        default_semantic_state=DEFAULT_SEMANTIC_STATE,
        enable_encounter_job_pass=enable_encounter_job_pass,
        enable_encounter_job_edge_guidance=enable_encounter_job_edge_guidance,
        enable_dynamic_node_vocabulary_packet=enable_dynamic_node_vocabulary_packet,
        # Source-local names are candidates, not authority to merge identities.
        enable_automatic_identity_consolidation=False,
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
        enable_encounter_job_edge_guidance=False,
        enable_dynamic_node_vocabulary_packet=False,
    )
)

# Legacy graph_extraction_profile names map onto explicit recap profile variants.
LEGACY_RECAP_PROFILE_ALIASES: dict[str, tuple[str, str]] = {
    "current_default": (RECAP_PROFILE_ID, RECAP_PROFILE_VERSION),
    "category_baseline": (RECAP_PROFILE_ID, RECAP_PROFILE_VERSION),
    "category_encounter_job_preview": ("recap_category_encounter_job_preview", "2.0"),
}

register_extraction_profile(
    _build_recap_profile(
        profile_id="recap_category_encounter_job_preview",
        profile_version="2.0",
        enable_encounter_job_pass=True,
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
