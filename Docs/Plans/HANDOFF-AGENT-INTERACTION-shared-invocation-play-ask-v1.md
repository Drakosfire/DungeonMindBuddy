---
document_id: dmb-handoff-agent-interaction-shared-invocation-play-ask-v1
title: Shared Agent Invocation / Play Ask v1 (A8)
document_class: implementation_handoff
status: design_complete_dispatch_blocked
version: 1.0
created_at: "2026-08-31"
updated_at: "2026-08-31"
workstream: AGENT-INTERACTION
predecessor:
  capability: A7 Play Durable Current-Moment SurfaceContext v1
  pr: 671
  accepted_review_head: 7f015f3e6ab7a39605565849803e25088a510d4c
  final_review: 5070720084
  merge_required_before_dispatch: true
design_branch: agent/shared-agent-invocation-play-ask-v1-design
design_parent: 7f015f3e6ab7a39605565849803e25088a510d4c
architecture_authorities:
  - ../Design/ARCHITECTURE-surface-interaction-layer.md
  - ../Design/DECISION-agent-context-compilation.md
  - ../Design/ARCHITECTURE-application-state-layer.md
  - ../Design/ARCHITECTURE-playable-material-and-runtime.md
companion_target:
  - ../Design/DESIGN-magic-moment-contextual-source-to-world-graph.md
---

# HANDOFF — Shared Agent Invocation / Play Ask v1 (A8)

**Created:** 2026-08-31  
**Status:** **DESIGN COMPLETE — NOT DISPATCHABLE UNTIL PR #671 MERGES AND THIS HANDOFF IS RE-ANCHORED ON EXACT POST-A7 `main`**  
**Design branch:** `agent/shared-agent-invocation-play-ask-v1-design`  
**Design parent:** `7f015f3e6ab7a39605565849803e25088a510d4c` — A7 PASS-equivalent head  
**Predecessor:** A7 / PR #671 / formal Cycle 4 review `5070720084` PASS-equivalent  
**Workstream / flow:** `AGENT-INTERACTION / A8`  
**Intended implementation branch after release:** `agent/shared-agent-invocation-play-ask-v1`  
**Intended PR title:** `AGENT-INTERACTION: enable truthful Play Ask`

> Release gate: do **not** implement from this branch while #671 is open. After #671 merges, re-read exact `main`, open PRs, and the merged A7 handoff. Rebase/recreate this one-file design commit on that exact authority, fill the A7 merge facts in §22, change status to `READY FOR DISPATCH`, and only then allocate the implementation lease.

---

## 1. Mission

Make the **existing app-scoped Agent chrome** genuinely usable from one READY Play Run.

A8 proves this user story:

> **As the GM running a durable Play Run, I can open the persistent “Ask DungeonBuddy” bar and ask a natural World question without leaving Play, without opening Plan, without supplying a fake live-session number, and without restating the current Beat/Scene. DungeonBuddy uses the Run’s authoritative campaign scope, current DungeonMind World authority, and A7’s server-resolved current-moment context while preserving my exact question as the World retrieval seed.**

Representative turn:

```text
Play Run
  Beat: Hold the Breach
  Scene: North Gate

GM asks:
  "What does Lysandra know about the swarm?"
```

Expected product behavior:

```text
existing AppChrome Agent bar
        ↓
Play Ask plugin
        ↓
identity-only A7 SurfaceContext witness
        +
Play campaign-scoped World request
        +
exact user question
        ↓
POST /api/agent/query
        ↓
server resolves product scope from the durable Play Run
        ↓
shared Agent query service
        ↓
DungeonMind World retrieval + A7 current Play context
        ↓
AgentRuntime
        ↓
visible answer in the same app-scoped Agent pane
```

A8 is **not** an Agent redesign. It makes already-landed A0–A7 capabilities reachable from Play through one truthful invocation path.

---

## 2. Why this is the next slice

The architecture target already says:

```text
Play produces current-work/current-runtime context
        ↓
Surface Interaction publishes pointers
        ↓
Agent Interaction consumes context
        ↓
DungeonMind supplies current World authority
```

A7 closes the first two arrows. The current product still stops at the third:

- `AgentInteractionChrome` is already app-scoped and persistent across routes;
- `AskPluginSlotProvider` is already app-scoped;
- Plan currently registers the only real Ask plugin;
- Play publishes truthful A7 context but does not register an Ask consumer;
- `/api/live/query` still requires `campaign_id + session` matching the currently mounted legacy/live packet;
- a Play Run has an authoritative campaign and Run identity, but **no truthful product reason to invent that top-level live-session number**.

Therefore the next useful capability is not “hoist the Agent bar.” That bar is already hoisted. The next capability is:

> **separate Agent invocation from the legacy live-session request shape, then characterize Play as the second real Ask consumer.**

This is the shortest path from architecture to the product moment we want to dogfood.

---

## 3. User-visible success / north-star metrics

A8 is accepted only when the following are all true.

### 3.1 Play Ask Reachability

From one READY v2 Play Run:

