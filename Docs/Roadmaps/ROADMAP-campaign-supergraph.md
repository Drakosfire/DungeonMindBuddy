# Roadmap — Campaign Supergraph

**Status:** Canonical implementation roadmap  
**Date:** 2026-07-10  
**Updated:** 2026-07-10 (PR322 review — materialization before projection; demolition ownership)  
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**PR slices:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)  
**Document audit:** [`Docs/Reports/graph-document-audit.md`](../Reports/graph-document-audit.md)

This roadmap describes **implementation milestones**, not experiments. Phases are sequential where noted; PR slices inside a phase may parallelize only when dependencies allow.

**This document + the PR tracker are the only ACTIVE AUTHORITY for Campaign Supergraph sequencing.** Older handoffs cannot override them.

**Supersedes as roadmap authority:** `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`, `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md`, and overlapping checklist roadmaps called out in the audit.

---

## Phase 0 — Architecture reset

**Objective:** Establish one coherent architectural foundation before more graph systems are built.

**Motivation:** Plan object-card dogfood proved the card path while exposing session-keyed latest-ingest as the wrong graph question. Continuing on preview/session-centric docs would deepen conceptual debt.

**Dependencies:** None.

**Expected PR slices:** Tracker **PR001**.

**Exit criteria:**

- Canonical architecture, roadmap, and PR tracker exist.
- Graph-document audit published with authority vs reference vs historical classifications.
- Superseded architecture docs archived with stubs.
- Forward-only production contract bans latest-ingest / preview-source / store-path graph selection.
- Combat is folded into Play in canonical docs.

---

## Phase 1 — Persistent Campaign Supergraph storage

**Objective:** One durable graph store per campaign with an explicit graph-head contract — not session-owned preview state.

**Motivation:** Surfaces need a real memory backend. Preview unions keyed to `session-N` latest ingest cannot express multi-session + worldbuilding memory.

**Dependencies:** Phase 0.

**Expected PR slices:** Tracker **PR002**.

**Demolition owned here (start):** Isolate production code from treating named preview sources / preview union stores as the campaign graph identity. Full deletion may complete in later cleanup once replacements land.

**Exit criteria:**

- Persistent Campaign Supergraph can be loaded/validated for a campaign without `use_latest_graph_ingest` for a single `session-X`.
- Graph-head contract exists (what “current campaign graph” means).
- Multi-source nodes can coexist in one store (fixture proof is necessary but **not sufficient** — Phase 3 populates the real union).
- Surfaces are not required to know preview-run paths.

---

## Phase 2 — Graph Kernel

**Objective:** Establish the Kernel public boundary, then fill it with identity and durable merge semantics.

**Motivation:** Surfaces and adapters must call one Kernel. A package-only Kernel without identity/merge is not the Kernel defined by the architecture.

**Dependencies:** Phase 1.

**Expected PR slices:**

- **PR003** — Kernel public boundary and invariants (deliberately thin)
- **PR004** — Identity and reconciliation
- **PR005** — Durable contribution merge (advances graph head)

**Exit criteria:**

- Adapters can only access Kernel/projection contracts (no storage-path graph selection).
- Identity resolution and merge rules live in Kernel APIs, not in Plan/Ingest UI.
- Authoring merges and extraction merges share merge semantics.
- Each slice states which existing modules are retained, rewritten, or deleted.

---

## Phase 3 — Initial Campaign Supergraph materialization

**Objective:** Produce the first **real**, populated persistent campaign union from already supported ingested source artifacts — before Projection Engine and Plan migration.

**Motivation:** Storage + merge APIs without a real graph leave Plan migration circular: Plan needs a useful graph, but the useful graph was previously scheduled after Plan. A multi-source fixture is not a substitute for the first ingested campaign union.

**Dependencies:** Phase 2 (especially PR005).

**Expected PR slices:** Tracker **PR006**.

**Demolition owned here:** Remove or isolate production dependence on preview union stores and named preview sources for **runtime graph availability**. Runtime must load the campaign graph head, not a preview fixture.

**Exit criteria:**

- Initial supported source domains are defined and documented.
- Real ingested contributions are imported/reprocessed into the campaign store.
- Identities are reconciled across multiple sessions under global identity.
- At least one non-recap / worldbuilding source domain is included if currently available.
- Campaign graph head is established and advanced.
- Coverage + validation report exists for the initial union.
- Reconstruction or incremental continuation is repeatable.
- A real campaign graph loads **without** preview source, eval fixture, explicit manifest, or latest-session selector as the selection mechanism.
- Provenance identifies contributing source artifacts for durable claims.
- Projection work (Phase 4) uses this graph as its acceptance fixture.
- Plan migration (Phase 5) can be tested against genuinely ingested campaign memory.

---

## Phase 4 — Projection Engine

**Objective:** Session (and other foci) are lenses over the **already materialized** Campaign Supergraph.

**Motivation:** Plan dogfood blocked on graph-context mismatch. Projection must read the persistent graph head with explicit focus — never latest-ingest.

**Dependencies:** Phase 3 (real populated graph).

**Expected PR slices:** Tracker **PR007**.

