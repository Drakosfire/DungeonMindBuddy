---
document_id: dmb-plan-shared-markdown-canvas-build-first
title: Shared Markdown Canvas — Build-First Execution Plan
document_class: implementation_plan
status: active
version: 1.0
created_at: "2026-07-26"
design: ../Design/DESIGN-shared-markdown-canvas-surface-composition.md
surface_authority: ../Design/ARCHITECTURE-plan-surface-toolbox.md
first_consumer: /build
---

# Shared Markdown Canvas — Build-First Execution Plan

## Status

**ACTIVE.** The prior BLD-00–BLD-10 foundation established source authoring,
extraction, review, and worldbuilding publication. This plan begins the componentization
phase: Build becomes the first consumer of a reusable document-bound Markdown canvas.

The sequence is deliberately narrow:

```text
MC-01 Build-first Markdown canvas session
  → MC-02 surface capability composition
      → MC-03 node authoring design gate
```

Only MC-01 is executable now.

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

This plan is now the sequencing authority for shared canvas/component work. It does
not replace:

- BLD-09 PDF/OCR;
- BLD-10c worldbuilding review UX;
- Agent Interaction R10;
- graph projection or Kernel architecture.

## Current product state

| Area | Current state | Next correction |
|---|---|---|
| Build editor | Direct `useWorkspaceDocumentAuthoring` + `MarkdownEditorCore` in `BuildSurfaceShell` | Render through shared canvas session/view |
| Build extraction | Sibling toolbar independently reloads snapshot and reads local draft | Consume `committed_clean` canvas envelope |
| Build operation races | Launch/refresh generations live in `useBuildExtraction` | Canvas command host owns document-bound arbitration; plugin keeps run-domain state |
| Plan Edit | Built inside `PlanSurfaceCanvas` and forwarded to AppChrome | Leave unchanged in MC-01; compose in MC-02 |
| Surface config | Build has constants but no real capability config; context type is Plan-shaped | Generalize in MC-02 |
| Node authoring | Owned by Graph Review Author Draft paths | Design gate before any shared capability |

## Slice table

| Slice | Status | Mission | Must remain false |
|---|---|---|---|
| MC-01 | **PREPARED for implementation after this docs PR merges** | Shared canvas session/view + Build migration + admitted extraction envelope | Plan migration, common capability catalog, node authoring, BLD-10c |
| MC-02 | QUEUED | Shared surface capability catalog/composer for Edit and Tools; real Build config | Node-authoring behavior, R10 relocation |
| MC-03 | DESIGN GATE | Decide and then migrate one graph node-authoring capability | Canvas-owned graph writes, Build-local copy |

## MC-01 — Build-first Markdown canvas session

### Outcome

A Build workspace document is opened, edited, saved, recovered, and consumed by
extraction through one shared canvas authority. The extraction tool no longer reloads
workspace snapshots or reads canvas local storage to decide whether it may launch.

### Merge-ready invariant

For one selected Build workspace-document UUID, the rendered editor, local draft,
authoritative snapshot, commit receipt, Agent Interaction context, and any
document-consuming command identify the same document and revision/digest authority.
Extraction can launch only from a `committed_clean` envelope produced by that authority.
Document changes invalidate pending document commands, and no canvas module knows what
an ExtractionRun is.

### Handoff

[`HANDOFF-pr425-build-first-markdown-canvas.md`](HANDOFF-pr425-build-first-markdown-canvas.md)

### Acceptance summary

- Build create/open/edit/save/conflict/recovery behavior is unchanged.
- Build extraction receives exact document ID, revision, and content digest from the
  canvas.
- `useBuildExtraction` no longer calls `getWorkspaceDocumentSnapshot` or
  `readWorkspaceDocumentLocalState`.
- Both launch→refresh and refresh→launch orderings retain current exact-run behavior.
- Document A completions cannot affect document B.
- Plan files and behavior are untouched.
- Source guards prove generic canvas modules import no Build/extraction/Graph Review
  types.

## MC-02 — Surface capability composition

### Outcome

Build and later Plan declare capabilities rather than assembling chrome ad hoc.

### Required design work

- Define capability IDs and typed params.
- Produce region contributions for AppChrome Edit and existing adaptive Tools.
- Generalize `SurfaceConfig` context away from a mandatory Plan descriptor.
- Establish shared baseline Markdown actions and explicit surface extensions.
- Give Build a real config consumed by its shell.

### Gate

Do not dispatch until MC-01 proves:

- the canvas API is not Build-shaped;
- admitted envelopes are sufficient for extraction;
- command arbitration survives Build races;
- Plan did not need to move to make the primitive viable.

## MC-03 — Node authoring design gate

### Outcome

Not yet selected. The gate must decide the reusable capability before code.

### Required inventory

- Graph Review Author Draft host and selection ownership;
- create/bind/merge/commit boundaries;
- source span and evidence authority;
- Build's permitted authoring mode;
- Plan's permitted selected-object behavior.

### Hard boundary

No node-authoring implementation may begin by copying Graph Review code into
`buildSurface/` or by giving `MarkdownCanvas` graph-write knowledge.

## Independent successors

- **BLD-10c:** exact-run/worldbuilding dispositions and prepare/confirm UX, consuming
  the shell once appropriate.
- **BLD-09:** PDF/OCR source lineage; independent.
- **R10:** move the one adaptive projection host into Agent Interaction.
- **Plan/runbook canvas migration:** only after MC-01, and likely after MC-02.
