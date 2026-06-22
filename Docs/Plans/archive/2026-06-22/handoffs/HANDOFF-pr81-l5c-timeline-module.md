---
document_id: dmb-handoff-pr81-l5c-timeline-module
title: PR 81 Handoff — L5C Timeline Module
document_class: handoff
status: ready_for_implementation
version: 0.1
created_at: "2026-05-28T15:00:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
  - path: Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-pr79-l5a-projection-command-contracts.md
    role: prior_contract_slice
  - path: Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-pr80-l5b-plan-view-projection.md
    role: prior_projection_slice
---

# PR 81 Handoff — L5C Timeline Module

## Reanchor

PR #79 is merged. It established the L5A projection/command contracts in Python:

```text
src/live_play/projections/
  targets.py
  capabilities.py
  commands.py
  invalidation.py
  write_results.py
```

PR #80 is merged. It established the first real projection consumer:

```text
GET /api/live/plan-view
src/live_play/projections/plan_view.py
evals/c2_live_prep/live/schemas/plan_view.schema.json
evals/c2_live_prep/live/session_22/plan_view.sample.json
```

The next clean slice is L5C: render that projection in the React live-control surface as a read-only Timeline module.

This PR should validate whether the plan-view payload feels usable when rendered. It should not expand backend architecture.

## Mission

Implement a read-only `timeline` module in `apps/live-control-ui` that consumes `GET /api/live/plan-view` and renders the Session 22 plan-view projection.

The desired data flow is:

```text
GET /api/live/plan-view
→ typed TypeScript client/types
→ App loads planView
→ SurfaceShell/moduleRegistry passes planView to modules
→ TimelineModule renders rows + typed refs
```

## Scope

Implement only the UI consumption slice:

- Add TypeScript types for the plan-view payload.
- Add `getPlanView()` to the UI API client.
- Load `planView` in `App.tsx` alongside surface/events/jobs.
- Pass `planView` through `SurfaceShell` and `ModuleRenderContext`.
- Add `TimelineModule.tsx`.
- Register `timeline` in `moduleRegistry.tsx`.
- Add `timeline` as an optional catalog module in the Session 22 live packet.
- Add `timeline` to the seed surface layout, preferably in the `bottom` slot and collapsed or ordered after roll stack if the layout becomes noisy.
- Add minimal styles consistent with existing module classes.
- Add tests for API client typing/mocking where useful, module rendering, registry wiring, and existing shell behavior.

