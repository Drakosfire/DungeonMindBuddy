"""Versioned, host-owned first-World review and durable recovery protocol.

These values are never model prompt context. A plan's signature and current owner
checks, not browser-carried hashes or a claimed World, establish its authority.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext.domain import DomainContractRef
from dungeonmind.contracts.vnext.native_source import NativeTextSourceOriginV1, NativeUtf8SpanProofV1
from dungeonmind.contracts.vnext.source import SourceRevisionV2
from dungeonmind.contracts.vnext.prospective import KnowledgeProspectivePublication
from dungeonmind.contracts.reviewed_world_initialization import (
    ReviewedWorldInitializationReceiptV1, ReviewedWorldInitializationReceiptV2,
)
from apps.live_control_server.models.extract_promote import (
    _ExtractPromoteModel, FirstWorldDisposition, FirstWorldGraphPlanSummary,
    FirstWorldNativeTarget,
)

NATIVE_PREPARE_SCHEMA = "dmb_native_first_world_prepare_request_v1"
NATIVE_PLAN_SCHEMA = "dmb_native_first_world_plan_v1"
NATIVE_CONFIRM_SCHEMA = "dmb_native_first_world_confirm_request_v1"
NATIVE_RECEIPT_SCHEMA = "dmb_native_first_world_confirm_v1"
NATIVE_ENVELOPE_SCHEMA = "dmb_native_first_world_signed_plan_v1"
SHA = r"^[0-9a-f]{64}$"
TAGGED_SHA = r"^sha256:[0-9a-f]{64}$"


def _aware(value: str) -> str:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value


class NativeFirstWorldPrepareRequest(_ExtractPromoteModel):
    schema_: Literal["dmb_native_first_world_prepare_request_v1"] = Field(alias="schema")
    run_id: str = Field(min_length=1, max_length=512)
    decisions: list[FirstWorldDisposition] = Field(min_length=1)

    @field_validator("run_id")
    @classmethod
    def _run(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("runId must be an exact nonblank identifier")
        return value


class NativeFirstWorldExistingBinding(_ExtractPromoteModel):
    """An actual sealed-parent proof, including its immutable producer receipt."""

    reviewed_evidence_ref_id: str = Field(min_length=1)
    proof: NativeUtf8SpanProofV1
    source_revision: SourceRevisionV2
    evidence_role: Literal["support", "context"]
    proof_authority_epoch: int = Field(ge=1)
    origin_kind: Literal["admission", "extension"]
    origin_operation_id: str = Field(min_length=1)
    origin_receipt_sha256: str = Field(pattern=SHA)
    introduced_revision_id: str = Field(min_length=1)


class NativeFirstWorldSourceStage(_ExtractPromoteModel):
    """A real observed state and caller-owned operation IDs, never future proofs."""

    admission_state: Literal["absent", "admitted"]
    admission_id: str = Field(min_length=1)
    admission_receipt_sha256: str | None = Field(default=None, pattern=SHA)
    native_source_artifact_id: str | None = None
    native_source_revision_id: str | None = None
    whole_document_evidence_ref_id: str | None = None
    document_id: str = Field(min_length=1)
    source_root_relpath: str = Field(min_length=1)
    document_revision: int = Field(ge=1)
    document_updated_at: str
    body_sha256: str = Field(pattern=SHA)
    origin: NativeTextSourceOriginV1
    genesis_initialization_id: str = Field(min_length=1)
    genesis_created_at: str
    head_revision_id: str | None
    head_profile_ref: SemanticProfileRef | None
    source_authority_epoch: int = Field(ge=0)
    extension_id: str = Field(min_length=1)
    profile_transition_id: str = Field(min_length=1)
    existing_bindings: list[NativeFirstWorldExistingBinding] = Field(default_factory=list)

    _timestamps = field_validator("document_updated_at", "genesis_created_at")(_aware)

    @model_validator(mode="after")
    def _actual_state(self):
        source_fields = (self.admission_receipt_sha256, self.native_source_artifact_id,
                         self.native_source_revision_id, self.whole_document_evidence_ref_id)
        if self.admission_state == "absent" and (self.existing_bindings or any(v is not None for v in source_fields)):
            raise ValueError("an absent admission cannot contain invented source identities")
        if self.admission_state == "admitted" and (
            not all(isinstance(v, str) and v.strip() for v in source_fields)
            or self.head_revision_id is None
        ):
            raise ValueError("an admitted source requires its real receipt and head")
        if any(b.proof_authority_epoch > self.source_authority_epoch for b in self.existing_bindings):
            raise ValueError("proof creation epoch cannot exceed observed source authority")
        refs = [b.reviewed_evidence_ref_id for b in self.existing_bindings]
        if len(refs) != len(set(refs)):
            raise ValueError("existing proof bindings must close each reviewed reference once")
        if (self.head_revision_id is None) != (self.head_profile_ref is None):
            raise ValueError("head and profile must describe the same observed state")
        if self.origin.object_id != self.document_id or self.origin.revision_id != f"registry-revision:{self.document_revision}":
            raise ValueError("origin must match the exact workspace revision")
        return self


class NativeFirstWorldPlanDraft(_ExtractPromoteModel):
    """Known review content before computing its own public commitment."""

    schema_: Literal["dmb_native_first_world_plan_v1"] = Field(default=NATIVE_PLAN_SCHEMA, alias="schema")
    plan_id: str = Field(min_length=1)
    decision_digest: str = Field(pattern=TAGGED_SHA)
    source_evidence_sha256: str = Field(pattern=TAGGED_SHA)
    world_id: str = Field(min_length=1)
    native_target: FirstWorldNativeTarget
    run_id: str = Field(min_length=1)
    run_revision: int = Field(ge=0)
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(pattern=TAGGED_SHA)
    workspace_document_id: str = Field(min_length=1)
    workspace_document_revision: str = Field(min_length=1)
    campaign_scope: str
    session_scope: None = None
    extraction_profile: Literal["worldbuilding_shepherds_flock_v0@0.1"]
    accepted_assertion_ids: list[str]
    rejected_assertion_ids: list[str]
    contribution_id: str = Field(min_length=1)  # reviewed product correlation, not a Kernel allocation
    contribution_payload_sha256: str = Field(pattern=SHA)
    reviewed_effect: dict[str, Any]
    summary: FirstWorldGraphPlanSummary
    confirmable: bool
    diagnostics: list[str] = Field(default_factory=list)
    compiler_intent_json: str = Field(min_length=1, max_length=8 * 1024 * 1024)
    compiler_intent_sha256: str = Field(pattern=SHA)
    domain_contract_ref: DomainContractRef
    target_profile_ref: SemanticProfileRef
    source_stage: NativeFirstWorldSourceStage
    publication_id: str = Field(min_length=1)
    prepared_by: str = Field(min_length=1)
    created_at: str
    expires_at: str
    policy: Literal["dmb_native_first_world_compiler_v1"] = "dmb_native_first_world_compiler_v1"

    _timestamps = field_validator("created_at", "expires_at")(_aware)

    @model_validator(mode="after")
    def _closed_scope(self):
        if self.campaign_scope != self.world_id:
            raise ValueError("review source scope must match its managed World")
        if (self.source_stage.document_id != self.workspace_document_id
                or str(self.source_stage.document_revision) != self.workspace_document_revision
                or self.source_revision_id != "sha256:" + self.source_stage.body_sha256):
            raise ValueError("plan source stage does not match its reviewed source")
        ids = self.accepted_assertion_ids + self.rejected_assertion_ids
        if len(ids) != len(set(ids)):
            raise ValueError("reviewed assertion inventory must be unique")
        if self.confirmable != bool(self.accepted_assertion_ids):
            raise ValueError("confirmable must match the accepted inventory")
        if datetime.fromisoformat(self.expires_at.replace("Z", "+00:00")) <= datetime.fromisoformat(self.created_at.replace("Z", "+00:00")):
            raise ValueError("expiry must follow preparation")
        return self


class NativeFirstWorldPlanContent(NativeFirstWorldPlanDraft):
    """Validated complete content, including its computed public commitment."""

    plan_digest: str = Field(pattern=TAGGED_SHA)


class NativeFirstWorldPlan(NativeFirstWorldPlanContent):
    token: str = Field(min_length=1, max_length=16 * 1024 * 1024)


class NativeFirstWorldConfirmRequest(_ExtractPromoteModel):
    schema_: Literal["dmb_native_first_world_confirm_request_v1"] = Field(alias="schema")
    plan: NativeFirstWorldPlan


class NativeFirstWorldConfirmReceipt(_ExtractPromoteModel):
    schema_: Literal["dmb_native_first_world_confirm_v1"] = Field(default=NATIVE_RECEIPT_SCHEMA, alias="schema")
    outcome: Literal["initialized", "already_initialized", "activation_pending"]
    world_id: str
    plan_id: str
    plan_digest: str
    decision_digest: str
    source_artifact_id: str
    source_revision_id: str
    contribution_id: str  # exact reviewed product correlation
    native_contribution_id: str
    native_world_id: str
    publication_id: str
    committed_revision_id: str
    applied_assertion_count: int = Field(ge=1)
    accepted_assertion_ids: list[str]
    rejected_assertion_ids: list[str]
    native_publication: KnowledgeProspectivePublication
    activation_status: Literal["active", "pending"]
    source_status: Literal["available", "unavailable", "unknown"]
    recovered: bool
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _durable_outcome(self):
        receipt = self.native_publication.publication_receipt
        if receipt.space_id != self.native_world_id or receipt.publication_id != self.publication_id:
            raise ValueError("receipt must match its exact native space and operation")
        if receipt.published_revision_id != self.committed_revision_id:
            raise ValueError("receipt must name the actual native publication")
        if (self.outcome == "activation_pending") != (self.activation_status == "pending"):
            raise ValueError("activation status must be truthful")
        if self.applied_assertion_count != len(self.accepted_assertion_ids):
            raise ValueError("reviewed count must match its exact accepted inventory")
        return self


class HistoricalFirstWorldReceipt(_ExtractPromoteModel):
    schema_: Literal["dmb_historical_first_world_receipt_v1"] = Field(default="dmb_historical_first_world_receipt_v1", alias="schema")
    world_id: str
    native_world_id: str
    plan_id: str
    plan_digest: str
    historical_receipt: ReviewedWorldInitializationReceiptV2 | ReviewedWorldInitializationReceiptV1
    activation_status: Literal["historical_only"] = "historical_only"

    @model_validator(mode="after")
    def _historical_identity(self):
        receipt = self.historical_receipt
        if (receipt.world_id != self.native_world_id or receipt.source_plan_id != self.plan_id
                or "sha256:" + receipt.source_plan_sha256 != self.plan_digest):
            raise ValueError("historical result must match the exact retained receipt")
        return self
