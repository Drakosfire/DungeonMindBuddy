---
document_id: dmb-plan-shared-markdown-canvas-build-first
title: Shared Markdown Canvas — Build-First Execution Plan
document_class: implementation_plan
status: active_prerequisite
version: 1.5
created_at: "2026-07-26"
updated_at: "2026-08-01"
design: ../Design/DESIGN-shared-markdown-canvas-surface-composition.md
interaction_authority: ../Design/ARCHITECTURE-surface-interaction-layer.md
surface_authority: ../Design/ARCHITECTURE-plan-surface-toolbox.md
successor_plan: PLAN-surface-interaction-hoist-build-first.md
first_consumer: /build
---

# Shared Markdown Canvas — Build-First Execution Plan

> **RE-ANCHOR (2026-08-01):** This plan is the **prerequisite plan** for Canvas and
> graphReference **landed primitives** (MC-01, R10a-deps, R10a, MC-02a). Remaining
> shared Nav/Tool/Edit hoist, Plan recomposition, and Build World Reference Loop
> route to
> [`PLAN-surface-interaction-hoist-build-first.md`](PLAN-surface-interaction-hoist-build-first.md)
> (SI-01–SI-05) — **not** as Build-local immediate wiring after MC-02a.

## Status

**PREREQUISITE COMPLETE** for its owned slices. MC-01, R10a-deps, R10a, and MC-02a
have landed. **Active composition sequencing** continues in the Surface Interaction
hoist plan.

Two parallel executable lanes (converge before Stay-on-Build v2):

```text
Lane 1 — projection / graph-reference composition (PREDECESSOR SLICES DONE)
  R10a-deps DONE → R10a DONE → MC-02a DONE
  Successor: SI-02–SI-04 in PLAN-surface-interaction-hoist-build-first.md

Lane 2 — inspection correctness (independent; start immediately)
  BLD inspection-truth defect

Convergence
  → Stay-on-Build v1 summary
      → Stay-on-Build v2 read-only inspector (tool projection)
          → Candidate-assisted Find existing
              → MC-03 node authoring design gate (still gated)
```

**Successor executable next (composition):** SI-01 characterize Plan → SI-02 hoist
shared Tool/Edit → SI-03 recompose Plan → SI-04 Build World Reference Loop — see
[`PLAN-surface-interaction-hoist-build-first.md`](PLAN-surface-interaction-hoist-build-first.md).

Lane 2 remains independently executable: BLD inspection-truth defect.

## Re-anchor

The historical Build roadmap correctly established:

- opaque workspace-document identity;
- the shared two-phase Markdown writer;
- immutable SourceArtifact and ExtractionRun lineage;
- Build extraction and exact Graph Review handoff;
- bounded worldbuilding extraction;
- governed worldbuilding write-plan prepare/confirm.

Its sequencing and current-state sections are no longer operationally accurate. The
full originals are archived at
`archive/2026-07-26/build-surface-foundation/`.

**2026-07-26 dogfood re-anchor** (see design § Dogfood re-anchor):

- Framing: Plan and Build consume the **same** graph-reference capabilities,
  configured per surface — not “Build behaves like Plan.”
- Decomposition: `reference_render` | `reference_insert_existing` |
  `reference_project`.
- Prerequisite path **(Path A, locked 2026-07-27):** projection-host dependency
  extraction (**R10a-deps**) → **R10a** lift into existing
  `AgentInteractionProvider` → remaining **MC-02a** → **MC-02b**. Do **not**
  create a sibling app-level `ProjectionProvider` that full R10 would have to
  absorb again.
- Exact-run boundary: Build may host a **read-only** exact-run inspector in that
  singular container; Build does **not** own dispositions, identity decisions,
  elevation, or prepare/confirm.
- Candidate insertion: **Find existing object** (operator selects); direct Insert
  only with an exact durable node ID already on the payload.
- Inspection truth is an **independent lane**, not a successor to MC-02b.
- Do not archive “no second review panel”; **replace** with the refined boundary
  above.

This plan is the **prerequisite sequencing authority** for shared canvas/component
**primitives**. Composition hoists and Build World Reference Loop are owned by
[`PLAN-surface-interaction-hoist-build-first.md`](PLAN-surface-interaction-hoist-build-first.md).
It does not replace:

- BLD-09 PDF/OCR;
- BLD-10c worldbuilding review UX (dispositions);
- full R10 bottom-pane + localStorage Phase A (R10a is lift-only);
- graph projection or Kernel architecture.

## Current product state

