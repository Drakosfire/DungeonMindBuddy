"""Contribution merge / supersession / retraction tests (PR005)."""

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
def fixture_store():
    return load_union_supergraph_store(DEFAULT_FIXTURE_PATH)


@pytest.fixture
def seeded_root(tmp_path: Path, fixture_store):
    result = kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:baseline-seed"],
    )
    return tmp_path, result.revision.revision_id


def _node_assertion(
    *,
    node_id: str,
    label: str,
    source_artifact_id: str,
    source_revision_id: str = "src-rev-1",
):
    return kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=label,
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": [label],
            "canon_state": "canonical",
        },
        evidence_ref_ids=[],
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )


def _mireward_assertion(
    *,
    source_domain: str,
    source_artifact_id: str,
    source_revision_id: str,
    evidence_ref_id: str,
):
    evidence = {
        "evidence_ref_id": evidence_ref_id,
        "source_artifact_id": source_artifact_id,
        "source_domain": source_domain,
    }
    if source_domain == "recap":
        evidence.update(
            {
                "session_id": "session-23",
                "source_span_ref_id": f"span:{evidence_ref_id}",
            }
        )
    return kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="location:mireward",
        label="Mireward",
        value={
            "kind": "location",
            "role": "town",
            "aliases": ["Mireward"],
            "source_domains": [source_domain],
            "evidence": [evidence],
            "canon_state": "canonical",
        },
        evidence_ref_ids=[evidence_ref_id],
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome=(
            "created_new" if source_domain == "worldbuilding" else "resolved_existing"
        ),
    )


def test_merge_contribution_publishes_world_revision(seeded_root) -> None:
    root, parent = seeded_root
    assertion = _node_assertion(
        node_id="npc_hester",
        label="Hester",
        source_artifact_id="artifact:authored:hester",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:authored:hester",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        campaign_scope="longmont-c2",
        accepted_assertions=[assertion],
    )
    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )
    assert result.published is True
    assert result.revision_id is not None
    assert result.parent_revision_id == parent
    assert contribution.contribution_id in result.contribution_ids

    head, revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert head.head_revision_id == result.revision_id
    assert revision.parent_revision_id == parent
    assert contribution.contribution_id in revision.operation_ids
    assert "npc_hester" in store.nodes
    assert store.nodes["npc_hester"].label == "Hester"


def test_failed_contribution_merge_leaves_prior_head_readable(seeded_root) -> None:
    root, parent = seeded_root
    # Edge endpoints do not exist → merge fails validation/value error path.
    assertion = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id="missing_a",
        target_node_id="missing_b",
        predicate="related_to",
        label="related to",
        value={},
        identity_resolution_outcome="created_new",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:bad",
        source_revision_id="src-rev-bad",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert result.published is False
    assert result.revision_id is None
    assert any("merge_failed" in d for d in result.diagnostics)

    head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert head.head_revision_id == parent
    assert "missing_a" not in store.nodes


def test_direct_merge_rekeys_stale_assertion_before_persistence(seeded_root) -> None:
    root, _ = seeded_root
    assertion = _node_assertion(
        node_id="npc_rekeyed",
        label="Rekeyed",
        source_artifact_id="artifact:rekeyed",
    ).model_copy(update={"assertion_id": "assertion:stale"})
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:rekeyed",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[],
    ).model_copy(update={"accepted_assertions": [assertion]})

    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )

    assert result.published is True
    assert any(d.startswith("assertion_identity_rekeyed:") for d in result.diagnostics)
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert assertion.assertion_id not in store.assertion_support
    assert result.accepted_assertion_ids[0] in store.assertion_support


