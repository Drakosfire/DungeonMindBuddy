---
document_id: dmb-handoff-pr322-plan-graph-context-contract-for-dogfood
title: Handoff - Plan Graph Context Contract Before Object-Card Dogfood Can Continue
status: ready_for_design_agent
version: 0.2
created_at: "2026-07-10"
updated_at: "2026-07-10"
branch_anchor: plan-surface/graph-object-card-dogfood
audience: designing_agent
source_role: dogfooding_agent
related_prs:
  - number: 316
    title: extract shared GraphObjectCard from Graph Review
    state: merged
  - number: 317
    title: harden GraphObjectCard and graph-aware resolver seam
    state: merged
  - number: 318
    title: wire reference chips to GraphObjectCard
    state: merged
  - number: 319
    title: Plan GraphObjectCard actions and source affordances
    state: merged
  - number: 320
    title: GraphObjectCard relationship traversal
    state: merged
  - number: 321
    title: dogfood harness + exposes graph-context blocker
    state: open
related_documents:
  - path: Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md
    role: projection_design_anchor
  - path: Docs/Design/DESIGN-plan-graph-memory-reanchor-after-dogfood-2026-07.md
    role: plan_consumer_reanchor_after_pr314
  - path: Docs/Plans/HANDOFF-design-recap-ingestion-to-supergraph.md
    role: prior_supergraph_ingest_design
suggested_next_pr: 322
roadmap_note: >
  PR321 = dogfood harness + blocker discovery (not complete usefulness dogfood).
  PR322 = Plan graph-context contract + projection load path.
  PR323 = continue object-card dogfood against a real projection.
  PR324 = Plan-scoped graph-memory Q&A contract.
  Q&A stays deferred until cards are searchable against real memory.
---

# Handoff — Plan Graph Context Contract (before dogfood can continue)

## 0. Mission for the designing agent

Design the **Plan graph-context contract** so `/plan` can load and search a real campaign/world Union Supergraph projection during prep dogfood.

Do **not** design Plan Q&A yet.

Do **not** redesign GraphObjectCard.

The product question PR321 was meant to answer is still unanswered:

```text
Can graph-projected campaign objects be added, viewed, removed, and judged useful from the GM’s perspective?
```

We cannot answer it while graph search returns unavailable for the requested Plan graph context.

## 0.1 Review outcome for PR321 (keep harness; do not claim usefulness dogfood complete)

PR321’s dogfood panel implementation is good and should survive merge:

- local add / view / remove / notes / coverage
- graph search in Edit → Insert refs
- no graph/corpus writes
- real Plan object-card path

But PR321 **cannot honestly satisfy** its original product acceptance in the current real environment, because Plan still asks for the wrong projection.

Required before merge (harness honesty, not context fix):

1. Keep this handoff as a repo artifact under `Docs/Plans/`.
2. PR body / manual test plan must say real campaign dogfood is blocked pending Plan graph-context selection.
3. Soften unavailable copy away from “memory session” framing; show requested graph-context diagnostics.
4. Make clear removal is local-only and usefulness was not validated when projection is unavailable.
5. Keep Q&A deferred.

**Do not** ask PR321 to fix the Plan graph context. That is PR322.

## 1. What shipped (substrate is real)

PR316–PR321 built a usable Plan object-card path:

| PR | What landed |
|---|---|
| 316 | Shared `GraphObjectCard` extracted from Graph Review |
| 317 | Graph-aware resolver seam |
| 318 | Plan reference chips → GraphObjectCard |
| 319 | Plan-safe actions + source/evidence affordances |
| 320 | Relationship traversal (exact `targetId`, loading-safe clicks) |
| 321 | Dogfood panel + Edit-toolbar graph search + local add/view/remove/notes + graph-context diagnostics / honest blocked copy |

Architecture clarification from dogfood (not a reimplementation of ingest):

```text
GraphObjectCard          = shared presentational primitive
GraphReviewNodeGameCard  = review wrapper (mode="review" + authoring slots)
PlanReferenceObjectCard  = plan wrapper (mode="plan" + Plan-safe actions)
```

Same builder (`buildGraphObjectCardFromNodeView`), same projection payload shape. Plan reuses the card; it does not fork a second card renderer.

## 2. What we observed in dogfood

### 2.1 Insert refs was sample-bound (fixed in PR321)

First dogfood note: Insert refs only offered hardcoded `RUNBOOK_REFERENCE_SAMPLES` (Lysandro / North Reach Gate / etc.).

