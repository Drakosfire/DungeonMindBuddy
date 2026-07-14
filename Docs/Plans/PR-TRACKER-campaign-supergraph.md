# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker — sole active sequencing authority
**Date:** 2026-07-10
**Updated:** 2026-07-13 — PR010B Rung 1–2 done (#350/#351); Rung 3 active (embedded Hermes graph-agent turn); Rung 4 next (thread/session binding)
**Architecture:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
**Hermes anchor:** [`Docs/Design/ANCHOR-agent-interaction-hermes.md`](../Design/ANCHOR-agent-interaction-hermes.md)

Tracker IDs are roadmap slice IDs, not GitHub PR numbers. Older handoffs, backlog items, research notes, and Project Sources cannot override this tracker.

## Global rules

- One slice, one independently useful capability.
- Replacement paths are deleted when the replacement becomes production-ready unless a named consumer is documented.
- Storage, projection, and retrieval contracts are forward-only until an explicit stability milestone.
- Agents are not privileged writers.
- Agent factual discovery is graph-only. Source documents may be read only through graph-admitted source anchors.
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
DOING   PR010B        Hermes graph-retrieval dogfood
BLOCKED PR011         Agent Context + governed tool runtime
READY   PR009         Play projection migration (parallel product lane)
BLOCKED PR012         Leftover cleanup safety net
```

PR010 is intentionally split into PR010A and PR010B. Do not renumber PR011 or PR012.

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

**Status:** `DOING`
**Phase:** 7 / read-only agent dogfood

**Active rungs:**

```text
DONE    PR010B Rung 1 — strict graph-only read-tool dispatcher (#350)
DONE    PR010B Rung 2 — model-visible tool catalog plus JSON-string adapter (#351)
DOING   PR010B Rung 3 — embedded Hermes graph-agent turn
NEXT    PR010B Rung 4 — Agent Interaction thread/session binding
LATER   product replacement, dogfood acceptance, and demolition
```

- **PR010B Rung 1 — graph-only Hermes read-tool executor** (`DONE` via #350): exact internal dispatch from the five PR010A tool names to the merged live-control retrieval service.
- **PR010B Rung 2 — model-visible tool catalog plus JSON-string adapter** (`DONE` via #351): OpenAI/Hermes-compatible function definitions derived from the same Rung 1 registry metadata, plus JSON-string execution over Rung 1 with existing PR010A success/error envelopes.
- **PR010B Rung 3 — embedded Hermes graph-agent turn** (this capability): dependency-locked in-process `AIAgent` turn with packaged `dungeonbuddy_graph` plugin; optional caller-owned history; typed result with ordered safe tool events. No thread binding or durable persistence.

**Next rung (blocked on Rung 3):**

- **PR010B Rung 4 — Agent Interaction thread/session binding and reload continuity**

**Later rungs (still false):**

- PR010B replacement / acceptance — Plan product wiring, obsolete Hermes retrieval demolition, dogfood proof, backend-toggle removal.
**Purpose:** Make Hermes the actual conversational agent for Plan prep, using only PR010A graph retrieval and graph-admitted source anchors.

**Deliverables:**

- Non-shell Hermes agent runtime integrated with `live-control` or a supported session boundary.
- One Hermes session ID per Agent Interaction thread.
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
5. Ask a question whose answer exists in Markdown but is absent from the graph.
6. Confirm Hermes abstains and reports a graph coverage gap; it must not search the Markdown directly.

**Success criteria:**

- Hermes, not Live, performs synthesis for the dogfood path.
- The graph is the only discovery/admission plane.
- No answer is produced from arbitrary Markdown, manifest routing, corpus index, lexical fallback, or ambient Hermes memory.
- Same-thread follow-ups preserve conversational identity while factual claims are refreshed from current graph state.
- Reload can resume the thread/session pointer.
- Trace proves which graph tools, revision, objects, edges, and source anchors were used.

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

## PR011 — Agent Context + Tool Runtime

**Status:** `BLOCKED` on accepted PR010B dogfood
**Phase:** 8

**Purpose:** Productionize the graph-grounded Hermes runtime and implement the complete typed capability model from PR005B.

**Deliverables:**

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

**Non-goals:** Fully autonomous campaign rewriting or replacing Graph Review.

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
