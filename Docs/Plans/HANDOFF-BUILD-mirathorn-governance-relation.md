# PRIME handoff — source-grounded Mirathorn governance relation

**Status:** ACTIVE — implementation extends Buddy PR #1196.
**Base contract:** Buddy main `6bde87a27dfeb3768015d96444d22e3c517106bb`; DungeonMind main `1d120886b00acf7f97b3744e88619abd97c34591` defines the reviewed world-object-v6/world-property-v4 pair.
**Branch:** `codex/mirathorn-governs-consumer`.
**Topology:** serial; incorporate the exact accepted Buddy and DungeonMind predecessors, retarget this existing PR to main, then review the completed integration. Downstream trade-context work stays held.
**Runtime/state ownership:** isolated non-serving checkout `/tmp/prime-mirathorn-governance-current`; tests may create/drop uniquely named disposable application-state databases on 54329. Native source-readback tests own the disposable pgvector container `prime-mirathorn-native-test-20261015`, loopback port 54332, with ephemeral data; remove it when this checkpoint ends. Do not start or restart serving processes, call a provider, publish retained World knowledge, or edit operator data.

## Outcome

Complete the Mirathorn governance path from the exact saved Build source into the existing candidate review/publication flow. The preserved v1.6 candidate already contains one `Mirathorn` location and one `Mirathorn City Council` organization, each carrying the same openable source span for the explicit Governance sentence, but it omits their `governs` edge. Buddy's v1.8 scene-scope profile removes prepared-scene contamination; this slice adds a new immutable Gazetteer profile version that preserves that behavior, adds the source title as identity evidence to the two existing nodes, and deterministically proposes the missing directed relation for review.

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
- Immutable v1.6 pipeline artifact `eae64dfa-e0bc-447c-aa1e-6b97fc5acff7` from the preserved non-serving experiment. Candidate SHA-256 `eeced17f5f23ce33edd60636b14ef19be0dc2e994d0a77986991c1c35c1288fb`.
- The saved candidate has 44 nodes and 20 edges. Replaying v1.9 preserves v1.8 scene exclusions, leaving 35 nodes and 14 edges. Its existing directed governance edge receives exact Governance-line and city-title evidence; no extra edge is created and the diagnostic is `evidence_attached`.
- Governance line 166 and frontmatter title line 2 retain their original indexed span IDs. No model call or source mutation occurs during replay.
- This is local candidate evidence. Retained World publication, ordinary Agent answers and operator acceptance remain unproven.

## Write set

- `Docs/Plans/HANDOFF-BUILD-mirathorn-governance-relation.md`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.test.tsx`
- `apps/live-control-ui/src/buildSurface/useBuildExtraction.ts`
- `apps/live_control_server/integrations/dungeonmind/assertion_qualification.py`
- `apps/live_control_server/models/extract_promote.py`
- `apps/live_control_server/routes/graph_preview.py`
- `apps/live_control_server/services/worldbuilding_ge_execution.py`
- `apps/live_control_server/services/worldbuilding_graph_publication.py`
- `evals/graph_memory_layer/examples/mirathorn_worldbuilding_query_gold_v1/gold.json`
- `evals/graph_memory_layer/validate_mirathorn_worldbuilding_query_gold_v1.py`
- `pyproject.toml`
- `src/graph_memory/extraction/worldbuilding_gazetteer_governance.py`
- `src/graph_memory/extraction/worldbuilding_profile_catalog.py`
- `tests/test_cutover_worldbuilding_authority_port.py`
- `tests/test_mirathorn_worldbuilding_query_gold_v1.py`
- `tests/test_s28_native_predicate_adoption.py`
- `tests/test_worldbuilding_gazetteer_governance.py`
- `tests/test_worldbuilding_gazetteer_profile.py`
- `tests/test_worldbuilding_ge_execution.py`
- `tests/test_worldbuilding_ge_route.py`
- `uv.lock`
- `Docs/Plans/HANDOFF-BUILD-mirathorn-prepared-scenario-scope.md`
- `tests/test_worldbuilding_source_catalog_admission.py`

The predecessor scenario handoff records its accepted merge. Publication source-catalog tests may change only to exercise the pinned governance/source-readback contract.

No corpus, raw model response, credential, database, candidate run output, serving configuration, or retained World change may enter the PR.

## Verification

- Reject negated/conditional governance while preserving an affirmative relation with an unrelated uncertain action; verify the exact paired catalog through its loaded catalog, not fields absent from the vocabulary reference.
- Unit-test title/section matching, exact openable evidence, endpoint ambiguity, direction, idempotency, and diagnostic behavior.
- Replay the saved candidate through the registered v1.9 profile and verify node/edge diffs, exact source span, and preservation of v1.8 exclusions.
- Run all applicable extraction, real disposable-PostgreSQL publication/source-catalog tests and source-readback checks using the accepted Core dependency. Preserve actual failures; earlier skipped evidence is not a current integration pass.
- Verify Build selects v1.9 and the registered-source GenerationEngine route admits it.
- Run the Mirathorn gold validator, focused Python and UI hook tests, TypeScript/build if available, Ruff, and cumulative `git diff --check`.
- Reinspect the cumulative base→head diff, then submit the exact PR #1196 head to ARCHITECTURE for independent review.

## Hold

This does not publish to Elderwyld, prove correct managed-World resolution, answer through ordinary Buddy conversation, or prove restart persistence. Keep the lifecycle goal active until those owning-boundary checks and operator inspection pass.
