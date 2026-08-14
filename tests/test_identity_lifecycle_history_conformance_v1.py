"""Fail-closed proofs for identity-lifecycle shadow reconstructability."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind_kernel.identity_lifecycle_history_conformance_v1 import (
    IdentityLifecycleHistoryConformanceError,
    prove_alias_remove_survivor_lineage,
    prove_identity_lifecycle_history_through_alias_remove,
    prove_identity_lifecycle_history_v1,
)
from graph_memory.kernel.identity_models import (
    IdentityDecisionRecord,
    IdentityMergeSideEffects,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    ClassifiedElement,
    SemanticClassification,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    LEGACY_SOURCE_HISTORY_POLICY,
    WholeWorldSourceHistoryPolicy,
    _contribution_history_classified_items,
    source_history_policy_from_identity_lifecycle_proof,
)


def _decision(
    *,
    decision_id: str = "dec-merge-1",
    kind: str = "merge",
    subject: str = "node_a",
    target: str | None = "node_b",
    status: str = "active",
    alias: str | None = None,
    affected: list[str] | None = None,
    merge_side_effects: IdentityMergeSideEffects | None | object = ...,
) -> dict[str, object]:
    if kind == "merge":
        if merge_side_effects is ...:
            side_effects = IdentityMergeSideEffects(aliases_added_to_target=["Shadow"])
        else:
            side_effects = merge_side_effects  # type: ignore[assignment]
    else:
        side_effects = None if merge_side_effects is ... else merge_side_effects  # type: ignore[assignment]
    return IdentityDecisionRecord(
        decision_id=decision_id,
        world_id="test",
        decision_kind=kind,  # type: ignore[arg-type]
        created_at="2026-01-01T00:00:00Z",
        actor="test",
        reason="test identity decision",
        subject_node_id=subject,
        target_node_id=target,
        affected_node_ids=affected if affected is not None else [item for item in (subject, target) if item],
        alias=alias,
        status=status,  # type: ignore[arg-type]
        merge_side_effects=side_effects,  # type: ignore[arg-type]
    ).model_dump(mode="json")


def _redirect(
    *,
    decision_id: str = "dec-merge-1",
    from_node_id: str = "node_a",
    to_node_id: str = "node_b",
    status: str = "active",
) -> SimpleNamespace:
    return SimpleNamespace(
        redirect_id=f"redirect:{decision_id}",
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        status=status,
    )


def _node(node_id: str, **state: object) -> SimpleNamespace:
    return SimpleNamespace(node_id=node_id, state=dict(state))


def _store(
    *,
    source_state: dict[str, object] | None = None,
    survivor_state: dict[str, object] | None = None,
    extra_nodes: dict[str, SimpleNamespace] | None = None,
    decisions: list[dict[str, object]] | None = None,
    redirects: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    source = _node(
        "node_a",
        **(
            source_state
            or {
                "memory_state": "merged_away",
                "identity_canon_state": "merged_away",
                "merged_into": "node_b",
                "last_identity_decision_id": "dec-merge-1",
            }
        ),
    )
    survivor = _node(
        "node_b",
        **(
            survivor_state
            or {
                "identity_state": "survivor",
                "identity_canon_state": "canonical",
                "last_identity_decision_id": "dec-merge-1",
            }
        ),
    )
    nodes = {"node_a": source, "node_b": survivor}
    if extra_nodes:
        nodes.update(extra_nodes)
    return SimpleNamespace(
        nodes=nodes,
        identity_decisions=decisions if decisions is not None else [_decision()],
        identity_redirects=redirects if redirects is not None else [_redirect()],
    )


def _prove(store: SimpleNamespace):
    return prove_identity_lifecycle_history_v1(
        store,
        world_id="test",
        canonical_revision_id="rev:test",
        canonical_graph_payload_sha256="0" * 64,
    )


def _prove_through(store: SimpleNamespace):
    return prove_identity_lifecycle_history_through_alias_remove(
        store,
        world_id="test",
        canonical_revision_id="rev:test",
        canonical_graph_payload_sha256="0" * 64,
    )


def _alias_remove_store(
    *,
    decisions: list[dict[str, object]] | None = None,
    survivor_pointer: str = "dec-remove-1",
    extra_nodes: dict[str, SimpleNamespace] | None = None,
    source_state: dict[str, object] | None = None,
    survivor_state: dict[str, object] | None = None,
    redirects: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return _store(
        source_state=source_state,
        survivor_state=survivor_state
        or {
            "identity_state": "survivor",
            "identity_canon_state": "canonical",
            "last_identity_decision_id": survivor_pointer,
        },
        extra_nodes=extra_nodes,
        decisions=decisions
        or [
            _decision(),
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
            ),
        ],
        redirects=redirects,
    )


def test_coherent_merge_shadow_is_reconstructable() -> None:
    proof = _prove(_store())
    assert proof.passed is True
    assert proof.unresolved_element_ids == []
    assert proof.reconstructable_count == 4
    assert proof.field_counts == {
        "identity_state": 1,
        "merged_into": 1,
        "last_identity_decision_id": 2,
    }
    assert set(proof.element_ids) == {
        "node:node_a:state:last_identity_decision_id",
        "node:node_a:state:merged_into",
        "node:node_b:state:identity_state",
        "node:node_b:state:last_identity_decision_id",
    }
    assert all(row.reconstructable for row in proof.rows)


def test_t13_adversarial_dangling_decision_fails() -> None:
    store = _store(
        source_state={
            "memory_state": "merged_away",
            "identity_canon_state": "merged_away",
            "merged_into": "node_b",
            "last_identity_decision_id": "nonexistent",
        },
        survivor_state={
            "identity_state": "survivor",
            "identity_canon_state": "canonical",
            "last_identity_decision_id": "dec-merge-1",
        },
    )
    proof = _prove(store)
    assert proof.passed is False
    assert "node:node_a:state:last_identity_decision_id" in proof.unresolved_element_ids
    dangling = next(
        row
        for row in proof.rows
        if row.element_id == "node:node_a:state:last_identity_decision_id"
    )
    assert dangling.reconstructable is False
    assert "dangling last_identity_decision_id" in dangling.rationale


def test_t14_adversarial_redirect_mismatch_fails() -> None:
    store = _store(
        redirects=[_redirect(to_node_id="node_c")],
        extra_nodes={"node_c": _node("node_c")},
    )
    proof = _prove(store)
    assert proof.passed is False
    merged = next(row for row in proof.rows if row.field == "merged_into")
    assert merged.reconstructable is False
    assert "disagrees with active redirect" in merged.rationale


def test_t15_adversarial_unsupported_identity_state_fails() -> None:
    store = _store(
        survivor_state={
            "identity_state": "split_from",
            "identity_canon_state": "canonical",
            "last_identity_decision_id": "dec-merge-1",
        }
    )
    proof = _prove(store)
    assert proof.passed is False
    identity = next(row for row in proof.rows if row.field == "identity_state")
    assert identity.reconstructable is False
    assert identity.stored_value == "split_from"
    assert "not proven by the current merge-survivor" in identity.rationale


def test_duplicate_decision_id_fails_closed() -> None:
    store = _store(decisions=[_decision(), _decision()])
    with pytest.raises(IdentityLifecycleHistoryConformanceError) as exc:
        _prove(store)
    assert exc.value.code == "duplicate_decision_id"


def test_expected_field_counts_refuse_stale_inventory() -> None:
    with pytest.raises(IdentityLifecycleHistoryConformanceError) as exc:
        prove_identity_lifecycle_history_v1(
            _store(),
            world_id="test",
            canonical_revision_id="rev:test",
            canonical_graph_payload_sha256="0" * 64,
            expected_field_counts={
                "identity_state": 7,
                "merged_into": 7,
                "last_identity_decision_id": 14,
            },
        )
    assert exc.value.code == "stale_identity_shadow_inventory"


def test_policy_factory_rejects_failed_proof() -> None:
    proof = _prove(
        _store(
            survivor_state={
                "identity_state": "split_from",
                "identity_canon_state": "canonical",
                "last_identity_decision_id": "dec-merge-1",
            }
        )
    )
    with pytest.raises(ValueError, match="has not passed"):
        source_history_policy_from_identity_lifecycle_proof(proof)


def test_policy_is_not_a_public_allowlist_constructor() -> None:
    with pytest.raises(TypeError):
        WholeWorldSourceHistoryPolicy(  # type: ignore[call-arg]
            policy_id="arbitrary",
            proven_node_state_history_element_ids=frozenset({"node:x:state:identity_state"}),
        )
    assert LEGACY_SOURCE_HISTORY_POLICY.proven_node_state_history_element_ids == frozenset()


def test_policy_factory_accepts_passed_proof() -> None:
    proof = _prove(_store())
    policy = source_history_policy_from_identity_lifecycle_proof(proof)
    assert policy.policy_id == "identity_lifecycle_history_v1"
    assert policy.proven_node_state_history_element_ids == frozenset(proof.element_ids)


def _history_element(element_id: str) -> ClassifiedElement:
    return ClassifiedElement(
        element_id=element_id,
        element_family="node_state",
        classification=SemanticClassification.SOURCE_MIGRATION_HISTORY,
        blocker_class=None,
        note="test",
    )


def test_contribution_history_excludes_proven_identity_shadow_ids() -> None:
    proof = _prove(_store())
    policy = source_history_policy_from_identity_lifecycle_proof(proof)
    contribution = _history_element("node:x:state:approval_state")
    identity_shadow = _history_element(proof.element_ids[0])
    unrelated = ClassifiedElement(
        element_id="node:x:field:kind",
        element_family="node_field",
        classification=SemanticClassification.REPRESENTABLE_BY_EXPLICIT_ADAPTER,
        blocker_class=None,
        note="test",
    )
    items = _contribution_history_classified_items(
        [contribution, identity_shadow, unrelated],
        policy,
    )
    assert [item.element_id for item in items] == [contribution.element_id]
    legacy_items = _contribution_history_classified_items(
        [contribution, identity_shadow],
        LEGACY_SOURCE_HISTORY_POLICY,
    )
    assert {item.element_id for item in legacy_items} == {
        contribution.element_id,
        identity_shadow.element_id,
    }


def test_merge_then_alias_remove_is_reconstructable() -> None:
    store = _alias_remove_store()
    merge_only = _prove(store)
    assert merge_only.passed is False
    assert len(merge_only.unresolved_element_ids) == 2
    proof = _prove_through(store)
    assert proof.passed is True
    assert proof.unresolved_element_ids == []
    assert proof.reconstructable_count == 4
    survivor_pointer = next(
        row
        for row in proof.rows
        if row.element_id == "node:node_b:state:last_identity_decision_id"
    )
    survivor_state = next(
        row for row in proof.rows if row.element_id == "node:node_b:state:identity_state"
    )
    assert survivor_pointer.decision_kind == "alias_remove"
    assert survivor_pointer.decision_id == "dec-remove-1"
    assert survivor_state.decision_kind == "alias_remove"
    assert survivor_state.lifecycle_role == "merge_survivor"
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert lineage.reconstructable is True
    assert lineage.causal_merge is not None
    assert lineage.causal_merge.decision_id == "dec-merge-1"
    assert "dec-merge-1" in survivor_pointer.rationale
    assert "dec-merge-1" in survivor_state.rationale


def test_historical_merge_survivor_still_passes_through_alias_remove() -> None:
    store = _store()
    merge_only = _prove(store)
    through = _prove_through(store)
    assert merge_only.passed is True
    assert through.passed is True
    assert through.element_ids == merge_only.element_ids
    assert all(row.decision_kind == "merge" for row in through.rows)


def test_merge_source_proof_unchanged_after_alias_remove() -> None:
    proof = _prove_through(_alias_remove_store())
    merged = next(row for row in proof.rows if row.field == "merged_into")
    source_pointer = next(
        row
        for row in proof.rows
        if row.element_id == "node:node_a:state:last_identity_decision_id"
    )
    assert merged.reconstructable is True
    assert merged.decision_id == "dec-merge-1"
    assert source_pointer.decision_id == "dec-merge-1"


def test_alias_remove_without_causal_merge_fails() -> None:
    store = _alias_remove_store(
        decisions=[
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
            )
        ]
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert lineage.reconstructable is False
    assert "no earlier causal merge" in lineage.rationale


def test_alias_remove_before_causal_merge_fails() -> None:
    store = _alias_remove_store(
        decisions=[
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
            ),
            _decision(),
        ]
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert lineage.reconstructable is False
    assert "no earlier causal merge" in lineage.rationale


def test_alias_remove_alias_not_in_merge_side_effects_fails() -> None:
    store = _alias_remove_store(
        decisions=[
            _decision(
                merge_side_effects=IdentityMergeSideEffects(
                    aliases_added_to_target=["Other"]
                )
            ),
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
            ),
        ]
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert "no earlier causal merge" in lineage.rationale


def test_wrong_alias_remove_subject_fails() -> None:
    store = _alias_remove_store(
        extra_nodes={"node_c": _node("node_c")},
        decisions=[
            _decision(),
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_c",
                target=None,
                alias="Shadow",
                affected=["node_c"],
            ),
        ],
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert "subject is not the current node" in lineage.rationale


def test_inactive_alias_remove_fails() -> None:
    store = _alias_remove_store(
        decisions=[
            _decision(),
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
                status="superseded",
            ),
        ]
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert "is not active" in lineage.rationale


def test_missing_merge_side_effects_fails() -> None:
    store = _alias_remove_store(
        decisions=[
            _decision(merge_side_effects=None),
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
            ),
        ]
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert "missing merge_side_effects" in lineage.rationale


def test_multiple_causal_merges_fail() -> None:
    store = _alias_remove_store(
        extra_nodes={
            "node_c": _node(
                "node_c",
                memory_state="merged_away",
                identity_canon_state="merged_away",
                merged_into="node_b",
                last_identity_decision_id="dec-merge-2",
            )
        },
        decisions=[
            _decision(),
            _decision(
                decision_id="dec-merge-2",
                subject="node_c",
                target="node_b",
                merge_side_effects=IdentityMergeSideEffects(
                    aliases_added_to_target=["Shadow"]
                ),
            ),
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
            ),
        ],
        redirects=[
            _redirect(),
            _redirect(decision_id="dec-merge-2", from_node_id="node_c", to_node_id="node_b"),
        ],
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert "multiple earlier causal merges" in lineage.rationale


def test_merge_then_split_then_alias_remove_fails() -> None:
    store = _alias_remove_store(
        decisions=[
            _decision(),
            _decision(
                decision_id="dec-split-1",
                kind="split",
                subject="node_b",
                target="node_d",
                affected=["node_b", "node_d"],
            ),
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
            ),
        ],
        extra_nodes={"node_d": _node("node_d")},
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert "invalidating split" in lineage.rationale


def test_merge_then_unmerge_then_alias_remove_fails() -> None:
    store = _alias_remove_store(
        decisions=[
            _decision(),
            _decision(
                decision_id="dec-unmerge-1",
                kind="unmerge",
                subject="node_a",
                target="node_b",
                affected=["node_a", "node_b"],
            ),
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
            ),
        ]
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert "invalidating unmerge" in lineage.rationale


def test_stale_alias_remove_pointer_fails() -> None:
    store = _alias_remove_store(
        extra_nodes={"node_c": _node("node_c")},
        decisions=[
            _decision(),
            _decision(
                decision_id="dec-remove-1",
                kind="alias_remove",
                subject="node_b",
                target=None,
                alias="Shadow",
                affected=["node_b"],
            ),
            _decision(
                decision_id="dec-merge-later",
                subject="node_c",
                target="node_b",
                merge_side_effects=IdentityMergeSideEffects(
                    aliases_added_to_target=["Later"]
                ),
            ),
        ],
    )
    proof = _prove_through(store)
    assert proof.passed is False
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    assert "stale" in lineage.rationale


def test_both_survivor_fields_share_one_lineage() -> None:
    store = _alias_remove_store()
    proof = _prove_through(store)
    lineage = prove_alias_remove_survivor_lineage(store, "node_b")
    pointer = next(
        row
        for row in proof.rows
        if row.element_id == "node:node_b:state:last_identity_decision_id"
    )
    identity = next(
        row for row in proof.rows if row.element_id == "node:node_b:state:identity_state"
    )
    assert pointer.decision_id == identity.decision_id == lineage.current.decision_id
    assert lineage.causal_merge.decision_id == "dec-merge-1"
    assert pointer.rationale.count("dec-merge-1") == 1
    assert identity.rationale.count("dec-merge-1") == 1
