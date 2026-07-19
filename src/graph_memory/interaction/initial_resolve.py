"""Create a GraphRetrievalSession from deterministic preflight / retrieval packets."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from graph_memory.interaction.authority_classifier import claims_from_preflight_envelope
from graph_memory.interaction.session import (
    CoverageState,
    GraphReferent,
    GraphRetrievalSession,
    RetrievalOperationEvent,
    SessionSnapshot,
)
from graph_memory.interaction.session_store import create_session


def _focus_dict(focus: Any) -> dict[str, Any]:
    if not isinstance(focus, Mapping):
        return {"kind": "none", "session_id": None, "campaign_id": None}
    kind = str(focus.get("kind") or "none")
    session_id = focus.get("session_id", focus.get("sessionId"))
    campaign_id = focus.get("campaign_id", focus.get("campaignId"))
    return {
        "kind": kind,
        "session_id": None if session_id is None else str(session_id),
        "campaign_id": None if campaign_id is None else str(campaign_id),
    }


def _infer_intent_hint(question: str) -> str:
    text = question.strip().lower()
    if "what changed" in text and "recap" in text:
        return "compare"
    if any(token in text for token in ("last session", "previous session", "happened")):
        return "timeline"
    if "compare" in text:
        return "compare"
    if "connected" in text or "connection" in text:
        return "explore"
    if "exact source" in text or "quote" in text:
        return "support"
    if text.startswith("what do we know") or "who is" in text:
        return "lookup"
    return "identify"


def create_session_from_preflight(
    envelope: Mapping[str, Any],
    *,
    question: str,
    explicit_referents: Sequence[Mapping[str, Any]] | None = None,
) -> GraphRetrievalSession:
    """Build and register one shared retrieval session from the preflight envelope."""
    revision_id = str(envelope.get("revision_id") or "").strip()
    if not revision_id:
        raise ValueError("preflight envelope requires revision_id")

    matched = [str(x) for x in (envelope.get("matched_node_ids") or []) if str(x).strip()]
    nodes_by_id = {
        str(node.get("node_id")): node
        for node in (envelope.get("nodes") or [])
        if isinstance(node, Mapping) and node.get("node_id")
    }

    referents: list[GraphReferent] = []
    for item in explicit_referents or []:
        if not isinstance(item, Mapping):
            continue
        ref_id = str(item.get("id") or "").strip()
        if not ref_id:
            continue
        referents.append(
            GraphReferent(
                kind=str(item.get("kind") or "node"),  # type: ignore[arg-type]
                id=ref_id,
                label=None if item.get("label") is None else str(item.get("label")),
                origin=str(item.get("origin") or "explicit_id"),  # type: ignore[arg-type]
                selected=True,
            )
        )

    for node_id in matched:
        node = nodes_by_id.get(node_id) or {}
        already = any(ref.id == node_id for ref in referents)
        if already:
            continue
        referents.append(
            GraphReferent(
                kind="node",
                id=node_id,
                label=None if node.get("label") is None else str(node.get("label")),
                origin="deterministic_match",
                match_reasons=["preflight_match"],
                selected=len(matched) == 1,
            )
        )

    claims = claims_from_preflight_envelope(envelope)
    latest_recap_raw = envelope.get("latest_recap_change")
    latest_recap_change = (
        dict(latest_recap_raw) if isinstance(latest_recap_raw, Mapping) else None
    )
    gap_codes: list[str] = []
    missing: list[str] = []
    coverage_state = (
        "partial_coverage" if matched and not claims else ("ready" if claims else "empty")
    )
    if latest_recap_change is not None:
        for code in latest_recap_change.get("diagnostic_codes") or []:
            text = str(code).strip()
            if text:
                gap_codes.append(text)
        if bool(latest_recap_change.get("memory_lag")):
            missing.append("latest_recap_in_graph_head")
            coverage_state = "partial_coverage"
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id=str(envelope.get("world_id") or ""),
            campaign_id=str(envelope.get("campaign_id") or ""),
            focus=_focus_dict(envelope.get("focus")),
            admissibility=str(envelope.get("admissibility") or "gm"),
            revision_id=revision_id,
            is_head=envelope.get("is_head") if isinstance(envelope.get("is_head"), bool) else None,
            scope_mode=str(envelope.get("scope_mode") or "campaign"),  # type: ignore[arg-type]
        ),
        question=question,
        intent_hint=_infer_intent_hint(question),
        referents=referents,
        claims=claims,
        preflight_candidate_ids=matched,
        coverage=CoverageState(
            state=coverage_state,
            known=[c.predicate or c.claim_kind for c in claims if c.may_state_as_campaign_fact()],
            missing=missing,
            gap_codes=gap_codes,
        ),
        diagnostics=[
            str(code)
            for code in (envelope.get("warning_codes") or [])
            if str(code).strip()
        ],
        latest_recap_change=latest_recap_change,
    )
    session.operations.append(
        RetrievalOperationEvent(
            operation_id=f"op:{uuid.uuid4().hex[:12]}",
            requested_by="server_initial",
            operation="resolve",
            inputs={"matched_node_ids": matched},
            status="completed" if matched else "partial",
            added_claim_ids=[c.claim_id for c in claims],
            diagnostic_codes=list(session.diagnostics),
        )
    )
    return create_session(session)


__all__ = [
    "create_session_from_preflight",
]
