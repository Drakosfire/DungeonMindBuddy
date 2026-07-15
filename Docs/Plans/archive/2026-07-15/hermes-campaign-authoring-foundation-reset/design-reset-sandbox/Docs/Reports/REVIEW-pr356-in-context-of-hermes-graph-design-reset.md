# REVIEW — PR356 in context of the Hermes × World Graph design reset

**Review date:** 2026-07-14  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Main/base SHA observed:** `4e9b489351ac2aa3eee3e62584b7fe0dd2cffac7`  
**PR356 head reviewed:** `2f10dd579fc14b2ea6cbc455de2b12ac2db2f4b9`  
**Disposition:** **SUPERSEDE WITH REPLACEMENT PR**

## Executive judgment

PR356 appears internally coherent with its narrow Rung 5 contract: it projects bounded visible user/assistant prose from the active Plan thread, validates it repeatedly at trust boundaries, preserves thread isolation, avoids a Hermes session pointer, and keeps grounding/citations current-turn-only.

That contract is no longer the correct next product slice. The Tripod dogfood failure is upstream of conversational continuity: the visible panel and Hermes do not consume one retrieval state, accepted graph claims are treated as unusable unless an anchor ID is present, and the classifier does not distinguish an available anchor from a readable or opened source. Merging PR356 would make pronoun replay more robust while leaving the factual interaction architecture incoherent.

The useful implementation should be retained conceptually, not merged as the foundation of the next ladder.

## Current PR state and changed-path inventory

GitHub reported:

- state: open;
- mergeable: true;
- base: `main @ 4e9b489351ac2aa3eee3e62584b7fe0dd2cffac7`;
- head: `2f10dd579fc14b2ea6cbc455de2b12ac2db2f4b9`;
- commits: 5;
- changed files: 18;
- additions/deletions: `+1480 / -37`.

The PR body is stale: it reports final head `a4d15f47…`, 16 paths, and 1,005 insertions. No GitHub review, review-thread, or CI-status artifacts were attached to the actual head at review time.

Actual changed paths:

```text
apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx
apps/live-control-ui/src/agentInteraction/hermesConversationHistory.test.ts
apps/live-control-ui/src/agentInteraction/hermesConversationHistory.ts
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx
apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts
apps/live_control_server/routes/live.py
apps/live_control_server/services/hermes_graph_agent_contract.py
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/live_agent_loop.py
tests/test_hermes_graph_agent.py
tests/test_hermes_graph_agent_host.py
tests/test_live_control_server.py
tests/test_live_query_hermes_graph.py
```

## Lens A — implementation correctness

### Behavior implemented correctly by inspection

1. **Bounded visible-prose replay.** The UI selects at most six complete prior user/assistant pairs, twelve messages, 4,000 characters per message, and 16,000 total characters.
2. **Thread isolation.** History is built only from the active thread supplied to `PlanAgentInteractionBar`.
3. **No durable Hermes continuity.** The request still carries no durable `session_id`; the observed Hermes session ID is trace-only.
4. **Fresh current-turn graph scope.** The host request is pinned to the server-resolved graph revision and scope for the new turn.
5. **Current-turn-only grounding.** The classifier ignores transcript messages and derives acceptance only from current tool events.
6. **Malformed-history isolation.** Invalid children/pairs are dropped at UI construction and rejected at HTTP/service/IPC boundaries.
7. **Non-Hermes rejection.** Supplying history to the legacy live backend is rejected rather than silently ignored.

### Conventional review findings

#### F1 — stale PR handback and unverifiable claimed results

The PR body does not describe the current head. The claimed path inventory and test results therefore cannot be accepted as proof for `2f10dd5…`. No combined CI status is attached.

**Severity:** blocking for merge confidence, not necessarily a code defect.  
**Required repair if PR were otherwise kept:** regenerate the handback from the actual head and independently rerun every owning-boundary command.

#### F2 — one contract duplicated across four implementations

The same role, pairing, per-message, total-character, and message-count rules are independently encoded in:

- browser projection;
- browser wire normalization;
- HTTP route normalization;
- service normalization;
- IPC request validation.

Repeated validation is appropriate; repeated policy implementation is not. The constants and semantic validator should have one canonical contract representation, with boundary-specific adapters calling it or proving equivalence through generated fixtures.

**Risk:** silent drift where a valid browser request is rejected downstream or malformed history is admitted by one boundary.

#### F3 — tests prove the contract with fake hosts, not the user journey

The HTTP and product tests synthesize tool events and anchor IDs. They do not prove:

- Hermes chooses a graph tool;
- the pinned Hermes callback emits the expected completion event in the production host;
- the published Eldyrwild graph returns Tripod claims/anchors;
- the UI panel and answer align;
- pronoun replay succeeds with the real model.

