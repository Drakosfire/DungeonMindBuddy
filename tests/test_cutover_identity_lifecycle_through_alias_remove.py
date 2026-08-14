"""Acceptance proofs for CUTOVER identity lifecycle through alias_remove."""

from __future__ import annotations

import hashlib
import subprocess
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    BlockerClass,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    source_history_policy_from_identity_lifecycle_proof,
)
from apps.live_control_server.services.cutover_identity_lifecycle_history_after_571 import (
    FIXTURE_RELPATH as HISTORICAL_575_FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256 as HISTORICAL_575_FIXTURE_SHA256,
)
from apps.live_control_server.services.cutover_identity_lifecycle_through_alias_remove import (
    CANONICAL_GRAPH_PAYLOAD_SHA256,
    CANONICAL_REVISION_ID,
    CAPTAIN_BLOCKER_ID,
    DISPATCH_BASE_SHA,
    FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256,
    THRIN_BLOCKER_ID,
    WORLD_ID,
    _report_bytes,
    compose_cutover_identity_lifecycle_through_alias_remove,
    verify_cutover_identity_lifecycle_through_alias_remove,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    snapshot_source_authority_inventory,
)


REPO = repo_root()
ROOT = world_graph_root()
FIXTURE_PATH = REPO / FIXTURE_RELPATH
HISTORICAL_PATH = REPO / HISTORICAL_575_FIXTURE_RELPATH


@pytest.fixture(scope="module")
def report() -> Any:
    return compose_cutover_identity_lifecycle_through_alias_remove(ROOT, REPO)


def test_dispatch_base_is_pr584_descendant() -> None:
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
    assert DISPATCH_BASE_SHA == "ad6dd2507d4f5ed2c5cc24e9c0c8b50df2e65ca9"


def test_canonical_pins(report: Any) -> None:
    assert report.world_id == WORLD_ID
    assert report.canonical_revision_id == CANONICAL_REVISION_ID
    assert report.canonical_graph_payload_sha256 == CANONICAL_GRAPH_PAYLOAD_SHA256
    assert CANONICAL_REVISION_ID == "rev:0c644e56b45bcaac709012206e3e41c2"
    assert CANONICAL_GRAPH_PAYLOAD_SHA256 == (
        "0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2"
    )


def test_merge_only_diagnostic_is_16_of_28_and_cannot_mint_policy(report: Any) -> None:
    diagnostic = report.merge_only_diagnostic
    assert diagnostic["candidate_count"] == 28
    assert diagnostic["reconstructable_count"] == 16
    assert diagnostic["unresolved_count"] == 12
    assert diagnostic["passed"] is False
    assert len(diagnostic["unresolved_element_ids"]) == 12
    assert report.merge_only_policy_refused is True
    from apps.live_control_server.integrations.dungeonmind_kernel.identity_lifecycle_history_conformance_v1 import (
        prove_identity_lifecycle_history_v1,
    )

    store = kernel.load_world_graph_revision_with_integrity(
        ROOT, WORLD_ID, CANONICAL_REVISION_ID
    )
    merge_only = prove_identity_lifecycle_history_v1(
        store,
        world_id=WORLD_ID,
        canonical_revision_id=CANONICAL_REVISION_ID,
        canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
    )
    with pytest.raises(ValueError, match="has not passed|unresolved"):
        source_history_policy_from_identity_lifecycle_proof(merge_only)


def test_current_lifecycle_proof_passes(report: Any) -> None:
    proof = report.current_lifecycle_proof
    assert proof["passed"] is True
    assert proof["unresolved_element_ids"] == []
    assert proof["reconstructable_count"] == len(proof["element_ids"])
    assert set(proof["element_ids"]) == set(report.pre_policy_attribute_assertion_ids)
    assert proof["field_counts"]["identity_state"] == 7
    assert proof["field_counts"]["merged_into"] == 7
    assert proof["field_counts"]["last_identity_decision_id"] == 14


def test_alias_remove_lineage_is_causal_and_list_ordered(report: Any) -> None:
    lineage = report.alias_remove_lineage
    assert lineage["ordering"] == "durable_decision_list_position"
    assert lineage["invalidating_split_unmerge"] is False
    assert lineage["survivor_count"] == 6
    rows = lineage["rows"]
    assert len(rows) == 6
    for row in rows:
        assert row["ordering"] == "durable_decision_list_position"
        assert row["alias_remove_decision_id"]
        assert row["causal_merge_decision_id"]
        assert row["alias_remove_decision_id"] != row["causal_merge_decision_id"]
        assert row["alias"]
    proof_rows = [
        row
        for row in report.current_lifecycle_proof["rows"]
        if row["decision_kind"] == "alias_remove" and row["field"] == "last_identity_decision_id"
    ]
    assert len(proof_rows) == 6
    for row in proof_rows:
        assert row["lifecycle_role"] == "merge_survivor"
        assert row["decision_status"] == "active"
        assert row["reconstructable"] is True
        assert "earlier merge" in row["rationale"]