def test_idempotent_reprocessing_does_not_duplicate_graph_state(seeded_root) -> None:
    root, _parent = seeded_root
    assertion = _node_assertion(
        node_id="npc_willow",
        label="Willow",
        source_artifact_id="artifact:willow",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:willow",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    first = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert first.published is True
    _head, _rev, store_after_first = kernel.open_current_world_graph(root, WORLD_ID)
    node_count = len(store_after_first.nodes)
    edge_count = len(store_after_first.edges)
    support = store_after_first.assertion_support[assertion.assertion_id]
    assert support["active_contribution_ids"] == [contribution.contribution_id]

    second = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert second.published is False
    assert any("idempotent_noop" in d for d in second.diagnostics)

    _head2, _rev2, store_after_second = kernel.open_current_world_graph(root, WORLD_ID)
    assert len(store_after_second.nodes) == node_count
    assert len(store_after_second.edges) == edge_count
    support2 = store_after_second.assertion_support[assertion.assertion_id]
    assert support2["active_contribution_ids"] == [contribution.contribution_id]


def test_superseded_contribution_retracts_only_unsupported_assertions(
    seeded_root,
) -> None:
    root, _ = seeded_root
    assertion_x = _node_assertion(
        node_id="npc_x",
        label="X",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-a",
    )
    assertion_y = _node_assertion(
        node_id="npc_y",
        label="Y",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-a",
    )
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-a",
        extraction_profile="test_profile",
        accepted_assertions=[assertion_x, assertion_y],
    )
    merge_a = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_a
    )
    assert merge_a.published is True

    assertion_x_b = _node_assertion(
        node_id="npc_x",
        label="X",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-b",
    )
    contrib_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:lineage",
        source_revision_id="src-rev-b",
        extraction_profile="test_profile",
        accepted_assertions=[assertion_x_b],
        supersedes_contribution_id=contrib_a.contribution_id,
    )
    result = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=contrib_b,
        superseded_contribution_id=contrib_a.contribution_id,
    )
    assert result.published is True
    assert contrib_a.contribution_id in result.superseded_contribution_ids

    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    support_x = store.assertion_support[assertion_x.assertion_id]
    support_y = store.assertion_support[assertion_y.assertion_id]
    assert support_x["support_state"] == "supported"
    assert contrib_b.contribution_id in support_x["active_contribution_ids"]
    assert support_y["support_state"] in {"unsupported", "retracted"}
    assert support_y["active_contribution_ids"] == []
    assert "npc_x" in store.nodes
    assert store.nodes["npc_y"].state.get("support_state") in {
        "unsupported",
        "retracted",
    }


def test_multi_source_support_preserves_assertion_after_one_retraction(
    seeded_root,
) -> None:
    root, _ = seeded_root
    assertion = _node_assertion(
        node_id="npc_shared",
        label="Shared",
        source_artifact_id="artifact:shared-a",
    )
    # Same assertion content → same assertion_id from both contributions.
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:shared-a",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    contrib_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:shared-b",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    assert contrib_a.contribution_id != contrib_b.contribution_id

    kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_a
    )
    kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_b
    )

    retract = kernel.retract_graph_contribution(
        root,
        world_id=WORLD_ID,
        contribution_id=contrib_a.contribution_id,
        reason="source a withdrawn",
    )
    assert retract.published is True

    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    support = store.assertion_support[assertion.assertion_id]
    assert support["support_state"] == "supported"
    assert contrib_b.contribution_id in support["active_contribution_ids"]
    assert contrib_a.contribution_id not in support["active_contribution_ids"]
    assert "npc_shared" in store.nodes
    assert (
        store.nodes["npc_shared"].state.get("memory_state") != "unsupported_assertion"
    )


def test_heterogeneous_provenance_support_survives_retraction_and_supersession(
    seeded_root,
) -> None:
    root, _ = seeded_root
    worldbuilding = _mireward_assertion(
        source_domain="worldbuilding",
        source_artifact_id="artifact:mireward:worldbuilding",
        source_revision_id="worldbuilding:1",
        evidence_ref_id="evidence:mireward:worldbuilding",
    )
    recap = _mireward_assertion(
        source_domain="recap",
        source_artifact_id="artifact:mireward:recap",
        source_revision_id="recap:1",
        evidence_ref_id="evidence:mireward:recap:1",
    )
    assert worldbuilding.assertion_id == recap.assertion_id
    contribution_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:worldbuilding",
        source_revision_id="worldbuilding:1",
        accepted_assertions=[worldbuilding],
    )
    contribution_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:recap",
        source_revision_id="recap:1",
        accepted_assertions=[recap],
    )
    kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution_a
    )
    kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution_b
    )

    retracted = kernel.retract_graph_contribution(
        root,
        world_id=WORLD_ID,
        contribution_id=contribution_a.contribution_id,
        reason="worldbuilding source withdrawn",
    )
    assert retracted.published is True
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    support = store.assertion_support[worldbuilding.assertion_id]
    assert support["support_state"] == "supported"
    assert support["active_contribution_ids"] == [contribution_b.contribution_id]
    assert contribution_a.contribution_id in support["retracted_contribution_ids"]
    assert "location:mireward" in store.nodes

    recap_replacement = _mireward_assertion(
        source_domain="recap",
        source_artifact_id="artifact:mireward:recap",
        source_revision_id="recap:2",
        evidence_ref_id="evidence:mireward:recap:2",
    )
    contribution_b2 = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:recap",
        source_revision_id="recap:2",
        accepted_assertions=[recap_replacement],
        supersedes_contribution_id=contribution_b.contribution_id,
    )
    superseded = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=contribution_b2,
        superseded_contribution_id=contribution_b.contribution_id,
    )
    assert superseded.published is True

    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    mireward_supports = [
        support
        for support in store.assertion_support.values()
        if support["graph_object_id"] == "location:mireward"
    ]
    assert len(mireward_supports) == 1
    support = mireward_supports[0]
    assert support["active_contribution_ids"] == [contribution_b2.contribution_id]
    assert contribution_b.contribution_id in support["superseded_contribution_ids"]
    assert "location:mireward" in store.nodes


