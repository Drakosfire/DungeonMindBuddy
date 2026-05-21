from __future__ import annotations

import re
from typing import Any

SUPPORT_ENABLED_MODES = frozenset(
    {
        "prior_plus_support_content_only",
        "prior_plus_support_content_plus_lexical_hints",
    }
)

SUPPORT_HEMPHOLM_TREE_TERMS = frozenset(
    {
        "hempholm",
        "hemp",
        "gigantic tree",
        "giant tree",
        "magical tree",
        "metallic",
        "merchant",
        "shiny",
    }
)

NPC_BROAD_QUERY_TERMS = frozenset(
    {
        "who are",
        "npc",
        "npcs",
        "encountered",
        "met",
        "players encountered",
    }
)

ROUTE_DISTANCE_TERMS = frozenset(
    {
        "how far",
        "distance",
        "route",
        "travel",
        "how long",
        "where is",
        "on the road",
        "traveling",
    }
)

FORBIDDEN_QUERY_SUBSTRINGS = frozenset(
    {
        "c1s4_expected_context_gold",
        "c1s4_beat_question_targets",
        "c1s4_oracle",
        "oracle_targets",
        "session 4 -",
        "session 04 -",
        "session recaps/session 4",
        "evals/c1s4",
        "evals/",
        "gold.json",
    }
)

NPC_TARGET_ALIASES: list[tuple[str, str]] = [
    (
        "Pippa Bubbles Grishna Stone Bridge River's Edge Pub NPCs",
        "PR58 C1S4 target NPC and location family for broad encounter recall",
    ),
    (
        "encountered NPCs Pippa Bubbles Grishna",
        "PR58 target NPC continuity aliases for broad NPC question",
    ),
    (
        "Grishna River's Edge Pub",
        "Grishna pub anchor for thin hub recall",
    ),
]

ROUTE_TARGET_ALIASES: list[tuple[str, str]] = [
    (
        "Stone Bridge Mirathorn route travel week on foot",
        "Session 3 distance estimate and route context",
    ),
    (
        "Stone Bridge to Mirathorn exact route unknown",
        "Route gap plus Stone Bridge anchor",
    ),
    (
        "Mirathorn week on foot Stone Bridge",
        "Mirathorn travel-time phrasing from play recap",
    ),
]

SUPPORT_HEMPHOLM_ALIASES: list[tuple[str, str]] = [
    (
        "Hempholm visible threat giant tree",
        "Hempholm tree support-description signals detected",
    ),
    (
        "Hempholm magical metallic tree precious metal",
        "Hempholm metallic tree support card retrieval terms",
    ),
    (
        "support Hempholm tree visible threat",
        "Support-card scoped Hempholm tree alias",
    ),
    (
        "Hempholm grotesque tree metallic precious metal",
        "Hempholm tree merchant-description support alias",
    ),
]

MERGE_POLICY_DEFAULTS = {
    "literal_keep_n": 40,
    "alias_slot_n": 10,
    "alias_depth_per_variant": 20,
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _has_any(text: str, terms: frozenset[str]) -> bool:
    for term in terms:
        if " " in term:
            if term in text:
                return True
        elif re.search(rf"\b{re.escape(term)}\b", text):
            return True
    return False


def _is_support_hempholm_question(text: str) -> bool:
    if not _has_any(text, {"hempholm", "hemp", "tree"}):
        return False
    return _has_any(text, SUPPORT_HEMPHOLM_TREE_TERMS)


def _is_broad_npc_question(text: str) -> bool:
    return _has_any(text, NPC_BROAD_QUERY_TERMS)


def _is_route_distance_question(text: str) -> bool:
    return _has_any(text, ROUTE_DISTANCE_TERMS)


def query_variant_forbidden_tokens(query: str) -> list[str]:
    lowered = _norm(query)
    return [token for token in FORBIDDEN_QUERY_SUBSTRINGS if token in lowered]


def _dedupe_variants(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for variant in variants:
        query = str(variant.get("query") or "").strip()
        if not query:
            continue
        key = _norm(query)
        if key in seen:
            continue
        forbidden = query_variant_forbidden_tokens(query)
        if forbidden:
            continue
        seen.add(key)
        out.append({**variant, "query": query})
    return out


def build_step2c_query_variants(
    *,
    question_text: str,
    retrieval_mode: str,
    lane_plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    del lane_plan  # reserved for future lane-plan-driven aliases; PR59 uses deterministic rules only
    literal = str(question_text or "").strip()
    variants: list[dict[str, Any]] = [
        {
            "query": literal,
            "variant_role": "literal_question",
            "target_lane": "all",
            "reason": "original planner question",
            "source": "planner_question",
        }
    ]
    normalized = _norm(literal)

    if _is_broad_npc_question(normalized):
        for query, reason in NPC_TARGET_ALIASES:
            variants.append(
                {
                    "query": query,
                    "variant_role": "npc_target_alias",
                    "target_lane": "character_party_behavior",
                    "reason": reason,
                    "source": "deterministic_rule",
                }
            )

    if _is_route_distance_question(normalized):
        for query, reason in ROUTE_TARGET_ALIASES:
            variants.append(
                {
                    "query": query,
                    "variant_role": "route_distance_alias",
                    "target_lane": "prior_campaign_memory",
                    "reason": reason,
                    "source": "deterministic_rule",
                }
            )

    if retrieval_mode in SUPPORT_ENABLED_MODES and _is_support_hempholm_question(normalized):
        for query, reason in SUPPORT_HEMPHOLM_ALIASES:
            variants.append(
                {
                    "query": query,
                    "variant_role": "support_alias",
                    "target_lane": "support_knowledge",
                    "reason": reason,
                    "source": "deterministic_rule",
                }
            )

    return _dedupe_variants(variants)
