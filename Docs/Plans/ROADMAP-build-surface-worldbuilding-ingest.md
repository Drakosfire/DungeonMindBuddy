---
document_id: dmb-roadmap-build-surface-worldbuilding-ingest
title: Build Surface and Worldbuilding Ingest Roadmap
document_class: roadmap
status: draft
version: 0.1
branch: docs/build-surface-worldbuilding-ingest
created_at: "2026-07-22"
last_updated_at: "2026-07-22"
---

# Build Surface and Worldbuilding Ingest Roadmap

- **Status:** Branch-local design draft; not yet adopted as `main` sequencing authority
- **Workstream:** Build / TipTap Markdown / heterogeneous source ingestion / World Supergraph
- **Branch:** `docs/build-surface-worldbuilding-ingest`
- **Execution design:** [`PLAN-build-surface-worldbuilding-ingest-pr-slices.md`](PLAN-build-surface-worldbuilding-ingest-pr-slices.md)
- **Architecture authority:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
- **Promotion bridge:** [`../Design/DESIGN-extract-promote-graph-review-bridge.md`](../Design/DESIGN-extract-promote-graph-review-bridge.md)

This document captures the proposed path from the current Plan/Ingest/TipTap
dogfood to a real Build surface that authors Markdown source artifacts and
launches reviewable worldbuilding extraction. It is deliberately branch-local:
it records a proposed workstream without changing the active Campaign
Supergraph tracker or claiming that heterogeneous ingestion is production-ready.

---

## 1. Goal

Build a reusable source-authoring and extraction workflow:

```text
Markdown source
  → TipTap editor
  → reviewed Source Artifact
  → extraction run
  → candidate graph
  → Graph Review
  → governed World Supergraph commit
```

The Build surface is the authoring and extraction-launch surface. Ingest and
Graph Review remain the correction and governed-publication surfaces.

The first useful worldbuilding target is the Shepherd’s Flock material:

1. cult overview;
2. one promoted meat-creature Markdown statblock;
3. one named NPC or faction-adjacent sheet;
4. review and commit through the existing graph publication boundary;
5. query the resulting world graph with no session focus.

The first target is a proving slice, not a promise to batch-ingest the entire
corpus.

---

## 2. Current state

### 2.1 What already exists

- `PlanSurfaceCanvas` already uses TipTap with StarterKit, callouts, references,
  local workspace state, Markdown export, graph chips, and Markdown save.
- `TiptapCalloutBridgeSpike` proves local drafts, import/export, block-boundary
  decoration, reference insertion, and two-phase Markdown file writes.
- `usePlanMarkdownSave` already wraps prepare → commit for a planning document.
- Graph Review has the governed extract-promote boundary:
  `preview_write` → `confirm_commit` → `GraphContribution` → immutable graph head.
- The World Supergraph architecture already models worldbuilding as a source
  domain in one world-owned graph. A world source may have no session focus.
- Mirathorn worldbuilding fixtures prove that source spans, provenance, and
  candidate-graph evaluation can exist without a session occurrence.
- `SurfaceMode` already includes `"build"` as a latent surface type, but there
  is no Build route, page, or primary navigation item yet.

### 2.2 What is still recap-shaped

The current live extraction path is not a generic source pipeline:

- `CategoryGraphExtractionOptions` requires both `session_id` and
  `session_number`.
- `graph_preview_runner.py` validates `session-N` identifiers and derives a
  numeric session from them.
- `recap_artifacts.py` is keyed by campaign/session/recap paths.
- `/api/live/graph-preview/*` is primarily a recap and latest-run read surface.
- The existing workspace registry only accepts `kind: "plan" | "runbook"`.
- The TipTap writer’s allowlist is limited to eval TipTap files and session prep
  Markdown.

These are adapters and contracts to generalize, not reasons to create a second
worldbuilding graph.

### 2.3 Markdown fidelity is a real gate

The current Markdown converter supports headings, paragraphs, lists, callouts,
and selected inline references. It warns on or flattens unsupported structures
such as tables, images, HTML, frontmatter, and horizontal rules.