def _legacy_assertion_id(
    *,
    assertion_kind: str,
    subject_node_id: str | None,
    target_node_id: str | None,
    predicate: str | None,
    label: str | None,
    value: dict,
    campaign_scope: str | None,
    temporal_scope: dict | None,
    epistemic_kind: str | None,
    visibility: str | None,
) -> str:
    import hashlib
    import json

    payload = {
        "assertion_kind": assertion_kind,
        "subject_node_id": subject_node_id,
        "target_node_id": target_node_id,
        "predicate": predicate,
        "label": label,
        "value": value,
        "campaign_scope": campaign_scope,
        "temporal_scope": temporal_scope,
        "epistemic_kind": epistemic_kind,
        "visibility": visibility,
    }
    digest = hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"assertion:{digest}"


def _with_legacy_assertion_id(assertion):
    return assertion.model_copy(
        update={
            "assertion_id": _legacy_assertion_id(
                assertion_kind=assertion.assertion_kind,
                subject_node_id=assertion.subject_node_id,
                target_node_id=assertion.target_node_id,
                predicate=assertion.predicate,
                label=assertion.label,
                value=assertion.value,
                campaign_scope=assertion.campaign_scope,
                temporal_scope=assertion.temporal_scope,
                epistemic_kind=assertion.epistemic_kind,
                visibility=assertion.visibility,
            )
        }
    )


def _seed_active_legacy_contribution(root: Path, contribution):
    """Persist a pre-repair contribution and publish its legacy support into head."""
    from graph_memory.kernel.contribution_merge import apply_accepted_assertions
    from graph_memory.world_supergraph.contribution_store import (
        # PR003_INTERNAL_GRAPH_KERNEL_EXEMPTION: test-local legacy head fixture.
        ContributionIndex,
        load_contribution_index,
        save_contribution_index,
        upsert_contribution_in_index,
        write_contribution_record,
    )

    path = write_contribution_record(root, WORLD_ID, contribution)
    original_bytes = path.read_bytes()
    _head, baseline, _store = kernel.open_current_world_graph(root, WORLD_ID)
    index = load_contribution_index(root, WORLD_ID)
    if index.baseline_revision_id is None:
        index = ContributionIndex(
            world_id=WORLD_ID, baseline_revision_id=baseline.revision_id
        )
    index = upsert_contribution_in_index(index, contribution)
    save_contribution_index(root, WORLD_ID, index)

    head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    proposed, _support, _accepted = apply_accepted_assertions(store, contribution)
    kernel.publish_world_graph_revision(
        root,
        WORLD_ID,
        proposed,
        operation_ids=[contribution.contribution_id],
        expected_parent_revision_id=head.head_revision_id,
    )
    return path, original_bytes


