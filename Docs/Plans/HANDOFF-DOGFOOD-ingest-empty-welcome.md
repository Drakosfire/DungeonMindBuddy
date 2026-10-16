# DOGFOOD: Ingest first-use and local toolbar

Status: ACTIVE
Topology: serial; one implementation PR based on `origin/main`
Branch: `codex/ingest-empty-welcome`
Checkout: `/tmp/dmb-ingest-empty-welcome`

Current base: `origin/main@c21feff20156fdd8c3c082cfa083895ceee5eef6` (fetched 2026-10-16).

## Objective

Make Ingest a welcoming, coherent workspace. When no World or exact extraction
run is selected, explain the next useful action. For the Elderwyld recap flow,
put Ingest-specific campaign/session/source identity and state-appropriate stage
actions in one local toolbar beneath the shared app navigation. Keep the recap
or welcome as the main projected surface, remove duplicate titles/statuses, and
preserve exact-run routing, source ownership, graph-review gates, and ingestion
behavior. The shared app navigation itself is out of scope.

## Write lease

Expected paths:

- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx`
- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.css`
- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.test.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`
- `Docs/Plans/HANDOFF-DOGFOOD-ingest-empty-welcome.md`

No API, database, ingestion pipeline, schema, source-admission, graph-review,
shared navigation, or 5202 runtime changes are in scope. The welcome may link to
Build for the same selected World, but it must not create a source or start
ingestion implicitly.

## Invariant and failure cases

- A missing World selection is a normal onboarding state, not an error alert.
- A failed or loading World selection remains visibly distinct and retains its
  current status semantics.
- A managed World with no exact extraction run gets a calm, useful landing and a
  route to Build; it does not infer or fabricate a run.
- Elderwyld's plain `/ingest?world=elderwyld` route is a normal new-recap entry:
  show a guided blank welcome, do not inherit a session number/title or on-disk
  readiness from the surrounding surface, and do not inspect an arbitrary
  session unless the operator explicitly selects it. Prior processed recaps
  remain unselected until the operator chooses one. A saved local draft still
  restores; a saved-recap URL still restores only when `view=recap` was explicit.
- An explicit recap deep-link with valid campaign/session/run identity still
  restores the exact saved recap; malformed explicit routes keep a visible
  route error.
- The blank welcome only focuses the raw recap field. It must not prepare,
  ingest, save, or otherwise mutate data.
- The blank entry does not imply a previously selected session or saved recap;
  no historical status is presented as the next action until a session is
  intentionally selected or loaded.
- The Ingest-local toolbar is the single home for Ingest-specific campaign,
  session, source, and stage controls. The page body does not repeat its title,
  campaign/session identity, or next-action status. The shared app navigation
  remains unchanged.
- Selecting a prior recap or changing toolbar fields does not prepare, run,
  admit, or publish it; those actions remain explicit and retain their existing
  gates.
- At desktop and narrow widths, the toolbar keeps controls identifiable and
  usable without squeezing the recap editor into a narrow column or hiding the
  current source/session context.
- Elderwyld's established recap entry and exact-run review flows remain intact.
- No state change may admit, import, publish, or associate source evidence.

## Verification

Run focused `MemoryIngestPage` tests, UI typecheck, production build, and
`git diff --check`. Inspect the cumulative `origin/main`→HEAD diff. Rendered
acceptance is required before calling the UX finished. Keep 5202 unchanged and
report API/auth limitations without claiming live ingestion acceptance.
The blank-route regression must prove no implicit `inspect_status` call or
prior-artifact selection, while explicit routes and locally saved drafts still
restore correctly.

## Completion

Commit and push the scoped implementation and open a draft PR. Do not merge
without explicit merge authority.

## Current route fix and verification — 2026-10-15

The current-main rebase also fixes the plain `/ingest?world=elderwyld` failure:
world-graph availability no longer forces saved-recap restoration unless the
URL explicitly selects `view=recap`. The IngestionModule and MemoryIngestPage
suites pass 69 tests, and the app TypeScript check passes. The integrated render
is pending; 5204 currently serves the Build-only branch, and neither 5202 nor
5203 should be used as evidence for this updated branch.


## Integrated preview acceptance — 2026-10-15 (supersedes pending-render note)

The integrated local preview on 5205 includes `main@3a890b9e` and current heads of PRs #1183, #1188, #1190, and #1191. The plain `/ingest?world=elderwyld` route opened a guided first-use welcome at desktop and 390px, with the raw recap field empty and no error about missing publication context. The existing campaign/session defaults may be shown, but no recap text was entered, prepared, ingested, or saved. The welcome remains visually prominent; existing operational/readiness detail is still present farther down the surface. No ingestion state was changed and 5202 was not modified.

The IngestionModule and MemoryIngestPage suites passed 69 tests; TypeScript and the combined production build passed. This verifies the entry experience, not a live ingestion run or authenticated persistence. The prior pending-render note is superseded.

## Current-main rebase and preview — 2026-10-15

Rebased the assigned PR #1191 onto current `origin/main@65ab104be533854e72e5b5277e07744bcfe2e1f9` (HEAD before final handoff sync: `109c804677b82a0dff4fc7741bb87a0a036dfa20`). The cumulative change remains within this handoff's six expected paths. The two IngestionModule test labels were updated to match the current `(DeepSeek)` UI label after the main rebase.

Verification on this head: focused IngestionModule and MemoryIngestPage suites passed 69 tests; UI typecheck and production build passed; `git diff --check origin/main...HEAD` passed. The current-head local preview visibly rendered the first-use welcome at desktop, including the three-step recap workflow, empty raw-recap field, and the statement that nothing is prepared or ingested until the user chooses those steps. Current-head narrow-width rendering could not be verified: the installed Playwright browser binary is missing and system Chrome terminated before capture. The prior 390px check is from the older pre-rebase preview and is not current-head evidence.

No recap was prepared, run, admitted, or saved. The existing `f43e48e6-c775-4960-824f-fb398fe50bb9` review candidate in 5202 was left unchanged. This PR improves first-use Ingest presentation only; it does not resolve the saved candidate's visible `team` → `tea` links, establish extraction quality, clarify rerun semantics, or prove authenticated persistence. Those are the next ingestion-mandate work, under a separately bounded handoff after this serial PR is reviewed/settled.

## Ingest-local toolbar pass — 2026-10-16

The active slice now places campaign, source session and title, source mode,
prior processed-recap selection/loading, and extraction/review actions in a
sticky Ingest-local toolbar below the shared navigation. The duplicate module
heading, workflow-progress card, and prior-recap card were removed from the
content area; the blank welcome and recap editor remain the projected surface.
Only the six leased paths changed. The shared app navigation and 5202 runtime
remain untouched.

Verification on the current local head: IngestionModule and MemoryIngestPage
suites passed 69 tests; UI typecheck and production build passed; `git diff
--check` passed. A production preview at 5208 rendered the fresh Elderwyld
route with the app navigation, local toolbar, empty session/title fields,
unselected prior recap list, disabled extraction actions, and blank recap
welcome. Narrow-width rendering was not available from the current browser
viewport controls, so CSS responsive behavior is implemented but not claimed as
visually accepted on this head.

No recap was prepared, run, admitted, or saved. This presentation change does
not claim to fix extraction quality or prove authenticated persistence.


## Current-main rebase — 2026-10-16

Rebased the existing PR #1191 onto fetched `origin/main@c21feff20156fdd8c3c082cfa083895ceee5eef6`. No commits since the prior base touched the six leased paths, and the cumulative scope remains unchanged. The focused IngestionModule and MemoryIngestPage suites pass 69 tests; `npm --prefix apps/live-control-ui run typecheck` passes; `npm --prefix apps/live-control-ui run build` passes with the existing large-chunk warning; cumulative `git diff --check` passes. This is still a presentation slice only. No recap, candidate, runtime, or persistence state was changed; extraction/linking quality, rerun semantics, and live persistence acceptance remain open Ingest-mandate work.

## Local-nav feedback follow-up — 2026-10-16

The latest UX feedback asked to consolidate Ingest controls in its local nav and
remove repeated content. That behavior is already part of this slice: the sticky
toolbar holds campaign/session/title identity, source mode and prior-recap
loading, extraction/review actions, and one live stage status. The body keeps the
welcome or recap editor as the projected surface; the old heading, progress card,
and separate prior-recap card are removed. No additional code change was needed
for this feedback.

Reverification on local HEAD `810a60a80194c08299eb6b96b4237cad147c351b`:
focused suites pass 69 tests, typecheck passes, and production build passes with
the existing large-chunk warning. Current rendered acceptance could not be
repeated: `5204` refused connections, and a static preview bind on `5208` failed
with `EPERM`. A fresh GitHub fetch also failed because this environment could
not resolve `github.com`; the remote PR head/status is therefore unverified in
this turn. No candidate, runtime, persistence, or 5202 state was changed.
