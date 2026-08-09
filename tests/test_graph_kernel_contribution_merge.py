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


def _attribute_assertion(
    *,
    attribute: str = "battlefield_role",
    evidence_ref_id: str = "evidence:attribute:1",
    source_artifact_id: str = "artifact:attribute:1",
    source_revision_id: str = "attribute-revision-1",
    artifact_domain: str = "manual_seed",
    evidence_domain: str | None = None,
    include_evidence: bool = True,
    include_artifact: bool = True,
):
    evidence_domain = evidence_domain or artifact_domain
    evidence = {
        "evidence_ref_id": evidence_ref_id,
        "source_artifact_id": source_artifact_id,
        "source_domain": evidence_domain,
        "locator": "jsonptr:/accepted_assertions/0",
    }
    artifact = {
        "source_artifact_id": source_artifact_id,
        "source_domain": artifact_domain,
        "campaign_id": "longmont-c2",
        "uri": f"repo://test/{source_artifact_id}",
    }
    value = {
        "attribute": attribute,
        "text": f"value for {attribute}",
        "source_domains": [artifact_domain],
        "evidence": [evidence] if include_evidence else [],
        "source_artifacts": [artifact] if include_artifact else [],
    }
    return kernel.build_assertion(
        assertion_kind="attribute",
        acceptance_state="accepted",
        subject_node_id="loc_mirathorn",
        value=value,
        evidence_ref_ids=[evidence_ref_id],
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="resolved_existing",
    )


def _attribute_contribution(assertion):
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id=assertion.source_artifact_id,
        source_revision_id=assertion.source_revision_id,
        extraction_profile="attribute-test",
        campaign_scope="longmont-c2",
        accepted_assertions=[assertion],
    )


def test_attribute_materializes_embedded_evidence_and_artifact(seeded_root) -> None:
    root, parent = seeded_root
    contribution = _attribute_contribution(_attribute_assertion())

    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )

    assert result.published is True
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert "evidence:attribute:1" in store.evidence
    assert "artifact:attribute:1" in store.source_artifacts


def test_attribute_dangling_evidence_fails_closed(seeded_root) -> None:
    root, parent = seeded_root
    assertion = _attribute_assertion(include_evidence=False)
    contribution = _attribute_contribution(assertion)

    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )

    assert result.published is False
    assert any("unresolved evidence references" in item for item in result.diagnostics)


def test_attribute_evidence_domain_mismatch_fails_closed(seeded_root) -> None:
    root, parent = seeded_root
    assertion = _attribute_assertion(
        artifact_domain="worldbuilding",
        evidence_domain="recap",
    )
    contribution = _attribute_contribution(assertion)

    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )

    assert result.published is False
    assert any("source domain disagrees" in item for item in result.diagnostics)


def test_attribute_missing_source_artifact_fails_closed(seeded_root) -> None:
    root, parent = seeded_root
    assertion = _attribute_assertion(include_artifact=False)
    contribution = _attribute_contribution(assertion)

    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )

    assert result.published is False
    assert any("missing source artifact" in item for item in result.diagnostics)


def test_multiple_attributes_share_legitimate_evidence(seeded_root) -> None:
    root, parent = seeded_root
    first = _attribute_contribution(
        _attribute_assertion(
            attribute="battlefield_role",
            evidence_ref_id="evidence:attribute:shared",
            source_artifact_id="artifact:attribute:shared",
        )
    )
    first_result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=first,
        expected_parent_revision_id=parent,
    )
    assert first_result.published is True

    # Distinct contribution identity (source_revision_id) so this is a new
    # contribution_id; shared evidence may still materialize once on the store.
    second_assertion = _attribute_assertion(
        attribute="challenge_expectation",
        evidence_ref_id="evidence:attribute:shared",
        source_artifact_id="artifact:attribute:shared",
        source_revision_id="rev-shared-2",
        include_artifact=False,
    )
    second = _attribute_contribution(second_assertion)
    second_result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=second,
        expected_parent_revision_id=first_result.revision_id,
    )

    assert second_result.published is True
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert list(store.evidence).count("evidence:attribute:shared") == 1


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


