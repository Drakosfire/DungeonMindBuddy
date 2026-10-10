"""Claim authority ledger for Hermes × World Graph interaction."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from graph_memory.interaction.schema_constants import GRAPH_CLAIM_SCHEMA

ClaimAuthorityClass = Literal[
    "governed_identity_decision",
    "gm_authored_accepted_assertion",
    "source_derived_accepted_assertion",
    "accepted_relationship",
    "accepted_explicit_attribute",
    "derived_summary",
    "inferred_relationship",
    "provisional_or_disputed",
    "generated_prep_suggestion",
    "unknown",
]

ClaimSupportState = Literal[
    "graph_accepted",
    "source_anchor_available",
    "source_anchor_unreadable",
    "source_opened",
    "source_integrity_failed",
    "source_graph_conflict",
    "inference_supported",
    "unsupported",
]

ClaimKind = Literal[
    "identity",
    "attribute",
    "source_observation",
    "relationship",
    "navigation_summary",
    "inference",
    "suggestion",
]

TurnOutcomeState = Literal[
    "graph_grounded",
    "source_verified",
    "partial_coverage",
    "inferred_from_graph",
    "conflicting_authority",
    "unsupported",
    "abstained",
    "execution_error",
    # No graph-retrieval tool was called this turn and no claims were already
    # accepted — Hermes answered from the visible conversation, not the graph.
    "conversation_context",
]


class ClaimSupport(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    state: ClaimSupportState = "unsupported"
    source_anchor_ids: list[str] = Field(default_factory=list)
    source_read_ids: list[str] = Field(default_factory=list)
    readable_anchor_ids: list[str] = Field(default_factory=list)
    unreadable_anchor_ids: list[str] = Field(default_factory=list)


class GraphClaim(BaseModel):
    """Explicit accepted (or disclosed) proposition usable as answer support."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_graph_claim_v1"] = Field(
        default=GRAPH_CLAIM_SCHEMA,
        alias="schema",
    )
    claim_id: str
    claim_kind: ClaimKind
    subject_node_id: str | None = None
    subject_label: str | None = None
    predicate: str | None = None
    object_node_id: str | None = None
    value_text: str | None = None
    epistemic_kind: str | None = None
    canon_state: str | None = None
    acceptance_state: str | None = None
    visibility: str | None = None
    campaign_scope: str | None = None
    revision_id: str
    authority_class: ClaimAuthorityClass
    support: ClaimSupport = Field(default_factory=ClaimSupport)
    used_in_answer: bool = False

    source_assertion_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    observation_kind: str | None = Field(default=None, exclude_if=lambda value: value is None)
    review_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    contribution_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    publication_revision_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    source_artifact_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    source_revision_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    evidence_ref_ids: list[str] = Field(default_factory=list, exclude_if=lambda value: not value)

    @model_validator(mode="after")
    def _require_reviewed_source_identity(self) -> GraphClaim:
        if self.claim_kind == "source_observation" and (
            self.authority_class != "source_derived_accepted_assertion"
            or self.observation_kind != "session_observation"
            or self.source_assertion_id != self.claim_id
            or not self.subject_node_id
            or not self.value_text
            or not self.review_id
            or not self.contribution_id
            or not self.publication_revision_id
            or not self.source_artifact_id
            or not self.source_revision_id
            or not self.evidence_ref_ids
        ):
            raise ValueError(
                "reviewed source observation needs exact review and evidence identity"
            )
        return self

    def may_state_as_campaign_fact(self) -> bool:
        return self.authority_class in {
            "governed_identity_decision",
            "gm_authored_accepted_assertion",
            "source_derived_accepted_assertion",
            "accepted_relationship",
            "accepted_explicit_attribute",
        }


def claims_to_dicts(claims: list[GraphClaim]) -> list[dict[str, Any]]:
    return [claim.model_dump(mode="json", by_alias=True) for claim in claims]


__all__ = [
    "ClaimAuthorityClass",
    "ClaimKind",
    "ClaimSupport",
    "ClaimSupportState",
    "GraphClaim",
    "TurnOutcomeState",
    "claims_to_dicts",
]
