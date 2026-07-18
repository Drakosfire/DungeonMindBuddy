"""Strict API models for extract → World Supergraph promote."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

STATUS_SCHEMA = "dmb_extract_promote_status_v1"
PREPARE_REQUEST_SCHEMA = "dmb_extract_promote_prepare_request_v1"
PREPARE_RESPONSE_SCHEMA = "dmb_extract_promote_prepare_v1"
CONFIRM_REQUEST_SCHEMA = "dmb_extract_promote_confirm_request_v1"
CONFIRM_RESPONSE_SCHEMA = "dmb_extract_promote_confirm_v1"
ERROR_SCHEMA = "dmb_extract_promote_error_v1"

DiagnosticSeverity = Literal["error", "warning", "info"]
WorldState = Literal["initialized", "uninitialized", "unreadable"]


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
    schema_: Literal["dmb_extract_promote_prepare_request_v1"] = Field(
        default=PREPARE_REQUEST_SCHEMA, alias="schema"
    )
    candidate_graph_path: str
    source_uri: str
    source_revision_id: str
    prepared_by: str
    world_id: str = "eldyrwild"
    source_artifact_id: str | None = None
    campaign_scope: str | None = None
    node_ids: list[str] | None = None
    nodes_only: bool = False

    @field_validator("candidate_graph_path", "source_uri", "source_revision_id", "prepared_by")
    @classmethod
    def _required_nonblank(cls, value: str, info) -> str:  # type: ignore[no-untyped-def]
        return _nonblank(value, field_name=info.field_name)

    @field_validator("world_id")
    @classmethod
    def _world_id(cls, value: str) -> str:
        return _nonblank(value, field_name="world_id")


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
