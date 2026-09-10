# HANDOFF — DOGFOOD-CONTINUITY: Stage 7A1 historical Ingest contextual Ask

**Created:** 2026-09-09  
**Status:** DESIGN READY / STOP-GATED — implementation dispatch is prohibited until the operator completes the post-#698 Stage 4A Human STOP and confirms Stage 7A1 remains the next capability.  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD  
**Canonical handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-7a1-ingest-contextual-ask-v1.md`  
**Implementation branch:** `dogfood-continuity/stage-7a1-ingest-contextual-ask-v1`  
**Suggested PR title:** `DOGFOOD-CONTINUITY: enable contextual Ask on historical Ingest`  
**Design base:** `db7c66603217ab037d0bdbce0802646c4cb1dcf7` — `main` after PR #698 merge  
**Predecessor:** PR #698 — Stage 4A opened-object usefulness  
**Predecessor accepted CODE head:** `4925afc348b0567e020344b8dc26d5d2e2a82a93`  
**Predecessor merge:** `db7c66603217ab037d0bdbce0802646c4cb1dcf7`  
**Predecessor review cycles:** 3  
**Post-#698 Human STOP:** **OPEN at design time**  
**Named successor:** Stage 7A2 — exact recap text-selection / highlight context for Agent turns

> **Dispatch gate:** This handoff may be reviewed and refined now. Do not start implementation until the post-#698 Human STOP has been performed against real C1/C2 material and the operator confirms that Stage 7A1 remains next. If the STOP changes product ordering, rebrief rather than implementing this document by inertia.

---

## 0. Concise re-anchor

The architecture work has crossed the point where another retrieval substrate is the highest-value move.

Current assembled truth:

```text
DungeonMind
  owns World identity, revision, graph truth, admissibility, evidence

Buddy APP-STATE
  owns exact durable source prose and product state

#697
  selected object → complete surface-neutral World object
  selected object Agent context uses that same complete-object contract

#698
  opened object → compact useful presentation
  all already-loaded relationships remain reachable
  technical identity lives behind Advanced

main
  db7c66603217ab037d0bdbce0802646c4cb1dcf7

next product question
  can I ask DungeonBuddy about the thing I am already reviewing
  without leaving Ingest or repasting context?
```

The current Agent shell is app-scoped, but Ask is still Plan-only. Ingest publishes a real lease-guarded surface identity and exact historical recap projection, yet opening Agent chrome on Ingest truthfully tells the GM to go to Plan.

The Demo-Ready roadmap already names the successor:

```text
Stage 7A — useful Agent-on-Ingest recap selection/highlight
```

This PR is the first bounded Stage 7A capability. It does **not** attempt the entire selection/highlight vision at once.

---

# 1. Capability decomposition

The next Agent-on-Ingest work contains several independently useful behaviors. Keep them separate.

| Candidate outcome | Independently useful? | Contract impact | Decision |
|---|---:|---|---|
| Ask from an exact loaded historical recap, with optional opened World object context | Yes | Existing SurfaceContext + World-context contracts gain one Ingest consumer | **KEEP — this PR** |
| Exact arbitrary text highlight / WorkSelection sent to Agent | Yes | New selection identity/transport/resolution contract | **SPLIT — Stage 7A2** |
| “Assess World Graph” / propose graph change from selection | Yes | Agent tool/write/proposal capability | **LATER — Magic Moment successor** |
| Generic Agent search defaults from campaign to World scope | Yes | Retrieval/ranking policy | **NOT THIS PR** |
| Repair Plan generic-lens campaign mismatch | Yes | Plan retrieval/lens policy | **NOT THIS PR** |
| Agent availability on Build / Play | Yes | New surface consumers and context contracts | **Stage 7B / later surface slices** |
| Cross-surface thread binding / source-revision-scoped thread persistence | Yes | Interaction-memory persistence | **Stage 7B** |
| Token/cost/retrieval observability expansion | Yes | Telemetry product surface | **Stage 7B** |
| Threat-specific Agent actions | Yes | Threat/tool capability | **NOT THIS PR** |

### Why selected object stays in this PR

The opened object is optional turn-local focus inside the same Ingest Ask capability, not a second retrieval system.

#697 already established:

```text
selected_node_id
  → existing Agent World-context request
  → same complete World-object service
  → same semantic object as Ingest / Plan / Build / Play
