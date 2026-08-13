"""Acceptance proofs for CUTOVER identity-lifecycle history after PR #571."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.identity_lifecycle_history_conformance_v1 import (
    EXPECTED_ELDRYWILD_FIELD_COUNTS,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    BlockerClass,
    SemanticClassification,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
    LEGACY_SOURCE_HISTORY_POLICY,
)
from apps.live_control_server.services import (
    cutover_identity_lifecycle_history_after_571 as cutover,
)
from apps.live_control_server.services.cutover_identity_lifecycle_history_after_571 import (
    BUDDY_BASE_SHA,
    CANONICAL_GRAPH_PAYLOAD_SHA256,
    CANONICAL_REVISION_ID,
    DUNGEONMIND_DEPENDENCY_REF,
    EXPECTED_ATTRIBUTE_ASSERTION_COUNT,
    EXPECTED_CONTRIBUTION_HISTORY_COUNT,
    EXPECTED_EVIDENCE_PROVENANCE_COUNT,
    EXPECTED_FIELD_COUNTS,
    EXPECTED_IDENTITY_HISTORY_COUNT,
    FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256,
    PREDECESSOR_FIXTURE_RELPATH,
    PREDECESSOR_FIXTURE_SHA256,
    CutoverIdentityLifecycleHistoryAfter571Error,
    _compose_report,
    _report_bytes,
    build_cutover_identity_lifecycle_history_after_571,
    get_cutover_identity_lifecycle_history_after_571_status,
    snapshot_source_authority_inventory,
    verify_cutover_identity_lifecycle_history_after_571,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    CANONICAL_RESIDUAL_EDGE_IDS,
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    MIGRATION_RESIDUAL_EDGE_IDS,
    _next_slice_recommendation,
)
from apps.live_control_server.services.cutover_whole_world_repin_after_dm30 import (
    verify_cutover_whole_world_repin_after_dm30,
)
from dungeonmind_dnd.application.world_object_vocabulary import (
    builtin_world_object_v5_vocabulary_ref,
)
from dungeonmind_dnd.application.world_property_vocabulary import (
    builtin_world_property_v3_vocabulary_ref,
)
from dungeonmind.application.semantic_profiles import descriptor_sha256
from dungeonmind_dnd.application.world_object_vocabulary import load_builtin_v3_descriptor


REPO = repo_root()
ROOT = world_graph_root()
FIXTURE_PATH = REPO / FIXTURE_RELPATH
PREDECESSOR_PATH = REPO / PREDECESSOR_FIXTURE_RELPATH


@pytest.fixture(scope="module")
def report() -> Any:
    return _compose_report(ROOT, REPO)


def _blocker(blockers: list[dict[str, Any]], blocker_class: str) -> dict[str, Any] | None:
    for row in blockers:
        if row["blocker_class"] == blocker_class:
            return row
    return None


def test_t1_branch_descends_from_pr571_merge() -> None:
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(REPO), "merge-base", "--is-ancestor", BUDDY_BASE_SHA, "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert BUDDY_BASE_SHA == "9d5efb7eaa92a4890bd49db45130e5843777c8b9"


def test_t2_dungeonmind_contracts_unchanged() -> None:
    object_ref = builtin_world_object_v5_vocabulary_ref()
    property_ref = builtin_world_property_v3_vocabulary_ref()
    profile = load_builtin_v3_descriptor()
    assert CURRENT_V5_TARGET.dungeonmind_dependency_ref == DUNGEONMIND_DEPENDENCY_REF
    assert DUNGEONMIND_DEPENDENCY_REF == "be76acc997c5fbcb8ceaa090969ec051afa6051d"
    assert object_ref.catalog_sha256 == (
        "f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8"
    )
    assert property_ref.catalog_sha256 == (
        "aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4"
    )
    assert descriptor_sha256(profile) == (
        "2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496"
    )


def test_t3_predecessor_fixture_exact() -> None:
    raw = PREDECESSOR_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == PREDECESSOR_FIXTURE_SHA256
    assert digest == "a666a2bc0d7fabe7a8b66e1dc93698a29bb911efede7c3089df28887477c13b5"


def test_t4_predecessor_verifier_still_passes() -> None:
    result = verify_cutover_whole_world_repin_after_dm30(root=ROOT, repo=REPO)
    assert result.verified is True


def test_t5_predecessor_still_reports_attribute_28() -> None:
    payload = json.loads(PREDECESSOR_PATH.read_text(encoding="utf-8"))
    row = _blocker(
        payload["migration_projection"]["blockers"],
        BlockerClass.ATTRIBUTE_ASSERTION.value,
    )
    assert row is not None
    assert row["count"] == 28


def test_t6_t9_identity_proof_inventory_and_reconstructable(report: Any) -> None:
    proof = report.identity_lifecycle_proof
    assert proof["field_counts"] == EXPECTED_ELDRYWILD_FIELD_COUNTS
    assert proof["field_counts"] == EXPECTED_FIELD_COUNTS
    assert proof["passed"] is True
    assert proof["unresolved_element_ids"] == []
    assert proof["reconstructable_count"] == 28
    assert len(proof["element_ids"]) == 28
    assert all(row["reconstructable"] is True for row in proof["rows"])


def test_t7_t8_attribute_set_equals_proof_ids(report: Any) -> None:
    proof_ids = set(report.identity_lifecycle_proof["element_ids"])
    delta_ids = set(report.classification_delta["element_ids"])
    assert proof_ids == delta_ids
    assert len(proof_ids) == EXPECTED_ATTRIBUTE_ASSERTION_COUNT
    assert report.classification_delta["count"] == 28
    assert report.classification_delta["lossless"] is True


def test_t10_decision_pointers_resolve(report: Any) -> None:
    for row in report.identity_lifecycle_proof["rows"]:
        if row["field"] != "last_identity_decision_id":
            continue
        assert isinstance(row["decision_id"], str) and row["decision_id"].strip()
        assert row["stored_value"] == row["decision_id"]
        assert row["decision_kind"] == "merge"
        assert row["decision_status"] == "active"


def test_t11_merged_away_sources_are_coherent(report: Any) -> None:
    for row in report.identity_lifecycle_proof["rows"]:
        if row["field"] != "merged_into":
            continue
        assert row["lifecycle_role"] == "merge_source"
        assert row["subject_node_id"] == row["node_id"]
        assert row["target_node_id"] == row["stored_value"]
        assert row["redirect_id"]
        assert row["redirect_status"] == "active"


def test_t12_survivor_state_is_coherent(report: Any) -> None:
    for row in report.identity_lifecycle_proof["rows"]:
        if row["field"] != "identity_state":
            continue
        assert row["stored_value"] == "survivor"
        assert row["lifecycle_role"] == "merge_survivor"
        assert row["target_node_id"] == row["node_id"]
        assert row["decision_kind"] == "merge"


def test_t16_historical_policy_byte_stable() -> None:
    before = PREDECESSOR_PATH.read_bytes()
    result = verify_cutover_whole_world_repin_after_dm30(root=ROOT, repo=REPO)
    after = PREDECESSOR_PATH.read_bytes()
    assert result.verified is True
    assert before == after
    assert hashlib.sha256(after).hexdigest() == PREDECESSOR_FIXTURE_SHA256
    assert LEGACY_SOURCE_HISTORY_POLICY.proven_node_state_history_element_ids == frozenset()


def test_t17_t18_successor_changes_exact_28_elements(report: Any) -> None:
    delta = report.classification_delta
    assert len(delta["transitions"]) == 28
    assert len(delta["element_ids"]) == 28
    assert len(set(delta["element_ids"])) == 28
    for row in delta["transitions"]:
        assert row["previous"]["classification"] == (
            SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP.value
        )
        assert row["previous"]["blocker_class"] == BlockerClass.ATTRIBUTE_ASSERTION.value
        assert row["current"]["classification"] == (
            SemanticClassification.SOURCE_MIGRATION_HISTORY.value
        )
        assert row["current"]["blocker_class"] is None
        assert row["explanation"]
    assert delta["field_counts"] == {
        "identity_state": 7,
        "merged_into": 7,
        "last_identity_decision_id": 14,
    }


def test_t19_attribute_clears(report: Any) -> None:
    for view_name in ("canonical_view", "migration_projection"):
        blockers = getattr(report, view_name)["blockers"]
        assert _blocker(blockers, BlockerClass.ATTRIBUTE_ASSERTION.value) is None


def test_t20_identity_history_remains_exact(report: Any) -> None:
    for view_name in ("canonical_view", "migration_projection"):
        row = _blocker(getattr(report, view_name)["blockers"], BlockerClass.IDENTITY_HISTORY.value)
        assert row is not None
        assert row["count"] == EXPECTED_IDENTITY_HISTORY_COUNT
        assert row["blocking_stage"] == "durable_adoption"
        assert "identity migration replay" in row["smallest_next_change"]


def test_contribution_history_stays_separate_from_identity_history(report: Any) -> None:
    for view_name in ("canonical_view", "migration_projection"):
        blockers = getattr(report, view_name)["blockers"]
        contribution = _blocker(blockers, BlockerClass.CONTRIBUTION_HISTORY.value)
        identity = _blocker(blockers, BlockerClass.IDENTITY_HISTORY.value)
        assert contribution is not None
        assert contribution["count"] == EXPECTED_CONTRIBUTION_HISTORY_COUNT
        assert contribution["count"] == 5285
        assert identity is not None
        assert identity["count"] == EXPECTED_IDENTITY_HISTORY_COUNT
        assert identity["count"] == 14
        assert contribution["blocking_stage"] == "durable_adoption"
        assert identity["blocking_stage"] == "durable_adoption"
    for view in ("canonical", "migration"):
        changed = {row["blocker_class"] for row in report.blocker_delta[view]["rows"]}
        assert BlockerClass.CONTRIBUTION_HISTORY.value not in changed
        assert BlockerClass.IDENTITY_HISTORY.value not in changed
        assert changed == {BlockerClass.ATTRIBUTE_ASSERTION.value}


def test_t21_evidence_provenance_unchanged(report: Any) -> None:
    row = _blocker(
        report.migration_projection["blockers"],
        BlockerClass.EVIDENCE_PROVENANCE.value,
    )
    assert row is not None
    assert row["count"] == EXPECTED_EVIDENCE_PROVENANCE_COUNT


def test_t22_relationship_inventory_unchanged(report: Any) -> None:
    canonical = report.canonical_view["relationship_inventory"]
    migration = report.migration_projection["relationship_inventory"]
    for key, value in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY.items():
        assert canonical[key] == value
    for key, value in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY.items():
        assert migration[key] == value
    assert set(canonical["residual_edge_ids"]) == CANONICAL_RESIDUAL_EDGE_IDS
    assert set(migration["residual_edge_ids"]) == MIGRATION_RESIDUAL_EDGE_IDS
    assert set(report.relationship_invariants["migration"]["residual_edge_ids"]) == (
        MIGRATION_RESIDUAL_EDGE_IDS
    )


def test_t23_canonical_migration_identity_proof_identical(report: Any) -> None:
    canonical_ids = report.classification_delta["element_ids"]
    migration_ids = [row["element_id"] for row in report.classification_delta["migration_transitions"]]
    assert canonical_ids == migration_ids
    assert report.identity_lifecycle_proof["element_ids"] == canonical_ids


def test_t24_no_source_mutation(report: Any) -> None:
    proof = report.mutation_proof
    assert proof["unchanged"] is True
    assert proof["head_revision_id"]["before"] == proof["head_revision_id"]["after"]
    assert proof["graph_tree_digest"]["before"] == proof["graph_tree_digest"]["after"]
    assert proof["source_authority"]["before"] == proof["source_authority"]["after"]
    assert proof["identity_authority"]["before"] == proof["identity_authority"]["after"]
    assert proof["predecessor_fixture_sha256"]["before"] == proof["predecessor_fixture_sha256"]["after"]
    live_head = kernel.open_world_graph_head(ROOT, "eldyrwild")
    assert live_head.head_revision_id == CANONICAL_REVISION_ID
    assert snapshot_world_graph_tree_digest(ROOT, "eldyrwild") == proof["graph_tree_digest"]["after"]
    assert snapshot_source_authority_inventory(ROOT) == proof["source_authority"]["after"]


def test_t25_stage_driven_recommendation(report: Any) -> None:
    derived = _next_slice_recommendation(report.migration_projection["blockers"])
    assert report.next_slice_recommendation == derived
    package_construction_remains = any(
        row.get("blocking_stage") == "adoption_package_construction"
        for row in report.migration_projection["blockers"]
    )
    if package_construction_remains:
        assert report.next_slice_recommendation["case"] != "CASE_B"


def test_t26_cutover_stays_not_ready(report: Any) -> None:
    assert report.cutover_disposition == "CUTOVER_NOT_READY"
    relationship = _blocker(
        report.migration_projection["blockers"],
        BlockerClass.RELATIONSHIP_PREDICATE.value,
    )
    assert relationship is not None
    assert relationship["count"] == 5
    assert relationship["blocking_stage"] == "adoption_package_construction"
    assert relationship["ownership_scope"] == "cross_repository"


def test_t27_deterministic_fixture(report: Any) -> None:
    built = build_cutover_identity_lifecycle_history_after_571(root=ROOT, repo=REPO)
    assert built.fixture_sha256
    assert FIXTURE_PATH.is_file()
    verified = verify_cutover_identity_lifecycle_history_after_571(root=ROOT, repo=REPO)
    assert verified.verified is True
    assert verified.fixture_sha256 == built.fixture_sha256
    reproduced = hashlib.sha256(_report_bytes(report)).hexdigest()
    assert reproduced == built.fixture_sha256
    locked = LOCKED_FIXTURE_SHA256.strip()
    if locked:
        assert built.fixture_sha256 == locked


def test_t28_stale_source_refusal(report: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cutover, "EXPECTED_ATTRIBUTE_ASSERTION_COUNT", 27)
    with pytest.raises(CutoverIdentityLifecycleHistoryAfter571Error) as exc:
        cutover._compose_report(ROOT, REPO)
    assert exc.value.code in {
        "stale_attribute_assertion_inventory",
        "identity_lifecycle_proof_count_mismatch",
        "classification_delta_mismatch",
        "predecessor_attribute_count_mismatch",
    }
    monkeypatch.setattr(
        cutover, "EXPECTED_ATTRIBUTE_ASSERTION_COUNT", EXPECTED_ATTRIBUTE_ASSERTION_COUNT
    )
    monkeypatch.setattr(
        cutover,
        "EXPECTED_FIELD_COUNTS",
        {"identity_state": 1, "merged_into": 1, "last_identity_decision_id": 1},
    )
    with pytest.raises(CutoverIdentityLifecycleHistoryAfter571Error) as exc:
        cutover._compose_report(ROOT, REPO)
    assert exc.value.code == "stale_identity_shadow_inventory"


def test_status_eligible() -> None:
    status = get_cutover_identity_lifecycle_history_after_571_status(ROOT, repo=REPO)
    assert status.eligibility == "eligible"
    assert status.canonical_graph_payload_sha256 == CANONICAL_GRAPH_PAYLOAD_SHA256
    assert status.predecessor_fixture_sha256 == PREDECESSOR_FIXTURE_SHA256


def test_analyze_exact_v5_entrypoint_stays_legacy_default() -> None:
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v5 import (
        analyze_exact_buddy_world_revision_v5,
    )
    import inspect

    source = inspect.getsource(analyze_exact_buddy_world_revision_v5)
    assert "source_history_policy" not in source
    assert "CURRENT_V5_TARGET" in source
