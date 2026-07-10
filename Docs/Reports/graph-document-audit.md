# Graph Document Audit — Campaign Supergraph Reset

**Date:** 2026-07-10  
**Status:** Active audit record for Phase 0  
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)  
**PR tracker:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)

## Purpose

Classify graph-related documentation under `Docs/` so contributors know what is authoritative, what is historical, and what was archived in the 2026-07-10 architecture reset.

## Action legend

| Action | Meaning |
|---|---|
| **KEEP** | Reusable contract or research still in force; not architecture ownership |
| **ACTIVE** | Current product/execution direction under the new north star |
| **SUPERSEDED** | No longer architecture/roadmap authority; may remain for history with a banner, or already archived |
| **ARCHIVE** | Moved (or already under an archive tree) — historical only |
| **DELETE** | Removed as duplicate/obsolete with no unique historical value |

## Replacement set (Phase 0)

| New document | Role |
|---|---|
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Canonical architecture |
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Canonical roadmap |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Reviewable implementation slices |
| `Docs/Reports/graph-document-audit.md` | This audit |

## Archive conventions

| Location | Use |
|---|---|
| `Docs/Archive/Architecture/` | Architecture docs superseded by the Campaign Supergraph reset (2026-07-10) |
| `Docs/Design/archive/YYYY-MM-DD/…` | Earlier design cleanups (e.g. 2026-06-28 preview-graph era) |
| `Docs/Reports/archive/YYYY-MM-DD/…` | Historical reports / gate proofs |
| `Docs/Plans/archive/YYYY-MM-DD/…` | Completed handoffs |
| `Docs/Archive/graph-review-a10/` | Index for A10 authored-memory trail (files often stay in place with banners) |

---

## A. Physically archived in this reset (`Docs/Archive/Architecture/`)

