# DOGFOOD Plan Blank Welcome

Status: ACTIVE

Branch: `codex/plan-empty-welcome` rebased onto `origin/main@3a890b9e`

Checkout: `/tmp/dmb-plan-empty-welcome`

Topology: parallel-independent from Build PRs #1183 and #1187; this lane owns only Plan authoring paths.

## Mission

Make a newly opened Plan feel like an inviting, intentional first page. A new local Plan draft begins truly blank and shows a temporary, Plan-specific welcome with a clear way to start writing, optional starting prompts, and the existing session-prep outline as an explicit choice. Plan documents open editable by default; the lock toggle is removed from the Plan canvas and Save remains the explicit write boundary. Preserve local draft recovery, promotion, save, and existing saved-document behavior. The welcome is presentation only and is never serialized.

## Write lease

- `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx`
- `apps/live-control-ui/src/planSurface/usePlanBlankAuthoring.ts`
- `apps/live-control-ui/src/planSurface/edit/editCapability.tsx`
- `apps/live-control-ui/src/planSurface/edit/editCapability.test.tsx`
- `apps/live-control-ui/src/planSurface/planSurface.css`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- Plan-owned tests under `apps/live-control-ui/src/planSurface/`
- This handoff

No shared shell, Build, Play, Ingest, server, database, or 5202 runtime changes. The lane may read their patterns but must not edit their files.

## Invariants and acceptance

- A fresh New Plan is actually empty until the user types or picks a starter; the previous session-prep content remains available by explicit action.
- Typing or choosing a starter dismisses the welcome without losing text, altering saved plans, or triggering an automatic save.
- Reload/recovery continues to preserve the local draft. Saving still uses the existing exact target-session and promotion/receipt gates.
- The welcome is keyboard accessible, responsive, and visually belongs inside the existing paper Plan canvas.
- The live World Plan route (`/plan?world=<world>`) uses the same temporary welcome when its editor is empty; choosing a starter is the only action that writes draft content.
- Verify the focused Plan tests, TypeScript, production build, `git diff --check`, and the exact cumulative diff.
- No 5202 changes. Rendered acceptance must use a current-main preview that includes this branch; do not use stale 5203.

## Live World Plan route lease amendment

Rendered DOGFOOD evidence showed that the current `/plan?world=elderwyld` route
renders `WorldOwnedPlanPage` and bypasses `PlanBlankPageWelcome`, leaving only
the “Unsaved Plan Draft” kicker over a blank sheet. The existing welcome in
`PlanSurfaceCanvas` covers a different Plan path and therefore does not meet the
new-user acceptance for the route users actually open.

The lease now includes `PlanSurfacePage.tsx` and `PlanSurfacePage.test.tsx` so
the World-owned blank editor can reuse the same Plan-specific welcome and
optional starters. Keep all welcome copy outside serialized editor content;
initial render must not create, save, or modify a Plan. Saved non-empty Plans
remain unchanged. This route and the starter interaction must be verified in
the integrated preview before the blank-document work is considered complete.

## Current main re-anchor and verification — 2026-10-15

The implementation is rebased on fetched `origin/main@3a890b9e` in
`/tmp/dmb-plan-empty-welcome`. The live World route is covered by the focused
blank-route test. The focused Plan route, Plan editor-host/shell, and edit
capability suites pass; the app TypeScript check passes. The broad
`PlanSurfacePage.test.tsx` file still has 44 failures in older conversation
tests that query the obsolete accessible region name “Saved World Plan
conversation” while the current page exposes “Plan workspace”. This same
accessibility-name mismatch was reproduced on current main before this blank
welcome change; those baseline assertions are not hidden or counted as passing.

The integrated rendered acceptance is still pending. The Build-only 5204
preview does not include this branch; the previous 5203 render predates the
current main re-anchor. Do not claim the Plan welcome is visually accepted until
it is checked with this branch in the integrated preview.


## Integrated preview acceptance — 2026-10-15 (supersedes pending-render note)

The integrated local preview on 5205 includes `main@3a890b9e` and the current heads of PRs #1183, #1188, #1190, and #1191. The blank live World Plan route rendered as a warm paper welcome at desktop and 390px; the first screen offers writing prompts and the existing outline as explicit choices. The welcome is presentation-only and the editor stays empty until the user acts. No Plan was saved or modified. 5202 was not modified.

The focused live blank-route, editor-host/shell, and edit-capability suites passed 106 tests total; TypeScript and the combined production build passed. The broad `PlanSurfacePage.test.tsx` still has 44 legacy conversation assertions using an obsolete accessible region name, reproduced against current main before this change; those are not counted as passing. The earlier pending-render note is superseded. Durable save was not part of this read-only visual acceptance.
