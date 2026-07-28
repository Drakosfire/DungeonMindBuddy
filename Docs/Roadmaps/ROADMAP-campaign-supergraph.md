# Roadmap — Campaign Supergraph

**Status:** Canonical implementation roadmap  
**Updated:** 2026-07-28 — PR380A, PR380B, and PR380C are merged; the durable read path and the human post-confirm authority transition are assembled.  
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Sequencing authority:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)  
**Current-state guide:** [`Docs/Design/STATUS-world-graph-continuity-spine.md`](../Design/STATUS-world-graph-continuity-spine.md)

This roadmap describes the infrastructure and product-authority milestones for one durable World Supergraph serving every DungeonBuddy surface. It intentionally omits completed PR-by-PR narrative; the tracker owns sequence and Git history preserves prior detail.

## Objective

DungeonBuddy uses one authoritative World Supergraph per world, with campaign-scoped assertions, evidence, chronology, and visibility. Plan, Play, Build, Graph Review, Ingest, and Agent Interaction consume revision-aware projections rather than owning independent graphs or campaign truth.

```text
source prose and authored records
→ candidate extraction
→ governed GraphContribution / identity resolution
→ proposed immutable World Graph revision
→ validation and atomic head advancement
→ campaign/focus/admissibility projection
→ product surfaces and Hermes
```

Source artifacts remain prose and evidence authority. The graph is durable materialized campaign knowledge. Conversation history is continuity, never campaign truth.

## Locked decisions

- Tenancy is one World Supergraph with campaign scopes.
- Published revisions are immutable; graph-head advancement is atomic.
- Identity, contribution, evidence, epistemic, temporal, visibility, and canon-state decisions are durable and replayable.
- Agents are not privileged writers. Durable changes require typed capabilities and explicit authority boundaries.
- Factual discovery is graph-first. Source excerpts are opened through graph-admitted anchors, except for explicitly typed server-owned memory-lag workflows.
- A graph miss remains visible. The product must not hide coverage gaps with arbitrary Markdown, manifest, corpus-index, or lexical fallback.
- Runtime graph selection never uses latest-ingest, preview-source, manifest path, run directory, or mutable store path.
- Replacement paths are deleted when their replacement becomes production-ready unless a named consumer is documented.

## Phase status

| Phase | State | Outcome |
|---|---|---|
| 0 — Architecture reset | DONE | Canonical architecture, authority model, roadmap, and tracker |
| 1 — Persistent storage | DONE | Durable per-world store, immutable revisions, atomic head |
| 2 — Graph Kernel | DONE | Identity outcomes, contributions, replay, retraction, correction durability |
| 2.5 — Source and agent contracts | DONE | Source authority, typed capability classes, no-privileged-writer rule |
| 3 — Initial publication | DONE | Eldyrwild Campaign 2 World Graph initialized and active |
| 4 — Projection Engine | DONE | Revision-pinned campaign/focus/admissibility projections |
| 5 — Surface integration | PARTIAL | Plan, Recap, Build context, and Agent reads are graph-backed; Play remains |
| 6 — Multi-source expansion | ONGOING | Additional recaps, worldbuilding, prep, and authored records enter through governed contributions |
| 7 — Graph-native retrieval | DONE | Hermes is graph-first in Plan with bounded evidence admission and continuity |
| 8 — Governed context and tools | ACTIVE | Human confirm reference path exists; candidate-path cleanup and fresh end-to-end acceptance remain |
| 9 — Living memory and cleanup | NOT STARTED | Continuous Plan/Play use with obsolete dual paths removed |

## Completed authority spine

```text
DONE  PR380A / #412  Revision-pinned World Graph recap projection
DONE  PR380B / #437  Recap + Build exact-ID World Graph consumption and shared object navigation
DONE  PR380C / #443  Graph Review post-confirm transition to the exact committed revision
```

PR380C means a terminal confirm receipt replaces candidate authority for its exact review binding. Graph Review either renders the receipt-pinned committed projection or preserves the receipt in a durable-read-unavailable state. It does not re-confirm, fall back to candidate content, or silently read current head.

## Current critical path

```text
READY   exact-run-candidate-review-projection
        Replace Graph Review's remaining preview-union / fixture-oriented candidate lane
        with a direct exact-ExtractionRun review projection.

BLOCKED retire-preview-union-review-materialization
        Delete preview-union lifecycle requirements, dormant Graph Preview paths, and
        legacy endpoints after the last product consumer moves.

READY   PR380D projection coordinator
        Normalize request construction, coalesce in-flight reads, add short-lived cache,
        revision invalidation, and projection telemetry. Cache is never authority.

BLOCKED PR380E Ingest primary-path simplification
        Simplify the source → extract → review → confirm workflow after candidate authority
        no longer depends on preview-union materialization.

READY   PR380F extraction and identity hardening
        Repair concrete dogfood failures without reopening graph tenancy or authority.

READY   fresh end-to-end durable-memory acceptance
        Prove ingest → review → confirm → exact committed reload → Plan/Hermes retrieval →
        process/browser reload against one bounded fixture.

BLOCKED PR011B Hermes preview_write / confirm_commit
        Reuse the human reference protocol; do not create an agent-specific write path.

READY   PR009 Play projection migration (parallel)
        Consume the same projection and admissibility contracts for encounter/play lenses.
```

The exact-run candidate projection and PR380D may proceed independently. Preview-union retirement must wait until the candidate path no longer consumes it. Hermes governed writes remain blocked on a freshly accepted human reference path, not merely on the presence of confirm code.

## Phase 8 exit criteria

- Ingest creates proposed memory and never auto-publishes.
- Graph Review presents candidates from an exact run-bound review model.
- Explicit GM confirmation publishes through the existing sealed proposal and Kernel path.
- A terminal receipt switches the surface to the exact committed revision.
- Fresh reload proves the object, evidence, and relationships remain durable and retrievable.
- Hermes uses the same preview/confirm capability model and cannot bypass Graph Review authority.
- Player-facing tools fail closed on GM-only assertions.
- Preview-union and obsolete product fallback paths are removed when their last consumer moves.

## Phase 9 objective

Create continuous, correctable campaign memory across Plan and Play. One durable object identity should survive recap ingestion, agent-assisted elaboration, planning references, exact mechanics binding, and Play runtime use without copying graph bodies or canonical mechanics between surfaces.

The coordinating integration roadmap is [`ROADMAP-cross-surface-statblock-demo.md`](ROADMAP-cross-surface-statblock-demo.md).

## Explicitly abandoned product paths

- Session-local or campaign-copied graphs as durable identity ownership.
- Latest-ingest or preview-union as runtime campaign authority.
- Agent-side manifest routing, arbitrary document paths, or repo-wide Markdown search.
- Chat/session memory as campaign fact authority.
- Silent graph mutation by Ingest, surfaces, or agents.
- A second Hermes-specific write protocol.
- Hiding graph coverage defects with a compatibility fallback.

## Historical detail

The longer pre-consolidation roadmap remains in Git history at `09aed8db`. Completed handoffs and dogfood reports remain evidence, but they do not override this roadmap, the architecture, or the active tracker.