```

Stage 7A1 only makes that existing selected-object Agent path reachable from Ingest.

### Why free-text highlight does not

A highlighted span has different identity and failure semantics:

```text
exact source revision
+ exact selected span
+ source-relative anchoring
+ stale selection behavior
+ bounded selected prose
```

That deserves one explicit WorkSelection contract. Do not smuggle it into `pointers[]` as opaque text or reuse graph-authoring selection types as an accidental permanent Agent API.

---

# 2. Mission and merge-ready invariant

## Mission

> **A GM reviewing a durable historical recap in Ingest can ask DungeonBuddy from the existing Agent chrome, and each turn is grounded in the exact loaded recap plus the currently opened World object when one is selected.**

## Merge-ready invariant

> **An Ingest Agent turn snapshots one active lease-guarded Ingest publication at submit time, resolves the exact loaded recap through Buddy APP-STATE, binds World retrieval to the historical projection’s exact DungeonMind revision/focus and optional selected node ID, and supplies only bounded semantic current-recap context to the model; stale, missing, mismatched, or changed context fails closed without changing generic Agent retrieval policy, World authority, or source authority.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes.** Every path answers whether one Ingest turn is bound to one exact recap/World snapshot and optional exact selected object. |
| Most adversarial sequence | Load C2S25 → open Karsemine → open Ask → submit → immediately select another object/load another recap → first response returns. The submitted turn must remain bound to the submit-time C2S25/Karsemine snapshot. |
| Does evidence detect it? | Required request-capture tests assert exact submit-time source pointers, revision pin, focus, and selected node; later UI changes cannot rewrite the recorded request. |
| Easiest boundary to under-test | Server Ingest SurfaceContext resolution against exact APP-STATE source identity. |
| Split trigger | If useful Ingest Ask requires a new free-text selection schema, generic World-search policy, new thread persistence model, or World/source write capability, stop and split. |

---

# 3. Canonical user story

The canonical witness is the real durable C2 Session 25 recap.

```text
1. GM opens Ingest.
2. GM loads C2 Session 25 historical recap.
3. Recap remains visible.
4. GM clicks Karsemine in the prose.
5. #698 opened-object card appears and remains the same trusted World object.
6. GM opens the existing global “Ask DungeonBuddy” chrome.
7. Ask is available here; it no longer says “Open Plan to enable Ask.”
8. The pane visibly communicates current context, approximately:

   Ingest · C2 Session 25
   Asking with Karsemine

9. GM asks:

   What else do we know about her?

10. The turn uses:
    - exact C2S25 durable recap identity from APP-STATE;
    - exact historical World revision/focus already backing the recap;
    - Karsemine’s exact durable node ID;
    - the existing complete-object Agent path from #697;
    - the explicit user question unchanged.
11. No recap text, source UUID, digest, graph revision, or node ID is dumped into model-facing prose merely because it exists.
12. The answer and citations use existing Agent/Hermes behavior.
13. Closing Ask returns to the same recap and opened object.
```

A second valid path is recap-only Ask:

```text
load C2S25 recap
→ do not open an object
→ Ask DungeonBuddy
→ ask a question with explicit named concepts
```

The turn still knows it is being asked from the exact C2S25 recap context. Generic retrieval remains governed by the existing campaign/focus policy.

This PR does **not** claim that the Agent can reason over arbitrary un-ingested recap prose merely because the recap is visible. Exact free-text selection is Stage 7A2.

---

# 4. Authorities and ownership

Read in this order before implementation:

1. `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`
2. `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
3. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
4. `Docs/Design/DECISION-agent-context-compilation.md`
5. `Docs/Plans/HANDOFF-AGENT-INTERACTION-surface-context-v1.md`
6. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v1.md`
7. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-4a-opened-object-usefulness-v1.md`
8. `Docs/Design/DESIGN-magic-moment-contextual-source-to-world-graph.md` — directional target only
9. Current implementation seams named in §11

