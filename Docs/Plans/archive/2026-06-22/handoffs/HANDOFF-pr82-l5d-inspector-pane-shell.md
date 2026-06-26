---
document_id: dmb-handoff-pr82-l5d-inspector-pane-shell
title: PR 82 Handoff — L5D Universal Inspector Pane Shell
status: ready_for_implementation
version: 0.1
created_at: "2026-05-28T23:30:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
  - path: Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-pr81-l5c-timeline-module.md
    role: prior_ui_projection_slice
---

# PR 82 Handoff — L5D Universal Inspector Pane Shell

## Reanchor

PR #79 established projection/command contracts.

PR #80 established the first derived projection: `GET /api/live/plan-view`.

PR #81 landed the first React projection consumer: typed `planView` loading, `TimelineModule`, inert ref chips, and the `timeline` catalog/layout module.

PR #82 is the next rung: introduce app-level inspector pane chrome and target-selection state without reading artifacts, rendering artifact bodies, exposing capabilities, or adding writes.

This is **Option B**:

```text
Timeline ref chip click
→ select target from already-loaded planView ref data
→ open shared InspectorPane shell
→ render metadata-only placeholder
```

No network request should happen when a ref is selected.

## Mission

Build the client-side backbone for universal inspection:

- shared target-selection state
- app-level `InspectorPane` shell
- Timeline ref chips that can select/open a target
- metadata-only selected-target rendering

The pane is a socket, not the powered system yet.

PR82 should make the app able to say, “this projection target is selected,” while honestly saying, “artifact reads/renderers/actions are not implemented yet.”

## Scope

Implement only the UI shell/state layer:

- Add a client-side selected-target type aligned with existing projection target vocabulary.
- Add an app-level pane state domain: closed, empty/open, selected target.
- Render `InspectorPane` as app chrome outside individual modules.
- Pass a target-selection callback through `SurfaceShell` / `ModuleRenderContext` to modules that can surface targets.
- Update `TimelineModule` so ref chips may be selectable buttons.
- On ref selection, open the pane using only the ref data already loaded in `planView`.
- Show selected target metadata: type, label, source status, role, target ID, and optional origin/module hint.
- Add empty and closed states.
- Add tests for pane state, Timeline selection, and non-regression of existing modules.
- Add minimal styling consistent with existing surface/module styles.

Recommended files:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/App.tsx
apps/live-control-ui/src/surface/SurfaceShell.tsx
apps/live-control-ui/src/surface/moduleRegistry.tsx
apps/live-control-ui/src/surface/InspectorPane.tsx
apps/live-control-ui/src/surface/InspectorPane.test.tsx
apps/live-control-ui/src/surface/targetTypes.ts
apps/live-control-ui/src/surface/TargetChip.tsx
apps/live-control-ui/src/surface/TargetChip.test.tsx
apps/live-control-ui/src/surface/modules/TimelineModule.tsx
apps/live-control-ui/src/surface/modules/TimelineModule.test.tsx
apps/live-control-ui/src/surface/SurfaceShell.test.tsx
apps/live-control-ui/src/test/fixtures.ts
apps/live-control-ui/src/styles.css
Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
```

Use actual existing paths if the implementation shape suggests better names, but do not create a parallel UI architecture.

## Hard Out of Scope

Do not add:

- `GET /api/live/artifact`
- `GET /api/live/capabilities`
- `POST /api/live/commands`
- artifact body rendering
- event detail fetching
- roll-table fetching
- NPC/location file reads
- capability/action buttons
- edit controls
- command submission
- retrieval integration
- browser-side corpus access
- server-side artifact/capability code
- any writes other than existing layout controls already present before PR82

If a selected target needs more information than the plan-view ref already carries, PR82 should display a placeholder and defer it to PR83/PR84.

## Target Model

Reuse the target vocabulary introduced in L5A and reflected in PR81 plan-view types:

```ts
export type ProjectionTargetType =
  | "event"
  | "roll_table"
  | "npc"
  | "location"
  | "runbook_section"
  | "job"
  | "open_loop"
  | "source_packet";
```

Suggested UI target type:

```ts
export interface PaneTarget {
  target_type: ProjectionTargetType;
  target_id: string;
  label: string;
  source_status: ProjectionSourceStatus;
  role?: string | null;
  origin?: {
    module_id: string;
    row_id?: string | null;
  };
}
```

This may live in `surface/targetTypes.ts` or `api/types.ts`. Prefer the location that avoids muddying API payload types with UI-only fields like `origin`.

Do not invent a second target vocabulary. UI target types must remain compatible with `PlanViewRef`.

## Pane State Model

A minimal state model is enough:

```ts
type InspectorPaneState =
  | { status: "closed" }
  | { status: "open"; target: PaneTarget | null };
