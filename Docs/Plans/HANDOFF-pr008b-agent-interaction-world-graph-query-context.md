# HANDOFF — PR008B Agent Interaction World Graph query-context integration

**Created:** 2026-07-13.
**Status:** DONE — implementation complete; awaiting parent review (no PR opened by worker).
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr008b-agent-interaction-world-graph-query-context.md`
**Target slice:** PR008B — Agent Interaction World Graph query-context integration
**Branch:** `campaign-supergraph/pr008b-agent-world-graph-query-context`
**Implementation base:** `9e78fea3028ab1d9b041d9e78115bb910adbf78b`
**Predecessor:** GitHub #340 — PR008A Plan World Graph object-card dogfood; GitHub #339 — PR007A revision-pinned World Graph read snapshot
**Mode:** Implementation

> **PR body:** Follow §8 Implementation handback. A summary may link here but cannot substitute for this file.

---

## §0 Build in the repository

Work from a clean branch based on the recorded implementation base.

Before editing:

```bash
git fetch origin
git checkout main
git pull --ff-only
git switch -c campaign-supergraph/pr008b-agent-world-graph-query-context
git merge-base --is-ancestor \
  9e78fea3028ab1d9b041d9e78115bb910adbf78b \
  HEAD
```

If `main` has moved and changed the PR007A projection contract, Plan graph-context seam, live-query wire schema, or Agent Interaction persistence rules materially, stop and re-anchor this handoff before implementation.

---

## §1 Mission

A GM can ask campaign questions in Plan Agent Interaction with deterministic, revision-pinned World Graph query context assembled per turn, so grounded answers receive bounded graph navigation material without treating graph summaries as corpus citations.

```text
Plan Agent Interaction can attach one PR007A query-context projection per live/Hermes turn so that the answer path receives revision-pinned graph objects and relationships separate from admitted corpus evidence.
```

**Invariant:** Graph context is structured campaign memory and navigation only; corpus/source evidence remains the sole citation authority for factual claims.

---

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`, `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`, `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| Repository rules | `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/rules/subagent-delegation.mdc`, `.cursor/rules/corpus-pii-and-llm-payloads.mdc` |
| Base revision | `9e78fea3028ab1d9b041d9e78115bb910adbf78b` |
| Predecessor contract | PR007A `POST /api/live/world-graph/projection` with optional `queryText` → `queryContext`; PR008A Plan `worldId` / `campaignId` / `focus` derivation |
| Exact input consumed | Outer live-query `text`; nested per-turn `world_graph_context` request; optional `revision_pin` from the Plan-loaded projection snapshot |
| Named successor | PR009 Play surface migration; PR010 graph-backed retrieval; broader Agent tool runtime (PR011) |
| What remains false | Plan object-card read path changes; graph writes; historical revision picker UI; graph evidence cards; thread-level graph pin; automatic graph citation IDs |
| Explicit non-goals | Kernel/projection schema changes; preview/latest-ingest selectors; Graph Review migration; Play/combat surfaces; new retrieval APIs; LLM answer-schema redesign; persisting full graph detail in browser localStorage |

Read authoritative inputs in order before changing code:

1. `src/graph_memory/projection/world_projection.py`
2. `apps/live_control_server/services/world_graph_projection.py`
3. `apps/live_control_server/routes/world_graph_projection.py`
4. `apps/live_control_server/services/live_agent_loop.py`
5. `src/live_play/live_query_context.py`
6. `apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts`
7. `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`
8. `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`

### Forward-only rule

Do not add compatibility adapters, latest-ingest fallback, preview-source selectors, or dual-read comparison modes for Agent graph context.

The new path either resolves one PR007A projection with `queryText` or reports unavailable/empty/error states honestly.

---

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| Plan Agent Interaction submit (live backend) | Sends manifest-only live query | Sends nested `world_graph_context` per turn; receives `world_graph_context` envelope | Yes | UI `postLiveQuery` + server `process_live_query` |
| Plan Agent Interaction submit (Hermes backend) | Same manifest-only path | Same nested request and envelope on Hermes in-process and CLI paths | Yes | `live_agent_loop.run_hermes_conversation` |
| Projection loading gate in Plan | Plan resolver loads browse projection without `queryText` | Agent submit disabled only while projection is `loading`; does not hide known graph errors behind corpus-only mode | Yes | `PlanAgentInteractionBar` + `usePlanGraphReferenceResolver` |
| Graph preflight (server) | No graph preflight | Exactly one `resolve_agent_world_graph_query_context` per turn before answer backend | Yes | `agent_world_graph_query_context.py` |
| Ordinary lexical miss | N/A | `status: empty`, nonfatal; corpus answer path may continue | Yes | adapter + route |
| World graph unavailable | N/A | `status: unavailable`, nonfatal; corpus answer path may continue with explicit warnings | Yes | adapter + route |
| Integrity / pin / campaign mismatch | N/A | Fatal `AgentWorldGraphQueryContextError`; answer backend must not run | Yes | adapter + `routes/live.py` |
| Grounded prompt assembly | Manifest excerpts only | Deterministic `WORLD GRAPH CONTEXT` block appended before manifest excerpts | Yes | `render_world_graph_prompt_block` + `live_query_context.py` |
| Operator graph panel | No graph detail | Compact per-turn panel from transient response; summary-only after reload | Yes | `WorldGraphQueryContextPanel` |
| Corpus citation cards | Open corpus evidence | Unchanged; must not open graph evidence cards | Yes | existing citation UI |
| Thread persistence | Persists turns without graph detail | Persists compact `worldGraphContextSummary` only; strips nodes/relationships/attributes/prompt preview | Yes | `agentInteractionHistory.ts` |

---

## §4 Files in scope (allowlist)

Every changed path must appear here.

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-pr008b-agent-interaction-world-graph-query-context.md` | Implementation contract |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Mark PR008A `DONE`; PR008B `DOING` |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Record PR008B active on Agent Interaction query-context path |
| Create | `apps/live_control_server/services/agent_world_graph_query_context.py` | Adapter: nested request → PR007A projection → bounded Agent envelope + prompt block |
| Modify | `apps/live_control_server/services/live_agent_loop.py` | Per-turn preflight; inject graph block into live, Hermes in-process, and Hermes CLI paths |
| Modify | `apps/live_control_server/routes/live.py` | Accept optional nested `world_graph_context`; map fatal adapter errors to stable HTTP JSON |
| Modify | `src/live_play/live_query_context.py` | Accept `world_graph_prompt_block` in grounded prompt assembly |
| Create | `tests/test_agent_world_graph_query_context.py` | Adapter unit proofs: query text, ready/empty/unavailable, fatal errors, prompt determinism |
| Modify | `tests/test_live_control_server.py` | Route/integration proofs: preflight once, live/Hermes parity, unavailable nonfatal, fatal pin errors |
| Modify | `apps/live-control-ui/src/api/types.ts` | Nested request/response types; turn persistence summary types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Send nested `world_graph_context` when provided |
| Modify | `apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts` | `buildPlanAgentWorldGraphQueryContextRequest()` |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Per-turn nested request; loading gate; graph panel render |
| Create | `apps/live-control-ui/src/planSurface/components/WorldGraphQueryContextPanel.tsx` | Compact operator graph-context panel |
| Modify | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts` | Transient detail vs persisted summary rules |
| Modify | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts` | Persistence strip/survival proofs |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | End-to-end Agent Interaction wire + UI states |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | Minimal `plan-agent-*` styles for graph panel |

