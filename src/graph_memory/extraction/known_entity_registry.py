"""Corpus-agnostic known-entity registry for deterministic mention matching.

Loads standing cast (PCs + traveling companions) from a campaign party registry,
resolves display names from hubs, and optionally merges aliases from an adjacent
``_npc_registry.json`` (companions / notable NPCs). Scope is injected via
``campaign_id`` / corpus paths — no Longmont-specific hardcoding in the matcher.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.graph_memory.party_context import (
    PARTY_REGISTRY_BASENAME,
    PartyContext,
    PartyMember,
    build_party_context_for_campaign,
    load_party_registry,
    resolve_campaign_corpus,
)

NPC_REGISTRY_BASENAME = "_npc_registry.json"

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+", re.UNICODE)


@dataclass(frozen=True)
class KnownEntity:
    slug: str
    kind: str  # "pc" | "companion"
    display_name: str
    canonical_entity_id: str
    aliases: tuple[str, ...]
    hub_rel_path: str
    hub_resolved: bool
    corpus_ref: Mapping[str, object]
    match_terms: tuple[tuple[str, str], ...] = ()  # (surface, match_method)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "kind": self.kind,
            "display_name": self.display_name,
            "canonical_entity_id": self.canonical_entity_id,
            "aliases": list(self.aliases),
            "hub_rel_path": self.hub_rel_path,
            "hub_resolved": self.hub_resolved,
            "corpus_ref": dict(self.corpus_ref),
            "match_terms": [{"surface": s, "match_method": m} for s, m in self.match_terms],
        }


@dataclass(frozen=True)
class KnownEntityRegistry:
    campaign_id: str
    session_key: str
    roster_session_key: str | None
    roster_carry_forward: bool
    registry_relpath: str | None
    entities: tuple[KnownEntity, ...]
    warnings: tuple[str, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def by_slug(self) -> dict[str, KnownEntity]:
        return {e.slug: e for e in self.entities}

    def by_canonical_id(self) -> dict[str, KnownEntity]:
        return {e.canonical_entity_id: e for e in self.entities}


def normalize_match_surface(value: str) -> str:
    """Unicode NFKC + casefold + punctuation strip for matching keys."""
    text = unicodedata.normalize("NFKC", value or "")
    text = text.casefold()
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


# Title/role tokens that must never become match aliases on their own.
# "Captain Lysandra Ironveil" must not yield alias "Captain"; NPC extras like
# "the captain" are likewise unsafe for deterministic attribution.
_TITLE_ROLE_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "captain",
        "commander",
        "professor",
        "sheriff",
        "mayor",
        "lord",
        "lady",
        "sir",
        "dame",
        "doctor",
        "dr",
        "sergeant",
        "general",
        "admiral",
        "king",
        "queen",
        "prince",
        "princess",
        "duke",
        "duchess",
        "baron",
        "baroness",
        "master",
        "mistress",
        "elder",
        "chief",
        "lieutenant",
        "colonel",
        "major",
        "private",
        "corporal",
    }
)


def is_unsafe_match_alias(surface: str) -> bool:
    """Reject title/role stopwords and determiner+title phrases (``the captain``)."""
    norm = normalize_match_surface(surface)
    if not norm:
        return True
    parts = norm.split()
    if len(parts) == 1:
        return parts[0] in _TITLE_ROLE_STOPWORDS
    if len(parts) == 2 and parts[0] in {"a", "an", "the"} and parts[1] in _TITLE_ROLE_STOPWORDS:
        return True
    return False


def _derived_aliases(display_name: str, slug: str) -> list[str]:
    aliases: list[str] = []
    display = (display_name or "").strip()
    if display:
        aliases.append(display)
        first = display.split()[0].strip(".,;:'\"") if display.split() else ""
        if (
            first
            and len(first) >= 3
            and first.casefold() != display.casefold()
            and not is_unsafe_match_alias(first)
        ):
            aliases.append(first)
    slug_label = slug.replace("_", " ").strip()
    if (
        slug_label
        and slug_label.casefold() not in {a.casefold() for a in aliases}
        and not is_unsafe_match_alias(slug_label)
    ):
        aliases.append(slug_label.title() if slug_label.islower() else slug_label)
    # Prefer first token of slug (baergrom) when distinct and not a title stopword
    slug_first = slug.split("_", 1)[0].strip()
    if slug_first and len(slug_first) >= 3 and not is_unsafe_match_alias(slug_first):
        titled = slug_first.title()
        if titled.casefold() not in {a.casefold() for a in aliases}:
            aliases.append(titled)
    return aliases


def _load_npc_alias_map(corpus_root: Path, campaign_rel: str) -> dict[str, list[str]]:
    path = corpus_root / campaign_rel / NPC_REGISTRY_BASENAME
    if not path.is_file():
        return {}
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = blob if isinstance(blob, list) else blob.get("npcs") if isinstance(blob, dict) else None
    if not isinstance(rows, list):
        return {}
    out: dict[str, list[str]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug") or "").strip()
        if not slug:
            continue
        aliases = [str(a).strip() for a in (row.get("aliases") or []) if str(a).strip()]
        display = str(row.get("display_name") or "").strip()
        if display:
            aliases = [display, *aliases]
        out[slug] = aliases
    return out


def _build_match_terms(
    display_name: str,
    slug: str,
    *,
    extra_aliases: Sequence[str] = (),
) -> tuple[tuple[str, str], ...]:
    terms: list[tuple[str, str]] = []
    seen_norm: set[str] = set()

    def add(surface: str, method: str) -> None:
        cleaned = surface.strip()
        if not cleaned:
            return
        # Canonical display name is always allowed; derived/extra aliases are not
        # when they collapse to a title/role stopword.
        if method != "canonical" and is_unsafe_match_alias(cleaned):
            return
        key = normalize_match_surface(cleaned)
        if not key or key in seen_norm:
            return
        seen_norm.add(key)
        terms.append((cleaned, method))

    add(display_name, "canonical")
    for alias in _derived_aliases(display_name, slug):
        method = "canonical" if alias.casefold() == display_name.casefold() else "alias"
        add(alias, method)
    for alias in extra_aliases:
        add(alias, "alias")
    # Longest first for matcher convenience
    terms.sort(key=lambda item: len(normalize_match_surface(item[0])), reverse=True)
    return tuple(terms)


def _member_to_known_entity(
    member: PartyMember,
    *,
    extra_aliases: Sequence[str] = (),
) -> KnownEntity:
    match_terms = _build_match_terms(
        member.display_name,
        member.slug,
        extra_aliases=extra_aliases,
    )
    aliases = tuple(
        surface for surface, method in match_terms if method == "alias"
    )
    return KnownEntity(
        slug=member.slug,
        kind=member.kind,
        display_name=member.display_name,
        canonical_entity_id=str(member.seed_node()["node_id"]),
        aliases=aliases,
        hub_rel_path=member.hub_rel_path,
        hub_resolved=member.hub_resolved,
        corpus_ref=member.corpus_ref(),
        match_terms=match_terms,
    )


def resolve_roster_session_key(
    registry: Mapping[str, Any] | None,
    session_key: str,
) -> tuple[str | None, bool]:
    """Return (resolved_session_key, carried_forward).

    Exact key wins. Otherwise use the greatest numeric session key ``<=`` request.
    Non-numeric keys only match exactly.
    """
    if not isinstance(registry, Mapping):
        return None, False
    rosters = registry.get("session_pc_rosters")
    if not isinstance(rosters, Mapping):
        # v2 shape
        session_rosters = registry.get("session_rosters")
        if isinstance(session_rosters, Mapping):
            if session_key in session_rosters:
                return session_key, False
            numeric_keys: list[int] = []
            for key in session_rosters:
                if str(key).isdigit():
                    numeric_keys.append(int(key))
            if session_key.isdigit() and numeric_keys:
                target = int(session_key)
                prior = [k for k in numeric_keys if k <= target]
                if prior:
                    chosen = str(max(prior))
                    return chosen, chosen != session_key
        return None, False

    if session_key in rosters and isinstance(rosters.get(session_key), list):
        return session_key, False
    if not session_key.isdigit():
        return None, False
    target = int(session_key)
    prior = [int(k) for k in rosters if str(k).isdigit() and int(k) <= target]
    if not prior:
        return None, False
    chosen = str(max(prior))
    return chosen, chosen != session_key


def build_known_entity_registry(
    campaign_id: str,
    session: int | str,
    *,
    corpus_root: Path | None = None,
    campaign_rel: str | None = None,
    party_ctx: PartyContext | None = None,
    include_npc_registry_aliases: bool = True,
) -> KnownEntityRegistry:
    root, rel = resolve_campaign_corpus(
        campaign_id,
        corpus_root=corpus_root,
        campaign_rel=campaign_rel,
    )
    registry = load_party_registry(root, rel)
    session_key = str(session).strip() if not isinstance(session, int) else str(session)
    if isinstance(session, bool):
        raise TypeError("session must not be a bool")

    roster_key, carried = resolve_roster_session_key(registry, session_key)
    if party_ctx is None:
        # Prefer exact/carry-forward session for party membership
        effective_session = int(roster_key) if roster_key and roster_key.isdigit() else session
        party_ctx = build_party_context_for_campaign(
            campaign_id,
            effective_session,
            corpus_root=root,
            campaign_rel=rel,
        )

    npc_aliases = (
        _load_npc_alias_map(root, rel) if include_npc_registry_aliases else {}
    )
    entities: list[KnownEntity] = []
    for member in party_ctx.members:
        extras = npc_aliases.get(member.slug, []) if member.kind == "companion" else []
        entities.append(_member_to_known_entity(member, extra_aliases=extras))

    registry_relpath = f"{rel}/{PARTY_REGISTRY_BASENAME}" if registry is not None else None
    warnings = list(party_ctx.warnings)
    if carried and roster_key:
        warnings.append(
            f"roster_carry_forward: session '{session_key}' using roster from '{roster_key}'"
        )

    return KnownEntityRegistry(
        campaign_id=str(party_ctx.campaign_id or campaign_id),
        session_key=session_key,
        roster_session_key=roster_key,
        roster_carry_forward=carried,
        registry_relpath=registry_relpath,
        entities=tuple(entities),
        warnings=tuple(warnings),
        diagnostics={
            "entity_count": len(entities),
            "pc_count": sum(1 for e in entities if e.kind == "pc"),
            "companion_count": sum(1 for e in entities if e.kind == "companion"),
            "npc_registry_alias_slugs": sorted(
                slug for slug in npc_aliases if any(e.slug == slug for e in entities)
            ),
        },
    )


# --------------------------------------------------------------------------- #
# World-graph-derived known entities (canonical-ID carry-forward)
# --------------------------------------------------------------------------- #

# Node kinds whose world-head entries may suppress session re-extraction by
# default: concrete, durable things. Threads/mysteries/events are excluded by
# default — a new session legitimately introduces new threads whose labels may
# rhyme with old ones, so suppressing on them needs an explicit opt-in.
WORLD_ENTITY_DEFAULT_KINDS: frozenset[str] = frozenset(
    {"npc", "location", "group", "faction", "item", "creature"}
)


def _world_match_terms(
    label: str,
    aliases: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    """Match terms from world-graph label + aliases only.

    Unlike party members, world node ids are not human slugs, so no slug-derived
    surfaces are synthesized (an id like ``loc_mireward_reach`` would only emit
    junk terms). The same unsafe-alias guard applies to graph aliases.
    """
    terms: list[tuple[str, str]] = []
    seen_norm: set[str] = set()

    def add(surface: str, method: str) -> None:
        cleaned = surface.strip()
        if not cleaned:
            return
        if method != "canonical" and is_unsafe_match_alias(cleaned):
            return
        key = normalize_match_surface(cleaned)
        if not key or key in seen_norm:
            return
        seen_norm.add(key)
        terms.append((cleaned, method))

    add(label, "canonical")
    for alias in aliases:
        add(alias, "alias")
    terms.sort(key=lambda item: len(normalize_match_surface(item[0])), reverse=True)
    return tuple(terms)


def known_entities_from_world_graph(
    graph: Mapping[str, Any],
    *,
    include_kinds: frozenset[str] | set[str] | None = WORLD_ENTITY_DEFAULT_KINDS,
    campaign_scopes: frozenset[str] | set[str] | None = None,
) -> list[KnownEntity]:
    """Convert world head-revision nodes into known-entity registry entries.

    ``canonical_entity_id`` is the world ``node_id`` verbatim, so deterministic
    mention matching, the prompt ledger, duplicate suppression, and evidence
    attachment all reference the canonical world identity directly.

    ``include_kinds`` filters on the node ``kind`` (``None`` = all kinds).
    ``campaign_scopes`` filters on ``state.campaign_scope`` (``None`` = all
    scopes; nodes with no scope are kept only when no filter is given).
    The graph-level ``aliases`` mapping (surface -> node_id) supplements each
    node's own ``aliases`` list.
    """
    raw_nodes = graph.get("nodes") if isinstance(graph, Mapping) else None
    if isinstance(raw_nodes, Mapping):
        node_rows = list(raw_nodes.values())
    elif isinstance(raw_nodes, Sequence):
        node_rows = list(raw_nodes)
    else:
        node_rows = []

    graph_aliases: dict[str, list[str]] = {}
    raw_aliases = graph.get("aliases") if isinstance(graph, Mapping) else None
    if isinstance(raw_aliases, Mapping):
        for surface, target in raw_aliases.items():
            if isinstance(target, str) and isinstance(surface, str):
                graph_aliases.setdefault(target, []).append(surface)

    entities: list[KnownEntity] = []
    for row in node_rows:
        if not isinstance(row, Mapping):
            continue
        node_id = str(row.get("node_id") or "").strip()
        label = str(row.get("label") or "").strip()
        if not node_id or not label:
            continue
        kind = str(row.get("kind") or row.get("role") or "").strip()
        if include_kinds is not None and kind not in include_kinds:
            continue
        state = row.get("state") if isinstance(row.get("state"), Mapping) else {}
        scope = str(state.get("campaign_scope") or "").strip()
        if campaign_scopes is not None and scope not in campaign_scopes:
            continue
        aliases: list[str] = []
        for a in row.get("aliases") or []:
            if isinstance(a, str) and a.strip():
                aliases.append(a)
        for a in graph_aliases.get(node_id, []):
            if a.strip():
                aliases.append(a)
        match_terms = _world_match_terms(label, aliases)
        if not match_terms:
            continue
        entities.append(
            KnownEntity(
                slug=node_id,
                kind=kind or "world_node",
                display_name=label,
                canonical_entity_id=node_id,
                aliases=tuple(a for a in aliases),
                hub_rel_path="",
                hub_resolved=False,
                corpus_ref={
                    "type": kind or "world_node",
                    "ref_id": node_id,
                    "resolution": "world_head",
                },
                match_terms=match_terms,
            )
        )
    return entities


def extend_known_entity_registry(
    base: KnownEntityRegistry,
    extras: Sequence[KnownEntity],
) -> KnownEntityRegistry:
    """Append extra known entities; base (party roster) wins id/slug collisions.

    Party anchors are the authoritative identity for PCs/companions, so an extra
    carrying the same slug or canonical id is dropped rather than merged.
    """
    seen_slugs = {e.slug for e in base.entities}
    seen_ids = {e.canonical_entity_id for e in base.entities}
    merged = list(base.entities)
    added = 0
    for entity in extras:
        if entity.slug in seen_slugs or entity.canonical_entity_id in seen_ids:
            continue
        seen_slugs.add(entity.slug)
        seen_ids.add(entity.canonical_entity_id)
        merged.append(entity)
        added += 1
    diagnostics = dict(base.diagnostics)
    diagnostics["extra_entities_offered"] = len(extras)
    diagnostics["extra_entities_added"] = added
    diagnostics["entity_count"] = len(merged)
    return KnownEntityRegistry(
        campaign_id=base.campaign_id,
        session_key=base.session_key,
        roster_session_key=base.roster_session_key,
        roster_carry_forward=base.roster_carry_forward,
        registry_relpath=base.registry_relpath,
        entities=tuple(merged),
        warnings=base.warnings,
        diagnostics=diagnostics,
    )
