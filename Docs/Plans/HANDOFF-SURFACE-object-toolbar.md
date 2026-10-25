# Bounded Surface plan toolbar and row removal

Operator priority: deliver the requested visible toolbar/drag contrast/pending-row
minus before resuming authored Graph-reference UI. PRIME owns design/implementation.
Use the existing Buddy checkout serially. First checkpoint/push graph work on
codex/authored-node-context (#1785), then switch a clean checkout to
codex/surface-object-toolbar from current origin/main. No runtime/dependency/data
changes before independent review and protected UI adoption. No parallel checkout.
Graph backend remains retained in draft; its UI lease is suspended while this bounded
slice owns the overlapping UI paths. This is not a pause of the overall active goal.

Exact write set:
- Docs/Plans/HANDOFF-SURFACE-object-toolbar.md (this contract copied into branch)
- apps/live-control-ui/src/surface/workPlans/SurfaceWorkPlan.tsx
- apps/live-control-ui/src/surface/workPlans/WorkPlanNode.tsx
- apps/live-control-ui/src/surface/workPlans/workPlans.css
- apps/live-control-ui/src/planSurface/components/DurableWorkPlan.tsx
- apps/live-control-ui/src/surfaceInteraction/contextHost/SurfaceNavbarIconButton.tsx
- apps/live-control-ui/src/surface/workPlans/SurfaceWorkPlan.test.tsx
- apps/live-control-ui/src/planSurface/components/DurableWorkPlan.test.tsx

One implementation PR. The toolbar is attached/sticky within the object, with move
handle, editable title, plus, existing green plan Save and hamburger together. Remove
duplicate title/bottom controls. Use shared SVG move/minus icons with explicit solid
contrast. Move remains the existing drag/edge-scroll/Alt-arrow handler, not a new DnD
system. Compose callbacks through the existing durable plan component; no copied state,
second executor, DOM reparenting or imperative command store. Retain current plan Save
and page-title/source Save ownership, including original disabled/CAS/recovery rules.

A minus removes only unexecuted steps from the locally retained review. Persist only
on explicit existing Save; continue requires saved state. Dispatched steps cannot be
removed: their binding/history stays intact. Keep at least one step, matching existing
APP review admission. No schema changes or API methods. The whole-object Trash/restore,
Empty Trash and conversation projection toggle are separate unimplemented lifecycle
requirements, not silently implemented by deleting the editor node.

Prove title/header controls appear once; minus retains local change and saves exact
remaining step IDs without executing; dispatched rows remain immutable; stale/archived/
busy rules persist. Existing actual editor movement/round-trip tests, relevant UI tests,
real tsc-b/Vite, exact cumulative independent review, PRIME merge and protected UI-only
adoption plus ordinary retained-state page checks are required. Do not overwrite the
older blank unsaved step or newer composer on 5202. This bounded UI slice does not
claim Graph context, full lifecycle, or complete creative-loop acceptance.
