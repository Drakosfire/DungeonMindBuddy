# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker (**sole ACTIVE AUTHORITY** for this workstream’s sequencing)  
**Date:** 2026-07-10  
**Updated:** 2026-07-10 (PR322 re-review — Model B tenancy, contribution lifecycle, head invariants, named PR006 corpus, enforceable boundaries, deletion-at-replacement)  
**Architecture:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)

Tracker IDs (`PR001`…) are **roadmap slice IDs**. They are not GitHub PR numbers. When a GitHub PR opens, record it under the slice.

Every slice must be independently reviewable: one mission, clear deliverables, explicit non-goals, falsifiable success criteria, and **which existing modules are retained, rewritten, or deleted**.

Older handoffs and surface roadmaps may be **ACTIVE REFERENCE** or **HISTORICAL EVIDENCE** (see audit). They cannot override this tracker.

---

## Global conventions

### Deletion at replacement time

When a replacement becomes production-ready, the replaced production path is **deleted in the same PR** unless a named remaining consumer prevents deletion.

Every implementation PR must enumerate:

```text
Retained temporarily:
Reason:
Remaining consumer:
Required deletion PR:
```

**PR012 is a leftover safety net, not the default demolition owner.** No path survives merely because PR012 exists.

### Integrity reporting

Cross-cutting (architecture §18). PR002, PR005, PR006, and PR007 each extend the machine-readable health/coverage surface.

### Locked architecture decisions

Do not re-open in implementation PRs without an explicit architecture amendment:

