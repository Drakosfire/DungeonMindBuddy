# Ingest — verify selected managed World on exact-run projection

Status: ACTIVE — PRIME authorizes DOGFOOD under the operator's Ingest assignment. ARCHITECTURE independently reviews; PRIME merges. Re-anchored base origin/main@119043228c60142e670bbad61d2cd73ed96426ba after merged #1286; its only overlapping `liveApi.ts` change is in the separate authorization helper, outside DOGFOOD's leased historical projection client function. Lane codex/ingest-managed-run-projection, /tmp/prime-ingest-recap-source-world-binding. Serial successor to merged #1284@44f3a3e57d162fbcf4c8a1de649a5b5395ed3d93. Parallel-independent of PRIME's next Agent source-navigation work; no unmerged dependency or shared implementation paths. Source binding implementation lease ended. Prior test services are stopped.

## One outcome

A fresh managed-World recap Process can reopen its exact source and Graph projection in the rendered Ingest experience when managed and native World IDs differ. Keep source revision/content/run identity exact. Candidate generation and source persistence are not Graph admission or publication.

DOGFOOD's isolated synthetic witness proved Process → durable APP source → exact-run native projection, then reproduced UI rejection: IngestionModule compares world:elderwyld against static longmont-c2→eldyrwild mapping. Do not repair a spelling, replace global mappings, or make managed ID equal native ID. ARCHITECTURE reviewed the contract below before activation.

## Contract

- Historical response exposes the verified frozen managed/native/binding-version tuple from the exact ExtractionRun world_campaign_ingest_context, alongside existing exact source/run identity. Keep the response worldId/snapshot World in the native namespace.
- The scoped historical request carries selected managedWorldId as a constraint only. Choose one closed, documented managed selector on the existing endpoint (one managed_world_id value, reject duplicates/unknown selectors), or an explicit managed-scoped route. Do not accept caller native World authority or arbitrary query forwarding. Existing generic unscoped reads retain their explicit semantics; do not add migration/enrichment/defaulting behavior.
- Server resolves the current managed binding through the existing managed World registry seam, requires agreement with the exact frozen managed/native/version tuple, registered/APP source native World, and projected snapshot. Recheck current binding before returning. Missing frozen context, unavailable/remapped/version-changed binding, foreign selected World or mismatched source refuse clearly before exposing an accepted projection. No new binding store, Core capability, provider call or native Graph write.
- Ingest captures managedWorldId together with run/source selection and request generation. A→B→A and same-run/different-World late replies cannot update the new view. Clear stale projection/errors on identity replacement.
- Exact-run UI calls the scoped read and checks echoed managed World, binding version and native snapshot. Build the verification request from that backend-verified native tuple, retaining campaign/session/revision integrity checks. Move static buildWorldGraphRecapProjectionRequest construction into the non-run branch only. Do not modify shared Build/global campaign mapping behavior in this slice.
- Preserve existing Graph/GM access controls and source trust qualifications. New source links do not imply candidate publication.

## Exclusive write set

- this handoff
- Docs/Plans/HANDOFF-INGEST-recap-source-world-binding.md (truthful merged predecessor settlement only)
- apps/live_control_server/models/historical_recap_projection.py
- apps/live_control_server/services/historical_recap_world_projection.py
- apps/live_control_server/routes/graph_preview.py (historical recap projection route only)
- apps/live-control-ui/src/api/types.ts (historical projection response only)
- apps/live-control-ui/src/api/liveApi.ts (historical projection client only)
- apps/live-control-ui/src/modules/IngestionModule.tsx
- apps/live-control-ui/src/modules/IngestionModule.test.tsx
- tests/test_historical_recap_world_projection.py
- tests/test_live_recap_ingest_graph_preview_api.py
- tests/test_graph_preview_routes.py (scoped historical route tests only)

No worldGraphSurfaceContext.ts, Build, Agent, selected-World registry/provider, schema/migration, corpus, retained source or Graph changes. Return concrete extra-path needs to PRIME once in a batch; do not expand capability silently.

## Verification and runtime lease

Prove managed!=native success; foreign selected managed World; remap/version drift before and during read; missing frozen context; APP/source mismatch; A→B→A late reply; exact-run/source identity; and actual Process(mock extraction) → fresh APP source → node-bearing projection → rendered reader/reload. Use synthetic data and unique disposable APP DBs on host54329. Report inherited failures separately. No paid provider calls, retained Graph publication, real recap ingestion or operator draft interaction under this slice.

