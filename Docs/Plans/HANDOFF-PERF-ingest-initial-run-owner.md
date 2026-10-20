# One initial exact-run observation per Ingest navigation

**Status:** COMPLETE; source lease released and accepted on5202.
**Base:**407c9a6730e0c84ecb3843ae9a7093ce4160fae4; branch codex/ingest-initial-run-owner, existing buddy-context-loop checkout.
**Topology:**serial after accepted1493; one useful frontend read-ownership capability, no backend/schema change. UI5202 artifacts owned; existing API/runtime/data untouched.

## Invariant and critique

Native current exacthandoff fetches same run twice sequentially (rootvalidation then Workbench). Root owns one navigation-scoped initial fullrecord observation and distributes it to root sourceReview and Workbench. Required discriminated observation prop; Workbench has NO fallback getExtractionRun and no optional legacy transport. Sole production caller is MemoryIngestPage. Test-only owners instantiate explicit observation/provider fixtures; they do not justify a product fallback. Retain downstream exactID/artifact/document/status/review-package checks, current source-review-only and Worldownership decisions. An observation is parsed transport data, not an admission verdict, latest choice or perpetual current authority.

One read per navigation/retry generation, exact World/fullsearch/allhandoffpins/generation binding, abort unresolved record/PlanView requests, reject late body results including A→B→A. Unresolved reads fence access-identity changes; accepted initial observations keep the existing captured lifetime. No NEW subscription/refetch on mutation readwaves, global settledcache/TTL, automaticrepost or continuous freshness claim. Fresh review/prepare/server action admission remains authoritative. This preserves activeconfirmation/correction/unknownresult/receipt ownership rather than unmounting it at mutation start/end. Broader continuously refreshed authority would need a separate lifecycle contract and synchronous transaction safeguards.

Use one current ownedsearch for branch/context/Agentpublication, not a mixture of window.location.search and effect state. Synchronously suppress stale context/sourceReview on navigation identity mismatch before effects; root errors remain explicit with read-only retry. Root verifies recordID and claimed artifact before presenting metadata; Workbench repeats relevant identity checks and server document lineage resolution. World/source-domain decisions stay current as before; no handoff means no exact-run read. Corrected child-run navigation updates the sole owner and gets a fresh observation. Preserve orphaned drafts, DOM state and all transaction/recovery semantics.

## Exclusive expected write lease

- This contract and accepted1493 HANDOFF-PERF-retired-ingest-catalog-reads.md settlement.
- UI ingestSurface MemoryIngestPage.tsx and test; new ingestInitialRunObservation.ts for closed observational type/identity helpers if useful (no second production loader).
- UI planSurface/graphReviewWorkbench GraphReviewWorkbenchModule.tsx and its current module/genericRun tests: required observation consumption only, existing downstream checks retained.
- UI src/test/ingestRunObservationTestHost.tsx (test fixture only) if needed to share explicit root-like observation ownership across direct module tests. No compatibility product path.
- UI api/liveApi.ts: optional transport AbortSignal for getExtractionRun/getPlanView only; exact query/body unchanged. Existing API tests verify transport-only signal/cancellation.
- Other existing owner test fixtures passing the Workbench only if required by the new required prop; no shared registry/lockfile/API/schema edits.
- Owned5202 index/assets only after exact-head independent review/merge, preserve prior product assets for active tabs.

Verify actual root+Workbench oneexactGET with slowPlanView, claimedlineagepositive, nohandoffzero; invalidWorld/artifact/record/selectors/error nofallback; route/World/ABA/latebody/accessduringpending/abortunmount/readretry; synchronous staleAgentcontext retirement; correctionchildfreshread; mutationstart/end duringconfirm/correction/unknownretry keeps owner/receipt/recovery. Focused owner tests, actualapp tsc/build, cumulative diff and exact-head independent review, PR/merge/5202nativeoneGET/protected17unchanged. Broader dead RecapGraphModule/manual/projection cleanup is separate. Full goal remains active: demand-driven fullgraph, heavycontroller split, user+Agent Rules lookup and native Combat; rulegraph experiments only after all objectives.

## Author evidence before independent review

Seven-file root/Workbench/generic/API/publication cohort168passes, including realpage+realWorkbench oneexactGET with deliberatelydelayedPlanView, downstreamcanonicalsourcepositive, acceptedsourceDOMidentity retained across mutationstart/end waves, complete existing correction/uncertain/receipt cases. Sixnewroot witnesses cover artifact mismatchbeforemetadata, incompleteclaimedlineagebeforelookup, A→B→A latebody/cancel plusstaleAgentcontext, unresolvedaccessrotationcancel/retry, acceptedowner lifetime, explicitfailedreadretry/unmountabort; existingWorld/source-only childremount cases pass. OptionalAPI signals verifiedtransport-only on exact encodedrun/PlanView URLs. Test-onlydirectWorkbench mounts use an explicit observation owner, no productionfallback. Fresh correction-child proofread remainsdistinct frominitialnavigation (keptunchanged), and subsequent childnavigation is fresh.

Actualapp `tsc -p tsconfig.app.json --noEmit` and productionbuild pass. BroaderIngestion/App/navigation retains119pass/5sameknownroot/navigationfailures previouslyexactbasereproduced by1493; no newbroaderfailure. Sourcecumulative diff inspected and diffcheckclean. Nativeaftercount and17protectedacceptance await independentlyreviewedmerge; initialdata is not advertised current aftermutations, no newwavefreshnesssubscription ortransactionlifecyclechange.

## Review, merge and accepted delivery

Architecture/Bugbot ReviewCycle1 approvedexactfad99e35347fbb14bcab4231bf670f160eb3e054; Architecture independently168/168focusedtests, no blockingfinding. PR1494 merged7da2ef9b8d2bf047fcfdd5ba82eee1c4a9b0b3c9. UI-only5202 adoptionindex-CjZti0LT.js/indexSHA25647f93e1eaf28187d3e249588b833fc0b095717c86a3540286dbdd20550f59488; existingAPI/source/services unchanged, oldassetsretained. NativeactualrootIngest→OpenGraphReview sameSession29source handoff nowONEexactGET2002769bytes versuspredecessortwo; reviewpackage200/canonicalsource/read-onlyexistingquoteguardintact,0catalog/providerreads. All17protectedresponsesunchanged. Ownedmeasurementtab/HTML removed. No livepublication/correction; transaction/correction/recovery evidence is owner-test coverage, not userWorldmutation. Screenshot unavailable; nativeDOM/requestmetadata receipts are PRIME evidence, not independentbrowserreplay. Remainingfullgraph/cache/code/Rules/Combat objectives stayopen.
