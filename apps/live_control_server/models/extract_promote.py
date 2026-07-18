"""Strict API models for extract → World Supergraph promote."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

STATUS_SCHEMA = "dmb_extract_promote_status_v1"
PREPARE_REQUEST_SCHEMA = "dmb_extract_promote_prepare_request_v2"
PREPARE_RESPONSE_SCHEMA = "dmb_extract_promote_prepare_v1"
CONFIRM_REQUEST_SCHEMA = "dmb_extract_promote_confirm_request_v1"
CONFIRM_RESPONSE_SCHEMA = "dmb_extract_promote_confirm_v1"
ERROR_SCHEMA = "dmb_extract_promote_error_v1"

DiagnosticSeverity = Literal["error", "warning", "info"]
WorldState = Literal["initialized", "uninitialized", "unreadable"]

SERVER_PREPARED_BY = "live_control:extract_promote"


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


class ExtractPromoteReviewSummary(_ExtractPromoteModel):
    new_object_count: int = 0
    connect_existing_count: int = 0
    relationship_count: int = 0
    unresolved_mention_count: int = 0
    rejected_assertion_count: int = 0


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


class ExtractPromoteConfirmRequest(_ExtractPromoteModel):
    schema_: Literal["dmb_extract_promote_confirm_request_v1"] = Field(
        default=CONFIRM_REQUEST_SCHEMA, alias="schema"
    )
    review_package: dict[str, Any]
    confirming_principal: str
    assertion_ids: list[str] | None = None
    dry_run: bool = False
    allow_live_world: bool = False
    allow_idempotent_noop: bool = False

    @field_validator("confirming_principal")
    @classmethod
    def _principal(cls, value: str) -> str:
        return _nonblank(value, field_name="confirming_principal")


class ExtractPromoteConfirmResponse(_ExtractPromoteModel):
    schema_: Literal["dmb_extract_promote_confirm_v1"] = Field(
        default=CONFIRM_RESPONSE_SCHEMA, alias="schema"
    )
    ok: bool
    dry_run: bool
    failure_reason: str | None = None
    result: dict[str, Any]


class ExtractPromoteErrorResponse(_ExtractPromoteModel):
    schema_: Literal["dmb_extract_promote_error_v1"] = Field(
        default=ERROR_SCHEMA, alias="schema"
    )
    code: str
    message: str
    status_code: int
    diagnostics: list[ExtractPromoteDiagnostic] = Field(default_factory=list)
    failure_result: dict[str, Any] | None = None
