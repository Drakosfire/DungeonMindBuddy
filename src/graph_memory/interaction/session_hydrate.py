"""Hydrate a GraphRetrievalSession from a wire/packet dict (host IPC)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from graph_memory.interaction.claims import GraphClaim
from graph_memory.interaction.session import (
    CoverageState,
    GraphReferent,
    GraphRetrievalSession,
    RetrievalOperationEvent,
    SessionSnapshot,
    SourceAnchorState,
    SourceReadEntry,
)
from graph_memory.interaction.session_store import create_session, replace_session


def hydrate_session_from_packet(packet: Mapping[str, Any]) -> GraphRetrievalSession:
    """Rebuild a local session from a Hermes host packet projection."""
    snapshot_raw = packet.get("snapshot") if isinstance(packet.get("snapshot"), Mapping) else {}
    snapshot = SessionSnapshot(
        world_id=str(snapshot_raw.get("world_id") or packet.get("world_id") or ""),
        campaign_id=str(snapshot_raw.get("campaign_id") or packet.get("campaign_id") or ""),
        focus=dict(snapshot_raw.get("focus") or packet.get("focus") or {"kind": "none", "session_id": None}),
        admissibility=str(snapshot_raw.get("admissibility") or packet.get("admissibility") or "gm"),
        revision_id=str(snapshot_raw.get("revision_id") or packet.get("revision_id") or ""),
        is_head=snapshot_raw.get("is_head") if isinstance(snapshot_raw.get("is_head"), bool) else None,
    )
    referents: list[GraphReferent] = []
    for item in packet.get("candidates") or packet.get("referents") or []:
        if not isinstance(item, Mapping):
            continue
        ref_id = str(item.get("id") or item.get("node_id") or "").strip()
        if not ref_id:
            continue
        referents.append(
            GraphReferent(
                kind=str(item.get("kind") or "node"),  # type: ignore[arg-type]
                id=ref_id,
                label=None if item.get("label") is None else str(item.get("label")),
                origin=str(item.get("origin") or "deterministic_match"),  # type: ignore[arg-type]
                match_reasons=[str(x) for x in (item.get("match_reasons") or [])],
                selected=bool(item.get("selected")),
            )
        )

    claims: list[GraphClaim] = []
    for item in packet.get("claim_ledger") or packet.get("claims") or []:
        if not isinstance(item, Mapping):
            continue
        claim_id = str(item.get("claim_id") or "").strip()
        if not claim_id:
            continue
        raw = dict(item)
        raw["claim_id"] = claim_id
        if not raw.get("revision_id"):
            raw["revision_id"] = snapshot.revision_id
        if not raw.get("authority_class"):
            raw["authority_class"] = "unknown"
        if not raw.get("claim_kind"):
            raw["claim_kind"] = "attribute"
        claims.append(GraphClaim.model_validate(raw))

    anchors: list[SourceAnchorState] = []
    for item in packet.get("source_anchors") or []:
        if not isinstance(item, Mapping):
            continue
        anchors.append(
            SourceAnchorState(
                anchor_id=str(item.get("anchor_id") or ""),
                readable=bool(item.get("readable")),
                opened=bool(item.get("opened")),
                locator_kind=(
                    None if item.get("locator_kind") is None else str(item.get("locator_kind"))
                ),
                supporting_claim_ids=[str(x) for x in (item.get("supporting_claim_ids") or [])],
            )
        )

    reads: list[SourceReadEntry] = []
    for item in packet.get("source_reads") or []:
        if not isinstance(item, Mapping):
            continue
        reads.append(SourceReadEntry.model_validate(dict(item)))

    operations: list[RetrievalOperationEvent] = []
    for item in packet.get("operations") or []:
        if not isinstance(item, Mapping):
            continue
        operations.append(RetrievalOperationEvent.model_validate(dict(item)))

    coverage_raw = packet.get("coverage") if isinstance(packet.get("coverage"), Mapping) else {}
    latest_recap_raw = packet.get("latest_recap_change")
    latest_recap_change = (
        dict(latest_recap_raw) if isinstance(latest_recap_raw, Mapping) else None
    )
    session = GraphRetrievalSession(
        id=str(packet.get("retrieval_session_id") or packet.get("id") or ""),
        snapshot=snapshot,
        question=str(packet.get("question") or ""),
        intent_hint=(
            None if packet.get("intent_hint") is None else str(packet.get("intent_hint"))
        ),
        referents=referents,
        operations=operations,
        claims=claims,
        source_anchors=[a for a in anchors if a.anchor_id],
        source_reads=reads,
        coverage=CoverageState(
            state=str(coverage_raw.get("state") or "unknown"),
            known=[str(x) for x in (coverage_raw.get("known") or [])],
            missing=[str(x) for x in (coverage_raw.get("missing") or [])],
            gap_codes=[str(x) for x in (coverage_raw.get("gap_codes") or [])],
        ),
        diagnostics=[str(x) for x in (packet.get("diagnostics") or [])],
        preflight_candidate_ids=[
            str(x) for x in (packet.get("preflight_candidate_ids") or [])
        ]
        or [ref.id for ref in referents],
        latest_recap_change=latest_recap_change,
    )
    if not session.id:
        raise ValueError("retrieval session packet missing id")
    # Prefer replace so repeated hydrations in the child overwrite cleanly.
    try:
        return replace_session(session)
    except Exception:
        return create_session(session)


__all__ = ["hydrate_session_from_packet"]
