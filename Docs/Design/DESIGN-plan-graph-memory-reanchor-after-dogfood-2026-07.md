# Design — Plan Graph-Memory Re-anchor After Dogfood

**Status:** Authoritative post-PR314 design re-anchor  
**Date:** 2026-07-10  
**Mode:** Design/documentation only — no runtime implementation in this note’s landing PR  
**Product goal authority:** `Docs/Design/DESIGN-plan-surface-session-prep-current-goal-2026-07.md`  
**Surface architecture authority:** `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`  
**Union Supergraph authority:** `Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md`  
**Supergraph roadmap:** `Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`  
**Source-vocabulary boundary:** `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`  
**Dogfood scaffold:** `Docs/Dogfood/PLAN-SURFACE-DOGFOOD-RUNBOOK.md`

---

## 1. Context

PR314 merged a `/plan?dogfood=1` checklist, local notes, recovery runbook, report copy, and tests. That proves the prep loop can be exercised honestly.

It does **not** prove that the current prep-memory drawer, index-shaped selected-object card, or corpus-index chip resolver are the durable architecture.

This note exists so the next implementation agent does not:

- treat the dogfood checklist as the product surface;
- polish transitional Hermes/live-query Q&A as if it were the final memory path;
- grow a second Plan-only object card instead of converging with Graph Review’s object card;
- wire more Plan behavior to corpus indexes rather than Union Supergraph projections;
- slip Author Draft, identity merge, or Graph Review diagnostics into `/plan`.

## 2. Current state (what PR314 dogfood can exercise)

`/plan` today can:

- show campaign / prep-session / memory-session context;
- edit one Tiptap session-prep board;
- save that board to a durable Session Prep Markdown path;
- recover local draft and/or durable Markdown across reload/restart;
- resolve reference chips into a Plan `SelectedObjectCard`;
- show a read-only source preview from that card;
- ask prep-memory questions through the Agent Interaction drawer;
- open supporting tools (statblock tool, roll actions when metadata exists);
- capture a dogfood report via `?dogfood=1`.

These are useful dogfood affordances. Several of their backends remain transitional.

## 3. Re-anchor decision

```text
/plan remains the GM session-prep cockpit.
/ingest remains the memory correction / Graph Review cockpit.
Union Supergraph becomes the target read model for graph-backed prep memory and object navigation.
Current /plan Q&A and reference chips are transitional corpus/index consumers, not the final graph-memory path.
```

Durable next direction:

```text
One prep board + one dogfood/reporting affordance
+ graph-backed selected-object navigation
+ graph-backed prep-memory Q&A
+ explicit escalation to /ingest when memory is wrong.
```

Do not define `/plan` as a graph review surface, an ingest surface, or a generic app dashboard.

### Union Supergraph is the target read model, not approved canon

```text
Union Supergraph = durable graph-memory read model.
Corpus markdown on disk = source of truth.
Graph projections = source-backed lenses over memory.
Graph summaries = not evidence by themselves.
```

Every graph-backed claim still needs source anchors / provenance. Preserve `SourceArtifact → SourceAnchor → SourceUnit`, opaque locators, and the surface-vocabulary boundary.

## 4. Transitional components

| Component | Role today | Classification | Target |
| --- | --- | --- | --- |
| Prep board (Tiptap) + Markdown save | Central prep work object | **Durable** | Keep; polish recovery/honesty, not replace |
| Session / document descriptors | Explicit campaign/session/target context | **Durable** | Keep |
| `/plan?dogfood=1` checklist + report | Operator measurement scaffold | **Scaffold** | Keep optional; never the product destination |
| `PlanAgentInteractionBar` → `postLiveQuery` → `/api/live/query` | Prep Q&A via planning corpus manifest / live retrieval / Hermes | **Transitional** | Plan-scoped graph-memory query over Union Supergraph |
| Plan `SelectedObjectCard` (corpus-index fields) | Game-facing chip card from npc/location/statblock/roll-table indexes | **Transitional** | Shared graph-object card primitive (extract/wrap `GraphReviewNodeGameCard`) |
| Chip resolver via corpus indexes | Opaque locator → index hit | **Fallback** | Graph-aware resolver first; index fallback; unresolved → `/ingest` |
| Source preview via `postCitationSource` | Read-only file excerpt | **Durable enough as a read path** | Prefer evidence/source anchors from graph node view when available |
| Party registry / statblock tool projections | Supporting prep tools | **Durable seams** | Keep as projections; do not invent parallel Plan tools |
| Author Draft / Graph Review diagnostics | Live under shared modules historically | **Out of Plan** | Remain `/ingest`-owned |

