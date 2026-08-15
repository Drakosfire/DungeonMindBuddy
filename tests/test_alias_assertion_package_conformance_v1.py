"""Fail-closed proofs for alias assertion package reconstruction."""

from __future__ import annotations

import copy
import dataclasses
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind_kernel import (
    alias_assertion_package_conformance_v1 as alias_pkg,
)
from apps.live_control_server.integrations.dungeonmind_kernel.alias_assertion_package_conformance_v1 import (
    IDENTITY_DERIVED_REASON,
    AliasAssertionPackageConformanceError,
    AliasPackageRevisionBinding,
    alias_package_binding_from_attested_revision,
    derive_bundled_alias_assertion_id,
    prove_alias_assertion_package_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    WholeWorldAliasAssertionPolicy,
    WholeWorldSourceHistoryPolicy,
    alias_assertion_policy_from_proof,
    _require_alias_assertion_policy_binding,
)
from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contribution_models import GraphContribution, GraphContributionAssertion
from graph_memory.kernel.contributions import compute_contribution_source_payload_sha256


_DEFAULT_GRAPH_OBJECT = object()


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
    campaign_scope: str | None = "longmont-c2",
    visibility: str | None = "gm",
    epistemic_kind: str | None = "source_derived_candidate",
    temporal_scope: dict[str, object] | None = None,
    evidence_ref_ids: list[str] | None = None,
    source_artifact_id: str | None = "artifact:a1",
    canon_state: str | None = "canonical",
) -> GraphContributionAssertion:
    value: dict[str, object] = {}
    if canon_state is not None:
        value["canon_state"] = canon_state
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
        evidence_ref_ids=list(evidence_ref_ids if evidence_ref_ids is not None else ["evidence:e1"]),
        source_artifact_id=source_artifact_id,
        campaign_scope=campaign_scope,
        visibility=visibility,
        epistemic_kind=epistemic_kind,
        temporal_scope=temporal_scope,
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


def _support(
    assertion: GraphContributionAssertion,
    *,
    support_state: str = "supported",
    graph_object_id: str | None | object = _DEFAULT_GRAPH_OBJECT,
    evidence_ref_ids: list[str] | None = None,
    source_artifact_ids: list[str] | None = None,
) -> dict[str, object]:
    cid = assertion.contribution_id
    refs = (
        list(evidence_ref_ids)
        if evidence_ref_ids is not None
        else list(assertion.evidence_ref_ids)
    )
    artifacts = (
        list(source_artifact_ids)
        if source_artifact_ids is not None
        else ([assertion.source_artifact_id] if assertion.source_artifact_id else [])
    )
    target = (
        assertion.subject_node_id
        if graph_object_id is _DEFAULT_GRAPH_OBJECT
        else graph_object_id
    )
    return DurableAssertionSupport(
        assertion_id=assertion.assertion_id,
        active_contribution_ids=[cid],
        evidence_ref_ids=refs,
        source_artifact_ids=artifacts,
        support_state=support_state,  # type: ignore[arg-type]
        assertion_kind=assertion.assertion_kind,
        graph_object_id=target,  # type: ignore[arg-type]
        per_contribution_evidence_ref_ids={cid: refs},
        per_contribution_source_artifact_ids={cid: artifacts},
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


def _manifest(
    *,
    world_id: str = "test",
    revision_id: str = "rev:test",
    payload: str = "0" * 64,
) -> SimpleNamespace:
    return SimpleNamespace(
        world_id=world_id,
        revision_id=revision_id,
        graph_payload_sha256=payload,
    )


def _binding(
    store: SimpleNamespace,
    *,
    world_id: str = "test",
    revision_id: str = "rev:test",
    payload: str = "0" * 64,
):
    """In-memory reconstruction helper. This is not revision attestation."""
    return AliasPackageRevisionBinding(
        world_id=world_id,
        canonical_revision_id=revision_id,
        canonical_graph_payload_sha256=payload,
        store_semantic_sha256=alias_pkg.store_semantic_sha256(store),
        _token=alias_pkg._ALIAS_PACKAGE_BINDING_TOKEN,
    )


def _publish_distinct_worlds(tmp_path: Path):
    from graph_memory.union_supergraph.load import (
        DEFAULT_FIXTURE_PATH,
        load_union_supergraph_store,
        parse_union_supergraph_store,
    )
    from graph_memory.world_supergraph import publish_world_graph_revision
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
        _load_exact_buddy_revision,
    )

    store_a = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    published_a = publish_world_graph_revision(
        tmp_path, "world-a", store_a, operation_ids=["op:a"]
    )
    payload = copy.deepcopy(store_a.model_dump(mode="json", by_alias=True))
    first_node_id = next(iter(payload["nodes"]))
    payload["nodes"][first_node_id]["label"] = (
        str(payload["nodes"][first_node_id]["label"]) + " B"
    )
    store_b = parse_union_supergraph_store(payload)
    published_b = publish_world_graph_revision(
        tmp_path, "world-b", store_b, operation_ids=["op:b"]
    )
    manifest_a, loaded_a = _load_exact_buddy_revision(
        root=tmp_path,
        world_id="world-a",
        revision_id=published_a.revision.revision_id,
    )
    manifest_b, loaded_b = _load_exact_buddy_revision(
        root=tmp_path,
        world_id="world-b",
        revision_id=published_b.revision.revision_id,
    )
    return manifest_a, loaded_a, manifest_b, loaded_b


