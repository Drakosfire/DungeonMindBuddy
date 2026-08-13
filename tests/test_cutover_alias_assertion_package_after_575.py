"""Acceptance proofs for CUTOVER alias assertion package after PR #575."""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Any

import pytest

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    BlockerClass,
    ClassifiedElement,
    SemanticClassification,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
)
from apps.live_control_server.services.cutover_alias_assertion_package_after_575 import (
    BUDDY_BASE_SHA,
    DUNGEONMIND_DEPENDENCY_REF,
    EXPECTED_CONTRIBUTION_HISTORY_COUNT,
    EXPECTED_EVIDENCE_PROVENANCE_COUNT,
    EXPECTED_IDENTITY_DERIVED_ALIAS_COUNT,
    EXPECTED_IDENTITY_HISTORY_COUNT,
    EXPECTED_PACKAGED_ALIAS_COUNT,
    FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256,
    PREDECESSOR_FIXTURE_RELPATH,
    PREDECESSOR_FIXTURE_SHA256,
    CutoverAliasAssertionPackageAfter575Error,
    _compose_report,
    build_alias_classification_delta,
    get_cutover_alias_assertion_package_after_575_status,
)
from apps.live_control_server.services.cutover_identity_lifecycle_history_after_571 import (
    verify_cutover_identity_lifecycle_history_after_571,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    CANONICAL_RESIDUAL_EDGE_IDS,
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    MIGRATION_RESIDUAL_EDGE_IDS,
)
from dungeonmind.application.semantic_profiles import descriptor_sha256
from dungeonmind_dnd.application.world_object_vocabulary import (
    builtin_world_object_v5_vocabulary_ref,
    load_builtin_v3_descriptor,
)
from dungeonmind_dnd.application.world_property_vocabulary import (
    builtin_world_property_v3_vocabulary_ref,
)


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


def _element(
    element_id: str,
    *,
    classification: SemanticClassification,
    blocker_class: BlockerClass | None,
) -> ClassifiedElement:
    return ClassifiedElement(
        element_id=element_id,
        element_family="node_field",
        classification=classification,
        blocker_class=blocker_class,
        note="test",
    )


