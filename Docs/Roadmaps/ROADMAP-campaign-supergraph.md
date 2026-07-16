# Roadmap — Campaign Supergraph

**Status:** Canonical implementation roadmap
**Date:** 2026-07-10
**Updated:** 2026-07-16 — Hermes product re-anchor accepted; Rung 5 live trial 1 passed, aggregate three-trial gate pending
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**PR slices:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)
**Hermes goal anchor:** [`Docs/Design/ANCHOR-hermes-campaign-sensemaking-goal.md`](../Design/ANCHOR-hermes-campaign-sensemaking-goal.md)

This roadmap describes Campaign Supergraph infrastructure milestones. This
document and the PR tracker remain sequencing authority for graph infrastructure.
The Hermes Campaign Authoring Foundation plan and its re-anchor record govern the
separate product/authoring gate. Older handoffs, experiments, backlog entries,
Project Sources, and historical Agent Interaction documents may explain why
decisions were made, but they cannot override either active authority.

## Locked architecture decisions

- Tenancy is **Model B**: one World Supergraph with campaign scopes.
- Published revisions are immutable and the graph head advances atomically.
- `GraphContribution` supersession, retraction, replay, and governed identity decisions are durable.
- Epistemic, temporal, visibility, provenance, and campaign-scope metadata are mandatory.
- Source artifacts remain prose/evidence authority; the World Supergraph is durable materialized knowledge state.
- Agents are not privileged writers. Durable changes require typed tools and preview → proposal-bound GM confirmation.
- Runtime graph selection never uses latest-ingest, preview-source, manifest path, run directory, or mutable store path.
- **Agent factual discovery is graph-only.** Markdown is reachable only through source anchors admitted by graph retrieval; it is not a parallel search/fallback plane.

## Global conventions

### Deletion at replacement time

When a replacement becomes production-ready, the replaced path is deleted in the same PR unless a named remaining consumer prevents deletion. Every implementation PR must state:

```text
Retained temporarily:
Reason:
Remaining consumer:
Required deletion PR:
```

PR012 is a leftover safety net, not the default owner of deferred demolition.

### Graph-only retrieval boundary

For Agent Interaction and other graph-aware consumers:

1. Discovery begins from a revision-pinned World Supergraph projection or graph-retrieval API.
2. Retrieval may return graph objects, attributes, relationships, paths, and graph-admitted source anchors.
3. A source reader may open only those admitted anchors, with bounded excerpts and stable evidence locators.
4. No product fallback may search manifests, corpus indexes, arbitrary repository Markdown, or lexical/vector stores outside graph admission.
5. A graph miss or evidence gap produces an explicit abstention and a coverage-gap diagnostic. It does not trigger hidden Markdown search.

This does **not** demote source documents. It makes the graph the routing/admission plane and source anchors the evidence plane.

## Current critical path

```text
DONE  PR006D2  Publish Eldyrwild C2 World Supergraph
DONE  PR007A   Revision-pinned projection/read snapshot
DONE  PR008A   Plan World Graph object-card migration
DONE  PR008B   Agent Interaction receives revision-pinned graph query context
DONE  PR010A   Graph retrieval contract and source-anchor admission
DOING PR010B   Hermes graph-retrieval dogfood
BLOCKED PR011  Agent Context + governed tool runtime
```

PR009 Play migration may proceed independently after PR008 lessons. Multi-source ingestion expansion can also continue without changing the graph-only Agent Interaction direction.

PR010B is decomposed into independently useful rungs:

```text
DONE    PR010B Rung 1 — graph-only dispatcher (#350)
DONE    PR010B Rung 2 — model-visible catalog and adapter (#351)
DONE    PR010B Rung 3 — embedded Hermes graph-agent turn (#352)
DONE    PR010B Rung 4A — process-isolated host (#353)
DONE    PR010B Rung 4B — single-turn backend product cutover (#354)
DONE    PR010B Rung 4C — Plan evidence presentation and completed-turn persistence (#355)
PASS*   PR010B Rung 5 — same-thread object continuity through bounded visible-prose replay
LATER   PR010B Rung 6 — durable Hermes session-pointer and reload/process lifecycle
LATER   PR010B Rung 7 — cumulative product acceptance and replaced-path demolition
```

`PASS*` means the first live Tripod continuity trial passed; the aggregate
three-trial dogfood gate is still open. The current Hermes branch contains the
bounded Rung 5 implementation and its trust-boundary tests, but it is not yet
the accepted Campaign Supergraph `main` path. The re-anchor retains that work as
S0 infrastructure and does not authorize Rung 6 or additional graph-tool
expansion before the remaining live Rung 5 trials and the Hermes Phase 0/S1
gates are complete.

---

## Phase 0 — Architecture reset

**Status:** Done via PR001 / GitHub #322.

Established the canonical architecture, roadmap, tracker, authority model, graph-head invariants, Model B tenancy, and deletion-at-replacement rule.

## Phase 1 — Persistent World Supergraph storage

**Status:** Done via PR002 / GitHub #323.

Established durable per-world storage, immutable revisions, atomic graph head, validation, rollback/rebuild seams, and separation from preview-run identity.