Worldbuilding documents commonly contain exactly those structures. Build must
not silently round-trip a source document into a lossy replacement.

Build v0 therefore needs one explicit policy:

- preserve unsupported blocks losslessly;
- block commit until unsupported blocks are resolved; or
- restrict v0 to newly authored Markdown within the supported subset.

The recommended first slice is the third option, plus a visible diagnostic
when an imported source is outside the safe editing subset.

---

## 3. Product boundaries

### Plan — session preparation

Plan edits session-oriented planning documents, reads graph projections, and
uses the existing planning save adapter. It does not own graph extraction or
durable graph commits.

### Build — source authoring and extraction launch

Build owns:

- creating or opening a source document;
- editing Markdown;
- source metadata and authority classification;
- saving a reviewable source artifact;
- launching an extraction run;
- handing the run to Graph Review.

Build does not own identity resolution, contribution merge, or graph-head
advancement.

### Ingest / Graph Review — correction and publication

Ingest owns proposed-memory creation. Graph Review owns judging and committing
the proposal. The final Build action is therefore **Open in Graph Review**, not
**Promote directly**.

---

## 4. Shared architecture

### 4.1 Shared UI layers

Extract the current duplicated TipTap behavior into layers rather than one
large surface component:

```text
MarkdownEditorCore
  ├─ TipTap setup and common extensions
  ├─ local draft state
  ├─ import/export
  ├─ dirty and lock state
  └─ editor lifecycle callbacks

MarkdownEditorToolset
  ├─ common edit actions
  ├─ insert-block actions
  ├─ Markdown export/save actions
  └─ AppChromeTools projection

Surface adapters
  ├─ Plan: graph chips, session prep save, planning context
  ├─ Build: source metadata, source save, extract action
  └─ Ingest: source review, diagnostics, Graph Review handoff
```

The current Spike should become a consumer of the shared editor, not become the
shared editor itself. Its runbook-specific reference samples and block-boundary
rules stay in the runbook adapter.

### 4.2 Generic source artifact

The runtime contract should represent a source independently of whether it is a
recap:

```text
SourceArtifact
  world_id
  campaign_id: optional
  session_id: optional
  source_domain: recap | worldbuilding | prep | mechanical
  document_class: play | world | reference | planning | statblock
  artifact_kind
  source_uri / repo-relative path
  content_type
  content_sha256
  authority_state
  visibility_state
  temporal_scope
```

For an evergreen Shepherd’s Flock world document:

```text
world_id: eldyrwild
campaign_id: null
session_id: null
source_domain: worldbuilding
document_class: world
artifact_kind: worldbuilding_doc
```

The source artifact, span index, provenance index, candidate graph, validation
report, and run manifest should be one reviewable bundle. A downstream reviewer
should not have to reconstruct the source from unrelated sibling files.

### 4.3 Generic extraction controller

The production pipeline should be source-agnostic:

```text
SourceArtifact
  → source-span bundle
  → extraction profile
  → candidate graph
  → validation
  → reviewable run
  → Graph Review
```

Recap ingestion becomes a `RecapSourceAdapter`. Build worldbuilding ingestion
uses a `WorldbuildingSourceAdapter`. Both call the same runtime extraction and
promotion contracts.

The production service must not import an eval-only runner as its architecture.
Evals should call the runtime contract and retain their own fixtures, gold, and
scoring adapters.

---

## 5. Roadmap phases

### Phase 0 — Contract and design lock

Define the source artifact, authority, provenance, run, and safe Markdown
round-trip contracts. Record the explicit boundary between Build and Graph
Review.

**Exit gate:** an implementation agent can identify the source schema, the
editor reuse boundary, the run lifecycle, the publication owner, and the
worldbuilding pilot without reading chat history.

### Phase 1 — Shared TipTap Markdown editor

Extract the common editor core from `PlanSurfaceCanvas` and
`TiptapCalloutBridgeSpike`. Preserve current Plan and Spike behavior while
making surface-specific behavior injectable.

**Exit gate:** Plan and the Spike both use the shared component; existing
editor, Markdown conversion, and save tests remain green.

### Phase 2 — Safe source-document persistence

