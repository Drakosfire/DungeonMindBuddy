# DOGFOOD: Ingest first-use welcome

Status: ACTIVE
Topology: serial; one implementation PR based on `origin/main`
Branch: `codex/ingest-empty-welcome`
Checkout: `/tmp/dmb-ingest-empty-welcome`

Base: fetched `origin/main@65ab104be533854e72e5b5277e07744bcfe2e1f9`.

## Objective

Make Ingest feel like a welcoming first-use surface when no World is selected or
when a managed World has no exact extraction run selected. Explain what the
surface is for and provide an actionable next step. Preserve the current
Elderwyld recap entry, exact-run routing, source ownership, graph-review gates,
and all ingestion/review behavior.

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
  show a guided blank welcome and do not attempt to restore a saved-recap route
  unless `view=recap` was explicitly requested.
- An explicit recap deep-link with valid campaign/session/run identity still
  restores the exact saved recap; malformed explicit routes keep a visible
  route error.
- The blank welcome only focuses the raw recap field. It must not prepare,
  ingest, save, or otherwise mutate data.
- Elderwyld's established recap entry and exact-run review flows remain intact.
- No state change may admit, import, publish, or associate source evidence.

## Verification

Run focused `MemoryIngestPage` tests, UI typecheck, production build, and
`git diff --check`. Inspect the cumulative `origin/main`→HEAD diff. Rendered
acceptance is required before calling the UX finished. Keep 5202 unchanged and
report API/auth limitations without claiming live ingestion acceptance.

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
