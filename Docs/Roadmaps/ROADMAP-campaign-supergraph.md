# Roadmap — Campaign Supergraph

**Status:** Canonical implementation roadmap  
**Date:** 2026-07-10  
**Updated:** 2026-07-11 (PR006A–C split; Phase 3 inventory → contribution → publication)  
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**PR slices:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)  
**Document audit:** [`Docs/Reports/graph-document-audit.md`](../Reports/graph-document-audit.md)

This roadmap describes **implementation milestones**, not experiments. Phases are sequential where noted; PR slices inside a phase may parallelize only when dependencies allow.

**This document + the PR tracker are the only ACTIVE AUTHORITY for Campaign Supergraph sequencing.** Older handoffs cannot override them.

**Supersedes as roadmap authority:** `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`, `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md`, and overlapping checklist roadmaps called out in the audit.

**Foundational decisions locked in architecture (do not re-litigate in implementation PRs):**

- Tenancy **Model B** — World Supergraph with campaign scopes
- Corpus prose vs durable authored assertions / identity decisions
- GraphContribution supersession / retraction / replay
- Immutable revisions + atomic graph head
- Mandatory epistemic / temporal / visibility metadata
- Explicit identity outcomes including split/unmerge
- GitHub repo docs are canonical; Project Sources are context inputs only (PR005A)
- Agents are not privileged graph writers — tool categories + preview → GM confirm (PR005B); see [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](../Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md)

---

## Global conventions (all phases)

### Deletion at replacement time

When a replacement becomes production-ready, the replaced production path is **deleted in the same PR** unless a named remaining consumer prevents deletion.

Every implementation PR must enumerate:

```text
Retained temporarily:
Reason:
Remaining consumer:
Required deletion PR:
```

No path survives merely because PR012 exists. PR012 is a leftover safety net.

### Integrity reporting

Machine-readable integrity/health reporting is cross-cutting (architecture §18). Phases 1, 2, 3, and 4 each extend the report surface; the first real graph must expose it, not only a markdown audit.

---

## Phase 0 — Architecture reset

**Objective:** Establish one coherent architectural foundation before more graph systems are built.

**Motivation:** Plan object-card dogfood proved the card path while exposing session-keyed latest-ingest as the wrong graph question. Continuing on preview/session-centric docs would deepen conceptual debt.

**Dependencies:** None.

**Expected PR slices:** Tracker **PR001**.

**Exit criteria:**

- Canonical architecture, roadmap, and PR tracker exist.
- Graph-document audit published with authority vs reference vs historical classifications.
- Supersedes architecture docs archived with stubs.
- Forward-only production contract bans latest-ingest / preview-source / store-path graph selection.
- Combat is folded into Play in canonical docs.
- Tenancy, authority, contribution lifecycle, head invariants, epistemic metadata, and identity outcomes are decided in the architecture document.

---

## Phase 1 — Persistent World Supergraph storage

**Objective:** One durable World Supergraph store per `worldId` with immutable revisions and an atomic graph-head contract.

**Motivation:** Surfaces need a real memory backend. Preview unions keyed to `session-N` latest ingest cannot express multi-session + shared worldbuilding memory. Campaign 1 and Campaign 2 already share Eldyrwild hubs.

**Dependencies:** Phase 0.

**Expected PR slices:** Tracker **PR002**.

**Demolition owned here (start):** Isolate production code from treating named preview sources / preview union stores as the campaign graph identity. Full deletion completes when replacement is production-ready (same PR or named consumer deferral).

**Exit criteria:**

- Persistent World Supergraph can be loaded/validated for a `worldId` without `use_latest_graph_ingest` for a single `session-X`.
- Graph-head contract satisfies architecture §7 (immutable revision, atomic publish, failed write leaves prior head, parent linkage, reader coherence, rebuild/rollback path).
- Multi-source + multi-campaign-scoped nodes can coexist in one store (fixture proof is necessary but **not sufficient** — Phase 3 populates the real union).
- Surfaces are not required to know preview-run paths.
- Integrity report stub exists (at least head revision + load/validate status).

