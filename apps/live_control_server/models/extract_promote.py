"""Strict API models for extract → World Supergraph promote."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from apps.live_control_server.models.world_graph_contribution_models import (
    ContributionIdentityMention,
    GraphContributionAssertion,
)

STATUS_SCHEMA = "dmb_extract_promote_status_v1"
PREPARE_REQUEST_SCHEMA = "dmb_extract_promote_prepare_request_v2"
PREPARE_RESPONSE_SCHEMA = "dmb_extract_promote_prepare_v1"
CONFIRM_REQUEST_SCHEMA = "dmb_extract_promote_confirm_request_v2"
CONFIRM_RESPONSE_SCHEMA = "dmb_extract_promote_confirm_v2"
ERROR_SCHEMA = "dmb_extract_promote_error_v1"
EXACT_RUN_REVIEW_SCHEMA = "dmb_extract_promote_exact_run_review_v1"
EVIDENCE_CORRECTION_REQUEST_SCHEMA = "dmb_exact_run_evidence_correction_request_v1"
EVIDENCE_CORRECTION_RESPONSE_SCHEMA = "dmb_exact_run_evidence_correction_response_v1"
RECAP_EVIDENCE_CORRECTION_RESPONSE_SCHEMA = "dmb_recap_evidence_correction_response_v1"
RECAP_CANDIDATE_CORRECTION_REQUEST_SCHEMA = "dmb_recap_candidate_correction_request_v1"
RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA = "dmb_recap_candidate_correction_response_v1"
RECAP_CANDIDATE_CORRECTION_REQUEST_SCHEMA_V3 = "dmb_recap_candidate_correction_request_v3"
RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA_V3 = "dmb_recap_candidate_correction_response_v3"
RECAP_CANDIDATE_CORRECTION_REQUEST_SCHEMA_V4 = "dmb_recap_candidate_correction_request_v4"
RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA_V4 = "dmb_recap_candidate_correction_response_v4"
RECAP_CANDIDATE_CORRECTION_REQUEST_SCHEMA_V5 = "dmb_recap_candidate_correction_request_v5"
RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA_V5 = "dmb_recap_candidate_correction_response_v5"
RECAP_SEMANTIC_DECISION_REQUEST_SCHEMA = "dmb_recap_semantic_decision_request_v1"
RECAP_SEMANTIC_DECISION_RESPONSE_SCHEMA = "dmb_recap_semantic_decision_response_v1"
WORLD_BUILDING_WRITE_PLAN_REQUEST_SCHEMA = (
    "dmb_worldbuilding_write_plan_prepare_request_v1"
)
WORLD_BUILDING_WRITE_PLAN_SCHEMA_V1 = "dmb_worldbuilding_write_plan_v1"
WORLD_BUILDING_WRITE_PLAN_SCHEMA = "dmb_worldbuilding_write_plan_v2"
# Readable aliases used by service/tests; retain the existing constant naming
# style for the older extract-promote contracts.
WORLDBUILDING_WRITE_PLAN_REQUEST_SCHEMA = WORLD_BUILDING_WRITE_PLAN_REQUEST_SCHEMA
WORLDBUILDING_WRITE_PLAN_SCHEMA = WORLD_BUILDING_WRITE_PLAN_SCHEMA
WORLDBUILDING_WRITE_PLAN_SCHEMA_V1 = WORLD_BUILDING_WRITE_PLAN_SCHEMA_V1

DiagnosticSeverity = Literal["error", "warning", "info"]
ExtractPromoteInspectionStatus = Literal["ready", "blocked", "invalid_evidence"]
WorldState = Literal["initialized", "uninitialized", "unreadable", "unmanaged"]
FirstWorldGraphState = Literal[
    "uninitialized",
    "initialized",
    "unreadable",
    "unmanaged",
]
FIRST_WORLD_PREPARE_REQUEST_SCHEMA = "dmb_first_world_graph_prepare_request_v1"
FIRST_WORLD_PLAN_SCHEMA = "dmb_first_world_graph_plan_v1"
FIRST_WORLD_CONFIRM_REQUEST_SCHEMA = "dmb_first_world_graph_confirm_request_v1"
FIRST_WORLD_CONFIRM_RESPONSE_SCHEMA = "dmb_first_world_graph_confirm_v1"

SERVER_PREPARED_BY = "live_control:extract_promote"
SERVER_CONFIRMING_PRINCIPAL = "live_control:graph_review_confirm"
PRODUCT_CONFIRM_ALLOW_LIVE_WORLD = True
PRODUCT_CONFIRM_DRY_RUN = False
PRODUCT_CONFIRM_ALLOW_IDEMPOTENT_NOOP = True


class _ExtractPromoteModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class ExtractPromoteDiagnostic(_ExtractPromoteModel):
    code: str
    message: str
    severity: DiagnosticSeverity = "error"


def _nonblank(value: str, *, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must be a non-blank string")
    if any(ch in text for ch in ("\r", "\n", "\t")):
        raise ValueError(f"{field_name} must not contain control whitespace")
    if len(text) > 256:
        raise ValueError(f"{field_name} must be at most 256 characters")
    return text


class ExtractPromoteStatusResponse(_ExtractPromoteModel):
    schema_: Literal["dmb_extract_promote_status_v1"] = Field(
        default=STATUS_SCHEMA, alias="schema"
    )
    world_id: str
    initialized: bool
    world_state: WorldState = "uninitialized"
    head_revision_id: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


class ExtractPromotePrepareRequest(_ExtractPromoteModel):
    """Product prepare selects a managed World; native target stays server-owned."""

    schema_: Literal["dmb_extract_promote_prepare_request_v2"] = Field(
        default=PREPARE_REQUEST_SCHEMA, alias="schema"
    )
    run_id: str
    managed_world_id: str | None = None
    node_ids: list[str] | None = None

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, value: str) -> str:
        return _nonblank(value, field_name="run_id")

    @field_validator("managed_world_id")
    @classmethod
    def _managed_world_id(cls, value: str | None) -> str | None:
        return _nonblank(value, field_name="managed_world_id") if value is not None else None


class ExtractPromotionReviewItem(_ExtractPromoteModel):
    """Game-facing presentation row; sealed package remains confirm authority."""

    assertion_id: str
    kind: Literal["object", "relationship", "attribute", "alias"]
    label: str
    action: Literal["create", "connect_existing", "update"]
    identity_outcome: str
    summary: str
    evidence_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    selectable: bool = False
    selected_by_default: bool = False
    depends_on_assertion_ids: list[str] = Field(default_factory=list)
    contribution_slice_id: str = ""
    slice_qualified_id: str = ""
    depends_on_slice_qualified_ids: list[str] = Field(default_factory=list)
    provenance: Literal["standing_context", "source_extraction"] | None = None


class ExtractPromoteReviewSummary(_ExtractPromoteModel):
    new_object_count: int = 0
    connect_existing_count: int = 0
    relationship_count: int = 0
    unresolved_mention_count: int = 0
    rejected_assertion_count: int = 0
    standing_accepted_proposals_count: int | None = None


class ExtractPromotePrepareResponse(_ExtractPromoteModel):
    schema_: Literal["dmb_extract_promote_prepare_v1"] = Field(
        default=PREPARE_RESPONSE_SCHEMA, alias="schema"
    )
    proposal_id: str
    proposal_digest: str
    parent_revision_id: str
    world_id: str
    accepted_proposals_count: int
    unresolved_mentions_count: int
    rejected_assertions_count: int
    confirmable: bool
    review_package: dict[str, Any]
    review_items: list[ExtractPromotionReviewItem] = Field(default_factory=list)
    review_summary: ExtractPromoteReviewSummary = Field(
        default_factory=ExtractPromoteReviewSummary
    )
    run_id: str | None = None
    campaign_id: str | None = None
    session_id: str | None = None


WorldbuildingDispositionDecision = Literal[
    "create_new",
    "bind_existing",
    "accept",
    "reject",
    "defer",
]


class WorldbuildingDisposition(_ExtractPromoteModel):
    assertion_id: str
    decision: WorldbuildingDispositionDecision
    target_node_id: str | None = None

    @field_validator("assertion_id")
    @classmethod
    def _assertion_id(cls, value: str) -> str:
        return _nonblank(value, field_name="assertion_id")

    @field_validator("target_node_id")
    @classmethod
    def _target_node_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _nonblank(value, field_name="target_node_id")

    @model_validator(mode="after")
    def _target_matches_decision(self) -> "WorldbuildingDisposition":
        if self.decision == "bind_existing" and self.target_node_id is None:
            raise ValueError("target_node_id is required for bind_existing")
        if self.decision != "bind_existing" and self.target_node_id is not None:
            raise ValueError(
                "target_node_id is only permitted for bind_existing"
            )
        return self


class WorldbuildingWritePlanPrepareRequest(_ExtractPromoteModel):
    schema_: Literal[WORLD_BUILDING_WRITE_PLAN_REQUEST_SCHEMA] = Field(
        default=WORLD_BUILDING_WRITE_PLAN_REQUEST_SCHEMA, alias="schema"
    )
    run_id: str
    expected_parent_revision_id: str
    dispositions: list[WorldbuildingDisposition] = Field(min_length=1)

    @field_validator("run_id", "expected_parent_revision_id")
    @classmethod
    def _required_ids(cls, value: str, info) -> str:
        return _nonblank(value, field_name=info.field_name)

class WorldbuildingWritePlanDecisionSnapshot(_ExtractPromoteModel):
    assertion_id: str
    candidate_kind: Literal["node", "edge"]
    decision: WorldbuildingDispositionDecision
    target_node_id: str | None = None


class WorldbuildingWritePlanContributionMeta(_ExtractPromoteModel):
    source_kind: Literal["source_extraction"] = "source_extraction"
    source_artifact_id: str
    source_revision_id: str
    extraction_profile: str
    campaign_scope: str | None = None
    authored_by: Literal["live_control:worldbuilding_write_plan"] = (
        "live_control:worldbuilding_write_plan"
    )


class WorldbuildingWritePlanIdentityAuthority(_ExtractPromoteModel):
    schema_: Literal["dmb_worldbuilding_identity_snapshot_v1"] = Field(
        default="dmb_worldbuilding_identity_snapshot_v1", alias="schema"
    )
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    identity_redirects: dict[str, str] = Field(default_factory=dict)
    alias_owners: dict[str, list[str]] = Field(default_factory=dict)


class WorldbuildingWritePlanEffect(_ExtractPromoteModel):
    contribution_meta: WorldbuildingWritePlanContributionMeta
    accepted_proposals: list[GraphContributionAssertion] = Field(
        default_factory=list
    )
    rejected_assertions: list[GraphContributionAssertion] = Field(
        default_factory=list
    )
    unresolved_mentions: list[ContributionIdentityMention] = Field(
        default_factory=list
    )
    deferred_candidate_ids: list[str] = Field(default_factory=list)
    node_id_map: dict[str, str] = Field(default_factory=dict)
    identity_outcome_snapshot: dict[str, str] = Field(default_factory=dict)
    candidate_effect_map: dict[str, list[str]] = Field(default_factory=dict)
    decision_snapshot: list[WorldbuildingWritePlanDecisionSnapshot] = Field(
        default_factory=list
    )
    identity_authority: WorldbuildingWritePlanIdentityAuthority | None = None


class WorldbuildingWritePlanSummary(_ExtractPromoteModel):
    create_new_node_count: int = 0
    bind_existing_node_count: int = 0
    accepted_edge_count: int = 0
    rejected_candidate_count: int = 0
    deferred_candidate_count: int = 0
    accepted_assertion_count: int = 0


class WorldbuildingWritePlanResponse(_ExtractPromoteModel):
    schema_: Literal[
        WORLD_BUILDING_WRITE_PLAN_SCHEMA,
        WORLD_BUILDING_WRITE_PLAN_SCHEMA_V1,
    ] = Field(default=WORLD_BUILDING_WRITE_PLAN_SCHEMA, alias="schema")
    version: Literal[1, 2] = 2
    plan_id: str
    plan_digest: str
    decision_digest: str
    world_id: str
    parent_revision_id: str
    run_id: str
    source_domain: Literal["worldbuilding"] = "worldbuilding"
    source_artifact_id: str
    source_revision_id: str
    extraction_profile: Literal["worldbuilding_shepherds_flock_v0@0.1"] = (
        "worldbuilding_shepherds_flock_v0@0.1"
    )
    candidate_preview_id: str
    candidate_schema: str
    candidate_version: str
    effect: WorldbuildingWritePlanEffect
    summary: WorldbuildingWritePlanSummary
    diagnostics: list[str] = Field(default_factory=list)
    confirmable: Literal[False] = False
    confirmable_reason: Literal[
        "BLD-10a prepares an inert write plan; graph confirmation is not implemented."
    ] = "BLD-10a prepares an inert write plan; graph confirmation is not implemented."
    prepare_binding: str | None = None


WORLD_BUILDING_WRITE_PLAN_CONFIRM_REQUEST_SCHEMA = (
    "dmb_worldbuilding_write_plan_confirm_request_v1"
)
WORLD_BUILDING_WRITE_PLAN_CONFIRM_RESPONSE_SCHEMA = (
    "dmb_worldbuilding_write_plan_confirm_v1"
)
ConfirmAuditStatus = Literal["ok", "degraded"]
WorldbuildingConfirmOutcome = Literal[
    "committed",
    "published_audit_degraded",
    "already_applied",
]


class WorldbuildingWritePlanConfirmRequest(_ExtractPromoteModel):
    schema_: Literal[WORLD_BUILDING_WRITE_PLAN_CONFIRM_REQUEST_SCHEMA] = Field(
        default=WORLD_BUILDING_WRITE_PLAN_CONFIRM_REQUEST_SCHEMA,
        alias="schema",
    )
    plan: WorldbuildingWritePlanResponse


class WorldbuildingWritePlanConfirmReceipt(_ExtractPromoteModel):
    schema_: Literal[WORLD_BUILDING_WRITE_PLAN_CONFIRM_RESPONSE_SCHEMA] = Field(
        default=WORLD_BUILDING_WRITE_PLAN_CONFIRM_RESPONSE_SCHEMA,
        alias="schema",
    )
    outcome: WorldbuildingConfirmOutcome
    world_id: str
    plan_id: str
    plan_digest: str
    decision_digest: str
    parent_revision_id: str
    committed_revision_id: str
    head_advanced: bool
    contribution_id: str
    applied_assertion_count: int
    accepted_assertion_ids: list[str] = Field(default_factory=list)
    rejected_assertion_ids: list[str] = Field(default_factory=list)
    unresolved_mention_ids: list[str] = Field(default_factory=list)
    audit_status: ConfirmAuditStatus
    warnings: list[str] = Field(default_factory=list)


ConfirmOutcome = Literal["committed", "already_applied", "published_audit_degraded"]


class ExtractPromoteConfirmRequest(_ExtractPromoteModel):
    schema_: Literal["dmb_extract_promote_confirm_request_v2"] = Field(
        default=CONFIRM_REQUEST_SCHEMA, alias="schema"
    )
    review_package: dict[str, Any]
    assertion_ids: list[str]

    @field_validator("assertion_ids")
    @classmethod
    def _assertion_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            item = str(raw).strip()
            if not item:
                raise ValueError("assertion_ids must not contain blank entries")
            if item in seen:
                raise ValueError("assertion_ids must not contain duplicates")
            seen.add(item)
            normalized.append(item)
        return normalized


class ExtractPromoteConfirmReceipt(_ExtractPromoteModel):
    schema_: Literal["dmb_extract_promote_confirm_v2"] = Field(
        default=CONFIRM_RESPONSE_SCHEMA, alias="schema"
    )
    outcome: ConfirmOutcome
    world_id: str
    proposal_id: str
    proposal_digest: str
    parent_revision_id: str
    committed_revision_id: str
    head_advanced: bool
    selected_assertion_ids: list[str]
    accepted_assertion_ids: list[str]
    affected_object_ids: list[str]
    applied_assertion_count: int
    audit_status: ConfirmAuditStatus
    warnings: list[str] = Field(default_factory=list)


class ExtractPromoteErrorResponse(_ExtractPromoteModel):
    schema_: Literal["dmb_extract_promote_error_v1"] = Field(
        default=ERROR_SCHEMA, alias="schema"
    )
    code: str
    message: str
    status_code: int
    diagnostics: list[ExtractPromoteDiagnostic] = Field(default_factory=list)
    failure_result: dict[str, Any] | None = None
    run_status: str | None = None
    inspection_status: ExtractPromoteInspectionStatus | None = None


class ExactRunReviewEvidence(_ExtractPromoteModel):
    """One inspectable SourceArtifact/span evidence binding for an assertion."""

    source_artifact_id: str
    source_span_ref_id: str
    paragraph_text: str
    anchor_quotes: list[str] = Field(default_factory=list)
    invalid_anchor_quotes: list[str] = Field(default_factory=list)
    start_line: int | None = None
    end_line: int | None = None


class ExactRunReviewAssertion(_ExtractPromoteModel):
    assertion_id: str
    kind: Literal["object", "relationship"]
    label: str
    summary: str
    evidence: list[ExactRunReviewEvidence] = Field(default_factory=list)


class ExactRunEvidenceQuoteCorrection(_ExtractPromoteModel):
    assertion_id: str
    evidence_index: int = Field(ge=0)
    source_span_ref_id: str
    quote_index: int = Field(ge=0)
    original_quote: str
    replacement_quote: str


class ExactRunEvidenceCorrectionRequest(_ExtractPromoteModel):
    schema_: Literal["dmb_exact_run_evidence_correction_request_v1"] = Field(
        default=EVIDENCE_CORRECTION_REQUEST_SCHEMA, alias="schema"
    )
    parent_run_id: str
    parent_candidate_sha256: str
    corrections: list[ExactRunEvidenceQuoteCorrection] = Field(min_length=1)


class ExactRunEvidenceCorrectionResponse(_ExtractPromoteModel):
    schema_: Literal["dmb_exact_run_evidence_correction_response_v1"] = Field(
        default=EVIDENCE_CORRECTION_RESPONSE_SCHEMA, alias="schema"
    )
    run_id: str
    parent_run_id: str
    parent_candidate_sha256: str
    candidate_sha256: str
    correction_digest: str
    status: Literal["reviewable"] = "reviewable"


class RecapEvidenceCorrectionResponse(_ExtractPromoteModel):
    schema_: Literal["dmb_recap_evidence_correction_response_v1"] = Field(
        default=RECAP_EVIDENCE_CORRECTION_RESPONSE_SCHEMA, alias="schema"
    )
    run_id: str
    parent_run_id: str
    parent_candidate_sha256: str
    candidate_sha256: str
    correction_digest: str
    status: Literal["reviewable"] = "reviewable"
    semantic_state: Literal["held", "accepted", "rejected"]
    semantic_basis_sha256: str


class RecapNodeDescriptionReplacement(_ExtractPromoteModel):
    node_id: str
    original_description: str
    replacement_description: str

    @field_validator("node_id")
    @classmethod
    def _node_id(cls, value: str) -> str:
        return _nonblank(value, field_name="node_id")

    @field_validator("replacement_description")
    @classmethod
    def _description(cls, value: str) -> str:
        if not value.strip() or value != value.strip() or len(value) > 4096:
            raise ValueError("replacement_description must be nonblank, trimmed and bounded")
        return value


class RecapCandidateNodeOmission(_ExtractPromoteModel):
    """Remove one isolated node, pinned to its complete canonical record."""

    node_id: str
    expected_node_sha256: str

    @field_validator("node_id")
    @classmethod
    def _node_id(cls, value: str) -> str:
        if not value or value != value.strip() or len(value) > 256 or any(ch in value for ch in ("\r", "\n", "\t")):
            raise ValueError("node_id must be nonblank, trimmed and bounded")
        return value

    @field_validator("expected_node_sha256")
    @classmethod
    def _digest(cls, value: str) -> str:
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("expected_node_sha256 must be lowercase SHA-256 hex")
        return value


class RecapNodeLabelReplacement(_ExtractPromoteModel):
    node_id: str
    original_label: str
    replacement_label: str

    @field_validator("node_id")
    @classmethod
    def _node_id(cls, value: str) -> str:
        return _nonblank(value, field_name="node_id")

    @field_validator("original_label", "replacement_label")
    @classmethod
    def _label(cls, value: str, info) -> str:
        if not value.strip() or value != value.strip() or len(value) > 4096:
            raise ValueError(f"{info.field_name} must be nonblank, trimmed and bounded")
        return value

    @model_validator(mode="after")
    def _changed(self) -> "RecapNodeLabelReplacement":
        if self.original_label == self.replacement_label:
            raise ValueError("replacement_label must differ from original_label")
        return self


class RecapCandidateCorrectionRequest(_ExtractPromoteModel):
    schema_: Literal["dmb_recap_candidate_correction_request_v1"] = Field(
        default=RECAP_CANDIDATE_CORRECTION_REQUEST_SCHEMA, alias="schema"
    )
    parent_run_id: str
    parent_candidate_sha256: str
    node_description_replacements: list[RecapNodeDescriptionReplacement] = Field(default_factory=list, max_length=1)
    node_label_replacements: list[RecapNodeLabelReplacement] = Field(default_factory=list, max_length=1)
    omitted_edge_ids: list[str] = Field(default_factory=list, max_length=1)

    node_omissions: list[RecapCandidateNodeOmission] = Field(default_factory=list, max_length=1)

    @model_validator(mode="after")
    def _bounded(self) -> "RecapCandidateCorrectionRequest":
        if self.node_omissions and (self.node_description_replacements or self.node_label_replacements or self.omitted_edge_ids):
            raise ValueError("node omission must be the only candidate correction")
        if not self.node_description_replacements and not self.node_label_replacements and not self.omitted_edge_ids and not self.node_omissions:
            raise ValueError("at least one candidate correction is required")
        targets = [v.node_id for v in (*self.node_description_replacements, *self.node_label_replacements)]
        if len(set(targets)) != len(targets):
            raise ValueError("duplicate node correction")
        if len(set(self.omitted_edge_ids)) != len(self.omitted_edge_ids):
            raise ValueError("duplicate omitted edge")
        if any(not value.strip() or value != value.strip() for value in self.omitted_edge_ids):
            raise ValueError("omitted edge IDs must be nonblank and trimmed")
        if len(self.parent_candidate_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.parent_candidate_sha256):
            raise ValueError("parent_candidate_sha256 must be lowercase SHA-256 hex")
        return self


class RecapCandidateCorrectionResponse(_ExtractPromoteModel):
    schema_: Literal["dmb_recap_candidate_correction_response_v1"] = Field(
        default=RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA, alias="schema"
    )
    run_id: str
    parent_run_id: str
    parent_candidate_sha256: str
    candidate_sha256: str
    manifest_sha256: str
    semantic_basis_sha256: str
    semantic_state: Literal["held", "accepted", "rejected"]
    status: Literal["reviewable"] = "reviewable"


class RecapSessionActionReplacement(_ExtractPromoteModel):
    node_id: str
    action_index: int = Field(ge=0)
    expected_old_text: str
    replacement_text: str

    @field_validator("node_id", "expected_old_text", "replacement_text")
    @classmethod
    def _text(cls, value: str) -> str:
        if not value.strip() or value != value.strip() or len(value) > 4096:
            raise ValueError("session action text and node ID must be nonblank, trimmed and bounded")
        return value

    @field_validator("action_index")
    @classmethod
    def _index(cls, value: int) -> int:
        if type(value) is not int:
            raise ValueError("action_index must be an integer")
        return value


class RecapCandidateCorrectionRequestV2(_ExtractPromoteModel):
    schema_: Literal["dmb_recap_candidate_correction_request_v2"] = Field(
        alias="schema"
    )
    parent_run_id: str
    parent_candidate_sha256: str
    node_description_replacements: list[RecapNodeDescriptionReplacement] = Field(default_factory=list, max_length=1)
    omitted_edge_ids: list[str] = Field(default_factory=list, max_length=1)
    session_action_replacements: list[RecapSessionActionReplacement] = Field(min_length=1, max_length=1)

    @model_validator(mode="after")
    def _bounded(self) -> "RecapCandidateCorrectionRequestV2":
        if self.node_description_replacements and self.node_description_replacements[0].node_id != self.session_action_replacements[0].node_id:
            raise ValueError("description and session action corrections must target the same node")
        if any(not value.strip() or value != value.strip() for value in self.omitted_edge_ids):
            raise ValueError("omitted edge IDs must be nonblank and trimmed")
        if len(self.parent_candidate_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.parent_candidate_sha256):
            raise ValueError("parent_candidate_sha256 must be lowercase SHA-256 hex")
        return self


class RecapCandidateCorrectionResponseV2(RecapCandidateCorrectionResponse):
    schema_: Literal["dmb_recap_candidate_correction_response_v2"] = Field(
        default="dmb_recap_candidate_correction_response_v2", alias="schema"
    )


class RecapCandidateEdgeTuple(_ExtractPromoteModel):
    """The four candidate-owned fields changed by one atomic tuple rewrite."""

    from_node_id: str
    relationship_type: str
    to_node_id: str
    label: str

    @field_validator("from_node_id", "to_node_id")
    @classmethod
    def _endpoint_id(cls, value: str, info) -> str:
        if (
            not value or value != value.strip() or len(value) > 256
            or any(ch in value for ch in ("\r", "\n", "\t"))
        ):
            raise ValueError(f"{info.field_name} must be nonblank, trimmed and bounded")
        return value

    @field_validator("relationship_type")
    @classmethod
    def _relationship_type(cls, value: str) -> str:
        if (
            not value or value != value.strip() or value != value.lower()
            or len(value) > 128
            or any(ch in value for ch in ("\r", "\n", "\t"))
        ):
            raise ValueError("relationship_type must be lowercase, trimmed and bounded")
        return value

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        if (
            not value or value != value.strip() or len(value) > 4096
            or any(ch in value for ch in ("\r", "\n", "\t"))
        ):
            raise ValueError("label must be nonblank, trimmed and bounded")
        return value


class RecapCandidateEdgeTupleReplacement(_ExtractPromoteModel):
    edge_id: str
    expected_tuple: RecapCandidateEdgeTuple
    replacement_tuple: RecapCandidateEdgeTuple

    @field_validator("edge_id")
    @classmethod
    def _edge_id(cls, value: str) -> str:
        if (
            not value or value != value.strip() or len(value) > 256
            or any(ch in value for ch in ("\r", "\n", "\t"))
        ):
            raise ValueError("edge_id must be nonblank, trimmed and bounded")
        return value

    @model_validator(mode="after")
    def _changed_tuple(self) -> "RecapCandidateEdgeTupleReplacement":
        if self.expected_tuple == self.replacement_tuple:
            raise ValueError("replacement tuple must differ from its preimage")
        return self


class RecapCandidateNodeTypeReplacement(_ExtractPromoteModel):
    """One exact-preimage type correction in a frozen recap candidate."""

    node_id: str
    expected_node_type: str
    replacement_node_type: str

    @field_validator("node_id")
    @classmethod
    def _node_id(cls, value: str) -> str:
        return _nonblank(value, field_name="node_id")

    @field_validator("expected_node_type", "replacement_node_type")
    @classmethod
    def _node_type(cls, value: str, info) -> str:
        if (
            not value or value != value.strip() or value != value.lower()
            or len(value) > 64
            or any(ch in value for ch in ("\r", "\n", "\t"))
        ):
            raise ValueError(f"{info.field_name} must be lowercase, trimmed and bounded")
        return value

    @model_validator(mode="after")
    def _changed_type(self) -> "RecapCandidateNodeTypeReplacement":
        if self.expected_node_type == self.replacement_node_type:
            raise ValueError("replacement node type must differ from its preimage")
        return self


class RecapCandidateCorrectionRequestV3(_ExtractPromoteModel):
    """A bounded, exact-preimage relation correction for one frozen candidate."""

    schema_: Literal[RECAP_CANDIDATE_CORRECTION_REQUEST_SCHEMA_V3] = Field(
        alias="schema"
    )
    parent_run_id: str
    parent_candidate_sha256: str
    edge_tuple_replacements: list[RecapCandidateEdgeTupleReplacement] = Field(
        min_length=1, max_length=7
    )
    node_type_replacements: list[RecapCandidateNodeTypeReplacement] = Field(
        default_factory=list, max_length=1
    )

    @field_validator("parent_run_id")
    @classmethod
    def _parent_run_id(cls, value: str) -> str:
        return _nonblank(value, field_name="parent_run_id")

    @field_validator("parent_candidate_sha256")
    @classmethod
    def _parent_candidate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("parent_candidate_sha256 must be lowercase SHA-256 hex")
        return value

    @model_validator(mode="after")
    def _node_type_correction_is_coordinated(self) -> "RecapCandidateCorrectionRequestV3":
        if self.node_type_replacements:
            node_id = self.node_type_replacements[0].node_id
            if not any(
                node_id in {
                    replacement.expected_tuple.from_node_id,
                    replacement.expected_tuple.to_node_id,
                    replacement.replacement_tuple.from_node_id,
                    replacement.replacement_tuple.to_node_id,
                }
                for replacement in self.edge_tuple_replacements
            ):
                raise ValueError("node type replacement must be paired with an edge tuple replacement for that node")
        return self


class RecapCandidateCorrectionResponseV3(RecapCandidateCorrectionResponse):
    schema_: Literal[RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA_V3] = Field(
        default=RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA_V3, alias="schema"
    )


class RecapCandidateEvidenceSpanReplacement(_ExtractPromoteModel):
    """One exact-preimage move of an evidence ref within its frozen source."""

    record_kind: Literal["node", "edge"]
    record_id: str
    evidence_index: int = Field(ge=0)
    expected_source_ref_id: str
    expected_source_artifact_id: str
    expected_source_span_ref_id: str
    replacement_source_span_ref_id: str
    expected_anchor_quotes: list[str] = Field(min_length=1, max_length=16)
    replacement_anchor_quotes: list[str] | None = Field(default=None, max_length=16)

    @field_validator(
        "record_id", "expected_source_ref_id", "expected_source_artifact_id",
        "expected_source_span_ref_id", "replacement_source_span_ref_id",
    )
    @classmethod
    def _identity(cls, value: str, info) -> str:
        return _nonblank(value, field_name=info.field_name)

    @field_validator("expected_anchor_quotes", "replacement_anchor_quotes")
    @classmethod
    def _quotes(cls, value: list[str] | None, info) -> list[str] | None:
        if value is None and info.field_name == "replacement_anchor_quotes":
            return None
        if not isinstance(value, list) or not value:
            raise ValueError(f"{info.field_name} must contain at least one quote")
        if any(
            not isinstance(item, str) or not item or item != item.strip() or len(item) > 4096
            for item in value
        ):
            raise ValueError(f"{info.field_name} entries must be nonblank, trimmed and bounded")
        return value

    @model_validator(mode="after")
    def _changed_span(self) -> "RecapCandidateEvidenceSpanReplacement":
        if self.expected_source_span_ref_id == self.replacement_source_span_ref_id:
            raise ValueError("replacement span must differ from the preimage")
        return self

    @field_validator("evidence_index")
    @classmethod
    def _evidence_index(cls, value: int) -> int:
        if type(value) is not int:
            raise ValueError("evidence_index must be an integer")
        return value


class RecapCandidateCorrectionRequestV4(_ExtractPromoteModel):
    """A bounded same-source evidence span relocation for one frozen candidate."""

    schema_: Literal[RECAP_CANDIDATE_CORRECTION_REQUEST_SCHEMA_V4] = Field(alias="schema")
    parent_run_id: str
    parent_candidate_sha256: str
    evidence_span_replacements: list[RecapCandidateEvidenceSpanReplacement] = Field(
        min_length=1, max_length=1
    )

    @field_validator("parent_run_id")
    @classmethod
    def _parent_run_id(cls, value: str) -> str:
        return _nonblank(value, field_name="parent_run_id")

    @field_validator("parent_candidate_sha256")
    @classmethod
    def _parent_candidate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("parent_candidate_sha256 must be lowercase SHA-256 hex")
        return value


class RecapCandidateCorrectionResponseV4(RecapCandidateCorrectionResponse):
    schema_: Literal[RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA_V4] = Field(
        default=RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA_V4, alias="schema"
    )


class RecapCandidateEvidenceReplacementV5(_ExtractPromoteModel):
    """One exact-preimage source evidence replacement in a bounded batch."""

    record_kind: Literal["node", "edge"]
    record_id: str
    evidence_index: int = Field(ge=0)
    expected_source_ref_id: str
    expected_source_artifact_id: str
    expected_source_span_ref_id: str
    replacement_source_span_ref_id: str
    expected_anchor_quotes: list[str] = Field(min_length=1, max_length=16)
    replacement_anchor_quotes: list[str] = Field(min_length=1, max_length=16)

    @field_validator(
        "record_id", "expected_source_ref_id", "expected_source_artifact_id",
        "expected_source_span_ref_id", "replacement_source_span_ref_id",
    )
    @classmethod
    def _identity(cls, value: str, info) -> str:
        return _nonblank(value, field_name=info.field_name)

    @field_validator("evidence_index")
    @classmethod
    def _evidence_index(cls, value: int) -> int:
        if type(value) is not int:
            raise ValueError("evidence_index must be an integer")
        return value

    @field_validator("expected_anchor_quotes", "replacement_anchor_quotes")
    @classmethod
    def _quotes(cls, value: list[str]) -> list[str]:
        if any(not item or item != item.strip() or len(item) > 4096 for item in value):
            raise ValueError("anchor quotes must be nonblank, trimmed and bounded")
        return value

    @model_validator(mode="after")
    def _changed_evidence(self) -> "RecapCandidateEvidenceReplacementV5":
        if (
            self.expected_source_span_ref_id == self.replacement_source_span_ref_id
            and self.expected_anchor_quotes == self.replacement_anchor_quotes
        ):
            raise ValueError("evidence replacement must change span or anchor quotes")
        return self


class RecapCandidateCorrectionRequestV5(_ExtractPromoteModel):
    """An atomic bounded evidence replacement batch for one frozen candidate."""

    schema_: Literal[RECAP_CANDIDATE_CORRECTION_REQUEST_SCHEMA_V5] = Field(alias="schema")
    parent_run_id: str
    parent_candidate_sha256: str
    evidence_replacements: list[RecapCandidateEvidenceReplacementV5] = Field(
        min_length=1, max_length=7
    )

    @field_validator("parent_run_id")
    @classmethod
    def _parent_run_id(cls, value: str) -> str:
        return _nonblank(value, field_name="parent_run_id")

    @field_validator("parent_candidate_sha256")
    @classmethod
    def _parent_candidate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("parent_candidate_sha256 must be lowercase SHA-256 hex")
        return value

    @model_validator(mode="after")
    def _unique_targets(self) -> "RecapCandidateCorrectionRequestV5":
        keys = [
            (item.record_kind, item.record_id, item.evidence_index)
            for item in self.evidence_replacements
        ]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate evidence replacement target")
        return self


class RecapCandidateCorrectionResponseV5(RecapCandidateCorrectionResponse):
    schema_: Literal[RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA_V5] = Field(
        default=RECAP_CANDIDATE_CORRECTION_RESPONSE_SCHEMA_V5, alias="schema"
    )


class RecapEvidenceRefSplitPart(_ExtractPromoteModel):
    source_span_ref_id: str
    quote_indices: list[int] = Field(min_length=1, max_length=16)

    @field_validator("source_span_ref_id")
    @classmethod
    def _span_id(cls, value: str) -> str:
        if not value or value != value.strip() or len(value) > 256 or any(ch in value for ch in ("\r", "\n", "\t")):
            raise ValueError("span ID must be nonblank, trimmed and bounded")
        return value


class RecapEvidenceRefSplit(_ExtractPromoteModel):
    record_kind: Literal["node", "edge"]
    record_id: str
    evidence_index: int = Field(ge=0)
    expected_evidence_ref_sha256: str
    parts: list[RecapEvidenceRefSplitPart] = Field(min_length=2, max_length=2)

    @field_validator("record_id")
    @classmethod
    def _record_id(cls, value: str) -> str:
        return RecapEvidenceRefSplitPart._span_id(value)

    @field_validator("expected_evidence_ref_sha256")
    @classmethod
    def _digest(cls, value: str) -> str:
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("evidence ref digest must be lowercase SHA-256 hex")
        return value

    @model_validator(mode="after")
    def _partitions(self) -> "RecapEvidenceRefSplit":
        if self.parts[0].source_span_ref_id == self.parts[1].source_span_ref_id:
            raise ValueError("split spans must be distinct")
        indices = [index for part in self.parts for index in part.quote_indices]
        if indices != list(range(len(indices))):
            raise ValueError("quote partitions must preserve every occurrence in order")
        return self


class RecapCandidateCorrectionRequestV6(_ExtractPromoteModel):
    """Split one complete frozen evidence ref without changing quote text."""

    schema_: Literal["dmb_recap_candidate_correction_request_v6"] = Field(alias="schema")
    parent_run_id: str
    parent_candidate_sha256: str
    source_revision_sha256: str
    span_index_sha256: str
    evidence_ref_splits: list[RecapEvidenceRefSplit] = Field(min_length=1, max_length=1)

    @field_validator("parent_run_id")
    @classmethod
    def _parent(cls, value: str) -> str:
        return _nonblank(value, field_name="parent_run_id")

    @field_validator("parent_candidate_sha256", "source_revision_sha256", "span_index_sha256")
    @classmethod
    def _sha(cls, value: str) -> str:
        return RecapEvidenceRefSplit._digest(value)


class RecapCandidateCorrectionResponseV6(RecapCandidateCorrectionResponse):
    schema_: Literal["dmb_recap_candidate_correction_response_v6"] = Field(
        default="dmb_recap_candidate_correction_response_v6", alias="schema"
    )


class ExactRunReviewPackage(_ExtractPromoteModel):
    """Server-owned exact-run review projection — source prose + assertion evidence.

    Not a sealed prepare proposal. Operators inspect this before preparing.
    """

    schema_: Literal["dmb_extract_promote_exact_run_review_v1"] = Field(
        default=EXACT_RUN_REVIEW_SCHEMA, alias="schema"
    )
    run_id: str
    derived_from_run_id: str | None = None
    source_domain: str
    source_artifact_id: str
    source_revision_id: str
    campaign_id: str | None = None
    session_id: str | None = None
    source_prose: str
    assertions: list[ExactRunReviewAssertion] = Field(default_factory=list)
    inspection_status: ExtractPromoteInspectionStatus = "ready"
    invalid_evidence_count: int = 0
    diagnostics: list[str] = Field(default_factory=list)
    # BLD-07 narrowed: worldbuilding_draft runs are inspect-only; publication
    # remains reserved for promote-eligible (played_canon) recap paths.
    promotable: bool = True
    promotable_reason: str | None = None
    # Present only for a recap child made by operator literal-evidence correction.
    semantic_disposition: dict[str, Any] | None = None
    # Additive first-world publish capability (CR02A). Generic promotable stays
    # false for worldbuilding; eligibility is a separate explicit path.
    world_id: str | None = None
    world_state: FirstWorldGraphState | None = None
    first_world_publish_eligible: bool = False
    first_world_publish_reason: str | None = None


class RecapSemanticDecisionRequest(_ExtractPromoteModel):
    schema_: Literal["dmb_recap_semantic_decision_request_v1"] = Field(
        default=RECAP_SEMANTIC_DECISION_REQUEST_SCHEMA, alias="schema"
    )
    expected_revision: int = Field(ge=1)
    candidate_sha256: str
    decision: Literal["accepted", "rejected"]
    review_decision_ref: str

    @field_validator("candidate_sha256")
    @classmethod
    def _candidate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("candidate_sha256 must be lowercase SHA-256 hex")
        return value

    @field_validator("review_decision_ref")
    @classmethod
    def _review_decision_ref(cls, value: str) -> str:
        return _nonblank(value, field_name="review_decision_ref")


class RecapSemanticDecisionResponse(_ExtractPromoteModel):
    schema_: Literal["dmb_recap_semantic_decision_response_v1"] = Field(
        default=RECAP_SEMANTIC_DECISION_RESPONSE_SCHEMA, alias="schema"
    )
    run_id: str
    revision: int
    candidate_sha256: str
    state: Literal["accepted", "rejected"]
    basis_sha256: str
    review_decision_ref: str
    reviewer_id: str
    decided_at: str


FirstWorldDecision = Literal["create_new", "reject", "accept"]
FirstWorldConfirmOutcome = Literal[
    "initialized",
    "already_initialized",
    "published_audit_degraded",
]


class FirstWorldDisposition(_ExtractPromoteModel):
    assertion_id: str
    decision: FirstWorldDecision

    @field_validator("assertion_id")
    @classmethod
    def _assertion_id(cls, value: str) -> str:
        return _nonblank(value, field_name="assertion_id")


class FirstWorldGraphPrepareRequest(_ExtractPromoteModel):
    schema_: Literal[FIRST_WORLD_PREPARE_REQUEST_SCHEMA] = Field(
        default=FIRST_WORLD_PREPARE_REQUEST_SCHEMA, alias="schema"
    )
    run_id: str
    decisions: list[FirstWorldDisposition] = Field(min_length=1)

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, value: str) -> str:
        return _nonblank(value, field_name="run_id")


class FirstWorldGraphPlanSummary(_ExtractPromoteModel):
    create_new_node_count: int = 0
    accepted_edge_count: int = 0
    rejected_candidate_count: int = 0
    accepted_assertion_count: int = 0


class FirstWorldGraphPlan(_ExtractPromoteModel):
    """Sealed, response-carried first-world initialization plan (confirm evidence)."""

    schema_: Literal[FIRST_WORLD_PLAN_SCHEMA] = Field(
        default=FIRST_WORLD_PLAN_SCHEMA, alias="schema"
    )
    plan_id: str
    plan_digest: str
    decision_digest: str
    world_id: str
    run_id: str
    source_artifact_id: str
    source_revision_id: str
    workspace_document_id: str
    workspace_document_revision: str
    campaign_scope: str | None = None
    session_scope: None = None
    extraction_profile: Literal["worldbuilding_shepherds_flock_v0@0.1"] = (
        "worldbuilding_shepherds_flock_v0@0.1"
    )
    accepted_assertion_ids: list[str] = Field(default_factory=list)
    rejected_assertion_ids: list[str] = Field(default_factory=list)
    contribution_id: str
    contribution_payload_sha256: str
    reviewed_effect: dict[str, Any]
    summary: FirstWorldGraphPlanSummary = Field(
        default_factory=FirstWorldGraphPlanSummary
    )
    confirmable: bool
    diagnostics: list[str] = Field(default_factory=list)


class FirstWorldGraphConfirmRequest(_ExtractPromoteModel):
    schema_: Literal[FIRST_WORLD_CONFIRM_REQUEST_SCHEMA] = Field(
        default=FIRST_WORLD_CONFIRM_REQUEST_SCHEMA, alias="schema"
    )
    plan: FirstWorldGraphPlan


class FirstWorldGraphConfirmReceipt(_ExtractPromoteModel):
    schema_: Literal[FIRST_WORLD_CONFIRM_RESPONSE_SCHEMA] = Field(
        default=FIRST_WORLD_CONFIRM_RESPONSE_SCHEMA, alias="schema"
    )
    outcome: FirstWorldConfirmOutcome
    world_id: str
    plan_id: str
    plan_digest: str
    decision_digest: str
    source_artifact_id: str
    source_revision_id: str
    contribution_id: str
    baseline_revision_id: str | None = None
    committed_revision_id: str | None = None
    applied_assertion_count: int
    accepted_assertion_ids: list[str] = Field(default_factory=list)
    rejected_assertion_ids: list[str] = Field(default_factory=list)
    audit_status: ConfirmAuditStatus
    warnings: list[str] = Field(default_factory=list)
