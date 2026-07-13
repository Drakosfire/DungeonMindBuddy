# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker (**sole ACTIVE AUTHORITY** for this workstream’s sequencing)
**Date:** 2026-07-10
**Updated:** 2026-07-12 (PR008A DOING; PR007A DONE #339; PR006D2 DONE #337; PR006D3A/D3B DEFERRED; PR006D split into D1/D2/D3; #336 draft = D1 generic Kernel init; PR006C #335 DONE; PR006B #334 DONE; PR006A #333 DONE; PR005B DONE #329)
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

### Forward-only storage and projection contracts

Until an explicit stability milestone is declared, Campaign Supergraph storage and
projection contracts are forward-only. Development revisions, fixtures, and local
graph state may be invalidated and rebuilt when contracts change. Backward
compatibility must not be introduced without an explicit architectural decision.

### Locked architecture decisions

Do not re-open in implementation PRs without an explicit architecture amendment:

- Tenancy Model B (world-owned + campaign scopes)
- Authority / correction persistence model
- GraphContribution lifecycle
- Immutable revision + atomic head invariants
- Mandatory epistemic / temporal / visibility metadata
- Identity resolution outcomes including split/unmerge
- GitHub repo docs are canonical; Project Sources are context inputs only (PR005A)
- Agents are not privileged graph writers (tool categories + preview → GM confirm; PR005B); normative contract [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](../Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md)

### Project Sources boundary (normative)

```text
GitHub repo docs are canonical.
Project Sources are context inputs.
Prepared replacement files are not active Project Sources until the human operator uploads them.
Historical / research / proposal docs cannot direct implementation.
When Project Sources conflict with GitHub, GitHub wins.
```

If this tracker and a jumpstart / Project Source / local handoff disagree, **this tracker wins**.

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
PR005A Context Audit + Source Reanchor  ← docs-only bridge
PR005B Agent Tool Contract + Authored Prep Contributions  ← docs-only bridge
PR006A Graph-Native Contribution Union Diagnostic
PR006B Separate Semantic Assertion Identity from Provenance
PR006C Approved Initial World Supergraph Contribution Bundle
PR006D Publish Initial Eldyrwild C2 World Supergraph (D1 Kernel / D2 service / D3 UI)
PR007 Projection Engine (revision-pinned + admissibility)
PR008 Plan surface migration
PR009 Play surface migration (incl. combat lenses)
PR010 Graph-backed retrieval
PR011 Agent Context + Tool Runtime
PR012 Obsolete-path cleanup safety net
```

Do **not** renumber PR007–PR012. PR006 is intentionally split into **PR006A–PR006D**. GitHub #330–#332 were closed unmerged experiments and are not active dependencies.

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

**Status:** `DONE` (GitHub #323 merged 2026-07-10)
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

**Status:** `DONE` (GitHub #326 merged 2026-07-10)
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

**Status:** `DONE` (GitHub #327 merged 2026-07-10)
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

## PR005A — Context Audit + Source Reanchor

**Status:** `DONE` (GitHub #328 merged 2026-07-11 as `3c859d455cc3c63ddeae166370eb7e4cce3a9f3a`)
**Phase:** 2.5 / docs bridge
**Purpose:** Reconcile Project Sources, local handoffs, active references, historical docs, and repo authority before agent tool contract work — so fresh agents cannot treat stale Project Sources, preview-union docs, research notes, or proposal-only handoffs as active repo authority.

**Deliverables:**

- Repo authority docs identify the PR005A / PR005B split
- Project Sources boundary is documented (GitHub canonical; Project Sources are context inputs)
- Local/source docs are classified as `ACTIVE_AUTHORITY`, `ACTIVE_REFERENCE`, `KEEP_CONTRACT`, `SOURCE_ANCHOR`, `RESEARCH_ONLY`, `HISTORICAL`, `SUPERSEDED`, or `PROPOSAL`
- Stale or dangerous docs have clear banners or audit entries
- No runtime code changes
- Next handoff for PR005B is prepared or referenced

**Success criteria:**

- A fresh agent can identify current repo authority without relying on Project Sources
- Historical/research/proposal docs cannot accidentally direct implementation
- The tracker remains the sole Campaign Supergraph implementation sequence
- PR006 remains Initial World Supergraph Materialization and is not renumbered
- Project Sources are described as context inputs, not repo authority

**Non-goals:**

- Hermes runtime
- Agent tool registry code
- Projection Engine
- Graph-backed retrieval
- PR006 materialization
- Plan encounter builder
- Content-pack storage runtime
- Autonomous writes
- Graph Review UX rewrite

**Depends on:** PR005 (landed).

**Retain / rewrite / delete:** Docs only — tracker, roadmap, audit, jumpstart, superseded banners. No runtime paths.

**Follow-up:** **PR005B** (Agent Tool Contract + Authored Prep Contributions) is the current docs bridge.

---

## PR005B — Agent Tool Contract + Authored Prep Contributions

**Status:** `DONE` (GitHub #329 merged 2026-07-11 as `99437abb1804f599614126701e0e9a24258fbca6`)
**Phase:** 2.5 / docs bridge
**Purpose:** Define how Agent Interaction, Hermes-shaped tools, Plan-authored prep, reusable content packs, and preview-write flows interact with the World Supergraph without creating a second memory system.

**Deliverables:**

- Agent tool capability categories: `read_only`, `draft_only`, `preview_write`, `confirm_commit`, `admin_diagnostic`
- Authored prep lifecycle: `draft`, `planned`, `placed`, `played`, `world_canon`, `retracted`, `superseded`
- Confirmed write boundaries through `GraphContribution`, Kernel merge/publish, source artifact revision, and governed identity/alias decision records
- Explicit rule that agents are not privileged graph writers
- Explicit rule that Plan remains a consumer surface
- Explicit rule that Graph Review / Ingest remains the correction cockpit
- Normative contract: [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](../Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md)
- Architecture / UX / anchor refinements so PR011 is clarified as Agent Context + Tool Runtime without moving runtime ahead of PR006/PR007

**Success criteria:**

- Agents cannot silently mutate the World Supergraph
- Hermes memory, UI thread memory, summaries, and chat history are not campaign canon
- Draft and planned prep are distinguishable from played and world-canon truth
- Content packs and reusable prep artifacts have a review/confirmation path
- Materialization remains a separate Phase 3 concern (now PR006A–D)

**Non-goals:**

- Hermes runtime implementation
- Agent tool registry code
- Plan encounter builder
- Projection Engine
- Graph-backed retrieval
- Content-pack storage runtime
- Autonomous writes
- PR006 materialization

**Depends on:** PR005A (DONE via #328).

**Retain / rewrite / delete:** Docs only — architecture § agent/tool contract, roadmap notes, Agent Interaction UX/anchor refinements. No runtime paths.

**Follow-up:** PR006A Graph-Native Contribution Union Diagnostic. GitHub #330–#332 are closed unmerged experiments — do not reuse.

---

## PR006A — Graph-Native Contribution Union Diagnostic

**Status:** `DONE` (GitHub #333 merged 2026-07-11 as `0b49f159b94a24d5d9fcc7b60ef304e26aad51ab`)
**Phase:** 3 / graph semantic diagnostic
**Purpose:** Determine whether two already-formed graph-native contributions
with distinct provenance domains can share a durable assertion-support record.

**Deliverables:** Graph-only script, test, and report that record heterogeneous
assertion identity, same-key node mutation, revision lineage, failed-write
safety, integrity, and rebuild behavior.

**Observed limitation:** `source_domains` participates in assertion identity:
`worldbuilding` and `recap` assertions for pre-resolved `location:mireward`
create separate support records. PR006A documents this graph-layer defect and
does not patch production behavior.

**Non-goals:** Identity resolution, source discovery, Markdown, corpus
inventory, extraction, publication, projection, runtime migration, and reuse
of #330–#332.

**Depends on:** PR005B (DONE via #329).

---

## PR006B — Separate Semantic Assertion Identity from Provenance

**Status:** `DONE` (GitHub #334 merged 2026-07-12 as `b234988056abebb5b2a033cf236548a7c8c472f5`)
**Phase:** 3 / Kernel semantic repair
**Purpose:** Repair the assertion-identity contract exposed by PR006A so
heterogeneous provenance can independently support one durable semantic
assertion without collapsing provenance evidence.

**Deliverables:**

- Assertion identity separates semantic claim identity from provenance metadata
- Heterogeneous graph-native provenance for one pre-resolved graph object
  produces one assertion-support record with independent contribution support
- Assertion support retains each contributing source artifact and evidence
- Rebuild, supersession, retraction, integrity reporting, and idempotency tests
  cover the repaired identity contract
- Explicit migration/rebuild handling for any pre-repair contribution ledger

**Success criteria:**

- `worldbuilding` and `recap` versions of the same semantic Mireward fact share
  an assertion ID and one support record while preserving two contribution and
  artifact references
- Distinct semantic facts remain distinct assertions
- Existing immutable-head and rebuild equivalence guarantees remain true

**Non-goals:** Source discovery, Markdown selection, corpus inventory,
extraction/reprocessing, contribution-bundle selection, publication,
projection, or runtime migration.

**Depends on:** PR006A.

---

## PR006C — Approved Initial World Supergraph Contribution Bundle

**Status:** `DONE` (GitHub #335 merged 2026-07-12 UTC as `f69c69f271c427209860d902636347b70fea5920`)
**Phase:** 3 / approved bundle
**Purpose:** Define the approved, reviewable graph-native contribution bundle
as `/ingest` bootstrap input for initial Eldyrwild C2 after PR006B establishes
correct multi-source assertion support. Each `manual_import` contribution is
one-source-lineage (one artifact + revision).

**Deliverables:**

- Checked-in `eldyrwild-longmont-c2-initial-v1` bundle under
  `graph_data/approved_contribution_bundles/`
- Strict manifest with SHA-256 locks and deterministic bundle digest
- Loader + validator package (`graph_memory.contribution_bundles`)
- Validation CLI and temporary Kernel dry-run proof (no production world head)
- Human report with Plan trust / non-trust boundaries

**Inputs:** Already-formed `GraphContribution` objects and governed identity
decision records. External-source discovery or extraction is upstream and not
this roadmap's concern.

**Non-goals:** Source discovery, Markdown selection, corpus inventory,
recap or directory enumeration, extraction/reprocessing, publication,
projection, or runtime migration.

**Depends on:** PR006B.

---

## PR006D — Publish Initial Eldyrwild C2 World Supergraph

**Status:** `DOING` (D1 DONE; D2 DONE; D3 deferred)
**Phase:** 3 / graph-native publication

PR006D is intentionally split after #336 review: one reviewable Kernel
contract first, then Eldyrwild activation service, then `/ingest` UI.

### PR006D1 — Generic atomic world initialization

**Status:** `DONE` (GitHub #336; merge `fc6e811dd865559f662bf710566bdb9683acc370`)
**Purpose:** Atomically initialize a new world from a validated contribution
plan without exposing a partial graph.

**Deliverables:**
- Structural-vs-fixture validator split (`validate_union_supergraph_store_payload`)
- Empty technical baseline
- Generic staging + atomic promotion
- Plan-bound `initialize_world_from_contributions` + receipt
- Revision-lineage classification (`active` / `active_head_advanced` /
  `inconsistent_lineage`)
- Rebuild + integrity proof

**Non-goals:** Eldyrwild magic numbers / forbidden legacy IDs; server/API/CLI;
`/ingest` UI; Projection Engine; Plan/Play migration.

**Depends on:** PR006C.

### PR006D2 — Approved Eldyrwild bootstrap activation service

**Status:** `DONE` (GitHub #337; merge `815f9d8d0f0582d3b8b7d86038e5d598c0a653b9`)
**Purpose:** Inspect and explicitly activate the approved Eldyrwild package
through a stable backend contract.

**Deliverables:** PR006C bundle pin + Eldyrwild acceptance policy; status /
prepare / confirm service; truthful idempotency; CLI; exact serialized API
contract; review projection for nodes/edges/attributes/sources.

**Non-goals:** `/ingest` UI.

**Depends on:** PR006D1.

### PR006D3 — `/ingest` review and activation UI

**Status:** `DEFERRED` (design #338; not a Plan dogfood blocker)
**Purpose:** Let a GM see exactly what campaign memory will be created and
explicitly publish it from `/ingest`.

**Deliverables:** Shared/generated API contract; node/relationship/attribute/
source review; confirmation UX; active health + reconstruction display;
real UI tests + dogfood.

**Depends on:** PR006D2.

**Note:** #330/#331 closed unmerged; not prerequisites. D3A design (#338) and
D3B UI implementation remain deferred — operator activation via PR006D2 CLI/API
is sufficient for projection dogfood.

### PR006D3A — `/ingest` design contract

**Status:** `DEFERRED` (GitHub design #338)

### PR006D3B — `/ingest` UI implementation

**Status:** `DEFERRED`

---

## PR007 — Projection Engine

**Status:** `DONE` (PR007A / GitHub #339)
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

- Plan (or a test harness) can request campaign=C2 + focus=Session 23 (or prep window) over the **PR006D published graph**
- **Projection always reads the persistent World Supergraph** (pinned revision). Ingest-run IDs are never graph-selection modes
- No production `preview-source`, `latest-ingest`, `recap-only` backend mode, or store/manifest path selectors in surface-facing APIs
- Test/developer loaders remain outside the production context contract
- Relationship traversal and object cards consume the same projection payload
- Admissibility tests fail closed for GM-only content under player-facing policies

**Demolition:** Replace graph-preview selection APIs with the persistent world graph read API; delete replaced production selectors in this PR unless a named consumer remains.

**Non-goals:** Plan Q&A; graph visualization product; write-path changes; reintroducing latest-ingest as a transitional production mode.

**Depends on:** PR006D2 (published world). PR006D3 UI deferred — not a blocker.

**Absorbs prior informal “plan graph-context contract” intent (without latest-ingest escape hatches).**

### PR007A — Revision-pinned World Graph read snapshot

**Status:** `DONE` (GitHub #339)
**Purpose:** Deliver the first production read API for revision-pinned World Graph
projection over the PR006D published Eldyrwild graph.

**Deliverables:** Pure projection models; Kernel `project_world_graph` +
`search_world_graph_projection`; live-control POST
`/api/live/world-graph/projection`; revision-bound attribute reconstruction;
deterministic lexical search; trust boundary honesty.

**Depends on:** PR006D2.

**Non-goals:** Plan UI wiring; preview/latest-ingest selectors; `/ingest` UI.

---

## PR008A — /plan World Graph dogfood migration

**Status:** `DOING`
**Phase:** 5
**Purpose:** First read-only Plan object-card dogfood against the PR007A projection, with one loaded revision shared by Plan reference navigation and dogfood diagnostics.

**Deliverables:**

- Plan graph-context wiring to production projection contract (`worldId` + `campaignId` + focus)
- UI object/reference navigation uses PR007A projection (not latest-ingest)
- Plan exposes the loaded `revisionId`, `worldId`, `campaignId`, focus, and head status
- Existing source/citation reading remains the evidentiary layer
- Insert-refs / dogfood search against real projection
- Continue object-card usefulness dogfood against the PR006D published World Supergraph
- **Delete** session-derived `useLatestGraphIngest` Plan path in this PR once real projection is wired

**Success criteria:**

- Real campaign dogfood can add/view/remove/judge cards against the PR006D published World Supergraph via PR007A projection
- Diagnostics show requested focus/context that matches GM intent
- No Plan-local graph store; no graph/corpus deletes from dogfood remove
- `useLatestGraphIngest` is gone from Plan production path (not deferred to PR012)

**Non-goals:** Agent Interaction; generalized GraphRAG / tool registry / graph writes; full retrieval sophistication (PR010 may follow); Author Draft in Plan; identity merge in Plan.

**Depends on:** PR007A. Builds on existing GraphObjectCard path (GitHub PR316–PR321 era).

```text
Retained temporarily: (none expected for useLatestGraphIngest)
Reason: n/a — delete in this PR
Remaining consumer: none
Required deletion PR: this PR (PR008A)
```

### PR008B — Agent Interaction World Graph query-context integration

**Status:** `READY` after PR008A.

**Purpose:** Give Agent Interaction deterministic, revision-pinned World Graph query
context after the Plan migration proves the projection contract useful.

**Non-goals:** Plan read-path changes, graph writes, or compatibility reads.

### PR008 follow-ons (as needed)

- Broader Plan surface polish after PR008A vertical dogfood lands
- Play surface migration remains **PR009**

---

## PR008 — Plan Surface Migration (umbrella)

**Status:** `BLOCKED` on PR007A
**Phase:** 5
**Purpose:** Umbrella for Plan surface migration; **PR008A** is the required first vertical dogfood slice. Broader Plan follow-ons may trail PR008A without blocking first read-only agent dogfood.

**Depends on:** PR007A.

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

## PR011 — Agent Context + Tool Runtime

**Status:** `BLOCKED` on PR010
**Phase:** 8
**Purpose:** Agent Interaction assembles context from projections, retrieval, source units, thread state, and surface context, then exposes typed `read_only` / `draft_only` / `preview_write` / `confirm_commit` / `admin_diagnostic` tools with no silent graph mutation (contract defined in PR005B; implemented here).

**Deliverables:**

- Agent context service over projection/retrieval/source-unit contracts
- Tool capability registry matching PR005B / architecture agent-tool contract
- Clear no-silent-write policy; preview → explicit GM confirm for durable writes
- Tooling that escalates corrections to Kernel write path / Graph Review

**Success criteria:**

- Agent backend is graph memory + retrieval + source units, not chat history or Hermes drawer internals as canon
- Agents cannot mutate the supergraph without an explicit write pipeline and GM confirmation
- Player-facing agents cannot receive GM-only assertions via adjacency alone

**Non-goals:** Fully autonomous campaign rewriting; replacing Graph Review; moving tool runtime ahead of PR006/PR007.

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

- Multi-source expansion beyond the PR006D published World Supergraph (Phase 6), including Campaign 1 chronology as needed
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
| Informal “Plan Q&A” | PR008A dogfood first; uses PR010 when retrieval-backed |
| Context audit / Project Sources boundary | **PR005A** (docs) |
| Agent tool / authored prep contract | **PR005B** (docs); runtime in **PR011** |
| GitHub #322 (this docs PR) | **PR001** |

---

## How to add a slice

1. Confirm it fits a roadmap phase.
2. Give it the next `PR0xx` id.
3. Write Purpose / Deliverables / Success criteria / Non-goals / Depends on / Demolition / Retain-rewrite-delete (including temporary retain block when needed).
4. Keep it independently reviewable — no “while we’re here” scope.
5. Do not add production compatibility modes for rejected architecture (latest-ingest, preview-source, store-path selection, campaign-copied world graphs, mutable-in-place heads).
6. Apply deletion-at-replacement; do not park deletions in PR012 by default.
