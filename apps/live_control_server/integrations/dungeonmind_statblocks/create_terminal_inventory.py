"""Fixture-backed create/read terminal-outcome inventory for SBW07b.

SBW07a owns which Server outcomes prove persistence never began. SBW07b must
consume this inventory rather than inferring terminality from HTTP status or
exception type alone.

This module never assigns AcceptanceOperationV1 authority states
(``dispatched_unknown``, ``server_committed``, ``reconciled``, ``terminal_failure``)
or product workflow states (``mechanics_saved``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)

FixtureKind = Literal["server", "synthetic"]
TerminalProof = Literal["yes", "no"]

__all__ = [
    "CreateOutcomeSpec",
    "CREATE_OUTCOME_INVENTORY",
    "TERMINAL_NON_BEGIN_SPECS",
    "NON_TERMINAL_SPECS",
    "is_fixture_proven_terminal_non_begin",
    "is_changed_body_idempotency_conflict",
]


@dataclass(frozen=True, slots=True)
class CreateOutcomeSpec:
    """One create/read adapter outcome with fixture provenance."""

    name: str
    server_error_code: str | None
    http_status: int | None
    fixture: str | None
    fixture_kind: FixtureKind
    buddy_category: str
    terminal_non_begin: TerminalProof
    proof: str


CREATE_OUTCOME_INVENTORY: tuple[CreateOutcomeSpec, ...] = (
    CreateOutcomeSpec(
        name="create_success",
        server_error_code=None,
        http_status=200,
        fixture="create-response.json",
        fixture_kind="server",
        buddy_category="create_success",
        terminal_non_begin="no",
        proof="Successful create returns an exact six-field locator; observed Server commitment, not terminal failure.",
    ),
    CreateOutcomeSpec(
        name="same_key_same_body_replay",
        server_error_code=None,
        http_status=200,
        fixture="create-response.json",
        fixture_kind="server",
        buddy_category="create_replay",
        terminal_non_begin="no",
        proof="Server returns the same logical statblock/revision/digest for same-key same-body replay.",
    ),
    CreateOutcomeSpec(
        name="same_key_changed_body_conflict",
        server_error_code="idempotency_conflict",
        http_status=409,
        fixture="create-idempotency-conflict.json",
        fixture_kind="server",
        buddy_category="downstream_conflict",
        terminal_non_begin="no",
        proof="Changed-body conflict rejects the new attempt only; original same-key operation may already be committed and must remain recoverable.",
    ),
    CreateOutcomeSpec(
        name="persistence_validation_failed",
        server_error_code="validation_failed",
        http_status=422,
        fixture="create-persistence-validation-failed.json",
        fixture_kind="server",
        buddy_category="downstream_validation_failed",
        terminal_non_begin="yes",
        proof=(
            "Server PersistenceValidationError emits validation_failed with "
            "details.is_persistence_ready=false before durable create begins "
            "(DungeonMindServer domain error + HTTP acceptance fixture shape)."
        ),
    ),
    CreateOutcomeSpec(
        name="request_validation_failed",
        server_error_code="invalid_request",
        http_status=422,
        fixture="create-invalid-request.json",
        fixture_kind="server",
        buddy_category="downstream_validation_failed",
        terminal_non_begin="yes",
        proof=(
            "DungeonMindServer v1 RequestValidationError handler returns invalid_request "
            "before the create handler runs; persistence has not begun."
        ),
    ),
    CreateOutcomeSpec(
        name="transport_timeout",
        server_error_code=None,
        http_status=None,
        fixture=None,
        fixture_kind="synthetic",
        buddy_category="downstream_timeout",
        terminal_non_begin="no",
        proof="Timeout does not prove persistence did not begin; retain dispatched_unknown at orchestration.",
    ),
    CreateOutcomeSpec(
        name="transport_unavailable",
        server_error_code=None,
        http_status=None,
        fixture=None,
        fixture_kind="synthetic",
        buddy_category="downstream_unavailable",
        terminal_non_begin="no",
        proof="Connection interruption does not prove non-begin.",
    ),
    CreateOutcomeSpec(
        name="auth_failure_without_non_begin_proof",
        server_error_code=None,
        http_status=401,
        fixture=None,
        fixture_kind="synthetic",
        buddy_category="downstream_authentication_failed",
        terminal_non_begin="no",
        proof="401/403 without a durable non-begin fixture remains auth uncertainty.",
    ),
    CreateOutcomeSpec(
        name="malformed_success_response",
        server_error_code=None,
        http_status=200,
        fixture=None,
        fixture_kind="synthetic",
        buddy_category="downstream_unexpected",
        terminal_non_begin="no",
        proof="Malformed/partial success is response integrity failure; do not invent a locator or declare terminal non-begin.",
    ),
    CreateOutcomeSpec(
        name="exact_read_dependency_failure",
        server_error_code=None,
        http_status=None,
        fixture=None,
        fixture_kind="synthetic",
        buddy_category="downstream_unavailable",
        terminal_non_begin="no",
        proof="Exact-read unavailability retains any already-observed locator at later layers; not terminal.",
    ),
    CreateOutcomeSpec(
        name="unrecognized_server_error",
        server_error_code=None,
        http_status=None,
        fixture=None,
        fixture_kind="synthetic",
        buddy_category="downstream_unexpected",
        terminal_non_begin="no",
        proof="Unrecognized Server errors remain non-terminal until a fixture proves non-begin.",
    ),
)

TERMINAL_NON_BEGIN_SPECS: tuple[CreateOutcomeSpec, ...] = tuple(
    spec for spec in CREATE_OUTCOME_INVENTORY if spec.terminal_non_begin == "yes"
)

NON_TERMINAL_SPECS: tuple[CreateOutcomeSpec, ...] = tuple(
    spec for spec in CREATE_OUTCOME_INVENTORY if spec.terminal_non_begin == "no"
)

_TERMINAL_BY_CODE: dict[tuple[str, int], CreateOutcomeSpec] = {
    (spec.server_error_code, spec.http_status): spec
    for spec in TERMINAL_NON_BEGIN_SPECS
    if spec.server_error_code is not None and spec.http_status is not None
}


def is_changed_body_idempotency_conflict(error: StatblockIntegrationError) -> bool:
    """True only for Server idempotency_conflict (changed-body attempt conflict)."""

    return (
        error.category == "downstream_conflict"
        and error.error_code == "idempotency_conflict"
        and error.status_code == 409
    )


def is_fixture_proven_terminal_non_begin(error: StatblockIntegrationError) -> bool:
    """Conservative terminal candidate check for SBW07b.

    Requires an exact (server_error_code, http_status) match from the inventory.
    HTTP status alone, category alone, or unrecognized codes never return True.
    """

    if error.error_code is None or error.status_code is None:
        return False
    if is_changed_body_idempotency_conflict(error):
        return False
    return (error.error_code, error.status_code) in _TERMINAL_BY_CODE
