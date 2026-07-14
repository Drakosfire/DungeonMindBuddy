"""Contribution source-authority digest tests (PR010A ladder Rung 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)


WORLD_ID = "eldyrwild"


@pytest.fixture
def seeded_root(tmp_path: Path):
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:baseline-seed"],
    )
    return tmp_path


def _node_contribution(*, artifact: str, node_id: str, label: str):
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=label,
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": [label],
        },
        source_artifact_id=artifact,
        identity_resolution_outcome="created_new",
    )
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id=artifact,
        source_revision_id="src-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )


def test_source_digest_stable_across_status_and_diagnostics() -> None:
    contrib = _node_contribution(
        artifact="artifact:stable",
        node_id="npc_stable",
        label="Stable",
    )
    base = kernel.compute_contribution_source_payload_sha256(contrib)
    lifecycle = contrib.model_copy(
        update={
            "status": "superseded",
            "diagnostics": [*contrib.diagnostics, "retracted:test"],
        }
    )
    assert kernel.compute_contribution_source_payload_sha256(lifecycle) == base
    full_base = kernel.compute_contribution_payload_sha256(contrib)
    full_lifecycle = kernel.compute_contribution_payload_sha256(lifecycle)
    assert full_base != full_lifecycle


def test_source_digest_changes_when_semantic_body_changes() -> None:
    contrib = _node_contribution(
        artifact="artifact:semantic",
        node_id="npc_semantic",
        label="Semantic",
    )
    base = kernel.compute_contribution_source_payload_sha256(contrib)
    mutated = contrib.model_copy(
        update={
            "accepted_assertions": [
                contrib.accepted_assertions[0].model_copy(
                    update={"label": "Semantic Changed"}
                )
            ]
        }
    )
    assert kernel.compute_contribution_source_payload_sha256(mutated) != base


def test_merge_stamps_source_digest_and_survives_supersession(seeded_root: Path) -> None:
    root = seeded_root
    first = _node_contribution(
        artifact="artifact:authority-a",
        node_id="npc_authority_a",
        label="AuthorityA",
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=first
    )
    assert merge.published is True
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    stamped = store.contribution_source_payload_sha256[first.contribution_id]
    assert stamped == kernel.compute_contribution_source_payload_sha256(first)

    replacement = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:authority-a",
        source_revision_id="src-2",
        extraction_profile="test_profile",
        accepted_assertions=[],
        supersedes_contribution_id=first.contribution_id,
    )
    superseded = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=replacement,
        superseded_contribution_id=first.contribution_id,
    )
    assert superseded.published is True
    _h2, _r2, after = kernel.open_current_world_graph(root, WORLD_ID)
    assert after.contribution_source_payload_sha256[first.contribution_id] == stamped
    assert replacement.contribution_id in after.contribution_source_payload_sha256

    rebuild = kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=False)
    assert "rebuild_equivalent_to_head" in rebuild.diagnostics


def test_initialization_authority_is_write_once(seeded_root: Path) -> None:
    root = seeded_root
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    stamped = kernel.stamp_initialization_authority(
        store,
        initialization_contribution_ids=["contribution:a"],
        initialization_plan_digest="a" * 64,
        initialization_attestation_digest="b" * 64,
    )
    same = kernel.stamp_initialization_authority(
        stamped,
        initialization_contribution_ids=["contribution:a"],
        initialization_plan_digest="a" * 64,
        initialization_attestation_digest="b" * 64,
    )
    assert same.initialization_plan_digest == "a" * 64
    with pytest.raises(ValueError, match="already established"):
        kernel.stamp_initialization_authority(
            stamped,
            initialization_contribution_ids=["contribution:a"],
            initialization_plan_digest="c" * 64,
            initialization_attestation_digest="b" * 64,
        )


def test_legacy_head_without_source_digests_requires_migration(
    seeded_root: Path,
) -> None:
    """Contributions present on a pre-authority head must migrate via rebuild."""
    root = seeded_root
    contrib = _node_contribution(
        artifact="artifact:legacy-digest",
        node_id="npc_legacy_digest",
        label="LegacyDigest",
    )
    # Simulate a legacy world: ledger+index updated without revision-bound digests.
    from graph_memory.world_supergraph.contribution_store import (
        ContributionIndex,
        save_contribution_index,
        upsert_contribution_in_index,
        write_contribution_record,
    )

    _head, revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    write_contribution_record(root, WORLD_ID, contrib)
    index = ContributionIndex(
        world_id=WORLD_ID, baseline_revision_id=revision.revision_id
    )
    index = upsert_contribution_in_index(index, contrib)
    save_contribution_index(root, WORLD_ID, index)
    assert store.contribution_source_payload_sha256 == {}

    blocked = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=_node_contribution(
            artifact="artifact:legacy-digest-b",
            node_id="npc_legacy_digest_b",
            label="LegacyDigestB",
        ),
    )
    assert blocked.published is False
    assert any(
        "contribution_source_digest_migration_required" in item
        for item in blocked.diagnostics
    )

    migrated = kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=True)
    assert migrated.published is True
    _h2, _r2, after = kernel.open_current_world_graph(root, WORLD_ID)
    assert (
        after.contribution_source_payload_sha256[contrib.contribution_id]
        == kernel.compute_contribution_source_payload_sha256(contrib)
    )

    allowed = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=_node_contribution(
            artifact="artifact:legacy-digest-c",
            node_id="npc_legacy_digest_c",
            label="LegacyDigestC",
        ),
    )
    assert allowed.published is True
