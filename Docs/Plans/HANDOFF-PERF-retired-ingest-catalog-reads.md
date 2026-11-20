# Retire unused Ingest catalog acquisition

**Status:** COMPLETE; source lease released and accepted on5202.
**Base:**337075a3ea175fef94b7e46f306b64a516a7902b; branch codex/retired-ingest-catalog-reads, existing buddy-context-loop checkout.
**Topology:**serial after accepted1492; no overlapping catalog/workbench lease found in current open PRs. API8000 and UI5202 owned established services/source/artifact; no new export/env/data migration.

## Invariant and critique

Current mounted Ingest renders published Memory or exact-run handoff. Its unconditional all-record catalog feeds a retired picker; its Gold sessions/compare effect writes discarded state and null/false provider props. Remove that acquisition closure instead of inventing a paged feature. Mounted Ingest and postpublication must issue zero catalog/unused Gold sessions/compare reads; exact lookup/review/promotion, terminal receipt adoption, unknown-result/recovery, manual variant selection and published Memory remain current. Remove incidental selection resets belonging only to discarded compare; preserve actual selected projection ownership.

Repository-wide closure audit: sole run-changed event listener is retired catalog hook; IngestionModule and promotion sheets only emit it. Optional onCatalogRefresh runs after actual receipt adoption; remove it/error copy, preserve adoption and managed Graph/readwave invalidation. Retire GET /graph-preview/extraction-runs with no fallback/tombstone; POST samepath and exactGET/{run} stay. Internal ingest_run_catalog adapter has REAL product_continuity.ingest_adoption consumer; preserve it, APPSTATE fullrecord/list/lineage/preflight and its typed errors. GraphGoldReviewModule is a genuine independent Gold API consumer; preserve shared endpoints/functions/types it uses. Leave orphaned browser selection bytes untouched; no read/migration/backward compatibility path.

## Exclusive expected write lease

- This contract and accepted1492 HANDOFF-PERF-exact-historical-passage.md settlement.
- UI ingestSurface MemoryIngestPage.tsx and tests; retire useIngestRunCatalogInformation, ingestRunCatalogApi, ingestRunCatalogSurfaceInformation and their tests.
- UI planSurface/graphReviewWorkbench GraphReviewWorkbenchModule.tsx/current module+genericRun tests; retire GraphReviewLoadSurface/LoadLaneSummary and obsolete appliedSelection module/tests after final consumer audit. Remove only catalog-only helpers/event in graphReviewWorkbenchUtils.ts and its tests, retaining live exact/manual/label helpers/types still consumed.
- GraphReviewExtractPromoteSheet, GraphReviewFirstWorldPublishSheet, GraphReviewWorldbuildingPublication and tests: remove obsolete refresh callback/event/error handling, keep terminal adoption/receipts/unknown results.
- UI modules/IngestionModule.tsx: obsolete event emit/import only, existing ingestion behavior unchanged.
- Any affected existing projection/App owner test fixtures only to remove retired required props and assert current behavior; no test deletion masking live behavior.
- Server routes/graph_preview.py catalogGET only; tests/test_ingest_run_catalog_routes.py migrate obsolete list HTTP assertions to retained directadapter owner coverage plus explicit retiredGET405 and current exactGET/POST presence.
- Owned API source file and5202 UI artifacts only after independent exact-head approval/merge, same established runtime/data/dependencies, retain rollback assets.

Prove production mounted Ingest/workbench negative acquisition plus positive exact-handoff/action/Memory and genuine Gold module behavior, publication receipt/adoption/uncertain tests, retiredGET405 andPOST/exactroutes unchanged. Focused owner tests/tsc/build, cumulative diff inspected, exact-head independent review then merge and paired5202 acceptance with17protected responses unchanged. No listing/schema/Rules/Combat redesign. Full goal remains active; broader demand-driven fullgraph/code loading, user+Agent Rules lookup and native Combat remain open; rule-graph experiments wait for all objectives.

## Author evidence before independent review

Native accepted baseline rootIngest makes one unusedcatalogGET200,631167decoded/encodedbytes, noGoldcalls on this rootbranch. RealMemoryIngestPage+realWorkbench exacthandoff test and publishedMemory/configrerender tests assert0catalog/Goldsession/compare acquisition; preserved independentGraphGoldReviewModule test passes itspositiveAPIreads. Current7fileIngest/exact/publication/Goldownercohort147passes; broaderIngestion/App/navigation119pass/5inheritedfailures. Exactbase337075a3e reproduced same fiveApp/navigation failures (39pass/5fail) using a temporary same-checkout source swap held in memory and restored in finally; no extra checkout/export or production artifact change. Old reader label assertions now use currentWorkingrecap region and deferredDiagnostics waits for actual content; no live receipt/unknown/recovery coverage removed.

Directinternalcatalog/routecohort7passes, preserving continuity adapter's shape/error/authority coverage and current exactread, explicitlyretiredGET405/JSON and POST/exactroutepresence. Existing Pydantic schema-shadow warnings unchanged. TypeScript actual applicationproject `tsc -p tsconfig.app.json --noEmit`, productionbuild and diffcheck pass. Native aftercounts/pairedAPI/UIdelivery/protected17acceptance await independentlyreviewedmerge. Furtherrepeat exactrun rootvalidation/Workbench reads merit a separate owned successor; no authority-reuse shortcut introduced here.

## Review, merge and accepted delivery

Architecture/Bugbot ReviewCycle1 approvedexactb69dc49ff5aa463befb6d255962f7258b3aee916; Architecture independently147/147focusedUI tests. Backend7/build/tsc/baseline proof remain author evidence. PR1493 merged407c9a6730e0c84ecb3843ae9a7093ce4160fae4. ExistingAPI619trackedruntimepaths matched337 beforeonegraph_preview.py atomicupdate/systemctlrestart; healthy200/retiredGET405,7expirednonterminalAgentrowtuples unchanged/no liveclaims. PID3086085, sameunit/bootstrap/source/env/dependencies/data; no migration. Default5202 index-q7GJqxTM.js/indexSHA25684f1ed0126328ec60cdf3226f0f3fd1b5baed0e05e229ffcf761bf58c454722a; oldassetsretained.

NativeacceptedrootIngestSession29candidate66nodes65relationships intact,0catalogGET versusbaseline1GET631167bytes;0unusedGold/providerreads. ActualOpenGraphReview handoff opens exactreadonlysource/reviewpackage200/canonicalprose andexistingnonliteralquote guard, no catalog/Goldreads, no publication/correction submitted. Postpublication absence/adoption is owner-test evidence, notliveWorldmutation. All17protectedresponsesunchangedafterAPI/browser; ownedtabs/temporarymeasuremententryremoved. Screenshot unavailable, DOM/requestmetadata evidence belongsPRIME. Nativealsofoundtwo sequentialsameexactrunGETs(root/Workbench), ownedbythe successor ratherthanclaimedfixedhere. Unusedsource-onlycatalogutilities/pickerclosure remain aseparatereachabilitycleanup; acceptedinvariantiszero unusedreads, notexhaustivedeadcodepurge.