def _prove(store: SimpleNamespace, contributions: dict[str, GraphContribution], **kwargs):
    binding = kwargs.pop("binding", None) or _binding(store)
    return prove_alias_assertion_package_v1(
        store,  # type: ignore[arg-type]
        binding=binding,
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
    policy = alias_assertion_policy_from_proof(proof, binding=_binding(store))
    assert policy.proven_alias_blocker_element_ids == frozenset(
        {"node:node:thrin:field:aliases"}
    )
    assert policy.world_id == "test"
    assert policy.canonical_revision_id == "rev:test"
    assert policy.canonical_graph_payload_sha256 == "0" * 64
    assert policy.package_proof_sha256


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


def test_identity_derived_residuals_refuse_alias_package_policy() -> None:
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
    with pytest.raises(ValueError, match="has not passed"):
        alias_assertion_policy_from_proof(proof, binding=_binding(store))


def _explicit_alias_fixture(**assertion_kwargs):
    node = _node("node:x", label="X", aliases=["X", "Y"])
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Y",
        label="Y",
        **assertion_kwargs,
    )
    return node, assertion


def test_missing_target_node_fails() -> None:
    store, contributions = _store(nodes={}, assertions=[])
    store.aliases = {"Orphan": "node:missing"}
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "missing_target_node" in proof.residuals[0].diagnostics or proof.residuals[
        0
    ].reason_code in {"alias_not_source_grounded", "non_derivable_key_without_source_alias"}
    with pytest.raises(ValueError):
        alias_assertion_policy_from_proof(proof, binding=_binding(store))


def test_assertion_subject_not_current_target_fails() -> None:
    node = _node("node:x", label="X", aliases=["X", "Y"])
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:other",
        contribution_id="contribution:2",
        alias="Y",
        label="Y",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    store.assertion_support[assertion.assertion_id] = _support(
        assertion, graph_object_id="node:x"
    )
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "assertion_subject_not_current_target" in proof.residuals[0].diagnostics


def test_support_not_supported_fails() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    store.assertion_support[assertion.assertion_id] = _support(
        assertion, support_state="unsupported"
    )
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "support_not_supported" in proof.residuals[0].diagnostics


def test_contribution_absent_from_replay_manifest_fails() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    store.contribution_replay_manifest = []
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "contribution_not_in_revision_replay_manifest" in proof.residuals[0].diagnostics


def test_contribution_inactive_in_revision_fails() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    store.contribution_replay_manifest[0].status = "superseded"
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "contribution_not_active_in_revision" in proof.residuals[0].diagnostics


def test_mutable_contribution_ledger_inactive_fails() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    contributions[assertion.contribution_id].status = "retracted"
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "contribution_ledger_not_active" in proof.residuals[0].diagnostics