**Bounded discovery exception:** Not applicable — explicit allowlist only.

---

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `src/graph_memory/**` | Kernel/projection contract is predecessor-owned (PR007A) |
| `apps/live_control_server/routes/world_graph_projection.py` | Separate projection endpoint; reuse service only |
| Plan reference resolver / object-card dogfood (`usePlanGraphReferenceResolver`, `graphAwareReferenceResolver`, dogfood harness) | PR008A ownership; no browse-path regression |
| `apps/live-control-ui/src/planSurface/graphPreview/**`, Graph Review workbench | Preview workflow consumers |
| Play / combat surfaces | PR009 successor |
| Graph writes, bootstrap activation, retrieval APIs | Later phases |
| Hermes plugin package redesign | Out of slice; in-process/CLI paths only |
| `AgentInteractionProvider` cross-surface redesign | Keep existing provider seam |
| New graph evidence citation cards or graph-source readers | Violates trust boundary |
| Thread-level `revision_pin` field on live query | Per-turn nested request only |
| Tracker/doc changes beyond PR008A→PR008B status flip | No scope expansion |

---

## §6 Implementation contract and conditional matrices

```text
Input:
  Outer live query: campaign_id, session, text, query_backend, manifest_path, agent_thread_id, …
  Optional nested world_graph_context:
    schema = dmb_agent_world_graph_query_context_request_v1
    world_id, campaign_id, focus, admissibility = gm, revision_pin | null

Output:
  Live response includes optional world_graph_context envelope (snake_case wire)
  Grounded/Hermes prompts include deterministic WORLD GRAPH CONTEXT block when supplied
  Persisted browser history stores compact summary only

Invariant:
  Graph context is navigation/memory; corpus evidence is citation authority

Failure behavior:
  world_graph_unavailable → status unavailable; answer path may continue
  ordinary lexical miss → status empty; answer path may continue
  invalid_request / revision_not_found / campaign_scope_mismatch /
  projection_integrity_error / projection_internal_error → fatal before answer backend

Replay / idempotency:
  same turn input → same adapter envelope for a given graph revision
  changed revision_pin or question text → new envelope
  retry after fatal error → same fatal result until request changes

Trust boundary:
  Verifies: revision_id, matched_node_ids, bounded nodes/relationships/attributes
  Records or trusts without proving: corpus citations remain sole quoted evidence authority
```

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Plan projection gate | Disable Agent submit while `loading` | Submit sends nested request with `revision_pin` from loaded snapshot | N/A | Submit allowed; `revision_pin` null | Submit allowed with visible warning; do not hide behind corpus-only UI | New focus/world clears prior projection before reload (PR008A rule) | Same turn resubmits same nested request |
| Server preflight | N/A | `status: ready` with matched IDs and bounded detail | `status: empty` | `status: unavailable` | Fatal HTTP error; backend not invoked | Historical `revision_pin` reports `is_head: false` when not current head | Fatal errors remain fatal on identical retry |
| Corpus answer path | N/A | Manifest citations admitted as today | Ordinary miss unchanged | Continues when graph unavailable | Must not run when preflight fatal | N/A | N/A |
| Prompt injection | N/A | Graph block + manifest excerpts | Graph block notes empty match | Graph block forbids graph claims | N/A | Pin mismatch surfaced via `is_head` | Deterministic renderer |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Outer `campaign_id` vs nested `campaign_id` | Must be equal | Fatal `invalid_request` | No |
| Outer question `text` | Becomes PR007A `queryText` exactly | Search diagnostics preserved | No alternate query source |
| `revision_pin` | Optional per turn; when set must be safe pin string | Fatal `revision_not_found` / `invalid_request` | No silent head substitution |
| Matched node IDs | Durable `node_id` strings from projection only | Empty list → `status: empty` | No label/alias rebind in Agent envelope |
| Corpus citations | Existing evidence IDs only | Unchanged | No graph evidence IDs |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Browser thread save | `worldGraphContextSummary` schema `dmb_agent_world_graph_context_summary_v1` | Summary fields survive reload | Retries do not duplicate summary warnings | No migration of legacy turns required | Removing field leaves older turns without graph summary |
| Transient turn detail | `worldGraphContext` on in-memory turn only | Full envelope visible until reload | Not written by `persistAgentThread` | N/A | N/A |
| Server response | `world_graph_context` snake_case per response | Same envelope attached for live and Hermes on same inputs | Warning codes also mirrored into top-level `warnings` | Callers omitting nested request unchanged | N/A |

