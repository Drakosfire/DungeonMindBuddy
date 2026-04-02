"""Shared normalization for entity_tags (schema: unique snake_case strings)."""

from __future__ import annotations

import re

DEFAULT_MAX_ENTITY_TAGS = 12


def normalize_entity_tags(
    raw: list[str] | None,
    *,
    max_tags: int = DEFAULT_MAX_ENTITY_TAGS,
) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        tok = re.sub(r"[^a-z0-9_]+", "_", str(item).strip().lower())
        tok = re.sub(r"_+", "_", tok).strip("_")
        if not tok or tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
        if len(out) >= max_tags:
            break
    return out
