"""Post-adapter relationship conformance over whole-world v4 residuals.

Derives an effective relationship ledger by applying the governed Eldyrwild
explicit-adapter catalog to the historical v4 residual set. Does not mutate
``whole_world_conformance_v4`` results or the World Graph.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_world_object_v4_vocabulary,
    vocabulary_sha256,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_explicit_adapters_v1 import (
    RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1,
    RelationshipExplicitAdapterCatalogV1,
    RelationshipExplicitAdapterIntegrityError,
    load_eldyrwild_relationship_explicit_adapter_catalog_v1,
    matches_explicit_adapter_domain_v1,
    _resolve_relationship_explicit_adapter_with_catalog,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_RESIDUAL_FINDINGS,
    ResidualDisposition,
    ResponsibleRepo,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _load_exact_buddy_revision,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    WholeWorldConformanceReportV4,
    _DUNGEONMIND_DEPENDENCY_REF_V4,
    analyze_exact_buddy_world_revision_v4,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore

RELATIONSHIP_EXPLICIT_ADAPTER_CONFORMANCE_SCHEMA_V1 = (
    "dmb_dungeonmind_relationship_explicit_adapter_conformance_v1"
)

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


class RelationshipExplicitAdapterConformanceReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = RELATIONSHIP_EXPLICIT_ADAPTER_CONFORMANCE_SCHEMA_V1
    world_id: str
    campaign_id: str
    source_revision_id: str
    source_graph_payload_sha256: str
    dungeonmind_dependency_ref: str
    world_object_vocabulary_revision: str
    world_object_vocabulary_sha256: str
    adapter_catalog_schema: str
    base_relationship_semantic_count: int
    base_relationship_represented_count: int
    base_relationship_residual_count: int
    uses_statblock_mechanics_count: int
    adapter_candidate_count: int
    adapter_applied_count: int
    adapter_failed_count: int
    newly_represented_edge_ids: list[str] = Field(default_factory=list)
    remaining_residual_edge_ids: list[str] = Field(default_factory=list)
    effective_relationship_represented_count: int
    effective_relationship_residual_count: int
    remaining_residual_by_predicate: list[InventoryCountRow] = Field(default_factory=list)
    remaining_residual_disposition_inventory: list[InventoryCountRow] = Field(
        default_factory=list
    )
    dungeonmind_owned_remaining_count: int
    dungeonmindbuddy_owned_remaining_count: int
    unadjudicated_remaining_count: int
    world_graph_digest_before: str | None = None
    world_graph_digest_after: str | None = None


class RelationshipExplicitAdapterConformanceError(RuntimeError):
    """Raised when adapter conformance invariants fail closed."""


def _counter_rows(counter: Counter[str]) -> list[InventoryCountRow]:
    return [
        InventoryCountRow(key=key, count=count) for key, count in sorted(counter.items())
    ]


def _ownership_for_remaining(
    remaining_edge_ids: list[str],
    *,
    adjudication_domain: bool,
) -> tuple[list[InventoryCountRow], int, int, int]:
    disposition_counter: Counter[str] = Counter()
    dm_owned = 0
    buddy_owned = 0
    unadjudicated = 0

    for edge_id in remaining_edge_ids:
        if not adjudication_domain:
            unadjudicated += 1
            disposition_counter["UNADJUDICATED"] += 1
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
    )


def _analyze_relationship_explicit_adapter_conformance_with_authorities(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    base_report: WholeWorldConformanceReportV4,
    catalog: RelationshipExplicitAdapterCatalogV1,
    world_graph_digest_before: str | None = None,
    world_graph_digest_after: str | None = None,
) -> RelationshipExplicitAdapterConformanceReportV1:
    """Private conformance path with injectable authorities (tests only).

    Production callers must use ``analyze_relationship_explicit_adapter_conformance_v1``,
    which always derives the live v4 base report and the immutable built-in catalog.
    """
    payload_sha = base_report.source_graph_payload_sha256
    adjudication_domain = matches_explicit_adapter_domain_v1(
        world_id=base_report.source_world_id,
        revision_id=base_report.source_revision_id,
        graph_payload_sha256=payload_sha,
    )
    candidate_ids = [record.edge_id for record in catalog.records]
    candidate_set = set(candidate_ids)

    base_residual = list(base_report.relationship_residual_edge_ids)
    base_residual_set = set(base_residual)
    vocabulary = load_builtin_world_object_v4_vocabulary()

    newly_represented: list[str] = []
    failed = 0
    store: UnionSupergraphStore | None = None

    if adjudication_domain:
        _, store = _load_exact_buddy_revision(
            root=root,
            world_id=world_id,
            revision_id=revision_id,
        )
        for edge_id in candidate_ids:
            if edge_id not in base_residual_set:
                failed += 1
                continue
            edge = store.edges.get(edge_id)
            if edge is None:
                failed += 1
                continue
            try:
                resolved = _resolve_relationship_explicit_adapter_with_catalog(
                    world_id=base_report.source_world_id,
                    revision_id=base_report.source_revision_id,
                    graph_payload_sha256=payload_sha,
                    edge=edge,
                    store=store,
                    catalog=catalog,
                    vocabulary=vocabulary,
                )
            except RelationshipExplicitAdapterIntegrityError:
                failed += 1
                continue
            if resolved is None:
                failed += 1
                continue
            newly_represented.append(edge_id)

    newly_set = set(newly_represented)
    remaining = sorted(edge_id for edge_id in base_residual if edge_id not in newly_set)

    predicate_counter: Counter[str] = Counter()
    if store is not None:
        for edge_id in remaining:
            edge = store.edges.get(edge_id)
            if edge is None:
                raise RelationshipExplicitAdapterConformanceError(
                    f"remaining residual edge missing from store: {edge_id}"
                )
            predicate_counter[edge.predicate] += 1
    elif adjudication_domain:
        raise RelationshipExplicitAdapterConformanceError(
            "adjudication-domain conformance requires a loaded revision store"
        )

    disposition_inventory, dm_owned, buddy_owned, unadjudicated = _ownership_for_remaining(
        remaining,
        adjudication_domain=adjudication_domain,
    )

    if adjudication_domain:
        forbidden = {
            row.key
            for row in disposition_inventory
            if row.key in _FORBIDDEN_REMAINING_DISPOSITIONS
        }
        if forbidden:
            raise RelationshipExplicitAdapterConformanceError(
                f"remaining residual ledger still contains closed dispositions: "
                f"{sorted(forbidden)}"
            )
        unexpected_candidates = candidate_set - newly_set
        if unexpected_candidates and failed == 0:
            raise RelationshipExplicitAdapterConformanceError(
                f"catalog edges not applied: {sorted(unexpected_candidates)}"
            )

    effective_represented = (
        base_report.relationship_represented_count + len(newly_represented)
    )
    effective_residual = len(remaining)
    if effective_represented + effective_residual != base_report.relationship_semantic_count:
        raise RelationshipExplicitAdapterConformanceError(
            "effective represented + residual must equal base semantic count: "
            f"{effective_represented}+{effective_residual}!="
            f"{base_report.relationship_semantic_count}"
        )

    return RelationshipExplicitAdapterConformanceReportV1(
        schema_version=RELATIONSHIP_EXPLICIT_ADAPTER_CONFORMANCE_SCHEMA_V1,
        world_id=base_report.source_world_id,
        campaign_id=base_report.source_campaign_id,
        source_revision_id=base_report.source_revision_id,
        source_graph_payload_sha256=payload_sha,
        dungeonmind_dependency_ref=_DUNGEONMIND_DEPENDENCY_REF_V4,
        world_object_vocabulary_revision=vocabulary.vocabulary_revision,
        world_object_vocabulary_sha256=vocabulary_sha256(vocabulary),
        adapter_catalog_schema=RELATIONSHIP_EXPLICIT_ADAPTER_CATALOG_SCHEMA_V1,
        base_relationship_semantic_count=base_report.relationship_semantic_count,
        base_relationship_represented_count=base_report.relationship_represented_count,
        base_relationship_residual_count=base_report.relationship_residual_count,
        uses_statblock_mechanics_count=base_report.uses_statblock_mechanics_count,
        adapter_candidate_count=len(candidate_ids),
        adapter_applied_count=len(newly_represented),
        adapter_failed_count=failed,
        newly_represented_edge_ids=sorted(newly_represented),
        remaining_residual_edge_ids=remaining,
        effective_relationship_represented_count=effective_represented,
        effective_relationship_residual_count=effective_residual,
        remaining_residual_by_predicate=_counter_rows(predicate_counter),
        remaining_residual_disposition_inventory=disposition_inventory,
        dungeonmind_owned_remaining_count=dm_owned,
        dungeonmindbuddy_owned_remaining_count=buddy_owned,
        unadjudicated_remaining_count=unadjudicated,
        world_graph_digest_before=world_graph_digest_before,
        world_graph_digest_after=world_graph_digest_after,
    )


def analyze_relationship_explicit_adapter_conformance_v1(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    world_graph_digest_before: str | None = None,
    world_graph_digest_after: str | None = None,
) -> RelationshipExplicitAdapterConformanceReportV1:
    """Apply the immutable built-in adapter catalog to a freshly derived v4 report.

    Translation-only: does not write the World Graph. Caller-supplied catalogs and
    base reports are intentionally not accepted.
    """
    base_report = analyze_exact_buddy_world_revision_v4(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    return _analyze_relationship_explicit_adapter_conformance_with_authorities(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
        base_report=base_report,
        catalog=load_eldyrwild_relationship_explicit_adapter_catalog_v1(),
        world_graph_digest_before=world_graph_digest_before,
        world_graph_digest_after=world_graph_digest_after,
    )


def compact_relationship_explicit_adapter_conformance_report_v1(
    report: RelationshipExplicitAdapterConformanceReportV1,
) -> dict[str, Any]:
    return report.model_dump(mode="json")


def derive_adjudication_explicit_adapter_edge_ids(
    adjudication_payload: dict[str, Any],
) -> list[str]:
    """Independent oracle: Buddy-owned EXPLICIT_ADAPTER_CANDIDATE + ADD adapter."""
    edge_ids: list[str] = []
    for record in adjudication_payload.get("records", []):
        if (
            record.get("responsible_repo") == "DungeonMindBuddy"
            and record.get("disposition") == "EXPLICIT_ADAPTER_CANDIDATE"
            and record.get("next_action") == "ADD_BUDDY_EXPLICIT_ADAPTER"
        ):
            edge_ids.append(record["edge_id"])
    return sorted(edge_ids)


def derive_adjudication_remaining_residual_edge_ids(
    adjudication_payload: dict[str, Any],
) -> list[str]:
    """Buddy-owned adjudication rows minus EXPLICIT_ADAPTER_CANDIDATE."""
    remaining: list[str] = []
    for record in adjudication_payload.get("records", []):
        if record.get("responsible_repo") != "DungeonMindBuddy":
            continue
        if record.get("disposition") == "EXPLICIT_ADAPTER_CANDIDATE":
            continue
        remaining.append(record["edge_id"])
    return sorted(remaining)