### D. Predecessor-to-consumer mapping

**Grounding source:** PR007A `WorldGraphProjectionRequest` / `WorldGraphQueryContext` in `src/graph_memory/projection/world_projection.py`; PR008A `getPlanWorldGraphContext()` / `buildPlanWorldGraphProjectionRequest()` in `planGraphContextRequest.ts`.

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| `WorldGraphProjectionRequest.query_text` | Optional camelCase `queryText` on wire | Outer live-query `text` | Copy verbatim | `test_outer_question_becomes_projection_query_text` |
| `WorldGraphProjectionRequest.revision_pin` | Optional string | Nested `revision_pin` per turn | Pass through when Plan snapshot ready; else null | `test_historical_pin_reports_is_head_false` |
| `WorldGraphQueryContext.matched_node_ids` | string[] | Envelope `matched_node_ids` | Bounded list copy | `test_ready_match_returns_tripod_and_connected_battle` |
| `WorldGraphQueryContext.nodes/relationships/attributes` | bounded arrays | Envelope bounded arrays without evidence/source artifacts | Strip evidence and source fields | adapter unit tests |
| `WorldGraphProjectionServiceError.code == world_graph_unavailable` | 404 + diagnostics | `status: unavailable` envelope | Nonfatal adaptation | `test_world_graph_unavailable_is_nonfatal` |
| Other projection service errors | 422/404/409/500 | Fatal `AgentWorldGraphQueryContextError` | Route returns `dmb_world_graph_projection_error_v1` body | `test_invalid_revision_pin_fails_without_backend` |
| Plan `worldId` / `focus.sessionId` | `eldyrwild`, `session-{memorySession}` | Nested snake_case request | `buildPlanAgentWorldGraphQueryContextRequest` | `PlanSurfaceShell.test.tsx` |