def test_merge_refuses_disagreeing_active_node_fingerprint(seeded_root) -> None:
    root, parent = seeded_root
    first = _node_assertion(
        node_id="pc:baergrom_test",
        label="Baergrom",
        source_artifact_id="artifact:seed:baergrom",
    )
    # Force seed-like role that differs from default npc/npc.
    first = first.model_copy(
        update={
            "value": {
                **dict(first.value),
                "kind": "pc",
                "role": "player-character",
            },
            "epistemic_kind": "fact",
        }
    )
    seed = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:seed:baergrom",
        source_revision_id="src-rev-seed",
        extraction_profile="test_profile",
        campaign_scope="longmont-c2",
        accepted_assertions=[first],
    )
    seed_result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=seed,
        expected_parent_revision_id=parent,
    )
    assert seed_result.published is True

    conflicting = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="pc:baergrom_test",
        label="Baergrom",
        value={
            "kind": "pc",
            "role": "pc",
            "summary": "Recap-derived combat summary",
            "source_domains": ["recap"],
            "aliases": ["Baergrom"],
            "canon_state": "canonical",
        },
        evidence_ref_ids=[],
        source_artifact_id="artifact:recap:session-24",
        source_revision_id="src-rev-recap",
        campaign_scope="longmont-c2",
        epistemic_kind="source_derived_candidate",
        visibility="gm",
        identity_resolution_outcome="resolved_existing",
    )
    extract = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:recap:session-24",
        source_revision_id="src-rev-recap",
        extraction_profile="test_profile",
        campaign_scope="longmont-c2",
        accepted_assertions=[conflicting],
    )
    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=extract,
        expected_parent_revision_id=seed_result.revision_id,
    )
    assert result.published is False
    assert any("disagrees with an already-active" in d for d in result.diagnostics)
    head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert head.head_revision_id == seed_result.revision_id
    supports = [
        s
        for s in (store.assertion_support or {}).values()
        if (s.get("graph_object_id") if isinstance(s, dict) else s.graph_object_id)
        == "pc:baergrom_test"
    ]
    assert len(supports) == 1


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
    from graph_memory.kernel.contribution_merge import (
        apply_accepted_assertions,
        stamp_contribution_source_digest,
    )
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
    # Source digests are a separate forward-only authority plane from assertion
    # identity repair. Stamp digests here so these fixtures isolate the legacy
    # assertion-id gate.
    proposed = stamp_contribution_source_digest(proposed, contribution)
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


def test_legacy_retract_then_equivalent_merge_requires_migration(seeded_root) -> None:
    root, _ = seeded_root
    legacy_assertion = _with_legacy_assertion_id(
        _mireward_assertion(
            source_domain="worldbuilding",
            source_artifact_id="artifact:mireward:legacy-retract",
            source_revision_id="worldbuilding:legacy-retract-1",
            evidence_ref_id="evidence:mireward:legacy-retract",
        )
    )
    legacy = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:legacy-retract",
        source_revision_id="worldbuilding:legacy-retract-1",
        accepted_assertions=[legacy_assertion],
    ).model_copy(update={"accepted_assertions": [legacy_assertion]})
    path, _original_bytes = _seed_active_legacy_contribution(root, legacy)

    retracted = kernel.retract_graph_contribution(
        root,
        world_id=WORLD_ID,
        contribution_id=legacy.contribution_id,
        reason="withdraw legacy source",
    )
    assert retracted.published is True
    post_retract_bytes = path.read_bytes()
    before_head, _before_rev, before_store = kernel.open_current_world_graph(
        root, WORLD_ID
    )
    assert legacy_assertion.assertion_id in before_store.assertion_support
    assert (
        legacy.contribution_id
        in before_store.assertion_support[legacy_assertion.assertion_id][
            "retracted_contribution_ids"
        ]
    )

    replacement = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:legacy-retract",
        source_revision_id="worldbuilding:legacy-retract-2",
        accepted_assertions=[
            _mireward_assertion(
                source_domain="worldbuilding",
                source_artifact_id="artifact:mireward:legacy-retract",
                source_revision_id="worldbuilding:legacy-retract-2",
                evidence_ref_id="evidence:mireward:legacy-retract-2",
            )
        ],
    )
    blocked = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=replacement
    )
    assert blocked.published is False
    assert "assertion_identity_migration_required" in blocked.diagnostics
    assert path.read_bytes() == post_retract_bytes
    from graph_memory.world_supergraph.paths import contribution_path

    assert not contribution_path(root, WORLD_ID, replacement.contribution_id).exists()
    after_head, _after_rev, after_store = kernel.open_current_world_graph(
        root, WORLD_ID
    )
    assert after_head.head_revision_id == before_head.head_revision_id
    current_id = replacement.accepted_assertions[0].assertion_id
    assert current_id not in after_store.assertion_support
    assert legacy_assertion.assertion_id in after_store.assertion_support

    migrated = kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=True)
    assert migrated.published is True
    allowed = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=replacement
    )
    assert allowed.published is True
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    mireward_supports = [
        support
        for support in store.assertion_support.values()
        if support["graph_object_id"] == "location:mireward"
        and support["support_state"] == "supported"
        and support["active_contribution_ids"]
    ]
    assert len(mireward_supports) == 1
    assert mireward_supports[0]["assertion_id"] == current_id
    assert replacement.contribution_id in mireward_supports[0]["active_contribution_ids"]


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


