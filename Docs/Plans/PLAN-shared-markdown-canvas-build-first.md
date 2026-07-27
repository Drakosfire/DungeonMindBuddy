---
document_id: dmb-plan-shared-markdown-canvas-build-first
title: Shared Markdown Canvas — Build-First Execution Plan
document_class: implementation_plan
status: active
version: 1.1
created_at: "2026-07-26"
updated_at: "2026-07-26"
design: ../Design/DESIGN-shared-markdown-canvas-surface-composition.md
surface_authority: ../Design/ARCHITECTURE-plan-surface-toolbox.md
first_consumer: /build
---

# Shared Markdown Canvas — Build-First Execution Plan

## Status

**ACTIVE.** MC-01 (shared Markdown canvas session + Build migration) has landed.
Dogfood after the preloaded Build canvas re-anchored the next sequence: shared
graph-reference capabilities and stay-on-Build extraction inspection — **not**
“Plan parity” by copying Plan providers, and **not** a Build-local candidate
workbench.

Executable next:

```text
R10a app-scoped projection host lift
  → MC-02a neutral graph-reference extraction
      → MC-02b Build enables shared reference capabilities
          → BLD inspection-truth defect
              → Stay-on-Build v1 summary
                  → Stay-on-Build v2 read-only inspector (tool projection)
                      → Candidate-assisted Find existing
                          → MC-03 node authoring design gate (still gated)
```

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
- Prerequisite: **R10a** lifts the singular projection host above routing before
  Build consumes it.
- Exact-run boundary: Build may host a **read-only** exact-run inspector in that
  singular container; Build does **not** own dispositions, identity decisions,
  elevation, or prepare/confirm.
- Candidate insertion: **Find existing object** (operator selects); direct Insert
  only with an exact durable node ID already on the payload.
- Do not archive “no second review panel”; **replace** with the refined boundary
  above.

This plan is the sequencing authority for shared canvas/component work. It does
not replace:

- BLD-09 PDF/OCR;
- BLD-10c worldbuilding review UX (dispositions);
- full R10 bottom-pane + localStorage Phase A (R10a is lift-only);
- graph projection or Kernel architecture.

## Current product state

| Area | Current state | Next correction |
|---|---|---|
| Build editor | Shared `MarkdownCanvasSession` + `MarkdownCanvas` on `/build` | Enable shared graph-reference capabilities (MC-02b) after R10a/MC-02a |
| Build extraction | Toolbar consumes `committed_clean` envelope | Stay-on-Build summary/inspector after MC-02b; handoff becomes secondary |
| Projection host | Plan shell + Graph Review each mount `ProjectionProvider` / container | **R10a** singular host above route switch |
| Plan Edit / refs | Plan-local search, chip runtime, projection open | **MC-02a** neutral contracts; Plan characterized consumer |
| Build graph interaction | Starter `#dmb-ref` chips render; no Edit dock / projection glance | MC-02b Build lens + docked search + shared glance |
| Node authoring | Graph Review Author Draft | MC-03 design gate |
| Inspection truth | Run can be `reviewable` while review-package 422s (`false_anchor_quote`) | BLD inspection-truth defect before Stay-on-Build v2 |

## Slice table

| Slice | Status | Mission | Must remain false |
|---|---|---|---|
| MC-01 | **DONE** (PR #426) | Shared canvas session/view + Build migration + admitted extraction envelope | — |
| R10a | **NEXT** | Singular projection registry/state/container above Plan/Build/Ingest routing; Plan interaction-equivalent | Build graph enablement; bottom-pane redesign; localStorage Phase A |
| MC-02a | QUEUED | Surface-neutral `reference_render` / `reference_insert_existing` / `reference_project`; Plan unchanged as consumer | Build enablement; extraction inspector; MC-03 |
| MC-02b | QUEUED | Build enables those three capabilities via Build lens + app-scoped host | Extraction candidates; dispositions; PlanGraphLoadPanel; node create |
| BLD inspection truth | QUEUED | Truthful inspection readiness vs `reviewable`; structured diagnostics | New Build panel; weakened evidence validation |
| Stay-on-Build v1 | QUEUED | In-place exact-run summary + secondary Open full Graph Review | Candidate selection; highlight; insert |
| Stay-on-Build v2 | QUEUED | Read-only Extraction Run Inspector as tool projection | Dispositions; identity correction; elevation; prepare/confirm; direct insert |
| Candidate Find existing | QUEUED | Candidate seeds shared search; operator selects; insert reference | Implicit candidate→node mapping; MC-03 create |
| MC-03 | DESIGN GATE | One reusable node-authoring capability | Canvas-owned graph writes; Build-local copy of Author Draft |

## R10a — App-scoped projection host lift

### Outcome

Projection state, registry, and AdaptiveProjectionContainer are owned once above the
route switch. Plan and Ingest Graph Review consume that host; UI remains the
current drawer/container chrome (no bottom-pane swap).

### Merge-ready invariant

Across Plan ↔ Build ↔ Ingest navigation there is exactly one projection provider
and one adaptive container. Plan’s existing open/close/content/tool projection
behavior is interaction-equivalent. Selected projection clears or revalidates when
surface context changes. Build gains **no** new graph-reference affordances.

### Must remain false

- Second container under `BuildSurfacePage`
- Agent Interaction bottom bar/pane redesign
- localStorage Phase A expansion
- Build Edit dock / chip glance enablement

## MC-02a — Neutral graph-reference capability extraction

### Outcome

Plan’s reference rendering, insertion, resolution, and object-opening behavior is
supplied through surface-neutral contracts without changing Plan behavior.

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

## BLD inspection truth — false_anchor_quote

### Outcome

An exact ExtractionRun reports inspection readiness truthfully. Invalid evidence
produces stable structured diagnostics. Exact-source validation is not weakened.

### Model choice (pick one in the slice)

- **A:** `reviewable` means package-materializable; else blocked/invalid-evidence.
- **B:** separate `run_status` and `inspection_status` (+ diagnostics).

Reproduce `loc_mirathorn`; freeze artifact/revision/span/quote. No new Build panel.

## Stay-on-Build v1 — exact-run summary

Successful extraction leaves the operator on Build with run ID/status, pinned
source revision/digest, diagnostic state, optional truthful count/category summary,
and secondary “Open full Graph Review.” No candidate selection, highlight, or insert.

## Stay-on-Build v2 — Extraction Run Inspector

Build-owned **tool projection** in the singular adaptive container: candidate list,
evidence/spans, pinned source preview/navigation, structured invalid-evidence
diagnostics. Revision-pinned evidence contract is mandatory. No dispositions,
identity correction, elevation, prepare/confirm, or direct candidate insertion.

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
- **R10 (remainder):** bottom Agent Interaction Bar/Pane + localStorage Phase A
  after R10a.
- **Plan/runbook canvas migration:** after MC-02b proves shared refs on Build.
