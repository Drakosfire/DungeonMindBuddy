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
    contribution list and complete payload digests are bound to the plan. It
    does **not** independently load or hash an on-disk bundle to re-prove the
    attested bundle digest.
    """

    bundle_id: str
    bundle_digest: str
    approved_bundle_merge_sha: str


class WorldInitializationContribution(_WorldInitModel):
    """One ordered contribution plus its complete canonical payload digest."""

    contribution_id: str
    payload_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class WorldInitializationPlan(_WorldInitModel):
    """Validated initialization plan bound to contribution contents."""

    schema_: Literal["dmb_world_initialization_plan_v1"] = Field(alias="schema")
    world_id: str
    campaign_id: str
    focus_session_id: str
    ordered_contributions: list[WorldInitializationContribution]
    approval_attestation: WorldInitializationApprovalAttestation

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)

    @property
    def ordered_contribution_ids(self) -> list[str]:
        """Compatibility view for callers that only need the ordered IDs."""
        return [item.contribution_id for item in self.ordered_contributions]


class WorldInitializationReceipt(_WorldInitModel):
    schema_: Literal["dmb_world_initialization_receipt_v1"] = Field(alias="schema")
    world_id: str
    campaign_id: str
    focus_session_id: str
    actor: str
    baseline_revision_id: str
    initial_head_revision_id: str
    plan_digest: str
    ordered_contributions: list[WorldInitializationContribution]
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

    @property
    def ordered_contribution_ids(self) -> list[str]:
        """Compatibility view for callers that only need the ordered IDs."""
        return [item.contribution_id for item in self.ordered_contributions]


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
