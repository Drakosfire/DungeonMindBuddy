# Design Agent Source Set — Curated Manifest

**Status:** ACTIVE REFERENCE / process index
**Created:** 2026-08-02
**Snapshot date:** 2026-08-02 (Project Sources filenames from design-agent Sources pane)
**Repository base at audit:** `917b9d5dff3985b3664aa274eafad7eacb776658` (`origin/main`)
**Document class:** curated source index — **not** architecture, roadmap, or PR-sequence authority

## Purpose

Give the design agent one checked-in entrypoint for **which repository documents to treat as current**, how Project Source filenames map to those documents, and what to do when attachments conflict with GitHub.

This file is an **index**. It does not invent Campaign Supergraph sequence, Kernel contracts, or surface ownership. When anything here conflicts with a named ACTIVE AUTHORITY document, the authority document wins.

## Authority rule (non-negotiable)

```text
Project Sources are user-managed context inputs.
They are not the GitHub repository.
They are not automatically current.
Prepared replacement files are not active Project Sources until the operator uploads them.
When Project Sources conflict with GitHub, GitHub wins.
Historical / research / proposal docs cannot direct implementation.
```

Full governance: [`Docs/Reports/graph-document-audit.md`](../Reports/graph-document-audit.md).
Process template: [`Docs/Plans/JUMPSTART-docs-relevance-first.md`](../Plans/JUMPSTART-docs-relevance-first.md).

## Compact active source set

Upload or attach **these repository paths** (or regenerated equivalents) when refreshing the design agent's Sources pane. Prefer exact repo-relative paths over bare basenames.

### ACTIVE AUTHORITY — may direct new work

| Role | Document | Purpose |
|---|---|---|
| Graph architecture | [`ARCHITECTURE-campaign-supergraph.md`](ARCHITECTURE-campaign-supergraph.md) | World Supergraph / Campaign Supergraph north star |
| Graph roadmap | [`../Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md) | Phases 0–9 |
| Graph PR sequence | [`../Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) | **Sole** Campaign Supergraph implementation sequence |
| Doc governance | [`../Reports/graph-document-audit.md`](../Reports/graph-document-audit.md) | Classification of Docs/ for graph work |
| Shared UI chrome | [`ARCHITECTURE-surface-interaction-layer.md`](ARCHITECTURE-surface-interaction-layer.md) | Nav / Agent / Tool / Edit / Projection host ownership |

### ACTIVE REFERENCE — current context; cannot override authorities above

| Role | Document | Purpose |
|---|---|---|
| Plan surface composition | [`ARCHITECTURE-plan-surface-toolbox.md`](ARCHITECTURE-plan-surface-toolbox.md) | Plan domain / SurfaceConfig; not universal bar owner |
| Graph path layout | [`GRAPH-MEMORY-PROJECT-LAYOUT.md`](GRAPH-MEMORY-PROJECT-LAYOUT.md) | Runtime / eval / fixture path boundaries |
| UI hoist sequence | [`../Plans/PLAN-surface-interaction-hoist-build-first.md`](../Plans/PLAN-surface-interaction-hoist-build-first.md) | SI-01+ runtime composition plan |
| Hermes product index | [`INDEX-hermes-campaign-authoring-foundation.md`](INDEX-hermes-campaign-authoring-foundation.md) | Small Hermes active set |
| Repo overview | [`../../README.md`](../../README.md) | Project README — product overview only |
| This manifest | [`INDEX-design-agent-source-set.md`](INDEX-design-agent-source-set.md) | Design-agent source bridge |

### SOURCE_ANCHOR

| Role | Document | Purpose |
|---|---|---|
| Corpus paths | [`../Anchors/CORPUS-ANCHOR.md`](../Anchors/CORPUS-ANCHOR.md) | Where Eldyrwild / Longmont markdown lives |

### PROCESS_TEMPLATE

| Role | Document | Purpose |
|---|---|---|
| Slice steward jumpstart | [`../Plans/JUMPSTART-docs-relevance-first.md`](../Plans/JUMPSTART-docs-relevance-first.md) | Select / dispatch / review / re-anchor one slice |
| PR handoff template | [`../../.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`](../../.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md) | Canonical checked-in handoff skeleton |

### Explicitly historical / superseded (do not use as current authority)

| Classification | Document | Replacement |
|---|---|---|
| SUPERSEDED stub | [`GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`](GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md) | Campaign Supergraph architecture + roadmap + tracker |
| HISTORICAL archive body | [`../Archive/Architecture/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`](../Archive/Architecture/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md) | Same replacements; archive evidence only |
| SUPERSEDED / HISTORICAL | [`dungeonbuddy_spec_architecture_v0_2.md`](dungeonbuddy_spec_architecture_v0_2.md) | `ARCHITECTURE-campaign-supergraph.md` (+ roadmap + tracker) |

## 2026-08-02 Project Sources snapshot — reconciliation

The design-agent Sources pane listed these **basenames**. Exact content was not available in the GitHub tree for every name; classifications below follow repository counterparts and the existing audit.

