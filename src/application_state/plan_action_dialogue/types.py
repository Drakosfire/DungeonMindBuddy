"""Typed Plan action records, reservations, and allowlisted projections."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from application_state.agent_conversation.types import (
    WorldPointer,
    PlanAskHistoryAttributionV1,
    PlanWorldGraphAssembledInputV1,
    PlanWorldGraphAuthorityV1,
    PlanWorldGraphCitationMapV2,
    PlanWorldGraphClaimSegmentV1,
    PlanWorldGraphConnectiveSegmentV1,
    PlanWorldGraphExecutionV2,
    PlanWorldGraphPacketV1,
)

ActionStatus = Literal["pending", "completed", "failed", "indeterminate"]
ActionType = Literal["compose", "revise"]
TargetKind = Literal["replace_selection", "insert_at_caret", "replace_playable_body"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class PlanActionBasis(StrictModel):
    world_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=128)
    object_revision: int = Field(strict=True, ge=1)
    work_revision_id: UUID
    revision_n: int = Field(strict=True, ge=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlanActionPlayableTargetReceipt(StrictModel):
    schema_version: Literal["dmb_plan_playable_target_receipt_v1"]
    kind: Literal["scene", "beat", "choice", "option"]
    id: str = Field(pattern=r"^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$")
    marker_grammar_version: Literal["v1", "v2"]
    body_scope: Literal["heading_body", "beat_direct_body", "option_item_content"]
    range_semantics_version: Literal["plan-playable-ranges-v1"]
    body_serialization_version: Literal["plan-playable-body-markdown-v1"]
    target_body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_typed_scope(self):
        if self.id.split(":", 1)[0] != self.kind:
            raise ValueError("Playable target receipt kind must match its ID prefix")
        if self.marker_grammar_version == "v1":
            valid_scope = self.body_scope == "heading_body"
        elif self.kind == "option":
            valid_scope = self.body_scope == "option_item_content"
        elif self.kind == "beat":
            valid_scope = self.body_scope == "beat_direct_body"
        else:
            valid_scope = self.body_scope == "heading_body"
        if not valid_scope:
            raise ValueError("Playable target receipt scope does not match its grammar and kind")
        return self


class PlanActionContinuation(StrictModel):
    continuation_of_action_id: UUID
    clarification_id: UUID
    previous_result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_instruction: str = Field(min_length=1, max_length=4000)


class PlanActionConsultationReceipt(StrictModel):
    """Server-frozen action inputs; draft intent is separate from Graph authority."""

    schema_version: Literal["dmb_plan_action_consultation_receipt_v1"] = (
        "dmb_plan_action_consultation_receipt_v1"
    )
    receipt_serializer_version: Literal["canonical-json-utf8-v1"]
    consultation_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: UUID
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    origin_conversation_id: UUID
    origin_pointer_revision: int = Field(strict=True, ge=1)
    surface_id: Literal["plan"]
    surface_instance_id: str = Field(min_length=1, max_length=128)
    basis: PlanActionBasis
    draft_matches_basis: bool
    draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_kind: Literal["replace_selection"]
    selected_text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    instruction: str = Field(min_length=1, max_length=4000)
    action_input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_status: Literal["resolved", "unavailable"] = "resolved"
    authority_failure_code: str | None = Field(default=None, min_length=1, max_length=128)
    graph_authority: PlanWorldGraphAuthorityV1 | None = None
    graph_packet: PlanWorldGraphPacketV1 | None = None
    assembled_input: PlanWorldGraphAssembledInputV1 | None = None
    continuation: PlanActionContinuation | None = None
    history_conversation_id: UUID | None = None
    history_attribution: list[PlanAskHistoryAttributionV1] = Field(
        default_factory=list, max_length=6
    )

    @model_validator(mode="after")
    def validate_receipt(self):
        from application_state.plan_action_dialogue.graph_consultation import (
            validate_consultation_receipt,
        )

        validate_consultation_receipt(self)
        return self


class ActionResultAttribution(StrictModel):
    schema_version: Literal["dmb_plan_action_result_v1"] = "dmb_plan_action_result_v1"
    result_id: UUID
    consultation_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    message: str = Field(min_length=1, max_length=12000)
    producing_provider_attempt_id: UUID
    answer_segments: list[
        Annotated[
            PlanWorldGraphClaimSegmentV1 | PlanWorldGraphConnectiveSegmentV1,
            Field(discriminator="kind"),
        ]
    ] = Field(min_length=1, max_length=128)
    citation_map: PlanWorldGraphCitationMapV2 | None
    claim_graph_event_ids: dict[str, list[UUID]] = Field(max_length=128)

    @model_validator(mode="after")
    def validate_message(self):
        if not self.message.strip():
            raise ValueError("action result message must be nonblank")
        return self


class PlanActionClarificationResult(ActionResultAttribution):
    kind: Literal["clarification"]


class PlanActionProposalResult(ActionResultAttribution):
    kind: Literal["proposal"]
    disposition: Literal[
        "supported_context_used",
        "no_relevant_established_fact_found",
        "explicit_draft_override_after_clarification",
    ]
    # Commit the inert response, preserving existing proposal-payload non-replay.
    proposal_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlanActionContextUnavailableResult(StrictModel):
    schema_version: Literal["dmb_plan_action_result_v1"] = "dmb_plan_action_result_v1"
    kind: Literal["context_unavailable"]
    result_id: UUID
    consultation_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    message: str = Field(min_length=1, max_length=12000)
    failure_code: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_failure(self):
        if not self.message.strip() or not self.failure_code.strip():
            raise ValueError("context unavailable result requires a visible message and failure code")
        return self


PlanActionConsultationResult = Annotated[
    PlanActionClarificationResult
    | PlanActionProposalResult
    | PlanActionContextUnavailableResult,
    Field(discriminator="kind"),
]


class PlanActionConsultation(StrictModel):
    schema_version: Literal["dmb_plan_action_consultation_v1"] = (
        "dmb_plan_action_consultation_v1"
    )
    receipt: PlanActionConsultationReceipt
    execution: PlanWorldGraphExecutionV2 | None
    result: PlanActionConsultationResult | None = None

    @model_validator(mode="after")
    def validate_consultation(self):
        from application_state.plan_action_dialogue.graph_consultation import (
            validate_consultation,
        )

        validate_consultation(self)
        return self


class ConsultationOptionalModel(StrictModel):
    consultation: PlanActionConsultation | None = None

    @model_serializer(mode="wrap")
    def serialize_legacy_shape(self, handler):
        data = handler(self)
        if self.consultation is None:
            data.pop("consultation", None)
        return data


class PlanActionReservation(StrictModel):
    idempotency_key: UUID
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_world_pointer: WorldPointer | None = None
    action_type: ActionType
    basis: PlanActionBasis
    draft_matches_basis: bool
    draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_kind: TargetKind
    selected_text_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    playable_target_receipt: PlanActionPlayableTargetReceipt | None = None
    instruction: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_target_witness(self):
        if self.expected_world_pointer is not None and (
            self.expected_world_pointer.world_id != self.basis.world_id
            or self.expected_world_pointer.active_conversation_id is None
            or self.expected_world_pointer.revision < 1
            or self.action_type != "revise"
            or self.target_kind != "replace_selection"
        ):
            raise ValueError("sourced Plan selection requires a current World conversation pointer")
        if self.target_kind == "replace_playable_body":
            if self.action_type != "revise" or self.selected_text_sha256 is not None or self.playable_target_receipt is None:
                raise ValueError("Playable body actions require a revise action and one typed target receipt")
        elif self.playable_target_receipt is not None:
            raise ValueError("Only Playable body actions may carry a typed target receipt")
        elif self.target_kind == "replace_selection" and self.selected_text_sha256 is None:
            raise ValueError("replace_selection requires a selected-text digest")
        elif self.target_kind == "insert_at_caret" and self.selected_text_sha256 is not None:
            raise ValueError("insert_at_caret cannot carry a selected-text digest")
        return self


class PlanActionRecord(ConsultationOptionalModel):
    action_id: UUID
    idempotency_key: UUID
    request_fingerprint: str
    action_type: ActionType
    basis: PlanActionBasis
    draft_matches_basis: bool
    draft_sha256: str
    target_kind: TargetKind
    selected_text_sha256: str | None
    playable_target_receipt: PlanActionPlayableTargetReceipt | None
    instruction: str
    status: ActionStatus
    assistant_summary: str | None
    failure_code: str | None
    dispatch_token: UUID | None
    fence: int
    action_sequence: int
    accepted_at: datetime
    completed_at: datetime | None
    lease_expires_at: datetime | None

    @model_validator(mode="after")
    def validate_consultation_binding(self):
        from application_state.plan_action_dialogue.graph_consultation import (
            validate_consultation_record,
        )

        validate_consultation_record(self)
        return self


class PlanActionProjection(ConsultationOptionalModel):
    action_id: UUID
    action_type: ActionType
    status: ActionStatus
    basis: PlanActionBasis
    instruction: str
    assistant_summary: str | None
    action_sequence: int
    accepted_at: datetime
    completed_at: datetime | None
    playable_target_receipt: PlanActionPlayableTargetReceipt | None


class PlanActionProjectionPage(StrictModel):
    schema_version: Literal["dmb_world_plan_action_projection_v1"] = (
        "dmb_world_plan_action_projection_v1"
    )
    basis: PlanActionBasis
    actions: list[PlanActionProjection] = Field(max_length=50)


class PlanActionConversationProjectionPage(StrictModel):
    schema_version: Literal["dmb_world_plan_action_conversation_projection_v1"] = (
        "dmb_world_plan_action_conversation_projection_v1"
    )
    world_id: str = Field(min_length=1, max_length=128)
    conversation_id: UUID
    actions: list[PlanActionProjection] = Field(max_length=50)
    next_before_action_sequence: int | None = Field(default=None, ge=1)


class CompletedPlanActionContext(ConsultationOptionalModel):
    action_id: UUID
    action_type: ActionType
    basis: PlanActionBasis
    instruction: str
    assistant_summary: str = Field(min_length=1)
    action_sequence: int
    accepted_at: datetime


def request_fingerprint(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