Generalize workspace document metadata beyond plan/runbook where appropriate,
or introduce a separate source-document registry. Extend the writer allowlist
only through an explicit source-domain policy. Add revision and backup safety
for worldbuilding paths.

**Exit gate:** a source document can be created, edited, prepared, reviewed,
committed, and reopened without silently changing unsupported Markdown.

### Phase 3 — Generic source-artifact and extraction run

Separate source artifact identity from recap session identity. Generalize
source-span generation, provenance, run manifests, status, and catalog queries.
Keep recap behavior byte-compatible through an adapter.

**Exit gate:** a worldbuilding source with `session_id = null` can produce a
validated, reviewable candidate run without inventing a session.

### Phase 4 — Build surface v0

Add `/build`, a quiet editor-first surface with a toolbar for:

- new/open source;
- source metadata;
- save draft;
- prepare/commit Markdown;
- extract candidate;
- open Graph Review.

Keep Build off the primary nav until it has the Phase 3 source/run path. Once
the v0 loop is useful, add Build as a deliberate sixth product surface rather
than hiding authoring under Ingest.

**Exit gate:** the operator can author a worldbuilding Markdown source and
launch a reviewable run from Build without direct filesystem access.

### Phase 5 — Worldbuilding extraction profile

Start with location, faction, NPC, creature/statblock-reference, and
institution/governance coverage. Keep ecology/resource extraction as an
explicit later profile because the existing ablation work shows it can cause
species/product explosion.

**Exit gate:** the Mirathorn or Shepherd’s Flock proving source produces
source-anchored candidates with correct authority and no session chronology
invented by the extractor.

### Phase 6 — Graph Review handoff and publication

Make generic runs first-class inputs to the existing Graph Review workbench.
The workbench should show source spans, evidence, candidate assertions, and
the same prepare/review/confirm flow for recap and worldbuilding runs.

**Exit gate:** a worldbuilding candidate can be reviewed, selectively prepared,
confirmed, committed to the World Supergraph, and queried at world focus.

### Phase 7 — PDF/OCR and Shepherd’s Flock pilot

Treat PDFs as source artifacts with an extraction lineage:

```text
PDF
  → validated OCR/Markdown artifact
  → human review
  → statblock source
  → mechanical extraction profile
  → Graph Review
```

Do not make raw PDF editing a Build v0 requirement. Reuse the existing
RulesIngestion Mark III artifacts, deduplicate the Shepherd’s Flock and
Mirathorn/Sewers copies, then pilot the cult overview, one meat creature, and
one named NPC.

**Exit gate:** the pilot has stable PDF/page provenance, validated Markdown
representation, reviewable graph candidates, and no duplicate source copies
creating duplicate durable identities.

---

## 6. Explicit non-goals

- Direct one-click Build → World Graph publication.
- A second graph for worldbuilding.
- Automatic promotion of every Markdown paragraph into canon.
- Raw PDF editing inside TipTap.
- Full Markdown/WYSIWYG parity in the first editor extraction.
- Ecology/resource taxonomy in the first generic profile.
- Replacing Graph Review with a Build-specific review cockpit.
- Moving the active Campaign Supergraph tracker as part of this branch-local
  design.

---

## 7. Falsification and quality gates

The roadmap is not successful merely because the UI renders.

Required evidence:

1. Plan and Spike preserve existing editor behavior after extraction.
2. Unsupported Markdown is surfaced and cannot be silently lost.
3. A source with no session produces no fabricated session ID or chronology.
4. Source spans and provenance resolve from candidate assertions.
5. Recap runs remain behaviorally compatible through their adapter.
6. Worldbuilding candidates preserve authority and visibility metadata.
7. Graph Review, not Build, owns confirmation and graph-head advancement.
8. Shepherd’s Flock pilot queries work with world focus and `session_id = null`.
9. PDF-derived candidates retain PDF/page/OCR lineage.

The phase-by-phase execution slices and their verification commands are defined
in [`PLAN-build-surface-worldbuilding-ingest-pr-slices.md`](PLAN-build-surface-worldbuilding-ingest-pr-slices.md).
