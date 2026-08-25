"""Storage-neutral World Graph authority port (CUTOVER D.2A).

Product services consume domain values and receipts. Production implements
this port with DungeonMind; buddy_files tests/tools may use a named file
adapter. Callers must not receive PostgreSQL connections, DSNs, repository
bundles, or DungeonMind infrastructure records.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from graph_memory.world_graph_mutation_context import WorldGraphMutationContext

WorldGraphAuthorityFailureCode = Literal[
    "authority_unavailable",
    "revision_unavailable",
    "integrity_failure",
    "stale_parent",
    "inexpressible",
    "publication_failed",
]
WorldGraphOperationNamespace = Literal["threat", "worldbuilding"]


class WorldGraphAuthorityError(RuntimeError):
    """Typed failure from World Graph authority. Never a raw infrastructure exception."""

    def __init__(
        self,
        message: str,
        *,
        code: WorldGraphAuthorityFailureCode,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(message)


@dataclass(frozen=True)
class WorldGraphHead:
    world_id: str
    revision_id: str


@dataclass(frozen=True)
class AuthorityObject:
    """One exact-revision object fact consumed by Threat preflight/verification."""

    object_id: str
    label: str
    kind: str
    role: str = ""
    aliases: tuple[str, ...] = ()
    source_domains: tuple[str, ...] = ()
    campaign_scope: str | None = None
    summary: str | None = None
    external_resource: Mapping[str, Any] | None = None
    property_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuthorityRelationship:
    """One exact-revision relationship fact consumed by Threat preflight/verification."""

    relationship_id: str
    subject_object_id: str
    target_object_id: str
    predicate: str
    direction: str = "outbound"
    source_domains: tuple[str, ...] = ()
    threat_statblock_binding: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class WorldGraphRevisionView:
    world_id: str
    revision_id: str
    parent_revision_id: str | None
    objects: Mapping[str, AuthorityObject]
    relationships: Mapping[str, AuthorityRelationship]
    supported_assertion_ids: frozenset[str] = field(default_factory=frozenset)
    contribution_source_digests: Mapping[str, str] = field(default_factory=dict)
    active_contribution_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class WorldGraphPublishRequest:
    world_id: str
    expected_parent_revision_id: str
    authority_operation_id: str
    actor: str
    contribution: Any
    review_package: Mapping[str, Any] | None = None
    accepted_assertion_ids: tuple[str, ...] = ()
    decision: str | None = None
    threat_node_id: str | None = None
    operation_namespace: WorldGraphOperationNamespace = "threat"


@dataclass(frozen=True)
class WorldGraphPublicationReceipt:
    world_id: str
    authority_operation_id: str
    parent_revision_id: str
    published_revision_id: str
    reviewed_contribution_id: str
    accepted_assertion_ids: tuple[str, ...]
    published: bool
    outcome: Literal["published", "already_applied"]
    reviewed_contribution_sha256: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    diagnostics: tuple[str, ...] = ()
    contribution_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorldGraphExpectedChildFacts:
    """Product facts the authority must prove on a published child."""

    threat_node_id: str
    decision: str
    external_resource_node_id: str | None = None
    binding_edge_id: str | None = None
    accepted_assertion_ids: tuple[str, ...] = ()
    expected_contribution_id: str | None = None
    expected_contribution_source_payload_sha256: str | None = None
    campaign_id: str | None = None
    contribution: Any = None
    expected_object_kind: str | None = "threat"


@dataclass(frozen=True)
class WorldGraphVerificationResult:
    status: Literal["passed", "degraded", "failed"]
    codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class WorldGraphAuthority(Protocol):
    """Capability boundary around DungeonMind World Graph authority."""

    def current_head(self, world_id: str) -> WorldGraphHead:
        """Public authority head identity for one world."""

    def read_revision(self, world_id: str, revision_id: str) -> WorldGraphRevisionView:
        """Immutable storage-neutral revision view for preflight and verification."""

    def mutation_context(
        self,
        world_id: str,
        revision_id: str,
        *,
        sealed_identity_snapshot: Mapping[str, Any] | None = None,
    ) -> WorldGraphMutationContext:
        """Exact parent graph facts plus identity semantics for prepare/confirm.

        Prepare (no sealed snapshot): adapt the immutable revision plus the
        current identity ledger. Confirm (sealed snapshot supplied): reconstruct
        identity from that snapshot and do not substitute today's live ledger.
        """

    def publish(self, request: WorldGraphPublishRequest) -> WorldGraphPublicationReceipt:
        """Publish one exact governed contribution against one expected public parent."""

    def recover(
        self,
        world_id: str,
        authority_operation_id: str,
        *,
        expected_parent_revision_id: str | None = None,
        contribution: Any | None = None,
        actor: str | None = None,
        operation_namespace: WorldGraphOperationNamespace = "threat",
    ) -> WorldGraphPublicationReceipt | None:
        """Recover one terminal publication by durable authority operation id.

        None means no terminal publication is proven. Contradictory authority
        state must raise ``WorldGraphAuthorityError(code="integrity_failure")``.
        When expected parent and/or contribution are supplied, the recovered
        publication must match those bindings or fail closed as integrity.
        ``operation_namespace`` selects the product family's review-operation
        mapping. Threat must keep D.2A's historical derivation.
        """

    def verify_child(
        self,
        *,
        receipt: WorldGraphPublicationReceipt,
        expected: WorldGraphExpectedChildFacts,
    ) -> WorldGraphVerificationResult:
        """Prove the published child against native or file-backed authority facts."""


def occupancy_contains(view: WorldGraphRevisionView, object_id: str) -> bool:
    return object_id in view.objects


def relationships_by_predicate(
    view: WorldGraphRevisionView,
    *,
    subject_object_id: str,
    predicate: str,
    target_object_id: str | None = None,
) -> list[AuthorityRelationship]:
    matches: list[AuthorityRelationship] = []
    for rel in view.relationships.values():
        if rel.subject_object_id != subject_object_id:
            continue
        if rel.predicate != predicate and rel.predicate.rsplit(":", 1)[-1] != predicate:
            continue
        if target_object_id is not None and rel.target_object_id != target_object_id:
            continue
        matches.append(rel)
    return matches


__all__ = [
    "AuthorityObject",
    "AuthorityRelationship",
    "WorldGraphAuthority",
    "WorldGraphAuthorityError",
    "WorldGraphAuthorityFailureCode",
    "WorldGraphExpectedChildFacts",
    "WorldGraphHead",
    "WorldGraphMutationContext",
    "WorldGraphOperationNamespace",
    "WorldGraphPublicationReceipt",
    "WorldGraphPublishRequest",
    "WorldGraphRevisionView",
    "WorldGraphVerificationResult",
    "occupancy_contains",
    "relationships_by_predicate",
]
