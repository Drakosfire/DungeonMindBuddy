"""Strict API models for the PR006D2 Eldyrwild bootstrap contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

BootstrapState = Literal[
    "ready",
    "invalid_bundle",
    "active",
    "active_head_advanced",
    "blocked_existing_world",
    "inconsistent_lineage",
    "error",
]

DiagnosticSeverity = Literal["error", "warning", "info"]
ReviewClassification = Literal["sourceDerived", "gmAuthored", "mixed"]

STATUS_SCHEMA = "dmb_world_graph_bootstrap_status_v1"
PREPARE_REQUEST_SCHEMA = "dmb_world_graph_bootstrap_prepare_request_v1"
PREPARE_RESPONSE_SCHEMA = "dmb_world_graph_bootstrap_prepare_v1"
CONFIRM_REQUEST_SCHEMA = "dmb_world_graph_bootstrap_confirm_request_v1"
CONFIRM_RESPONSE_SCHEMA = "dmb_world_graph_bootstrap_confirm_v1"
ERROR_SCHEMA = "dmb_world_graph_bootstrap_error_v1"
CONTRACT_SCHEMA = "dmb_world_graph_bootstrap_api_contract_v1"


class _BootstrapModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class BootstrapDiagnostic(_BootstrapModel):
    code: str
    message: str
    severity: DiagnosticSeverity = "error"


class BootstrapApprovalAttestation(_BootstrapModel):
    bundle_id: str
    bundle_digest: str
    approved_bundle_merge_sha: str


class BootstrapPlanContribution(_BootstrapModel):
    contribution_id: str
    payload_sha256: str


class BootstrapReceipt(_BootstrapModel):
    schema_: Literal["dmb_world_initialization_receipt_v1"] = Field(alias="schema")
    world_id: str
    campaign_id: str
    focus_session_id: str
    actor: str
    baseline_revision_id: str
    initial_head_revision_id: str
    plan_digest: str
    ordered_contributions: list[BootstrapPlanContribution]
    identity_decision_ids: list[str]
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
    approval_attestation: BootstrapApprovalAttestation
    created_at: str


class BootstrapEvidenceSummary(_BootstrapModel):
    evidence_ref_id: str
    source_artifact_id: str
    source_domain: str
    session_id: str | None = None
    locator: str | None = None
    source_span_ref_id: str | None = None
    locator_status: Literal["verified", "unverified"] = "unverified"


class BootstrapSourceArtifact(_BootstrapModel):
    source_artifact_id: str
    source_domain: str
    uri: str
    campaign_id: str
    session_id: str | None = None
    classification: ReviewClassification


class BootstrapContributionReview(_BootstrapModel):
    contribution_id: str
    source_kind: str
    classification: Literal["sourceDerived", "gmAuthored"]
    authored_by: str | None = None
    source_artifact_id: str | None = None
    source_revision_id: str | None = None
    accepted_assertion_count: int
    node_ids: list[str]
    edge_ids: list[str]
    attribute_assertion_ids: list[str]


class BootstrapNodeReview(_BootstrapModel):
    node_id: str
    label: str
    kind: str
    role: str
    aliases: list[str]
    source_domains: list[str]
    contribution_ids: list[str]
    evidence: list[BootstrapEvidenceSummary]
    classification: ReviewClassification


class BootstrapRelationshipReview(_BootstrapModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    predicate: str
    label: str
    session_ids: list[str]
    source_domains: list[str]
    contribution_ids: list[str]
    evidence: list[BootstrapEvidenceSummary]
    classification: ReviewClassification


class BootstrapAttributeReview(_BootstrapModel):
    assertion_id: str
    subject_node_id: str
    attribute: str
    text: str
    source_domains: list[str]
    contribution_id: str
    evidence: list[BootstrapEvidenceSummary]
    classification: ReviewClassification


class BootstrapReviewSummary(_BootstrapModel):
    contribution_count: int
    node_count: int
    relationship_count: int
    attribute_count: int
    accepted_assertion_count: int
    support_count: int
    evidence_count: int
    source_artifact_count: int
    source_domains: list[str]
    focus_sessions: list[str]


class BootstrapReview(_BootstrapModel):
    summary: BootstrapReviewSummary
    contributions: list[BootstrapContributionReview]
    nodes: list[BootstrapNodeReview]
    relationships: list[BootstrapRelationshipReview]
    attributes: list[BootstrapAttributeReview]
    sources: list[BootstrapSourceArtifact]
    evidence: list[BootstrapEvidenceSummary]
    trust_boundary: list[str]


class BootstrapTrustBoundary(_BootstrapModel):
    can_trust: list[str]
    cannot_trust: list[str]


class WorldGraphBootstrapPrepareRequest(_BootstrapModel):
    schema_: Literal["dmb_world_graph_bootstrap_prepare_request_v1"] = Field(
        PREPARE_REQUEST_SCHEMA,
        alias="schema",
    )
    actor: str = Field(min_length=1, max_length=128)

    @field_validator("actor")
    @classmethod
    def _actor_must_not_be_blank(cls, value: str) -> str:
        if not value.strip() or any(char in value for char in "\r\n\t"):
            raise ValueError("actor must be a bounded non-blank string")
        return value.strip()


class WorldGraphBootstrapConfirmRequest(_BootstrapModel):
    schema_: Literal["dmb_world_graph_bootstrap_confirm_request_v1"] = Field(
        CONFIRM_REQUEST_SCHEMA,
        alias="schema",
    )
    actor: str = Field(min_length=1, max_length=128)
    proposal_id: str = Field(min_length=1, max_length=256)
    confirm_token: str = Field(min_length=1, max_length=8192)

    @field_validator("actor")
    @classmethod
    def _actor_must_not_be_blank(cls, value: str) -> str:
        if not value.strip() or any(char in value for char in "\r\n\t"):
            raise ValueError("actor must be a bounded non-blank string")
        return value.strip()


class WorldGraphBootstrapEffects(_BootstrapModel):
    contribution_count: int
    predicted_revision_count: int
    ordered_contribution_ids: list[str]
    predicted_baseline_revision_id: str
    predicted_initial_head_revision_id: str


class WorldGraphBootstrapStatusResponse(_BootstrapModel):
    schema_: Literal["dmb_world_graph_bootstrap_status_v1"] = Field(
        STATUS_SCHEMA,
        alias="schema",
    )
    state: BootstrapState
    world_id: str
    campaign_id: str
    focus_session_id: str
    bundle_id: str
    bundle_digest: str
    approved_bundle_merge_sha: str
    bundle_valid: bool
    current_head_revision_id: str | None = None
    initial_head_revision_id: str | None = None
    head_advanced_since_initialization: bool = False
    review: BootstrapReview | None = None
    trust_boundary: BootstrapTrustBoundary
    diagnostics: list[BootstrapDiagnostic] = Field(default_factory=list)
    receipt: BootstrapReceipt | None = None


class WorldGraphBootstrapPrepareResponse(_BootstrapModel):
    schema_: Literal["dmb_world_graph_bootstrap_prepare_v1"] = Field(
        PREPARE_RESPONSE_SCHEMA,
        alias="schema",
    )
    prepared: Literal[True] = True
    actor: str
    proposal_id: str
    confirm_token: str
    plan_digest: str
    predicted_baseline_revision_id: str
    predicted_initial_head_revision_id: str
    review: BootstrapReview
    effects: WorldGraphBootstrapEffects
    no_mutation_guarantees: list[str]
    diagnostics: list[BootstrapDiagnostic] = Field(default_factory=list)


class WorldGraphBootstrapConfirmResponse(_BootstrapModel):
    schema_: Literal["dmb_world_graph_bootstrap_confirm_v1"] = Field(
        CONFIRM_RESPONSE_SCHEMA,
        alias="schema",
    )
    confirmed: Literal[True] = True
    actor: str
    proposal_id: str
    plan_digest: str
    published: bool
    state: BootstrapState
    baseline_revision_id: str | None = None
    initial_head_revision_id: str | None = None
    current_head_revision_id: str | None = None
    receipt: BootstrapReceipt | None = None
    no_mutation_guarantees: list[str]
    diagnostics: list[BootstrapDiagnostic] = Field(default_factory=list)


class WorldGraphBootstrapErrorResponse(_BootstrapModel):
    schema_: Literal["dmb_world_graph_bootstrap_error_v1"] = Field(
        ERROR_SCHEMA,
        alias="schema",
    )
    code: str
    message: str
    status_code: int
    bootstrap_state: BootstrapState
    diagnostics: list[BootstrapDiagnostic] = Field(default_factory=list)


__all__ = [
    "BootstrapApprovalAttestation",
    "BootstrapAttributeReview",
    "BootstrapContributionReview",
    "BootstrapDiagnostic",
    "BootstrapEvidenceSummary",
    "BootstrapPlanContribution",
    "BootstrapReceipt",
    "BootstrapRelationshipReview",
    "BootstrapReview",
    "BootstrapReviewSummary",
    "BootstrapSourceArtifact",
    "BootstrapState",
    "BootstrapTrustBoundary",
    "CONTRACT_SCHEMA",
    "CONFIRM_REQUEST_SCHEMA",
    "CONFIRM_RESPONSE_SCHEMA",
    "ERROR_SCHEMA",
    "PREPARE_REQUEST_SCHEMA",
    "PREPARE_RESPONSE_SCHEMA",
    "STATUS_SCHEMA",
    "WorldGraphBootstrapConfirmRequest",
    "WorldGraphBootstrapConfirmResponse",
    "WorldGraphBootstrapEffects",
    "WorldGraphBootstrapErrorResponse",
    "WorldGraphBootstrapPrepareRequest",
    "WorldGraphBootstrapPrepareResponse",
    "WorldGraphBootstrapStatusResponse",
]