If an older Agent handoff conflicts with current `main`, current architecture + merged runtime win.

## 4.1 DungeonMind owns World truth

Do not add graph storage, graph reconstruction, selected-object synthesis, or canon policy to Buddy.

Selected-object Agent context must continue through the existing #697 World-context / complete-object contract.

## 4.2 Buddy APP-STATE owns exact source prose

Historical recap context is not trusted because the browser says “Session 25.”

The client may submit bounded identity pointers. The server must resolve them through the existing APP-STATE source service and verify the persisted source’s campaign/session/domain identity.

Do not:

```text
read checkout Markdown as Agent current-recap authority
trust visible recap prose as server truth
trust a URL path as source identity
query PostgreSQL directly from Agent code
copy recap Markdown into AgentInteractionProvider
```

## 4.3 Surface Interaction owns current surface publication

Canonical turn-scoped client source remains:

```text
SurfaceInteractionPublication.agentContext
```

Do not promote these into transport authority:

```text
activeSurfaceContext
URL parsing
DOM inspection
thread title
ambientSummary
conversation history
```

Ingest already publishes through the legacy-to-neutral lease bridge. Extend that one publication path; do not create a second Ingest context store.

## 4.4 Agent Interaction owns turn compilation

Reuse:

```text
AskPluginSlot
AgentInteractionProvider
/api/live/query
ContextAssembler
AgentRuntime
Hermes runtime
existing citation/trace contracts
```

Do not create an Ingest-specific model endpoint or harness.

---

# 5. Existing contracts to reuse

## 5.1 SurfaceContext wire stays v1

Do not create `dmb_agent_surface_context_request_v2` for this slice.

Existing wire:

```text
dmb_agent_surface_context_request_v1
  surface_id
  campaign_id
  document_id
  session_number
  pointers[]
```

The generic client builder already accepts non-Plan surfaces:

```text
buildAgentSurfaceContextRequest(...)
```

The Plan-only helper must remain Plan-only:

```text
buildPlanAgentSurfaceContextRequest(...)
```

Ingest uses the generic builder.

## 5.2 Ingest pointer vocabulary

For a loaded historical recap, publish exactly these identity pointers unless current code proves an equivalent existing canonical identifier is required:

```text
source_artifact
source_revision
source_sha256
```

All three originate from the exact `HistoricalRecapWorldProjectionResponse`:

```text
sourceArtifactId
sourceRevisionId
sourceSha256
```

Rules:

- values are identity assertions, never model prose;
- no selected text is encoded into pointers;
- no recap Markdown is encoded into pointers;
- no graph object body is encoded into pointers;
- no `runId` is required merely to orient the model if exact source identity is sufficient;
- if implementation proves exact source resolution requires an additional persisted run identity, stop and amend the contract explicitly rather than adding it ad hoc.

The neutral publication should contain no source pointers before an exact historical recap is ready.

## 5.3 World-context wire stays v1

Reuse:

```text
dmb_agent_world_graph_query_context_request_v1
```

Build the Ingest request from the **historical projection snapshot**, not the Plan lens.

Expected mapping:

```text
world_id        ← projection.snapshot.worldId
campaign_id     ← projection.snapshot.campaignId / exact validated equivalent
scope_mode      ← projection.snapshot.scopeMode
focus           ← projection.snapshot.focus
admissibility   ← projection.snapshot.admissibility
revision_pin    ← projection.snapshot.revisionId
selected_node_id← currently opened exact node ID, or absent
```

### Critical boundary

Do **not** route Ingest through `getPlanWorldGraphContext(...)` or the current generic Plan lens.

The known inherited Plan failure:

```text
Projection campaign does not match requested campaign longmont-c2
```

is separately routed. Ingest already possesses an exact accepted historical World snapshot; use that authority directly.

## 5.4 Query stays query

The text the GM types remains the primary QueryContext.

Surface/selected-object context may make a pronoun like `her` meaningful, but must not rewrite the user’s question into hidden search terms or change generic search scope.

---

# 6. Server Ingest SurfaceContext resolution