def test_source_payload_digest_differs_from_replay_digest_fails() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    store.contribution_replay_manifest[0].source_payload_sha256 = "f" * 64
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "contribution_source_digest_drift" in proof.residuals[0].diagnostics


def test_per_contribution_evidence_lineage_drift_fails() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    store.assertion_support[assertion.assertion_id] = _support(
        assertion, evidence_ref_ids=["evidence:other"]
    )
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "per_contribution_evidence_lineage_drift" in proof.residuals[0].diagnostics


def test_per_contribution_artifact_lineage_drift_fails() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    store.assertion_support[assertion.assertion_id] = _support(
        assertion, source_artifact_ids=["artifact:other"]
    )
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "per_contribution_source_artifact_lineage_drift" in proof.residuals[0].diagnostics


def test_empty_evidence_refs_fail() -> None:
    node, assertion = _explicit_alias_fixture(evidence_ref_ids=[])
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "empty_evidence_refs" in proof.residuals[0].diagnostics


def test_dangling_evidence_ref_fails() -> None:
    node, assertion = _explicit_alias_fixture(evidence_ref_ids=["evidence:missing"])
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "dangling_evidence_ref" in proof.residuals[0].diagnostics


def test_dangling_source_artifact_fails() -> None:
    node, assertion = _explicit_alias_fixture(source_artifact_id="artifact:missing")
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "dangling_source_artifact" in proof.residuals[0].diagnostics


