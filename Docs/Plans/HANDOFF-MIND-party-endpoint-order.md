# MIND — retain configured party endpoints during consolidation

Status: ACTIVE; PRIME implements solo under the operator's foundational-work authorization.
Base: Buddy origin/main `78c56b3786cbadd2f38594c4058ed830a3d8d13a`.
Branch: `codex/party-endpoint-order`.
Lane: `/home/drakosfire/.local/state/dungeonmindbuddy/experiments/party-endpoint-order-20261014/source`; non-serving.

## Outcome

Make existing configured party context available before raw-edge endpoint validation. The same consolidation function currently advertises the party in its pre-edge node list, drops model edges referencing that ID, and only then recreates it. Synthetic owning-boundary reproduction confirms the order defect. Preserve configured membership context and ordinary edge/source checks; do not infer a party when no roster exists or claim that standing context proves session participation.

## Exclusive write set

- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `tests/test_party_endpoint_consolidation_order.py`
- this handoff

Topology: serial after merged PR #1142 at `78c56b3786cbadd2f38594c4058ed830a3d8d13a`, which carries registered verified identity context. The next leased successor is #1145, stacked on this slice and sharing `category_candidate_graph_extractor.py`; #1189 is serialized after #1145 because it also edits that extractor and the registered graph-preview runner. PR #1139 was rechecked and is disjoint (`recap_extraction_profile.py`). No serving ports/state leased.

## Verification and completion

Owning pipeline must advertise and retain an evidence-bearing edge through the configured party endpoint, seed membership edges once, and still reject unknown endpoints. A no-roster source must not gain a party. Inspect exact cumulative diff, test the owning pipeline plus existing category/party regressions, lint, commit/push/open assigned PR.

PRIME-authored: ARCHITECTURE independently reviews the updated exact head under the operator's standing review assignment; PRIME retains merge authority. No provider call, publication, schema change, server or retained-data mutation in this implementation. Source-backed output/rollout follows accepted merge; endpoint consistency does not establish semantic relationship correctness.
