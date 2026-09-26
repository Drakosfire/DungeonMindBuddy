# Documentation Authority Audit — World / Campaign Settlement

**Date:** 2026-07-10
**Settlement refresh:** 2026-09-25
**Status:** ACTIVE documentation-governance authority
**Architecture:** [`ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**Source manifest:** [`INDEX-design-agent-source-set.md`](../Design/INDEX-design-agent-source-set.md)
**Settlement evidence:** [`REPORT-repository-settlement-2026-09-25.md`](REPORT-repository-settlement-2026-09-25.md)

## Purpose

Classify repository documents by what keeps them alive **now**. A self-declared
`ACTIVE`, `NEXT`, or `canonical` label is not enough when implementation
and ownership have moved past it.

## Classification

| Class | Meaning |
|---|---|
| **ACTIVE AUTHORITY** | Current invariants/ownership; may direct work inside its domain |
| **ACTIVE REFERENCE** | Current context/contract; cannot invent sequence |
| **PROCESS** | Repository/steward operating law |
| **SOURCE ANCHOR** | Regenerable path/index grounding |
| **SETTLEMENT_HOLD** | Known stale authority whose physical retirement is temporarily blocked by an active write lease |
| **SUPERSEDED** | Replacement exists; path may remain as forwarding stub |
| **HISTORICAL / FROZEN** | Evidence only; status rows cannot dispatch work |
| **ARCHIVED** | Historical body preserved under archive tree |
| **DELETE** | No living consumer or unique historical value |

## 2026-09-25 settlement decisions

| Document | Classification | Current role |
|---|---|---|
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | **ACTIVE AUTHORITY** | World-model invariants; runtime ownership re-anchored to DungeonMind/WorldKeeper/Buddy |
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | **SETTLEMENT_HOLD** | Program history; self-claim to current roadmap is stale, physical retirement blocked by UI #761 path lease |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | **HISTORICAL / FROZEN** | Old Campaign/CUTOVER sequence; no dispatch |
| `Docs/Design/STATUS-world-graph-continuity-spine.md` | **HISTORICAL / FROZEN** | August continuity snapshot |
| `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` | **ACTIVE AUTHORITY** | Stable shared chrome/Surface/Canvas ownership |
| `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md` | **SUPERSEDED** | Construction scaffold; DOGFOOD-POLISH closeout proves landed outcome |
| `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` | **ACTIVE REFERENCE** | Plan-domain composition only |
| `Docs/Design/INDEX-hermes-campaign-authoring-foundation.md` | **SUPERSEDED** | July Hermes reset history; AgentRuntime is current product boundary |
| `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md` | **ACTIVE AUTHORITY** | Buddy → WorldKeeper → DungeonMind authoring ownership |
| `Docs/Design/DECISION-agent-context-compilation.md` | **ACTIVE REFERENCE** | Agent context policy |
| `Docs/Design/DECISION-agent-runtime-and-semantic-adjudication.md` | **ACTIVE REFERENCE** | Buddy AgentRuntime/harness boundary |
| `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | **ACTIVE AUTHORITY** | Current CON-READY pickup |
| `Docs/Roadmaps/ROADMAP-con-ready.md` | **ACTIVE AUTHORITY** | Current product acceptance roadmap |
| `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | **ACTIVE AUTHORITY** | Play/Playable sequence |
| `Docs/Design/INDEX-design-agent-source-set.md` | **ACTIVE REFERENCE** | Curated current-source bridge |
| `Docs/Process/STEWARD-CYCLE.md` | **PROCESS** | Steward lifecycle |
| `AGENTS.md` | **PROCESS** | Foundational repository operating law |
| `Docs/Anchors/CORPUS-ANCHOR.md` | **SOURCE ANCHOR** | Corpus path grounding |
| `Docs/Plans/JUMPSTART-docs-relevance-first.md` | **SUPERSEDED** | Forwarding stub to STEWARD-CYCLE |

## Why Campaign Supergraph sequencing is settled

CUTOVER closure evidence records:

```text
D.3A mounted graph-engine excision     COMPLETE / MERGED  Buddy #665
D.3B physical graph-engine deletion    COMPLETE / MERGED  Buddy #667
D.3 Buddy graph-engine demolition      DONE
CUTOVER implementation                 CLOSED
```

The August 29 closure report explicitly named the Campaign tracker, roadmap,
status guide, and source mirrors as the mutable authority sync set. That sync
did not complete. This audit closes the safe, non-colliding part now.

The World-model architecture survives because its invariants still have living
consumers. The Buddy-local implementation sequence does not.

## Current ownership boundary

```text
DungeonBuddy  product interaction, sources/work, projections, AgentRuntime
WorldKeeper   semantic World-change prepare/confirm coordination
DungeonMind   durable World identity/provenance/revisions/publication/reads
```

Any older document that assigns durable graph-head/storage/identity ownership
to Buddy's Graph Kernel is historical implementation placement unless a current
compatibility seam is explicitly named.

## Immediate-source rule

Use the clean set in `INDEX-design-agent-source-set.md`. In particular, do
not upload the frozen Campaign tracker/status, the superseded SI hoist plan, or
the superseded Hermes foundation index as current context.

The exact pre-settlement audit body is archived at
`Docs/Reports/archive/2026-09-25/graph-document-audit-pre-settlement.md`.

## Settlement hold: Campaign roadmap

The canonical Campaign roadmap path is intentionally not modified in this pass.
Open UI PR #761 explicitly edits it. Creating a second write lane on that path
would violate the repository's own settlement discipline.

Until the blocked successor runs:

- its self-declared `Canonical implementation roadmap` header is stale;
- it cannot override this audit or the current source manifest;
- it is excluded from the clean Project Sources export;
- no new Campaign slice may be dispatched from it.

## Archive conventions

- `Docs/Design/archive/YYYY-MM-DD/` — superseded design/index bodies.
- `Docs/Plans/archive/YYYY-MM-DD/` — completed/superseded implementation plans.
- `Docs/Reports/archive/YYYY-MM-DD/` — historical audits/reports.
- Git history remains valid evidence; an archive copy is used when old links or
  discoverability benefit from an explicit retained body.