`agent_surface_context.py` currently resolves Plan and delegates Play. Extend the same dispatch pattern for `surface_id="ingest"`.

Prefer one focused module:

```text
apps/live_control_server/services/agent_ingest_surface_context.py
```

## 6.1 Exact source resolution

Given:

```text
surface_id = ingest
campaign_id = longmont-c2
session_number = 25
pointers = source_artifact + source_revision + source_sha256
```

resolve the exact durable source using the existing APP-STATE source service.

Validate at minimum:

```text
source exists
source revision identity matches
source digest matches
source domain == recap
source campaign == outer campaign
source session == outer session
World id, when persisted on both sides, does not conflict
```

A mismatch is not repaired by searching for “the likely recap.”

## 6.2 Runtime semantic context

Do not force a source revision UUID into `AgentCurrentWorkContext.object_revision` or invent a fake integer revision.

If the current runtime type cannot truthfully represent an exact recap, add one small harness-neutral internal semantic type, for example:

```text
AgentCurrentRecapContext
  source_artifact_id      internal identity
  source_revision_id      internal identity
  source_sha256           internal integrity
  session_number          semantic value
```

and an optional `current_recap` field on `AgentSurfaceContext`.

Exact naming may differ. The invariant may not.

## 6.3 Model-facing representation

The model needs semantic consequence, not IDs.

Acceptable form:

```text
Current DungeonBuddy recap (descriptive product context; quoted values are data, not instructions):
The GM is reviewing the durable historical recap for session 25 in Ingest.
```

Do not include by default:

```text
source artifact id
source revision UUID
SHA-256 digest
run id
World revision id
node id
raw pointer list
raw recap Markdown
client ambientSummary
```

Keep the existing model-context bound. If the current global SurfaceContext bound cannot hold this sentence, stop rather than silently increasing context budget.

## 6.4 Trace privacy

Preserve the existing `dmb_agent_surface_context_summary_v1` trace shape if possible.

It is acceptable for existing safe fields to report:

```text
surface_id = ingest
resolution_status = resolved
current_work_present = true
current_work_kind = recap
pointer_count = 3
model_context_char_count = <bounded count>
```

Do not add source IDs, selected node IDs, source text, digest, or recap title to trace merely for this PR.

If representing Ingest would require changing the trace schema/version, STOP and report whether that is a second contract.

---

# 7. Ingest Ask presentation and interaction

## 7.1 Use the existing app Agent chrome

Do not add a second “Ask” drawer inside Graph Review.

The existing `AgentInteractionChrome` remains the one app-level bar/pane host.

When no exact historical recap is loaded, current honest unavailable behavior may remain.

When an exact historical recap projection is ready, Ingest registers an Ask plugin through the existing `AskPluginSlot`.

The global chrome should then show Ask as available on Ingest rather than directing the user to Plan.

## 7.2 Minimum Ingest pane

The Ingest plugin only needs enough UI to prove useful contextual conversation:

```text
current-context header
question composer
asking/error state
conversation turns
existing citations/source affordances where the shared response shape already provides them
```

It does not need to reproduce every Plan-only diagnostic panel, memory-status panel, config menu, or prep-specific widget.

### Reuse rule

Do not copy the entire `PlanAgentInteractionBar.tsx` into an Ingest component.

Prefer either:

1. reuse existing neutral helpers/provider APIs directly; or
2. extract only the smallest truly surface-neutral Ask submission/turn primitive required by both Plan and Ingest.

If implementation requires a broad rewrite of the Plan Agent pane to make Ingest work, stop and split the shared-Ask extraction from the Ingest consumer.

## 7.3 Context visibility

Before submit, the GM should be able to tell what current product context Ask will use.

Minimum truthful presentation:

```text
Ingest · C2 Session 25
```

When an object is open:

```text
Asking with Karsemine
```

Do not display raw IDs in this ordinary path.

## 7.4 Selected object

`GraphReviewHistoricalRecapProjection` already owns the exact `activeNodeId` used by #697/#698 opened-object inspection.

The Ingest Ask plugin may consume that exact ID as optional turn context.

At submit time:

