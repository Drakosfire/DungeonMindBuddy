# Completed implementation record — Build Mirathorn Gazetteer livestock hygiene

**Status:** MERGED into Buddy main as `3a890b9ec8b4e4c9924779249fe8570b7ecf9d1c` (PR #1189, 2026-10-15). The bounded implementation/review lease ended at merge. Post-merge candidate execution and any publication are separate lifecycle work under the active PRIME goal; this handoff does not authorize publication.
**Base:** DungeonMindBuddy `main@25cba5a5e00130a38303d2c1c1d7bc9736527be9` (includes #1145)
**Branch:** `codex/mirathorn-gazetteer-fauna-hygiene`
**Topology:** serial successor after merged PR #1187
**Runtime/DB ownership:** none; do not touch serving ports, application state, or native World data in this slice.

## Outcome

Publishable Build extraction profile `worldbuilding_gazetteer_v1@1.6` must preserve the source’s explicitly owned Fantastic Livestock sections on their registered owner-place description with resolvable source citations, while preventing model-created per-species and livestock-cultural-significance `event` nodes from entering the candidate when their evidence is wholly contained in that exact retained section.

Every removed candidate node and any incident proposed edge must remain inspectable as a deferred item with its original evidence references, stable identity, reason, and next review action. Preserve the complete original node/edge proposal in the run's digest-bound private consolidation-diagnostics component, keyed to the deferred item ID; the closed deferred-item schema stays unchanged. Ambiguous candidates remain for review. No source-backed text or evidence may be discarded, and no individual creature, product, instance, route, or played event may be invented. Named recurring festivals remain eligible event definitions.

Expose 1.6 as the active Gazetteer choice in Build and run it through the same pinned GenerationEngine/OpenRouter DeepSeek V4.1 Flash path. Keep 1.5 and its historical prompt/profile behavior immutable and addressable.

## Evidence motivating this slice

Merged PR #1187 established the exact saved Build revision → GenerationEngine candidate route. Its local candidate run is `6d8cba03-2399-4b24-be71-908e6cd9369a`, based on document `a5f32e92-80d1-42c8-96bd-4587321f39e7`, revision 2, SHA-256 `70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342`, using profile `worldbuilding_gazetteer_v1@1.5`.

The run retained source-backed livestock sections verbatim on the owning Elderwyld location node, with exact span references, but also emitted seven livestock-related nodes as `event` (six species definitions plus a Float Goat cultural-significance node). The Mirathorn gold expects queryable transport/ecology knowledge, not livestock-as-event semantics. This is a candidate-quality correction; no publication or ordinary Agent answer is claimed by the prior run.

## Write set

- `Docs/Plans/HANDOFF-BUILD-mirathorn-gazetteer-livestock-hygiene.md`
- `src/graph_memory/extraction/worldbuilding_gazetteer_profile.py`
- `src/graph_memory/extraction/worldbuilding_profile_catalog.py`
- `src/graph_memory/extraction/worldbuilding_source_sections.py`
- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `src/graph_memory/extraction/graph_preview_runner.py`
- `apps/live_control_server/services/worldbuilding_ge_execution.py`
- `apps/live_control_server/routes/graph_preview.py`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.ts`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.test.tsx`
- `tests/test_worldbuilding_source_sections.py`
- `tests/test_worldbuilding_gazetteer_profile.py`
- `tests/test_worldbuilding_ge_execution.py`
- `tests/test_worldbuilding_ge_route.py`
- `tests/test_graph_preview_runner.py`
- `tests/test_registered_extraction_failure_evidence.py`
- `evals/graph_memory_layer/examples/mirathorn_worldbuilding_query_gold_v1/gold.json`

No other paths are leased. Do not include or stage local corpus, run output, raw provider responses, credentials, database dumps, or any private source content.

## Implementation constraints

- Preserve profiles 1.0–1.5 unchanged; profile 1.6 is the only newly active policy.
- Make the removal rule depend on the exact recognized livestock section, event node type, exact normalized candidate-label patterns, and evidence refs wholly contained in that section’s retained source-span set. Do not use broad keyword matching alone.
- Preserve existing constrained edge review and role-support handling. Defer incident edges rather than leaving dangling endpoints.
- Keep exact source text and citation spans on the owner location; preserve source-to-span resolution and `can_open_source` behavior.
- Keep the run bound to the committed Build document ID, revision, source artifact, and SHA. The client cannot select provider or World target.
- No World publication, retained Graph write, runtime deployment, or change to the private existing run. The saved run is read-only regression evidence.
- Do not make provider calls merely to repeat an unchanged inference request. Use deterministic/synthetic tests for this slice; a later exact-source run with the new profile must have an actual prompt/profile change, use the existing standing DeepSeek approval, record usage, and remain candidate-only pending review.

## Required verification

1. Source-section unit tests prove exact owner, bounds, species-section labels, source-span IDs, verbatim retained text, and failure on missing/ambiguous owner or malformed spans.
2. Profile tests prove 1.5 remains unchanged, 1.6 is separately catalogued, recurring festival nodes remain, exact livestock event duplicates are deferred with evidence, related edges are deferred, unrelated events survive, and ambiguous/mixed-evidence candidates remain reviewable.
3. Owning pipeline tests run synthetic pass outputs through the real `run_category_pipeline` and 1.6 retainer; they verify no evidence loss, no dangling edges, source-stamped deferred proposals, and full node/edge proposal recovery by disposition ID (including an empty edge label and extra qualifier fields).
4. A production-runner persistence test proves consolidation diagnostics are saved as a private mode-`0600` component with a checked digest; deferred proposal references resolve through that run's source/span components, and positive candidate endpoints remain valid.
5. Build selection/route tests prove the UI selects 1.6 and the server routes it through the pinned GE adapter with immutable source checks; 1.5 retains its exact historical route.
6. The Mirathorn gold validator passes with only current profile/catalog snapshot hashes and the available-profile inventory synchronized; source facts, answer expectations, provenance, and `execution_profile: unverified` remain unchanged.
7. Reprocess the saved Mirathorn candidate locally with the new deterministic policy, without provider access or changing the old run. Record only aggregate evidence (counts, exact profile, source/run hashes, retained/deferred IDs) outside the PR; do not export source text.
8. Run focused tests, TypeScript check, Ruff, and diff check on the exact cumulative head. Request ARCHITECTURE review before merge.

## Verification result

- Reprocessing the saved revision-2 candidate through the 1.6 deterministic postprocessor made zero provider calls. The candidate changed from 39 nodes / 13 events / 10 deferred items to 32 nodes / 6 events / 17 deferred items. The 20 remaining edges have no dangling endpoints.
- All 62 spans in the owned Fantastic Livestock section remain on its source-backed owner node. Across the resulting graph and review dispositions, all 213 citation references resolve; no span reference was unresolved.
- The correction defers six species-definition event nodes and one livestock-cultural-significance event node. This demonstrates safe exclusion from the positive event graph, not queryable species-node representation.
- On the amended head, source/profile/execution/route suites plus the registered-run persistence regression: 42 passed (9 existing Pydantic field-name warnings). The broader graph-preview runner and registered failure-evidence suites: 30 passed (1 existing Pydantic field-name warning).
- The Mirathorn gold validator reports 18 facts, 10 questions, and 4 explicit omissions valid; its test file passes 16 tests. A structural comparison confirms the gold's source facts, questions, required expectations, corpus lock, methodology, and graph-contract snapshot are unchanged from the pinned base. Only profile-snapshot hashes, available-profile inventory, and the clarifying note changed.
- The complete `useBuildExtraction` UI test file previously passed 37 tests; UI TypeScript check passed. No UI paths changed in this review-cycle amendment.
- Ruff and `git diff --check` pass on the amended write set.
- This evidence reprocesses the prior 1.5 candidate locally. No new 1.6 provider run, World publication, retained Graph write, server restart, or ordinary Agent query has occurred. Those lifecycle gates remain open.

## Follow-through

After review and merge, re-anchor `main`, run a new-source exact-revision extraction under profile 1.6 only if needed to prove the changed prompt and route, and inspect the candidate against the frozen Mirathorn gold before attempting publication. Preserve separate pending/publication state and verify target World binding before any write. This handoff itself does not authorize publication.

## Review-cycle amendment — deferred proposal auditability and gold snapshot

ARCHITECTURE's independent review of the first PR head found that the closed `DeferredItem` record only carries a label/reason/evidence subset. That is not enough to inspect the original semantic proposal, especially for an edge with an empty label. This amendment extends the exact PR write set to retain each full canonical proposal in the existing `consolidation_diagnostics` component, keyed to the unchanged disposition ID. Evidence refs are stamped with the exact source artifact and source-ref identity before persistence. The component is atomically written mode `0600`, digest-bound in the ExtractionRun manifest, and remains private local run evidence. No deferred schema or public retrieval contract is widened.

The same review found that the source-locked Mirathorn gold pinned stale profile/catalog hashes. Its current code-snapshot hashes and available-profile inventory are synchronized in the gold file. All source facts, expected answers, evidence quotes, graph-path expectations, and provenance remain untouched; the gold continues to state that the execution profile is unverified. This is metadata synchronization, not 1.6 execution evidence or a change to acceptance expectations.
