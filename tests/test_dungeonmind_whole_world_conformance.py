"""Whole Buddy World Graph → DungeonMind adoption-readiness conformance proofs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations import dungeonmind_kernel as bridge_pkg
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA,
    WholeWorldConformanceError,
    analyze_exact_buddy_world_revision,
    build_exact_dungeonmind_adoption_revision,
    inspect_dungeonmind_durable_adoption_seam,
    snapshot_world_graph_tree_digest,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)

WORLD_ID = "whole-world-conformance"
CAMPAIGN_ID = "longmont-c2"
ELDYRWILD_WORLD_ID = "eldyrwild"
ELDYRWILD_REVISION_ID = "rev:3413bf6f5044cf2680233f5e37c90dcf"
ELDYRWILD_PAYLOAD_SHA256 = (
    "346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa"
)
_CONTRIBUTION_SEQ = 0


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:whole-world-baseline"],
    )
    return tmp_path


def _contribution(*assertions: Any):
    global _CONTRIBUTION_SEQ
    _CONTRIBUTION_SEQ += 1
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:whole-world",
        source_revision_id=f"whole-world-{_CONTRIBUTION_SEQ}",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=list(assertions),
    )


def _publish_node(root: Path, *, node_id: str, kind: str, role: str) -> str:
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=f"Whole world {kind}",
        campaign_scope=CAMPAIGN_ID,
        value={"kind": kind, "role": role, "source_domains": ["manual_seed"]},
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(assertion)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _publish_edge(
    root: Path,
    *,
    edge_id: str,
    source_node_id: str,
    target_node_id: str,
    predicate: str,
) -> str:
    assertion = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        campaign_scope=CAMPAIGN_ID,
        value={"edge_id": edge_id, "direction": "outbound"},
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(assertion)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _tree_digest(root: Path, world_id: str = WORLD_ID) -> str:
    return snapshot_world_graph_tree_digest(root, world_id)


def test_unsupported_kind_fixture_is_not_ready_and_build_refuses(seeded_root: Path) -> None:
    for node_id, kind, role in (
        ("threat:whole", "threat", "threat"),
        ("npc:whole", "npc", "ally"),
        ("pc:whole", "pc", "player_character"),
        ("loc:whole", "location", "place"),
        ("fac:whole", "faction", "organization"),
        ("enc:whole", "encounter", "encounter"),
        ("cre:whole", "creature", "creature"),
        ("item:whole", "item", "object"),
    ):
        _publish_node(seeded_root, node_id=node_id, kind=kind, role=role)
    revision_id = _publish_node(seeded_root, node_id="mystery:whole", kind="mystery", role="mystery")

    report = analyze_exact_buddy_world_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    assert report.unaccounted_durable_elements == 0
    gap_kinds = {row.key for row in report.kind_inventory if row.key in {"item", "mystery"}}
    assert gap_kinds == {"item", "mystery"}

    with pytest.raises(WholeWorldConformanceError):
        build_exact_dungeonmind_adoption_revision(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
        )


def test_unsupported_predicate_fixture_is_not_ready(seeded_root: Path) -> None:
    _publish_node(seeded_root, node_id="threat:whole", kind="threat", role="threat")
    _publish_node(seeded_root, node_id="loc:whole", kind="location", role="place")
    revision_id = _publish_edge(
        seeded_root,
        edge_id="edge:threat:located_in:loc",
        source_node_id="threat:whole",
        target_node_id="loc:whole",
        predicate="located_in",
    )

    report = analyze_exact_buddy_world_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    assert report.located_in_gap_count == 1
    assert any(
        bucket.classification.value == "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
        and bucket.element_family == "edge"
        for bucket in report.mapping_buckets
    )


def test_completeness_invariant_accounts_every_durable_element(seeded_root: Path) -> None:
    revision_id = _publish_node(seeded_root, node_id="item:whole", kind="item", role="object")
    report = analyze_exact_buddy_world_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    assert report.unaccounted_durable_elements == 0
    assert report.classified_elements_count > 0
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"


def test_exact_revision_pin_does_not_read_head_after_pin(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r1 = _publish_node(seeded_root, node_id="threat:r1", kind="threat", role="threat")
    r2 = _publish_node(seeded_root, node_id="threat:r2", kind="threat", role="threat")

    def _forbidden_head(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("analyze must not consult World Graph head after revision pin")

    monkeypatch.setattr(kernel, "open_world_graph_head", _forbidden_head)

    report = analyze_exact_buddy_world_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=r1,
    )
    assert report.source_revision_id == r1
    assert report.source_revision_id != r2


def test_analyze_is_read_only_for_tmp_world(seeded_root: Path) -> None:
    revision_id = _publish_node(seeded_root, node_id="threat:whole", kind="threat", role="threat")
    before = _tree_digest(seeded_root)
    analyze_exact_buddy_world_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    after = _tree_digest(seeded_root)
    assert before == after


def test_eldyrwild_whole_world_integration_when_present() -> None:
    root = world_graph_root()
    world_root = (root / "graph_memory" / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.is_dir():
        world_root = (root / "worlds" / ELDYRWILD_WORLD_ID).resolve()
    if not world_root.is_dir():
        pytest.skip("real Eldyrwild world tree missing (CI without out/)")

    head = kernel.open_world_graph_head(root, ELDYRWILD_WORLD_ID)
    assert head is not None
    assert head.head_revision_id == ELDYRWILD_REVISION_ID

    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    report = analyze_exact_buddy_world_revision(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after

    assert report.schema_version == WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA
    assert report.source_revision_id == ELDYRWILD_REVISION_ID
    assert report.source_graph_payload_sha256 == ELDYRWILD_PAYLOAD_SHA256
    assert report.inventory["nodes"] == 438
    assert report.inventory["edges"] == 348
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    assert report.unaccounted_durable_elements == 0
    assert report.mechanics_specialization_retained is True
    assert report.durable_adoption_seam.status == "DURABLE_ADOPTION_BOUNDARY_MISSING"
    assert report.postgres_status == "BLOCKED"
    assert report.blockers

    kind_map = {row.key: row.count for row in report.kind_inventory}
    for kind, count in (
        ("item", 125),
        ("location", 103),
        ("mystery", 93),
        ("npc", 45),
        ("group", 29),
        ("faction", 13),
        ("party", 11),
        ("pc", 6),
        ("creature", 4),
        ("threat", 3),
        ("encounter", 2),
        ("event", 2),
        ("external_resource", 2),
    ):
        assert kind_map.get(kind) == count

    mapped_kind_counts = {
        row.key: row.count
        for row in report.kind_inventory
        if row.key
        in {
            "threat",
            "npc",
            "pc",
            "location",
            "faction",
            "encounter",
            "creature",
            "external_resource",
        }
    }
    assert mapped_kind_counts["threat"] == 3
    assert mapped_kind_counts["npc"] == 45

    gap_inventory = {row.key for row in report.kind_inventory if row.key in {"item", "mystery", "group", "party", "event"}}
    assert gap_inventory == {"item", "mystery", "group", "party", "event"}

    mechanics_buckets = [
        bucket
        for bucket in report.mapping_buckets
        if bucket.element_family == "edge"
        and any("uses_statblock" in note for note in bucket.notes)
    ]
    assert mechanics_buckets
    assert report.uses_statblock_mechanics_count >= 1
    assert report.located_in_gap_count >= 1

    blocker_classes = {blocker.blocker_class.value for blocker in report.blockers}
    for expected in (
        "WORLD_OBJECT_KIND",
        "RELATIONSHIP_PREDICATE",
        "DURABLE_ADOPTION_BOUNDARY",
        "CONTRIBUTION_HISTORY",
    ):
        assert expected in blocker_classes


def test_bridge_exports_still_public() -> None:
    for export in (
        "bridge_exact_buddy_world_object",
        "bridge_exact_buddy_threat",
        "map_buddy_world_object_id",
    ):
        assert export in bridge_pkg.__all__


def test_durable_adoption_seam_missing_on_current_pin() -> None:
    seam = inspect_dungeonmind_durable_adoption_seam()
    assert seam.status == "DURABLE_ADOPTION_BOUNDARY_MISSING"
    assert seam.missing_public_adoption_service is True
