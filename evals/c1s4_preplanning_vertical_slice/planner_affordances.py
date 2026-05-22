from __future__ import annotations

import re
from typing import Any

DERIVATION_METHOD = "support_affordance_rules_v1"

PLANNER_AFFORDANCE_VOCAB = frozenset(
    {
        "approach_description",
        "boxed_text",
        "visible_landmark",
        "first_impression",
        "sensory_description",
        "travel_context",
        "npc_intro",
        "social_tension",
        "faction_pressure",
        "merchant_role",
        "healer_role",
        "authority_figure",
        "family_pressure",
        "optional_npc",
        "encounter_design",
        "battlefield_terrain",
        "environmental_hazard",
        "civilian_pressure",
        "objective_design",
        "investigation_clue",
        "monster_mechanics",
        "escalation_trigger",
        "campaign_continuity",
        "route_uncertainty",
        "location_gap",
        "canon_gap",
        "support_only",
    }
)


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _find_match(text: str, terms: list[str]) -> str | None:
    hay = _norm(text)
    for term in terms:
        needle = _norm(term)
        if needle and needle in hay:
            return term
    return None


def _field_text(card: dict[str, Any], field: str) -> str:
    value = card.get(field)
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value or "")


SUPPORT_AFFORDANCE_RULES: list[dict[str, Any]] = [
    {"affordance": "visible_landmark", "fields": ("title", "summary", "retrieval_terms"), "any": ["visible", "seen", "distance", "huge", "towering", "village-scale", "obvious"]},
    {"affordance": "approach_description", "fields": ("title", "summary", "retrieval_terms"), "any": ["approach", "road", "first sight", "village-scale", "visible threat"]},
    {"affordance": "first_impression", "fields": ("title", "summary", "retrieval_terms"), "any": ["visible", "obvious", "first", "gossip", "rumor", "weird-color"]},
    {"affordance": "sensory_description", "fields": ("title", "summary", "retrieval_terms"), "any": ["visible", "sickly", "thorned", "shiny", "metallic", "glowing", "dank air", "warm roots"]},
    {"affordance": "npc_intro", "fields": ("title", "summary", "retrieval_terms"), "any": ["npc", "merchant", "healer", "store", "family", "villager", "optional", "boy", "father", "priest", "mage", "trader"]},
    {"affordance": "social_tension", "fields": ("title", "summary", "retrieval_terms"), "any": ["pressure", "tension", "angry", "frightened", "reckless", "panic", "mob", "worried", "grieving"]},
    {"affordance": "merchant_role", "fields": ("title", "summary", "retrieval_terms"), "any": ["merchant", "store", "trader", "trade goods", "supplies", "magical wagon"]},
    {"affordance": "healer_role", "fields": ("title", "summary", "retrieval_terms"), "any": ["healer", "priest", "wounded", "injuries", "mercy", "faith"]},
    {"affordance": "family_pressure", "fields": ("title", "summary", "retrieval_terms"), "any": ["family", "father", "boy", "home", "survival", "winter"]},
    {"affordance": "optional_npc", "fields": ("title", "summary", "retrieval_terms"), "any": ["optional", "can be used", "recurring traveler", "optional weird-color npc"]},
    {"affordance": "encounter_design", "fields": ("title", "summary", "retrieval_terms"), "any": ["encounter", "attack creatures", "danger radius", "retaliation", "villagers become fed up", "tree mauls"]},
    {"affordance": "battlefield_terrain", "fields": ("title", "summary", "retrieval_terms"), "any": ["terrain", "radius", "roots", "tree", "reach", "branches", "garden", "site"]},
    {"affordance": "civilian_pressure", "fields": ("title", "summary", "retrieval_terms"), "any": ["villagers", "civilians", "townsfolk", "reckless action", "mob", "children", "father"]},
    {"affordance": "objective_design", "fields": ("title", "summary", "retrieval_terms"), "any": ["objective", "protect", "rescue", "stop", "avoid", "evacuate", "healing problem", "injuries"]},
    {"affordance": "environmental_hazard", "fields": ("title", "summary", "retrieval_terms"), "any": ["hazard", "danger", "attack creatures", "fire", "thorn", "root network", "danger radius", "mauls"]},
    {"affordance": "investigation_clue", "fields": ("title", "summary", "retrieval_terms"), "any": ["clue", "investigated", "arcana", "perception", "aura", "metallic leaves", "root-network"]},
    {"affordance": "monster_mechanics", "fields": ("title", "summary", "retrieval_terms"), "any": ["mechanics", "reach", "danger radius", "fire vulnerability", "retaliation", "attack creatures"]},
    {"affordance": "escalation_trigger", "fields": ("title", "summary", "retrieval_terms"), "any": ["escalation", "fed up", "drink", "axes", "attack the tree", "retaliation", "second wave"]},
    {"affordance": "travel_context", "fields": ("title", "summary", "retrieval_terms"), "any": ["road", "route", "travel", "toward", "westward"]},
    {"affordance": "support_only", "fields": ("title", "summary", "retrieval_terms"), "any": ["source module", "planning support", "adaptation", "optional source material"]},
]