- Tenancy Model B (world-owned + campaign scopes)
- Authority / correction persistence model
- GraphContribution lifecycle
- Immutable revision + atomic head invariants
- Mandatory epistemic / temporal / visibility metadata
- Identity resolution outcomes including split/unmerge

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
PR002 Storage + immutable revision / graph-head contract
PR003 Kernel public boundary (thin, enforceable)
PR004 Identity outcomes + split/unmerge
PR005 Durable contribution merge (idempotent, retractable, rebuildable)
PR006 Initial real materialization (named acceptance corpus)  ← before projection
PR007 Projection Engine (revision-pinned + admissibility)
PR008 Plan surface migration
PR009 Play surface migration (incl. combat lenses)
PR010 Graph-backed retrieval
PR011 Agent context service
PR012 Obsolete-path cleanup safety net
```

---

## PR001 — Architecture Reset

**Status:** `DONE` (GitHub #322 merged 2026-07-10)  
**Phase:** 0  
**Purpose:** Reset documentation around the Campaign / World Supergraph north star before more implementation.

**Deliverables:**

- Canonical architecture, roadmap, PR tracker, document audit
- Archive superseded architecture docs; stubs at old paths
- Forward-only production selector bans; Combat folded into Play
- Materialization milestone before projection; demolition ownership assigned
- Tenancy Model B, authority loop, contribution lifecycle, head invariants, epistemic metadata, identity outcomes decided in architecture

**Success criteria:**

- New contributor FAQ answerable from new docs alone (architecture §21)
- No circular “Plan needs real graph / real graph after Plan” sequencing
- No unresolved dual-authority or mutable-head ambiguity left for PR002 to invent
- No runtime behavior changes required in this slice

**Non-goals:** Storage, Kernel, materialization, projection, UI, migrations.

**Retain / rewrite / delete:** Docs only — rewrite authority docs; archive superseded architecture; delete duplicate Session-24 stub target content (pointer remains).

---

## PR002 — World Supergraph Storage + Graph-Head Contract

**Status:** `DOING` (GitHub #323)  
**Phase:** 1  
**Purpose:** Persistent per-`worldId` graph store with **immutable revisions** and an **atomic graph head**; not session-owned preview state; not mutable in-place JSON as the product model.

**Deliverables:**

- Durable load/store/validate seams for one World Supergraph per `worldId`
- Graph-head contract matching architecture §7:
  - published revision immutable
  - head points to exactly one validated revision
  - merge builds proposed next revision without mutating current head bytes
  - validation before head advancement
  - atomic head advancement
  - failed writes leave prior head readable
  - revision records parent + contributing operation(s)
  - readers receive one coherent revision
  - rebuild/rollback path (even if crude)
- Campaign scope representable on assertions (Model B), even if v0 dogfood emphasizes one campaign
- Clear separation from preview-run artifacts (runs may remain provenance/ops metadata only)
- Integrity report stub: head revision id, parent, load/validate status
- Tests for load/validate round-trip on a multi-source **fixture** (fixture ≠ Phase 3 real union)

**Success criteria:**

- A world store can be opened without `use_latest_graph_ingest` for a single `session-N`
- Worldbuilding + multi-session + campaign-scoped nodes can coexist in one store fixture
- Concurrent/failed write tests leave prior head readable
- Surfaces are not required to know preview-run paths

**Demolition:** Begin isolating production dependence on named preview sources / preview union stores as campaign graph identity.

```text
Retained temporarily: preview union loaders still used by Graph Review / live ingest until PR006/PR007 replacements
Reason: no durable world head yet
Remaining consumer: Graph Review live-run projection; ingest preview materialization
Required deletion PR: PR006 (runtime availability) / PR007 (surface selection APIs) / leftovers → PR012
```

**Non-goals:** Populating the first real union (PR006); Plan UI migration; retrieval; full contribution lifecycle (PR005).

**Depends on:** PR001.

**Retain / rewrite / delete:** State explicitly in the implementation PR which `union_supergraph` / preview-store modules are retained vs rewritten. Do not ship mutable-in-place current-graph as the head model.

---

## PR003 — Graph Kernel Public Boundary

**Status:** `DONE` (GitHub #324 merged into PR002 branch; #325 lands commits on `main`)  
**Phase:** 2  
**Purpose:** Deliberately **thin** contract-boundary PR: establish Kernel public APIs and invariants without pretending identity/merge are done — with **enforceable** guards, not documentation-only ceremony.

**Deliverables:**

- Kernel module boundaries in `src/graph_memory` (what adapters may call)
- Documented invariants matching architecture Kernel section
- **Enforcement method (required — pick and implement at least one per language boundary):**
  - Python: import-linter (or equivalent) dependency rules forbidding apps → storage internals
  - TypeScript: ESLint `no-restricted-imports` for graph storage paths / banned selectors
  - Package exports that hide internals
  - CI grep/schema tests ensuring surface-facing APIs omit `preview-source`, `latest-ingest`, store/manifest path selectors
- Explicit list of APIs reserved for identity (PR004) and merge (PR005)

**Success criteria:**

- Kernel boundary is reviewable and **CI-enforced**
- No new identity or merge semantics claimed as complete in this slice
- Runtime adapters have a single legal call surface
- Tracker distinguishes enforceable boundaries from aspirational ones in the PR description

**Non-goals:** Implementing identity resolution; implementing durable merge; projection UX; authoring forms.

**Depends on:** PR002.

**Retain / rewrite / delete:** Prefer wrapping/retaining proven model/validate code behind the boundary; delete illegal cross-imports from apps into storage internals in this PR when detected.

---

## PR004 — Identity and Reconciliation

**Status:** `DOING` (GitHub #326; stacked on PR003 / #325)  
**Phase:** 2  
**Purpose:** Fill the Kernel boundary with world-global identity, aliases, explicit resolution outcomes, provisional identities, and reversible merge/split/unmerge.

**Deliverables:**

- Identity resolution APIs used by merge and extraction
- Explicit outcomes: `resolved_existing`, `created_new`, `provisional_new`, `ambiguous`, `blocked_collision`, `rejected`, `human_override`
- Rules for which outcomes may enter the durable graph and in what state
- Cross-class collision diagnostics available to review tooling
- **Split / unmerge** APIs and durable identity decision records (replayable)
- Tests for alias merge, blocked collisions, ambiguous non-promotion, provisional exclusion from strict projections, and split/unmerge

**Success criteria:**

- Same real-world entity does not become multiple durable identities without an explicit merge decision
- Ambiguous candidates do not silently become canonical identity
- Provisional nodes are marked noncanonical
- Human override / split / unmerge are durable and replayable
- UI does not perform identity merge

**Non-goals:** Fuzzy “feel lucky” resolution in Plan; automatic silent merges without policy; durable contribution merge pipeline (PR005).

**Depends on:** PR003.

**Retain / rewrite / delete:**
- Retained temporarily: `union_supergraph.redirects` / merge-reconciliation helpers (internal mechanics); Graph Review preview materialization.
- Rewritten: identity outcome classification + merge/split/unmerge decisions live in `graph_memory.kernel`.
- Deleted in this PR: PR003 fake completed identity stubs (promoted to real exports).
- Required deletion PR: PR005 (durable contribution merge destination), PR006–PR007 (preview runtime replacement).

---

## PR005 — Durable Contribution Merge

**Status:** `DOING`  
**Phase:** 2  
**Purpose:** Extraction candidates and authored overlays merge into the World Supergraph as **GraphContributions**, with idempotency, supersession, retraction, rebuild, and atomic graph-head advancement.

**Deliverables:**

- `GraphContribution` model (architecture §5) with contribution IDs
- Merge/reconciliation path into persistent store producing proposed immutable revisions
- Idempotent reprocessing of unchanged sources
- Supersession when source revisions are replaced; retraction of unsupported assertions without deleting still-supported ones
- Multi-source independent support for the same assertion
- Graph Review authoring commits use the same merge semantics as extraction merges
- **Approved correction replay:** authored assertions + identity decisions survive full reconstruction
- Source-derived claims distinguishable from human-authored assertions; corpus/graph disagreement inspectable
- Inspectable merge diagnostics + integrity report fields (contribution failures, stale revisions, unsupported assertions)
- Graph-head advancement only after validation

**Success criteria:**

- Authoring merge and extraction merge do not fork semantic rules
- Rebuild from contributions + identity decisions yields equivalent graph head
- Failed merge leaves prior head readable
- Preview-only materialization is no longer the only write destination
- Epistemic / visibility / temporal metadata survive union

**Non-goals:** Selecting/importing the full initial real acceptance corpus (PR006); redesigning Graph Review UX; gold-fixture workflow beyond merge target.

**Depends on:** PR002, PR003, PR004.

**Retain / rewrite / delete:**

```text
Retained temporarily:
- Existing preview materialization paths.
- Existing Graph Review preview panels and preview-store request fields.
- Existing union_supergraph helpers reused internally where useful.

