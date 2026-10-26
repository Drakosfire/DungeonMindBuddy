"""Typed Plan action records, reservations, and allowlisted projections."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator, TypeAdapter

from application_state.agent_conversation.plan_authoring import PlanJevProposalOriginV1, PlanJevAuthoringReservationV1

from application_state.agent_conversation.types import (
    WorldPointer,
    PlanAskHistoryAttributionV1,
    PlanWorldGraphAssembledInputV1,
    PlanWorldGraphAuthorityV1,
    PlanWorldGraphCitationMapV2,
    PlanWorldGraphClaimSegmentV1,
    PlanWorldGraphConnectiveSegmentV1,
    PlanWorldGraphExecutionV2,
    PlanWorldGraphExecutionV3,
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


class PlanActionSelectionSectionV1(StrictModel):
    id: str = Field(pattern=r"^heading:(0|[1-9][0-9]{0,6}):[1-6]$")
    apply_from: int = Field(strict=True, ge=0, le=1_000_000)
    apply_to: int = Field(strict=True, ge=0, le=1_000_000)

    @model_validator(mode="after")
    def validate_root(self):
        if int(self.id.split(":", 2)[1]) != self.apply_from:
            raise ValueError("selection section ID must name its exact apply root")
        return self


class PlanActionSelectionAnchorV1(StrictModel):
    model_config = ConfigDict(validate_by_name=True)

    schema_version: Literal["dmb_plan_selection_anchor_v1"]
    editor_format: Literal["world-plan-tiptap-json-v1"]
    editor_json_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    anchor: int = Field(strict=True, ge=0, le=1_000_000)
    head: int = Field(strict=True, ge=0, le=1_000_000)
    from_: int = Field(alias="from", strict=True, ge=0, le=1_000_000)
    to: int = Field(strict=True, ge=0, le=1_000_000)
    section: PlanActionSelectionSectionV1 | None

    @model_validator(mode="after")
    def validate_range_and_size(self):
        if self.anchor == self.head or self.from_ != min(self.anchor, self.head) or self.to != max(self.anchor, self.head):
            raise ValueError("selection anchor range must match its directional endpoints")
        if self.section is not None and not (
            self.section.apply_from <= self.from_ < self.to <= self.section.apply_to
        ):
            raise ValueError("selection anchor must fit its exact heading section")
        encoded = json.dumps(
            self.model_dump(mode="json", by_alias=True),
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > 512:
            raise ValueError("selection anchor exceeds 512 canonical UTF-8 bytes")
        return self


class PlanActionContinuation(StrictModel):
    continuation_of_action_id: UUID
    clarification_id: UUID
    previous_result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_instruction: str = Field(min_length=1)


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
    instruction: str = Field(min_length=1)
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
    execution: PlanWorldGraphExecutionV2 | PlanWorldGraphExecutionV3 | None
    result: PlanActionConsultationResult | None = None

    @model_validator(mode="after")
    def validate_consultation(self):
        from application_state.plan_action_dialogue.graph_consultation import (
            validate_consultation,
        )

        validate_consultation(self)
        return self


class ActionPromptReferenceV1(StrictModel):
    owner_kind: Literal["plan_action"] = "plan_action"
    world_id: str = Field(min_length=1, max_length=128)
    action_id: UUID
    dispatch_fence: int = Field(strict=True, ge=1)
    authorization_event_id: UUID
    provider_attempt_id: UUID
    evidence_id: UUID
    provider: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=256)
    api_mode: str = Field(min_length=1, max_length=64)
    serializer_version: Literal["canonical-json-utf8-v1", "typesafe-sdk-json-v1", "openai-sdk-json-v1"]
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_utf8_bytes: int = Field(strict=True, ge=1, le=16 * 1024 * 1024)


class PlanActionConsultationV2(StrictModel):
    schema_version: Literal["dmb_plan_action_consultation_v2"] = "dmb_plan_action_consultation_v2"
    receipt: PlanActionConsultationReceipt
    execution: PlanWorldGraphExecutionV2 | PlanWorldGraphExecutionV3 | None
    result: PlanActionConsultationResult | None = None
    prompt_references: list[ActionPromptReferenceV1] = Field(max_length=512)

    @model_validator(mode="after")
    def validate_consultation(self):
        from application_state.plan_action_dialogue.graph_consultation import (
            validate_consultation, validate_prompt_references,
        )
        validate_consultation(self)
        validate_prompt_references(self)
        return self


class ActionTerminalFailureV1(StrictModel):
    """Closed provider report; no raw strings or authority supplied by the child."""
    phase: Literal["provider_lifecycle"]
    reason: Literal["lifecycle_ack_denied", "provider_transport_ambiguous", "provider_exception_ambiguous", "provider_response_incomplete"]
    transition: Literal["sdk_entered", "response_received", "outcome_unknown"]
    acknowledged: bool = Field(strict=True)
    transportExceptionClass: Literal["RemoteProtocolError", "ReadTimeout", "ConnectError", "ConnectionError"] | None = None
    responseStatus: Literal["incomplete", "failed", "other"] | None = None
    incompleteReason: Literal["max_output_tokens", "length", "content_filter", "unspecified", "other"] | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.transportExceptionClass is not None and self.reason != "provider_transport_ambiguous":
            raise ValueError("transport class requires transport failure")
        if (self.responseStatus is not None) != (self.reason == "provider_response_incomplete"):
            raise ValueError("response status requires incomplete response")
        if self.incompleteReason is not None and self.responseStatus != "incomplete":
            raise ValueError("incomplete reason requires incomplete status")
        if self.reason == "lifecycle_ack_denied" and self.acknowledged:
            raise ValueError("denied acknowledgement must be false")
        if self.reason != "lifecycle_ack_denied" and self.transition != "outcome_unknown":
            raise ValueError("ambiguous report requires unknown transition")
        return self


class ActionTerminalDiagnosticV1(StrictModel):
    schema_version: Literal["dmb_plan_action_terminal_diagnostic_v1"] = "dmb_plan_action_terminal_diagnostic_v1"
    world_id: str = Field(min_length=1, max_length=128)
    action_id: UUID
    dispatch_fence: int = Field(strict=True, ge=1)
    attribution: Literal["provider_attempt", "action_only"]
    availability: Literal["captured", "unavailable"]
    unavailable_reason: Literal["invalid_reported_by_host", "invalid_observed_at_parent", "missing_or_not_retained", "contradictory_binding"] | None = None
    failure: ActionTerminalFailureV1 | None = None
    runtime_status: Literal["ok", "error", "unavailable"]
    error_origin: Literal["runtime_result", "parent_adapter"]
    error_category: Literal["provider_lifecycle_unavailable", "request_budget_veto", "hermes_turn_error", "prompt_capture_unavailable", "other", "unavailable"]
    authorization_event_id: UUID | None = None
    provider_attempt_id: UUID | None = None
    callback_sequence: int | None = Field(default=None, strict=True, ge=0)
    parent_acknowledged: bool | None = Field(default=None, strict=True)
    matching_transition_event_id: UUID | None = None
    latest_durable_outcome_event_id: UUID | None = None
    latest_durable_outcome: Literal["sdk_entered", "response_received", "outcome_unknown", "known_not_sent"] | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.availability == "captured":
            if self.failure is None or self.unavailable_reason is not None:
                raise ValueError("captured diagnostic requires a valid report")
        elif self.failure is not None or self.unavailable_reason is None:
            raise ValueError("unavailable diagnostic requires provenance only")
        identities = (self.authorization_event_id, self.provider_attempt_id, self.callback_sequence,
                      self.parent_acknowledged, self.matching_transition_event_id,
                      self.latest_durable_outcome_event_id, self.latest_durable_outcome)
        if self.attribution == "action_only":
            if any(value is not None for value in identities):
                raise ValueError("Action-only diagnostic cannot attribute a provider")
        elif (self.availability != "captured" or any(value is None for value in identities[:4])):
            raise ValueError("provider attribution requires callback identity")
        if (self.latest_durable_outcome_event_id is None) != (self.latest_durable_outcome is None):
            raise ValueError("durable outcome requires its event identity")
        if len(json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) > 4096:
            raise ValueError("terminal diagnostic exceeds storage limit")
        return self


class PlanActionConsultationV3(StrictModel):
    schema_version: Literal["dmb_plan_action_consultation_v3"] = "dmb_plan_action_consultation_v3"
    receipt: PlanActionConsultationReceipt
    execution: PlanWorldGraphExecutionV2 | PlanWorldGraphExecutionV3 | None
    result: PlanActionConsultationResult | None = None
    prompt_references: list[ActionPromptReferenceV1] = Field(max_length=512)
    terminal_diagnostic: ActionTerminalDiagnosticV1

    @model_validator(mode="after")
    def validate_consultation(self):
        from application_state.plan_action_dialogue.graph_consultation import (
            validate_consultation, validate_prompt_references, validate_terminal_diagnostic,
        )
        validate_consultation(self)
        validate_prompt_references(self)
        validate_terminal_diagnostic(self)
        return self


PrivatePlanActionConsultation = Annotated[
    PlanActionConsultation | PlanActionConsultationV2 | PlanActionConsultationV3, Field(discriminator="schema_version"),
]
_CONSULTATION = TypeAdapter(PrivatePlanActionConsultation)


def decode_consultation(payload: object) -> PrivatePlanActionConsultation:
    return _CONSULTATION.validate_python(payload)


def public_consultation(value: PrivatePlanActionConsultation | None) -> PlanActionConsultation | None:
    if value is None:
        return None
    return PlanActionConsultation(receipt=value.receipt, execution=value.execution, result=value.result)


class ConsultationOptionalModel(StrictModel):
    consultation: PlanActionConsultation | None = None

    @model_serializer(mode="wrap")
    def serialize_legacy_shape(self, handler):
        data = handler(self)
        if self.consultation is None:
            data.pop("consultation", None)
        if getattr(self, "selection_anchor", None) is None:
            data.pop("selection_anchor", None)
        if getattr(self, "authoring_origin", None) is None:
            data.pop("authoring_origin", None)
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
    selection_anchor: PlanActionSelectionAnchorV1 | None = None
    instruction: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_target_witness(self):
        if self.selection_anchor is not None and (
            self.action_type != "revise" or self.target_kind != "replace_selection"
        ):
            raise ValueError("selection anchor belongs only to a revised Plan selection")
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
    consultation: PrivatePlanActionConsultation | None = None
    authoring_origin: PlanJevAuthoringReservationV1 | PlanJevProposalOriginV1 | None = None
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
    selection_anchor: PlanActionSelectionAnchorV1 | None = None
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
        origin = self.authoring_origin
        if origin is not None:
            if (self.consultation is not None or origin.action_id != self.action_id
                    or origin.idempotency_key != self.idempotency_key
                    or origin.action_request_fingerprint != self.request_fingerprint
                    or origin.basis.model_dump() != self.basis.model_dump()
                    or (isinstance(origin, PlanJevProposalOriginV1) != (self.status == "completed"))
                    or origin.action_fence > self.fence
                    or (self.status == "completed" and origin.action_fence != self.fence)):
                raise ValueError("Plan authoring action differs from its immutable origin")
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
    selection_anchor: PlanActionSelectionAnchorV1 | None = None


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