def test_party_registry_source_artifact_session_id_drift_allows_merge(seeded_root) -> None:
    """Re-promoting standing registry with a new session stamp must not refuse merge."""
    root, parent = seeded_root
    artifact_id = "artifact:party-registry:longmont-c1"
    digest = "abc123digest"

    def _party_attribute(*, session_id: str, contribution_rev: str, attribute: str):
        evidence_ref_id = f"evidence:{artifact_id}:{attribute}"
        assertion = kernel.build_assertion(
            assertion_kind="attribute",
            acceptance_state="accepted",
            subject_node_id="loc_mirathorn",
            value={
                "attribute": attribute,
                "text": f"value for {attribute}",
                "source_domains": ["party_registry"],
                "evidence": [
                    {
                        "evidence_ref_id": evidence_ref_id,
                        "source_artifact_id": artifact_id,
                        "source_domain": "party_registry",
                        "session_id": session_id,
                        "source_span_ref_id": f"{artifact_id}:standing",
                    }
                ],
                "source_artifacts": [
                    {
                        "source_artifact_id": artifact_id,
                        "source_domain": "party_registry",
                        "campaign_id": "longmont-c1",
                        "content_sha256": digest,
                        "session_id": session_id,
                        "uri": "repo://corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json",
                    }
                ],
            },
            evidence_ref_ids=[evidence_ref_id],
            source_artifact_id=artifact_id,
            source_revision_id=f"sha256:{digest}",
            campaign_scope="longmont-c1",
            epistemic_kind="fact",
            visibility="gm",
            identity_resolution_outcome="resolved_existing",
        )
        return kernel.create_graph_contribution(
            world_id=WORLD_ID,
            source_kind="standing_context",
            source_artifact_id=artifact_id,
            source_revision_id=contribution_rev,
            extraction_profile="party_registry_standing",
            campaign_scope="longmont-c1",
            accepted_assertions=[assertion],
        )

    first = _party_attribute(
        session_id="session-3",
        contribution_rev="rev-party-s3",
        attribute="party_roster_note",
    )
    first_result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=first,
        expected_parent_revision_id=parent,
    )
    assert first_result.published is True, first_result.diagnostics

    second = _party_attribute(
        session_id="session-4",
        contribution_rev="rev-party-s4",
        attribute="party_roster_note_v2",
    )
    second_result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=second,
        expected_parent_revision_id=first_result.revision_id,
    )
    assert second_result.published is True, second_result.diagnostics
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert store.source_artifacts[artifact_id].session_id == "session-3"


def _race_merge_contribution(
    root: Path,
    *,
    contribution: object,
    expected_parent: str,
    monkeypatch: pytest.MonkeyPatch,
    barrier: object,
) -> tuple[list[object], list[BaseException]]:
    import graph_memory.kernel.contribution_merge as contribution_merge_mod

    real_publish = contribution_merge_mod.publish_world_graph_revision

    def sync_publish(*args, **kwargs):
        barrier.wait(timeout=5)
        return real_publish(*args, **kwargs)

    monkeypatch.setattr(
        contribution_merge_mod,
        "publish_world_graph_revision",
        sync_publish,
    )
    results: list[object] = []
    errors: list[BaseException] = []

    def _run() -> None:
        try:
            results.append(
                kernel.merge_contribution_to_revision(
                    root,
                    world_id=WORLD_ID,
                    contribution=contribution,
                    expected_parent_revision_id=expected_parent,
                )
            )
        except BaseException as exc:
            errors.append(exc)

    import threading

    threads = [threading.Thread(target=_run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results, errors


def _assert_post_race_contribution_index_and_digest(
    root: Path,
    *,
    winner_id: str,
    loser_id: str | None = None,
    same_plan: bool = False,
) -> None:
    import json

    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_index,
        load_contribution_record,
        list_contribution_records,
    )

    index = load_contribution_index(root, WORLD_ID)
    assert winner_id in index.active_contribution_ids
    assert winner_id in index.all_contribution_ids
    discovered = {record.contribution_id for record in list_contribution_records(root, WORLD_ID)}
    assert winner_id in discovered

    if loser_id is not None and not same_plan:
        assert loser_id not in index.active_contribution_ids
        assert loser_id in index.all_contribution_ids
        assert loser_id in index.failed_contribution_ids
        loser_path = (
            root
            / "graph_memory"
            / "worlds"
            / WORLD_ID
            / "contributions"
            / f"{loser_id.replace(':', '__')}.json"
        )
        loser_record = json.loads(loser_path.read_text(encoding="utf-8"))
        assert loser_record["status"] == "failed"

    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    winner_obj = load_contribution_record(root, WORLD_ID, winner_id)
    source_digest = kernel.compute_contribution_source_payload_sha256(winner_obj)
    assert store.contribution_source_payload_sha256.get(winner_id) == source_digest


def _rmw_test_contribution(*, suffix: str, status: str):
    assertion = _node_assertion(
        node_id=f"npc_index_rmw_{suffix}",
        label=f"IndexRMW{suffix}",
        source_artifact_id=f"artifact:index-rmw-{suffix}",
    )
    digest_byte = {"a": "c1", "b": "c2"}[suffix]
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id=f"artifact:index-rmw-{suffix}",
        source_revision_id=f"src-rev-rmw-{suffix}",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
        authored_by="live_control:worldbuilding_write_plan",
        proposal_digest="sha256:" + (digest_byte * 32),
    )
    return contribution.model_copy(update={"status": status})


