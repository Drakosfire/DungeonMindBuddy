# Surface plan controls

## Authority and lane

Delivered serial presentation slice, designed and owned by PRIME on explicit operator
feedback: compact readable work plans, consistent icons, developer metadata hidden
behind an object hamburger, selected-passage actions in Surface navigation.
Base 340cad9877e7af690dfd4d34f5b6a93a65021202, branch codex/surface-plan-controls,
existing buddy-context-loop checkout. No concurrent open PR owns these paths; #1764
remains parked. Existing8000/5202 delivery only after exact cumulative independent
Bugbot review and protected adoption. No APP/native schema, payload, executor or
Graph input contract changes. One implementation PR.

## Invariant and failure cases

Author controls reveal outcome and step text before machinery. Pending/deferred
steps remain editable/selectable; a dispatched immutable step displays status,
not a disabled inclusion checkbox. Completed replies collapse by default with an
explicit disclosure to inspect them; prepared suggestions stay distinguishable
from saved/completed work and keep their review action. No clipping multiline text.
Raw placement receipts remain available through a shared hamburger + Developer
toggle, off by default. Ordinary recovery alerts, Check Save, and retained copies
stay available without enabling Developer. No destructive action added.
Selection actions contribute to the existing Surface navigation host, never a
body-level floating portal. Preserve editor selection on pointer invocation,
revalidate capture and retire contribution on editor unmount/selection clearing.
No fallback floating toolbar when no host exists. Keyboard labels remain explicit.
Reuse the shared plus/floppy icon buttons. Add/Save never implicitly dispatch.

## Expected write lease

- This handoff; Docs/Plans/HANDOFF-AGENT-intentional-build-response.md predecessor sync.
- apps/live-control-ui/src/surface/SurfaceObjectMenu.tsx and .test.tsx and .css
- apps/live-control-ui/src/surface/workPlans/{SurfaceWorkPlan,StagedWorkPlan}.tsx
- apps/live-control-ui/src/surface/workPlans/workPlans.css
- apps/live-control-ui/src/planSurface/components/DurableWorkPlan{,.test}.tsx
- apps/live-control-ui/src/surfaceInteraction/SurfaceSelectionActions{,.test}.tsx
- apps/live-control-ui/src/surfaceInteraction/SurfaceSelectionActions.css
- apps/live-control-ui/src/surfaceInteraction/contextHost/surfaceNavbar.css

## Verification

Independent critique before implementation; focused boundary tests for metadata
visibility, immutable status/collapse, pending edits and navbar contribution cleanup;
actual UI TypeScript project build and Vite build; exact cumulative Bugbot review.
Ordinary controls on5202 after protected UI delivery: narrow/wide plan scan,
completed expansion, editable pending rows, menu Developer receipt inspection,
selection toolbar in navigation with no floating duplicate. Preserve current author
blank step and composer note; do not save or dispatch them as verification.

## Explicit successor: Graph context

Page reference chips exist. Investigate whether Build conversation accepts a chosen
Graph identity and obtains an admitted read, rather than merely receiving its name.
A durable request attachment/read contract is separate scope, not a decorative slash
command in this presentation slice. Likewise the observed Discuss reply drafting
content for a deferred insertion is retained as a separate scope-control defect.

## Rendered spacing correction — delivered successor

PR1782 merged4e015a4300650ad30860aa600f8d9d9c411b9804 after independent
approval at148936bc3b53e7256dda0fc1d944359fb24e124c. Protected UI-only adoption
retained3276 APP rows, native rows,27 frozen components and89 product files;
API340cad98 remained untouched. Ordinary page reload retained the saved outcome,
a deferred editable row, and the older blank unsaved step. Completed disclosure
and opt-in menu appeared, but the rendered page exposed inherited header display:grid
and grid auto-placement leaving checkbox below text. PRIME authorizes a bounded
serial correction in codex/surface-plan-spacing from4e015a43. Exclusive write set:
this handoff, SurfaceWorkPlan.tsx, StagedWorkPlan.tsx, workPlans.css. Same presentation
contract, no new capability. One successor PR; independent exact-head review and
protected UI-only delivery, then actual narrow/wide rendered proof. No state writes
or model calls needed to prove this correction. Graph input remains next scope.

The same rendered check found object-menu clicks can leave a non-text editor
selection. The navigation contribution must apply the existing capture eligibility
(single paragraph/heading containing only text), not expose text actions for object
selection. PRIME extends this correction lease to SurfaceSelectionActions.tsx and
its test before editing; no change to capture/admission or action execution.


## Settlement

Both presentation slices are merged and ordinarily verified at UI62eb05d04. This
write lease is released; it grants no concurrent implementation authority. Current
facts and proof limits travel in the consuming HANDOFF-AGENT-authored-node-context.md.
