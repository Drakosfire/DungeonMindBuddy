"""Contribution rebuild tests (PR005)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)
from graph_memory.world_supergraph.contribution_store import (
    # PR003_INTERNAL_GRAPH_KERNEL_EXEMPTION: test-local legacy ledger fixture.
    ContributionIndex,
    save_contribution_index,
    upsert_contribution_in_index,
    write_contribution_record,
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


def test_rebuild_from_contributions_matches_head_for_fixture(seeded_root: Path) -> None:
    root = seeded_root
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_rebuild",
        label="Rebuild NPC",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Rebuild NPC"],
        },
        source_artifact_id="artifact:rebuild",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    authored = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:rebuild",
        source_revision_id="authored-1",
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=authored
    )
    assert merge.published is True

    # Apply an identity decision on a pair of fixture nodes and ensure rebuild keeps it.
    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    # Use a harmless alias decision recorded on the store (human override record).
    decision = kernel.build_identity_decision_record(
        world_id=WORLD_ID,
        decision_kind="human_override",
        actor="gm",
        reason="confirm rebuild npc",
        subject_node_id="npc_rebuild",
        source_candidate_id="candidate:rebuild",
    )
    store = kernel.record_identity_decision(store, decision)
    published = kernel.publish_world_revision(
        root,
        WORLD_ID,
        store,
        operation_ids=[decision.decision_id],
        expected_parent_revision_id=merge.revision_id,
    )
    assert published.revision.revision_id

    result = kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=False)
    assert "rebuild_equivalent_to_head" in result.diagnostics
    assert authored.contribution_id in result.contribution_ids

    _h2, _r2, head_store = kernel.open_current_world_graph(root, WORLD_ID)
    assert "npc_rebuild" in head_store.nodes
    decision_ids = {item.get("decision_id") for item in head_store.identity_decisions}
    assert decision.decision_id in decision_ids


def test_rebuild_loads_identity_decisions_from_ledger_not_head(
    seeded_root: Path, monkeypatch
) -> None:
    """Rebuild must replay decisions from the durable ledger, not the current head."""
    root = seeded_root
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_ledger_rebuild",
        label="Ledger Rebuild NPC",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Ledger Rebuild NPC"],
        },
        source_artifact_id="artifact:ledger-rebuild",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    authored = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:ledger-rebuild",
        source_revision_id="authored-1",
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=authored
    )
    assert merge.published is True

    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    decision = kernel.build_identity_decision_record(
        world_id=WORLD_ID,
        decision_kind="human_override",
        actor="gm",
        reason="ledger-backed rebuild decision",
        subject_node_id="npc_ledger_rebuild",
        source_candidate_id="candidate:ledger-rebuild",
    )
    store = kernel.record_identity_decision(store, decision)
    kernel.publish_world_revision(
        root,
        WORLD_ID,
        store,
        operation_ids=[decision.decision_id],
        expected_parent_revision_id=merge.revision_id,
    )

    # Prove collect does not depend on head: empty head identity_decisions while
    # the durable ledger still holds the payload.
    real_load = kernel.load_current_world_graph

    def _load_without_head_decisions(root_path, world_id):
        head, rev, current = real_load(root_path, world_id)
        stripped = current.model_copy(update={"identity_decisions": []})
        return head, rev, stripped

    monkeypatch.setattr(
        "graph_memory.kernel.contribution_rebuild.load_current_world_graph",
        _load_without_head_decisions,
    )
    kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=False)

    import json

    ledger_path = (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "identity_decisions"
        / f"{decision.decision_id.replace(':', '__')}.json"
    )
    persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert persisted["reason"] == "ledger-backed rebuild decision"

    report = json.loads(
        (
            root
            / "graph_memory"
            / "worlds"
            / WORLD_ID
            / "contribution_rebuild"
            / "latest.json"
        ).read_text(encoding="utf-8")
    )
    assert decision.decision_id in report["identity_decision_ids"]


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


def test_rebuild_migrates_legacy_provenance_split_without_rewriting_ledger(
    seeded_root: Path,
) -> None:
    root = seeded_root
    _head, baseline, _store = kernel.open_current_world_graph(root, WORLD_ID)

    def legacy_assertion(
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
        value = {
            "kind": "location",
            "role": "town",
            "aliases": ["Mireward"],
            "source_domains": [source_domain],
            "evidence": [evidence],
            "canon_state": "canonical",
        }
        current = kernel.build_assertion(
            assertion_kind="node",
            acceptance_state="accepted",
            subject_node_id="location:mireward",
            label="Mireward",
            value=value,
            evidence_ref_ids=[evidence_ref_id],
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            campaign_scope="longmont-c2",
            epistemic_kind="fact",
            visibility="gm",
            identity_resolution_outcome=(
                "created_new"
                if source_domain == "worldbuilding"
                else "resolved_existing"
            ),
        )
        return current.model_copy(
            update={
                "assertion_id": _legacy_assertion_id(
                    assertion_kind=current.assertion_kind,
                    subject_node_id=current.subject_node_id,
                    target_node_id=current.target_node_id,
                    predicate=current.predicate,
                    label=current.label,
                    value=current.value,
                    campaign_scope=current.campaign_scope,
                    temporal_scope=current.temporal_scope,
                    epistemic_kind=current.epistemic_kind,
                    visibility=current.visibility,
                )
            }
        )

    old_a = legacy_assertion(
        source_domain="worldbuilding",
        source_artifact_id="artifact:mireward:worldbuilding",
        source_revision_id="worldbuilding:1",
        evidence_ref_id="evidence:mireward:worldbuilding",
    )
    old_b = legacy_assertion(
        source_domain="recap",
        source_artifact_id="artifact:mireward:recap",
        source_revision_id="recap:1",
        evidence_ref_id="evidence:mireward:recap",
    )
    assert old_a.assertion_id != old_b.assertion_id
    contribution_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:worldbuilding",
        source_revision_id="worldbuilding:1",
        accepted_assertions=[old_a],
    ).model_copy(update={"accepted_assertions": [old_a]})
    contribution_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:mireward:recap",
        source_revision_id="recap:1",
        accepted_assertions=[old_b],
    ).model_copy(update={"accepted_assertions": [old_b]})

    path_a = write_contribution_record(root, WORLD_ID, contribution_a)
    path_b = write_contribution_record(root, WORLD_ID, contribution_b)
    original_a = path_a.read_bytes()
    original_b = path_b.read_bytes()
    index = ContributionIndex(
        world_id=WORLD_ID, baseline_revision_id=baseline.revision_id
    )
    index = upsert_contribution_in_index(index, contribution_a)
    index = upsert_contribution_in_index(index, contribution_b)
    save_contribution_index(root, WORLD_ID, index)

    rebuilt = kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=True)
    assert rebuilt.published is True
    assert path_a.read_bytes() == original_a
    assert path_b.read_bytes() == original_b

    _head, revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    supports = [
        support
        for support in store.assertion_support.values()
        if support["graph_object_id"] == "location:mireward"
    ]
    assert len(supports) == 1
    support = supports[0]
    assert set(support["active_contribution_ids"]) == {
        contribution_a.contribution_id,
        contribution_b.contribution_id,
    }
    assert set(support["source_artifact_ids"]) == {
        "artifact:mireward:worldbuilding",
        "artifact:mireward:recap",
    }
    assert set(support["evidence_ref_ids"]) == {
        "evidence:mireward:worldbuilding",
        "evidence:mireward:recap",
    }
    assert set(store.nodes["location:mireward"].source_domains) == {
        "worldbuilding",
        "recap",
    }
    assert revision.parent_revision_id == baseline.revision_id

    report = json.loads(
        (
            root
            / "graph_memory"
            / "worlds"
            / WORLD_ID
            / "contribution_rebuild"
            / "latest.json"
        ).read_text(encoding="utf-8")
    )
    assert {
        (item["contribution_id"], item["old_assertion_id"], item["new_assertion_id"])
        for item in report["assertion_identity_rekeys"]
    } == {
        (
            contribution_a.contribution_id,
            old_a.assertion_id,
            supports[0]["assertion_id"],
        ),
        (
            contribution_b.contribution_id,
            old_b.assertion_id,
            supports[0]["assertion_id"],
        ),
    }
    assert report["compared_revision_id"] == baseline.revision_id
    assert report["published"] is True
    assert report["published_revision_id"] == revision.revision_id
    assert report["head_revision_id"] == revision.revision_id
    assert report["equivalent_to_compared_revision"] is False
    assert report["equivalent_to_published_head"] is True
    assert report["equivalent_to_head"] is True

    verification = kernel.rebuild_from_contributions(
        root, world_id=WORLD_ID, publish=False
    )
    assert verification.published is False
    assert "rebuild_equivalent_to_head" in verification.diagnostics


def test_pinned_rebuild_does_not_mislabel_head_equivalence(seeded_root: Path) -> None:
    """Pinned audit must pin replay inputs and not claim current-head equivalence."""
    root = seeded_root
    first = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_pin_a",
        label="Pin A",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Pin A"],
        },
        source_artifact_id="artifact:pin-a",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:pin-a",
        source_revision_id="authored-pin-a",
        authored_by="gm",
        accepted_assertions=[first],
    )
    merge_a = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_a
    )
    assert merge_a.published is True
    pinned_revision_id = merge_a.revision_id
    assert pinned_revision_id

    second = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_pin_b",
        label="Pin B",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Pin B"],
        },
        source_artifact_id="artifact:pin-b",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    contrib_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:pin-b",
        source_revision_id="authored-pin-b",
        authored_by="gm",
        accepted_assertions=[second],
    )
    merge_b = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_b
    )
    assert merge_b.published is True
    current_head = merge_b.revision_id
    assert current_head != pinned_revision_id

    # Production path: pin only compare_revision_id. Replay membership must come
    # from revision A even though the live index already contains contribution B.
    result = kernel.rebuild_from_contributions(
        root,
        world_id=WORLD_ID,
        publish=False,
        compare_revision_id=pinned_revision_id,
    )
    assert result.published is False
    assert contrib_a.contribution_id in result.contribution_ids
    assert contrib_b.contribution_id not in result.contribution_ids
    assert "rebuild_replay_pinned_to_revision:" + pinned_revision_id in result.diagnostics
    assert "rebuild_equivalent_to_pinned_revision" in result.diagnostics
    assert "rebuild_differs_from_head" in result.diagnostics
    assert "rebuild_equivalent_to_head" not in result.diagnostics
    assert any(
        d.startswith(f"head_advanced_past_compare_revision:{current_head}")
        for d in result.diagnostics
    )

    report = json.loads(
        (
            root
            / "graph_memory"
            / "worlds"
            / WORLD_ID
            / "contribution_rebuild"
            / "latest.json"
        ).read_text(encoding="utf-8")
    )
    assert report["compared_revision_id"] == pinned_revision_id
    assert report["current_head_revision_id"] == current_head
    assert report["head_revision_id"] == current_head
    assert report["equivalent_to_pinned_revision"] is True
    assert report["equivalent_to_compared_revision"] is True
    assert report["equivalent_to_head"] is False
    assert contrib_b.contribution_id not in report["contribution_ids"]


def test_pinned_rebuild_survives_later_retraction(seeded_root: Path) -> None:
    """Pinned audit must ignore later ledger retraction of a contribution active at pin."""
    root = seeded_root
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_pin_retract",
        label="Pin Retract",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Pin Retract"],
        },
        source_artifact_id="artifact:pin-retract",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    contrib = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:pin-retract",
        source_revision_id="authored-pin-retract",
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib
    )
    assert merge.published is True
    pinned_revision_id = merge.revision_id
    assert pinned_revision_id

    retract = kernel.retract_graph_contribution(
        root,
        world_id=WORLD_ID,
        contribution_id=contrib.contribution_id,
        reason="post-pin retract",
    )
    assert retract.published is True
    assert retract.revision_id != pinned_revision_id

    result = kernel.rebuild_from_contributions(
        root,
        world_id=WORLD_ID,
        publish=False,
        compare_revision_id=pinned_revision_id,
    )
    assert "rebuild_equivalent_to_pinned_revision" in result.diagnostics
    assert "replayed_retracted_support_removal:" not in "\n".join(result.diagnostics)
    assert "npc_pin_retract" in kernel.load_world_graph_revision(
        root, WORLD_ID, pinned_revision_id
    ).nodes


def test_pinned_rebuild_survives_later_identity_supersession(
    seeded_root: Path,
) -> None:
    """Pinned identity snapshot status must not follow later ledger mutations."""
    root = seeded_root
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_pin_identity",
        label="Pin Identity",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Pin Identity"],
        },
        source_artifact_id="artifact:pin-identity",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    contrib = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:pin-identity",
        source_revision_id="authored-pin-identity",
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib
    )
    assert merge.published is True

    _head, _rev, store = kernel.open_current_world_graph(root, WORLD_ID)
    decision = kernel.build_identity_decision_record(
        world_id=WORLD_ID,
        decision_kind="human_override",
        actor="gm",
        reason="pin-time identity decision",
        subject_node_id="npc_pin_identity",
        source_candidate_id="candidate:pin-identity",
    )
    store = kernel.record_identity_decision(store, decision)
    published = kernel.publish_world_revision(
        root,
        WORLD_ID,
        store,
        operation_ids=[decision.decision_id],
        expected_parent_revision_id=merge.revision_id,
    )
    pinned_revision_id = published.revision.revision_id

    # Mutate the durable ledger status after the pin without advancing a matching
    # graph revision that would change the pin snapshot.
    from graph_memory.world_supergraph.identity_decision_store import (
        load_identity_decision_record,
        write_identity_decision_record,
    )

    ledger = load_identity_decision_record(root, WORLD_ID, decision.decision_id)
    write_identity_decision_record(
        root,
        WORLD_ID,
        ledger.model_copy(update={"status": "superseded"}),
    )

    result = kernel.rebuild_from_contributions(
        root,
        world_id=WORLD_ID,
        publish=False,
        compare_revision_id=pinned_revision_id,
    )
    assert "rebuild_equivalent_to_pinned_revision" in result.diagnostics
    report = json.loads(
        (
            root
            / "graph_memory"
            / "worlds"
            / WORLD_ID
            / "contribution_rebuild"
            / "latest.json"
        ).read_text(encoding="utf-8")
    )
    assert decision.decision_id in report["identity_decision_ids"]


def test_pinned_rebuild_fails_closed_without_replay_manifest(
    seeded_root: Path, monkeypatch
) -> None:
    """Pinned audits must refuse digests-only revisions that lack a replay plan."""
    root = seeded_root
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_pin_legacy",
        label="Pin Legacy",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Pin Legacy"],
        },
        source_artifact_id="artifact:pin-legacy",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    contrib = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id="artifact:pin-legacy",
        source_revision_id="authored-pin-legacy",
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib
    )
    assert merge.published is True
    pinned_revision_id = merge.revision_id
    assert pinned_revision_id

    real_load = kernel.load_world_graph_revision

    def _strip_manifest(root_path, world_id, revision_id):
        store = real_load(root_path, world_id, revision_id)
        if revision_id != pinned_revision_id:
            return store
        return store.model_copy(update={"contribution_replay_manifest": []})

    monkeypatch.setattr(
        "graph_memory.kernel.contribution_rebuild.load_world_graph_revision",
        _strip_manifest,
    )
    with pytest.raises(ValueError, match="lacks contribution_replay_manifest"):
        kernel.rebuild_from_contributions(
            root,
            world_id=WORLD_ID,
            publish=False,
            compare_revision_id=pinned_revision_id,
        )

def _rebuild_correction_node(
    *,
    node_id: str,
    label: str,
    source_artifact_id: str,
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
        source_revision_id="src-rev-rebuild",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )


def _rebuild_correction_edge(
    *,
    edge_id: str,
    source_node_id: str,
    target_node_id: str,
    predicate: str,
    source_artifact_id: str,
    evidence_ref_id: str,
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
        source_revision_id="src-rev-rebuild",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="resolved_existing",
    )


def test_pinned_rebuild_reproduces_edge_assertion_correction(
    seeded_root: Path,
) -> None:
    root = seeded_root
    node_src = _rebuild_correction_node(
        node_id="npc_rebuild_src",
        label="Rebuild Src",
        source_artifact_id="artifact:rebuild:a",
    )
    node_tgt = _rebuild_correction_node(
        node_id="npc_rebuild_tgt",
        label="Rebuild Tgt",
        source_artifact_id="artifact:rebuild:a",
    )
    edge_x = _rebuild_correction_edge(
        edge_id="edge:npc_rebuild_src:threatens:npc_rebuild_tgt",
        source_node_id="npc_rebuild_src",
        target_node_id="npc_rebuild_tgt",
        predicate="threatens",
        source_artifact_id="artifact:rebuild:a",
        evidence_ref_id="evidence:rebuild:x",
    )
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:rebuild:a",
        source_revision_id="src-rev-a",
        extraction_profile="test_profile",
        accepted_assertions=[node_src, node_tgt, edge_x],
    )
    merge_a = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_a
    )
    assert merge_a.published is True

    edge_xp = _rebuild_correction_edge(
        edge_id="edge:npc_rebuild_tgt:threatens:npc_rebuild_src",
        source_node_id="npc_rebuild_tgt",
        target_node_id="npc_rebuild_src",
        predicate="threatens",
        source_artifact_id="artifact:rebuild:c",
        evidence_ref_id="evidence:rebuild:xp",
    )
    correction = kernel.create_edge_assertion_correction_contribution(
        world_id=WORLD_ID,
        authored_by="gm-operator",
        target_contribution_id=contrib_a.contribution_id,
        target_assertion_id=edge_x.assertion_id,
        replacement_assertion=edge_xp,
        source_artifact_id="artifact:rebuild:c",
        produced_at="2026-08-09T12:00:00Z",
    )
    corrected = kernel.correct_edge_assertion_support(
        root,
        world_id=WORLD_ID,
        contribution=correction,
        expected_parent_revision_id=merge_a.revision_id,
    )
    assert corrected.published is True
    corrected_rev = corrected.revision_id

    rebuild = kernel.rebuild_from_contributions(
        root,
        world_id=WORLD_ID,
        compare_revision_id=corrected_rev,
        publish=False,
    )
    assert "rebuild_equivalent_to_pinned_revision" in rebuild.diagnostics

    pinned = kernel.load_world_graph_revision(root, WORLD_ID, corrected_rev)
    assert pinned.assertion_support[edge_x.assertion_id]["support_state"] == "contradicted"
    assert pinned.assertion_support[edge_xp.assertion_id]["support_state"] == "supported"

    # Tamper correction linkage on disk → pinned rebuild fails closed.
    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_record,
        write_contribution_record,
    )

    loaded = load_contribution_record(root, WORLD_ID, correction.contribution_id)
    tampered = loaded.model_copy(
        update={
            "assertion_corrections": [
                loaded.assertion_corrections[0].model_copy(
                    update={"target_assertion_id": "assertion:tampered"}
                )
            ]
        }
    )
    write_contribution_record(root, WORLD_ID, tampered)
    with pytest.raises(ValueError, match="source digest mismatch"):
        kernel.rebuild_from_contributions(
            root,
            world_id=WORLD_ID,
            compare_revision_id=corrected_rev,
            publish=False,
        )


def test_unpinned_rebuild_legacy_digest_only_head_preserves_ledger_lifecycle(
    seeded_root: Path, monkeypatch
) -> None:
    """Digest-only heads must not invent status=active for superseded contributions."""
    root = seeded_root
    assertion_x = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_legacy_x",
        label="Legacy X",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Legacy X"],
        },
        source_artifact_id="artifact:legacy:a",
        source_revision_id="src-rev-legacy-a",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    assertion_y = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_legacy_y",
        label="Legacy Y",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Legacy Y"],
        },
        source_artifact_id="artifact:legacy:a",
        source_revision_id="src-rev-legacy-a",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:legacy:a",
        source_revision_id="src-rev-legacy-a",
        extraction_profile="test_profile",
        accepted_assertions=[assertion_x, assertion_y],
    )
    merge_a = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_a
    )
    assert merge_a.published is True

    assertion_x_b = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_legacy_x",
        label="Legacy X",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Legacy X"],
        },
        source_artifact_id="artifact:legacy:b",
        source_revision_id="src-rev-legacy-b",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="resolved_existing",
    )
    contrib_b = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:legacy:b",
        source_revision_id="src-rev-legacy-b",
        extraction_profile="test_profile",
        accepted_assertions=[assertion_x_b],
        supersedes_contribution_id=contrib_a.contribution_id,
    )
    supersede = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=contrib_b,
        superseded_contribution_id=contrib_a.contribution_id,
    )
    assert supersede.published is True

    _head, _rev, head_store = kernel.open_current_world_graph(root, WORLD_ID)
    assert contrib_a.contribution_id in (
        head_store.contribution_source_payload_sha256 or {}
    )
    assert list(head_store.contribution_replay_manifest or [])
    assert (
        head_store.assertion_support[assertion_y.assertion_id]["support_state"]
        in {"unsupported", "retracted"}
    )

    real_load = kernel.load_current_world_graph

    def _strip_head_manifest(root_path, world_id):
        head, revision, store = real_load(root_path, world_id)
        return (
            head,
            revision,
            store.model_copy(update={"contribution_replay_manifest": []}),
        )

    monkeypatch.setattr(
        "graph_memory.kernel.contribution_rebuild.load_current_world_graph",
        _strip_head_manifest,
    )

    rebuild = kernel.rebuild_from_contributions(
        root, world_id=WORLD_ID, publish=False
    )
    assert "rebuild_replay_ordered_from_revision_authority" not in rebuild.diagnostics
    assert any(
        d.startswith(
            f"replayed_superseded_support_removal:{contrib_a.contribution_id}"
        )
        for d in rebuild.diagnostics
    )
    assert "rebuild_omitted_replay_manifest_for_legacy_compare" in rebuild.diagnostics
    assert "rebuild_equivalent_to_compared_revision" in rebuild.diagnostics


def test_contradict_without_replacement_rebuilds_pinned_and_unpinned(
    seeded_root: Path,
) -> None:
    """Contradiction-only Q must reconstruct equivalently pinned and as head."""
    root = seeded_root
    node_src = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_contradict_src",
        label="Contradict Src",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Contradict Src"],
        },
        source_artifact_id="artifact:contradict:a",
        source_revision_id="src-rev-a",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    node_tgt = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc_contradict_tgt",
        label="Contradict Tgt",
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Contradict Tgt"],
        },
        source_artifact_id="artifact:contradict:a",
        source_revision_id="src-rev-a",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    edge_x = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id="npc_contradict_src",
        target_node_id="npc_contradict_tgt",
        predicate="threatens",
        label="threatens",
        value={
            "edge_id": "edge:npc_contradict_src:threatens:npc_contradict_tgt",
            "source_node_id": "npc_contradict_src",
            "target_node_id": "npc_contradict_tgt",
            "predicate": "threatens",
            "source_domains": ["manual_seed"],
            "evidence": [
                {
                    "evidence_ref_id": "evidence:contradict:x",
                    "source_artifact_id": "artifact:contradict:a",
                    "source_domain": "manual_seed",
                }
            ],
            "canon_state": "canonical",
        },
        evidence_ref_ids=["evidence:contradict:x"],
        source_artifact_id="artifact:contradict:a",
        source_revision_id="src-rev-a",
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="resolved_existing",
    )
    contrib_a = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:contradict:a",
        source_revision_id="src-rev-a",
        extraction_profile="test_profile",
        accepted_assertions=[node_src, node_tgt, edge_x],
    )
    merge_a = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contrib_a
    )
    assert merge_a.published is True

    contradiction = kernel.create_edge_assertion_contradiction_contribution(
        world_id=WORLD_ID,
        authored_by="gm-operator",
        target_assertion_id=edge_x.assertion_id,
        target_contribution_ids=[contrib_a.contribution_id],
        source_artifact_id="artifact:contradict:c",
        produced_at="2026-08-10T13:00:00Z",
    )
    published = kernel.contradict_edge_assertion_support(
        root,
        world_id=WORLD_ID,
        contribution=contradiction,
        expected_parent_revision_id=merge_a.revision_id,
    )
    assert published.published is True
    q = published.revision_id
    assert q is not None

    pinned_rebuild = kernel.rebuild_from_contributions(
        root,
        world_id=WORLD_ID,
        compare_revision_id=q,
        publish=False,
    )
    assert "rebuild_equivalent_to_pinned_revision" in pinned_rebuild.diagnostics

    unpinned_rebuild = kernel.rebuild_from_contributions(
        root,
        world_id=WORLD_ID,
        publish=False,
    )
    assert (
        "rebuild_equivalent_to_head" in unpinned_rebuild.diagnostics
        or "rebuild_equivalent_to_published_head" in unpinned_rebuild.diagnostics
    )

    pinned = kernel.load_world_graph_revision(root, WORLD_ID, q)
    assert pinned.assertion_support[edge_x.assertion_id]["support_state"] == "contradicted"
    assert pinned.assertion_support[edge_x.assertion_id]["active_contribution_ids"] == []
    assert contrib_a.contribution_id in pinned.assertion_support[edge_x.assertion_id][
        "contradicted_contribution_ids"
    ]
    assert "edge:npc_contradict_src:threatens:npc_contradict_tgt" in pinned.edges
    assert contradiction.contribution_id in (
        pinned.contribution_source_payload_sha256 or {}
    )


def _publish_node_contribution(
    root: Path,
    *,
    node_id: str,
    label: str,
    aliases: list[str],
    artifact_id: str,
    revision_id: str,
) -> None:
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=label,
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": aliases,
        },
        source_artifact_id=artifact_id,
        campaign_scope="longmont-c2",
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    authored = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="graph_review_authored_assertion",
        source_artifact_id=artifact_id,
        source_revision_id=revision_id,
        authored_by="gm",
        accepted_assertions=[assertion],
    )
    merge = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=authored
    )
    assert merge.published is True


def test_rebuild_replays_merge_then_alias_remove(seeded_root: Path) -> None:
    root = seeded_root
    _publish_node_contribution(
        root,
        node_id="npc_rebuild_tgt",
        label="Canonical Rebuild",
        aliases=["Canonical Rebuild"],
        artifact_id="artifact:rebuild-tgt",
        revision_id="authored-rebuild-tgt",
    )
    _publish_node_contribution(
        root,
        node_id="npc_rebuild_src",
        label="Shadow Rebuild",
        aliases=["Shadow Rebuild"],
        artifact_id="artifact:rebuild-src",
        revision_id="authored-rebuild-src",
    )
    _head, parent, store = kernel.open_current_world_graph(root, WORLD_ID)
    merged, merge_decision = kernel.merge_identity(
        store,
        world_id=WORLD_ID,
        source_node_id="npc_rebuild_src",
        target_node_id="npc_rebuild_tgt",
        actor="gm",
        reason="merge shadow rebuild source",
    )
    cleaned, remove_decision = kernel.remove_identity_alias(
        merged,
        world_id=WORLD_ID,
        subject_node_id="npc_rebuild_tgt",
        alias="Shadow Rebuild",
        actor="gm",
        reason="retire shadow rebuild alias",
        root=root,
    )
    published = kernel.publish_world_revision(
        root,
        WORLD_ID,
        cleaned,
        operation_ids=[merge_decision.decision_id, remove_decision.decision_id],
        expected_parent_revision_id=parent.revision_id,
    )
    assert published.revision.revision_id
    live = kernel.load_world_graph_revision(root, WORLD_ID, published.revision.revision_id)

    result = kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=False)
    assert "rebuild_equivalent_to_head" in result.diagnostics
    assert "Shadow Rebuild" not in live.nodes["npc_rebuild_tgt"].aliases
    assert live.aliases.get("shadow rebuild") is None
    assert live.aliases.get("canonical rebuild") == "npc_rebuild_tgt"
    merge_row = next(
        item
        for item in live.identity_decisions
        if item["decision_id"] == merge_decision.decision_id
    )
    assert "Shadow Rebuild" in merge_row["merge_side_effects"]["aliases_added_to_target"]


def test_rebuild_fails_closed_when_alias_remove_precedes_introducing_merge(
    seeded_root: Path,
) -> None:
    root = seeded_root
    _publish_node_contribution(
        root,
        node_id="npc_order_tgt",
        label="Order Target",
        aliases=["Order Target"],
        artifact_id="artifact:order-tgt",
        revision_id="authored-order-tgt",
    )
    _publish_node_contribution(
        root,
        node_id="npc_order_src",
        label="Order Shadow",
        aliases=["Order Shadow"],
        artifact_id="artifact:order-src",
        revision_id="authored-order-src",
    )
    _head, parent, store = kernel.open_current_world_graph(root, WORLD_ID)
    # Materialize the alias without a merge so alias_remove can be recorded first.
    nodes = dict(store.nodes)
    target = nodes["npc_order_tgt"]
    nodes["npc_order_tgt"] = target.model_copy(
        update={"aliases": [*target.aliases, "Order Shadow"]}
    )
    aliases = dict(store.aliases)
    aliases["order shadow"] = "npc_order_tgt"
    planted = store.model_copy(update={"nodes": nodes, "aliases": aliases})
    removed, remove_decision = kernel.remove_identity_alias(
        planted,
        world_id=WORLD_ID,
        subject_node_id="npc_order_tgt",
        alias="Order Shadow",
        actor="gm",
        reason="remove before introducing merge",
        root=root,
    )
    first = kernel.publish_world_revision(
        root,
        WORLD_ID,
        removed,
        operation_ids=[remove_decision.decision_id],
        expected_parent_revision_id=parent.revision_id,
    )
    _h2, parent2, current = kernel.open_current_world_graph(root, WORLD_ID)
    merged, merge_decision = kernel.merge_identity(
        current,
        world_id=WORLD_ID,
        source_node_id="npc_order_src",
        target_node_id="npc_order_tgt",
        actor="gm",
        reason="introducing merge after remove",
    )
    kernel.publish_world_revision(
        root,
        WORLD_ID,
        merged,
        operation_ids=[merge_decision.decision_id],
        expected_parent_revision_id=parent2.revision_id,
    )
    with pytest.raises(ValueError, match="not currently materialized"):
        kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=False)
    assert first.revision.revision_id
