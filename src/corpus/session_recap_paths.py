"""Corpus-relative paths for session recap derivatives (_normalized, _breadcrumbed, _session_memory)."""

from __future__ import annotations

import re
from pathlib import Path

# Curated slugs for generic Session N - Recap titles (mirrors materialize_normalized_recaps).
_SLUGS: dict[tuple[str, int], str] = {
    ("longmont-c1", 1): "Stonebridge and Glowkindle Rats",
    ("longmont-c1", 9): "Battle with the Meat Monsters",
    ("longmont-c1", 10): "Thraxx and the Last Warehouse",
    ("longmont-c1", 12): "The Persistent Bugbear",
    ("longmont-c1", 15): "Cult Tunnels and Captain Idris",
    ("longmont-c1", 16): "Peacemaker Fiddle Meat Pile",
    ("longmont-c1", 17): "Festival Aftermath Loose Ends",
    ("longmont-c2", 2): "Steel Fangs Colosseum",
    ("longmont-c2", 3): "Storms Torbin and Shepherd",
    ("longmont-c2", 4): "Wolf Manor Mage Duel",
    ("longmont-c2", 5): "Lysandra Tea Guardhouse",
    ("longmont-c2", 6): "Barn Fleshborn Shepherd Wake",
    ("longmont-c2", 7): "Portals Tentacles Barn",
    ("longmont-c2", 8): "Dustwalker Cellar Barin Party",
    ("longmont-c2", 9): "Costume Contest Temple Aspitome",
    ("longmont-c2", 10): "Festival Crafting Elementals",
    ("longmont-c2", 11): "Coliseum Finals Tealeaf Tea",
    ("longmont-c2", 12): "Dustwalker Globe Duel",
    ("longmont-c2", 13): "Council Curfew Swamp March",
    ("longmont-c2", 14): "Supplies Wolf Crypt Letter",
    ("longmont-c2", 15): "Ride Out Mossford Ale",
    ("longmont-c2", 16): "Thinking Tree Sneaking Forest",
    ("longmont-c2", 18): "Wyvern Mother Fallen Spine",
    ("longmont-c2", 19): "Mossford Plans Stuart Inn",
    ("longmont-c2", 20): "Gnat Swarm Marla Lysandra",
}

PILOT_BLESSED_SESSIONS: tuple[tuple[int, int], ...] = (
    (1, 1),
    (1, 2),
    (1, 3),
    (1, 13),
    (2, 20),
)

# Tool-shaped / generic recap tails that must never become a canonical slug or title.
# Shared by the live ingest route and pipeline so frontend/backend guards stay aligned.
GENERIC_RECAP_TAILS: frozenset[str] = frozenset(
    {
        "",
        "ingest",
        "ingestion",
        "raw recap",
        "raw recap ingest",
        "raw recap ingestion",
        "recap",
        "recap ingest",
        "recap ingestion",
        "session recap",
    }
)


def recap_tail(text: str | None) -> str:
    """Normalize a slug/title/basename down to its comparable tail.

    ``"Session 23 - Mireward Gate Battle"`` -> ``"mireward gate battle"``;
    ``"ingest"`` -> ``"ingest"``; ``None`` -> ``""``.
    """
    raw = str(text or "").strip()
    if not raw:
        return ""
    m = re.match(r"^Session\s+\d+\s*(?:-\s*)?(.+)$", raw, re.I)
    if m:
        raw = m.group(1).strip()
    return raw.rstrip(":").strip().lower()


def is_generic_recap_tail(text: str | None) -> bool:
    return recap_tail(text) in GENERIC_RECAP_TAILS


def normalized_recap_candidates(
    corpus_root: Path,
    *,
    campaign_number: int,
    session: int,
) -> list[Path]:
    """All ``_normalized/Session N - *.md`` files for a session (excludes ``_archive``)."""
    norm_dir = corpus_root / session_recaps_prefix(campaign_number) / "_normalized"
    if not norm_dir.is_dir():
        return []
    seen: dict[Path, None] = {}
    for pattern in (f"Session {session:02d} - *.md", f"Session {session} - *.md"):
        for path in norm_dir.glob(pattern):
            if path.is_file():
                seen.setdefault(path.resolve(), None)
    return sorted(seen.keys())


def campaign_id_from_number(campaign_number: int) -> str:
    if campaign_number not in (1, 2):
        raise ValueError(f"unsupported campaign number: {campaign_number}")
    return f"longmont-c{campaign_number}"


