"""Unit tests for extract-promote review projection (PR011A2)."""

from __future__ import annotations

from graph_memory.extract_promote_review_projection import (
    project_promote_review,
)
from graph_memory.kernel.contribution_models import (
    ContributionIdentityMention,
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.extract_identity_gate import IdentityGateResult


def _assertion(
    *,
    assertion_id: str,
    kind: str,
    label: str,
    outcome: str | None,
    subject: str | None = None,
    target: str | None = None,
    predicate: str | None = None,
) -> GraphContributionAssertion:
    return GraphContributionAssertion(
        assertion_id=assertion_id,
        assertion_kind=kind,  # type: ignore[arg-type]
        subject_node_id=subject,
        target_node_id=target,
        predicate=predicate,
        label=label,
        acceptance_state="accepted",
        identity_resolution_outcome=outcome,
        contribution_id="contrib:test",
        evidence_ref_ids=["ref:1"],
        source_artifact_id="artifact:test",
    )


def test_project_promote_review_defaults_and_counts() -> None:
    contribution = GraphContribution(
        contribution_id="contrib:test",
        world_id="eldyrwild",
        source_kind="source_extraction",
        produced_at="2026-07-18T00:00:00Z",
        accepted_assertions=[],
        candidate_assertions=[],
    )
    gate = IdentityGateResult(
        parent_revision_id="rev:parent",
        world_id="eldyrwild",
        contribution=contribution,
        accepted_proposals=[
            _assertion(
                assertion_id="a-node",
                kind="node",
                label="Hesta",
                outcome="created_new",
                subject="npc_hesta",
            ),
            _assertion(
                assertion_id="a-edge",
                kind="edge",
                label="works at",
                outcome=None,
                subject="npc_hesta",
                target="loc_apothecary",
                predicate="works_at",
            ),
        ],
        unresolved_mentions=[
            ContributionIdentityMention(
                mention_id="m1",
                label="Strange figure",
                object_kind="npc",
                identity_resolution_outcome="ambiguous",
                diagnostics=["two rivals"],
            )
        ],
        rejected_assertions=[
            _assertion(
                assertion_id="a-rej",
                kind="node",
                label="Noise",
                outcome="rejected",
                subject="noise",
            )
        ],
        identity_outcome_snapshot={"npc_hesta": "created_new"},
        node_id_map={"npc_hesta": "npc_hesta"},
    )

    items, summary = project_promote_review(gate)
    assert summary.new_object_count == 1
    assert summary.relationship_count == 1
    assert summary.unresolved_mention_count == 1
    assert summary.rejected_assertion_count == 1

    accepted = [i for i in items if i.selectable]
    assert len(accepted) == 2
    assert all(i.selected_by_default for i in accepted)
    assert accepted[0].action == "create"
    assert accepted[0].kind == "object"
    assert accepted[1].kind == "relationship"

    blocked = [i for i in items if not i.selectable]
    assert len(blocked) == 2
    assert all(not i.selected_by_default for i in blocked)
    assert blocked[0].assertion_id.startswith("unresolved:")
    assert blocked[1].assertion_id.startswith("rejected:")