```text
open persistent Agent bar
→ Ask pane is available
→ enter one question
→ exactly one Agent request
→ exactly one visible user turn
→ exactly one visible assistant turn
```

No navigation to `/plan` is required.

### 3.2 Invocation Truthfulness

For the Play Agent request:

```text
client-supplied live session field = 0 occurrences
client-supplied query backend selector = 0 occurrences
client-supplied legacy manifest path = 0 occurrences
client-supplied legacy Hermes session id = 0 occurrences
```

The new Play request must not manufacture a session number merely to satisfy `/api/live/query`.

### 3.3 Context Correctness

Accepted current Play context must still satisfy A7:

```text
Run identity       → Buddy Play APP-STATE
pinned Runbook     → exact committed revision + digest
current Beat       → owning Run progress
current Scene?     → owning Run progress
model prose        → exact pinned authored slices only
```

Stale Beat/Scene/revision witnesses never silently become a different “current” context.

### 3.4 Query Primacy

The literal:

```text
What does Lysandra know about the swarm?
```

must remain byte-for-byte equivalent through:

```text
HTTP request text
→ World projection outer_text
→ GraphRetrievalSession / packet question
→ AgentRuntimeInvocation.message
```

with valid Play context and with stale/degraded Play context.

### 3.5 Context Waste

A8 does not enlarge A7’s current-moment budget:

```text
Beat title    ≤ 160 chars
Beat body     ≤ 320 chars
Scene title   ≤ 160 chars
Scene body    ≤ 640 chars
CURRENT PLAY  ≤ 1536 chars
```

No whole Runbook preload.

### 3.6 Run-local thread correctness

Two different Runs of the same Runbook must **not** silently share one active Agent thread merely because `playable_artifact_id` is the same.

A8 must prove:

```text
Run A + Runbook X → Play thread scope A
Run B + Runbook X → Play thread scope B
```

Plan’s existing document-scoped thread behavior must remain unchanged.

---

## 4. Non-goals

A8 does **not** implement:

```text
Play inspection context
WorkSelectionAnchor
At-a-Glance retrieval ranking
current Beat/Scene retrieval ranking
query-conditioned SurfaceContext omission
semantic relevance scoring
embedding retrieval
context token-budget compiler
Interaction Attention
Interaction Memory durability
Combat context
World writes / graph proposal workflow
Magic Moment right-click assessment
PydanticAI production selection
AgentRuntime public-contract redesign
Plan source-bundle/freshness UI extraction
full Plan Agent UI rewrite
live-turn mutation behavior from the new Agent endpoint
cross-campaign Play graph lens
world-wide Play scope
```

Do not turn A8 into “make every surface Agent-capable.” It proves one second consumer: **READY Play**.

---

## 5. Frozen architecture decision

A8 introduces one surface-neutral **Agent query transport/service seam**, characterized first by Play.

### 5.1 New product endpoint

Preferred v1 route:

```http
POST /api/agent/query
```

This is an Agent/Hermes graph-query endpoint, not a live-turn endpoint.

It must not accept the legacy live-query fields:

```text
session
mode
query_backend
manifest_path
hermes_session_id
```

### 5.2 New request shape

Directional exact contract:

```python
class AgentQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_query_request_v1"] = Field(alias="schema")
    text: str = Field(min_length=1)
    agent_thread_id: str | None = None
    hermes_session_pointer: str | None = None
    trace_requested: bool | None = None
    world_graph_context: AgentWorldGraphQueryContextRequest
    conversation_history: Any | None = None
    surface_context: AgentSurfaceContextRequest
```

Important:

> **There is intentionally no top-level client `campaign_id` and no top-level client `session`.**

For A8 Play, product campaign authority is derived server-side from the durable Run identified by `surface_context`’s `play_run` pointer.

The nested `world_graph_context` remains a requested World lens, not product-scope authority.

### 5.3 A8 endpoint admissibility

A8 v1 accepts only:

```text
surface_context.surface_id == "play"
```

A Plan request continues through the existing `/api/live/query` path in A8.

Do **not** claim `/api/agent/query` is fully multi-surface until a later PR explicitly characterizes Plan/Build against it.

---

## 6. Server-owned Play product scope

The new route/service must establish Play product scope before World retrieval.

### 6.1 Required scope witness

From the A7 identity-only wire, use:

```text
play_run
```

as the minimum authority lookup key.

The server must:

1. require `surface_id == play`;
2. require exactly one canonical `play_run` pointer;
3. load that Run through the existing Play APP-STATE authority;
4. derive the authoritative product campaign from `PlayRunRecord.campaign_id`;
5. never derive product campaign from URL, thread metadata, `ambientSummary`, document title, or the World request itself.

A small public helper on the owning Play context service is acceptable, for example:

```python
@dataclass(frozen=True, slots=True)
class AgentPlayQueryScope:
    run_id: str
    campaign_id: str


def resolve_agent_play_query_scope(
    request: AgentSurfaceContextRequest,
    *,
    root: Path,
) -> AgentPlayQueryScope:
    ...
```