def test_contribution_index_rmw_winner_save_then_loser_preserves_winner(
    seeded_root,
) -> None:
    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_index,
        upsert_and_save_contribution_index,
        write_contribution_record,
    )

    root, _parent = seeded_root
    active = _rmw_test_contribution(suffix="a", status="active")
    failed = _rmw_test_contribution(suffix="b", status="failed")
    write_contribution_record(root, WORLD_ID, active)
    write_contribution_record(root, WORLD_ID, failed)

    upsert_and_save_contribution_index(root, WORLD_ID, active)
    upsert_and_save_contribution_index(root, WORLD_ID, failed)

    index = load_contribution_index(root, WORLD_ID)
    assert active.contribution_id in index.active_contribution_ids
    assert failed.contribution_id in index.failed_contribution_ids
    assert failed.contribution_id not in index.active_contribution_ids
    assert set(index.all_contribution_ids) == {
        active.contribution_id,
        failed.contribution_id,
    }


def test_contribution_index_rmw_loser_save_then_winner_preserves_winner(
    seeded_root,
) -> None:
    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_index,
        upsert_and_save_contribution_index,
        write_contribution_record,
    )

    root, _parent = seeded_root
    active = _rmw_test_contribution(suffix="a", status="active")
    failed = _rmw_test_contribution(suffix="b", status="failed")
    write_contribution_record(root, WORLD_ID, active)
    write_contribution_record(root, WORLD_ID, failed)

    upsert_and_save_contribution_index(root, WORLD_ID, failed)
    upsert_and_save_contribution_index(root, WORLD_ID, active)

    index = load_contribution_index(root, WORLD_ID)
    assert active.contribution_id in index.active_contribution_ids
    assert failed.contribution_id in index.failed_contribution_ids
    assert failed.contribution_id not in index.active_contribution_ids
    assert set(index.all_contribution_ids) == {
        active.contribution_id,
        failed.contribution_id,
    }


def test_concurrent_same_plan_race_one_publish_winner_stays_active(
    seeded_root, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    import threading

    root, parent = seeded_root
    assertion = _node_assertion(
        node_id="npc_same_plan_race",
        label="SamePlanRace",
        source_artifact_id="artifact:same-plan-race",
    )
    proposal_digest = "sha256:" + ("a1" * 32)
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:same-plan-race",
        source_revision_id="src-rev-same-plan",
        extraction_profile="test_profile",
        accepted_assertions=[assertion],
        authored_by="live_control:worldbuilding_write_plan",
        proposal_digest=proposal_digest,
    )
    barrier = threading.Barrier(2)
    results, errors = _race_merge_contribution(
        root,
        contribution=contribution,
        expected_parent=parent,
        monkeypatch=monkeypatch,
        barrier=barrier,
    )
    published = [item for item in results if item.published]
    assert len(published) == 1
    assert len(errors) == 1
    assert "stale parent" in str(errors[0]).lower()

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
    head_after, _, _ = kernel.open_current_world_graph(root, WORLD_ID)
    assert head_after.head_revision_id != parent
    _assert_post_race_contribution_index_and_digest(
        root,
        winner_id=contribution.contribution_id,
        same_plan=True,
    )


