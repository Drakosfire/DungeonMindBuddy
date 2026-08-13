"""Fail-closed proofs for identity-lifecycle shadow reconstructability."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind_kernel.identity_lifecycle_history_conformance_v1 import (
    IdentityLifecycleHistoryConformanceError,
    prove_identity_lifecycle_history_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    LEGACY_SOURCE_HISTORY_POLICY,
    WholeWorldSourceHistoryPolicy,
    source_history_policy_from_identity_lifecycle_proof,
)
from graph_memory.kernel.identity_models import IdentityDecisionRecord


def _decision(
    *,
    decision_id: str = "dec-merge-1",
    kind: str = "merge",
    subject: str = "node_a",
    target: str = "node_b",
    status: str = "active",
) -> dict[str, object]:
    return IdentityDecisionRecord(
        decision_id=decision_id,
        world_id="test",
        decision_kind=kind,  # type: ignore[arg-type]
        created_at="2026-01-01T00:00:00Z",
        actor="test",
        reason="test merge",
        subject_node_id=subject,
        target_node_id=target,
        affected_node_ids=[subject, target],
        status=status,  # type: ignore[arg-type]
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