| # | Project Source basename | Repo counterpart | Classification | Conflict / note |
|---:|---|---|---|---|
| 1 | `TEMPLATE-pr-handoff(1).md` | none found; use `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` | **SOURCE_ONLY** → map to **PROCESS_TEMPLATE** | Download-style `(1)` name; not checked in under that basename |
| 2 | `README.md` | ambiguous basename; likely [`README.md`](../../README.md) | **AMBIGUOUS** → treat root README as **ACTIVE_REFERENCE** | Do not attach arbitrary nested `README.md` files as architecture |
| 3 | `GRAPH-MEMORY-PROJECT-LAYOUT.md` | [`Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md`](GRAPH-MEMORY-PROJECT-LAYOUT.md) | **ACTIVE_REFERENCE** | MATCH |
| 4 | `ARCHITECTURE-plan-surface-toolbox.md` | [`Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`](ARCHITECTURE-plan-surface-toolbox.md) | **ACTIVE_REFERENCE** | MATCH — Plan composition only; UI chrome → surface-interaction architecture |
| 5 | `GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | [`Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`](GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md) | **SUPERSEDED** | MATCH stub; must not direct sequencing |
| 6 | `archived-full-GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` | none under that name; body at [`Docs/Archive/Architecture/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`](../Archive/Architecture/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md) | **SOURCE_ONLY** name → **HISTORICAL** counterpart | Prefer Design stub + Archive path; do not treat archive body as current |
| 7 | `dungeonbuddy_spec_architecture_v0_2.md` | [`Docs/Design/dungeonbuddy_spec_architecture_v0_2.md`](dungeonbuddy_spec_architecture_v0_2.md) | **SUPERSEDED** / **HISTORICAL** | MATCH with banner; conceptual ancestor only |
| 8 | `PROPOSAL-context-audit-source-reanchor.md` | **not found** under DungeonOverMind | **SOURCE_ONLY** / **PROPOSAL** | Do not recreate; absorbed intent lives in this audit + jumpstart |
| 9 | `source-reconciliation-report(2).md` | **not found** under DungeonOverMind | **SOURCE_ONLY** | Local/operator report; not repository authority |
| 10 | `LLM-graph-construction.md` | **not found** under DungeonOverMind | **SOURCE_ONLY** / **RESEARCH_ONLY** | Extraction/eval patterns only if attached; never roadmap |
| 11 | `CORPUS-ANCHOR.md` | [`Docs/Anchors/CORPUS-ANCHOR.md`](../Anchors/CORPUS-ANCHOR.md) | **SOURCE_ANCHOR** | MATCH |
| 12 | `PROJECT-SOURCES-OPERATING-TEMPLATE.md` | **not found**; nearest process docs are Jumpstart + this manifest | **SOURCE_ONLY** → map to **PROCESS_TEMPLATE** counterparts | Prefer Jumpstart + this INDEX over recreating the missing template |

### Unresolved source-only items

These basenames remain **outside the GitHub tree**. Agents must not invent content for them or treat attachments as current architecture:

1. `PROPOSAL-context-audit-source-reanchor.md`
2. `source-reconciliation-report(2).md`
3. `LLM-graph-construction.md`
4. `PROJECT-SOURCES-OPERATING-TEMPLATE.md`
5. `TEMPLATE-pr-handoff(1).md` (use checked-in `HANDOFF.template.md` instead)
6. `archived-full-GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` (use Archive path above)

## Precedence when sources conflict

```text
1. Operator-approved ACTIVE AUTHORITY documents on the current main tip
2. PR tracker for Campaign Supergraph sequencing (never overridden by Project Sources)
3. ACTIVE REFERENCE / KEEP contracts for domain context
4. PROCESS templates (Jumpstart, HANDOFF.template, this INDEX)
5. SOURCE_ANCHOR path indexes
6. Historical / superseded docs (evidence only)
7. Attached Project Sources and chat summaries
```

Classify each conflict as `MATCH`, `SOURCE_AHEAD`, `REPOSITORY_AHEAD`, `CONFLICT`, `SOURCE_ONLY`, or `REPOSITORY_ONLY`. Record which authority wins and why before dispatching work.

## Refresh procedure

After a docs-authority merge, or after the operator changes Project Sources:

1. Confirm the immutable revision: `git fetch origin main && git rev-parse origin/main`.
2. Re-read this INDEX and [`graph-document-audit.md`](../Reports/graph-document-audit.md).
3. Replace Project Source uploads with the **compact active source set** paths above (exact paths, not ambiguous basenames).
4. Remove or demote superseded/historical attachments so they cannot be mistaken for current authority.
5. Leave unresolved source-only local drafts out of the Sources pane unless the operator explicitly wants research/proposal context — and keep their classification visible.
6. Update the snapshot date / base SHA in this INDEX when the curated set changes.

## Explicit exclusions

Do **not** put these in the design-agent active source set as architecture or sequencing authority:

- Corpus prose payloads under `corpus/` (PII / campaign-private; use CORPUS-ANCHOR for paths only)
- Generated eval artifacts, run reports, and fixture dumps under `evals/**/artifacts/` or `out/`
- Stale or completed handoffs that still say ACTIVE / IN FLIGHT without merged banners
- Archived evidence under `Docs/Archive/`, `Docs/**/archive/`, and historical dogfood reports (except when researching a named past decision)
- Runtime TypeScript/Python sources used as if they were normative design authority
- Competing PR sequences invented in Project Sources, jumpstarts, or chat

## Related indexes

| Index | Scope |
|---|---|
| [`INDEX-hermes-campaign-authoring-foundation.md`](INDEX-hermes-campaign-authoring-foundation.md) | Hermes product documents |
| [`../Archive/Architecture/README.md`](../Archive/Architecture/README.md) | Archived architecture set |
| [`../Roadmaps/README.md`](../Roadmaps/README.md) | Roadmap folder pointer |

## Deliberate non-goals

- Does not copy missing Project Source files into the repository.
- Does not create a second architecture authority.
- Does not change runtime behavior, schemas, corpus data, or UI implementation.
- Does not absorb graph PR sequencing into a UI or Hermes plan.
