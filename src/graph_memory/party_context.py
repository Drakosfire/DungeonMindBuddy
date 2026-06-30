"""Deterministic party-context construction for graph-memory extraction.

The graph extractor needs **standing campaign context** — who is in the party
this session and which canonical entities they are tied to — so that recurring
party-side actors (PCs, companion NPCs like Thrin and Lysandra) are not "missed"
simply because a single recap does not re-introduce them. That gap is a
*context* problem, not a model failure: party membership is durable campaign
state that lives in the corpus, not something each recap restates.

This module builds that context **deterministically** (directory walk +
frontmatter parse, no LLM, no network):

* PCs and companion NPCs for ``(campaign, session)`` come from the campaign
  ``_party_registry.json`` (``party_registry_v1``): ``session_pc_rosters`` and
  the sibling ``session_companion_rosters`` added for non-PC travelling
  companions. This is the same registry the sentence-routing eval consumes via
  ``evals/sentence_routing_retrieval_falsification/session_roster.py``.
* Each member is resolved to its canonical hub (``<sub>/<slug>/README.md``),
  yielding a **resolved ``corpus_ref``** — the strongest identity key for
  ``identity_resolution.canonical_node_key`` and therefore the thing that makes
  a party member dedup-stable across sessions.
* "Related nodes" are harvested from the hub README's cross-links
  (``PCs/<slug>/`` / ``NPCs/<slug>/`` route fragments) as a deterministic
  adjacency seed.

Node-shape policy (see module-level note ``PARTY_NODE_SHAPE``): party members
are emitted as ordinary ``character`` nodes carrying a **resolved corpus_ref**.
They are *context anchors*, not session-novel extractions — the
"anchor vs. novel" distinction is expressed by membership in this context set
(keyed by hub_path via :func:`PartyContext.anchor_hub_paths`), **not** by a bespoke
node field, so the candidate-graph schema is unchanged and the comparator can
exclude anchors from node recall/precision denominators.

Discovery, not provision: this is task-agnostic standing context derived from
corpus-resident registry/frontmatter the model could itself read. It is the
mechanized form of discovery, not a per-request runbook pasted into a prompt.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.ingestion.frontmatter import split_frontmatter

PARTY_REGISTRY_SCHEMA = "party_registry_v1"
PARTY_REGISTRY_V2_SCHEMA = "party_registry_v2"
PARTY_REGISTRY_BASENAME = "_party_registry.json"
PARTY_REGISTRY_SCHEMAS = frozenset({PARTY_REGISTRY_SCHEMA, PARTY_REGISTRY_V2_SCHEMA})

# Dogfood defaults for the Longmont Campaign 2 graph-extraction experiments.
DEFAULT_CORPUS_ROOT = Path("corpus/eldyrwild-markdown")
DEFAULT_CAMPAIGN_REL = "Longmont Campaign/Campaign 2"

# campaign_id -> (corpus_root, campaign_rel under corpus root)
CAMPAIGN_CORPUS: dict[str, tuple[Path, str]] = {
    "longmont-c2": (DEFAULT_CORPUS_ROOT, DEFAULT_CAMPAIGN_REL),
    "longmont-c1": (DEFAULT_CORPUS_ROOT, "Longmont Campaign/Campaign 1"),
    "elderwyld": (DEFAULT_CORPUS_ROOT, "Elderwyld"),
}

# Party members are canonical hub entities. They appear in the candidate graph
# as ordinary ``character`` nodes with a resolved corpus_ref; the marker that
# they are pre-existing anchors (not new extractions) is set membership, not a
# node field. Keep this string in sync with the module docstring.
PARTY_NODE_SHAPE = "character"

_KIND_SUBDIR = {"pc": "PCs", "companion": "NPCs"}
_KIND_CORPUS_REF_TYPE = {"pc": "pc", "companion": "npc"}

_ROUTE_SLUG_RE = re.compile(r"/(?:PCs|NPCs)/([a-z0-9_]+)/")
_PLAYER_RE = re.compile(r"Player:\s*([^.\n\"]+)")
_TITLE_SPLIT_RE = re.compile(r"[—–(]")


@dataclass(frozen=True)
class PartyMember:
    slug: str
    kind: str  # "pc" | "companion"
    display_name: str
    corpus_ref_type: str  # "pc" | "npc"
    hub_rel_path: str  # corpus-root-relative "<...>/README.md"
    hub_resolved: bool
    player: str | None = None
    related_hub_slugs: tuple[str, ...] = ()

    def corpus_ref(self) -> dict[str, object]:
        """Resolved (or proposed) corpus_ref dict matching ``CorpusRef`` shape."""
        resolved = self.hub_resolved
        return {
            "type": self.corpus_ref_type,
            "ref_id": self.slug,
            "resolution": "resolved" if resolved else "proposed",
            "hub_path": self.hub_rel_path if resolved else None,
        }

    def seed_node(self) -> dict[str, object]:
        """Identity-bearing candidate-graph node stub for this party member.

        A lightweight context node (not a full ``CandidateGraphPreview`` node):
        it carries exactly the fields ``identity_resolution`` reads so the
        member dedup-matches its extracted counterpart by hub_path.
        """
        return {
            "node_id": f"node:{self.slug.replace('_', '-')}",
            "label": self.display_name,
            "node_type": PARTY_NODE_SHAPE,
            "corpus_ref": self.corpus_ref(),
        }


@dataclass(frozen=True)
class PartyContext:
    campaign_id: str | None
    session: str
    party_names: tuple[str, ...]
    members: tuple[PartyMember, ...]
    warnings: tuple[str, ...] = field(default=())

    def pcs(self) -> tuple[PartyMember, ...]:
        return tuple(m for m in self.members if m.kind == "pc")

    def companions(self) -> tuple[PartyMember, ...]:
        return tuple(m for m in self.members if m.kind == "companion")

    def seed_nodes(self) -> list[dict[str, object]]:
        return [m.seed_node() for m in self.members]

    def anchor_hub_paths(self) -> set[str]:
        """Resolved hub_paths of party members — the set a comparator uses to
        exclude standing party anchors from node recall/precision denominators."""
        return {m.hub_rel_path for m in self.members if m.hub_resolved}


def campaign_dir(corpus_root: Path, campaign_rel: str) -> Path:
    return corpus_root / campaign_rel


def party_registry_path(corpus_root: Path, campaign_rel: str) -> Path:
    return campaign_dir(corpus_root, campaign_rel) / PARTY_REGISTRY_BASENAME


def load_party_registry(corpus_root: Path, campaign_rel: str) -> dict | None:
    """Load and schema-check the campaign ``_party_registry.json`` (``None`` if absent/wrong)."""
    path = party_registry_path(corpus_root, campaign_rel)
    if not path.is_file():
        return None
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(blob, dict):
        return None
    schema = str(blob.get("schema") or "").strip()
    if schema and schema not in PARTY_REGISTRY_SCHEMAS:
        return None
    return blob


def resolve_campaign_corpus(
    campaign_id: str,
    *,
    corpus_root: Path | None = None,
    campaign_rel: str | None = None,
) -> tuple[Path, str]:
    """Resolve corpus root + campaign folder for a campaign_id."""
    if campaign_rel is not None:
        root = (corpus_root if corpus_root is not None else DEFAULT_CORPUS_ROOT).resolve()
        return root, campaign_rel
    entry = CAMPAIGN_CORPUS.get(campaign_id.strip())
    if entry is None:
        raise ValueError(f"unknown campaign_id for party registry: {campaign_id}")
    default_root, rel = entry
    root = (corpus_root if corpus_root is not None else default_root).resolve()
    return root, rel


def build_party_context_for_campaign(
    campaign_id: str,
    session: int | str,
    *,
    corpus_root: Path | None = None,
    campaign_rel: str | None = None,
) -> PartyContext:
    root, rel = resolve_campaign_corpus(
        campaign_id,
        corpus_root=corpus_root,
        campaign_rel=campaign_rel,
    )
    return build_party_context(session, corpus_root=root, campaign_rel=rel)


def _session_key(session: int | str) -> str:
    if isinstance(session, bool):  # guard: bool is an int subclass
        raise TypeError("session must not be a bool")
    if isinstance(session, int):
        return str(session)
    return str(session).strip()


def _roster_slugs(registry: dict, key: str, session_key: str) -> list[str]:
    raw = registry.get(key)
    if not isinstance(raw, dict):
        return []
    entry = raw.get(session_key)
    if not isinstance(entry, list):
        return []
    return [str(x).strip() for x in entry if str(x).strip()]


def _read_frontmatter_and_body(path: Path) -> tuple[str | None, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, ""
    return split_frontmatter(text)


def _frontmatter_title(block: str | None) -> str | None:
    if not block:
        return None
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("title:"):
            raw = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            return raw or None
    return None


def _display_name_from_title(title: str | None, slug: str) -> str:
    if title:
        head = _TITLE_SPLIT_RE.split(title, 1)[0].strip()
        if head:
            return head
    return slug.replace("_", " ").title()


def _player_from_block(block: str | None) -> str | None:
    if not block:
        return None
    m = _PLAYER_RE.search(block)
    return m.group(1).strip() if m else None


def _related_hub_slugs(body: str, self_slug: str) -> tuple[str, ...]:
    seen: list[str] = []
    for slug in _ROUTE_SLUG_RE.findall(body or ""):
        if slug == self_slug or slug in seen:
            continue
        seen.append(slug)
    return tuple(seen)


def _resolve_member(corpus_root: Path, campaign_rel: str, slug: str, kind: str) -> PartyMember:
    subdir = _KIND_SUBDIR[kind]
    hub_rel = f"{campaign_rel}/{subdir}/{slug}/README.md"
    readme = corpus_root / hub_rel
    resolved = readme.is_file()
    block, body = _read_frontmatter_and_body(readme) if resolved else (None, "")
    display = _display_name_from_title(_frontmatter_title(block), slug)
    player = _player_from_block(block) if kind == "pc" else None
    return PartyMember(
        slug=slug,
        kind=kind,
        display_name=display,
        corpus_ref_type=_KIND_CORPUS_REF_TYPE[kind],
        hub_rel_path=hub_rel,
        hub_resolved=resolved,
        player=player,
        related_hub_slugs=_related_hub_slugs(body, slug),
    )


def build_party_context(
    session: int | str,
    *,
    corpus_root: Path = DEFAULT_CORPUS_ROOT,
    campaign_rel: str = DEFAULT_CAMPAIGN_REL,
) -> PartyContext:
    """Deterministic party context for ``session`` from the campaign registry + hubs."""
    session_key = _session_key(session)
    registry = load_party_registry(corpus_root, campaign_rel)
    warnings: list[str] = []
    if registry is None:
        warnings.append(f"no {PARTY_REGISTRY_BASENAME} for campaign '{campaign_rel}'")
        registry = {}

    campaign_id = registry.get("campaign_id")
    party_names = tuple(str(n) for n in (registry.get("pc_party_names") or []) if str(n).strip())

    pc_slugs = _roster_slugs(registry, "session_pc_rosters", session_key)
    companion_slugs = _roster_slugs(registry, "session_companion_rosters", session_key)
    if str(registry.get("schema") or "") == PARTY_REGISTRY_V2_SCHEMA:
        roster = (registry.get("session_rosters") or {}).get(session_key, {})
        if isinstance(roster, dict):
            if not pc_slugs and isinstance(roster.get("pcs"), list):
                pc_slugs = [str(x).strip() for x in roster["pcs"] if str(x).strip()]
            if not companion_slugs and isinstance(roster.get("companions"), list):
                companion_slugs = [str(x).strip() for x in roster["companions"] if str(x).strip()]
    if not pc_slugs:
        warnings.append(f"no session_pc_rosters['{session_key}'] entry")

    members: list[PartyMember] = []
    for slug in pc_slugs:
        members.append(_resolve_member(corpus_root, campaign_rel, slug, "pc"))
    for slug in companion_slugs:
        members.append(_resolve_member(corpus_root, campaign_rel, slug, "companion"))

    for m in members:
        if not m.hub_resolved:
            warnings.append(f"unresolved hub for {m.kind} '{m.slug}': {m.hub_rel_path}")

    return PartyContext(
        campaign_id=str(campaign_id) if campaign_id is not None else None,
        session=session_key,
        party_names=party_names,
        members=tuple(members),
        warnings=tuple(warnings),
    )
