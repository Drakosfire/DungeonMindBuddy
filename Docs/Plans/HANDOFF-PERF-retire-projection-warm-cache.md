# One pending projection transport owner

**Status:** COMPLETE; reviewed, merged and accepted on5202; source lease released.
**Base:**7da2ef9b8d2bf047fcfdd5ba82eee1c4a9b0b3c9; branch codex/retire-projection-warm-cache, existing buddy-context-loop checkout.
**Topology:**serial after accepted1494. Current open work has no overlapping projectioncache/API lease. UI5202 only; API/data/dependencies unchanged.

## Invariant and critique

Retire legacy global projectionRequestCache (native+recap120-secondTTL/eightsettledentries) and its test/config/stats/reset interfaces. Existing protected transport already owns exact pending sharing for native/recap/managed projectionPOSTs with access/options/body/responseclone fences. No settledprojectionHTTPcache remains; explicit sequential reads are fresh. Do not add a substitute TTL, compatibilitymodule/reset shim, new projectionSignal option, demand/idle/providerlifetime policy or eager Graph redesign in this slice.

Keep existing credential/reconnect/revoke/mutation dispatch+settlement startReadWave hooks. Replace cache's revision-event invalidation with one small API-boundary event→startReadWave binding installed BEFORE first projectionrequest, shared byallthreeprojectionwrappers. Track actualEventTarget and remove/rebind on window change; HMR disposal unregisters current listener. It retains no responses/promises/timers. The global wave deliberately retires sharing across protectedreads, not just projections.

startReadWave clears pendingregistry/incrementsversion, but current owners may finish their capturedread. Do NOT claim it rejects all oldowner bodies. After-event acquisitions cannot join before-event requests; old settlement cannot delete the newer pendingentry or populate a removed globalcache. Existing consumer/epoch/channel validation continues to own display admission. Native/managed/recap exactserialization, World/revision/scope/error semantics unchanged. Expected extra genuine sequential reads until later demand ownership are honest freshness costs, not duplicated pendingwork or a universal navigation-performance win.

## Exclusive expected write lease

- This contract and accepted1494 HANDOFF-PERF-ingest-initial-run-owner.md settlement.
- UI src/api/liveApi.ts: remove cacheimport/resetcalls/wrappers; exactbodyapiFetch and scoped revisionlistener only. Existing inFlightReads.ts behavior unchanged.
- Retire src/planSurface/reference/projectionRequestCache.ts and its dedicated tests; no fallback/exportstub.
- Existing src/api/liveApi.test.ts remove retired resets; liveApi.readEfficiency.test.tsx and/or new projectiontransport owner test file: pendingequivalence, settledsuccess/errorfreshness, commit-eventwave/newpendingidentity, credential/body/request isolation, listeneridempotence/window/HMRownership wheretestable.
- Other test imports only if finalconsumerclosure requires; shared Graphprovider/channel/renderers unchanged in this prerequisite.
- Owned5202 index/assets after exact-head review/merge, preservepriorproductassets; no APIrestart/sourceexport/data change.

Verify pendingnative/recap/managed1HTTPperexactkey, sequentialsettledsuccess/error2, postcommiteventdistinctnewresponse witholdcompletionnotdeletingnewrequest, auth/header/scope/query/bodyfieldsdistinct, existingmutation/clone/bodyguards and nativeWorldbinding/errorpreservation. FocusedAPI/transport/rendererownercohorts, actualapp tsc/build, cumulative diff and independent exact-head review, merge and native/protected17acceptance. No totalRAM/target-laptop claim from source retention analysis. Next demand capability will release fullprojection AND scopedchannelbytes on last consumer; it must address existing commit-before-cancelled provider bug separately. Rulesuser+Agenttool/Combat stillpending; rulegraph experiments wait for all objectives.

## Author verification

Focused transport/acquisition cohort50/50 passes, including14 new projection acquisition cases; API/native Graph provider boundary153/153 passes. Actual application TypeScript project and production Vite build pass (existing large-chunk warning remains). No retired cache references remain under UI src. Cumulative source diff inspected and diffcheck clean. Production entry index-BtItgvKx.js; no runtime adoption before exact-head independent review. Sequential fresh reads are deliberate; no measured total-memory or universal latency claim.

## Accepted delivery

Architecture/Bugbot Cycle1 APPROVE exact9012a0ab039dbbbbe022b1e5009b69ac32fe7868; independently203/203 focused tests. PR1495 merge4574abf82ef176fbcf870628107d5c9e46a7f83b. UI-only default5202 index-BtItgvKx.js, indexSHA256a8c4a6c70d3f177dc7706b314f7bf4ed512aa884a5ac08653a6c6cccf423f111; prior assets retained, API unchanged/healthy. Native Plan one managed projectionPOST200/no inference and Next→Document→Cards retained First sight of Edge. Ended Play review/reflections rendered. All17protectedresponses unchanged. Owned tab/temporaryHTML removed. Native evidence belongs PRIME, independent review source/tests only. No demand/memory reduction claim.
