# Roadmap — Campaign Supergraph

**Status:** Canonical implementation roadmap  
**Date:** 2026-07-10  
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**PR slices:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)  
**Document audit:** [`Docs/Reports/graph-document-audit.md`](../Reports/graph-document-audit.md)

This roadmap describes **implementation milestones**, not experiments. Phases are sequential where noted; PR slices inside a phase may parallelize when dependencies allow.

**Supersedes as roadmap authority:** `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`, `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md`, and overlapping checklist roadmaps called out in the audit.

---

## Phase 0 — Architecture reset

**Objective:** Establish one coherent architectural foundation before more graph systems are built.

**Motivation:** Dogfood of Plan object cards (PR316–PR321 era) proved the card path while exposing that Plan still asks the wrong graph question (session-keyed latest-ingest vs campaign/world memory). Continuing implementation on preview/session-centric docs would deepen conceptual debt.

**Dependencies:** None.

**Expected PR slices:** Tracker **PR001** (this documentation reset).

**Exit criteria:**

- Canonical architecture, roadmap, and PR tracker exist.
- Graph-document audit published; superseded architecture docs archived with banners.
- Cross-references on active docs point at `ARCHITECTURE-campaign-supergraph.md`.
- A new contributor can answer the architecture FAQ without reading experimental ladder docs.

---

## Phase 1 — Persistent Campaign Supergraph

**Objective:** One durable graph store per campaign that is not a session-owned preview artifact.

**Motivation:** Surfaces need a real memory backend. Preview unions keyed to `session-N` latest ingest cannot express “sessions 21–23 + worldbuilding.”

**Dependencies:** Phase 0.

**Expected PR slices:** Tracker **PR002** (storage), related load/validate seams.

**Exit criteria:**

- Persistent Campaign Supergraph can be loaded/validated for a campaign independently of “latest preview ingest for session-X.”
- Worldbuilding and multi-session contributions can coexist in one store (even if ingestion UX is still limited).
- No surface is required to treat preview-run identity as campaign memory identity.

---

## Phase 2 — Graph Kernel

**Objective:** Harden the durable semantic core: model, identity, evidence, merge, validation.

**Motivation:** Surfaces and adapters must call one Kernel. Identity and evidence must not be reinvented in UI or per-route adapters.

**Dependencies:** Phase 1 storage seams (may overlap early Kernel contract work).

**Expected PR slices:** Tracker **PR003** (Kernel), **PR004** (identity), **PR005** (persistent merge pipeline).

**Exit criteria:**

- Identity resolution and merge rules live in Kernel APIs, not in Plan/Ingest UI.
- Evidence/source-domain contracts are the only provenance language for durable claims.
- Authoring merges (Graph Review) and extraction merges share the same merge semantics.
- Cross-class collision policy is explicit and testable.

---

## Phase 3 — Projection Engine

**Objective:** Session (and other foci) are lenses over the Campaign Supergraph.

**Motivation:** Plan dogfood blocked on graph-context mismatch. Projection must accept an explicit focus + mode, not silently mean “latest ingest for derived memorySession.”

**Dependencies:** Phase 1; Kernel read APIs from Phase 2.

**Expected PR slices:** Tracker **PR006** (Projection Engine), including Plan graph-context contract.

**Exit criteria:**

- Projection request includes campaign + focus + projection mode.
- Focus overlay highlights session-anchored evidence without cloning identity.
- Unavailable projection reports honest diagnostics (requested context), not “memory session” framing as architecture.
- Search over projected node views is a first-class read affordance.

---

## Phase 4 — Surface integration

**Objective:** Plan (then Play and others) consume projections only; no surface-owned graph semantics.

**Motivation:** Object cards, chip insert, relationship traversal, and dogfood already exist as UI. They need a real projection. Q&A must wait until cards are useful against real memory.

**Dependencies:** Phase 3.

