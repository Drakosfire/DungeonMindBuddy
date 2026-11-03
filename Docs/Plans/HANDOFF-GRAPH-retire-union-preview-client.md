# GRAPH: retire the unused Union preview client

Status: MERGED_DELIVERED; implementation and delivery leases RELEASED.
Owner: PRIME. Base: origin/main@94e969cc68c85e0f6b6514cc245fa408c294e4f6.
Branch: codex/retire-union-preview-client.
Checkout: /home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy.
Topology: serial GRAPH successor to merged/delivered PR2050. Parallel-independent
of ADVERSARY PR2051@e834db1d937be81756be2522a19241df4658553b (four profile/test/
quality-handoff paths; no overlap). Relevant open-PR file audit found no shared
expected path; the older observation-review PR touches different API/workbench
files. Reuse this checkout/dependencies. No provider, new environment, database,
running service, publication or Graph/Gold effect lease.

## One reviewable outcome

Remove getUnionSupergraphProjection, its default wrapper, query type, exclusive
preview-source environment read and exclusive response-type import. There is no
current application consumer; remaining executable references are obsolete mocks,
spies and three transport-serialization tests. Those tests pretend the retired
HTTP 410 endpoint serves projections. Remove that false client capability without
replacing it with a shim, fallback, alias or another store.

Most changed paths are narrow test closure for that one deleted export. Preserve
native request bodies, owner/binding checks, explicit prepare/confirm, unknown
outcome/recovery assertions and current Graph/Gold readers. Do not remove whole
current tests merely because an unused mock is present. Remove only exclusive
mock properties/calls/imports/negative assertions and newly unused local fixture
values; retain their other assertions. A source-only test title/comment may be
updated to describe the remaining native behavior accurately.

## Exclusive expected write set

- apps/live-control-ui/src/api/liveApi.ts
- apps/live-control-ui/src/api/liveApi.test.ts
- apps/live-control-ui/src/buildSurface/BuildRecapPublication.test.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel.test.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx
- apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx
- apps/live-control-ui/src/planSurface/graphPreview/GraphIngestProjectionPanel.test.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorDraftWorkspace.test.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts
- Docs/Plans/HANDOFF-GRAPH-retire-union-preview-client.md
- Docs/Plans/HANDOFF-GRAPH-retire-union-recap-renderer.md
- Docs/Plans/HANDOFF-INGEST-database-execution-evidence.md

Only the liveApi.ts retired block/import/config/default wrapper and one obsolete
comment in graphReviewLiveReviewState.ts change application source. The nine
listed test files close retired imports/mocks; liveApi.test.ts loses only three
exclusive serialization cases. The two predecessor handoffs record truthful
merged/delivered completion and close superseded implementation leases. No other
source/test/contract path is authorized without a checkpoint.

## Critique, preservation and validation

UnionSupergraphProjectionResponse and shared fixtures still support current
Graph/Gold presentation. Do not edit api/types.ts, shared readers, native Graph
transport, backend directory discovery or its retired endpoint, Gold/fixtures,
source identity/admission/publication, model policy or ADVERSARY's quality files.
The remaining developer route/panel/retired-state machinery is a separate audit
and cleanup; this slice does not finish the overall demolition goal.

Removing a spy is not evidence that native authority remains correct. Run the
existing nine-file API/native-review cohort before and after, compare exact failed
names/messages at base, and preserve the remaining publication/receipt assertions.
Expect only the three retired serialization tests to disappear. Run full fresh
TypeScript checking and inspect import/caller closure. Preserve all original
failures; do not repair adjacent fixtures, restore the export for tests, or call
an inherited failing cohort all green. No new mirrored deletion tests are needed.

Review the exact cumulative diff, commit/push/open one PR, obtain independent
Bugbot review and applicable CI, then merge/deliver under standing PRIME authority
with a separately re-anchored resource lease. Technical checks are not model,
Gold, ordinary dogfood or operator acceptance. No live data effects are authorized.

## Author verification

Fresh full TypeScript checking passes and neither retired export/config/query
symbol remains in UI source/tests. Exact-base nine-file cohort: 259 passes and
12 failures; after removal: 256 passes and the identical 12 failed names/messages.
Only the three retired serialization cases disappeared. Existing failures concern
conversation-history mock shapes and the Published recap selector; they remain
retained and are not counted as passing or repaired here.

A TypeScript-AST assertion audit verifies all other expect chains are unchanged,
excluding only retired-function negative assertions and those three exclusive
cases. Native prepare/confirm, receipts, unknown outcomes and owner checks remain.
The consumed authoring projection fixture stays; only one fixture used solely by
the removed mock was deleted. No alias/stub was introduced. Evidence:
union-preview-client-author-verification.json and linked original logs/assertion
proof. Independent review, CI and protected merge/delivery remain required.

## Completed predecessor settlement

Merged ce41c101cd7af7a19d4ab467638bbbbc0c969b7e after independent exact-head and
actual-merge review plus all seven CI checks. Delivered and conserved8,958source
blobs,91primarytables,nine sessionfiles,savedPlanHTTP and439nativeobjects. UI
base/head/serving118file manifests identical; no frontend replacement required.
API health ready; provider0,DBwrites0,dependencies unchanged. The exact review,
inherited test failures and delivery limits above remain distinct. Proof:
retire-union-preview-client-api-delivery-proof.json under the established private
runtime-evidence/q01-published-graph-authority root. This closes the prior lease;
it does not claim the larger demolition or ingestion-quality objective complete.