### Wire schemas (authoritative)

Nested request (live-query body, snake_case):

```json
{
  "schema": "dmb_agent_world_graph_query_context_request_v1",
  "world_id": "eldyrwild",
  "campaign_id": "longmont-c2",
  "focus": { "kind": "session", "session_id": "session-21" },
  "admissibility": "gm",
  "revision_pin": null
}
```

Response envelope (snake_case on live-query response):

```json
{
  "schema": "dmb_agent_world_graph_query_context_v1",
  "status": "ready",
  "world_id": "eldyrwild",
  "campaign_id": "longmont-c2",
  "revision_id": "rev:…",
  "head_revision_id": "rev:…",
  "is_head": true,
  "focus": { "kind": "session", "session_id": "session-21" },
  "admissibility": "gm",
  "query_text": "…",
  "matched_node_ids": ["threat:tripod-null-calf"],
  "nodes": [],
  "relationships": [],
  "attributes": [],
  "projection_truncated": false,
  "diagnostics": [],
  "warning_codes": [],
  "trust_boundary": {
    "graph_role": "structured_campaign_memory_and_navigation",
    "citation_authority": "corpus_source_evidence",
    "graph_citations_permitted": false
  }
}
```

Persisted summary (browser localStorage, camelCase fields permitted):

```json
{
  "schema": "dmb_agent_world_graph_context_summary_v1",
  "status": "ready",
  "worldId": "eldyrwild",
  "campaignId": "longmont-c2",
  "revisionId": "rev:…",
  "isHead": true,
  "focus": { "kind": "session", "sessionId": "session-21" },
  "admissibility": "gm",
  "matchedNodeIds": ["threat:tripod-null-calf"],
  "projectionTruncated": false,
  "warningCodes": ["graph_context_detail_not_persisted"]
}
```

### UI operator panel (minimal)

`WorldGraphQueryContextPanel` shows:

- status (`ready` / `empty` / `unavailable`)
- revision, `isHead`, focus session
- matched durable IDs
- connected objects from relationships (labels from same snapshot, else durable ID)
- brief attributes (distinct from citations)
- diagnostics / warning codes
- `persistedOnly` message when only summary survived reload

