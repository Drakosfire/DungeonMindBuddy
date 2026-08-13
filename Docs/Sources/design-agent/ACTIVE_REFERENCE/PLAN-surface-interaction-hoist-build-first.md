---
document_id: dmb-plan-surface-interaction-hoist-build-first
title: Surface Interaction Layer — Hoist Build-First Execution Plan
document_class: implementation_plan
status: active
version: 1.0
created_at: "2026-08-01"
updated_at: "2026-08-01"
architecture: ../Design/ARCHITECTURE-surface-interaction-layer.md
canvas_authority: ../Design/DESIGN-shared-markdown-canvas-surface-composition.md
plan_domain: ../Design/ARCHITECTURE-plan-surface-toolbox.md
prerequisite_plan: PLAN-shared-markdown-canvas-build-first.md
---

# Surface Interaction Layer — Hoist Build-First Execution Plan

## Status

**ACTIVE.** This plan is the **sequencing authority** for hoisting shared Nav, Tool,
Edit, and Agent/Projection hosts and recomposing Plan and Build surfaces around the
independent Canvas primitive.

[`PLAN-shared-markdown-canvas-build-first.md`](PLAN-shared-markdown-canvas-build-first.md)
remains the **prerequisite plan** for Canvas and graphReference landing. Remaining
Build/Plan **composition** work routes here — not as Build-local immediate wiring
after MC-02a.

## Re-anchor (2026-08-01)

| Predecessor | Status | Merge SHA |
|---|---|---|
| MC-01 Canvas — PR #426 | **DONE** | `7d98074d434a5310d21d4fe645e497789e0a3114` |
| R10a app projection host — PR #441 | **DONE** | `4ec74045f0b7878434e911fa73c407727d3e958c` |
| MC-02a neutral graphReference — PR #431 | **DONE** | `130104442b0ac7ad9a56c7e744014f1b8d56ad62` |
| R10a-deps — PR #438 | **DONE** | (ancestor of R10a) |
| Shared Nav / Tool / Edit hoist | **NOT LANDED** — target | SI-02 |
| Plan recomposition | **NOT LANDED** | SI-03 |
| Build World Reference Loop | **NOT LANDED** | SI-04 |