def campaign_number_from_id(campaign_id: str) -> int:
    m = re.match(r"^longmont-c(\d+)$", campaign_id.strip(), re.I)
    if not m:
        raise ValueError(f"unsupported campaign_id: {campaign_id}")
    return int(m.group(1))


def slug_from_title(title: str, campaign_id: str, session: int) -> str:
    key = (campaign_id, session)
    if key in _SLUGS:
        return str(_SLUGS[key])
    t = str(title or "").strip()
    m = re.match(r"^Session\s+\d+\s*-\s*(.+)$", t, re.I)
    if m:
        t = m.group(1).strip()
    t = re.sub(r":+\s*$", "", t).strip()
    if re.match(r"^Recap:?$", t, re.I):
        raise ValueError(f"generic recap title for {campaign_id} S{session}; add _SLUGS entry")
    if not t:
        raise ValueError(f"Unresolved slug for {campaign_id} S{session}")
    return t


def normalized_basename(*, campaign_id: str, session: int, title: str | None = None) -> str:
    slug = slug_from_title(title or f"Session {session}", campaign_id, session)
    return f"Session {session:02d} - {slug}"


def session_recaps_prefix(campaign_number: int) -> str:
    return f"Longmont Campaign/Campaign {campaign_number}/Session Recaps"


def normalized_basename_from_disk(corpus_root: Path, *, campaign_number: int, session: int) -> str:
    """Resolve basename from an existing ``_normalized/Session … - <slug>.md`` file."""
    norm_dir = corpus_root / session_recaps_prefix(campaign_number) / "_normalized"
    candidates = normalized_recap_candidates(
        corpus_root, campaign_number=campaign_number, session=session
    )
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"expected exactly one normalized recap for C{campaign_number}S{session} under {norm_dir}"
        )
    return candidates[0].stem


def _basename(
    *,
    campaign_number: int,
    session: int,
    title: str | None,
    corpus_root: Path | None,
) -> str:
    if corpus_root is not None:
        return normalized_basename_from_disk(corpus_root, campaign_number=campaign_number, session=session)
    campaign_id = campaign_id_from_number(campaign_number)
    return normalized_basename(campaign_id=campaign_id, session=session, title=title)


def normalized_recap_relpath(
    *,
    campaign_number: int,
    session: int,
    title: str | None = None,
    corpus_root: Path | None = None,
) -> str:
    base = _basename(
        campaign_number=campaign_number,
        session=session,
        title=title,
        corpus_root=corpus_root,
    )
    return f"{session_recaps_prefix(campaign_number)}/_normalized/{base}.md"


def breadcrumbed_relpath(
    *,
    campaign_number: int,
    session: int,
    title: str | None = None,
    corpus_root: Path | None = None,
) -> str:
    base = _basename(
        campaign_number=campaign_number,
        session=session,
        title=title,
        corpus_root=corpus_root,
    )
    return f"{session_recaps_prefix(campaign_number)}/_breadcrumbed/{base}.breadcrumbed.md"


def frontmatter_seed_relpath(
    *,
    campaign_number: int,
    session: int,
    title: str | None = None,
    corpus_root: Path | None = None,
) -> str:
    base = _basename(
        campaign_number=campaign_number,
        session=session,
        title=title,
        corpus_root=corpus_root,
    )
    return f"{session_recaps_prefix(campaign_number)}/_breadcrumbed/{base}.frontmatter_seed.md"


def session_memory_jsonl_relpath(
    *,
    campaign_number: int,
    session: int,
    title: str | None = None,
    corpus_root: Path | None = None,
) -> str:
    base = _basename(
        campaign_number=campaign_number,
        session=session,
        title=title,
        corpus_root=corpus_root,
    )
    return f"{session_recaps_prefix(campaign_number)}/_session_memory/{base}.records_meta.jsonl"


def session_memory_meta_relpath(
    *,
    campaign_number: int,
    session: int,
    title: str | None = None,
    corpus_root: Path | None = None,
) -> str:
    base = _basename(
        campaign_number=campaign_number,
        session=session,
        title=title,
        corpus_root=corpus_root,
    )
    return f"{session_recaps_prefix(campaign_number)}/_session_memory/{base}.records_meta.json"


def resolve_under_corpus(corpus_root: Path, rel_path: str) -> Path:
    return (corpus_root / rel_path).resolve()
