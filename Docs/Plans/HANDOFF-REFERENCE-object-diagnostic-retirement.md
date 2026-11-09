# REFERENCE: retire the unmounted object diagnostic

Status: ACTIVE source retirement. PRIME owns one serial slice from remote main
fff6c97095eb23827d4f3d83b839f29da229e483, branch
codex/reference-object-diagnostic-retirement, existing buddy-context-loop checkout.
No unmerged parent or runtime lease. Storage recovery hold and coordination-off
instructions remain in force.

## Outcome and caller proof

Remove GraphObjectDogfoodPanel and its private collection model/storage helpers.
Exact component/import-path searches find no production mount or caller outside
these six files. This old manual diagnostic projects a collection of legacy
Graph cards and ratings; it is not the mounted native reference picker or preview.
No replacement store, adapter, picker or provenance mechanism is introduced.

The private CSS suffix in planSurface.css contains only graph-object-dogfood-
selectors. No retained component uses that prefix. Keep the distinct
plan-reference-object-card classes used by ThreatSheetProjection.

Browser records under dmb.planGraphObjectDogfood.* remain untouched. Deleting
this already unmounted UI is not authorization to migrate, clear or rewrite any
stored note, collection, source, draft, World or Run.

## Exclusive write lease

UI paths are under apps/live-control-ui/src:
- planSurface/dogfood/GraphObjectDogfoodPanel.tsx and its .test.tsx
- planSurface/dogfood/graphObjectDogfoodModel.ts and its .test.ts
- planSurface/dogfood/graphObjectDogfoodStorage.ts and its .test.ts
- planSurface/planSurface.css: only the private graph-object-dogfood suffix

Remove exactly the three retired test entries from ci/test-classification.json.
The partition in HANDOFF-PLAY-shared-native-retrieval.md permits these atomic
retirement entries; CI PR2288 retains its other classifications and qualification
paths. ci/contracts.json, the frozen original-command fixture and CI guard code
remain unchanged. This handoff and HANDOFF-REFERENCE-adoption-inventory.md record
the current caller decision.

Retain usePlanGraphReferenceResolver, PlanReferenceObjectCard, projection binding
and shared host, buildPlanGraphObjectActions and its statblock caller, Graph lens,
reference chips and native preview, and all tests of their retained behavior.
The remaining Plan diagnostic/resolver/card retirement is separate: Plan panel
tests are still in the frozen CI command fixture and need an owning contract
decision before removal. Held server PR2104 is unaffected.

## Verification and completion

Before deletion, prove the three test files' actual baseline collected cases and
statuses. After deletion, search remaining imports/symbols/private CSS, verify the
classification delta and unchanged frozen CI contracts, and inspect the cumulative
diff. Run exact-head inventory/command guards and the repo-owned local hosted
frontend/build verifier; validate its immutable evidence. Run the discovered
suite at the integrated checkpoint and account for precisely the retired cases;
retain all unrelated red diagnostics and evaluate any new failure separately.
Obtain independent exact-head review, push/open the owning PR and merge under
standing PRIME authority when source gates pass. This source-only retirement
needs no database, provider, browser-state, migration or service action. The full
References/statblock goal remains open until its other requirements are proved.
