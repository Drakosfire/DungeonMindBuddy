# HANDOFF — DOGFOOD-POLISH: Intentional Build Document Context

**Line of work:** DOGFOOD-POLISH  
**Status:** DOING  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Predecessor:** PR #551 — `SURFACE: add global World Graph status and generic context bar`  
**Base:** `main` after PR #551 (`721bf3211f1173241c09bbdb86007328a6c58a70`)  
**Branch:** `agent/dogfood-polish-build-document-context`  
**Suggested PR title:** `DOGFOOD-POLISH: load Build documents through Surface Context`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-dogfood-polish-build-document-context.md`

---

## Mission

Make Build the **second real consumer of the generic Surface Context Bar**.

Build must answer *what worldbuilding source am I working on?* and let the operator intentionally load an existing source, switch among sources, create a new source, and return via Back/Forward — **without** treating navigation to `/build` as permission to create durable data.

After PR #551, Plan publishes `PREP`. Build now publishes **`DOCUMENT`** via the same host seam: selector, campaign/class badges, switching/error state, `+ New source`, and light authoring status.

Implementation pillars:

- **Retire bare-entry auto-create** — remove `startBareBuildAutoCreate`, latch, and route-entry POST semantics; bare `/build` and `/build?campaign=…` produce **0 workspace-document POSTs**.
- **Build DOCUMENT module** — Build-owned composition (`BuildSurfaceContext`, selector, create control) contributing `id = "build-document"`, `label = "DOCUMENT"` through `SurfaceContextHost`.
- **Resolve-before-navigate** — Build-owned `useBuildWorkspaceDocumentController`: exact snapshot preflight, monotonic load generation, failed switch keeps prior authority, history sync with same protection.
- **Shared create controller** — consume `createWorkspaceDocumentCreationController()` for New Source (required title; no default `"Untitled worldbuilding source"`).
- **`hideReadyHeader`** — smallest neutral MarkdownCanvas seam so DOCUMENT context owns title/status summary; Canvas starts with authored content.

Target flow:

```text
/build
→ DOCUMENT context visible
→ choose existing source OR intentionally create New source
→ exact documentId becomes authoritative
→ Canvas opens that exact source
```

---

## Governing invariant

> **Build's active work object is one exact server-issued workspace `documentId`. Surface Context is where the operator chooses that object; MarkdownCanvas remains the authority for its contents, revision, dirty state, save, and reconciliation.**

```text
documentId     = document identity
campaign       = document campaign/context metadata, not identity
campaigns/session = World Graph lens state, not document identity
SurfaceContextHost = presentation/composition
Build          = document-selection policy
MarkdownCanvasSession = document authoring authority
```

A failed or stale attempt to open another source never silently replaces the currently authoritative source.

**Architectural falsification:** Build adopts the generic Surface Context host without teaching the host what a Build document is. If Build requires redesigning `SurfaceContextHost` for worldbuilding semantics, **STOP** and reassess the abstraction.

See plan architecture: AppChrome → World Graph + SurfaceContextHost → Build DOCUMENT module; controller resolves then commits URL/history; MarkdownCanvasSession keyed by `documentId`; create flows through shared `createWorkspaceDocumentCreationController`.

---

## Target product (summary)

**Loaded source:** DOCUMENT row shows title (primary), campaign badge, light class/status, `+ New source`. Never lead with `documentId`, `target_relpath`, revision, or registry internals.

**Empty Build:** `No source loaded` + Choose source + New source. Campaign hint may order/prefill UI; it is not permission to write.

**New Source:** small popover (Campaign + required Title); defaults `documentClass = lore`, `authorityState = draft`, `visibilityState = internal`.

**Selector:** all active `worldbuilding_source` across campaigns; option value is `record.document_id` only; duplicate titles get quiet disambiguation hints, not UUIDs.

**Status in context:** compact `Saved` / `Unsaved changes` / `Saving…` / `Needs reconciliation` — not revision/hash/phase jargon.

---

## Falsification highlights

| Scenario | Required outcome |
|---|---|
| Empty entry `/build` or `?campaign=` | 0 POSTs; DOCUMENT visible; selector + New source available |
| Direct `?documentId=B` | exact B resolves → B Canvas + context |
| Switch A → B | resolve B first; one history entry; A authoritative until B admitted |
| Failed / stale switch | A (or C) remains Canvas, URL, context; no fallback heuristics |
| Back/Forward | same resolve-first protection; broken history restores current + error |
| Create New source | exactly one POST; activate from POST `document_id` only |
| Create / activation failure | current doc unchanged; Retry Open = 0 additional POSTs |
| Dirty A → B → A | local draft for A survives |
| Cross-campaign switch | exact documentId; campaign metadata updates; graph lens params preserved |
| Ready Canvas chrome | title/status once in Surface Context; editor starts immediately |
| Build → Plan | DOCUMENT disappears; PREP appears; World Graph stays in nav |

Owning tests: controller (list, fencing, history, query preservation), context UI, create lifecycle, page integration replacing auto-create assertions. Retain Build authority/reconciliation and Agent Interaction proofs.

---

## Explicit non-goals

- Document rename or general metadata-edit UI
- Ingest into DOCUMENT (`BuildIngestToolbar`, extraction, graph publication)
- Ingest surface context redesign
- World Graph nav / graph reload changes (graph reload regression is merge-blocking)
- Teaching the host about Build document schemas or moving authority into AppChrome
- Build graph-node insertion, Statblock/Threat parity, Play context, Plan→Play, promotion, Agent continuity redesign
- Server registry changes unless an actual invariant gap is discovered

Rename/light metadata, graph insert, and shared tools remain successors (see Backlog READY *Build Plan-parity chrome*).

---

## Boundaries (preserve)

- **Agent Interaction:** publish only after MarkdownCanvas accepts record; switching keeps A until B admitted.
- **World Graph:** DOCUMENT campaign ≠ graph `campaigns`/`session`; switching documents must not independently reload graph.
- **MarkdownCanvas:** owns content, save, conflict/reconciliation UI; context bar survives load/error/conflict states for selected identity.

---

## Merge gate

Merge only if:

> **Opening Build is read-only with respect to document creation until the operator explicitly chooses New source; loading, switching, creation, history, Canvas authority, and Surface Context all converge on the same exact opaque `documentId`.**

And:

> **Build adopted the generic Surface Context host without teaching the host what a Build document is.**

---

## Likely implementation shape

```text
apps/live-control-ui/src/buildSurface/
  BuildSurfacePage.tsx          (simplify; remove auto-create)
  BuildSurfaceContext.tsx
  BuildDocumentSelector.tsx
  BuildDocumentCreateControl.tsx
  useBuildWorkspaceDocumentController.ts

apps/live-control-ui/src/markdownCanvas/MarkdownCanvas.tsx
  hideReadyHeader (or equivalent — ready-state header only)

Shared: surfaceInteraction/contextHost/, workspaceDocumentCreation.ts,
        workspaceDocumentNavigation.ts, MarkdownCanvasSessionProvider
```

Mirror Plan resolve-first patterns (`PlanSurfaceShell` / `loadPlanningDocument`) but Build-owned with snapshot preflight. Do not add new server endpoints.

---

## Successor

After merge, Build has World Graph context + exact loaded document context + authoring Canvas. Next polish: rename/metadata, graph-node insertion, shared tools/Statblock — and evidence for Play's multi-module context stack from two real adopters.

**Authority:** Full product brief in parent chat handoff (2026-08-10, §0–§38). Implementation plan: `.cursor/plans/build_document_context_b66a3e7e.plan.md`.
