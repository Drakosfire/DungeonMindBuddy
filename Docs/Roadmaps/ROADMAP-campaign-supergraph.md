# Roadmap — Campaign Supergraph

**Status:** Canonical implementation roadmap  
**Updated:** 2026-08-09 — PR #536 is merged (current-support-aware relationship conformance); Lysandra handoff is re-anchored to parent-relative gates and blocked on Eldyrwild contribution-integrity heal for `contribution:d3d244474789879c`. Historical adjudication-domain effective conformance remains `294 represented / 52 residual`.  
**Repository anchor:** `413e808112dc85499651cf232ff71614dc4b18b6`  
**DungeonMind pin:** `2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4`  
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Sequencing authority:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)  
**Current-state guide:** [`Docs/Design/STATUS-world-graph-continuity-spine.md`](../Design/STATUS-world-graph-continuity-spine.md)  
**UI shell (cross-boundary):** [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)

This roadmap describes the infrastructure and product-authority milestones for one durable World Supergraph serving every DungeonBuddy surface. It intentionally omits completed PR-by-PR narrative; the tracker owns exact sequence and Git history preserves prior detail.

## Objective

DungeonBuddy uses one authoritative World Supergraph per world, with campaign-scoped assertions, evidence, chronology, visibility, correction history, and projections for every product surface. Plan, Play, Build, Graph Review, Ingest, and Agent Interaction consume revision-aware projections rather than owning independent graphs or campaign truth.

```text
source prose and authored records
→ candidate extraction or governed authoring
→ GraphContribution / identity resolution / correction authority
→ proposed immutable World Graph revision
→ validation and atomic head advancement
→ campaign/focus/admissibility projection
→ product surfaces and Hermes
```

Source artifacts remain prose and evidence authority. The graph is durable materialized campaign knowledge. Conversation history is continuity, never campaign truth.

## Locked decisions

- Tenancy is one World Supergraph with campaign scopes.
- Published revisions are immutable; graph-head advancement is atomic.
- Identity, contribution, evidence, epistemic, temporal, visibility, canon-state, and approved correction decisions are durable and replayable.
- Agents are not privileged writers. Durable changes require typed capabilities and explicit authority boundaries.
- Factual discovery is graph-first. Source excerpts are opened through graph-admitted anchors, except for explicitly typed server-owned memory-lag workflows.
- A graph miss remains visible. The product must not hide coverage gaps with arbitrary Markdown, manifest, corpus-index, or lexical fallback.
- Runtime graph selection never uses latest-ingest, preview-source, manifest path, run directory, or mutable store path.
- Replacement paths are deleted when their replacement becomes production-ready unless a named consumer is documented.
- Conformance analyzers, adjudication fixtures, and explicit adapters are interpretation/proof layers. They do not silently mutate the World Graph.
- A source-derived assertion may remain historically true-to-source while being semantically wrong as current graph meaning. Human correction must preserve that historical source authority while explicitly changing current durable assertion authority.

## Phase status

| Phase | State | Outcome |
|---|---|---|
| 0 — Architecture reset | DONE | Canonical architecture, authority model, roadmap, and tracker |
| 1 — Persistent storage | DONE | Durable per-world store, immutable revisions, atomic head |
| 2 — Graph Kernel foundations | DONE | Identity outcomes, contribution lifecycle, replay, retraction, source-revision supersession, CAS publication |
| 2.5 — Source and agent contracts | DONE | Source authority, typed capability classes, no-privileged-writer rule |
| 3 — Initial publication | DONE | Eldyrwild Campaign 2 World Graph initialized and active |
| 4 — Projection Engine | DONE | Revision-pinned campaign/focus/admissibility projections |
| 5 — Surface integration | PARTIAL | Plan, Recap, Build context, and Agent reads are graph-backed; Play remains |
| 6 — Multi-source expansion | ONGOING | Additional recaps, worldbuilding, prep, and authored records enter through governed contributions |
| 7 — Graph-native retrieval | DONE | Hermes is graph-first in Plan with bounded evidence admission and continuity |
| 8 — Governed context, correction, and tools | ACTIVE | Human confirm reference path exists; exact assertion-correction authority and candidate-path cleanup remain |
| 9 — Living memory and cleanup | NOT STARTED | Continuous Plan/Play use with obsolete dual paths removed and corrected memory surviving normal operation |