## Phase 2 — Graph Kernel

**Status:** Done via PR003–PR005 / GitHub #324–#327.

Established the enforceable Kernel boundary, identity outcomes including split/unmerge, durable contribution merge, supersession/retraction/replay, and correction persistence.

## Phase 2.5 — Source reanchor and agent contract bridge

**Status:** Done via PR005A/PR005B / GitHub #328–#329.

Established repository authority, Project Sources boundaries, typed agent capability categories, authored-prep lifecycle, and the no-privileged-writer rule. Runtime tooling remained intentionally deferred.

## Phase 3 — Initial World Supergraph publication

**Status:** Core publication done; bootstrap UI deferred.

PR006A–PR006D2 repaired semantic assertion identity, approved the initial Eldyrwild C2 contribution bundle, initialized the world atomically, and activated the published graph. PR006D3 `/ingest` activation UI remains deferred because it is not a Plan or Hermes dogfood dependency.

## Phase 4 — Projection Engine

**Status:** Done via PR007A / GitHub #339.

The production read contract accepts `worldId`, `campaignId`, focus, projection mode, admissibility, and optional revision pin. It always reads a coherent World Supergraph revision and fails closed on visibility or integrity errors.

## Phase 5 — Surface integration

**Status:** Plan read path and Agent query context done; Play remains.

- **PR008A / GitHub #340:** Plan object cards, relationship traversal, reference insertion, and dogfood diagnostics read the World Graph projection. The Plan latest-ingest path was removed.
- **PR008B / GitHub #342:** Agent Interaction receives deterministic, revision-pinned graph query context alongside the existing transitional answer paths.
- **PR009:** Play consumes the same projection contracts, including combat/encounter as a Play lens.

PR008B proved that attaching graph context is not enough. The Hermes agent must actively retrieve from the graph, preserve thread identity, and use source anchors without falling back to unrelated Markdown discovery.

## Phase 6 — Multi-source ingestion expansion

**Objective:** Grow the same World Supergraph with additional sessions, worldbuilding, Campaign 1 chronology as needed, prep artifacts, and other source families.

**Exit criteria:**

- New domains contribute through `GraphContribution` and Kernel publication.
- Provenance, supersession, retraction, and identity remain correct.
- Graph head advances without preview-store dependence.
- Agent retrieval sees new material only after it is represented in the graph.

Phase 6 may run alongside PR010 work. Missing coverage is repaired through ingestion/graph contribution, not masked by agent-side Markdown fallback.

## Phase 7 — Graph-native retrieval

**Objective:** Make the World Supergraph the sole discovery and evidence-admission plane for factual Agent Interaction.

### PR010A — Graph retrieval contract

**Status:** Done via GitHub #346–#349.

**Purpose:** Provide deterministic, revision-pinned retrieval primitives over projected graph state before introducing the Hermes agent loop.

**Required capabilities:**

- Search projected objects by label, alias, kind, attributes, and relationship text.
- Resolve an exact graph object by durable ID.
- Traverse bounded neighborhoods with endpoint-relative relationships and admissibility filtering.
- Return attributes, relationship paths, focus relevance, and revision metadata.
- Return source anchors/evidence locators attached to admitted graph assertions.
- Read a bounded source excerpt only through an anchor returned by the same retrieval result.
- Return explicit `enough`, `partial`, `empty`, `denied`, `truncated`, and `unavailable` outcomes.
- Expose coverage gaps without consulting another retrieval system.

**Non-goals:** LLM orchestration, chat sessions, graph writes, arbitrary document search, manifest lookup, repo-wide Markdown search, or a compatibility fallback.

**Exit criteria:**

- Tripod Null-Calf can be found from a natural-language prep question.
- Its North Gate relationships and prep-relevant connected objects can be traversed from the same pinned revision.
- Returned claims retain source anchors and visibility metadata.
- A graph miss remains a graph miss; tests prove no fallback reader/search is invoked.

### PR010B — Hermes graph-retrieval dogfood

