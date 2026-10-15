# DOGFOOD: Ingest first-use welcome

Status: ACTIVE
Topology: serial; one implementation PR based on `origin/main`
Branch: `codex/ingest-empty-welcome`
Checkout: `/home/drakosfire/.codex/worktrees/ingest-empty-welcome/DungeonMindBuddy`

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
- Elderwyld's established recap entry and exact-run review flows remain intact.
- No state change may admit, import, publish, or associate source evidence.

## Verification

Run focused `MemoryIngestPage` tests, UI typecheck, production build, and
`git diff --check`. Inspect the cumulative `origin/main`→HEAD diff. Rendered
acceptance is required before calling the UX finished; if 5202 or its API/auth
dependencies are unavailable, report that limitation without claiming visual
acceptance.

## Completion

Commit and push the scoped implementation and open a draft PR. Do not merge
without explicit merge authority.
