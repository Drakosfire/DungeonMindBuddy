# INGEST: rendered recap and source-durability acceptance

**Status:** ACTIVE — PRIME explicitly dispatched this bounded acceptance slice on 2026-10-17. No operator action is required.
**Base:** fetched `origin/main@72c22ee15bd6dd841f51bd0b2462f117444fbba4` after merged PR #1314.
**Branch:** `codex/ingest-rendered-recap-acceptance`.
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` (existing assigned checkout; no new worktree).
**Topology:** serial; one acceptance PR. PRIME owns independent review and merge. #1235 and #1244 remain separate held Ingest lanes and are not dependencies or part of this diff.

## Mission

Close the rendered and owning-persistence evidence gap for the ordinary Ingest path: write or paste a recap, choose **Process**, then see the exact-run graph-enriched recap. This slice proves the flow with synthetic data and makes no product/runtime changes. The durable APP source and exact historical projection are independently exercised at the API boundary with disposable fixtures.

## Verified behavior and limits

- Current UI at isolated port 5206 rendered a synthetic Session 22 from blank composer through one mocked `generate_recap_memory` request to the exact-run historical projection. The rendered recap showed a Mireward node pill and the exact run/source digest notice.
- At 1280×900 and 390×844, the rendered document had no horizontal overflow.
- All browser API calls were intercepted and answered with synthetic fixtures. No request reached a live API, corpus, World Graph, provider, or retained database. The global Graph badge correctly remained **Needs attention** because the isolated preview has no Agent local-session service; this does not negate the mocked exact-run UI render or prove live Graph connectivity.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` passes 45 tests, including the exact-run rendered recap and node pill assertions. `git diff --check` passes. Python syntax parsing passes for the changed API test.
- The owning API suite `tests/test_live_recap_ingest_graph_preview_api.py::test_recap_ingest_generate_recap_memory_with_graph_extraction_fake_client` exercises ordinary Process with a fake extractor, canonical/normalized recap creation, exact ExtractionRun and candidate manifest, durable APP source creation and source markdown readback, then the exact-run historical projection endpoint with the frozen managed/native World binding. The complete suite previously passed 27 tests with 11 existing Pydantic schema warnings on accepted main `98f60ba`; it could not be rerun on this base because available cached Python environments do not match `uv.lock` (the installed DungeonMind package lacks `SourceAnchorBatchRequest`, and the GenerationEngine cache lacks `ImageOptions`). The focused `tests/test_live_recap_ingest_api.py` suite is likewise blocked at import by that stale dependency set; no test assertion failed.
- `npm run build` is blocked by five existing TypeScript errors in untouched `src/planSurface/components/WorldPlanAgentAnswer.tsx` (lines 47, 49, and 50). The changed Ingest test itself passes.
- This does not process the user's retained Session 10 or Session 29 recap, prove live credentials/provider availability, publish candidate facts, or establish full World integration. No real recap, retained corpus, Graph, database, or 5202 was touched.
- The earlier #1287 synthetic witness found the shared node hover-summary card partially clipped at narrow width. Its stylesheet is outside this lease and remains a separate follow-up.

## Predecessor settlements in this PR

- PR #1311 merged at `98f60ba74b363aa39d8936f1c1f55a8981368255` from `1fe58d2d7453d684015e7910e4835d5b9fdb8613`; its generic canonical-title lineage implementation lease ended.
- PR #1287 merged at `6c8d7b05a0e274d20325e953a66a7c8805e8fbfd` from `570f8c1ae0d4d1481f54dc68c08606ec87215635`; its exact managed/native run-binding implementation lease ended.
- PR #1276 merged at `448e88d9006b19cfb607d4ac5afde14d6d44d856`; it established the graph-enriched recap as the primary Ingest view.

The two corresponding handoffs are marked SETTLED here with factual merge and limitation records.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-rerun-source-lineage.md` — predecessor settlement only
- `Docs/Plans/HANDOFF-INGEST-managed-run-projection.md` — predecessor settlement only
- `Docs/Plans/HANDOFF-INGEST-rendered-recap-acceptance.md` — this contract and acceptance record
- `tests/test_live_recap_ingest_api.py` — synthetic Process response/run identity coverage only
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — exact-run rendered fixture consistency/identity coverage only

No production code, server routes, schemas, migrations, raw source, Graph candidate, retained database, provider configuration, or runtime files are leased. Return to PRIME before expanding paths or behavior.

## Acceptance and verification

- Keep the local Ingest UI fixture's session, recap text, exact run ID, source artifact, graph snapshot, and node mention coherent; assert the Process response supplies the exact run identity the UI reads.
- Run the complete `IngestionModule.test.tsx` suite and `tests/test_live_recap_ingest_api.py` plus the owning `tests/test_live_recap_ingest_graph_preview_api.py` suite against disposable state.
- Run applicable UI typecheck/build, Python compile/format checks for changed Python paths if any, and cumulative `git diff --check`.
- Keep the rendered API mocked and synthetic, and use no real provider. Stop only servers started by this slice and verify their ports are clear. Do not read/write 5202 data or alter the serving branch.
- Inspect the exact cumulative base-to-head diff, commit, push, open/update this PR, and report the precise boundary proven and remaining limits. Merge remains PRIME's authority.

## Next direction

The next Ingest priority comes from the first concrete failure observed in an ordinary user flow. Do not create a second implementation slice or require the operator to dogfood before reporting this acceptance evidence to PRIME.
