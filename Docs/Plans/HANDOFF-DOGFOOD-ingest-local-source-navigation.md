# DOGFOOD: simplify Ingest local source navigation

**Status:** ACTIVE — directly authorized follow-up to operator feedback on 2026-10-16.
**Base:** fetched `origin/main@b5a0f290acd42d6115307b8ff0c877f18c149259` after #1236 merged.
**Branch:** `codex/ingest-local-nav-source-flow`.
**Checkout:** `/home/drakosfire/.codex/worktrees/ingest-manual-source-load/DungeonMindBuddy`.
**Topology:** serial successor to merged #1191. Parallel-independent from open #1235 (`codex/ingest-source-observation-review`, head `f896a4a17f52b636e41ab42685a7745c374a2af3`, based on `b2c76cb6c83b3e4d9835376dd92956ab5f2b6f13`); #1235 changes API extraction/promote and Graph Review files, with no overlap in this lease. The #1236 main merge changed no leased UI files.
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

- Add/adjust mounted tests for the simplified source controls, New recap reset,
  successful prior recap load from the blank route, visible source-read failure,
  and preservation of invalid explicit-route validation.
- Run the focused IngestionModule suite, UI typecheck, production build, and
  `git diff --check`.
- Inspect the cumulative `origin/main`→HEAD diff. Render the changed UI at
  desktop and narrow widths without triggering Prepare, Extract, Review, or any
  data write. Do not claim end-to-end ingestion acceptance from presentation
  evidence.

## Completion

Commit and push the bounded implementation and open a PR. Merge remains a
separate authorization.
