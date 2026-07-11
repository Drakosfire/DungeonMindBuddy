"""Typed Graph Kernel identity models (PR004)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IdentityResolutionOutcome = Literal[
    "resolved_existing",
    "created_new",
    "provisional_new",
    "ambiguous",
    "blocked_collision",
    "rejected",
    "human_override",
]

IdentityDecisionKind = Literal[
    "alias_add",
    "alias_remove",
    "merge",
    "split",
    "unmerge",
    "reject_candidate",
    "mark_ambiguous",
    "human_override",
]

IdentityCanonState = Literal[
    "canonical",
    "noncanonical_provisional",
    "merged_away",
    "split_from",
    "rejected",
]


class _IdentityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class IdentityCandidate(_IdentityModel):
    world_id: str
    candidate_id: str
    label: str
    object_kind: str
    aliases: list[str] = Field(default_factory=list)
    evidence_ref_ids: list[str] = Field(default_factory=list)
    campaign_scope: str | None = None
    source_artifact_id: str | None = None
    proposed_node_id: str | None = None
    confidence: float | None = None


class IdentityResolution(_IdentityModel):
    world_id: str
    candidate_id: str
    outcome: IdentityResolutionOutcome
    target_node_id: str | None = None
    created_node_id: str | None = None
    provisional_node_id: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    canon_state: IdentityCanonState | None = None
    decision_id: str | None = None


class IdentityAliasMapRewrite(_IdentityModel):
    """One alias-map key rewrite performed during merge (for replayable unmerge)."""

    alias_key: str
    prior_owner_node_id: str | None
    new_owner_node_id: str


class IdentityMergeSideEffects(_IdentityModel):
    """Merge delta required to reverse identity/alias state on unmerge."""

    aliases_added_to_target: list[str] = Field(default_factory=list)
    evidence_ref_ids_added_to_target: list[str] = Field(default_factory=list)
    source_domains_added_to_target: list[str] = Field(default_factory=list)
    alias_map_rewrites: list[IdentityAliasMapRewrite] = Field(default_factory=list)


class IdentityDecisionRecord(_IdentityModel):
    decision_id: str
    world_id: str
    decision_kind: IdentityDecisionKind
    created_at: str
    actor: str
    reason: str
    source_candidate_id: str | None = None
    subject_node_id: str | None = None
    target_node_id: str | None = None
    affected_node_ids: list[str] = Field(default_factory=list)
    alias: str | None = None
    reversible: bool = True
    supersedes_decision_ids: list[str] = Field(default_factory=list)
    status: Literal["active", "superseded", "retracted"] = "active"
    merge_side_effects: IdentityMergeSideEffects | None = None