def test_concurrent_different_plan_race_one_publish_winner_stays_active(
    seeded_root, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    import threading

    root, parent = seeded_root
    assertion_a = _node_assertion(
        node_id="npc_diff_plan_race_a",
        label="DiffPlanA",
        source_artifact_id="artifact:diff-plan-race-a",
    )
    assertion_b = _node_assertion(
        node_id="npc_diff_plan_race_b",
        label="DiffPlanB",
        source_artifact_id="artifact:diff-plan-race-b",
    )
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:diff-plan-race-a",
        source_revision_id="src-rev-a",
        extraction_profile="test_profile",
        accepted_assertions=[assertion_a],
        authored_by="live_control:worldbuilding_write_plan",
        proposal_digest="sha256:" + ("b1" * 32),
    )
    contrib_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:diff-plan-race-b",
        source_revision_id="src-rev-b",
        extraction_profile="test_profile",
        accepted_assertions=[assertion_b],
        authored_by="live_control:worldbuilding_write_plan",
        proposal_digest="sha256:" + ("b2" * 32),
    )
    barrier = threading.Barrier(2)
    import graph_memory.kernel.contribution_merge as contribution_merge_mod

    real_publish = contribution_merge_mod.publish_world_graph_revision

    def sync_publish(*args, **kwargs):
        barrier.wait(timeout=5)
        return real_publish(*args, **kwargs)

    monkeypatch.setattr(
        contribution_merge_mod,
        "publish_world_graph_revision",
        sync_publish,
    )
    results: list[tuple[str, object]] = []
    errors: list[tuple[str, BaseException]] = []

    def _run(label: str, contribution: object) -> None:
        try:
            merge_result = kernel.merge_contribution_to_revision(
                root,
                world_id=WORLD_ID,
                contribution=contribution,
                expected_parent_revision_id=parent,
            )
            results.append((label, merge_result))
        except BaseException as exc:
            errors.append((label, exc))

    threads = [
        threading.Thread(target=_run, args=("a", contrib_a)),
        threading.Thread(target=_run, args=("b", contrib_b)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    published = [(label, item) for label, item in results if item.published]
    assert len(published) == 1
    assert len(errors) == 1
    assert "stale parent" in str(errors[0][1]).lower()

    winner_id = published[0][1].contribution_ids[0]
    winner_path = (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{winner_id.replace(':', '__')}.json"
    )
    winner_record = json.loads(winner_path.read_text(encoding="utf-8"))
    assert winner_record["status"] == "active"
    loser_label = errors[0][0]
    loser_id = (
        contrib_a.contribution_id
        if loser_label == "a"
        else contrib_b.contribution_id
    )
    _assert_post_race_contribution_index_and_digest(
        root,
        winner_id=winner_id,
        loser_id=loser_id,
    )


# ---------------------------------------------------------------------------
# Governed structural edge-assertion correction
# ---------------------------------------------------------------------------


def _correction_node_assertion(
    *,
    node_id: str,
    label: str,
    source_artifact_id: str,
    source_revision_id: str = "src-rev-correction",
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
        },
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )


def _correction_edge_assertion(
    *,
    edge_id: str,
    source_node_id: str,
    target_node_id: str,
    predicate: str,
    source_artifact_id: str,
    source_revision_id: str = "src-rev-correction",
    evidence_ref_id: str = "evidence:correction:edge",
):
    return kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        label=predicate,
        value={
            "edge_id": edge_id,
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "predicate": predicate,
            "source_domains": ["manual_seed"],
            "evidence": [
                {
                    "evidence_ref_id": evidence_ref_id,
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                }
            ],
            "canon_state": "canonical",
        },
        evidence_ref_ids=[evidence_ref_id],
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="resolved_existing",
    )


def _publish_source_with_edge_and_siblings(root: Path):
    """Source contribution A: edge X plus unrelated node assertions Y and Z."""
    node_src = _correction_node_assertion(
        node_id="npc_correction_src",
        label="Correction Src",
        source_artifact_id="artifact:correction:a",
    )
    node_tgt = _correction_node_assertion(
        node_id="npc_correction_tgt",
        label="Correction Tgt",
        source_artifact_id="artifact:correction:a",
    )
    node_y = _correction_node_assertion(
        node_id="npc_correction_y",
        label="Sibling Y",
        source_artifact_id="artifact:correction:a",
    )
    node_z = _correction_node_assertion(
        node_id="npc_correction_z",
        label="Sibling Z",
        source_artifact_id="artifact:correction:a",
    )
    edge_x = _correction_edge_assertion(
        edge_id="edge:npc_correction_src:threatens:npc_correction_tgt",
        source_node_id="npc_correction_src",
        target_node_id="npc_correction_tgt",
        predicate="threatens",
        source_artifact_id="artifact:correction:a",
        evidence_ref_id="evidence:correction:x",
    )
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:correction:a",
        source_revision_id="src-rev-a",
        extraction_profile="test_profile",
        accepted_assertions=[node_src, node_tgt, edge_x, node_y, node_z],
        authored_by="extractor",
    )
    merge_a = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_a
    )
    assert merge_a.published is True
    return contrib_a, edge_x, node_y, node_z, merge_a.revision_id