Phase 2's foundational lifecycle is complete, but it should not be read as claiming every correction granularity exists. The current Kernel can supersede or retract whole contributions. It does **not** yet expose a governed assertion-level correction operation that can replace one defective assertion while preserving unrelated assertions from the same source contribution. That missing capability is active Phase-8 work because it is required for safe human-authored correction over already-published memory.

## Completed product authority spine

```text
DONE  PR380A / #412  Revision-pinned World Graph recap projection
DONE  PR380B / #437  Recap + Build exact-ID World Graph consumption and shared object navigation
DONE  PR380C / #443  Graph Review post-confirm transition to the exact committed revision
```

PR380C means a terminal confirm receipt replaces candidate authority for its exact review binding. Graph Review either renders the receipt-pinned committed projection or preserves the receipt in a durable-read-unavailable state. It does not re-confirm, fall back to candidate content, or silently read current head.

## Completed DungeonMind semantic-adoption spine

The August adoption work changed the question from “can selected Buddy objects be bridged?” to “can the entire existing World Graph be understood and eventually adopted without losing meaning or authority?”

```text
DONE  #521  Generalized exact Buddy world-object bridge
DONE  #522  Whole-world conformance inventory; adoption fails closed on real gaps
DONE  #523  Re-pin after DungeonMind graph-v5/world-object-v2; emit exact residual ledger
DONE  #525  Re-pin after DungeonMind PR #28; reduce semantic gaps to 59 relationships
DONE  #526  Source-ground and adjudicate every residual relationship
DONE  #528  Re-pin after DungeonMind PR #29; 287/59 → 291/55; DungeonMind relationship debt → 0
DONE  #530  Govern three remaining explicit adapters; 291/55 → 294/52
DONE  #531  Carry adjudication across proven descendants; compose effective conformance
DONE  #534  Targeted structural edge-assertion correction (synthetic/replay-safe; no Eldyrwild mutation)
DONE  #536  Current-support-aware relationship conformance (durable history ≠ current residual)
```

At the immutable Eldyrwild adjudication domain:

- `346` durable relationship semantics;
- `294` effectively represented against the pinned DungeonMind contracts;
- `52` effective residual relationships;
- `2` retained `uses_statblock` mechanics attachments;
- `0` remaining DungeonMind-owned relationship debt in the exact adjudication domain.

The remaining relationship debt is Buddy-owned. The adjudication ledger distinguishes source corrections, compound assertions that are not one relationship, identity-not-relationship cases, and insufficient-evidence cases. Those are different authority problems and should not be collapsed into one migration PR.

## Current critical path — semantic correction before cutover

```text
READY   eldyrwild-contribution-integrity-heal
        Restore contribution:d3d244474789879c ledger source-payload digest to the
        revision-bound seal so pinned rebuild_from_contributions succeeds.
        Do not rewrite immutable revision history; pinned rebuild is not waivable.

BLOCKED eldyrwild-lysandra-threat-direction-correction
        Depends on the integrity heal above, plus merged #534+#536.
        Parent-relative gate: semantic unchanged / represented +1 / residual −1 /
        mechanics unchanged. Live-write fence, complete preflight, dual artifact
        seals, integrity_failure status, and successful pinned rebuild of Q.

BLOCKED effective-conformance-after-first-correction
        Re-anchor descendant fixtures/tracker on the actual post-Q baseline.
        Do not force historical absolute counts onto an evolved live head.
        The original adjudication anchor and historical analyzers remain unchanged.

BLOCKED remaining-buddy-semantic-correction-slices
        Select the next bounded correction/decomposition/identity/evidence slice
        from the residual ledger only after the first real correction proves the
        write/replay pattern.

BLOCKED DungeonMind whole-world authority cutover
        Requires Buddy semantic closure plus a public governed DungeonMind
        existing-world adoption seam. Diagnostic readiness alone cannot switch
        product or Play mechanics authority.
```

