"""SBW09a: durable Threat/statblock publication-operation contracts."""
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
    GraphContextSnapshotV1,
    require_draft_id,
)

PUBLICATION_OPERATION_SCHEMA = "dmb_threat_statblock_publication_operation_v1"
SOURCE_SNAPSHOT_SCHEMA = "dmb_threat_publication_source_snapshot_v1"
BEGIN_REQUEST_SCHEMA = "dmb_begin_threat_statblock_publication_request_v1"
RESPONSE_SCHEMA = "dmb_threat_statblock_publication_operation_response_v1"
ERROR_SCHEMA = "dmb_threat_statblock_publication_error_v1"

_GRAPH_REVISION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_OPERATION_ID_PUBOP_RE = re.compile(r"^pubop_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

AuthorityState = Literal[
    "awaiting_identity_resolution",
    "identity_resolved",
    "prepared",
    "confirming",
    "committed_unverified",
    "verified",
    "stale",
    "failed",
    "cancelled",
]

PublicationResultLabel = Literal[
    "publication_claimed",
    "publication_resumed",
    "publication_stale",
    "publication_cancelled",
]

ArtifactKind = Literal[
    "identity_resolution",
    "prepared_graph_plan",
    "graph_commit_receipt",
    "publication_verification",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def validate_publication_operation_id(value: str) -> str:
    cleaned = value.strip()
    try:
        return str(UUID(cleaned))
    except ValueError:
        if _OPERATION_ID_PUBOP_RE.fullmatch(cleaned):
            return cleaned
        raise ValueError("invalid operation_id")


def _require_graph_revision_id(value: str) -> str:
    cleaned = value.strip()
    if not _GRAPH_REVISION_ID_RE.fullmatch(cleaned):
        raise ValueError("invalid graph revision id")
    return cleaned


def canonical_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def claim_request_digest_for_begin(
    *,
    draft_id: str,
    operation_id: str,
    expected_draft_version: int,
    expected_parent_revision_id: str,
) -> str:
    body = {
        "schema": BEGIN_REQUEST_SCHEMA,
        "draft_id": require_draft_id(draft_id),
        "operation_id": validate_publication_operation_id(operation_id),
        "expected_draft_version": expected_draft_version,
        "expected_parent_revision_id": _require_graph_revision_id(
            expected_parent_revision_id
        ),
    }
    return canonical_digest(body)


class ThreatPublicationSourceSnapshotV1(StrictModel):
    schema_name: Literal["dmb_threat_publication_source_snapshot_v1"] = Field(
        default=SOURCE_SNAPSHOT_SCHEMA, alias="schema"
    )
    source_draft_id: str
    source_draft_version: int = Field(ge=1)
    world_id: str
    campaign_id: str
    name: str
    description: str
    threat_kind: str
    intended_roles: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    graph_context_snapshot: GraphContextSnapshotV1
    accepted_mechanics_ref: AcceptedMechanicsRefV1

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("source_draft_id")
    @classmethod
    def _source_draft_id(cls, value: str) -> str:
        return require_draft_id(value)


def source_snapshot_digest_for(snapshot: ThreatPublicationSourceSnapshotV1) -> str:
    return canonical_digest(snapshot.model_dump(mode="json", by_alias=True))


class PublicationArtifactRefV1(StrictModel):
    artifact_kind: ArtifactKind
    artifact_id: str = Field(min_length=1, max_length=128)
    artifact_schema: str = Field(min_length=1, max_length=128)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    storage_owner: str = Field(min_length=1, max_length=128)


class ThreatStatblockPublicationOperationV1(StrictModel):
    schema_name: Literal["dmb_threat_statblock_publication_operation_v1"] = Field(
        default=PUBLICATION_OPERATION_SCHEMA, alias="schema"
    )
    operation_id: str
    operation_version: int = Field(ge=1)
    claim_request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_snapshot: ThreatPublicationSourceSnapshotV1
    source_snapshot_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    world_id: str
    campaign_id: str
    expected_parent_revision_id: str
    last_observed_head_revision_id: str
    authority_state: AuthorityState
    phase_artifacts: list[PublicationArtifactRefV1] = Field(default_factory=list)
    terminal_code: str | None = None
    terminal_message: str | None = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("expected_parent_revision_id", "last_observed_head_revision_id")
    @classmethod
    def _revision_ids(cls, value: str) -> str:
        return _require_graph_revision_id(value)

    @model_validator(mode="after")
    def _invariants(self) -> ThreatStatblockPublicationOperationV1:
        recomputed_snapshot = source_snapshot_digest_for(self.source_snapshot)
        if recomputed_snapshot != self.source_snapshot_digest:
            raise ValueError("source_snapshot_digest does not match source_snapshot")

        if self.world_id != self.source_snapshot.world_id:
            raise ValueError("world_id must match source_snapshot.world_id")
        if self.campaign_id != self.source_snapshot.campaign_id:
            raise ValueError("campaign_id must match source_snapshot.campaign_id")

        refs = list(self.phase_artifacts)
        kinds = [ref.artifact_kind for ref in refs]
        if len(kinds) != len(set(kinds)):
            raise ValueError("duplicate phase artifact kind")

        by_kind = {ref.artifact_kind: ref for ref in refs}
        state = self.authority_state
        has_terminal = self.terminal_code is not None or self.terminal_message is not None
        if state != "failed" and has_terminal:
            raise ValueError(f"{state} forbids terminal fields")

        def _require(*artifact_kinds: ArtifactKind) -> None:
            for kind in artifact_kinds:
                if kind not in by_kind:
                    raise ValueError(f"{state} requires {kind} artifact ref")

        def _forbid(*artifact_kinds: ArtifactKind) -> None:
            for kind in artifact_kinds:
                if kind in by_kind:
                    raise ValueError(f"{state} forbids {kind} artifact ref")

        if state == "awaiting_identity_resolution":
            if refs:
                raise ValueError("awaiting_identity_resolution forbids phase artifacts")
        elif state == "identity_resolved":
            _require("identity_resolution")
            _forbid("prepared_graph_plan", "graph_commit_receipt", "publication_verification")
        elif state == "prepared":
            _require("identity_resolution", "prepared_graph_plan")
            _forbid("graph_commit_receipt", "publication_verification")
        elif state == "confirming":
            _require("identity_resolution", "prepared_graph_plan")
            _forbid("publication_verification")
        elif state == "committed_unverified":
            _require("identity_resolution", "prepared_graph_plan", "graph_commit_receipt")
            _forbid("publication_verification")
        elif state == "verified":
            _require(
                "identity_resolution",
                "prepared_graph_plan",
                "graph_commit_receipt",
                "publication_verification",
            )
        elif state == "cancelled":
            if "graph_commit_receipt" in by_kind:
                raise ValueError("cancelled forbids graph_commit_receipt artifact")
        elif state in {"stale", "failed"}:
            pass

        return self


class BeginThreatStatblockPublicationRequestV1(StrictModel):
    schema_name: Literal["dmb_begin_threat_statblock_publication_request_v1"] = Field(
        default=BEGIN_REQUEST_SCHEMA, alias="schema"
    )
    operation_id: str
    expected_draft_version: int = Field(ge=1)
    expected_parent_revision_id: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_publication_operation_id(value)

    @field_validator("expected_parent_revision_id")
    @classmethod
    def _expected_parent(cls, value: str) -> str:
        return _require_graph_revision_id(value)


class ReconcileThreatStatblockPublicationRequestV1(StrictModel):
    expected_operation_version: int = Field(ge=1)

    model_config = ConfigDict(extra="forbid")


class CancelThreatStatblockPublicationRequestV1(StrictModel):
    expected_operation_version: int = Field(ge=1)

    model_config = ConfigDict(extra="forbid")


class ThreatStatblockPublicationOperationResponseV1(StrictModel):
    schema_name: Literal["dmb_threat_statblock_publication_operation_response_v1"] = Field(
        default=RESPONSE_SCHEMA, alias="schema"
    )
    result_label: PublicationResultLabel
    operation: ThreatStatblockPublicationOperationV1
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ThreatStatblockPublicationDiagnosticV1(StrictModel):
    code: str
    message: str

    model_config = ConfigDict(extra="forbid")


class ThreatStatblockPublicationErrorV1(StrictModel):
    schema_name: Literal["dmb_threat_statblock_publication_error_v1"] = Field(
        default=ERROR_SCHEMA, alias="schema"
    )
    code: str
    message: str
    status_code: int
    diagnostics: list[ThreatStatblockPublicationDiagnosticV1] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
