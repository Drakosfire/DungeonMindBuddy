"""Acceptance proofs for CUTOVER Captain/Thrin alias assertion package."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    BlockerClass,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    ALIAS_ASSERTION_POLICY_ID,
    IDENTITY_LIFECYCLE_SOURCE_HISTORY_POLICY_ID,
    source_history_policy_from_identity_lifecycle_proof,
)
from apps.live_control_server.services.cutover_identity_lifecycle_history_after_571 import (
    FIXTURE_RELPATH as HISTORICAL_575_FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256 as HISTORICAL_575_FIXTURE_SHA256,
)
from apps.live_control_server.services.cutover_alias_assertion_package_after_shadow_alias_remove import (
    CANONICAL_GRAPH_PAYLOAD_SHA256,
    CANONICAL_REVISION_ID,
    CAPTAIN_BLOCKER_ID,
    DISPATCH_BASE_SHA,
    FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256,
    THRIN_BLOCKER_ID,
    WORLD_ID,
    _contribution_history_digest,
    _loaded_store_digest,
    _report_bytes,
    compose_cutover_alias_assertion_package_after_shadow_alias_remove,
    verify_cutover_alias_assertion_package_after_shadow_alias_remove,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    MIGRATION_RESIDUAL_EDGE_IDS,
    snapshot_source_authority_inventory,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore


REPO = repo_root()
ROOT = world_graph_root()
FIXTURE_PATH = REPO / FIXTURE_RELPATH
HISTORICAL_PATH = REPO / HISTORICAL_575_FIXTURE_RELPATH


@pytest.fixture(scope="module")
def report() -> Any:
    return compose_cutover_alias_assertion_package_after_shadow_alias_remove(ROOT, REPO)


def test_dispatch_base_is_pr586_descendant() -> None:
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
    assert DISPATCH_BASE_SHA == "17a58740502e99d592f05ba9a10f1d8401e09581"


def test_canonical_pins(report: Any) -> None:
    assert report.world_id == WORLD_ID
    assert report.canonical_revision_id == CANONICAL_REVISION_ID
    assert report.canonical_graph_payload_sha256 == CANONICAL_GRAPH_PAYLOAD_SHA256
    assert CANONICAL_REVISION_ID == "rev:0c644e56b45bcaac709012206e3e41c2"
    assert CANONICAL_GRAPH_PAYLOAD_SHA256 == (
        "0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2"
    )


def test_merge_only_diagnostic_cannot_mint_source_history_policy(report: Any) -> None:
    diagnostic = report.merge_only_diagnostic
    assert diagnostic["candidate_count"] == 28
    assert diagnostic["reconstructable_count"] == 16
    assert diagnostic["unresolved_count"] == 12
    assert diagnostic["passed"] is False
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


def test_source_history_policy_is_same_store_not_retrofitted(report: Any) -> None:
    policy = report.source_history_policy
    assert policy["policy_id"] == IDENTITY_LIFECYCLE_SOURCE_HISTORY_POLICY_ID
    assert policy["source"] == "source_history_policy_from_identity_lifecycle_proof"
    assert policy["same_store_world_id"] == WORLD_ID
    assert policy["same_store_revision_id"] == CANONICAL_REVISION_ID
    assert policy["same_store_payload_sha256"] == CANONICAL_GRAPH_PAYLOAD_SHA256
    assert policy["proven_element_count"] == len(
        report.current_lifecycle_proof["element_ids"]
    )


def test_pre_package_ep_inventory_is_exactly_captain_and_thrin(report: Any) -> None:
    assert report.pre_package_evidence_provenance_ids == [
        CAPTAIN_BLOCKER_ID,
        THRIN_BLOCKER_ID,
    ]


def test_alias_package_proof_covers_current_blockers(report: Any) -> None:
    proof = report.alias_package_proof
    assert proof["passed"] is True
    assert proof["residuals"] == []
    assert proof["blocker_element_ids"] == [CAPTAIN_BLOCKER_ID, THRIN_BLOCKER_ID]
    assert set(proof["covered_blocker_element_ids"]) == {
        CAPTAIN_BLOCKER_ID,
        THRIN_BLOCKER_ID,
    }
    assert proof["package_row_count"] == len(proof["package_rows"])
    assert proof["package_row_count"] >= 2
    by_blocker = {row["blocker_element_id"] for row in proof["package_rows"]}
    assert by_blocker == {CAPTAIN_BLOCKER_ID, THRIN_BLOCKER_ID}
    for row in proof["package_rows"]:
        assert row["reconstructable"] is True
        assert row["buddy_source_assertion_id"]
        assert row["buddy_source_contribution_id"]
        assert row["buddy_source_payload_sha256"]
        assert row["source_evidence_ref_ids"]
        assert row["source_artifact_ids"]
        assert row["dungeonmind_assertion_id"]
        assert row["dungeonmind_alias_record"]
        assert row["metadata_derivation"]["campaign_scope"]
        assert row["metadata_derivation"]["temporal_scope"] == (
            "unknown_no_fictional_time_mapping"
        )
        temporal = row["dungeonmind_alias_record"]["assertion_metadata"]["temporal_scope"]
        assert temporal["kind"] == "unknown"


def test_alias_policy_is_revision_bound_to_current_proof(report: Any) -> None:
    policy = report.alias_assertion_policy
    assert policy["policy_id"] == ALIAS_ASSERTION_POLICY_ID
    assert policy["world_id"] == WORLD_ID
    assert policy["canonical_revision_id"] == CANONICAL_REVISION_ID
    assert policy["canonical_graph_payload_sha256"] == CANONICAL_GRAPH_PAYLOAD_SHA256
    assert policy["package_proof_sha256"]
    assert set(policy["proven_alias_blocker_element_ids"]) == {
        CAPTAIN_BLOCKER_ID,
        THRIN_BLOCKER_ID,
    }
    assert report.policy["source"] == "alias_assertion_policy_from_proof"


def test_remeasurement_clears_alias_evidence_provenance(report: Any) -> None:
    assert report.attribute_assertion_count == 0
    assert report.evidence_provenance["count"] == 0
    assert report.evidence_provenance["examples"] == []
    assert report.identity_history_count == 20
    assert report.contribution_history_count == 5291
    blockers = {row["blocker_class"] for row in report.post_policy_blockers}
    assert BlockerClass.EVIDENCE_PROVENANCE.value not in blockers
    assert BlockerClass.ATTRIBUTE_ASSERTION.value not in blockers


def test_relationships_unchanged(report: Any) -> None:
    canonical = report.relationship_invariants["canonical"]
    migration = report.relationship_invariants["migration"]
    for key, value in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY.items():
        assert canonical[key] == value
    for key, value in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY.items():
        assert migration[key] == value
    assert set(migration["residual_edge_ids"]) == MIGRATION_RESIDUAL_EDGE_IDS
    assert len(migration["residual_edge_ids"]) == 5


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
    assert report.mutation_proof["assertion_support_unchanged"] is True
    assert report.mutation_proof["contributions_unchanged"] is True
    assert report.mutation_proof["loaded_store_unchanged"] is True
    assert after_head.head_revision_id == CANONICAL_REVISION_ID
    assert after_tree == before
    assert after_source == snapshot_source_authority_inventory(ROOT)


def test_captain_thrin_package_implemented_and_cutover_not_ready(report: Any) -> None:
    assert report.captain_thrin_package_implemented is True
    assert report.cutover_disposition == "CUTOVER_NOT_READY"
    assert "captain_thrin_package_implemented" in report.diagnostics
    assert "alias_assertion_policy_revision_bound" in report.diagnostics
    assert report.next_slice_recommendation["case"] != "CASE_B"


def test_historical_575_fixture_digest_and_merge_only_world(report: Any) -> None:
    raw = HISTORICAL_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == HISTORICAL_575_FIXTURE_SHA256
    historical = report.historical_575
    assert historical["fixture_path"] == HISTORICAL_575_FIXTURE_RELPATH
    assert historical["fixture_digest_matches_locked"] is True
    assert historical["merge_only_proof"]["passed"] is True
    assert historical["error"] is None


def test_sealed_report_is_checkout_path_portable(report: Any) -> None:
    fixture_path = report.historical_575["fixture_path"]
    assert fixture_path == HISTORICAL_575_FIXTURE_RELPATH
    assert not Path(fixture_path).is_absolute()
    encoded = _report_bytes(report).decode()
    assert str(REPO) not in encoded
    assert "/tmp/" not in encoded


def test_compose_is_byte_identical_across_repo_roots(tmp_path: Path, report: Any) -> None:
    alias = tmp_path / "other_checkout"
    alias.symlink_to(REPO)
    reproduced = compose_cutover_alias_assertion_package_after_shadow_alias_remove(
        ROOT, alias
    )
    assert _report_bytes(report) == _report_bytes(reproduced)
    assert str(alias.resolve()) not in _report_bytes(reproduced).decode()
    assert str(alias) not in _report_bytes(reproduced).decode()


def _minimal_union_store(**updates: Any) -> UnionSupergraphStore:
    payload = {
        "schema": "dmb_union_supergraph_store_v0",
        "version": "0.1",
        "campaign_id": "longmont-c2",
        "graph_id": None,
        "graph_domains": [],
        "source_domains": [],
        "focus_session_id": "session-23",
        "nodes": {},
        "edges": {},
        "evidence": {},
        "source_artifacts": {},
        "aliases": {},
        "identity_redirects": [],
        "identity_merge_records": [],
        "identity_decisions": [],
        "assertion_support": {},
        "contribution_source_payload_sha256": {"contribution:base": "a" * 64},
        "contribution_replay_manifest": [],
        "initialization_contribution_ids": ["contribution:base"],
        "initialization_plan_digest": None,
        "initialization_attestation_digest": None,
        "adjacency": {},
        "diagnostics": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
    }
    payload.update(updates)
    return UnionSupergraphStore.model_validate(payload)


def test_contribution_history_digest_detects_real_field_change() -> None:
    store = _minimal_union_store()
    before_contrib = _contribution_history_digest(store)
    before_store = _loaded_store_digest(store)
    mutated = store.model_copy(
        update={
            "contribution_source_payload_sha256": {
                "contribution:base": "b" * 64,
            }
        }
    )
    assert _contribution_history_digest(mutated) != before_contrib
    assert _loaded_store_digest(mutated) != before_store


def test_build_verify_roundtrip_when_fixture_present(report: Any) -> None:
    if not LOCKED_FIXTURE_SHA256.strip() and not FIXTURE_PATH.is_file():
        pytest.skip("fixture not sealed yet")
    result = verify_cutover_alias_assertion_package_after_shadow_alias_remove(
        root=ROOT, repo=REPO
    )
    if not FIXTURE_PATH.is_file():
        pytest.skip("fixture not sealed yet")
    assert result.verified is True
    reproduced = compose_cutover_alias_assertion_package_after_shadow_alias_remove(
        ROOT, REPO
    )
    stored = FIXTURE_PATH.read_bytes()
    assert hashlib.sha256(stored).hexdigest() == result.fixture_sha256
    if LOCKED_FIXTURE_SHA256.strip():
        assert result.fixture_sha256 == LOCKED_FIXTURE_SHA256
    assert stored == _report_bytes(reproduced)
