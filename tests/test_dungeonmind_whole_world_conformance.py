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
from graph_memory.union_supergraph.model import UnionSupergraphStore
import apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance as wwc

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
        and bucket.element_family == "edge_field"
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


def test_unknown_durable_extra_field_cannot_report_zero_unaccounted(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adversarial: extras allowed by Pydantic must not silently vanish from accounting."""
    revision_id = _publish_node(seeded_root, node_id="threat:extra", kind="threat", role="threat")
    original_load = wwc._load_exact_buddy_revision

    def _load_with_unknown_extras(*, root: Path, world_id: str, revision_id: str):
        manifest, store = original_load(root=root, world_id=world_id, revision_id=revision_id)
        payload = store.model_dump(mode="python", by_alias=True)
        first_node_id = next(iter(payload["nodes"]))
        first_edge_id = next(iter(payload["edges"])) if payload["edges"] else None
        first_artifact_id = (
            next(iter(payload["source_artifacts"])) if payload["source_artifacts"] else None
        )
        payload["nodes"][first_node_id]["unexpected_durable_node_field"] = "must-block"
        if first_edge_id is not None:
            payload["edges"][first_edge_id]["unexpected_durable_edge_field"] = "must-block"
        if first_artifact_id is not None:
            payload["source_artifacts"][first_artifact_id][
                "unexpected_durable_artifact_field"
            ] = "must-block"
        else:
            # Fixture worlds always have at least the graph-native artifact after publish.
            payload["source_artifacts"]["artifact:adversarial"] = {
                "schema_version": "dmb_source_artifact_v1",
                "source_artifact_id": "artifact:adversarial",
                "source_domain": "manual_seed",
                "campaign_id": CAMPAIGN_ID,
                "session_id": None,
                "uri": "file://adversarial",
                "content_sha256": "abc",
                "status": "active",
                "unexpected_durable_artifact_field": "must-block",
            }
        mutated = UnionSupergraphStore.model_validate(payload)
        return manifest, mutated

    monkeypatch.setattr(wwc, "_load_exact_buddy_revision", _load_with_unknown_extras)
    report = analyze_exact_buddy_world_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    assert report.unaccounted_durable_elements > 0
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    assert any(
        blocker.blocker_class.value == "SOURCE_INTEGRITY" for blocker in report.blockers
    )
    assert any(
        "unexpected_durable_node_field" in example
        for blocker in report.blockers
        if blocker.blocker_class.value == "SOURCE_INTEGRITY"
        for example in blocker.examples
    )


def test_source_domain_fields_are_classified_not_wholesale_adapters(
    seeded_root: Path,
) -> None:
    revision_id = _publish_node(seeded_root, node_id="npc:domain", kind="npc", role="ally")
    report = analyze_exact_buddy_world_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    artifact_field_buckets = [
        bucket
        for bucket in report.mapping_buckets
        if bucket.element_family == "source_artifact_field"
    ]
    assert artifact_field_buckets
    # Wholesale "source_artifact" family must not be the only accounting unit.
    assert not any(bucket.element_family == "source_artifact" for bucket in report.mapping_buckets)


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
    # Exact revision pin is source identity; current head may have advanced.
    assert head.head_revision_id is not None

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
        if bucket.element_family == "edge_field"
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
        "EVIDENCE_PROVENANCE",
    ):
        assert expected in blocker_classes

    artifact_domains = {
        row.key: row.count for row in report.artifact_source_domain_inventory
    }
    assert artifact_domains.get("recap") == 16
    assert artifact_domains.get("worldbuilding") == 4
    assert artifact_domains.get("statblock") == 3
    assert artifact_domains.get("party_registry") == 1
    assert artifact_domains.get("manual_seed") == 1

    evidence_domains = {
        row.key: row.count for row in report.evidence_source_domain_inventory
    }
    assert evidence_domains.get("recap") == 158
    assert evidence_domains.get("statblock") == 9
    assert evidence_domains.get("manual_seed") == 13

    # Field-level source/evidence accounting (not wholesale artifact rows).
    assert any(
        bucket.element_family == "source_artifact_field"
        and "session_recap" in " ".join(bucket.notes)
        for bucket in report.mapping_buckets
    )
    assert any(
        bucket.element_family == "source_artifact_field"
        and bucket.classification.value == "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
        and any("statblock" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
    )
    assert any(
        bucket.element_family == "evidence_field"
        and bucket.classification.value == "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
        and any("statblock" in note or "party_registry" in note for note in bucket.notes)
        for bucket in report.mapping_buckets
    )


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
    # Methods must be introspected from WorldGraphRepository, not a hardcoded set.
    assert seam.world_graph_repository_methods == [
        "get_head",
        "get_revision",
        "publish_revision",
        "rollback_head",
    ]
    assert "adopt" not in " ".join(seam.world_graph_repository_methods).lower()


def test_contribution_history_alone_keeps_disposition_not_ready(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Migration history must block READY even when seam is present and other gaps cleared."""
    revision_id = _publish_node(seeded_root, node_id="threat:history", kind="threat", role="threat")

    monkeypatch.setattr(
        wwc,
        "inspect_dungeonmind_durable_adoption_seam",
        lambda: wwc.DurableAdoptionSeamStatusReport(
            status="DURABLE_ADOPTION_BOUNDARY_PRESENT",
            rationale="test double: seam present for history-isolation",
            world_graph_repository_methods=["adopt_existing_world"],
            missing_public_adoption_service=False,
        ),
    )

    original_append = wwc._append_classification

    def _append_clearing_semantic_gaps(**kwargs: Any) -> None:
        classification = kwargs["classification"]
        if classification in wwc._BLOCKING_CLASSIFICATIONS:
            kwargs["classification"] = wwc.SemanticClassification.EXACTLY_REPRESENTABLE
            kwargs["blocker_class"] = None
            kwargs["note"] = "cleared for migration-history isolation"
        original_append(**kwargs)

    monkeypatch.setattr(wwc, "_append_classification", _append_clearing_semantic_gaps)

    report = analyze_exact_buddy_world_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    blocker_classes = {blocker.blocker_class.value for blocker in report.blockers}
    assert "CONTRIBUTION_HISTORY" in blocker_classes
    assert "DURABLE_ADOPTION_BOUNDARY" not in blocker_classes
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"
    # Only history should remain as the readiness gate once other gaps are cleared.
    assert all(
        blocker.blocker_class.value == "CONTRIBUTION_HISTORY" for blocker in report.blockers
    )


def test_authority_state_canonical_is_semantic_gap_not_authority_adapter(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Buddy authority_state ≠ DM SourceArtifact.authority (different semantic axes)."""
    revision_id = _publish_node(seeded_root, node_id="npc:authority", kind="npc", role="ally")
    original_load = wwc._load_exact_buddy_revision

    def _load_with_authority(*, root: Path, world_id: str, revision_id: str):
        manifest, store = original_load(root=root, world_id=world_id, revision_id=revision_id)
        payload = store.model_dump(mode="python", by_alias=True)
        if not payload["source_artifacts"]:
            payload["source_artifacts"]["artifact:authority"] = {
                "schema_version": "dmb_source_artifact_v1",
                "source_artifact_id": "artifact:authority",
                "source_domain": "manual_seed",
                "campaign_id": CAMPAIGN_ID,
                "uri": "file://authority",
                "status": "active",
                "authority_state": "canonical",
            }
        else:
            first_id = next(iter(payload["source_artifacts"]))
            payload["source_artifacts"][first_id]["authority_state"] = "canonical"
        return manifest, UnionSupergraphStore.model_validate(payload)

    monkeypatch.setattr(wwc, "_load_exact_buddy_revision", _load_with_authority)
    report = analyze_exact_buddy_world_revision(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
    )
    authority_gaps = [
        bucket
        for bucket in report.mapping_buckets
        if bucket.element_family == "source_artifact_field"
        and bucket.classification.value == "DUNGEONMIND_SEMANTIC_CONTRACT_GAP"
        and any("authority_state" in note for note in bucket.notes)
    ]
    assert authority_gaps
    assert any("evidentiary role" in note for bucket in authority_gaps for note in bucket.notes)
    assert report.disposition == "WHOLE_GRAPH_ADOPTION_NOT_READY"