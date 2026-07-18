# Roadmap — Campaign Supergraph

**Status:** Canonical implementation roadmap
**Date:** 2026-07-10
**Updated:** 2026-07-18 — PR011A1 ingest-run → promotion binding on `main` (`bcc874ed`, #364); Phase 8 critical path is PR011A2 (Graph Review panel); see DESIGN-extract-promote-graph-review-bridge.md
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**PR slices:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)
**Hermes goal anchor:** [`Docs/Design/ANCHOR-hermes-campaign-sensemaking-goal.md`](../Design/ANCHOR-hermes-campaign-sensemaking-goal.md)
**Write-path product bridge:** [`Docs/Design/DESIGN-extract-promote-graph-review-bridge.md`](../Design/DESIGN-extract-promote-graph-review-bridge.md)

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
- **Agent factual discovery is graph-first.** Graph claims are the canonical materialized fact plane; graph-admitted source anchors are the normal source-evidence route. A server-owned artifact registry may admit a narrowly typed source (today: latest-recap) for explicit memory-lag workflows; that material remains source evidence, not promoted graph memory. Hermes cannot discover arbitrary Markdown or filesystem paths.

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

### Graph-first retrieval boundary

For Agent Interaction and other graph-aware consumers:

1. Discovery begins from a revision-pinned World Supergraph projection or graph-retrieval API.
2. Retrieval may return graph objects, attributes, relationships, neighborhoods, and graph-admitted source anchors.
3. A source reader may open only those admitted anchors, with bounded excerpts and stable evidence locators.
4. Narrow exception: a server-owned artifact registry may admit a narrowly typed source (today: latest-recap) for disclosed memory-lag workflows. Selection and path resolution are server-owned; the result is source evidence, not graph memory.
5. No product fallback may search manifests, corpus indexes, arbitrary repository Markdown, or lexical/vector stores outside graph or registry admission.
6. A graph miss or evidence gap produces an explicit abstention and a coverage-gap diagnostic. It does not trigger hidden Markdown search.

This does **not** demote source documents. It makes the graph the normal routing/admission plane, source anchors the normal evidence plane, and the registry the only narrow non-graph source admission for typed memory-lag workflows.

## Current critical path

```text
DONE  PR006D2  Publish Eldyrwild C2 World Supergraph
DONE  PR007A   Revision-pinned projection/read snapshot
DONE  PR008A   Plan World Graph object-card migration
DONE  PR008B   Agent Interaction receives revision-pinned graph query context
DONE  PR010A   Graph retrieval contract and source-anchor admission
DONE  PR010B   Hermes graph-retrieval dogfood (Rungs 5–7 all accepted; merged main #356)
DONE  PR011A-foundation  Extract/promote shared ops + HTTP prepare/confirm (#363, `fdd7ec82`)
DONE  PR011A1  Server-owned ingest-run → promotion binding (#364, `bcc874ed`)
DOING PR011A2  Graph Review prepare / review panel
BLOCKED PR011A3  Confirm, durable reload, Session 25 dogfood (on A2)
BLOCKED PR011B Hermes preview_write / confirm_commit over the same path (on A3)
```

PR009 Play migration may proceed independently after PR008 lessons. Multi-source ingestion expansion can also continue without changing the graph-first Agent Interaction direction.

Product bridge design (Ingest proposes → Graph Review judges/commits):
[`DESIGN-extract-promote-graph-review-bridge.md`](../Design/DESIGN-extract-promote-graph-review-bridge.md).

PR010B is decomposed into independently useful rungs:

```text
DONE    PR010B Rung 1 — graph-only dispatcher (#350)
DONE    PR010B Rung 2 — model-visible catalog and adapter (#351)
DONE    PR010B Rung 3 — embedded Hermes graph-agent turn (#352)
DONE    PR010B Rung 4A — process-isolated host (#353)
DONE    PR010B Rung 4B — single-turn backend product cutover (#354)
DONE    PR010B Rung 4C — Plan evidence presentation and completed-turn persistence (#355)
DONE    PR010B Rung 5 — same-thread object continuity through bounded visible-prose replay
PASS    PR010B Rung 6 — durable Hermes session-pointer and reload/process lifecycle
PASS    PR010B Rung 7 — cumulative product acceptance and replaced-path demolition
```

