"""Gazetteer definitions without inventing played episodes or individuals."""
from copy import deepcopy
from dataclasses import asdict, replace
import re
from typing import Any
from .extraction_profile import ExtractionPassSpec, register_extraction_profile
from .worldbuilding_extraction_profile import WORLDBUILDING_PROFILE
from .worldbuilding_source_sections import owned_livestock_sections, retain_owned_sections
from .worldbuilding_role_support import compile_role_support
from .worldbuilding_edge_review import ConstrainedEdgeReviewPassSpec

GAZETTEER_PROFILE_ID = "worldbuilding_gazetteer_v1"
GAZETTEER_PROFILE_VERSION = "1.0"

def validate_gazetteer_candidate_bounds(graph):
    allowed = {"character", "creature", "location", "faction", "organization", "group", "event"}
    errors = []
    if graph.get("session_id") not in (None, ""):
        errors.append("gazetteer candidate must keep session_id null")
    for node in graph.get("nodes", []):
        if node.get("node_type") not in allowed:
            errors.append("gazetteer node type is outside declared bounds")
        if not node.get("evidence_refs"):
            errors.append("gazetteer node requires evidence")
    for edge in graph.get("edges", []):
        if not edge.get("from_node_id") or not edge.get("to_node_id") or not edge.get("evidence_refs"):
            errors.append("gazetteer edge requires endpoints and evidence")
    if graph.get("beats"):
        errors.append("session beats are forbidden for gazetteer extraction")
    return errors

GAZETTEER_PROFILE = register_extraction_profile(replace(
    WORLDBUILDING_PROFILE,
    profile_id=GAZETTEER_PROFILE_ID, profile_version=GAZETTEER_PROFILE_VERSION,
    node_passes=tuple(replace(p, instruction=p.instruction + (" Exclude species/kind definitions: location_pass preserves them as place descriptions; retain explicitly named individual creatures only." if p.pass_id == "actor_pass" else " Preserve explicitly associated livestock/ecology definitions, transport uses, cultural products, qualified cosmology and history in place descriptions with exact source evidence; do not invent a species object." if p.pass_id == "location_pass" else "") +
        " Preserve qualified source descriptions, beliefs and allegations; never turn proposed hooks into played facts.")
        for p in WORLDBUILDING_PROFILE.node_passes) + (
        ExtractionPassSpec(pass_id="definition_pass", default_node_type="event",
            instruction="Do not mint species/taxonomy creature identities. Preserve source-backed livestock definitions and uses/products in the explicitly associated place descriptions through location_pass, not invented items or statblocks. Extract recurring named festivals as event definitions, never a played episode or invented date. Preserve origin/history and belief attribution; defer unplayed plot hooks.",
            progress_label="Extracting named setting definitions", allowed_node_types=("event",)),),
    vocabulary_policy={
        "mode": "bounded_gazetteer",
        "included_node_types": ["character", "creature", "location", "faction", "organization", "group", "event"],
        "excluded_node_types": ["item", "beat", "clue", "mystery"],
    },
    post_extraction_validation_policy={
        "require_evidence_refs": True, "require_null_session": True,
        "forbid_session_beats": True, "auto_promotion": False,
        "definition_semantics": "species knowledge on associated places; recurring festivals; no played episodes",
    },
    post_extraction_validator=validate_gazetteer_candidate_bounds,
))


GAZETTEER_SOURCE_RETENTION_PROFILE = register_extraction_profile(replace(
    GAZETTEER_PROFILE, profile_version="1.1", source_section_retainer=retain_owned_sections,
))


