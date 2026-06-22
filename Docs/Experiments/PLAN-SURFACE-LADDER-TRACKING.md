# Plan Surface Ladder Tracking

Version: 0.1  
Status: active implementation on main  
Workstream: Plan Surface / SurfaceConfig / Projection  
Trunk branch: `experiment/plan-surface-ladder`  
Sibling workstream: `experiment/ontology-taxonomy-ladder` (derived semantics; consume via adapter only)

## Purpose

Track the Plan Surface ladder: an intentional `/plan` route composed from `SurfaceConfig` + `PlanSurfaceShell` (NavBar, EditBar, SurfaceCanvas) that publishes context and projections into the app-level agent interaction layer.

Canon decision (2026-06-21): **Agent interaction is not a `/plan` sub-state.** `AgentInteractionProvider` belongs above routes/surfaces, alongside or inside `AppChrome`, and owns the user's interaction continuity across projects and surfaces. Individual surfaces publish current context and available projections; they do not own the agent conversation, proof trail, open/minimized pane state, or cross-project interaction history.

The old right-side `/plan` Tools drawer is implementation state only. The target pattern is a persistent bottom **Agent Interaction Bar** plus expandable **Agent Interaction Pane**. The pane renders registered projections such as chat/ask, recap ingestion, statblock workbench, reference inspectors, and corpus-impact proof views. `/plan` contributes planning context and plan-specific projections; the bar remains a user/app-level affordance.

Composition target:

```text
AppChrome
  AgentInteractionProvider
    Route / Surface
      PlanSurfaceShell
      LiveControlSurface
      TiptapSurface

  AgentInteractionBar
  AgentInteractionPane
```

State ownership:

- `AgentInteractionProvider` owns conversation/thread pointers, pane open/minimized state, active projection, recent tool runs, notifications, and proof-trail pointers.
- Surfaces publish ambient context: campaign/session, selected document block, selected reference, active event/job, corpus root/project id, and available projection registrations.
- Project/corpus writes remain scoped to explicit tool flows and backend APIs; the provider stores pointers and summaries, not canonical corpus payloads.
- First persistence may be browser-local, but the design target is user-level continuity outside any one project repo.

## Branch Contract

Root experiment branch:

`experiment/plan-surface-ladder`

Stacked PR branches:

`surface-exp/<number>-<short-name>`

## Rung Map

| Rung | Slug | Depends on |
|------|------|------------|
| R0 | ladder-scaffold | — |
| R1 | surface-shell-plan-route | R0 |
| L1 | shared-reference-resolver | R0 |
| L2 | derived-views-adapter | R0 |
| L3 | edit-capability | R0 |
| R2 | projection-registry | R1 |
| R8 | surface-theme | R1 |
| R6 | ingestion-tool-mount | R2 |
| R7 | statblock-tool-mount | R2 |
| R5 | reference-projection | R2, L1, L2, L3 |
| R10 | agent-interaction-provider | R2, R5, R6, R7 |
| R9 | integration-verification | R5, R6, R7, R8, R10 |

## Defensible Rubric (every PR)

- **Testing:** unit + seam test at owning boundary; §7 command named in handoff.
- **Security:** two-phase writer + allowlist for corpus writes; validate `refId` before path use; no secrets/PII in artifacts.
- **Simplicity:** one app-level agent interaction provider, one projection registry, one edit capability, one resolver, one theme; resolve kinds, don't declare enums.
- **Composability:** leaf modules usable without shell; typed contracts; allowlist-scoped diffs.

## Handoffs

See `Docs/Plans/HANDOFF-pr*-plan-surface-*.md` for agent dispatch packages.

## Verification (integration)

```bash
cd apps/live-control-ui && npm run build && npm test -- --run src/planSurface
uv run pytest tests/test_live_recap_ingest_api.py -q
```