```text
selected object exists
  → selected_node_id = exact activeNodeId

no selected object
  → selected_node_id absent
```

Never derive selected identity from label text.

Changing the open object after submit affects the **next** turn only.

---

# 8. State / failure matrix

| Observable state | Required behavior |
|---|---|
| Ingest, no historical recap loaded | Ask remains honestly unavailable/disabled; do not fabricate recap context. |
| Historical recap projection loading | Do not submit a turn claiming exact recap context. |
| Exact historical recap ready | Ask plugin available; neutral publication carries exact source pointers. |
| Recap ready, no object open | Turn carries exact recap SurfaceContext + exact World snapshot; no selected node ID. |
| Recap ready, object open | Same plus exact `selected_node_id`. |
| APP-STATE source missing | SurfaceContext enrichment resolves `unavailable`; do not fall back to checkout Markdown. Explicit query may continue under existing Agent failure-tolerance policy if World context remains valid. |
| Source campaign/session mismatch | Reject SurfaceContext enrichment; do not silently relabel scope. |
| Source revision/digest mismatch | Reject/unavailable; do not choose latest source revision. |
| Historical World snapshot malformed/mismatched | Do not submit a fabricated World context; show truthful unavailable state or omit the optional World context according to existing `/api/live/query` contract. |
| Selected node no longer valid for exact World snapshot | Existing selected-object Agent semantics handle miss/partial truthfully; do not label-search fallback. |
| User changes object after clicking Submit | In-flight request remains bound to submit-time selected node ID. |
| User loads another recap after clicking Submit | In-flight request remains bound to submit-time source pointers + World revision/focus. |
| Agent runtime unavailable | Existing Agent error presentation; current recap remains visible and unchanged. |
| Ask pane closes/reopens | Recap/object state remains owned by Ingest; Agent chrome does not become recap authority. |

### No fallback sources

There is no fallback from exact source identity to:

```text
latest recap
current filesystem file
URL session guess
visible DOM text
conversation history
```

---

# 9. Thread / interaction-memory boundary

Stage 7A1 does not redesign thread persistence.

Existing Agent Interaction thread behavior may continue across Ingest turns. The current recap is resolved independently on every turn and must be visibly current in the pane.

Do **not** add a new persisted `sourceRevisionId` field to thread records merely to complete this PR.

If dogfood shows cross-recap thread mixing is confusing, route exact source-revision thread binding to Stage 7B interaction continuity.

Conversation history may assist pronoun/intent interpretation. It may not override the current submit-time SurfaceContext or World revision.

---

# 10. Explicit non-goals

This PR must not absorb:

- arbitrary recap text selection/highlight transport;
- `WorkSelectionAnchor` schema design;
- right-click `Assess World Graph`;
- automatic graph/node/edge proposals;
- World writes or `preview_write` / `confirm_commit`;
- generic Agent campaign → World search default changes;
- generic retrieval ranking/relevance experiments;
- the Plan generic-lens campaign mismatch repair;
- Agent availability on Build;
- Agent availability on Play;
- cross-surface Agent thread persistence redesign;
- new thread durable schema;
- new Agent runtime/harness;
- PydanticAI production selection;
- new model provider;
- recap summarization from raw source prose;
- reading arbitrary source Markdown into model context;
- Stage 4 Threat styling;
- session-navigation redesign;
- Build/Play material/template work;
- current-fiction temporal reducer;
- broad telemetry UI;
- token/cost dashboard;
- APP-STATE migration;
- DungeonMind API changes unless a concrete accepted contract defect is discovered.

Stage 7A is **not complete** after Stage 7A1. Stage 7A2 remains the explicit text-selection/highlight successor.

---

# 11. Implementation seam / write lease

The implementation must begin from the exact post-#698 `main`, not from the design branch’s assumptions if `main` has moved.

Expected production paths:

```text
apps/live-control-ui/src/planSurface/types.ts
apps/live-control-ui/src/planSurface/config/ingestSurfaceConfig.ts
apps/live-control-ui/src/agentInteraction/surfaceInteractionCompat.ts
apps/live-control-ui/src/agentInteraction/agentSurfaceContextRequest.ts
apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx

apps/live_control_server/services/agent_runtime.py
apps/live_control_server/services/agent_surface_context.py
```