Recommended files:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/App.tsx
apps/live-control-ui/src/surface/SurfaceShell.tsx
apps/live-control-ui/src/surface/moduleRegistry.tsx
apps/live-control-ui/src/surface/modules/TimelineModule.tsx
apps/live-control-ui/src/surface/modules/TimelineModule.test.tsx
apps/live-control-ui/src/surface/modules/*existing tests if registry/shell coverage belongs there
apps/live-control-ui/src/App.css or existing stylesheet path
evals/c2_live_prep/live/session_22/live_packet.json
evals/c2_live_prep/live/session_22/surface_layout.json
tests/test_live_surface_layout_contracts.py or existing server/layout test file, only if catalog/layout schema coverage needs updating
```

Use actual existing paths if names differ, but do not create a parallel UI architecture.

## Out of Scope

Do not implement:

- Universal inspector pane.
- Pane target selection state.
- Clicking refs to open anything.
- Artifact read endpoints.
- Capability endpoint.
- `POST /api/live/commands`.
- Command execution.
- Editable timeline rows.
- Beat completion/reconciliation workflows.
- Retrieval calls from the browser.
- Corpus reads or writes from the browser.
- Any new backend projection behavior unless a tiny catalog/layout fixture update is required.

This PR is read-only UI consumption.

## Product Constraints

The timeline is orientation, not task management.

It may show statuses such as `projected`, `active`, `played`, `blocked`, or `unknown`, but it must not create a workflow around marking beats complete, reconciling planned vs played state, or editing projected rows.

The UI should feel like a live GM cockpit, not a repo dashboard. Human labels should lead. Source paths, if ever exposed, belong in secondary/provenance treatment, not row titles.

## Existing Code Seams

Current relevant UI files on `main`:

```text
apps/live-control-ui/src/App.tsx
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/surface/SurfaceShell.tsx
apps/live-control-ui/src/surface/moduleRegistry.tsx
apps/live-control-ui/src/surface/modules/NowModule.tsx
apps/live-control-ui/src/surface/modules/RollStackModule.tsx
```

Observed current seams:

- `App.tsx` owns top-level load state and currently loads surface, events, and jobs.
- `liveApi.ts` has API helpers for surface, events, jobs, query, layout save, roll resolve, job completion, and packet rebuild.
- `types.ts` does not yet define plan-view types.
- `SurfaceShell.tsx` passes shared module data through `ModuleRenderContext`.
- `moduleRegistry.tsx` currently renders `chat`, `record`, `roll_stack`, and `now`; unknown modules fall back to `UnsupportedModule`.

PR81 should extend these seams directly.

## Required TypeScript Contract

Add types that mirror `plan_view.schema.json`.

Suggested shape:

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

export type ProjectionSourceStatus =
  | "derived"
  | "authoritative"
  | "live_only"
  | "stale"
  | "missing"
  | "unknown";

export type TimelineStatus =
  | "projected"
  | "active"
  | "played"
  | "skipped"
  | "blocked"
  | "unknown";

export interface PlanViewRef {
  target_type: ProjectionTargetType;
  target_id: string;
  label: string;
  source_status: ProjectionSourceStatus;
  role?: string | null;
}

export interface PlanViewStateLinks {
  event_ids: string[];
  job_ids: string[];
  open_loop_ids: string[];
}

export interface PlanViewTimelineRow {
  id: string;
  label: string;
  status: TimelineStatus;
  time_hint?: string | null;
  summary: string;
  table_ready_prompt?: string | null;
  refs: PlanViewRef[];
  state_links: PlanViewStateLinks;
}

export interface PlanViewProjection {
  schema_version: string;
  campaign_id: string;
  session: number;
  authoritative: false;
  generated_at: string;
  derived_from: string[];
  timeline: PlanViewTimelineRow[];
}
```

Do not use `any` for timeline rows or refs.

## API Client Requirements

Add:

```ts
export async function getPlanView(): Promise<PlanViewProjection> {
  return apiFetch<PlanViewProjection>("/api/live/plan-view");
}
```

`App.tsx` should fetch plan view during `refreshAll()` using the same API helper pattern as events/jobs.

Recommended load behavior:

```text
getSurface()
Promise.all([getEvents(), getJobs(), getPlanView()])
```

A plan-view load failure may put the app into the existing top-level error state for PR81. A later PR can make per-module degraded loading more nuanced. If per-module error handling is cheap and localized, it is allowed, but do not distort the app state model to support it yet.

## Timeline Module Behavior

`TimelineModule` should render:

- Module title from catalog entry when available.
- A small non-authoritative/derived indicator.
- Empty state when `timeline.length === 0`.
- One row per timeline beat.
- Human row label.
- Status badge.
- Time hint if present.
- Summary.
- Table-ready prompt if present.
- Ref chips for each ref.

Recommended visual hierarchy:

```text
Timeline
Derived plan · session 22

[projected] Pre-travel Silver Raven dispatch
Pre-travel
The session opens with comms pressure...
Prompt: Who receives the next outbound message first?
[runbook_section] Session 22 runbook pre-travel beats
[open_loop] Silver Raven reply
```

Ref chips should be inert display elements. Buttons/links imply interactivity and should wait for PR82/PR83 unless they are explicitly disabled and not misleading.

## Ref Chip Rules

Render chips as:

```text
<target_type label>: <label>
```

Examples:

```text
roll table · Storm weather
npc · Lysandro Ironveil
location · Mireward Gate
open loop · Grobnok evening contact
```

Use human labels first. `target_id` may be present in a title attribute or visually muted metadata if useful, but it must not be the primary label.

Do not show source paths as row titles or chip labels.

## Catalog/Layout Requirements

Add the module to `live_packet.surface_catalog`:

```json
{
  "module_id": "timeline",
  "title": "Timeline",
  "default_slot": "bottom",
  "required": false,
  "enabled_by_default": true,
  "description": "Read-only projected session beats from the derived plan-view projection.",
  "config_schema": null
}
```

Add a corresponding `surface_layout.json` module row if the seed layout enumerates enabled modules explicitly. Suggested default:

```json
{
  "module_id": "timeline",
  "slot": "bottom",
  "order": 30,
  "enabled": true,
  "collapsed": false,
  "size": null,
  "config": {}
}
```

If bottom slot becomes noisy, set `collapsed: true` or place it after `roll_stack`; do not move it to primary `main` by default unless the layout currently has no better place.

## Test Requirements

Minimum tests:

1. `getPlanView()` calls `/api/live/plan-view` and returns typed payload shape via existing API mock style, if API client tests exist.
2. `TimelineModule` renders row label, status, time hint, summary, and table-ready prompt.
3. `TimelineModule` renders typed ref chips using `target_type` and human `label`.
4. `TimelineModule` renders empty state for an empty timeline.
5. `moduleRegistry` renders `TimelineModule` for `module_id: "timeline"`.
6. Existing Chat, Record, RollStack, and Now module behavior remains intact.
7. Surface layout/catalog tests still pass after adding the optional `timeline` module.
8. No test should assert click/edit/command behavior for timeline refs.

Suggested commands:

```bash
cd apps/live-control-ui
npm test -- --runInBand
npm run build
```

If `--runInBand` is not supported by Vitest in this package, use:

```bash
cd apps/live-control-ui
npm test
npm run build
```

Server-side fixture/layout verification, if needed:

```bash
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_surface_layout_contracts.py -q
```

Use the actual existing test filename if layout validation lives elsewhere.

## Acceptance Criteria

- Timeline module appears as an optional catalog module.
- The seed layout can render the timeline module without breaking required modules.
- App loads `planView` from `GET /api/live/plan-view`.
- Timeline rows show human labels, status, time hint, summary, and table-ready prompt.
- Refs render as typed inert chips: `npc`, `location`, `roll_table`, `open_loop`, etc.
- Empty, loading, and error states exist at either app or module level.
- Raw source paths are not primary labels.
- No writes are introduced.
- Existing Chat, Record, RollStack, Now, layout controls, and live query refresh behavior remain intact.

## Explicit Non-Goals / Review Traps

Request changes if PR81 adds any of these:

- Click-to-edit timeline row behavior.
- Clicking refs to open an inspector pane.
- New `GET /api/live/artifact` or `GET /api/live/capabilities` backend work.
- `POST /api/live/commands`.
- Any browser-side corpus file access.
- Any attempt to make the timeline authoritative.
- Beat completion, reconciliation, or task-management semantics.
- Direct display of raw source paths as the primary timeline experience.

## Recommended Nano-Commit Plan

```text
1. docs: add PR81 L5C handoff
2. api: add plan-view TypeScript types and client helper
3. ui: load planView through App and SurfaceShell context
4. ui: add TimelineModule and registry wiring
5. data: add timeline catalog/layout seed entries
6. test: cover timeline rendering, registry, and existing UI invariants
7. docs: update checklist evidence after verification
```

Keep implementation commits small enough that review can detect UI scope creep early.

## PR Body Template

```text
## Summary

- Adds typed UI client/types for `GET /api/live/plan-view`.
- Loads plan-view projection in the React surface.
- Adds read-only `TimelineModule` rendering rows, statuses, prompts, and typed ref chips.
- Registers `timeline` as an optional catalog/layout module.
- Adds tests for timeline rendering and registry behavior.

## Verification

- [ ] `cd apps/live-control-ui && npm test`
- [ ] `cd apps/live-control-ui && npm run build`
- [ ] `uv run pytest tests/test_live_control_server.py -q` if catalog/layout fixtures changed

## Out of scope

- Inspector pane
- Clicking refs
- Artifact/capability reads
- Command bus
- Timeline edits or beat reconciliation
- Retrieval integration
- Corpus reads/writes from the browser
```

## Review Rubric

Reviewer should check:

- Is this purely UI consumption of the existing plan-view endpoint?
- Does it avoid backend expansion except catalog/layout fixture updates?
- Does `TimelineModule` render human-facing labels rather than path-first/debug labels?
- Are refs typed and inert?
- Are loading/error/empty states accounted for?
- Does the module integrate through existing `App` → `SurfaceShell` → `moduleRegistry` seams?
- Do existing Chat/Record/RollStack/Now behaviors remain intact?
- Does it avoid inspector, command bus, artifact reads, and writes?

## Next Slice

After PR81, proceed to:

```text
PR 82 — L5D Universal Inspector Pane Shell
```

PR82 should introduce pane target state and shared chrome, but still no artifact reads/writes.

Keep the forward sequence:

```text
81 Timeline Module
82 Inspector Pane Shell
83 Artifact + Capability Reads
84 Read-only Pane Renderers
85 Command Bus First Writes
86 Pane Actions
87 Scoped Roll-table Writes
```

This sequence preserves the scrutiny ladder and prevents the UI from jumping straight into editable projection chaos.
