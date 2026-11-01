"""Authored working-copy identity; never a saved-source or World evidence receipt.

The browser owns the editor snapshot. APP can prove that its Markdown and identity
match the accepted turn, not that unsaved text was independently authored or saved.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

POLICY = "captured_build_working_draft_context_v1"
ROLE = "authored_working_draft_not_world_or_played_truth"


def digest(value) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class BuildDraftSnapshotV1(_Frozen):
    schema_: Literal["dmb_build_draft_snapshot_v1"] = Field(
        default="dmb_build_draft_snapshot_v1", alias="schema")
    world_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    registry_revision: int = Field(strict=True, ge=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    visibility: Literal["internal", "player_safe"]
    draft_markdown: str
    draft_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    editor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft_generation: int = Field(strict=True, ge=0)

    @model_validator(mode="after")
    def exact_markdown(self):
        if sha256(self.draft_markdown.encode("utf-8", errors="strict")).hexdigest() != self.draft_sha256:
            raise ValueError("Working draft differs from its captured Markdown digest")
        return self

    def saved_basis(self) -> dict:
        return {key: getattr(self, key) for key in (
            "world_id", "document_id", "registry_revision", "content_sha256", "visibility")}

    @property
    def snapshot_sha256(self) -> str:
        return digest(self.model_dump(mode="json", by_alias=True))

    def reference(self) -> dict:
        """Routing identity deliberately omits the page body and write authority."""
        return {"policy": POLICY, "snapshot_sha256": self.snapshot_sha256,
            "document_id": self.document_id, "draft_sha256": self.draft_sha256}


class BuildDraftContextRequestV1(_Frozen):
    snapshot: BuildDraftSnapshotV1
    conversation_id: UUID
    expected_pointer_revision: int = Field(strict=True, ge=0)


class BuildDraftContextRecordV1(_Frozen):
    schema_: Literal["dmb_build_draft_context_record_v1"] = Field(
        default="dmb_build_draft_context_record_v1", alias="schema")
    record_id: UUID
    turn_id: UUID
    conversation_id: UUID
    attempt: int = Field(strict=True, ge=1)
    submitted_intent_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_pointer_revision: int = Field(strict=True, ge=0)
    role: Literal["authored_working_draft_not_world_or_played_truth"] = ROLE
    snapshot: BuildDraftSnapshotV1


def validate_record(record: BuildDraftContextRecordV1, turn) -> None:
    """Reconstruct the accepted identity at APP's owning boundary, without IO."""
    execution = turn.graph_context_execution
    receipt = turn.graph_context_receipt
    if execution is not None and native_build_action(execution) is not None:
        validate_native_record(record,receipt,execution,world_id=turn.world_id,conversation_id=turn.conversation_id,
            turn_id=turn.turn_id,attempt=turn.attempt,submitted_intent_fingerprint=turn.submitted_intent_fingerprint_v2)
        return
    if (execution is None or receipt is None
        or getattr(execution.policy, "working_draft_context_policy", None) != POLICY
        or getattr(execution.policy, "working_draft_snapshot_sha256", None) != record.snapshot.snapshot_sha256
        or getattr(execution.policy, "working_draft_context_sha256", None) != captured_context_sha256(record)):
        raise ValueError("Working draft lacks its frozen context capability")
    validate_record_identity(record,world_id=turn.world_id,conversation_id=turn.conversation_id,
        turn_id=turn.turn_id,attempt=turn.attempt,submitted_intent_fingerprint=turn.submitted_intent_fingerprint_v2,
        saved_basis=receipt.source_basis)


def captured_context_sha256(record):
    """The existing submitted draft-context commitment, not a second manifest."""
    return digest({"snapshot": record.snapshot.model_dump(mode="json", by_alias=True),
        "conversation_id": str(record.conversation_id), "expected_pointer_revision": record.expected_pointer_revision})


