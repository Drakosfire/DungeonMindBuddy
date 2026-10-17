# HANDOFF — INGEST recap route consistency

**Status:** ACTIVE — PRIME dispatched the scoped #1299 failure-path repair in the existing assigned checkout.
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` (reused; no new worktree).
**Base:** rebased onto `origin/main@892cc46b50c3420765c00064db1dec46248c4d7d` after verifying the current remote main through GitHub.
**Branch:** `codex/ingest-1299-repair`, created from tested candidate `83a0eee183744071cf065bba6b715a3ba3eb518b`.
**PR:** [#1299](https://github.com/Drakosfire/DungeonMindBuddy/pull/1299), `INGEST: preserve drafts across saved recap routes`.
**Topology:** serial repair on the existing #1299 PR. No additional PR. PRIME retains merge authority.

## Lane preservation

The parked `codex/dogfood-recap-presentation` changes were saved in `stash@{0}` with message `PARKED dogfood-recap-presentation before INGEST-1299 repair`. `git stash show --include-untracked --stat stash@{0}` verified ten paths, including the untracked DOGFOOD handoff. Do not apply this stash into the #1299 repair branch; preserve it for its own future lease.

## Mission

Preserve unsaved drafts while direct saved-recap URLs and picker navigation behave consistently. Repair the failure path where returning to a draft before a pending `inspect_status` settles leaves `loadingPriorIngestion` true, gates autosave, and loses edits on remount. Limit new product changes to this failure-path repair and its paired regression cases.

## Current-code evidence and invariant

- `?campaign=<id>&session=session-N&view=recap` is explicit reader intent. It restores the exact recap and opens the graph-enriched reader.
- A direct saved-recap URL without `view=recap` currently hydrates the exact session. If a current normalized source is proven and no non-empty matching draft is restored, the component automatically enters the reader and its restore path canonicalizes the URL to `view=recap`.
- A matching non-empty local draft suppresses automatic reader entry. This preserves editable operator text and must not be overridden merely to force the reader.
- The prior dogfood observation reported a different direct-link view from picker navigation. Reproduce both the no-draft and matching-draft cases at the UI boundary. If the draft-preservation path is the distinction, make that path clear and offer an explicit way to open the saved reader while retaining the draft.

> **Invariant:** view intent follows verified saved-source state and explicit draft intent. Preserve a non-empty draft under its original storage key and campaign/session identity across reader navigation and remount. Read-only projection never overwrites, clears, or obscures an unsaved draft without a visible, reversible operator action. Do not imply that a local projection or candidate was admitted to World memory.

## Exact write set

- `Docs/Plans/HANDOFF-INGEST-recap-route-consistency.md`
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`

No other files. No API, extraction, persistence, schema, provider, corpus, Graph-admission, shared-navigation, or runtime-service changes. Do not edit or apply the parked DOGFOOD paths.

## Acceptance

- Test a direct exact-session URL without `view=recap`, both with no saved draft and with a different-session draft in the editor slot. It must reach the same graph-enriched reader as picker loading, canonicalize the URL without adding a history step, and preserve the other-session draft across hydration.
- Test a matching unsaved draft on a direct URL; it remains editable and its text is preserved, with clear status explaining why the reader was not opened automatically.
- Test loading a saved recap with a different session identity while a draft exists through both the picker and direct URL. The draft remains stored under its original key, the saved reader opens, a remount preserves the draft, and a visible Return to draft action restores the original session and text.
- If a direct saved-recap route cannot be verified, keep the mismatched draft visibly recoverable. Do not expose an editor whose selected session would not be persisted over the preserved draft key.
- Preserve unrelated query parameters and exact campaign/session binding.
- Keep source and Graph-admission claims truthful.
- Test `returnToDraft` while `inspect_status` is pending, covering both later resolution and rejection. After editing, autosave must resume and a remount must restore the new text.
- Verify with the focused IngestionModule UI suite, package typecheck/build where available, and `git diff --check` against the rebased head.
- No provider calls, Process, Graph Review mutation, graph admission, source publication, server-side persistence write, or 5202 change/restart. Browser-local draft storage is in scope and is explicitly verified by the tests.

## Implementation and verification evidence

- A direct exact-session URL without `view=recap` still opens the graph-enriched reader when the saved normalized source is verified and no matching draft is present; the URL is canonicalized to `view=recap`.
- A different-session draft in the editor storage slot is now protected during that direct-route hydration too. The draft candidate is identified before the automatic reader transition, so the persistence effect cannot replace it with the requested saved session’s empty editor state; `Return to draft` recovers it after a reader remount.
- If the exact-session URL cannot be verified, the preserved draft is shown with a clear “Draft preserved” notice and only the Return to draft action; this avoids showing a blank editable surface whose changes would not be persisted while the candidate draft is protected.
- When a matching non-empty draft exists, the editor stays open, the status explains that the draft is open, and `View saved recap` opens the saved projection without replacing that draft.
- Loading another processed recap now suspends draft writes while the reader is active, retains the draft under its original campaign/session local-storage key, and exposes `Return to draft`. The return action restores the draft identity and text; remounting the saved-reader URL also recovers the return action from the original draft key.
- `npm run test -- src/modules/IngestionModule.test.tsx`: passed, 43 tests, including successful direct-route return and an unverified-route recovery path.
- `npx vite build`: passed independently; Vite reports the repository’s existing large-chunk advisory. `npm run build` cannot reach Vite because the package typecheck step reports the existing WorldPlanAgentAnswer errors below.
- `npm run typecheck`: still stops on five existing errors in unchanged `src/planSurface/components/WorldPlanAgentAnswer.tsx` (TS2532 line 47, TS18048 line 49, TS2339 line 50). The edited Ingest files are not named by these diagnostics.
- `git diff --check`: passed.
- `returnToDraft` now clears the prior-inspection loading state after invalidating the pending request. Two parameterized regressions cover both a late resolve and a late rejection, then verify updated draft text persists and survives remount.
- On the rebased candidate: `npm run test -- src/modules/IngestionModule.test.tsx` — 45/45 passed. React emitted non-fatal `act(...)` warnings from existing asynchronous UI updates.
- On the rebased candidate: `npx vite build` — passed; existing large-chunk warning remains.
- `npm run typecheck` — still fails on five existing errors in unchanged `src/planSurface/components/WorldPlanAgentAnswer.tsx` (TS2532 line 47, TS18048 line 49, and TS2339 three times on line 50). No diagnostics point to the leased Ingest files.
- `git diff --check origin/main...HEAD` — passed before this handoff update.
- No provider calls, Process, Graph Review mutation, graph admission, source publication, server-side persistence write, or 5202 change/restart was performed.

## Review and completion

The remote PR remains at head `0e9cde0a2eb39d4fb1ad0cadf3a2a9660dcbf6ba` while this repair is prepared. Update the same PR with the exact cumulative base/head and checks, then send the head to PRIME for independent review. Do not merge without PRIME’s approval.
