# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker (**sole ACTIVE AUTHORITY** for this workstream’s sequencing)  
**Date:** 2026-07-10  
**Updated:** 2026-07-10 (PR322 review — materialization slice, Kernel boundaries, demolition, selector ban)  
**Architecture:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)

Tracker IDs (`PR001`…) are **roadmap slice IDs**. They are not GitHub PR numbers. When a GitHub PR opens, record it under the slice.

Every slice must be independently reviewable: one mission, clear deliverables, explicit non-goals, falsifiable success criteria, and **which existing modules are retained, rewritten, or deleted**.

Older handoffs and surface roadmaps may be **ACTIVE REFERENCE** or **HISTORICAL EVIDENCE** (see audit). They cannot override this tracker.

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

## Sequence (forward-only)

```text
PR001 Architecture reset
PR002 Storage + graph-head contract
PR003 Kernel public boundary (thin)
PR004 Identity and reconciliation
PR005 Durable contribution merge
PR006 Initial real campaign materialization   ← required before projection
PR007 Projection Engine
PR008 Plan surface migration
PR009 Play surface migration (incl. combat lenses)
PR010 Graph-backed retrieval
PR011 Agent context service
PR012 Obsolete-path cleanup closeout
```

---

## PR001 — Architecture Reset

**Status:** `DOING` (GitHub #322)  
**Phase:** 0  
**Purpose:** Reset documentation around the Campaign Supergraph north star before more implementation.

**Deliverables:**

- Canonical architecture, roadmap, PR tracker, document audit
- Archive superseded architecture docs; stubs at old paths
- Forward-only production selector bans; Combat folded into Play
- Materialization milestone before projection; demolition ownership assigned

**Success criteria:**

- New contributor FAQ answerable from new docs alone
- No circular “Plan needs real graph / real graph after Plan” sequencing
- No runtime behavior changes required in this slice

**Non-goals:** Storage, Kernel, materialization, projection, UI, migrations.

**Retain / rewrite / delete:** Docs only — rewrite authority docs; archive superseded architecture; delete duplicate Session-24 stub target content (pointer remains).

---

## PR002 — Campaign Supergraph Storage + Graph-Head Contract

**Status:** `READY` (after PR001)  
**Phase:** 1  
**Purpose:** Persistent per-campaign graph store with an explicit graph head; not session-owned preview state.

**Deliverables:**

- Durable load/store/validate seams for one Campaign Supergraph per campaign
- Graph-head contract (current durable revision surfaces will read)
- Clear separation from preview-run artifacts (runs may remain provenance/ops metadata only)
- Tests for load/validate round-trip on a multi-source **fixture** (fixture ≠ Phase 3 real union)

**Success criteria:**

- A campaign store can be opened without `use_latest_graph_ingest` for a single `session-N`
- Worldbuilding + multi-session nodes can coexist in one store fixture
- Surfaces are not required to know preview-run paths

**Demolition:** Begin isolating production dependence on named preview sources / preview union stores as campaign graph identity (full removal completes in PR006/PR012 as replacements land).

**Non-goals:** Populating the first real campaign union (PR006); Plan UI migration; retrieval.

**Depends on:** PR001.

**Retain / rewrite / delete:** State explicitly in the implementation PR which `union_supergraph` / preview-store modules are retained vs rewritten.

---

## PR003 — Graph Kernel Public Boundary

**Status:** `READY`  
**Phase:** 2  
**Purpose:** Deliberately **thin** contract-boundary PR: establish Kernel public APIs and invariants without pretending identity/merge are done.

**Deliverables:**

- Kernel module boundaries in `src/graph_memory` (what adapters may call)
- Documented invariants matching architecture §7
- Tests that UI/adapters cannot import storage internals or select graphs by path/manifest
- Explicit list of APIs reserved for identity (PR004) and merge (PR005)

**Success criteria:**

- Kernel boundary is reviewable and enforced
- No new identity or merge semantics claimed as complete in this slice
- Runtime adapters have a single legal call surface

**Non-goals:** Implementing identity resolution; implementing durable merge; projection UX; authoring forms.

**Depends on:** PR002.

**Retain / rewrite / delete:** Prefer wrapping/retaining proven model/validate code behind the boundary; delete illegal cross-imports from apps into storage internals.

---

## PR004 — Identity and Reconciliation

**Status:** `READY`  
**Phase:** 2  
**Purpose:** Fill the Kernel boundary with global identity, aliases, and cross-class collision policy.

**Deliverables:**

- Identity resolution APIs used by merge and extraction
- Cross-class collision diagnostics available to review tooling
- Tests for alias merge and blocked collisions

**Success criteria:**

- Same real-world entity does not become multiple durable identities across sessions without an explicit merge decision
- UI does not perform identity merge

**Non-goals:** Fuzzy “feel lucky” resolution in Plan; automatic silent merges without policy; durable merge pipeline (PR005).

**Depends on:** PR003.

**Retain / rewrite / delete:** State which `identity_resolution` / collision modules are retained, rewritten, or deleted.

---

## PR005 — Durable Contribution Merge

**Status:** `READY`  
**Phase:** 2  
**Purpose:** Extraction candidates and authored overlays merge into the Campaign Supergraph and advance the graph head through one pipeline.

**Deliverables:**

- Merge/reconciliation path into persistent store
- Graph Review authoring commits use the same merge semantics as extraction merges
- Inspectable merge diagnostics
- Graph-head advancement on successful merge

**Success criteria:**

- Authoring merge and extraction merge do not fork semantic rules
- Preview-only materialization is no longer the only write destination

**Non-goals:** Selecting/importing the full initial real campaign source set (PR006); redesigning Graph Review UX; gold-fixture workflow beyond merge target.

**Depends on:** PR002, PR003, PR004.

**Retain / rewrite / delete:** State which preview-materialize vs durable-merge paths are rewritten or deleted as write destinations.

---

## PR006 — Initial Campaign Supergraph Materialization

**Status:** `BLOCKED` on PR005  
**Phase:** 3  
**Purpose:** Produce the first **real** persistent campaign union from already supported ingested source artifacts, and prove it before projection/Plan migration.

**Deliverables:**

- Define the initial supported source domains
- Import or reprocess real ingested graph contributions into the campaign store
- Reconcile identities across multiple sessions
- Include at least one non-recap / worldbuilding source domain if currently available
- Establish and advance the campaign graph head
- Coverage and validation report for the initial union
- Prove repeatable reconstruction or incremental continuation
- Remove dependence on preview fixtures for **runtime graph availability**

**Success criteria:**

- A real campaign graph loads without preview source, eval fixture, explicit manifest, or latest-session selector as the selection mechanism
- It contains multiple sessions under global identity
- Provenance identifies the source artifacts that contributed each durable claim
- Projection work (PR007) uses this graph as its acceptance fixture
- Plan migration (PR008) can be tested against genuinely ingested campaign memory

**Demolition:** Remove or isolate production dependence on preview union stores and named preview sources for runtime graph availability.

**Non-goals:** Projection Engine; Plan UI migration; unbounded multi-source expansion (Phase 6); treating a synthetic multi-source fixture as this slice’s acceptance graph.

**Depends on:** PR005.

**Retain / rewrite / delete:** Delete or quarantine production code paths that treat preview unions as the campaign graph; retain eval fixtures for tests only.

---

## PR007 — Projection Engine

**Status:** `BLOCKED` on PR006  
**Phase:** 4  
**Purpose:** Focus-as-lens projection over the materialized Campaign Supergraph with a production graph-context contract.

**Deliverables:**

- Projection request contract: `campaignId`, focus, `projectionMode`, admissibility
- Focus overlay + node views + adjacency from Campaign Supergraph graph head
- Honest unavailable diagnostics (requested focus)
- Client-searchable projected node views (label/alias/kind/id)
- Play combat/encounter expressible as a Play lens (not a separate graph API)

**Success criteria:**

- Plan (or a test harness) can request focus=Session 23 (or a prep window) over the **PR006 real campaign graph**
- **Projection always reads the persistent Campaign Supergraph.** Ingest-run IDs may appear as provenance or operational metadata, but they are never graph-selection modes for surfaces
- No production `preview-source`, `latest-ingest`, `recap-only` backend mode, or store/manifest path selectors in surface-facing APIs
- Test/developer loaders remain outside the production context contract
- Relationship traversal and object cards consume the same projection payload

**Demolition:** Replace graph-preview selection APIs with the persistent campaign graph read API.

**Non-goals:** Plan Q&A; graph visualization product; write-path changes; reintroducing latest-ingest as a transitional production mode.

**Depends on:** PR006.

**Absorbs prior informal “plan graph-context contract” intent (without latest-ingest escape hatches).**

---

## PR008 — Plan Surface Migration

**Status:** `BLOCKED` on PR007  
**Phase:** 5  
**Purpose:** `/plan` consumes Projection Engine only for graph-backed object navigation and search against the real campaign graph.

**Deliverables:**

- Plan graph-context wiring to production projection contract
- Insert-refs / dogfood search against real projection
- Continue object-card usefulness dogfood
- Keep Q&A deferred until dogfood passes usefulness bar
- **Delete** session-derived `useLatestGraphIngest` Plan path once real projection is wired

**Success criteria:**

- Real campaign dogfood can add/view/remove/judge cards against the PR006 graph via PR007 projection
- Diagnostics show requested focus/context that matches GM intent
- No Plan-local graph store; no graph/corpus deletes from dogfood remove
- `useLatestGraphIngest` is gone from Plan production path

**Non-goals:** Plan-scoped Q&A in the same slice unless dogfood already unblocked and explicitly scoped; Author Draft in Plan; identity merge in Plan.

**Depends on:** PR007. Builds on existing GraphObjectCard path (GitHub PR316–PR321 era).

---

## PR009 — Play Surface Migration

**Status:** `BLOCKED` on PR007 (may trail PR008)  
**Phase:** 5  
**Purpose:** Play consumes the same projection contracts for live-relevant objects, including combat/encounter as Play lenses.

**Deliverables:**

- Play graph-context + projection consumer seam
- Combat/encounter as Play projection lenses (not a peer surface or peer graph)
- Shared object-card presentation where appropriate
- No Play-owned graph semantics

**Success criteria:**

- Play can resolve/display projected objects for the live focus / combat lens
- Same Kernel/projection contracts as Plan

**Non-goals:** Full combat automation; rewriting live packet system in the same slice; introducing Combat as a top-level surface.

**Depends on:** PR007; preferably after PR008 lessons.

---

## PR010 — Graph-backed Retrieval

**Status:** `BLOCKED` on PR007 + useful Plan consumption  
**Phase:** 7  
**Purpose:** Retrieval admits evidence through graph identity and relationships.

**Deliverables:**

- Graph-native retrieval API for surfaces/agents
- Provenance-preserving admission rules
- Explicit deprecation path for transitional corpus-index / live-query memory answers

**Success criteria:**

- Prep/agent questions can be answered from graph-admitted evidence with source anchors
- Retrieval does not invent a second memory product or select graphs by ingest run

**Non-goals:** Replacing all lexical retrieval helpers; unsupervised ontology generation.

**Depends on:** PR007, PR008 (dogfood pressure), Kernel stability.

---

## PR011 — Agent Context Service

**Status:** `BLOCKED` on PR010  
**Phase:** 8  
**Purpose:** Agent Interaction assembles context from Campaign Supergraph + retrieval.

**Deliverables:**

- Agent context service over projection/retrieval contracts
- Clear no-silent-write policy
- Tooling that escalates corrections to write path / Graph Review

**Success criteria:**

- Agent backend is graph memory, not chat history or Hermes drawer internals
- Agents cannot mutate the supergraph without an explicit write pipeline

**Non-goals:** Fully autonomous campaign rewriting; replacing Graph Review.

**Depends on:** PR010.

---

## PR012 — Obsolete-Path Cleanup Closeout

**Status:** `BLOCKED` on PR008 (and preferably PR009)  
**Phase:** 9  
**Purpose:** Delete dead dual-architecture runtime after replacements have landed.

**Deliverables:**

- Remove dead graph-preview routes/adapters no longer on the production path
- Remove environment defaults that select named preview sources for runtime graph availability
- Remove fixture-specific runtime branches that bypass the campaign graph head
- Confirm surface-facing APIs cannot select store/manifest/latest-ingest backends
- Short closeout note listing deleted paths

**Success criteria:**

- Production runtime has one graph architecture: Campaign Supergraph + Projection Engine
- Grep/CI guards (where practical) fail if banned selectors reappear in surface-facing contracts

**Non-goals:** Rewriting eval harnesses; deleting historical docs/archives; removing isolated test loaders that are explicitly non-production.

**Depends on:** PR006–PR008 at minimum.

---

## Follow-on slices (not yet numbered)

Reserve tracker IDs when scoped:

- Multi-source expansion beyond the PR006 initial domain set (Phase 6)
- Category-pipeline (or successor) as default write extraction
- Build surface migration
- Living-memory hardening dogfoods (Phase 9)
- Plan-scoped graph-memory Q&A (only after PR008 dogfood usefulness; prefer PR010 when retrieval-backed)

---

## Mapping from prior Plan ladder (informational)

| Prior informal ID | Tracker home |
|---|---|
| GitHub PR316–PR320 object-card path | Prerequisite substrate for PR008 |
| GitHub PR321 dogfood harness | Prerequisite evidence; keep harness |
| Informal “graph-context” / old “PR322” | **PR007** (+ Plan wiring in **PR008**) |
| Informal “continue dogfood” | **PR008** after **PR006** |
| Informal “Plan Q&A” | Follow-on after PR008; uses PR010 when retrieval-backed |
| GitHub #322 (this docs PR) | **PR001** |

---

## How to add a slice

1. Confirm it fits a roadmap phase.
2. Give it the next `PR0xx` id.
3. Write Purpose / Deliverables / Success criteria / Non-goals / Depends on / Demolition / Retain-rewrite-delete.
4. Keep it independently reviewable — no “while we’re here” scope.
5. Do not add production compatibility modes for rejected architecture (latest-ingest, preview-source, store-path selection).
