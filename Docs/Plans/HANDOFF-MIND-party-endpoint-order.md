# MIND — retain configured party endpoints during consolidation

Status: ACTIVE; PRIME implements solo under the operator's foundational-work authorization.
Base: Buddy origin/main `c9f5c21f3b835f35660b85fbd2e9a38312c401d4`.
Branch: `codex/party-endpoint-order`.
Lane: `/home/drakosfire/.local/state/dungeonmindbuddy/experiments/party-endpoint-order-20261014/source`; non-serving.

## Outcome

Make existing configured party context available before raw-edge endpoint validation. The same consolidation function currently advertises the party in its pre-edge node list, drops model edges referencing that ID, and only then recreates it. Synthetic owning-boundary reproduction confirms the order defect. Preserve configured membership context and ordinary edge/source checks; do not infer a party when no roster exists or claim that standing context proves session participation.

## Exclusive write set

- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `tests/test_party_endpoint_consolidation_order.py`
- this handoff

Topology: parallel-independent of PR1142, which leases registered runner/controller, known-entity matcher and its own test/handoff. No shared write paths or unmerged behavioral dependency. Open PR1139 is also disjoint. No other agent dispatched.

## Verification and completion

Owning pipeline must advertise and retain an evidence-bearing edge through the configured party endpoint, seed membership edges once, and still reject unknown endpoints. A no-roster source must not gain a party. Inspect exact cumulative diff, test the owning pipeline plus existing category/party regressions, lint, commit/push/open assigned PR.

PRIME-authored: independent review before merge. Current review-only exception covered1140/1141; pending standing-review question remains unanswered. No implicit reviewer dispatch. No provider call, publication, schema change, server or retained-data mutation in this implementation. Source-backed output/rollout follows accepted merge; endpoint consistency does not establish semantic relationship correctness.
