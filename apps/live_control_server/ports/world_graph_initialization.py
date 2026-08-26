"""Storage-neutral zero-parent World Graph initialization port (CUTOVER D.2C2).

Existing-parent publication stays on ``WorldGraphAuthority.publish``. This port
is a sibling for pristine first-world initialization. Product services consume
domain values and receipts; they must not receive PostgreSQL connections, DSNs,
repository bundles, or DungeonMind infrastructure records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

WorldGraphInitializationFailureCode = Literal[
    "authority_unavailable",
    "integrity_failure",
    "already_initialized",
    "idempotency_conflict",
    "inexpressible",
    "initialization_failed",
]
WorldGraphInitializationProbeState = Literal[
    "uninitialized",
    "initialized",
    "unreadable",
]
WorldGraphInitializationOutcome = Literal["initialized", "already_initialized"]


class WorldGraphInitializationError(RuntimeError):
    """Typed failure from initialization authority. Never a raw infrastructure exception."""

    def __init__(
        self,
        message: str,
        *,
        code: WorldGraphInitializationFailureCode,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(message)


@dataclass(frozen=True)
class WorldGraphInitializationState:
    """Advisory probe result. DungeonMind's initialize transaction remains pristine authority."""

    world_id: str
    state: WorldGraphInitializationProbeState
    initialization_id: str | None = None
    published_revision_id: str | None = None


@dataclass(frozen=True)
class WorldGraphInitializationRequest:
    """Product-facing first-world initialize request. No graph payload or DSN."""

    world_id: str
    campaign_id: str
    initialization_id: str
    source_plan_schema: str
    source_plan_id: str
    source_plan_sha256: str
    actor: str
    source_artifact: Any
    source_revision_token: str
    source_uri: str
    reviewed_contribution: Any
    run_id: str | None = None
    workspace_document_id: str | None = None
    workspace_document_revision: str | None = None
    decision_digest: str | None = None


@dataclass(frozen=True)
class WorldGraphInitializationReceipt:
    """Storage-neutral first-world initialize receipt."""

    world_id: str
    initialization_id: str
    published_revision_id: str
    reviewed_contribution_id: str
    reviewed_contribution_sha256: str
    accepted_assertion_ids: tuple[str, ...]
    outcome: WorldGraphInitializationOutcome
    command_sha256: str | None = None
    baseline_revision_id: str | None = None
    initialized_at: datetime | None = None


class WorldGraphInitializationAuthority(Protocol):
    """Capability boundary around zero-parent World Graph initialization."""

    def probe(self, world_id: str) -> WorldGraphInitializationState:
        """Advisory initialization state. Missing Buddy files are not uninitialized."""

    def initialize(
        self,
        request: WorldGraphInitializationRequest,
    ) -> WorldGraphInitializationReceipt:
        """Create or exactly replay one genesis revision for a pristine world."""
