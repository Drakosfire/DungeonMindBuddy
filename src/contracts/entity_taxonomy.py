"""Shared taxonomy normalization for entity classes and subtype facets."""

from __future__ import annotations

import re
from typing import Literal

EntityClass = Literal[
    "actor",
    "group",
    "place",
    "object",
    "event",
    "concept",
]

DEFAULT_MAX_SEMANTIC_FACETS = 16

SourceProfile = Literal[
    "worldbuilding",
    "session_recap",
    "npc_dossier",
    "item_card",
    "encounter_table",
    "cultural_event_doc",
]

Authority = Literal[
    "canon_reference",
    "planning_note",
    "play_record",
    "rumor_or_belief",
    "mechanic_reference",
]

ExcludeReason = Literal[
    "generic_noun",
    "descriptive_phrase",
    "document_structure",
    "game_mechanic",
    "sentence_fragment",
    "temporal_connector",
    "underspecified_collective",
]

ALLOWED_SUBTYPE_FACETS: set[str] = {
    "deity",
    "species",
    "festival",
    "ritual",
    "artifact",
    "settlement",
    "building",
    "vehicle",
    "cult",
    "guild",
    "family",
    "title",
    "law",
    "doctrine",
    "prophecy",
    "curse",
    "institution",
    "profession",
    "organization",
    "government",
    "trade_good",
    "consumable",
    "weapon",
    "route",
}

ALLOWED_NARRATIVE_TAGS: set[str] = {
    "plot_hook",
    "theme",
    "conflict",
    "mystery",
    "foreshadowing",
    "reveal",
    "threat",
    "goal",
    "secret",
}

ALLOWED_DOCUMENT_TAGS: set[str] = {
    "summary",
    "prep_note",
    "boxed_text",
    "branch_point",
    "section_header",
    "timeline_note",
}

# Backward-compat alias for callers not yet migrated.
EntityKind = EntityClass
ALLOWED_SEMANTIC_FACETS = ALLOWED_SUBTYPE_FACETS


def normalize_semantic_facets(
    raw: list[str] | None,
    *,
    max_facets: int = DEFAULT_MAX_SEMANTIC_FACETS,
) -> list[str]:
    """Normalize and constrain semantic facets.

    Allowed shape:
    - controlled tokens in ALLOWED_SUBTYPE_FACETS
    - namespaced facets in `domain:*` form for campaign-specific extensions
    """
    if not raw:
        return []

    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        token = str(item).strip().lower()
        if not token:
            continue

        token = re.sub(r"[^a-z0-9:_-]+", "_", token)
        token = re.sub(r"_+", "_", token).strip("_")
        if not token:
            continue

        if token in ALLOWED_SUBTYPE_FACETS:
            normalized = token
        elif token.startswith("domain:"):
            suffix = token.split(":", 1)[1].strip()
            suffix = re.sub(r"[^a-z0-9_-]+", "_", suffix)
            suffix = re.sub(r"_+", "_", suffix).strip("_")
            if not suffix:
                continue
            normalized = f"domain:{suffix}"
        else:
            continue

        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
        if len(out) >= max_facets:
            break
    return out

