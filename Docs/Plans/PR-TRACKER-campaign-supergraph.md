# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker — sole sequencing authority for Campaign Supergraph slices  
**Updated:** 2026-07-28 after PR380C / GitHub #443 merged to `main` as `09aed8db`  
**Architecture:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)  
**Integration roadmap:** [`Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md`](../Roadmaps/ROADMAP-cross-surface-statblock-demo.md)
**UI shell (cross-boundary):** [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)

This tracker records only current sequence, dependencies, and exit proofs. Completed implementation narrative belongs in merged PRs, archived handoffs, and acceptance reports.

## Rules

- One slice, one independently useful capability.
- Agents are not privileged writers.
- Graph claims are the canonical materialized fact plane; source anchors are the normal evidence route.
- No product fallback may select latest-ingest, preview-source, mutable run/store paths, arbitrary Markdown, or a parallel corpus index.
- Replacement paths are deleted in the replacement PR unless a named remaining consumer is documented.
- `DONE` requires merged code and the slice's stated exit proof. Code presence alone does not satisfy live acceptance.

## Status legend

| Status | Meaning |
|---|---|
| `READY` | Dependencies are met; a handoff may be authored/dispatched |
| `DOING` | One active implementation slice owns the capability |
| `BLOCKED` | Waiting on a named dependency or acceptance gate |
| `DONE` | Merged and exit proof satisfied |
| `DEFERRED` | Intentionally outside the current critical path |

## Current sequence

| Slice | Status | Depends on | Required outcome |
|---|---|---|---|
| PR001–PR007A foundations | DONE | — | Durable World Graph, Kernel, publication, revision-pinned projection |
| PR008A Plan graph migration | DONE | PR007A | Plan objects and references read World Graph identity |
| PR010A/PR010B Hermes graph retrieval | DONE | PR007A/PR008 | Graph-first Hermes reads, admitted evidence, multi-turn and reload continuity |
| PR011A foundation/A1/A2 | DONE | Kernel + ingest registry | Sealed prepare/confirm operations, server-owned run binding, game-facing review sheet |
| PR380A / #412 | DONE | projection engine | Canonical recap reads one exact World Graph snapshot |
| PR380B / #437 | DONE | PR380A | Recap and Build consume shared exact-ID World Graph objects |
| PR380C / #443 | DONE | PR380B + confirm receipt | Terminal confirm replaces candidate authority with exact committed revision |
| exact-run-candidate-review-projection | READY | PR380C | Graph Review candidates come from one exact ExtractionRun-bound review model |
| retire-preview-union-review-materialization | BLOCKED | exact-run candidate projection | Remove preview-union product lifecycle and obsolete Graph Preview consumers |
| PR380D projection coordinator/cache/telemetry | READY | PR380B/PR380C | Shared request recipes, coalescing, warm cache, revision invalidation, telemetry |
| PR380E Ingest primary-path simplification | BLOCKED | exact-run candidate projection + retirement plan | Product workflow visibly separates source, candidate, review, and committed memory |
| PR380F extraction/identity hardening | READY | concrete dogfood defect | Narrow fixes preserve identity, evidence, and replay invariants |
| durable-memory end-to-end acceptance | READY | PR380C | Fresh fixture proves confirm, exact reload, Plan/Hermes retrieval, and reload persistence |
| PR011B Hermes governed writes | BLOCKED | accepted human reference path | Hermes prepares/proposes through the same protocol; GM remains confirmation authority |
| PR009 Play projection migration | READY | PR007A + surface lessons | Play consumes revision-pinned graph and admissibility contracts |
| PR012 leftover cleanup | BLOCKED | replacement slices | Delete only leftovers with a documented remaining consumer |
| dungeonmind-whole-world-adoption | DOING | #521 | Prove whole Buddy World Graph → DM adoption readiness without weakening Campaign Supergraph invariants; blocks DM product authority cutover and Play mechanics authority cutover until READY |

## Immediate dispatch order

1. Dispatch `exact-run-candidate-review-projection`.
2. In parallel, dispatch PR380D if it remains isolated from candidate-authority semantics.
3. After the candidate path moves, retire preview-union materialization and simplify Ingest.
4. Run fresh end-to-end durable-memory dogfood against the assembled path.
5. Unblock PR011B only when the human path is accepted, not merely unit-tested.
6. Continue PR009 independently when Play capacity is available.

## Current acceptance debt

The following are not erased by PR380C:

- The pre-confirm catalog/live lane still relies on preview-union-era materialization.
- The human confirm path needs a fresh bounded end-to-end acceptance run after the reconstituted PR380A/B/C sequence.
- Browser-reload receipt rehydration is deferred; post-confirm authority is currently an in-session transition.
- Projection coordination, invalidation, and telemetry are not yet app-level shared ownership.
- Hermes continuity is strong in Plan but not yet route-independent across Ingest, Build, and Plan.
- Play has not migrated to the World Graph projection spine.
- Worldbuilding draft elevation remains a separate authority design problem; do not relabel drafts as played canon for convenience.

## Completion evidence map

| Capability | Owning evidence |
|---|---|
| Storage, Kernel, projection contracts | Tests under `src/graph_memory`, server projection contracts, merged PRs |
| Graph Review candidate/confirm lifecycle | Graph Review integration tests and exact binding/interleaving tests |
| Durable memory acceptance | A bounded dogfood report showing exact IDs and revisions before and after reload |
| Hermes grounding | Tool trace, revision metadata, admitted anchors, abstention/coverage-gap tests |
| Surface migration | Exact-ID navigation tests and proof no preview/latest-ingest fallback is invoked |
| Demolition | Static/path inventory plus deletion of replaced product consumers |

## Adding a slice

Every new slice must state:

- purpose and independently useful outcome;
- owner and dependency;
- public/durable contract impact;
- user-visible authority transition;
- exact failure model;
- acceptance proof;
- explicit non-goals;
- retained paths, remaining consumers, and deletion owner.

Do not reopen completed tenancy, authority, or graph-first decisions through a compatibility layer.

## Historical detail

The detailed tracker snapshot before consolidation is available in Git history at `09aed8db`. Archived handoffs and reports remain implementation evidence, not sequencing authority.
