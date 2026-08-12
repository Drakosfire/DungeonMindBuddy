"""Acceptance proofs for the post-#566 CUTOVER whole-world re-anchor."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    BlockerClass,
    enumerate_durable_element_ids,
    inspect_dungeonmind_durable_adoption_seam,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    analyze_exact_buddy_world_revision_v4,
)
from apps.live_control_server.services import (
    cutover_whole_world_reanchor as cutover,
)
from apps.live_control_server.services import (
    eldyrwild_relationship_node_kind_source_repair as repair,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    CANONICAL_GRAPH_PAYLOAD_SHA256,
    CANONICAL_RESIDUAL_EDGE_IDS,
    CANONICAL_REVISION_ID,
    CHANGED_KIND_PATHS,
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256,
    MIGRATION_NEWLY_REPRESENTED_EDGE_IDS,
    MIGRATION_RESIDUAL_EDGE_IDS,
    _compose_report,
    _report_bytes,
    build_cutover_whole_world_reanchor,
    get_cutover_whole_world_reanchor_status,
    snapshot_source_authority_inventory,
    verify_cutover_whole_world_reanchor,
)


REPO = repo_root()
ROOT = world_graph_root()
FIXTURE_PATH = REPO / FIXTURE_RELPATH

_REQUIRED_BLOCKER_FIELDS = {
    "blocker_class",
    "count",
    "examples",
    "presence_scope",
    "blocking_stage",
    "ownership_scope",
    "responsible_repo",
    "smallest_next_change",
    "ledger_disposition",
}


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report() -> Any:
    if not (ROOT / "graph_memory" / "worlds" / "eldyrwild").is_dir():
        pytest.skip("Eldyrwild world graph not present")
    return _compose_report(ROOT, REPO)


def test_exact_activation_pins_and_status(report: Any) -> None:
    status = get_cutover_whole_world_reanchor_status(ROOT, repo=REPO)
    assert status.eligibility == "eligible"
    assert report.buddy_repository_base_sha == cutover.BUDDY_BASE_SHA
    assert report.canonical_revision_id == CANONICAL_REVISION_ID
    assert report.canonical_graph_payload_sha256 == CANONICAL_GRAPH_PAYLOAD_SHA256
    assert report.dungeonmind_dependency_ref == cutover.DUNGEONMIND_DEPENDENCY_REF
    assert report.repair_authority["manifest_sha256"] == repair.LOCKED_MANIFEST_SHA256


def test_fixture_digest_is_locked_and_byte_stable(report: Any) -> None:
    raw = FIXTURE_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == LOCKED_FIXTURE_SHA256
    assert raw == _report_bytes(report)


def test_canonical_effective_relationship_inventory_is_exact(report: Any) -> None:
    relationship = report.canonical_view["relationship_inventory"]
    assert {
        key: relationship[key] for key in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
    } == EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
    assert set(relationship["residual_edge_ids"]) == CANONICAL_RESIDUAL_EDGE_IDS


def test_migration_relationship_inventory_comes_from_locked_proof(report: Any) -> None:
    relationship = report.migration_projection["relationship_inventory"]
    assert {
        key: relationship[key] for key in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    } == EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    assert set(relationship["residual_edge_ids"]) == MIGRATION_RESIDUAL_EDGE_IDS
    assert set(relationship["newly_represented_edge_ids"]) == (
        MIGRATION_NEWLY_REPRESENTED_EDGE_IDS
    )
    assert relationship["authority"] == "eldyrwild-relationship-node-kind-source-repair-v1"


def test_projection_changes_exactly_four_kind_paths(report: Any) -> None:
    assert report.projection_delta["changed_durable_paths"] == list(CHANGED_KIND_PATHS)
    assert report.repair_authority["changed_node_kind_paths"] == list(CHANGED_KIND_PATHS)
    assert report.projection_delta["changed_node_ids"] == sorted(
        {
            "item_shatter_mages_tower",
            "mystery_stone_bridge_river_name",
            "loc:guilds",
            "item:torvak-hemp-caravan",
        }
    )


def test_projection_preserves_durable_ids_and_has_no_aspects(report: Any) -> None:
    base_store = cutover.whole_world_v4._load_exact_buddy_revision(
        root=ROOT,
        world_id="eldyrwild",
        revision_id=CANONICAL_REVISION_ID,
    )[1]
    overlay = repair._overlay_store(base_store)
    assert enumerate_durable_element_ids(base_store) == enumerate_durable_element_ids(
        overlay
    )
    assert "aspect" not in _report_bytes(report).decode("utf-8").lower()


def test_both_views_have_complete_durable_accounting(report: Any) -> None:
    assert report.canonical_view["unaccounted_durable_elements"] == 0
    assert report.migration_projection["unaccounted_durable_elements"] == 0


def test_raw_v4_relationship_totals_do_not_leak_into_report(report: Any) -> None:
    raw_v4 = analyze_exact_buddy_world_revision_v4(
        root=ROOT,
        world_id="eldyrwild",
        revision_id=CANONICAL_REVISION_ID,
    )
    assert raw_v4.relationship_residual_count == 15
    assert report.canonical_view["relationship_inventory"]["residual"] == 9
    assert report.migration_projection["relationship_inventory"]["residual"] == 5
    assert report.canonical_view["relationship_inventory"]["authority"].endswith(
        "effective_conformance_v1"
    )
    assert report.migration_projection["relationship_inventory"]["authority"].endswith(
        "source-repair-v1"
    )


def test_relationship_blockers_replace_raw_v4_rows(report: Any) -> None:
    for view_name, expected_count in (("canonical_view", 9), ("migration_projection", 5)):
        rows = [
            row
            for row in getattr(report, view_name)["blockers"]
            if row["blocker_class"] == BlockerClass.RELATIONSHIP_PREDICATE.value
        ]
        assert len(rows) == 1
        assert rows[0]["count"] == expected_count
        assert rows[0]["ledger_disposition"] == "replaced_by_effective_relationship"
    assert report.projection_delta["changed_blockers"][0]["blocker_class"] == (
        BlockerClass.RELATIONSHIP_PREDICATE.value
    )


def test_dual_sense_stop_edges_remain_explicit(report: Any) -> None:
    residual = set(report.migration_projection["relationship_residual_edge_ids"])
    assert residual == set(repair.STAGE_B_REMAINING_RESIDUAL_EDGE_IDS)
    assert {
        "edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of",
        "edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9",
        "edge:node:headmaster_tinkerbright:leads:loc:wizard_college",
        "edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry",
        "edge:pc:caelynn:participates_in:node:hempholm_folk_revelry",
    } == residual


def test_adoption_seam_is_introspected(report: Any) -> None:
    expected = inspect_dungeonmind_durable_adoption_seam()
    assert report.adoption_seam.model_dump(mode="json") == expected.model_dump(mode="json")
    assert report.adoption_seam.status == "DURABLE_ADOPTION_BOUNDARY_MISSING"


def test_normalized_blockers_carry_presence_stage_and_ownership(report: Any) -> None:
    for view_name in ("canonical_view", "migration_projection"):
        for row in getattr(report, view_name)["blockers"]:
            assert _REQUIRED_BLOCKER_FIELDS <= set(row)
            assert row["presence_scope"] in {
                "canonical_only",
                "projection_only",
                "both",
            }
            assert row["blocking_stage"] in {
                "adoption_package_construction",
                "durable_adoption",
                "shadow_parity",
                "authority_promotion",
            }
            assert row["ownership_scope"] in {"singular", "cross_repository"}
            if row["ownership_scope"] == "singular":
                assert row["responsible_repo"] in {"DungeonMind", "DungeonMindBuddy"}
            else:
                assert row["responsible_repo"] is None

    dual_sense = next(
        row
        for row in report.migration_projection["blockers"]
        if row["blocker_class"] == BlockerClass.RELATIONSHIP_PREDICATE.value
    )
    assert dual_sense["ownership_scope"] == "cross_repository"
    assert dual_sense["responsible_repo"] is None
    assert dual_sense["blocking_stage"] == "authority_promotion"
    assert dual_sense["presence_scope"] == "both"

    kind = next(
        row
        for row in report.migration_projection["blockers"]
        if row["blocker_class"] == BlockerClass.WORLD_OBJECT_KIND.value
    )
    assert kind["blocking_stage"] == "adoption_package_construction"
    assert kind["ownership_scope"] == "singular"
    assert kind["responsible_repo"] == "DungeonMind"
    assert kind["presence_scope"] == "both"
    assert any("thread" in example or "kind" in example for example in kind["examples"])


def test_blocker_ledger_is_lossless_against_whole_world_rows(report: Any) -> None:
    carry = report.blocker_carry_forward
    assert carry["lossless"] is True
    assert carry["non_blocking_operational_classifications"] == []
    dispositions = {row["disposition"] for row in carry["rows"]}
    assert dispositions <= {"carried", "replaced_by_effective_relationship"}
    assert "replaced_by_effective_relationship" in dispositions
    original_classes = {
        (row["view"], row["original_blocker_class"]) for row in carry["rows"]
    }
    assert ("canonical", BlockerClass.RELATIONSHIP_PREDICATE.value) in original_classes
    assert ("migration", BlockerClass.WORLD_OBJECT_KIND.value) in original_classes
    for row in carry["rows"]:
        if row["disposition"] == "carried":
            assert row["cutover_count"] == row["original_count"]


def test_cutover_recommends_case_a_for_thread_kind_gap(report: Any) -> None:
    assert report.cutover_disposition == "CUTOVER_NOT_READY"
    recommendation = report.next_slice_recommendation
    assert recommendation["case"] == "CASE_A"
    assert recommendation["repository"] == "DungeonMind"
    assert recommendation["basis_blocker_classes"] == [
        BlockerClass.WORLD_OBJECT_KIND.value
    ]
    assert recommendation["basis_blocking_stages"] == ["adoption_package_construction"]
    assert "thread" in recommendation["change"]
    assert BlockerClass.DURABLE_ADOPTION_BOUNDARY.value in recommendation[
        "deferred_durable_adoption_gates"
    ]
    assert BlockerClass.RELATIONSHIP_PREDICATE.value in recommendation[
        "cross_repository_decision_sets"
    ]


def test_case_b_only_when_package_construction_is_clear() -> None:
    durable_only = [
        {
            "blocker_class": BlockerClass.DURABLE_ADOPTION_BOUNDARY.value,
            "count": 1,
            "examples": ["WorldGraphRepository"],
            "presence_scope": "both",
            "blocking_stage": "durable_adoption",
            "ownership_scope": "singular",
            "responsible_repo": "DungeonMind",
            "smallest_next_change": "Add public governed adopt-existing-world.",
            "ledger_disposition": "carried",
        },
        {
            "blocker_class": BlockerClass.POSTGRES_ADOPTION.value,
            "count": 1,
            "examples": ["postgres"],
            "presence_scope": "both",
            "blocking_stage": "durable_adoption",
            "ownership_scope": "singular",
            "responsible_repo": "DungeonMind",
            "smallest_next_change": "Exercise Postgres after seam exists.",
            "ledger_disposition": "carried",
        },
    ]
    recommendation = cutover._next_slice_recommendation(durable_only)
    assert recommendation["case"] == "CASE_B"
    assert recommendation["basis_blocking_stages"] == ["durable_adoption"]


def test_build_and_verify_are_non_publishing(report: Any) -> None:
    before_head = kernel.open_world_graph_head(ROOT, "eldyrwild").head_revision_id
    before_tree = snapshot_world_graph_tree_digest(ROOT, "eldyrwild")
    before_source = snapshot_source_authority_inventory(ROOT)
    built = build_cutover_whole_world_reanchor(root=ROOT, repo=REPO)
    verified = verify_cutover_whole_world_reanchor(root=ROOT, repo=REPO)
    assert built.fixture_sha256 == LOCKED_FIXTURE_SHA256
    assert "already_built" in built.diagnostics
    assert verified.verified
    assert kernel.open_world_graph_head(ROOT, "eldyrwild").head_revision_id == before_head
    assert snapshot_world_graph_tree_digest(ROOT, "eldyrwild") == before_tree
    assert snapshot_source_authority_inventory(ROOT) == before_source


def test_source_authority_families_are_unchanged_by_compose(report: Any) -> None:
    before = snapshot_source_authority_inventory(ROOT)
    _ = _compose_report(ROOT, REPO)
    after = snapshot_source_authority_inventory(ROOT)
    assert after == before
    assert set(after) >= {
        "contribution_index",
        "contributions",
        "contribution_rebuild",
        "identity_decisions",
        "identity_decision_index",
        "revisions",
        "initialization",
        "head",
    }


def test_stale_fixture_pin_refuses_replacement(
    report: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cutover, "LOCKED_FIXTURE_SHA256", "0" * 64)
    with pytest.raises(cutover.CutoverWholeWorldReanchorError) as excinfo:
        build_cutover_whole_world_reanchor(root=ROOT, repo=REPO)
    assert excinfo.value.code == "fixture_digest_mismatch"
    assert hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest() == LOCKED_FIXTURE_SHA256


@pytest.mark.parametrize(
    ("attr", "value", "code"),
    [
        ("CANONICAL_REVISION_ID", "rev:deadbeef", "stale_canonical_head"),
        ("CANONICAL_GRAPH_PAYLOAD_SHA256", "0" * 64, "canonical_payload_mismatch"),
        ("LOCKED_REPAIR_MANIFEST_SHA256", "1" * 64, "repair_manifest_mismatch"),
        ("DUNGEONMIND_DEPENDENCY_REF", "0" * 40, "dependency_pin_mismatch"),
    ],
)
def test_stale_dependency_pins_refuse_before_publication(
    report: Any,
    monkeypatch: pytest.MonkeyPatch,
    attr: str,
    value: str,
    code: str,
) -> None:
    monkeypatch.setattr(cutover, attr, value)
    if attr == "DUNGEONMIND_DEPENDENCY_REF":
        # Contract pin check compares report.dungeonmind_dependency_ref too.
        with pytest.raises(cutover.CutoverWholeWorldReanchorError) as excinfo:
            _compose_report(ROOT, REPO)
        assert excinfo.value.code in {code, "dependency_pin_mismatch", "contract_pin_mismatch"}
        return
    with pytest.raises(cutover.CutoverWholeWorldReanchorError) as excinfo:
        _compose_report(ROOT, REPO)
    assert excinfo.value.code == code
    # Fixture bytes must remain untouched by refused compose.
    assert hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest() == LOCKED_FIXTURE_SHA256


def test_stale_contract_pin_refuses(report: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    pins = dict(cutover._contract_pins())
    pins["world_object_vocabulary"] = "world-object-v999"
    monkeypatch.setattr(cutover, "_contract_pins", lambda: pins)
    with pytest.raises(cutover.CutoverWholeWorldReanchorError) as excinfo:
        _compose_report(ROOT, REPO)
    assert excinfo.value.code == "contract_pin_mismatch"


def test_repair_authority_proof_is_locked(report: Any) -> None:
    assert report.repair_authority["verified"] is True
    assert report.repair_authority["proof"]["passed"] is True
    assert report.repair_authority["proof"]["zero_regressions"] is True
    assert report.repair_authority["proof"]["projected_inventory"] == (
        EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    )


def test_cutover_owned_effective_proofs_supersede_stale_suite(report: Any) -> None:
    """Historical effective-conformance suite still pins pre-#563 R_current.

    CUTOVER owns the post-#566 equivalent proof via effective conformance on
    the canonical pin plus the locked #566 isolated repair proof.
    """
    assert "historical_effective_conformance_suite_superseded_by_cutover_owned_proofs" in (
        report.diagnostics
    )
    assert report.canonical_view["relationship_inventory"]["authority"] == (
        "dmb_dungeonmind_relationship_effective_conformance_v1"
    )
    assert report.migration_projection["relationship_inventory"]["authority"] == (
        "eldyrwild-relationship-node-kind-source-repair-v1"
    )
    assert {
        key: report.canonical_view["relationship_inventory"][key]
        for key in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
    } == EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
    assert {
        key: report.migration_projection["relationship_inventory"][key]
        for key in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    } == EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY


def test_report_fixture_has_no_graph_write_surface(report: Any) -> None:
    assert report.diagnostics == [
        "non_publishing",
        "canonical_relationship_authority:effective_conformance",
        "migration_relationship_authority:prove_isolated_repair_effect",
        "overlay_manifest_payload_sha_reflects_canonical_pin_for_domain_matching",
        "raw_v4_relationship_predicate_blockers_replaced_by_owning_ledgers",
        "next_slice_derived_from_normalized_blocker_stages",
        "historical_effective_conformance_suite_superseded_by_cutover_owned_proofs",
    ]
    assert "apply" not in json.dumps(_fixture()).lower()