Expected new focused production modules, if needed:

```text
apps/live-control-ui/src/agentInteraction/IngestAgentInteractionPlugin.tsx
apps/live-control-ui/src/agentInteraction/ingestAgentWorldContextRequest.ts
apps/live_control_server/services/agent_ingest_surface_context.py
```

Expected owning tests:

```text
apps/live-control-ui/src/agentInteraction/agentSurfaceContextRequest.test.ts
apps/live-control-ui/src/agentInteraction/surfaceInteractionCompat.test.ts
apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.test.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.test.tsx
apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.test.tsx

tests/test_agent_surface_context.py
tests/test_live_control_server.py
tests/test_live_query_hermes_graph.py
```

Not every listed path must change. A changed path must be justified by the invariant.

### Bounded discovery exception

Implementation may add at most **4** additional paths under:

```text
apps/live-control-ui/src/agentInteraction/
apps/live_control_server/services/
tests/
```

only when required for a focused shared helper or owning regression directly serving §2.

If another product domain, persisted schema, or API family must change, STOP and rebrief.

### State-authority sync after accepted implementation

Update separately after implementation review/merge:

```text
Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
this handoff status/evidence block
```

Do not hide roadmap sequencing edits inside a behavioral fix commit.

---

# 12. Implementation contract

```text
INPUT
  active historical Ingest projection
    exact campaign/session
    exact source artifact/revision/digest
    exact DungeonMind snapshot/revision/focus
  optional exact activeNodeId
  explicit user question
  existing Agent thread/history

CLIENT OUTPUT
  existing /api/live/query request
    existing question
    existing conversation history
    surface_context = dmb_agent_surface_context_request_v1
    world_graph_context = dmb_agent_world_graph_query_context_request_v1
      revision pinned to historical projection
      optional selected_node_id

SERVER RESOLUTION
  SurfaceContext
    verify exact recap through APP-STATE
    compile bounded CURRENT RECAP semantic context
  WorldContext
    existing DungeonMind authority / #697 selected-object path

MODEL
  explicit question
  bounded current-recap semantic context
  existing World/retrieval context
  existing conversation continuity

OUTPUT
  ordinary existing Agent response / citations / trace
```

### Replay / idempotency

```text
same visible state + same question
  → same source identity and World revision/focus are submitted

selected object changes
  → next submission carries new exact selected_node_id

loaded recap changes
  → next submission carries new source identity + World revision/focus

retry after Agent error
  → fresh submit-time snapshot; never resurrect hidden stale pointers
```

### Trust boundary

The server verifies:

```text
source identity/digest/revision through APP-STATE
source campaign/session/domain
World context through existing accepted Agent/DungeonMind contracts
```

The server does not treat these as factual authority:

```text
client labels
ambientSummary
thread title
visible DOM
URL prose
```

---

# 13. Evidence required to merge

## 13.1 Client SurfaceContext publication

Prove:

1. Ingest with no loaded historical recap publishes no source pointers.
2. Exact historical recap ready publishes exactly the accepted source identity pointers.
3. Loading a different recap replaces those pointers; stale pointers do not remain on the active lease.
4. generic `buildAgentSurfaceContextRequest` emits `surface_id="ingest"`, exact campaign/session, `document_id=null`, and bounded pointers.
5. Plan-only builder remains Plan-only and existing Plan tests stay green.

## 13.2 Server exact recap resolution

Prove:

6. exact durable recap identity resolves from APP-STATE.
7. wrong digest fails closed.
8. wrong source revision fails closed.
9. wrong campaign fails closed.
10. wrong session fails closed.
11. non-recap source fails closed.
12. missing APP-STATE source does not fall back to filesystem Markdown.
13. model-facing context contains semantic current recap/session but no source IDs/digest/raw prose.
14. trace remains bounded and contains no source IDs/prose.

## 13.3 Exact historical World context

Prove:

15. Ingest World-context request uses the historical projection revision pin.
16. focus/campaign/admissibility come from that same accepted snapshot.
17. selected object adds the exact selected node ID.
18. no selected object omits `selected_node_id`.
19. the builder does not call/use Plan generic lens state.
20. generic Agent scope defaults remain unchanged.

## 13.4 Ingest UI / Agent plugin

Prove:

21. no recap loaded → Agent chrome remains honestly unavailable for Ask.
22. exact recap loaded → Ingest Ask plugin registers in existing global host.
23. the pane visibly states current recap context.
24. opened object is visibly reflected as current turn context without showing raw ID.
25. submission sends both exact SurfaceContext and exact World context.
26. changing object after submit does not mutate captured request.
27. changing recap after submit does not mutate captured request.
28. response/error leaves recap and opened-object state intact.
29. closing/reopening Agent does not navigate away from Ingest.

## 13.5 Selected-object parity

Use one mocked or bounded integration witness to prove:

```text
Ingest selected_node_id = Karsemine exact ID
→ Agent server receives selected node
→ existing #697 selected-object envelope path is used
→ no alternate label-based object interpretation is introduced
```

Do not duplicate #697’s entire complete-object suite.

## 13.6 Regression

At minimum rerun the focused suites covering:

```text
Agent SurfaceContext
Agent World selected-object context
Agent Interaction chrome/provider
Plan Agent Ask
historical Ingest recap/object projection
live query server contract
```

Production UI paths change, so run:

```bash
cd apps/live-control-ui && npm test -- --run <focused suites>
cd apps/live-control-ui && npm run build
```

If the inherited `ThreatPublicationPanel.tsx: JSX` build failure is still present on base, follow baseline-failure protocol: compare exact base/head and do not call the build green.

Also run:

```bash
git diff --check
git diff --name-only <base>...HEAD
git diff --stat <base>...HEAD -- <leased paths>
```

Backend focused test commands must be recorded exactly in handback.

---

# 14. Minimal live dogfood proof

Use real durable C1/C2 state. Do not fabricate a special fixture as the only human proof.

## Witness A — C2S25 selected object

```text
open Ingest
load C2 Session 25
click Karsemine
open Ask DungeonBuddy
verify visible context says Ingest / C2S25 / Karsemine
ask: “What else do we know about her?”
```

Require:

```text
Ask available without leaving Ingest             yes
recap remains visible/current                     yes
selected object remains open                      yes
turn uses exact source revision/digest            yes, trace/request proof
turn uses exact historical World revision         yes
turn selected_node_id is exact Karsemine ID       yes
selected object uses #697 semantic path            yes
raw ids/digests absent from ordinary UI/model     yes
citations/answer render through existing Agent    yes
```

## Witness B — same recap, no selected object

Close the object and ask a named question, for example:

```text
What do we know about Lysandra from around this point in the campaign?
```

Require:

```text
current recap context present
selected_node_id absent
explicit named query remains retrieval seed
generic scope policy unchanged
```

## Witness C — context replacement

Load a different durable C1/C2 recap after using C2S25.

Require:

```text
pane shows new recap context
next request uses new exact source identity
next request uses new exact World snapshot/focus
no C2S25 source pointer leaks into the new turn
```

If another recap is unavailable in APP-STATE, use the nearest real durable adopted source and record the coverage limitation truthfully; do not re-ingest to manufacture proof.

---

# 15. Human STOP — “Does the Agent finally belong where I am working?”

After merge, stop before Stage 7A2.

Dogfood naturally from Ingest and ask:

> **Can I stay inside an old recap, click something I care about, and ask DungeonBuddy a useful follow-up without explaining what page, session, or object I mean?**

Judge:

- Does Ask feel like part of Ingest rather than a Plan feature teleported here?
- Is current recap context obvious enough without technical clutter?
- Does clicking an object make pronoun/follow-up questions meaningfully better?
- Does the answer remain trustworthy about World/source provenance?
- Does stale context ever survive a recap/object change?
- Is recap-only Ask useful enough to keep?
- What questions immediately make you want to highlight exact prose?

Classify failures:

```text
A — useful as-is
C — current-context identity/presentation problem
O — selected-object context problem
W — World retrieval problem outside Stage 7A1
S — source identity / exact recap problem
T — thread/continuity problem for Stage 7B
H — exact text highlight is the missing capability → Stage 7A2
X — unrelated successor
```

Do not auto-dispatch Stage 7A2 until this STOP is discussed.

---

# 16. Stop conditions

STOP and report rather than expanding if:

- exact Ingest recap context cannot be represented without creating a new `/api/live/query` schema version;
- source identity cannot be verified through current APP-STATE service boundaries;
- the implementation needs raw recap Markdown in Agent context just to establish current work;
- selected-object Agent parity requires changing DungeonMind complete-object semantics;
- the proposed fix is label/alias guessing rather than exact selected node ID;
- Ingest Ask requires repairing generic Plan lens/search policy;
- free-text selection becomes required for the mission;
- thread records require a new persisted source-revision field;
- sharing the Ask UI requires a broad rewrite rather than a narrow neutral extraction;
- the Agent runtime/harness must change providers;
- a World write/proposal path becomes necessary;
- a path outside §11 or bounded discovery is required;
- post-#698 Human STOP changes the product ordering before dispatch.

Report:

```text
Stop condition:
Observed behavior:
Invariant clause affected:
Owning boundary:
New public/durable contract discovered:
Required evidence now missing:
Why Stage 7A1 cannot absorb it:
Proposed successor:
Roadmap/steward update needed:
```

---

# 17. Acceptance rubric

- [ ] Post-#698 Human STOP completed and operator explicitly confirms Stage 7A1 dispatch.
- [ ] Exactly one capability remains: contextual Ask from exact historical Ingest recap with optional selected World object.
- [ ] #697 selected-object semantic contract remains unchanged.
- [ ] #698 opened-object interaction remains unchanged.
- [ ] Agent Ask uses the existing app Agent chrome and existing `/api/live/query` path.
- [ ] Ingest SurfaceContext comes from active lease-guarded neutral publication.
- [ ] Exact recap identity resolves through APP-STATE.
- [ ] No checkout-Markdown / URL / DOM fallback becomes source authority.
- [ ] Existing SurfaceContext v1 wire schema remains unchanged.
- [ ] Ingest pointer vocabulary is bounded and identity-only.
- [ ] Historical World context is pinned to the exact recap projection snapshot.
- [ ] Optional selected object uses exact `selected_node_id` and #697 Agent path.
- [ ] User question remains unchanged QueryContext.
- [ ] Generic Agent retrieval scope/ranking policy remains unchanged.
- [ ] Plan generic-lens bug remains outside this PR.
- [ ] Model-facing recap context is sparse semantic prose, not raw IDs or source body.
- [ ] Trace does not leak source IDs/digest/prose.
- [ ] No new durable thread schema is introduced.
- [ ] Free-text highlight / WorkSelection remains NOT DONE and named as Stage 7A2.
- [ ] Build/Play Agent availability remains NOT DONE.
- [ ] Stage 7B observability/continuity remains NOT DONE.
- [ ] Focused exact-head tests and build/base-head evidence are recorded.
- [ ] Real C1/C2 Ingest dogfood passes the selected-object witness.
- [ ] Human STOP is performed after merge before any Stage 7A2 dispatch.

---

# 18. Required review handback

The CODE handback must include:

1. exact base and head SHA;
2. nano-commit list and story for each;
3. actual changed paths vs §11 lease;
4. exact SurfaceContext request captured from Ingest;
5. exact World-context request captured from Ingest;
6. proof the source identity resolved from APP-STATE rather than checkout files;
7. proof selected-object path reuses #697 semantics;
8. model-facing CURRENT RECAP example with sensitive/internal identity removed;
9. trace summary example proving no source prose/IDs leaked;
10. all focused commands and exact results;
11. base/head disposition for any inherited production build failure;
12. live C1/C2 witnesses and what was actually observed;
13. explicit confirmation that generic search/lens policy did not change;
14. explicit confirmation that free-text highlight remains unimplemented;
15. stop conditions encountered, or `none`.

The PR description is transport metadata only. This checked-in handoff, the cumulative diff, nano commits, evidence, and review findings are the implementation contract.