def test_branch_descends_from_pr576_merge() -> None:
    result = subprocess.run(
        ["git", "-C", str(REPO), "merge-base", "--is-ancestor", BUDDY_BASE_SHA, "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert BUDDY_BASE_SHA == "fda746b99a8a9830280bf1beac126a8221ddedfc"


def test_dungeonmind_contracts_unchanged() -> None:
    object_ref = builtin_world_object_v5_vocabulary_ref()
    property_ref = builtin_world_property_v3_vocabulary_ref()
    profile = load_builtin_v3_descriptor()
    assert CURRENT_V5_TARGET.dungeonmind_dependency_ref == DUNGEONMIND_DEPENDENCY_REF
    assert object_ref.catalog_sha256 == (
        "f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8"
    )
    assert property_ref.catalog_sha256 == (
        "aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4"
    )
    assert descriptor_sha256(profile) == (
        "2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496"
    )


def test_predecessor_fixture_exact() -> None:
    raw = PREDECESSOR_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == PREDECESSOR_FIXTURE_SHA256
    assert digest == "1a2cd8f9c47b223d4623fccbe1c988dd8d3eb1c8796078a32a32720f51ef000b"


def test_predecessor_verifier_still_passes() -> None:
    result = verify_cutover_identity_lifecycle_history_after_571(root=ROOT, repo=REPO)
    assert result.verified is True


def test_status_eligible() -> None:
    status = get_cutover_alias_assertion_package_after_575_status(ROOT, repo=REPO)
    assert status.eligibility == "eligible"


def test_exact_eight_alias_blockers(report: Any) -> None:
    proof = report.alias_assertion_proof
    assert proof["passed"] is True
    assert len(proof["blocker_element_ids"]) == EXPECTED_EVIDENCE_PROVENANCE_COUNT
    assert len(proof["covered_blocker_element_ids"]) == EXPECTED_PACKAGED_ALIAS_COUNT
    assert len(proof["identity_derived_blocker_element_ids"]) == EXPECTED_IDENTITY_DERIVED_ALIAS_COUNT
    assert proof["residual_count"] == 0
    assert set(proof["covered_blocker_element_ids"]) == {
        "node:node:captain-lysandra-ironveil:field:aliases",
        "node:node:thrin-branchborn:field:aliases",
    }


def test_classification_delta_is_lossless_eight(report: Any) -> None:
    delta = report.classification_delta
    assert delta["lossless"] is True
    assert delta["count"] == 8
    assert delta["packaged_count"] == 2
    assert delta["identity_derived_count"] == 6
    packaged = set(report.alias_assertion_proof["covered_blocker_element_ids"])
    history = set(report.alias_assertion_proof["identity_derived_blocker_element_ids"])
    for row in delta["transitions"]:
        previous = row["previous"]
        current = row["current"]
        assert previous["classification"] == SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP.value
        assert previous["blocker_class"] == BlockerClass.EVIDENCE_PROVENANCE.value
        assert current["blocker_class"] is None
        if row["element_id"] in packaged:
            assert current["classification"] == SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER.value
        elif row["element_id"] in history:
            assert current["classification"] == SemanticClassification.SOURCE_MIGRATION_HISTORY.value
        else:
            raise AssertionError(row["element_id"])


def test_evidence_provenance_clears(report: Any) -> None:
    for view_name in ("canonical_view", "migration_projection"):
        blockers = getattr(report, view_name)["blockers"]
        assert _blocker(blockers, BlockerClass.EVIDENCE_PROVENANCE.value) is None
        assert _blocker(blockers, BlockerClass.ATTRIBUTE_ASSERTION.value) is None


def test_history_counts_stay_separate(report: Any) -> None:
    for view_name in ("canonical_view", "migration_projection"):
        blockers = getattr(report, view_name)["blockers"]
        contribution = _blocker(blockers, BlockerClass.CONTRIBUTION_HISTORY.value)
        identity = _blocker(blockers, BlockerClass.IDENTITY_HISTORY.value)
        assert contribution is not None
        assert contribution["count"] == EXPECTED_CONTRIBUTION_HISTORY_COUNT
        assert identity is not None
        assert identity["count"] == EXPECTED_IDENTITY_HISTORY_COUNT
    for view in ("canonical", "migration"):
        changed = {row["blocker_class"] for row in report.blocker_delta[view]["rows"]}
        assert changed == {BlockerClass.EVIDENCE_PROVENANCE.value}


def test_relationships_unchanged(report: Any) -> None:
    canonical = report.canonical_view["relationship_inventory"]
    migration = report.migration_projection["relationship_inventory"]
    for key, value in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY.items():
        assert canonical[key] == value
    for key, value in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY.items():
        assert migration[key] == value
    assert set(canonical["residual_edge_ids"]) == CANONICAL_RESIDUAL_EDGE_IDS
    assert set(migration["residual_edge_ids"]) == MIGRATION_RESIDUAL_EDGE_IDS


def test_no_mutation(report: Any) -> None:
    assert report.mutation_proof["unchanged"] is True
    assert report.cutover_disposition == "CUTOVER_NOT_READY"
    assert report.next_slice_recommendation.get("case") != "CASE_B"


def test_compensating_classification_change_fails() -> None:
    packaged = {"node:a:field:aliases"}
    history = {"node:b:field:aliases"}
    previous = [
        _element(
            "node:a:field:aliases",
            classification=SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
            blocker_class=BlockerClass.EVIDENCE_PROVENANCE,
        ),
        _element(
            "node:b:field:aliases",
            classification=SemanticClassification.DUNGEONMIND_DURABILITY_CONTRACT_GAP,
            blocker_class=BlockerClass.EVIDENCE_PROVENANCE,
        ),
        _element(
            "node:unrelated:field:kind",
            classification=SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            blocker_class=None,
        ),
    ]
    current = [
        _element(
            "node:a:field:aliases",
            classification=SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
            blocker_class=None,
        ),
        _element(
            "node:b:field:aliases",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
        ),
        _element(
            "node:unrelated:field:kind",
            classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
            blocker_class=None,
        ),
    ]
    with pytest.raises(CutoverAliasAssertionPackageAfter575Error) as exc:
        build_alias_classification_delta(
            view="canonical",
            previous_elements=previous,
            current_elements=current,
            packaged_ids=packaged,
            identity_derived_ids=history,
        )
    assert exc.value.code == "classification_delta_mismatch"


def test_sealed_fixture_digest() -> None:
    digest = hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    assert digest == LOCKED_FIXTURE_SHA256
    stored = json.loads(FIXTURE_PATH.read_bytes())
    assert stored["schema"] == "dmb_cutover_alias_assertion_package_after_575_v1"
    assert stored["cutover_disposition"] == "CUTOVER_NOT_READY"
    assert stored["classification_delta"]["count"] == 8
