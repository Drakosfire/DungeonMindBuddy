# DOGFOOD: simplify Ingest evidence presentation

**Status:** ACTIVE under the user-authorized Ingest-first UX iteration (2026-10-16).
**Base:** GitHub reports current `main@61991c78ab01ed8e4f694ec4b36c2863ff5fb198`. Shell fetch is unavailable because `github.com` DNS failed. The checkout starts at `c3198d4c8ba7342ffdcef4aec74b56c7a7d1da15`, the UI head merged by #1256; local `origin/main@85b3949c5cb4fd6419767c7a6037e3002a20750e` contains that merge, and GitHub confirms current main descends from it. Later #1257 and #1258 changes are server/agent files outside this UI write set.
**Branch:** `codex/ingest-evidence-surface-cleanup`.
**Checkout:** `/tmp/dmb-ingest-local-nav-refresh`.
**Topology:** serial successor to merged #1256, one follow-on PR. Open #1235 owns Graph Review/source-observation review files; open #1244 owns packaging/reference recovery; neither overlaps this UI lease. #1251 and #1258 are merged prerequisites and do not own these paths.
**Runtime/data:** UI-only. Rendered 5202/5204 were observed read-only. No source, candidate, Corpus, graph, persistence, provider, or serving action is permitted in this slice.

## Objective

Keep the sticky Ingest local navigation as the home for recap identity, source
loading, workflow actions, and one concise current status. Reduce the clutter
below it by showing each proof fact once. File existence and corpus impact
currently repeat the same recap paths and Found/Missing states; readiness lanes
repeat the current next action already shown in the nav.

## Invariants

- Do not move or duplicate campaign/session/title, source loading, Prepare,
  Extract, Review, or concise current status out of the local navigation.
- Keep the recap editor and saved-source projection on the main surface.
- Preserve every on-disk existence result, exact path, record count, source
  preview, graph count/status, warning/error, authority transition, canonical
  preview/diff, and spelling audit. Details may be collapsed or expanded at the
  relevant file row, but no proof may be silently discarded.
- Do not expose duplicate summary states: the navbar owns the current status and
  next action; one per-file row owns that file's existence and preview evidence.
- Do not change ingestion gates, API contracts, or write behavior.

## Exclusive write set

- This handoff
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`
- `apps/live-control-ui/src/styles.css` (only the existing Ingest proof-row
  selectors)

## Acceptance

- Remove the redundant readiness-lane list that repeats the nav's current
  next-action/status summary.
- Combine file proof and corpus-impact presentation into one list. Each row
  shows Found/Missing once, retains its exact path and record count, and offers
  any available size/time/preview as a per-file expansion.
- Keep run diagnostics inspectable without duplicating visible nav text.
- Add focused regression tests for one file-status presentation and expandable
  per-file evidence. Run the focused Ingest suites, UI typecheck/build where
  dependencies permit, and cumulative `git diff --check`.
- No Prepare, Extract, Review mutation, Graph admission, persistence, or
  publication action is used for verification.

## Stop conditions

Stop if proof rows require API changes, new persistence state, or a shared
cross-surface component. Return that exact contract need for a separate bounded
slice rather than broadening this UI lease.

## Verification

- `IngestionModule.test.tsx`: 63 passed.
- `npm run typecheck`: passed.
- `npm run build`: passed; Vite reports the existing large-chunk warning.
- `git diff --check`: passed.
- Browser acceptance of this follow-on is not claimed. 5202 remains on main and
  was read-only; 5204 was not changed. No ingestion or graph action was run.
