"""Models for Kernel world initialization (PR006D1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WorldInitializationState = Literal[
    "ready",
    "active",
    "active_head_advanced",
    "blocked_existing_world",
    "inconsistent_lineage",
    "error",
]

PLAN_SCHEMA = "dmb_world_initialization_plan_v1"
RECEIPT_SCHEMA = "dmb_world_initialization_receipt_v1"


class _WorldInitModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class WorldInitializationApprovalAttestation(_WorldInitModel):
    """Caller-attested approval metadata.

    The Kernel records these fields on the receipt after verifying that the
    contribution list is structurally bound to the plan. It does **not**
    independently load or hash an on-disk bundle to re-prove the digest.
    """

    bundle_id: str
    bundle_digest: str
    approved_bundle_merge_sha: str


class WorldInitializationPlan(_WorldInitModel):
    """Validated initialization plan bound to an ordered contribution ID list."""

    schema_: str = Field(alias="schema")
    world_id: str
    campaign_id: str
    focus_session_id: str
    ordered_contribution_ids: list[str]
    approval_attestation: WorldInitializationApprovalAttestation

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class WorldInitializationReceipt(_WorldInitModel):
    schema_: str = Field(alias="schema")
    world_id: str
    campaign_id: str
    actor: str
    baseline_revision_id: str
    initial_head_revision_id: str
    ordered_contribution_ids: list[str]
    identity_decision_ids: list[str] = Field(default_factory=list)
    node_count: int
    edge_count: int
    accepted_assertion_count: int
    assertion_support_count: int
    evidence_count: int
    source_artifact_count: int
    source_domains: list[str]
    rebuild_equivalent: bool
    world_integrity_ok: bool
    contribution_integrity_ok: bool
    plan_binding_verified: bool
    approval_attestation: WorldInitializationApprovalAttestation
    created_at: str

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class WorldInitializationResult(_WorldInitModel):
    published: bool
    state: WorldInitializationState
    baseline_revision_id: str | None
    initial_head_revision_id: str | None
    current_head_revision_id: str | None
    receipt: WorldInitializationReceipt | None
    diagnostics: list[str] = Field(default_factory=list)


class WorldInitializationError(RuntimeError):
    """Fail-closed initialization error."""

    def __init__(
        self,
        message: str,
        *,
        state: WorldInitializationState = "error",
        diagnostics: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.state = state
        self.diagnostics = list(diagnostics or [])