```

`null` target means the pane is open but no target is selected. This supports empty-state rendering and future keyboard/layout flows.

Recommended app-level state location: `App.tsx` or a small `InspectorPaneContext` if prop drilling becomes ugly. Do not introduce Redux/Zustand or a broad state library.

## InspectorPane Behavior

The pane should render three states:

1. Closed: not visible, or rendered with `hidden`/not mounted.
2. Open empty: “Select a timeline ref or record event to inspect.”
3. Open selected target: metadata-only placeholder.

Selected target content should include:

- human label
- target type
- source status
- role, if present
- target ID as secondary/debug metadata
- origin module/row, if available
- explicit placeholder copy: “Read renderer not implemented yet.”

Example selected state:

```text
Inspector
Roll table · Travel weather table
source: authoritative
role: next_roll
id: T-WX
origin: timeline / beat-day1-weather-front

Read renderer not implemented yet. Artifact and capability reads arrive in PR83.
```

The close control should close the pane without mutating layout or server state.

## Timeline Ref Selection

Update `TimelineModule` so refs can receive an optional callback:

```ts
onSelectTarget?: (target: PaneTarget) => void;
```

If `onSelectTarget` is present, render ref chips as buttons. If absent, render inert display chips. This preserves reusable module behavior and keeps tests simple.

On click, build `PaneTarget` from the existing ref:

```ts
{
  target_type: ref.target_type,
  target_id: ref.target_id,
  label: ref.label,
  source_status: ref.source_status,
  role: ref.role ?? null,
  origin: {
    module_id: "timeline",
    row_id: row.id,
  },
}
```

Do not fetch anything. Do not infer file paths. Do not synthesize artifact content.

## Target Chip / Display Helper

PR81 currently formats timeline refs locally. PR82 should consider extracting a dumb display helper to prevent formatting drift:

```text
TargetChip
- display mode: span
- selectable mode: button
- label format: "roll table · Travel weather table"
```

Rules:

- Human label first.
- `target_id` may be a title or secondary metadata, not the primary display label.
- Source paths must not appear as chip labels.
- Click means “select target,” not “open artifact.”

## App Integration

Expected flow:

```text
App owns selected pane target
→ SurfaceShell receives onSelectTarget
→ ModuleRenderContext exposes onSelectTarget
→ TimelineModule receives onSelectTarget
→ Timeline ref button selects target
→ App opens InspectorPane with selected target
```

`InspectorPane` should render alongside `SurfaceShell` as app chrome, or inside `SurfaceShell` but outside individual modules. It should not be owned by `TimelineModule`.

## Tests

Minimum tests:

1. `InspectorPane` renders closed/empty/selected states.
2. Selected state renders label, target type, source status, role, target ID, and renderer-not-implemented copy.
3. `TimelineModule` renders inert chips when no `onSelectTarget` is supplied.
4. `TimelineModule` renders selectable chips when `onSelectTarget` is supplied.
5. Clicking a timeline ref calls `onSelectTarget` with the expected `PaneTarget` built only from ref + row metadata.
6. `SurfaceShell` or App-level integration test proves clicking a timeline ref opens the inspector pane.
7. Existing Chat, Record, RollStack, Now, Timeline display behavior remains intact.
8. No test should mock `GET /api/live/artifact`, `GET /api/live/capabilities`, or `POST /api/live/commands`.

Suggested verification:

```bash
cd apps/live-control-ui
npm test
npm run build
```

Run Python tests only if docs/fixtures/schemas/server-facing files change:

```bash
uv run pytest tests/test_live_play_schemas.py -q
uv run pytest tests/test_live_control_server.py -q
```

## Acceptance Criteria

- Inspector pane exists as shared app chrome, not inside `TimelineModule`.
- Pane can be closed.
- Pane has an open empty state.
- Pane has a selected-target placeholder state.
- Timeline ref chips can select a target and open the pane.
- Selected target shows only metadata already present in plan-view refs.
- Opening/selecting a target performs no network request.
- There are no artifact reads, capability reads, commands, actions, or writes.
- Existing modules keep working.
- Tests cover shell/state/selection behavior.

## Review Traps

Request changes if PR82 includes:

- artifact/capability endpoints
- server-side artifact read code
- command bus work
- action buttons like “edit,” “save,” “queue patch,” or “mark done”
- click-to-edit behavior
- browser file/corpus reads
- target content pretending to be complete artifact data
- Timeline-owned inspector state
- module-specific pane implementation that cannot generalize beyond Timeline

## PR Body Template

```text
## Summary

- Adds shared inspector pane state/chrome for selected projection targets.
- Adds metadata-only selected-target rendering.
- Wires Timeline ref chips to open the inspector pane using already-loaded plan-view ref data.
- Keeps pane content read-placeholder only; no artifact/capability reads or writes.
- Adds tests for pane states, target selection, and Timeline integration.

## Verification

- [ ] `cd apps/live-control-ui && npm test`
- [ ] `cd apps/live-control-ui && npm run build`

## Out of scope

- Artifact reads
- Capability reads
- Command bus
- Read renderers
- Pane actions
- Writes
- Retrieval integration
- Browser-side corpus access
```

## Next Slice

After PR82, proceed to:

```text
PR83 — L5E Artifact + Capability Reads
```

PR83 should add safe server-side read contracts. PR84 should render read payloads. PR82 should not do either.
