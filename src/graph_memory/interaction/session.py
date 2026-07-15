"""Turn-scoped GraphRetrievalSession shared by panel and Hermes."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.interaction.claims import GraphClaim
from graph_memory.interaction.references import (
    GraphReference,
    InferenceReference,
    SourceCitation,
)
from graph_memory.interaction.schema_constants import GRAPH_RETRIEVAL_SESSION_SCHEMA

ReferentOrigin = Literal[
    "explicit_id",
    "ui_selection",
    "thread_pinned",
    "prior_resolved",
    "deterministic_match",
    "prose_lexical",
    "clarification",
]

OperationName = Literal[
    "resolve",
    "object",
    "neighborhood",
    "compare",
    "path",
    "timeline",
    "support",
    "coverage",
    "source_read",
    "search",
]

OperationStatus = Literal["started", "completed", "partial", "failed", "blocked"]
RequestedBy = Literal["server_initial", "hermes", "user_click"]


class SessionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    world_id: str
    campaign_id: str
    focus: dict[str, Any] = Field(default_factory=dict)
    admissibility: str = "gm"
    revision_id: str
    is_head: bool | None = None


class GraphReferent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    kind: Literal["node", "edge", "assertion"] = "node"
    id: str
    label: str | None = None
    origin: ReferentOrigin = "deterministic_match"
    match_reasons: list[str] = Field(default_factory=list)
    selected: bool = False


class SourceAnchorState(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    anchor_id: str
    readable: bool = False
    opened: bool = False
    locator_kind: str | None = None
    supporting_claim_ids: list[str] = Field(default_factory=list)


class SourceReadEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    source_read_id: str
    anchor_id: str
    outcome: str
    content_sha256: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    truncated: bool = False
    source_artifact_id: str | None = None


class RetrievalOperationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    operation_id: str
    requested_by: RequestedBy
    operation: OperationName
    inputs: dict[str, Any] = Field(default_factory=dict)
    status: OperationStatus
    added_claim_ids: list[str] = Field(default_factory=list)
    added_anchor_ids: list[str] = Field(default_factory=list)
    diagnostic_codes: list[str] = Field(default_factory=list)
    duration_ms: float | None = None


class CoverageState(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    state: str = "unknown"
    known: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    gap_codes: list[str] = Field(default_factory=list)


class GraphRetrievalSession(BaseModel):
    """Append-only retrieval session shared by UI and Hermes for one factual turn."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_graph_retrieval_session_v1"] = Field(
        default=GRAPH_RETRIEVAL_SESSION_SCHEMA,
        alias="schema",
    )
    id: str = Field(default_factory=lambda: f"grs:{uuid.uuid4().hex[:16]}")
    snapshot: SessionSnapshot
    question: str = ""
    intent_hint: str | None = None
    referents: list[GraphReferent] = Field(default_factory=list)
    operations: list[RetrievalOperationEvent] = Field(default_factory=list)
    claims: list[GraphClaim] = Field(default_factory=list)
    source_anchors: list[SourceAnchorState] = Field(default_factory=list)
    source_reads: list[SourceReadEntry] = Field(default_factory=list)
    inferences: list[InferenceReference] = Field(default_factory=list)
    graph_references: list[GraphReference] = Field(default_factory=list)
    source_citations: list[SourceCitation] = Field(default_factory=list)
    coverage: CoverageState = Field(default_factory=CoverageState)
    diagnostics: list[str] = Field(default_factory=list)
    preflight_candidate_ids: list[str] = Field(default_factory=list)
    # Server-owned S1 comparison metadata. Dict form keeps the interaction
    # package free of apps imports while surviving host IPC round-trips.
    latest_recap_change: dict[str, Any] | None = None

    def claim_by_id(self, claim_id: str) -> GraphClaim | None:
        for claim in self.claims:
            if claim.claim_id == claim_id:
                return claim
        return None

    def upsert_claims(self, claims: list[GraphClaim]) -> list[str]:
        existing = {claim.claim_id: index for index, claim in enumerate(self.claims)}
        added: list[str] = []
        for claim in claims:
            if claim.claim_id in existing:
                self.claims[existing[claim.claim_id]] = claim
            else:
                self.claims.append(claim)
                added.append(claim.claim_id)
        return added

    def selected_referent_ids(self) -> list[str]:
        return [ref.id for ref in self.referents if ref.selected]

    def project_for_panel(self) -> dict[str, Any]:
        factual = [c for c in self.claims if c.may_state_as_campaign_fact()]
        return {
            "schema": GRAPH_RETRIEVAL_SESSION_SCHEMA,
            "retrieval_session_id": self.id,
            "status": "ready" if self.preflight_candidate_ids or factual else "empty",
            "world_id": self.snapshot.world_id,
            "campaign_id": self.snapshot.campaign_id,
            "revision_id": self.snapshot.revision_id,
            "is_head": self.snapshot.is_head,
            "focus": dict(self.snapshot.focus),
            "admissibility": self.snapshot.admissibility,
            "query_text": self.question,
            "matched_node_ids": list(self.preflight_candidate_ids),
            "selected_referent_ids": self.selected_referent_ids(),
            "claims": [c.model_dump(mode="json", by_alias=True) for c in factual],
            "source_anchors": [
                a.model_dump(mode="json", by_alias=True) for a in self.source_anchors
            ],
            "source_reads": [
                r.model_dump(mode="json", by_alias=True) for r in self.source_reads
            ],
            "inferences": [
                i.model_dump(mode="json", by_alias=True) for i in self.inferences
            ],
            "coverage": self.coverage.model_dump(mode="json", by_alias=True),
            "diagnostics": list(self.diagnostics),
            "trust_boundary": {
                "graph_role": "canonical_accepted_claims_and_navigation",
                "citation_authority": "opened_source_reads",
                "graph_citations_permitted": True,
            },
            **(
                {"latest_recap_change": dict(self.latest_recap_change)}
                if isinstance(self.latest_recap_change, dict)
                else {}
            ),
        }

    def project_for_hermes(self) -> dict[str, Any]:
        packet: dict[str, Any] = {
            "schema": GRAPH_RETRIEVAL_SESSION_SCHEMA,
            "retrieval_session_id": self.id,
            "snapshot": self.snapshot.model_dump(mode="json", by_alias=True),
            "question": self.question,
            "intent_hint": self.intent_hint,
            "candidates": [
                ref.model_dump(mode="json", by_alias=True) for ref in self.referents
            ],
            "claim_ledger": [
                c.model_dump(mode="json", by_alias=True) for c in self.claims
            ],
            "source_anchors": [
                a.model_dump(mode="json", by_alias=True) for a in self.source_anchors
            ],
            "available_expansions": [
                "object",
                "neighborhood",
                "compare",
                "path",
                "timeline",
                "support",
                "coverage",
            ],
            "diagnostics": list(self.diagnostics),
        }
        if isinstance(self.latest_recap_change, dict):
            packet["latest_recap_change"] = dict(self.latest_recap_change)
        return packet


__all__ = [
    "CoverageState",
    "GraphReferent",
    "GraphRetrievalSession",
    "OperationName",
    "OperationStatus",
    "ReferentOrigin",
    "RequestedBy",
    "RetrievalOperationEvent",
    "SessionSnapshot",
    "SourceAnchorState",
    "SourceReadEntry",
]
