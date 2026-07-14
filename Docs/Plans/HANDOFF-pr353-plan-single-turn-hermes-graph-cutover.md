---
pr_body_template: |
  ## Outcome

  A GM using the existing Plan Agent Interaction pane can select Hermes and receive one graph-grounded answer with graph-admitted citations and an inspectable tool trace through the existing `/api/live/query` product path, without invoking legacy retrieval or claiming conversational continuity.

  ## Scope and verification

  * Predecessor base: `e6a95e267f743d78239500209dd7333a6f65cf67` (merge of GitHub PR #352)
  * Implementation base: the docs-only commit that lands this handoff on `main`
  * Changed paths: report the actual §4 paths
  * Verification: report every §7 command and live scenario with exact result and provenance
  * Baseline failures and waivers: compare the complete suite on predecessor and head; do not inherit PR #352's author-local counts without rerunning
  * Deferred successors: same-thread Hermes continuity, reload/session-pointer continuity, product-path demolition, backend-toggle removal, and all write tools
---

# HANDOFF — PR010B Rung 4: Plan single-turn Hermes graph cutover

**Created:** 2026-07-14  
**Status:** ACTIVE — dispatch exactly one implementation capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr353-plan-single-turn-hermes-graph-cutover.md`  
**Predecessor base:** `e6a95e267f743d78239500209dd7333a6f65cf67` — merge of GitHub PR #352  
**Implementation base:** the docs-only commit that lands this handoff on `main`; record the immutable SHA before dispatch  
**Suggested branch:** `agent/pr010b4-plan-single-turn-hermes-graph-cutover`  
**Suggested PR title:** `feat(agent): cut Plan Hermes queries over graph-agent runtime`

> **Dispatch gate**
>
> Commit this handoff before dispatch. Use that docs-only commit as the implementation base while retaining `e6a95e267f743d78239500209dd7333a6f65cf67` as the predecessor anchor.
>
> This checked-in handoff is the complete authority. The worker must implement it without compression, omission, or silent reinterpretation.
>
> Opening the implementation pull request must be the final repository action. Do not open a draft early.

---

## §0 Capability decomposition decision

PR010B is a product ladder, not one implementation slice. Rung 3 proved a reusable embedded Hermes turn but deliberately did not expose it through the Plan product path. This slice makes exactly one independently useful product journey true: one factual Plan question reaches that graph-only turn and returns a usable answer, citations, and trace.

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Host the process-exclusive Rung 3 runtime behind a persistent isolated local worker boundary | No — required safety boundary for product invocation | Yes — internal host request/result contract | No | Yes | Yes | Include |
| Route `query_backend="hermes"` from the existing Plan `/api/live/query` path to one Rung 3 turn | Yes — mission capability | Yes — live-query Hermes behavior | Yes | Yes | Yes | Include |
| Resolve authoritative graph scope before dispatch and pin the Hermes turn to the resolved revision | No — required trust boundary | Yes — product dispatch contract | No | Yes | Yes | Include |
| Shape one Rung 3 result into the existing answer-first response with graph grounding state, safe trace, and graph-anchor citations | No — required product result | Yes — additive response contract | Yes | Yes | Yes | Include |
| Open a cited source through the existing opaque `source-anchor/read` route | No — required citation journey | Yes — additive client citation variant only | Yes | Yes | Yes | Include |
| Enforce explicit abstention or error when graph evidence is insufficient or runtime grounding is absent | No — required failure side of the same factual boundary | Yes — observable response state | Yes | Yes | Yes | Include |
| Preserve bounded graph-citation metadata in the existing local turn record | No — required round trip for the same answer | Yes — additive persisted citation variant | Yes | Yes | Yes | Include |
| Carry prior turns into Hermes and resolve same-thread pronouns such as “it” | Yes | Yes | Yes | Yes | Yes | Successor — Rung 5 |
| Persist and restore a Hermes session pointer across page reload or process restart | Yes | Yes | Yes | Yes | Yes | Successor — Rung 6 |
| Delete manifest/corpus/lexical/arbitrary-path/CLI-one-shot/Live fallback paths | Yes | Yes | Yes | Yes | Yes | Successor — Rung 7 |
| Remove the Live/Hermes backend selector and make Hermes the sole steady-state Plan backend | Yes | Yes | Yes | Yes | Yes | Successor — Rung 7 after acceptance |
| Add writes, drafts, preview/confirm, or generalized agent capabilities | Yes | Yes | Yes | Yes | Yes | Successor — PR011 |
| Reconcile tracker and roadmap to the seven-rung ladder | No — authority synchronization | No runtime contract | No | No | No | Include |

**Selected capability**

A safe, single-turn product cutover for the existing Plan Hermes mode: one factual request is dispatched through a persistent process-isolated host to the merged Rung 3 graph agent and returned as an answer-first response with graph-admitted citations, safe trace, and fail-closed abstention behavior.

**Why the included rows share one invariant**

The process boundary, route adapter, response contract, citation interaction, and UI proof are all necessary to make one product request genuinely graph-only. Removing any one of them either leaves Rung 3 unreachable, exposes an unsafe in-process runtime, makes the result unusable, or permits an ungrounded answer to masquerade as success.

**Named successors**

1. **PR010B Rung 5 — same-thread Hermes continuity:** send bounded prior conversation history, bind one Hermes conversational identity to one Agent Interaction thread, and prove fresh graph reads on follow-up questions.
2. **PR010B Rung 6 — reload/session-pointer continuity:** persist and restore the thread-to-Hermes session pointer without treating chat as campaign canon.
3. **PR010B Rung 7 — product acceptance and demolition:** remove legacy Hermes retrieval, CLI one-shot product behavior, Live synthesis fallback, and the steady-state backend toggle.
4. **PR011 — Agent Context + governed tool runtime:** add typed non-read capabilities, preview/confirm, and app-level context assembly only after PR010B acceptance.

---

## §1 Mission

```text
A GM using the existing Plan Agent Interaction pane can select Hermes and receive one graph-grounded answer with graph-admitted citations and an inspectable tool trace through the existing /api/live/query product path, without invoking legacy retrieval or claiming conversational continuity.
```

**Invariant**

```text
Every Plan request with query_backend="hermes" is answered, abstained, or failed solely from one server-scoped, revision-pinned Rung 3 graph-agent turn running behind a persistent process-isolated host; no manifest, corpus, arbitrary-path, lexical, CLI-one-shot, ambient-memory, prior-turn, or Live-synthesis path may contribute to the answer or rescue a failure.
```

**Mission falsification test**

```text
This is not one slice if implementation must also preserve conversational meaning across turns, resume a Hermes session after reload, delete all legacy runtime code, remove the backend selector, change graph retrieval semantics, add a new Agent Interaction surface, or enable any write-capable tool.
```

---

## §2 Context, authority, and boundaries

| Field | Required content |
| --- | --- |
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Design/ANCHOR-agent-interaction-hermes.md`; `Docs/Design/UX-STORIES-agent-interaction-hermes.md`; `.hermes.md` |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md`; `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` |
| Predecessor base | `e6a95e267f743d78239500209dd7333a6f65cf67` — merge of GitHub PR #352 |
| Implementation base | Docs-only commit that lands this handoff on `main`; record immutable SHA before dispatch |
| Predecessor contract | PR #352 `HermesGraphAgentTurnRequest`, `HermesGraphAgentTurnResult`, safe ordered tool events, configurable fail-closed capability policy, exact five-tool plugin surface, and process-exclusive isolation statement; PR010A retrieval/source-anchor models and routes; existing `dmb_live_query_response_v1` product envelope |
| Exact input consumed | Existing `POST /api/live/query` request with `query_backend="hermes"`, non-empty question, outer campaign/session, existing Agent Interaction thread ID, optional trace flag, and required nested `dmb_agent_world_graph_query_context_request_v1` |
| Named successor | PR010B Rung 5 — same-thread Hermes continuity |
| What remains false | No prior-turn history reaches Hermes; no thread-to-Hermes session binding; no reload/session resume; no permanent default-backend cutover; no legacy-code demolition; no write tools; no Play integration |
| Explicit non-goals | New chat UI, new citation panel, new graph retrieval operation, graph writes, cancellation transport, cross-surface context, provider abstraction lift, arbitrary source browsing, compatibility fallback, server-side thread persistence, generalized multi-worker scheduling, or app-wide agent runtime |

### Current repository state that constrains this slice

The merged predecessor contains a real Rung 3 `AIAgent` turn, but its own module contract states that it is **process-exclusive, not generally server-safe**. During a turn it mutates process-wide `sys.path`, `sys.modules["agent..."]`, and `HERMES_HOME`. Its private lock serializes Rung 3 callers against each other but cannot protect unrelated FastAPI threads. Directly importing and invoking it from the live-control request thread is prohibited for this slice.

The current product Hermes branch is still transitional:

* `process_live_query(..., query_backend="hermes")` calls `run_hermes_conversation` in `live_agent_loop.py`;
* that path may invoke `hermes --oneshot` or the legacy `dungeon_context_lookup` plugin;
* the graph envelope is attached for inspection but is not the factual Hermes tool boundary;
* the browser always sends `manifest_path`, including for Hermes requests;
* the browser forwards a stored `hermes_session_id`, even though Rung 3 does not provide product continuity;
* existing citations are path-shaped and use the arbitrary-path citation reader, while PR010A provides an opaque source-anchor read route.

The repository already has the required source-reader surface at:

```text
POST /api/live/world-graph/retrieval/source-anchor/read
```

It accepts the strict PR010A `WorldGraphSourceAnchorReadRequest`. Do not add a second source-reading route.

### Required authority synchronization

Update tracker and roadmap to this sequence:

```text
DONE    PR010B Rung 1 — graph-only read-tool executor (#350)
DONE    PR010B Rung 2 — model-visible catalog and JSON adapter (#351)
DONE    PR010B Rung 3 — embedded single-turn Hermes AIAgent (#352)
DOING   PR010B Rung 4 — Plan single-turn Hermes graph cutover
NEXT    PR010B Rung 5 — same-thread Hermes continuity
LATER   PR010B Rung 6 — reload/session-pointer continuity
LATER   PR010B Rung 7 — product acceptance and legacy demolition
```

Do not renumber PR011 or PR012. PR009 remains a parallel product lane.

### Read authoritative inputs in order before changing code

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
3. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
4. `Docs/Design/ANCHOR-agent-interaction-hermes.md`
5. `Docs/Design/UX-STORIES-agent-interaction-hermes.md`
6. `.hermes.md`
7. `Docs/Plans/HANDOFF-pr352-hermes-embedded-graph-agent-turn.md`
8. `apps/live_control_server/services/hermes_graph_agent.py`
9. `src/graph_memory/hermes_graph_plugin.py`
10. `src/graph_memory/retrieval/models.py`
11. `apps/live_control_server/routes/world_graph_retrieval.py`
12. `apps/live_control_server/services/agent_world_graph_query_context.py`
13. `apps/live_control_server/routes/live.py`
14. `apps/live_control_server/services/live_agent_loop.py`
15. `apps/live_control_server/main.py`
16. `apps/live-control-ui/src/api/types.ts`
17. `apps/live-control-ui/src/api/liveApi.ts`
18. `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`
19. `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx`
20. `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
21. `tests/test_hermes_graph_agent.py`
22. `tests/test_world_graph_retrieval_routes.py`
23. Existing live-query and Plan Agent Interaction owning tests
24. `AGENTS.md`
25. `.cursor/rules/external-agent-pr-loop.mdc`
26. `.cursor/skills/external-agent-pr-loop/SKILL.md`

Inspection-only except where §4 explicitly permits modification:

* `integrations/hermes/plugins/dungeonbuddy/**`
* legacy manifest/corpus retrieval services
* CLI-one-shot implementation
* PR009/Play paths
* PR011 capability/write contracts

### Authority precedence

```text
1. Current repository architecture and accepted decisions
2. Current Campaign Supergraph roadmap and tracker after this handoff is checked in
3. This checked-in handoff
4. Merged PR010A and PR010B Rung 1–3 contracts
5. Current repository implementation and owning tests
6. Reviewed Hermes upstream API as pinned by PR #352
7. Project Sources, historical handoffs, proposals, and chat summaries
```

If `main` moves beyond the recorded implementation base, another branch changes any §4 production path, or the Rung 3 result shape differs materially from this handoff, stop and report whether re-anchoring is required.

---

## §3 Observable-path inventory

| Observable path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
| --- | --- | --- | ---: | --- |
| Select **Hermes tools** in the existing Plan Agent Interaction pane and submit one factual question | Request enters transitional `run_hermes_conversation`; may use manifest lookup or CLI one-shot | Request reaches exactly one persistent-hosted Rung 3 graph-agent turn | Yes | Plan component → live API → live-query service |
| Resolve graph scope | Client supplies nested graph request; server resolves a projection envelope but old Hermes path does not use it as authoritative tool scope | Server requires the nested request, validates outer campaign identity, resolves it once, and passes `world_id`, `campaign_id`, `focus`, `admissibility`, and the **resolved `revision_id`** as the Rung 3 revision pin | Yes | `agent_world_graph_query_context` + Hermes query adapter |
| Host Rung 3 from FastAPI | Direct in-process call would expose unrelated server threads to Rung 3 global mutation | One reusable dedicated worker process owns all Rung 3 imports and turns; live-control communicates through bounded typed local IPC | Yes | Hermes graph-agent host |
| Positive single-turn answer | No real product path through Rung 3 | Non-empty Rung 3 final response is shown only when product grounding validation succeeds | Yes | Hermes query response adapter |
| Graph-anchor citations | Existing citations require repository paths | Product response emits only opaque graph-anchor citation metadata derived from real PR010A tool results | Yes | Rung 3 safe result summary + response adapter |
| Click a graph citation | UI calls path-based `/api/live/citation-source` | UI calls existing PR010A `/api/live/world-graph/retrieval/source-anchor/read` with exact anchor ID and pinned scope | Yes | API client + existing retrieval route + Plan component |
| Tool trace | Transitional trace describes manifest/CLI work | Existing trace drawer shows ordered graph tool start/completion/error states, duration, outcomes, revision, node IDs, edge IDs, anchor IDs, and diagnostic codes without prompt/source/path leakage | Yes | Response adapter + existing trace component |
| Graph returns `partial` or `truncated` with admitted anchors | Behavior is not product-grounded | Qualified answer may be shown with warnings and citations; state is visibly partial | Yes | Grounding classifier + UI |
| Graph returns `empty` or `denied`, or no admitted anchor exists | Legacy path may answer from other retrieval | Stable abstention is returned; no model prose is presented as grounded and no fallback runs | Yes | Grounding classifier |
| Graph/tool result is `unavailable` | Transitional backend may expose mixed behavior | Return explicit unavailable/error state; never call manifest, Live synthesis, or CLI fallback | Yes | Host/query adapter |
| Rung 3 returns `status="error"` | Old product path owns unrelated fallbacks | Map to typed product error; no answer, session pointer, or fallback | Yes | Query adapter + route |
| Model returns prose without any successful graph tool completion | Could appear as a normal answer | Treat as grounding-contract failure and do not expose the prose as a factual answer | Yes | Query adapter |
| Missing `world_graph_context` | Hermes can still use manifest path | Reject before host invocation with `world_graph_context_required` | Yes | Live-query route/service |
| Non-null `manifest_path` on a Hermes request | Browser always sends it | Current browser omits it; server rejects stale/malicious Hermes requests that still send it | Yes | API client + route/service validation |
| Non-null `hermes_session_id` on Rung 4 | Browser may reuse a stored session handle | Current browser omits it; server rejects it as `hermes_continuity_not_supported` | Yes | API client + route/service validation |
| Existing `agent_thread_id` | Used for local UI organization | May be echoed for UI turn ownership only; it must not become Hermes history or a Rung 3 session ID | Yes | Query adapter |
| Second Hermes question in the same visible Plan thread | UI can submit it and currently forwards a session handle | It is a new independent Rung 3 turn with no prior messages; pronoun continuity is not claimed | Yes | UI + query adapter + host |
| Page reload after a Rung 4 answer | Existing local turn record reloads | Saved answer, bounded trace, and opaque citation metadata may display; no Hermes session resumes and no old messages are sent to a new turn | Yes | Local thread serializer |
| Live backend sibling path | Existing Live behavior | Remains behaviorally unchanged; no graph-host code runs when `query_backend="live"` | Yes | `process_live_query` branch tests |
| Worker startup or pre-accept crash | No worker exists | Start or restart once before request acceptance; no user-visible fallback | Yes | Host lifecycle |
| Worker dies, hangs, or times out after accepting a turn | No defined behavior | Do not replay the turn; return typed lost/timeout error, discard the worker, and create a fresh worker only for a later request | Yes | Host lifecycle |
| App shutdown/test teardown | No graph worker exists | Stop worker and release IPC resources deterministically | Yes | FastAPI lifespan + host |

No row authorizes same-thread factual continuity, reload/session resume, or demolition.

---

## §4 Files in scope — allowlist

Every changed path must appear below. The handoff document itself is committed before dispatch and therefore belongs to the implementation base, not the implementation diff.

### Authority synchronization

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Mark Rung 3 done and publish the Rung 4–7 sequence |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Reconcile the critical path and product ladder to the same sequence |

### Backend/product runtime

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Modify | `apps/live_control_server/main.py` | Own deterministic lifecycle cleanup for the persistent Hermes worker |
| Modify | `apps/live_control_server/routes/live.py` | Validate Hermes-only request constraints and map typed query errors without changing Live behavior |
| Modify | `apps/live_control_server/services/live_agent_loop.py` | Replace only the `query_backend="hermes"` branch with the new graph-query adapter; retain legacy implementation for later deletion |
| Modify | `apps/live_control_server/services/hermes_graph_agent.py` | Extend safe completion summaries only as needed for actual snapshot and graph-anchor citation metadata; do not weaken Rung 3 policy or isolation |
| Create | `apps/live_control_server/services/hermes_graph_agent_host.py` | Persistent process-isolated local host for serialized Rung 3 turns |
| Create | `apps/live_control_server/services/hermes_graph_query.py` | Authoritative scope translation, grounding classification, response/citation/trace shaping, and typed product errors |

### Backend tests

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Modify | `tests/test_hermes_graph_agent.py` | Prove any safe-summary extension with real PR010A models and preserve every Rung 3 invariant |
| Create | `tests/test_hermes_graph_agent_host.py` | Prove process reuse, serialization, bounded IPC, crash/timeout semantics, no post-accept replay, and cleanup |
| Create | `tests/test_live_query_hermes_graph.py` | Owning route/service proof for positive answer, citations, abstention, failures, rejected legacy inputs, and unchanged Live sibling path |
| Modify | `tests/test_live_control_server.py` | Prove application lifecycle cleanup only if existing app-lifecycle coverage lives here |

### Existing Plan surface and client contract

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Modify | `apps/live-control-ui/src/api/types.ts` | Add discriminated graph-anchor citation, source-anchor-read, graph-grounding, and safe trace types while retaining legacy citation compatibility |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Omit manifest/session fields for Hermes and call the existing source-anchor read route |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` | Prevent stale Hermes session handles from surviving a Rung 4 response |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Submit a single-turn Hermes request, render graph citations, and open citations through anchor reads in the existing pane |
| Modify | `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx` | Render graph grounding and safe graph tool details in the existing trace drawer without a new panel |
| Modify | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts` | Persist only bounded graph citation/grounding metadata and no Hermes session, prompt, tool arguments, path, or source body |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | Minimal styling only for graph citation/grounding states inside the existing pane |

### Frontend tests

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx` | Prove Rung 4 responses clear rather than persist/reuse Hermes session identity |
| Create | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts` | Prove additive citation round trip and redaction/persistence rules |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | Existing-surface integration proof for request shape, answer, anchor click, trace, abstention, and error states |

### Bounded discovery exception

```text
Directory:
  apps/live-control-ui/src/planSurface/components/

Maximum additional paths:
  1

Allowed path kinds:
  One existing focused test file that already owns PlanAgentInteractionBar behavior, if PlanSurfaceShell.test.tsx is not the owning test after inspection.

Decision rule for including a path:
  The path must already test the existing Plan Agent Interaction submission/citation/trace journey and must replace—not duplicate—the proposed new coverage location.

Required report when a path is added:
  Name the path, explain why the listed test could not own the guarantee, and keep the total frontend test surface no larger than necessary.
```

Any other required path is a stop condition. Generated lockfiles, dependency files, graph Kernel files, retrieval route files, deployment files, and new UI modules are not implicitly authorized.

---

## §5 Files and capabilities explicitly out of scope

| Path, ownership layer, or capability | Why this slice must not touch or claim it |
| --- | --- |
| `integrations/hermes/plugins/dungeonbuddy/**` | Legacy plugin demolition belongs to Rung 7; this slice proves the replacement path without deleting historical code |
| Legacy manifest/corpus/lexical services | They may remain for named non-Hermes or test consumers until Rung 7; they must be unreachable from the new Hermes branch |
| CLI-one-shot implementation | No edit or deletion here; the new product path must not invoke it |
| Broad refactor or deletion inside `live_agent_loop.py` | Only the Hermes branch seam may change; cleanup is independently reviewable Rung 7 work |
| `apps/live_control_server/routes/world_graph_retrieval.py` and PR010A service/Kernel semantics | The existing opaque anchor route is sufficient; changing retrieval is a second capability |
| `src/graph_memory/retrieval/**` except model imports in tests | No new retrieval schema or semantic operation is required |
| New HTTP endpoint for Hermes turns | The mission uses existing `/api/live/query`; a second public route is unnecessary contract growth |
| Network-exposed Hermes worker service | Local persistent process isolation is sufficient for this slice; deployment/service discovery is separate infrastructure |
| Multiple Hermes worker processes or generalized job scheduling | Throughput scaling is not required to prove one safe product turn |
| Cancellation API or streaming response transport | Independently useful runtime behavior; defer unless an existing boundary makes it unavoidable, then stop |
| Conversation history, pronoun resolution, thread-bound Hermes session | Rung 5 |
| Server-side thread persistence and reload session resume | Rung 6 |
| Backend selector removal or default-backend policy change | Rung 7 after dogfood acceptance |
| Deletion of Live synthesis path | Rung 7; Live backend remains a separate explicitly selected sibling during this rung |
| New citation pane, new trace panel, or surface redesign | Existing Plan pane, source reader area, and trace drawer must be extended in place |
| Persisted raw tool outputs, source excerpts, prompts, model messages, or arbitrary paths | Violates the active Hermes inspectability boundary |
| Graph writes, prep drafts, preview/confirm, or operator tools | PR011 |
| Play surface integration | PR009 parallel lane |
| Full multi-source ingestion expansion | Parallel graph-coverage work, not an agent runtime fallback |

Nearby work is not authorization.

---

## §6 Implementation contract and conditional matrices

### Core product contract

```text
Input:
  Existing POST /api/live/query request with:
    query_backend = "hermes"
    non-empty text
    outer campaign_id and session matching the loaded live packet
    agent_thread_id allowed only as UI identity
    trace_requested optional
    world_graph_context required and validated through the existing PR008B model
    manifest_path must be null/absent
    hermes_session_id must be null/absent

Authoritative scope:
  Resolve world_graph_context through resolve_agent_world_graph_query_context.
  Use only the resolved envelope for:
    world_id
    campaign_id
    focus
    admissibility
    revision_pin = resolved revision_id
  Do not use client-supplied envelope detail or graph query results as prompt facts.
  Do not expose an HTTP capability_policy field.
  Product dispatch uses the default graph-only Rung 3 capability policy.

Host call:
  Submit one bounded serializable turn request to the persistent isolated worker.
  conversation_history = None
  session_id = a fresh per-turn execution ID, not agent_thread_id and not a durable session pointer
  root = server-owned repository root, never an HTTP field

Output:
  Existing dmb_live_query_response_v1 envelope with:
    mode = "hermes_graph_single_turn"
    answer = grounded model response or stable product abstention
    status = "ok", "partial", or "error"
    context_packet = null
    mutations = []
    hermes_session = null
    agent_thread_id = caller UI thread identity
    turn_id = fresh product turn ID
    world_graph_context = resolved envelope
    graph_grounding = dmb_hermes_graph_grounding_v1
    citations = discriminated legacy-path or world-graph-anchor citation list
    agent_trace = safe graph trace

Invariant:
  Same as §1.

Failure behavior:
  invalid Hermes request → typed 422; worker not invoked
  graph preflight unavailable → typed 503; worker not invoked
  worker unavailable before acceptance → one restart attempt, then typed 503
  worker lost after acceptance → typed 502/503; no replay
  worker timeout after acceptance → typed 504; no replay; worker replaced for later requests
  Rung 3 status=error → typed product error; no fallback
  no successful graph completion → grounding-contract error; model prose discarded
  graph evidence insufficient → stable 200 partial abstention; no fallback

Replay / idempotency:
  same HTTP payload submitted twice → two independent turns; no implicit deduplication
  changed input → new independent turn
  retry after a pre-accept host startup failure → allowed once inside host
  retry after worker acceptance/provider invocation → prohibited automatically
  duplicate IPC request ID → reject within the active worker lifecycle

Trust boundary:
  Verifies:
    outer campaign/session match
    required graph context
    authoritative resolved revision and scope
    Rung 3 status and safe tool events
    model actually used permitted graph tools
    citations came from real tool result anchors
    no unsupported manifest/session input
  Records or trusts without proving:
    model prose quality after grounding eligibility is established
    user-selected visible Agent Interaction thread label
  Rejects:
    arbitrary paths
    manifest selectors
    caller capability policy
    caller root
    caller Hermes session identity
    model prose without graph execution
    fabricated citation IDs parsed from model text
```

### Persistent process-isolated host contract

The host is part of the product safety boundary, not a developer smoke harness.

```text
Topology:
  live-control FastAPI process
    → one local typed IPC client
      → one long-lived dedicated Python worker process
        → run_hermes_graph_agent_turn

Required properties:
  - Use the multiprocessing "spawn" context or an equivalently clean Python process boundary, not fork-from-request, hermes --oneshot, or a shell command.
  - The worker process alone imports and executes the process-exclusive Rung 3 runtime.
  - Reuse the worker across requests.
  - Serialize requests in the worker; one active turn at a time is acceptable.
  - Bound request and response payload size.
  - Carry an opaque request ID and explicit accepted/result/error messages.
  - Never send capability policy, arbitrary filesystem paths, prompts beyond the user question, or source bodies through IPC except what the Rung 3 result contract already requires internally.
  - Return a JSON-safe or explicitly serialized typed result; do not pickle arbitrary caller objects across the trust boundary.
  - Shut down deterministically from FastAPI lifespan and test teardown.
```

A worker crash may be retried only before the request has been acknowledged as accepted. Once accepted, the parent cannot prove whether provider/tool execution occurred; automatic replay would risk duplicate cost and inconsistent side effects. Return an error instead.

### Product grounding classification

The product adapter must not equate `Rung 3 status="ok"` with a grounded answer.

Build grounding state from typed/safe tool completion records, never from model prose.

```text
GROUNDING ELIGIBLE:
  - Rung 3 status is ok;
  - final_response is non-empty;
  - at least one permitted graph tool has a completion record;
  - no runtime contract failure occurred;
  - at least one graph-admitted source anchor was returned by a real PR010A result;
  - the response citations are derived from those recorded anchors.

GROUNDED:
  eligible and evidence/retrieval outcomes support an answer.

PARTIAL_GROUNDED:
  eligible, but at least one relevant result is partial or truncated;
  show the answer with warnings and citations.

ABSTAINED:
  result is empty, denied, unavailable, has no admitted source anchor,
  or otherwise lacks enough admissible evidence.
  Discard unsupported model prose and return the stable product abstention.

CONTRACT_ERROR:
  status ok but no successful permitted graph completion, malformed safe result,
  citation not attributable to a tool result, or final_response missing.
  Return typed error and do not show model prose.
```

Stable abstention text:

```text
DungeonBuddy’s World Graph does not currently contain enough admitted evidence to answer this confidently.
```

The response may append concise machine-derived diagnostic context, but it must not answer from another source.

### Safe Rung 3 result extension

If the current Rung 3 event/result contract does not expose enough data to build product citations and actual revision trace, extend it additively with bounded typed summaries derived from the real PR010A result models.

Permitted safe metadata:

```text
snapshot:
  worldId
  campaignId
  revisionId
  headRevisionId
  isHead
  focus
  admissibility

source anchor summary:
  anchorId
  revisionId
  evidenceRefId
  sourceArtifactId
  sourceDomain
  sessionId
  locatorKind
  displayLabel
  readable
  optional lineStart / lineEnd / truncated / contentSha256 from a source-anchor read
```

Prohibited in safe events, product trace, response citations, and persisted turns:

```text
source content or source body
arbitrary or resolved filesystem path
raw query text
raw tool arguments
raw prompt/system prompt
provider secret or headers
stack trace
full Hermes messages/tool payloads
```

Tests must construct and serialize real `WorldGraphRetrievalResult`, `WorldGraphSourceAnchor`, `WorldGraphSourceAnchorReadResult`, and `WorldGraphRetrievalErrorResponse` objects. Hand-written approximations are not acceptable proof.

### Graph citation contract

Make `LiveQueryCitation` an additive discriminated union.

Legacy citations remain readable:

```text
kind absent or "legacy_path"
existing evidence_id/path/line/source_role/authority fields
```

New graph citations:

```text
kind = "world_graph_anchor"
anchor_id
revision_id
world_id
campaign_id
focus
admissibility
source_domain
source_artifact_id
evidence_ref_id
locator_kind
display_label
readable
optional line_start / line_end / truncated / content_sha256
```

Rules:

* A graph citation is created only from a recorded PR010A source anchor returned during the turn.
* Do not parse anchors from the model answer.
* Deduplicate by exact `anchor_id`; merge only metadata from the same exact anchor.
* Display label is presentation only and never resolves identity.
* Clicking a graph citation calls the existing source-anchor read route with the citation's exact scope and revision.
* Saved citation clicks remain pinned to the original revision. They must not silently rebind to current head.
* A failed or unreadable anchor returns the existing PR010A error/outcome visibly; it never falls back to a path reader.

### Safe trace contract

Reuse the existing trace drawer. Do not add a second panel.

The graph trace must include, in safe bounded form:

* fresh product turn/execution ID;
* runtime `hermes_graph_agent_host`;
* backend `hermes`;
* mode `graph_only_single_turn`;
* process-isolation indicator;
* authoritative world/campaign/focus/admissibility/revision;
* ordered tool name and state;
* duration where available;
* retrieval schema and outcome;
* matched node IDs;
* relationship `edgeId` values;
* source-anchor IDs;
* diagnostic codes;
* final grounding state and whether the product abstained.

It must set `prompt_preview` absent/null and must not manufacture token usage when Hermes does not return it.

---

### §6A State and fallback matrix

| Observable path | Loading or initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity or contract failure | Stale or superseded | Retry or replay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Plan Hermes request | Existing asking state; no alternate backend | One hosted Rung 3 turn → grounded response | Stable abstention; no alternate retrieval | Visible error/unavailable state | Fail closed; discard unsupported prose | Turn remains pinned to resolved revision | New user submission only after accepted turn |
| Graph-context preflight | Existing graph-context loading state blocks/defers submit | Resolve exact revision and scope | `status=empty` may still dispatch search against that revision | `status=unavailable` → 503; no provider call | Existing fatal projection error response; no provider call | Explicit caller revision resolves or errors | Safe to retry because worker not invoked |
| Persistent worker startup | Start lazily or by app lifecycle | Worker ready and reused | N/A | One pre-accept restart, then 503 | Protocol/version mismatch fails closed | Worker binary is current process code only | One restart before acceptance |
| Active worker turn | Show asking state | Typed result returned | Grounding classifier abstains | Host/provider/tool unavailable maps to error | Malformed/mismatched result fails closed | Rung 3 uses pinned revision | Never auto-replay after accepted acknowledgment |
| Source-anchor click | Existing source loading state | Exact opaque anchor read at citation revision | Existing empty/unreadable outcome shown | Existing unavailable error shown | Existing integrity error shown | Never read current head as substitute | User may explicitly retry same pinned anchor |
| Legacy `query_backend="live"` sibling | Existing behavior | Existing Live result | Existing Live behavior | Existing Live behavior | Existing Live behavior | Existing Live behavior | Existing Live behavior |
| Hermes request carrying manifest/session | N/A | N/A | N/A | N/A | 422 reject before host; no compatibility fallback | N/A | Caller must resend corrected request |

No fallback source is permitted for the Hermes path.

---

### §6B Identity matrix

| Situation | Required matching rule | Ambiguity behavior | Fallback permitted? | Persistence consequence |
| --- | --- | --- | --- | --- |
| Agent Interaction thread | Exact caller `agent_thread_id`; UI organization only | Missing ID may receive existing generated UI ID behavior | No factual fallback | Existing local thread may persist; never becomes Hermes session identity |
| Product turn | Fresh exact `turn_id` per request | Collision must regenerate/fail, never overwrite | No | Persisted as existing turn identity |
| Hermes execution | Fresh exact worker/Rung 3 execution ID per turn | Never infer from thread or prior response | No | Trace-only; `hermes_session` remains null and is not persisted |
| World/campaign | Exact values from resolved graph envelope; outer campaign must match | Mismatch rejects request | No | Persist exact bounded scope summary only |
| Graph revision | Exact resolved `revision_id` becomes Rung 3 pin | Missing/unavailable revision rejects before turn | No latest-head fallback after resolution | Citation and grounding metadata retain exact revision |
| Graph node/relationship | Exact durable `nodeId` / `edgeId` from tool result | Labels/aliases are display only in product mapping | No | Bounded IDs may persist in safe trace/grounding summary |
| Source anchor | Exact opaque `anchorId` | Duplicate exact IDs deduplicate; differing IDs never merge by label | No path or label fallback | Persist opaque ID plus bounded metadata, not source body |
| Display label | Presentation only | Duplicate labels are allowed | No | May persist as non-authoritative display text |
| Rename | Durable IDs remain stable; product does not remap | No label-based rebinding | No | Existing saved citation remains ID/revision-bound |
| Deletion/retraction | Exact pinned revision governs old citation | Current-head absence does not rebind | No | Saved historical citation may become unavailable under policy but remains unchanged |
| Rebinding | Prohibited in this slice | Fail unresolved | No | No stored reference changes identity automatically |

---

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate or replay behavior | Compatibility or migration | Rollback or reversion |
| --- | --- | --- | --- | --- | --- |
| Save Plan turn | Existing local Agent Interaction thread record | Answer, status, bounded trace, graph grounding summary, and citation metadata load without raw source/tool/prompt data | Re-saving same thread replaces current thread record under existing behavior | Additive citation union; legacy citations without `kind` remain legacy path citations | Revert code leaves old records readable; unknown additive fields are ignored |
| Save graph citation | `kind="world_graph_anchor"` plus exact anchor/scope/revision metadata | Exact anchor identity and revision survive reload | Exact duplicate anchors deduplicate within one response | No migration of legacy path citations; no conversion between variants | Remove new turn/citation through existing thread deletion/clear behavior |
| Save trace | Existing safe trace representation, extended only with explicitly bounded graph fields | No prompt preview, raw summaries, paths, source body, or messages survive | Existing turn replacement behavior | Old traces remain readable with optional fields absent | Existing clear/delete behavior |
| Hermes session | No durable representation in Rung 4 | `hermes_session` is null after response and reload | No replay/resume | Existing stale session handles must be cleared on a successful Rung 4 response and not sent | Rung 5/6 will introduce an explicit contract later |
| Worker request | In-memory IPC request ID only | No restart persistence | Duplicate active ID rejected; accepted request never auto-replayed | No cross-version replay | Worker restart discards in-flight state |
| Source content | Not persisted by this capability | N/A | N/A | Existing legacy content behavior is not extended to graph citations | N/A |
| Page reload | Existing local thread only | Previously saved answer/citation summary displays | Reload does not rerun provider or graph tools | No Hermes session resume | User may start a new independent turn |

This slice does not introduce server-side conversation storage or a durable worker queue.

---

### §6D Predecessor-to-consumer mapping

**Grounding sources**

```text
Canonical Rung 3 types:
  apps/live_control_server/services/hermes_graph_agent.py

Canonical PR010A types:
  src/graph_memory/retrieval/models.py

Canonical graph-context request/response:
  apps/live_control_server/services/agent_world_graph_query_context.py

Canonical product request/response and UI types:
  apps/live_control_server/routes/live.py
  apps/live-control-ui/src/api/types.ts
```

| Predecessor field or outcome | Real shape and optionality | Consumer field or behavior | Transformation | Proof fixture or test |
| --- | --- | --- | --- | --- |
| `HermesGraphAgentTurnResult.status` | `"ok" | "error"` | Product success/error eligibility | `error` always maps to typed product error; `ok` still requires grounding validation | Real/fake Rung 3 typed result in `tests/test_live_query_hermes_graph.py` |
| `final_response` | `str | None` | `LiveQueryResponse.answer` | Use only for grounded/partial-grounded; discard for abstained/contract-error | Positive, empty, no-tool, and provider-error tests |
| `messages` | List of Hermes message dicts | Not exposed or persisted in Rung 4 | Ignore for product continuity; do not derive citations from it | Response redaction test |
| `hermes_session_id` | Non-empty per Rung 3 turn | Trace execution ID only | Never map to `hermes_session` | Session-clearing tests |
| `process_isolation` | `"process_exclusive"` | Trace/runtime diagnostics | Preserve as bounded metadata; host supplies actual process boundary | Host + trace tests |
| Tool event `tool_name/state/duration_ms` | Ordered safe fields; duration optional | `agent_trace.steps` / graph trace details | Preserve order; no free-form tool payload | Rung 3 real model + route mapping test |
| Tool event `outcome` | PR010A outcome or null | Grounding classifier and warnings | Apply exact enum semantics | Parametrized route tests |
| Tool event `matched_node_ids` | Bounded list | Graph grounding/trace | Preserve exact IDs, bounded | Route mapping test |
| Tool event `relationship_ids` | Real `edgeId` values | Graph grounding/trace | Preserve exact IDs; never use synthetic `id` fixture as primary | `tests/test_hermes_graph_agent.py` real relationship model |
| Tool event/source summary `source_anchor_ids` | Opaque IDs | Graph citations | Deduplicate exact IDs; enrich only from same real result | Real source-anchor models |
| `WorldGraphRetrievalResult.snapshot` | Optional snapshot with revision/head/scope | Product graph grounding | Preserve actual values; compare to authoritative dispatch scope | Snapshot mismatch fail-closed test |
| `WorldGraphRetrievalResult.sourceAnchors[]` | Real camelCase anchor fields | `world_graph_anchor` citation | Field-level mapping defined above | Real model serialization test |
| `WorldGraphSourceAnchorReadResult` | Outcome, anchor metadata, optional content, hash, lines, truncation | Existing source reader display | Client receives content only from explicit click response; turn persistence keeps metadata only | Existing route test + Plan click integration |
| `WorldGraphRetrievalErrorResponse` | Schema, code, message, statusCode, diagnostics | Tool error / product error or abstention | Preserve code/diagnostics; never label as successful completion | Rung 3 error-event + route tests |
| Resolved graph envelope `revision_id` | Actual revision or null | Rung 3 `revision_pin` | Required non-null for dispatch; use resolved value, not raw request pin | Scope-spoof test |
| Resolved graph envelope `focus` | snake_case response dict | Rung 3 focus mapping | Convert to Rung 3 expected mapping without changing meaning | Exact mapping test |
| Live request `manifest_path` | Optional string | Hermes validation | Non-null with Hermes is invalid; Live behavior unchanged | Sibling-path route tests |
| Live request `hermes_session_id` | Optional string | Hermes validation | Non-null with Rung 4 is invalid | Route + UI request-shape tests |
| Existing path citation | Required path/evidence fields | Legacy citation union branch | Preserve unchanged; absent `kind` means legacy | Storage/component regression tests |
| New graph citation | Additive discriminated variant | Plan evidence card/source read | Never fabricate path fields | Type/storage/component tests |

Invented near-match fixtures are prohibited. Tests that exercise mapping must serialize the canonical Pydantic models or consume the canonical TypeScript contract.

---

## §7 Verification ownership map and commands

### Verification ownership map

| Guarantee | Owning boundary | Command or manual scenario | Expected evidence |
| --- | --- | --- | --- |
| Rung 3 safety contract remains intact | Rung 3 runtime/tests | Focused Rung 3 suite | Exact tool surface, scope enforcement, safe summaries, process-exclusive behavior still pass |
| Worker isolates global Hermes mutations from FastAPI process | Host process integration | Host tests inspect parent env/modules during worker turn | Parent `HERMES_HOME`, `sys.path`, and `agent.*` state unchanged |
| Worker is reused and serialized | Host | Two sequential and concurrent client requests | Same worker PID reused; max active Rung 3 turns is one |
| Pre-accept crash may restart once | Host | Inject startup/death before accepted acknowledgment | One restart and truthful result/error |
| Post-accept loss is never replayed | Host | Inject death after accepted acknowledgment | No second execution; typed lost error |
| Timeout is bounded and worker is replaced only for later requests | Host | Inject hanging turn | Typed timeout; no replay; later request uses fresh worker |
| Shutdown cleans worker/IPC | FastAPI lifespan + host | App/test client lifecycle | Worker no longer alive; resources closed |
| Hermes request uses resolved authoritative scope | Query service/route | Spoof nested/raw values and inspect hosted request | Worker receives resolved world/campaign/focus/admissibility/revision only |
| Hermes rejects manifest and session compatibility inputs | Route/service | Submit stale request fields | 422; host spy not called |
| Positive Plan Hermes request reaches hosted Rung 3 | Route/service | Mock only host/provider boundary as appropriate | One hosted call and graph-grounded response |
| Product discards no-tool model prose | Query adapter | Rung 3 `ok` result with final prose and zero completions | Typed grounding error; prose absent |
| Empty/denied/no-anchor result abstains | Query adapter | Parametrized canonical results | Stable abstention; no fallback spies called |
| Partial/truncated with anchor is qualified | Query adapter | Canonical result models | Partial status, warnings, answer, citation |
| Graph citations use exact PR010A anchor shape | Rung 3 summary + query adapter | Real model serialization | Correct anchor/revision/source metadata; no path/content |
| Source click uses opaque anchor route | API client + Plan component + existing route | Component integration | Request body contains exact scope/anchor; no path reader call |
| Trace is useful and safe | Query adapter + trace component + storage | Backend mapping and UI tests | Tool names/outcomes/IDs visible; prompt/path/content absent before and after persistence |
| Hermes session is not persisted or reused | UI provider/history/request builder | UI tests and storage round trip | `hermesSession` null; next request omits ID |
| Live backend is unchanged | `process_live_query` route/service | Existing Live tests plus sibling spy | No graph host call for Live requests |
| Existing legacy citations remain readable | Type/storage/component | Frontend regression | Old path citation renders and opens as before |
| Single-turn product journey works | Existing Plan surface | Manual live proof | Real provider calls graph tools, answer/citations/trace visible |
| Coverage gap is honest | Existing Plan surface | Manual negative proof | Stable abstention and diagnostics; no hidden source answer |

### Required backend commands

Run from repository root and record exact results:

```bash
uv sync --frozen

uv run pytest -q \
  tests/test_hermes_graph_agent.py \
  tests/test_hermes_graph_agent_host.py \
  tests/test_live_query_hermes_graph.py \
  tests/test_hermes_graph_read_tools.py \
  tests/test_hermes_graph_read_tool_adapter.py \
  tests/test_agent_world_graph_query_context.py \
  tests/test_world_graph_retrieval_routes.py \
  tests/test_live_query_manifest_context.py \
  tests/test_live_control_server.py

uv run ruff check \
  apps/live_control_server/main.py \
  apps/live_control_server/routes/live.py \
  apps/live_control_server/services/live_agent_loop.py \
  apps/live_control_server/services/hermes_graph_agent.py \
  apps/live_control_server/services/hermes_graph_agent_host.py \
  apps/live_control_server/services/hermes_graph_query.py \
  tests/test_hermes_graph_agent.py \
  tests/test_hermes_graph_agent_host.py \
  tests/test_live_query_hermes_graph.py \
  tests/test_live_control_server.py
```

Run the complete suite on both predecessor and head under the same resolved environment:

```bash
uv run pytest -q
```

Do not inherit or quote PR #352's author-local full-suite counts as the current result. Record a fresh base/head comparison.

### Required frontend commands

Run from `apps/live-control-ui` and record exact results:

```bash
npm test -- --run \
  src/agentInteraction/AgentInteractionProvider.test.tsx \
  src/planSurface/components/agentInteractionHistory.test.ts \
  src/planSurface/PlanSurfaceShell.test.tsx

npm run build
```

If the bounded-discovery test path replaces one listed test, report the exact final command.

### Repository diff checks

```bash
git diff --check
git diff --stat <implementation-base>...HEAD -- <all §4 paths>
git diff --name-only <implementation-base>...HEAD
```

### Static no-fallback proof

Add a focused automated proof that the new host/query modules and the new Hermes branch do not import or invoke:

```text
integrations.hermes.plugins.dungeonbuddy
handle_dungeon_context_lookup
manifest_context_query
live_query_context
subprocess-based Hermes CLI
hermes --oneshot
OpenAI client directly
Live synthesis fallback
```

The process host may use Python process primitives. It must not execute a Hermes CLI command or a shell command.

### Minimal live proof

```text
Existing surface used:
  Plan Agent Interaction pane at /plan with the existing backend selector and trace drawer.

Initial state:
  Published Eldyrwild/Campaign 2 World Graph available.
  Real provider credentials configured for the pinned Hermes runtime.
  Existing Plan graph context resolves to a concrete revision.
  No legacy manifest or CLI mode is enabled for the Hermes request.

Positive action:
  Select Hermes tools.
  Ask: “What do we know about Tripod Null-Calf at the North Gate?”

Expected positive observation:
  - Existing /api/live/query is the browser request.
  - One persistent worker-hosted Rung 3 turn runs.
  - Hermes calls only the five graph tools.
  - The answer uses useful game language.
  - At least one graph-anchor citation is visible.
  - Clicking it opens a bounded source excerpt through source-anchor/read.
  - Trace shows actual revision, graph tools, outcomes, node/edge/anchor IDs, and durations.
  - No manifest path, CLI one-shot, Live synthesis, or durable Hermes session is present.

Negative action:
  Ask a question whose answer is known to exist in Markdown but is absent from the World Graph.

Expected negative observation:
  - Product returns the stable graph-coverage abstention.
  - Diagnostic/trace shows empty, denied, unavailable, or missing-evidence state as applicable.
  - No legacy answer appears.
  - Browser/network/server evidence shows no manifest, arbitrary-path, corpus, lexical, CLI, or Live fallback call.

Evidence captured:
  - exact request/response bodies with secrets and question text redacted as appropriate;
  - screenshot or recording of answer, citation click, and trace;
  - worker/server log showing request ID, worker PID, accepted/result state, and no fallback invocation;
  - provider provenance identified as author-local manual evidence, not CI.
```

The live proof must use the existing surface. Do not build a diagnostic page, worker console, or dogfood report UI.

### Baseline failure protocol

PR #352 reported author-local full-suite failures on its then-current environment. Those counts are historical evidence only.

For every required command failing on the predecessor:

* run the same command on `e6a95e267f743d78239500209dd7333a6f65cf67` and head;
* use the same lock/environment and command shape;
* report exact node IDs or grouped failure classes;
* state whether head introduces any additional failure;
* do not call the complete gate green;
* request an explicit operator waiver if a required failing gate remains.

Required evidence shape:

| Command | Base result | Head result | New failure introduced? | Acceptance effect | Waiver |
| --- | --- | --- | ---: | --- | --- |
| `<command>` | `<exact result>` | `<exact result>` | Yes / No | Blocked / acceptable with explicit waiver | None or named waiver |

Focused owning-boundary tests, frontend tests, build, lint, and diff checks must be green. A pre-existing full-suite failure cannot waive a new failure in an owning test.

---

## §8 Required implementation handback

The PR body or implementation handback must include:

1. Predecessor SHA `e6a95e267f743d78239500209dd7333a6f65cf67`.
2. Docs-only implementation-base SHA.
3. Head SHA.
4. Actual changed paths.
5. Focused diff stat limited to §4 paths.
6. Every §7 command and exact result.
7. Provenance for each result: author-local, independently rerun local, CI, or manual observation.
8. Worker topology and process-lifecycle summary.
9. Exact host retry/timeout outcomes proven.
10. Positive and negative live-proof evidence.
11. Exact product request/response examples with sensitive text removed.
12. Proof that Hermes requests omit/reject `manifest_path` and `hermes_session_id`.
13. Proof that `query_backend="live"` remains unchanged.
14. Proof that graph citations use opaque anchor IDs and the existing anchor-read route.
15. Proof that raw prompts, source bodies, paths, tool arguments, messages, and secrets are absent from response and persisted turns.
16. Base/head complete-suite comparison.
17. Explicit operator waivers; write `none` when none exist.
18. Paths outside §4; write `none` or include a stop report.
19. Stop conditions encountered and resolution; write `none` when none exist.
20. Deviations from §6 matrices; write `none` when none exist.
21. Confirmation that same-thread continuity remains false.
22. Confirmation that reload/session resume remains false.
23. Confirmation that legacy code and backend selector remain for Rung 7.
24. Confirmation that no write tool or PR011 capability was added.
25. Confirmation that the authoritative handoff was implemented without compression or omitted constraints.

Opening the pull request must be the final repository action on the implementation branch.

---

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true.

* [ ] Exactly one capability from §1 is delivered: one Plan Hermes request reaches one safely hosted Rung 3 turn and returns a usable graph-grounded result — proved by route/service integration and live proof.
* [ ] The Rung 3 runtime is not invoked directly in the FastAPI process — proved by host integration and parent-process isolation tests.
* [ ] The worker is persistent, reused, serialized, bounded, and deterministically cleaned up — proved by host tests.
* [ ] A request is automatically retried only before worker acceptance; accepted turns are never replayed automatically — proved by crash-injection tests.
* [ ] Authoritative scope comes from the resolved graph envelope and the Rung 3 turn is pinned to its actual revision — proved by spoof/mapping tests.
* [ ] Hermes requests require graph context and reject manifest/session compatibility inputs before host invocation — proved by route tests.
* [ ] The positive response is shown only after product grounding validation, not merely Rung 3 `status="ok"` — proved by no-tool and malformed-result tests.
* [ ] Empty, denied, unavailable, and no-anchor cases abstain or fail closed without fallback — proved by parametrized route tests and negative live proof.
* [ ] Partial/truncated results with admitted anchors are qualified and visibly partial — proved by route/component tests.
* [ ] Citations are derived only from real PR010A source anchors and never from model prose — proved by canonical-model mapping tests.
* [ ] Clicking a graph citation uses the existing opaque source-anchor route and never the path reader — proved by component integration and existing route proof.
* [ ] Trace exposes useful graph operations and IDs while excluding prompts, source bodies, paths, raw arguments, messages, and secrets — proved before and after persistence.
* [ ] `hermes_session` remains null, stale handles are cleared, and subsequent visible-thread turns remain independent — proved by UI/storage/request tests.
* [ ] Existing local turn persistence round-trips additive graph citation metadata without creating session continuity — proved by storage tests.
* [ ] Legacy path citations and the explicitly selected Live backend continue to work — proved by sibling-path regressions.
* [ ] No new Hermes HTTP route, citation panel, graph retrieval operation, or server-side thread store is introduced — proved by diff review.
* [ ] No legacy code is silently deleted or adapted into the graph runtime — proved by diff review and §5 audit.
* [ ] Tracker and roadmap reflect Rung 3 done, Rung 4 active, and Rung 5–7 separate — proved by documentation inspection.
* [ ] No unexpected path changed — proved by `git diff --name-only <implementation-base>...HEAD`.
* [ ] Baseline failures are reported truthfully and any waiver is explicit.
* [ ] Local, CI, and manual evidence provenance is distinguished.
* [ ] Rung 5, Rung 6, Rung 7, PR009, and PR011 remain unimplemented and unclaimed.
* [ ] The complete authoritative handoff survived dispatch without omitted constraints.

---

## §10 Reviewer protocol

Review the product invariant before reviewing individual files.

1. Restate §1 mission and invariant.
2. Confirm the implementation base is the docs-only handoff commit and predecessor remains PR #352's merge.
3. Compare the actual diff with §0, §3, §4, and §5.
4. Inspect whether the worker is a persistent process boundary rather than direct FastAPI invocation or per-turn CLI subprocess.
5. Verify the parent process does not import/execute the process-exclusive Rung 3 turn during a request.
6. Audit worker acknowledgment, timeout, crash, restart, shutdown, and replay semantics.
7. Trace one positive request from Plan submit through `/api/live/query`, graph-context resolution, host IPC, Rung 3, response shaping, citation display, and anchor click.
8. Trace one graph miss and every runtime failure sibling path; look explicitly for fallback calls.
9. Verify scope is overwritten from the resolved envelope and the actual resolved revision is pinned.
10. Verify no caller can supply capability policy, root, arbitrary path, manifest, or Hermes session identity.
11. Verify grounding eligibility is machine-derived from typed tool results, not model prose.
12. Inspect canonical PR010A model serialization in tests; reject hand-written near-match fixtures.
13. Verify relationship IDs use `edgeId` and source citations use exact `anchorId`.
14. Audit response, trace, logs, IPC, and local storage for raw prompt/source/path/tool/message leakage.
15. Verify graph-anchor click uses the existing source-anchor route with exact revision-bound scope.
16. Confirm legacy path citation and Live backend sibling behavior remain intact.
17. Confirm multiple visible turns do not imply or implement conversational continuity.
18. Confirm reload displays prior turn data only and does not resume Hermes.
19. Check tracker/roadmap sequence and ensure Rung 5–7 remain separate.
20. Compare base/head complete-suite failures and review any waiver.
21. Confirm the pull request was opened only after final implementation/verification state.

File count and line count do not determine coherence. The cross-layer diff is acceptable only because every layer establishes or proves the single graph-only product-turn invariant.

---

## §11 Re-review protocol

Begin every re-review from the prior finding ledger.

| Prior finding | Claimed fix | Owning files or tests | Verified? | New consequence? |
| --- | --- | --- | ---: | --- |
| `<finding>` | `<claimed resolution>` | `<paths/tests>` | Yes / No | `<none or consequence>` |

For each finding:

1. Verify the claimed fix at its owning boundary.
2. Re-run the whole single-turn invariant, not only the modified line.
3. Re-audit all sibling paths: positive, partial, empty, denied, unavailable, no-tool, host startup, post-accept crash, timeout, source click, persistence, Live backend.
4. Inspect whether the fix introduced direct in-process execution, hidden replay, a fallback, session persistence, path-based citation, or a second public route.
5. Re-run redaction checks across response, trace, IPC, logs, and local storage.
6. Re-check same-thread and reload behavior remain explicitly unsupported.
7. Add new findings to the ledger.

Do not treat a passing mocked UI response as proof that the real hosted Rung 3 boundary is exercised.

---

## Stop conditions

Stop and report rather than expanding scope when implementation discovers:

* the Rung 3 runtime cannot be hosted safely without changing its fundamental capability-policy or graph-tool contract;
* a network service, deployment unit, container, or process supervisor is required for the worker to be useful;
* the existing `/api/live/query` envelope cannot represent the result without a second independently useful API;
* citations cannot be made usable without changing PR010A source-anchor semantics or adding arbitrary-path access;
* useful answer grounding requires persisted raw tool results, source bodies, or Hermes messages;
* same-thread history is required for the first-turn question to work;
* reload/session resume is required for this product slice to be useful;
* accepted-turn retry semantics cannot be determined safely;
* worker lifecycle requires a path outside §4 or the bounded exception;
* the predecessor Rung 3 result differs materially from the canonical types mapped in §6D;
* current repository rules prohibit the selected process boundary;
* a required owning suite has a new head-only failure;
* a baseline failure requires operator waiver before acceptance;
* legacy demolition is necessary to prevent the new Hermes branch from reaching fallback code rather than making it unreachable by construction;
* a new product/operator surface is proposed as verification;
* any write-capable tool or PR011 contract becomes necessary;
* any handoff constraint cannot be implemented without reinterpretation.

Use this report:

```text
Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor slice:
Tracker or authority update needed:
Operator decision required:
```

The worker must not resolve a stop condition by silently broadening the mission.

---

## Final dispatch check

Before sending this handoff to an implementation agent, confirm:

* [ ] §0 records the seven-rung decomposition and selects only Rung 4.
* [ ] §1 describes one independently useful product capability.
* [ ] The graph-only single-turn invariant is reused consistently.
* [ ] §2 names PR #352's merge as predecessor and the docs-only handoff commit as implementation base.
* [ ] §2 records why direct FastAPI invocation of Rung 3 is prohibited.
* [ ] §3 inventories positive, miss, failure, host, citation, persistence, and sibling Live paths.
* [ ] §4 expresses the expected cross-layer diff exactly or through the one bounded test exception.
* [ ] §5 names Rung 5, Rung 6, Rung 7, PR009, and PR011 boundaries.
* [ ] §6 specifies authoritative scope, host acknowledgment/replay, grounding, citation, trace, and persistence behavior.
* [ ] Every §6 matrix is complete.
* [ ] §6D maps real Rung 3 and PR010A vocabulary field by field.
* [ ] Every §9 behavioral claim maps to an owning §7 proof.
* [ ] Live proof uses only the existing Plan pane and trace/source-reader affordances.
* [ ] Full-suite baseline handling requires a fresh base/head comparison.
* [ ] Stop conditions are concrete.
* [ ] The checked-in handoff contains the full authority.
* [ ] No essential constraint exists only in chat.