**Expected PR slices:** Tracker **PR007** (Plan), **PR008** (Play), follow-on Combat/Build/Agent as needed.

**Suggested Plan sub-sequence (product pressure):**

1. Wire Plan to Projection Engine / graph-context contract (unblocks dogfood).
2. Rerun object-card usefulness dogfood against real campaign projection.
3. Only then: Plan-scoped graph-memory Q&A.

**Exit criteria:**

- `/plan` loads a real campaign projection for intended prep focus (e.g. recent sessions + worldbuilding), not only `session-(live-1)` latest ingest.
- Object-card dogfood can judge usefulness honestly.
- Play (and later surfaces) use the same projection contracts.
- No new surface-local graph stores.

---

## Phase 5 — Multi-source ingestion

**Objective:** Recaps, worldbuilding, prep, and future artifact families all write into the same Campaign Supergraph.

**Motivation:** The graph is only as useful as its sources. Multi-source must not create multi-graph.

**Dependencies:** Phases 1–2; extraction quality path (category pipeline or successor) graduated into runtime write path.

**Expected PR slices:** Ingestion PRs under tracker follow-ons after **PR005**; graph-first recap ingest; worldbuilding ingest.

**Exit criteria:**

- At least two source domains contribute durable nodes/edges to one campaign store.
- Graph-first ingest does not require breadcrumb/session-memory gates.
- Provenance remains inspectable per source domain.

---

## Phase 6 — Graph-native retrieval

**Objective:** Retrieval admits evidence through graph identity and relationships; lexical/vector helpers are subordinate.

**Motivation:** Prep Q&A and agents need relationship-aware, provenance-preserving recall — not a second memory product.

**Dependencies:** Phases 3–4; stable projection/Kernel read APIs.

**Expected PR slices:** Tracker **PR009**.

**Exit criteria:**

- Graph-backed retrieval API exists for surfaces/agents.
- Transitional corpus-index / live-query paths are explicitly marked transitional or removed where replaced.
- Answers can cite graph-admitted evidence with source anchors.

---

## Phase 7 — Agent backend

**Objective:** Agent Interaction uses the Campaign Supergraph + retrieval as its memory backend.

**Motivation:** Agents are surfaces with tools. Chat history is not campaign memory.

**Dependencies:** Phase 6.

**Expected PR slices:** Tracker **PR010**.

**Exit criteria:**

- Agent context assembly requests projected/admissible graph context.
- Agents cannot silently mutate the supergraph.
- Hermes-shaped transitional drawers are not the architecture target.

---

## Phase 8 — Living campaign memory

**Objective:** Continuous, correctable campaign memory used at the table across prep and play.

**Motivation:** End state: the GM trusts the graph as the working memory layer, with clear escalation when memory is wrong.

**Dependencies:** Phases 4–7.

**Expected PR slices:** Product hardening PRs (dogfood-driven); not a single tracker ID.

**Exit criteria:**

- Prep and play share one campaign memory backend.
- Corrections flow through Graph Review / write path and reappear in projections.
- Session focus remains a lens throughout.

---

## Relationship to recent Plan object-card work

| Prior framing | Role under this roadmap |
|---|---|
| PR316–PR320 GraphObjectCard path | Substrate for Phase 4 (keep) |
| PR321 dogfood harness + blocker discovery | Evidence that Phase 3 graph-context is required |
| “PR322 plan graph-context” | Absorbed into Phase 3 / tracker **PR006** (+ Plan wiring in **PR007**) |
| “PR323 continue dogfood” | Phase 4 Plan dogfood after projection works |
| “PR324 Plan Q&A” | Phase 4 / Phase 6 — only after useful cards against real projection |

Do not resume Q&A as the next architecture move. Fix graph context and projection first.

---

## Non-goals for this roadmap document

- Implementing storage, Kernel, or UI in the Phase 0 PR
- Preserving preview/session-graph abstractions for compatibility
- Treating eval ladder documents as execution authority
