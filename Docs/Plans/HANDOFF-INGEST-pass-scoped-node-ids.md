# INGEST: pass-scoped standard recap candidate node IDs

Status: ACTIVE. Root owns design and implementation under the authorized C1S1–10 goal.

## Outcome and evidence

Independent producer passes own local IDs. Before a standard-v2 recap inventory
crosses into beat/relationship extraction, the host must give every node a unique,
reversible pass-qualified candidate ID. This is candidate composition, not semantic
identity consolidation. Never merge by name or guess an ambiguous edge endpoint.

Actual control S8 run 211ec186-fcdf-40db-8256-74e9c7c1c79b failed with duplicate_node_id.
Object/thread passes reused N001–N007; eight edges refer to ambiguous IDs.
Independent owner review SHA256 fa1aecefd0b8a0b72a34951b50f4382247d06ee3f56ca232590f2e457f9965df.
Retain the failed run and its costs; do not salvage those edges or overwrite it.

## Lane, topology and writes

Branch codex/ingest-pass-scoped-node-ids, base #2145 exact
ceecc1854eea05558b5109e97442d02a3ec378e5. Serial repair stacked on #2145;
merge/rebase parent first. Experimental #2148 is parked, not an active concurrent
write lease; do not inherit its role change. Shared evaluator #2146 and BUILD
#2147 have no write overlap. No merge/deployment authority.

Exclusive expected writes:
- src/graph_memory/extraction/category_candidate_graph_extractor.py
- tests/test_recap_pass_scoped_node_ids.py
- tests/test_category_candidate_graph_extractor.py (existing inventory/endpoint fixtures)
- tests/test_recap_quote_integrity.py (owning pipeline expected candidate IDs)
- this handoff

No source edits, model/schema/prompt policy/allocation changes, semantic merges,
new producer, database migration, publication or provider calls in this slice.
Worldbuilding and encounter-preview behavior remain unchanged. Standard-v2 node
IDs change intentionally; raw model captures remain unchanged and diagnostics
retain pass/local/candidate mapping. Later edges must use the advertised IDs.

## Failure cases and verification

Missing or duplicate IDs within one pass fail before later inventories/requests;
independent pass IDs cannot collide even with delimiter-like text. Composition
must be deterministic across its repeated calls and never mutate input payloads.
Unqualified old/ambiguous edge endpoints cannot bind to new IDs. Full actual
pipeline tests must show downstream prompts advertise distinct IDs and exact
returned endpoint IDs survive to the candidate; source/evidence text is invariant.
Replay the retained node outputs offline for regression, without reinterpreting
old ambiguous edges. Run owning regressions, inspect cumulative diff, independent
exact-head review, commit/push/open PR. Fresh extraction and governed publication
remain required afterward; offline replay is not actual ingestion acceptance.