_ACTOR_SOURCE_FIDELITY = (
    " A capitalized species, breed heading, product or plural kind is not an individual. "
    "Extract only explicitly individuated people or creatures; capitalization alone is not "
    "individuality evidence. Preserve uncertainty for merely referenced actors."
)
_PLACE_SOURCE_FIDELITY = (
    " Use source-extractive descriptions for the exact named referent, retaining its source "
    "heading or exact naming clause and separately citing owner/section context. Do not add "
    "bridging ownership, membership, subtype, institutional or geographic claims. Enumerate "
    "explicitly named places and establishments, including ones named through an owner or "
    "proprietor, without upgrading proprietor to legal ownership. Retain named features and "
    "customs in parent prose when independent identity/type is not established. Preserve all "
    "relevant source clauses across paragraphs; every quoted clause needs its actual source "
    "span, not one nearby citation for the whole description. Do not omit named customs or "
    "qualifiers merely to shorten prose. A city being by a lake or at the base of peaks remains "
    "a city geography statement; preserve the city subject and its naming context rather than "
    "turning it into landform containment or a landform's own trade role. Political collectives "
    "and unresolved cosmological referents are not Locations merely because they are named. "
    "Role phrases alone do not prove a separate place identity. Authored approach/arrival "
    "scenery remains prepared-scenario prose with its original heading and qualifications, "
    "not enduring place facts or played events. Preserve source beliefs, hedges and examples. "
    "Explicitly scoped livestock sections are retained separately by the profile's deterministic "
    "source step; retain their named owner place, not independent species instances."
)

GAZETTEER_SOURCE_FIDELITY_PROFILE = register_extraction_profile(replace(
    GAZETTEER_SOURCE_RETENTION_PROFILE,
    profile_version="1.2",
    node_passes=tuple(replace(
        spec, instruction=spec.instruction + (
            _ACTOR_SOURCE_FIDELITY if spec.pass_id == "actor_pass" else
            _PLACE_SOURCE_FIDELITY if spec.pass_id == "location_pass" else ""
        ),
    ) for spec in GAZETTEER_SOURCE_RETENTION_PROFILE.node_passes),
))


GAZETTEER_ROLE_SUPPORT_PROFILE = register_extraction_profile(replace(
    GAZETTEER_SOURCE_FIDELITY_PROFILE, profile_version="1.3",
    source_section_retainer=compile_role_support,
))


GAZETTEER_ADVISORY_REVIEW_PROFILE = register_extraction_profile(replace(
    GAZETTEER_ROLE_SUPPORT_PROFILE, profile_version="1.4",
    edge_review_pass=ExtractionPassSpec(
        pass_id="edge_review_pass", default_node_type=None, kind="edge_review",
        progress_label="Reviewing proposed relationships",
        instruction=(
            "Select only source-supported edge proposals using the complete source packet. "
            "Endpoint descriptions, types and labels are navigation, not accepted truth. "
            "Check exact referents, relation meaning/direction, qualifications and source "
            "authoring context. A proprietor is not necessarily an owner; settlers fleeing "
            "a polity do not establish that polity as a causal actor. Do not rewrite, add "
            "or repair proposals. Return only retained_edge_ids. Omissions remain deferred "
            "for review, not proven false. Your selection is advisory, not fact acceptance."
        ),
    ),
))


# The bound catalog is request-local; frozen1.4 keeps its original schema/prompt.

GAZETTEER_CONSTRAINED_REVIEW_PROFILE = register_extraction_profile(replace(
    GAZETTEER_ADVISORY_REVIEW_PROFILE, profile_version="1.5",
    edge_review_pass=ConstrainedEdgeReviewPassSpec(
        **asdict(GAZETTEER_ADVISORY_REVIEW_PROFILE.edge_review_pass),
    ),
))


def _livestock_species_for_event_label(label: Any, species_labels: list[str]) -> str | None:
    cleaned = re.sub(r"\s+", " ", str(label or "")).strip()
    match = re.fullmatch(r"(.+?)\s+Livestock Definition", cleaned, flags=re.I)
    if match:
        cleaned = match.group(1).strip()
    else:
        match = re.fullmatch(r"Cultural Significance of (.+)", cleaned, flags=re.I)
        if match:
            cleaned = match.group(1).strip()
    normalized = {re.sub(r"\s+", " ", name).strip().casefold(): name
                  for name in species_labels}
    return normalized.get(cleaned.casefold())