Use existing A7 parsing/Run-read semantics rather than creating a second Run registry.

### 6.2 Scope failure vs enrichment failure

These are intentionally different.

Cannot establish a valid Run scope:

```text
missing play_run
malformed/noncanonical play_run
Run does not exist / APP-STATE unavailable
```

→ **do not invoke the model.** Return typed Agent-query request/unavailable failure.

Run scope established, but A7 current-moment witness is stale:

```text
revision mismatch
Beat mismatch
Scene mismatch
campaign witness mismatch
other A7 enrichment rejection
```

→ continue the explicit user query in the **server-derived Run campaign**, but omit SurfaceContext enrichment exactly as A7 requires.

This distinction preserves both truths:

```text
scope must be authoritative
context enrichment may fail closed without losing the user's question
```

---

## 7. Play World scope v1

A8 deliberately keeps Play World scope boring and deterministic.

For one Play turn:

```text
product campaign = authoritative Run campaign
World scope mode = campaign
focus = none
admissibility = gm
revision pin = null/current unless a neutral exact current projection pin is already available without new coupling
```

### 7.1 Client request builder

Create a Play-specific, non-Plan helper, directionally:

```ts
buildPlayAgentWorldGraphQueryContextRequest(run: PlayRunRecord)
  -> AgentWorldGraphQueryContextRequest | null
```

It may use the existing neutral campaign→World helper:

```text
worldGraph/worldGraphSurfaceContext.getWorldIdForCampaign
```

It must not import:

```text
PlanSessionDescriptor
getPlanWorldGraphContext
buildPlanAgentWorldGraphQueryContextRequest
PlanGraphLens
PlanGraphReferenceResolver
```

If the Run campaign has no known World mapping, Ask is disabled/unavailable with a truthful reason. Do not silently fall back to `eldyrwild` or any default World.

### 7.2 Server validation

For A8 Play, require:

```text
world_graph_context.campaign_id == authoritative Run campaign
scope_mode == campaign
focus.kind == none
admissibility == gm
```

A8 does not permit Play to broaden to world scope or another campaign.

DungeonMind remains final authority for the requested World/revision.

---

## 8. Shared Agent query service

Do not duplicate the whole Hermes branch in a second route.

Create a neutral Buddy-owned service, directionally:

```python
process_agent_query(...)
```

owned under:

```text
apps/live_control_server/services/agent_query.py
```

Its job is to own the common graph-Agent turn sequence:

```text
request validation
→ product-scope validation supplied by caller / Play scope resolver
→ conversation-history normalization
→ World context resolution
→ latest-recap comparison when applicable
→ SurfaceContext resolution
→ AgentRuntime / Hermes graph turn
→ product response
```

### 8.1 Existing `/api/live/query` compatibility

The existing Hermes branch of `process_live_query(...)` may delegate into this shared service **only if parity is proven**.

Its current Plan/live behavior must remain equivalent:

```text
outer campaign/session check remains on /api/live/query
Plan SurfaceContext session check remains
legacy live response session remains present
conversation-history validation remains
Hermes pointer continuity remains
trace shape/status remains compatible
```

The new Play route does not gain live-turn mutation behavior.

### 8.2 No second harness path

A8 must still cross:

```text
AgentRuntime.run(invocation)
```

exactly once per successful turn.

Do not call Hermes host APIs directly from the new route.

---

## 9. Remove live-packet authority from Hermes product envelope where necessary

Today `run_hermes_graph_query(...)` uses `packet` for two product concerns:

```text
pointer continuity campaign
response.session
```

That is acceptable for `/api/live/query`, but not a reason to manufacture a Play session.

A8 may make the smallest compatible internal change needed so a graph-Agent turn can run with:

```text
product_campaign_id = authoritative Run campaign
product_session_number = None
```

while existing live callers preserve current behavior.

Recommended direction:

```python
run_hermes_graph_query(
    ...,
    packet: Mapping[str, Any] | None = None,
    product_campaign_id: str | None = None,
    product_session_number: int | None = None,
)
```

with a guarded internal resolution rule:

```text
existing live caller:
  campaign/session derive exactly as before from packet

new Agent caller:
  product_campaign_id required
  product_session_number = None
  packet may be absent
```

Then:

- Hermes pointer continuity keys against **product campaign**, not an unrelated mounted live packet;
- product response includes `session` only when the product actually has a session value;
- `LiveQueryResponse.session` is already optional on the client; no fake value is required.

Small naming variations are acceptable. The invariant is not.

### 9.1 Existing pointer persistence location

A8 may continue to use the current `HermesSessionPointerStore(session_base)` as an implementation detail when a configured `session_base` exists.

That does **not** mean the live packet supplies Play product scope.

Do not migrate Agent pointer/thread durability to APP-STATE in A8. That remains an explicit future persistence decision.

---

## 10. SurfaceContext contract

A8 reuses A7. Do not invent a second Play context wire.

Client request source:

