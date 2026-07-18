# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker — sole active sequencing authority
**Date:** 2026-07-10
**Updated:** 2026-07-17 — PR363 extract/promote foundation on `main` (`fdd7ec82`); PR011 split into PR011A* (Graph Review bridge) + PR011B (Hermes capability); PR011A1 READY
**Architecture:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
**Hermes goal anchor:** [`Docs/Design/ANCHOR-hermes-campaign-sensemaking-goal.md`](../Design/ANCHOR-hermes-campaign-sensemaking-goal.md)

Tracker IDs are roadmap slice IDs, not GitHub PR numbers. This tracker sequences
Campaign Supergraph infrastructure. The Hermes reset plan and re-anchor record
sequence the separate product/authoring gate. Older handoffs, backlog items,
research notes, and Project Sources cannot override either active authority.

## Global rules

- One slice, one independently useful capability.
- Replacement paths are deleted when the replacement becomes production-ready unless a named consumer is documented.
- Storage, projection, and retrieval contracts are forward-only until an explicit stability milestone.
- Agents are not privileged writers.
- Agent factual discovery is graph-first. Graph claims are the canonical materialized fact plane; graph-admitted source anchors are the normal source-evidence route.
- Narrow exception: a server-owned artifact registry may admit a narrowly typed source (today: latest-recap) for explicit memory-lag workflows. Registry selection, path resolution, and root containment are server-owned. Hermes cannot discover arbitrary Markdown or filesystem paths. Admitted registry material is source evidence, not promoted graph memory.
- No product compatibility mode may select latest-ingest, preview-source, run/store/manifest paths, arbitrary Markdown, or a parallel corpus index.

## Status legend

| Status | Meaning |
|---|---|
| `READY` | Dependencies met; may start |
| `DOING` | Active implementation |
| `BLOCKED` | Waiting on a named dependency |
| `DONE` | Merged and exit criteria met |
| `DEFERRED` | Intentionally later |

## Forward sequence

```text
DONE    PR001–PR005B  Foundation, Kernel, authority, and agent/write contracts
DONE    PR006A–D2     Initial Eldyrwild World Supergraph publication
DEFERRED PR006D3      Bootstrap activation UI
DONE    PR007A        Revision-pinned projection/read snapshot
DONE    PR008A        Plan World Graph migration
DONE    PR008B        Agent Interaction graph query-context attachment
DONE    PR010A        Graph retrieval contract + source-anchor admission
DONE    PR010B        Hermes graph-retrieval dogfood
DONE    PR011A-foundation  Extract/promote shared ops + HTTP (#363, `fdd7ec82`)
DOING   PR011A1       Server-owned ingest-run → promotion binding
BLOCKED PR011A2       Graph Review prepare / review panel (on A1)
BLOCKED PR011A3       Confirm, durable reload, Session 25 dogfood (on A2)
BLOCKED PR011B        Hermes preview_write / confirm_commit (on A3)
READY   PR009         Play projection migration (parallel product lane)
BLOCKED PR012         Leftover cleanup safety net
```

PR010 is intentionally split into PR010A and PR010B. PR011 is split into
PR011A* (human Graph Review `confirm_commit` reference path) and PR011B
(Hermes capability over the same path). Do not renumber PR011 or PR012.

Product binding design: [`DESIGN-extract-promote-graph-review-bridge.md`](../Design/DESIGN-extract-promote-graph-review-bridge.md).