Reason:
- PR005 introduces durable contribution merge as a write destination, but PR006
  performs the first real acceptance-corpus materialization and PR007/PR008
  migrate projection/surface reads.

Rewritten:
- Extraction-like and authored graph writes now share GraphContribution merge
  semantics via graph_memory.kernel.
- Contribution records are durable under worlds/<worldId>/contributions/.
- Supersession/retraction/update behavior happens through the Kernel.
- Graph head advancement for contribution merges goes through immutable world
  revisions.

Deleted in this PR:
- Fake PR005 reserved API placeholders (promoted to real Kernel exports).

Required deletion PR:
- PR006 removes reliance on preview graph availability for initial materialization.
- PR007 replaces projection read paths with revision-pinned Projection Engine.
- PR008 removes Plan latest-ingest selectors.
- PR012 catches leftover preview/session graph paths.
```
---

## PR006 — Initial World Supergraph Materialization

**Status:** `BLOCKED` on PR005  
**Phase:** 3  
**Purpose:** Produce the first **real and representative** persistent union from the **named acceptance corpus**, and prove it before projection/Plan migration.

**Named acceptance corpus (required — not “if available”):**

| Family | Scope |
|---|---|
| World | Eldyrwild |
| Campaign scope | Longmont Campaign 2 |
| Recaps | Canonical C2 Sessions **1–23** |
| PCs | All approved C2 PC hub packages |
| Worldbuilding | **Required:** Mirathorn + Mireward hubs under `Elderwyld/Cities and Towns/` |
| Campaign hubs | C2 NPC/faction/location hubs needed for Session 23–adjacent Plan dogfood (enumerate in inventory) |
| Mechanical | Statblocks/encounters required by initial Plan dogfood |
| Authored | Approved Graph Review assertions / identity decisions in scope at run time |

**Deliverables:**

- Publish requested source inventory before/with the run
- Import or reprocess real ingested contributions into the world store
- Reconcile identities under world-global identity with campaign-scoped chronology
- Establish and advance the world graph head
- Machine-readable coverage + health report **and** human summary including:
  - requested vs ingested vs skipped (with reasons)
  - entity/edge counts by source domain
  - unresolved / provisional / ambiguous identities
  - rejected contributions
  evidence coverage
  - unsupported projection requirements
  - explicit “what Plan can / cannot trust”
- Prove reconstruction / incremental continuation under contribution semantics
- Remove dependence on preview fixtures for **runtime graph availability**

**Success criteria:**

- Graph loads without preview source, eval fixture, explicit manifest, or latest-session selector as the selection mechanism
- Contains multi-session Campaign 2 chronology under world-global identity
- Includes required worldbuilding hubs (Mirathorn + Mireward)
- Provenance identifies contributing source artifacts / contributions for durable claims
- Approved corrections in scope survive reconstruction
- Projection work (PR007) uses this graph as its acceptance fixture
- Plan migration (PR008) can be tested against genuinely ingested memory useful for Session 23–adjacent prep

**Demolition:** Delete or quarantine production code paths that treat preview unions as the runtime campaign graph when the world head is the replacement. If a named consumer still requires a preview loader, record the retain block and required deletion PR.

**Non-goals:** Projection Engine; Plan UI migration; unbounded multi-source expansion (Phase 6); treating a synthetic multi-source fixture as this slice’s acceptance graph; optional worldbuilding.

**Depends on:** PR005.

---

## PR007 — Projection Engine

**Status:** `BLOCKED` on PR006  
**Phase:** 4  
**Purpose:** Focus-as-lens projection over the materialized World Supergraph with revision pinning and visibility/admissibility enforcement.

**Deliverables:**

- Projection request contract: `worldId`, `campaignId`, focus, `projectionMode`, admissibility, optional `revisionPin`
- Focus overlay + node views + adjacency from pinned graph-head revision
- Visibility / epistemic admissibility filtering and tests (no secret leakage via adjacency)
- Honest unavailable diagnostics (requested focus/scope)
- Client-searchable projected node views (label/alias/kind/id)
- Play combat/encounter expressible as a Play lens (not a separate graph API)
- Integrity fields for projection truncation and admissibility denial aggregates

**Success criteria:**

- Plan (or a test harness) can request campaign=C2 + focus=Session 23 (or prep window) over the **PR006 real graph**
- **Projection always reads the persistent World Supergraph** (pinned revision). Ingest-run IDs are never graph-selection modes
- No production `preview-source`, `latest-ingest`, `recap-only` backend mode, or store/manifest path selectors in surface-facing APIs
- Test/developer loaders remain outside the production context contract
- Relationship traversal and object cards consume the same projection payload
- Admissibility tests fail closed for GM-only content under player-facing policies

**Demolition:** Replace graph-preview selection APIs with the persistent world graph read API; delete replaced production selectors in this PR unless a named consumer remains.

**Non-goals:** Plan Q&A; graph visualization product; write-path changes; reintroducing latest-ingest as a transitional production mode.

**Depends on:** PR006.

**Absorbs prior informal “plan graph-context contract” intent (without latest-ingest escape hatches).**

---

## PR008 — Plan Surface Migration

**Status:** `BLOCKED` on PR007  
**Phase:** 5  
**Purpose:** `/plan` consumes Projection Engine only for graph-backed object navigation and search against the real world graph under Campaign 2 scope.

**Deliverables:**

- Plan graph-context wiring to production projection contract (`worldId` + `campaignId` + focus)
- Insert-refs / dogfood search against real projection
- Continue object-card usefulness dogfood against PR006 acceptance corpus
- Keep Q&A deferred until dogfood passes usefulness bar
- **Delete** session-derived `useLatestGraphIngest` Plan path in this PR once real projection is wired

**Success criteria:**

- Real campaign dogfood can add/view/remove/judge cards against the PR006 graph via PR007 projection
- Diagnostics show requested focus/context that matches GM intent
- No Plan-local graph store; no graph/corpus deletes from dogfood remove
- `useLatestGraphIngest` is gone from Plan production path (not deferred to PR012)

**Non-goals:** Plan-scoped Q&A in the same slice unless dogfood already unblocked and explicitly scoped; Author Draft in Plan; identity merge in Plan.

**Depends on:** PR007. Builds on existing GraphObjectCard path (GitHub PR316–PR321 era).

```text
Retained temporarily: (none expected for useLatestGraphIngest)
Reason: n/a — delete in this PR
Remaining consumer: none
Required deletion PR: this PR (PR008)
```

---

## PR009 — Play Surface Migration

**Status:** `BLOCKED` on PR007 (may trail PR008)  
**Phase:** 5  
**Purpose:** Play consumes the same projection contracts for live-relevant objects, including combat/encounter as Play lenses.

**Deliverables:**

- Play graph-context + projection consumer seam
- Combat/encounter as Play projection lenses (not a peer surface or peer graph)
- Shared object-card presentation where appropriate
- Admissibility respected for live/player-facing contexts
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
**Purpose:** Retrieval admits evidence through graph identity and relationships with provenance and admissibility.

**Deliverables:**

- Graph-native retrieval API for surfaces/agents
- Provenance-preserving admission rules
- Explicit deprecation path for transitional corpus-index / live-query memory answers (deletion-at-replacement)

**Success criteria:**

- Prep/agent questions can be answered from graph-admitted evidence with source anchors
- Retrieval does not invent a second memory product or select graphs by ingest run
- Visibility rules are enforced

**Non-goals:** Replacing all lexical retrieval helpers; unsupervised ontology generation.

**Depends on:** PR007, PR008 (dogfood pressure), Kernel stability.

---

## PR011 — Agent Context Service

**Status:** `BLOCKED` on PR010  
**Phase:** 8  
**Purpose:** Agent Interaction assembles context from World Supergraph + retrieval.

**Deliverables:**

- Agent context service over projection/retrieval contracts
- Clear no-silent-write policy
- Tooling that escalates corrections to write path / Graph Review

**Success criteria:**

- Agent backend is graph memory, not chat history or Hermes drawer internals
- Agents cannot mutate the supergraph without an explicit write pipeline
- Player-facing agents cannot receive GM-only assertions via adjacency alone

**Non-goals:** Fully autonomous campaign rewriting; replacing Graph Review.

**Depends on:** PR010.

---

## PR012 — Obsolete-Path Cleanup Safety Net

**Status:** `BLOCKED` on PR008 (and preferably PR009)  
**Phase:** 9  
**Purpose:** Delete **leftover** dual-architecture runtime after earlier PRs applied deletion-at-replacement. Not the primary demolition owner.

**Deliverables:**

- Remove dead graph-preview routes/adapters that earlier PRs deferred with a named consumer that is now gone
- Remove environment defaults that still select named preview sources for runtime graph availability
- Remove fixture-specific runtime branches that bypass the world graph head
- Confirm surface-facing APIs cannot select store/manifest/latest-ingest backends
- Short closeout note listing deleted paths and any remaining explicit non-production loaders

**Success criteria:**

- Production runtime has one graph architecture: World Supergraph + Projection Engine
- Grep/CI guards fail if banned selectors reappear in surface-facing contracts
- No “we left it for PR012” paths without a prior named-consumer retain block

**Non-goals:** Rewriting eval harnesses; deleting historical docs/archives; removing isolated test loaders that are explicitly non-production; carrying demolition that should have landed in PR006–PR008.

**Depends on:** PR006–PR008 at minimum.

---

## Follow-on slices (not yet numbered)

Reserve tracker IDs when scoped:

- Multi-source expansion beyond the PR006 acceptance corpus (Phase 6), including Campaign 1 chronology as needed
- Category-pipeline (or successor) as default write extraction
- Build surface migration
- Living-memory hardening dogfoods (Phase 9)
- Plan-scoped graph-memory Q&A (only after PR008 dogfood usefulness; prefer PR010 when retrieval-backed)
- Model C layered composition — only if Model B scoping proves insufficient (architecture amendment required)

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
3. Write Purpose / Deliverables / Success criteria / Non-goals / Depends on / Demolition / Retain-rewrite-delete (including temporary retain block when needed).
4. Keep it independently reviewable — no “while we’re here” scope.
5. Do not add production compatibility modes for rejected architecture (latest-ingest, preview-source, store-path selection, campaign-copied world graphs, mutable-in-place heads).
6. Apply deletion-at-replacement; do not park deletions in PR012 by default.