```text
AgentInteractionProvider.surfaceInteractionPublication
        ↓
buildAgentSurfaceContextRequest(...)
        ↓
require surface_id == play
```

A small sibling helper is recommended:

```ts
buildPlayAgentSurfaceContextRequest(publication)
```

with the same fail-closed behavior as the existing Plan helper.

Forbidden sources:

```text
activeSurfaceContext
ambientSummary
URL run query
DOM
thread metadata
visible Beat/Scene title
client-authored Beat/Scene prose
```

A8 must preserve the exact A7 pointer vocabulary/cardinality and server re-resolution semantics.

---

## 11. Play Agent UI contribution

The owner of the bar does not change.

```text
AgentInteractionChrome = App-scoped host owner
PlayAgentInteractionPlugin = active Play surface contribution
```

Create a thin Play plugin, directionally:

```text
apps/live-control-ui/src/playSurface/PlayAgentInteractionPlugin.tsx
```

Mount it only when Play has one READY, admitted durable Run.

### 11.1 Minimum UI

The first Play Ask proof needs only:

```text
thread title
visible chronological user/assistant transcript
question input
submit button
asking/error state
new thread / thread switch if already cheap through Provider actions
Advanced trace visibility using existing neutral AgentTraceInspector if practical
minimal grounding/citation disclosure if already available from persisted turn data
```

Do not copy the entire `PlanAgentInteractionBar`.

Specifically do not pull in:

```text
Plan source bundle
Plan ingestion coverage
Plan context-sufficiency ladder
Plan retrieval freshness panel
Plan corpus change panel
Plan graph-lens UI
Plan document/session descriptor
Plan citation-source reader UI
```

Those are Plan product capabilities, not requirements for generic Ask.

### 11.2 Existing chrome wording

Update `AgentInteractionChrome` only enough to stop lying that Ask is Plan-only.

When no Ask plugin is present:

```text
Ask is unavailable for the current surface.
```

When Play READY registers its plugin:

```text
Ask DungeonBuddy · Play
```

Do not add route detection. Plugin presence + active Surface publication remain authority for availability/display.

---

## 12. Thread scope: Run identity is not document identity

This is a correctness requirement, not optional polish.

A7 Play publishes:

```text
run_id
playable_artifact_id
```

Those are different identities.

Two Runs may point at the same Runbook. Therefore A8 must not scope Play Agent threads only by:

```text
campaign + surface + documentId
```

### 12.1 Add one neutral surface-instance key

Extend client-local Agent Interaction scope/thread metadata with an optional neutral field, recommended:

```ts
surfaceInstanceId?: string | null
```

Semantics:

```text
Plan
  documentId = planning WorkObject
  surfaceInstanceId = null
  existing storage keys remain byte-for-byte unchanged

Play
  documentId = playable_artifact_id
  surfaceInstanceId = exact run_id
  thread/index active key uses surfaceInstanceId
```

Do not put `run_id` into `documentId`.

### 12.2 Storage compatibility

Existing Plan localStorage keys must not move.

Recommended suffix rule:

```text
surfaceInstanceId present:
  <campaign>:<surface>:instance:<surfaceInstanceId>

otherwise:
  preserve existing document-scoped / surface-scoped suffix exactly
```

Thread payload and index may add optional `surfaceInstanceId` without migrating historical Plan data if loader compatibility proves safe.

If existing parser/schema invariants make the optional addition unsafe, stop and split a tiny **A8A Agent Thread Scope v1** prerequisite rather than silently rewriting existing local storage.

### 12.3 Persistence boundary remains unchanged

This is still bounded browser convenience state.

A8 does **not** decide APP-STATE durability for Agent threads or Interaction Memory.

---

## 13. Play plugin scope publication

When a READY Run is active, the Play plugin rehydrates Agent Interaction scope as:

```ts
{
  campaignId: run.campaign_id,
  sessionNumber: null,
  surfaceId: "play",
  documentId: run.playable_artifact_id,
  surfaceInstanceId: run.run_id,
}
```

This scope controls client thread selection only.

It is **not** World authority and is **not** the server’s product-scope proof. Server product scope still comes from re-reading the Run through APP-STATE.

When Play leaves READY state / switches Runs:

```text
prior plugin unregisters
prior lease cannot submit
Provider rehydrates the new run-local scope
stale async completion cannot append to the wrong Run thread
```

Existing lease/token protections should be reused rather than creating route flags.

---

## 14. Submission algorithm

For one READY Play Run:

```text
1. trim user text
2. require non-empty + not already asking
3. require current lease publication is Play
4. snapshot A7 identity-only SurfaceContext from current lease
5. build campaign-only/no-focus/gm World request from admitted Run campaign
6. ensure/reuse Run-scoped Agent thread
7. build bounded visible conversation history from that thread
8. POST /api/agent/query
9. append exactly one response turn through Provider-owned thread action
10. clear input
```

No optimistic assistant turn.

If submission fails before a response:

```text
input remains recoverable
thread receives no fabricated assistant turn
retry does not duplicate the prior user turn
```

---

## 15. Exact A8 request example

