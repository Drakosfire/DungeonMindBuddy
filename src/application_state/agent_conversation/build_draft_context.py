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
    context_sha = digest({"snapshot": record.snapshot.model_dump(mode="json", by_alias=True),
        "conversation_id": str(record.conversation_id), "expected_pointer_revision": record.expected_pointer_revision})
    receipt = turn.graph_context_receipt
    if (execution is None or receipt is None
        or getattr(execution.policy, "working_draft_context_policy", None) != POLICY
        or getattr(execution.policy, "working_draft_snapshot_sha256", None) != record.snapshot.snapshot_sha256
        or getattr(execution.policy, "working_draft_context_sha256", None) != context_sha):
        raise ValueError("Working draft lacks its frozen context capability")
    if (record.turn_id != turn.turn_id or record.conversation_id != turn.conversation_id
        or record.attempt != turn.attempt or record.submitted_intent_fingerprint != turn.submitted_intent_fingerprint_v2
        or record.snapshot.world_id != turn.world_id
        or record.snapshot.saved_basis() != receipt.source_basis.model_dump(mode="json", by_alias=True)):
        raise ValueError("Working draft differs from its accepted turn and saved basis")


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
    from .types import BuildDraftContextCapturedV1, ProviderAttemptAuthorizedEventV1, BuildWriterEvidenceSelectionV1
    rows = [e for e in execution.events if isinstance(e, BuildDraftContextCapturedV1)]
    if len(rows) > 1:
        raise ValueError("A turn captures one immutable working draft")
    for event in rows:
        if (getattr(execution.policy, "working_draft_context_policy", None) != POLICY
            or getattr(execution.policy, "working_draft_snapshot_sha256", None) != event.record.snapshot.snapshot_sha256):
            raise ValueError("Working draft differs from its frozen execution capability")
        if any(isinstance(e, BuildWriterEvidenceSelectionV1) or
            (isinstance(e, ProviderAttemptAuthorizedEventV1)
                and (e.provider,e.model,e.api_mode) == execution.policy.provider_roles.writer.identity())
            for e in execution.events[:event.sequence]):
            raise ValueError("Working draft cannot change after writer selection or authorization")


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
    rows = [e for e in execution.events if isinstance(e, BuildDraftProviderInclusionV1)]
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
            if (not isinstance(between, (BuildSectionProviderInclusionV1, RelatedRecapContextProviderInclusionEventV2))
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
