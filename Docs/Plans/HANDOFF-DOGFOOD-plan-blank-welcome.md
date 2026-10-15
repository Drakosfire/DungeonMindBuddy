# DOGFOOD Plan Blank Welcome

Status: ACTIVE

Branch: `codex/plan-empty-welcome` from `origin/main@31c50448`

Checkout: `/home/drakosfire/.codex/worktrees/plan-empty-welcome/DungeonMindBuddy`

Topology: parallel-independent from Build PRs #1183 and #1187; this lane owns only Plan authoring paths.

## Mission

Make a newly opened Plan feel like an inviting, intentional first page. A new local Plan draft begins truly blank and shows a temporary, Plan-specific welcome with a clear way to start writing, optional starting prompts, and the existing session-prep outline as an explicit choice. Plan documents open editable by default; the lock toggle is removed from the Plan canvas and Save remains the explicit write boundary. Preserve local draft recovery, promotion, save, and existing saved-document behavior. The welcome is presentation only and is never serialized.

## Write lease

- `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx`
- `apps/live-control-ui/src/planSurface/usePlanBlankAuthoring.ts`
- `apps/live-control-ui/src/planSurface/edit/editCapability.tsx`
- `apps/live-control-ui/src/planSurface/edit/editCapability.test.tsx`
- `apps/live-control-ui/src/planSurface/planSurface.css`
- Plan-owned tests under `apps/live-control-ui/src/planSurface/`
- This handoff

No shared shell, Build, Play, Ingest, server, database, or 5202 runtime changes. The lane may read their patterns but must not edit their files.

## Invariants and acceptance

- A fresh New Plan is actually empty until the user types or picks a starter; the previous session-prep content remains available by explicit action.
- Typing or choosing a starter dismisses the welcome without losing text, altering saved plans, or triggering an automatic save.
- Reload/recovery continues to preserve the local draft. Saving still uses the existing exact target-session and promotion/receipt gates.
- The welcome is keyboard accessible, responsive, and visually belongs inside the existing paper Plan canvas.
- Verify the focused Plan tests, TypeScript, production build, `git diff --check`, and the exact cumulative diff.
- No 5202 changes. Live rendered acceptance is separate from structural tests and may remain blocked by the unavailable 5203 preview.