| Document | Former path | Current purpose | Action | Reason | Replacement |
|---|---|---|---|---|---|
| Supergraph architecture roadmap v0 | `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | Prior accepted roadmap | **ARCHIVE** | Replaced as architecture/roadmap authority | `ARCHITECTURE-campaign-supergraph.md` + `ROADMAP-campaign-supergraph.md` |
| Union supergraph projection design v0 | `Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md` | Recap projection + union store design | **ARCHIVE** | Architecture superseded; lessons absorbed | `ARCHITECTURE-campaign-supergraph.md` |
| Graph memory workstream anchor | `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md` | Operational agent anchor | **ARCHIVE** | Operational authority → tracker + architecture | `PR-TRACKER-campaign-supergraph.md` |
| Graph retrieval thesis anchor | `Docs/Design/ANCHOR-dungeonBuddy-graph-retrieval.md` | Pre-supergraph retrieval thesis | **ARCHIVE** | Lessons kept; not execution authority | `ARCHITECTURE-campaign-supergraph.md` |
| Plan graph-memory re-anchor (post-PR314) | `Docs/Design/DESIGN-plan-graph-memory-reanchor-after-dogfood-2026-07.md` | Plan transitional vs durable table | **ARCHIVE** | Consumption rules folded into architecture §5–§8 | `ARCHITECTURE-campaign-supergraph.md` |
| Contextual vocabulary roadmap checklist | `Docs/Design/GRAPH-MEMORY-CONTEXTUAL-VOCABULARY-ROADMAP.md` | Vocabulary milestone checklist | **ARCHIVE** | Checklist roadmaps → PR tracker | `PR-TRACKER-campaign-supergraph.md` |
| Live extractor prompt harness | `Docs/Design/GRAPH-MEMORY-LIVE-EXTRACTOR-PROMPT-HARNESS.md` | Historical harness design | **ARCHIVE** | Experimental harness, not Kernel | — |
| Live recap ingest run bundle | `Docs/Design/GRAPH-MEMORY-LIVE-RECAP-INGEST-RUN-BUNDLE.md` | Eval-ladder bundle spec | **ARCHIVE** | Eval seam, not product architecture | — |

Stub pointers remain at former paths (short redirect notes) so old links do not 404 silently.

---

## B. Deleted in this reset

| Document | Action | Reason | Replacement |
|---|---|---|---|
| `Docs/Design/GRAPH-MEMORY-SESSION-24-MANUAL-PROJECTION-DOGFOOD.md` | **DELETE** | Duplicate of archived copy | `Docs/Design/archive/2026-06-28/graph-memory/GRAPH-MEMORY-SESSION-24-MANUAL-PROJECTION-DOGFOOD.md` |

---

## C. KEEP — reusable contracts / research

| Document | Purpose | Action | Reason |
|---|---|---|---|
| `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md` | SourceArtifact→Anchor→Unit boundary | **KEEP** | Surface vocabulary still in force |
| `Docs/Design/GRAPH-MEMORY-SOURCE-SPAN-EVIDENCE-RESOLVER.md` | Source-span evidence resolver | **KEEP** | Evidence contract |
| `Docs/Design/GRAPH-MEMORY-CANDIDATE-GRAPH-PREVIEW-IR.md` | Candidate IR (candidates ≠ durable store) | **KEEP** | Extraction IR contract |
| `Docs/Design/GRAPH-MEMORY-MULTI-PASS-EXTRACTION-CONTRACT.md` | Multi-pass extraction shape | **KEEP** | Write-path design contract |
| `Docs/Design/GRAPH-MEMORY-LIVE-EXTRACTOR-OUTPUT-RECONCILIATION.md` | Live envelope reconciliation | **KEEP** | Extraction bridge contract |
| `Docs/Design/GRAPH-MEMORY-ENCOUNTER-JOB-TAXONOMY-DECISION.md` | `quest` / `combat_encounter` taxonomy | **KEEP** | Accepted taxonomy decision |
| `Docs/Design/DESIGN-contextual-vocabulary-layer.md` | Vocabulary layer design | **KEEP** | Identity/vocab direction |
| `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` | Plan toolbox architecture | **KEEP** | Surface architecture; not graph ownership |
| `Docs/Design/ANCHOR-agent-interaction-hermes.md` | Agent interaction boundary | **KEEP** | Surface/agent boundary |
| `Docs/Design/RESEARCH-graph-visualization-exploration.md` | Viz library research | **KEEP** | Research only |
| `Docs/Reports/GRAPH-MEMORY-CROSS-CLASS-BLOCKED-DIAGNOSTICS.md` | Cross-class collision diagnostics | **KEEP** | Identity-safety evidence |
| `Docs/Reports/archive/2026-06-28/graph-memory/GRAPH-MEMORY-SHARED-SOURCE-VOCABULARY-CONTRACT.md` | Full vocabulary contract copy | **KEEP** | Prefer Design CONTRACT as canonical pointer |
| `Docs/Reports/archive/2026-06-28/graph-memory/GRAPH-MEMORY-SURFACE-VOCABULARY-BOUNDARY.md` | Surface vs graph vocabulary | **KEEP** | Boundary rules |
| `Docs/Anchors/CORPUS-ANCHOR.md` | Corpus path index | **KEEP** | Corpus navigation |

---

## D. ACTIVE — current under new north star

| Document | Purpose | Action | Reason | Notes |
|---|---|---|---|---|
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Canonical architecture | **ACTIVE** | North star | — |
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Canonical roadmap | **ACTIVE** | Phases 0–8 | — |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Implementation slices | **ACTIVE** | PR001–PR010 | — |
| `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` | Path boundaries runtime/eval | **ACTIVE** | Update pointers to new architecture | Merge into architecture later if desired |
| `Docs/Design/DESIGN-graph-object-authoring-surface.md` | Graph Review write-path checkpoint | **ACTIVE** | Write surface still valid | Points at new architecture |
| `Docs/Plans/ROADMAP-graph-object-authoring-surface.md` | Authoring execution trail | **ACTIVE** | Paused checkpoint; subordinate to PR tracker | — |
| `Docs/Reports/SPIKE-CLOSEOUT-graph-review-authored-memory-2026-07.md` | Authored-memory spike closeout | **ACTIVE** | Write-path checkpoint | — |
| `Docs/Design/DESIGN-plan-surface-session-prep-current-goal-2026-07.md` | `/plan` product checkpoint | **ACTIVE** | Session-as-lens product goal | Update supergraph authority links |
| `Docs/Plans/HANDOFF-graph-first-recap-ingest.md` | Graph-first ingest direction | **ACTIVE** | Aligns with forward-only write path | — |
| `Docs/Plans/GRAPH-MEMORY-RUNTIME-CATEGORY-PIPELINE-INTEGRATION-HANDOFF.md` | Wire category pipeline to runtime | **ACTIVE** | Extraction quality path | — |
| `Docs/Dogfood/PLAN-SURFACE-DOGFOOD-RUNBOOK.md` | Plan dogfood runbook | **ACTIVE** | Operator scaffold | — |
| `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md` | Plan ladder tracking | **ACTIVE** | Adjacent surface tracking | — |
| `Docs/Design/DESIGN-ingest-surface.md` | `/ingest` naming note | **ACTIVE**→prefer authoring surface | Short; may archive later | Prefer `DESIGN-graph-object-authoring-surface.md` |

---

## E. SUPERSEDED (banner / leave or already replaced)

| Document | Purpose | Action | Reason | Replacement |
|---|---|---|---|---|
| `Docs/Design/DESIGN-graph-review-gold-authoring-workbench.md` | Gold workbench design | **SUPERSEDED** | Replaced by object-authoring surface | `DESIGN-graph-object-authoring-surface.md` |
| `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md` | Gold workbench roadmap | **SUPERSEDED** | Same | `ROADMAP-graph-object-authoring-surface.md` |
| `Docs/Design/dungeonbuddy_spec_architecture_v0_2.md` | Early tiered-memory spec | **SUPERSEDED** | Parallel early architecture | `ARCHITECTURE-campaign-supergraph.md` |

---

## F. Already archived (prior cleanups) — remain ARCHIVE

All files under:

- `Docs/Design/archive/2026-06-28/graph-memory/`
- `Docs/Reports/archive/2026-06-28/graph-memory/` (except KEEP contracts noted above)
- `Docs/Plans/archive/**` graph handoffs
- A10 notes indexed by `Docs/Archive/graph-review-a10/README.md`

**Action:** **ARCHIVE** (no move required). Preview-graph UX, eval fixture specs, and gate-proof reports stay historical.

Notable ACTIVE-era dogfood reports that remain in `Docs/Reports/` but are **ARCHIVE**-class evidence (not authority):

| Document | Action | Reason |
|---|---|---|
| `Docs/Reports/DOGFOOD-graph-object-authoring-a10-user-stories.md` | **ARCHIVE** (in place) | Historical; closeout is authority |
| `Docs/Reports/GRAPH-MEMORY-RUNTIME-ENCOUNTER-JOB-DOGFOOD-C1S1.md` | **ARCHIVE** (in place) | Point-in-time dogfood |
| `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-*.md` | **ARCHIVE** (in place) | Ablation evidence |
| `Docs/Plans/GRAPH-MEMORY-EXTRACTION-SPIKE-ANCHOR.md` | **ARCHIVE** (in place) | Frozen spike map |
| `Docs/Plans/HANDOFF-design-recap-ingestion-to-supergraph.md` | **ARCHIVE** (in place) | Pre-reset design handoff |
| `Docs/Plans/HANDOFF-a10m-union-supergraph-merge-reconciliation.md` | **ARCHIVE** (in place) | Pre-PR305 merge plan |
| `Docs/Plans/NOTE-a10*.md`, `NOTE-a8*`, `NOTE-a9a*` | **ARCHIVE** (in place) | Hardening notes |
| `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md` | **ARCHIVE** (in place) | Eval ladder history |
| `Docs/Experiments/GRAPH-MEMORY-FORK-TRACKING.md` | **ARCHIVE** (in place) | Obsolete fork tracking |

---

## G. Summary counts (approximate)

| Action | Count |
|---|---|
| KEEP | ~14 |
| ACTIVE | ~14 (including new Phase 0 docs) |
| SUPERSEDED | ~3 left in place + 8 moved this reset |
| ARCHIVE | ~70+ (including prior archive trees) |
| DELETE | 1 |

---

## H. Contributor FAQ map

| Question | Read |
|---|---|
| What is the Campaign Supergraph? | Architecture §1–§2 |
| What owns graph state? | Architecture §3 |
| How does data enter? | Architecture §4, §9 |
| How do surfaces consume? | Architecture §5–§6, §8 |
| What is the Graph Kernel? | Architecture §7 |
| Ingestion vs projection? | Architecture §4 vs §5–§6 |
| Long-term roadmap? | `ROADMAP-campaign-supergraph.md` |
| Implementation PRs? | `PR-TRACKER-campaign-supergraph.md` |
| What was superseded? | This audit + `Docs/Archive/Architecture/README.md` |
