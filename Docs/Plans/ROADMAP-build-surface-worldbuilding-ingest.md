---
document_id: dmb-roadmap-build-surface-worldbuilding-ingest
title: Build Surface and Worldbuilding Ingest Roadmap
document_class: roadmap
status: proposed
version: 0.2
branch: docs/build-surface-worldbuilding-ingest
created_at: "2026-07-22"
last_updated_at: "2026-07-22"
---

# Build Surface and Worldbuilding Ingest Roadmap

- **Status:** Proposed for adoption by PR 382; not implementation sequencing authority until the post-merge tracker sync is complete.
- **Workstream:** Build / TipTap Markdown / heterogeneous source ingestion / World Supergraph
- **Execution design:** [`PLAN-build-surface-worldbuilding-ingest-pr-slices.md`](PLAN-build-surface-worldbuilding-ingest-pr-slices.md)
- **Architecture authority:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
- **Surface authority:** [`../Design/ARCHITECTURE-plan-surface-toolbox.md`](../Design/ARCHITECTURE-plan-surface-toolbox.md)
- **Workspace identity contract:** [`../Design/CONTRACT-workspace-document-identity-v1.md`](../Design/CONTRACT-workspace-document-identity-v1.md)
- **Publication bridge:** [`../Design/DESIGN-extract-promote-graph-review-bridge.md`](../Design/DESIGN-extract-promote-graph-review-bridge.md)

This roadmap proposes the path from the current Plan/Ingest/TipTap dogfood to a
Build surface that authors Markdown source documents and launches reviewable
worldbuilding extraction. Merging this document adopts the design decisions
below; it does not by itself activate any implementation handoff. The Campaign
Supergraph tracker must be updated atomically after merge before BLD-01 becomes
ACTIVE.

---

## 1. Goal

Build a reusable source-authoring and extraction workflow:

```text
Mutable workspace document
  → reviewed committed source revision
  → immutable SourceArtifact evidence identity
  → ExtractionRun
  → candidate graph
  → Graph Review
  → governed World Supergraph commit
```

The Build surface is the authoring and extraction-launch surface. Ingest and
Graph Review remain the correction and governed-publication surfaces.

The first proving target is bounded Shepherd’s Flock material:

1. one cult overview source;
2. one promoted meat-creature or statblock-reference source;
3. one named NPC or faction-adjacent source;
4. review and commit through the existing Graph Review publication boundary;
5. query the resulting World Supergraph with no session focus.

This is a proving slice, not a promise to batch-ingest the corpus.

---

## 2. Locked design decisions

### 2.1 Build document identity and graph evidence identity are separate

Build authors a mutable `WorkspaceDocument` using the existing opaque,
server-issued UUID identity model. BLD-02 may extend the workspace discriminator
with an explicit `worldbuilding_source` kind and typed metadata, but it must not
reuse ingestion/evidence IDs or infer identity from title/path.

A committed workspace revision may then produce a distinct immutable
`SourceArtifact` evidence identity. The relationship is explicit:

```text
WorkspaceDocument
  document_id
  revision
  target_relpath
  mutable metadata and draft lifecycle

SourceArtifact
  source_artifact_id
  workspace_document_id
  workspace_document_revision
  content_sha256
  source-domain authority and visibility
  immutable source lineage
```

The source artifact ID is never the workspace document ID. No join may be
performed by rewriting strings, parsing paths, or matching display labels.

### 2.2 Existing graph-memory contracts are evolved, not shadowed

The repository already has source-artifact, source-span, evidence, and graph
run contracts. The Build workstream must graduate or adapt those authorities:

- `src/graph_memory/evidence/source_artifact.py`
- `src/graph_memory/source_span.py`
- `src/graph_memory/ingestion/graph_ingest_run.py`
- existing evidence and contribution contracts under `src/graph_memory`

BLD-03 must not create parallel top-level `source_artifact.py`,
`source_spans.py`, or `provenance.py` authorities. A new canonical
`ExtractionRun` contract is permitted only when the existing recap-shaped
manifest becomes an explicit compatibility adapter or migration seam in the
same slice.

### 2.3 Build is the second configured Surface, not a second shell architecture

Build must reuse the shared Surface architecture and AppChrome composition:

- one `SurfaceConfig` abstraction;
- one app-scoped projection registry and adaptive container;
- one edit capability and two-phase writer path;
- one theme/token system;
- one Agent Interaction continuity host.

`BuildSurfacePage` may supply Build-specific configuration and adapters.
Build must consume the shared workspace-document authoring seam (BLD-05a:
snapshot read, local-state v3, authoring state machine). It must not invent a
parallel shell, local-draft schema, or content-read path. The live-control
module `SurfaceShell` is not that authoring seam.

### 2.4 Extraction profiles own executable extraction policy explicitly

The generic extraction runtime accepts a versioned extraction profile. A
profile owns or references:

- enabled extraction passes and category bounds;
- pass instructions/prompt templates;
- structured-output schema IDs and versions;
- vocabulary/context policies;
- source-domain defaults;
- post-extraction validation rules.

BLD-04 creates the profile protocol and extracts the current recap behavior into
an explicit recap profile without changing semantics. BLD-08 adds the bounded
worldbuilding profile. Prompt behavior must not remain hidden as unversioned
constants inside a supposedly generic runtime.

### 2.5 Build launches proposals; Graph Review publishes

Build can save a source revision, prepare a SourceArtifact, launch extraction,
show exact run state, and open that exact run in Graph Review. Build cannot
prepare or confirm a graph contribution.

Graph Review continues to use the existing governed publication implementation:

- shared Kernel ops: `src/graph_memory/extract_promote_ops.py`;
- HTTP boundary: `apps/live_control_server/routes/extract_promote.py`;
- explicit proposal-bound confirmation;
- immutable graph-head advancement and exact revision reload.

No application-local duplicate of `extract_promote_ops.py` may be created.

---

## 3. Current state

### 3.1 Existing useful seams

- `PlanSurfaceCanvas` uses TipTap with local workspace state, Markdown export,
  graph chips, and Markdown save.
- `TiptapCalloutBridgeSpike` proves import/export, block-boundary decoration,
  reference insertion, local drafts, and two-phase Markdown writes.
- Workspace documents use opaque server-issued UUIDs and registry-owned target
  paths.
- Graph Review has the governed `preview_write` / `confirm_commit` boundary that
  creates `GraphContribution` records and advances an immutable graph head.
- Worldbuilding is already a source domain in one world-owned graph; it does not
  require a session occurrence.
- `SurfaceMode` already includes `build`, but there is no Build route or product
  surface.

### 3.2 Recap-shaped seams that require graduation

- category extraction options require campaign/session fields;
- graph preview runners and manifests are recap/session oriented;
- current run loading often depends on preview/latest-run conventions;
- current workspace kinds are `plan | runbook`;
- the TipTap writer allowlist excludes approved worldbuilding source roots;
- extraction prompts and category instructions are embedded in recap runtime
  code rather than selected through a versioned profile.

These are contracts to graduate, not reasons to create a second graph, second
source vocabulary, or Build-specific publication path.

### 3.3 Markdown fidelity remains a gate

The converter supports a bounded subset and may warn on or flatten tables,
images, HTML, frontmatter, and horizontal rules. Build v0 therefore supports
newly authored Markdown within the proven subset and visibly blocks unsafe or
lossy commit. Full Markdown parity is a successor capability.

---

## 4. Product boundaries

### Plan — session preparation

Plan edits session-oriented planning documents and consumes graph projections.
It does not own extraction or graph-head advancement.

### Build — source authoring and extraction launch

Build owns:

- creating/opening a worldbuilding workspace document;
- editing supported Markdown;
- source metadata and authority classification;
- committing a reviewable source revision;
- producing an immutable SourceArtifact from that revision;
- launching an exact ExtractionRun;
- handing the run to Graph Review.

Build does not own identity resolution, contribution merge, or graph-head
advancement.

### Ingest / Graph Review — correction and publication

Ingest creates proposed memory. Graph Review judges candidate assertions and
commits selected contributions. The terminal Build action is **Open in Graph
Review**, never **Promote directly**.

---

## 5. Roadmap phases

### Phase 0 — Adopt contracts and sequencing

Adopt this roadmap and slice plan, then update the active tracker atomically.
Resolve the workspace-document → SourceArtifact identity boundary, established
contract paths, Surface reuse obligation, profile ownership, and publication
owner before dispatch.

**Exit gate:** BLD-01 may be PREPARED as a stacked draft PR against this docs
head; it becomes ACTIVE/MERGEABLE only after BLD-00 merge, tracker adoption,
rebase, and immutable merge-SHA anchoring. Later slices may be PREPARED against
predecessor heads while remaining draft.

### Phase 1 — Shared TipTap Markdown editor

Extract common editor lifecycle and Markdown conversion behavior while Plan and
the Spike retain their surface-specific adapters.

**Exit gate:** both consumers use one shared editor; current behavior and tests
remain green.

### Phase 2 — Safe worldbuilding workspace persistence

Extend the workspace document contract explicitly for
`worldbuilding_source`, add typed metadata and server-owned safe target policy,
and preserve revision, backup, root-containment, and two-phase write behavior.

**Exit gate:** a Build source can be created, committed, reopened, and rejected
safely when stale, unsafe, or lossy.

### Phase 3A — Canonical source and run contracts

Graduate existing evidence/source-span contracts and introduce a canonical
source-domain-neutral ExtractionRun contract with an explicit recap manifest
adapter.

**Exit gate:** a worldbuilding source revision with `session_id = null` has a
stable SourceArtifact, resolvable spans, and durable exact run identity without
parallel authorities.