### Why targeted assertion correction was a prerequisite

Contribution supersession is intentionally source-revision-shaped: replacing contribution A with contribution B removes A's support from every assertion A carried, then re-applies B. That is correct when a source revision is replaced. It is too broad when a human adjudicates exactly one extracted assertion as semantically wrong while the rest of that source contribution remains valid.

PR #534 published the correction primitive that preserves four distinct facts at once:

1. the historical source contribution really did assert the old meaning;
2. the human correction is a separate governed authored authority;
3. unrelated assertions from the historical contribution remain actively supported;
4. replay of contributions plus correction records reconstructs the corrected head exactly.

The first synthetic proof used a multi-assertion source contribution so the implementation could not accidentally pass by superseding an entire one-assertion contribution. The next proof must apply that seam to the exact Lysandra Eldyrwild target.

## Parallel product path retained

The July product work remains valid and may proceed in parallel when it does not touch semantic correction/adoption authority:

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

READY   PR009 Play projection migration
        Consume the same projection and admissibility contracts for encounter/play lenses.
```

The tracker, not this roadmap, decides which `READY` slice is dispatched next. At the current anchor it gives priority to the bounded Lysandra threat-direction correction, then the exact `294/52 → 295/51` descendant conformance proof, before the next whole-world semantic slice.

## Phase 8 exit criteria

- Ingest creates proposed memory and never auto-publishes.
- Graph Review presents candidates from an exact run-bound review model.
- Explicit GM confirmation publishes through the existing sealed proposal and Kernel path.
- A terminal receipt switches the surface to the exact committed revision.
- Fresh reload proves the object, evidence, and relationships remain durable and retrievable.
- A human-authored factual correction can replace one exact durable assertion without retiring unrelated source-derived assertions.
- Historical source evidence remains inspectable after correction; current projection reflects only the governed active meaning.
- Correction replay is deterministic and stale-parent failure leaves the prior head untouched.
- Hermes uses the same preview/confirm capability model and cannot bypass Graph Review authority.
- Player-facing tools fail closed on GM-only assertions.
- Preview-union and obsolete product fallback paths are removed when their last consumer moves.

## Phase 9 objective

Create continuous, correctable campaign memory across Plan and Play. One durable object identity should survive recap ingestion, agent-assisted elaboration, planning references, exact mechanics binding, human correction, and Play runtime use without copying graph bodies or canonical mechanics between surfaces.

The coordinating integration roadmap is [`ROADMAP-cross-surface-statblock-demo.md`](ROADMAP-cross-surface-statblock-demo.md).

## Explicitly abandoned product and migration paths

- Session-local or campaign-copied graphs as durable identity ownership.
- Latest-ingest or preview-union as runtime campaign authority.
- Agent-side manifest routing, arbitrary document paths, or repo-wide Markdown search.
- Chat/session memory as campaign fact authority.
- Silent graph mutation by Ingest, surfaces, agents, conformance analyzers, or adapters.
- Whole-contribution supersession used as a shortcut for a narrower human assertion correction unless the whole source revision is actually being replaced.
- Rewriting historical source prose or adjudication fixtures to make a residual disappear.
- Global predicate reversal/rename rules introduced to repair one adjudicated edge.
- A second Hermes-specific write protocol.
- Hiding graph coverage defects with a compatibility fallback.

## Historical detail

The longer pre-consolidation roadmap remains in Git history at `09aed8db`. Completed handoffs and dogfood reports remain evidence, but they do not override this roadmap, the architecture, or the active tracker. The August semantic-adoption transition is preserved by merged PRs #521–#531 and their exact fixtures/source seals.