Rungs 5–7 are all accepted. The `agent/pr010b5-plan-hermes-thread-continuity`
branch merged into `main` as `129a4c40` (PR #356) on 2026-07-17, closing the
"remaining merge gates" condition that had kept Rung 7 cumulative `PASS` open.
Three external-critique hardening rounds landed on the same branch before
merge and are therefore also on `main`:

1. Claim-authority escape hatches closed (no implicit zero-tool-call trust, no
   missing-provenance → GM-canon default, no cross-revision claim support).
2. Natural model prose preserved as the frontstage answer (`graph_context_synthesis`
   authority label) with deterministic claim bullets moved to a support/debug
   field, and explicit `declare_conversation_context` always wins.
3. Expand-tool honesty: `ExpansionOperation` reduced to `object` / `neighborhood`
   / `search` / `support`; `ExpandTarget.kind` is `node`-only;
   `relationFamilies` / `claimPredicates` / `bounds` removed from the
   model-visible schema; targetless `neighborhood` now fails closed instead of
   silently becoming `search`; per-operation target cardinality is enforced
   (`object`/`support` exactly one, `neighborhood` 1–8, `search` 0–8) and the
   trace records `effective_targets` alongside the raw request; claim
   hydration is fail-closed (`GraphClaim.model_validate`, no inventing
   `revision_id`/`claim_kind`/`authority_class`); the Hermes pointer store's
   concurrency contract is documented as same-process-only.

Hermes is the only Plan Agent Interaction backend; Live remains for
`/surface` ChatModule. Remaining known gaps (not Rung 5/6/7 blockers): the real
`AIAgent` wire-start environment failure, source-anchor readability
(`unreadable_source_anchors`), and the absence of CI status checks on this
repo (verification provenance is local/manual `pytest`/`vitest` runs, not a
GitHub Actions gate).

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

**Status:** Done — Rungs 5–7 all accepted; merged to `main` as `129a4c40` (PR #356) on 2026-07-17. PR011A-foundation is DONE (#363, `fdd7ec82`); PR011A1 is DONE (#364, `bcc874ed`); next is PR011A2. PR009 remains an independent parallel lane.

**Purpose:** Run Hermes as the actual conversational agent over PR010A read tools and dogfood multi-turn graph-grounded prep in the existing Agent Interaction surface.

**Rung sequence:**

- **Rung 1 (DONE / #350):** Strict graph-only Hermes read-tool dispatcher over the five PR010A operations.
- **Rung 2 (DONE / #351):** Model-visible tool catalog and JSON-string execution adapter derived from the same Rung 1 registry metadata.
- **Rung 3 (DONE / #352):** Embedded in-process Hermes `AIAgent` turn with packaged `dungeonbuddy_graph` plugin, optional caller-owned history, and typed tool-event results.
- **Rung 4A (DONE / #353):** Persistent process-isolated Hermes graph-agent host.
- **Rung 4B (DONE / #354):** Single-turn Hermes backend product cutover through the host with fail-closed grounding.
- **Rung 4C / PR355 (DONE / #355):** Plan presentation of grounding, opaque graph citations, bounded tool trace, and reload-safe local completed-turn persistence (display only — not Hermes session resume).
- **Rung 5 (DONE / planned #356):** Same-thread object continuity through bounded replay of prior visible role/content pairs, accepted across three live trials. Each trial showed fresh `expand_graph_retrieval` after conversational referent resolution at the pinned revision; prior prose resolved shorthand only and was not treated as campaign truth. `unreadable_source_anchors` remains a separate source-evidence gate on the backlog. Rung 5 does not establish a persistent Hermes session, persist an internal Hermes transcript, own demolition, or change the backend selector/default.
- **Rung 6 (PASS):** Durable Hermes session-pointer and reload/process lifecycle accepted. Server-authoritative opaque `hptr-*` pointer with thread binding, durable store, accepted/rejected/recovered telemetry, and deterministic recovery contracts. Live dogfood after full shutdown/reload showed `accepted` pointer continuation, `worker_pid_changed`, and fresh graph retrieval; Thread B isolation passed; invalid/expired recovery is proven by contract tests (not UI dogfood). Distinct from Rung 4C display persistence and Rung 5 prose replay. Evidence: [`HERMES-RUNG6-BASELINE-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG6-BASELINE-DOGFOOD-2026-07-16.md).
- **Rung 7 (PASS):** Plan Hermes-only demolition and Turns 1–2/reload evidence are present. Coverage-gap authority is proven by deterministic product-path contracts after an explicit tracker amendment (live stochastic coverage-gap prose is optional). The remaining merge gate cleared with the 2026-07-17 merge to `main` (`129a4c40`, PR #356), which also carries three rounds of external-critique hardening (claim-authority escape hatches, natural-prose preservation, expand-tool/hydration/pointer-store honesty). Evidence: [`HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md).

**Target runtime shape:**

- Hermes owns synthesis and tool choice for each graph-agent turn.
- Rung 5 continuity is bounded visible-prose replay from the active local Plan thread, not a durable Hermes session.
- Rung 6 owns one server-authoritative opaque Hermes session pointer per Agent Interaction thread and its process/restart lifecycle; that lifecycle gate is accepted.
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
6. Coverage-gap authority: deterministic contract tests prove Hermes abstains / reports the gap and does not search Markdown, manifest, corpus, or lexical fallback. A live stochastic coverage-gap turn is optional evidence, not a required gate.
7. Reload restores completed-turn display (Rung 4C). Durable Hermes session-pointer resume is Rung 6, not Rung 5 prose replay.

**Live Rung 5 evidence:** [`HERMES-RUNG5-TRIPOD-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG5-TRIPOD-DOGFOOD-2026-07-16.md) is the Rung 5 acceptance report (DONE, three live trials) and keeps the source-anchor evidence gap separate from the Rung 5 verdict.

**Live Rung 6 evidence:** [`HERMES-RUNG6-BASELINE-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG6-BASELINE-DOGFOOD-2026-07-16.md) is the Rung 6 acceptance report (PASS). The real `AIAgent` wire-start environment failure remains a separate open item.

**Live Rung 7 evidence:** [`HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md) records demolition progress and coverage-gap contract proof; cumulative gate remains `DOING`.

**Non-goals:** Full operator tool parity, graph writes, draft persistence, preview/confirm, Play migration, generalized autonomous planning, or broad UI redesign.

**Demolition owned by PR010B:**

- Remove manifest/corpus/lexical tools from the Hermes product toolset.
- Remove arbitrary-path document reads from the Hermes product path.
- Remove CLI one-shot as the product backend; retain only an explicitly non-production debug harness if still useful.
- Remove the steady-state Live/Hermes backend toggle once Hermes graph dogfood is accepted.

## Phase 8 — Agent Context + Tool Runtime

**Objective:** Productionize the graph-grounded Hermes agent and add governed operator tools.

**Expected slices:** PR011A* (human Graph Review `confirm_commit` reference path), then PR011B (Hermes capability over the same path).

**Current state (2026-07-18):** PR011A-foundation is `DONE` on `main` via GitHub #363
(`fdd7ec82`): shared extract/promote ops + HTTP prepare/confirm/status with
proposal seal, assertion selection, and truthful post-publication audit.
PR011A1 is `DONE` via GitHub #364 (`bcc874ed`): server-owned
`resolve_promotable_ingest_run(run_id)` and `runId`-only product prepare.
The missing product work is the Graph Review prepare / review panel (PR011A2),
then confirm/reload dogfood (A3) — not a second Kernel.

PR011 umbrella still owns app-level context assembly, the typed capability
registry (`read_only`, `draft_only`, `preview_write`, `confirm_commit`,
`admin_diagnostic`), and cross-surface continuity. Delivery order is fixed:

```text
DONE     PR011A-foundation (#363, `fdd7ec82`)
DONE     PR011A1 — runId → server-resolved prepare (#364, `bcc874ed`)
DOING    PR011A2 — Graph Review review panel + typed review projection
THEN     PR011A3 — confirm, durable reload, Session 25 Hesta dogfood
THEN     PR011B  — Hermes uses the same confirm_commit path
```

**Exit criteria:**

- Hermes reads current graph state and source anchors, not ambient memory.
- Threads remain non-canonical continuity and see current graph head on fresh reads.
- Durable writes require preview and explicit GM confirmation in Graph Review.
- Ingest never auto-publishes; Graph Review owns judging and committing proposed memory.
- Player-facing agents cannot receive GM-only assertions through adjacency or tool calls.
- Transitional Agent Interaction drawers and duplicate runtime paths are retired when replaced.
- No second agent-specific write protocol alongside the human reference path.

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