def test_alias_text_not_explicitly_present_fails() -> None:
    node = _node("node:x", label="X", aliases=["X", "Y"])
    assertion = _assertion(
        assertion_id="assertion:alias-nope",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Nope",
        label="Nope",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert proof.residuals[0].reason_code == "alias_not_source_grounded"


def test_alias_label_value_disagreement_fails() -> None:
    node = _node("node:x", label="X", aliases=["X", "Y"])
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Y",
        label="Z",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "alias_label_value_disagree" in proof.residuals[0].diagnostics


def test_ambiguous_derived_assertion_id_collision_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        alias_pkg,
        "derive_bundled_alias_assertion_id",
        lambda **_kwargs: "assertion:collision",
    )
    node = _node("node:x", label="X", aliases=["X", "A", "B"])
    assertion = _assertion(
        assertion_id="assertion:node-x",
        kind="node",
        subject="node:x",
        contribution_id="contribution:1",
        aliases=["A", "B"],
        label="X",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    with pytest.raises(AliasAssertionPackageConformanceError) as exc:
        _prove(store, contributions)
    assert exc.value.code == "alias_assertion_id_collision"


def test_partial_package_refuses_policy() -> None:
    node = _node("node:x", label="X", aliases=["X", "Y", "Z"])
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
    assert proof.passed is False
    assert proof.residuals
    assert any(row.alias_value == "Z" for row in proof.residuals)
    with pytest.raises(ValueError, match="has not passed"):
        alias_assertion_policy_from_proof(proof, binding=_binding(store))


def test_null_campaign_scope_stays_world_universal() -> None:
    node, assertion = _explicit_alias_fixture(campaign_scope=None)
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    store.campaign_id = "longmont-c2"
    proof = _prove(store, contributions)
    assert proof.passed is True
    row = proof.package_rows[0]
    metadata = row.dungeonmind_alias_record["assertion_metadata"]
    assert metadata["campaign_scope"] is None
    assert row.metadata_derivation["campaign_scope"] == "source_assertion_null_world_universal"


def test_source_vs_current_node_metadata_conflict_stops() -> None:
    node = _node(
        "node:x",
        label="X",
        aliases=["X", "Y"],
        visibility="player",
        epistemic_kind="inferred",
        canon_state="provisional",
    )
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Y",
        label="Y",
        visibility="gm",
        epistemic_kind="source_derived_candidate",
        canon_state="canonical",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "source_current_visibility_conflict" in proof.residuals[0].diagnostics


def test_source_metadata_preserved_when_node_unrecognized() -> None:
    node = _node(
        "node:x",
        label="X",
        aliases=["X", "Y"],
        visibility="not-a-visibility",
        epistemic_kind="not-an-epistemic",
        canon_state="not-a-canon",
    )
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Y",
        label="Y",
        visibility="gm",
        epistemic_kind="source_derived_candidate",
        canon_state="canonical",
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is True
    row = proof.package_rows[0]
    metadata = row.dungeonmind_alias_record["assertion_metadata"]
    assert metadata["visibility"] == "gm"
    assert metadata["epistemic_kind"] == "source_derived_candidate"
    assert metadata["canon_state"] == "canonical"
    assert row.metadata_derivation["visibility"] == "source_assertion"
    assert row.metadata_derivation["epistemic_kind"] == "source_assertion"
    assert row.metadata_derivation["canon_state"] == "source_assertion_value"


def test_current_node_fallback_when_source_absent() -> None:
    node = _node("node:x", label="X", aliases=["X", "Y"])
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Y",
        label="Y",
        visibility=None,
        epistemic_kind=None,
        canon_state=None,
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is True
    row = proof.package_rows[0]
    assert row.metadata_derivation["visibility"] == "current_node_state"
    assert row.metadata_derivation["epistemic_kind"] == "current_node_state"
    assert row.metadata_derivation["canon_state"] == "current_node_state"
    metadata = row.dungeonmind_alias_record["assertion_metadata"]
    assert metadata["visibility"] == "gm"
    assert metadata["epistemic_kind"] == "source_derived_candidate"
    assert metadata["canon_state"] == "canonical"


def test_unrecognized_current_node_fallback_stops() -> None:
    node = _node(
        "node:x",
        label="X",
        aliases=["X", "Y"],
        visibility="not-a-visibility",
        epistemic_kind="not-an-epistemic",
        canon_state="not-a-canon",
    )
    assertion = _assertion(
        assertion_id="assertion:alias-y",
        kind="alias",
        subject="node:x",
        contribution_id="contribution:2",
        alias="Y",
        label="Y",
        visibility=None,
        epistemic_kind=None,
        canon_state=None,
    )
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert proof.residuals[0].diagnostics[0] in {
        "unrecognized_visibility",
        "unrecognized_epistemic_kind",
        "unrecognized_canon_state",
    }


def test_session_refs_do_not_infer_fictional_time() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is True
    row = proof.package_rows[0]
    metadata = row.dungeonmind_alias_record["assertion_metadata"]
    assert metadata["session_refs"] == ["session-25"]
    assert metadata["temporal_scope"]["kind"] == "unknown"
    assert row.metadata_derivation["temporal_scope"] == "unknown_no_fictional_time_mapping"
    assert metadata["temporal_scope"]["kind"] != "world_timeless"


def test_unknown_temporal_scope_not_upgraded_to_world_timeless() -> None:
    node, assertion = _explicit_alias_fixture(temporal_scope={"kind": "unknown"})
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is True
    metadata = proof.package_rows[0].dungeonmind_alias_record["assertion_metadata"]
    assert metadata["temporal_scope"]["kind"] == "unknown"


def test_ungoverned_fictional_time_mapping_stops() -> None:
    node, assertion = _explicit_alias_fixture(temporal_scope={"kind": "world_timeless"})
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is False
    assert "ungoverned_fictional_time_mapping" in proof.residuals[0].diagnostics


def test_passing_row_records_every_metadata_derivation() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    assert proof.passed is True
    derivation = proof.package_rows[0].metadata_derivation
    for key in (
        "campaign_scope",
        "visibility",
        "epistemic_kind",
        "canon_state",
        "evidence_ref_ids",
        "session_refs",
        "temporal_scope",
    ):
        assert derivation.get(key)
        assert derivation[key] != "hidden_metadata_fallback"


def test_wrong_world_revision_payload_alias_policy_fails_closed() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    policy = alias_assertion_policy_from_proof(proof, binding=_binding(store))
    with pytest.raises(ValueError, match="does not match"):
        _require_alias_assertion_policy_binding(
            policy=policy,
            manifest=_manifest(world_id="other-world"),
            world_id="other-world",
            revision_id="rev:test",
        )
    with pytest.raises(ValueError, match="does not match"):
        _require_alias_assertion_policy_binding(
            policy=policy,
            manifest=_manifest(revision_id="rev:other"),
            world_id="test",
            revision_id="rev:other",
        )
    with pytest.raises(ValueError, match="does not match"):
        _require_alias_assertion_policy_binding(
            policy=policy,
            manifest=_manifest(payload="1" * 64),
            world_id="test",
            revision_id="rev:test",
        )
    _require_alias_assertion_policy_binding(
        policy=policy,
        manifest=_manifest(),
        world_id="test",
        revision_id="rev:test",
    )


def test_analyzer_trusts_manifest_revision_not_separate_argument() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    proof = _prove(store, contributions)
    policy = alias_assertion_policy_from_proof(proof, binding=_binding(store))
    with pytest.raises(ValueError, match="do not match attested manifest"):
        _require_alias_assertion_policy_binding(
            policy=policy,
            manifest=_manifest(),
            world_id="test",
            revision_id="rev:other",
        )
    with pytest.raises(ValueError, match="do not match attested manifest"):
        _require_alias_assertion_policy_binding(
            policy=policy,
            manifest=_manifest(),
            world_id="other-world",
            revision_id="rev:test",
        )


def test_legacy_alias_policy_skips_revision_binding() -> None:
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        LEGACY_ALIAS_ASSERTION_POLICY,
    )

    _require_alias_assertion_policy_binding(
        policy=LEGACY_ALIAS_ASSERTION_POLICY,
        manifest=_manifest(world_id="anything", revision_id="rev:anything", payload="f" * 64),
        world_id="anything",
        revision_id="rev:anything",
    )


