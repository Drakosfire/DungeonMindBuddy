"""SBW09b: Threat publication identity-resolution models (handoff §9).

Durable explicit create-new / connect-existing / refuse identity authority for
one SBW09a publication operation. No World Graph, ThreatDraft, or mechanics
mutation — contracts only.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import (
    OperationState,
    ThreatPublicationSourceSnapshotV1,
    validate_publication_operation_id,
    _canonical_json_digest,
    _DIGEST_RE,
    _MAX_ACTOR,
    _MAX_NOTE,
    _require_parent_revision_id,
)

PREPARE_REQUEST_SCHEMA = "dmb_prepare_threat_identity_candidates_request_v1"
CANDIDATE_SET_SCHEMA = "dmb_threat_publication_identity_candidate_set_v1"
CREATE_REQUEST_SCHEMA = "dmb_create_threat_identity_resolution_request_v1"
RESOLUTION_SCHEMA = "dmb_threat_publication_identity_resolution_v1"
LEDGER_SCHEMA = "dmb_threat_publication_identity_ledger_v1"
RESPONSE_SCHEMA = "dmb_threat_publication_identity_response_v1"

MATCHING_PROFILE_V1 = "dmb_threat_identity_match_v1"
SUGGESTED_ADVISORY_CANDIDATES = 12
MAX_TOTAL_CANDIDATES = 32
MAX_RESOLUTIONS_PER_OPERATION = 16
MAX_QUERY_TEXT = 500
_CREATED_NODE_ID_RE = re.compile(r"^threat:authored:[0-9a-f]{32}$")

_RESOLUTION_ID_TRES_RE = re.compile(r"^tres_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

IdentityDecision = Literal["create_new", "connect_existing", "refuse"]
ResolutionState = Literal["active", "superseded"]

ThreatPublicationIdentityResultLabel = Literal[
    "publication_identity_candidates_ready",
    "publication_identity_created_new",
    "publication_identity_connected_existing",
    "publication_identity_refused",
    "publication_identity_superseded",
    "publication_identity_operation_not_ready",
    "publication_identity_candidate_overflow",
    "publication_identity_candidate_set_changed",
    "publication_identity_review_required",
    "publication_identity_target_not_found",
    "publication_identity_target_invalid",
    "publication_identity_new_id_collision",
    "publication_identity_busy",
    "publication_identity_input_conflict",
    "publication_identity_history_full",
    "publication_identity_not_found",
    "publication_identity_graph_unavailable",
    "publication_identity_storage_unavailable",
    "publication_identity_integrity_failure",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def validate_resolution_id(value: str) -> str:
    cleaned = value.strip()
    try:
        return str(UUID(cleaned))
    except ValueError:
        if _RESOLUTION_ID_TRES_RE.fullmatch(cleaned):
            return cleaned
        raise ValueError("invalid resolution_id") from None


def normalize_exact_collision_text(text: str) -> str:
    """NFKC → trim → collapse internal whitespace → casefold; punctuation preserved."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.casefold()


def derive_created_node_id(
    *,
    world_id: str,
    campaign_id: str,
    draft_id: str,
    operation_id: str,
) -> str:
    """Handoff §9.7 deterministic proposed Threat ID."""
    seed = "\0".join(
        ["dmb_threat_identity_v1", world_id, campaign_id, draft_id, operation_id]
    )
    digest_hex = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
    created = f"threat:authored:{digest_hex}"
    if not _CREATED_NODE_ID_RE.fullmatch(created):
        raise ValueError("derived created_node_id has invalid form")
    return created


class PrepareThreatIdentityCandidatesRequestV1(StrictModel):
    schema_name: Literal["dmb_prepare_threat_identity_candidates_request_v1"] = Field(
        default=PREPARE_REQUEST_SCHEMA, alias="schema"
    )
    query_text: str | None = Field(default=None, max_length=MAX_QUERY_TEXT)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("query_text")
    @classmethod
    def _query_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query_text must be nonblank when supplied")
        return cleaned


class ThreatIdentityCandidateV1(StrictModel):
    node_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    role: str = Field(min_length=1)
    aliases: list[str]
    campaign_scope: str | None = None
    summary: str | None = None
    source_domains: list[str]
    binding_ids: list[str]
    has_exact_accepted_binding: bool
    match_score: int
    match_reasons: list[str]
    exact_name_collision: bool

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _candidate_snapshots_equal(
    left: ThreatIdentityCandidateV1, right: ThreatIdentityCandidateV1
) -> bool:
    return left.model_dump(mode="json", by_alias=True) == right.model_dump(
        mode="json", by_alias=True
    )