---

## Phase 2 — Graph Kernel

**Objective:** Establish the Kernel public boundary, then fill it with identity outcomes and durable contribution merge semantics.

**Motivation:** Surfaces and adapters must call one Kernel. A package-only Kernel without identity/merge/contribution lifecycle is not the Kernel defined by the architecture.

**Dependencies:** Phase 1.

**Expected PR slices:**

- **PR003** — Kernel public boundary and invariants (deliberately thin; **enforceable** import/API guards)
- **PR004** — Identity and reconciliation (outcomes, provisional, split/unmerge)
- **PR005** — Durable contribution merge (IDs, idempotency, supersession, retraction, rebuild, correction replay, head advancement)

**Exit criteria:**

- Adapters can only access Kernel/projection contracts (enforced, not aspirational).
- Identity resolution outcomes and merge/retract rules live in Kernel APIs, not in Plan/Ingest UI.
- Authoring merges and extraction merges share contribution/merge semantics.
- Approved corrections survive reconstruction.
- Integrity report includes contribution and identity diagnostics.
- Each slice states which existing modules are retained, rewritten, or deleted — and any temporary retains name their deletion PR.

---

## Phase 2.5 — Source Reanchor and Agent Tool Contract Bridge

**Objective:** Prevent stale Project Sources, historical architecture docs, research notes, and proposal-only handoffs from directing implementation — then define the agent/tool and authored-prep contracts before materialization.

**Motivation:** After PR005, jumpstarts and Project Sources can drift ahead of (or contradict) the tracker. Agents must re-anchor on GitHub authority before designing Hermes tool contracts. Separately, agent/tool design must not invent a second memory system or pull Hermes runtime ahead of PR006/PR007.

**Dependencies:** Phase 2 (especially PR005).

**Expected PR slices:**

- **PR005A** — Context Audit + Source Reanchor (docs/process)
- **PR005B** — Agent Tool Contract + Authored Prep Contributions (docs/design)

**These are docs/design bridge slices.** They do **not** populate the graph, implement Projection Engine, or implement runtime Agent Interaction tooling. They preserve **PR006** as the first real materialization slice.

**Exit criteria:**

- Tracker and roadmap name the PR005A / PR005B split; PR006–PR012 numbering unchanged.
- Project Sources boundary is explicit: GitHub wins; Project Sources are context inputs; prepared replacements are inactive until uploaded.
- Stale/superseded docs have banners or audit classifications that prevent accidental authority.
- Agent tool categories and authored-prep lifecycle are documented in [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](../Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md) as contracts for later **PR011** — not as runtime work in this phase.
- PR006 remains focused on named acceptance-corpus materialization.

---

## Phase 3 — Initial World Supergraph materialization

**Objective:** Produce the first **real**, **representative** persistent union from a **named acceptance corpus** — before Projection Engine and Plan migration.

**Motivation:** Storage + merge APIs without a useful graph leave Plan migration circular. A multi-source fixture is not a substitute. “Real” is not the same as “representative.” The closed #330/#331 monolith showed inventory, contribution conversion, and publication must ship as separate reviewable slices.

**Dependencies:** Phase 2 and completion of PR005A / PR005B, unless explicitly waived by the operator. Phase 2.5 is docs/design only and must not dilute Phase 3 into tool runtime — but docs-only does **not** mean optional when the tracker sequences those bridges before materialization.

**Expected PR slices:**

- **PR006A** — Pinned acceptance-corpus inventory (explicit paths, hashes, provenance IDs, and world/campaign authority metadata only)
- **PR006B** — Canonical C2 recap sources → `GraphContribution`s via existing Kernel contracts
- **PR006C** — Full named-corpus publication, rebuild, and coverage proof

Do **not** renumber PR007–PR012. GitHub #330/#331 were closed unmerged and are not prerequisites.

