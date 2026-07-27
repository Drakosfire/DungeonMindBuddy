"""SBW07b: acceptance operation models and API contracts (§12)."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    CreateStatblockRequestV1,
    StatblockDefinitionV1Input,
    ValidationReceiptV1,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
    PROVIDER_DUNGEONMIND,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ContractNameV1,
    ContractVersionV1,
)

ACCEPTANCE_OPERATION_SCHEMA = "dmb_statblock_acceptance_operation_v1"
_OPERATION_ID_ACCOP_RE = re.compile(r"^accop_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def create_request_digest_for_body(body: dict[str, Any]) -> str:
    """Buddy-local canonical SHA-256 digest over a create-request JSON body."""
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


AuthorityState = Literal[
    "dispatched_unknown",
    "server_committed",
    "reconciled",
    "terminal_failure",
]
DraftRefState = Literal["missing", "attached", "failed", "conflicted"]
AcceptanceResultLabel = Literal[
    "acceptance_blocked",
    "acceptance_busy",
    "acceptance_history_full",
    "acceptance_input_conflict",
    "acceptance_draft_unavailable",
    "dispatched_unknown",
    "server_committed_reference_pending",
    "mechanics_saved",
    "accepted_ref_conflict",
    "terminal_failure",
]


def validate_operation_id(value: str) -> str:
    cleaned = value.strip()
    try:
        return str(UUID(cleaned))
    except ValueError:
        if _OPERATION_ID_ACCOP_RE.fullmatch(cleaned):
            return cleaned
        raise ValueError("invalid operation_id")


def idempotency_key_for_operation(operation_id: str) -> str:
    """Deterministic Server idempotency key bound to the Buddy operation."""
    return validate_operation_id(operation_id)


class AcceptedMechanicsRefV1(StrictModel):
    """ThreatDraft materialization: six-field identity + provenance."""

    provider: Literal["dungeonmind"] = PROVIDER_DUNGEONMIND
    statblock_id: str = Field(pattern=r"^sb_[a-z0-9]+$")
    revision_id: str = Field(pattern=r"^rev_[a-z0-9]+$")
    contract: ContractNameV1
    contract_version: ContractVersionV1
    definition_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    accepted_from_candidate_id: str | None = Field(
        default=None, pattern=r"^cand_[a-z0-9]+$"
    )
    accepted_from_draft_version: int = Field(ge=1)
    accepted_at: str = Field(min_length=1, max_length=64)

    @classmethod
    def from_locator(
        cls,
        locator: MechanicsLocatorV1,
        *,
        accepted_from_draft_version: int,
        accepted_at: str,
        accepted_from_candidate_id: str | None = None,
    ) -> AcceptedMechanicsRefV1:
        return cls(
            provider=locator.provider,
            statblock_id=locator.statblock_id,
            revision_id=locator.revision_id,
            contract=locator.contract,
            contract_version=locator.contract_version,
            definition_digest=locator.definition_digest,
            accepted_from_candidate_id=accepted_from_candidate_id,
            accepted_from_draft_version=accepted_from_draft_version,
            accepted_at=accepted_at,
        )

    def to_mechanics_locator(self) -> MechanicsLocatorV1:
        return MechanicsLocatorV1(
            provider=self.provider,
            statblock_id=self.statblock_id,
            revision_id=self.revision_id,
            contract=self.contract,
            contract_version=self.contract_version,
            definition_digest=self.definition_digest,
        )


class AcceptanceMaterializationV1(StrictModel):
    draft_ref: DraftRefState = "missing"


class AcceptanceOperationV1(StrictModel):
    schema_name: Literal["dmb_statblock_acceptance_operation_v1"] = Field(
        default=ACCEPTANCE_OPERATION_SCHEMA, alias="schema"
    )
    operation_id: str
    idempotency_key: str = Field(min_length=1)
    create_request_digest: str = Field(min_length=1)
    request_body: dict[str, Any]
    source_draft_id: str
    source_draft_version: int = Field(ge=1)
    source_candidate_id: str | None = Field(default=None, pattern=r"^cand_[a-z0-9]+$")
    validation_receipt_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority_state: AuthorityState
    locator: MechanicsLocatorV1 | None = None
    materialization: AcceptanceMaterializationV1 = Field(
        default_factory=AcceptanceMaterializationV1
    )
    terminal_code: str | None = None
    failure_category: str | None = None
    http_status: int | None = None
    terminal_details: dict[str, Any] | None = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_operation_id(value)

    @model_validator(mode="after")
    def _authority_invariants(self) -> AcceptanceOperationV1:
        # Replay authority: typed create body + digest + idempotency/provenance bind.
        try:
            typed_body = CreateStatblockRequestV1.model_validate(self.request_body)
        except Exception as exc:
            raise ValueError(
                "request_body must validate as CreateStatblockRequestV1"
            ) from exc

        recomputed = create_request_digest_for_body(self.request_body)
        if recomputed != self.create_request_digest:
            raise ValueError("create_request_digest does not match request_body")

        expected_key = idempotency_key_for_operation(self.operation_id)
        if self.idempotency_key != expected_key:
            raise ValueError("idempotency_key must equal operation_id key")
        if typed_body.idempotency_key != self.idempotency_key:
            raise ValueError("request_body.idempotency_key must equal record key")

        # CandidateId is a pydantic RootModel — str(value) yields "root='cand_…'",
        # not the bare id. Compare the root string (or plain str) instead.
        raw_candidate = typed_body.candidate_id
        if raw_candidate is None:
            body_candidate = None
        else:
            root = getattr(raw_candidate, "root", None)
            body_candidate = root if isinstance(root, str) else str(raw_candidate)
        if body_candidate != self.source_candidate_id:
            raise ValueError(
                "source_candidate_id must match request_body.candidate_id"
            )

        state = self.authority_state
        has_terminal = (
            self.terminal_code is not None
            or self.failure_category is not None
            or self.http_status is not None
            or self.terminal_details is not None
        )
        if state == "dispatched_unknown":
            if self.locator is not None:
                raise ValueError("dispatched_unknown requires locator=null")
            if self.materialization.draft_ref != "missing":
                raise ValueError("dispatched_unknown requires draft_ref=missing")
            if has_terminal:
                raise ValueError("dispatched_unknown forbids terminal fields")
        elif state == "server_committed":
            if self.locator is None:
                raise ValueError("server_committed requires locator")
            if self.materialization.draft_ref not in {
                "missing",
                "failed",
                "conflicted",
            }:
                raise ValueError("server_committed draft_ref must be pending attach")
            if has_terminal:
                raise ValueError("server_committed forbids terminal fields")
        elif state == "reconciled":
            if self.locator is None:
                raise ValueError("reconciled requires locator")
            if self.materialization.draft_ref != "attached":
                raise ValueError("reconciled requires draft_ref=attached")
            if has_terminal:
                raise ValueError("reconciled forbids terminal fields")
        elif state == "terminal_failure":
            if self.locator is not None:
                raise ValueError("terminal_failure requires locator=null")
            if self.materialization.draft_ref != "missing":
                raise ValueError("terminal_failure requires draft_ref=missing")
            if (
                not self.terminal_code
                or not self.failure_category
                or self.http_status is None
            ):
                raise ValueError("terminal_failure requires terminal fields")
            # Reload must still satisfy SBW07a fixture-proven non-begin predicate.
            from apps.live_control_server.integrations.dungeonmind_statblocks.create_terminal_inventory import (
                is_fixture_proven_terminal_non_begin,
            )
            from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
                StatblockIntegrationError,
            )

            evidence = StatblockIntegrationError(
                category=self.failure_category,
                message="stored terminal evidence",
                status_code=self.http_status,
                error_code=self.terminal_code,
                details=dict(self.terminal_details or {}),
            )
            if not is_fixture_proven_terminal_non_begin(evidence):
                raise ValueError(
                    "terminal_failure evidence does not satisfy SBW07a non-begin predicate"
                )
        return self


class AcceptThreatDraftMechanicsRequestV1(StrictModel):
    operation_id: str
    expected_draft_version: int = Field(ge=1)
    definition: StatblockDefinitionV1Input
    validation_receipt: ValidationReceiptV1
    validation_definition_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_candidate_id: str | None = Field(default=None, pattern=r"^cand_[a-z0-9]+$")
    change_summary: str = Field(min_length=1, max_length=2000)
    actor: str | None = Field(default=None, max_length=128)
    accepted_through: dict[str, Any] | None = None

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        return validate_operation_id(value)


class AcceptThreatDraftMechanicsResponseV1(StrictModel):
    schema_name: Literal["dmb_accept_threat_draft_mechanics_response_v1"] = Field(
        default="dmb_accept_threat_draft_mechanics_response_v1",
        alias="schema",
    )
    draft_id: str
    operation_id: str
    result_label: AcceptanceResultLabel
    authority_state: AuthorityState | None = None
    draft_ref: DraftRefState | None = None
    workflow_state: Literal["drafting", "candidate_ready", "mechanics_saved"] | None = (
        None
    )
    locator: MechanicsLocatorV1 | None = None
    terminal_code: str | None = None
    failure_category: str | None = None
    http_status: int | None = None
    message: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ReadAcceptanceOperationResponseV1(StrictModel):
    schema_name: Literal["dmb_read_acceptance_operation_response_v1"] = Field(
        default="dmb_read_acceptance_operation_response_v1",
        alias="schema",
    )
    draft_id: str
    operation: AcceptanceOperationV1 | None = None
    result_label: AcceptanceResultLabel | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