def test_legacy_active_contribution_remerge_fails_closed(seeded_root) -> None:
    root, _parent = seeded_root
    assertion = _with_legacy_assertion_id(
        _mireward_assertion(
            source_domain="worldbuilding",
            source_artifact_id="artifact:mireward:legacy",
            source_revision_id="worldbuilding:legacy-1",
            evidence_ref_id="evidence:mireward:legacy",
        )
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:legacy",
        source_revision_id="worldbuilding:legacy-1",
        accepted_assertions=[assertion],
    ).model_copy(update={"accepted_assertions": [assertion]})
    path, original_bytes = _seed_active_legacy_contribution(root, contribution)

    before_head, _before_rev, before_store = kernel.open_current_world_graph(
        root, WORLD_ID
    )
    assert assertion.assertion_id in before_store.assertion_support

    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )

    assert result.published is False
    assert result.revision_id is None
    assert "assertion_identity_migration_required" in result.diagnostics
    assert path.read_bytes() == original_bytes

    after_head, _after_rev, after_store = kernel.open_current_world_graph(
        root, WORLD_ID
    )
    assert after_head.head_revision_id == before_head.head_revision_id
    assert set(after_store.assertion_support) == set(before_store.assertion_support)
    assert assertion.assertion_id in after_store.assertion_support
    current_id = kernel.compute_assertion_id(
        assertion_kind=assertion.assertion_kind,
        subject_node_id=assertion.subject_node_id,
        target_node_id=assertion.target_node_id,
        predicate=assertion.predicate,
        label=assertion.label,
        value=assertion.value,
        campaign_scope=assertion.campaign_scope,
        temporal_scope=assertion.temporal_scope,
        epistemic_kind=assertion.epistemic_kind,
        visibility=assertion.visibility,
    )
    assert current_id != assertion.assertion_id
    assert current_id not in after_store.assertion_support


def test_legacy_active_contribution_supersession_fails_closed(seeded_root) -> None:
    root, _ = seeded_root
    legacy_assertion = _with_legacy_assertion_id(
        _mireward_assertion(
            source_domain="worldbuilding",
            source_artifact_id="artifact:mireward:legacy-super",
            source_revision_id="worldbuilding:legacy-super-1",
            evidence_ref_id="evidence:mireward:legacy-super",
        )
    )
    legacy = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:legacy-super",
        source_revision_id="worldbuilding:legacy-super-1",
        accepted_assertions=[legacy_assertion],
    ).model_copy(update={"accepted_assertions": [legacy_assertion]})
    path, original_bytes = _seed_active_legacy_contribution(root, legacy)

    replacement_assertion = _mireward_assertion(
        source_domain="worldbuilding",
        source_artifact_id="artifact:mireward:legacy-super",
        source_revision_id="worldbuilding:legacy-super-2",
        evidence_ref_id="evidence:mireward:legacy-super-2",
    )
    replacement = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:legacy-super",
        source_revision_id="worldbuilding:legacy-super-2",
        accepted_assertions=[replacement_assertion],
        supersedes_contribution_id=legacy.contribution_id,
    )
    before_head, _before_rev, before_store = kernel.open_current_world_graph(
        root, WORLD_ID
    )

    result = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=replacement,
        superseded_contribution_id=legacy.contribution_id,
    )

    assert result.published is False
    assert result.revision_id is None
    assert "assertion_identity_migration_required" in result.diagnostics
    assert path.read_bytes() == original_bytes
    from graph_memory.world_supergraph.paths import contribution_path

    assert not contribution_path(
        root, WORLD_ID, replacement.contribution_id
    ).exists()

    after_head, _after_rev, after_store = kernel.open_current_world_graph(
        root, WORLD_ID
    )
    assert after_head.head_revision_id == before_head.head_revision_id
    assert legacy_assertion.assertion_id in after_store.assertion_support
    assert set(after_store.assertion_support) == set(before_store.assertion_support)


def _edge_assertion(
    *,
    source_domain: str,
    source_artifact_id: str,
    source_revision_id: str,
    evidence_ref_id: str,
):
    evidence = {
        "evidence_ref_id": evidence_ref_id,
        "source_artifact_id": source_artifact_id,
        "source_domain": source_domain,
    }
    if source_domain == "recap":
        evidence.update(
            {
                "session_id": "session-23",
                "source_span_ref_id": f"span:{evidence_ref_id}",
            }
        )
    return kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id="pc_caelynn",
        target_node_id="loc_mirathorn",
        predicate="scouted",
        label="scouted",
        value={
            "edge_id": "edge:pc_caelynn:scouted:loc_mirathorn",
            "source_node_id": "pc_caelynn",
            "target_node_id": "loc_mirathorn",
            "predicate": "scouted",
            "source_domains": [source_domain],
            "evidence": [evidence],
            "canon_state": "canonical",
        },
        evidence_ref_ids=[evidence_ref_id],
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome=(
            "created_new" if source_domain == "worldbuilding" else "resolved_existing"
        ),
    )


