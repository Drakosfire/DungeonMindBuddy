# Roadmap — Cross-Surface World Graph + Statblock Demo

**Status:** Active integration roadmap  
**Updated:** 2026-07-28 after PR380A/B/C reconstitution completed  
**Product anchor:** GitHub issue #410  
**Scope:** Ingest, Graph Review, World Graph, Hermes Agent Interaction, Build, Statblock Workbench, Plan, and Play  
**Authority:** This roadmap coordinates workstreams. It does not replace the Campaign Supergraph architecture/tracker, Build contracts, or statblock roadmap.

## Demo goal

Demonstrate that DungeonBuddy is a governed continuity layer rather than a set of disconnected generators.

```text
observed in play
→ extracted from recap prose
→ reviewed as candidate memory
→ explicitly confirmed into the World Graph
→ selected as persistent agent context
→ elaborated into a Threat brief
→ approved for statblock generation
→ rendered, edited, validated, and saved as immutable mechanics
→ bound to the same Threat graph object
→ referenced in Plan
→ resolved in Play
```

### Product invariant

> One durable World Graph, many disposable projections; one coherent Agent Interaction layer, many surface-specific toolsets; one object identity across the lifecycle; every durable write crosses an explicit authority boundary.

The final proof must keep three identities coherent:

```text
Threat node ID
Agent thread ID
Statblock ID + selected revision ID + definition digest
```

## Current state

| Demo slice | State | Current truth |
|---|---|---|
| DEMO-00 — Decompose old PR #380 | DONE | Useful integration work was split into narrow successors instead of reviving the omnibus branch |
| DEMO-01 — Shared World Graph projection spine | PARTIAL | PR380A/B/C are merged: recap projection, shared exact-ID navigation, Build read context, and post-confirm authority work; app-level coordinator/cache/invalidation and candidate-path cleanup remain |
| DEMO-02 — Cross-surface Agent Interaction continuity | PARTIAL | Hermes graph retrieval and same-thread continuity work in Plan; provider ownership is partly hoisted, but route-independent thread identity and pinned context ledger remain |
| DEMO-03 — Ingested Threat to approved ThreatDraft | BLOCKED | Agent-approved typed ThreatDraft creation remains missing; depends on stable cross-surface context |
| DEMO-04 — Candidate to immutable mechanics save | PARTIAL | Generation, semantic rendering, editing, and validation are strong; complete accepted-mechanics product proof must stay exact ID/revision/digest bound |
| DEMO-05 — Threat/statblock binding contract | DESIGNED / BLOCKED | Typed external resource and `uses_statblock` projection contract remain to implement |
| DEMO-06 — Governed product Threat binding | BLOCKED | Requires saved mechanics plus DEMO-05 and human-confirmed graph write |
| DEMO-07 — Plan consumption | BLOCKED | Plan graph references exist; exact mechanics binding does not |
| DEMO-08 — Play projection/runtime adapter | READY LATER | Campaign Supergraph PR009 is ready, but exact Threat mechanics resolution depends on binding |
| DEMO-09 — Repeatable dogfood package | BLOCKED | Requires the complete spine and resettable fixture/evidence package |

## Completed PR380 milestone

The old integration branch has now yielded three merged, independently useful capabilities:

- **PR380A / #412:** canonical recap prose and mentions are projected from one exact World Graph revision.
- **PR380B / #437:** Recap and Build open the same durable node IDs through shared graph-object navigation; preview state is not their authority.
- **PR380C / #443:** after terminal confirmation, Graph Review replaces candidate authority with the exact committed revision and preserves the receipt on read failure.

This completes DEMO-00's decomposition objective. It does **not** complete DEMO-01 because pre-confirm candidate review still carries preview-union-era ownership and shared projection coordination remains unfinished.

## Authority boundaries