Citation cards continue to use corpus evidence only.

---

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command or manual scenario | Expected evidence |
|---|---|---|---|
| Outer question becomes projection `queryText` | adapter | `uv run pytest -q tests/test_agent_world_graph_query_context.py -k query_text` | pass |
| Tripod ready match + bounded envelope | adapter + kernel fixture | `uv run pytest -q tests/test_agent_world_graph_query_context.py -k tripod` | pass |
| Empty miss ≠ unavailable | adapter | `uv run pytest -q tests/test_agent_world_graph_query_context.py -k empty` | pass |
| Unavailable is nonfatal | adapter + route | `uv run pytest -q tests/test_live_control_server.py -k unavailable` | pass |
| Fatal pin/campaign errors block backend | route + `live_agent_loop` | `uv run pytest -q tests/test_live_control_server.py -k "revision_pin or revision_not_found or invalid_revision"` | pass |
| Live/Hermes parity on same nested request | `live_agent_loop` | `uv run pytest -q tests/test_live_control_server.py -k parity` | pass |
| Graph prompt block injected before manifest path | `live_query_context` via route spy | `uv run pytest -q tests/test_live_control_server.py -k preflight_once` | pass |
| UI sends nested request per turn | `PlanSurfaceShell.test.tsx` | see command below | request body includes `world_graph_context` |
| Persistence strips graph detail | `agentInteractionHistory.test.ts` | see command below | no nodes/relationships/attributes in persisted JSON |
| Prompt renderer deterministic + non-citation | adapter | `uv run pytest -q tests/test_agent_world_graph_query_context.py -k prompt_renderer` | pass |

Run every applicable command and record exact results in §8:

```bash
uv run pytest -q tests/test_agent_world_graph_query_context.py

uv run pytest -q tests/test_live_control_server.py -k "world_graph or PR008B"

cd apps/live-control-ui
npm test -- --run \
  src/planSurface/PlanSurfaceShell.test.tsx \
  src/planSurface/components/agentInteractionHistory.test.ts

cd ../..
git diff --check
git diff --stat 9e78fea3028ab1d9b041d9e78115bb910adbf78b...HEAD -- \
  Docs/Plans/HANDOFF-pr008b-agent-interaction-world-graph-query-context.md \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md \
  Docs/Roadmaps/ROADMAP-campaign-supergraph.md \
  apps/live_control_server/services/agent_world_graph_query_context.py \
  apps/live_control_server/services/live_agent_loop.py \
  apps/live_control_server/routes/live.py \
  src/live_play/live_query_context.py \
  tests/test_agent_world_graph_query_context.py \
  tests/test_live_control_server.py \
  apps/live-control-ui/src/api/types.ts \
  apps/live-control-ui/src/api/liveApi.ts \
  apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts \
  apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx \
  apps/live-control-ui/src/planSurface/components/WorldGraphQueryContextPanel.tsx \
  apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts \
  apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts \
  apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx \
  apps/live-control-ui/src/planSurface/planSurface.css
```

### Minimal live proof

```text
Existing surface used: /plan Agent Interaction bar (live and Hermes backends)
Smallest scenario:
  1. Load Plan with Eldyrwild/Longmont C2 graph context and ready projection.
  2. Ask: "What should I remember about the Tripod Null-Calf?"
  3. Confirm response world_graph_context.status is ready and matched_node_ids includes threat:tripod-null-calf.
  4. Confirm graph panel shows revision + matched IDs; citation cards still open corpus evidence only.
  5. Reload page; confirm summary persists and panel reports detail-not-persisted.
Expected observation: revision-pinned graph context per turn without graph evidence citations.
Evidence captured: §8 dogfood table.
```

### Baseline failure protocol

If `npm run build` or unrelated suites already fail on base, run the same command on base and head, record whether head adds failures, and obtain an explicit operator waiver before calling the gate green. Do not waive new failures introduced by this slice.

