# INGEST: hold source-local article variants for identity review

Status: ACTIVE. Human grants full ownership and authority over historical graph repair and integration. This is the first bounded runtime slice; the overall repair goal remains active. PRIME explicitly confirms no overlap with its Buddy/Core identity/mutation work. Held Plan-writer PR1764 remains outside scope.

Lane: codex/historical-graph-repair, /home/drakosfire/Projects/.codex/historical-graph-repair/DungeonMindBuddy, fetched base4d3f2f1aace33496aaedea3e1ed2b86d84906803. Serial topology: one implementation PR, followed by governed historical correction and reviewed location binding slices. No primary writes, merge, deployment or service changes.

Expected write lease: this handoff; apps/live_control_server/models/world_graph_mutation_context.py; tests/test_source_local_article_collision.py. Independent benchmark evidence stays in the existing benchmark lane. Ports/services unchanged; full-World native6ee636 and APP/files clone on55447 used read-only for prepare/probes.

Invariant: for source-local candidate creation only, a definite-article variation of an existing active label/alias must trigger plausible-match review rather than silently create another canonical identity. It must not bind or merge, weaken cross-kind checks, activate retracted identities, broaden legacy automatic identity resolution, or conflate arbitrary substrings. Exact candidate/source/parent proof remains mandatory for later reviewed binding.

Evidence: unchanged DeepSeek S10 The Grit and Grime location is created_new/default-selected against existing Grit and Grime; label-only full-context control confirms cause. Source-correct Grit remains ambiguous and requires future reviewed location binding. This slice prevents one duplicate route; it does not retire historical records or claim successful later integration.

Verification: owning classifier tests for both directions, aliases, cross-kind, inactive records, unrelated names, source-local versus ordinary identity behavior; reproduce original red behavior; rerun full-World context and actual candidate prepare on exact source/runtime pins; inspect cumulative base-to-head diff. No model calls needed. Open one implementation PR after validation; no merge authority inferred.