### Phase 3B — Generic extraction runtime and profiles

Introduce source adapters and the extraction-profile protocol. Preserve current
recap behavior through a versioned recap profile; permit a sessionless
worldbuilding source to run without category tuning.

**Exit gate:** recap and worldbuilding fixture runs use the same runtime,
failures are explicit, and every reviewable candidate resolves to evidence.

### Phase 4 — Build surface v0

Add `/build` as a configured shared Surface with editor-first composition,
metadata, save/reopen, and exact document identity. Add primary navigation only
when the source-authoring loop is functional.

**Exit gate:** the operator can author and reopen a worldbuilding source through
the product UI without direct filesystem access.

### Phase 5 — Build extraction controls

Bind extraction to a committed source revision, launch and recover an exact run,
and open that run in Graph Review. No latest-run fallback is permitted.

**Exit gate:** refresh/retry preserves exact run identity and Build contains no
publication action.

### Phase 6 — Generic Graph Review run loading

Adapt Graph Review’s selected-run binding and the existing Kernel publication
path to source-domain-neutral runs. Do not create a new promotion service.

**Exit gate:** a worldbuilding run can be reviewed, selectively confirmed,
committed, and reloaded at the exact graph revision without a fake session lens.

### Phase 7 — Bounded worldbuilding profile and pilot

Add a versioned worldbuilding profile covering bounded locations, factions,
NPCs, creatures/statblock references, and institutions/governance. Run repeated
Shepherd’s Flock trials and publish only manually accepted candidates.

**Exit gate:** candidates retain evidence, session remains null, incidental
ecology does not explode, and aggregate evidence is recorded without raw
payload disclosure.

### Phase 8 — PDF/OCR lineage pilot

Treat a PDF and its validated OCR/Markdown derivation as separate linked source
artifacts. Preserve PDF/page/region lineage through extraction and Graph Review.

**Exit gate:** page evidence survives reload, validation failures block review,
and duplicate copies do not silently create duplicate durable identities.

---

## 6. Explicit non-goals

- Direct Build → World Graph publication.
- A second graph for worldbuilding.
- Reusing workspace document IDs as evidence SourceArtifact IDs.
- Parallel source-artifact, span, provenance, run, or promotion authorities.
- Automatic promotion of Markdown paragraphs into canon.
- Raw PDF editing inside TipTap.
- Full Markdown/WYSIWYG parity in Build v0.
- Ecology/resource taxonomy in the first profile.
- Replacing Graph Review with a Build-specific review cockpit.
- Activating all handoffs merely because this documentation PR merges.

---

## 7. Adoption and dispatch protocol

PR 382 is the design-adoption PR. Stacked implementation work is allowed before
predecessors merge, but merge authority remains gated.

### PREPARED / DRAFT

A slice may be implemented as a **stacked draft PR** against the current
predecessor head (or an unmerged predecessor PR tip). PREPARED work may include
code, tests, and review comments. It is **not** mergeable.

### ACTIVE / MERGEABLE

A slice becomes ACTIVE/MERGEABLE only after:

1. its predecessor is merged;
2. the active tracker records adoption / the predecessor merge SHA;
3. the implementation branch is rebased onto that immutable merge SHA;
4. the handoff is re-anchored to that base.

After PR 382 merges:

1. add the BLD sequence to the active Campaign Supergraph tracker or an approved
   sibling tracker;
2. record PR 382’s merge SHA as the BLD-00 base;
3. promote BLD-01 from PREPARED/DRAFT to ACTIVE/MERGEABLE once rebased onto that
   SHA; leave later slices PREPARED/DRAFT until their own predecessor gates clear;
4. assign actual PR numbers when implementation PRs open (draft PRs may already
   exist under PREPARED);
5. after each accepted implementation PR, atomically sync tracker, handoff
   status/archive, and next base SHA.

No implementation PR may be marked ready to merge while still PREPARED/DRAFT or
while based on an unmerged predecessor tip.

---

## 8. Falsification and quality gates

The roadmap is not successful merely because `/build` renders.

Required evidence:

1. Plan and the Spike preserve behavior after editor extraction.
2. Workspace document and SourceArtifact identities remain distinct and linked
   explicitly.
3. Unsupported Markdown is visible and cannot be silently lost.
4. Existing evidence/source-span/run authorities are evolved rather than
   shadowed.
5. A sessionless source produces no fabricated session ID or chronology.
6. Every candidate assertion resolves to source evidence.
7. Recap behavior remains compatible through explicit adapters/profiles.
8. Build is a configured shared Surface, not a parallel shell architecture.
9. Graph Review alone owns prepare/confirm and graph-head advancement.
10. Worldbuilding profile behavior is versioned, bounded, and repeat-tested.
11. PDF-derived candidates retain original PDF/page/OCR lineage.