Fix landed in PR321:

- Client-side search over `projection.node_views` (label, alias, kind, role, id, summary)
- Edit toolbar **Insert refs** hosts `PlanGraphRefSearch`
- Canvas stays header + markdown only (search was briefly in the main view; moved back to Edit toolbox)

### 2.2 Graph search has nothing real to search (blocker)

In Edit → Insert refs / dogfood panel, the operator sees projection unavailable for the **requested Plan graph context**.

This is not a React mounting bug. The UI is correctly reporting an empty/missing projection for the session id Plan asked for.

### 2.3 Root cause: Plan session derivation ≠ graph substrate

Current Plan derivation (`createPlanSessionDescriptor` / `buildPlanContextFromPlanView`):

```text
plan-view.session (live) = 22   # from /api/live/plan-view packet
prepSession              = 23   # live + 1
memorySession            = 21   # live - 1  ← used as graph lookup key
```

Graph search / dogfood / chip resolution then call:

```text
getUnionSupergraphProjection({
  campaignId: "longmont-c2",
  sessionId: "session-21",          // from memorySession
  useLatestGraphIngest: true,       // latest ingest run for that session only
})
```

Backend `use_latest_graph_ingest=true` resolves the latest preview union graph ingest run for the **exact** `campaign_id` + `session_id`, then builds the projection from that manifest. If Plan asks for `longmont-c2 / session-21` and there is no latest graph-ingest run for that exact key, the UI correctly gets unavailable.

Meanwhile the existing Union Supergraph **preview** substrate is **not** “latest ingest for session-21.” Default preview source is `s22-anchor-quote-n3-s23-gold`. The preview store builder uses Session 22 and Session 23 inputs, with `focus_session_id` supplied separately.

So Plan is asking the wrong question of the graph API. The dogfood UI is not broken. The graph context contract is missing.

### 2.4 What the GM actually wants

Operator intent during this dogfood:

```text
Work with the graph of sessions 23, 22, 21
+ the worldbuilding supergraph
while preparing the next session.
```

Desired mental model (already in design docs, not yet wired into Plan):

```text
One campaign/world union projection
focus_session_id = the prep-relevant focus (likely session-23)
included sources = recent recaps + worldbuilding
UI searches/navigates that one projection
browser does NOT fetch and merge three session graphs itself
```

### 2.5 `/plan?dogfood=1` is not the boutique problem

`?dogfood=1` only reveals the checklist + graph-object dogfood panel. It is not a dedicated Session-23-only route.

The boutique smell is the **hardcoded live→prep→memory arithmetic** and the **session-21 latest-ingest lookup**, not the dogfood query param.

## 3. Evidence pointers

| Claim | Where |
|---|---|
| `memorySession = ingestSession = live - 1` | `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts` |
| Graph resolver uses `session-${memorySession}` + `useLatestGraphIngest: true` | `apps/live-control-ui/src/planSurface/reference/usePlanGraphReferenceResolver.ts` |
| Requested-context diagnostic helper | `apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts` |
| Union projection API resolves latest ingest run per campaign+session | `apps/live_control_server/routes/graph_preview.py` (`use_latest_graph_ingest`) |
| Preview store is s22+s23 focused | `apps/live_control_server/services/union_supergraph_projection_adapter.py` (`TWO_SESSION_PREVIEW_SOURCE`, `_build_preview_store`) |
| Default preview source env | `apps/live-control-ui/src/api/liveApi.ts` (`s22-anchor-quote-n3-s23-gold`) |
| Design target: session is a lens, not the whole graph | `Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md` |
| Plan should consume Union Supergraph read model | `Docs/Design/DESIGN-plan-graph-memory-reanchor-after-dogfood-2026-07.md` |
| Tests encode Session 21 as memory for live 22 | `planSessionDescriptor.test.ts`, dogfood/resolver fixtures |

## 4. What must be designed / built before dogfood continues

### 4.1 Plan graph-context contract (required)

Define an explicit Plan-owned graph context, separate from the old “memory session for prep Q&A corpus” concept if those diverge.

Minimum fields to decide:

```text
campaignId
prepSession
graphFocusSessionId          # e.g. session-23
graphProjectionMode          # latest-ingest | preview-source | explicit-store | campaign-union
graphProjectionSelector      # how the API finds the store/run
includedSessionIds           # e.g. [21, 22, 23] — product claim, may be store metadata
includesWorldbuilding        # product claim
```