The handoff correctly named real dogfood as an acceptance owner, but the PR does not contain externally visible proof of it.

#### F4 — replay is lexically useful but structurally weak

A clicked/selected graph object is not represented as a typed conversational referent. PR356 asks Hermes to reconstruct identity from prose even when the product has already resolved a durable node ID. This makes the weakest signal carry the continuity burden.

### Tests not run in this review environment

A repository checkout and the operator’s activated World Graph/runtime were not available. The GitHub connector allowed complete source and PR inspection but not local execution. Therefore this report does **not** claim any test suite passed.

## Lens B — architectural correctness

### A1 — PR356 improves continuity on top of a false retrieval split

The preflight resolver computes matched node IDs, node views, relationships, and attributes for the panel. `build_hermes_graph_turn_request` discards those fields and passes only scope/revision. Hermes must rediscover the same object through a separate model-directed retrieval path.

Prose replay cannot repair disagreement between those paths. It may even make the discrepancy more confusing by resolving “it” correctly while the agent still fails to produce an admitted graph completion.

### A2 — the acceptance classifier tests anchor presence, not grounding

A completion is “evidence-bearing” when it has:

- completion state;
- matching scope;
- outcome `enough | partial | truncated`;
- at least one source-anchor ID.

It does **not** test:

- which explicit graph claims were returned;
- whether the anchor is readable;
- whether Hermes opened it;
- whether a source read passed integrity checks;
- which claims the final answer used;
- whether the answer is direct fact or synthesis.

Thus the current `grounded` label is semantically false.

### A3 — accepted graph-native assertions are second-class

Tripod is represented as accepted, canonical, GM-authored graph assertions with explicit epistemic/canon/visibility metadata. The product still treats those claims as unusable unless a source-anchor event passes a generic classifier. That conflicts with the Campaign Supergraph’s role as durable canonical materialized memory and makes graph-native corrections awkwardly dependent on a separate “source” copy of themselves.

### A4 — visible panel state overclaims product success

The panel renders candidate matches, connected objects, and attributes as concrete graph context. It does not show whether Hermes received, used, rejected, or independently rediscovered them. A successful panel beside an abstaining answer is therefore expected behavior under the current architecture, not an exceptional bug.

### A5 — durable sessions would preserve confusion

Adding a persistent Hermes session now would preserve prose, tool chatter, and unresolved retrieval assumptions across turns. It would not establish a coherent claim-authority model. Durable continuity must follow—not precede—the shared retrieval/claim protocol.

## Dogfood findings relevant to PR356

1. The canned `hermes_insufficient_evidence` response proves only that the classifier found no qualifying completion.
2. Unreadable Tripod graph-data anchors alone do not explain the abstention, because unreadable anchors are still emitted and the classifier accepts anchor IDs without checking readability.
3. The high-probability runtime causes are:
   - Hermes called no graph tool;
   - no completion callback was captured;
   - the completed retrieval returned no anchors for selected objects;
   - a malformed or unexpected result shape summarized to no outcome/anchors.
4. The pinned Hermes 0.18.2 callback passes the raw tool result string to `tool_complete_callback`, reducing the likelihood that upstream output persistence stripped the JSON before DungeonBuddy observed it.
5. The exact first runtime cause still requires the operator’s captured Tripod request/trace and activated graph root.

## Salvageable implementation

Retain or reapply after the retrieval reset:

- bounded chronological projection of visible prose;
- strict role/content-only wire shape;
- active-thread isolation;
- per-message and total-size caps;
- malformed-pair isolation;
- no factual authority assigned to conversation text;
- tests for cross-thread leakage and stale-revision prose.

Do not retain as-is:

- duplicated independent history-policy implementations;
- prose as the primary UI referent mechanism;
- the assumption that continuity is the next critical path;
- acceptance tests that substitute synthetic anchor IDs for a real claim/evidence journey.

## Risks of merging

- reinforces the current ladder’s sequencing;
- increases contract surface that will be rewritten;
- creates pressure to proceed to durable sessions before authority/retrieval is coherent;
- improves a secondary behavior while the primary object-lookup journey remains broken;
- makes future demolition politically harder because more tests encode the old architecture.

## Risks of closing/superseding

- loses an immediately useful implementation of safe prose replay;
- delays pronoun follow-ups until the shared referent protocol lands;
- requires reapplying some frontend/service tests later.

These are bounded and cheaper than stabilizing the wrong architecture.

## Recommendation

**SUPERSEDE WITH REPLACEMENT PR**

Keep PR356 open only long enough to preserve review context and cherry-pick/reference the safe history-projection work. Do not merge it as a foundation. The replacement sequence should first establish claim authority, a shared retrieval session, and panel/answer alignment; selected-object referents and bounded prose replay then return as a later continuity slice.
