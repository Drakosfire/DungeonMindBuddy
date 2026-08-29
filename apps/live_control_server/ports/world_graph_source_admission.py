"""Storage-neutral World Graph source-admission port (CUTOVER D.2C4).

Product services consume Buddy source identity and admitted DungeonMind IDs.
Production implements this port with DungeonMind SourceRepository put/get/snapshot.
Callers must not receive PostgreSQL connections, DSNs, repository bundles, or
DungeonMind infrastructure records.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

WorldGraphSourceAdmissionFailureCode = Literal[
    "authority_unavailable",
    "source_not_admitted",
    "source_identity_conflict",
    "source_identity_missing",
    "inexpressible",
]


class WorldGraphSourceAdmissionError(RuntimeError):
    """Typed failure from source-admission authority. Never a raw infrastructure exception."""

    def __init__(
        self,
        message: str,
        *,
        code: WorldGraphSourceAdmissionFailureCode,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(message)


@dataclass(frozen=True)
class WorldGraphSourceAdmissionRequest:
    """Buddy source identity to map and prove/admit before a confirmable prepare."""

    world_id: str
    campaign_id: str
    source_artifact: Any
    source_revision_token: str
    source_uri: str | None = None


@dataclass(frozen=True)
class AdmittedSourceIdentity:
    """Sealed DungeonMind source pair after catalog-aware derive + admit."""

    source_artifact_id: str
    source_revision_id: str
    content_sha256: str
    buddy_source_revision_id: str


class WorldGraphSourceAdmissionAuthority(Protocol):
    """Capability boundary around DungeonMind SourceRepository admission."""

    def prove_or_admit(
        self, request: WorldGraphSourceAdmissionRequest
    ) -> AdmittedSourceIdentity:
        """Idempotently admit the mapped SourceArtifactV2 + SourceRevision pair."""

    def prove(
        self,
        *,
        world_id: str,
        source_artifact_id: str,
        source_revision_id: str,
        source_revision_token: str | None = None,
    ) -> AdmittedSourceIdentity:
        """Re-prove a sealed pair via provenance snapshot. Confirm must not first-admit."""
