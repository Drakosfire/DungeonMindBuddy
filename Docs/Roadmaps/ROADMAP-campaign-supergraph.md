# Roadmap — Campaign Supergraph

**Status:** Canonical implementation roadmap
**Date:** 2026-07-10
**Updated:** 2026-07-13 — PR010A done (#346–#349); PR010B Rung 1 done (#350); Rung 2 model adapter active; Rung 3 agent/session loop next
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**PR slices:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)
**Hermes anchor:** [`Docs/Design/ANCHOR-agent-interaction-hermes.md`](../Design/ANCHOR-agent-interaction-hermes.md)

This roadmap describes implementation milestones. This document and the PR tracker are the only active sequencing authority for Campaign Supergraph work. Older handoffs, experiments, backlog entries, Project Sources, and historical Agent Interaction documents may explain why decisions were made, but they cannot override this roadmap.

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
DONE    PR010B Rung 1 — strict graph-only read-tool dispatcher (#350)
DOING   PR010B Rung 2 — model-visible tool catalog plus JSON-string adapter
NEXT    PR010B Rung 3 — real in-process Hermes agent/session loop
LATER   PR010B thread binding, product replacement, dogfood acceptance, and demolition
```

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

**Status:** Doing — Rung 1 complete (#350); Rung 2 (model-visible catalog + JSON-string adapter) active; Rung 3 (real in-process Hermes agent/session loop) next.

**Purpose:** Run Hermes as the actual conversational agent over PR010A read tools and dogfood multi-turn graph-grounded prep in the existing Agent Interaction surface.

**Rung sequence:**

- **Rung 1 (DONE / #350):** Strict graph-only Hermes read-tool dispatcher over the five PR010A operations.
- **Rung 2 (DOING):** Model-visible tool catalog and JSON-string execution adapter derived from the same Rung 1 registry metadata. No model loop, session, route, UI, or plugin migration.
- **Rung 3 (NEXT):** Real in-process Hermes agent/session loop using the Rung 2 catalog and adapter.
- **Later:** Agent Interaction thread/session binding, Plan product wiring, obsolete retrieval demolition, dogfood acceptance, and backend-toggle removal.

**Target runtime shape:**

- Hermes owns synthesis, tool choice, and thread conversation state.
- One Hermes session maps to one Agent Interaction thread.
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
7. Reload restores the thread/session pointer and can continue without treating chat history as campaign canon.

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