Decide whether `memorySession` remains a corpus/Q&A concept and graph focus becomes a sibling field, or whether Plan collapses them into one honest descriptor.

### 4.2 Projection load path for Plan (required)

Replace “always `useLatestGraphIngest` for `session-${memorySession}`” with a Plan-specific load rule that can actually return nodes for current prep.

Candidate modes (design must pick one primary for dogfood):

1. **Preview source** — use existing `s22-anchor-quote-n3-s23-gold` (or successor) with `focus_session_id=session-23` so dogfood unblocks immediately against known substrate.
2. **Latest ingest for focus session** — e.g. latest run for `session-23`, not `session-21`.
3. **Campaign-union store** — true long-term target: one store covering 21/22/23 + worldbuilding; Plan only passes focus + campaign.

Honest product copy if Session 21 is not yet in the store:

```text
Projection includes Sessions 22–23 + worldbuilding.
Session 21 is not in this store yet.
```

Do not silently claim 21/22/23 coverage the store does not have.

### 4.3 Materialization gap (likely required for full intent)

If the GM requires Sessions **21 + 22 + 23 + worldbuilding** in one searchable graph, design whether that is:

- a new/extended preview union build,
- a campaign-union materialization from existing ingest runs,
- or out of scope for the immediate unblock (document as follow-up).

UI search cannot invent Session 21 nodes that are not in the projection payload.

### 4.4 Header / dogfood honesty (required)

Plan chrome and dogfood copy must show:

```text
Preparing Session N
Graph focus: Session F
Projection: <what actually loaded>
```

So the operator is not told “memory through Session 21” while searching a Session-23-focused union, or vice versa.

PR321 already shows **requested** graph-context diagnostics in the dogfood panel. PR322 should make those fields match a load path that can succeed, and show what actually loaded.

### 4.5 Explicit non-goals for the next design slice

- Plan-scoped graph-memory Q&A (`/api/live/query` changes)
- Graph writes / node deletion / Author Draft in `/plan`
- Fuzzy identity resolution
- Graph visualization
- Replacing Graph Review
- Rebuilding GraphObjectCard

## 5. Acceptance bar for “dogfood can continue”

Dogfood resumes when an operator on `/plan?dogfood=1` can:

```text
1. Open Edit → Insert refs
2. See real projection nodes from the campaign/world graph (not “unavailable”)
3. Search by label/alias and find objects from the intended sessions/worldbuilding
4. Insert a chip and/or Add card → View through PlanReferenceObjectCard
5. Traverse relationships
6. Mark useful/thin/confusing/wrong
```

Without that, PR321 validates UI chrome + discovers the context blocker, not graph usefulness.

## 6. Suggested design outputs

The designing agent should produce:

1. **Decision record** — Plan graph-context fields and how they relate to `memorySession` / prep / live.
2. **Load algorithm** — exact `getUnionSupergraphProjection` arguments Plan will use for dogfood now vs campaign-union later.
3. **Coverage honesty** — what sessions/domains the chosen projection actually contains today.
4. **Slice plan** — smallest PR to unblock dogfood (PR322), then PR323 continue dogfood, then PR324 Q&A.
5. **Updated roadmap note** — Q&A stays paused until object-card dogfood against a real projection succeeds.

## 7. Corrected roadmap framing

```text
PR321 — dogfood harness + exposes graph-context blocker
PR322 — Plan graph-context contract + projection load path
PR323 — continue / rerun graph-object-card dogfood against a real projection
PR324 — Plan-scoped graph-memory Q&A contract
```

Original “PR322 = Q&A” is deferred until cards are searchable against real memory.

## 8. Open questions for design (do not leave implicit)

1. For current Longmont C2 prep, is **graph focus Session 23** correct even when live packet says Session 22?
2. Should Plan URL params (`?session=`, `?campaign=`) override live packet arithmetic for graph focus?
3. Is the immediate dogfood unblock allowed to use the **preview source** (`s22-anchor-quote-n3-s23-gold`), or must it be a live ingest run?
4. What is the minimum bar for “includes Session 21” — must it be in the first unblock PR, or is honest “22+23+worldbuilding only” acceptable for one dogfood pass?
5. Does prep-memory Q&A keep using `memorySession=21` while graph cards use focus `23`, or must those converge?

## 9. One-sentence brief

**Plan’s object-card path is ready; Plan’s graph lookup still asks for Session 21 latest-ingest and misses the Session 22/23 + worldbuilding union the GM needs — design the Plan graph-context contract and load path before continuing dogfood or starting Q&A.**
