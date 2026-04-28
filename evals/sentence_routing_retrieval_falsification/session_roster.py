"""Session PC roster from recap frontmatter and campaign ``_party_registry.json``; canonical ordering vs hub manifest."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.ingestion.frontmatter import split_frontmatter


def parse_session_pc_roster_raw(block: str) -> list[str] | None:
    """
    Parse optional ``session_pc_roster`` from a YAML-ish frontmatter *block* (between --- fences).

    Supported forms::

        session_pc_roster: baergrom, bonogo, caelynn

        session_pc_roster: [baergrom, bonogo, caelynn]

    Returns ``None`` if the key is absent; empty list if present but empty.
    Unknown tokens are preserved for filtering against manifest later.
    """
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("session_pc_roster:"):
            continue
        raw = stripped.split(":", 1)[1].strip()
        if not raw:
            return []
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            if not inner:
                return []
            parts = [p.strip().strip('"').strip("'") for p in inner.split(",")]
            return [p for p in parts if p]
        return [p.strip() for p in raw.split(",") if p.strip()]
    return None


def canonical_session_pc_roster_slugs(
    *,
    parsed: list[str] | None,
    manifest_ordered_slugs: list[str],
) -> list[str]:
    """
    Order and filter ``parsed`` slugs to manifest membership, using ``manifest_ordered_slugs`` order.

    When ``parsed`` is ``None`` (key absent), returns ``manifest_ordered_slugs`` (full manifest).
    """
    if not manifest_ordered_slugs:
        return []
    if parsed is None:
        return list(manifest_ordered_slugs)
    wanted = {str(x).strip().lower() for x in parsed if str(x).strip()}
    out = [s for s in manifest_ordered_slugs if s.lower() in wanted]
    return out if out else list(manifest_ordered_slugs)


def _party_registry_json_path(*, corpus_root: Path, recap_relative_path: str) -> Path | None:
    """``<campaign>/Session Recaps/<recap>.md`` → ``<campaign>/_party_registry.json`` if that file exists."""
    rel = (recap_relative_path or "").strip()
    if not rel:
        return None
    try:
        recap = (corpus_root / rel).resolve()
        recap.relative_to(corpus_root.resolve())
    except ValueError:
        return None
    if recap.parent.name != "Session Recaps":
        return None
    candidate = recap.parent.parent / "_party_registry.json"
    return candidate if candidate.is_file() else None


def _session_key_for_registry(inp: dict[str, Any], recap_relative_path: str) -> str | None:
    raw = inp.get("session")
    if raw is not None:
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int):
            return str(raw)
        if isinstance(raw, float):
            return str(int(raw))
        s = str(raw).strip()
        return s or None
    name = Path(recap_relative_path).name
    m = re.search(r"Session\s+(\d+)", name, re.IGNORECASE)
    return m.group(1) if m else None


def _session_pc_rosters_from_registry_file(
    *,
    corpus_root: Path,
    recap_relative_path: str,
    campaign_id: str | None,
    session_key: str,
) -> list[str] | None:
    """
    Return roster slugs from ``session_pc_rosters["<session>"]`` when present and campaign matches.

    ``None`` means no registry entry (caller falls back to full manifest order).
    """
    path = _party_registry_json_path(corpus_root=corpus_root, recap_relative_path=recap_relative_path)
    if path is None:
        return None
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(blob, dict):
        return None
    reg_schema = str(blob.get("schema") or "").strip()
    if reg_schema and reg_schema != "party_registry_v1":
        return None
    reg_cid = blob.get("campaign_id")
    if campaign_id and reg_cid is not None and str(reg_cid).strip() != str(campaign_id).strip():
        return None
    raw = blob.get("session_pc_rosters")
    if not isinstance(raw, dict):
        return None
    entry = raw.get(session_key)
    if entry is None:
        return None
    if not isinstance(entry, list):
        return None
    out = [str(x).strip() for x in entry if str(x).strip()]
    return out


def resolve_session_pc_roster_slugs(
    *,
    inp: dict[str, Any],
    corpus_root: Path,
    manifest_jsonable: list[dict[str, Any]],
) -> list[str]:
    """
    Session roster for routing and ``the_party`` expansion.

    Resolution order:

    1. ``session_pc_roster`` in the recap file frontmatter when the key is present (including empty).
    2. ``session_pc_rosters["<session>"]`` in ``<campaign>/_party_registry.json`` when defined
       (``session`` from ``input.session`` or parsed from ``Session N - …`` filename).
    3. Full hub-manifest PC order when both are absent.
    """
    ordered = [
        str(e.get("slug") or "").strip()
        for e in manifest_jsonable
        if str(e.get("subject_class") or "").strip() == "pc"
    ]
    ordered = [s for s in ordered if s]
    if not ordered:
        return []

    rel = str(inp.get("recap_relative_path") or "").strip()
    if not rel:
        return canonical_session_pc_roster_slugs(parsed=None, manifest_ordered_slugs=ordered)

    path = corpus_root / rel
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return canonical_session_pc_roster_slugs(parsed=None, manifest_ordered_slugs=ordered)

    block, _ = split_frontmatter(text)
    if block is None:
        parsed_fm: list[str] | None = None
    else:
        parsed_fm = parse_session_pc_roster_raw(block)

    if parsed_fm is not None:
        return canonical_session_pc_roster_slugs(parsed=parsed_fm, manifest_ordered_slugs=ordered)

    cid_raw = inp.get("campaign_id")
    cid = str(cid_raw).strip() if cid_raw is not None else ""
    sk = _session_key_for_registry(inp, rel)
    if sk:
        reg_list = _session_pc_rosters_from_registry_file(
            corpus_root=corpus_root,
            recap_relative_path=rel,
            campaign_id=cid or None,
            session_key=sk,
        )
        if reg_list is not None:
            return canonical_session_pc_roster_slugs(parsed=reg_list, manifest_ordered_slugs=ordered)

    return canonical_session_pc_roster_slugs(parsed=None, manifest_ordered_slugs=ordered)
