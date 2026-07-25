"""Bounded Shepherd's Flock worldbuilding extraction profile.

Owns pass order, instructions, schema refs, vocabulary policy, and category
bounds for evergreen lore — not recap chronology or incidental ecology.

Compatibility: the durable profile_id is Shepherd's-Flock-scoped
(`worldbuilding_shepherds_flock_v0`) and is the admitted contract for that
pilot cohort. Document-class admission is intentionally broader
(`lore` / `gazetteer` / `faction` / `place` / `institution`) so the same
bounded passes can be exercised on similar evergreen prose without implying a
universal worldbuilding quality claim or a second reusable profile ID.
"""

from __future__ import annotations

from typing import Any, Mapping

from src.graph_memory.extraction.extraction_profile import (
    ExtractionPassSpec,
    ExtractionProfile,
    register_extraction_profile,
)
from src.graph_memory.extraction.recap_extraction_profile import EVIDENCE_RULE

WORLDBUILDING_PROFILE_ID = "worldbuilding_shepherds_flock_v0"
WORLDBUILDING_PROFILE_VERSION = "0.1"

# Only types present in production CandidateGraphPreview.NODE_TYPES.
# Institutions/governance are represented as faction | organization | group —
# graduating a distinct `institution` node type requires a durable vocabulary
# predecessor and is out of this profile's scope.
INCLUDED_NODE_TYPES: frozenset[str] = frozenset(
    {
        "character",
        "creature",
        "location",
        "faction",
        "organization",
        "group",
    }
)

EXCLUDED_NODE_TYPES: frozenset[str] = frozenset(
    {
        "item",
        "mystery",
        "beat",
        "event",
        "clue",
        "ecology",
        "resource",
        "flora",
        "fauna_incidental",
        "product",
        "material",
        "scenery",
    }
)

EXCLUDED_CATEGORY_BEHAVIOR = {
    "incidental_species": "omit",
    "food_flora_products": "omit",
    "unnamed_inhabitants": "omit",
    "speculative_cosmology": "omit",
    "session_beats": "omit",
    "automatic_identity_merges": "forbid",
}

DEFAULT_SEMANTIC_STATE = {
    "canon_state": "worldbuilding_draft",
    "lifecycle_state": "candidate",
    "evidence_role": "source_evidence",
    "authority_state": "system_derived",
    "visibility_state": "gm_private",
}

_ACTOR_TYPES = ("character", "creature")
_LOCATION_TYPES = ("location",)
_COLLECTIVE_TYPES = ("faction", "organization", "group")

_NODE_PASSES: tuple[ExtractionPassSpec, ...] = (
    ExtractionPassSpec(
        pass_id="actor_pass",
        default_node_type="character",
        instruction=(
            "Extract named NPCs and named creatures only. "
            "Do not invent mechanical statblock fields absent from the source. "
            "Omit unnamed generic inhabitants and disposable encounter fodder."
        ),
        progress_label="Extracting named actors and creatures",
        allowed_node_types=_ACTOR_TYPES,
    ),
    ExtractionPassSpec(
        pass_id="location_pass",
        default_node_type="location",
        instruction=(
            "Extract named locations and meaningful sublocations only. "
            "Omit pure scenery without durable identity."
        ),
        progress_label="Extracting locations",
        allowed_node_types=_LOCATION_TYPES,
    ),
    ExtractionPassSpec(
        pass_id="collective_pass",
        default_node_type="faction",
        instruction=(
            "Extract factions, organizations, collectives, governance, "
            "command structures, and doctrine only when explicitly stated. "
            "Use node_type faction, organization, or group. "
            "Do not invent an institution node type."
        ),
        progress_label="Extracting factions and organizations",
        allowed_node_types=_COLLECTIVE_TYPES,
    ),
)

