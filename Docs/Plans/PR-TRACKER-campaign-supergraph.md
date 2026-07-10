# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker  
**Date:** 2026-07-10  
**Architecture:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)

Tracker IDs (`PR001`…) are **roadmap slice IDs**. They are not GitHub PR numbers. When a GitHub PR opens, record it under the slice.

Every slice must be independently reviewable: one mission, clear deliverables, explicit non-goals, falsifiable success criteria.

---

## Status legend

| Status | Meaning |
|---|---|
| `READY` | Can start once dependencies are met |
| `DOING` | Active |
| `BLOCKED` | Waiting on dependency or decision |
| `DONE` | Merged + exit criteria met |
| `DEFERRED` | Intentionally later |

---

## PR001 — Architecture Reset

**Status:** `DOING` (this documentation PR)  
**Phase:** 0  
**Purpose:** Reset documentation around the Campaign Supergraph north star before more implementation.

**Deliverables:**

- `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
- `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
- `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
- `Docs/Reports/graph-document-audit.md`
- Archive superseded architecture docs under `Docs/Archive/Architecture/`
- Cross-reference updates on active docs

**Success criteria:**

- New contributor FAQ answerable from new docs alone
- Superseded architecture docs archived with pointers
- No runtime behavior changes required

**Non-goals:** Storage, Kernel, projection engine, UI, migrations.

---

## PR002 — Campaign Supergraph Storage

**Status:** `READY` (after PR001)  
**Phase:** 1  
**Purpose:** Persistent per-campaign graph store that is not session-owned preview state.

**Deliverables:**

- Durable load/store/validate seams for one Campaign Supergraph per campaign
- Clear separation from preview-run artifacts (runs may remain operational metadata)
- Tests for load/validate round-trip on a multi-source fixture

**Success criteria:**

- A campaign store can be opened without `use_latest_graph_ingest` for a single `session-N`
- Worldbuilding + multi-session nodes can coexist in one store fixture
- Surfaces are not required to know preview-run paths

**Non-goals:** Full multi-source ingest UX; Plan UI migration; retrieval.

**Depends on:** PR001.

---

## PR003 — Graph Kernel

**Status:** `READY` (after PR002 storage seams exist; contracts may start earlier)  
**Phase:** 2  
**Purpose:** Package durable graph semantics behind Kernel APIs.

**Deliverables:**

- Kernel module boundaries in `src/graph_memory` (model, validate, report, load)
- Explicit API surface for adapters (no UI imports of storage internals)
- Tests that adapters can only access Kernel/projection contracts

**Success criteria:**

- Documented Kernel in/out of scope matches architecture §7
- Runtime adapters call Kernel; no new identity logic in UI

**Non-goals:** Projection focus UX; authoring forms; agent tools.

**Depends on:** PR002 (for persistence); may share branch sequencing with PR004.

---

## PR004 — Identity Resolution

**Status:** `READY`  
**Phase:** 2  
**Purpose:** Global identity, aliases, and cross-class collision policy in the Kernel.

**Deliverables:**

- Identity resolution APIs used by merge and extraction
- Cross-class collision diagnostics remain available to review tooling
- Tests for alias merge and blocked collisions

**Success criteria:**

- Same real-world entity does not become multiple durable identities across sessions without an explicit merge decision
- UI does not perform identity merge

**Non-goals:** Fuzzy “feel lucky” resolution in Plan; automatic silent merges without policy.

**Depends on:** PR003 (or lands as part of Kernel hardening with clear commit boundaries).

---

## PR005 — Persistent Merge Pipeline

**Status:** `READY`  
**Phase:** 2  
**Purpose:** Extraction candidates and authored overlays merge into the Campaign Supergraph through one pipeline.

**Deliverables:**

- Merge/reconciliation path into persistent store
- Graph Review authoring commits use the same merge semantics as extraction merges
- Inspectable merge diagnostics

**Success criteria:**

- Authoring merge and extraction merge do not fork semantic rules
- Preview-only materialization is no longer the only write destination

**Non-goals:** Redesigning Graph Review UX; gold-fixture authoring workflow changes beyond merge target.

**Depends on:** PR002, PR003, PR004.

---

## PR006 — Projection Engine

**Status:** `READY`  
**Phase:** 3  
**Purpose:** Focus-as-lens projection over the Campaign Supergraph with an explicit graph-context contract.

**Deliverables:**

- Projection request contract: `campaignId`, focus, `projectionMode`, admissibility
- Focus overlay + node views + adjacency from Campaign Supergraph
- Honest unavailable diagnostics (requested context)
- Client-searchable projected node views (label/alias/kind/id)

**Success criteria:**

- Plan (or a test harness) can request focus=Session 23 (or a prep window) over a campaign store that includes adjacent sessions + worldbuilding
- Projection does not mean “latest ingest for derived memorySession” unless that mode is explicitly selected and documented as transitional
- Relationship traversal and object cards consume the same projection payload

**Non-goals:** Plan Q&A; graph visualization product; write-path changes.

**Depends on:** PR002; Kernel read APIs from PR003+.

**Absorbs prior “PR322 plan graph-context contract” intent.**

---

## PR007 — Plan Surface Migration

**Status:** `BLOCKED` on PR006  
**Phase:** 4  
**Purpose:** `/plan` consumes Projection Engine only for graph-backed object navigation and search.

**Deliverables:**

- Plan graph-context wiring (replace session-keyed latest-ingest default)
- Insert-refs / dogfood search against real projection
- Continue object-card usefulness dogfood
- Keep Q&A deferred until dogfood passes usefulness bar

**Success criteria:**

- Real campaign dogfood can add/view/remove/judge cards against a real projection
- Diagnostics show requested graph context that matches GM intent
- No Plan-local graph store; no graph/corpus deletes from dogfood remove

**Non-goals:** Plan-scoped Q&A in the same slice unless dogfood already unblocked and explicitly scoped; Author Draft in Plan; identity merge in Plan.

**Depends on:** PR006. Builds on existing GraphObjectCard path (GitHub PR316–PR321 era).

---

## PR008 — Play Surface Migration

**Status:** `BLOCKED` on PR006 (may trail PR007)  
**Phase:** 4  
**Purpose:** Play consumes the same projection contracts for live-relevant objects.

**Deliverables:**

- Play graph-context + projection consumer seam
- Shared object-card presentation where appropriate
- No Play-owned graph semantics

**Success criteria:**

- Play can resolve/display projected objects for the live focus
- Same Kernel/projection contracts as Plan

**Non-goals:** Full combat automation; rewriting live packet system in the same slice.

**Depends on:** PR006; preferably after PR007 lessons.

---

## PR009 — Graph-backed Retrieval

**Status:** `BLOCKED` on PR006 + useful Plan consumption  
**Phase:** 6  
**Purpose:** Retrieval admits evidence through graph identity and relationships.

**Deliverables:**

- Graph-native retrieval API for surfaces/agents
- Provenance-preserving admission rules
- Explicit deprecation path for transitional corpus-index / live-query memory answers

**Success criteria:**

- Prep/agent questions can be answered from graph-admitted evidence with source anchors
- Retrieval does not invent a second memory product

**Non-goals:** Replacing all lexical retrieval helpers; unsupervised ontology generation.

**Depends on:** PR006, PR007 (dogfood pressure), Kernel stability.

---

## PR010 — Agent Context Service

**Status:** `BLOCKED` on PR009  
**Phase:** 7  
**Purpose:** Agent Interaction assembles context from Campaign Supergraph + retrieval.

**Deliverables:**

- Agent context service over projection/retrieval contracts
- Clear no-silent-write policy
- Tooling that escalates corrections to write path / Graph Review

**Success criteria:**

- Agent backend is graph memory, not chat history or Hermes drawer internals
- Agents cannot mutate the supergraph without an explicit write pipeline

**Non-goals:** Fully autonomous campaign rewriting; replacing Graph Review.

**Depends on:** PR009.

---

## Follow-on slices (not yet numbered)

Reserve tracker IDs when scoped:

- Multi-source worldbuilding ingest (Phase 5)
- Category-pipeline (or successor) as default write extraction
- Combat / Build surface migration
- Living-memory hardening dogfoods (Phase 8)
- Plan-scoped graph-memory Q&A (only after PR007 dogfood usefulness)

---

## Mapping from prior Plan ladder (informational)

| Prior informal ID | Tracker home |
|---|---|
| GitHub PR316–PR320 object-card path | Prerequisite substrate for PR007 |
| GitHub PR321 dogfood harness | Prerequisite evidence; keep harness |
| “PR322 graph-context” | **PR006** (+ Plan wiring in **PR007**) |
| “PR323 continue dogfood” | **PR007** acceptance / follow-up |
| “PR324 Plan Q&A” | Follow-on after PR007; uses PR009 when retrieval-backed |

---

## How to add a slice

1. Confirm it fits a roadmap phase.
2. Give it the next `PR0xx` id.
3. Write Purpose / Deliverables / Success criteria / Non-goals / Depends on.
4. Keep it independently reviewable — no “while we’re here” scope.