**Demolition owned here:** Replace graph-preview selection APIs with the persistent campaign graph read API. No production `preview-source`, `latest-ingest`, `recap-only` backend, or store/manifest path selectors in surface-facing contracts.

**Exit criteria:**

- Projection request includes campaign + focus + projection mode; always reads Campaign Supergraph graph head.
- Focus overlay highlights session-anchored evidence without cloning identity.
- Play combat/encounter behavior is expressible as a Play lens, not a separate graph.
- Unavailable projection reports honest diagnostics for requested focus — not memory-session / latest-ingest framing.
- Search over projected node views is a first-class read affordance.
- Acceptance tests use the Phase 3 real campaign graph (not preview fixtures as the product backend).

---

## Phase 5 — Surface integration

**Objective:** Plan (then Play, including combat lenses) consume projections only; no surface-owned graph semantics.

**Motivation:** Object cards and dogfood harnesses exist. They need the real projection from Phase 3–4. Q&A waits until cards are useful against real memory.

**Dependencies:** Phase 4.

**Expected PR slices:** Tracker **PR008** (Plan), **PR009** (Play), Build follow-ons as needed.

**Demolition owned here (Plan):** Delete the session-derived `useLatestGraphIngest` path once Plan uses the real projection.

**Suggested Plan sub-sequence:**

1. Wire Plan to Projection Engine / production graph-context contract.
2. Rerun object-card usefulness dogfood against the Phase 3 campaign graph.
3. Only then: Plan-scoped graph-memory Q&A (later / retrieval-backed).

**Exit criteria:**

- `/plan` loads a real campaign projection for intended prep focus from the campaign graph head.
- Object-card dogfood can judge usefulness honestly against ingested memory.
- Play uses the same projection contracts; combat is a Play lens.
- No new surface-local graph stores; obsolete Plan latest-ingest path removed.

---

## Phase 6 — Multi-source ingestion expansion

**Objective:** Expand artifact families writing into the same Campaign Supergraph beyond the initial materialization set.

**Motivation:** Phase 3 creates the first real union. Phase 6 grows coverage (more sessions, prep, additional worldbuilding, future families) without creating multi-graph.

**Dependencies:** Phases 2–3; extraction quality path graduated into runtime write path as needed.

**Expected PR slices:** Follow-on ingest PRs after **PR006**; graph-first recap ingest; additional worldbuilding/prep domains.

**Exit criteria:**

- Additional source domains contribute durable nodes/edges to the same campaign store.
- Graph-first ingest does not require breadcrumb/session-memory gates.
- Provenance remains inspectable per source domain.
- Graph head advances without preview-store dependence.

---

## Phase 7 — Graph-native retrieval

**Objective:** Retrieval admits evidence through graph identity and relationships; lexical/vector helpers are subordinate.

**Dependencies:** Phases 4–5; stable projection/Kernel read APIs.

**Expected PR slices:** Tracker **PR010**.

**Exit criteria:**

- Graph-backed retrieval API exists for surfaces/agents.
- Transitional corpus-index / live-query paths are explicitly marked transitional or removed where replaced.
- Answers cite graph-admitted evidence with source anchors.

---

## Phase 8 — Agent backend

**Objective:** Agent Interaction uses the Campaign Supergraph + retrieval as its memory backend.

**Dependencies:** Phase 7.

**Expected PR slices:** Tracker **PR011**.

**Exit criteria:**

- Agent context assembly requests projected/admissible graph context.
- Agents cannot silently mutate the supergraph.
- Hermes-shaped transitional drawers are not the architecture target.

---

## Phase 9 — Living campaign memory + obsolete-path cleanup

**Objective:** Continuous correctable campaign memory at the table, and deletion of dead dual-architecture runtime.

**Dependencies:** Phases 5–8.

**Expected PR slices:** Product hardening (dogfood-driven); tracker **PR012** cleanup closeout.

**Demolition owned here (closeout):** Delete dead adapters, routes, environment defaults, and fixture-specific runtime branches after replacements have landed.

**Exit criteria:**

- Prep and play share one campaign memory backend.
- Corrections flow through Graph Review / write path and reappear in projections.
- Session focus remains a lens throughout.
- Preview/latest-ingest/store-path production paths are gone, not merely unused.

---

## Relationship to recent Plan object-card work

| Prior framing | Role under this roadmap |
|---|---|
| GitHub PR316–PR320 GraphObjectCard path | Substrate for Phase 5 Plan migration (keep) |
| GitHub PR321 dogfood harness + blocker discovery | Evidence that real graph context is required |
| Informal “plan graph-context” | Absorbed into Phase 4 **PR007** + Plan wiring **PR008** |
| Informal “continue dogfood” | Phase 5 after Phase 3 materialization |
| Informal “Plan Q&A” | After useful cards; prefer Phase 7 retrieval-backed |

Do not resume Q&A as the next architecture move. Materialize the real campaign union, then project, then migrate Plan.

---

## Non-goals for this roadmap document

- Implementing storage, Kernel, materialization, or UI in the Phase 0 PR
- Preserving preview/session-graph abstractions for compatibility
- Treating eval ladder documents or older handoffs as execution authority
- Treating a multi-source fixture as the first real campaign union
