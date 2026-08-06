"""SBW09c2b: durable Threat publication-commit models (parent authority §6).

Proposal-bound commit authority: claim one exact active SBW09c1 proposal, persist
intent before Kernel mutation, recover via SBW09c2a, and pin verification to an
immutable revision. This module never mutates the World Graph or predecessor stores.
"""
from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import (
    _canonical_json_digest,
    _DIGEST_RE,
    _MAX_ACTOR,
    _MAX_NOTE,
    _require_parent_revision_id,
    validate_publication_operation_id,
)
from apps.live_control_server.models.threat_publication_identity import (
    ThreatIdentityCandidateV1,
    validate_resolution_id,
)
from apps.live_control_server.models.threat_publication_proposal import (
    validate_proposal_id,
)

COMMIT_SCHEMA = "dmb_threat_publication_commit_v1"
LEDGER_SCHEMA = "dmb_threat_publication_commit_ledger_v1"
CONFIRM_REQUEST_SCHEMA = "dmb_confirm_threat_publication_request_v1"
RESPONSE_SCHEMA = "dmb_threat_publication_commit_response_v1"

_COMMIT_ID_TCOMMIT_RE = re.compile(r"^tcommit_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_RAW_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_CODE_LIST = 64
_MAX_CODE_LEN = 200

CommitDecision = Literal["create_new", "connect_existing"]
CommitState = Literal[
    "committing",
    "uncommitted",
    "ambiguous",
    "committed_unverified",
    "committed_verified",
]
VerificationStatus = Literal["not_started", "passed", "degraded", "failed"]
MergeAttemptCount = Literal[1, 2]

ThreatPublicationCommitResultLabel = Literal[
    "publication_commit_verified",
    "publication_commit_committed_unverified",
    "publication_commit_recovery_pending",
    "publication_commit_uncommitted",
    "publication_commit_outcome_ambiguous",
    "publication_commit_proposal_not_active",
    "publication_commit_proposal_incompatible",
    "publication_commit_operation_not_ready",
    "publication_commit_resolution_not_active",
    "publication_commit_predecessor_mismatch",
    "publication_commit_parent_mismatch",
    "publication_commit_busy",
    "publication_commit_input_conflict",
    "publication_commit_not_found",
    "publication_commit_graph_unavailable",
    "publication_commit_storage_unavailable",
    "publication_commit_integrity_failure",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def validate_commit_id(value: str) -> str:
    cleaned = value.strip()
    try:
        return str(UUID(cleaned))
    except ValueError:
        if _COMMIT_ID_TCOMMIT_RE.fullmatch(cleaned):
            return cleaned
        raise ValueError("invalid commit_id") from None


def _bounded_unique_codes(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = item.strip()
        if not text:
            raise ValueError("code entries must be nonblank")
        if len(text) > _MAX_CODE_LEN:
            raise ValueError("code entry exceeds bound")
        if text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    if len(cleaned) > _MAX_CODE_LIST:
        raise ValueError("code list exceeds bound")
    return cleaned


class ConfirmThreatPublicationRequestV1(StrictModel):
    schema_name: Literal["dmb_confirm_threat_publication_request_v1"] = Field(
        default=CONFIRM_REQUEST_SCHEMA, alias="schema"
    )
    commit_id: str
    sealed_proposal_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_parent_revision_id: str
    actor: str = Field(min_length=1, max_length=_MAX_ACTOR)
    operator_note: str | None = Field(default=None, max_length=_MAX_NOTE)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("commit_id")
    @classmethod
    def _commit_id(cls, value: str) -> str:
        return validate_commit_id(value)

    @field_validator("expected_parent_revision_id")
    @classmethod
    def _parent(cls, value: str) -> str:
        return _require_parent_revision_id(value)


def confirm_request_digest(
    draft_id: str,
    operation_id: str,
    proposal_id: str,
    request: ConfirmThreatPublicationRequestV1,
) -> str:
    identity = {
        "draft_id": draft_id,
        "operation_id": operation_id,
        "proposal_id": proposal_id,
        "commit_id": request.commit_id,
        "sealed_proposal_digest": request.sealed_proposal_digest,
        "expected_parent_revision_id": request.expected_parent_revision_id,
        "actor": request.actor,
        "operator_note": request.operator_note,
    }
    return _canonical_json_digest(identity)


class ThreatPublicationCommitV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_commit_v1"] = Field(
        default=COMMIT_SCHEMA, alias="schema"
    )
    commit_id: str
    request_digest: str = Field(pattern=_DIGEST_RE)

    draft_id: str
    operation_id: str
    proposal_id: str
    proposal_request_digest: str = Field(pattern=_DIGEST_RE)
    sealed_proposal_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sealed_proposal_version: int = Field(ge=1)

    resolution_id: str
    source_digest: str = Field(pattern=_DIGEST_RE)
    resolution_request_digest: str = Field(pattern=_DIGEST_RE)
    candidate_set_digest: str = Field(pattern=_DIGEST_RE)
    world_id: str = Field(min_length=1, max_length=200)
    campaign_id: str = Field(min_length=1, max_length=200)
    expected_parent_revision_id: str

    expected_contribution_id: str = Field(min_length=1)
    expected_contribution_source_payload_sha256: str
    accepted_assertion_ids: list[str]

    decision: CommitDecision
    threat_node_id: str = Field(min_length=1)
    selected_target: ThreatIdentityCandidateV1 | None = None
    external_resource_node_id: str = Field(min_length=1)
    binding_id: str = Field(min_length=1)
    binding_edge_id: str = Field(min_length=1)

    state: CommitState
    merge_attempt_count: MergeAttemptCount
    committed_revision_id: str | None = None
    recovered_via_operation_lookup: bool = False
    verification_status: VerificationStatus = "not_started"
    verification_codes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    created_by: str = Field(min_length=1, max_length=_MAX_ACTOR)
    operator_note: str | None = Field(default=None, max_length=_MAX_NOTE)
    created_at: str = Field(min_length=1, max_length=64)
    updated_at: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("commit_id")
    @classmethod
    def _commit_id(cls, value: str) -> str:
        return validate_commit_id(value)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("proposal_id")
    @classmethod
    def _proposal_id(cls, value: str) -> str:
        return validate_proposal_id(value)

    @field_validator("resolution_id")
    @classmethod
    def _resolution_id(cls, value: str) -> str:
        return validate_resolution_id(value)

    @field_validator("expected_parent_revision_id", "committed_revision_id")
    @classmethod
    def _parent_or_revision(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_parent_revision_id(value)

    @field_validator("expected_contribution_source_payload_sha256")
    @classmethod
    def _source_digest(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not _RAW_SHA256_RE.fullmatch(cleaned):
            raise ValueError(
                "expected_contribution_source_payload_sha256 must be raw lowercase 64-hex"
            )
        return cleaned

    @field_validator("verification_codes", "warnings")
    @classmethod
    def _codes(cls, value: list[str]) -> list[str]:
        return _bounded_unique_codes(value)

    @model_validator(mode="after")
    def _commit_invariants(self) -> ThreatPublicationCommitV1:
        if len(self.accepted_assertion_ids) != len(set(self.accepted_assertion_ids)):
            raise ValueError("accepted_assertion_ids must be unique")

        if self.decision == "create_new" and self.selected_target is not None:
            raise ValueError("create_new requires selected_target=null")
        if self.decision == "connect_existing" and self.selected_target is None:
            raise ValueError("connect_existing requires selected_target")

        noncommitted = self.state in {"committing", "uncommitted", "ambiguous"}
        committed = self.state in {"committed_unverified", "committed_verified"}
        if noncommitted and self.committed_revision_id is not None:
            raise ValueError(f"{self.state} requires committed_revision_id=null")
        if committed and not self.committed_revision_id:
            raise ValueError(f"{self.state} requires a nonblank committed_revision_id")

        if self.state == "committed_verified" and self.verification_status != "passed":
            raise ValueError("committed_verified requires verification_status=passed")
        if self.state == "committed_unverified" and self.verification_status not in {
            "not_started",
            "degraded",
            "failed",
        }:
            raise ValueError(
                "committed_unverified permits only not_started, degraded, or failed"
            )
        if noncommitted and self.verification_status != "not_started":
            raise ValueError("noncommitted states require verification_status=not_started")

        if self.recovered_via_operation_lookup and not self.committed_revision_id:
            raise ValueError(
                "recovered_via_operation_lookup=true requires a committed revision"
            )
        return self


class ThreatPublicationCommitLedgerV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_commit_ledger_v1"] = Field(
        default=LEDGER_SCHEMA, alias="schema"
    )
    draft_id: str
    operation_id: str
    commit: ThreatPublicationCommitV1

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @model_validator(mode="after")
    def _ledger_invariants(self) -> ThreatPublicationCommitLedgerV1:
        if self.commit.draft_id != self.draft_id:
            raise ValueError("commit draft_id must match ledger draft_id")
        if self.commit.operation_id != self.operation_id:
            raise ValueError("commit operation_id must match ledger operation_id")
        return self


class ThreatPublicationCommitResponseV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_commit_response_v1"] = Field(
        default=RESPONSE_SCHEMA, alias="schema"
    )
    draft_id: str
    operation_id: str
    proposal_id: str | None
    commit_id: str
    result_label: ThreatPublicationCommitResultLabel
    commit: ThreatPublicationCommitV1 | None = None
    # True means the confirm request was admitted into the durable commit ledger.
    # Admitted responses must carry that exact record; pre-admission responses do not.
    commit_admitted: bool
    retry_allowed: bool
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

    @field_validator("proposal_id")
    @classmethod
    def _proposal_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_proposal_id(value)

    @field_validator("commit_id")
    @classmethod
    def _commit_id(cls, value: str) -> str:
        return validate_commit_id(value)

    @model_validator(mode="after")
    def _admission_matches_record(self) -> ThreatPublicationCommitResponseV1:
        if self.commit_admitted != (self.commit is not None):
            raise ValueError("commit_admitted must match whether the durable commit record is present")
        return self