class ThreatIdentityCandidateSetV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_identity_candidate_set_v1"] = Field(
        default=CANDIDATE_SET_SCHEMA, alias="schema"
    )
    draft_id: str
    operation_id: str
    source_digest: str = Field(pattern=_DIGEST_RE)
    expected_parent_revision_id: str
    matching_profile: Literal["dmb_threat_identity_match_v1"]
    candidate_query: str
    eligible_threat_count: int = Field(ge=0)
    exact_collision_count: int = Field(ge=0)
    truncated: bool
    candidates: list[ThreatIdentityCandidateV1]
    candidate_set_digest: str = Field(pattern=_DIGEST_RE)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("expected_parent_revision_id")
    @classmethod
    def _parent(cls, value: str) -> str:
        return _require_parent_revision_id(value)

    @field_validator("candidate_query")
    @classmethod
    def _candidate_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("candidate_query must be nonblank")
        if len(cleaned) > MAX_QUERY_TEXT:
            raise ValueError("candidate_query exceeds maximum length")
        return cleaned

    @model_validator(mode="after")
    def _digest_and_candidates(self) -> ThreatIdentityCandidateSetV1:
        ids = [c.node_id for c in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate candidate node_id")
        if len(self.candidates) > MAX_TOTAL_CANDIDATES:
            raise ValueError("candidate count exceeds maximum")
        if len(self.candidates) > self.eligible_threat_count:
            raise ValueError("candidate count exceeds eligible_threat_count")
        collision_flags = sum(1 for c in self.candidates if c.exact_name_collision)
        if collision_flags != self.exact_collision_count:
            raise ValueError("exact_collision_count does not match candidate flags")
        for candidate in self.candidates:
            if candidate.kind.casefold() != "threat":
                raise ValueError("candidate kind must be Threat")
        expected = candidate_set_digest_for_set(self)
        if expected != self.candidate_set_digest:
            raise ValueError("candidate_set_digest does not match recomputed digest")
        return self


def candidate_set_digest_payload(candidate_set: ThreatIdentityCandidateSetV1) -> dict[str, Any]:
    dumped = candidate_set.model_dump(mode="json", by_alias=True)
    dumped.pop("candidate_set_digest", None)
    return dumped


def candidate_set_digest_for_set(candidate_set: ThreatIdentityCandidateSetV1) -> str:
    return _canonical_json_digest(candidate_set_digest_payload(candidate_set))


class CreateThreatIdentityResolutionRequestV1(StrictModel):
    schema_name: Literal["dmb_create_threat_identity_resolution_request_v1"] = Field(
        default=CREATE_REQUEST_SCHEMA, alias="schema"
    )
    resolution_id: str
    matching_profile: Literal["dmb_threat_identity_match_v1"]
    candidate_query: str = Field(min_length=1, max_length=MAX_QUERY_TEXT)
    candidate_set_digest: str = Field(pattern=_DIGEST_RE)
    decision: IdentityDecision
    target_node_id: str | None = None
    rejected_candidate_node_ids: list[str]
    actor: str = Field(min_length=1, max_length=_MAX_ACTOR)
    reason: str = Field(min_length=1, max_length=_MAX_NOTE)
    supersedes_resolution_id: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("resolution_id", "supersedes_resolution_id")
    @classmethod
    def _resolution_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_resolution_id(value)

    @field_validator("candidate_query")
    @classmethod
    def _candidate_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("candidate_query must be nonblank")
        return cleaned

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("reason must be nonblank")
        return cleaned


def resolution_request_digest(
    draft_id: str,
    operation_id: str,
    request: CreateThreatIdentityResolutionRequestV1,
) -> str:
    identity = {
        "draft_id": draft_id,
        "operation_id": operation_id,
        "resolution_id": request.resolution_id,
        "matching_profile": request.matching_profile,
        "candidate_query": request.candidate_query,
        "candidate_set_digest": request.candidate_set_digest,
        "decision": request.decision,
        "target_node_id": request.target_node_id,
        "rejected_candidate_node_ids": sorted(request.rejected_candidate_node_ids),
        "actor": request.actor,
        "reason": request.reason,
        "supersedes_resolution_id": request.supersedes_resolution_id,
    }
    return _canonical_json_digest(identity)


def resolution_request_from_resolution(
    resolution: ThreatPublicationIdentityResolutionV1,
) -> CreateThreatIdentityResolutionRequestV1:
    target_node_id: str | None = None
    if resolution.decision == "connect_existing" and resolution.selected_target is not None:
        target_node_id = resolution.selected_target.node_id
    return CreateThreatIdentityResolutionRequestV1(
        resolution_id=resolution.resolution_id,
        matching_profile=resolution.matching_profile,
        candidate_query=resolution.candidate_query,
        candidate_set_digest=resolution.candidate_set_digest,
        decision=resolution.decision,
        target_node_id=target_node_id,
        rejected_candidate_node_ids=list(resolution.rejected_candidate_node_ids),
        actor=resolution.actor,
        reason=resolution.reason,
        supersedes_resolution_id=resolution.supersedes_resolution_id,
    )


class ThreatPublicationIdentityResolutionV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_identity_resolution_v1"] = Field(
        default=RESOLUTION_SCHEMA, alias="schema"
    )
    resolution_id: str
    draft_id: str
    operation_id: str
    source_digest: str = Field(pattern=_DIGEST_RE)
    expected_parent_revision_id: str
    matching_profile: Literal["dmb_threat_identity_match_v1"]
    candidate_query: str
    candidate_set: ThreatIdentityCandidateSetV1
    candidate_set_digest: str = Field(pattern=_DIGEST_RE)
    request_digest: str = Field(pattern=_DIGEST_RE)
    decision: IdentityDecision
    selected_target: ThreatIdentityCandidateV1 | None = None
    created_node_id: str | None = None
    rejected_candidate_node_ids: list[str] = Field(default_factory=list)
    actor: str = Field(min_length=1, max_length=_MAX_ACTOR)
    reason: str = Field(min_length=1, max_length=_MAX_NOTE)
    state: ResolutionState
    supersedes_resolution_id: str | None = None
    superseded_by_resolution_id: str | None = None
    created_at: str = Field(min_length=1, max_length=64)
    updated_at: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("resolution_id", "supersedes_resolution_id", "superseded_by_resolution_id")
    @classmethod
    def _resolution_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_resolution_id(value)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("expected_parent_revision_id")
    @classmethod
    def _parent(cls, value: str) -> str:
        return _require_parent_revision_id(value)

    @field_validator("candidate_query")
    @classmethod
    def _candidate_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("candidate_query must be nonblank")
        if len(cleaned) > MAX_QUERY_TEXT:
            raise ValueError("candidate_query exceeds maximum length")
        return cleaned

    @field_validator("created_node_id")
    @classmethod
    def _created_node_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _CREATED_NODE_ID_RE.fullmatch(value):
            raise ValueError("created_node_id has invalid form")
        return value

    @model_validator(mode="after")
    def _resolution_invariants(self) -> ThreatPublicationIdentityResolutionV1:
        if self.candidate_set_digest != self.candidate_set.candidate_set_digest:
            raise ValueError("candidate_set_digest does not match embedded candidate_set")
        if self.candidate_query != self.candidate_set.candidate_query:
            raise ValueError("candidate_query does not match embedded candidate_set")
        expected_request_digest = resolution_request_digest(
            self.draft_id,
            self.operation_id,
            resolution_request_from_resolution(self),
        )
        if expected_request_digest != self.request_digest:
            raise ValueError("request_digest does not match recomputed digest")
        candidate_ids = {c.node_id for c in self.candidate_set.candidates}
        candidate_by_id = {c.node_id: c for c in self.candidate_set.candidates}
        if len(self.rejected_candidate_node_ids) != len(set(self.rejected_candidate_node_ids)):
            raise ValueError("rejected_candidate_node_ids must be unique")
        if not set(self.rejected_candidate_node_ids).issubset(candidate_ids):
            raise ValueError("rejected_candidate_node_ids must be members of candidate set")
        if self.decision == "create_new":
            if self.selected_target is not None or self.created_node_id is None:
                raise ValueError("create_new requires created_node_id and no selected_target")
        elif self.decision == "connect_existing":
            if self.selected_target is None or self.created_node_id is not None:
                raise ValueError("connect_existing requires selected_target and no created_node_id")
            if self.selected_target.node_id not in candidate_ids:
                raise ValueError("selected_target must be a snapshotted candidate")
            if self.selected_target.kind.casefold() != "threat":
                raise ValueError("selected_target kind must be Threat")
            snapshotted = candidate_by_id[self.selected_target.node_id]
            if not _candidate_snapshots_equal(self.selected_target, snapshotted):
                raise ValueError("selected_target must equal the complete snapshotted candidate")
            if self.selected_target.node_id in self.rejected_candidate_node_ids:
                raise ValueError("selected_target cannot be rejected")
        elif self.decision == "refuse":
            if self.selected_target is not None or self.created_node_id is not None:
                raise ValueError("refuse requires no selected_target or created_node_id")
        if self.state == "active" and self.superseded_by_resolution_id is not None:
            raise ValueError("active resolution cannot have superseded_by_resolution_id")
        if self.state == "superseded" and self.superseded_by_resolution_id is None:
            raise ValueError("superseded resolution requires superseded_by_resolution_id")
        return self


