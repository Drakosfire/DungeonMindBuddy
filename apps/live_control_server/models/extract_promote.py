"""Strict API models for extract → World Supergraph promote."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

STATUS_SCHEMA = "dmb_extract_promote_status_v1"
PREPARE_REQUEST_SCHEMA = "dmb_extract_promote_prepare_request_v2"
PREPARE_RESPONSE_SCHEMA = "dmb_extract_promote_prepare_v1"
CONFIRM_REQUEST_SCHEMA = "dmb_extract_promote_confirm_request_v2"
CONFIRM_RESPONSE_SCHEMA = "dmb_extract_promote_confirm_v2"
ERROR_SCHEMA = "dmb_extract_promote_error_v1"
EXACT_RUN_REVIEW_SCHEMA = "dmb_extract_promote_exact_run_review_v1"

DiagnosticSeverity = Literal["error", "warning", "info"]
WorldState = Literal["initialized", "uninitialized", "unreadable"]

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
    """Product prepare: ``{runId, nodeIds?}`` only — world is server-owned."""

    schema_: Literal["dmb_extract_promote_prepare_request_v2"] = Field(
        default=PREPARE_REQUEST_SCHEMA, alias="schema"
    )
    run_id: str
    node_ids: list[str] | None = None

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, value: str) -> str:
        return _nonblank(value, field_name="run_id")


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
    review_package: dict[str, Any]
    review_items: list[ExtractPromotionReviewItem] = Field(default_factory=list)
    review_summary: ExtractPromoteReviewSummary = Field(
        default_factory=ExtractPromoteReviewSummary
    )
    run_id: str | None = None
    campaign_id: str | None = None
    session_id: str | None = None


ConfirmOutcome = Literal["committed", "already_applied", "published_audit_degraded"]
ConfirmAuditStatus = Literal["ok", "degraded"]


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


class ExactRunReviewEvidence(_ExtractPromoteModel):
    """One inspectable SourceArtifact/span evidence binding for an assertion."""

    source_artifact_id: str
    source_span_ref_id: str
    paragraph_text: str
    anchor_quotes: list[str] = Field(default_factory=list)
    start_line: int | None = None
    end_line: int | None = None


class ExactRunReviewAssertion(_ExtractPromoteModel):
    assertion_id: str
    kind: Literal["object", "relationship"]
    label: str
    summary: str
    evidence: list[ExactRunReviewEvidence] = Field(default_factory=list)


class ExactRunReviewPackage(_ExtractPromoteModel):
    """Server-owned exact-run review projection — source prose + assertion evidence.

    Not a sealed prepare proposal. Operators inspect this before preparing.
    """

    schema_: Literal["dmb_extract_promote_exact_run_review_v1"] = Field(
        default=EXACT_RUN_REVIEW_SCHEMA, alias="schema"
    )
    run_id: str
    source_domain: str
    source_artifact_id: str
    source_revision_id: str
    campaign_id: str | None = None
    session_id: str | None = None
    source_prose: str
    assertions: list[ExactRunReviewAssertion] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    # BLD-07 narrowed: worldbuilding_draft runs are inspect-only; publication
    # remains reserved for promote-eligible (played_canon) recap paths.
    promotable: bool = True
    promotable_reason: str | None = None