def compile_gazetteer_livestock_hygiene(graph, rows):
    """Retain owned livestock prose and defer its duplicate event proposals."""
    result, diagnostics = compile_role_support(graph, rows)
    sections = owned_livestock_sections(rows)
    deferred_ids = {item.get("item_id") for item in result.get("deferred_items", [])}
    deferred_proposals: dict[str, dict[str, Any]] = {}
    removed_node_ids = set()
    deferred_nodes = []

    for node in result.get("nodes", []):
        if node.get("node_type") != "event":
            continue
        evidence_span_ids = {
            ref.get("source_span_ref_id") for ref in node.get("evidence_refs", [])
            if isinstance(ref, dict)
        }
        if not evidence_span_ids or None in evidence_span_ids:
            continue
        matches = []
        for section in sections:
            species = _livestock_species_for_event_label(
                node.get("label"), section["species_labels"],
            )
            if species and evidence_span_ids.issubset(set(section["source_span_ref_ids"])):
                matches.append((section, species))
        if len(matches) != 1:
            continue
        section, species = matches[0]
        item_id = "deferred:livestock-section:node:" + str(node["node_id"])
        if item_id in deferred_ids:
            raise ValueError("livestock hygiene disposition identity collision")
        refs = [ref for ref in node.get("evidence_refs", []) if isinstance(ref, dict)]
        result.setdefault("deferred_items", []).append({
            "item_id": item_id,
            "label": node.get("label") or "",
            "reason": "livestock_definition_retained_on_owner_place",
            "evidence_refs": refs,
            "warnings": ["source_support_policy:worldbuilding_gazetteer_v1@1.6"],
            "suggested_next_step": (
                f"Review the source-backed {species} section on "
                f"{section['owner_label']}; do not treat it as a played event."
            ),
        })
        deferred_proposals[item_id] = {
            "item_id": item_id,
            "kind": "node",
            "proposal": deepcopy(node),
        }
        deferred_ids.add(item_id)
        removed_node_ids.add(node["node_id"])
        deferred_nodes.append(node["node_id"])

    if removed_node_ids:
        kept_nodes = [node for node in result.get("nodes", [])
                      if node.get("node_id") not in removed_node_ids]
        kept_edges = []
        deferred_edges = []
        for edge in result.get("edges", []):
            if (edge.get("from_node_id") not in removed_node_ids
                    and edge.get("to_node_id") not in removed_node_ids):
                kept_edges.append(edge)
                continue
            item_id = "deferred:livestock-section:edge:" + str(edge["edge_id"])
            if item_id in deferred_ids:
                raise ValueError("livestock hygiene disposition identity collision")
            result.setdefault("deferred_items", []).append({
                "item_id": item_id,
                "label": edge.get("label") or "",
                "reason": "livestock_endpoint_deferred_with_source_definition",
                "evidence_refs": [ref for ref in edge.get("evidence_refs", [])
                                  if isinstance(ref, dict)],
                "warnings": ["source_support_policy:worldbuilding_gazetteer_v1@1.6"],
                "suggested_next_step": (
                    "Review this proposed relationship after choosing a non-event "
                    "representation for the retained source definition."
                ),
            })
            deferred_proposals[item_id] = {
                "item_id": item_id,
                "kind": "edge",
                "proposal": deepcopy(edge),
            }
            deferred_ids.add(item_id)
            deferred_edges.append(edge["edge_id"])
        result["nodes"] = kept_nodes
        result["edges"] = kept_edges
    else:
        deferred_edges = []

    diagnostics["livestock_semantic_hygiene"] = {
        "profile": "worldbuilding_gazetteer_v1@1.6",
        "deferred_node_ids": deferred_nodes,
        "deferred_edge_ids": deferred_edges,
        "owner_sections": len(sections),
        "deferred_proposals": {
            item_id: deferred_proposals[item_id]
            for item_id in sorted(deferred_proposals)
        },
    }
    return result, diagnostics


GAZETTEER_LIVESTOCK_HYGIENE_PROFILE = register_extraction_profile(replace(
    GAZETTEER_CONSTRAINED_REVIEW_PROFILE,
    profile_version="1.6",
    node_passes=tuple(replace(
        spec,
        instruction=spec.instruction + (
            " A named livestock species, breed, product, or cultural description in an "
            "explicitly owned Fantastic Livestock section is not an event. Return no "
            "event node for it; the profile retains those exact source sections on their "
            "owner place. Continue to extract explicitly named recurring festivals as "
            "event definitions, never as played episodes."
        ) if spec.pass_id == "definition_pass" else spec.instruction,
    ) for spec in GAZETTEER_CONSTRAINED_REVIEW_PROFILE.node_passes),
    source_section_retainer=compile_gazetteer_livestock_hygiene,
))
