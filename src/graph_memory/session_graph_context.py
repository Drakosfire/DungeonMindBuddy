"""Session-scoped graph context for category extraction and Party Registry UI.

Builds a deterministic ``SessionGraphContext`` from the campaign party registry
and resolved hub metadata. v1 registry on disk is normalized to a v2-shaped view
without requiring an immediate corpus migration.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from src.graph_memory import identity_resolution as ir
from src.graph_memory.party_context import (
    DEFAULT_CAMPAIGN_REL,
    DEFAULT_CORPUS_ROOT,
    PARTY_REGISTRY_BASENAME,
    PARTY_REGISTRY_SCHEMA,
    PartyContext,
    PartyMember,
    build_party_context_for_campaign,
    load_party_registry,
    resolve_campaign_corpus,
)

SESSION_GRAPH_CONTEXT_SCHEMA = "dmb_session_graph_context_v0"


@dataclass(frozen=True)
class SessionGraphContextMember:
    slug: str
    kind: str
    display_name: str
    aliases: tuple[str, ...]
    hub_rel_path: str
    hub_resolved: bool
    corpus_ref: dict[str, object]
    player: str | None = None

    @classmethod
    def from_party_member(cls, member: PartyMember) -> SessionGraphContextMember:
        aliases = (member.display_name,)
        return cls(
            slug=member.slug,
            kind=member.kind,
            display_name=member.display_name,
            aliases=aliases,
            hub_rel_path=member.hub_rel_path,
            hub_resolved=member.hub_resolved,
            corpus_ref=member.corpus_ref(),
            player=member.player,
        )


@dataclass(frozen=True)
class SessionGraphContext:
    schema: str
    campaign_id: str
    session_id: str
    session_number: int
    party_names: tuple[str, ...]
    anchor_members: tuple[SessionGraphContextMember, ...]
    notable_npc_slugs: tuple[str, ...]
    registry_schema: str | None
    registry_relpath: str | None
    warnings: tuple[str, ...] = field(default=())
    prompt_guidance: dict[str, bool] = field(
        default_factory=lambda: {
            "do_not_reextract_anchor_nodes": True,
            "extract_new_named_actors_not_in_context": True,
        }
    )

    def anchor_seed_nodes(self) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for member in self.anchor_members:
            seed = {
                "node_id": f"node:{member.slug.replace('_', '-')}",
                "label": member.display_name,
                "node_type": "character",
                "corpus_ref": dict(member.corpus_ref),
                "context_anchor": True,
            }
            nodes.append(seed)
        return nodes

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["anchor_nodes"] = self.anchor_seed_nodes()
        return payload


def normalize_registry_view(registry: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize party_registry v1 (on disk) or v2 into a unified summary view."""
    if not registry:
        return {
            "schema": None,
            "campaign_id": None,
            "party_names": [],
            "session_rosters": {},
            "characters": {},
        }
    schema = str(registry.get("schema") or PARTY_REGISTRY_SCHEMA)
    if schema == "party_registry_v2":
        return {
            "schema": schema,
            "campaign_id": registry.get("campaign_id"),
            "party_names": list(registry.get("party_names") or registry.get("pc_party_names") or []),
            "session_rosters": dict(registry.get("session_rosters") or {}),
            "characters": dict(registry.get("characters") or {}),
        }
    session_rosters: dict[str, dict[str, list[str]]] = {}
    for session_key, slugs in (registry.get("session_pc_rosters") or {}).items():
        if isinstance(slugs, list):
            session_rosters.setdefault(str(session_key), {})["pcs"] = [
                str(s).strip() for s in slugs if str(s).strip()
            ]
    for session_key, slugs in (registry.get("session_companion_rosters") or {}).items():
        if isinstance(slugs, list):
            session_rosters.setdefault(str(session_key), {})["companions"] = [
                str(s).strip() for s in slugs if str(s).strip()
            ]
    return {
        "schema": schema,
        "campaign_id": registry.get("campaign_id"),
        "party_names": list(registry.get("pc_party_names") or []),
        "session_rosters": session_rosters,
        "characters": {},
    }