def test_heterogeneous_provenance_edge_unions_domains_and_survives_retraction(
    seeded_root,
) -> None:
    root, _ = seeded_root
    worldbuilding = _edge_assertion(
        source_domain="worldbuilding",
        source_artifact_id="artifact:edge:worldbuilding",
        source_revision_id="worldbuilding:edge-1",
        evidence_ref_id="evidence:edge:worldbuilding",
    )
    recap = _edge_assertion(
        source_domain="recap",
        source_artifact_id="artifact:edge:recap",
        source_revision_id="recap:edge-1",
        evidence_ref_id="evidence:edge:recap",
    )
    assert worldbuilding.assertion_id == recap.assertion_id

    contribution_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:edge:worldbuilding",
        source_revision_id="worldbuilding:edge-1",
        accepted_assertions=[worldbuilding],
    )
    contribution_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:edge:recap",
        source_revision_id="recap:edge-1",
        accepted_assertions=[recap],
    )
    kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution_a
    )
    kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution_b
    )

    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    edge_id = "edge:pc_caelynn:scouted:loc_mirathorn"
    assert edge_id in store.edges
    assert list(store.edges).count(edge_id) == 1
    edge = store.edges[edge_id]
    assert set(edge.source_domains) == {"worldbuilding", "recap"}

    supports = [
        support
        for support in store.assertion_support.values()
        if support["graph_object_id"] == edge_id
    ]
    assert len(supports) == 1
    support = supports[0]
    assert support["assertion_id"] == worldbuilding.assertion_id
    assert set(support["active_contribution_ids"]) == {
        contribution_a.contribution_id,
        contribution_b.contribution_id,
    }
    assert set(support["source_artifact_ids"]) == {
        "artifact:edge:worldbuilding",
        "artifact:edge:recap",
    }
    assert set(support["evidence_ref_ids"]) == {
        "evidence:edge:worldbuilding",
        "evidence:edge:recap",
    }

    retracted = kernel.retract_graph_contribution(
        root,
        world_id=WORLD_ID,
        contribution_id=contribution_a.contribution_id,
        reason="worldbuilding edge withdrawn",
    )
    assert retracted.published is True
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert edge_id in store.edges
    support = store.assertion_support[worldbuilding.assertion_id]
    assert support["support_state"] == "supported"
    assert support["active_contribution_ids"] == [contribution_b.contribution_id]
    assert contribution_a.contribution_id in support["retracted_contribution_ids"]