**Demolition owned here:** Remove or isolate production dependence on preview union stores and named preview sources for **runtime graph availability**. Runtime must load the world graph head, not a preview fixture. Delete replaced paths in the publication slice (PR006C) unless a named consumer remains.

**Named acceptance corpus (normative for PR006A–C):**

| Family | Requirement |
|---|---|
| World | Eldyrwild (`worldId` for `corpus/eldyrwild-markdown`) |
| Primary campaign scope | Longmont **Campaign 2** (Plan dogfood consumer) |
| Recaps | All **canonical** Campaign 2 session recaps **Sessions 1–23** (planning cutoff for North Gate / Session 23–adjacent Plan dogfood) |
| PC identity | All currently approved Campaign 2 PC hub packages |
| Worldbuilding (required) | Mirathorn and Mireward world hubs under `Elderwyld/Cities and Towns/` (not optional) |
| Campaign support | Pinned Campaign 2 NPC / faction / statblock sources, explicitly scoped to `longmont-c2` |
| World support | Pinned Mirathorn / Mireward support sources, explicitly world-scoped (`campaign_scope: null`) |
| Mechanical | Statblock / encounter artifacts required by the initial Plan dogfood |
| Authored corrections | All approved Graph Review authored assertions / identity decisions for this scope that exist at materialization time |

**Exit criteria:**

- Requested source inventory published before/with the run.
- Successfully ingested vs skipped sources listed with reasons.
- Entity/edge counts by source domain; unresolved identities; rejected contributions; evidence coverage.
- Unsupported projection requirements called out explicitly.
- Specific statement of what Plan can and cannot trust.
- Identities reconciled under world-global identity with campaign-scoped chronology.
- Worldbuilding hubs above are included (required).
- Graph head established and advanced; reconstruction/replay proven with contribution semantics.
- Machine-readable health/coverage report exists.
- Loads **without** preview source, eval fixture, explicit manifest, or latest-session selector as the selection mechanism.
- Projection work (Phase 4) uses this graph as its acceptance fixture.
- Plan migration (Phase 5) can be tested against genuinely ingested campaign memory.

---

## Phase 4 — Projection Engine

**Objective:** Campaign + session (and other foci) are lenses over the **already materialized** World Supergraph, revision-pinned, with admissibility enforcement.

**Motivation:** Plan dogfood blocked on graph-context mismatch. Projection must read the persistent graph head with explicit campaign + focus — never latest-ingest.

**Dependencies:** Phase 3 (real populated graph).

**Expected PR slices:** Tracker **PR007**.

**Demolition owned here:** Replace graph-preview selection APIs with the persistent world graph read API. Delete replaced production selectors in this PR unless a named consumer remains.

**Exit criteria:**

- Projection request includes `worldId` + `campaignId` + focus + projection mode; always reads World Supergraph head (or explicit revision pin).
- Focus overlay highlights session-anchored evidence without cloning identity.
- Visibility / epistemic admissibility tests pass (no GM-secret leakage via adjacency).
- Play combat/encounter behavior is expressible as a Play lens, not a separate graph.
- Unavailable projection reports honest diagnostics — not memory-session / latest-ingest framing.
- Search over projected node views is a first-class read affordance.
- Integrity/diagnostics include projection truncation and admissibility denial aggregates.
- Acceptance tests use the Phase 3 real graph (not preview fixtures as the product backend).

---

## Phase 5 — Surface integration

**Objective:** Plan (then Play, including combat lenses) consume projections only; no surface-owned graph semantics.

**Motivation:** Object cards and dogfood harnesses exist. They need the real projection from Phase 3–4. Q&A waits until cards are useful against real memory.

**Dependencies:** Phase 4.

**Expected PR slices:** Tracker **PR008** (Plan), **PR009** (Play), Build follow-ons as needed.

**Demolition owned here (Plan):** Delete the session-derived `useLatestGraphIngest` path in the same PR that wires real projection (no deferral to PR012 without a named consumer).

**Suggested Plan sub-sequence:**

