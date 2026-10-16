# DOGFOOD: simplify Ingest local source navigation

**Status:** ACTIVE — directly authorized follow-up to operator feedback on 2026-10-16.
**Base:** fetched `origin/main@fc1daff4b7fc8f6ba7d35445dd22e9fca15f6d49` after #1250 merged.
**Branch:** `codex/ingest-local-nav-source-flow`.
**Checkout:** `/tmp/dmb-ingest-local-nav-refresh` (isolated refresh lane; the original clean checkout is preserved).
**Topology:** serial successor to merged #1191. Parallel-independent from open #1235 (`codex/ingest-source-observation-review`, head `46ecdd5019f7fc70519b0e7b50b1a1ebe6955994`, based on `b2c76cb6c83b3e4d9835376dd92956ab5f2b6f13`); #1235 changes extraction/promote and Graph Review files, with no overlap in this lease. Open #1244 (`codex/ingest-candidate-evidence-ref-recovery`, head `d081196b0785821e124248b7bb7761dd234f3d28`) changes graph packaging and its handoff, also with no overlap. Open #1251 (`codex/ingest-evidence-readiness`, head `8e1ebf64b1ed677808b6b435f8d2d23e32f576ac`) changes readiness modules and the server adapter, with no overlap in this lease. The #1250 main merge changed no leased UI files.
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

Rebased the existing PR onto fetched `origin/main@98b28b08470ae9320e638dda8d8810b492b86ca0` after #1247 and #1248 merged. Those main changes do not touch the three leased UI source paths. The cumulative diff remains limited to the nine leased paths. After rebasing, the focused IngestionModule and MemoryIngestPage suites pass 72 tests. Both UI TypeScript projects pass when their build-info files are redirected to `/tmp`; the default typecheck cannot write its configured cache under the read-only shared `node_modules`. The production bundle builds to `/tmp/dmb-ingest-preview` with the existing Vite large-chunk warning. `git diff --check` passes.

Rendered the rebuilt production bundle at desktop and a 390px viewport. At both
widths, campaign/session/title and source/workflow actions stay in the local
toolbar; the 390px viewport reports document scroll width 375px, with no
horizontal overflow. The render exposed a restored-draft state where prepared
Session 29 work appeared alongside an empty raw-text
editor. The surface now identifies that prepared source and directs the user
to Review or an explicit Load, rather than presenting the empty field as the
active source. The static preview had no live artifact registry, so this
verifies presentation only, not reading the live saved source. This render
preceded the latest-main rebase; the rebase did not change leased UI source
files, and the production bundle was rebuilt afterward. No prepare, extract,
review, save, or ingestion-data action was performed. 5202 and 5204 were not
changed; 5204 still serves the pre-nav implementation until this PR is
reviewed and deployed. Bugbot reviewed the recovered-source change before the
latest-main rebase and found no confirmed bugs.

Re-anchored again on `origin/main@fc1daff4b7fc8f6ba7d35445dd22e9fca15f6d49`
after #1250 merged. The merge changes agent-response diagnostics and does not
touch any of this lease's nine paths. The cumulative UI diff is unchanged from
the acceptance above. A fresh focused-test attempt in the isolated refresh
checkout could not start because Vitest is not installed there. `npm ci` stalled
and was interrupted; `npm ci --offline --ignore-scripts` then failed with
`ENOTCACHED` because the React package was not in the local npm cache. No
tracked dependency manifests or UI source files changed. The prior 72-test,
typecheck, build, and desktop/390px rendered results remain the only executed
verification for the unchanged UI diff. Open #1235, #1244, and #1251 were
rechecked; their changed paths do not overlap this UI lease.

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
- When a restored local draft has a prepared recap but no loaded source text,
  the editor shows a prepared-source notice instead of an empty raw-input
  field. A regression test covers this state; a failed explicit source read
  still returns to the raw editor for recovery.

## Completion

The bounded implementation is committed and pushed in PR #1237. It remains
open for review; merge and deployment to 5202 remain separate authorization.