_EDGE_PASS = ExtractionPassSpec(
    pass_id="edge_pass",
    default_node_type=None,
    instruction=(
        "Extract durable, source-backed relationships among consolidated nodes only. "
        "Require exact endpoints and evidence. Do not invent label-first edges or "
        "automatic identity merges. Leave unresolved identity as unresolved."
    ),
    progress_label="Extracting durable relationships",
    kind="edge",
)


def validate_worldbuilding_candidate_bounds(
    candidate_graph: Mapping[str, Any],
) -> list[str]:
    """Return validation errors for category, evidence, and null-session bounds."""
    errors: list[str] = []
    session_id = candidate_graph.get("session_id")
    if session_id not in (None, ""):
        errors.append("worldbuilding candidate must keep session_id null")

    for node in candidate_graph.get("nodes") or []:
        if not isinstance(node, Mapping):
            errors.append("node must be an object")
            continue
        node_id = str(node.get("node_id") or "<missing>")
        node_type = str(node.get("node_type") or "").strip()
        if node_type in EXCLUDED_NODE_TYPES:
            errors.append(
                f"node {node_id} uses excluded type {node_type!r}"
            )
        elif node_type not in INCLUDED_NODE_TYPES:
            errors.append(
                f"node {node_id} uses undeclared type {node_type!r}"
            )
        refs = node.get("evidence_refs") or []
        if not refs:
            errors.append(f"node {node_id} is missing evidence_refs")

    for edge in candidate_graph.get("edges") or []:
        if not isinstance(edge, Mapping):
            errors.append("edge must be an object")
            continue
        edge_id = str(edge.get("edge_id") or "<missing>")
        if not edge.get("from_node_id") or not edge.get("to_node_id"):
            errors.append(f"edge {edge_id} requires exact endpoints")
        if not (edge.get("evidence_refs") or []):
            errors.append(f"edge {edge_id} is missing evidence_refs")

    for beat in candidate_graph.get("beats") or []:
        errors.append("session beats are forbidden for evergreen worldbuilding")
        break

    return errors


WORLDBUILDING_PROFILE = register_extraction_profile(
    ExtractionProfile(
        profile_id=WORLDBUILDING_PROFILE_ID,
        profile_version=WORLDBUILDING_PROFILE_VERSION,
        admitted_source_domains=frozenset({"worldbuilding"}),
        admitted_document_classes=frozenset(
            {"lore", "gazetteer", "faction", "place", "institution"}
        ),
        node_passes=_NODE_PASSES,
        beat_pass=None,
        encounter_job_pass=None,
        edge_pass=_EDGE_PASS,
        evidence_rule=EVIDENCE_RULE,
        default_semantic_state=DEFAULT_SEMANTIC_STATE,
        enable_encounter_job_pass=False,
        enable_party_participation_attachment=False,
        enable_encounter_job_edge_guidance=False,
        enable_dynamic_node_vocabulary_packet=False,
        allow_null_session=True,
        schema_ids={
            "envelope": "dmb_live_extractor_candidate_envelope_v0",
            "candidate_graph": "dmb_candidate_graph_preview_v0",
            "node_pass": "dmb_category_node_pass_v1",
            "edge_pass": "dmb_category_edge_pass_v1",
        },
        vocabulary_policy={
            "mode": "bounded_worldbuilding",
            "included_node_types": sorted(INCLUDED_NODE_TYPES),
            "excluded_node_types": sorted(EXCLUDED_NODE_TYPES),
        },
        post_extraction_validation_policy={
            "require_evidence_refs": True,
            "require_null_session": True,
            "included_node_types": sorted(INCLUDED_NODE_TYPES),
            "excluded_node_types": sorted(EXCLUDED_NODE_TYPES),
            "excluded_category_behavior": EXCLUDED_CATEGORY_BEHAVIOR,
            "forbid_session_beats": True,
            "auto_promotion": False,
        },
        post_extraction_validator=validate_worldbuilding_candidate_bounds,
    )
)
