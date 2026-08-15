"""Acceptance proofs for CUTOVER dual-sense relationship decomposition."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_dual_sense_decomposition_v1 import (
    evaluate_global_aspect_substitution_v1,
    package_canonical_bytes,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
)
from apps.live_control_server.services.cutover_relationship_dual_sense_decomposition_after_alias_package import (
    CANONICAL_GRAPH_PAYLOAD_SHA256,
    CANONICAL_REVISION_ID,
    DISPATCH_BASE_SHA,
    EXACT_SOURCE_NODE_IDS,
    LOCKED_PACKAGE_SHA256,
    MANIFEST_RELPATH,
    WORLD_ID,
    build_cutover_relationship_dual_sense_decomposition_after_alias_package,
    compose_cutover_relationship_dual_sense_decomposition_after_alias_package,
    verify_cutover_relationship_dual_sense_decomposition_after_alias_package,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    MIGRATION_RESIDUAL_EDGE_IDS,
    snapshot_source_authority_inventory,
)
from apps.live_control_server.services.eldyrwild_relationship_node_kind_source_repair import (
    LOCKED_MANIFEST_SHA256 as PREDECESSOR_LOCKED_SHA256,
)


REPO = repo_root()
ROOT = world_graph_root()
MANIFEST_PATH = REPO / MANIFEST_RELPATH


@pytest.fixture(scope="module")
def report() -> Any:
    return compose_cutover_relationship_dual_sense_decomposition_after_alias_package(
        ROOT, REPO
    )


def test_dispatch_base_is_pr587_descendant() -> None:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO),
            "merge-base",
            "--is-ancestor",
            DISPATCH_BASE_SHA,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert DISPATCH_BASE_SHA == "cc5dc6ddba0750924a46cf13843498c124937e5f"


def test_pins_and_predecessor_authority(report: Any) -> None:
    assert report.canonical_revision_id == CANONICAL_REVISION_ID
    assert report.canonical_graph_payload_sha256 == CANONICAL_GRAPH_PAYLOAD_SHA256
    assert report.dungeonmind_dependency_ref == CURRENT_V5_TARGET.dungeonmind_dependency_ref
    assert CURRENT_V5_TARGET.target_id == "current_v5"
    assert report.predecessor_repair_verified is True
    assert report.predecessor_repair_manifest_sha256 == PREDECESSOR_LOCKED_SHA256
    assert "predecessor_repair_loader_consumed" in report.diagnostics
    assert PREDECESSOR_LOCKED_SHA256 == (
        "96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247"
    )


def test_package_covers_exact_three_and_five(report: Any) -> None:
    package = report.package
    assert [row["source_node_id"] for row in package["decomposition_rows"]] == list(
        EXACT_SOURCE_NODE_IDS
    )
    assigned = [row["edge_id"] for row in package["endpoint_assignments"]]
    assert assigned == sorted(MIGRATION_RESIDUAL_EDGE_IDS)
    assert len(assigned) == 5
    by_source = {row["source_node_id"]: row for row in package["decomposition_rows"]}
    assert by_source["loc:wizard_college"]["aspect_key"] == "organization"
    assert by_source["loc:wizard_college"]["projected_dm_kind"] == "dnd5e:faction"
    assert by_source["loc:wizard_college"]["stored_buddy_kind"] == "location"
    assert by_source["node:meat_distribution_network_session9"]["aspect_key"] == "site"
    assert (
        by_source["node:meat_distribution_network_session9"]["projected_dm_kind"]
        == "dnd5e:location"
    )
    assert by_source["node:hempholm_folk_revelry"]["aspect_key"] == "event"
    assert by_source["node:hempholm_folk_revelry"]["projected_dm_kind"] == "dnd5e:event"
    assert all(
        row["assigned_endpoint"] == "target" for row in package["endpoint_assignments"]
    )
    dumped = json.dumps(package)
    assert "node:aspect:" not in dumped
    assert report.decomposition_proof["passed"] is True


def test_package_projection_admits_assigned_and_retains_stored_senses(
    report: Any,
) -> None:
    projection = report.package_projection
    assert projection["passed"] is True
    assert projection["retained_regressions"] == []
    assert projection["uncovered_current_residual_edge_ids"] == []
    assert projection["extra_package_edge_assignments"] == []
    assert {row["edge_id"] for row in projection["assigned_admissions"]} == set(
        MIGRATION_RESIDUAL_EDGE_IDS
    )
    assert all(row["admitted"] is True for row in projection["assigned_admissions"])
    assert all(row["admitted"] is True for row in projection["retained_admissions"])
    assert projection["schema"] == "dmb_relationship_dual_sense_decomposition_v1_package_projection"
    assert "migration_relationship" not in projection


def test_global_aspect_lie_regresses_retained_eldyrwild_edges(report: Any) -> None:
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        whole_world_conformance_v4 as whole_world_v4,
    )
    from apps.live_control_server.integrations.dungeonmind_kernel.relationship_dual_sense_decomposition_v1 import (
        DualSenseDecompositionPackageV1,
    )

    _manifest, store = whole_world_v4._load_exact_buddy_revision(
        root=ROOT,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
    )
    package = DualSenseDecompositionPackageV1.model_validate(report.package)
    college = evaluate_global_aspect_substitution_v1(
        store,
        package=package,
        source_node_id="loc:wizard_college",
        target=CURRENT_V5_TARGET,
    )
    network = evaluate_global_aspect_substitution_v1(
        store,
        package=package,
        source_node_id="node:meat_distribution_network_session9",
        target=CURRENT_V5_TARGET,
    )
    revelry = evaluate_global_aspect_substitution_v1(
        store,
        package=package,
        source_node_id="node:hempholm_folk_revelry",
        target=CURRENT_V5_TARGET,
    )
    assert college == [
        "edge:node:thalia:travels_to:loc:wizard_college",
        "edge:node:torbin:travels_to:loc:wizard_college",
    ]
    assert network == [
        "edge:node:captain_blart:leads:node:meat_distribution_network_session9:coordinates",
        "edge:node:lyra:leads:node:meat_distribution_network_session9",
    ]
    assert revelry == ["edge:node:hempholm_folk_revelry:within:loc:hempholm"]


def test_authoritative_relationship_state_is_unchanged(report: Any) -> None:
    canonical = report.relationship_invariants["canonical"]
    migration = report.relationship_invariants["migration"]
    assert {
        key: canonical[key] for key in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
    } == EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
    assert {
        key: migration[key] for key in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    } == EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    assert set(migration["residual_edge_ids"]) == set(MIGRATION_RESIDUAL_EDGE_IDS)
    assert report.relationship_invariants["package_does_not_relabel_authoritative_state"] is True
    assert report.cutover_disposition == "CUTOVER_NOT_READY"
    assert report.next_slice_recommendation["case"] != "CASE_B"
    assert report.next_slice_recommendation["owner"] == "DungeonMind"


def test_no_world_graph_or_source_mutation(report: Any) -> None:
    proof = report.mutation_proof
    assert proof["head_unchanged"] is True
    assert proof["tree_unchanged"] is True
    assert proof["loaded_store_unchanged"] is True
    assert proof["source_authority_unchanged"] is True
    assert proof["node_kinds_unchanged"] is True
    assert proof["head_before"] == CANONICAL_REVISION_ID
    live_head = kernel.open_world_graph_head(ROOT, WORLD_ID)
    assert live_head.head_revision_id == proof["head_after"]
    assert snapshot_world_graph_tree_digest(ROOT, WORLD_ID) == proof["tree_after"]
    assert snapshot_source_authority_inventory(ROOT) == proof["source_authority_after"]


def test_build_is_idempotent_and_verify_matches() -> None:
    first = build_cutover_relationship_dual_sense_decomposition_after_alias_package(
        root=ROOT, repo=REPO
    )
    second = build_cutover_relationship_dual_sense_decomposition_after_alias_package(
        root=ROOT, repo=REPO
    )
    assert first.package_sha256 == second.package_sha256
    assert second.already_built is True
    assert MANIFEST_PATH.is_file()
    locked = LOCKED_PACKAGE_SHA256.strip()
    if locked:
        assert first.package_sha256 == locked
    verified = verify_cutover_relationship_dual_sense_decomposition_after_alias_package(
        root=ROOT, repo=REPO
    )
    assert verified.verified is True
    raw = MANIFEST_PATH.read_bytes()
    from apps.live_control_server.integrations.dungeonmind_kernel.relationship_dual_sense_decomposition_v1 import (
        DualSenseDecompositionPackageV1,
        sha256_bytes,
    )

    stored = DualSenseDecompositionPackageV1.model_validate(json.loads(raw))
    assert package_canonical_bytes(stored) == raw
    assert sha256_bytes(raw) == first.package_sha256


def test_no_whole_world_analyzer_policy_was_added() -> None:
    source = Path(
        "apps/live_control_server/services/"
        "cutover_relationship_dual_sense_decomposition_after_alias_package.py"
    ).read_text(encoding="utf-8")
    assert "alias_assertion_policy" not in source
    assert "_analyze_loaded_buddy_world_store_v5" not in source
    assert "analyze_exact_buddy_world_revision_v5" not in source
    assert "predecessor_authority_from_locked_bytes" not in source
    assert "predecessor_authority_from_sealed_repair" in source