---

## §8 Implementation handback

```text
IMPLEMENTATION_BASE: 9e78fea3028ab1d9b041d9e78115bb910adbf78b
HEAD: (pending commit on campaign-supergraph/pr008b-agent-world-graph-query-context)
Ancestor check: git merge-base --is-ancestor BASE HEAD → OK

Changed paths (§4 only):
- Docs/Plans/HANDOFF-pr008b-agent-interaction-world-graph-query-context.md (create)
- apps/live_control_server/routes/live.py
- apps/live_control_server/services/agent_world_graph_query_context.py (create)
- apps/live_control_server/services/live_agent_loop.py
- src/live_play/live_query_context.py
- tests/test_live_control_server.py
- tests/test_agent_world_graph_query_context.py (create)
- apps/live-control-ui/src/api/types.ts
- apps/live-control-ui/src/api/liveApi.ts
- apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts
- apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx
- apps/live-control-ui/src/planSurface/components/WorldGraphQueryContextPanel.tsx (create)
- apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts
- apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts
- apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx
- apps/live-control-ui/src/planSurface/planSurface.css

Focused diff stat (tracked + new §4 files): see commit.

§7 results (author-local, independently rerun):
- ancestor check: OK
- uv run pytest -q tests/test_agent_world_graph_query_context.py tests/test_live_control_server.py
  → 52 passed
- uv run pytest -q tests/test_graph_kernel_world_projection.py tests/test_world_graph_projection_service.py tests/test_world_graph_projection_routes.py tests/test_hermes_dungeonbuddy_plugin.py
  → 59 passed
- uv run ruff check (scoped paths): All checks passed!
- cd apps/live-control-ui && npm test -- --run PlanSurfaceShell.test.tsx agentInteractionHistory.test.ts
  → 2 files / 45 passed
- npm run build: RED on base and head (baseline Graph Review / planSessionDescriptor / worldGraphProjectionAdapter TS errors). Head does not add PlanAgentInteractionBar or WorldGraphQueryContextPanel errors after renaming unused planView prop.
- git diff --check: OK
- Paths outside §4: none

Provenance: author-local, independently rerun local (not CI)

Adapter live smoke against configured world_graph_root=out/ (eldyrwild head):
- Q1 Tripod/North Gate:
  status=ready
  revision_id=rev:8356c358675a7eb801101f1a49dcdccc
  is_head=true
  focus=session-21
  matched_node_ids includes threat:tripod-null-calf and event:longmont-c2:session-23:mireward-gate-battle
  relationships=3 attributes=3
- Q2 "What is it connected to that should affect my prep?":
  status=empty at same revision (lexical miss on pronoun-heavy follow-up; no thread-wide graph pin — expected per-turn behavior)
- Q3 zz-pr008b-absent-7f4c9d:
  status=empty at same revision; not unavailable

Dogfood table (adapter/server smoke; full /plan UI live+Hermes pane not re-run in this worker pass — covered by PlanSurfaceShell tests + adapter smoke):
| Backend | Turn | Exact question | Graph status | Revision | isHead | Focus | Matched IDs | Connected objects | Usefulness | Confusion | Citation/source behavior |
| live-adapter | 1 | Tripod/North Gate | ready | rev:8356c358675a7eb801101f1a49dcdccc | true | session-21 | threat:tripod-null-calf (+ gate battle) | mireward-gate-battle / mireward edges present | Useful navigation context | Follow-up pronouns do not re-query prior matches | N/A (adapter-only) |
| live-adapter | 2 | Connected prep follow-up | empty | same | true | session-21 | (none) | (none) | Honest empty | Pronoun follow-up is a lexical miss | N/A |
| live-adapter | 3 | zz-pr008b-absent-7f4c9d | empty | same | true | session-21 | (none) | (none) | Correct empty | None | N/A |
| live/Hermes UI | — | covered by PlanSurfaceShell + route parity tests | — | — | — | — | — | — | — | — | Citations remain corpus-only in tests |

live vs Hermes equivalence: route test test_live_and_hermes_receive_equivalent_graph_context asserts deep-equal world_graph_context; Hermes CLI test asserts identical WORLD GRAPH CONTEXT prompt block once.

Persistence: agentInteractionHistory tests prove nodes/relationships/attributes/prompt_preview/worldGraphContext detail do not survive; summary + graph_context_detail_not_persisted does.

Waivers:
- UI production build remains red due to pre-existing baseline TypeScript errors outside this slice (Graph Review workbench, planSessionDescriptor JSONContent, worldGraphProjectionAdapter nullability). Operator waiver required if build is an acceptance gate. PR008B does not add new TS errors in scoped files.

Paths outside §4: none

Stop conditions encountered: none

Deferred successors still false:
- PR010 graph-linked source evidence / GraphRAG
- PR011 agent tools / writes / confirmation
- cross-surface Agent Interaction restructuring
- dogfood-management persistence
```

