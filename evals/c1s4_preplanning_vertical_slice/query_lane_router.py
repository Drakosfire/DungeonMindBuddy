from __future__ import annotations

import re
from typing import Any

LANE_PROFILES_V1: dict[str, dict[str, Any]] = {
    "prior_npc_context": {"known_gaps": {"floor_chars": 300, "target_chars": 600, "max_chars": 1000, "priority": 0}, "prior_campaign_memory": {"floor_chars": 4500, "target_chars": 6500, "max_chars": 7500, "priority": 1}, "support_knowledge": {"floor_chars": 0, "target_chars": 0, "max_chars": 500, "priority": 9}},
    "route_or_distance_gap": {"known_gaps": {"floor_chars": 1000, "target_chars": 1800, "max_chars": 2500, "priority": 0}, "prior_campaign_memory": {"floor_chars": 1500, "target_chars": 3000, "max_chars": 4500, "priority": 2}, "support_knowledge": {"floor_chars": 0, "target_chars": 0, "max_chars": 500, "priority": 3}},
    "support_description": {"known_gaps": {"floor_chars": 500, "target_chars": 1000, "max_chars": 1500, "priority": 0}, "support_knowledge": {"floor_chars": 2500, "target_chars": 3500, "max_chars": 4500, "priority": 1}, "prior_campaign_memory": {"floor_chars": 1000, "target_chars": 2500, "max_chars": 3500, "priority": 2}},
    "default_mixed": {"known_gaps": {"floor_chars": 500, "target_chars": 1000, "max_chars": 1500, "priority": 0}, "prior_campaign_memory": {"floor_chars": 3000, "target_chars": 5000, "max_chars": 6500, "priority": 1}, "support_knowledge": {"floor_chars": 0, "target_chars": 1500, "max_chars": 2500, "priority": 2}},
}

TERM_RULES = {
    "route_terms": ["how far", "distance", "route", "travel", "road", "between", "where is", "how long"],
    "support_terms": ["hempholm", "tree", "magical", "metallic", "merchant", "visible", "support"],
    "prior_terms": ["who are", "npc", "encountered", "stone bridge", "pippa", "bubbles", "grishna", "river's edge"],
    "gap_terms": ["do we know", "is it established", "exact", "canon", "how far", "route"],
}

def _has_any(text: str, terms: list[str]) -> bool:
    return any(t in text for t in terms)

def extract_query_features(question_text: str) -> dict[str, Any]:
    t = re.sub(r"\s+", " ", question_text.lower())
    asks_route = _has_any(t, TERM_RULES["route_terms"])
    asks_support = _has_any(t, TERM_RULES["support_terms"])
    has_support_entities = any(x in t for x in ["hempholm", "tree", "magical", "metallic", "merchant"])
    asks_prior = _has_any(t, TERM_RULES["prior_terms"])
    asks_gap = _has_any(t, TERM_RULES["gap_terms"])
    return {
        "schema": "dmb_query_features_v1",
        "detected_terms": {
            "route_terms": [x for x in TERM_RULES["route_terms"] if x in t],
            "support_terms": [x for x in TERM_RULES["support_terms"] if x in t],
            "prior_terms": [x for x in TERM_RULES["prior_terms"] if x in t],
            "gap_terms": [x for x in TERM_RULES["gap_terms"] if x in t],
        },
        "intent_signals": {
            "asks_prior_npc_context": asks_prior,
            "asks_route_or_distance": asks_route,
            "asks_generation_or_description": "describe" in t or "description" in t,
            "asks_support_or_world_context": asks_support,
            "has_support_specific_entities": has_support_entities,
            "asks_known_gap_sensitive_question": asks_gap,
        },
    }

def build_lane_plan(*, question_text: str, retrieval_mode: str, candidate_depth: int = 50, total_budget_chars: int = 8000) -> dict[str, Any]:
    qf = extract_query_features(question_text)
    sig = qf["intent_signals"]
    profile = "default_mixed"
    if sig["asks_support_or_world_context"] and retrieval_mode != "prior_only" and sig.get("has_support_specific_entities"):
        profile = "support_description"
    elif sig["asks_route_or_distance"] or sig["asks_known_gap_sensitive_question"]:
        profile = "route_or_distance_gap"
    elif sig["asks_prior_npc_context"]:
        profile = "prior_npc_context"
    lanes = {k: dict(v) for k, v in LANE_PROFILES_V1[profile].items()}
    if retrieval_mode == "prior_only":
        lanes["support_knowledge"] = {"floor_chars": 0, "target_chars": 0, "max_chars": 0, "priority": 9}
    return {"schema": "dmb_lane_plan_v1", "profile": profile, "candidate_depth": candidate_depth, "total_budget_chars": total_budget_chars, "lanes": lanes, "query_features": qf}
