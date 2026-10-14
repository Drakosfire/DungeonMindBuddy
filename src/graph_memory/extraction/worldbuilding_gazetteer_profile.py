"""Gazetteer definitions without inventing played episodes or individuals."""
from dataclasses import replace
from .extraction_profile import ExtractionPassSpec, register_extraction_profile
from .worldbuilding_extraction_profile import WORLDBUILDING_PROFILE

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