Architecture authority:
[`ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md).

## Sequence

```text
SI-00  Docs authority sync (this plan + architecture)     DONE — docs slice
SI-01  Characterize Plan contributions to shared hosts   NEXT
SI-02  Hoist shared Tool / Edit hosts + publication       QUEUED
SI-03  Recompose Plan (consumer, not bar owner)           QUEUED
SI-04  Build World Reference Loop                         QUEUED
SI-05  Dogfood / refine shared interaction               QUEUED
Play   Surface recomposition                              LATER (explicitly out of SI scope)
```

### Boundaries (non-negotiable)

- **Characterize before moving** — SI-01 completes before SI-02 edits shared hosts.
- **One host per bar** — no second Tool/Edit/Projection under a surface route.
- **Canvas independent** — document authority stays in `MarkdownCanvasSession`.
- **Plan not shared API** — Plan is characterized consumer; neutral contracts in shared packages.
- **Build not bar owner** — Build publishes capabilities; shared bars own UI.
- **Build loop:** search → inspect → insert → save → reload → reopen.
- **Extraction inspector separate** — tool projection, not Edit Bar.
- **Graph writes separate** — Supergraph/Kernel path only.

## Slice table

| Slice | Status | Mission | Must remain false |
|---|---|---|---|
| SI-00 | **DONE** (docs) | Neutral architecture + authority sync across active docs | Runtime hoist; new types |
| SI-01 | **NEXT** | Map Plan Tool/Edit/Agent/projection publications vs target manifest | Moving code before map exists |
| SI-02 | QUEUED | Shared Tool Bar + Edit Bar hosts in Interaction Layer; publication API | Plan-local duplicate bars; Build bar ownership |
| SI-03 | QUEUED | Plan recomposed as characterized consumer | Plan owning shared host implementation |
| SI-04 | QUEUED | Build enables World Reference Loop via shared hosts + Build lens | Build-local graphReference fork; Edit Bar Find existing |
| SI-05 | QUEUED | Dogfood Build + Plan; refine publication contracts | Play scope creep |
| R10b remainder | QUEUED (parallel track) | Bottom Agent Bar/Pane + localStorage Phase A | Second projection owner |
| BLD inspection truth | Independent lane | Truthful reviewable vs package readiness | Blocking SI-00–02 |
| Stay-on-Build v1/v2 | QUEUED after SI-04 + BLD | In-place summary / read-only inspector | Dispositions on Build |

## SI-01 — Characterize Plan contributions

### Outcome

A contribution map lists every Plan-local assembly of Tool Bar, Edit Bar, Agent
context, and projection registration with target shared-host ownership and migration
notes. No production moves until the map is checked in.

### Include

- Inventory: `PlanSurfaceShell`, Edit dock model, tool registry entries, graphReference
  consumer paths, AgentInteraction publication today.
- Label each as **stay Plan-domain** vs **hoist to Interaction Layer**.
- Explicit **non-goals**: Plan session prep policy, callout extensions, prep-memory
  query shapes stay Plan-domain.

### Must remain false

- Hoisting code in the same PR as the map
- Declaring Plan the permanent shared API owner

## SI-02 — Hoist shared Tool / Edit hosts

### Outcome

AppChrome owns Tool Bar and Edit Bar rendering. Active surface publishes tool
launchers and edit commands through the conceptual manifest seam (implementation
details in handoff allowlist when dispatched).

### Include

- Single Tool Bar host; single Edit Bar host.
- Lease-scoped registration/cleanup (same token pattern as R10a projection host).
- Build may publish empty tool set until SI-04.

### Must remain false

- `composeSurfaceCapabilities` owning bar DOM
- SurfaceShell owning bars
- Find existing on Edit Bar

## SI-03 — Recompose Plan

### Outcome

Plan route uses shared Tool/Edit hosts. Plan retains prep lens, characterized
graphReference consumer, and Plan extensions (callouts, lock policy).

### Must remain false

- Plan-local duplicate Tool/Edit bars
- Plan as shared package API owner

## SI-04 — Build World Reference Loop

### Outcome

Build publishes Build graph lens + reference capabilities into shared hosts:

```text
search (Tool Bar) → inspect (Projection) → insert (Canvas edit) → save → reload → reopen
```

Uses neutral `graphReference` from MC-02a (#431). **Find existing** is Tool Bar.

### Include

- `reference_render`, `reference_insert_existing`, `reference_project` with Build lens
- Docked search, chip glance, persistence through Canvas save/reload

### Exclude

- Extraction run inspector (Stay-on-Build v2)
- Candidate-assisted Find existing (successor)
- Graph writes / node creation (MC-03 gate)

### Must remain false

- Build-owned AgentInteractionProvider state
- MC-02b as immediate Build-local step without SI-02/SI-03
- Importing Plan surface components as durable API

## SI-05 — Dogfood / refine

### Outcome

Operator can prepare on Plan and worldbuild on Build with shared chrome, independent
Canvas, and truthful lease behavior across surface switches.

## Relationship to prerequisite plan

[`PLAN-shared-markdown-canvas-build-first.md`](PLAN-shared-markdown-canvas-build-first.md)
owned MC-01, R10a-deps, R10a, MC-02a. Those slices are **DONE**. MC-02b as
"Build enables shared reference capabilities" **successor work lives under SI-04**
here, not as ad hoc Build-local wiring.

Historical Build roadmap/plan archives remain forwarding records only — link
[`ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)
and this plan.

## Named successors (outside this plan's immediate queue)

- Stay-on-Build v1/v2 — [`HANDOFF-build-stay-on-build-dogfood-after-mc02.md`](HANDOFF-build-stay-on-build-dogfood-after-mc02.md) (re-anchor after #431)
- R10b bottom pane + localStorage Phase A
- MC-03 node authoring design gate
- Play surface Interaction Layer recomposition

## Verification

Each implementation slice requires its own HANDOFF with section 4 allowlist and
section 7 verification. Docs-only SI-00 is satisfied by authority scans and link
validation on the touched document set.
