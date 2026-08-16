"""Current/history partition and v2 history proofs for the Eldyrwild adoption bundle."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
    EXPECTED_CURRENT_SEMANTIC,
    EXPECTED_HISTORY_ONLY,
    EXPECTED_MECHANICS,
    EXPECTED_RAW_EDGE_COUNT,
    FALSE_STOP_EDGE_IDS,
    build_eldyrwild_existing_world_adoption_bundle_v2,
    evaluate_false_stop_edges,
    partition_raw_stored_edges,
    raw_edges_would_create_vocabulary_blockers,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _load_exact_buddy_revision,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    resolve_buddy_predicate_mapping_v4,
)
from apps.live_control_server.services.eldyrwild_relationship_node_kind_source_repair import (
    DEFERRED_RESIDUAL_EDGE_IDS,
    KIND_REPAIR_SPECS,
    STAGE_B_REMAINING_RESIDUAL_EDGE_IDS,
)
from dungeonmind.application.existing_world_adoption import parse_existing_world_adoption_bundle
from dungeonmind.application.graph_snapshot import VersionedUnionGraphSnapshotReader
from dungeonmind.contracts.existing_world_adoption import EXISTING_WORLD_ADOPTION_BUNDLE_V2_SCHEMA
from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
from dungeonmind_dnd.application.world_object_vocabulary import load_builtin_v3_descriptor
from graph_memory.world_supergraph.contribution_store import list_contribution_records

ROOT = world_graph_root()
REPO = repo_root()
WORLD_ID = "eldyrwild"
REV = "rev:0c644e56b45bcaac709012206e3e41c2"
HIRES_EDGE_ID = "edge:pc:ephanna:hires:node:thrin-branchborn"
REPORTS_THREAT_EDGE_ID = (
    "edge:faction:town-guards-mireward-gate:reports_threat_in:"
    "mystery:session25:west-wall-screaming-and-dark-shapes-below"
)


@pytest.fixture(scope="module")
def loaded_store():
    manifest, store = _load_exact_buddy_revision(root=ROOT, world_id=WORLD_ID, revision_id=REV)
    return manifest, store


@pytest.fixture(scope="module")
def built_bundle():
    digest_before = snapshot_world_graph_tree_digest(ROOT, WORLD_ID)
    built = build_eldyrwild_existing_world_adoption_bundle_v2(root=ROOT, repo=REPO)
    digest_after = snapshot_world_graph_tree_digest(ROOT, WORLD_ID)
    assert digest_before == digest_after
    return built


def test_raw_current_mechanics_history_partition(loaded_store) -> None:
    _manifest, store = loaded_store
    partition = partition_raw_stored_edges(store)
    current = set(partition.current_semantic_ids)
    mechanics = set(partition.mechanics_ids)
    history = set(partition.history_ids)
    raw = set(store.edges)
    assert len(raw) == EXPECTED_RAW_EDGE_COUNT
    assert len(current) == EXPECTED_CURRENT_SEMANTIC
    assert len(mechanics) == EXPECTED_MECHANICS
    assert len(history) == EXPECTED_HISTORY_ONLY
    assert current & mechanics == set()
    assert current & history == set()
    assert mechanics & history == set()
    assert current | mechanics | history == raw


def test_prior_false_stop_sixteen_are_history_only(loaded_store) -> None:
    _manifest, store = loaded_store
    contributions = list_contribution_records(ROOT, WORLD_ID)
    reports = evaluate_false_stop_edges(store, contributions=contributions)
    partition = partition_raw_stored_edges(store)
    assert len(reports) == 16
    assert {item.edge_id for item in reports} == set(FALSE_STOP_EDGE_IDS)
    assert all(item.raw_stored for item in reports)
    assert all(item.current_semantic is False for item in reports)
    assert all(item.final_disposition == "SOURCE_MIGRATION_HISTORY" for item in reports)
    assert set(FALSE_STOP_EDGE_IDS) <= set(partition.history_ids)
    assert set(FALSE_STOP_EDGE_IDS).isdisjoint(partition.current_semantic_ids)


def test_raw_store_scan_is_the_false_positive_that_caused_the_stop(loaded_store) -> None:
    _manifest, store = loaded_store
    blockers = raw_edges_would_create_vocabulary_blockers(store)
    assert set(FALSE_STOP_EDGE_IDS) <= set(blockers)
    assert resolve_buddy_predicate_mapping_v4("hires") is None
    assert resolve_buddy_predicate_mapping_v4("reports_threat_in") is None
    partition = partition_raw_stored_edges(store)
    assert HIRES_EDGE_ID in partition.history_ids
    assert REPORTS_THREAT_EDGE_ID in partition.history_ids
    assert HIRES_EDGE_ID not in partition.current_semantic_ids


def test_residual_progression_nine_to_five_to_zero(built_bundle) -> None:
    built = built_bundle
    kind_repair_ids = {
        edge_id
        for spec in KIND_REPAIR_SPECS
        for edge_id in spec["affected_deferred_edge_ids"]
    }
    assert built.residual_before_projections == 9
    assert set(DEFERRED_RESIDUAL_EDGE_IDS) == kind_repair_ids | set(
        STAGE_B_REMAINING_RESIDUAL_EDGE_IDS
    )
    assert built.represented_after_kind_repair == 318
    assert built.residual_after_kind_repair == 5
    assert {item.edge_id for item in built.mapped_relationships if item.resolution == "kind_repair"} == kind_repair_ids
    assert {
        item.edge_id for item in built.mapped_relationships if item.resolution == "aspect_selection"
    } == set(STAGE_B_REMAINING_RESIDUAL_EDGE_IDS)
    assert built.current_unrepresentable_count == 0
    assert built.v6_relationship_count == EXPECTED_CURRENT_SEMANTIC


def test_historical_hires_omitted_from_graph_but_retained_in_v2_history(
    loaded_store, built_bundle
) -> None:
    _manifest, store = loaded_store
    built = built_bundle
    assert HIRES_EDGE_ID in store.edges
    graph_ids = {row["relationship_id"] for row in built.bundle.graph_payload["relationships"]}
    assert HIRES_EDGE_ID not in graph_ids
    assert HIRES_EDGE_ID not in set(built.partition.current_semantic_ids)
    hires_assertion = None
    hires_correction = None
    for contribution in built.bundle.contributions:
        for assertion in contribution.assertions:
            if assertion.predicate == "hires" and assertion.subject_object_id == "pc:ephanna":
                hires_assertion = assertion
        for correction in contribution.assertion_corrections:
            if hires_assertion and correction.target_assertion_id == hires_assertion.assertion_id:
                hires_correction = correction
    assert hires_assertion is not None
    assert hires_correction is not None
    assert hires_correction.correction_kind.value == "contradicts"


def test_session25_reports_threat_in_is_history_with_correction(built_bundle) -> None:
    built = built_bundle
    graph_ids = {row["relationship_id"] for row in built.bundle.graph_payload["relationships"]}
    assert REPORTS_THREAT_EDGE_ID not in graph_ids
    report = next(item for item in built.false_stop_reports if item.edge_id == REPORTS_THREAT_EDGE_ID)
    assert report.current_support_state == "contradicted"
    assert report.correction_contribution_ids
    assert "contradicts" in report.correction_kinds or "contradicts_and_replaces" in report.correction_kinds


def test_parser_accepts_canonical_v2_bundle(built_bundle) -> None:
    built = built_bundle
    descriptor = load_builtin_v3_descriptor()
    parsed = parse_existing_world_adoption_bundle(
        built.canonical_bytes,
        graph_reader=VersionedUnionGraphSnapshotReader(
            StaticSemanticProfileRegistry([descriptor])
        ),
    )
    assert parsed.schema_version == EXISTING_WORLD_ADOPTION_BUNDLE_V2_SCHEMA
    assert parsed.graph_schema == "dm_union_graph_v6"
    assert len(parsed.contributions) == built.contribution_count
    assert parsed.graph_payload["relationship_endpoint_aspect_schema"] == (
        "dm_relationship_endpoint_aspect_v1"
    )


def test_history_edge_with_unknown_predicate_does_not_block_vocabulary(built_bundle) -> None:
    built = built_bundle
    assert built.current_unrepresentable_count == 0
    graph_predicates = {row["predicate"] for row in built.bundle.graph_payload["relationships"]}
    assert "dnd5e:hires" not in graph_predicates
    assert "hires" not in graph_predicates
    assert "reports_threat_in" not in graph_predicates


def test_correction_targets_exist_in_bundled_history(built_bundle) -> None:
    built = built_bundle
    contributions = {item.contribution_id: item for item in built.bundle.contributions}
    for contribution in built.bundle.contributions:
        assertion_ids = {item.assertion_id for item in contribution.assertions}
        for correction in contribution.assertion_corrections:
            target = contributions[correction.target_contribution_id]
            target_ids = {item.assertion_id for item in target.assertions}
            assert correction.target_assertion_id in target_ids
            if correction.replacement_assertion_id is not None:
                assert correction.replacement_assertion_id in assertion_ids


def test_source_derived_candidate_is_preserved(built_bundle) -> None:
    kinds = [
        assertion.epistemic_kind.value
        for contribution in built_bundle.bundle.contributions
        for assertion in contribution.assertions
    ]
    assert "source_derived_candidate" in kinds
    assert kinds.count("source_derived_candidate") == 1389


def test_mechanics_remain_outside_generic_relationships(built_bundle) -> None:
    built = built_bundle
    assert len(built.mechanics_proofs) == EXPECTED_MECHANICS
    assert all(item.disposition == "A" for item in built.mechanics_proofs)
    graph_ids = {row["relationship_id"] for row in built.bundle.graph_payload["relationships"]}
    assert set(built.partition.mechanics_ids).isdisjoint(graph_ids)


def test_graph_contains_only_current_semantic_relationships(built_bundle) -> None:
    built = built_bundle
    graph_ids = {row["relationship_id"] for row in built.bundle.graph_payload["relationships"]}
    assert graph_ids == set(built.partition.current_semantic_ids)
    assert graph_ids.isdisjoint(built.partition.history_ids)
    assert graph_ids.isdisjoint(built.partition.mechanics_ids)
    assert set(built.partition.current_semantic_ids).isdisjoint(built.partition.history_ids)


def test_producer_does_not_import_adoption_persistence() -> None:
    source = Path(
        "apps/live_control_server/integrations/dungeonmind_kernel/"
        "eldyrwild_existing_world_adoption_bundle_v2.py"
    ).read_text(encoding="utf-8")
    assert "adopt_existing_world" not in source
    assert "ExistingWorldAdoptionCommandV2" not in source