| Layer | Reads | Authorized durable writes |
|---|---|---|
| Ingest | source recap, extraction candidate, current graph | proposed memory only; no auto-publish |
| Graph Review / Kernel | sealed proposal, evidence, identity state | explicit confirmed contribution and graph revision |
| Build | exact graph context, authored document, exact ExtractionRun | document/source revisions; later governed proposals |
| Agent Interaction | graph pointers, admitted evidence, surface context | typed proposals/tool requests; never privileged direct writes |
| Statblock Workbench | ThreatDraft, candidate, validation result | immutable accepted mechanics revision |
| Plan | graph projection, documents, exact external bindings | planning document and graph references; no silent graph mutation |
| Play | encounter projection, canonical mechanics, runtime state | Play-owned runtime state; no canonical mechanics mutation |

The UI must keep these states visibly distinct:

```text
source draft
extraction candidate
inspect-only candidate
reviewed proposal
committed graph memory
validated statblock candidate
mechanics saved
Threat/statblock binding proposed
binding committed
planned reference
Play runtime instance
```

## Remaining DEMO-01 work

1. Replace Graph Review's remaining preview-union/live candidate lane with a direct exact-ExtractionRun review model.
2. Retire preview-union materialization and obsolete Graph Preview product consumers after the last dependency moves.
3. Establish one app-level projection coordinator for normalized requests, coalescing, warm cache, exact snapshot identity, revision invalidation, and telemetry.
4. Simplify Ingest around the truthful source → candidate → review → confirm lifecycle.
5. Run a fresh end-to-end durable-memory proof through Recap, Graph Review, Plan/Hermes, and reload.

## Forward delivery sequence

### DEMO-02 — Cross-surface Agent Interaction continuity

- Campaign/thread identity independent of route and document.
- Active surface context attached to the thread.
- Durable pointer-only pinned-context ledger.
- **Use as agent context** on shared graph-object cards.
- Safe clearing/re-resolution when source, campaign, revision, or visibility changes.

**Exit proof:** select a Threat in Ingest, ask Hermes about it, navigate to Build or Plan, and continue the same thread with the same exact Threat pointer plus new surface context.

### DEMO-03 — Approved ThreatDraft

```text
propose_threat_draft
→ visible request preview
→ human confirmation
→ create_threat_draft
→ exact draft ID/version
→ generate_statblock_candidate
```

The request carries campaign/world scope, Threat node ID, pinned context IDs, graph revision, approved brief, and optional document locator. Hermes cannot fabricate missing identity or provenance.

### DEMO-04 — Immutable mechanics

Complete semantic candidate rendering, exact-definition editing, validation, digest-bound receipt, explicit Accept/Save, and reload by exact statblock ID/revision/digest. “Mechanics saved” remains distinct from “graph binding committed.”

### DEMO-05/06 — Exact binding and governed publication

The World Graph stores a typed external statblock locator and exact selected revision/digest, not a copied statblock body. Saved mechanics plus an exact Threat produce a reviewed binding proposal and an explicit confirmed graph revision.

Per-object Threat/NPC/PC conformance bridging (#521) is closed synthetically; **whole-graph DungeonMind adoption** is a separate readiness track (`HANDOFF-kernel-dungeonmind-whole-world-adoption.md`). Publishing real dogfood mechanics remains a precondition, not the immediate critical path to mechanics-authority cutover — that cutover waits on whole-graph READY + product projection gates.

### DEMO-07/08 — Plan and Play

Plan stores the Threat pointer and resolves the exact bound mechanics revision. Play consumes the same Threat and mechanics, then may create Play-owned runtime HP/initiative/condition state without mutating canonical mechanics.

### DEMO-09 — Repeatable acceptance package

Provide a bounded recap fixture, seeded graph baseline, known-good prompts, exact receipts, Plan target, Play target, reset procedure, authority-state checklist, and failure/recovery notes.

## Non-goals

- Recreating the old PR #380 omnibus branch.
- Autonomous graph publication or mechanics binding.
- Copying graph bodies, source prose, or statblock definitions between surfaces.
- Treating a cache, candidate projection, chat transcript, or Play runtime state as canonical authority.
- Full combat automation as a prerequisite for the demo.

## Historical detail

The longer integration snapshot before PR380C merged remains in Git history at `09aed8db`. Owning workstream trackers and accepted contracts remain authoritative where this roadmap only coordinates them.
