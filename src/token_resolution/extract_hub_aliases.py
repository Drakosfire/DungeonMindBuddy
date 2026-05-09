"""Extract :class:`HubAliasSpec` rows from corpus / breadcrumb frontmatter.

The breadcrumb frontmatter is the canonical source of entity slugs, routes, and
recap aliases. We treat it as immutable input here and produce a list of
``HubAliasSpec`` rows plus a deduped list of "protected tokens" — slug-derived
words that must never be turned into route stopwords by ``derive_stopwords``
(otherwise we'd suppress real signal like ``lysandra`` or ``magma``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.token_resolution.contracts import HubAliasSpec

_FM_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*$", re.DOTALL | re.MULTILINE)

_ENTITY_INDEX_HEADER_RE = re.compile(r"^entity_index:\s*$", re.MULTILINE)

_PARTY_BLOCK_RE = re.compile(
    r"^  parties:\s*\n((?:    [^\n]*\n)+)",
    re.MULTILINE,
)

_GENERIC_ENTITY_LIST_HEADERS: tuple[str, ...] = (
    "pcs",
    "npcs",
    "locations",
    "new_hub_candidates",
)


@dataclass(frozen=True)
class HubAliasExtraction:
    """Bundle of alias specs and protected tokens derived from a single source."""

    aliases: tuple[HubAliasSpec, ...]
    protected_tokens: tuple[str, ...]
    source_paths: tuple[str, ...]


def _read_frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (without the ``---`` fences) or ``""``."""
    match = _FM_BLOCK_RE.search(text)
    if not match:
        return ""
    return match.group(1)


def _slug_to_surface_aliases(slug: str) -> list[str]:
    """Turn ``captain_lysandra_ironveil`` into surface-form aliases.

    Produces the human phrase + each token (length >= 3) so retrieval can hit on
    any of ``"captain"``, ``"lysandra"``, ``"ironveil"``, or the full phrase.
    """
    cleaned = (slug or "").strip().lower()
    if not cleaned:
        return []
    parts = [p for p in re.split(r"[_\-\s]+", cleaned) if p]
    if not parts:
        return []
    aliases: list[str] = []
    phrase = " ".join(parts).strip()
    if len(parts) >= 2 and phrase and phrase not in aliases:
        aliases.append(phrase)
    for token in parts:
        if len(token) >= 3 and token not in aliases:
            aliases.append(token)
    return aliases


def _slug_protected_tokens(slug: str) -> list[str]:
    """Slug → individual tokens that should be protected from stopword derivation."""
    cleaned = (slug or "").strip().lower()
    if not cleaned:
        return []
    parts = [p for p in re.split(r"[_\-\s]+", cleaned) if p]
    return [p for p in parts if len(p) >= 3]


def _parse_party_blocks(frontmatter: str) -> list[dict[str, str | list[str]]]:
    """Return a list of parsed ``parties`` entries.

    The breadcrumb frontmatter parties block is two-deep YAML:

    .. code-block:: yaml

        parties:
          party_merchant_guards:
            slug: party_merchant_guards
            display_name: "Merchant-guard fellowship (Session 1)"
            aliases_in_recap:
              - "the group"
              - "the team"
    """
    out: list[dict[str, str | list[str]]] = []
    block_match = _PARTY_BLOCK_RE.search(frontmatter)
    if not block_match:
        return out
    block_text = block_match.group(1)
    current: dict[str, str | list[str]] | None = None
    aliases_target: list[str] | None = None
    for line in block_text.splitlines():
        if not line.strip():
            continue
        if re.match(r"^    [A-Za-z0-9_]+:\s*$", line):
            if current is not None:
                out.append(current)
            current = {}
            aliases_target = None
            continue
        if current is None:
            continue
        scalar_match = re.match(r"^      ([A-Za-z0-9_]+):\s*(.*)$", line)
        if scalar_match:
            key = scalar_match.group(1)
            value = scalar_match.group(2).strip()
            if key == "aliases_in_recap" and not value:
                current[key] = []
                aliases_target = current[key]  # type: ignore[assignment]
                continue
            aliases_target = None
            stripped = value.strip().strip('"').strip("'")
            current[key] = stripped
            continue
        list_match = re.match(r"^        -\s+(.*)$", line)
        if list_match and aliases_target is not None:
            value = list_match.group(1).strip().strip('"').strip("'")
            if value:
                aliases_target.append(value)
            continue
    if current is not None:
        out.append(current)
    return out