def test_policy_minted_from_current_passed_proof_only(report: Any) -> None:
    assert report.policy["source"] == "source_history_policy_from_identity_lifecycle_proof"
    assert report.policy["policy_id"] == "identity_lifecycle_history_v1"
    assert report.policy["proven_element_count"] == len(
        report.current_lifecycle_proof["element_ids"]
    )


def test_remeasurement_is_recorded(report: Any) -> None:
    assert isinstance(report.attribute_assertion_count, int)
    assert report.evidence_provenance["count"] == 2
    assert set(report.evidence_provenance["examples"]) == {
        CAPTAIN_BLOCKER_ID,
        THRIN_BLOCKER_ID,
    }
    assert report.identity_history_count == 20
    assert report.contribution_history_count == 5291
    # Recorded observation, not a classifier constant. Hypothesis: 0.
    assert report.attribute_assertion_count == 0


def test_relationships_unchanged(report: Any) -> None:
    canonical = report.relationship_invariants["canonical"]
    migration = report.relationship_invariants["migration"]
    for key, value in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY.items():
        assert canonical[key] == value
    for key, value in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY.items():
        assert migration[key] == value


def test_no_mutation(report: Any) -> None:
    before = snapshot_world_graph_tree_digest(ROOT, WORLD_ID)
    after_head = kernel.open_world_graph_head(ROOT, WORLD_ID)
    after_tree = snapshot_world_graph_tree_digest(ROOT, WORLD_ID)
    after_source = snapshot_source_authority_inventory(ROOT)
    assert report.mutation_proof["head_before"] == CANONICAL_REVISION_ID
    assert report.mutation_proof["head_after"] == CANONICAL_REVISION_ID
    assert report.mutation_proof["tree_digest_unchanged"] is True
    assert report.mutation_proof["payload_unchanged"] is True
    assert report.mutation_proof["identity_ledger_unchanged"] is True
    assert report.mutation_proof["aliases_unchanged"] is True
    assert report.mutation_proof["contributions_unchanged"] is True
    assert after_head.head_revision_id == CANONICAL_REVISION_ID
    assert after_tree == before
    assert after_source == snapshot_source_authority_inventory(ROOT)


def test_captain_thrin_package_not_implemented(report: Any) -> None:
    assert report.captain_thrin_package_implemented is False
    assert CAPTAIN_BLOCKER_ID in report.evidence_provenance["examples"]
    assert THRIN_BLOCKER_ID in report.evidence_provenance["examples"]
    assert "captain_thrin_package_not_implemented" in report.diagnostics
    blockers = {row["blocker_class"] for row in report.post_policy_blockers}
    assert BlockerClass.EVIDENCE_PROVENANCE.value in blockers


def test_historical_575_fixture_digest_and_merge_only_world(report: Any) -> None:
    raw = HISTORICAL_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == HISTORICAL_575_FIXTURE_SHA256
    historical = report.historical_575
    assert historical["fixture_digest_matches_locked"] is True
    assert historical["merge_only_proof"]["passed"] is True
    assert historical["merge_only_proof"]["candidate_count"] == 28
    assert historical["merge_only_proof"]["unresolved_count"] == 0
    assert historical["error"] is None


def test_build_verify_roundtrip_when_fixture_present(report: Any) -> None:
    if not LOCKED_FIXTURE_SHA256.strip() and not FIXTURE_PATH.is_file():
        pytest.skip("fixture not sealed yet")
    result = verify_cutover_identity_lifecycle_through_alias_remove(root=ROOT, repo=REPO)
    if not FIXTURE_PATH.is_file():
        pytest.skip("fixture not sealed yet")
    assert result.verified is True
    reproduced = compose_cutover_identity_lifecycle_through_alias_remove(ROOT, REPO)
    if FIXTURE_PATH.is_file():
        stored = FIXTURE_PATH.read_bytes()
        assert hashlib.sha256(stored).hexdigest() == result.fixture_sha256
        if LOCKED_FIXTURE_SHA256.strip():
            assert result.fixture_sha256 == LOCKED_FIXTURE_SHA256
        assert stored == _report_bytes(reproduced)