def test_prove_store_a_with_store_b_pins_is_refused() -> None:
    node_a, assertion_a = _explicit_alias_fixture()
    store_a, contrib_a = _store(nodes={node_a.node_id: node_a}, assertions=[assertion_a])
    node_b = _node("node:b", label="B", aliases=["B", "Other"])
    assertion_b = _assertion(
        assertion_id="assertion:alias-other",
        kind="alias",
        subject="node:b",
        contribution_id="contribution:b",
        alias="Other",
        label="Other",
    )
    store_b, _contrib_b = _store(nodes={node_b.node_id: node_b}, assertions=[assertion_b])
    binding_b = _binding(
        store_b,
        world_id="world-B",
        revision_id="rev:B",
        payload="b" * 64,
    )
    with pytest.raises(AliasAssertionPackageConformanceError) as exc:
        _prove(store_a, contrib_a, binding=binding_b)
    assert exc.value.code == "alias_package_store_binding_mismatch"


def test_expected_pins_for_store_b_on_store_a_revision_are_refused(
    tmp_path: Path,
) -> None:
    manifest_a, loaded_a, manifest_b, _loaded_b = _publish_distinct_worlds(tmp_path)
    with pytest.raises(AliasAssertionPackageConformanceError) as exc:
        alias_package_binding_from_attested_revision(
            root=tmp_path,
            world_id=manifest_a.world_id,
            revision_id=manifest_a.revision_id,
            expected_world_id=manifest_b.world_id,
            expected_revision_id=manifest_b.revision_id,
            expected_graph_payload_sha256=manifest_b.graph_payload_sha256,
            store=loaded_a,
        )
    assert exc.value.code == "alias_package_binding_pin_mismatch"


