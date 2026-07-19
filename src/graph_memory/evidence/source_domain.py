from __future__ import annotations

from typing import Literal

SourceDomain = Literal[
    "recap",
    "statblock",
    "worldbuilding",
    "npc_note",
    "location_note",
    "faction_note",
    "item_note",
    "session_memory",
    "manual_seed",
    "future_artifact",
    "party_registry",
]

KNOWN_SOURCE_DOMAINS: frozenset[str] = frozenset(
    {
        "recap",
        "statblock",
        "worldbuilding",
        "npc_note",
        "location_note",
        "faction_note",
        "item_note",
        "session_memory",
        "manual_seed",
        "future_artifact",
        "party_registry",
    }
)


def is_known_source_domain(value: str) -> bool:
    return value in KNOWN_SOURCE_DOMAINS
