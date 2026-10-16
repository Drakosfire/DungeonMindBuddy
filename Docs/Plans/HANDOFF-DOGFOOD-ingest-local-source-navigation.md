# DOGFOOD: simplify Ingest local source navigation

**Status:** ACTIVE — directly authorized follow-up to operator feedback on 2026-10-16.
**Base:** fetched `origin/main@64e659248c9d40681b33df2c29a9a2573dfd6a8f` after #1243 merged.
**Branch:** `codex/ingest-local-nav-source-flow`.
**Checkout:** `/home/drakosfire/.codex/worktrees/ingest-manual-source-load/DungeonMindBuddy`.
**Topology:** serial successor to merged #1191. Parallel-independent from open #1235 (`codex/ingest-source-observation-review`, head `46ecdd5019f7fc70519b0e7b50b1a1ebe6955994`, based on `b2c76cb6c83b3e4d9835376dd92956ab5f2b6f13`); #1235 changes extraction/promote and Graph Review files, with no overlap in this lease. Open #1244 changes graph packaging and its handoff, also with no overlap. The #1243 main merge changed no leased UI files.
**Runtime:** UI-only. Do not change 5202, 5204, APIs, graph/corpus data, or extraction state.

## Objective

Make the Ingest local navigation the single, calm home for recap identity,
source choice, and explicit workflow actions. Keep the recap editor as the main
work surface. Remove repeated controls and help text so the path reads once:
choose or start a source, prepare it, extract, then review.

This is a UI/source-selection slice. It does not improve extraction quality,
source admission, graph enrichment, rerun semantics, or durable ingestion
architecture.

## Write lease

- `Docs/Plans/HANDOFF-DOGFOOD-ingest-local-source-navigation.md`
- `Docs/Plans/HANDOFF-DOGFOOD-ingest-empty-welcome.md` (settle merged #1191)
- `Docs/Plans/HANDOFF-DOGFOOD-recap-reader-navigation.md` (settle merged #883)
- `Docs/Plans/HANDOFF-DOGFOOD-recap-review-action.md` (settle merged #879)
- `Docs/Plans/HANDOFF-DOGFOOD-recap-canvas.md` (settle merged #881)
- `Docs/Plans/HANDOFF-DOGFOOD-recap-candidate-completion.md` (settle merged #878)
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`
- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.css`

The merged predecessor handoffs are updated only to close their completed
implementation leases; their historical evidence and remaining product gates
stay intact. No API, schema, pipeline, shared navigation, graph review, or
provider files are leased.

## Invariants and failure cases

- The toolbar owns campaign, session/title, source selection, and one
  state-appropriate Prepare → Extract → Review path.
- A single **New recap** action returns to a raw draft. Do not also expose
  equivalent Paste recap or Unload controls, or a Processed mode toggle that
  merely repeats the selected-source state.
- Prior recap selection and loading remain explicit. Loading from a blank
  `/ingest?world=…` entry is a manual action, not route restoration; it must not
  fail because the blank URL lacks campaign/session query parameters. Explicit
  malformed recap routes must continue to fail visibly.
- A failed source read must show a failure, not a success toast with an empty
  preview.
- The recap editor remains the main canvas. Remove helper copy that repeats the
  source paths already shown in the toolbar. Keep one concise live status and
  one instance of each control (including Replace graph).
- Changes to the toolbar do not prepare, extract, save, admit, or publish data.
- Desktop and narrow layouts keep session identity and the source/actions
  usable without creating a narrow editor column.

## Verification

- Mounted `IngestionModule` suite: 58/58 passed. Coverage includes the single
  source/extraction controls, New recap reset, blank-route load, visible
  source-read failure, invalid explicit-route rejection, and one Replace graph
  checkbox.
- UI typecheck and production build passed. Build retains the existing Vite
  large-chunk warning.
- `git diff --check` passed.
- Rendered the production bundle in an isolated preview at 1280px and 390px.
  The local navigation stayed usable at both sizes; at 390px, document width
  matched viewport width (390px). No Prepare, Extract, Review, or data write was
  triggered. 5202 and 5204 were untouched.
- The successful and failing source-load paths were exercised with mocked API
  responses. This is not live ingestion acceptance and does not prove source
  admission or extraction correctness.

## Current-main rebase and acceptance — 2026-10-16

Rebased the existing PR onto fetched `origin/main@64e659248c9d40681b33df2c29a9a2573dfd6a8f`.
The cumulative diff remains limited to the nine leased paths. The focused
IngestionModule and MemoryIngestPage suites pass 71 tests; UI typecheck and
production build pass (with the existing Vite large-chunk warning); and
`git diff --check` passes.

The rebased production preview was rendered at desktop and 390px. At desktop,
campaign/session/title and source/workflow actions sit in one local toolbar
above the blank welcome. At 390px, those fields stack without horizontal
overflow and the welcome remains readable. No prepare, extract, review, save,
or ingestion-data action was performed. 5202 and 5204 were not changed; 5204
still serves the pre-nav implementation until this PR is reviewed and deployed.

## Implementation notes

- Removed the visible Paste recap / Processed toggles, Unload button, group
  headings, repeated source instructions, repeated graph-replacement prompt,
  and duplicate advanced Replace graph checkbox. New recap remains the sole
  reset action.
- The live status now carries the source/session/title next action; the blank
  welcome no longer repeats the toolbar's draft state.
- Manual prior-recap load now writes a valid recap route after source content
  is read, bypasses route-restoration validation for the manual selection, and
  displays failures instead of a success state when the source is missing.

## Completion

Commit and push the bounded implementation and open a PR. Merge remains a
separate authorization.
