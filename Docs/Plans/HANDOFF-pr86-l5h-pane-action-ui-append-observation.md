---
document_id: dmb-handoff-pr86-l5h-pane-action-ui-append-observation
title: PR 86 Handoff — L5H Pane Action UI for append_observation
status: completed
version: 0.1
created_at: "2026-05-29T15:30:00Z"
completed_at: "2026-05-29T16:10:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
  - path: Docs/Plans/HANDOFF-pr85-l5g-command-bus-first-write.md
    role: prior_backend_command_slice
---

# PR 86 Handoff — L5H Pane Action UI for append_observation

## Mission

Wire Inspector Pane UI to submit the already-supported `append_observation` command through:

`POST /api/live/commands`

with explicit action gating so only allowlisted enabled capability (`append_observation` on `observed_play`) is actionable.

## Scope Delivered

- Added full UI-side command/write-result types in:
  - `apps/live-control-ui/src/api/types.ts`
- Added command submit helper:
  - `apps/live-control-ui/src/api/liveApi.ts` (`postCommand`)
- Added scoped action component:
  - `apps/live-control-ui/src/surface/AppendObservationAction.tsx`
  - compact form, validation, submit/cancel, pending state
  - idempotency key generation per submit
  - accepted/rejected/noop/conflict/error result rendering
- Updated capability rendering:
  - `apps/live-control-ui/src/surface/CapabilityList.tsx`
  - disabled capabilities remain informational
  - only allowlisted `append_observation` capability renders action UI
  - accidentally enabled unsupported capabilities remain inert
- Updated inspector integration:
  - `apps/live-control-ui/src/surface/InspectorPane.tsx`
  - submits command via `postCommand`
  - refreshes selected target artifact/capabilities after accepted/noop
  - calls App-level `onCommandAccepted` callback for global refresh
- Updated app integration:
  - `apps/live-control-ui/src/App.tsx`
  - passes `handleCommandAccepted` callback that calls `refreshAll()`
- Added/updated tests:
  - `apps/live-control-ui/src/surface/AppendObservationAction.test.tsx`
  - `apps/live-control-ui/src/surface/CapabilityList.test.tsx`
  - `apps/live-control-ui/src/surface/InspectorPane.test.tsx`
  - `apps/live-control-ui/src/api/liveApi.test.ts`
  - `apps/live-control-ui/src/App.commandAccepted.test.tsx`
  - supporting fixture updates in `apps/live-control-ui/src/test/fixtures.ts`

## Out of Scope (Preserved)

- No generic capability runner.
- No `patch_artifact` action UI.
- No `queue_canon_patch` action UI.
- No markdown/artifact editing controls.
- No roll-table patch flow.
- No backend command expansion.
- No retrieval refresh execution.
- No browser-side file access.

## Verification

```bash
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
```
