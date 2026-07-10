# Graph Document Audit — Campaign Supergraph Reset

**Date:** 2026-07-10  
**Updated:** 2026-07-10 (PR322 review — sharper authority classes)  
**Status:** Active audit record for Phase 0  
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)  
**PR tracker:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)

## Purpose

Classify graph-related documentation under `Docs/` so contributors know what can **direct new work**, what is **implementation context only**, and what is **historical**.

**Rule:** For Campaign Supergraph sequencing, [`PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) is the **only** active implementation sequence. A fresh agent must not pick an older handoff and resume the superseded architecture.

## Action legend

| Action | Meaning |
|---|---|
| **ACTIVE AUTHORITY** | May direct new work. Conflicts with these docs are bugs. |
| **ACTIVE REFERENCE** | Current implementation context (product checkpoint, contract, paused trail). Useful, but **cannot override** architecture or PR tracker. |
| **KEEP** | Reusable contract/research still in force; not a roadmap. |
| **HISTORICAL EVIDENCE** | Remains readable; cannot direct work. Prefer banners over silent authority. |
| **SUPERSEDED** | Replaced; stub or banner points at replacement. |
| **ARCHIVED** | Under an archive tree (or moved in this reset). |
| **DELETE** | Removed as duplicate/obsolete with no unique historical value. |

## Replacement set (Phase 0) — ACTIVE AUTHORITY

| New document | Role |
|---|---|
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Canonical architecture |
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Canonical roadmap |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Sole Campaign Supergraph implementation sequence |
| `Docs/Reports/graph-document-audit.md` | This audit (governance of docs, not runtime) |

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
| `Docs/Design/GRAPH-MEMORY-SOURCE-SPAN-EVIDENCE-RESOLVER.md` | Source-span evidence | **KEEP** | Evidence contract |
| `Docs/Design/GRAPH-MEMORY-CANDIDATE-GRAPH-PREVIEW-IR.md` | Candidate IR | **KEEP** | Extraction IR (candidates ≠ durable store) |
| `Docs/Design/GRAPH-MEMORY-MULTI-PASS-EXTRACTION-CONTRACT.md` | Multi-pass extraction | **KEEP** | Write-path design contract |
| `Docs/Design/GRAPH-MEMORY-LIVE-EXTRACTOR-OUTPUT-RECONCILIATION.md` | Live envelope reconciliation | **KEEP** | Extraction bridge contract |
| `Docs/Design/GRAPH-MEMORY-ENCOUNTER-JOB-TAXONOMY-DECISION.md` | Encounter/job taxonomy | **KEEP** | Accepted taxonomy decision |
| `Docs/Design/DESIGN-contextual-vocabulary-layer.md` | Vocabulary layer | **KEEP** | Identity/vocab direction |
| `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` | Plan toolbox | **KEEP** | Surface architecture; not graph ownership |
| `Docs/Design/ANCHOR-agent-interaction-hermes.md` | Agent boundary | **KEEP** | Surface/agent boundary |
| `Docs/Design/RESEARCH-graph-visualization-exploration.md` | Viz research | **KEEP** | Research only |
| `Docs/Reports/GRAPH-MEMORY-CROSS-CLASS-BLOCKED-DIAGNOSTICS.md` | Collision diagnostics | **KEEP** | Identity-safety evidence |
| `Docs/Reports/archive/2026-06-28/graph-memory/GRAPH-MEMORY-SHARED-SOURCE-VOCABULARY-CONTRACT.md` | Full vocab contract copy | **KEEP** | Prefer Design CONTRACT as canonical |
| `Docs/Reports/archive/2026-06-28/graph-memory/GRAPH-MEMORY-SURFACE-VOCABULARY-BOUNDARY.md` | Surface vs graph vocab | **KEEP** | Boundary rules |
| `Docs/Anchors/CORPUS-ANCHOR.md` | Corpus path index | **KEEP** | Corpus navigation |

---

## D. ACTIVE AUTHORITY — may direct new Campaign Supergraph work

| Document | Role |
|---|---|
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Architecture north star |
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Phases 0–9 |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | **Sole** implementation sequence (PR001–PR012) |
| `Docs/Reports/graph-document-audit.md` | Doc governance for this reset |

No other document may invent a competing Campaign Supergraph PR sequence.

---

## E. ACTIVE REFERENCE — current context; cannot override tracker

| Document | Purpose | Action | Why not authority |
|---|---|---|---|
| `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` | Path boundaries runtime/eval | **ACTIVE REFERENCE** | Layout note; sequencing lives in tracker |
| `Docs/Design/DESIGN-graph-object-authoring-surface.md` | Graph Review write-path checkpoint | **ACTIVE REFERENCE** | Write-surface product; subordinate to architecture §4/§8 and tracker merge slices |
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
| `Docs/Design/DESIGN-graph-review-gold-authoring-workbench.md` | **SUPERSEDED** | `DESIGN-graph-object-authoring-surface.md` |
| `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md` | **SUPERSEDED** | `ROADMAP-graph-object-authoring-surface.md` + Campaign Supergraph tracker |
| `Docs/Design/dungeonbuddy_spec_architecture_v0_2.md` | **SUPERSEDED** | `ARCHITECTURE-campaign-supergraph.md` |

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
| `Docs/Plans/HANDOFF-a10m-union-supergraph-merge-reconciliation.md` | **HISTORICAL EVIDENCE** |
| `Docs/Plans/NOTE-a10*.md`, `NOTE-a8*`, `NOTE-a9a*` | **HISTORICAL EVIDENCE** |
| `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md` | **HISTORICAL EVIDENCE** |
| `Docs/Experiments/GRAPH-MEMORY-FORK-TRACKING.md` | **HISTORICAL EVIDENCE** |

---

## H. Summary counts (approximate)

| Action | Count |
|---|---|
| ACTIVE AUTHORITY | 4 |
| ACTIVE REFERENCE | ~10 |
| KEEP | ~14 |
| SUPERSEDED | ~3 + stubs |
| HISTORICAL EVIDENCE / ARCHIVED | ~70+ |
| DELETE | 1 |

---

## I. Contributor FAQ map

| Question | Read |
|---|---|
| What is the Campaign Supergraph? | Architecture §1–§2 |
| What owns graph state? | Architecture §3 |
| How does data enter? | Architecture §4, §9 |
| How do surfaces consume? | Architecture §5–§6, §8 |
| What is the Graph Kernel? | Architecture §7 |
| Ingestion vs projection? | Architecture §4 vs §5–§6 |
| First real populated union? | Roadmap Phase 3 · Tracker **PR006** |
| Long-term roadmap? | `ROADMAP-campaign-supergraph.md` |
| Implementation PRs? | `PR-TRACKER-campaign-supergraph.md` only |
| What was superseded? | This audit + `Docs/Archive/Architecture/README.md` |
