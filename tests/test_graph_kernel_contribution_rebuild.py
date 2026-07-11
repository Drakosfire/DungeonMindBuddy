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

    verification = kernel.rebuild_from_contributions(
        root, world_id=WORLD_ID, publish=False
    )
    assert verification.published is False
    assert "rebuild_equivalent_to_head" in verification.diagnostics
