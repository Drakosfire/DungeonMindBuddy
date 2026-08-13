"""Fail-closed proofs for alias assertion package reconstruction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind_kernel.alias_assertion_package_conformance_v1 import (
    IDENTITY_DERIVED_REASON,
    AliasAssertionPackageConformanceError,
    derive_bundled_alias_assertion_id,
    prove_alias_assertion_package_v1,
)
from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contribution_models import GraphContribution, GraphContributionAssertion
from graph_memory.kernel.contributions import compute_contribution_source_payload_sha256


def _node(
    node_id: str,
    *,
    label: str,
    aliases: list[str],
    **state: object,
) -> SimpleNamespace:
    return SimpleNamespace(
        node_id=node_id,
        kind="npc",
        label=label,
        aliases=aliases,
        state={
            "visibility": "gm",
            "epistemic_kind": "source_derived_candidate",
            "canon_state": "canonical",
            **state,
        },
    )


def _assertion(
    *,
    assertion_id: str,
    kind: str,
    subject: str,
    contribution_id: str,
    aliases: list[str] | None = None,
    alias: str | None = None,
    label: str | None = None,
) -> GraphContributionAssertion:
    value: dict[str, object] = {"canon_state": "canonical"}
    if aliases is not None:
        value["aliases"] = aliases
    if alias is not None:
        value["alias"] = alias
    return GraphContributionAssertion(
        assertion_id=assertion_id,
        assertion_kind=kind,  # type: ignore[arg-type]
        subject_node_id=subject,
        label=label,
        value=value,
        evidence_ref_ids=["evidence:e1"],
        source_artifact_id="artifact:a1",
        campaign_scope="longmont-c2",
        visibility="gm",
        epistemic_kind="source_derived_candidate",
        acceptance_state="accepted",
        contribution_id=contribution_id,
    )


def _contribution(assertion: GraphContributionAssertion) -> GraphContribution:
    return GraphContribution(
        contribution_id=assertion.contribution_id,
        world_id="test",
        source_kind="source_extraction",
        produced_at="2026-01-01T00:00:00Z",
        status="active",
        accepted_assertions=[assertion],
    )


def _support(assertion: GraphContributionAssertion) -> dict[str, object]:
    cid = assertion.contribution_id
    return DurableAssertionSupport(
        assertion_id=assertion.assertion_id,
        active_contribution_ids=[cid],
        evidence_ref_ids=["evidence:e1"],
        source_artifact_ids=["artifact:a1"],
        support_state="supported",
        assertion_kind=assertion.assertion_kind,
        graph_object_id=assertion.subject_node_id,
        per_contribution_evidence_ref_ids={cid: ["evidence:e1"]},
        per_contribution_source_artifact_ids={cid: ["artifact:a1"]},
    ).model_dump(mode="json")


def _store(
    *,
    nodes: dict[str, SimpleNamespace],
    assertions: list[GraphContributionAssertion],
    aliases: dict[str, str] | None = None,
    redirects: list[SimpleNamespace] | None = None,
) -> tuple[SimpleNamespace, dict[str, GraphContribution]]:
    contributions = {assertion.contribution_id: _contribution(assertion) for assertion in assertions}
    digest_map = {
        cid: compute_contribution_source_payload_sha256(contrib)
        for cid, contrib in contributions.items()
    }
    store = SimpleNamespace(
        nodes=nodes,
        aliases=aliases or {},
        identity_redirects=redirects or [],
        identity_merge_records=[],
        assertion_support={
            assertion.assertion_id: _support(assertion) for assertion in assertions
        },
        contribution_source_payload_sha256=digest_map,
        contribution_replay_manifest=[
            SimpleNamespace(
                contribution_id=cid,
                status="active",
                source_payload_sha256=digest,
            )
            for cid, digest in digest_map.items()
        ],
        evidence={"evidence:e1": SimpleNamespace(session_id="session-25")},
        source_artifacts={"artifact:a1": SimpleNamespace()},
    )
    return store, contributions


def _prove(store: SimpleNamespace, contributions: dict[str, GraphContribution], **kwargs):
    return prove_alias_assertion_package_v1(
        store,  # type: ignore[arg-type]
        world_id="test",
        canonical_revision_id="rev:test",
        canonical_graph_payload_sha256="0" * 64,
        contribution_loader=contributions.__getitem__,
        **kwargs,
    )


def test_bundled_node_alias_is_reconstructable() -> None:
    node = _node("node:thrin", label="Thrin", aliases=["Thrin", "Thrin Branchborn"])
    assertion = _assertion(
        assertion_id="assertion:thrin",
        kind="node",
        subject="node:thrin",
        contribution_id="contribution:1",
        aliases=["Thrin", "Thrin Branchborn"],
        label="Thrin",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is True
    assert proof.residual_count == 0
    assert proof.blocker_element_ids == ["node:node:thrin:field:aliases"]
    assert proof.package_rows[0].source_form == "bundled_node_alias"
    assert proof.package_rows[0].alias_value == "Thrin Branchborn"
    assert proof.package_rows[0].dungeonmind_assertion_id == derive_bundled_alias_assertion_id(
        world_id="test",
        target_node_id="node:thrin",
        source_buddy_node_assertion_id="assertion:thrin",
        alias_value="Thrin Branchborn",
    )


def test_explicit_alias_assertion_preserves_source_id() -> None:
    node = _node("node:x", label="X", aliases=["X", "Y"])
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Y",
        label="Y",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is True
    assert proof.package_rows[0].source_form == "explicit_alias_assertion"
    assert proof.package_rows[0].dungeonmind_assertion_id == "assertion:alias-y"


def test_canonical_label_is_not_a_blocker() -> None:
    node = _node("node:x", label="X", aliases=["X"])
    store, contributions = _store(nodes={node.node_id: node}, assertions=[])
    proof = _prove(store, contributions)
    assert proof.blocker_element_ids == []
    assert proof.package_rows == []
    assert proof.passed is False


def test_duplicate_text_from_distinct_assertions_is_not_collapsed() -> None:
    node = _node("node:x", label="X", aliases=["X", "Y"])
    a1 = _assertion(
        assertion_id="assertion:a1",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:a",
        alias="Y",
        label="Y",
    )
    a2 = _assertion(
        assertion_id="assertion:a2",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:b",
        alias="Y",
        label="Y",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[a1, a2])
    proof = _prove(store, contributions)
    assert proof.passed is True
    assert len(proof.package_rows) == 2
    assert {row.buddy_source_assertion_id for row in proof.package_rows} == {
        "assertion:a1",
        "assertion:a2",
    }


def test_identity_derived_alias_is_residual() -> None:
    survivor = _node(
        "item_foot",
        label="Foot of a statue",
        aliases=["Foot of a statue", "Enormous boulder"],
        identity_state="survivor",
    )
    merged = _node(
        "item_boulder",
        label="Enormous boulder",
        aliases=["Enormous boulder"],
        merged_into="item_foot",
        memory_state="merged_away",
    )
    assertion = _assertion(
        assertion_id="assertion:foot",
        kind="node",
        subject="item_foot",
        contribution_id="contribution:1",
        aliases=["Foot of a statue"],
        label="Foot of a statue",
    )
    redirect = SimpleNamespace(
        redirect_id="redirect:1",
        from_node_id="item_boulder",
        to_node_id="item_foot",
        status="active",
    )
    store, contributions = _store(
        nodes={survivor.node_id: survivor, merged.node_id: merged},
        assertions=[assertion],
        redirects=[redirect],
    )
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert proof.residual_count == 1
    residual = proof.residuals[0]
    assert residual.reason_code == IDENTITY_DERIVED_REASON
    assert residual.alias_value == "Enormous boulder"
    assert "item_boulder" in residual.source_candidate_ids
    assert proof.covered_blocker_element_ids == []


def test_digest_drift_fails_closed() -> None:
    node = _node("node:x", label="X", aliases=["X", "Y"])
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Y",
        label="Y",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    store.contribution_source_payload_sha256[assertion.contribution_id] = "0" * 64
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert proof.residuals[0].reason_code == "alias_not_source_grounded"
    assert "contribution_source_digest_drift" in proof.residuals[0].diagnostics


def test_stale_inventory_refuses() -> None:
    node = _node("node:x", label="X", aliases=["X", "Y"])
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Y",
        label="Y",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    with pytest.raises(AliasAssertionPackageConformanceError) as exc:
        _prove(store, contributions, expected_blocker_element_ids=["node:other:field:aliases"])
    assert exc.value.code == "stale_alias_blocker_inventory"


def test_child_id_is_deterministic() -> None:
    first = derive_bundled_alias_assertion_id(
        world_id="eldyrwild",
        target_node_id="node:thrin",
        source_buddy_node_assertion_id="assertion:1275811e41cbb14c",
        alias_value="Thrin Branchborn",
    )
    second = derive_bundled_alias_assertion_id(
        world_id="eldyrwild",
        target_node_id="node:thrin",
        source_buddy_node_assertion_id="assertion:1275811e41cbb14c",
        alias_value="Thrin Branchborn",
    )
    other = derive_bundled_alias_assertion_id(
        world_id="eldyrwild",
        target_node_id="node:thrin",
        source_buddy_node_assertion_id="assertion:1275811e41cbb14c",
        alias_value="Other",
    )
    assert first == second
    assert first.startswith("assertion:cutover-alias:")
    assert first != other