class ThreatPublicationIdentityLedgerV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_identity_ledger_v1"] = Field(
        default=LEDGER_SCHEMA, alias="schema"
    )
    draft_id: str
    operation_id: str
    source_digest: str = Field(pattern=_DIGEST_RE)
    expected_parent_revision_id: str
    active_resolution_id: str | None = None
    resolutions: list[ThreatPublicationIdentityResolutionV1] = Field(
        max_length=MAX_RESOLUTIONS_PER_OPERATION
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("active_resolution_id")
    @classmethod
    def _active_resolution_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_resolution_id(value)

    @field_validator("expected_parent_revision_id")
    @classmethod
    def _parent(cls, value: str) -> str:
        return _require_parent_revision_id(value)

    @model_validator(mode="after")
    def _ledger_invariants(self) -> ThreatPublicationIdentityLedgerV1:
        ids = [r.resolution_id for r in self.resolutions]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate resolution_id in identity ledger")
        by_id = {r.resolution_id: r for r in self.resolutions}

        active_records = [r for r in self.resolutions if r.state == "active"]
        if len(active_records) > 1:
            raise ValueError("more than one active identity resolution")
        if self.active_resolution_id is not None:
            active = by_id.get(self.active_resolution_id)
            if active is None:
                raise ValueError("active_resolution_id does not reference a ledger resolution")
            if active.state != "active":
                raise ValueError("active_resolution_id must reference an active resolution")
        elif active_records:
            raise ValueError("active resolution exists without active_resolution_id pointer")

        for resolution in self.resolutions:
            if resolution.draft_id != self.draft_id:
                raise ValueError("resolution draft_id must match ledger draft_id")
            if resolution.operation_id != self.operation_id:
                raise ValueError("resolution operation_id must match ledger operation_id")
            if resolution.source_digest != self.source_digest:
                raise ValueError("resolution source_digest must match ledger source_digest")
            if resolution.expected_parent_revision_id != self.expected_parent_revision_id:
                raise ValueError(
                    "resolution expected_parent_revision_id must match ledger"
                )
            if resolution.candidate_set.draft_id != self.draft_id:
                raise ValueError("candidate_set draft_id must match ledger draft_id")
            if resolution.candidate_set.operation_id != self.operation_id:
                raise ValueError("candidate_set operation_id must match ledger operation_id")
            if resolution.candidate_set.source_digest != self.source_digest:
                raise ValueError("candidate_set source_digest must match ledger source_digest")
            if (
                resolution.candidate_set.expected_parent_revision_id
                != self.expected_parent_revision_id
            ):
                raise ValueError(
                    "candidate_set expected_parent_revision_id must match ledger"
                )

            if resolution.supersedes_resolution_id is not None:
                predecessor = by_id.get(resolution.supersedes_resolution_id)
                if predecessor is None:
                    raise ValueError("supersedes_resolution_id must reference a ledger resolution")
                if predecessor.superseded_by_resolution_id != resolution.resolution_id:
                    raise ValueError("supersession link is not bidirectional")
            if resolution.superseded_by_resolution_id is not None:
                successor = by_id.get(resolution.superseded_by_resolution_id)
                if successor is None:
                    raise ValueError("superseded_by_resolution_id must reference a ledger resolution")
                if successor.supersedes_resolution_id != resolution.resolution_id:
                    raise ValueError("supersession link is not bidirectional")

        for start_id in by_id:
            visited: set[str] = set()
            current: str | None = start_id
            while current is not None:
                if current in visited:
                    raise ValueError("identity resolution lineage contains a cycle")
                visited.add(current)
                current = by_id[current].supersedes_resolution_id
        return self


class ThreatPublicationIdentityResponseV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_identity_response_v1"] = Field(
        default=RESPONSE_SCHEMA, alias="schema"
    )
    draft_id: str
    operation_id: str
    result_label: ThreatPublicationIdentityResultLabel
    candidate_set: ThreatIdentityCandidateSetV1 | None = None
    resolution: ThreatPublicationIdentityResolutionV1 | None = None
    predecessor_state: OperationState | None = None
    predecessor_usable: bool
    message: str | None = Field(default=None, max_length=_MAX_NOTE)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)


def source_name_from_snapshot(snapshot: ThreatPublicationSourceSnapshotV1) -> str:
    return snapshot.name.strip()