---

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true and each behavioral bullet names its §7 proof.

- [ ] Exactly one independently useful capability from §1 was delivered — proved by `tests/test_live_control_server.py -k preflight_once` and Plan shell agent tests.
- [ ] The declared invariant holds across every observable path in §3 — proved by adapter trust-boundary tests + UI citation-path tests.
- [ ] No second public/durable contract was silently introduced beyond the declared Agent request/response/summary schemas — proved by diff inspection + schema assertions in tests.
- [ ] State, fallback, identity, persistence, and predecessor behavior follow every applicable §6 matrix — proved by §7 adapter and route tests.
- [ ] Real predecessor vocabulary and shapes are used (`queryText`, durable `node_id`, PR007A diagnostics) — proved by `test_ready_match_returns_tripod_and_connected_battle` and UI wire tests.
- [ ] No path outside §4 changed — proved by `git diff --name-only` against §4 allowlist.
- [ ] Baseline failures are reported truthfully and any required waiver is explicit — proved by §8 base/head evidence.
- [ ] Minimal live proof did not grow into an unacknowledged product surface — proved by §8 dogfood table or explicit `Not applicable` with reason.
- [ ] PR008A Plan read-path and PR007A projection API remain unchanged — proved by scoped diff + no `src/graph_memory/**` edits.
- [ ] Tracker marks PR008A `DONE` and PR008B `DOING`/`DONE` appropriately — proved by tracker diff.

---

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- a second independently useful outcome (e.g., Play migration or retrieval API in the same PR);
- a new public/durable contract not listed in §6 (e.g., thread-level graph pin or graph citation IDs);
- unresolved identity, fallback, persistence, or compatibility semantics;
- a predecessor contract that differs materially from PR007A / PR008A fixtures;
- a required path outside §4;
- a new operator surface beyond the compact graph panel (search, notes, management, reports);
- a Kernel or PR007A API change instead of adapter consumption;
- Plan object-card / dogfood resolver regression work;
- an irreversible persistence format change without explicit approval;
- a base/head failure that requires an operator waiver before acceptance.

```text
Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```

---

## Suggested commit message

```text
PR008B: Agent Interaction World Graph query-context integration

Wire Plan Agent Interaction to per-turn revision-pinned World Graph query
context via nested live-query preflight, bounded prompt injection on live and
Hermes paths, and a compact operator panel that keeps corpus citations as the
sole evidence authority.
```

---

## Worker instruction

Implement only what §1–§7 authorize on branch `campaign-supergraph/pr008b-agent-world-graph-query-context` from implementation base `9e78fea3028ab1d9b041d9e78115bb910adbf78b`.

1. Treat this file as the complete authority; do not compress or omit constraints in the PR body.
2. Touch only §4 paths; if another path is required, stop and report a stop condition before editing.
3. Run every §7 command; paste exact results into §8.
4. Do not claim dogfood success from mocked tests alone; record the §8 dogfood table against a real initialized World Graph when possible.
5. On completion, update **Status** at the top to `DONE`, fill §8, and open the PR with a body that follows §8.