Representative browser payload:

```json
{
  "schema": "dmb_agent_query_request_v1",
  "text": "What does Lysandra know about the swarm?",
  "agent_thread_id": "agent-thread-...",
  "hermes_session_pointer": null,
  "trace_requested": true,
  "world_graph_context": {
    "schema": "dmb_agent_world_graph_query_context_request_v1",
    "world_id": "eldyrwild",
    "campaign_id": "longmont-c2",
    "scope_mode": "campaign",
    "focus": {
      "kind": "none",
      "session_id": null,
      "campaign_id": null
    },
    "admissibility": "gm",
    "revision_pin": null
  },
  "conversation_history": null,
  "surface_context": {
    "schema": "dmb_agent_surface_context_request_v1",
    "surface_id": "play",
    "campaign_id": "longmont-c2",
    "document_id": "<playable artifact UUID>",
    "session_number": null,
    "pointers": [
      {"kind": "play_run", "value": "<run UUID>"},
      {"kind": "playable_revision", "value": "1"},
      {"kind": "current_beat", "value": "beat:hold-the-breach"},
      {"kind": "current_scene", "value": "scene:north-gate"}
    ]
  }
}
```

Explicitly absent:

```text
campaign_id at top level
session at top level
mode
query_backend
manifest_path
hermes_session_id
Beat/Scene prose
ambientSummary
```

---

## 16. Response contract

A8 may reuse the existing graph-Agent product response shape consumed as `LiveQueryResponse`, with these constraints:

```text
mode = hermes_graph_agent
mutations = []
events_written = []
jobs_queued = []
agent_thread_id / turn_id preserved
Hermes pointer handle preserved when available
grounding/citations preserved
agent_trace preserved
session key omitted for /api/agent/query when product_session_number is null
```

Do not add a fake `session: 1`, current mounted session, Runbook target session, or current Beat number.

If a later cleanup wants to rename `LiveQueryResponse`, that is not A8.

---

## 17. Telemetry / observability

A8 inherits A0/A1/A5/A6/A7 telemetry and must preserve all existing schema keys.

Add one content-free product-scope phase for the new Agent path, recommended:

```text
phase name: agent_query_scope_resolution
```

Exact summary vocabulary should remain small. Directional fields:

```text
scope_schema = dmb_agent_query_scope_summary_v1
surface_id = play
scope_status = resolved | rejected | unavailable
campaign_id = <authoritative Run campaign or null>
session_number_present = false
run_scope_resolved = true | false
```

No Run UUID, document UUID, Beat/Scene ID, question, or prose in baseline trace.

A8 must preserve:

```text
A5 context_assembly exact 14-key schema
A6/A7 surface_context_resolution exact 8-key schema
A7 current Play model-context char count
model usage/cost/timing behavior
```

Provider-reported model input usage remains billing truth.

---

## 18. Failure semantics

### 18.1 No READY Run

Play Ask plugin absent.

Global Agent chrome truthfully says Ask is unavailable on current Play state.

### 18.2 Run scope unavailable

No model call.

Return a typed Agent-query failure such as:

```text
agent_query_play_scope_unavailable
```

Do not fall back to mounted live packet campaign/session.

### 18.3 Unknown campaign→World mapping on client

Disable submit / show truthful unavailable state.

Do not guess a World ID.

### 18.4 World unavailable

Use existing typed World/Hermes unavailable response behavior. No legacy corpus fallback.

### 18.5 Stale current-moment witness

A7 behavior:

```text
query executes in authoritative Run campaign
surface_context_resolution = rejected_surface/rejected_scope as appropriate
CURRENT PLAY block omitted
warning preserved
```

Do not silently substitute a different Beat/Scene.

### 18.6 Surface lease changes during request

Async completion captured under Run A must not mutate Run B’s active thread after a route/Run switch.

If current Provider helpers do not already guarantee this for thread append, add the minimum lease/scope identity comparison at completion.

Do not invent a general async task framework.

---

## 19. Required proving story

Use the A7 dogfood shape:

```text
Campaign: longmont-c2
Run: exact durable Run
Beat: Hold the Breach
Scene: North Gate
Question: What does Lysandra know about the swarm?
```

Required proof:

```text
Play READY
→ Agent bar says Ask available
→ open pane
→ question submitted once
→ POST /api/agent/query contains no top-level session
→ server derives campaign from durable Run
→ World request stays campaign/no-focus/gm
→ A7 SurfaceContext resolves Beat + Scene
→ retrieval packet question is exact literal
→ AgentRuntime message is exact literal
→ CURRENT PLAY block is present and <=1536 chars
→ visible answer appears in Play Agent transcript
→ trace available under Advanced diagnostics
```

Then stale the Scene witness while the authoritative Run remains valid:

```text
same exact question
→ same authoritative Run campaign World scope
→ A7 context rejected/omitted
→ query still executes
→ no silent Scene substitution
```

---

## 20. Required tests

### 20.1 Server route contract

New owning tests must prove:

```text
POST /api/agent/query accepts v1 Play request
unknown keys rejected
schema required/alias-only
session is not a legal request field
query_backend is not a legal request field
manifest_path is not a legal request field
hermes_session_id is not a legal request field
non-Play surface rejected in A8 v1
malformed/missing play_run stops before model
Run scope campaign is server-derived
World campaign mismatch rejected before model
world scope != campaign rejected
focus != none rejected
admissibility != gm rejected
```

### 20.2 Shared service parity

Prove one fake AgentRuntime receives equivalent core invocation semantics for:

```text
existing /api/live/query Hermes path
new /api/agent/query Play path
```

where equivalence means the shared AgentRuntime contract, not identical SurfaceContext.

Existing Plan/live route behavior remains green.

### 20.3 No fake session

Assert:

```text
request body has no session
new agent response has no session when product_session_number=None
Hermes pointer continuity campaign == authoritative Run campaign
```

Do not merely assert UI ignored a session field.

### 20.4 Query primacy

Using the literal Lysandra/swarm question, assert:

```text
request.text
World outer_text
retrieval packet question
AgentRuntimeInvocation.message
```

are exact matches.

### 20.5 A7 degradation

Valid Run scope + stale Scene witness:

```text
model still invoked once
World scope unchanged
SurfaceContext absent in invocation
surface trace records rejection
```

### 20.6 Thread Run isolation

Client storage/provider tests:

```text
same campaign + play + same Runbook + Run A ≠ Run B active/index storage
switching A → B loads B thread, not A
switching B → A restores A thread
Plan legacy/document keys unchanged byte-for-byte
```

### 20.7 UI plugin

READY Play:

```text
registers Ask presence
rehydrates Run-scoped thread scope
uses current lease SurfaceContext request
posts once
renders one user + one assistant turn
uses Provider append/persistence
```

Chooser/blocked/integrity failure:

```text
no Play Ask plugin presence
```

### 20.8 Lease switch during in-flight request

Characterize:

```text
submit on Run A
switch to Run B before response resolves
Run A response does not append to Run B thread
```

### 20.9 Regression floor

At minimum rerun:

```text
tests/test_agent_play_surface_context.py
tests/test_agent_surface_context.py
tests/test_agent_context_assembler.py
tests/test_agent_runtime.py
tests/test_hermes_agent_runtime.py
tests/test_pydantic_ai_agent_runtime.py
tests/test_hermes_graph_agent.py
tests/test_hermes_graph_agent_host.py
tests/test_live_query_hermes_graph.py
tests/test_live_control_server.py
tests/test_agent_graph_policy.py
```

plus all new Agent-query owning tests.

Client:

```text
agentInteraction history/storage tests
AgentInteractionProvider tests touching thread scope
AgentInteractionChrome tests
A7 playSurfaceAgentContext tests
new PlayAgentInteractionPlugin tests
new Play World query request tests
liveApi/agent request serialization tests
npm run typecheck
```

---

## 21. Provisional write lease

**This lease is not active until the post-A7 release recheck in §22.**

After #671 merges, recheck exact `main` and open PRs. If any path below is actively leased, stop and serialize rather than dispatching this list unchanged.

### 21.1 Create — server

```text
apps/live_control_server/routes/agent.py
apps/live_control_server/services/agent_query.py
tests/test_agent_query.py
```

One additional dedicated server test file is allowed if route and service tests are clearer separated; record it before editing.

### 21.2 Create — client

```text
apps/live-control-ui/src/playSurface/PlayAgentInteractionPlugin.tsx
apps/live-control-ui/src/playSurface/PlayAgentInteractionPlugin.test.tsx
apps/live-control-ui/src/playSurface/playAgentQueryContext.ts
apps/live-control-ui/src/playSurface/playAgentQueryContext.test.ts
```

### 21.3 Modify — server

```text
apps/live_control_server/main.py
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/agent_surface_context.py
apps/live_control_server/services/agent_play_surface_context.py
tests/test_live_control_server.py
tests/test_live_query_hermes_graph.py
```

### 21.4 Modify — client

```text
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx
apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx
apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts
apps/live-control-ui/src/agentInteraction/agentSurfaceContextRequest.ts
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts
apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx
```

A bounded existing `AgentInteractionProvider` test file may be added to the lease after exact path discovery; record path/assertion/reason before edit.

### 21.5 State-authority docs

```text
Docs/Plans/HANDOFF-AGENT-INTERACTION-play-current-moment-surface-context-v1.md
Docs/Plans/HANDOFF-AGENT-INTERACTION-shared-invocation-play-ask-v1.md
```

A7 edit is backward-looking completion sync only after its merge facts are known.

### 21.6 Read-only / verification-only