def validate_record_identity(record, *, world_id, conversation_id, turn_id, attempt,
                             submitted_intent_fingerprint, saved_basis):
    if (type(attempt) is not int or record.turn_id != turn_id or record.conversation_id != conversation_id
        or record.attempt != attempt or record.submitted_intent_fingerprint != submitted_intent_fingerprint
        or record.snapshot.world_id != world_id
        or record.snapshot.saved_basis() != saved_basis.model_dump(mode="json", by_alias=True)):
        raise ValueError("Working draft differs from its accepted turn and saved basis")


def native_build_action(execution):
    """Select the concrete shared Build owner without a legacy policy view."""
    if getattr(execution.policy,'policy_version',None) != 'surface_native_execution_v1':
        return None
    from .native_execution import SurfaceNativeExecutionV1, NativeBuildActionV1
    return execution.policy.action if type(execution) is SurfaceNativeExecutionV1 and type(execution.policy.action) is NativeBuildActionV1 else None


def validate_native_record(record, receipt, execution, *, world_id, conversation_id, turn_id, attempt,
                           submitted_intent_fingerprint):
    """Join the actual consumer identity; this grants no dispatch or edit authority."""
    from . import types as t
    from .native_context import SurfaceNativeContextReceiptV1, BuildWorkContextV1
    action=native_build_action(execution)
    if (action is None or type(receipt) is not SurfaceNativeContextReceiptV1
            or type(receipt.work_context) is not BuildWorkContextV1 or world_id != action.intent.world_id
            or t.submitted_turn_intent_fingerprint_v2(action.intent) != submitted_intent_fingerprint
            or captured_context_sha256(record) != action.intent.build_draft_context_sha256):
        raise ValueError('Working draft differs from the actual native Build submission')
    validate_record_identity(record,world_id=world_id,conversation_id=conversation_id,turn_id=turn_id,
        attempt=attempt,submitted_intent_fingerprint=submitted_intent_fingerprint,
        saved_basis=receipt.work_context.source_basis)


def writer_reference(record: BuildDraftContextRecordV1) -> dict:
    """One complete body, separate from cited sources and historical dialogue."""
    return {"policy": POLICY, "role": ROLE, "record_id": str(record.record_id),
        "snapshot_sha256": record.snapshot.snapshot_sha256,
        "draft_markdown": record.snapshot.draft_markdown}


def validate_writer_reference(value, record: BuildDraftContextRecordV1, turn) -> None:
    validate_record(record, turn)
    if value != writer_reference(record):
        raise ValueError("Writer working draft differs from its included context record")


def validate_execution_records(execution) -> None:
    from .types import (BuildDraftContextCapturedV1, ProviderAttemptAuthorizedEventV1,
        BuildWriterEvidenceSelectionV1, submitted_turn_intent_fingerprint_v2)
    action = native_build_action(execution)
    rows = [e for e in execution.events if isinstance(e, BuildDraftContextCapturedV1)]
    if len(rows) > 1:
        raise ValueError("A turn captures one immutable working draft")
    for event in rows:
        record=BuildDraftContextRecordV1.model_validate_json(event.record.model_dump_json(by_alias=True))
        if action is not None:
            if (captured_context_sha256(record) != action.intent.build_draft_context_sha256
                    or record.submitted_intent_fingerprint != submitted_turn_intent_fingerprint_v2(action.intent)):
                raise ValueError('Working draft differs from its frozen native submission')
        elif (getattr(execution.policy, "working_draft_context_policy", None) != POLICY
            or getattr(execution.policy, "working_draft_snapshot_sha256", None) != record.snapshot.snapshot_sha256):
            raise ValueError("Working draft differs from its frozen execution capability")
        if any(isinstance(e, BuildWriterEvidenceSelectionV1) or
            (isinstance(e, ProviderAttemptAuthorizedEventV1)
                and (e.provider,e.model,e.api_mode) == execution.policy.provider_roles.writer.identity())
            for e in execution.events[:event.sequence]):
            raise ValueError("Working draft cannot change after writer selection or authorization")
    if action is not None and not rows and action.intent.build_draft_context_sha256 is not None and any(
            isinstance(e,(ProviderAttemptAuthorizedEventV1,BuildWriterEvidenceSelectionV1)) for e in execution.events):
        raise ValueError('Native Build must capture its submitted draft before provider or writer selection')


