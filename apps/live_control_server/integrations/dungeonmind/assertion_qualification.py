"""Kernel-free Buddy → DungeonMind assertion qualification (CUTOVER D.3A).

Extracted from whole-world conformance v4 / v1 helpers so mounted governed
writes can qualify kinds and predicates without importing
``graph_memory.kernel`` / ``world_supergraph`` / ``union_supergraph`` or
``integrations/dungeonmind_kernel/**``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_world_object_v5_vocabulary,
)

_BUDDY_TO_DM_KIND: dict[str, str] = {
    "threat": "dnd5e:threat",
    "npc": "dnd5e:npc",
    "pc": "dnd5e:player_character",
    "creature": "dnd5e:creature",
    "location": "dnd5e:location",
    "faction": "dnd5e:faction",
    "encounter": "dnd5e:encounter",
    "item": "dnd5e:item",
    "mystery": "dnd5e:mystery",
    "group": "dnd5e:group",
    "party": "dnd5e:party",
    "event": "dnd5e:event",
}

_BUDDY_TO_DM_KIND_V5: dict[str, str] = {
    **_BUDDY_TO_DM_KIND,
    "thread": "dnd5e:thread",
}

# Direct Buddy predicate → dnd5e:<same> (no generic f"dnd5e:{pred}" fallback).
_DIRECT_PREDICATE_MAP: frozenset[str] = frozenset(
    {
        "allied_with",
        "associated_with",
        "attacks",
        "aware_of",
        "carries",
        "causes",
        "commands",
        "contains",
        "cooperates_with",
        "displaced_from",
        "holds",
        "knows_about",
        "leads",
        "leads_to",
        "located_in",
        "member_of",
        "near",
        "owns",
        "parent_of",
        "part_of",
        "participates_in",
        "possesses",
        "present_at",
        "pursues",
        "recruits_for",
        "rivals",
        "serves",
        "south_of",
        "suspects",
        "threatens",
        "travels_to",
        "trusts",
        "works_with",
    }
)

_RENAME_PREDICATE_MAP: dict[str, str] = {
    "appeared_in": "dnd5e:present_at",
    "linked_to": "dnd5e:associated_with",
    "occurred_at": "dnd5e:occurs_at",
    "participated_in": "dnd5e:participates_in",
    "path_to": "dnd5e:leads_to",
    "results_in": "dnd5e:causes",
    "routes_to": "dnd5e:leads_to",
    "sublocation_of": "dnd5e:part_of",
    "within": "dnd5e:located_in",
}

# Buddy pred → (dm_term, reverse_endpoints). Only belongs_to uses reverse.
_REVERSE_ENDPOINT_PREDICATE_MAP: dict[str, tuple[str, bool]] = {
    "belongs_to": ("dnd5e:owns", True),
}

_INTENTIONALLY_UNRESOLVED_PREDICATES: frozenset[str] = frozenset(
    {
        "carries_report_to",
        "controls_comms_with",
        "defends_weakened_location",
        "identified_as",
        "mission_targets",
        "objective_of",
        "part_of_group",
        "reports_threat_in",
        "same_as",
    }
)

_USES_STATBLOCK = "uses_statblock"

# Full-edge direction audit: reverse-qualifier patterns in edge_id (casefold).
_DIRECTION_REVERSE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "threatens": (
        re.compile(r"is-threatened-by", re.IGNORECASE),
        re.compile(r"threatened-by", re.IGNORECASE),
    ),
    "attacks": (
        re.compile(r"is-attacked-by", re.IGNORECASE),
        re.compile(r"attacked-by", re.IGNORECASE),
    ),
    "owns": (
        re.compile(r"is-owned-by", re.IGNORECASE),
        re.compile(r"owned-by", re.IGNORECASE),
    ),
    "contains": (
        re.compile(r"is-contained-in", re.IGNORECASE),
        re.compile(r"is-contained-by", re.IGNORECASE),
    ),
    "leads": (
        re.compile(r"is-led-by", re.IGNORECASE),
        re.compile(r"led-by", re.IGNORECASE),
    ),
    "commands": (
        re.compile(r"is-commanded-by", re.IGNORECASE),
        re.compile(r"commanded-by", re.IGNORECASE),
    ),
    "serves": (
        re.compile(r"is-served-by", re.IGNORECASE),
        re.compile(r"served-by", re.IGNORECASE),
    ),
    "parent_of": (
        re.compile(r"is-child-of", re.IGNORECASE),
        re.compile(r"child-of", re.IGNORECASE),
    ),
    "causes": (
        re.compile(r"is-caused-by", re.IGNORECASE),
        re.compile(r"caused-by", re.IGNORECASE),
    ),
}


@dataclass(frozen=True, slots=True)
class QualificationTarget:
    """Slim current-v5 target surface needed by mounted write qualification."""

    buddy_to_dm_kind: Mapping[str, str]
    world_object_loader: Callable[[], Any]


CURRENT_V5_TARGET = QualificationTarget(
    buddy_to_dm_kind=_BUDDY_TO_DM_KIND_V5,
    world_object_loader=load_builtin_world_object_v5_vocabulary,
)


def predicate_allowed_endpoints(
    dm_predicate: str,
    vocabulary: Any,
) -> tuple[frozenset[str], frozenset[str]] | None:
    for predicate in vocabulary.predicates:
        if predicate.term == dm_predicate:
            return frozenset(predicate.subject_kinds), frozenset(predicate.object_kinds)
    return None


# Historical private name used by world_graph_writes call sites.
_predicate_allowed_endpoints = predicate_allowed_endpoints


def resolve_buddy_predicate_mapping_v4(
    buddy_predicate: str,
) -> tuple[str | None, bool] | None:
    """Return (dm_term, reverse_endpoints) for an explicit v4 map, else None.

    Intentionally unresolved / mechanics / unknown predicates return None.
    Does not invent ``dnd5e:{pred}`` or ``dnd5e:related_to``.
    """
    if buddy_predicate == _USES_STATBLOCK:
        return None
    if buddy_predicate in _INTENTIONALLY_UNRESOLVED_PREDICATES:
        return None
    if buddy_predicate in _REVERSE_ENDPOINT_PREDICATE_MAP:
        return _REVERSE_ENDPOINT_PREDICATE_MAP[buddy_predicate]
    if buddy_predicate in _RENAME_PREDICATE_MAP:
        return _RENAME_PREDICATE_MAP[buddy_predicate], False
    if buddy_predicate in _DIRECT_PREDICATE_MAP:
        return f"dnd5e:{buddy_predicate}", False
    return None


def edge_has_reverse_direction_qualifier_v4(
    *,
    buddy_predicate: str,
    edge_id: str,
) -> bool:
    """True when edge_id contains a reverse-qualifier pattern for the Buddy predicate."""
    patterns = _DIRECTION_REVERSE_PATTERNS.get(buddy_predicate)
    if not patterns:
        return False
    return any(pattern.search(edge_id) for pattern in patterns)
