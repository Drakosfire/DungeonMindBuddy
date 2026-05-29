---
document_id: dmb-handoff-pr88-l5j-roll-table-patch-ui-preview
title: PR 88 Handoff — L5J Roll-table Patch UI Preview
status: completed
version: 0.1
created_at: "2026-05-29T18:15:00Z"
completed_at: "2026-05-29T23:45:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
  - path: Docs/Plans/HANDOFF-pr87-l5i-scoped-roll-table-patch-command.md
    role: prior_backend_patch_slice
---

# PR 88 Handoff — L5J Roll-table Patch UI Preview

## Mission

Add a constrained, preview-first roll-table patch UI in the Inspector Pane for `patch_artifact` capability on `roll_table` targets only, using the existing `POST /api/live/commands` command bus path.

## Scope Delivered

- Added UI write-result metadata support:
  - `apps/live-control-ui/src/api/types.ts`
- Added dedicated preview-first roll-table patch action:
  - `apps/live-control-ui/src/surface/PatchArtifactAction.tsx`
- Added defensive metadata extraction/rendering for patch previews:
  - uses `metadata.patch` only when shape is present
  - renders diff/tokens/replacement metadata when available
- Enforced preview-first confirm gating in UI:
  - confirm disabled until successful server dry-run (`status=noop` + `metadata.patch.dry_run=true`)
  - editing fields invalidates preview
  - confirm submits previewed values only
  - stale token preview detection blocks confirm
  - accepted confirm clears stale preview/form values
- Implemented confirm idempotency key behavior:
  - generated per previewed patch
  - reused for retry on same preview after network error
  - regenerated after new preview post-edit
- Extended capability gating seam (no generic runner):
  - `patch_artifact` action renders only when all are true:
    - target type `roll_table`
    - capability enabled
    - `command_type=patch_artifact`
    - `lane=prep_note`
  - unsupported enabled capabilities remain inert
  - `queue_canon_patch` remains inert
  - `append_observation` preserved
  - files:
    - `apps/live-control-ui/src/surface/CapabilityList.tsx`
    - `apps/live-control-ui/src/surface/InspectorPane.tsx`
- Added/updated tests for preview/confirm flow + gating + non-regression:
  - `apps/live-control-ui/src/surface/PatchArtifactAction.test.tsx`
  - `apps/live-control-ui/src/surface/CapabilityList.test.tsx`
  - `apps/live-control-ui/src/surface/InspectorPane.test.tsx`
  - `apps/live-control-ui/src/api/liveApi.test.ts`
  - `apps/live-control-ui/src/test/fixtures.ts`
- Updated styles:
  - `apps/live-control-ui/src/styles.css`

## Out of Scope Preserved

- No backend command expansion
- No new patch endpoint
- No generic capability executor
- No patch UI for non-roll-table targets
- No `queue_canon_patch` UI
- No markdown editor / rich editor
- No browser-side file access
- No client-supplied source paths

## Verification

```bash
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
```