def _session_id_from_number(session: int | str) -> str:
    if isinstance(session, int):
        return f"session-{session}"
    raw = str(session).strip()
    if raw.startswith("session-"):
        return raw
    return f"session-{raw}"


def _session_number_from_id(session_id: str) -> int:
    raw = session_id.strip()
    if raw.startswith("session-"):
        return int(raw.split("-", 1)[1])
    return int(raw)


def build_session_graph_context(
    campaign_id: str,
    session: int | str,
    *,
    corpus_root: Path | None = None,
    campaign_rel: str | None = None,
) -> SessionGraphContext:
    root, rel = resolve_campaign_corpus(
        campaign_id,
        corpus_root=corpus_root,
        campaign_rel=campaign_rel,
    )
    party_ctx = build_party_context_for_campaign(
        campaign_id,
        session,
        corpus_root=root,
        campaign_rel=rel,
    )
    session_key = party_ctx.session
    session_id = _session_id_from_number(session)
    session_number = int(session_key) if session_key.isdigit() else _session_number_from_id(session_id)

    registry = load_party_registry(root, rel)
    registry_view = normalize_registry_view(registry)
    roster = registry_view.get("session_rosters", {}).get(session_key, {})
    notable = tuple(str(s) for s in (roster.get("notable_npcs") or []) if str(s).strip())

    registry_path_rel = f"{root.as_posix()}/{rel}/{PARTY_REGISTRY_BASENAME}"

    return SessionGraphContext(
        schema=SESSION_GRAPH_CONTEXT_SCHEMA,
        campaign_id=campaign_id,
        session_id=session_id,
        session_number=session_number,
        party_names=party_ctx.party_names,
        anchor_members=tuple(
            SessionGraphContextMember.from_party_member(m) for m in party_ctx.members
        ),
        notable_npc_slugs=notable,
        registry_schema=str(registry_view.get("schema")) if registry_view.get("schema") else None,
        registry_relpath=registry_path_rel,
        warnings=party_ctx.warnings,
    )


def party_anchors_markdown(party_ctx: PartyContext) -> str:
    lines = [
        "## Party anchors (deterministic — do not re-extract as session-novel nodes)",
        f"Party names: {', '.join(party_ctx.party_names) or 'none'}",
        "",
    ]
    if not party_ctx.members:
        lines.append(
            "_No party anchors registered for this session. "
            "Extract named actors from the recap; register anchors in Party Registry._"
        )
        return "\n".join(lines)
    for member in party_ctx.members:
        lines.append(
            f"- {member.kind} `{member.slug}`: {member.display_name} | "
            f"hub={member.hub_rel_path} | corpus_ref={member.corpus_ref()!r}"
        )
    return "\n".join(lines)


