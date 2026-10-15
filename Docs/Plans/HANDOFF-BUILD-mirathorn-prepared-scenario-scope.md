# PRIME handoff — Mirathorn prepared-scenario scope

**Status:** ACTIVE  
**Base:** Buddy PR #1193 head eb70124039890e4887b32e8c96b4cef797f4fea2  
**Branch:** codex/mirathorn-prepared-scenario-v18  
**Topology:** one stacked PR; keep role-citation v1.7 as its explicit parent  
**Runtime/state ownership:** none. Do not start or restart servers, call a provider, publish World knowledge, or edit retained data.

## Outcome

Add Gazetteer profile worldbuilding_gazetteer_v1@1.8 and make Build select it. Its deterministic source-scope pass must prevent unplayed Mirathorn hooks and arrival-scene content from becoming durable graph facts, while preserving exact source passage access and source-supported Mirathorn setting facts.

Use only these source headings as prepared-scenario boundaries:

- #### Plot Hooks and Encounters, through the next heading at level 1 or 2.
- ## Approach to Mirathorn, through the next level-1 heading or the end of this document.

Do not classify the intervening Quirks of the Elderwyld / Reaches section as prepared-scene content. Source text and spans stay immutable. Defer scene-supported nodes and edges with their complete proposals and citations. If an entity mixes scene and durable evidence, remove unsupported descriptions and aliases; retain its minimal identity only when a clean durable relationship independently supports it. Do not send contaminated prose to the positive candidate graph.

## Frozen source and replay evidence

- Build document a5f32e92-80d1-42c8-96bd-4587321f39e7, saved revision 2.
- Source SHA-256: 70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342.
- Starting candidate: existing local v1.6 result, 44 nodes / 20 edges; no provider call is needed for this deterministic repair.
- Expected replay result: 35 nodes / 14 edges; defer nine scene-only nodes and six scene-supported edges; sanitize the mixed City Guard description while retaining its source-backed Thalia command edge. Keep the Reaches spans outside the excluded ranges. The Float Goat approach sentence at line 314 stays openable as source passage only.

The source-locked gold facts, questions, quotes, and answer criteria are frozen. Update only profile inventory and truthful implementation notes. These counts prove candidate shaping only, not World publication, ordinary-Agent answers, or operator acceptance.

## Write set

- Docs/Plans/HANDOFF-BUILD-mirathorn-prepared-scenario-scope.md
- src/graph_memory/extraction/worldbuilding_gazetteer_scenario_scope.py
- src/graph_memory/extraction/worldbuilding_profile_catalog.py
- src/graph_memory/extraction/category_candidate_graph_extractor.py
- apps/live_control_server/routes/graph_preview.py
- apps/live_control_server/services/worldbuilding_ge_execution.py
- apps/live-control-ui/src/buildSurface/useBuildExtraction.ts
- apps/live-control-ui/src/buildSurface/useBuildExtraction.test.tsx
- evals/graph_memory_layer/examples/mirathorn_worldbuilding_query_gold_v1/gold.json
- tests/test_worldbuilding_gazetteer_scenario_scope.py
- tests/test_worldbuilding_gazetteer_profile.py
- tests/test_worldbuilding_ge_route.py
- tests/test_worldbuilding_ge_execution.py
- tests/test_graph_preview_runner.py

Do not stage corpus text, private provider responses, credentials, candidate-run output, database files, or serving configuration.

## Verification and review

- Prove the headings and line-range boundaries, including Reaches exclusion, unique span identities, and fail-closed malformed boundaries.
- Prove scene-only nodes and edges are deferred with full evidence, no scene evidence remains in positive nodes/edges, the mixed City Guard claim is cleared, the durable command edge survives, and every retained edge has live endpoints.
- Prove all diagnostic deferred proposals are stamped and persisted as immutable run evidence, including proposals from nested source-retention diagnostics.
- Prove profile 1.8 is catalogued, selected by Build, and accepted by the exact-revision GenerationEngine route. Run the actual registered-source/database boundary in CI or the owning test environment.
- Replay the exact saved v1.6 candidate locally with the v1.8 deterministic pass. Do not rerun inference or edit gold acceptance expectations.
- Run focused Python tests, UI hook tests, typecheck/build, Ruff, and cumulative diff checks. Report any environment-only missing boundary evidence precisely.
- Send the exact completed head for independent ARCHITECTURE review before PRIME considers merge.

## Hold

This slice does not publish the resulting candidate or alter Elderwyld. After merge, resume the active PRIME lifecycle goal with exact registered-source extraction, review, publication to the verified World, ordinary Agent multi-hop questions with opened passages, and restart persistence.