def test_edge_assertion_correction_atomicity_preserves_siblings(seeded_root) -> None:
    root, _ = seeded_root
    contrib_a, edge_x, node_y, node_z, parent = _publish_source_with_edge_and_siblings(
        root
    )
    _head, _rev, before = kernel.open_current_world_graph(root, WORLD_ID)
    support_y_before = dict(before.assertion_support[node_y.assertion_id])
    support_z_before = dict(before.assertion_support[node_z.assertion_id])

    edge_xp = _correction_edge_assertion(
        edge_id="edge:npc_correction_tgt:threatens:npc_correction_src",
        source_node_id="npc_correction_tgt",
        target_node_id="npc_correction_src",
        predicate="threatens",
        source_artifact_id="artifact:correction:c",
        evidence_ref_id="evidence:correction:xp",
    )
    correction = kernel.create_edge_assertion_correction_contribution(
        world_id=WORLD_ID,
        authored_by="gm-operator",
        target_contribution_id=contrib_a.contribution_id,
        target_assertion_id=edge_x.assertion_id,
        replacement_assertion=edge_xp,
        source_artifact_id="artifact:correction:c",
        source_revision_id="correction-1",
    )
    assert correction.assertion_corrections
    assert len(correction.accepted_assertions) == 1

    result = kernel.correct_edge_assertion_support(
        root,
        world_id=WORLD_ID,
        contribution=correction,
        expected_parent_revision_id=parent,
    )
    assert result.published is True
    assert result.revision_id != parent
    assert edge_x.assertion_id in result.contradicted_assertion_ids
    assert edge_xp.assertion_id in result.accepted_assertion_ids

    # Old pinned revision unchanged.
    old_store = kernel.load_world_graph_revision(root, WORLD_ID, parent)
    old_support_x = old_store.assertion_support[edge_x.assertion_id]
    assert old_support_x["support_state"] == "supported"
    assert contrib_a.contribution_id in old_support_x["active_contribution_ids"]

    _head2, _rev2, store = kernel.open_current_world_graph(root, WORLD_ID)
    support_x = store.assertion_support[edge_x.assertion_id]
    support_xp = store.assertion_support[edge_xp.assertion_id]
    assert support_x["support_state"] == "contradicted"
    assert support_x["active_contribution_ids"] == []
    assert contrib_a.contribution_id in support_x["contradicted_contribution_ids"]
    assert support_xp["support_state"] == "supported"
    assert correction.contribution_id in support_xp["active_contribution_ids"]

    # Unrelated Y/Z support + provenance unchanged.
    assert store.assertion_support[node_y.assertion_id] == support_y_before
    assert store.assertion_support[node_z.assertion_id] == support_z_before

    # Source contribution A remains active (not superseded/retracted).
    from graph_memory.world_supergraph.contribution_store import load_contribution_record

    loaded_a = load_contribution_record(root, WORLD_ID, contrib_a.contribution_id)
    assert loaded_a.status == "active"