def _parse_generic_entity_list(frontmatter: str, header: str) -> list[dict[str, str]]:
    """Parse simple list-of-maps under ``entity_index.<header>:``.

    Handles ``pcs``, ``npcs``, ``locations``, ``new_hub_candidates``. Each entry
    is a ``-``-prefixed map with ``slug`` and either ``route`` or
    ``proposed_route`` and an optional ``rationale``/``subject_type``.
    """
    header_re = re.compile(rf"^  {re.escape(header)}:\s*$", re.MULTILINE)
    next_peer_re = re.compile(r"^  [A-Za-z0-9_]+:\s*$", re.MULTILINE)
    item_open_re = re.compile(r"^    -\s+([A-Za-z0-9_]+):\s*(.*)$")
    child_re = re.compile(r"^      ([A-Za-z0-9_]+):\s*(.*)$")

    header_match = header_re.search(frontmatter)
    if not header_match:
        return []
    end_idx = len(frontmatter)
    for peer in next_peer_re.finditer(frontmatter, header_match.end()):
        if peer.start() > header_match.end():
            end_idx = peer.start()
            break
    body = frontmatter[header_match.end():end_idx]

    out: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    for line in body.splitlines():
        if not line.strip():
            continue
        item_match = item_open_re.match(line)
        if item_match:
            if cur is not None:
                out.append(cur)
            cur = {item_match.group(1): item_match.group(2).strip().strip('"').strip("'")}
            continue
        child_match = child_re.match(line)
        if child_match and cur is not None:
            cur[child_match.group(1)] = child_match.group(2).strip().strip('"').strip("'")
    if cur is not None:
        out.append(cur)
    return out


def _campaign_id_from_frontmatter(frontmatter: str) -> str:
    match = re.search(r"^\s*campaign_id:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def extract_hub_aliases_from_frontmatter(
    frontmatter: str,
    *,
    source_path: str = "",
) -> HubAliasExtraction:
    """Extract :class:`HubAliasSpec` rows from a single breadcrumb frontmatter block."""
    aliases: list[HubAliasSpec] = []
    protected: list[str] = []
    if _ENTITY_INDEX_HEADER_RE.search(frontmatter) is None:
        return HubAliasExtraction((), (), (source_path,) if source_path else ())

    for party in _parse_party_blocks(frontmatter):
        slug = str(party.get("slug") or "").strip().lower()
        if not slug:
            continue
        slug_aliases = _slug_to_surface_aliases(slug)
        recap_aliases = [
            str(a).strip()
            for a in party.get("aliases_in_recap", [])  # type: ignore[arg-type]
            if str(a).strip()
        ]
        display_name = str(party.get("display_name", "")).strip()
        all_aliases = []
        if display_name:
            all_aliases.append(display_name)
        all_aliases.extend(slug_aliases)
        all_aliases.extend(recap_aliases)
        aliases.append(
            HubAliasSpec(
                slug=slug,
                subject_class="Party",
                aliases=all_aliases,
                source_ref=source_path or "",
            )
        )
        protected.extend(_slug_protected_tokens(slug))

    for header in _GENERIC_ENTITY_LIST_HEADERS:
        for entry in _parse_generic_entity_list(frontmatter, header):
            slug = str(entry.get("slug") or "").strip().lower()
            if not slug:
                continue
            subject_class = {
                "pcs": "PC",
                "npcs": "NPC",
                "locations": "Location",
                "new_hub_candidates": (entry.get("subject_type") or "NewHubCandidate")
                .strip()
                .capitalize()
                or "NewHubCandidate",
            }[header]
            entry_aliases = _slug_to_surface_aliases(slug)
            display_name = str(entry.get("display_name", "")).strip()
            if display_name:
                entry_aliases.insert(0, display_name)
            aliases.append(
                HubAliasSpec(
                    slug=slug,
                    subject_class=subject_class,
                    aliases=entry_aliases,
                    source_ref=source_path or "",
                )
            )
            protected.extend(_slug_protected_tokens(slug))

    return HubAliasExtraction(
        aliases=tuple(aliases),
        protected_tokens=tuple(dict.fromkeys(protected)),
        source_paths=(source_path,) if source_path else (),
    )


def extract_hub_aliases_from_paths(
    breadcrumb_paths: Iterable[Path],
) -> HubAliasExtraction:
    """Extract aliases from one or more breadcrumb markdown files."""
    all_aliases: list[HubAliasSpec] = []
    all_protected: list[str] = []
    seen_paths: list[str] = []
    for path in breadcrumb_paths:
        text = Path(path).read_text(encoding="utf-8")
        frontmatter = _read_frontmatter(text)
        if not frontmatter:
            continue
        extraction = extract_hub_aliases_from_frontmatter(
            frontmatter,
            source_path=str(path),
        )
        all_aliases.extend(extraction.aliases)
        all_protected.extend(extraction.protected_tokens)
        seen_paths.append(str(path))
    return HubAliasExtraction(
        aliases=tuple(all_aliases),
        protected_tokens=tuple(dict.fromkeys(all_protected)),
        source_paths=tuple(seen_paths),
    )


def extract_campaign_id(breadcrumb_paths: Iterable[Path]) -> str:
    """Best-effort: campaign id from the first breadcrumb file with a parseable header."""
    for path in breadcrumb_paths:
        try:
            frontmatter = _read_frontmatter(Path(path).read_text(encoding="utf-8"))
        except OSError:
            continue
        cid = _campaign_id_from_frontmatter(frontmatter)
        if cid:
            return cid
    return ""
