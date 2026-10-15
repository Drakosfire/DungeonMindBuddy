# PRIME handoff — source-grounded Mirathorn governance relation

**Status:** ACTIVE — implementation extends Buddy PR #1196.  
**Base contract:** Buddy PR #1195 head `42c5e51528746d853f8a80d874220b729f160e95`.  
**Branch:** `codex/mirathorn-governs-consumer`.  
**Topology:** stacked; #1193 → #1195 → #1196, with DungeonMind #121 defining the native vocabulary pinned by #1196.  
**Runtime/state ownership:** none. Do not start or restart servers, call a provider, publish World knowledge, or edit retained data.

## Outcome

Complete the Mirathorn governance path from the exact saved Build source into the existing candidate review/publication flow. The preserved v1.5 candidate already contains one `Mirathorn` location and one `Mirathorn City Council` organization, each carrying the same openable source span for the explicit Governance sentence, but it omits their `governs` edge. Buddy's v1.8 scene-scope profile removes prepared-scene contamination; this slice adds a new immutable Gazetteer profile version that preserves that behavior, adds the source title as identity evidence to the two existing nodes, and deterministically proposes the missing directed relation for review.

Add the relation only when all conditions hold:

- The source has one unique frontmatter title or level-1 heading of the form `The City of <name>`.
- Source-index rows may group several physical lines. Matching reads those lines individually but keeps the original span ID and exact line quote for openable citations.
- One Governance section contains exactly one explicit `city-state governed by a council` statement.
- Exactly one location candidate matches the title name and exactly one organization/faction candidate uses one of `<city> City Council`, `City Council of <city>`, `<city> Council`, or `Council of <city>`.
- Both endpoint candidates carry the same exact source-span citation, quote, and openable source anchor for the governance statement.
- There is no conflicting or duplicate `governs` edge and no deterministic edge-ID collision.

Do not create or rename nodes, infer council membership, reverse a model edge, or publish automatically. Ambiguity and incomplete endpoint evidence produce explicit diagnostics and no new edge. The accepted candidate remains subject to ordinary review and the pinned native write admission in PR #1196.

## Frozen replay input

- Build document `a5f32e92-80d1-42c8-96bd-4587321f39e7`, revision 2.
- Source SHA-256 `70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342`.
- Reuse preserved exact-source candidate run `6d8cba03-2399-4b24-be71-908e6cd9369a`; do not rerun inference.
- The explicit Governance statement is at source line 166. The v1.5 candidate already has openable line-166 evidence on `org_mirathorn_city_council` and `loc_mirathorn`.
- The frontmatter title is line 2 inside the indexed source span covering lines 1–12. v1.9 cites the exact title line while preserving that source span's original ID.
- The preserved candidate starts with 39 nodes and 20 edges. Its replay through the registered v1.8 profile leaves 29 nodes and 18 edges; v1.9 leaves 29 nodes and 19 edges, adds the openable title citation to both existing endpoints, and adds `org_mirathorn_city_council —governs→ loc_mirathorn` with the exact title and line-166 citations. This candidate differs from the separate 44-node/20-edge replay used in PR #1195 because its model extraction output differs; both use the same saved source bytes. This is candidate evidence only, not native publication or ordinary-Agent acceptance.

## Write set

- This handoff.
- `src/graph_memory/extraction/worldbuilding_gazetteer_governance.py`
- `src/graph_memory/extraction/worldbuilding_profile_catalog.py`
- `apps/live_control_server/services/worldbuilding_ge_execution.py`
- `apps/live_control_server/routes/graph_preview.py`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.ts`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.test.tsx`
- `tests/test_worldbuilding_gazetteer_governance.py`
- `tests/test_worldbuilding_gazetteer_profile.py`
- `tests/test_worldbuilding_ge_route.py`
- `tests/test_worldbuilding_ge_execution.py`
- Mirathorn gold inventory and validator, only to record the exact profile/replay evidence.
- Existing PR #1196 write-plan qualification/tests and dependency pin only if required to keep the relation's candidate-to-native contract coherent.

No corpus, raw model response, credential, database, candidate run output, serving configuration, or retained World change may enter the PR.

## Verification

- Unit-test title/section matching, exact openable evidence, endpoint ambiguity, direction, idempotency, and diagnostic behavior.
- Replay the saved candidate through the registered v1.9 profile and verify node/edge diffs, exact source span, and preservation of v1.8 exclusions.
- The current focused Python suite passes 45 tests; 9 database/live-composition cases are deselected because this isolated environment does not provide the required PostgreSQL/paired-contract fixtures. Ruff, compileall, the gold validator, and `git diff --check` pass. UI vitest/TypeScript dependencies are absent in this checkout.
- Verify Build selects v1.9 and the registered-source GenerationEngine route admits it.
- Run the Mirathorn gold validator, focused Python and UI hook tests, TypeScript/build if available, Ruff, and cumulative `git diff --check`.
- Reinspect the cumulative base→head diff, then submit the exact PR #1196 head to ARCHITECTURE for independent review.

## Hold

This does not publish to Elderwyld, prove correct managed-World resolution, answer through ordinary Buddy conversation, or prove restart persistence. Keep the lifecycle goal active until those owning-boundary checks and operator inspection pass.