def test_edge_assertion_correction_rejects_multi_source_target(seeded_root) -> None:
    root, _ = seeded_root
    contrib_a, edge_x, _y, _z, parent = _publish_source_with_edge_and_siblings(root)
    # Second independent supporter for the same edge assertion.
    edge_x_b = _correction_edge_assertion(
        edge_id="edge:npc_correction_src:threatens:npc_correction_tgt",
        source_node_id="npc_correction_src",
        target_node_id="npc_correction_tgt",
        predicate="threatens",
        source_artifact_id="artifact:correction:b",
        evidence_ref_id="evidence:correction:xb",
    )
    assert edge_x_b.assertion_id == edge_x.assertion_id
    contrib_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:correction:b",
        source_revision_id="src-rev-b",
        extraction_profile="test_profile",
        accepted_assertions=[edge_x_b],
    )
    merge_b = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_b
    )
    assert merge_b.published is True
    parent = merge_b.revision_id

    edge_xp = _correction_edge_assertion(
        edge_id="edge:npc_correction_tgt:threatens:npc_correction_src",
        source_node_id="npc_correction_tgt",
        target_node_id="npc_correction_src",
        predicate="threatens",
        source_artifact_id="artifact:correction:c",
        evidence_ref_id="evidence:correction:xp",
    )
    correction = kernel.create_edge_assertion_correction_contribution(
        world_id=WORLD_ID,
        authored_by="gm-operator",
        target_contribution_id=contrib_a.contribution_id,
        target_assertion_id=edge_x.assertion_id,
        replacement_assertion=edge_xp,
        source_artifact_id="artifact:correction:c",
    )
    result = kernel.correct_edge_assertion_support(
        root,
        world_id=WORLD_ID,
        contribution=correction,
        expected_parent_revision_id=parent,
    )
    assert result.published is False
    assert result.failure_code == "correction_rejected"
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    support_x = store.assertion_support[edge_x.assertion_id]
    assert support_x["support_state"] == "supported"
    assert set(support_x["active_contribution_ids"]) == {
        contrib_a.contribution_id,
        contrib_b.contribution_id,
    }
    assert edge_xp.assertion_id not in store.assertion_support


def test_edge_assertion_correction_stale_parent_and_exact_retry(seeded_root) -> None:
    root, _ = seeded_root
    contrib_a, edge_x, _y, _z, parent = _publish_source_with_edge_and_siblings(root)
    edge_xp = _correction_edge_assertion(
        edge_id="edge:npc_correction_tgt:threatens:npc_correction_src",
        source_node_id="npc_correction_tgt",
        target_node_id="npc_correction_src",
        predicate="threatens",
        source_artifact_id="artifact:correction:c",
        evidence_ref_id="evidence:correction:xp",
    )
    correction = kernel.create_edge_assertion_correction_contribution(
        world_id=WORLD_ID,
        authored_by="gm-operator",
        target_contribution_id=contrib_a.contribution_id,
        target_assertion_id=edge_x.assertion_id,
        replacement_assertion=edge_xp,
        source_artifact_id="artifact:correction:c",
        produced_at="2026-08-09T00:00:00Z",
    )

    # Advance head with an unrelated write so expected parent is stale.
    unrelated = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:correction:unrelated",
        accepted_assertions=[
            _correction_node_assertion(
                node_id="npc_correction_unrelated",
                label="Unrelated",
                source_artifact_id="artifact:correction:unrelated",
            )
        ],
    )
    advanced = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=unrelated
    )
    assert advanced.published is True
    newer_head = advanced.revision_id

    with pytest.raises(ValueError, match="stale parent"):
        kernel.correct_edge_assertion_support(
            root,
            world_id=WORLD_ID,
            contribution=correction,
            expected_parent_revision_id=parent,
        )
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert _head.head_revision_id == newer_head
    assert store.assertion_support[edge_x.assertion_id]["support_state"] == "supported"

    # Exact success then exact retry is idempotent.
    first = kernel.correct_edge_assertion_support(
        root,
        world_id=WORLD_ID,
        contribution=correction,
        expected_parent_revision_id=newer_head,
    )
    assert first.published is True
    corrected_rev = first.revision_id
    retry = kernel.correct_edge_assertion_support(
        root,
        world_id=WORLD_ID,
        contribution=correction,
        expected_parent_revision_id=corrected_rev,
    )
    assert retry.published is False
    assert "idempotent_noop:correction_already_applied" in retry.diagnostics
    assert retry.revision_id == corrected_rev
    _head2, _rev2, store2 = kernel.open_current_world_graph(root, WORLD_ID)
    assert _head2.head_revision_id == corrected_rev
    support_x = store2.assertion_support[edge_x.assertion_id]
    assert support_x["contradicted_contribution_ids"].count(contrib_a.contribution_id) == 1


