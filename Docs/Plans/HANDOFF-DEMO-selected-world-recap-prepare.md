# HANDOFF — DEMO: bind recap prepare to the selected managed World

**Status:** SETTLED — Buddy PR #985 merged at `c49bde2fb91a5e7722f4332c1792e3267cf337cd` from reviewed head `490be0fdf99a127fccfb78268cc8e78f2bde10a0` on 2026-10-07. Its ten-path caller lease is closed.
**Owner:** DEMO. PRIME owns independent review, merge coordination, and runtime rollout.
**Base:** `origin/main@7f429fa63680bbaef91316132cfe02dc46c072fd` (after SERVER #983 merged).
**Branch:** `codex/demo-managed-world-recap-target`.
**Topology:** parallel-independent from PRIME's #979 interrupted-turn recovery lane, #970 Plan readers, and SERVER #982 diagnostics-only rollout; their active code paths do not overlap this slice. PRIME explicitly transferred the roadmap path below from #979 to this lane.
**Test-path addition:** PRIME explicitly added `GraphReviewWorkbenchModule.test.tsx` alongside `GraphReviewGenericRun.test.tsx`; both contain existing run-only prepare expectations and are in this same single capability lease.

PR #985's merge completed this caller slice without preparing or publishing a
recap, writing runtime/database/Graph state, or accepting the connected demo.
The historical branch and base below identify the reviewed implementation.

## User outcome

Review a recap for the currently selected verified managed World before confirm. The active production prepare caller, `GraphReviewWorkbenchModule`, must send the exact selected managed World ID to the existing #980 prepare contract. The separately leased `GraphReviewSessionToolbar` component must follow the same contract in its direct-mount coverage; it currently has no production callsite. The run's campaign, session, and declared source World remain source scope; they never select the publication destination.

## Accepted contract and failure handling

- Read `useSelectedWorld()` at each caller. Only `kind === "managed"` supplies a usable `worldId`; do not infer from campaign, run, source artifact, status endpoint, or default World.
- Make `managedWorldId` required in the Buddy request type and API call, serializing it with the existing schema, run ID, and optional node IDs. SERVER #980 still validates the active binding and seals/revalidates native identity at prepare/confirm.
- Disable prepare and show useful guidance for legacy, loading, or failed verification states.
- Capture the selected target for each request. If the selected World changes while prepare is pending, clear any old sheet and ignore the stale success/error so a review for World A cannot appear under World B.
- `GraphReviewSessionToolbar` currently consults a status endpoint that has no selected-target input. PRIME authorized removing this global/default-World preflight from the caller; let selected-target prepare determine readiness and show its typed failure. Do not expand or change the endpoint.
- Keep confirm-time server checks authoritative. This UI slice does not publish, confirm, change runtime state, or exercise a provider.

## Historical write lease (released at #985 merge)

The original implementation allowlist was:

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
- The latest re-anchor fetched `origin/main@7f429fa63680bbaef91316132cfe02dc46c072fd` after SERVER #983 merged. Open PRs #970, #979, and #982 were checked; #982 is diagnostics-only, #970 is disjoint, and #979 retains only its superseded roadmap hunk pending reconciliation. No PR was assigned to this lane before publication.
- PRIME separately leased #979's conversation source/test paths to a recovery lane for the interrupted-turn refresh state. Those paths do not overlap this allowlist; #979's later rebase must carry its default-Graph change onto the settled recovery fix. This is not a gate for the selected-World prepare slice.
- Callsite audit on the re-anchored source found `GraphReviewSessionToolbar` only in its component file and dedicated test; `GraphReviewWorkbenchModule` is the active production prepare caller. The toolbar remains in this lane because it is explicitly named in the authorized write lease; it is not counted as production route coverage.

## Verification record — 2026-10-06

- Rebased on `origin/main@7f429fa63680bbaef91316132cfe02dc46c072fd`. Source/test head `9dcc7c5cc06e5fdf05ac5a6499c733365719d099` passed all four owning files: 85 tests passed.
- `git diff --check origin/main` passed.
- `npm --prefix apps/live-control-ui run build` stopped in `tsc -b` at the existing error `src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace 'JSX'`. That file is outside this lease and unchanged; Vite did not run.
- No runtime, provider, shared database, or Graph write was exercised. No recap was prepared or published.

## Owning-boundary acceptance

Prove all of the following with mounted/UI and transport tests:

1. Prepare serializes the exact selected managed ID, run ID, schema, and optional node IDs.
2. The active production caller and the separately tested toolbar component send World A's exact ID; no campaign or source identity is substituted.
3. Missing/unverified selection disables the caller and exposes actionable guidance.
4. A pending World-A prepare cannot populate a review sheet after switching to World B; a matching current-World response still opens review.
5. A target-specific prepare rejection leaves the review/confirm sheet closed and displays the server's typed message. A default status response for another World cannot gate the selected-target request.

The four owning test files and `git diff --check` passed on the recorded source/test head. The UI build/typecheck retains the recorded inherited JSX namespace failure. Inspect the exact cumulative base-to-head diff before publication; do not claim rollout, publication, operator acceptance, or J1–J6 completion. Push and open/update the assigned PR under repository policy; PRIME retains merge authority.

## Post-merge settlement

Buddy PR #985 merged at `c49bde2fb91a5e7722f4332c1792e3267cf337cd` from exact
reviewed head `490be0fdf99a127fccfb78268cc8e78f2bde10a0` on 2026-10-07. The
ten-path lease is released. Its four owning suites passed 85 tests and
`git diff --check` passed. The JSX namespace build failure recorded above was
subsequently fixed by Buddy #991; DOGFOOD #1000's production build passed on
current main with the existing bundle-size warning. These checks do not claim
recap publication, production rollout, operator acceptance, or J1–J6 completion.
