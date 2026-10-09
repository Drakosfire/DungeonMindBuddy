"""Typed records and commands for provider-neutral Agent conversations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, NoReturn
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
                        key in {
                            "submitted_intent_v2",
                            "graph_context_receipt",
                            "graph_context_execution",
                        }
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


class PlanWorldGraphCitationV2(StrictModel):
    claim_id: str = Field(min_length=1, max_length=128)
    target_kind: Literal["assertion", "relationship"]
    target_id: str = Field(min_length=1, max_length=256)
    graph_revision: str = Field(min_length=1, max_length=256)
    evidence_ref_ids: list[str] = Field(min_length=1, max_length=64)
    source_read_ids: list[str] = Field(max_length=8)
    source_opened: bool

    @model_validator(mode="after")
    def validate_source_opened(self) -> PlanWorldGraphCitationV2:
        if self.source_opened != bool(self.source_read_ids):
            raise ValueError("source_opened must be derived from source read IDs")
        if any(not value.strip() or value != value.strip() for value in self.source_read_ids):
            raise ValueError("source read IDs must be nonblank and trimmed")
        if self.source_read_ids != sorted(set(self.source_read_ids)):
            raise ValueError("source read IDs must be sorted and unique")
        if any(not value.strip() or value != value.strip() for value in self.evidence_ref_ids):
            raise ValueError("citation refs must be nonblank and trimmed")
        if self.evidence_ref_ids != sorted(set(self.evidence_ref_ids)):
            raise ValueError("citation refs must be sorted and unique")
        return self


class PlanWorldGraphCitationMapV2(StrictModel):
    schema_: Literal["dmb_graph_citation_map_v2"] = Field(
        default="dmb_graph_citation_map_v2", alias="schema"
    )
    context_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entries: list[PlanWorldGraphCitationV2] = Field(max_length=128)


class PlanWorldGraphCompletionV2(StrictModel):
    schema_: Literal["dmb_plan_world_graph_completion_v2"] = Field(
        default="dmb_plan_world_graph_completion_v2", alias="schema"
    )
    context_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    answer_basis: Literal["committed_plan", "committed_plan_plus_world_graph"]
    answer_context_status: Literal[
        "graph_grounded", "graph_grounded_partial",
        "plan_only_insufficient_evidence", "plan_only_graph_unused",
    ]
    answer_segments: list[PlanWorldGraphAnswerSegmentV1] = Field(min_length=1, max_length=128)
    citation_map: PlanWorldGraphCitationMapV2 | None

    @model_validator(mode="after")
    def validate_completion_shape(self) -> PlanWorldGraphCompletionV2:
        graph_claims = [s for s in self.answer_segments if isinstance(s, PlanWorldGraphClaimSegmentV1)]
        if self.answer_basis != ("committed_plan_plus_world_graph" if graph_claims else "committed_plan"):
            raise ValueError("answer basis must follow the typed answer segments")
        if self.citation_map is not None and self.citation_map.context_receipt_sha256 != self.context_receipt_sha256:
            raise ValueError("citation map must bind the completion receipt digest")
        plan_only = self.answer_context_status in {"plan_only_insufficient_evidence", "plan_only_graph_unused"}
        if plan_only and (graph_claims or self.citation_map is not None):
            raise ValueError("Plan-only completion cannot carry Graph claims or citations")
        if not plan_only:
            if not graph_claims or self.citation_map is None or not self.citation_map.entries:
                raise ValueError("Graph-grounded completion requires claims and citations")
            claims = {s.claim_id: s for s in graph_claims}
            entries = self.citation_map.entries
            if len(claims) != len(graph_claims) or len(entries) != len(graph_claims) or len({e.claim_id for e in entries}) != len(entries):
                raise ValueError("Graph citation map must correspond one-to-one with claims")
            for entry in entries:
                claim = claims.get(entry.claim_id)
                if claim is None or (claim.target_kind != entry.target_kind or claim.target_id != entry.target_id or claim.graph_revision != entry.graph_revision or claim.evidence_ref_ids != entry.evidence_ref_ids):
                    raise ValueError("citation map entry must match its Graph claim")
        if len(self.model_dump_json(by_alias=True).encode("utf-8")) > 1_048_576:
            raise ValueError("Graph completion record exceeds the storage size limit")
        return self


PlanWorldGraphCitation = PlanWorldGraphCitationV1 | PlanWorldGraphCitationV2
PlanWorldGraphCitationMap = PlanWorldGraphCitationMapV1 | PlanWorldGraphCitationMapV2
PlanWorldGraphCompletion = PlanWorldGraphCompletionV1 | PlanWorldGraphCompletionV2


class GraphCompletionRejectionCode(str, Enum):
    """Closed internal categories for fixed completion-validation failures."""

    RECEIPT_BINDING = "completion_receipt_binding"
    PLAN_BASIS_ATTRIBUTION = "plan_basis_attribution"
    STATUS_EVIDENCE_MISMATCH = "status_evidence_mismatch"
    GRAPH_PACKET_NOT_INCLUDED = "graph_packet_not_included"
    CITATION_MAP_MISSING = "citation_map_missing"
    CITATION_MAP_CLAIM_SET = "citation_map_claim_set"
    CITATION_ENTRY_MISSING = "citation_entry_missing"
    CLAIM_TARGET_NOT_DISPATCHED = "claim_target_not_dispatched"
    GRAPH_REVISION_MISMATCH = "graph_revision_mismatch"
    EVIDENCE_NOT_CANDIDATE = "evidence_not_candidate"
    EVIDENCE_NOT_DISPATCHED = "evidence_not_dispatched"
    EVIDENCE_ORDER = "evidence_order"
    CITATION_EVIDENCE_MISMATCH = "citation_evidence_mismatch"
    PRODUCING_RESPONSE_MISSING = "producing_response_missing"
    CLAIM_BINDING_SET = "claim_binding_set"
    CLAIM_TARGET_NOT_IN_ENVELOPE = "claim_target_not_in_envelope"
    BINDING_EVENT_DUPLICATE = "binding_event_duplicate"
    BINDING_EVENT_NOT_IN_ENVELOPE = "binding_event_not_in_envelope"
    BINDING_EVENT_SUPPORT_MISMATCH = "binding_event_support_mismatch"
    CLAIM_SUPPORT_MISSING = "claim_support_missing"
    CITED_EVIDENCE_INSUFFICIENT = "cited_evidence_insufficient"
    CITATION_CLAIM_MISMATCH = "citation_claim_mismatch"
    GROUNDED_STATUS_MISMATCH = "grounded_status_mismatch"
    PLAN_ONLY_STATUS_MISMATCH = "plan_only_status_mismatch"


class GraphCompletionValidationError(ValueError):
    """A ValueError with a fixed, non-content-bearing internal rejection code."""

    def __init__(
        self,
        rejection_code: GraphCompletionRejectionCode,
        message: str,
    ) -> None:
        self.rejection_code = rejection_code
        super().__init__(message)


def _reject_graph_completion(
    rejection_code: GraphCompletionRejectionCode,
    message: str,
) -> NoReturn:
    """Raise a backward-compatible ValueError classified by a closed code."""
    raise GraphCompletionValidationError(rejection_code, message)


class PlanAskHistoryAttributionV1(StrictModel):
    """Validated provenance accompanying one completed Plan Graph Ask."""

    schema_: Literal["dmb_plan_ask_history_attribution_v1"] = Field(
        default="dmb_plan_ask_history_attribution_v1", alias="schema"
    )
    source_turn_id: UUID
    source_conversation_id: UUID
    source_sequence: int = Field(strict=True, ge=1)
    source_turn_status: Literal["completed"] = "completed"
    surface_resolution: Literal["resolved"] = "resolved"
    surface_id: Literal["plan"] = "plan"
    surface_instance_id: str = Field(min_length=1, max_length=128)
    plan_basis: PlanAskContextBasis
    playable_target: PlanPlayableTargetReceiptV1 | None
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
    citation_map: PlanWorldGraphCitationMap | None

    @model_validator(mode="after")
    def validate_attribution(self) -> "PlanAskHistoryAttributionV1":
        if (
            self.citation_map is not None
            and self.citation_map.context_receipt_sha256 != self.context_receipt_sha256
        ):
            raise ValueError(
                "Ask history citations must bind the exact context receipt"
            )
        return self


class CompletedPlanAskPair(StrictModel):
    """Visible Ask pair with optional validated Graph attribution."""

    source_kind: Literal["ask"] = "ask"
    source_sequence: int = Field(strict=True, ge=1)
    source_record_id: UUID
    accepted_at: datetime
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    history_attribution: PlanAskHistoryAttributionV1 | None = None

    @model_validator(mode="after")
    def validate_visible_text(self) -> "CompletedPlanAskPair":
        if not self.question.strip() or not self.answer.strip():
            raise ValueError(
                "completed Plan Ask pairs require visible question and answer"
            )
        if self.history_attribution is not None:
            if (
                self.history_attribution.source_turn_id != self.source_record_id
                or self.history_attribution.source_sequence != self.source_sequence
            ):
                raise ValueError("Ask history attribution must match its source turn")
            if (
                "\n".join(
                    segment.text for segment in self.history_attribution.answer_segments
                )
                != self.answer
            ):
                raise ValueError(
                    "Ask history completion segments must match its answer"
                )
        return self


class GraphExecutionAccountingV1(StrictModel):
    kind: Literal["exact_token_count", "conservative_upper_bound"]
    estimator: str = Field(min_length=1, max_length=128)


class GraphExecutionPolicyV1(StrictModel):
    policy_version: str = Field(min_length=1, max_length=128)
    allowed_graph_operations: list[str] = Field(min_length=1, max_length=32)
    max_provider_attempts: int = Field(strict=True, ge=1, le=128)
    max_graph_operations: int = Field(strict=True, ge=0, le=512)
    max_results_per_operation: int = Field(strict=True, ge=0, le=4096)
    max_total_provider_input_tokens: int = Field(strict=True, ge=1)
    max_total_provider_output_tokens: int = Field(strict=True, ge=1)
    provider_input_accounting: GraphExecutionAccountingV1
    source_opened: Literal[False]

    @model_validator(mode="after")
    def validate_policy(self) -> "GraphExecutionPolicyV1":
        if any(not item.strip() for item in self.allowed_graph_operations):
            raise ValueError("allowed Graph operations cannot be blank")
        if self.allowed_graph_operations != sorted(set(self.allowed_graph_operations)):
            raise ValueError("allowed Graph operations must be sorted and unique")
        if (
            self.provider_input_accounting.kind == "conservative_upper_bound"
            and self.provider_input_accounting.estimator
            != "utf8_json_bytes_plus_64_per_node_v1"
        ):
            raise ValueError("unknown conservative provider input estimator")
        return self


class GraphSourceScopeAnchorV2(StrictModel):
    anchor_id: str = Field(min_length=1, max_length=256)
    evidence_ref_id: str = Field(min_length=1, max_length=256)
    source_artifact_id: str = Field(min_length=1, max_length=256)
    source_revision_id: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_pins(self) -> GraphSourceScopeAnchorV2:
        if any(
            not value.strip() or value != value.strip()
            for value in (self.anchor_id, self.evidence_ref_id, self.source_artifact_id, self.source_revision_id)
        ):
            raise ValueError("source scope pins must be nonblank and trimmed")
        return self


class GraphSourceReadScopeV2(StrictModel):
    schema_: Literal["dmb_graph_source_read_scope_v2"] = Field(
        default="dmb_graph_source_read_scope_v2", alias="schema"
    )
    retrieval_session_id: str = Field(min_length=1, max_length=128)
    world_id: str = Field(min_length=1, max_length=256)
    campaign_id: str | None = Field(default=None, max_length=256)
    graph_revision: str = Field(min_length=1, max_length=256)
    admitted_anchors: list[GraphSourceScopeAnchorV2] = Field(max_length=512)

    @model_validator(mode="after")
    def validate_scope(self) -> GraphSourceReadScopeV2:
        if any(
            not value.strip() or value != value.strip()
            for value in (self.retrieval_session_id, self.world_id, self.graph_revision)
        ) or (self.campaign_id is not None and (not self.campaign_id.strip() or self.campaign_id != self.campaign_id.strip())):
            raise ValueError("source-read scope identifiers must be nonblank and trimmed")
        ids = [a.anchor_id for a in self.admitted_anchors]
        if ids != sorted(set(ids)):
            raise ValueError("source scope anchors must be sorted and unique")
        return self


class GraphSelectedTargetV1(StrictModel):
    kind: Literal["object", "relationship", "assertion"]
    target_id: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_id(self) -> "GraphSelectedTargetV1":
        if self.target_id != self.target_id.strip() or any(c in self.target_id for c in "\r\n\t"):
            raise ValueError("selected target ID must be canonical")
        return self


class GraphSelectedFocusV1(StrictModel):
    kind: Literal["none", "session"]
    session_id: str | None


class GraphSelectedContextV1(StrictModel):
    world_id: str = Field(min_length=1, max_length=256)
    campaign_id: str | None
    scope_mode: Literal["world", "campaign", "world_cross_campaign"]
    focus: GraphSelectedFocusV1
    admissibility: Literal["gm", "player"]
    revision_id: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_context(self) -> "GraphSelectedContextV1":
        if (self.scope_mode == "campaign") != bool(self.campaign_id):
            raise ValueError("selected campaign context is invalid")
        if self.focus.kind == "session":
            if not self.campaign_id or not self.focus.session_id:
                raise ValueError("session focus requires campaign and session")
        elif self.focus.session_id is not None:
            raise ValueError("none focus cannot carry session")
        return self


class GraphSelectedIndexCommitmentV1(StrictModel):
    schema_: Literal["dmb_selected_source_anchor_index_commitment_v1"] = Field(default="dmb_selected_source_anchor_index_commitment_v1", alias="schema")
    context: GraphSelectedContextV1
    access_context_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_targets: list[GraphSelectedTargetV1] = Field(min_length=1, max_length=8)
    admitted_targets: list[GraphSelectedTargetV1] = Field(max_length=8)
    not_visible_targets: list[GraphSelectedTargetV1] = Field(max_length=8)
    requested_count: int = Field(strict=True, ge=1, le=8)
    admitted_count: int = Field(strict=True, ge=0, le=8)
    not_visible_count: int = Field(strict=True, ge=0, le=8)
    provenance_gap_count: int = Field(strict=True, ge=0)
    unavailable_binding_count: int = Field(strict=True, ge=0)
    eligible_count: int = Field(strict=True, ge=0, le=512)
    max_entries: Literal[512]
    status: Literal["complete", "unavailable"]
    index_scope: Literal["selected_targets"]
    selector_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_commitment(self) -> "GraphSelectedIndexCommitmentV1":
        arrays = [self.requested_targets, self.admitted_targets, self.not_visible_targets]
        keys = [[(target.kind, target.target_id) for target in items] for items in arrays]
        if any(items != sorted(set(items)) for items in keys):
            raise ValueError("selected targets must be canonical and unique")
        requested, admitted, hidden = map(set, keys)
        if admitted & hidden or admitted | hidden != requested or (
            self.requested_count, self.admitted_count, self.not_visible_count
        ) != tuple(len(items) for items in keys):
            raise ValueError("selected coverage partition is invalid")
        context = self.context.model_dump(mode="json")
        if self.access_context_sha256 != _canonical_sha256(context):
            raise ValueError("selected access context digest changed")
        selector = {"schema": "dm_selected_source_anchor_selector_v1", "context": context,
            "max_entries": self.max_entries, "targets": [target.model_dump(mode="json") for target in self.requested_targets]}
        if self.selector_sha256 != _canonical_sha256(selector):
            raise ValueError("selected selector digest changed")
        if (self.status == "complete") != (self.eligible_count > 0):
            raise ValueError("selected status/count conflict")
        return self


class GraphSelectedSourceReadScopeV2(GraphSourceReadScopeV2):
    initial_claim_packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_index_commitment: GraphSelectedIndexCommitmentV1

    @model_validator(mode="after")
    def validate_selected_scope(self) -> "GraphSelectedSourceReadScopeV2":
        commitment = self.selected_index_commitment
        if self.graph_revision != commitment.context.revision_id or self.campaign_id != commitment.context.campaign_id or len(self.admitted_anchors) != commitment.eligible_count:
            raise ValueError("selected scope differs from committed context/pins")
        entries = []
        for anchor in self.admitted_anchors:
            item = anchor.model_dump(mode="json")
            if item["anchor_id"].startswith("source-anchor:v1:"):
                item["anchor_id"] = "dm-source-anchor:v1:" + item["anchor_id"][len("source-anchor:v1:"):]
            entries.append(item)
        index = {"schema": "dm_selected_source_anchor_index_v1", "selector_sha256": commitment.selector_sha256,
            "status": commitment.status, "admitted_targets": [target.model_dump(mode="json") for target in commitment.admitted_targets],
            "not_visible_targets": [target.model_dump(mode="json") for target in commitment.not_visible_targets],
            "provenance_gap_count": commitment.provenance_gap_count, "unavailable_binding_count": commitment.unavailable_binding_count,
            "eligible_count": commitment.eligible_count, "entries": entries}
        if commitment.index_sha256 != _canonical_sha256(index):
            raise ValueError("selected index digest changed")
        return self


class GraphExecutionPolicyV2(GraphExecutionPolicyV1):
    source_read_scope: GraphSelectedSourceReadScopeV2 | GraphSourceReadScopeV2
    max_source_read_calls: int = Field(strict=True, ge=0, le=8)
    max_source_read_anchors: int = Field(strict=True, ge=0, le=8)
    max_source_read_chars: int = Field(strict=True, ge=0, le=96000)
    max_chars_per_source_read: int = Field(strict=True, ge=1, le=12000)

    @model_validator(mode="after")
    def validate_source_budgets(self) -> GraphExecutionPolicyV2:
        if (self.policy_version == "plan_world_graph_execution_selected_scope_v1") != isinstance(self.source_read_scope, GraphSelectedSourceReadScopeV2):
            raise ValueError("selected execution policy requires the selected scope subtype")
        if (self.max_source_read_calls == 0) != (self.max_source_read_anchors == 0):
            raise ValueError("disabled source-read budgets must set call and anchor limits to zero")
        if (self.max_source_read_calls == 0) != (self.max_source_read_chars == 0):
            raise ValueError("disabled source-read budgets must set call and character limits to zero")
        if self.max_source_read_calls > 0 and not self.source_read_scope.admitted_anchors:
            raise ValueError("enabled source reads require admitted source anchors")
        return self


class GraphExecutionEventBaseV1(StrictModel):
    event_id: UUID
    sequence: int = Field(strict=True, ge=0, le=2047)
    kind: str


class ValidatedGraphOperationEventV1(GraphExecutionEventBaseV1):
    kind: Literal["validated_graph_operation"]
    operation_id: UUID
    operation: str = Field(min_length=1, max_length=128)
    request_arguments_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_revision: str = Field(min_length=1, max_length=256)
    result_packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assertion_ids: list[str] = Field(max_length=512)
    relationship_ids: list[str] = Field(max_length=512)
    evidence_ref_ids: list[str] = Field(max_length=1024)
    evidence_sufficiency_status: Literal["sufficient", "insufficient"]
    coverage_status: Literal["complete", "incomplete"]
    truncated: bool
    source_opened: Literal[False]

    @model_validator(mode="after")
    def validate_ids(self) -> "ValidatedGraphOperationEventV1":
        for name in ("assertion_ids", "relationship_ids", "evidence_ref_ids"):
            values = getattr(self, name)
            if any(not value.strip() for value in values) or values != sorted(set(values)):
                raise ValueError(f"{name} must be nonblank, sorted, and unique")
        return self


class ProviderAttemptAuthorizedEventV1(GraphExecutionEventBaseV1):
    kind: Literal["provider_attempt_authorized"]
    provider_attempt_id: UUID
    envelope_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    serializer_version: Literal["canonical-json-utf8-v1"]
    provider: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=256)
    api_mode: str = Field(min_length=1, max_length=64)
    tool_schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_accounting_kind: Literal["exact_token_count", "conservative_upper_bound"]
    input_estimator: str = Field(min_length=1, max_length=128)
    input_tokens: int = Field(strict=True, ge=0)
    output_token_reserve: int = Field(strict=True, ge=0)
    included_assertion_ids: list[str] = Field(max_length=512)
    included_relationship_ids: list[str] = Field(max_length=512)
    included_evidence_ref_ids: list[str] = Field(max_length=1024)
    included_graph_event_ids: list[UUID] = Field(max_length=512)

    @model_validator(mode="after")
    def validate_included_ids(self) -> "ProviderAttemptAuthorizedEventV1":
        for name in ("included_assertion_ids", "included_relationship_ids", "included_evidence_ref_ids"):
            values = getattr(self, name)
            if any(not value.strip() for value in values) or values != sorted(set(values)):
                raise ValueError(f"{name} must be nonblank, sorted, and unique")
        if len(set(self.included_graph_event_ids)) != len(self.included_graph_event_ids):
            raise ValueError("included Graph event IDs must be unique")
        return self


class ProviderOutcomeEventV1(GraphExecutionEventBaseV1):
    kind: Literal["provider_outcome"]
    provider_attempt_id: UUID
    outcome: Literal["sdk_entered", "response_received", "known_not_sent", "outcome_unknown"]
    status_code: int | None = Field(default=None, strict=True, ge=100, le=599)
    request_id: str | None = Field(default=None, max_length=256)
    response_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class CompletionBindingEventV1(GraphExecutionEventBaseV1):
    kind: Literal["completion_binding"]
    provider_attempt_id: UUID
    completion_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    claim_graph_event_ids: dict[str, list[UUID]] = Field(max_length=256)


class SourceReadAuthorizationEventV2(GraphExecutionEventBaseV1):
    kind: Literal["source_read_authorized_v2"]
    read_call_id: UUID
    context_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_session_id: str = Field(min_length=1, max_length=128)
    world_id: str = Field(min_length=1, max_length=256)
    campaign_id: str | None = Field(default=None, max_length=256)
    graph_revision: str = Field(min_length=1, max_length=256)
    anchors: list[GraphSourceScopeAnchorV2] = Field(min_length=1, max_length=8)
    max_chars: int = Field(strict=True, ge=1, le=12000)

    @model_validator(mode="after")
    def validate_context_ids(self) -> SourceReadAuthorizationEventV2:
        if any(
            not value.strip() or value != value.strip()
            for value in (self.retrieval_session_id, self.world_id, self.graph_revision)
        ) or (self.campaign_id is not None and (not self.campaign_id.strip() or self.campaign_id != self.campaign_id.strip())):
            raise ValueError("source-read authorization identifiers must be nonblank and trimmed")
        return self


class SourceReadAnchorReceiptV2(StrictModel):
    source_read_id: str = Field(min_length=1, max_length=128)
    anchor_id: str = Field(min_length=1, max_length=256)
    evidence_ref_id: str = Field(min_length=1, max_length=256)
    source_artifact_id: str = Field(min_length=1, max_length=256)
    source_revision_id: str | None = Field(default=None, max_length=256)
    outcome: Literal["enough", "partial", "empty", "denied", "truncated", "unavailable"]
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    line_start: int | None = Field(default=None, strict=True, ge=1)
    line_end: int | None = Field(default=None, strict=True, ge=1)
    returned_chars: int = Field(strict=True, ge=0, le=12000)
    truncated: bool
    evidence_sufficiency_status: Literal["sufficient", "insufficient"]

    @model_validator(mode="after")
    def validate_content(self) -> SourceReadAnchorReceiptV2:
        if any(
            not value.strip() or value != value.strip()
            for value in (self.source_read_id, self.anchor_id, self.evidence_ref_id, self.source_artifact_id)
        ) or (self.source_revision_id is not None and (not self.source_revision_id.strip() or self.source_revision_id != self.source_revision_id.strip())):
            raise ValueError("source-read receipt identifiers must be nonblank and trimmed")
        if (self.line_start is None) != (self.line_end is None):
            raise ValueError("source-read line bounds must be supplied together")
        if self.line_start is not None and self.line_end < self.line_start:
            raise ValueError("source-read line range is reversed")
        has_content = self.returned_chars > 0
        if has_content != (self.content_sha256 is not None):
            raise ValueError("source-read content length and digest must agree")
        if has_content and self.source_revision_id is None:
            raise ValueError("content-bearing source reads require the trusted source revision")
        if not has_content and self.outcome == "enough":
            raise ValueError("enough source-read outcome requires returned content")
        if has_content and self.outcome in {"empty", "denied", "unavailable"}:
            raise ValueError("failed source-read outcomes cannot carry content")
        if self.outcome == "truncated" and not self.truncated:
            raise ValueError("truncated outcome must carry the truncation marker")
        return self


class ValidatedSourceReadEventV2(GraphExecutionEventBaseV1):
    kind: Literal["validated_source_read_v2"]
    read_call_id: UUID
    receipts: list[SourceReadAnchorReceiptV2] = Field(min_length=1, max_length=8)


class ProviderAttemptAuthorizedEventV2(ProviderAttemptAuthorizedEventV1):
    kind: Literal["provider_attempt_authorized_v2"]
    included_source_read_event_ids: list[UUID] = Field(max_length=8)

    @model_validator(mode="after")
    def validate_source_event_ids(self) -> ProviderAttemptAuthorizedEventV2:
        if len(set(self.included_source_read_event_ids)) != len(self.included_source_read_event_ids):
            raise ValueError("included source-read event IDs must be unique")
        return self




GraphExecutionEventV2 = Annotated[
    ValidatedGraphOperationEventV1
    | ProviderAttemptAuthorizedEventV1
    | ProviderAttemptAuthorizedEventV2
    | ProviderOutcomeEventV1
    | CompletionBindingEventV1
    | SourceReadAuthorizationEventV2
    | ValidatedSourceReadEventV2,
    Field(discriminator="kind"),
]


GraphExecutionEventV1 = Annotated[
    ValidatedGraphOperationEventV1
    | ProviderAttemptAuthorizedEventV1
    | ProviderOutcomeEventV1
    | CompletionBindingEventV1,
    Field(discriminator="kind"),
]


class PlanWorldGraphExecutionV1(StrictModel):
    schema_: Literal["dmb_agent_plan_world_graph_execution_v1"] = Field(
        default="dmb_agent_plan_world_graph_execution_v1", alias="schema"
    )
    context_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: GraphExecutionPolicyV1
    events: list[GraphExecutionEventV1] = Field(max_length=2048)

    @model_validator(mode="after")
    def validate_execution(self) -> "PlanWorldGraphExecutionV1":
        if [event.sequence for event in self.events] != list(range(len(self.events))):
            raise ValueError("Graph execution events must have contiguous sequence numbers")
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("Graph execution event IDs must be unique")
        operation_ids: set[UUID] = set()
        attempts: dict[UUID, ProviderAttemptAuthorizedEventV1] = {}
        outcomes: dict[UUID, list[str]] = {}
        completion_bindings = 0
        for event in self.events:
            if isinstance(event, ValidatedGraphOperationEventV1):
                if attempts:
                    latest_attempt_id = next(reversed(attempts))
                    if outcomes[latest_attempt_id][-1:] == ["outcome_unknown"]:
                        raise ValueError("Graph operations cannot continue after an unknown provider outcome")
                if event.operation not in self.policy.allowed_graph_operations:
                    raise ValueError("Graph operation is outside the accepted policy")
                if event.operation_id in operation_ids:
                    raise ValueError("Graph operation ID must be unique within the turn")
                operation_ids.add(event.operation_id)
            elif isinstance(event, ProviderAttemptAuthorizedEventV1):
                if event.provider_attempt_id in attempts:
                    raise ValueError("provider attempt ID was authorized more than once")
                if attempts:
                    latest_attempt_id = next(reversed(attempts))
                    prior_outcomes = outcomes[latest_attempt_id]
                    if not prior_outcomes or prior_outcomes[-1] not in {"response_received", "known_not_sent"}:
                        raise ValueError("a new provider attempt requires a resolved prior attempt")
                if event.input_accounting_kind != self.policy.provider_input_accounting.kind or event.input_estimator != self.policy.provider_input_accounting.estimator:
                    raise ValueError("provider attempt accounting differs from accepted policy")
                attempts[event.provider_attempt_id] = event
                outcomes[event.provider_attempt_id] = []
            elif isinstance(event, ProviderOutcomeEventV1):
                if event.provider_attempt_id not in attempts:
                    raise ValueError("provider outcome requires a prior authorization")
                prior = outcomes[event.provider_attempt_id]
                if event.outcome == "sdk_entered" and prior:
                    raise ValueError("SDK entry must be the first provider outcome")
                if event.outcome == "known_not_sent" and prior:
                    raise ValueError("known-not-sent must be recorded before SDK entry")
                if event.outcome not in {"sdk_entered", "known_not_sent", "outcome_unknown"} and not prior:
                    raise ValueError("provider outcome requires observed SDK entry")
                if prior and prior[-1] in {"response_received", "known_not_sent", "outcome_unknown"}:
                    raise ValueError("provider attempt already has a terminal outcome")
                prior.append(event.outcome)
            elif isinstance(event, CompletionBindingEventV1):
                completion_bindings += 1
                if completion_bindings > 1 or event.sequence != len(self.events) - 1:
                    raise ValueError("completion binding must be unique and the final execution event")
                if event.provider_attempt_id not in attempts or outcomes[event.provider_attempt_id][-1:] != ["response_received"]:
                    raise ValueError("completion binding requires a response-received attempt")
        if len(attempts) > self.policy.max_provider_attempts:
            raise ValueError("provider attempt policy limit exceeded")
        graph_events = [e for e in self.events if isinstance(e, ValidatedGraphOperationEventV1)]
        if len(graph_events) > self.policy.max_graph_operations:
            raise ValueError("Graph operation policy limit exceeded")
        graph_by_event_id = {event.event_id: event for event in graph_events}
        if any(
            len(event.assertion_ids) + len(event.relationship_ids) + len(event.evidence_ref_ids)
            > self.policy.max_results_per_operation
            for event in graph_events
        ):
            raise ValueError("Graph operation result limit exceeded")
        input_total = sum(event.input_tokens for event in attempts.values())
        output_total = sum(event.output_token_reserve for event in attempts.values())
        if input_total > self.policy.max_total_provider_input_tokens or output_total > self.policy.max_total_provider_output_tokens:
            raise ValueError("provider token budget exceeded")
        for attempt in attempts.values():
            if any(event_id not in graph_by_event_id for event_id in attempt.included_graph_event_ids):
                raise ValueError("provider envelope references an unknown Graph operation event")
        if len(self.model_dump_json(by_alias=True).encode("utf-8")) > 1_048_576:
            raise ValueError("Graph execution record exceeds the storage size limit")
        return self


class PlanWorldGraphExecutionV2(StrictModel):
    schema_: Literal["dmb_agent_plan_world_graph_execution_v2"] = Field(
        default="dmb_agent_plan_world_graph_execution_v2", alias="schema"
    )
    context_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: GraphExecutionPolicyV2
    events: list[GraphExecutionEventV2] = Field(max_length=2048)

    @model_validator(mode="after")
    def validate_execution(self) -> PlanWorldGraphExecutionV2:
        expected_policy_digest = _canonical_sha256({
            "schema": self.schema_,
            "context_receipt_sha256": self.context_receipt_sha256,
            "policy": self.policy.model_dump(mode="json", by_alias=True),
        })
        if self.execution_policy_sha256 != expected_policy_digest:
            raise ValueError("Graph execution policy digest does not match its frozen scope and budgets")
        if [event.sequence for event in self.events] != list(range(len(self.events))):
            raise ValueError("Graph execution events must have contiguous sequence numbers")
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("Graph execution event IDs must be unique")
        scope = self.policy.source_read_scope
        scope_by_anchor = {anchor.anchor_id: anchor for anchor in scope.admitted_anchors}
        auths: dict[UUID, SourceReadAuthorizationEventV2] = {}
        receipts_by_event: dict[UUID, ValidatedSourceReadEventV2] = {}
        receipts_by_call: set[UUID] = set()
        all_read_ids: set[str] = set()
        authorized_chars = authorized_anchors = 0
        latest_attempt_id: UUID | None = None
        latest_outcome: str | None = None
        for event in self.events:
            if isinstance(event, (SourceReadAuthorizationEventV2, ValidatedSourceReadEventV2)) and latest_outcome == "outcome_unknown":
                raise ValueError("source reads cannot continue after an unknown provider outcome")
            if isinstance(event, CompletionBindingEventV1) and event.sequence != len(self.events) - 1:
                raise ValueError("completion binding must be the final V2 execution event")
            if isinstance(event, (ProviderAttemptAuthorizedEventV1, ProviderAttemptAuthorizedEventV2)):
                latest_attempt_id = event.provider_attempt_id
                latest_outcome = None
            elif isinstance(event, ProviderOutcomeEventV1) and event.provider_attempt_id == latest_attempt_id:
                latest_outcome = event.outcome
            if isinstance(event, SourceReadAuthorizationEventV2):
                if event.read_call_id in auths:
                    raise ValueError("source-read call ID was authorized more than once")
                if (
                    event.context_receipt_sha256 != self.context_receipt_sha256
                    or event.execution_policy_sha256 != self.execution_policy_sha256
                    or event.retrieval_session_id != scope.retrieval_session_id
                    or event.world_id != scope.world_id
                    or event.campaign_id != scope.campaign_id
                    or event.graph_revision != scope.graph_revision
                ):
                    raise ValueError("source-read authorization differs from the frozen source scope")
                anchor_ids = [anchor.anchor_id for anchor in event.anchors]
                if len(anchor_ids) != len(set(anchor_ids)):
                    raise ValueError("source-read authorization anchor IDs must be unique")
                if any(scope_by_anchor.get(anchor.anchor_id) != anchor for anchor in event.anchors):
                    raise ValueError("source-read authorization contains an unadmitted or changed anchor")
                if event.max_chars > self.policy.max_chars_per_source_read:
                    raise ValueError("source-read per-call character limit exceeded")
                auths[event.read_call_id] = event
                authorized_chars += event.max_chars * len(event.anchors)
                authorized_anchors += len(event.anchors)
            elif isinstance(event, ValidatedSourceReadEventV2):
                auth = auths.get(event.read_call_id)
                if auth is None or event.sequence <= auth.sequence:
                    raise ValueError("validated source read requires an earlier authorization")
                if event.read_call_id in receipts_by_call:
                    raise ValueError("source-read authorization already has a receipt")
                if len(event.receipts) != len(auth.anchors):
                    raise ValueError("source-read receipt count must match its authorization")
                for expected, result in zip(auth.anchors, event.receipts, strict=True):
                    if (
                        result.anchor_id != expected.anchor_id
                        or result.evidence_ref_id != expected.evidence_ref_id
                        or result.source_artifact_id != expected.source_artifact_id
                    ):
                        raise ValueError("source-read receipt pins differ from the authorized anchor")
                    if result.source_revision_id is not None and result.source_revision_id != expected.source_revision_id:
                        raise ValueError("source-read receipt source revision differs from the admitted revision")
                    if result.returned_chars > auth.max_chars:
                        raise ValueError("source-read returned characters exceed the authorization")
                    if result.source_read_id in all_read_ids:
                        raise ValueError("source-read ID must be unique within the turn")
                    all_read_ids.add(result.source_read_id)
                receipts_by_event[event.event_id] = event
                receipts_by_call.add(event.read_call_id)
            elif isinstance(event, ProviderAttemptAuthorizedEventV2):
                if any(event_id not in receipts_by_event for event_id in event.included_source_read_event_ids):
                    raise ValueError("provider envelope references an unknown or later source-read receipt")
        if len(auths) > self.policy.max_source_read_calls:
            raise ValueError("source-read call budget exceeded")
        if authorized_anchors > self.policy.max_source_read_anchors:
            raise ValueError("source-read anchor budget exceeded")
        if authorized_chars > self.policy.max_source_read_chars:
            raise ValueError("source-read character budget exceeded")

        # Reuse the V1 execution validator for the unchanged Graph/provider state machine.
        legacy_events: list[dict[str, object]] = []
        for event in self.events:
            if isinstance(event, (SourceReadAuthorizationEventV2, ValidatedSourceReadEventV2)):
                continue
            payload = event.model_dump(mode="json", by_alias=True)
            if isinstance(event, ProviderAttemptAuthorizedEventV2):
                payload["kind"] = "provider_attempt_authorized"
                payload.pop("included_source_read_event_ids", None)
            payload["sequence"] = len(legacy_events)
            legacy_events.append(payload)
        legacy_policy = {
            key: value for key, value in self.policy.model_dump(mode="json", by_alias=True).items()
            if key in {
                "policy_version", "allowed_graph_operations", "max_provider_attempts",
                "max_graph_operations", "max_results_per_operation",
                "max_total_provider_input_tokens", "max_total_provider_output_tokens",
                "provider_input_accounting", "source_opened",
            }
        }
        PlanWorldGraphExecutionV1.model_validate({
            "schema": "dmb_agent_plan_world_graph_execution_v1",
            "context_receipt_sha256": self.context_receipt_sha256,
            "policy": legacy_policy,
            "events": legacy_events,
        })
        if len(self.model_dump_json(by_alias=True).encode("utf-8")) > 1_048_576:
            raise ValueError("Graph execution record exceeds the storage size limit")
        return self


def graph_execution_policy_digest_v2(
    context_receipt_sha256: str, policy: GraphExecutionPolicyV2
) -> str:
    return _canonical_sha256({
        "schema": "dmb_agent_plan_world_graph_execution_v2",
        "context_receipt_sha256": context_receipt_sha256,
        "policy": policy.model_dump(mode="json", by_alias=True),
    })


PlanWorldGraphExecution = PlanWorldGraphExecutionV1 | PlanWorldGraphExecutionV2


_SELECTED_SOURCE_INDEX_SELECTION_POLICY_V1 = "parent_initial_retrieval_with_selected_source_index_v1"

_BOUNDED_SOURCE_INDEX_SELECTION_POLICY_V1 = (
    "parent_initial_retrieval_with_bounded_source_index_v1"
)


def validate_selected_source_binding(receipt: PlanWorldGraphContextReceiptV1, execution: PlanWorldGraphExecution | None) -> None:
    """Bind the selected policy to its immutable composite at every read/write boundary."""
    selected_policy = receipt.graph_packet.selection_policy_version == _SELECTED_SOURCE_INDEX_SELECTION_POLICY_V1
    selected_scope = isinstance(execution.policy.source_read_scope, GraphSelectedSourceReadScopeV2) if isinstance(execution, PlanWorldGraphExecutionV2) else False
    if selected_policy != selected_scope:
        raise ValueError("selected receipt policy and frozen scope differ")
    if selected_scope:
        selected = execution.policy.source_read_scope
        if selected.world_id != receipt.graph_authority.managed_world_id or selected.campaign_id != receipt.graph_authority.campaign_id or selected.graph_revision != receipt.graph_authority.graph_revision or any(anchor.evidence_ref_id not in receipt.graph_packet.candidate_evidence_ref_ids for anchor in selected.admitted_anchors):
            raise ValueError("selected scope differs from managed receipt authority")
        composite = {"schema": "dmb_selected_retrieval_composite_v1", "selection_policy_version": _SELECTED_SOURCE_INDEX_SELECTION_POLICY_V1,
            "initial_claim_packet_sha256": selected.initial_claim_packet_sha256,
            "selected_index": selected.selected_index_commitment.model_dump(mode="json", by_alias=True),
            "source_pins": [anchor.model_dump(mode="json") for anchor in selected.admitted_anchors]}
        if _canonical_sha256(composite) != receipt.graph_packet.retrieval_packet_sha256:
            raise ValueError("selected composite differs from frozen receipt")
        context = selected.selected_index_commitment.context
        if context.world_id != receipt.graph_authority.native_world_id or context.revision_id != receipt.graph_authority.graph_revision or context.scope_mode != "world_cross_campaign" or context.campaign_id != receipt.graph_authority.campaign_id or context.admissibility != "gm" or context.focus.kind != "none" or receipt.graph_authority.admissibility_version != "gm-v1":
            raise ValueError("selected native context differs from receipt authority")


def validate_completion_against_receipt(
    completion: PlanWorldGraphCompletion,
    receipt: PlanWorldGraphContextReceiptV1,
) -> None:
    if completion.context_receipt_sha256 != receipt.context_receipt_sha256:
        _reject_graph_completion(
            GraphCompletionRejectionCode.RECEIPT_BINDING,
            "completion must bind the exact stored Graph receipt",
        )
    if (
        isinstance(completion, PlanWorldGraphCompletionV2)
        and completion.citation_map is not None
        and any(
            entry.source_opened or entry.source_read_ids
            for entry in completion.citation_map.entries
        )
    ):
        _reject_graph_completion(
            GraphCompletionRejectionCode.CITATION_CLAIM_MISMATCH,
            "source-opened citations require a V2 execution envelope",
        )
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
            _reject_graph_completion(
                GraphCompletionRejectionCode.PLAN_BASIS_ATTRIBUTION,
                "Plan claim attribution must match the frozen Plan digest",
            )

    if completion.answer_context_status == "plan_only_insufficient_evidence":
        if packet.evidence_sufficiency_status != "insufficient":
            _reject_graph_completion(
                GraphCompletionRejectionCode.STATUS_EVIDENCE_MISMATCH,
                "insufficient Plan-only status requires insufficient receipt evidence",
            )
    elif completion.answer_context_status == "plan_only_graph_unused":
        if packet.evidence_sufficiency_status != "sufficient":
            _reject_graph_completion(
                GraphCompletionRejectionCode.STATUS_EVIDENCE_MISMATCH,
                "unused Graph status requires sufficient receipt evidence",
            )
    elif completion.answer_context_status == "graph_grounded":
        if (
            packet.evidence_sufficiency_status != "sufficient"
            or packet.coverage_status != "complete"
            or packet.truncated
        ):
            _reject_graph_completion(
                GraphCompletionRejectionCode.STATUS_EVIDENCE_MISMATCH,
                "fully grounded status requires sufficient complete untruncated evidence",
            )
    elif completion.answer_context_status == "graph_grounded_partial":
        if packet.evidence_sufficiency_status != "sufficient" or (
            packet.coverage_status == "complete" and not packet.truncated
        ):
            _reject_graph_completion(
                GraphCompletionRejectionCode.STATUS_EVIDENCE_MISMATCH,
                "partially grounded status requires incomplete or truncated evidence",
            )

    dispatched = {
        "assertion": set(assembled.dispatched_assertion_ids),
        "relationship": set(assembled.dispatched_relationship_ids),
    }
    candidate_evidence = set(packet.candidate_evidence_ref_ids)
    dispatched_evidence = set(assembled.dispatched_evidence_ref_ids)
    if claims:
        if assembled.packet_disposition != "included":
            _reject_graph_completion(
                GraphCompletionRejectionCode.GRAPH_PACKET_NOT_INCLUDED,
                "Graph claims require an included Graph packet",
            )
        if completion.citation_map is None:
            _reject_graph_completion(
                GraphCompletionRejectionCode.CITATION_MAP_MISSING,
                "Graph claims require a citation map",
            )
        entries = {entry.claim_id: entry for entry in completion.citation_map.entries}
        if len(entries) != len(completion.citation_map.entries):
            _reject_graph_completion(
                GraphCompletionRejectionCode.CITATION_MAP_CLAIM_SET,
                "citation map claim IDs must be unique",
            )
        for claim in claims:
            entry = entries.get(claim.claim_id)
            if entry is None:
                _reject_graph_completion(
                    GraphCompletionRejectionCode.CITATION_ENTRY_MISSING,
                    "every Graph claim requires exactly one citation entry",
                )
            if claim.target_id not in dispatched[claim.target_kind]:
                _reject_graph_completion(
                    GraphCompletionRejectionCode.CLAIM_TARGET_NOT_DISPATCHED,
                    "Graph claim target must be in the dispatched packet",
                )
            if claim.graph_revision != receipt.graph_authority.graph_revision:
                _reject_graph_completion(
                    GraphCompletionRejectionCode.GRAPH_REVISION_MISMATCH,
                    "Graph claim must use the frozen Graph revision",
                )
            if not set(claim.evidence_ref_ids).issubset(candidate_evidence):
                _reject_graph_completion(
                    GraphCompletionRejectionCode.EVIDENCE_NOT_CANDIDATE,
                    "Graph claim evidence refs must be in the frozen candidate set",
                )
            indexed_refs = set(claim.evidence_ref_ids) - dispatched_evidence
            if indexed_refs and packet.selection_policy_version in {_BOUNDED_SOURCE_INDEX_SELECTION_POLICY_V1, _SELECTED_SOURCE_INDEX_SELECTION_POLICY_V1}:
                _reject_graph_completion(
                    GraphCompletionRejectionCode.EVIDENCE_NOT_DISPATCHED,
                    "indexed Graph evidence requires a producing execution envelope",
                )
            if not set(claim.evidence_ref_ids).issubset(dispatched_evidence):
                _reject_graph_completion(
                    GraphCompletionRejectionCode.EVIDENCE_NOT_DISPATCHED,
                    "Graph claim evidence refs must be in the dispatched packet",
                )
            if claim.evidence_ref_ids != sorted(set(claim.evidence_ref_ids)):
                _reject_graph_completion(
                    GraphCompletionRejectionCode.EVIDENCE_ORDER,
                    "Graph claim evidence refs must be sorted and unique",
                )
            if set(entry.evidence_ref_ids) != set(claim.evidence_ref_ids):
                _reject_graph_completion(
                    GraphCompletionRejectionCode.CITATION_EVIDENCE_MISMATCH,
                    "citation refs must match the Graph claim refs",
                )


def derive_execution_answer_context_status(
    *,
    context_receipt_sha256: str,
    answer_segments: list[PlanWorldGraphAnswerSegmentV1],
    citation_map: PlanWorldGraphCitationMapV1 | None,
    receipt: PlanWorldGraphContextReceiptV1,
    execution: PlanWorldGraphExecution,
    producing_provider_attempt_id: UUID,
    claim_graph_event_ids: dict[str, list[UUID]],
) -> Literal[
    "graph_grounded",
    "graph_grounded_partial",
    "plan_only_insufficient_evidence",
    "plan_only_graph_unused",
]:
    """Validate producing-envelope evidence and derive its answer context status.

    This accepts the typed completion fields separately so callers can derive a
    status before constructing the final status-bearing completion model.

    ``graph_grounded`` means every cited support packet in the producing envelope
    is sufficient, complete, and untruncated. It does not assert corpus-wide
    completeness.
    """
    if context_receipt_sha256 != receipt.context_receipt_sha256:
        _reject_graph_completion(
            GraphCompletionRejectionCode.RECEIPT_BINDING,
            "completion must bind the exact stored Graph receipt",
        )
    auths = {
        event.provider_attempt_id: event
        for event in execution.events
        if isinstance(event, ProviderAttemptAuthorizedEventV1)
    }
    outcomes = [
        event for event in execution.events
        if isinstance(event, ProviderOutcomeEventV1)
        and event.provider_attempt_id == producing_provider_attempt_id
    ]
    producing = auths.get(producing_provider_attempt_id)
    if producing is None or not outcomes or outcomes[-1].outcome != "response_received":
        _reject_graph_completion(
            GraphCompletionRejectionCode.PRODUCING_RESPONSE_MISSING,
            "completion requires a durable response from its producing attempt",
        )
    events = {
        event.event_id: event
        for event in execution.events
        if isinstance(event, ValidatedGraphOperationEventV1)
    }
    included_event_ids = set(producing.included_graph_event_ids)
    included_assertions = set(producing.included_assertion_ids)
    included_relationships = set(producing.included_relationship_ids)
    included_evidence = set(producing.included_evidence_ref_ids)
    dispatched = {
        "assertion": set(receipt.assembled_input.dispatched_assertion_ids),
        "relationship": set(receipt.assembled_input.dispatched_relationship_ids),
    }
    claims = [s for s in answer_segments if isinstance(s, PlanWorldGraphClaimSegmentV1)]
    indexed_policy = (
        receipt.graph_packet.selection_policy_version
        in {_BOUNDED_SOURCE_INDEX_SELECTION_POLICY_V1, _SELECTED_SOURCE_INDEX_SELECTION_POLICY_V1}
    )
    source_scope = (
        execution.policy.source_read_scope
        if isinstance(execution, PlanWorldGraphExecutionV2)
        else None
    )
    scope_anchors: dict[str, list[GraphSourceScopeAnchorV2]] = {}
    if source_scope is not None:
        for anchor in source_scope.admitted_anchors:
            scope_anchors.setdefault(anchor.evidence_ref_id, []).append(anchor)
    source_reads_by_id: dict[str, SourceReadAnchorReceiptV2] = {}
    if isinstance(producing, ProviderAttemptAuthorizedEventV2):
        included_read_events = set(producing.included_source_read_event_ids)
        source_reads_by_id = {
            read.source_read_id: read
            for event in execution.events
            if isinstance(event, ValidatedSourceReadEventV2)
            and event.event_id in included_read_events
            for read in event.receipts
        }
    for segment in answer_segments:
        if isinstance(segment, PlanWorldGraphPlanClaimSegmentV1) and segment.plan_content_sha256 != receipt.plan_basis.content_sha256:
            _reject_graph_completion(
                GraphCompletionRejectionCode.PLAN_BASIS_ATTRIBUTION,
                "Plan claim attribution must match the frozen Plan digest",
            )
    if set(claim_graph_event_ids) != {claim.claim_id for claim in claims}:
        _reject_graph_completion(
            GraphCompletionRejectionCode.CLAIM_BINDING_SET,
            "completion binding must map each Graph claim exactly once",
        )
    if claims and citation_map is None:
        _reject_graph_completion(
            GraphCompletionRejectionCode.CITATION_MAP_MISSING,
            "Graph claims require a citation map",
        )
    citation_entries = {} if citation_map is None else {entry.claim_id: entry for entry in citation_map.entries}
    if claims and (len(citation_entries) != len(citation_map.entries) or set(citation_entries) != {claim.claim_id for claim in claims}):
        _reject_graph_completion(
            GraphCompletionRejectionCode.CITATION_MAP_CLAIM_SET,
            "citation map must correspond one-to-one with Graph claims",
        )
    sufficient_sources: list[tuple[str, bool]] = []
    for claim in claims:
        if claim.graph_revision != receipt.graph_authority.graph_revision:
            _reject_graph_completion(
                GraphCompletionRejectionCode.GRAPH_REVISION_MISMATCH,
                "Graph claim must use the frozen Graph revision",
            )
        target_ids = dispatched[claim.target_kind] | (
            included_assertions if claim.target_kind == "assertion" else included_relationships
        )
        if claim.target_id not in target_ids:
            _reject_graph_completion(
                GraphCompletionRejectionCode.CLAIM_TARGET_NOT_IN_ENVELOPE,
                "Graph claim target is absent from the final producing envelope",
            )
        if claim.evidence_ref_ids != sorted(set(claim.evidence_ref_ids)):
            _reject_graph_completion(
                GraphCompletionRejectionCode.EVIDENCE_ORDER,
                "Graph claim evidence refs must be sorted and unique",
            )
        refs = set(claim.evidence_ref_ids)
        indexed_refs = (
            refs - set(receipt.assembled_input.dispatched_evidence_ref_ids)
            if indexed_policy else set()
        )
        indexed_reads: dict[str, SourceReadAnchorReceiptV2] = {}
        citation_for_claim = citation_entries.get(claim.claim_id)
        if indexed_refs:
            if (
                not indexed_policy
                or not indexed_refs.issubset(set(receipt.graph_packet.candidate_evidence_ref_ids))
                or not isinstance(producing, ProviderAttemptAuthorizedEventV2)
                or not isinstance(citation_for_claim, PlanWorldGraphCitationV2)
            ):
                _reject_graph_completion(
                    GraphCompletionRejectionCode.EVIDENCE_NOT_DISPATCHED,
                    "out-of-dispatch evidence requires the selected source-index policy and a producing V2 read",
                )
            if not indexed_refs.issubset(scope_anchors):
                _reject_graph_completion(
                    GraphCompletionRejectionCode.EVIDENCE_NOT_DISPATCHED,
                    "out-of-dispatch evidence must be admitted by the frozen source scope",
                )
            for ref in indexed_refs:
                matching = [
                    source_reads_by_id[read_id]
                    for read_id in citation_for_claim.source_read_ids
                    if read_id in source_reads_by_id
                    and source_reads_by_id[read_id].evidence_ref_id == ref
                ]
                matching = [
                    read for read in matching
                    if any(
                        read.anchor_id == anchor.anchor_id
                        and read.source_artifact_id == anchor.source_artifact_id
                        and read.source_revision_id == anchor.source_revision_id
                        for anchor in scope_anchors[ref]
                    )
                    and read.outcome in {"enough", "partial", "truncated"}
                    and read.content_sha256 is not None
                    and read.returned_chars > 0
                    and read.evidence_sufficiency_status == "sufficient"
                ]
                if not matching:
                    _reject_graph_completion(
                        GraphCompletionRejectionCode.CITATION_CLAIM_MISMATCH,
                        "indexed evidence requires sufficient content from a matching producing-attempt source read",
                    )
                indexed_reads[ref] = matching[0]
            included_targets = included_assertions if claim.target_kind == "assertion" else included_relationships
            if claim.target_id not in included_targets:
                _reject_graph_completion(
                    GraphCompletionRejectionCode.CLAIM_TARGET_NOT_IN_ENVELOPE,
                    "indexed evidence requires a target included by the producing attempt",
                )
        mapped_ids = claim_graph_event_ids[claim.claim_id]
        if len(mapped_ids) != len(set(mapped_ids)):
            _reject_graph_completion(
                GraphCompletionRejectionCode.BINDING_EVENT_DUPLICATE,
                "completion binding event IDs must be unique per claim",
            )
        support_packets: list[tuple[set[str], set[str], str, str, bool]] = []
        if claim.target_id in dispatched[claim.target_kind] and refs.issubset(set(receipt.assembled_input.dispatched_evidence_ref_ids)):
            if claim.target_id in (included_assertions if claim.target_kind == "assertion" else included_relationships) and refs.issubset(included_evidence):
                support_packets.append((set(receipt.assembled_input.dispatched_assertion_ids) | set(receipt.assembled_input.dispatched_relationship_ids), set(receipt.assembled_input.dispatched_evidence_ref_ids), receipt.graph_packet.evidence_sufficiency_status, receipt.graph_packet.coverage_status, receipt.graph_packet.truncated))
        for event_id in mapped_ids:
            event = events.get(event_id)
            if event is None or event_id not in included_event_ids:
                _reject_graph_completion(
                    GraphCompletionRejectionCode.BINDING_EVENT_NOT_IN_ENVELOPE,
                    "citation event must be validated and present in the final producing envelope",
                )
            targets = set(event.assertion_ids if claim.target_kind == "assertion" else event.relationship_ids)
            included_targets = included_assertions if claim.target_kind == "assertion" else included_relationships
            indexed_event_support = bool(indexed_refs) and indexed_refs.issubset(set(event.evidence_ref_ids))
            if (
                claim.target_id in targets
                and claim.target_id in included_targets
                and refs.issubset(set(event.evidence_ref_ids))
                and (refs - indexed_refs).issubset(included_evidence)
                and (not indexed_refs or indexed_event_support)
            ):
                support_packets.append((targets, set(event.evidence_ref_ids), event.evidence_sufficiency_status, event.coverage_status, event.truncated))
            else:
                _reject_graph_completion(
                    GraphCompletionRejectionCode.BINDING_EVENT_SUPPORT_MISMATCH,
                    "completion binding names an event that does not support its claim",
                )
        if not support_packets:
            _reject_graph_completion(
                GraphCompletionRejectionCode.CLAIM_SUPPORT_MISSING,
                "Graph claim target and evidence refs lack included validated support",
            )
        if any(status != "sufficient" for _, _, status, _, _ in support_packets):
            _reject_graph_completion(
                GraphCompletionRejectionCode.CITED_EVIDENCE_INSUFFICIENT,
                "Graph grounded claims require sufficient cited evidence",
            )
        sufficient_sources.extend((status, coverage == "complete" and not truncated) for _, _, status, coverage, truncated in support_packets)
        if indexed_refs and (
            receipt.graph_packet.coverage_status != "complete"
            or receipt.graph_packet.truncated
        ):
            sufficient_sources.append(("sufficient", False))
        if any(read.outcome != "enough" or read.truncated for read in indexed_reads.values()):
            sufficient_sources.append(("sufficient", False))
        if citation_map is None:
            _reject_graph_completion(
                GraphCompletionRejectionCode.CITATION_MAP_MISSING,
                "Graph claims require a citation map",
            )
        entry = citation_entries.get(claim.claim_id)
        if entry is None or entry.target_kind != claim.target_kind or entry.target_id != claim.target_id or entry.graph_revision != claim.graph_revision or entry.evidence_ref_ids != claim.evidence_ref_ids:
            _reject_graph_completion(
                GraphCompletionRejectionCode.CITATION_CLAIM_MISMATCH,
                "citation map entry must match its Graph claim",
            )
    if claims:
        return (
            "graph_grounded"
            if all(complete for _, complete in sufficient_sources)
            else "graph_grounded_partial"
        )
    initial_ids_in_envelope = bool(
        set(receipt.assembled_input.dispatched_assertion_ids).intersection(included_assertions)
        or set(receipt.assembled_input.dispatched_relationship_ids).intersection(included_relationships)
        or set(receipt.assembled_input.dispatched_evidence_ref_ids).intersection(included_evidence)
    )
    sufficient = (
        receipt.graph_packet.evidence_sufficiency_status == "sufficient"
        and receipt.assembled_input.packet_disposition == "included"
        and initial_ids_in_envelope
    )
    sufficient = sufficient or any(
        event.event_id in included_event_ids
        and event.evidence_sufficiency_status == "sufficient"
        and (
            set(event.assertion_ids).intersection(included_assertions)
            or set(event.relationship_ids).intersection(included_relationships)
            or set(event.evidence_ref_ids).intersection(included_evidence)
        )
        for event in events.values()
    )
    return "plan_only_graph_unused" if sufficient else "plan_only_insufficient_evidence"


def validate_execution_completion(
    completion: PlanWorldGraphCompletion,
    receipt: PlanWorldGraphContextReceiptV1,
    execution: PlanWorldGraphExecution,
    producing_provider_attempt_id: UUID,
    claim_graph_event_ids: dict[str, list[UUID]],
) -> None:
    """Validate supplied status against the derived producing-envelope status."""
    validate_selected_source_binding(receipt, execution)
    if isinstance(completion, PlanWorldGraphCompletionV2):
        if not isinstance(execution, PlanWorldGraphExecutionV2):
            raise ValueError("V2 completion requires a V2 execution record")  # noqa: TRY004
        _validate_v2_completion_source_reads(completion, execution, producing_provider_attempt_id)
    expected_status = derive_execution_answer_context_status(
        context_receipt_sha256=completion.context_receipt_sha256,
        answer_segments=completion.answer_segments,
        citation_map=completion.citation_map,
        receipt=receipt,
        execution=execution,
        producing_provider_attempt_id=producing_provider_attempt_id,
        claim_graph_event_ids=claim_graph_event_ids,
    )
    if completion.answer_context_status == expected_status:
        return
    if expected_status in {"graph_grounded", "graph_grounded_partial"}:
        _reject_graph_completion(
            GraphCompletionRejectionCode.GROUNDED_STATUS_MISMATCH,
            "Graph grounded status does not match cited execution evidence",
        )
    _reject_graph_completion(
        GraphCompletionRejectionCode.PLAN_ONLY_STATUS_MISMATCH,
        "Plan-only status does not match evidence in the producing envelope",
    )


def _validate_v2_completion_source_reads(completion: PlanWorldGraphCompletionV2, execution: PlanWorldGraphExecutionV2, producing_provider_attempt_id: UUID) -> None:
    if completion.citation_map is None:
        return
    attempt = next((e for e in execution.events if isinstance(e, (ProviderAttemptAuthorizedEventV1, ProviderAttemptAuthorizedEventV2)) and e.provider_attempt_id == producing_provider_attempt_id), None)
    included = set(attempt.included_source_read_event_ids) if isinstance(attempt, ProviderAttemptAuthorizedEventV2) else set()
    reads = {read.source_read_id: read for event in execution.events if isinstance(event, ValidatedSourceReadEventV2) and event.event_id in included for read in event.receipts}
    for citation in completion.citation_map.entries:
        if citation.source_opened != bool(citation.source_read_ids) or not set(citation.source_read_ids).issubset(reads):
            _reject_graph_completion(GraphCompletionRejectionCode.CITATION_CLAIM_MISMATCH, "citation source-opened state must bind source reads in the producing envelope")
        for read_id in citation.source_read_ids:
            read = reads[read_id]
            if read.outcome not in {"enough", "partial", "truncated"} or read.content_sha256 is None or read.returned_chars == 0 or read.source_revision_id is None or read.evidence_ref_id not in citation.evidence_ref_ids:
                _reject_graph_completion(GraphCompletionRejectionCode.CITATION_CLAIM_MISMATCH, "citation source read must contain validated content for cited evidence")


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
    graph_context_execution: PlanWorldGraphExecution | None = None

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
            validate_selected_source_binding(receipt, self.graph_context_execution)
            if self.graph_context_execution is not None:
                execution = self.graph_context_execution
                if execution.events:
                    raise ValueError("accepted Graph execution record must start empty")
                if execution.context_receipt_sha256 != receipt.context_receipt_sha256:
                    raise ValueError("Graph execution policy must bind the frozen receipt")
                accounting = execution.policy.provider_input_accounting
                if isinstance(execution, PlanWorldGraphExecutionV2):
                    scope = execution.policy.source_read_scope
                    if (
                        scope.world_id != receipt.graph_authority.managed_world_id
                        or scope.campaign_id != receipt.graph_authority.campaign_id
                        or scope.graph_revision != receipt.graph_authority.graph_revision
                        or any(a.evidence_ref_id not in receipt.graph_packet.candidate_evidence_ref_ids for a in scope.admitted_anchors)
                    ):
                        raise ValueError("V2 source-read scope must match the frozen Graph receipt")
                validate_selected_source_binding(receipt, execution)
                if accounting.estimator != receipt.assembled_input.tokenizer_name:
                    raise ValueError("receipt tokenizer metadata differs from Graph execution policy")
                if (
                    accounting.kind == "conservative_upper_bound"
                    and receipt.assembled_input.tokenizer_version != "v1"
                ):
                    raise ValueError("receipt accounting differs from Graph execution policy")
        elif self.graph_context_receipt is not None:
            raise ValueError("Graph context receipt requires submitted intent v2")
        if self.graph_context_execution is not None and self.submitted_intent_v2 is None:
            raise ValueError("Graph execution requires submitted intent v2")
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
    graph_context_execution: PlanWorldGraphExecution | None = None
    completion: PlanWorldGraphCompletion | None = None
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
        if self.graph_context_receipt is not None:
            validate_selected_source_binding(self.graph_context_receipt, self.graph_context_execution)
        if self.graph_context_execution is not None:
            if self.graph_context_receipt is None:
                raise ValueError("Graph execution requires its frozen context receipt")
            if self.submitted_intent_fingerprint_v2 is None:
                raise ValueError("Graph execution requires a v2 submitted-intent fingerprint")
            if self.graph_context_execution.context_receipt_sha256 != self.graph_context_receipt.context_receipt_sha256:
                raise ValueError("Graph execution must bind the exact stored receipt")
            has_completion_binding = any(
                isinstance(event, CompletionBindingEventV1)
                for event in self.graph_context_execution.events
            )
            if has_completion_binding != (self.completion is not None):
                raise ValueError("completion binding must be present exactly when completion is stored")
        if self.completion is not None:
            if self.graph_context_receipt is None:
                raise ValueError("Graph completion requires its frozen context receipt")
            if self.graph_context_execution is None:
                validate_completion_against_receipt(
                    self.completion, self.graph_context_receipt
                )
            else:
                bindings = [e for e in self.graph_context_execution.events if isinstance(e, CompletionBindingEventV1)]
                if len(bindings) != 1:
                    raise ValueError("execution completion requires exactly one completion binding")
                binding = bindings[0]
                if binding.completion_sha256 != _canonical_sha256(self.completion.model_dump(mode="json", by_alias=True)):
                    raise ValueError("completion binding digest does not match completion")
                validate_execution_completion(
                    self.completion,
                    self.graph_context_receipt,
                    self.graph_context_execution,
                    binding.provider_attempt_id,
                    binding.claim_graph_event_ids,
                )
        return self


class TurnResult(StrictModel):
    world_id: str
    conversation_id: UUID
    turn_id: UUID
    expected_revision: int = Field(ge=1)
    assistant_text: str
    completion: PlanWorldGraphCompletion | None = None
    producing_provider_attempt_id: UUID | None = None
    claim_graph_event_ids: dict[str, list[UUID]] | None = None

    @model_validator(mode="after")
    def validate_text(self) -> "TurnResult":
        if not self.assistant_text.strip():
            raise ValueError("assistant_text is required")
        if (self.producing_provider_attempt_id is None) != (self.claim_graph_event_ids is None):
            raise ValueError("execution completion binding inputs must be supplied together")
        if self.completion is None and self.producing_provider_attempt_id is not None:
            raise ValueError("completion binding inputs require a completion")
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


class CommandResolutionRequestV1(StrictModel):
    schema_: Literal["dmb_agent_new_conversation_resolution_request_v1"] = Field(default="dmb_agent_new_conversation_resolution_request_v1", alias="schema")
    resolution_operation_id: UUID
    original_command: ConversationCommand
    expected_current_pointer_revision: int = Field(ge=0)
    expected_current_active_conversation_id: UUID | None

    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json", by_alias=True, exclude={"resolution_operation_id"}))


class OccupiedCommandProofV1(StrictModel):
    world_id: str
    command_id: UUID
    command_kind: CommandKind
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class CommandResolutionRecordV1(StrictModel):
    schema_: Literal["dmb_agent_new_conversation_resolution_record_v1"] = Field(default="dmb_agent_new_conversation_resolution_record_v1", alias="schema")
    request: CommandResolutionRequestV1
    original_command_kind: Literal["new"] = "new"
    original_request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolution_request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_pointer: WorldPointer
    outcome: Literal["confirmed", "retired", "submitted_binding_blocked"]
    actor: str = Field(min_length=1)
    recorded_at: str
    record_serializer_version: Literal["canonical-json-ascii-v1"] = "canonical-json-ascii-v1"
    confirmed_receipt: ConversationCommandReceipt | None
    occupied_receipt: OccupiedCommandProofV1 | None
    retirement_operation_id: UUID | None
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_record(self) -> "CommandResolutionRecordV1":
        command = self.request.original_command
        if self.original_request_fingerprint != request_fingerprint(command) or self.resolution_request_fingerprint != self.request.fingerprint():
            raise ValueError("resolution fingerprint mismatch")
        if self.observed_pointer.world_id != command.world_id:
            raise ValueError("resolution World mismatch")
        timestamp = datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("recorded time must include timezone")
        if self.outcome == "confirmed":
            receipt = self.confirmed_receipt
            if receipt is None or self.occupied_receipt is not None or self.retirement_operation_id is not None or (
                receipt.world_id != command.world_id or receipt.command_id != command.command_id or receipt.command_kind != "new"
                or receipt.active_conversation_id != receipt.conversation_id or receipt.conversation_id == command.expected_active_conversation_id
                or receipt.pointer_revision <= command.expected_pointer_revision
            ):
                raise ValueError("invalid confirmed proof")
        elif self.outcome == "retired":
            if self.confirmed_receipt is not None or self.occupied_receipt is not None or self.retirement_operation_id != self.request.resolution_operation_id or (
                self.observed_pointer.revision != self.request.expected_current_pointer_revision
                or self.observed_pointer.active_conversation_id != self.request.expected_current_active_conversation_id
            ):
                raise ValueError("invalid retirement proof")
        else:
            proof = self.occupied_receipt
            if proof is None or self.confirmed_receipt is not None or self.retirement_operation_id is not None or (
                proof.world_id != command.world_id or proof.command_id != command.command_id
                or (proof.command_kind == "new" and proof.request_fingerprint == self.original_request_fingerprint)
            ):
                raise ValueError("invalid blocked proof")
        if self.record_sha256 != _fingerprint(self.model_dump(mode="json", by_alias=True, exclude={"record_sha256"})):
            raise ValueError("resolution record digest mismatch")
        return self

    @classmethod
    def create(cls, **values) -> "CommandResolutionRecordV1":
        # Normalize typed fields through JSON mode before hashing the immutable record.
        values = {key: value.model_dump(mode="json", by_alias=True) if isinstance(value, BaseModel) else str(value) if isinstance(value, UUID) else value for key, value in values.items()}
        values.update(schema="dmb_agent_new_conversation_resolution_record_v1", original_command_kind="new", record_serializer_version="canonical-json-ascii-v1")
        return cls.model_validate({**values, "record_sha256": _fingerprint(values)})
