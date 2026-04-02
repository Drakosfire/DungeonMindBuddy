"""Shared taxonomy normalization for entity kinds and semantic facets."""

from __future__ import annotations

import re
from typing import Literal

EntityKind = Literal[
    "actor",
    "group",
    "place",
    "object",
    "event",
    "concept",
    "document_anchor",
    "unknown",
]

DEFAULT_MAX_SEMANTIC_FACETS = 16

ALLOWED_SEMANTIC_FACETS: set[str] = {
    "deity",
    "species",
    "creature_species",
    "profession",
    "title",
    "festival",
    "ritual",
    "ceremony",
    "organization",
    "government",
    "trade_good",
    "consumable",
    "artifact",
    "weapon",
    "document_section",
    "plot_hook",
    "theme",
    "conflict",
    "route",
    "settlement",
}


def normalize_semantic_facets(
    raw: list[str] | None,
    *,
    max_facets: int = DEFAULT_MAX_SEMANTIC_FACETS,
) -> list[str]:
    """Normalize and constrain semantic facets.

    Allowed shape:
    - controlled tokens in ALLOWED_SEMANTIC_FACETS
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

        if token in ALLOWED_SEMANTIC_FACETS:
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