Isolated NON-SERVING UI5206/API8006 only if both are free; do not evict listeners. Explicitly configure/assert the UI proxy points to its leased API before any browser navigation. All fixture registry/source/World reads and writes must resolve within disposable roots; assert an empty synthetic artifact selector before Process. Reject any request to live8000/8001/8002. Use try/finally cleanup for processes, browser and disposable DB; verify owned listeners are gone on success/failure and before handback. Keep 5202/8000,5876/8002,publication8001 untouched. The operator explicitly requires shutting down test servers when finished.

Previous witness isolation incident: an initial preview used Vite default proxy8000 and GET /api/live/graph-preview/artifacts?campaign_id=longmont-c2 may have refreshed derived recap registry metadata through ensure_recap_artifacts_registry. It stopped before Process/source submission/World writes. Do not repeat a live GET or rollback data to investigate this incident; preserve that bounded evidence.

Finish implementation → owning tests/rendered witness → cumulative diff inspection → commit/push/PR. Return exact head, tests, screenshots/evidence, remaining gates and cleanup confirmation. Independent ARCHITECTURE review and PRIME merge remain required; no redundant operator permission gate for ordinary authorized execution.

## Implementation checkpoint — 2026-10-16

The scoped selector, frozen/current binding checks, projection snapshot check, response tuple, exact-run UI request/verification, and A→B→A stale-response guard are implemented in the leased files. Generic unscoped historical reads do not receive managed binding metadata and retain the existing projection semantics. Synthetic regressions cover managed/native ID divergence, foreign selection, pre-/mid-read registry drift, source/snapshot mismatch, missing frozen context, duplicate selector, exact-run UI binding, and selection changes.

Owning-boundary verification passed: Python 3.13 pytest for the three relevant suites (62 passed), the IngestionModule Vitest suite (41 passed), TypeScript app check, UI production build, scoped Ruff checks for changed Python files, `compileall`, and `git diff --check`. The build reports its existing large-chunk warning; Vitest reports existing React `act(...)` warnings in the local-navigation test. A broader Ruff invocation also found an unused import in untouched `apps/live_control_server/routes/recap_ingest.py`; that file is outside this handoff’s diff.

One earlier pre-fix local test invocation used checkout-root registry paths and may have replaced pre-existing ignored files under this isolated `/tmp` checkout’s `out/registries`; the exact pre-state was unavailable, and no speculative restoration or deletion was attempted. The fixture now redirects all writes into pytest `tmp_path`. This bounded caveat was separately reported to PRIME.

Rendered witness used a unique disposable APP-STATE database, synthetic Session 22 recap, synthetic managed binding `elderwyld` → native `world:elderwyld`, and a synthetic Mireward projection. Process created an exact ExtractionRun and durable APP source. The Ingest reader loaded that exact source and its node-bearing Mireward pill on initial load and after a fresh page reload; hovering the pill revealed its synthetic summary. Exact recap projection and artifact-catalog reads returned 200 through the Vite proxy explicitly set to `http://127.0.0.1:8006`. At 390px the document had no horizontal overflow. Screenshots were captured locally at `/tmp/ingest-managed-projection-desktop.png` and `/tmp/ingest-managed-projection-narrow.png`.

Acceptance limitations: the isolated app has no local Agent session service, so `/api/live/agent/local-session` returns 503 and the global Graph badge says “Needs attention”; the exact recap projection reads still succeed. On the narrow screenshot, the shared hover summary card sits against and is partially clipped by the right viewport edge. Its shared styling is in `apps/live-control-ui/src/graphReference/graphReference.css`, outside this exclusive lease; do not expand this slice silently. PRIME should track that narrow hover-card issue separately. No full World integration, live Graph object expansion, real recap/provider use, retained Graph publication, or operator draft interaction is claimed.

The API and UI previews were stopped; ports 5206 and 8006 have no remaining listeners, and the unique disposable APP-STATE database was confirmed dropped. 5202/8000 remain untouched. Keep this PR in draft pending independent ARCHITECTURE review and PR CI; PRIME retains merge authority.