## 5. Target contracts

### 5.1 Graph-backed selected-object view

Shared object view shape (Plan and Graph Review consume one primitive):

```text
selected object
identity / aliases
game summary
related objects
source/evidence context
Plan-specific actions
details hidden by default
```

Plan mode hides review-only machinery by default:

- comparison status;
- gold/live lane labels;
- delta IDs;
- merge internals;
- authoring controls;
- diagnostics.

Plan mode shows game-useful information first:

- what this object is;
- why it matters now;
- related objects / connected edges;
- relevant statblock or roll-table if available;
- source/evidence access;
- “open in `/ingest`” if correction is needed.

Do **not** keep growing an independent index-shaped `SelectedObjectCard` as the durable object UI. Extract or wrap the existing Graph Review card shape (`GraphReviewNodeGameCard`) rather than rebuilding it.

### 5.2 Graph-aware chip resolution ladder

```text
dmb-ref / dmb-node locator
→ graph-aware resolver
→ Union Supergraph node view if available
→ corpus-index fallback if graph node unavailable
→ unresolved card with /ingest escalation
```

Locators stay opaque. Plan does not own taxonomy, alias merging, or identity resolution.

### 5.3 Plan-scoped prep-memory query

Current path:

```text
PlanAgentInteractionBar
→ postLiveQuery
→ /api/live/query
→ planning corpus manifest / live retrieval / Hermes option
```

That path is blocked in dogfood when `campaign_id` / `session` do not match the server’s loaded live packet. Prep memory should not depend on “whatever live packet the server booted with.”

Target path:

```text
Plan prep question
→ plan-scoped graph-memory query contract
→ Union Supergraph projection / source-backed evidence
→ answer with object refs, citations, source anchors, freshness state
```

This note does **not** implement that endpoint. The next implementation must define a plan-scoped contract that is not gated by live-packet session mismatch.

### 5.4 Source / evidence / freshness envelope

Answers and object cards remain pointers-first:

- citations and source anchors;
- freshness / proof state;
- honest ungrounded or unavailable states;
- no corpus bodies or graph internals as the default GM view.

### 5.5 `/ingest` escalation

`/ingest` owns:

- memory correction;
- Graph Review;
- Author Draft;
- identity merge;
- event-log commit;
- authored overlay writes.

Plan may show memory status, freshness, unresolved warnings, source/evidence read views, and “open in `/ingest`.” Plan must not absorb the correction cockpit.

## 6. Non-goals

- Graph-backed Q&A implementation in the re-anchor docs PR.
- Changing `/api/live/query` as part of the docs PR.
- Changing `SelectedObjectCard` or `GraphReviewNodeGameCard` in the docs PR.
- Prep packet.
- Graph writes from `/plan`.
- Author Draft or Graph Review diagnostics in `/plan`.
- Renaming the Plan / Play / Build surface model.
- Combat migration or `/play` work.
- Broad cleanup of unrelated historical docs.

## 7. Next implementation sequence

Small PRs, in order:

1. **Extract shared graph-object card model** — shared view shape + Plan mode that hides review machinery; wrap or extract from `GraphReviewNodeGameCard` rather than extending index-shaped Plan card forever.
2. **Add graph-aware resolver seam / adapter** — resolution ladder above; keep corpus-index fallback.
3. **Define plan-scoped graph-memory query contract** — not live-packet-gated; returns object refs, citations, source anchors, freshness.
4. **Wire Plan Q&A to graph-memory read path behind fallback** — keep current live-query path as fallback until the graph path is trustworthy.
5. **Dogfood and report** — exercise via `/plan?dogfood=1` and the runbook; judge success against the real prep loop, not checklist completeness.

## 8. Acceptance criteria for this re-anchor

- Docs distinguish PR314 dogfood scaffolding from durable product architecture.
- Current prep-memory drawer and Plan selected-object card are named transitional / fallback where appropriate.
- Memory correction is explicitly routed to `/ingest`.
- Union Supergraph projection is the target graph-backed read path for Plan object navigation and prep-memory Q&A.
- Source-vocabulary boundary is preserved: no graph summary as evidence.
- Next code agent has an implementation order without inferring architecture from scattered historical plans.
- No runtime behavior changes required to land this re-anchor.
