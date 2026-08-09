"""Effective relationship conformance for Eldyrwild descendants.

Composes:
  base world-object-v4 classification
  + adjudication continuity
  + three PR #29 exact edge interpretations where continuity survives
  + three PR #530 explicit adapters where continuity survives

Historical analyzers remain historical. This module answers which adjudicated
semantics remain valid on an explicitly requested revision.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_world_object_v4_vocabulary,
    vocabulary_sha256,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
    RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1,
    RelationshipAdjudicationContinuityReportV1,
    analyze_relationship_adjudication_continuity_v1,
    continuity_active_edge_ids_v1,
    continuity_invalidated_edge_ids_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_explicit_adapters_v1 import (
    RelationshipExplicitAdapterCatalogV1,
    RelationshipExplicitAdapterIntegrityError,
    ResolvedRelationshipExplicitAdapterV1,
    _assert_shape_matches_catalog,
    _dm_kind_for_buddy_kind,
    _node_buddy_kind,
    load_eldyrwild_relationship_explicit_adapter_catalog_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_RESIDUAL_FINDINGS,
    ResidualDisposition,
    ResponsibleRepo,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _load_exact_buddy_revision,
    _predicate_allowed_endpoints,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    WholeWorldConformanceReportV4,
    _DUNGEONMIND_DEPENDENCY_REF_V4,
    analyze_exact_buddy_world_revision_v4,
)
from graph_memory.union_supergraph.model import (
    UnionSupergraphEdge,
    UnionSupergraphStore,
)

RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1 = (
    "dmb_dungeonmind_relationship_effective_conformance_v1"
)

# Exact PR #29 published interpretations (never global by Buddy predicate).
_PR29_EDGE_INTERPRETATIONS_V1: dict[str, str] = {
    "edge:node:fey_entity:present_at:pc:ephanna:appears-to-ephanna-in-prison": (
        "dnd5e:appears_to"
    ),
    "edge:pc:bonogo:defends_weakened_location:node:prisoners_session9:protects": (
        "dnd5e:protects"
    ),
    "edge:pc:caelynn:controls_comms_with:npc_grobnok": "dnd5e:communicates_with",
}

_ACTIVE_CONTINUITY = frozenset({"ANCHOR", "CARRIED_FORWARD"})

_FORBIDDEN_REMAINING_DISPOSITIONS = frozenset(
    {
        ResidualDisposition.EXPLICIT_ADAPTER_CANDIDATE.value,
        ResidualDisposition.NEW_PREDICATE_CANDIDATE.value,
        ResidualDisposition.EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE.value,
    }
)


class InventoryCountRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    count: int


class InvalidatedAdjudicationObservationV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    continuity_state: str
    original_disposition: str
    diagnostic: str | None = None
    diagnostic_detail: str | None = None
    note: str = (
        "this edge had prior adjudication but that adjudication no longer applies"
    )


class RelationshipEffectiveConformanceReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1
    world_id: str
    campaign_id: str
    source_revision_id: str
    source_graph_payload_sha256: str
    dungeonmind_dependency_ref: str
    world_object_vocabulary_revision: str
    world_object_vocabulary_sha256: str
    continuity_report_schema: str
    relationship_semantic_count: int
    relationship_effectively_represented_count: int
    relationship_effective_residual_count: int
    uses_statblock_mechanics_count: int
    base_relationship_represented_count: int
    base_relationship_residual_count: int
    pr29_interpretation_applied_count: int
    explicit_adapter_applied_count: int
    active_adjudicated_edge_ids: list[str] = Field(default_factory=list)
    invalidated_adjudication_edge_ids: list[str] = Field(default_factory=list)
    invalidated_adjudication_observations: list[InvalidatedAdjudicationObservationV1] = (
        Field(default_factory=list)
    )
    newly_represented_by_continuity_edge_ids: list[str] = Field(default_factory=list)
    remaining_residual_edge_ids: list[str] = Field(default_factory=list)
    remaining_residual_by_predicate: list[InventoryCountRow] = Field(default_factory=list)
    remaining_residual_disposition_inventory: list[InventoryCountRow] = Field(
        default_factory=list
    )
    dungeonmind_owned_remaining_count: int
    dungeonmindbuddy_owned_remaining_count: int
    unadjudicated_remaining_count: int
    requires_readjudication_count: int
    world_graph_digest_before: str | None = None
    world_graph_digest_after: str | None = None


class RelationshipEffectiveConformanceError(RuntimeError):
    """Raised when effective conformance invariants fail closed."""


def _counter_rows(counter: Counter[str]) -> list[InventoryCountRow]:
    return [
        InventoryCountRow(key=key, count=count) for key, count in sorted(counter.items())
    ]


def _continuity_by_edge(
    continuity: RelationshipAdjudicationContinuityReportV1,
) -> dict[str, Any]:
    return {row.edge_id: row for row in continuity.rows}


def resolve_carried_relationship_explicit_adapter_v1(
    *,
    world_id: str,
    revision_id: str,
    graph_payload_sha256: str,
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
    continuity_state: Literal[
        "ANCHOR",
        "CARRIED_FORWARD",
        "INVALIDATED_BY_EDGE_CHANGE",
        "INVALIDATED_BY_SOURCE_CHANGE",
        "EDGE_REMOVED",
        "NOT_DESCENDANT",
        "REQUIRES_READJUDICATION",
    ],
) -> ResolvedRelationshipExplicitAdapterV1 | None:
    """Resolve a PR #530 adapter only when adjudication continuity still applies.

    Always uses the immutable built-in catalog and world-object-v4. Does not
    accept caller-supplied catalogs or vocabularies.
    """
    del world_id, revision_id, graph_payload_sha256  # continuity_state is authority
    if continuity_state not in _ACTIVE_CONTINUITY:
        return None
    catalog = load_eldyrwild_relationship_explicit_adapter_catalog_v1()
    return _resolve_carried_adapter_with_catalog(
        edge=edge,
        store=store,
        catalog=catalog,
        continuity_state=continuity_state,
    )


def _resolve_carried_adapter_with_catalog(
    *,
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
    catalog: RelationshipExplicitAdapterCatalogV1,
    continuity_state: str,
) -> ResolvedRelationshipExplicitAdapterV1 | None:
    if continuity_state not in _ACTIVE_CONTINUITY:
        return None
    record = next((r for r in catalog.records if r.edge_id == edge.edge_id), None)
    if record is None:
        return None
    vocabulary = load_builtin_world_object_v4_vocabulary()
    _assert_shape_matches_catalog(record, edge=edge, store=store)
    if record.reverse_endpoints:
        subject_id = edge.target_node_id
        object_id = edge.source_node_id
        subject_kind = _node_buddy_kind(store, subject_id)
        object_kind = _node_buddy_kind(store, object_id)
    else:
        subject_id = edge.source_node_id
        object_id = edge.target_node_id
        subject_kind = _node_buddy_kind(store, subject_id)
        object_kind = _node_buddy_kind(store, object_id)
    subject_dm = _dm_kind_for_buddy_kind(subject_kind or "")
    object_dm = _dm_kind_for_buddy_kind(object_kind or "")
    if subject_dm is None or object_dm is None:
        raise RelationshipExplicitAdapterIntegrityError(
            f"carried adapter {edge.edge_id}: unmapped endpoint kinds"
        )
    allowed = _predicate_allowed_endpoints(record.dungeonmind_term, vocabulary)
    if allowed is None:
        raise RelationshipExplicitAdapterIntegrityError(
            f"world-object-v4 missing predicate {record.dungeonmind_term!r}"
        )
    subject_kinds, object_kinds = allowed
    if subject_dm not in subject_kinds or object_dm not in object_kinds:
        raise RelationshipExplicitAdapterIntegrityError(
            f"carried adapter {edge.edge_id}: endpoints not admitted by v4"
        )
    return ResolvedRelationshipExplicitAdapterV1(
        edge_id=edge.edge_id,
        dungeonmind_term=record.dungeonmind_term,
        reverse_endpoints=record.reverse_endpoints,
        effective_subject_node_id=subject_id,
        effective_object_node_id=object_id,
        effective_subject_dm_kind=subject_dm,
        effective_object_dm_kind=object_dm,
        expected_buddy_predicate=record.expected_buddy_predicate,
        adjudication_reason_code=record.adjudication_reason_code,
    )


def _admit_pr29_interpretation(
    *,
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
    term: str,
    vocabulary: Any,
) -> bool:
    source_kind = _node_buddy_kind(store, edge.source_node_id)
    target_kind = _node_buddy_kind(store, edge.target_node_id)
    source_dm = _dm_kind_for_buddy_kind(source_kind or "")
    target_dm = _dm_kind_for_buddy_kind(target_kind or "")
    if source_dm is None or target_dm is None:
        return False
    allowed = _predicate_allowed_endpoints(term, vocabulary)
    if allowed is None:
        return False
    subject_kinds, object_kinds = allowed
    return source_dm in subject_kinds and target_dm in object_kinds


def _ownership_for_remaining(
    remaining_edge_ids: list[str],
    *,
    continuity: RelationshipAdjudicationContinuityReportV1,
) -> tuple[list[InventoryCountRow], int, int, int, int]:
    by_edge = _continuity_by_edge(continuity)
    disposition_counter: Counter[str] = Counter()
    dm_owned = 0
    buddy_owned = 0
    unadjudicated = 0
    requires_readjudication = 0

    for edge_id in remaining_edge_ids:
        row = by_edge.get(edge_id)
        if row is None:
            finding = ELDYRWILD_RESIDUAL_FINDINGS.get(edge_id)
            if finding is None:
                unadjudicated += 1
                disposition_counter["UNADJUDICATED"] += 1
                continue
            # Residual that was never an original adjudication finding.
            unadjudicated += 1
            disposition_counter["UNADJUDICATED"] += 1
            continue

        if row.continuity_state == "REQUIRES_READJUDICATION":
            requires_readjudication += 1
            disposition_counter["REQUIRES_READJUDICATION"] += 1
            continue
        if row.continuity_state not in _ACTIVE_CONTINUITY:
            # Invalidated prior adjudication: still observable, not silently generic.
            requires_readjudication += 1
            disposition_counter["REQUIRES_READJUDICATION"] += 1
            continue

        finding = ELDYRWILD_RESIDUAL_FINDINGS.get(edge_id)
        if finding is None:
            unadjudicated += 1
            disposition_counter["UNADJUDICATED"] += 1
            continue
        disposition_counter[finding.disposition.value] += 1
        if finding.responsible_repo == ResponsibleRepo.DUNGEONMIND:
            dm_owned += 1
        elif finding.responsible_repo == ResponsibleRepo.DUNGEONMINDBUDDY:
            buddy_owned += 1
        else:
            unadjudicated += 1

    return (
        _counter_rows(disposition_counter),
        dm_owned,
        buddy_owned,
        unadjudicated,
        requires_readjudication,
    )


def _analyze_relationship_effective_conformance_with_authorities(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    base_report: WholeWorldConformanceReportV4,
    continuity: RelationshipAdjudicationContinuityReportV1,
    catalog: RelationshipExplicitAdapterCatalogV1,
    store: UnionSupergraphStore | None = None,
    world_graph_digest_before: str | None = None,
    world_graph_digest_after: str | None = None,
) -> RelationshipEffectiveConformanceReportV1:
    """Private effective-conformance path with injectable authorities (tests only)."""
    vocabulary = load_builtin_world_object_v4_vocabulary()
    active_ids = set(continuity_active_edge_ids_v1(continuity))
    invalidated_ids = continuity_invalidated_edge_ids_v1(continuity)
    by_edge = _continuity_by_edge(continuity)

    live_store = store
    if live_store is None:
        _, live_store = _load_exact_buddy_revision(
            root=root,
            world_id=world_id,
            revision_id=revision_id,
        )

    base_residual = list(base_report.relationship_residual_edge_ids)
    base_residual_set = set(base_residual)
    newly: list[str] = []
    pr29_applied = 0
    adapter_applied = 0

    # PR #29 exact interpretations where continuity survives and base still residual.
    for edge_id, term in sorted(_PR29_EDGE_INTERPRETATIONS_V1.items()):
        if edge_id not in active_ids:
            continue
        if edge_id not in base_residual_set:
            # Already represented by historical v4 exact-domain override on anchor.
            continue
        edge = live_store.edges.get(edge_id)
        if edge is None:
            continue
        if not _admit_pr29_interpretation(
            edge=edge, store=live_store, term=term, vocabulary=vocabulary
        ):
            continue
        newly.append(edge_id)
        pr29_applied += 1

    newly_set = set(newly)

    # PR #530 explicit adapters where continuity survives.
    for record in catalog.records:
        edge_id = record.edge_id
        if edge_id in newly_set:
            continue
        if edge_id not in base_residual_set:
            continue
        row = by_edge.get(edge_id)
        if row is None or row.continuity_state not in _ACTIVE_CONTINUITY:
            continue
        edge = live_store.edges.get(edge_id)
        if edge is None:
            continue
        try:
            resolved = _resolve_carried_adapter_with_catalog(
                edge=edge,
                store=live_store,
                catalog=catalog,
                continuity_state=row.continuity_state,
            )
        except RelationshipExplicitAdapterIntegrityError:
            continue
        if resolved is None:
            continue
        newly.append(edge_id)
        newly_set.add(edge_id)
        adapter_applied += 1

    remaining = sorted(edge_id for edge_id in base_residual if edge_id not in newly_set)
    predicate_counter: Counter[str] = Counter()
    for edge_id in remaining:
        edge = live_store.edges.get(edge_id)
        if edge is None:
            raise RelationshipEffectiveConformanceError(
                f"remaining residual edge missing from store: {edge_id}"
            )
        predicate_counter[edge.predicate] += 1

    (
        disposition_inventory,
        dm_owned,
        buddy_owned,
        unadjudicated,
        requires_from_remaining,
    ) = _ownership_for_remaining(remaining, continuity=continuity)

    requires_readjudication = max(
        continuity.requires_readjudication_count,
        requires_from_remaining,
    )

    # On the exact Eldyrwild active continuity set, remaining must not include
    # closed successor dispositions that were already resolved.
    if (
        continuity.anchor_is_ancestor
        and continuity.world_id == base_report.source_world_id
        and all(row.continuity_state in _ACTIVE_CONTINUITY for row in continuity.rows)
    ):
        forbidden = {
            row.key
            for row in disposition_inventory
            if row.key in _FORBIDDEN_REMAINING_DISPOSITIONS
        }
        if forbidden:
            raise RelationshipEffectiveConformanceError(
                "remaining residual ledger still contains closed dispositions: "
                f"{sorted(forbidden)}"
            )

    effective_represented = base_report.relationship_represented_count + len(newly)
    effective_residual = len(remaining)
    if (
        effective_represented + effective_residual
        != base_report.relationship_semantic_count
    ):
        raise RelationshipEffectiveConformanceError(
            "effective represented + residual must equal semantic count: "
            f"{effective_represented}+{effective_residual}!="
            f"{base_report.relationship_semantic_count}"
        )

    observations = [
        InvalidatedAdjudicationObservationV1(
            edge_id=row.edge_id,
            continuity_state=row.continuity_state,
            original_disposition=row.original_disposition,
            diagnostic=row.diagnostic,
            diagnostic_detail=row.diagnostic_detail,
        )
        for row in continuity.rows
        if row.edge_id in set(invalidated_ids)
    ]

    return RelationshipEffectiveConformanceReportV1(
        schema_version=RELATIONSHIP_EFFECTIVE_CONFORMANCE_SCHEMA_V1,
        world_id=base_report.source_world_id,
        campaign_id=base_report.source_campaign_id,
        source_revision_id=base_report.source_revision_id,
        source_graph_payload_sha256=base_report.source_graph_payload_sha256,
        dungeonmind_dependency_ref=_DUNGEONMIND_DEPENDENCY_REF_V4,
        world_object_vocabulary_revision=vocabulary.vocabulary_revision,
        world_object_vocabulary_sha256=vocabulary_sha256(vocabulary),
        continuity_report_schema=RELATIONSHIP_ADJUDICATION_CONTINUITY_SCHEMA_V1,
        relationship_semantic_count=base_report.relationship_semantic_count,
        relationship_effectively_represented_count=effective_represented,
        relationship_effective_residual_count=effective_residual,
        uses_statblock_mechanics_count=base_report.uses_statblock_mechanics_count,
        base_relationship_represented_count=base_report.relationship_represented_count,
        base_relationship_residual_count=base_report.relationship_residual_count,
        pr29_interpretation_applied_count=pr29_applied,
        explicit_adapter_applied_count=adapter_applied,
        active_adjudicated_edge_ids=sorted(active_ids),
        invalidated_adjudication_edge_ids=invalidated_ids,
        invalidated_adjudication_observations=observations,
        newly_represented_by_continuity_edge_ids=sorted(newly),
        remaining_residual_edge_ids=remaining,
        remaining_residual_by_predicate=_counter_rows(predicate_counter),
        remaining_residual_disposition_inventory=disposition_inventory,
        dungeonmind_owned_remaining_count=dm_owned,
        dungeonmindbuddy_owned_remaining_count=buddy_owned,
        unadjudicated_remaining_count=unadjudicated,
        requires_readjudication_count=requires_readjudication,
        world_graph_digest_before=world_graph_digest_before,
        world_graph_digest_after=world_graph_digest_after,
    )


def analyze_relationship_effective_conformance_v1(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    world_graph_digest_before: str | None = None,
    world_graph_digest_after: str | None = None,
) -> RelationshipEffectiveConformanceReportV1:
    """Compose v4 + continuity + carried PR #29/#530 interpretations.

    Always binds built-in adjudication/source-seal/adapter authorities. Does not
    accept caller-supplied catalogs, seals, base reports, or vocabularies.
    """
    base_report = analyze_exact_buddy_world_revision_v4(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    continuity = analyze_relationship_adjudication_continuity_v1(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    return _analyze_relationship_effective_conformance_with_authorities(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
        base_report=base_report,
        continuity=continuity,
        catalog=load_eldyrwild_relationship_explicit_adapter_catalog_v1(),
        world_graph_digest_before=world_graph_digest_before,
        world_graph_digest_after=world_graph_digest_after,
    )


def compact_relationship_effective_conformance_report_v1(
    report: RelationshipEffectiveConformanceReportV1,
) -> dict[str, Any]:
    return report.model_dump(mode="json")