def test_graph_review_authored_assertion_uses_same_merge_path(seeded_root) -> None:
    root, _ = seeded_root
    assertion = _node_assertion(
        node_id="npc_authored",
        label="Authored NPC",
        source_artifact_id="artifact:graph-review:authored",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:graph-review:authored",
        source_revision_id="authored-1",
        extraction_profile=None,
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    assert contribution.source_kind == "graph_review_authored_assertion"
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert result.published is True
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    node = store.nodes["npc_authored"]
    assert (
        node.state.get("introduced_by_contribution_id") == contribution.contribution_id
    )
    support = store.assertion_support[assertion.assertion_id]
    assert support["introduced_by_contribution_id"] == contribution.contribution_id


def test_ambiguous_identity_contribution_does_not_enter_canonical_graph(
    seeded_root,
) -> None:
    root, parent = seeded_root
    mention = kernel.ContributionIdentityMention(
        mention_id="mention:hester",
        label="Hester",
        object_kind="npc",
        identity_resolution_outcome="ambiguous",
        diagnostics=["multiple plausible matches"],
        candidate_node_ids=["npc_a", "npc_b"],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:ambiguous",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[],
        unresolved_mentions=[mention],
        diagnostics=["ambiguous candidate retained"],
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert result.published is True
    assert any("ambiguous" in d for d in result.diagnostics)
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert "mention:hester" not in store.nodes
    assert all(nid != "mention:hester" for nid in store.nodes)
    # No new canonical node from the ambiguous mention.
    assert "npc_hester" not in store.nodes


def test_blocked_collision_contribution_does_not_merge(seeded_root) -> None:
    root, parent = seeded_root
    # Accepted assertion marked with blocked_collision outcome must not enter graph.
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="loc_willow_collision",
        label="Willow",
        value={
            "kind": "location",
            "role": "location",
            "source_domains": ["manual_seed"],
        },
        identity_resolution_outcome="blocked_collision",
    )
    mention = kernel.ContributionIdentityMention(
        mention_id="mention:willow",
        label="Willow",
        object_kind="location",
        identity_resolution_outcome="blocked_collision",
        diagnostics=["cross-kind collision with npc Willow"],
        candidate_node_ids=["npc_willow_existing"],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:blocked",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
        unresolved_mentions=[mention],
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert result.published is True
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert "loc_willow_collision" not in store.nodes
    assert any("blocked_collision" in d for d in result.diagnostics)


def test_blocked_only_contribution_is_idempotent_on_remerge(seeded_root) -> None:
    root, parent = seeded_root
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="loc_blocked_idem",
        label="Blocked",
        value={
            "kind": "location",
            "role": "location",
            "source_domains": ["manual_seed"],
        },
        identity_resolution_outcome="blocked_collision",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:blocked-idem",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    first = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert first.published is True
    head_after_first, _, _ = kernel.open_current_world_graph(root, WORLD_ID)

    second = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert second.published is False
    assert any("idempotent_noop" in d for d in second.diagnostics)
    head_after_second, _, _ = kernel.open_current_world_graph(root, WORLD_ID)
    assert head_after_second.head_revision_id == head_after_first.head_revision_id


def test_failed_supersede_does_not_mark_old_contribution_superseded(
    seeded_root, monkeypatch
) -> None:
    root, _ = seeded_root
    assertion = _node_assertion(
        node_id="npc_super_tx",
        label="SuperTx",
        source_artifact_id="artifact:super-tx",
    )
    old = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:super-tx",
        source_revision_id="src-rev-a",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    merge_old = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=old
    )
    assert merge_old.published is True

    new = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:super-tx",
        source_revision_id="src-rev-b",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
        supersedes_contribution_id=old.contribution_id,
    )

    def _boom(*_args, **_kwargs):
        raise kernel.WorldGraphValidationError("forced publish failure")

    monkeypatch.setattr(
        "graph_memory.kernel.contribution_merge.publish_world_graph_revision",
        _boom,
    )
    result = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=new,
        superseded_contribution_id=old.contribution_id,
    )
    assert result.published is False
    assert result.superseded_contribution_ids == []

    import json

    old_path = (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{old.contribution_id.replace(':', '__')}.json"
    )
    old_record = json.loads(old_path.read_text(encoding="utf-8"))
    assert old_record["status"] == "active"
    index = json.loads(
        (
            root / "graph_memory" / "worlds" / WORLD_ID / "contribution_index.json"
        ).read_text(encoding="utf-8")
    )
    assert old.contribution_id in index["active_contribution_ids"]
    assert old.contribution_id not in index["superseded_contribution_ids"]
    new_path = (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{new.contribution_id.replace(':', '__')}.json"
    )
    new_record = json.loads(new_path.read_text(encoding="utf-8"))
    assert new_record["status"] == "failed"


def test_failed_retract_does_not_mark_contribution_retracted(
    seeded_root, monkeypatch
) -> None:
    root, _ = seeded_root
    assertion = _node_assertion(
        node_id="npc_retract_tx",
        label="RetractTx",
        source_artifact_id="artifact:retract-tx",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:retract-tx",
        source_revision_id="src-rev-1",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert merge.published is True

    def _boom(*_args, **_kwargs):
        raise kernel.WorldGraphValidationError("forced retract publish failure")

    monkeypatch.setattr(
        "graph_memory.kernel.contribution_merge.publish_world_graph_revision",
        _boom,
    )
    result = kernel.retract_graph_contribution(
        root,
        world_id=WORLD_ID,
        contribution_id=contribution.contribution_id,
        reason="should not stick",
    )
    assert result.published is False

    import json

    record_path = (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{contribution.contribution_id.replace(':', '__')}.json"
    )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["status"] == "active"
    index = json.loads(
        (
            root / "graph_memory" / "worlds" / WORLD_ID / "contribution_index.json"
        ).read_text(encoding="utf-8")
    )
    assert contribution.contribution_id in index["active_contribution_ids"]
    assert contribution.contribution_id not in index["retracted_contribution_ids"]