def context_record(execution):
    from .types import BuildDraftContextCapturedV1
    rows = [e for e in execution.events if isinstance(e, BuildDraftContextCapturedV1)]
    if len(rows) != 1:
        raise ValueError("Provider draft context requires one admitted snapshot")
    return rows[0]


def validate_inclusion_input(inclusion, execution, prepared_request_json):
    if not isinstance(prepared_request_json, str) or sha256(prepared_request_json.encode()).hexdigest() != inclusion.envelope_sha256:
        raise ValueError("Working draft inclusion requires its exact prepared envelope")
    from .source_writer_output import strict_json
    body = strict_json(prepared_request_json)
    if not isinstance(body, dict):
        raise ValueError("Working draft provider envelope must be an object")
    if native_build_action(execution) is not None and isinstance(body.get('input'),list):
        from .build_primary_context import verify_native_work_input
        from .types import BuildSourceContextBasisV1
        captured=context_record(execution)
        verify_native_work_input(execution,BuildSourceContextBasisV1(**captured.record.snapshot.saved_basis()),prepared_request_json)
        if (inclusion.draft_event_id != captured.event_id
                or inclusion.snapshot_sha256 != captured.record.snapshot.snapshot_sha256):
            raise ValueError('Provider working draft differs from its admitted context')
        return
    if native_build_action(execution) is not None and (
            "input" in body or not isinstance(body.get("state"), dict)
            or body.get("model") != execution.policy.provider_roles.controller.model):
        raise ValueError("Native Build draft requires its writer frame or typed controller state")
    carrier = strict_json(body["input"]) if isinstance(body.get("input"), str) else body.get("state")
    captured = context_record(execution)
    if isinstance(body.get('input'), str):
        from .plan_objective import validate_packet as validate_objective_packet
        validate_objective_packet(carrier, execution)
    from .build_related_pages import validate_packet as validate_related_packet
    validate_related_packet(carrier,execution)
    if (inclusion.draft_event_id != captured.event_id
        or inclusion.snapshot_sha256 != captured.record.snapshot.snapshot_sha256
        or not isinstance(carrier, dict)
        or carrier.get("working_draft_context") != writer_reference(captured.record)):
        raise ValueError("Provider working draft differs from its admitted context")


def validate_provider_inclusions(execution):
    from .types import (BuildDraftProviderInclusionV1, ProviderAttemptAuthorizedEventV1,
        BuildSectionProviderInclusionV1, RelatedRecapContextProviderInclusionEventV2)
    from .authored_graph_references import policy_enabled
    from .types import BuildAuthoredProviderInclusionV1
    bundle_types = (BuildSectionProviderInclusionV1, RelatedRecapContextProviderInclusionEventV2)
    if policy_enabled(execution.policy):
        bundle_types += (BuildAuthoredProviderInclusionV1,)
    rows = [e for e in execution.events if isinstance(e, BuildDraftProviderInclusionV1)]
    action=native_build_action(execution)
    if action is not None and action.intent.build_draft_context_sha256 is not None:
        providers=[e for e in execution.events if isinstance(e,ProviderAttemptAuthorizedEventV1)]
        if any(not any(row.provider_attempt_id == provider.provider_attempt_id for row in rows) for provider in providers):
            raise ValueError('Native Build provider requires its exact captured-draft inclusion')
    if not rows:
        return
    captured = context_record(execution)
    seen = set()
    for inclusion in rows:
        if (inclusion.provider_attempt_id in seen or inclusion.sequence <= captured.sequence
            or inclusion.draft_event_id != captured.event_id
            or inclusion.snapshot_sha256 != captured.record.snapshot.snapshot_sha256):
            raise ValueError("Working draft provider inclusion is repeated or has the wrong snapshot")
        seen.add(inclusion.provider_attempt_id)
        attempts = [e for e in execution.events if isinstance(e, ProviderAttemptAuthorizedEventV1)
            and e.provider_attempt_id == inclusion.provider_attempt_id]
        # Inclusion precedes durable provider authorization, matching the existing section protocol.
        if attempts:
            if len(attempts) != 1 or attempts[0].sequence <= inclusion.sequence or attempts[0].envelope_sha256 != inclusion.envelope_sha256:
                raise ValueError("Working draft inclusion differs from its provider authorization")
        end = attempts[0].sequence if attempts else len(execution.events)
        for between in execution.events[inclusion.sequence+1:end]:
            if (not isinstance(between, bundle_types)
                or between.provider_attempt_id != inclusion.provider_attempt_id
                or between.envelope_sha256 != inclusion.envelope_sha256):
                raise ValueError("Draft inclusion must precede the exact provider authorization bundle")


