"""SBW09c1: durable Threat publication-proposal models (handoff §6).

No-write publication-proposal authority: seal one exact ready SBW09a operation
plus one exact active SBW09b resolution into one reviewable proposal package.
This module never mutates the World Graph or predecessor stores.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Literal
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
from apps.live_control_server.models.threat_publication_identity import validate_resolution_id

PROPOSAL_SCHEMA = "dmb_threat_publication_proposal_v1"
LEDGER_SCHEMA = "dmb_threat_publication_proposal_ledger_v1"
PREPARE_REQUEST_SCHEMA = "dmb_prepare_threat_publication_proposal_request_v1"
RESPONSE_SCHEMA = "dmb_threat_publication_proposal_response_v1"

MAX_PROPOSALS_PER_OPERATION = 16

_PROPOSAL_ID_TPUB_RE = re.compile(r"^tpub_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

ProposalDecision = Literal["create_new", "connect_existing"]
ProposalState = Literal["active", "superseded"]

ThreatPublicationProposalResultLabel = Literal[
    "publication_proposal_ready",
    "publication_proposal_superseded",
    "publication_proposal_identity_refused",
    "publication_proposal_operation_not_ready",
    "publication_proposal_resolution_not_active",
    "publication_proposal_predecessor_mismatch",
    "publication_proposal_parent_mismatch",
    "publication_proposal_typed_collision",
    "publication_proposal_busy",
    "publication_proposal_input_conflict",
    "publication_proposal_history_full",
    "publication_proposal_not_found",
    "publication_proposal_graph_unavailable",
    "publication_proposal_storage_unavailable",
    "publication_proposal_integrity_failure",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def validate_proposal_id(value: str) -> str:
    cleaned = value.strip()
    try:
        return str(UUID(cleaned))
    except ValueError:
        if _PROPOSAL_ID_TPUB_RE.fullmatch(cleaned):
            return cleaned
        raise ValueError("invalid proposal_id") from None


class ThreatPublicationEffectSummaryV1(StrictModel):
    decision: ProposalDecision
    threat_node_id: str
    external_resource_node_id: str
    binding_edge_id: str
    accepted_assertion_count: int = Field(ge=0)
    authored_field_assertion_count: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class PrepareThreatPublicationProposalRequestV1(StrictModel):
    schema_name: Literal["dmb_prepare_threat_publication_proposal_request_v1"] = Field(
        default=PREPARE_REQUEST_SCHEMA, alias="schema"
    )
    proposal_id: str
    actor: str = Field(min_length=1, max_length=_MAX_ACTOR)
    operator_note: str | None = Field(default=None, max_length=_MAX_NOTE)
    supersedes_proposal_id: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("proposal_id", "supersedes_proposal_id")
    @classmethod
    def _proposal_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_proposal_id(value)


def prepare_request_digest(
    draft_id: str,
    operation_id: str,
    resolution_id: str,
    request: PrepareThreatPublicationProposalRequestV1,
) -> str:
    identity = {
        "draft_id": draft_id,
        "operation_id": operation_id,
        "resolution_id": resolution_id,
        "proposal_id": request.proposal_id,
        "actor": request.actor,
        "operator_note": request.operator_note,
        "supersedes_proposal_id": request.supersedes_proposal_id,
    }
    return _canonical_json_digest(identity)


class ThreatPublicationProposalV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_proposal_v1"] = Field(
        default=PROPOSAL_SCHEMA, alias="schema"
    )
    proposal_id: str
    request_digest: str = Field(pattern=_DIGEST_RE)
    draft_id: str
    operation_id: str
    resolution_id: str
    source_digest: str = Field(pattern=_DIGEST_RE)
    resolution_request_digest: str = Field(pattern=_DIGEST_RE)
    candidate_set_digest: str = Field(pattern=_DIGEST_RE)
    expected_parent_revision_id: str
    decision: ProposalDecision
    threat_node_id: str
    sealed_proposal_id: str
    sealed_proposal_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sealed_proposal_version: int = Field(ge=1)
    sealed_proposal: dict[str, Any]
    expected_contribution_id: str = Field(min_length=1)
    accepted_assertion_ids: list[str]
    effect_summary: ThreatPublicationEffectSummaryV1
    state: ProposalState
    supersedes_proposal_id: str | None = None
    superseded_by_proposal_id: str | None = None
    created_by: str = Field(min_length=1, max_length=_MAX_ACTOR)
    operator_note: str | None = Field(default=None, max_length=_MAX_NOTE)
    created_at: str = Field(min_length=1, max_length=64)
    updated_at: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("proposal_id", "sealed_proposal_id", "supersedes_proposal_id", "superseded_by_proposal_id")
    @classmethod
    def _proposal_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_proposal_id(value)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("resolution_id")
    @classmethod
    def _resolution_id(cls, value: str) -> str:
        return validate_resolution_id(value)

    @field_validator("expected_parent_revision_id")
    @classmethod
    def _parent(cls, value: str) -> str:
        return _require_parent_revision_id(value)

    @model_validator(mode="after")
    def _proposal_invariants(self) -> ThreatPublicationProposalV1:
        if self.proposal_id != self.sealed_proposal_id:
            raise ValueError("sealed_proposal_id must equal proposal_id")
        package_id = str(self.sealed_proposal.get("proposal_id") or "")
        if package_id != self.proposal_id:
            raise ValueError("sealed_proposal.proposal_id must equal proposal_id")
        package_digest = str(self.sealed_proposal.get("proposal_digest") or "")
        normalized = self.sealed_proposal_digest.removeprefix("sha256:")
        if package_digest not in {normalized, self.sealed_proposal_digest}:
            raise ValueError("sealed_proposal_digest does not match sealed_proposal package")
        if self.proposal_id == self.supersedes_proposal_id:
            raise ValueError("proposal cannot supersede itself")
        if self.proposal_id == self.superseded_by_proposal_id:
            raise ValueError("proposal cannot be superseded by itself")
        if self.state == "active" and self.superseded_by_proposal_id is not None:
            raise ValueError("active proposal cannot have superseded_by_proposal_id")
        if self.state == "superseded" and self.superseded_by_proposal_id is None:
            raise ValueError("superseded proposal requires superseded_by_proposal_id")
        if len(self.accepted_assertion_ids) != len(set(self.accepted_assertion_ids)):
            raise ValueError("accepted_assertion_ids must be unique")
        return self


class ThreatPublicationProposalLedgerV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_proposal_ledger_v1"] = Field(
        default=LEDGER_SCHEMA, alias="schema"
    )
    draft_id: str
    operation_id: str
    active_proposal_id: str | None = None
    proposals: list[ThreatPublicationProposalV1] = Field(
        default_factory=list, max_length=MAX_PROPOSALS_PER_OPERATION
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

    @field_validator("active_proposal_id")
    @classmethod
    def _active_proposal_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_proposal_id(value)

    @model_validator(mode="after")
    def _ledger_invariants(self) -> ThreatPublicationProposalLedgerV1:
        ids = [item.proposal_id for item in self.proposals]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate proposal_id in proposal ledger")
        by_id = {item.proposal_id: item for item in self.proposals}

        active_records = [item for item in self.proposals if item.state == "active"]
        if len(active_records) > 1:
            raise ValueError("more than one active publication proposal")
        if self.active_proposal_id is not None:
            active = by_id.get(self.active_proposal_id)
            if active is None:
                raise ValueError("active_proposal_id does not reference a ledger proposal")
            if active.state != "active":
                raise ValueError("active_proposal_id must reference an active proposal")
        elif active_records:
            raise ValueError("active proposal exists without active_proposal_id pointer")

        for proposal in self.proposals:
            if proposal.draft_id != self.draft_id:
                raise ValueError("proposal draft_id must match ledger draft_id")
            if proposal.operation_id != self.operation_id:
                raise ValueError("proposal operation_id must match ledger operation_id")
            expected_digest = prepare_request_digest(
                self.draft_id,
                self.operation_id,
                proposal.resolution_id,
                PrepareThreatPublicationProposalRequestV1.model_validate(
                    {
                        "proposal_id": proposal.proposal_id,
                        "actor": proposal.created_by,
                        "operator_note": proposal.operator_note,
                        "supersedes_proposal_id": proposal.supersedes_proposal_id,
                    }
                ),
            )
            if expected_digest != proposal.request_digest:
                raise ValueError("request_digest does not match recomputed proposal identity")

            if proposal.supersedes_proposal_id is not None:
                predecessor = by_id.get(proposal.supersedes_proposal_id)
                if predecessor is None:
                    raise ValueError("supersedes_proposal_id must reference a ledger proposal")
                if predecessor.superseded_by_proposal_id != proposal.proposal_id:
                    raise ValueError("supersession link is not bidirectional")
            if proposal.superseded_by_proposal_id is not None:
                successor = by_id.get(proposal.superseded_by_proposal_id)
                if successor is None:
                    raise ValueError("superseded_by_proposal_id must reference a ledger proposal")
                if successor.supersedes_proposal_id != proposal.proposal_id:
                    raise ValueError("supersession link is not bidirectional")

        for start_id in by_id:
            visited: set[str] = set()
            current: str | None = start_id
            while current is not None:
                if current in visited:
                    raise ValueError("proposal lineage contains a cycle")
                visited.add(current)
                current = by_id[current].supersedes_proposal_id
        return self


class ThreatPublicationProposalResponseV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_proposal_response_v1"] = Field(
        default=RESPONSE_SCHEMA, alias="schema"
    )
    draft_id: str
    operation_id: str
    resolution_id: str | None
    result_label: ThreatPublicationProposalResultLabel
    proposal: ThreatPublicationProposalV1 | None = None
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

    @field_validator("resolution_id")
    @classmethod
    def _resolution_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_resolution_id(value)


def canonical_string_list(values: list[str]) -> list[str]:
    cleaned = [item.strip() for item in values if isinstance(item, str) and item.strip()]
    return sorted(set(cleaned))


def deterministic_evidence_id(*parts: str) -> str:
    seed = "\0".join(parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"evidence:tpub:{digest}"


def operation_source_artifact_id(operation_id: str) -> str:
    return f"threat-publication-operation:{operation_id}"


def resolution_source_artifact_id(resolution_id: str) -> str:
    return f"threat-publication-resolution:{resolution_id}"


def operation_verified_source_uri(
    *, world_id: str, campaign_id: str, draft_id: str, operation_id: str
) -> str:
    return f"threat-publication://{world_id}/{campaign_id}/{draft_id}/{operation_id}"


def resolution_verified_source_uri(
    *, world_id: str, campaign_id: str, draft_id: str, operation_id: str, resolution_id: str
) -> str:
    return (
        f"threat-publication://{world_id}/{campaign_id}/{draft_id}/{operation_id}"
        f"/resolution/{resolution_id}"
    )
