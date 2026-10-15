# DOGFOOD Play blank welcome

Status: ACTIVE

Branch: `codex/play-empty-welcome` rebased onto `origin/main@3a890b9e`

Checkout: `/tmp/dmb-play-empty-welcome-reanchor`

Topology: parallel-independent from Build PR #1183 and Plan PR #1188. This slice owns Play's first-use chooser presentation only.

## Mission

Make Play's no-run / no-Runbook state feel like a deliberate beginning. Explain how to start from a saved Runbook or create a blank one, remove duplicate empty-state copy, and retain the existing exact-run creation and selection authority.

## Write lease

- `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`
- `apps/live-control-ui/src/playSurface/StartRunPanel.tsx`
- `apps/live-control-ui/src/playSurface/playSurface.css`
- `apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx`
- `apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx`
- This handoff

No changes to Run identity, Run creation semantics, API contracts, server, database, Build, Plan, Ingest, shared app shell, or 5876. Keep 5202 unchanged; rendered checks use an isolated current-main preview.

## Invariants and acceptance

- A verified empty Run list is visually distinct from loading, unavailable, recovery-pending, and exact-Run failure states.
- A first-time user sees a clear path to select a saved Runbook or create a blank Runbook; existing creation and exact-revision gates remain unchanged.
- Empty Runs and empty Runbooks are explained once, without repeated status copy.
- The experience is responsive, keyboard accessible, and visually belongs to the Play surface.
- Verify focused Play tests, UI TypeScript, production build, `git diff --check`, and the exact cumulative diff.
- Keep 5876 and 5202 untouched. Do not claim visual acceptance without inspecting a current-main preview that includes this branch.

## Current verification — 2026-10-15

The Play focused page and start-panel suites pass 48 tests, and the app
TypeScript check passes. Rendered acceptance remains pending in the integrated
current-main preview; the Build-only 5204 preview does not include this branch,
and Elderwyld already has saved Runs, so a verified empty Run state still needs
an isolated empty-world fixture or a safe UI-only fixture.


## Integrated preview acceptance — 2026-10-15

The integrated local preview on 5205 includes `main@3a890b9e` and current heads of PRs #1183, #1188, #1190, and #1191. Shared navigation from Build opened the Play surface. Elderwyld already has saved Runs, so the no-run welcome could not be exercised against live World state without creating/changing data; this remains a visual acceptance gap. The first-run state is covered by the focused Play page and Start Run panel tests (48 passed), and TypeScript plus the combined production build passed. No Runbook or Run was created; 5202 and 5876 were not modified.