```text
Docs/Design/ARCHITECTURE-surface-interaction-layer.md
Docs/Design/DECISION-agent-context-compilation.md
Docs/Design/ARCHITECTURE-application-state-layer.md
Docs/Design/ARCHITECTURE-playable-material-and-runtime.md
Docs/Design/DESIGN-magic-moment-contextual-source-to-world-graph.md
apps/live_control_server/services/agent_runtime.py
apps/live_control_server/services/agent_context_assembler.py
apps/live_control_server/services/agent_graph_policy.py
apps/live_control_server/services/pydantic_ai_agent_runtime.py
apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx
apps/live-control-ui/src/agentInteraction/AskPluginSlot.tsx
src/graph_memory/**
pyproject.toml
uv.lock
MODEL_POLICY.json
```

`PlanAgentInteractionBar.tsx` is deliberately read-only in A8. If the implementation believes it must rewrite/move this component, **stop** and redesign/split rather than absorbing Plan UX into the Play proof.

---

## 22. Release gate after A7 merge

Before implementation dispatch, a steward must perform all of the following.

### 22.1 Re-anchor

Record:

```text
PR #671 state = merged
A7 accepted head = 7f015f3e6ab7a39605565849803e25088a510d4c
A7 final formal review = 5070720084 PASS-equivalent
A7 merge SHA = <fill after merge>
current main = <exact SHA>
open PRs = <exact list>
```

If A7 merged at a different head, stop and review the post-review delta before using this design.

### 22.2 Rebase/recreate the handoff

This design branch is parented from the reviewed A7 head, not current main.

After merge:

```text
rebase/recreate this one-file handoff commit on exact post-A7 main
verify only this handoff changes in the release commit
change status → READY FOR DISPATCH
record exact dispatch base
re-run lease collision check
```

Do not merge this current design branch wholesale if that would replay A7 commits already merged to main.

### 22.3 Activate lease

Only after the above recheck does §21 become the exclusive A8 write lease.

---

## 23. A7 backward sync required in A8 implementation PR

Once A7 is merged, A8 implementation must synchronize the A7 handoff backward with only actual facts:

```text
status = COMPLETE / MERGED
PR = #671
accepted head = 7f015f3e6ab7a39605565849803e25088a510d4c
merge = <actual merge SHA>
formal review cycles = 4
Cycle 1 = 5063079166 CHANGES REQUESTED-equivalent
Cycle 2 = 5068956875 CHANGES REQUESTED-equivalent
Cycle 3 = 5069887383 CHANGES REQUESTED-equivalent
Cycle 4 = 5070720084 PASS-equivalent
active successor = A8 Shared Agent Invocation / Play Ask v1
```

Do not invent the merge SHA before it exists.

---

## 24. Stop conditions

Stop rather than expanding if A8 requires any of the following:

```text
changing DungeonMind contracts
new World write capability
new graph retrieval/ranking semantics
current Beat/Scene as access control
current Beat/Scene appended to the user query
whole Runbook preload
new embedding/vector search
Interaction Memory persistence
APP-STATE Agent persistence selection
PydanticAI production selection
AgentRuntime public-contract break
PlanAgentInteractionBar rewrite/migration
Plan source-bundle UI extraction
Build Agent support
Play inspection/selection
Combat context
At-a-Glance retrieval seeds
cross-campaign/world-scope Play querying
live-turn mutations from /api/agent/query
client-supplied fake session requirement
using run_id as documentId
silently sharing one Play thread across two Runs of one Runbook
new dependency or lockfile change
```

If adding `surfaceInstanceId` cannot be done compatibly without a meaningful local-storage migration, split **A8A Thread Scope v1** first.

---

## 25. Implementation sequence

Recommended nano-commit order after release:

```text
1. A8: add server Agent query request/scope contract + owning tests
2. A8: extract shared Agent-query service while preserving live Hermes parity
3. A8: permit sessionless product envelope / authoritative continuity campaign
4. A8: add Play campaign-only World request builder + transport serializer
5. A8: add neutral Run-scoped thread instance key + compatibility tests
6. A8: add thin Play Ask plugin
7. A8: wire READY Play → plugin and neutral chrome wording
8. A8: add end-to-end query-primacy / stale-context / lease-switch proofs
9. A8: backward-sync A7 + CODE handback
```

Do not use commit order as permission to merge partially. One PR, one independently useful capability.

---

## 26. Verification commands

Exact commands may be adjusted to discovered test filenames, but handback must report exact totals.

Server floor:

```bash
uv run pytest \
  tests/test_agent_query.py \
  tests/test_agent_play_surface_context.py \
  tests/test_agent_surface_context.py \
  tests/test_agent_context_assembler.py \
  tests/test_agent_runtime.py \
  tests/test_hermes_agent_runtime.py \
  tests/test_pydantic_ai_agent_runtime.py \
  tests/test_hermes_graph_agent.py \
  tests/test_hermes_graph_agent_host.py \
  tests/test_live_query_hermes_graph.py \
  tests/test_live_control_server.py \
  tests/test_agent_graph_policy.py \
  -q
```

Server static:

```bash
uv run ruff check \
  apps/live_control_server/routes/agent.py \
  apps/live_control_server/services/agent_query.py \
  apps/live_control_server/services/live_agent_loop.py \
  apps/live_control_server/services/hermes_graph_query.py \
  apps/live_control_server/services/agent_surface_context.py \
  apps/live_control_server/services/agent_play_surface_context.py \
  tests/test_agent_query.py \
  tests/test_live_query_hermes_graph.py \
  tests/test_live_control_server.py
```

