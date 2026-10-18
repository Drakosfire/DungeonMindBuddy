# INGEST: tolerate node type metadata on dispositions

Status: ACTIVE — PRIME approved this bounded correction and exact path lease after the retained Session 29 failure was diagnosed on 2026-10-17.

Base: `origin/main@34f8859cdfb087e97184fce2b8c797ba9ad28015`, verified against GitHub after #1392; this adds only unrelated Play handoff settlement.
Branch: `codex/ingest-disposition-node-type-tolerance`.
Checkout: `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` (reused and re-anchored to this base; Git metadata is shared outside the workspace and standard Git mutations use the authorized elevated path).
Topology: serial; one INGEST implementation PR. PRIME owns merge and any deployment. ARCHITECTURE reviews the exact cumulative diff.

The first commit contains this handoff and the truthful settlement of the #1391 predecessor handoff only. Product/test changes follow that handoff-first commit.

## Capability and invariant

The thread extraction pass may return a disposition item with an optional string `node_type`. This is model metadata on an ignored/deferred item; it does not turn the item into a graph node, grant it a type, or make it eligible for graph assertions or promotion. Buddy's existing `_normalize_disposition` constructs a whitelist of disposition fields and discards `node_type` before the candidate graph is built.

The strict caller schema must tolerate only that one optional string property on disposition records. Keep `additionalProperties: false`. Reject `null`, booleans, objects, and all non-string `node_type` values. Continue rejecting every other undeclared property. Do not alter positive node, edge, beat, or other pass schemas. Do not change GenerationEngine's generic conformance behavior or add broad response repair.

This is an input-shape compatibility correction only. It does not change extraction prompts, evidence interpretation, graph semantics, candidate dispositions, publication, or runtime configuration. Unknown or malformed output remains fail-closed.

## Failure evidence

The exact retained live run is `graph-ingest:longmont-c2:session-29:20261018T003459Z`, extraction run `2039e450-7ab8-4bf1-8288-723f4b9db397`, from the one authorized Process after PR #1391 merged. The saved source was reused unchanged (source SHA-256 `2bfe3db6a204de5b8638a041027eb71e5d61159f80f8c209ece848e043d6ebbf`); no candidate graph, publication, or graph mutation resulted.

Private run root: `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/out/graph_memory/runs/longmont-c2/session-29/20261018T003352Z`.

- `extraction_run/inference_call_ledger.json` records five initial pass calls and one conformance retry, all routed through OpenRouter to `deepseek/deepseek-v4.1-flash-1017`. The public run projection's `model_id: null` and skipped candidate step are incomplete status metadata; the private ledger is the provider-execution evidence.
- The first `thread_pass` response, provider response `gen-1792283664-ePMdfFcQeCJk8oFwjbrV`, is malformed JSON (missing a quote in a `node_id` key). The attempt artifact SHA-256 is `737954e4bb69e06794d5d7256d914ce381fa97d558a68e39b0a6cfa1c3e8ac59`.
- The one conformance correction, provider response `gen-1792283681-uaEBCNspjC2qz54CzCOC`, is valid JSON but the strict `thread_pass` schema rejects `deferred_items[1].node_type` as an additional property. The attempt artifact SHA-256 is `c82e8df7deeea015467b3ceb88a593bdbc35cee1f209038281e2ef4e4f1b0678`.
- Offline validation against the current schema reproduces exactly that one schema error on the repaired response. The failed run has no candidate path and zero candidate nodes, edges, and beats.

The private attempt artifacts are retained for offline review and must not be copied into checked-in fixtures. Tests use a small synthetic response with the same extra-field shape.

## Exclusive expected write set

| Path | Purpose |
| --- | --- |
| `Docs/Plans/HANDOFF-INGEST-disposition-node-type-tolerance.md` | This bounded contract, evidence, verification, and truthful status |
| `Docs/Plans/HANDOFF-INGEST-extractive-beat-summaries.md` | Settle merged PR #1391 only |
| `src/graph_memory/extraction/category_candidate_graph_schema.py` | Add one optional string property to the disposition-item schema only |
| `tests/test_graph_memory_category_candidate_graph_schema.py` | Assert exact acceptance/rejection boundaries for disposition schema |
| `tests/test_category_candidate_graph_extractor.py` | Prove normalization drops the field and preserves declared disposition data |

No other path is leased. The extractor implementation need not change: `_normalize_disposition` already copies only declared fields. If that invariant has changed on current `main`, stop and return the exact boundary and additional paths to PRIME before editing.

## Acceptance and failure cases

- Validate the exact retained conformance-repair response offline against the new `thread_pass` schema. It must pass; the malformed initial response remains invalid JSON and must not be normalized or admitted.
- Verify disposition records without `node_type` remain valid; a string `node_type` is tolerated only on ignored/deferred items; `null`, booleans, objects, and arbitrary unknown keys are rejected.
- Exercise the complete category extractor candidate-construction path with string `node_type` on both an ignored and deferred item. The resulting candidate keeps every declared field, evidence reference, and deferred `suggested_next_step`; it contains no `node_type`, creates no positive node from either disposition, and does not mutate the provider payload.
- Prove positive node and edge schemas remain unchanged and strict. No broad schema relaxation, prompt-only mitigation, provider rerun, candidate promotion, database write, World publication, or runtime restart is part of this slice.

## Implementation evidence

- The thread disposition schema now permits one optional string `node_type` on ignored/deferred items while retaining `additionalProperties: false`. Positive actor-node and edge schemas still reject undeclared `node_type` metadata.
- The extractor-boundary regression sends `node_type` on both ignored and deferred provider items through candidate construction. Normalization drops that metadata, preserves the declared disposition fields, leaves the provider payload untouched, and does not create positive graph nodes from disposition records.
- Focused verification: the schema and category-extractor suites pass (`8 passed`); Ruff and `git diff --check` pass.
- Exact private-response replay is offline: the original captured thread response remains malformed JSON (decode error at character 2514), while the captured conformance retry validates against the corrected thread schema with zero errors. These private response artifacts remain outside the repository. No provider call or live Process rerun was made.

## Verification and limits

- Run the owning schema and category-extractor test suites, including the exact extra-field and unknown-field cases.
- Run an offline replay of the retained repaired thread response; do not call a provider.
- Run `git diff --check` and inspect the exact cumulative `origin/main` → PR-head diff against this allowlist.
- Preserve the settled #1391 implementation and its evidence. This slice does not establish successful Session 29 extraction or full Ingest readiness.
- Commit the handoff first, implement and test the single capability, then commit/push/open one PR. Send PRIME the exact base/head, handoff-first commit, tests, offline replay result, and remaining limits. ARCHITECTURE reviews the exact head; PRIME decides merge and any later deployed Process attempt.
