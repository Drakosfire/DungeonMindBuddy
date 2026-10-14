# MIND — preserve mentioned verified NPC endpoints

Status: ACTIVE; PRIME implements solo under the operator's foundational-work priority.
Base: Buddy origin/main `9083530dae7cfadb4578a4727dab09478e4b5db2`.
Branch: `codex/known-npc-endpoints`.
Lane: `/home/drakosfire/.local/state/dungeonmindbuddy/experiments/known-npc-endpoints-20261014/source`.

## Outcome and invariant

A caller-supplied verified known NPC, unambiguously mentioned in the source, remains a canonical context endpoint after duplicate observation suppression. Its current-source mention evidence is attached before edge prompt assembly. This repairs the existing known-entity integration; it does not resolve recognition candidates or import World knowledge automatically.

Failure reproduced with saved extraction fixtures: NPC appears in the known ledger, generated duplicate is removed, but no canonical endpoint is inserted. Edge prompt requires consolidated endpoints; relationships are lost or bound incorrectly. Preserve the distinction between endpoint availability and semantic relationship correctness.

## Exclusive write set

- `src/graph_memory/extraction/known_entity_mention_matcher.py`
- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `tests/test_known_npc_endpoint_pipeline.py`
- this handoff

Only already verified registry kinds npc, character, dnd5e:npc are in scope. No automatic name-based identity admission, unknown-kind coercion, prior-fact copying, new schema, provider route, corpus edit, retained write, migration, or serving change.

Topology: parallel-independent of held #1139 (profile default) and #1140 (C2 roster); distinct files and no unmerged behavior dependency. Relevant open PRs inspected. No other agent dispatched.

## Verification and rollout

Synthetic full pipeline must expose one canonical mentioned NPC in the edge input and retain its source-backed relationship. Reject ambiguous matches; do not insert unmentioned entities; preserve existing party identities and duplicate suppression. Run focused neighboring known-entity/category tests and inspect exact cumulative diff.

PRIME-authored: independent review required before merge. After accepted merge, owning ingestion path needs fresh candidate evidence before runtime adoption; endpoint tests do not prove semantic entailment, full graph readiness, or operator acceptance. No live ports or databases leased.