**Status:** Doing — Rung 1–4C complete (#350–#355); Rung 5 live validation is in progress with trial 1 passed. PR011 remains blocked until PR010B is cumulatively accepted. PR009 remains an independent parallel lane.

**Purpose:** Run Hermes as the actual conversational agent over PR010A read tools and dogfood multi-turn graph-grounded prep in the existing Agent Interaction surface.

**Rung sequence:**

- **Rung 1 (DONE / #350):** Strict graph-only Hermes read-tool dispatcher over the five PR010A operations.
- **Rung 2 (DONE / #351):** Model-visible tool catalog and JSON-string execution adapter derived from the same Rung 1 registry metadata.
- **Rung 3 (DONE / #352):** Embedded in-process Hermes `AIAgent` turn with packaged `dungeonbuddy_graph` plugin, optional caller-owned history, and typed tool-event results.
- **Rung 4A (DONE / #353):** Persistent process-isolated Hermes graph-agent host.
- **Rung 4B (DONE / #354):** Single-turn Hermes backend product cutover through the host with fail-closed grounding.
- **Rung 4C / PR355 (DONE / #355):** Plan presentation of grounding, opaque graph citations, bounded tool trace, and reload-safe local completed-turn persistence (display only — not Hermes session resume).
- **Rung 5 (PASS* / planned #356):** Same-thread object continuity through bounded replay of prior visible role/content pairs. The first live Tripod trial passed: Turn 2 issued fresh `expand_graph_retrieval` calls, recovered from an initial `missing_seed_node_ids` result, and returned Tripod/Mireward relationships at the pinned revision. Prior prose resolved shorthand only; it was not treated as campaign truth. `unreadable_source_anchors` kept the trial in partial coverage because source excerpts were not opened. Two more live trials are required before marking the rung `DONE`. Rung 5 does not establish a persistent Hermes session, persist an internal Hermes transcript, own demolition, or change the backend selector/default.
- **Rung 6 (LATER):** Durable Hermes session-pointer continuity and reload/process-restart lifecycle (distinct from Rung 4C display persistence and Rung 5 stateless prose replay).
- **Rung 7 (LATER):** Cumulative product acceptance, obsolete Hermes path demolition, backend-toggle removal, and default-backend decision.

**Target runtime shape:**

- Hermes owns synthesis and tool choice for each graph-agent turn.
- Rung 5 continuity is bounded visible-prose replay from the active local Plan thread, not a durable Hermes session.
- Rung 6 (not yet) owns one Hermes session pointer per Agent Interaction thread and its process/restart lifecycle.
- The runtime is embedded/in-process or uses a supported session API; shelling out to `hermes --oneshot` is not the product path.
- The Live synthesizer is not a fallback for Hermes failures or graph misses.
- Hermes long-term memory is disabled for campaign facts.

**Initial read-only tool vocabulary:**

- `search_campaign_graph`
- `get_campaign_object`
- `get_object_neighborhood`
- `get_object_evidence`
- `read_source_anchor`

These tools are graph/revision scoped. `read_source_anchor` accepts an opaque anchor from graph retrieval, not an arbitrary file path.

**Dogfood acceptance:**

1. Ask: “What do we know about Tripod Null-Calf at the North Gate?”
2. Hermes retrieves the graph object, relationships, attributes, and anchored evidence.
3. The answer cites admitted anchors and exposes revision/tool trace metadata.
4. Ask in the same thread: “What is it connected to that should affect my prep?”
5. Hermes resolves “it” from thread context, performs bounded graph traversal, and explains concrete prep implications.
6. If the graph lacks an answer, Hermes says so and reports the missing coverage. It does not search other Markdown.
7. Reload restores completed-turn display (Rung 4C). Durable Hermes session-pointer resume is Rung 6, not Rung 5 prose replay.

**Live Rung 5 evidence:** [`HERMES-RUNG5-TRIPOD-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG5-TRIPOD-DOGFOOD-2026-07-16.md) records trial 1 as a continuity/retrieval pass and keeps the source-anchor evidence gap separate from the Rung 5 verdict.

**Non-goals:** Full operator tool parity, graph writes, draft persistence, preview/confirm, Play migration, generalized autonomous planning, or broad UI redesign.

**Demolition owned by PR010B:**

- Remove manifest/corpus/lexical tools from the Hermes product toolset.
- Remove arbitrary-path document reads from the Hermes product path.
- Remove CLI one-shot as the product backend; retain only an explicitly non-production debug harness if still useful.
- Remove the steady-state Live/Hermes backend toggle once Hermes graph dogfood is accepted.

## Phase 8 — Agent Context + Tool Runtime

**Objective:** Productionize the graph-grounded Hermes agent and add governed operator tools.

**Expected slice:** PR011.

PR011 builds on accepted PR010B behavior. It adds app-level context assembly, cross-surface continuity, typed `read_only`, `draft_only`, `preview_write`, `confirm_commit`, and `admin_diagnostic` capabilities, and proposal-bound writes through Kernel paths.

**Exit criteria:**

- Hermes reads current graph state and source anchors, not ambient memory.
- Threads remain non-canonical continuity and see current graph head on fresh reads.
- Durable writes require preview and explicit GM confirmation.
- Player-facing agents cannot receive GM-only assertions through adjacency or tool calls.
- Transitional Agent Interaction drawers and duplicate runtime paths are retired when replaced.

## Phase 9 — Living campaign memory and cleanup

**Objective:** Continuous, correctable campaign memory across Plan and Play, with obsolete dual-architecture paths removed.

**Expected slices:** dogfood-driven hardening and PR012 only for leftovers that could not be deleted by their replacement PR.

---

## What this roadmap explicitly abandons

- Agent-side manifest routing as a product retrieval plane.
- Corpus-index or repo-wide Markdown search as a fallback when graph retrieval is thin.
- Arbitrary document reads by path from the conversational agent.
- `hermes --oneshot` as the product runtime.
- A permanent Live-versus-Hermes backend choice.
- Treating chat/session memory as campaign truth.
- Hiding graph coverage defects by answering from unmodeled source files.

The consequence is intentional: graph coverage quality becomes visible. When Hermes cannot answer, the product identifies a memory/ingestion gap that can be corrected through the governed graph pipeline.
