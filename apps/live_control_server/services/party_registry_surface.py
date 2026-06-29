"""Party Registry read surface for /plan toolbox."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.graph_memory.party_context import (
    build_party_context_for_campaign,
    load_party_registry,
    resolve_campaign_corpus,
)
from src.graph_memory.session_graph_context import (
    SESSION_GRAPH_CONTEXT_SCHEMA,
    build_session_graph_context,
    normalize_registry_view,
)
from src.live_play.recap_stage_paths import corpus_root


PARTY_REGISTRY_SURFACE_SCHEMA = "dmb_party_registry_surface_v1"


class PartyRegistryMemberRow(BaseModel):
    slug: str
    kind: str
    display_name: str
    hub_rel_path: str
    hub_resolved: bool
    player: str | None = None
    corpus_ref: dict[str, Any] = Field(default_factory=dict)


class PartyRegistrySurfaceResponse(BaseModel):
    schema_version: str = PARTY_REGISTRY_SURFACE_SCHEMA
    campaign_id: str
    session: int
    session_id: str
    registry_schema: str | None = None
    registry_relpath: str | None = None
    party_names: list[str] = Field(default_factory=list)
    pc_slugs: list[str] = Field(default_factory=list)
    companion_slugs: list[str] = Field(default_factory=list)
    notable_npc_slugs: list[str] = Field(default_factory=list)
    members: list[PartyRegistryMemberRow] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    registry_summary: dict[str, Any] = Field(default_factory=dict)
    session_graph_context: dict[str, Any] = Field(default_factory=dict)
    available_session_keys: list[str] = Field(default_factory=list)
    has_session_roster: bool = False
    known_pc_slugs: list[str] = Field(default_factory=list)
    known_companion_slugs: list[str] = Field(default_factory=list)


def build_party_registry_surface(
    *,
    campaign_id: str,
    session: int,
) -> PartyRegistrySurfaceResponse:
    root, rel = resolve_campaign_corpus(campaign_id, corpus_root=corpus_root())
    registry = load_party_registry(root, rel)
    registry_view = normalize_registry_view(registry)
    party_ctx = build_party_context_for_campaign(
        campaign_id,
        session,
        corpus_root=root,
        campaign_rel=rel,
    )
    session_ctx = build_session_graph_context(
        campaign_id,
        session,
        corpus_root=root,
        campaign_rel=rel,
    )
    session_key = party_ctx.session
    roster = registry_view.get("session_rosters", {}).get(session_key, {})
    pc_slugs = list(roster.get("pcs") or [])
    companion_slugs = list(roster.get("companions") or [])
    if not pc_slugs:
        pc_slugs = [m.slug for m in party_ctx.pcs()]
    if not companion_slugs:
        companion_slugs = [m.slug for m in party_ctx.companions()]

    members = [
        PartyRegistryMemberRow(
            slug=m.slug,
            kind=m.kind,
            display_name=m.display_name,
            hub_rel_path=m.hub_rel_path,
            hub_resolved=m.hub_resolved,
            player=m.player,
            corpus_ref=m.corpus_ref(),
        )
        for m in party_ctx.members
    ]

    available_sessions = sorted(
        registry_view.get("session_rosters", {}).keys(),
        key=lambda k: int(k) if str(k).isdigit() else 0,
    )
    session_rosters = registry_view.get("session_rosters", {})
    has_session_roster = session_key in session_rosters and bool(
        (session_rosters.get(session_key) or {}).get("pcs")
        or (session_rosters.get(session_key) or {}).get("companions")
    )
    known_pc_slugs: set[str] = set()
    known_companion_slugs: set[str] = set()
    for roster in session_rosters.values():
        if isinstance(roster, dict):
            known_pc_slugs.update(str(s) for s in (roster.get("pcs") or []) if str(s).strip())
            known_companion_slugs.update(
                str(s) for s in (roster.get("companions") or []) if str(s).strip()
            )

    return PartyRegistrySurfaceResponse(
        campaign_id=campaign_id,
        session=session,
        session_id=session_ctx.session_id,
        registry_schema=session_ctx.registry_schema,
        registry_relpath=session_ctx.registry_relpath,
        party_names=list(party_ctx.party_names),
        pc_slugs=pc_slugs,
        companion_slugs=companion_slugs,
        notable_npc_slugs=list(session_ctx.notable_npc_slugs),
        members=members,
        warnings=list(party_ctx.warnings),
        registry_summary=registry_view,
        session_graph_context=session_ctx.to_dict(),
        available_session_keys=available_sessions,
        has_session_roster=has_session_roster,
        known_pc_slugs=sorted(known_pc_slugs),
        known_companion_slugs=sorted(known_companion_slugs),
    )