Client:

```bash
cd apps/live-control-ui
npm test -- --run \
  src/playSurface/PlayAgentInteractionPlugin.test.tsx \
  src/playSurface/playAgentQueryContext.test.ts \
  src/playSurface/playSurfaceAgentContext.test.ts \
  src/api/liveApi.test.ts \
  src/planSurface/components/agentInteractionHistory.test.ts
npm run typecheck
```

Repository:

```bash
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

If test discovery reveals exact relevant existing Provider/Chrome tests, add them to the floor and record why.

---

## 27. CODE → REVIEW handback requirements

The implementation handback must include:

1. PR URL / branch / exact reviewable head SHA;
2. exact post-A7 dispatch-base SHA;
3. current-main/open-PR/lease recheck at dispatch and handback;
4. mission + user story;
5. changed paths + diffstat;
6. nano-commit list;
7. exact `/api/agent/query` wire schema;
8. proof forbidden legacy fields are rejected;
9. exact server Play product-scope resolution rule;
10. proof product campaign derives from durable Run;
11. exact Play World scope v1 policy;
12. proof no client top-level session is sent;
13. proof Agent response omits session for sessionless product invocation;
14. exact Hermes continuity campaign behavior;
15. proof existing `/api/live/query` Plan/Hermes behavior remains compatible;
16. proof exactly one AgentRuntime call per successful turn;
17. A7 SurfaceContext request source and pointer parity;
18. exact Lysandra/swarm query-primacy proof;
19. stale Scene/revision degradation proof;
20. CURRENT PLAY ≤1536 proof;
21. baseline trace privacy + new scope-phase key set;
22. exact thread `surfaceInstanceId` semantics;
23. Run A/Run B same-Runbook isolation proof;
24. byte-for-byte Plan storage-key compatibility proof;
25. READY-only Play plugin registration proof;
26. in-flight Run switch/no-wrong-thread append proof;
27. visible one-user/one-assistant turn proof;
28. verification commands + exact totals;
29. dependency/lockfile status;
30. A7 predecessor backward sync;
31. bounded lease exceptions;
32. stop conditions encountered (`none` when none);
33. successor claims that remain false.

---

## 28. Reviewer checklist

A reviewer should be able to answer **yes** to all:

```text
[ ] READY Play can use the existing app-scoped Agent pane.
[ ] No second Agent bar/host was created.
[ ] Play does not import Plan session/graph helpers.
[ ] New Agent request has no client session field.
[ ] New Agent request has no backend/mode/legacy manifest selector.
[ ] Server product campaign comes from the durable Run.
[ ] World request is campaign-only/no-focus/gm for A8 Play.
[ ] Missing Run scope stops before model execution.
[ ] Stale Beat/Scene context does not stop the explicit query.
[ ] Stale Beat/Scene is never silently substituted.
[ ] Exact user query stays the retrieval seed.
[ ] AgentRuntime is crossed exactly once.
[ ] A7 CURRENT PLAY bounds remain unchanged.
[ ] No whole Runbook is preloaded.
[ ] No IDs/question/prose leak into baseline trace.
[ ] Existing Plan /api/live/query behavior stays green.
[ ] Play thread scope distinguishes two Runs of one Runbook.
[ ] Plan localStorage keys are unchanged.
[ ] In-flight Run switch cannot append to the wrong thread.
[ ] No live-turn mutation behavior is reachable from /api/agent/query.
[ ] No World writes, inspection, memory, ranking, or PydanticAI selection leaked in.
[ ] A7 state authority is synchronized truthfully.
```

Any “no” is a blocker unless the handoff is explicitly revised by the steward before implementation.

---

## 29. Successor claims that remain false after A8

Even after successful A8 merge, these remain false:

```text
Plan uses /api/agent/query
Build Ask is supported
Play inspection reaches Agent
WorkSelectionAnchor reaches Agent
At-a-Glance refs affect retrieval
current Beat/Scene alter graph ranking
query-conditioned SurfaceContext omission exists
context relevance scoring exists
context token-budget compiler is complete
Interaction Attention exists
Interaction Memory is durable
Agent threads are APP-STATE durable
Combat context reaches Agent
Magic Moment graph assessment is shipped
Agent can publish World truth
PydanticAI is production-selected
```

Likely next re-anchor question after A8:

> **Now that Plan and Play can both produce truthful Agent turns, which missing context signal most improves Context Sufficiency without increasing Context Waste: explicit inspection/selection, or deterministic query-conditioned relevance?**

Do not preselect the successor before re-anchoring on merged A8 and dogfood evidence.

---

## 30. Design rationale in one sentence

> **A8 turns the already-shared Agent chrome and already-truthful Play context into one real Play conversation, while removing the last false product assumption that every Agent turn must pretend to be a live-session query.**
