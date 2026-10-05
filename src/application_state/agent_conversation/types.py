"""Typed records and commands for provider-neutral Agent conversations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Resolution = Literal["resolved", "absent", "unresolved", "unavailable"]
ConversationStatus = Literal["active", "archived"]
TurnStatus = Literal["accepted", "running", "completed", "failed", "interrupted"]
CommandKind = Literal["new", "archive", "reopen"]
TurnClaimDisposition = Literal["claimed", "pending", "completed"]


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _fingerprint_compatible_payload(value: object) -> object:
    """Omit additive null fields so legacy provenance and request hashes stay stable."""
    if isinstance(value, list):
        return [_fingerprint_compatible_payload(item) for item in value]
    if isinstance(value, dict):
        is_turn_submission = {
            "conversation_id",
            "expected_conversation_revision",
            "user_text",
            "provenance",
        }.issubset(value)
        is_provenance = {
            "surface_resolution",
            "primary_work",
            "selected_object",
        }.issubset(value)
        is_reference = {
            "resolution",
            "kind",
            "object_id",
            "revision",
            "content_sha256",
        }.issubset(value)
        return {
            key: _fingerprint_compatible_payload(item)
            for key, item in value.items()
            if not (
                item is None
                and (
                    (key == "surface_instance_id" and is_provenance)
                    or (
                        key in {"submitted_intent_v2", "graph_context_receipt"}
                        and is_turn_submission
                    )
                    or (
                        key in {"object_revision", "work_revision_id", "revision_n"}
                        and is_reference
                    )
                )
            )
        }
    return value


def request_fingerprint(value: BaseModel) -> str:
    """Hash a typed request for idempotency; request JSON is never persisted."""
    payload = value.model_dump(
        mode="json",
        exclude={
            "command_id",
            "idempotency_key",
            "submitted_intent_v1",
            "submitted_intent_v2",
        },
    )
    return _fingerprint(_fingerprint_compatible_payload(payload))


def turn_idempotency_fingerprint(
    world_id: str, user_text: str, provenance: "TurnProvenance"
) -> str:
    """Fingerprint turn meaning, independent of conversation routing and CAS revision."""

    return _fingerprint(
        _fingerprint_compatible_payload(
            {
                "world_id": world_id,
                "user_text": user_text,
                "provenance": provenance.model_dump(mode="json"),
            }
        )
    )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class HistoricalReference(StrictModel):
    """Historical typed identity; never a current-context or permission grant."""

    resolution: Resolution
    kind: str | None = None
    object_id: str | None = None
    revision: str | None = None
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    object_revision: int | None = Field(default=None, strict=True, ge=1)
    work_revision_id: UUID | None = None
    revision_n: int | None = Field(default=None, strict=True, ge=1)

    @model_validator(mode="after")
    def validate_resolution(self) -> "HistoricalReference":
        typed_content_revision = (
            self.object_revision,
            self.work_revision_id,
            self.revision_n,
        )
        has_typed_content_revision = any(
            value is not None for value in typed_content_revision
        )
        if has_typed_content_revision and not all(
            value is not None for value in typed_content_revision
        ):
            raise ValueError(
                "Content object revision, WorkRevision ID, and revision number must be supplied together"
            )
        if has_typed_content_revision and (
            self.resolution != "resolved" or self.content_sha256 is None
        ):
            raise ValueError(
                "typed Content revisions require a resolved reference and full content digest"
            )
        if self.resolution == "resolved":
            if (
                not self.kind
                or not self.kind.strip()
                or not self.object_id
                or not self.object_id.strip()
            ):
                raise ValueError("resolved references require kind and object_id")
        elif self.resolution == "absent" and any(
            value is not None
            for value in (
                self.kind,
                self.object_id,
                self.revision,
                self.content_sha256,
                self.object_revision,
                self.work_revision_id,
                self.revision_n,
            )
        ):
            raise ValueError("absent references cannot carry an object identity")
        if self.kind is not None and not self.kind.strip():
            raise ValueError("reference kind cannot be blank")
        if self.object_id is not None and not self.object_id.strip():
            raise ValueError("reference object_id cannot be blank")
        return self


PlanPlayableKind = Literal["scene", "beat", "choice", "option"]
PlayableMarkerGrammarVersion = Literal["v1", "v2"]
PLAN_PLAYABLE_TARGET_SCHEMA = "dmb_plan_playable_target_v1"
PLAN_PLAYABLE_TARGET_REFERENCE_KIND = "dmb_plan_playable_target_v1"
_PLAN_PLAYABLE_ID_PATTERN = r"^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$"


class SubmittedPlanPlayableTargetV1(StrictModel):
    """Client-supplied identity only; marker grammar remains server-derived."""

    schema_: Literal["dmb_plan_playable_target_v1"] = Field(alias="schema")
    kind: PlanPlayableKind
    id: str = Field(min_length=6, max_length=135, pattern=_PLAN_PLAYABLE_ID_PATTERN)

    @model_validator(mode="after")
    def validate_target(self) -> "SubmittedPlanPlayableTargetV1":
        if not self.id.startswith(f"{self.kind}:"):
            raise ValueError("Playable target id prefix must match its kind")
        return self


class PlanPlayableTargetReceiptV1(StrictModel):
    """Server-validated target plus the grammar version of its pinned Plan."""

    schema_: Literal["dmb_plan_playable_target_receipt_v1"] = Field(alias="schema")
    kind: PlanPlayableKind
    id: str = Field(min_length=6, max_length=135, pattern=_PLAN_PLAYABLE_ID_PATTERN)
    marker_grammar_version: PlayableMarkerGrammarVersion

    @model_validator(mode="after")
    def validate_target(self) -> "PlanPlayableTargetReceiptV1":
        if not self.id.startswith(f"{self.kind}:"):
            raise ValueError("Playable target id prefix must match its kind")
        return self


def encode_plan_playable_target_reference(
    receipt: PlanPlayableTargetReceiptV1,
) -> HistoricalReference:
    """Encode a typed receipt in an existing supporting-reference row."""
    return HistoricalReference(
        resolution="resolved",
        kind=PLAN_PLAYABLE_TARGET_REFERENCE_KIND,
        object_id=receipt.id,
        revision=receipt.marker_grammar_version,
    )


def decode_plan_playable_target_reference(
    reference: HistoricalReference,
) -> PlanPlayableTargetReceiptV1 | None:
    """Decode only the reserved target codec; reject malformed stored rows."""
    if reference.kind != PLAN_PLAYABLE_TARGET_REFERENCE_KIND:
        return None
    if (
        reference.resolution != "resolved"
        or reference.object_id is None
        or reference.revision not in {"v1", "v2"}
        or reference.content_sha256 is not None
        or reference.object_revision is not None
        or reference.work_revision_id is not None
        or reference.revision_n is not None
    ):
        raise ValueError("stored Playable target reference is malformed")
    kind, separator, _ = reference.object_id.partition(":")
    if not separator or kind not in {"scene", "beat", "choice", "option"}:
        raise ValueError("stored Playable target identity is malformed")
    return PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind=kind,
        id=reference.object_id,
        marker_grammar_version=reference.revision,
    )


class PlanAskContextBasis(StrictModel):
    """Server-resolved committed Plan basis used only to filter Ask history."""

    world_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=128)
    object_revision: int = Field(strict=True, ge=1)
    work_revision_id: UUID
    revision_n: int = Field(strict=True, ge=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_basis(self) -> "PlanAskContextBasis":
        if self.world_id != self.world_id.strip():
            raise ValueError(
                "Plan Ask basis World must not contain surrounding whitespace"
            )
        if not self.world_id.strip():
            raise ValueError("Plan Ask basis World is required")
        if self.document_id != self.document_id.strip():
            raise ValueError(
                "Plan Ask basis document must not contain surrounding whitespace"
            )
        if not self.document_id.strip():
            raise ValueError("Plan Ask basis document is required")
        return self


class CompletedPlanAskPair(StrictModel):
    """Visible, safe Ask pair with stable source-local merge metadata."""

    source_kind: Literal["ask"] = "ask"
    source_sequence: int = Field(strict=True, ge=1)
    source_record_id: UUID
    accepted_at: datetime
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_visible_text(self) -> "CompletedPlanAskPair":
        if not self.question.strip() or not self.answer.strip():
            raise ValueError(
                "completed Plan Ask pairs require visible question and answer"
            )
        return self


class TurnProvenance(StrictModel):
    world_id: str
    surface_resolution: Resolution
    surface_id: str | None = None
    surface_instance_id: str | None = None
    primary_work: HistoricalReference
    supporting_work: list[HistoricalReference] = Field(
        default_factory=list, max_length=32
    )
    selected_object: HistoricalReference

    @model_validator(mode="after")
    def validate_provenance(self) -> "TurnProvenance":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if self.surface_resolution == "resolved":
            if not self.surface_id or not self.surface_id.strip():
                raise ValueError("resolved surface requires surface_id")
        elif self.surface_resolution == "absent" and self.surface_id is not None:
            raise ValueError("absent surface cannot carry surface_id")
        if self.surface_id is not None and not self.surface_id.strip():
            raise ValueError("surface_id cannot be blank")
        if self.surface_instance_id is not None:
            if not self.surface_instance_id.strip():
                raise ValueError("surface_instance_id cannot be blank")
            if self.surface_resolution != "resolved":
                raise ValueError(
                    "surface instance identity requires a resolved surface"
                )
        if self.surface_resolution == "absent" and self.surface_instance_id is not None:
            raise ValueError("absent surface cannot carry surface_instance_id")
        target_references = [
            reference
            for reference in self.supporting_work
            if reference.kind == PLAN_PLAYABLE_TARGET_REFERENCE_KIND
        ]
        if len(target_references) > 1:
            raise ValueError("turn provenance cannot carry duplicate Playable targets")
        if target_references:
            decode_plan_playable_target_reference(target_references[0])
            primary = self.primary_work
            if (
                self.surface_id != "plan"
                or self.surface_resolution != "resolved"
                or primary.resolution != "resolved"
                or primary.kind != "plan"
                or primary.object_revision is None
                or primary.work_revision_id is None
                or primary.revision_n is None
                or primary.content_sha256 is None
                or self.selected_object.resolution != "absent"
            ):
                raise ValueError(
                    "Playable target provenance requires an exact Plan basis and no Graph selection"
                )
        return self


class SubmittedPrimaryWorkIntentV1(StrictModel):
    kind: Literal["plan", "build", "run", "combat"]
    object_id: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(strict=True, ge=1)
    expected_revision_n: int | None = Field(default=None, strict=True, ge=1)
    expected_content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_plan_basis(self) -> "SubmittedPrimaryWorkIntentV1":
        has_revision_n = self.expected_revision_n is not None
        has_digest = self.expected_content_sha256 is not None
        if has_revision_n != has_digest:
            raise ValueError(
                "submitted Plan revision and digest must be supplied together"
            )
        if self.kind != "plan" and (has_revision_n or has_digest):
            raise ValueError("submitted Plan basis is only valid for Plan work")
        return self


class SubmittedGraphFocusIntentV1(StrictModel):
    kind: Literal["none", "session"]
    session_id: str | None = Field(default=None, max_length=128)
    campaign_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_focus(self) -> "SubmittedGraphFocusIntentV1":
        if self.kind == "none" and (
            self.session_id is not None or self.campaign_id is not None
        ):
            raise ValueError("none submitted graph focus cannot carry identities")
        if self.kind == "session" and not self.session_id:
            raise ValueError("session submitted graph focus requires session_id")
        return self


class SubmittedGraphRequestIntentV1(StrictModel):
    mode: Literal["none", "world", "campaign"]
    world_id: str | None = Field(default=None, max_length=128)
    campaign_id: str | None = Field(default=None, max_length=128)
    revision_pin: str | None = Field(default=None, max_length=256)
    focus: SubmittedGraphFocusIntentV1 | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "SubmittedGraphRequestIntentV1":
        if self.mode == "none" and any(
            value is not None
            for value in (
                self.world_id,
                self.campaign_id,
                self.revision_pin,
                self.focus,
            )
        ):
            raise ValueError("none submitted graph request cannot carry scope or focus")
        if self.mode == "world" and (not self.world_id or self.focus is None):
            raise ValueError("world submitted graph request requires World and focus")
        if self.mode == "campaign" and (not self.campaign_id or self.focus is None):
            raise ValueError(
                "campaign submitted graph request requires campaign and focus"
            )
        return self


class SubmittedGraphSelectionIntentV1(StrictModel):
    node_id: str = Field(min_length=1, max_length=256)


class SubmittedTurnIntentV1(StrictModel):
    """Stable, normalized caller intent; excludes resolver output and routing CAS."""

    schema_: Literal["dmb_agent_submitted_turn_intent_v1"] = Field(
        default="dmb_agent_submitted_turn_intent_v1", alias="schema"
    )
    world_id: str = Field(min_length=1, max_length=128)
    client_thread_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=8000)
    surface_id: str = Field(min_length=1, max_length=64)
    surface_instance_id: str = Field(min_length=1, max_length=128)
    client_work_state: Literal["none", "saved_clean", "saved_dirty", "new_unsaved"]
    primary_work: SubmittedPrimaryWorkIntentV1 | None
    playable_target: SubmittedPlanPlayableTargetV1 | None = None
    graph_request: SubmittedGraphRequestIntentV1
    graph_selection: SubmittedGraphSelectionIntentV1 | None

    @model_validator(mode="after")
    def validate_identity(self) -> "SubmittedTurnIntentV1":
        if (
            not self.world_id.strip()
            or not self.client_thread_id.strip()
            or not self.message.strip()
        ):
            raise ValueError(
                "submitted World, client thread, and message must be non-blank"
            )
        if not self.surface_id.strip() or not self.surface_instance_id.strip():
            raise ValueError("submitted surface identities must be non-blank")
        if (
            self.surface_id == "plan"
            and self.primary_work is not None
            and self.primary_work.kind == "plan"
            and self.primary_work.expected_revision_n is None
        ):
            raise ValueError(
                "Plan content turns require the exact committed content pin"
            )
        if (
            self.graph_request.mode == "world"
            and self.graph_request.world_id != self.world_id
        ):
            raise ValueError("submitted graph World must match submitted turn World")
        if self.graph_selection is not None and self.graph_request.mode == "none":
            raise ValueError("submitted graph selection requires a graph request")
        if self.playable_target is not None and (
            self.surface_id != "plan"
            or self.primary_work is None
            or self.primary_work.kind != "plan"
            or self.client_work_state not in {"saved_clean", "saved_dirty"}
            or self.graph_request.mode != "none"
            or self.graph_selection is not None
        ):
            raise ValueError(
                "Playable target intent requires a graphless saved Plan turn"
            )
        return self


def submitted_turn_intent_fingerprint_v1(intent: SubmittedTurnIntentV1) -> str:
    """Hash canonical submitted semantics, never current resolver output."""
    payload = intent.model_dump(
        mode="json", by_alias=True, exclude={"client_thread_id"}
    )
    # Older no-target fingerprints were computed before this optional field
    # existed. Omit its null shape byte-for-byte; targeted intents include it.
    if payload.get("playable_target") is None:
        payload.pop("playable_target", None)
    return _fingerprint(payload)


class PlanContextPolicyV1(StrictModel):
    schema_: Literal["dmb_plan_context_policy_v1"] = Field(
        default="dmb_plan_context_policy_v1", alias="schema"
    )
    policy: Literal["auto_plan_world"]


class SubmittedTurnIntentV2(StrictModel):
    """Normalized explicit Plan/World Graph policy intent, before resolution."""

    schema_: Literal["dmb_agent_submitted_turn_intent_v2"] = Field(
        default="dmb_agent_submitted_turn_intent_v2", alias="schema"
    )
    world_id: str = Field(min_length=1, max_length=128)
    client_thread_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=8000)
    surface_id: Literal["plan"]
    surface_instance_id: str = Field(min_length=1, max_length=128)
    client_work_state: Literal["saved_clean", "saved_dirty"]
    primary_work: SubmittedPrimaryWorkIntentV1
    plan_context_policy: PlanContextPolicyV1
    playable_target: SubmittedPlanPlayableTargetV1 | None = None
    graph_request: SubmittedGraphRequestIntentV1
    graph_selection: SubmittedGraphSelectionIntentV1 | None

    @model_validator(mode="after")
    def validate_policy_turn(self) -> "SubmittedTurnIntentV2":
        if (
            not self.world_id.strip()
            or not self.client_thread_id.strip()
            or not self.message.strip()
        ):
            raise ValueError(
                "submitted World, client thread, and message must be non-blank"
            )
        if not self.surface_instance_id.strip():
            raise ValueError("submitted surface instance must be non-blank")
        if (
            self.primary_work.kind != "plan"
            or self.primary_work.expected_revision_n is None
        ):
            raise ValueError(
                "auto_plan_world requires the exact committed Plan content pin"
            )
        if self.graph_request.mode != "none" or self.graph_selection is not None:
            raise ValueError(
                "auto_plan_world requires generic graph_request=none and no selection"
            )
        if self.playable_target is not None and (
            self.playable_target.kind not in {"scene", "beat", "choice", "option"}
        ):
            raise ValueError("auto_plan_world playable focus is invalid")
        return self


def submitted_turn_intent_fingerprint_v2(intent: SubmittedTurnIntentV2) -> str:
    """Fingerprint only normalized caller intent, excluding routing thread identity."""
    payload = intent.model_dump(
        mode="json", by_alias=True, exclude={"client_thread_id"}
    )
    return _fingerprint(payload)


class PlanWorldGraphAuthorityV1(StrictModel):
    managed_world_id: str = Field(min_length=1, max_length=128)
    native_world_id: str = Field(min_length=1, max_length=128)
    binding_version: int = Field(strict=True, ge=1)
    scope_mode: Literal["world"]
    campaign_id: None = None
    admissibility_version: str = Field(min_length=1, max_length=128)
    graph_revision: str = Field(min_length=1, max_length=256)


class PlanWorldGraphPacketV1(StrictModel):
    schema_: Literal["dmb_plan_world_graph_packet_v1"] = Field(
        default="dmb_plan_world_graph_packet_v1", alias="schema"
    )
    packet_serializer_version: Literal["canonical-json-utf8-v1"]
    selection_policy_version: str = Field(min_length=1, max_length=128)
    evidence_sufficiency_policy_version: str = Field(min_length=1, max_length=128)
    retrieval_packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_assertion_ids: list[str] = Field(max_length=512)
    candidate_relationship_ids: list[str] = Field(max_length=512)
    candidate_evidence_ref_ids: list[str] = Field(max_length=1024)
    retrieval_status: Literal["complete", "empty"]
    evidence_sufficiency_status: Literal["sufficient", "insufficient"]
    result_limit: int = Field(strict=True, ge=0)
    coverage_status: Literal["complete", "incomplete"]
    truncated: bool
    omission_reasons: list[str] = Field(max_length=32)

    @model_validator(mode="after")
    def validate_packet(self) -> "PlanWorldGraphPacketV1":
        for name in (
            "candidate_assertion_ids",
            "candidate_relationship_ids",
            "candidate_evidence_ref_ids",
        ):
            values = getattr(self, name)
            if any(not value.strip() for value in values):
                raise ValueError(f"{name} cannot contain blank IDs")
            if values != sorted(set(values)):
                raise ValueError(f"{name} must be sorted and unique")
        if self.retrieval_status == "empty" and (
            self.candidate_assertion_ids
            or self.candidate_relationship_ids
            or self.candidate_evidence_ref_ids
            or self.evidence_sufficiency_status != "insufficient"
        ):
            raise ValueError(
                "empty retrieval requires no candidates and insufficient evidence"
            )
        if self.truncated and self.coverage_status != "incomplete":
            raise ValueError("truncated Graph packet requires incomplete coverage")
        if any(not reason.strip() for reason in self.omission_reasons):
            raise ValueError("Graph packet omission reasons cannot be blank")
        return self


class PlanWorldGraphSourceTokenAccountingV1(StrictModel):
    source_kind: Literal["plan", "history", "graph", "instructions", "tools", "message"]
    source_id: str = Field(min_length=1, max_length=256)
    input_tokens: int = Field(strict=True, ge=0)


class PlanWorldGraphHistoryPinV1(StrictModel):
    turn_id: UUID
    answer_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlanWorldGraphAssembledInputV1(StrictModel):
    assembler_version: str = Field(min_length=1, max_length=128)
    budget_policy_version: str = Field(min_length=1, max_length=128)
    provider_model_name: str = Field(min_length=1, max_length=128)
    provider_model_version: str = Field(min_length=1, max_length=128)
    tokenizer_name: str = Field(min_length=1, max_length=128)
    tokenizer_version: str = Field(min_length=1, max_length=128)
    provider_envelope_input_tokens: int = Field(strict=True, ge=0)
    output_token_reserve: int = Field(strict=True, ge=0)
    context_window_limit: int = Field(strict=True, ge=1)
    packet_disposition: Literal["included", "omitted_insufficient"]
    packet_disposition_reason: Literal["insufficient_evidence"] | None = None
    dispatched_packet_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    dispatched_assertion_ids: list[str] = Field(max_length=512)
    dispatched_relationship_ids: list[str] = Field(max_length=512)
    dispatched_evidence_ref_ids: list[str] = Field(max_length=1024)
    source_token_accounting: list[PlanWorldGraphSourceTokenAccountingV1] = Field(
        max_length=128
    )
    included_history: list[PlanWorldGraphHistoryPinV1] = Field(max_length=64)
    assembled_input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_assembled_input(self) -> "PlanWorldGraphAssembledInputV1":
        for name in (
            "dispatched_assertion_ids",
            "dispatched_relationship_ids",
            "dispatched_evidence_ref_ids",
        ):
            values = getattr(self, name)
            if any(not value.strip() for value in values):
                raise ValueError(f"{name} cannot contain blank IDs")
            if values != sorted(set(values)):
                raise ValueError(f"{name} must be sorted and unique")
        if (
            self.provider_envelope_input_tokens + self.output_token_reserve
            > self.context_window_limit
        ):
            raise ValueError(
                "provider envelope plus output reserve exceeds context window"
            )
        included = self.packet_disposition == "included"
        if included != (self.dispatched_packet_sha256 is not None):
            raise ValueError("dispatched packet digest must match packet disposition")
        if included:
            if self.packet_disposition_reason is not None:
                raise ValueError("included packet cannot carry an omission reason")
        elif (
            self.packet_disposition_reason != "insufficient_evidence"
            or self.dispatched_assertion_ids
            or self.dispatched_relationship_ids
            or self.dispatched_evidence_ref_ids
        ):
            raise ValueError(
                "omitted insufficient packet cannot carry Graph payload IDs"
            )
        return self


class PlanWorldGraphContextReceiptV1(StrictModel):
    schema_: Literal["dmb_agent_plan_world_graph_context_receipt_v1"] = Field(
        default="dmb_agent_plan_world_graph_context_receipt_v1", alias="schema"
    )
    receipt_serializer_version: Literal["canonical-json-utf8-v1"]
    context_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan_context_policy: PlanContextPolicyV1
    plan_basis: PlanAskContextBasis
    playable_target: PlanPlayableTargetReceiptV1 | None
    graph_authority: PlanWorldGraphAuthorityV1
    graph_packet: PlanWorldGraphPacketV1
    assembled_input: PlanWorldGraphAssembledInputV1
    evidence_mode: Literal["metadata_only"]
    source_opened: Literal[False]

    @model_validator(mode="after")
    def validate_receipt(self) -> "PlanWorldGraphContextReceiptV1":
        if self.graph_authority.managed_world_id != self.plan_basis.world_id:
            raise ValueError("Graph authority managed World must match Plan basis")
        packet = self.graph_packet
        assembled = self.assembled_input
        if assembled.packet_disposition == "omitted_insufficient":
            if packet.evidence_sufficiency_status != "insufficient":
                raise ValueError("only insufficient evidence may be omitted")
        elif packet.evidence_sufficiency_status != "sufficient":
            raise ValueError("included Graph packet requires sufficient evidence")
        if not set(assembled.dispatched_assertion_ids).issubset(
            packet.candidate_assertion_ids
        ):
            raise ValueError(
                "dispatched assertion IDs must come from retrieved candidates"
            )
        if not set(assembled.dispatched_relationship_ids).issubset(
            packet.candidate_relationship_ids
        ):
            raise ValueError(
                "dispatched relationship IDs must come from retrieved candidates"
            )
        if not set(assembled.dispatched_evidence_ref_ids).issubset(
            packet.candidate_evidence_ref_ids
        ):
            raise ValueError(
                "dispatched evidence IDs must come from retrieved candidates"
            )
        if self.context_receipt_sha256 != plan_world_graph_context_receipt_digest(self):
            raise ValueError("Graph context receipt digest does not match its contents")
        return self


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def plan_world_graph_context_receipt_digest(
    receipt: PlanWorldGraphContextReceiptV1,
) -> str:
    payload = receipt.model_dump(
        mode="json", by_alias=True, exclude={"context_receipt_sha256"}
    )
    return _canonical_sha256(payload)


class PlanWorldGraphClaimSegmentV1(StrictModel):
    kind: Literal["graph_claim"]
    claim_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4000)
    target_kind: Literal["assertion", "relationship"]
    target_id: str = Field(min_length=1, max_length=256)
    graph_revision: str = Field(min_length=1, max_length=256)
    evidence_ref_ids: list[str] = Field(min_length=1, max_length=64)


class PlanWorldGraphPlanClaimSegmentV1(StrictModel):
    kind: Literal["plan_claim"]
    text: str = Field(min_length=1, max_length=4000)
    plan_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlanWorldGraphProposalSegmentV1(StrictModel):
    kind: Literal["proposal"]
    text: str = Field(min_length=1, max_length=4000)
    label: Literal["invented_idea"]


class PlanWorldGraphConnectiveSegmentV1(StrictModel):
    kind: Literal["connective"]
    text: str = Field(min_length=1, max_length=4000)


PlanWorldGraphAnswerSegmentV1 = (
    PlanWorldGraphClaimSegmentV1
    | PlanWorldGraphPlanClaimSegmentV1
    | PlanWorldGraphProposalSegmentV1
    | PlanWorldGraphConnectiveSegmentV1
)


class PlanWorldGraphCitationV1(StrictModel):
    claim_id: str = Field(min_length=1, max_length=128)
    target_kind: Literal["assertion", "relationship"]
    target_id: str = Field(min_length=1, max_length=256)
    graph_revision: str = Field(min_length=1, max_length=256)
    evidence_ref_ids: list[str] = Field(min_length=1, max_length=64)
    source_opened: Literal[False]


class PlanWorldGraphCitationMapV1(StrictModel):
    schema_: Literal["dmb_graph_citation_map_v1"] = Field(
        default="dmb_graph_citation_map_v1", alias="schema"
    )
    context_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entries: list[PlanWorldGraphCitationV1] = Field(max_length=128)


class PlanWorldGraphCompletionV1(StrictModel):
    schema_: Literal["dmb_plan_world_graph_completion_v1"] = Field(
        default="dmb_plan_world_graph_completion_v1", alias="schema"
    )
    context_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    answer_basis: Literal["committed_plan", "committed_plan_plus_world_graph"]
    answer_context_status: Literal[
        "graph_grounded",
        "graph_grounded_partial",
        "plan_only_insufficient_evidence",
        "plan_only_graph_unused",
    ]
    answer_segments: list[PlanWorldGraphAnswerSegmentV1] = Field(
        min_length=1, max_length=128
    )
    citation_map: PlanWorldGraphCitationMapV1 | None

    @model_validator(mode="after")
    def validate_completion_shape(self) -> "PlanWorldGraphCompletionV1":
        graph_claims = [
            segment
            for segment in self.answer_segments
            if isinstance(segment, PlanWorldGraphClaimSegmentV1)
        ]
        expected_basis = (
            "committed_plan_plus_world_graph" if graph_claims else "committed_plan"
        )
        if self.answer_basis != expected_basis:
            raise ValueError("answer basis must follow the typed answer segments")
        if (
            self.citation_map is not None
            and self.citation_map.context_receipt_sha256 != self.context_receipt_sha256
        ):
            raise ValueError("citation map must bind the completion receipt digest")
        plan_only = self.answer_context_status in {
            "plan_only_insufficient_evidence",
            "plan_only_graph_unused",
        }
        if plan_only and (graph_claims or self.citation_map is not None):
            raise ValueError(
                "Plan-only completion cannot carry Graph claims or citations"
            )
        if not plan_only:
            if (
                not graph_claims
                or self.citation_map is None
                or not self.citation_map.entries
            ):
                raise ValueError(
                    "Graph-grounded completion requires claims and citations"
                )
            claims_by_id = {segment.claim_id: segment for segment in graph_claims}
            entries = self.citation_map.entries
            entry_ids = [entry.claim_id for entry in entries]
            if (
                len(claims_by_id) != len(graph_claims)
                or len(entries) != len(graph_claims)
                or len(set(entry_ids)) != len(entry_ids)
            ):
                raise ValueError(
                    "Graph citation map must correspond one-to-one with claims"
                )
            for entry in entries:
                claim = claims_by_id.get(entry.claim_id)
                if claim is None or (
                    claim.target_kind != entry.target_kind
                    or claim.target_id != entry.target_id
                    or claim.graph_revision != entry.graph_revision
                    or sorted(set(claim.evidence_ref_ids))
                    != sorted(set(entry.evidence_ref_ids))
                ):
                    raise ValueError("citation map entry must match its Graph claim")
                if entry.evidence_ref_ids != sorted(set(entry.evidence_ref_ids)):
                    raise ValueError("citation refs must be sorted and unique")
        return self


def validate_completion_against_receipt(
    completion: PlanWorldGraphCompletionV1,
    receipt: PlanWorldGraphContextReceiptV1,
) -> None:
    if completion.context_receipt_sha256 != receipt.context_receipt_sha256:
        raise ValueError("completion must bind the exact stored Graph receipt")
    packet = receipt.graph_packet
    assembled = receipt.assembled_input
    claims = [
        segment
        for segment in completion.answer_segments
        if isinstance(segment, PlanWorldGraphClaimSegmentV1)
    ]
    for segment in completion.answer_segments:
        if isinstance(segment, PlanWorldGraphPlanClaimSegmentV1) and (
            segment.plan_content_sha256 != receipt.plan_basis.content_sha256
        ):
            raise ValueError("Plan claim attribution must match the frozen Plan digest")

    if completion.answer_context_status == "plan_only_insufficient_evidence":
        if packet.evidence_sufficiency_status != "insufficient":
            raise ValueError(
                "insufficient Plan-only status requires insufficient receipt evidence"
            )
    elif completion.answer_context_status == "plan_only_graph_unused":
        if packet.evidence_sufficiency_status != "sufficient":
            raise ValueError("unused Graph status requires sufficient receipt evidence")
    elif completion.answer_context_status == "graph_grounded":
        if (
            packet.evidence_sufficiency_status != "sufficient"
            or packet.coverage_status != "complete"
            or packet.truncated
        ):
            raise ValueError(
                "fully grounded status requires sufficient complete untruncated evidence"
            )
    elif completion.answer_context_status == "graph_grounded_partial":
        if packet.evidence_sufficiency_status != "sufficient" or (
            packet.coverage_status == "complete" and not packet.truncated
        ):
            raise ValueError(
                "partially grounded status requires incomplete or truncated evidence"
            )

    dispatched = {
        "assertion": set(assembled.dispatched_assertion_ids),
        "relationship": set(assembled.dispatched_relationship_ids),
    }
    candidate_evidence = set(packet.candidate_evidence_ref_ids)
    dispatched_evidence = set(assembled.dispatched_evidence_ref_ids)
    if claims:
        if assembled.packet_disposition != "included":
            raise ValueError("Graph claims require an included Graph packet")
        if completion.citation_map is None:
            raise ValueError("Graph claims require a citation map")
        entries = {entry.claim_id: entry for entry in completion.citation_map.entries}
        if len(entries) != len(completion.citation_map.entries):
            raise ValueError("citation map claim IDs must be unique")
        for claim in claims:
            entry = entries.get(claim.claim_id)
            if entry is None:
                raise ValueError(
                    "every Graph claim requires exactly one citation entry"
                )
            if claim.target_id not in dispatched[claim.target_kind]:
                raise ValueError("Graph claim target must be in the dispatched packet")
            if claim.graph_revision != receipt.graph_authority.graph_revision:
                raise ValueError("Graph claim must use the frozen Graph revision")
            if not set(claim.evidence_ref_ids).issubset(candidate_evidence):
                raise ValueError(
                    "Graph claim evidence refs must be in the frozen candidate set"
                )
            if not set(claim.evidence_ref_ids).issubset(dispatched_evidence):
                raise ValueError(
                    "Graph claim evidence refs must be in the dispatched packet"
                )
            if claim.evidence_ref_ids != sorted(set(claim.evidence_ref_ids)):
                raise ValueError("Graph claim evidence refs must be sorted and unique")
            if set(entry.evidence_ref_ids) != set(claim.evidence_ref_ids):
                raise ValueError("citation refs must match the Graph claim refs")


class WorldPointer(StrictModel):
    world_id: str
    active_conversation_id: UUID | None
    revision: int = Field(ge=0)


class Conversation(StrictModel):
    conversation_id: UUID
    world_id: str
    status: ConversationStatus
    revision: int = Field(ge=1)
    next_turn_sequence: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ConversationCommand(StrictModel):
    world_id: str
    command_id: UUID
    expected_pointer_revision: int = Field(ge=0)
    expected_active_conversation_id: UUID | None

    @model_validator(mode="after")
    def validate_world(self) -> "ConversationCommand":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        return self


class ArchiveCommand(ConversationCommand):
    conversation_id: UUID


class ReopenCommand(ConversationCommand):
    conversation_id: UUID


class ConversationCommandReceipt(StrictModel):
    world_id: str
    command_id: UUID
    command_kind: CommandKind
    conversation_id: UUID
    active_conversation_id: UUID | None
    pointer_revision: int = Field(ge=0)
    recorded_at: datetime


class TurnSubmission(StrictModel):
    world_id: str
    conversation_id: UUID
    idempotency_key: UUID
    expected_conversation_revision: int = Field(ge=1)
    user_text: str
    provenance: TurnProvenance
    submitted_intent_v1: SubmittedTurnIntentV1 | None = None
    submitted_intent_v2: SubmittedTurnIntentV2 | None = None
    graph_context_receipt: PlanWorldGraphContextReceiptV1 | None = None

    @model_validator(mode="after")
    def validate_submission(self) -> "TurnSubmission":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if not self.user_text.strip():
            raise ValueError("user_text is required")
        if self.provenance.world_id != self.world_id:
            raise ValueError("turn provenance World does not match request World")
        if self.submitted_intent_v1 is not None and (
            self.submitted_intent_v1.world_id != self.world_id
            or self.submitted_intent_v1.message != self.user_text
        ):
            raise ValueError("submitted intent World/message must match the turn")
        if (
            self.submitted_intent_v1 is not None
            and self.submitted_intent_v2 is not None
        ):
            raise ValueError("a turn cannot carry both submitted intent v1 and v2")
        if self.submitted_intent_v2 is not None:
            intent = self.submitted_intent_v2
            if self.graph_context_receipt is None:
                raise ValueError(
                    "auto_plan_world turn requires a frozen Graph context receipt"
                )
            if intent.world_id != self.world_id or intent.message != self.user_text:
                raise ValueError("submitted intent World/message must match the turn")
            receipt = self.graph_context_receipt
            if (
                receipt.plan_context_policy != intent.plan_context_policy
                or receipt.plan_basis.world_id != self.world_id
                or receipt.plan_basis.document_id != intent.primary_work.object_id
                or receipt.plan_basis.object_revision
                != intent.primary_work.expected_revision
                or receipt.plan_basis.revision_n
                != intent.primary_work.expected_revision_n
                or receipt.plan_basis.content_sha256
                != intent.primary_work.expected_content_sha256
                or not _receipt_target_matches_intent(
                    receipt.playable_target, intent.playable_target
                )
                or receipt.graph_authority.managed_world_id != self.world_id
                or self.provenance.world_id != self.world_id
                or self.provenance.surface_id != "plan"
                or self.provenance.surface_instance_id != intent.surface_instance_id
                or self.provenance.primary_work.kind != "plan"
                or self.provenance.primary_work.object_id
                != receipt.plan_basis.document_id
                or self.provenance.primary_work.object_revision
                != receipt.plan_basis.object_revision
                or self.provenance.primary_work.work_revision_id
                != receipt.plan_basis.work_revision_id
                or self.provenance.primary_work.revision_n
                != receipt.plan_basis.revision_n
                or self.provenance.primary_work.content_sha256
                != receipt.plan_basis.content_sha256
            ):
                raise ValueError(
                    "Graph context receipt must match the submitted Plan intent"
                )
        elif self.graph_context_receipt is not None:
            raise ValueError("Graph context receipt requires submitted intent v2")
        return self


def _receipt_target_matches_intent(
    receipt_target: PlanPlayableTargetReceiptV1 | None,
    intent_target: SubmittedPlanPlayableTargetV1 | None,
) -> bool:
    """Compare shared target identity while retaining receipt-only grammar metadata."""
    if receipt_target is None or intent_target is None:
        return receipt_target is None and intent_target is None
    # marker_grammar_version is intentionally receipt-only: its typed value and
    # inclusion in the receipt digest remain independently validated/persisted.
    return (
        receipt_target.kind == intent_target.kind
        and receipt_target.id == intent_target.id
    )


class Turn(StrictModel):
    turn_id: UUID
    conversation_id: UUID
    world_id: str
    idempotency_key: UUID
    sequence: int = Field(ge=1)
    revision: int = Field(ge=1)
    status: TurnStatus
    user_text: str
    assistant_text: str | None
    failure_code: str | None
    provenance: TurnProvenance
    submitted_intent_fingerprint_v1: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    submitted_intent_fingerprint_v2: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    graph_context_receipt: PlanWorldGraphContextReceiptV1 | None = None
    completion: PlanWorldGraphCompletionV1 | None = None
    attempt: int = Field(ge=0)
    claim_expires_at: datetime | None = None
    accepted_at: datetime
    completed_at: datetime | None
    updated_at: datetime

    @model_validator(mode="after")
    def validate_claim_expiry(self) -> "Turn":
        if self.status != "running" and self.claim_expires_at is not None:
            raise ValueError("only a running turn can carry an active claim expiry")
        if (
            self.submitted_intent_fingerprint_v1 is not None
            and self.submitted_intent_fingerprint_v2 is not None
        ):
            raise ValueError("turn cannot carry both submitted-intent fingerprints")
        if (
            self.graph_context_receipt is not None
            and self.submitted_intent_fingerprint_v2 is None
        ):
            raise ValueError("Graph receipt requires a v2 submitted-intent fingerprint")
        if self.completion is not None:
            if self.graph_context_receipt is None:
                raise ValueError("Graph completion requires its frozen context receipt")
            validate_completion_against_receipt(
                self.completion, self.graph_context_receipt
            )
        return self


class TurnResult(StrictModel):
    world_id: str
    conversation_id: UUID
    turn_id: UUID
    expected_revision: int = Field(ge=1)
    assistant_text: str
    completion: PlanWorldGraphCompletionV1 | None = None

    @model_validator(mode="after")
    def validate_text(self) -> "TurnResult":
        if not self.assistant_text.strip():
            raise ValueError("assistant_text is required")
        return self


class TurnFailure(StrictModel):
    world_id: str
    conversation_id: UUID
    turn_id: UUID
    expected_revision: int = Field(ge=1)
    failure_code: str

    @model_validator(mode="after")
    def validate_code(self) -> "TurnFailure":
        if not self.failure_code.strip():
            raise ValueError("failure_code is required")
        return self


class TurnClaimReceipt(StrictModel):
    disposition: TurnClaimDisposition
    turn: Turn


class DraftSave(StrictModel):
    world_id: str
    conversation_id: UUID
    draft_id: UUID
    expected_revision: int = Field(ge=0)
    body: str
    provenance: TurnProvenance
    explicitly_revalidated_source: bool = False

    @model_validator(mode="after")
    def validate_draft(self) -> "DraftSave":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if self.provenance.world_id != self.world_id:
            raise ValueError("draft provenance World does not match request World")
        return self


class Draft(StrictModel):
    world_id: str
    conversation_id: UUID
    draft_id: UUID
    revision: int = Field(ge=1)
    body: str
    provenance: TurnProvenance
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DraftSubmit(StrictModel):
    world_id: str
    conversation_id: UUID
    draft_id: UUID
    expected_draft_revision: int = Field(ge=1)
    idempotency_key: UUID
    expected_conversation_revision: int = Field(ge=1)
    provenance: TurnProvenance

    @model_validator(mode="after")
    def validate_submit(self) -> "DraftSubmit":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if self.provenance.world_id != self.world_id:
            raise ValueError("submission provenance World does not match request World")
        return self


class DraftSubmitReceipt(StrictModel):
    turn: Turn
    draft_id: UUID
    retired_draft_revision: int = Field(ge=1)
    retired_at: datetime


class LegacyTurn(StrictModel):
    source_turn_id: str
    world_id: str
    user_text: str
    assistant_text: str | None
    provenance: TurnProvenance

    @model_validator(mode="after")
    def validate_legacy_turn(self) -> "LegacyTurn":
        if not self.source_turn_id.strip():
            raise ValueError("source_turn_id is required")
        if not self.world_id.strip() or self.provenance.world_id != self.world_id:
            raise ValueError("legacy turn must carry the exact verified World ID")
        if not self.user_text.strip():
            raise ValueError("legacy user_text is required")
        return self


class LegacyImport(StrictModel):
    world_id: str
    source_import_key: str
    source_thread_id: str
    expected_pointer_revision: int = Field(ge=0)
    expected_active_conversation_id: UUID | None
    activate: bool
    turns: list[LegacyTurn] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_import(self) -> "LegacyImport":
        if not self.world_id.strip():
            raise ValueError("world_id is required")
        if not self.source_import_key.strip() or not self.source_thread_id.strip():
            raise ValueError("source import key and thread ID are required")
        if any(turn.world_id != self.world_id for turn in self.turns):
            raise ValueError(
                "every legacy turn must exactly match the verified World ID"
            )
        return self


class LegacyImportReceipt(StrictModel):
    world_id: str
    source_import_key: str
    conversation_id: UUID
    active_conversation_id: UUID | None
    pointer_revision: int
    imported_turn_count: int
    recorded_at: datetime
