# Graph Document Audit — Campaign Supergraph Reset

**Date:** 2026-07-10
**Updated:** 2026-08-12 (development-process reference re-anchored from Jumpstart to Steward Cycle)
**Status:** Active audit record for Phase 0 (+ PR005A source reanchor; PR005B contract; design-agent source bridge)
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
**PR tracker:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)
**Design-agent source index:** [`Docs/Design/INDEX-design-agent-source-set.md`](../Design/INDEX-design-agent-source-set.md)

## Purpose

Classify graph-related documentation under `Docs/` so contributors know what can **direct new work**, what is **implementation context only**, and what is **historical**.

**Rule:** For Campaign Supergraph sequencing, [`PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) is the **only** active implementation sequence. A fresh agent must not pick an older handoff and resume the superseded architecture.

**PR005A / PR005B note:** Tracker slice **PR005A (Context Audit + Source Reanchor)** enforces the Project Sources / local-doc boundary. **PR005B** defines the agent-tool and authored-prep contract in [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](../Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md). Steward process references and Project Sources cannot invent a competing sequence.

## Action legend

| Action | Meaning |
|---|---|
| **ACTIVE AUTHORITY** | May direct new work. Conflicts with these docs are bugs. |
| **ACTIVE REFERENCE** | Current implementation context (product checkpoint, contract, paused trail). Useful, but **cannot override** architecture or PR tracker. |
| **KEEP** / **KEEP_CONTRACT** | Reusable contract/research still in force; not a roadmap. |
| **SOURCE_ANCHOR** | Path/index grounding; regenerate rather than invent sequencing. |
| **RESEARCH_ONLY** | Useful patterns; cannot direct implementation sequence. |
| **PROPOSAL** | Draft / not yet accepted; cannot direct work until promoted into authority docs. |
| **HISTORICAL EVIDENCE** | Remains readable; cannot direct work. Prefer banners over silent authority. |
| **SUPERSEDED** | Replaced; stub or banner points at replacement. |
| **ARCHIVED** | Under an archive tree (or moved in this reset). |
| **DELETE** | Removed as duplicate/obsolete with no unique historical value. |

## Project Sources and local handoff boundary

```text
Project Sources are user-managed context inputs.
They are not the GitHub repository.
They are not automatically current.
Prepared replacement files are not active Project Sources until the operator uploads them.
When Project Sources conflict with GitHub, GitHub wins.
Historical / research / proposal docs cannot direct implementation.
```

Current steward process reference: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). It may govern how a slice is selected/dispatched/reviewed, but if any process reference and the tracker disagree on Campaign Supergraph sequence, **the tracker wins**.

Legacy [`Docs/Plans/JUMPSTART-docs-relevance-first.md`](../Plans/JUMPSTART-docs-relevance-first.md) is a superseded forwarding stub retained for old links only.

Curated design-agent source bridge: [`Docs/Design/INDEX-design-agent-source-set.md`](../Design/INDEX-design-agent-source-set.md). Prefer that INDEX when choosing which repository paths to attach as Project Sources.

### Local / Project Source classification (when present)

These names often appear as Project Sources or local drafts. Classification below is normative for agents even when the file is not (yet) in the GitHub tree:

| Document / name | Classification | Notes |
|---|---|---|
| `Docs/Design/INDEX-design-agent-source-set.md` | **ACTIVE_REFERENCE** / process index | Curated design-agent source bridge; not architecture/roadmap authority |
| `Docs/Process/STEWARD-CYCLE.md` | **ACTIVE_REFERENCE** / process reference | Canonical steward design/decomposition/parallel-lane/review/re-anchor process; cannot invent graph sequence |
| `PROJECT-SOURCES-OPERATING-TEMPLATE.md` | **SOURCE_ONLY** when absent; process intent covered by Steward Cycle + INDEX | Not found in tree as of 2026-08-02; do not recreate blindly |
| `PROPOSAL-context-audit-source-reanchor.md` | **SOURCE_ONLY** / **PROPOSAL** | Not found in tree as of 2026-08-02; proposal-only if attached |
| `source-reconciliation-report(2).md` | **SOURCE_ONLY** | Not found in tree as of 2026-08-02; local/operator report only |
| `LLM-graph-construction.md` | **SOURCE_ONLY** / **RESEARCH_ONLY** | Not found in tree as of 2026-08-02; extraction/eval patterns only |
| `TEMPLATE-pr-handoff(1).md` | **SOURCE_ONLY**; use checked-in HANDOFF template | Map to `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` |
| `Docs/Design/dungeonbuddy_spec_architecture_v0_2.md` | **SUPERSEDED** / **HISTORICAL** | Banner required; conceptual ancestor only |
| `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | **SUPERSEDED** | Stub points at Campaign Supergraph authority |
| `Docs/Archive/Architecture/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` (archived full copy) | **HISTORICAL** | Full historical copy; cannot direct work |
| `Docs/Anchors/CORPUS-ANCHOR.md` | **SOURCE_ANCHOR** / **KEEP_CONTRACT** | Corpus path grounding |
| `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` | **ACTIVE_REFERENCE** | Plan composition; not Campaign Supergraph sequencing; UI chrome → surface-interaction architecture |
| `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` | **ACTIVE AUTHORITY** (UI shell) | Shared bars / projection hosts; does not sequence graph PRs |
| `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` | **ACTIVE_REFERENCE** | Layout note; sequencing lives in tracker |
| `Docs/Plans/JUMPSTART-docs-relevance-first.md` | **SUPERSEDED** process stub | Historical links forward to `Docs/Process/STEWARD-CYCLE.md`; do not use as active process authority |

### 2026-08-02 design-agent Sources snapshot

**Base:** `917b9d5dff3985b3664aa274eafad7eacb776658` (`origin/main` at audit time)
**Evidence:** design-agent Sources pane filenames (screenshot inventory); content not available for every basename under the DungeonOverMind tree.
**Result:** reconciled into [`Docs/Design/INDEX-design-agent-source-set.md`](../Design/INDEX-design-agent-source-set.md).

| Project Source basename | Result |
|---|---|
| `GRAPH-MEMORY-PROJECT-LAYOUT.md` | MATCH → Design layout note (**ACTIVE_REFERENCE**) |
| `ARCHITECTURE-plan-surface-toolbox.md` | MATCH → Plan composition (**ACTIVE_REFERENCE**) |
| `GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | MATCH → Design stub (**SUPERSEDED**) |
| `dungeonbuddy_spec_architecture_v0_2.md` | MATCH → Design historical (**SUPERSEDED**) |
| `CORPUS-ANCHOR.md` | MATCH → Anchors (**SOURCE_ANCHOR**) |
| `README.md` | MATCH → repository root `README.md` (**ACTIVE_REFERENCE**) | Product overview only; not architecture or sequencing authority |
| `archived-full-GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | SOURCE_ONLY name; Archive body is HISTORICAL counterpart |
| `TEMPLATE-pr-handoff(1).md` | SOURCE_ONLY; map to checked-in `HANDOFF.template.md` |
| `PROPOSAL-context-audit-source-reanchor.md` | SOURCE_ONLY / PROPOSAL — not in tree |
| `source-reconciliation-report(2).md` | SOURCE_ONLY — not in tree |
| `LLM-graph-construction.md` | SOURCE_ONLY / RESEARCH_ONLY — not in tree |
| `PROJECT-SOURCES-OPERATING-TEMPLATE.md` | SOURCE_ONLY — not in tree; Steward Cycle + INDEX cover process |

**Unresolved source-only basenames (do not invent content):**
`PROPOSAL-context-audit-source-reanchor.md`, `source-reconciliation-report(2).md`, `LLM-graph-construction.md`, `PROJECT-SOURCES-OPERATING-TEMPLATE.md`, `TEMPLATE-pr-handoff(1).md`, `archived-full-GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`.

**Operator action after merge:** refresh Project Sources from the INDEX compact active set; demote superseded/historical attachments; leave unresolved local drafts out unless explicitly needed as research/proposal context.

---

## Replacement set (Phase 0) — ACTIVE AUTHORITY

| New document | Role |
|---|---|
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Canonical architecture |
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Canonical roadmap |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Sole Campaign Supergraph implementation sequence |
| `Docs/Reports/graph-document-audit.md` | This audit (governance of docs, not runtime) |
| `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` | Shared UI chrome / interaction-host ownership (not graph sequencing) |

## Archive conventions

| Location | Use |
|---|---|
| `Docs/Archive/Architecture/` | Architecture docs superseded by the Campaign Supergraph reset (2026-07-10) |
| `Docs/Design/archive/YYYY-MM-DD/…` | Earlier design cleanups (e.g. 2026-06-28 preview-graph era) |
| `Docs/Reports/archive/YYYY-MM-DD/…` | Historical reports / gate proofs |
| `Docs/Plans/archive/YYYY-MM-DD/…` | Completed handoffs |
| `Docs/Archive/graph-review-a10/` | Index for A10 authored-memory trail |

---

## A. Physically archived in this reset (`Docs/Archive/Architecture/`)

| Document | Former path | Action | Reason | Replacement |
|---|---|---|---|---|
| Supergraph architecture roadmap v0 | `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | **ARCHIVED** | Replaced as architecture/roadmap authority | Architecture + Roadmap + Tracker |
| Union supergraph projection design v0 | `Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md` | **ARCHIVED** | Architecture superseded; lessons absorbed | Architecture |
| Graph memory workstream anchor | `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md` | **ARCHIVED** | Operational authority → tracker | Tracker |
| Graph retrieval thesis anchor | `Docs/Design/ANCHOR-dungeonBuddy-graph-retrieval.md` | **ARCHIVED** | Lessons kept; not execution authority | Architecture |
| Plan graph-memory re-anchor (post-PR314) | `Docs/Design/DESIGN-plan-graph-memory-reanchor-after-dogfood-2026-07.md` | **ARCHIVED** | Consumption rules folded into architecture | Architecture |
| Contextual vocabulary roadmap checklist | `Docs/Design/GRAPH-MEMORY-CONTEXTUAL-VOCABULARY-ROADMAP.md` | **ARCHIVED** | Checklist roadmaps → PR tracker | Tracker |
| Live extractor prompt harness | `Docs/Design/GRAPH-MEMORY-LIVE-EXTRACTOR-PROMPT-HARNESS.md` | **ARCHIVED** | Experimental harness | — |
| Live recap ingest run bundle | `Docs/Design/GRAPH-MEMORY-LIVE-RECAP-INGEST-RUN-BUNDLE.md` | **ARCHIVED** | Eval seam | — |

Stub pointers remain at former paths.

---

## B. Deleted in this reset

| Document | Action | Reason | Replacement |
|---|---|---|---|
| `Docs/Design/GRAPH-MEMORY-SESSION-24-MANUAL-PROJECTION-DOGFOOD.md` (body) | **DELETE** | Duplicate of archived copy | `Docs/Design/archive/2026-06-28/graph-memory/…` (stub at old path) |

---

## C. KEEP — reusable contracts / research

| Document | Purpose | Action | Reason |
|---|---|---|---|
| `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md` | SourceArtifact→Anchor→Unit | **KEEP** | Surface vocabulary still in force |
| `Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md` | Agent tool capabilities + authored-prep lifecycle | **KEEP_CONTRACT** / ACTIVE DESIGN CONTRACT | Normative for PR011; not sequencing authority; not PR006 materialization |
| `Docs/Design/GRAPH-MEMORY-SOURCE-SPAN-EVIDENCE-RESOLVER.md` | Source-span evidence | **KEEP** | Evidence contract |
| `Docs/Design/GRAPH-MEMORY-CANDIDATE-GRAPH-PREVIEW-IR.md` | Candidate IR | **KEEP** | Extraction IR (candidates ≠ durable store) |
| `Docs/Design/GRAPH-MEMORY-MULTI-PASS-EXTRACTION-CONTRACT.md` | Multi-pass extraction | **KEEP** | Write-path design contract |
| `Docs/Design/GRAPH-MEMORY-LIVE-EXTRACTOR-OUTPUT-RECONCILIATION.md` | Live envelope reconciliation | **KEEP** | Extraction bridge contract |
| `Docs/Design/GRAPH-MEMORY-ENCOUNTER-JOB-TAXONOMY-DECISION.md` | Encounter/job taxonomy | **KEEP** | Accepted taxonomy decision |
| `Docs/Design/DESIGN-contextual-vocabulary-layer.md` | Vocabulary layer | **KEEP** | Identity/vocab direction |
| `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` | Plan toolbox | **ACTIVE REFERENCE** / **KEEP** | Surface architecture; not graph ownership or sequencing |
| `Docs/Design/ANCHOR-hermes-campaign-sensemaking-goal.md` | Hermes product goal | **ACTIVE PROPOSED** | Reset goal anchor; reconcile at Phase 1 |
| `Docs/Design/INDEX-hermes-campaign-authoring-foundation.md` | Hermes active document set | **ACTIVE PROPOSED** | Current Hermes design index |
| `Docs/Design/ANCHOR-agent-interaction-hermes.md` | Superseded agent boundary | **ARCHIVED STUB** | Historical source is under the 2026-07-15 Hermes reset archive |
| `Docs/Design/RESEARCH-graph-visualization-exploration.md` | Viz research | **RESEARCH_ONLY** / **KEEP** | Research only |
| `Docs/Reports/GRAPH-MEMORY-CROSS-CLASS-BLOCKED-DIAGNOSTICS.md` | Collision diagnostics | **KEEP** | Identity-safety evidence |
| `Docs/Reports/archive/2026-06-28/graph-memory/GRAPH-MEMORY-SHARED-SOURCE-VOCABULARY-CONTRACT.md` | Full vocab contract copy | **KEEP** | Prefer Design CONTRACT as canonical |
| `Docs/Reports/archive/2026-06-28/graph-memory/GRAPH-MEMORY-SURFACE-VOCABULARY-BOUNDARY.md` | Surface vs graph vocab | **KEEP** | Boundary rules |
| `Docs/Anchors/CORPUS-ANCHOR.md` | Corpus path index | **SOURCE_ANCHOR** / **KEEP** | Corpus navigation |
| `Docs/Process/STEWARD-CYCLE.md` | Steward development process | **ACTIVE REFERENCE** | Process reference; tracker still owns Campaign Supergraph sequence |

---

## D. ACTIVE AUTHORITY — may direct new Campaign Supergraph work

| Document | Role |
|---|---|
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Architecture north star |
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Phases 0–9 |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | **Sole** implementation sequence (PR001–PR012, including PR005A/PR005B bridges) |
| `Docs/Reports/graph-document-audit.md` | Doc governance for this reset |

No other document may invent a competing Campaign Supergraph PR sequence.

**Adjacent UI authority (not graph sequencing):** `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` owns shared bar/projection-host composition. It must not invent graph PR order.

---

## E. ACTIVE REFERENCE — current context; cannot override tracker

| Document | Purpose | Action | Why not authority |
|---|---|---|---|
| `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` | Path boundaries runtime/eval | **ACTIVE REFERENCE** | Layout note; sequencing lives in tracker |
| `Docs/Design/INDEX-design-agent-source-set.md` | Design-agent Project Sources bridge | **ACTIVE REFERENCE** | Index only; cannot invent architecture or PR sequence |
| `Docs/Process/STEWARD-CYCLE.md` | Design/review steward cycle | **ACTIVE REFERENCE** | Process only; cannot invent PR sequence; defers to tracker |
| `Docs/Design/DESIGN-graph-object-authoring-surface.md` | Graph Review write-path checkpoint | **ACTIVE REFERENCE** | Write-surface product; subordinate to architecture §4/§8 and tracker merge slices |
| `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md` | Ingest preview → Graph Review → World Graph promote ladder (PR011A*) | **ACTIVE REFERENCE** | Product binding design; sequencing lives in tracker PR011A1–A3/B |
| `Docs/Plans/ROADMAP-graph-object-authoring-surface.md` | Authoring execution trail (paused) | **ACTIVE REFERENCE** | Paused trail; cannot invent parallel supergraph roadmap |
| `Docs/Reports/SPIKE-CLOSEOUT-graph-review-authored-memory-2026-07.md` | Authored-memory spike closeout | **ACTIVE REFERENCE** | Proven invariants; not sequencing authority |
| `Docs/Design/DESIGN-plan-surface-session-prep-current-goal-2026-07.md` | `/plan` product checkpoint | **ACTIVE REFERENCE** | Plan product goals; graph sequencing → tracker |
| `Docs/Dogfood/PLAN-SURFACE-DOGFOOD-RUNBOOK.md` | Plan dogfood operator scaffold | **ACTIVE REFERENCE** | Operator how-to; not architecture |
| `Docs/Plans/HANDOFF-graph-first-recap-ingest.md` | Graph-first ingest direction | **ACTIVE REFERENCE** | Feeds Phase 6 / write work; does not replace PR006–PR012 |
| `Docs/Plans/GRAPH-MEMORY-RUNTIME-CATEGORY-PIPELINE-INTEGRATION-HANDOFF.md` | Wire category pipeline to runtime | **ACTIVE REFERENCE** | Extraction quality path; schedule via tracker follow-ons |
| `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md` | Plan ladder tracking | **ACTIVE REFERENCE** | Adjacent surface tracking; not supergraph roadmap |
| `Docs/Design/DESIGN-ingest-surface.md` | `/ingest` naming note | **ACTIVE REFERENCE** | Prefer authoring-surface doc; do not treat as roadmap |

---

## F. SUPERSEDED (banner / leave)

| Document | Action | Replacement |
|---|---|---|
| `Docs/Plans/JUMPSTART-docs-relevance-first.md` | **SUPERSEDED** forwarding stub | `Docs/Process/STEWARD-CYCLE.md` |
| `Docs/Design/DESIGN-graph-review-gold-authoring-workbench.md` | **SUPERSEDED** | `DESIGN-graph-object-authoring-surface.md` |
| `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md` | **ARCHIVED STUB** (2026-07-15) | Body under `Plans/archive/2026-07-15/superseded-roadmaps/`; replacement `ROADMAP-graph-object-authoring-surface.md` |
| `Docs/Design/dungeonbuddy_spec_architecture_v0_2.md` | **SUPERSEDED** / **HISTORICAL** | `ARCHITECTURE-campaign-supergraph.md` (+ roadmap + tracker). Banner required; do not use for sequencing or Kernel contracts. |
| `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | **SUPERSEDED** | Stub → Campaign Supergraph architecture / roadmap / tracker |

---

## G. HISTORICAL EVIDENCE / ARCHIVED (cannot direct work)

Already under archive trees, or in-place historical:

| Document / tree | Action |
|---|---|
| `Docs/Design/archive/2026-06-28/graph-memory/**` | **ARCHIVED** |
| `Docs/Reports/archive/2026-06-28/graph-memory/**` (except KEEP contracts) | **ARCHIVED** / **KEEP** where noted |
| `Docs/Plans/archive/**` graph handoffs | **ARCHIVED** |
| `Docs/Archive/graph-review-a10/**` | **ARCHIVED** index |
| `Docs/Reports/DOGFOOD-graph-object-authoring-a10-user-stories.md` | **HISTORICAL EVIDENCE** |
| `Docs/Reports/GRAPH-MEMORY-RUNTIME-ENCOUNTER-JOB-DOGFOOD-C1S1.md` | **HISTORICAL EVIDENCE** |
| `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-*.md` | **HISTORICAL EVIDENCE** |
| `Docs/Plans/GRAPH-MEMORY-EXTRACTION-SPIKE-ANCHOR.md` | **HISTORICAL EVIDENCE** |
| `Docs/Plans/HANDOFF-design-recap-ingestion-to-supergraph.md` | **HISTORICAL EVIDENCE** |
| `Docs/Plans/HANDOFF-a10m-union-supergraph-merge-reconciliation.md` | **ARCHIVED STUB** (2026-07-15) | Body under `Plans/archive/2026-07-15/completed-supergraph-handoffs/` |
| `Docs/Plans/NOTE-a10*.md`, `NOTE-a8*`, `NOTE-a9a*` | **HISTORICAL EVIDENCE** |
| `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md` | **HISTORICAL EVIDENCE** |
| `Docs/Experiments/GRAPH-MEMORY-FORK-TRACKING.md` | **HISTORICAL EVIDENCE** |
| `Docs/Archive/Architecture/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | **HISTORICAL** full copy (stub remains at Design path) |

---

## H. Summary counts (approximate)

| Action | Count |
|---|---|
| ACTIVE AUTHORITY | 4 |
| ACTIVE REFERENCE | ~10 |
| KEEP | ~14 |
| SUPERSEDED | ~4 + stubs |
| HISTORICAL EVIDENCE / ARCHIVED | ~70+ |
| DELETE | 1 |

---

## I. Contributor FAQ map

| Question | Read |
|---|---|
| What is the Campaign / World Supergraph? | Architecture §1–§2 |
| Tenancy (why not one graph per campaign)? | Architecture §3 (Model B) |
| Corpus vs graph authority / corrections? | Architecture §4 |
| GraphContribution / retract / replay? | Architecture §5–§6 |
| Graph head / immutable revisions? | Architecture §7 |
| How do surfaces consume? | Architecture §8, §11 |
| Epistemic / visibility invariants? | Architecture §9 |
| Identity outcomes / split-unmerge? | Architecture §10 |
| What is the Graph Kernel? | Architecture §12 |
| First real populated union (named corpus)? | Roadmap Phase 3 · Tracker **PR006** |
| Project Sources vs GitHub authority? | This audit · Project Sources boundary · Tracker **PR005A** · [`INDEX-design-agent-source-set.md`](../Design/INDEX-design-agent-source-set.md) |
| Which docs should the design agent attach? | [`INDEX-design-agent-source-set.md`](../Design/INDEX-design-agent-source-set.md) compact active set |
| How should a steward select/dispatch/review a slice? | [`STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md) |
| Agent tool / authored prep contracts? | [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](../Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md) · Tracker **PR005B** (docs); runtime **PR011** |
| Long-term roadmap? | `ROADMAP-campaign-supergraph.md` |
| Implementation PRs? | `PR-TRACKER-campaign-supergraph.md` only |
| Shared UI bars / Canvas ownership? | `ARCHITECTURE-surface-interaction-layer.md` (UI); Plan composition remains `ARCHITECTURE-plan-surface-toolbox.md` |
| What was superseded? | This audit + `Docs/Archive/Architecture/README.md` |