1. Wire Plan to Projection Engine / production graph-context contract.
2. Rerun object-card usefulness dogfood against the Phase 3 graph.
3. Only then: Plan-scoped graph-memory Q&A (later / retrieval-backed).

**Exit criteria:**

- `/plan` loads a real campaign projection for intended prep focus from the world graph head.
- Object-card dogfood can judge usefulness honestly against ingested memory.
- Play uses the same projection contracts; combat is a Play lens.
- No new surface-local graph stores; obsolete Plan latest-ingest path removed.

---

## Phase 6 — Multi-source ingestion expansion

**Objective:** Expand artifact families writing into the same World Supergraph beyond the initial materialization set (more sessions, Campaign 1 chronology as needed, additional world hubs, prep families).

**Motivation:** Phase 3 creates the first representative union for Plan. Phase 6 grows coverage without creating multi-graph or per-campaign copied world entities.

**Dependencies:** Phases 2–3; extraction quality path graduated into runtime write path as needed.

**Expected PR slices:** Follow-on ingest PRs after **PR006**; graph-first recap ingest; additional worldbuilding/prep domains.

**Exit criteria:**

- Additional source domains contribute durable assertions to the same world store.
- Graph-first ingest does not require breadcrumb/session-memory gates.
- Contribution supersession/retraction remains correct as sources expand.
- Provenance remains inspectable per source domain.
- Graph head advances without preview-store dependence.

---

## Phase 7 — Graph-native retrieval

**Objective:** Retrieval admits evidence through graph identity and relationships; lexical/vector helpers are subordinate; admissibility preserved.

**Dependencies:** Phases 4–5; stable projection/Kernel read APIs.

**Expected PR slices:** Tracker **PR010**.

**Exit criteria:**

- Graph-backed retrieval API exists for surfaces/agents.
- Transitional corpus-index / live-query paths are explicitly marked transitional or removed where replaced (deletion-at-replacement rule).
- Answers cite graph-admitted evidence with source anchors and respect visibility.

---

## Phase 8 — Agent Context + Tool Runtime

**Objective:** Agent Interaction uses the World Supergraph + retrieval as its memory backend, and exposes governed tools that read, draft, preview-write, or confirm-commit — never silent graph mutation. Normative contract: [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](../Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md) (authored in PR005B; **implemented here**).

**Dependencies:** Phase 7.

**Expected PR slices:** Tracker **PR011** (Agent Context + Tool Runtime).

**Exit criteria:**

- Agent context assembly requests projected/admissible graph context with revision pins.
- Typed tool capabilities match PR005B / the contract (`read_only`, `draft_only`, `preview_write`, `confirm_commit`, `admin_diagnostic`).
- Agents cannot silently mutate the supergraph; durable writes require proposal-bound preview → explicit GM confirm through Kernel paths.
- Hermes long-term/session memory and transitional drawers are not campaign canon and are not the architecture target.

---

## Phase 9 — Living campaign memory + leftover cleanup

**Objective:** Continuous correctable campaign memory at the table, and deletion of any leftover dual-architecture runtime.

**Dependencies:** Phases 5–8.

**Expected PR slices:** Product hardening (dogfood-driven); tracker **PR012** cleanup **safety net** only.

**Demolition owned here (closeout only):** Delete leftovers that earlier PRs could not remove because of named remaining consumers — not the main demolition burden.

**Exit criteria:**

- Prep and play share one world memory backend under campaign scope.
- Corrections flow through Graph Review / write path, survive rebuild, and reappear in projections.
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

Do not resume Q&A as the next architecture move. Materialize the named acceptance corpus, then project, then migrate Plan.

---

## Non-goals for this roadmap document

- Implementing storage, Kernel, materialization, or UI in the Phase 0 PR
- Preserving preview/session-graph abstractions for compatibility
- Treating eval ladder documents or older handoffs as execution authority
- Treating a multi-source fixture as the first real campaign union
- Deferring tenancy / authority / contribution / head / epistemic decisions into PR002+
