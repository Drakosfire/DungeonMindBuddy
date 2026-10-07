# HANDOFF — DEMO: bind recap prepare to the selected managed World

**Status:** ACTIVE — PRIME authorized the Buddy caller implementation on 2026-10-06.
**Owner:** DEMO. PRIME owns independent review, merge coordination, and runtime rollout.
**Base:** `origin/main@87308f996289e5c3fde5c82d29c24a6203b95302` (after SERVER #981 merged).
**Branch:** `codex/demo-managed-world-recap-target`.
**Topology:** parallel-independent from the frozen #979 source lane and SERVER diagnostics; their active write paths do not overlap this slice. #970 remains open with disjoint Plan reader paths. The roadmap path below was explicitly transferred by PRIME from #979 to this lane.
**Test-path addition:** PRIME explicitly added `GraphReviewWorkbenchModule.test.tsx` alongside `GraphReviewGenericRun.test.tsx`; both contain existing run-only prepare expectations and are in this same single capability lease.

## User outcome

Review a recap for the currently selected verified managed World before confirm. Both production prepare callers must send the exact selected managed World ID to the existing #980 prepare contract. The run's campaign, session, and declared source World remain source scope; they never select the publication destination.

## Accepted contract and failure handling

- Read `useSelectedWorld()` at each caller. Only `kind === "managed"` supplies a usable `worldId`; do not infer from campaign, run, source artifact, status endpoint, or default World.
- Make `managedWorldId` required in the Buddy request type and API call, serializing it with the existing schema, run ID, and optional node IDs. SERVER #980 still validates the active binding and seals/revalidates native identity at prepare/confirm.
- Disable prepare and show useful guidance for legacy, loading, or failed verification states.
- Capture the selected target for each request. If the selected World changes while prepare is pending, clear any old sheet and ignore the stale success/error so a review for World A cannot appear under World B.
- `GraphReviewSessionToolbar` currently consults a status endpoint that has no selected-target input. PRIME authorized removing this global/default-World preflight from the caller; let selected-target prepare determine readiness and show its typed failure. Do not expand or change the endpoint.
- Keep confirm-time server checks authoritative. This UI slice does not publish, confirm, change runtime state, or exercise a provider.

## Exclusive write lease

The only expected write paths are:

- `Docs/Plans/HANDOFF-DEMO-selected-world-recap-prepare.md`
- `Docs/Roadmaps/ROADMAP-demo.md`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/api/extractPromoteApi.ts`
- `apps/live-control-ui/src/api/extractPromoteApi.test.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewSessionToolbar.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx`

Any needed route/schema change, selected-world resolver change, confirmation-sheet redesign, server/runtime change, or additional path is a stop-and-rebrief signal. Shared ports, databases, corpora, and runtime processes are read-only and unused by this lane.

## Re-anchor and collision record

- Buddy #980 merged at `a92371b7b2e727d1d45bef1c8e1d7a3d01b58193`. It requires explicit `managedWorldId`, resolves and seals the verified managed/native binding, rejects a conflicting declared source World, and revalidates before a governed write. It does not change the UI or status endpoint.
- SERVER #981 merged at `87308f996289e5c3fde5c82d29c24a6203b95302`; its diagnostics paths are server-owned and disjoint. The historical Graph Ask remains one terminal failed turn with no replay.
- DEMO #979 remains open/draft at frozen head `147709865824f3ae680c9011a3a185c994c7dd69`, based on `a869c27a7b4b3d6e77048bbb80a55984d709e705`. Its source review passed, and the one live question verified the default checkbox but failed to produce a completed Graph answer (`answer_validation_failed` after provider response). PRIME transferred `Docs/Roadmaps/ROADMAP-demo.md` to this lane; #979 must rebase and drop/reconcile its superseded roadmap hunk before any later merge. Do not edit its source branch or retry the question.
- Open #970 changes Plan reader/page/card paths, not this lease. #981's former server diagnostic paths are outside the lease and merged. No current PR edits this lane's eight code/test paths.

## Owning-boundary acceptance

Prove all of the following with mounted/UI and transport tests:

1. Prepare serializes the exact selected managed ID, run ID, schema, and optional node IDs.
2. Each caller sends World A's exact ID; no campaign or source identity is substituted.
3. Missing/unverified selection disables the caller and exposes actionable guidance.
4. A pending World-A prepare cannot populate a review sheet after switching to World B; a matching current-World response still opens review.
5. A target-specific prepare rejection leaves the review/confirm sheet closed and displays the server's typed message. A default status response for another World cannot gate the selected-target request.

Run the four owning test files, the relevant Graph Review suites, `git diff --check`, and the UI build/typecheck. Preserve any inherited failure precisely. Inspect the exact cumulative base-to-head diff before commit and PR. Update the roadmap and this handoff with truthful test/head evidence; do not claim rollout, publication, operator acceptance, or J1–J6 completion. Push and open/update the assigned PR under repository policy; PRIME retains merge authority.