| Area | Current state | Successor correction |
|---|---|---|
| Build editor | Shared `MarkdownCanvasSession` + `MarkdownCanvas` on `/build` | SI-04 Build World Reference Loop (not Build-local MC-02b wiring) |
| Build extraction | Toolbar consumes `committed_clean` envelope | Stay-on-Build summary/inspector after SI-04 + BLD; handoff becomes secondary |
| Projection host | **DONE** — R10a landed (PR #441) | R10b bottom pane + localStorage (parallel) |
| Plan Edit / refs | Plan characterized consumer of neutral `graphReference` (#431) | SI-01 map → SI-03 recompose Plan on shared Tool/Edit hosts |
| Build graph interaction | Starter `#dmb-ref` chips render; shared loop not enabled | SI-04 after SI-02/SI-03 |
| Node authoring | Graph Review Author Draft | MC-03 design gate |
| Inspection truth | Run can be `reviewable` while review-package 422s (`false_anchor_quote`) | **Lane 2 now:** BLD inspection-truth defect |

## Slice table

| Slice | Status | Mission | Must remain false |
|---|---|---|---|
| MC-01 | **DONE** (PR #426) | Shared canvas session/view + Build migration + admitted extraction envelope | — |
| R10a-deps | **DONE** (PR #438) | Projected Plan/Ingest content stops requiring route-local hooks | — |
| R10a | **DONE** (PR #441) — [`HANDOFF-r10a-app-scoped-projection-host-lift.md`](./HANDOFF-r10a-app-scoped-projection-host-lift.md) | Singular projection host in `AgentInteractionProvider` | Build graph enablement was explicitly deferred |
| MC-02a | **DONE** (PR #431) — [`HANDOFF-pr431-surface-neutral-graph-reference-loop.md`](./HANDOFF-pr431-surface-neutral-graph-reference-loop.md) | Neutral `graphReference` contracts; Plan characterized consumer | Build enablement deferred to SI-04 |
| MC-02b | **SUCCESSOR: SI-04** | Build World Reference Loop via shared hosts — see [`PLAN-surface-interaction-hoist-build-first.md`](PLAN-surface-interaction-hoist-build-first.md) | Build-local immediate wiring; Edit Bar Find existing |
| BLD inspection truth | **NEXT (Lane 2)** | Truthful inspection readiness vs `reviewable`; structured diagnostics | New Build panel; weakened evidence validation; waiting on MC-02* |
| Stay-on-Build v1 | QUEUED | In-place exact-run summary + secondary Open full Graph Review | Candidate selection; highlight; insert; untruthful `reviewable` display if BLD not landed |
| Stay-on-Build v2 | QUEUED | Read-only Extraction Run Inspector as tool projection | Dispositions; identity correction; elevation; prepare/confirm; direct insert |
| Candidate Find existing | QUEUED | Candidate seeds shared search; operator selects; insert reference | Implicit candidate→node mapping; MC-03 create |
| MC-03 | DESIGN GATE | One reusable node-authoring capability | Canvas-owned graph writes; Build-local copy of Author Draft |

## Path A lock — R10a-deps predecessor (DONE)

Path A required projection-host dependency extraction before the app-level lift.
R10a-deps (PR #438) landed that contract: projected Plan/Graph Review renderers
consume typed registered bindings rather than route-local provider ancestry.

R10a now owns the singular-host lift into `AgentInteractionProvider` with
tokenized nullable surface publication. Path B (expanding R10a to absorb the
entire dependency + publication rewrite in one slice) remains explicitly not
chosen.

## R10a-deps — Projection-host dependency extraction

### Outcome

Projected content renderers used by Plan and Graph Review no longer depend on
route-local React context hooks for correctness. Dependencies reach the
app-level renderer via **explicit projection payloads** and/or **app-level
registered dependency adapters** owned by the future host.

### Merge-ready invariant

With providers unmounted around a mounted container in a focused test harness,
existing Plan content projections and Graph Review diagnostics projections still
render and navigate correctly from supplied payloads/registrations. No new
surface enablement; no container ownership move yet.

### Must remain false

- Moving `AdaptiveProjectionContainer` / `ProjectionProvider` above the route switch
- Build graph-reference enablement
- Bottom-pane redesign / localStorage Phase A
- Silent auto-pick on ambiguous references

## R10a — App-scoped projection host lift

### Outcome

Projection registry, selected-projection state, and AdaptiveProjectionContainer
ownership move into the existing app-level **`AgentInteractionProvider`** (already
above the route switch and already owning a surface-context publication seam).
Plan and Ingest Graph Review consume that host; UI remains the current
drawer/container chrome (no bottom-pane swap).

### Ownership lock

- **Absorb into `AgentInteractionProvider`.** Do **not** introduce a sibling
  app-level `ProjectionProvider` that full R10 would migrate again.
- R10a ships the **minimum truthful publication seam** required for the lift
  (architecture already assigns full context-publishing to R10; R10a cannot omit
  the subset that makes an inactive/active host honest).

### Publication / registration contract (R10a must specify and test)

1. **Nullable inactive host** — routes with no projection capability leave the
   host with no bound surface; container renders nothing; `openTool` is a no-op
   or explicit error, never closes over a stale Plan config.
2. **Registration + cleanup identity** — bind/unbind carries a surface identity
   token so late Plan/Ingest cleanup cannot erase the next surface’s binding.
3. **Surface-change policy** — active projection clears or revalidates when the
   bound surface identity/context changes; rules are explicit and tested.
4. **Dependency reachability** — Plan resolver and Graph Review live-state
   dependencies reach the app-level renderer only through R10a-deps seams
   (payloads / registered adapters), not via remounting route-local providers
   around a secretly local container.
5. **Build with no tools** — Build may publish a minimal surface binding with
   empty `tools` and no content renderers; it must not mount a second container
   and must not require a full Plan-shaped `PlanContextDescriptor` unless Build
   actually enables projection consumption (that enablement is MC-02b).
6. **SurfaceConfig generalization** — host accepts nullable / Build-capable
   surface publication; mandatory Plan-only context is not the app-host invariant.

### Merge-ready invariant

Across Plan ↔ Build ↔ Ingest navigation there is exactly one projection owner
(`AgentInteractionProvider`) and one adaptive container. Plan’s existing
open/close/content/tool projection behavior is interaction-equivalent. Selected
projection clears or revalidates when surface binding changes. Build gains **no**
new graph-reference affordances.

### Must remain false

- Second container under `BuildSurfacePage`
- Sibling app-level `ProjectionProvider`
- Agent Interaction bottom bar/pane redesign
- localStorage Phase A expansion
- Build Edit dock / chip glance enablement
- Hidden route-local containers retained “temporarily” after the lift

## MC-02a — Neutral graph-reference capability extraction

### Outcome

Remaining Plan reference rendering, insertion, resolution, and object-opening
behavior is supplied through surface-neutral contracts without changing Plan
behavior. (Host-dependency extraction already landed in R10a-deps; this slice
finishes the capability IDs and Plan-as-characterized-consumer work.)

### Required design/implementation work

- Characterize Plan paths first; then extract or wrap:
  search, `insertMarkdownReference`, resolution states, `openGraphReference`,
  chip runtime.
- Keep capability IDs independently enableable.
- Shared glance uses `GraphObjectCard`; ambiguous resolution never auto-picks.
- Optional thin shared-card cleanup only if required for the invariant.

### Must remain false

- Build enablement
- Extraction / Graph Review disposition changes (beyond shared-card extract)
- Renaming Plan UI copy in a way that changes operator-visible Plan behavior

## MC-02b — Build enables shared reference capabilities

### Outcome

A Build Markdown document can render, insert, persist, and open **existing** graph
references using neutral capabilities and the app-scoped host. Build document and
extraction authority remain unchanged.

### Include

- Build Surface capability config + Build graph lens
- Docked existing-object search
- Insert → dirty → Save → reload persistence
- Chip click → truthful resolution → shared GraphObjectCard glance

### Exclude

- Extraction candidates / run inspector
- Node creation / elevation
- Graph Review handoff redesign
- PlanGraphLoadPanel / transitional graph-loader UX

### Dogfood proof

Wherever there is a Markdown canvas on Build, an existing graph object can be
referenced durably and opened interactively — without visiting `/ingest`.

## BLD inspection truth — false_anchor_quote (Lane 2)

### Outcome

An exact ExtractionRun reports inspection readiness truthfully. Invalid evidence
produces stable structured diagnostics. Exact-source validation is not weakened.

### Sequencing

**Independent of Lane 1.** May start immediately and merge without waiting for
R10a-deps / R10a / MC-02*. Converges with Lane 1 **before Stay-on-Build v2**.
Stay-on-Build v1 that displays `reviewable` / inspection readiness **depends on
this slice** so Build does not reproduce the same untruthful status.

### Model choice (pick one in the slice)

- **A:** `reviewable` means package-materializable; else blocked/invalid-evidence.
- **B:** separate `run_status` and `inspection_status` (+ diagnostics).

Reproduce `loc_mirathorn`; freeze artifact/revision/span/quote. No new Build panel.

## Stay-on-Build v1 — exact-run summary

Successful extraction leaves the operator on Build with run ID/status, pinned
source revision/digest, diagnostic state, optional truthful count/category summary,
and secondary “Open full Graph Review.” No candidate selection, highlight, or insert.
If the summary surfaces inspection readiness / `reviewable`, BLD inspection truth
must already be landed.

## Stay-on-Build v2 — Extraction Run Inspector

Build-owned **tool projection** in the singular adaptive container: candidate list,
evidence/spans, pinned source preview/navigation, structured invalid-evidence
diagnostics. Revision-pinned evidence contract is mandatory. No dispositions,
identity correction, elevation, prepare/confirm, or direct candidate insertion.
Requires Lane 1 through MC-02b (host + Build binding) **and** Lane 2 (truthful
inspection readiness).

## Candidate-assisted Find existing

Candidate → Find existing object → shared WG search prefilled → operator selects →
insert reference → dirty → Save. Bridge only; does not create nodes or canonize
candidates.

## MC-03 — Node authoring design gate

Unchanged: design gate before any create/bind graph-write capability. No copying
Graph Review Author Draft into `buildSurface/`; no canvas-owned graph writes.

## Independent successors

- **BLD-10c:** worldbuilding dispositions and prepare/confirm UX on Graph Review.
- **BLD-09:** PDF/OCR source lineage; independent.
- **R10 (remainder / R10b):** bottom Agent Interaction Bar/Pane + localStorage
  Phase A after R10a (same provider; no second ownership migration).
- **Plan/runbook canvas migration:** after MC-02b proves shared refs on Build.