QUERY_AFFORDANCE_RULES: list[dict[str, Any]] = [
    {"affordance": "approach_description", "any": ["approaches", "approach", "first see", "see first", "from a distance"]},
    {"affordance": "boxed_text", "any": ["boxed text", "boxed-text", "read aloud", "improvised version"]},
    {"affordance": "visible_landmark", "any": ["from a distance", "seen from", "visible", "first see", "see first"]},
    {"affordance": "first_impression", "any": ["first", "first see", "see first", "first three", "first npcs"]},
    {"affordance": "npc_intro", "any": ["first three npcs", "first npcs", "players should meet", "who should they meet", "npcs the players should meet"]},
    {"affordance": "social_tension", "any": ["tension", "pressure", "represent"]},
    {"affordance": "encounter_design", "any": ["design", "encounter", "battlefield", "not just a monster"]},
    {"affordance": "battlefield_terrain", "any": ["battlefield", "terrain", "battlefield terrain"]},
    {"affordance": "civilian_pressure", "any": ["civilians", "villagers", "bystanders"]},
    {"affordance": "environmental_hazard", "any": ["hazards", "hazard", "danger"]},
    {"affordance": "objective_design", "any": ["objectives", "goals", "protect", "rescue"]},
]


def derive_planner_affordances_for_support_card(
    card: dict[str, Any],
    *,
    include_retrieval_terms: bool = True,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rule in SUPPORT_AFFORDANCE_RULES:
        affordance = str(rule["affordance"])
        if affordance not in PLANNER_AFFORDANCE_VOCAB or affordance in seen:
            continue
        fields = tuple(rule.get("fields") or ("title", "summary"))
        if not include_retrieval_terms:
            fields = tuple(f for f in fields if f != "retrieval_terms")
        for field in fields:
            text = _field_text(card, field)
            match = _find_match(text, list(rule.get("any") or []))
            if match:
                out.append(
                    {
                        "affordance": affordance,
                        "basis_field": field,
                        "basis_match": match,
                        "derivation_method": DERIVATION_METHOD,
                        "confidence": "deterministic",
                        "source_visible": True,
                    }
                )
                seen.add(affordance)
                break
    return out


def derive_query_planner_affordances(question: str) -> list[str]:
    text = _norm(question)
    out: list[str] = []
    seen: set[str] = set()
    for rule in QUERY_AFFORDANCE_RULES:
        affordance = str(rule["affordance"])
        if affordance in seen:
            continue
        if _find_match(text, list(rule.get("any") or [])):
            out.append(affordance)
            seen.add(affordance)
    return out


def affordance_query_text(affordances: list[str]) -> str:
    terms = [a.replace("_", " ") for a in affordances if a in PLANNER_AFFORDANCE_VOCAB]
    return " ".join(terms)