def test_edge_assertion_correction_lifecycle_guards(seeded_root) -> None:
    root, _ = seeded_root
    contrib_a, edge_x, _y, _z, parent = _publish_source_with_edge_and_siblings(root)
    edge_xp = _correction_edge_assertion(
        edge_id="edge:npc_correction_tgt:threatens:npc_correction_src",
        source_node_id="npc_correction_tgt",
        target_node_id="npc_correction_src",
        predicate="threatens",
        source_artifact_id="artifact:correction:c",
        evidence_ref_id="evidence:correction:xp",
    )
    correction = kernel.create_edge_assertion_correction_contribution(
        world_id=WORLD_ID,
        authored_by="gm-operator",
        target_contribution_id=contrib_a.contribution_id,
        target_assertion_id=edge_x.assertion_id,
        replacement_assertion=edge_xp,
        source_artifact_id="artifact:correction:c",
    )
    published = kernel.correct_edge_assertion_support(
        root,
        world_id=WORLD_ID,
        contribution=correction,
        expected_parent_revision_id=parent,
    )
    assert published.published is True
    corrected_rev = published.revision_id

    retract_c = kernel.retract_graph_contribution(
        root,
        world_id=WORLD_ID,
        contribution_id=correction.contribution_id,
        reason="attempt undo correction",
        expected_parent_revision_id=corrected_rev,
    )
    assert retract_c.published is False
    assert retract_c.failure_code == "correction_lifecycle_unsupported"

    retract_a = kernel.retract_graph_contribution(
        root,
        world_id=WORLD_ID,
        contribution_id=contrib_a.contribution_id,
        reason="attempt retract corrected source",
        expected_parent_revision_id=corrected_rev,
    )
    assert retract_a.published is False
    assert retract_a.failure_code == "correction_lifecycle_unsupported"

    supersede_a = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=kernel.create_graph_contribution(
            world_id=WORLD_ID,
            source_kind="source_extraction",
            source_artifact_id="artifact:correction:supersede",
            source_revision_id="src-rev-super",
            accepted_assertions=[
                _correction_node_assertion(
                    node_id="npc_correction_super",
                    label="Super",
                    source_artifact_id="artifact:correction:supersede",
                )
            ],
            supersedes_contribution_id=contrib_a.contribution_id,
        ),
        superseded_contribution_id=contrib_a.contribution_id,
        expected_parent_revision_id=corrected_rev,
    )
    assert supersede_a.published is False
    assert supersede_a.failure_code == "correction_lifecycle_unsupported"

    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    assert _head.head_revision_id == corrected_rev
    assert store.assertion_support[edge_x.assertion_id]["support_state"] == "contradicted"
    assert (
        store.assertion_support[edge_xp.assertion_id]["support_state"] == "supported"
    )


def test_merge_rejects_assertion_corrections_without_dedicated_op(seeded_root) -> None:
    root, _ = seeded_root
    contrib_a, edge_x, _y, _z, _parent = _publish_source_with_edge_and_siblings(root)
    edge_xp = _correction_edge_assertion(
        edge_id="edge:npc_correction_tgt:threatens:npc_correction_src",
        source_node_id="npc_correction_tgt",
        target_node_id="npc_correction_src",
        predicate="threatens",
        source_artifact_id="artifact:correction:c",
        evidence_ref_id="evidence:correction:xp",
    )
    correction = kernel.create_edge_assertion_correction_contribution(
        world_id=WORLD_ID,
        authored_by="gm-operator",
        target_contribution_id=contrib_a.contribution_id,
        target_assertion_id=edge_x.assertion_id,
        replacement_assertion=edge_xp,
        source_artifact_id="artifact:correction:c",
    )
    blocked = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=correction
    )
    assert blocked.published is False
    assert blocked.failure_code == "correction_requires_dedicated_operation"


def test_correction_linkage_changes_contribution_identity(seeded_root) -> None:
    _root, _ = seeded_root
    edge_xp = _correction_edge_assertion(
        edge_id="edge:npc_correction_tgt:threatens:npc_correction_src",
        source_node_id="npc_correction_tgt",
        target_node_id="npc_correction_src",
        predicate="threatens",
        source_artifact_id="artifact:correction:c",
        evidence_ref_id="evidence:correction:xp",
    )
    c1 = kernel.create_edge_assertion_correction_contribution(
        world_id=WORLD_ID,
        authored_by="gm-operator",
        target_contribution_id="contribution:target-a",
        target_assertion_id="assertion:target-x",
        replacement_assertion=edge_xp,
        source_artifact_id="artifact:correction:c",
        produced_at="2026-08-09T00:00:00Z",
    )
    c2 = kernel.create_edge_assertion_correction_contribution(
        world_id=WORLD_ID,
        authored_by="gm-operator",
        target_contribution_id="contribution:target-b",
        target_assertion_id="assertion:target-x",
        replacement_assertion=edge_xp,
        source_artifact_id="artifact:correction:c",
        produced_at="2026-08-09T00:00:00Z",
    )
    assert c1.contribution_id != c2.contribution_id
    d1 = kernel.compute_contribution_source_payload_sha256(c1)
    d2 = kernel.compute_contribution_source_payload_sha256(c2)
    assert d1 != d2