PR010B Rungs 5–7 are all accepted and merged into `main` as `129a4c40` (PR #356,
2026-07-17). The merge also carries three rounds of external-critique
hardening that landed on the same branch before merge: closing claim-authority
escape hatches, preserving natural model prose as the frontstage answer while
labeling it honestly (`graph_context_synthesis`), and making the
`expand_graph_retrieval` tool schema, claim hydration, and pointer-store
concurrency contract match what the executor actually does (see Rung 7
evidence report addendum below). Hermes is the only Plan Agent Interaction
backend; Live remains for `/surface` ChatModule. Verification provenance is
still local/manual `pytest`/`vitest` runs — this repo has no CI status checks
attached to PRs; that is a standing, accepted limitation, not a Rung 7 blocker.
Evidence: [`HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md).

## Completed foundation

| Slice | Status | Outcome |
|---|---|---|
| PR001 | `DONE` — GitHub #322 | Canonical architecture, roadmap, tracker, audit |
| PR002 | `DONE` — GitHub #323 | Durable World Supergraph storage and atomic head |
| PR003 | `DONE` — GitHub #324/#325 | Enforceable Kernel public boundary |
| PR004 | `DONE` — GitHub #326 | Identity outcomes, provisional state, split/unmerge |
| PR005 | `DONE` — GitHub #327 | Durable contribution merge, replay, retraction |
| PR005A | `DONE` — GitHub #328 | Context/source authority reanchor |
| PR005B | `DONE` — GitHub #329 | Agent capability and authored-prep contract |
| PR006A | `DONE` — GitHub #333 | Heterogeneous-provenance diagnostic |
| PR006B | `DONE` — GitHub #334 | Semantic assertion identity separated from provenance |
| PR006C | `DONE` — GitHub #335 | Approved initial Eldyrwild C2 contribution bundle |
| PR006D1 | `DONE` — GitHub #336 | Generic atomic world initialization |
| PR006D2 | `DONE` — GitHub #337 | Eldyrwild bootstrap activation service |
| PR006D3 | `DEFERRED` — design #338 | `/ingest` activation UI; not a Hermes dependency |
| PR007A | `DONE` — GitHub #339 | Revision-pinned World Graph projection/read API |
| PR008A | `DONE` — GitHub #340 | Plan object-card/reference migration; latest-ingest removed |
| PR008B | `DONE` — GitHub #342 | Agent Interaction receives revision-pinned graph context |

## PR008 — Plan surface migration umbrella

**Status:** `DONE` for the required read-only migration and Agent query-context slices.

Broader Plan polish may continue as independent product slices, but it does not block graph retrieval or Hermes dogfood.

## PR009 — Play surface migration

**Status:** `READY`
**Phase:** 5

**Purpose:** Make Play consume the same revision-pinned projection contracts for live objects and combat/encounter lenses.

**Deliverables:**

- Play projection consumer with world/campaign/focus/admissibility.
- Combat/encounter represented as a Play lens, not a peer graph.
- Shared graph-object presentation where useful.
- Player-facing admissibility proven fail-closed.

**Non-goals:** Full combat automation, Hermes agent runtime, or graph writes.

**Depends on:** PR007A and lessons from PR008A.

## PR010A — Graph retrieval contract + source-anchor admission

**Status:** `DONE` — merged ladder `#346` (Mirathorn accepted locator correction), `#347` (contribution source authority), `#348` (Kernel retrieval), `#349` (live-control retrieval API)
**Phase:** 7

**Purpose:** Create the deterministic read contract that lets surfaces and agents discover, traverse, and admit evidence from one revision-pinned World Supergraph without consulting a parallel Markdown retrieval system.

**Public contract must include:**

- Request: `worldId`, `campaignId`, focus, admissibility, question/search text, optional seed node IDs, optional revision pin, explicit bounds.
- Result revision: requested revision, head revision, `isHead`, world/campaign/focus.
- Matched graph objects with durable IDs, labels, aliases, kinds, summaries, and relevance reasons.
- Bounded relationships/neighborhood paths with endpoint-relative direction.
- Attributes and focus relevance.
- Source anchors/evidence locators admitted through active graph assertions.
- Stable outcome: `enough`, `partial`, `empty`, `denied`, `truncated`, or `unavailable`.
- Coverage and admissibility diagnostics.

**Tool-shaped read primitives:**

- `search_campaign_graph`
- `get_campaign_object`
- `get_object_neighborhood`
- `get_object_evidence`
- `read_source_anchor`

`read_source_anchor` accepts only an anchor emitted by graph retrieval. It does not accept an arbitrary filesystem or corpus path.

**Success criteria:**

- Natural-language search finds `threat:tripod-null-calf` on the published Eldyrwild graph.
- A bounded traversal returns its North Gate and prep-relevant connections from the same pinned revision.
- Source anchors are sufficient to open bounded evidence excerpts.
- Visibility and epistemic restrictions survive search and traversal.
- Graph miss tests prove manifest lookup, corpus index, arbitrary Markdown search, and lexical fallback are never called.
- Integrity/truncation/coverage diagnostics are machine-readable.

**Non-goals:** LLM calls, Hermes session state, chat UI changes, writes, full GraphRAG ranking, embeddings, arbitrary source discovery.

**Depends on:** PR007A, PR008A/PR008B dogfood pressure, stable Kernel read APIs.

**Demolition:** None yet. PR010A establishes the replacement contract; PR010B removes old Hermes retrieval paths when the new product path becomes usable.

## PR010B — Hermes graph-retrieval dogfood

**Status:** `DONE` — Rungs 5–7 all accepted; merged `main` `129a4c40` (PR #356) on 2026-07-17
**Phase:** 7 / read-only agent dogfood

**Active rungs:**

```text
DONE    PR010B Rung 1 — graph-only dispatcher (#350)
DONE    PR010B Rung 2 — model-visible catalog and adapter (#351)
DONE    PR010B Rung 3 — embedded Hermes graph-agent turn (#352)
DONE    PR010B Rung 4A — process-isolated host (#353)
DONE    PR010B Rung 4B — single-turn backend product cutover (#354)
DONE    PR010B Rung 4C — Plan evidence presentation and completed-turn persistence (#355)
DONE    PR010B Rung 5 — same-thread object continuity through bounded visible-prose replay
PASS    PR010B Rung 6 — durable Hermes session-pointer and reload/process lifecycle
PASS    PR010B Rung 7 — cumulative product acceptance and replaced-path demolition (#356)
```

- **PR010B Rung 1 — graph-only Hermes read-tool executor** (`DONE` via #350): exact internal dispatch from the five PR010A tool names to the merged live-control retrieval service.
- **PR010B Rung 2 — model-visible tool catalog plus JSON-string adapter** (`DONE` via #351): OpenAI/Hermes-compatible function definitions derived from the same Rung 1 registry metadata, plus JSON-string execution over Rung 1 with existing PR010A success/error envelopes.
- **PR010B Rung 3 — embedded Hermes graph-agent turn** (`DONE` via #352): dependency-locked in-process `AIAgent` turn with packaged `dungeonbuddy_graph` plugin; typed result with ordered safe tool events.
- **PR010B Rung 4A / PR353 — persistent Hermes graph-agent host** (`DONE` via #353): process-isolated reusable worker host with bounded JSON IPC and no-replay acceptance barrier.
- **PR010B Rung 4B / PR354 — single-turn Hermes backend product cutover** (`DONE` via #354): `query_backend="hermes"` routes one revision-pinned turn through the PR353 host with grounding classification and no legacy fallback.
- **PR010B Rung 4C / PR355 — Plan graph evidence presentation and reload-safe turn persistence** (`DONE` via #355, merge `7671a633`): present grounding labels, opaque revision-pinned graph citations, bounded graph-tool trace, and local turn persistence for one completed PR354 turn. Reload-safe means saved answer/citation/trace display only — not Hermes session resume.

**Completed continuity, lifecycle, and cumulative rungs:**

- **PR010B Rung 5 — same-thread object continuity through bounded visible-prose replay** (`DONE`, planned GitHub `#356`): accepted across three live trials. Each trial showed bounded prior role/content replay resolving the shorthand referent, followed by fresh `expand_graph_retrieval` at the pinned revision supplying the factual result. `unreadable_source_anchors` remains a separate source-evidence gate on the backlog. Evidence: [`HERMES-RUNG5-TRIPOD-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG5-TRIPOD-DOGFOOD-2026-07-16.md).
- **Rung 6 (PASS) — durable Hermes session-pointer and reload/process lifecycle:** server-authoritative opaque pointer, thread binding, durable store, and deterministic recovery contracts accepted. Live dogfood after full shutdown/reload showed `accepted` pointer continuation, `worker_pid_changed`, and fresh graph retrieval; Thread B isolation passed; invalid/expired recovery proven by contract tests (not UI dogfood). [`HERMES-RUNG6-BASELINE-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG6-BASELINE-DOGFOOD-2026-07-16.md)
- **Rung 7 (PASS) — cumulative product acceptance and Plan Hermes-only demolition:** demolition and Turns 1–2/reload evidence are present; coverage-gap authority is proven by deterministic contract tests (live stochastic coverage-gap prose is not required — see Required dogfood). The remaining merge gate cleared with the 2026-07-17 merge of `agent/pr010b5-plan-hermes-thread-continuity` to `main` (`129a4c40`, PR #356). Three external-critique rounds landed on the branch before merge (claim-authority hardening, natural-prose preservation with `graph_context_synthesis` labeling, expand-tool/hydration/pointer-store honesty — see commits `2db5da67`, `293fdf43`, `09898467`, `6db1e18a`, `c92e5a02`). Verification provenance remains local/manual (no CI status checks attached to this repo). [`HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md)

**Purpose:** Make Hermes the actual conversational agent for Plan prep, using PR010A graph retrieval, graph-admitted source anchors, and the narrow server-owned registry-admitted latest-recap exception for disclosed memory lag.

**Deliverables:**

- Non-shell Hermes agent runtime integrated with `live-control` or a supported session boundary.
- One server-authoritative opaque Hermes session pointer per Agent Interaction thread.
- Multi-turn conversation with current graph reads and explicit revision metadata.
- Agent tool loop over the PR010A read-only vocabulary.
- Cite-or-abstain policy tied to returned anchors.
- Tool start/completion, retrieval outcome, source-anchor, revision, and timing trace events.
- Full thread payload persistence by pointer/ID without treating the thread as canon.
- Existing Agent Interaction UI extended rather than redesigned.

**Required dogfood:**

1. Ask: “What do we know about Tripod Null-Calf at the North Gate?”
2. Confirm Hermes calls graph tools and cites admitted source anchors.
3. Ask: “What is it connected to that should affect my prep?”
4. Confirm the same thread resolves “it,” traverses the graph, and returns useful connected-object implications.
5. Coverage-gap authority (answer exists in Markdown but is absent from the graph): prove by deterministic contract tests that Hermes abstains / reports the gap and does not search Markdown, manifest, corpus, or lexical fallback. A live stochastic coverage-gap turn is optional evidence, not a required gate.
6. Reload restores completed-turn display and accepted opaque session-pointer continuation (Rung 6).

**Success criteria:**

- Hermes, not Live, performs synthesis for the Plan dogfood path.
- Graph claims are the canonical fact plane; graph anchors are the normal source-evidence route; the registry-admitted latest-recap path is the only narrow non-graph source admission and remains source evidence, not graph memory.
- No answer is produced from arbitrary Markdown, manifest routing, corpus index, lexical fallback, or ambient Hermes memory.
- Same-thread follow-ups preserve conversational identity via bounded visible-prose replay while factual claims are refreshed from current graph state (Rung 5 DONE).
- Reload restores completed-turn display (Rung 4C) and durable Hermes session-pointer resume (Rung 6 PASS).
- Trace proves which graph tools, revision, objects, edges, and source anchors were used.
- Model-facing expand operations advertise only implemented primitives (`object`, `neighborhood`, `search`, `support`); specialized latest-recap comparison remains a separate typed server workflow.

**Non-goals:** Full operator tool parity, writes, drafts, preview/confirm, app-wide provider hoist, Play migration, autonomous campaign editing.

**Depends on:** PR010A.

**Retain / rewrite / delete:**

```text
Retained temporarily:
- Legacy manifest/corpus lookup code only for non-Hermes tests or named non-product consumers.
- Optional direct CLI smoke harness only if explicitly labeled development-only.

Rewritten:
- Hermes Plan query path becomes a real agent/tool loop.
- Conversation thread owns Hermes session identity.
- Source reading is anchor-bound.

Deleted from the Hermes product path:
- dungeon_search / lexical fallback
- dungeon_manifest_index
- manifest-backed dungeon_context_lookup
- arbitrary-path dungeon_get_document
- hermes --oneshot subprocess backend
- Live synthesis fallback for Hermes questions
- steady-state Live/Hermes backend toggle after acceptance

Required deletion PR:
- PR010B for Hermes product-path replacements.
- PR012 only for leftovers with a named remaining consumer.
```

## PR011 — Agent Context + Tool Runtime (umbrella)

**Status:** `DOING` via PR011A* first; PR011B after the human reference path exists  
**Phase:** 8  
**Design:** [`DESIGN-extract-promote-graph-review-bridge.md`](../Design/DESIGN-extract-promote-graph-review-bridge.md)

**Purpose:** Productionize governed writes (`preview_write` / `confirm_commit`) and
the complete typed capability model from PR005B. Human Graph Review is the
reference `confirm_commit` path; Hermes must not get a second write protocol.

**Umbrella deliverables (still owned by PR011 overall):**

- App-level context assembly over graph retrieval, source anchors, thread state, and surface context.
- `read_only`, `draft_only`, `preview_write`, `confirm_commit`, and `admin_diagnostic` registry.
- Proposal-bound/revision-bound preview and explicit GM confirmation for durable writes.
- Cross-thread/current-head invalidation and re-read behavior.
- Escalation to Graph Review/Kernel for corrections.

**Success criteria:**

- Agent memory is World Supergraph + source anchors; chat/Hermes memory is continuity only.
- No silent graph mutation.
- Stale proposals fail closed.
- Player-facing tools cannot leak GM-only assertions.
- Ingest creates proposed memory; Graph Review owns judging and committing it.

**Non-goals:** Fully autonomous campaign rewriting or replacing Graph Review.

### PR011A-foundation — Extract/promote HTTP boundary

**Status:** `DONE` — GitHub #363, merge `fdd7ec82` (2026-07-17/18)  
**Outcome:** Shared `extract_promote_ops` + CLI + HTTP prepare/confirm/status;
proposal seal; assertion selection; truthful post-publication audit; pinned
rebuild with contribution replay manifest. Operator path-based prepare remains
acceptable for CLI bootstrap only.

### PR011A1 — Server-owned ingest-run → promotion binding

**Status:** `DOING`  
**Depends on:** PR011A-foundation

**Purpose:** Replace browser-supplied path prepare with server-owned
`resolve_promotable_ingest_run(run_id)`.

**Deliverables:**

- `resolve_promotable_ingest_run(run_id)` → validated manifest, source artifact +
  digest, candidate graph, profile, campaign/session scope, promotability diagnostics.
- Product HTTP prepare body becomes `{ runId, nodeIds? }` only (forward-only;
  delete path fields from the product contract).
- CLI may keep internal path-based ops.

**Success criteria:**

- Unknown / failed / invalid / non-preview-ready runs cannot prepare.
- Campaign/session mismatches fail closed.
- Source and candidate paths resolve from the run manifest only.
- Graph store can never become evidence.
- Proposal remains pinned to the current graph head.
- No browser-supplied manifest, source, or candidate path is accepted.

**Non-goals:** Graph Review UI panel; Hermes tools; automatic ingest publish.

### PR011A2 — Graph Review prepare / review panel

**Status:** `BLOCKED` on PR011A1  
**Depends on:** PR011A1

**Purpose:** Bind a selected ingest run to prepare and present a game-facing
review sheet (not a diagnostics dump).

**Deliverables:**

- `extractPromoteApi.ts` + typed frontend contracts.
- **Review & merge** in Graph Review toolbar/header; enable only for promotable
  selected runs against an initialized World Graph.
- Typed `ExtractPromotionReviewItem[]` review projection alongside the sealed package.
- Selection UX: accepted items selected by default; zero-selection disables confirm;
  unresolved/rejected visible but unselected.

**Success criteria:**

- Prepare opens a review sheet with game-facing object/relationship items.
- UI does not parse Kernel proposal internals as the presentation model.
- Sealed package remains confirmation authority.

**Non-goals:** Durable confirm/reload dogfood (A3); operator `allowLiveWorld` UI.

### PR011A3 — Confirm, durable reload, Session 25 dogfood

**Status:** `BLOCKED` on PR011A2  
**Depends on:** PR011A2

**Purpose:** Explicit **Merge N changes into campaign memory**, then prove the
object journey on Session 25 (Hesta / apothecary ↔ Mireward).

**Deliverables:**

- Product confirm sends sealed proposal + selected assertion IDs only;
  confirming principal and live-world policy are server-owned.
- Post-confirm: reload committed revision, refresh catalog, open durable objects,
  compact success receipt.
- Explicit failure UX for stale / already_applied / publish failed / audit degraded.
- End-to-end dogfood proof recorded (ingest → review → merge → Plan/Hermes retrieve → reload).

**Success criteria:**

- World Graph head advances; Hesta (or chosen Session 25 object) is durable and
  retrievable; evidence and relationships are openable; reload persists.

**Non-goals:** Hermes capability registry (PR011B); autonomous merges.

### PR011B — Hermes `preview_write` / `confirm_commit`

**Status:** `BLOCKED` on PR011A3  
**Depends on:** PR011A3 human reference path

**Purpose:** Expose the same governed write capability to Hermes without creating
a second agent-specific protocol. Hermes launches/prepares; GM confirmation still
lands on the Graph Review confirmation surface (or an equivalent bound confirm).

**Non-goals:** Autonomous durable writes; bypassing proposal digest / parent revision.

## PR012 — Obsolete-path cleanup safety net

**Status:** `BLOCKED` on PR009–PR011 replacement work
**Phase:** 9

Deletes only leftovers that earlier replacement PRs could not remove because of a documented remaining consumer. It is not permission to defer PR010B demolition.

## How to add a slice

1. Confirm the capability belongs to a roadmap phase.
2. Give it the next compatible tracker ID or sub-slice without renumbering PR011/PR012.
3. Define purpose, deliverables, success criteria, non-goals, dependencies, demolition, and retain/rewrite/delete.
4. Keep one independently useful outcome.
5. Never add fallback compatibility for rejected architecture.