class DraftReferenceClaimV1(_Frozen):
    kind: Literal["draft_reference_claim"]
    text: str = Field(min_length=1)
    draft_record_id: UUID



def _body_rows(packet):
    return [*packet.get("opened_passages", []), *packet.get("artifact_under_edit", {}).get("sections", []),
        *packet.get("decision", {}).get("state", {}).get("evidence", [])]


def _body_passages(packet):
    return packet.get("decision", {}).get("state", {}).get("passages", {})


def pack_body_aliases(packet):
    """Omit only byte-identical bodies; keep every authority/receipt selector."""
    from copy import deepcopy
    lane = packet.get("working_draft_context")
    if not isinstance(lane, dict) or lane.get("policy") != POLICY or not isinstance(lane.get("draft_markdown"),str):
        raise ValueError("Draft aliases require their explicit authored context lane")
    result = deepcopy(packet)
    rows = _body_rows(result)
    for row in rows:
        if isinstance(row, dict) and row.get("text") == lane.get("draft_markdown"):
            row.pop("text")
            row["text_ref"] = "working_draft_context"
    passages = _body_passages(result)
    for key, value in passages.items():
        if isinstance(value,str) and value == lane.get("draft_markdown"):
            passages[key] = {"text_ref":"working_draft_context"}
    return result


def resolve_body_aliases(packet):
    """Resolve exact carrier aliases before independent source-body comparison."""
    from copy import deepcopy
    rows = _body_rows(packet)
    if not (any(isinstance(row,dict) and "text_ref" in row for row in rows)
        or any(isinstance(value,dict) and "text_ref" in value for value in _body_passages(packet).values())):
        return packet
    result = deepcopy(packet)
    lane = result.get("working_draft_context")
    rows = _body_rows(result)
    for row in rows:
        if not isinstance(row, dict) or "text_ref" not in row:
            continue
        if ("text" in row or row["text_ref"] != "working_draft_context" or not isinstance(lane,dict)
            or lane.get("policy") != POLICY or not isinstance(lane.get("draft_markdown"),str)):
            raise ValueError("Source-body alias lacks its exact working-draft text")
        row.pop("text_ref")
        row["text"] = lane["draft_markdown"]
    passages = _body_passages(result)
    for key, value in passages.items():
        if not isinstance(value,dict) or "text_ref" not in value:
            continue
        if (set(value) != {"text_ref"} or value["text_ref"] != "working_draft_context"
            or not isinstance(lane,dict) or lane.get("policy") != POLICY
            or not isinstance(lane.get("draft_markdown"),str)):
            raise ValueError("Passage alias lacks its exact working-draft text")
        passages[key] = lane["draft_markdown"]
    return result
