"""Gazetteer definitions without inventing played episodes or individuals."""
from dataclasses import replace
from .extraction_profile import ExtractionPassSpec, register_extraction_profile
from .worldbuilding_extraction_profile import WORLDBUILDING_PROFILE
from .worldbuilding_source_sections import retain_owned_sections

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