def test_manifest_b_plus_store_a_expected_b_is_refused_at_binding_creation(
    tmp_path: Path,
) -> None:
    manifest_a, loaded_a, manifest_b, loaded_b = _publish_distinct_worlds(tmp_path)
    with pytest.raises(TypeError):
        alias_package_binding_from_attested_revision(
            manifest=manifest_b,
            store=loaded_a,
            expected_world_id=manifest_b.world_id,
            expected_revision_id=manifest_b.revision_id,
            expected_graph_payload_sha256=manifest_b.graph_payload_sha256,
        )
    with pytest.raises(AliasAssertionPackageConformanceError) as exc:
        alias_package_binding_from_attested_revision(
            root=tmp_path,
            world_id=manifest_b.world_id,
            revision_id=manifest_b.revision_id,
            expected_world_id=manifest_b.world_id,
            expected_revision_id=manifest_b.revision_id,
            expected_graph_payload_sha256=manifest_b.graph_payload_sha256,
            store=loaded_a,
        )
    assert exc.value.code == "alias_package_store_revision_mismatch"
    binding_b = alias_package_binding_from_attested_revision(
        root=tmp_path,
        world_id=manifest_b.world_id,
        revision_id=manifest_b.revision_id,
        expected_world_id=manifest_b.world_id,
        expected_revision_id=manifest_b.revision_id,
        expected_graph_payload_sha256=manifest_b.graph_payload_sha256,
        store=loaded_b,
    )
    assert binding_b.world_id == manifest_b.world_id
    assert binding_b.canonical_revision_id == manifest_b.revision_id
    assert binding_b.canonical_graph_payload_sha256 == manifest_b.graph_payload_sha256
    assert binding_b.store_semantic_sha256 == alias_pkg.store_semantic_sha256(loaded_b)
    assert binding_b.store_semantic_sha256 != alias_pkg.store_semantic_sha256(loaded_a)


def test_policy_factory_refuses_mismatched_binding() -> None:
    node_a, assertion_a = _explicit_alias_fixture()
    store_a, contrib_a = _store(nodes={node_a.node_id: node_a}, assertions=[assertion_a])
    proof_a = _prove(store_a, contrib_a)
    node_b = _node("node:b", label="B", aliases=["B", "Other"])
    assertion_b = _assertion(
        assertion_id="assertion:alias-other",
        kind="alias",
        subject="node:b",
        contribution_id="contribution:b",
        alias="Other",
        label="Other",
    )
    store_b, contrib_b = _store(nodes={node_b.node_id: node_b}, assertions=[assertion_b])
    binding_b = _binding(
        store_b,
        world_id="world-B",
        revision_id="rev:B",
        payload="b" * 64,
    )
    proof_b = _prove(store_b, contrib_b, binding=binding_b)
    with pytest.raises(ValueError, match="does not match attested revision binding"):
        alias_assertion_policy_from_proof(proof_a, binding=binding_b)
    policy_b = alias_assertion_policy_from_proof(proof_b, binding=binding_b)
    assert policy_b.world_id == "world-B"


def test_prove_rejects_caller_claimed_pin_kwargs() -> None:
    node, assertion = _explicit_alias_fixture()
    store, contributions = _store(nodes={node.node_id: node}, assertions=[assertion])
    with pytest.raises(TypeError):
        prove_alias_assertion_package_v1(
            store,  # type: ignore[arg-type]
            world_id="world-B",
            canonical_revision_id="rev:B",
            canonical_graph_payload_sha256="b" * 64,
            contribution_loader=contributions.__getitem__,
        )


def test_public_binding_constructor_rejects_arbitrary_pins() -> None:
    with pytest.raises(TypeError, match="not a public constructor"):
        AliasPackageRevisionBinding(
            world_id="world-B",
            canonical_revision_id="rev:B",
            canonical_graph_payload_sha256="b" * 64,
            store_semantic_sha256="0" * 64,
            _token=object(),
        )


def test_public_alias_policy_constructor_rejects_arbitrary_allowlist() -> None:
    with pytest.raises(TypeError, match="not a public constructor"):
        WholeWorldAliasAssertionPolicy(
            policy_id="alias_assertion_package_v1",
            world_id="eldyrwild",
            canonical_revision_id="rev:test",
            canonical_graph_payload_sha256="0" * 64,
            proven_alias_blocker_element_ids=frozenset(
                {"node:node:captain-lysandra-ironveil:field:aliases"}
            ),
            package_proof_sha256="0" * 64,
            _token=object(),
        )
    import apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 as v4

    assert not hasattr(v4, "alias_assertion_policy_from_element_ids")


def test_source_history_policy_public_fields_unchanged() -> None:
    names = {item.name for item in dataclasses.fields(WholeWorldSourceHistoryPolicy)}
    assert names == {"policy_id", "proven_node_state_history_element_ids", "_token"}
    assert "world_id" not in names
    assert "canonical_revision_id" not in names
    assert "canonical_graph_payload_sha256" not in names

