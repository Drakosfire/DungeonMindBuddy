"""Session-local entity candidate lists for Stage B1 routing_context (Stage 1 → Stage B hook).

These strings are **not** manifest hub slugs. They give B1 optional substring anchors for
session NPCs and locations when Stage 1 (or GM-authored recap frontmatter) publishes richer
candidate sets than ``session_npc_names`` alone.

Contract: :file:`STAGE_B_ENTITY_CANDIDATES.md`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.ingestion.frontmatter import split_frontmatter


def _parse_inline_string_list(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1].strip()
    return [p.strip().strip('"').strip("'") for p in raw.split(",") if p.strip()]


def _dedupe_ci(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in names:
        s = str(raw).strip()
        if not s:
            continue
        k = s.casefold()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


def parse_session_entity_candidates_raw(block: str) -> dict[str, list[str]] | None:
    """
    Parse optional entity-candidate keys from a YAML-ish recap frontmatter *block*.

    Supported keys (comma-separated or ``[a, b]`` lists)::

        session_npc_candidate_names: Stuart, Marla, Mirathorn liaison
        session_location_candidate_names: forest, town, tower
    """
    npc: list[str] | None = None
    loc: list[str] | None = None
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("session_npc_candidate_names:"):
            raw = stripped.split(":", 1)[1].strip()
            npc = _parse_inline_string_list(raw)
        elif stripped.startswith("session_location_candidate_names:"):
            raw = stripped.split(":", 1)[1].strip()
            loc = _parse_inline_string_list(raw)
    if npc is None and loc is None:
        return None
    out: dict[str, list[str]] = {}
    if npc is not None:
        out["npc_names"] = npc
    if loc is not None:
        out["location_names"] = loc
    return out


def _string_list_from_any(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return _parse_inline_string_list(raw)
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("label") or "").strip()
                if name:
                    out.append(name)
            else:
                s = str(item).strip()
                if s:
                    out.append(s)
        return out
    return []


def resolve_session_entity_candidates(*, inp: dict[str, Any], corpus_root: Path | None) -> tuple[list[str], list[str]]:
    """
    Return ``(npc_candidate_names, location_candidate_names)`` merged from scenario input + recap frontmatter.

    Input shapes (any may be absent):

    - ``input.session_entity_candidates``: ``{"npc_names": [...], "location_names": [...]}``
    - ``input.session_npc_candidate_names`` / ``input.session_location_candidate_names``: lists or strings
    """
    npc: list[str] = []
    loc: list[str] = []

    blob = inp.get("session_entity_candidates")
    if isinstance(blob, dict):
        npc.extend(_string_list_from_any(blob.get("npc_names")))
        npc.extend(_string_list_from_any(blob.get("npc_labels")))
        loc.extend(_string_list_from_any(blob.get("location_names")))
        loc.extend(_string_list_from_any(blob.get("location_labels")))

    npc.extend(_string_list_from_any(inp.get("session_npc_candidate_names")))
    loc.extend(_string_list_from_any(inp.get("session_location_candidate_names")))

    if corpus_root is not None:
        rel = str(inp.get("recap_relative_path") or "").strip()
        if rel:
            try:
                text = (corpus_root / rel).read_text(encoding="utf-8")
            except OSError:
                text = ""
            else:
                fm_block, _ = split_frontmatter(text)
                if fm_block:
                    parsed = parse_session_entity_candidates_raw(fm_block)
                    if parsed:
                        npc.extend(_string_list_from_any(parsed.get("npc_names")))
                        loc.extend(_string_list_from_any(parsed.get("location_names")))

    return _dedupe_ci(npc), _dedupe_ci(loc)
