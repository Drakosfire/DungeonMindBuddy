# DOGFOOD Play blank welcome

Status: ACTIVE

Branch: `codex/play-empty-welcome` from `origin/main@31c5044872076a9bdfd17fced71caf11510121c1`

Checkout: `/home/drakosfire/.codex/worktrees/play-empty-welcome/DungeonMindBuddy`

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

No changes to Run identity, Run creation semantics, API contracts, server, database, Build, Plan, Ingest, shared app shell, or 5876. 5202 is the assigned dogfood port; no 5202 server is currently listening. Runtime changes must remain on that port.

## Invariants and acceptance

- A verified empty Run list is visually distinct from loading, unavailable, recovery-pending, and exact-Run failure states.
- A first-time user sees a clear path to select a saved Runbook or create a blank Runbook; existing creation and exact-revision gates remain unchanged.
- Empty Runs and empty Runbooks are explained once, without repeated status copy.
- The experience is responsive, keyboard accessible, and visually belongs to the Play surface.
- Verify focused Play tests, UI TypeScript, production build, `git diff --check`, and the exact cumulative diff.
- Keep 5876 untouched. Use 5202 for rendered verification when the current branch preview can be run safely; do not claim visual acceptance without inspecting that render.
