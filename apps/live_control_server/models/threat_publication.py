"""SBW09a: durable Threat publication-operation ledger models (handoff §9).

No-write publication-operation authority: begin/read/refresh/cancel/retry over
a draft-scoped immutable source snapshot and expected World Graph parent. This
module never mutates ThreatDraft, accepted mechanics, DungeonMind, or the
World Graph; it only defines the strict contracts durable to
``out/threat_publication_operations/<draft_id>/ledger.json``.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptedMechanicsRefV1,
)
from apps.live_control_server.models.threat_draft import (
    EncounterContextV1,
    FocusV1,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    ThreatDraftV1,
    require_draft_id,
)

SOURCE_SNAPSHOT_SCHEMA = "dmb_threat_publication_source_v1"
OPERATION_SCHEMA = "dmb_threat_publication_operation_v1"
LEDGER_SCHEMA = "dmb_threat_publication_ledger_v1"
BEGIN_REQUEST_SCHEMA = "dmb_begin_threat_publication_operation_request_v1"
CANCEL_REQUEST_SCHEMA = "dmb_cancel_threat_publication_operation_request_v1"
RETRY_REQUEST_SCHEMA = "dmb_retry_threat_publication_operation_request_v1"
RESPONSE_SCHEMA = "dmb_threat_publication_operation_response_v1"

MAX_PUBLICATION_OPERATIONS_PER_DRAFT = 32

# Bounds mirror ThreatDraftV1 (apps/live_control_server/models/threat_draft.py)
# so the snapshot accepts exactly what the predecessor already validated.
_MAX_TEXT = 20_000
_MAX_LIST = 64
_MAX_NAME = 200
_MAX_SHORT = 64
_MAX_LIST_ELEMENT = 500
_MAX_ACTOR = 200
_MAX_NOTE = 2000

_OPERATION_ID_PUBOP_RE = re.compile(r"^pubop_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
# World Graph revision ids are typically `rev:<hex>`; accept the colon form.
_PARENT_REVISION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_DIGEST_RE = r"^sha256:[0-9a-f]{64}$"

StaleReason = Literal[
    "draft_version_changed",
    "source_digest_changed",
    "accepted_mechanics_changed",
    "world_or_campaign_changed",
    "graph_parent_changed",
]

OperationState = Literal["ready", "stale", "cancelled", "superseded"]

ThreatPublicationResultLabel = Literal[
    "publication_ready",
    "publication_stale",
    "publication_cancelled",
    "publication_superseded",
    "publication_busy",
    "publication_input_conflict",
    "publication_parent_mismatch",
    "publication_source_mismatch",
    "publication_history_full",
    "publication_not_found",
    "publication_draft_unavailable",
    "publication_graph_unavailable",
    "publication_storage_unavailable",
    "publication_integrity_failure",
    "publication_invalid_state",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def validate_publication_operation_id(value: str) -> str:
    """UUID or bounded ``pubop_...``; reject path traversal and aliasing."""
    cleaned = value.strip()
    try:
        return str(UUID(cleaned))
    except ValueError:
        if _OPERATION_ID_PUBOP_RE.fullmatch(cleaned):
            return cleaned
        raise ValueError("invalid publication operation_id") from None


def _require_parent_revision_id(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or not _PARENT_REVISION_ID_RE.fullmatch(cleaned):
        raise ValueError("invalid expected_parent_revision_id")
    return cleaned


def _bounded_string_list(values: list[str], *, label: str) -> list[str]:
    bounded: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise ValueError(f"invalid {label} element")
        cleaned = item.strip()
        if not cleaned:
            raise ValueError(f"empty {label} element")
        if len(cleaned) > _MAX_LIST_ELEMENT:
            raise ValueError(f"{label} element exceeds max length")
        bounded.append(cleaned)
    return bounded


def _canonical_json_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ThreatPublicationSourceSnapshotV1(StrictModel):
    """Immutable projection of committed ThreatDraft fields (handoff §9.4).

    No candidate bodies, statblock definitions, rules elements, rendered
    Markdown, mutable timestamps, candidate workflow lists, or UI state.
    """

    schema_name: Literal["dmb_threat_publication_source_v1"] = Field(
        default=SOURCE_SNAPSHOT_SCHEMA, alias="schema"
    )
    draft_id: str
    draft_version: int = Field(ge=1)
    world_id: str
    campaign_id: str
    focus: FocusV1 | None = None
    name: str = Field(min_length=1, max_length=_MAX_NAME)
    slug_hint: str | None = Field(default=None, max_length=_MAX_NAME)
    description: str = Field(min_length=1, max_length=_MAX_TEXT)
    threat_kind: str = Field(min_length=1, max_length=_MAX_SHORT)
    intended_roles: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    tags: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    generation_intent: GenerationIntentV1
    encounter_context: EncounterContextV1
    graph_context_snapshot: GraphContextSnapshotV1
    accepted_mechanics_ref: AcceptedMechanicsRefV1

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("intended_roles", "tags")
    @classmethod
    def _role_tag_items(cls, values: list[str]) -> list[str]:
        return _bounded_string_list(values, label="role or tag")


def source_digest_for_snapshot(snapshot: ThreatPublicationSourceSnapshotV1) -> str:
    """SHA-256 over sorted-key compact-separator alias JSON (handoff §9.4)."""
    return _canonical_json_digest(snapshot.model_dump(mode="json", by_alias=True))


def build_source_snapshot(draft: ThreatDraftV1) -> ThreatPublicationSourceSnapshotV1:
    """Build the immutable publication source snapshot from a committed draft.

    Callers must already have validated ``draft.workflow_state == mechanics_saved``
    and ``draft.accepted_mechanics_ref is not None`` before calling this.
    """
    if draft.accepted_mechanics_ref is None:
        raise ValueError("draft has no accepted_mechanics_ref")
    return ThreatPublicationSourceSnapshotV1(
        draft_id=draft.draft_id,
        draft_version=draft.version,
        world_id=draft.world_id,
        campaign_id=draft.campaign_id,
        focus=draft.focus,
        name=draft.name,
        slug_hint=draft.slug_hint,
        description=draft.description,
        threat_kind=draft.threat_kind,
        intended_roles=list(draft.intended_roles),
        tags=list(draft.tags),
        generation_intent=draft.generation_intent,
        encounter_context=draft.encounter_context,
        graph_context_snapshot=draft.graph_context_snapshot,
        accepted_mechanics_ref=draft.accepted_mechanics_ref,
    )


class BeginThreatPublicationOperationRequestV1(StrictModel):
    schema_name: Literal["dmb_begin_threat_publication_operation_request_v1"] = Field(
        default=BEGIN_REQUEST_SCHEMA, alias="schema"
    )
    operation_id: str
    expected_draft_version: int = Field(ge=1)
    expected_parent_revision_id: str
    actor: str = Field(min_length=1, max_length=_MAX_ACTOR)
    operator_note: str | None = Field(default=None, max_length=_MAX_NOTE)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("expected_parent_revision_id")
    @classmethod
    def _parent(cls, value: str) -> str:
        return _require_parent_revision_id(value)


class CancelThreatPublicationOperationRequestV1(StrictModel):
    schema_name: Literal["dmb_cancel_threat_publication_operation_request_v1"] = Field(
        default=CANCEL_REQUEST_SCHEMA, alias="schema"
    )
    actor: str = Field(min_length=1, max_length=_MAX_ACTOR)
    note: str | None = Field(default=None, max_length=_MAX_NOTE)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RetryThreatPublicationOperationRequestV1(StrictModel):
    schema_name: Literal["dmb_retry_threat_publication_operation_request_v1"] = Field(
        default=RETRY_REQUEST_SCHEMA, alias="schema"
    )
    new_operation_id: str
    expected_parent_revision_id: str
    actor: str = Field(min_length=1, max_length=_MAX_ACTOR)
    operator_note: str | None = Field(default=None, max_length=_MAX_NOTE)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("new_operation_id")
    @classmethod
    def _new_operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("expected_parent_revision_id")
    @classmethod
    def _parent(cls, value: str) -> str:
        return _require_parent_revision_id(value)


def begin_request_digest(
    draft_id: str, request: BeginThreatPublicationOperationRequestV1
) -> str:
    """Canonical digest over begin-request identity, including route draft_id."""
    identity = {
        "draft_id": draft_id,
        "operation_id": request.operation_id,
        "expected_draft_version": request.expected_draft_version,
        "expected_parent_revision_id": request.expected_parent_revision_id,
        "actor": request.actor,
        "operator_note": request.operator_note,
    }
    return _canonical_json_digest(identity)


def retry_request_digest(
    draft_id: str,
    operation_id: str,
    request: RetryThreatPublicationOperationRequestV1,
) -> str:
    """Canonical digest over retry-request identity (old + new operation ids)."""
    identity = {
        "draft_id": draft_id,
        "operation_id": operation_id,
        "new_operation_id": request.new_operation_id,
        "expected_parent_revision_id": request.expected_parent_revision_id,
        "actor": request.actor,
        "operator_note": request.operator_note,
    }
    return _canonical_json_digest(identity)


class ThreatPublicationOperationV1(StrictModel):
    """Handoff §9.5. ``operator_note`` is additive to the literal field list so
    ``request_digest`` can be recomputed and verified on every ledger load
    (draft_id is supplied by the owning ``ThreatPublicationLedgerV1``).
    """

    schema_name: Literal["dmb_threat_publication_operation_v1"] = Field(
        default=OPERATION_SCHEMA, alias="schema"
    )
    operation_id: str
    request_digest: str = Field(pattern=_DIGEST_RE)
    source_snapshot: ThreatPublicationSourceSnapshotV1
    source_digest: str = Field(pattern=_DIGEST_RE)
    expected_parent_revision_id: str
    state: OperationState
    stale_reasons: list[StaleReason] = Field(default_factory=list, max_length=len(StaleReason.__args__))
    supersedes_operation_id: str | None = None
    superseded_by_operation_id: str | None = None
    cancelled_by: str | None = Field(default=None, max_length=_MAX_ACTOR)
    cancellation_note: str | None = Field(default=None, max_length=_MAX_NOTE)
    operator_note: str | None = Field(default=None, max_length=_MAX_NOTE)
    created_by: str = Field(min_length=1, max_length=_MAX_ACTOR)
    created_at: str = Field(min_length=1, max_length=64)
    updated_at: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("supersedes_operation_id", "superseded_by_operation_id")
    @classmethod
    def _lineage_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_publication_operation_id(value)

    @field_validator("expected_parent_revision_id")
    @classmethod
    def _parent(cls, value: str) -> str:
        return _require_parent_revision_id(value)

    @model_validator(mode="after")
    def _digest_and_state_invariants(self) -> ThreatPublicationOperationV1:
        recomputed_source_digest = source_digest_for_snapshot(self.source_snapshot)
        if recomputed_source_digest != self.source_digest:
            raise ValueError("source_digest does not match source_snapshot")

        if self.operation_id == self.supersedes_operation_id:
            raise ValueError("operation cannot supersede itself")
        if self.operation_id == self.superseded_by_operation_id:
            raise ValueError("operation cannot be superseded by itself")

        if self.state == "ready":
            if self.stale_reasons:
                raise ValueError("ready operation cannot have stale_reasons")
            if self.superseded_by_operation_id is not None:
                raise ValueError("ready operation cannot be superseded")
            if self.cancelled_by is not None or self.cancellation_note is not None:
                raise ValueError("ready operation cannot carry cancellation fields")
        elif self.state == "stale":
            if not self.stale_reasons:
                raise ValueError("stale operation requires at least one stale reason")
            if self.superseded_by_operation_id is not None:
                raise ValueError("stale operation cannot be superseded while active")
            if self.cancelled_by is not None or self.cancellation_note is not None:
                raise ValueError("stale operation cannot carry cancellation fields")
        elif self.state == "cancelled":
            if not self.cancelled_by:
                raise ValueError("cancelled operation requires cancelled_by")
            if self.superseded_by_operation_id is not None:
                raise ValueError("cancelled operation cannot be superseded")
        elif self.state == "superseded":
            if not self.superseded_by_operation_id:
                raise ValueError("superseded operation requires superseded_by_operation_id")
            if self.cancelled_by is not None or self.cancellation_note is not None:
                raise ValueError("superseded operation cannot carry cancellation fields")
        return self


class ThreatPublicationLedgerV1(StrictModel):
    """Handoff §9.6. Draft-scoped commit authority; at most one active op."""

    schema_name: Literal["dmb_threat_publication_ledger_v1"] = Field(
        default=LEDGER_SCHEMA, alias="schema"
    )
    draft_id: str
    active_operation_id: str | None = None
    operations: list[ThreatPublicationOperationV1] = Field(
        default_factory=list, max_length=MAX_PUBLICATION_OPERATIONS_PER_DRAFT
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("active_operation_id")
    @classmethod
    def _active_operation_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_publication_operation_id(value)

    @model_validator(mode="after")
    def _ledger_invariants(self) -> ThreatPublicationLedgerV1:
        ids = [op.operation_id for op in self.operations]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate operation_id in publication ledger")
        by_id = {op.operation_id: op for op in self.operations}

        active_like = [op for op in self.operations if op.state in ("ready", "stale")]
        if len(active_like) > 1:
            raise ValueError("more than one active publication operation")
        if self.active_operation_id is not None:
            active_op = by_id.get(self.active_operation_id)
            if active_op is None:
                raise ValueError("active_operation_id does not reference a ledger operation")
            if active_op.state not in ("ready", "stale"):
                raise ValueError("active_operation_id must reference a ready or stale operation")
        elif active_like:
            raise ValueError("active operation exists without active_operation_id pointer")

        for op in self.operations:
            if op.source_snapshot.draft_id != self.draft_id:
                raise ValueError("operation source_snapshot.draft_id must match ledger draft_id")
            expected_digest = _expected_request_digest_for_operation(self.draft_id, op)
            if expected_digest != op.request_digest:
                raise ValueError("request_digest does not match recomputed operation identity")

            if op.supersedes_operation_id is not None:
                predecessor = by_id.get(op.supersedes_operation_id)
                if predecessor is None:
                    raise ValueError("supersedes_operation_id must reference a ledger operation")
                if predecessor.superseded_by_operation_id != op.operation_id:
                    raise ValueError("supersession link is not bidirectional")
                if predecessor.source_digest != op.source_digest:
                    raise ValueError("retry lineage must preserve source_digest exactly")
            if op.superseded_by_operation_id is not None:
                successor = by_id.get(op.superseded_by_operation_id)
                if successor is None:
                    raise ValueError("superseded_by_operation_id must reference a ledger operation")
                if successor.supersedes_operation_id != op.operation_id:
                    raise ValueError("supersession link is not bidirectional")

        for start_id in by_id:
            visited: set[str] = set()
            current: str | None = start_id
            while current is not None:
                if current in visited:
                    raise ValueError("publication lineage contains a cycle")
                visited.add(current)
                current = by_id[current].supersedes_operation_id
        return self


def _expected_request_digest_for_operation(
    draft_id: str, op: ThreatPublicationOperationV1
) -> str:
    """Recompute the request digest an operation must carry (ledger-load check).

    Mirrors ``begin_request_digest``/``retry_request_digest`` exactly; draft_id
    is supplied by the owning ledger since the operation record does not embed it.
    """
    if op.supersedes_operation_id is not None:
        identity = {
            "draft_id": draft_id,
            "operation_id": op.supersedes_operation_id,
            "new_operation_id": op.operation_id,
            "expected_parent_revision_id": op.expected_parent_revision_id,
            "actor": op.created_by,
            "operator_note": op.operator_note,
        }
    else:
        identity = {
            "draft_id": draft_id,
            "operation_id": op.operation_id,
            "expected_draft_version": op.source_snapshot.draft_version,
            "expected_parent_revision_id": op.expected_parent_revision_id,
            "actor": op.created_by,
            "operator_note": op.operator_note,
        }
    return _canonical_json_digest(identity)


class ThreatPublicationOperationResponseV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_operation_response_v1"] = Field(
        default=RESPONSE_SCHEMA, alias="schema"
    )
    draft_id: str
    result_label: ThreatPublicationResultLabel
    operation: ThreatPublicationOperationV1 | None = None
    message: str | None = Field(default=None, max_length=_MAX_NOTE)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