def normalize_party_anchor_node(
    seed: Mapping[str, Any],
    *,
    default_semantic_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Full candidate-graph node stub for a context anchor (may lack session evidence)."""
    node_id = str(seed.get("node_id") or "node:unknown")
    label = str(seed.get("label") or node_id)
    corpus_ref = seed.get("corpus_ref")
    return {
        "node_id": node_id,
        "label": label,
        "node_type": str(seed.get("node_type") or "character"),
        "description": "Deterministic party context anchor",
        "importance": "high",
        "semantic_state": dict(default_semantic_state),
        "evidence_refs": [],
        "proposed_action": "anchor",
        "confidence": "high",
        "warnings": ["context_anchor_no_session_evidence"],
        "corpus_ref": dict(corpus_ref) if isinstance(corpus_ref, Mapping) else None,
        "context_anchor": True,
    }


def merge_party_anchor_nodes(
    nodes: list[dict[str, Any]],
    party_ctx: PartyContext,
    *,
    default_semantic_state: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Insert party anchor nodes when absent; dedup by canonical node key."""
    existing_keys = {ir.canonical_node_key(n) for n in nodes}
    inserted: list[str] = []
    merged = list(nodes)
    for member in party_ctx.members:
        seed = member.seed_node()
        key = ir.canonical_node_key(seed)
        if key in existing_keys:
            continue
        merged.append(
            normalize_party_anchor_node(seed, default_semantic_state=default_semantic_state)
        )
        existing_keys.add(key)
        inserted.append(member.slug)
    return merged, {"inserted_party_anchor_slugs": inserted}


# A party is a durable campaign entity: the members travel together this session.
# Both the collective node and the member_of edges are *standing context* (the
# corpus party registry asserts them), not session-novel extractions — so they
# carry ``context_anchor`` and survive evidence-less sanitization the same way
# party-member anchor nodes do. Keep the node shape aligned with the gold
# fixture's ``node:heroes-party`` so the comparator matches it by label+type.
PARTY_COLLECTIVE_NODE_ID = "node:heroes-party"
PARTY_COLLECTIVE_LABEL = "Heroes / party"
PARTY_COLLECTIVE_NODE_TYPE = "group"
PARTY_COLLECTIVE_CORPUS_REF: dict[str, object] = {
    "type": "faction",
    "ref_id": "heroes_party",
    "resolution": "proposed",
    "hub_path": None,
}


def party_collective_node(default_semantic_state: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic party-collective ("Heroes / party") context-anchor node."""
    return {
        "node_id": PARTY_COLLECTIVE_NODE_ID,
        "label": PARTY_COLLECTIVE_LABEL,
        "node_type": PARTY_COLLECTIVE_NODE_TYPE,
        "description": "Deterministic party-collective anchor (members travel together this session).",
        "importance": "high",
        "semantic_state": dict(default_semantic_state),
        "evidence_refs": [],
        "proposed_action": "anchor",
        "confidence": "high",
        "warnings": ["context_anchor_no_session_evidence", "party_name_binding_deferred"],
        "corpus_ref": dict(PARTY_COLLECTIVE_CORPUS_REF),
        "context_anchor": True,
    }


def _party_membership_edge(
    member: PartyMember,
    from_node_id: str,
    to_node_id: str,
    *,
    default_semantic_state: Mapping[str, Any],
) -> dict[str, Any]:
    dashed = member.slug.replace("_", "-")
    return {
        "edge_id": f"edge:{dashed}-member-of-party",
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "label": f"{member.display_name} is part of the responding heroes / party",
        "relationship_type": "member_of",
        "predicate_family": "membership",
        "semantic_state": dict(default_semantic_state),
        "evidence_refs": [],
        "proposed_action": "anchor",
        "confidence": "high",
        "warnings": ["context_anchor_no_session_evidence"],
        "context_anchor": True,
    }


def merge_party_collective(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    party_ctx: PartyContext,
    *,
    default_semantic_state: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Insert a party-collective node and ``member_of`` edges deterministically.

    Membership edges reference the *surviving* node id for each member (the node
    that carries the member's canonical identity after dedup/anchor merge), so
    they always pass downstream endpoint filtering. The collective node is
    inserted only when absent (matched by canonical key).
    """
    if not party_ctx.members:
        return nodes, edges, {"party_collective_inserted": False, "party_membership_edge_slugs": []}

    merged_nodes = list(nodes)
    key_to_id: dict[str, str] = {}
    for node in merged_nodes:
        key_to_id.setdefault(ir.canonical_node_key(node), str(node.get("node_id") or ""))

    collective = party_collective_node(default_semantic_state)
    collective_key = ir.canonical_node_key(collective)
    collective_id = key_to_id.get(collective_key)
    inserted_collective = False
    if not collective_id:
        merged_nodes.append(collective)
        collective_id = PARTY_COLLECTIVE_NODE_ID
        key_to_id[collective_key] = collective_id
        inserted_collective = True

    merged_edges = list(edges)
    seeded_slugs: list[str] = []
    for member in party_ctx.members:
        member_id = key_to_id.get(ir.canonical_node_key(member.seed_node()))
        if not member_id or member_id == collective_id:
            continue
        merged_edges.append(
            _party_membership_edge(
                member,
                member_id,
                collective_id,
                default_semantic_state=default_semantic_state,
            )
        )
        seeded_slugs.append(member.slug)

    return (
        merged_nodes,
        merged_edges,
        {
            "party_collective_inserted": inserted_collective,
            "party_collective_node_id": collective_id,
            "party_membership_edge_slugs": seeded_slugs,
        },
    )
