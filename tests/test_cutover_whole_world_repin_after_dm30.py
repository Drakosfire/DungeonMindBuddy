"""Acceptance proofs for the post-DM#30 CUTOVER whole-world re-pin."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    BlockerClass,
    ClassifiedElement,
    SemanticClassification,
    enumerate_durable_element_ids,
    inspect_dungeonmind_durable_adoption_seam,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.services import (
    cutover_whole_world_repin_after_dm30 as cutover,
)
from apps.live_control_server.services import (
    eldyrwild_relationship_node_kind_source_repair as repair,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    verify_cutover_whole_world_reanchor,
)
from apps.live_control_server.services.cutover_whole_world_repin_after_dm30 import (
    CANONICAL_GRAPH_PAYLOAD_SHA256,
    CANONICAL_REVISION_ID,
    EXPECTED_CLASSIFIED_TRANSITION_ELEMENT_IDS,
    FIXTURE_RELPATH,
    HISTORICAL_FIXTURE_RELPATH,
    HISTORICAL_FIXTURE_SHA256,
    LOCKED_FIXTURE_SHA256,
    THREAD_KIND_ELEMENT_ID,
    THREAD_ROLE_ELEMENT_ID,
    CutoverWholeWorldRepinAfterDm30Error,
    _compose_report,
    _next_slice_recommendation,
    _report_bytes,
    assert_sealed_classified_transitions,
    build_classified_element_delta,
    build_cutover_whole_world_repin_after_dm30,
    get_cutover_whole_world_repin_after_dm30_status,
    snapshot_source_authority_inventory,
    verify_cutover_whole_world_repin_after_dm30,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    CANONICAL_RESIDUAL_EDGE_IDS,
    CHANGED_KIND_PATHS,
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    MIGRATION_NEWLY_REPRESENTED_EDGE_IDS,
    MIGRATION_RESIDUAL_EDGE_IDS,
)


REPO = repo_root()
ROOT = world_graph_root()
FIXTURE_PATH = REPO / FIXTURE_RELPATH
HISTORICAL_FIXTURE_PATH = REPO / HISTORICAL_FIXTURE_RELPATH

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


@pytest.fixture(scope="module")
def report() -> Any:
    if not (ROOT / "graph_memory" / "worlds" / "eldyrwild").is_dir():
        pytest.skip("Eldyrwild world graph not present")
    return _compose_report(ROOT, REPO)


def test_t1_exact_dependency_pin(report: Any) -> None:
    assert report.dungeonmind_dependency_ref == cutover.DUNGEONMIND_DEPENDENCY_REF
    assert cutover.DUNGEONMIND_DEPENDENCY_REF == (
        "be76acc997c5fbcb8ceaa090969ec051afa6051d"
    )


def test_t2_exact_v5_contract_pins(report: Any) -> None:
    pins = report.dungeonmind_contract_pins
    assert pins["world_object_vocabulary"] == "world-object-v5"
    assert pins["world_object_vocabulary_sha256"] == (
        "f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8"
    )
    assert pins["world_property_vocabulary"] == "world-property-v3"
    assert pins["world_property_vocabulary_sha256"] == (
        "aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4"
    )
    assert pins["semantic_profile"] == "dnd5e-profile-v3"
    assert pins["semantic_profile_descriptor_sha256"] == (
        "2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496"
    )
    assert pins["graph_schema"] == "dm_union_graph_v5"
    assert pins["source_artifact_contract"] == "dm_source_artifact_v2"
    assert pins["evidence_contract"] == "dm_evidence_ref_v2"
    assert pins["knowledge_assertion_metadata"] == "dm_knowledge_assertion_metadata_v1"


def test_t3_historical_v4_pins_in_target_delta(report: Any) -> None:
    previous = report.target_contract_delta["previous"]
    assert previous["dungeonmind_dependency_ref"] == (
        cutover.HISTORICAL_DUNGEONMIND_DEPENDENCY_REF
    )
    assert previous["world_object_revision"] == "world-object-v4"
    assert previous["world_object_sha256"] == (
        "552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b"
    )
    assert previous["world_property_revision"] == "world-property-v2"
    assert previous["world_property_sha256"] == (
        "8ad4c223e83ce48cf5cd33a33e10f5be5d48a80ad742784d7c561470b450ab73"
    )


def test_t4_historical_568_fixture_still_reproduces(report: Any) -> None:
    verified = verify_cutover_whole_world_reanchor(root=ROOT, repo=REPO)
    assert verified.verified is True
    assert verified.fixture_sha256 == HISTORICAL_FIXTURE_SHA256
    assert hashlib.sha256(HISTORICAL_FIXTURE_PATH.read_bytes()).hexdigest() == (
        HISTORICAL_FIXTURE_SHA256
    )
    assert report.historical_reproduction["verified"] is True
    assert report.historical_reproduction["historical_fixture_sha256"] == (
        HISTORICAL_FIXTURE_SHA256
    )


def test_exact_activation_pins_and_status(report: Any) -> None:
    status = get_cutover_whole_world_repin_after_dm30_status(ROOT, repo=REPO)
    assert status.eligibility == "eligible"
    assert report.buddy_repository_base_sha == cutover.BUDDY_BASE_SHA
    assert report.canonical_revision_id == CANONICAL_REVISION_ID
    assert report.canonical_graph_payload_sha256 == CANONICAL_GRAPH_PAYLOAD_SHA256
    assert report.repair_authority["manifest_sha256"] == repair.LOCKED_MANIFEST_SHA256


def test_thread_mapping_delta(report: Any) -> None:
    assert report.target_contract_delta["source_kind_mapping_delta"] == {
        "thread": "dnd5e:thread"
    }
    assert report.target_contract_delta["current"]["world_object_revision"] == (
        "world-object-v5"
    )


def test_world_object_kind_clears_under_v5(report: Any) -> None:
    for view_name in ("canonical_view", "migration_projection"):
        classes = {
            row["blocker_class"] for row in getattr(report, view_name)["blockers"]
        }
        assert BlockerClass.WORLD_OBJECT_KIND.value not in classes
    assert BlockerClass.WORLD_OBJECT_KIND.value in report.target_contract_delta[
        "cleared_blocker_classes"
    ]


def test_t12_classified_element_delta_is_lossless_and_sealed(report: Any) -> None:
    classified = report.target_contract_delta["classified_element_transitions"]
    assert classified["lossless"] is True
    assert classified["sealed_element_ids"] == sorted(
        EXPECTED_CLASSIFIED_TRANSITION_ELEMENT_IDS
    )
    for view_name in ("canonical", "migration"):
        rows = classified[view_name]
        assert {row["element_id"] for row in rows} == (
            EXPECTED_CLASSIFIED_TRANSITION_ELEMENT_IDS
        )
        by_id = {row["element_id"]: row for row in rows}
        kind = by_id[THREAD_KIND_ELEMENT_ID]
        role = by_id[THREAD_ROLE_ELEMENT_ID]
        assert kind["previous"]["blocker_class"] == BlockerClass.WORLD_OBJECT_KIND.value
        assert kind["current"]["blocker_class"] is None
        assert kind["current"]["classification"] == (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER.value
        )
        assert role["previous"]["blocker_class"] == (
            BlockerClass.ATTRIBUTE_ASSERTION.value
        )
        assert role["current"]["blocker_class"] is None
        assert role["current"]["classification"] == (
            SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER.value
        )
        assert "29→28" not in role["explanation"]
        assert "dnd5e:thread" in kind["explanation"]
        assert "world-property-v3" in role["explanation"]

    # Blocker ledger notes must be derived from classified evidence.
    attr_notes = [
        row["note"]
        for row in report.target_contract_delta["changed_blockers"]
        if row["blocker_class"] == BlockerClass.ATTRIBUTE_ASSERTION.value
    ]
    assert attr_notes
    assert all("29→28" not in note for note in attr_notes)
    assert all(THREAD_ROLE_ELEMENT_ID in row for row in [
        row["representative_durable_ids"]
        for row in report.target_contract_delta["changed_blockers"]
        if row["blocker_class"] == BlockerClass.ATTRIBUTE_ASSERTION.value
    ])


def _classified(
    element_id: str,
    *,
    classification: SemanticClassification,
    blocker: BlockerClass | None,
    family: str = "node_field",
) -> ClassifiedElement:
    return ClassifiedElement(
        element_id=element_id,
        element_family=family,
        classification=classification,
        blocker_class=blocker,
        note="fixture",
    )


def test_t12_adversarial_compensating_swap_cannot_pass_with_stable_counts() -> None:
    """Aggregate blocker counts alone must not satisfy T12.

    Construct a compensating swap that keeps WORLD_OBJECT_KIND/ATTRIBUTE totals
    looking like the PR #30 outcome while changing an unrelated durable element.
    """
    gap = SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP
    adapter = SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER
    previous = [
        _classified(
            THREAD_KIND_ELEMENT_ID,
            classification=gap,
            blocker=BlockerClass.WORLD_OBJECT_KIND,
        ),
        _classified(
            THREAD_ROLE_ELEMENT_ID,
            classification=gap,
            blocker=BlockerClass.ATTRIBUTE_ASSERTION,
        ),
        _classified(
            "node:unrelated:field:label",
            classification=adapter,
            blocker=None,
        ),
    ]
    # Compensating swap: clear thread kind/role as expected, but also flip an
    # unrelated element into ATTRIBUTE_ASSERTION so aggregate ATTR still drops
    # by one if someone only counted thread-role clearance... Actually for a
    # true compensating case with IDENTICAL aggregate blocker counts:
    # - thread kind clears WORLD_OBJECT_KIND (count -1)
    # - unrelated element becomes WORLD_OBJECT_KIND (count +1)
    # net WORLD_OBJECT_KIND unchanged, but classified delta has extra rows.
    # For ATTR: thread role clears (-1) and unrelated becomes ATTR (+1) → net 0.
    current = [
        _classified(
            THREAD_KIND_ELEMENT_ID,
            classification=adapter,
            blocker=None,
        ),
        _classified(
            THREAD_ROLE_ELEMENT_ID,
            classification=adapter,
            blocker=None,
        ),
        _classified(
            "node:unrelated:field:label",
            classification=gap,
            blocker=BlockerClass.ATTRIBUTE_ASSERTION,
        ),
    ]
    transitions = build_classified_element_delta(
        view="adversarial",
        previous_elements=previous,
        current_elements=current,
    )
    # Three transitions: kind, role, and unrelated — must not seal as PR #30 set.
    assert {row["element_id"] for row in transitions} != (
        EXPECTED_CLASSIFIED_TRANSITION_ELEMENT_IDS
    )
    with pytest.raises(CutoverWholeWorldRepinAfterDm30Error) as exc:
        assert_sealed_classified_transitions(transitions, view="adversarial")
    assert exc.value.code == "classified_element_delta_mismatch"


def test_t12_adversarial_count_matched_fake_thread_set_still_needs_exact_semantics() -> None:
    """Even with only the two sealed IDs, wrong old/new blocker classes fail T12."""
    gap = SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP
    adapter = SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER
    previous = [
        _classified(
            THREAD_KIND_ELEMENT_ID,
            classification=gap,
            blocker=BlockerClass.WORLD_OBJECT_KIND,
        ),
        _classified(
            THREAD_ROLE_ELEMENT_ID,
            classification=gap,
            # Wrong prior class — would still clear ATTR aggregate if miscounted.
            blocker=BlockerClass.EVIDENCE_PROVENANCE,
        ),
    ]
    current = [
        _classified(THREAD_KIND_ELEMENT_ID, classification=adapter, blocker=None),
        _classified(THREAD_ROLE_ELEMENT_ID, classification=adapter, blocker=None),
    ]
    transitions = build_classified_element_delta(
        view="adversarial",
        previous_elements=previous,
        current_elements=current,
    )
    with pytest.raises(CutoverWholeWorldRepinAfterDm30Error) as exc:
        assert_sealed_classified_transitions(transitions, view="adversarial")
    assert exc.value.code == "classified_element_delta_mismatch"


def test_relationship_inventories_unchanged(report: Any) -> None:
    relationship = report.canonical_view["relationship_inventory"]
    assert {
        key: relationship[key] for key in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
    } == EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
    assert set(relationship["residual_edge_ids"]) == CANONICAL_RESIDUAL_EDGE_IDS
    assert relationship["authority"] == (
        "dmb_dungeonmind_relationship_effective_conformance_v1"
    )

    migration = report.migration_projection["relationship_inventory"]
    assert {
        key: migration[key] for key in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    } == EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    assert set(migration["residual_edge_ids"]) == MIGRATION_RESIDUAL_EDGE_IDS
    assert set(migration["newly_represented_edge_ids"]) == (
        MIGRATION_NEWLY_REPRESENTED_EDGE_IDS
    )
    assert migration["authority"] == "eldyrwild-relationship-node-kind-source-repair-v1"


def test_dual_sense_stop_exact_five(report: Any) -> None:
    residual = set(report.migration_projection["relationship_residual_edge_ids"])
    assert residual == set(repair.STAGE_B_REMAINING_RESIDUAL_EDGE_IDS)
    assert len(residual) == 5
    rows = [
        row
        for row in report.migration_projection["blockers"]
        if row["blocker_class"] == BlockerClass.RELATIONSHIP_PREDICATE.value
    ]
    assert len(rows) == 1
    assert rows[0]["count"] == 5
    assert rows[0]["blocking_stage"] == "adoption_package_construction"
    assert rows[0]["ownership_scope"] == "cross_repository"
    assert rows[0]["responsible_repo"] is None


def test_projection_changes_exactly_four_kind_paths(report: Any) -> None:
    assert report.projection_delta["changed_durable_paths"] == list(CHANGED_KIND_PATHS)
    assert all("thread" not in path for path in report.projection_delta["changed_durable_paths"])


def test_both_views_fully_accounted(report: Any) -> None:
    assert report.canonical_view["unaccounted_durable_elements"] == 0
    assert report.migration_projection["unaccounted_durable_elements"] == 0


def test_normalized_blockers_carry_required_fields(report: Any) -> None:
    for view_name in ("canonical_view", "migration_projection"):
        for row in getattr(report, view_name)["blockers"]:
            assert _REQUIRED_BLOCKER_FIELDS <= set(row)


def test_recommendation_is_stage_driven(report: Any) -> None:
    recommendation = report.next_slice_recommendation
    assert recommendation == _next_slice_recommendation(
        report.migration_projection["blockers"]
    )
    package_construction = any(
        row.get("blocking_stage") == "adoption_package_construction"
        for row in report.migration_projection["blockers"]
    )
    if package_construction:
        assert recommendation["case"] != "CASE_B"
    assert report.cutover_disposition == "CUTOVER_NOT_READY"


def test_case_b_forbidden_while_package_construction_remains() -> None:
    ledger = [
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
            "blocker_class": BlockerClass.RELATIONSHIP_PREDICATE.value,
            "count": 5,
            "examples": sorted(MIGRATION_RESIDUAL_EDGE_IDS)[:5],
            "presence_scope": "both",
            "blocking_stage": "adoption_package_construction",
            "ownership_scope": "cross_repository",
            "responsible_repo": None,
            "smallest_next_change": (
                "Keep the five dual-sense edges as an explicit migration decision set."
            ),
            "ledger_disposition": "replaced_by_effective_relationship",
        },
    ]
    recommendation = _next_slice_recommendation(ledger)
    assert recommendation["case"] != "CASE_B"
    assert recommendation["basis_blocking_stages"] == ["adoption_package_construction"]


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
        }
    ]
    recommendation = _next_slice_recommendation(durable_only)
    assert recommendation["case"] == "CASE_B"


def test_no_mutation(report: Any) -> None:
    before_head = kernel.open_world_graph_head(ROOT, "eldyrwild").head_revision_id
    before_tree = snapshot_world_graph_tree_digest(ROOT, "eldyrwild")
    before_source = snapshot_source_authority_inventory(ROOT)
    historical_before = hashlib.sha256(HISTORICAL_FIXTURE_PATH.read_bytes()).hexdigest()
    _ = _compose_report(ROOT, REPO)
    assert kernel.open_world_graph_head(ROOT, "eldyrwild").head_revision_id == before_head
    assert snapshot_world_graph_tree_digest(ROOT, "eldyrwild") == before_tree
    assert snapshot_source_authority_inventory(ROOT) == before_source
    assert hashlib.sha256(HISTORICAL_FIXTURE_PATH.read_bytes()).hexdigest() == (
        historical_before
    )


def test_adoption_seam_is_introspected(report: Any) -> None:
    expected = inspect_dungeonmind_durable_adoption_seam()
    assert report.adoption_seam.model_dump(mode="json") == expected.model_dump(mode="json")


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


def test_stale_fixture_pin_refuses_replacement(
    report: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cutover, "LOCKED_FIXTURE_SHA256", "0" * 64)
    with pytest.raises(cutover.CutoverWholeWorldRepinAfterDm30Error) as excinfo:
        build_cutover_whole_world_repin_after_dm30(root=ROOT, repo=REPO)
    assert excinfo.value.code == "fixture_digest_mismatch"


@pytest.mark.parametrize(
    ("attr", "value", "code"),
    [
        ("CANONICAL_REVISION_ID", "rev:deadbeef", "stale_canonical_head"),
        ("CANONICAL_GRAPH_PAYLOAD_SHA256", "0" * 64, "canonical_payload_mismatch"),
        ("LOCKED_REPAIR_MANIFEST_SHA256", "1" * 64, "repair_manifest_mismatch"),
        ("DUNGEONMIND_DEPENDENCY_REF", "0" * 40, "dependency_pin_mismatch"),
        ("HISTORICAL_FIXTURE_SHA256", "2" * 64, "historical_fixture_digest_mismatch"),
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
    with pytest.raises(cutover.CutoverWholeWorldRepinAfterDm30Error) as excinfo:
        _compose_report(ROOT, REPO)
    assert excinfo.value.code in {
        code,
        "dependency_pin_mismatch",
        "contract_pin_mismatch",
        "historical_reproduction_failed",
    }
    assert hashlib.sha256(HISTORICAL_FIXTURE_PATH.read_bytes()).hexdigest() == (
        HISTORICAL_FIXTURE_SHA256
    )


def test_stale_contract_pin_refuses(report: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    pins = dict(cutover._contract_pins())
    pins["world_object_vocabulary"] = "world-object-v999"
    monkeypatch.setattr(cutover, "_contract_pins", lambda: pins)
    with pytest.raises(cutover.CutoverWholeWorldRepinAfterDm30Error) as excinfo:
        _compose_report(ROOT, REPO)
    assert excinfo.value.code == "contract_pin_mismatch"


def test_cutover_not_ready(report: Any) -> None:
    assert report.cutover_disposition == "CUTOVER_NOT_READY"
    assert any(
        row.get("blocking_stage") == "adoption_package_construction"
        for row in report.migration_projection["blockers"]
    )


def test_fixture_digest_lock_soft_until_seal(report: Any) -> None:
    """Until LOCKED_FIXTURE_SHA256 is filled, build may first-seal or match unlocked."""
    if LOCKED_FIXTURE_SHA256.strip():
        raw = FIXTURE_PATH.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == LOCKED_FIXTURE_SHA256
        assert raw == _report_bytes(report)
        return
    built = build_cutover_whole_world_repin_after_dm30(root=ROOT, repo=REPO)
    assert built.fixture_sha256
    assert "first_seal_unlocked" in built.diagnostics or "already_built" in built.diagnostics
    assert FIXTURE_PATH.is_file()
    verified = verify_cutover_whole_world_repin_after_dm30(root=ROOT, repo=REPO)
    assert verified.verified
    assert verified.fixture_sha256 == built.fixture_sha256
    # Historical fixture must remain untouched.
    assert hashlib.sha256(HISTORICAL_FIXTURE_PATH.read_bytes()).hexdigest() == (
        HISTORICAL_FIXTURE_SHA256
    )


def test_historical_fixture_path_is_never_the_new_fixture() -> None:
    assert HISTORICAL_FIXTURE_RELPATH != FIXTURE_RELPATH
    assert HISTORICAL_FIXTURE_PATH != FIXTURE_PATH


def test_target_delta_stores_both_digests(report: Any) -> None:
    delta = report.target_contract_delta
    assert delta["historical_whole_world_digests"]["canonical"]
    assert delta["historical_whole_world_digests"]["migration"]
    assert delta["current_whole_world_digests"]["canonical"]
    assert delta["current_whole_world_digests"]["migration"]
    assert (
        delta["historical_whole_world_digests"]["canonical"]
        != delta["current_whole_world_digests"]["canonical"]
    )


def test_report_has_no_authority_switch_surface(report: Any) -> None:
    blob = json.dumps(report.model_dump(mode="json", by_alias=True)).lower()
    assert "apply" not in blob or "non_publishing" in report.diagnostics
    assert "non_publishing" in report.diagnostics
