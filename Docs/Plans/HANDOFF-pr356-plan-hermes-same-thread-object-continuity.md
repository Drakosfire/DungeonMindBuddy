# HANDOFF — PR010B Rung 5: bounded same-thread object continuity

**Created:** 2026-07-14
**Status:** ACTIVE — dispatch exactly one implementation capability after the docs-only re-anchor described below.
**Expected GitHub PR:** `#356`
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr356-plan-hermes-same-thread-object-continuity.md`
**Suggested branch:** `agent/pr010b5-plan-hermes-thread-continuity`
**Predecessor merge:** PR355 / `7671a633f7a82dd040fb5f599885f1d6af4b35f0`
**Implementation base:** the docs-only Rung 5 re-anchor commit from current `main`; record its exact SHA when dispatching the worker.

If another pull request claims `#356` before this handoff is committed, rename the handoff and branch to the next available number before dispatch. Do not leave the planned PR number ambiguous.

---

# Dispatcher-only prerequisite — docs-only authority re-anchor

This is the next repository action. It happens before the coding agent begins and is not part of the implementation PR diff.

Commit the following five documentation changes together as one docs-only re-anchor:

| Action | Path                                                                    | Required synchronization                                                                                                             |
| ------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Create | `Docs/Plans/HANDOFF-pr356-plan-hermes-same-thread-object-continuity.md` | Commit this complete handoff without compression or omitted sections                                                                 |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`                          | Mark Rung 4C / PR355 `DONE`; mark Rung 5 `READY`; sharpen Rung 5/6/7 ownership                                                       |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`                          | Record the merged ladder and make Rung 5 the next critical-path capability                                                           |
| Modify | `Docs/Design/ANCHOR-agent-interaction-hermes.md`                        | Replace the obsolete “after PR008B” state with the post-PR355 state and separate stateless prose replay from durable Hermes sessions |
| Modify | `Docs/Design/UX-STORIES-agent-interaction-hermes.md`                    | Assign same-thread pronoun resolution to Rung 5 and session/reload lifecycle to Rung 6                                               |

The synchronized ladder must read substantively as:

```text
DONE    Rung 1 — graph-only dispatcher
DONE    Rung 2 — model-visible catalog and adapter
DONE    Rung 3 — embedded Hermes graph-agent turn
DONE    Rung 4A — process-isolated host
DONE    Rung 4B — single-turn backend product cutover
DONE    Rung 4C — Plan evidence presentation and completed-turn persistence (#355)
READY   Rung 5 — same-thread object continuity through bounded visible-prose replay
LATER   Rung 6 — durable Hermes session-pointer and reload/process lifecycle
LATER   Rung 7 — cumulative product acceptance and replaced-path demolition
```

The authority documents must also record:

* PR010B remains the active umbrella.
* PR011 remains blocked until PR010B is cumulatively accepted.
* PR009 remains an independent parallel lane.
* Rung 5 does not establish a persistent Hermes session.
* Rung 5 does not make prior conversation text factual authority.
* Rung 5 does not own demolition or backend-selector removal.
* Reload-safe completed-turn display already exists from Rung 4C.
* Rung 6, not Rung 5, owns thread-to-Hermes session identity and its process/restart lifecycle.
* Rung 7 owns any remaining real-runtime cumulative proof and deletion of replaced Hermes product paths.

After committing the re-anchor:

```bash
git rev-parse HEAD
git show -s --format='%H%n%P%n%s' HEAD
```

Record that SHA as the implementation base. Create the implementation branch from exactly that commit.

Do not dispatch from the raw PR355 merge commit while the canonical tracker and roadmap still describe PR355 as active.

---

## §0 Capability decomposition decision

| Candidate outcome                                                                              |                  Independently useful? |      Durable contract changed? | Product surface changed? | Failure model changed? | Decision                                           |
| ---------------------------------------------------------------------------------------------- | -------------------------------------: | -----------------------------: | -----------------------: | ---------------------: | -------------------------------------------------- |
| Synchronize the canonical roadmap, tracker, Hermes anchor, and UX stories after PR355          | No; prerequisite authority maintenance |            No runtime contract |                       No |                     No | Complete in the dispatcher’s docs-only base commit |
| Project bounded prior visible user/assistant prose from the active local Plan thread           |                           No by itself | Yes, outbound request contract |               Indirectly |                    Yes | Include as one layer of Rung 5                     |
| Carry that projection through the HTTP, service, and host boundaries                           |                           No by itself |                            Yes |                       No |                    Yes | Include as one layer of Rung 5                     |
| Resolve pronouns or shorthand while requiring fresh graph tools for every factual claim        |                                    Yes |                            Yes |                      Yes |                    Yes | **Selected capability**                            |
| Preserve exact new-turn revision, scope, grounding, and citation authority despite prior prose |                           No by itself |                            Yes |                      Yes |                    Yes | Include; it is the core safety invariant           |
| Bind one local thread to a durable Hermes session                                              |                                    Yes |                            Yes |                      Yes |                    Yes | Rung 6 successor                                   |
| Resume Hermes internal state across reload or process restart                                  |                                    Yes |                            Yes |                      Yes |                    Yes | Rung 6 successor                                   |
| Run the cumulative production journey and delete replaced Hermes paths                         |                                    Yes |                            Yes |                      Yes |                    Yes | Rung 7 successor                                   |
| Remove the Live/Hermes selector or change the default backend                                  |                                    Yes |                            Yes |                      Yes |                    Yes | Rung 7 successor                                   |
| Add server-side thread or transcript storage                                                   |                                    Yes |                            Yes |                      Yes |                    Yes | Reject from PR010B Rung 5                          |
| Add drafts, writes, preview, confirmation, or Graph Review mutation tools                      |                                    Yes |                            Yes |                      Yes |                    Yes | PR011 successor                                    |

**Selected capability**

```text
Same-thread object continuity through bounded replay of prior visible role/content pairs, with fresh graph retrieval remaining the exclusive authority for every new factual turn.
```

**Why the included layers form one capability**

The browser projection, HTTP contract, service validation, host request, graph-authority enforcement, and end-to-end tests are not independently valuable. They are the necessary trust boundaries for one user-observable behavior: a follow-up such as “What is it connected to?” understands the active thread’s referent without reusing prior factual evidence.

**Named successors**

```text
Rung 6 — durable thread-to-Hermes session identity and reload/process-restart lifecycle.
Rung 7 — cumulative real-runtime acceptance, obsolete Hermes path demolition, selector removal, and default-backend decision.
PR011 — governed read/draft/write tool runtime.
```

---

## §1 Mission

```text
A GM can ask a second question in the same local Plan thread using pronouns or shorthand established by prior visible turns, and Hermes resolves that conversational identity while performing fresh graph retrieval for every factual claim.
```

### Invariant

```text
Prior visible conversation prose may identify the subject of the new question, but the new request’s server-resolved graph scope and revision, its current graph-tool results, and its newly admitted source anchors are the only authorities for facts, grounding, and citations.
```

Every changed layer must establish or prove that invariant.

### Mission falsification test

This is no longer one Rung 5 slice if implementation must also deliver any of the following:

```text
- a durable Hermes session pointer;
- Hermes internal transcript persistence;
- server-side thread storage;
- session restoration after process restart;
- a new graph operation;
- automatic graph-head polling or revision migration;
- graph writes or authored-prep persistence;
- legacy-path demolition;
- backend-selector removal;
- a default-backend change;
- Play-surface continuity;
- a new chat or diagnostic surface.
```

Stop rather than quietly absorbing one of those outcomes.

---

## §2 Context, authority, and boundaries

| Field                          | Required interpretation                                                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Parent authority               | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` and `Docs/Plans/PR-TRACKER-campaign-supergraph.md` after the docs-only re-anchor |
| Product/architecture reference | `Docs/Design/ANCHOR-agent-interaction-hermes.md`                                                                                |
| Acceptance reference           | `Docs/Design/UX-STORIES-agent-interaction-hermes.md`                                                                            |
| Repository operating rules     | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/skills/external-agent-pr-loop/SKILL.md`                       |
| Predecessor                    | Merged PR355, merge SHA `7671a633f7a82dd040fb5f599885f1d6af4b35f0`                                                              |
| Existing host seam             | `HermesGraphAgentTurnRequest.conversation_history` and `AIAgent.run_conversation(..., conversation_history=...)`                |
| Existing factual authority     | PR354/PR355 current-turn graph envelope, current tool events, grounding classifier, and opaque source-anchor citation admission |
| Exact browser input            | The active local thread’s prior visible completed turns, treated as `unknown`                                                   |
| Exact server input             | Optional `conversation_history`, treated as `unknown` again at the HTTP and service boundaries                                  |
| Exact factual input            | The current request’s newly resolved World Graph envelope and current host tool results                                         |
| Named successor                | Rung 6 durable Hermes session-pointer continuity                                                                                |
| What remains false             | No persistent Hermes session, no server transcript, no process-state continuation, no write capability, no demolition           |
| Explicit non-goals             | Listed in §5                                                                                                                    |

Read these inputs in order before editing code:

1. The re-anchored roadmap.
2. The re-anchored tracker.
3. This handoff.
4. The re-anchored Hermes anchor and UX stories.
5. `AGENTS.md`.
6. `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`.
7. `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`.
8. `apps/live-control-ui/src/api/liveApi.ts`.
9. `apps/live_control_server/routes/live.py`.
10. `apps/live_control_server/services/live_agent_loop.py`.
11. `apps/live_control_server/services/hermes_graph_query.py`.
12. `apps/live_control_server/services/hermes_graph_agent_contract.py`.
13. `apps/live_control_server/services/hermes_graph_agent.py`, inspection only.
14. The owning tests listed in §4.

### Authority precedence

```text
1. Re-anchored Campaign Supergraph roadmap and tracker
2. Re-anchored Hermes architecture anchor
3. This checked-in handoff
4. Accepted behavior on current main and its owning tests
5. UX acceptance stories
6. PR summaries and historical handoffs
7. Chat summaries or local notes
```

The PR description is not an acceptance authority. Review the repository behavior, tests, serialized payloads, and manual evidence. Stale PR prose alone is not a blocker and must not trigger administrative rework.

### Existing seams that should be extended, not rebuilt

The repository already has most of the internal plumbing:

* `HermesGraphAgentTurnRequest` already contains optional `conversation_history`.
* The host wire contract already serializes `conversationHistory`.
* The embedded runtime already passes caller-owned history to `run_conversation`.
* The Hermes system policy already states that prior messages resolve intent and pronouns only.
* The graph query adapter already pins the current request to a resolved revision.
* Grounding and citation admission already ignore Hermes transcript messages.
* The Plan thread already stores bounded visible questions and answers locally.
* PR355 already sanitizes untrusted turns during construction, persistence, and rehydration.
* Graph citations are already isolated from legacy path citations.

Rung 5 should connect and harden these seams. It must not introduce a second conversation store or a new agent runtime.

---

## §3 Observable-path inventory

| Observable path                                        | Current behavior                                   | Required behavior                                                                                                           | Owning boundary                                       |
| ------------------------------------------------------ | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| First Hermes question in a new thread                  | One independent graph-agent turn; no prior history | Preserve the exact independent-turn behavior; omit `conversation_history` when no valid prior pairs exist                   | Plan projection + API serializer                      |
| Second question in the same thread                     | Another independent turn with no prior prose       | Send a bounded chronological projection of the active thread’s prior visible user/assistant pairs                           | Plan + serializer                                     |
| Pronoun follow-up                                      | “It” lacks conversational referent                 | Hermes may use prior prose to resolve “it,” then must call current graph tools                                              | Hermes runtime + real dogfood                         |
| Shorthand follow-up                                    | User must repeat the full object name              | Shorthand established by prior visible turns may identify the object                                                        | Same                                                  |
| Fresh factual retrieval                                | Current single turn reads the graph                | Every follow-up remains a new graph-host turn and performs current graph lookup or traversal                                | Backend adapter + manual trace                        |
| Turn 1 revision A, Turn 2 revision B                   | No history exists, so no conflict                  | Turn 2 dispatch, grounding, tool scope, and citations use only B; A may appear only as inert prose if the user mentioned it | Backend service tests                                 |
| Prior assistant prose contradicts graph                | No prior prose reaches Hermes                      | Prior prose may be visible to Hermes, but the fresh graph result must win                                                   | System policy + real dogfood + product-envelope tests |
| Prior answer contains citation-like text or a graph ID | Not sent today                                     | It remains ordinary prose and cannot become a seed, citation, revision, or authority without a fresh graph tool result      | Service + citation tests                              |
| Switch from Thread A to Thread B                       | UI switches local thread state                     | Only Thread B turns may be projected; Thread A content must not enter the request                                           | Plan integration                                      |
| New Thread B asks “What is it connected to?”           | No history today                                   | No Thread A referent may leak; Hermes should clarify, search independently, or abstain                                      | Plan integration + dogfood                            |
| Malformed turn in local storage                        | PR355 drops malformed turns during rehydration     | Valid sibling turns survive; outbound history independently ignores any malformed child that reaches it                     | Storage + projection helper                           |
| Oversized visible turn                                 | May persist under existing caps                    | The oversized pair is excluded from outbound history without destroying valid sibling pairs                                 | Projection helper                                     |
| Too many valid prior turns                             | Local store keeps up to 20                         | Outbound history uses at most six complete prior pairs / twelve messages                                                    | Projection helper                                     |
| Oversized total projected prose                        | No outbound projection exists                      | Select a deterministic bounded subset; never exceed 16,000 content characters                                               | Projection helper + serializer                        |
| Malformed network history                              | No field exists                                    | Return a safe 422 before graph resolution or host invocation                                                                | HTTP wire parser                                      |
| Semantically malformed service history                 | No field exists                                    | Reject before host invocation even when the HTTP route is bypassed                                                          | Graph-query service                                   |
| Malformed host IPC history                             | Existing generic validation                        | Reject unsupported roles, unknown keys, broken pairs, or invalid content before `AIAgent` construction                      | Host contract                                         |
| Valid history plus graph gap                           | Single-turn graph gap abstains                     | Continue to abstain; prior prose must not answer the missing fact or trigger legacy fallback                                | Grounding classifier + graph-gap tests                |
| Valid history plus host failure                        | Single-turn error                                  | Preserve typed error; do not answer from prior prose                                                                        | Backend                                               |
| Trace contains IDs and events                          | Trace is observability                             | Trace remains non-authoritative and is never copied into conversation history                                               | Projection + response review                          |
| Prior graph citations exist                            | Stored separately on each turn                     | Do not copy citations, anchors, revision, focus, or scope into history                                                      | Projection helper                                     |
| Prior legacy path citations exist                      | Stored on Live turns                               | Do not copy paths, excerpts, or legacy evidence metadata into Hermes history                                                | Projection helper                                     |
| Source body has been opened                            | Component-only state                               | Never enter history, request persistence, or Hermes transcript                                                              | Plan + serialization                                  |
| Completed-turn persistence                             | Stores visible sanitized turn state                | Continue storing existing Q/A and evidence presentation only; do not persist a separate transcript or session pointer       | Existing storage                                      |
| Reload shows old turns                                 | Rung 4C behavior                                   | Preserve display. Rung 5 adds no promise of Hermes internal session resume                                                  | Regression tests                                      |
| Follow-up after reload                                 | Existing visible turns may be present locally      | Any request remains a fresh host turn using bounded visible prose, not a resumed Hermes session                             | Serializer + no-session proof                         |
| Live backend selected                                  | Legacy Live request flow                           | Continue unchanged; do not send or consume Hermes conversation history                                                      | API + backend sibling tests                           |
| Source-bundle failure                                  | Does not block PR355 graph interaction             | Continue not to block Hermes continuity                                                                                     | Plan regression                                       |
| Backend selector                                       | Remains user-visible                               | Do not remove it or change its default                                                                                      | Diff review                                           |

### Critical acceptance journey

```text
Turn 1:
“What do we know about Tripod Null-Calf at the North Gate?”

Turn 2:
“What is it connected to that should affect my prep?”
```

For Turn 2, all of the following must be independently true:

1. “It” resolves to Tripod Null-Calf from prior visible prose.
2. Hermes performs a fresh graph search, exact lookup, or traversal.
3. The dispatched graph scope is taken from Turn 2’s resolved request.
4. Turn 2’s revision is not copied from Turn 1.
5. Turn 2’s factual claims follow current graph results rather than prior assistant prose.
6. Turn 2 emits only citations admitted by Turn 2’s accepted tool events.
7. Turn 1 source anchors do not automatically carry forward.
8. No Hermes session pointer is sent.
9. No internal Hermes transcript is loaded or saved.
10. A graph gap still abstains.

---

## §4 Files in scope — implementation allowlist

The handoff and authority documents are already part of the docs-only implementation base. The coding agent must not edit them in PR356.

### Backend request, service, and host-wire boundaries

| Action | Path                                                               | Purpose                                                                                                                            |
| ------ | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| Modify | `apps/live_control_server/routes/live.py`                          | Add and independently validate the optional HTTP `conversation_history` field; reject invalid or Live-backend use before execution |
| Modify | `apps/live_control_server/services/live_agent_loop.py`             | Carry only validated Hermes history into the graph-query adapter; preserve the legacy Live sibling path                            |
| Modify | `apps/live_control_server/services/hermes_graph_query.py`          | Independently normalize history, attach it to the current host request, and preserve current-turn graph authority                  |
| Modify | `apps/live_control_server/services/hermes_graph_agent_contract.py` | Harden the existing host IPC history contract around exact roles, exact keys, complete pairs, and bounded content                  |
| Modify | `tests/test_live_query_hermes_graph.py`                            | Prove current-revision authority, contradiction resistance, graph-gap abstention, no citation carryover, and host-call behavior    |
| Modify | `tests/test_live_control_server.py`                                | Prove HTTP wire parsing, typed 422 outcomes, Live sibling isolation, and no host invocation on invalid input                       |
| Modify | `tests/test_hermes_graph_agent.py`                                 | Prove the embedded agent receives exact chronological history while its system policy preserves graph authority                    |
| Modify | `tests/test_hermes_graph_agent_host.py`                            | Prove IPC round trip, bounds, role restrictions, pair ordering, and malformed-history rejection                                    |

### Frontend projection, serialization, and existing Plan integration

| Action | Path                                                                              | Purpose                                                                                                  |
| ------ | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Modify | `apps/live-control-ui/src/api/types.ts`                                           | Add the narrow role/content history type and request option                                              |
| Modify | `apps/live-control-ui/src/api/liveApi.ts`                                         | Independently sanitize and serialize history for Hermes only, using a fresh object with no raw overlay   |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts`                                    | Own exact outbound request-shape, omission, bounds, and forbidden-field proof                            |
| Create | `apps/live-control-ui/src/agentInteraction/hermesConversationHistory.ts`          | Project bounded complete role/content pairs from untrusted active-thread turns                           |
| Create | `apps/live-control-ui/src/agentInteraction/hermesConversationHistory.test.ts`     | Own projection order, caps, sibling preservation, poison-field exclusion, and malformed-input behavior   |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`     | Build history from the exact active thread at submit time and pass it only to Hermes requests            |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx`                  | Prove complete first-turn/second-turn, thread isolation, persistence/reload, and request-body journeys   |
| Modify | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts` | Extend adversarial rehydration proof so malformed stored children cannot contaminate outbound continuity |

**Expected implementation diff:** 16 paths.

No CSS change should be necessary. This is behavioral continuity through the existing UI.

If a required production change cannot be completed within this allowlist, stop and report the missing owning boundary. Do not silently add a nearby provider, storage, graph, or runtime file.

---

## §5 Explicitly out of scope — denylist

### Authority and historical documents

The implementation agent must not modify:

* `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
* `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
* `Docs/Design/ANCHOR-agent-interaction-hermes.md`
* `Docs/Design/UX-STORIES-agent-interaction-hermes.md`
* this handoff

Those paths belong to the dispatch base and later atomic post-merge synchronization.

### Runtime and graph implementation

Inspection is allowed; modification is not:

* `apps/live_control_server/services/hermes_graph_agent.py`
* `apps/live_control_server/services/hermes_graph_agent_host.py`
* `apps/live_control_server/services/agent_world_graph_query_context.py`
* `apps/live_control_server/routes/world_graph_retrieval.py`
* `apps/live_control_server/services/world_graph_retrieval.py`
* `src/graph_memory/retrieval/**`
* `src/graph_memory/kernel/**`
* `src/graph_memory/hermes_graph_plugin.py`
* `integrations/hermes/**`
* `.hermes.md`

The existing runtime already accepts caller-owned history and already contains the correct factual-authority policy. Modify it only after stopping and proving that this declared seam is materially false.

### Frontend state and persistence

Do not add or modify:

* a Hermes session field;
* a separate conversation transcript in local storage;
* server-side thread persistence;
* a new provider or app-wide context;
* cross-device synchronization;
* a new chat surface;
* new citation or trace UI;
* automatic history editing or summarization;
* hidden system-message persistence.

`AgentInteractionProvider.tsx` and production `agentInteractionHistory.ts` should remain unchanged unless a demonstrated owning-boundary defect makes the handoff impossible. Existing sanitized Q/A turns are the source; this PR adds an outbound projection, not a new store.

### Product behavior

Do not implement:

* Hermes session IDs in request or response;
* durable thread-to-session binding;
* reuse of a host-side Hermes transcript;
* process-restart continuation;
* server-side transcript replay;
* automatic graph-head polling;
* historical-revision browsing;
* graph writes;
* authored-prep drafts;
* preview or confirm flows;
* Play continuity;
* backend-selector removal;
* default-backend changes;
* obsolete-path demolition;
* manifest, corpus, lexical, arbitrary-Markdown, or Live-synthesis fallback.

### Forbidden shortcuts

* Do not send complete `AgentInteractionTurn` objects.
* Do not spread a raw turn into a history message.
* Do not send turn IDs, timestamps, status, backend, model, trace, diagnostics, warnings, grounding, revisions, graph context, citations, source anchors, source bodies, paths, evidence snapshots, raw tool arguments, or UI state.
* Do not send hidden system messages from the browser.
* Do not send the current question twice; it remains the top-level `text`.
* Do not derive `seedNodeIds` from prior prose.
* Do not copy a prior source anchor into a new citation.
* Do not reuse Turn 1’s graph revision for Turn 2 because it appeared in local state.
* Do not let assistant prose bypass graph retrieval.
* Do not classify grounding from history or trace.
* Do not use a sanitized projection and then overlay raw wire values afterward.
* Do not merge histories from multiple threads.
* Do not select history by campaign alone when a specific active thread exists.
* Do not convert malformed history into an unbounded prompt string.
* Do not persist the outbound `conversation_history` payload as a second transcript.
* Do not add a compatibility fallback when history is invalid.
* Do not treat a mocked agent response as complete manual dogfood.

---

## §6 Contract specification

### §6A — Product history schema

The HTTP request gains one optional field for Hermes requests:

```json
{
  "conversation_history": [
    {
      "role": "user",
      "content": "What do we know about Tripod Null-Calf at the North Gate?"
    },
    {
      "role": "assistant",
      "content": "Tripod Null-Calf is a siege scout associated with the North Gate..."
    }
  ]
}
```

Canonical message type:

```text
role: exactly "user" or "assistant"
content: a non-empty string after trimming
```

Canonical sequence:

```text
[user, assistant, user, assistant, ...]
```

History must consist only of complete prior Q/A pairs.

Stable product bounds:

```text
Maximum prior turn pairs:       6
Maximum messages:              12
Maximum characters per message: 4,000
Maximum total content characters: 16,000
```

The limits count string characters after outer whitespace trimming.

Allowed empty forms:

```text
field absent
field null
empty array
```

They all mean no prior conversation history.

The Hermes serializer should omit the field entirely when the normalized projection is empty.

### §6B — Browser projection from untrusted turns

Create:

```ts
buildHermesConversationHistory(turns: unknown): HermesConversationHistoryMessage[]
```

The function owns one trust boundary. TypeScript annotations do not make its input trusted.

Input order is the repository’s existing thread order:

```text
newest turn first
```

Required algorithm:

1. If `turns` is not an array, return `[]`.
2. Examine entries independently.
3. A valid entry is a non-array object containing:

   * a non-empty string `question`;
   * a non-empty string `answer`.
4. Ignore every other property.
5. Trim outer whitespace from question and answer.
6. If either string exceeds 4,000 characters, drop that complete pair.
7. Never emit half a pair.
8. Continue examining siblings after a malformed or oversized pair.
9. Select no more than six valid pairs.
10. Never let selected content exceed 16,000 total characters.
11. When a pair would exceed the remaining total budget, skip that pair and continue examining older siblings that may fit.
12. After selection, reverse the selected pairs into chronological order.
13. Flatten each pair as:

    * `{ role: "user", content: question }`
    * `{ role: "assistant", content: answer }`
14. Return newly constructed objects.
15. Never mutate the source turns.

Example:

```text
Stored turns:     newest T3, T2, oldest T1
Outbound history: T1 user, T1 assistant, T2 user, T2 assistant, T3 user, T3 assistant
```

The helper must not inspect whether prior prose was grounded. Grounded, partial, abstained, and error answers are all visible prose, not factual authority. The current turn’s graph retrieval remains responsible for truth.

### §6C — Serializer boundary

`postLiveQuery` must treat `options.conversationHistory` as `unknown` again.

Add an independent outbound normalizer. It may share constants and types with the projection helper, but it must not trust the caller merely because the Plan component used that helper.

The serializer must:

* accept only complete alternating user/assistant pairs;
* drop malformed pairs without dropping valid siblings;
* reapply all product bounds;
* construct a new array of new `{role, content}` objects;
* omit `conversation_history` if no valid pair survives;
* include it only when `queryBackend === "hermes"`;
* never include it in a Live request;
* never spread a raw history message into the request;
* never overlay raw options after constructing the sanitized body.

Canonical Hermes body keys after this PR:

```text
campaign_id
session
mode
query_backend
text
agent_thread_id
trace_requested
optional world_graph_context
optional conversation_history
```

Still forbidden:

```text
manifest_path
hermes_session_id
session_id
hermes transcript
source bodies
trace
citations
graph metadata copied from prior turns
```

The Live request branch remains unchanged except that a supplied Hermes-history option is ignored and never serialized.

### §6D — Plan submit boundary

At submit time:

1. Resolve or create `currentThread` exactly as today.
2. For Hermes only, call the history projection with `currentThread.turns`.
3. Do not use the component’s broad `turns` value if it can differ from `currentThread.turns`.
4. Do not use `threadSummaries`.
5. Do not use `turnResponses`.
6. Do not use raw response objects.
7. Do not include the new question in history.
8. Pass the projection through `LiveQueryOptions.conversationHistory`.
9. Submit the current question through the existing top-level `text`.
10. Preserve the current graph-context request behavior.
11. Preserve existing response construction, sanitization, rendering, and persistence.

Thread switching must naturally change the source collection because the active `currentThread` changes. There must be no global history cache.

### §6E — HTTP wire boundary

The HTTP field is untrusted JSON.

The route must independently validate before calling `process_live_query`.

A suitable shape is:

```py
conversation_history: Any | None = None
```

followed by a route-owned parser that constructs a fresh normalized list.

Do not rely solely on a Pydantic annotation such as `list[HistoryMessage]` and then treat the resulting children as authoritative. The route parser must explicitly establish:

* list or null;
* maximum twelve messages;
* exact child keys `role` and `content`;
* no unknown child keys;
* exact roles `user` and `assistant`;
* alternating complete pairs;
* non-empty trimmed string content;
* 4,000-character per-message cap;
* 16,000-character total cap.

Invalid Hermes wire history returns HTTP 422 with the existing typed validation envelope:

```json
{
  "schema": "dmb_live_query_validation_error_v1",
  "code": "hermes_history_invalid",
  "message": "<bounded diagnostic>",
  "statusCode": 422,
  "diagnostics": [
    {
      "code": "hermes_history_invalid",
      "message": "<bounded diagnostic>",
      "severity": "error"
    }
  ]
}
```

Do not echo invalid content in the error.

For `query_backend != "hermes"`:

* absent, null, or empty history is harmless;
* a non-empty history payload returns 422 with code:

```text
conversation_history_not_supported
```

No Live classification, mutation, context lookup, or other backend path may run after this rejection.

### §6F — Service boundary

`process_live_query` gains an optional history argument and forwards it only through the `query_backend == "hermes"` branch.

`hermes_graph_query.py` must own an independent service normalizer:

```py
normalize_hermes_conversation_history(value: Any) -> list[dict[str, str]] | None
```

It must repeat the semantic checks in §6E rather than assuming the route was used.

Direct callers, tests, alternate routes, or future internal integrations must not bypass the invariant.

On service-validation failure:

* raise `HermesGraphQueryRequestError`;
* use code `hermes_history_invalid`;
* do not resolve graph context;
* do not construct the host;
* do not invoke `host.execute`;
* do not run a fallback.

`build_hermes_graph_turn_request` must accept only the normalized history and construct:

```py
HermesGraphAgentTurnRequest(
    question=current_question,
    world_id=current_scope.world_id,
    campaign_id=current_scope.campaign_id,
    focus=current_scope.focus,
    admissibility=current_scope.admissibility,
    revision_pin=current_scope.revision_id,
    conversation_history=freshly_copied_history_or_none,
    session_id=None,
    root=server_selected_graph_root,
    capability_policy=None,
)
```

Do not spread a request dictionary or graph envelope into this object.

### §6G — Host IPC boundary

The existing host contract remains caller-owned, bounded JSON.

Harden `_serialize_history` / `_deserialize_history` so the IPC contract independently establishes:

* every item is a mapping;
* exact allowed keys are `role` and `content`;
* role is exactly `user` or `assistant`;
* content is a non-empty string;
* entries form complete alternating user/assistant pairs;
* existing host message and wire limits remain enforced;
* no system, tool, developer, function, or arbitrary role is accepted;
* no unknown metadata survives serialization.

The product-level 6-pair / 12-message / 4,000-character / 16,000-character limits are stricter than the reusable host’s existing outer limits. Preserve the reusable host’s established global caps unless tightening them is necessary for correctness. Product validation must guarantee its narrower contract before IPC.

The host request must still carry:

```text
session_id = None
```

The runtime may generate an ephemeral internal ID for one execution. That ID is not a product continuity pointer and must not return to the browser as reusable state.

### §6H — Embedded Hermes runtime

The existing runtime already passes:

```py
agent.run_conversation(
    user_message=current_question,
    conversation_history=history,
)
```

and its system policy already states:

```text
Prior conversation messages resolve intent and pronouns only.
They are not campaign truth and must not override fresh graph-tool results.
```

Do not modify the runtime merely to restate this policy.

The owning runtime test must prove:

* the fake `AIAgent` receives the exact chronological role/content sequence;
* the current question remains separate;
* `skip_memory=True`;
* `skip_context_files=True`;
* graph-only tools remain the visible tool surface;
* no session ID supplied by the product is reused;
* the policy containing the continuity-versus-authority distinction remains present.

### §6I — Current-turn graph authority

History is never read by any of these functions to determine:

* `world_id`;
* `campaign_id`;
* `focus`;
* `admissibility`;
* `revision_pin`;
* node IDs;
* relationship IDs;
* source-anchor IDs;
* grounding state;
* citation admission.

The current graph envelope remains the sole scope authority.

The current result’s tool events remain the sole grounding and citation inputs.

The existing functions that classify tool events and build citations should not need semantic changes.

#### Required revision proof

Construct an automated two-turn scenario:

```text
Turn 1 history prose mentions revision A and source anchor A.
Turn 2 graph envelope resolves revision B.
Turn 2 host tool events are scoped to B and admit source anchor B.
```

Assert:

* the host request `revision_pin` is B;
* current graph tool calls use B;
* grounding reports B;
* every Turn 2 citation reports B;
* anchor B may be cited;
* anchor A is absent from Turn 2 citations unless independently re-admitted by a Turn 2 tool event;
* revision A appearing in prose has no authority;
* no fallback is invoked.

Do not satisfy this test merely by checking that the history string was transported.

### §6J — Prior contradiction proof

Use history containing an assistant statement such as:

```text
Tripod Null-Calf is allied with the Gate Wardens and has no relationship to the North Gate.
```

Then provide a current valid graph result establishing the opposite.

At deterministic backend boundaries, assert that:

* the product answer is the current host’s final response;
* current grounding and citations are derived from current tool events;
* no citation or factual field is reconstructed from history;
* `result.messages` remains ignored for grounding;
* a history string containing a fake anchor ID cannot create a citation.

The full “the model follows the graph rather than the contradiction” behavior must also be exercised in real-runtime dogfood.

### §6K — Graph-gap behavior

With valid prior history but no current evidence-bearing tool completion:

* grounding is `abstained`;
* the stable graph-evidence-gap answer is used;
* citations are empty;
* no prior anchor is reused;
* no prior prose is promoted into a factual answer;
* no manifest, corpus, lexical, arbitrary Markdown, CLI, or Live fallback runs.

A history-bearing graph gap is a required regression test, not an inferred consequence.

### §6L — Persistence and reload boundary

Do not add a new persistent field for:

* `conversation_history`;
* Hermes messages;
* Hermes session pointer;
* host transcript;
* model context;
* system prompt.

The existing sanitized local turns remain the only prose source.

Outbound history is reconstructed on demand from visible sanitized turns.

The complete serialized local-storage object must not contain:

```text
hermes_session_id
conversation_history
RAW_HERMES_TRANSCRIPT_SECRET
RAW_SYSTEM_MESSAGE_SECRET
RAW_SOURCE_BODY_SECRET
RAW_TOOL_ARGUMENT_SECRET
```

Existing turn fields such as sanitized `question`, `answer`, grounding, citations, and safe trace remain governed by PR355. Do not remove them.

A follow-up after browser reload, when visible persisted turns are projected, is still a fresh stateless host turn. It is not evidence that a Hermes session resumed. Rung 5 must not add tests or UI language claiming resumed Hermes internal state.

### §6M — Failure matrix

| Condition                                  | Required result                                         |      Host invoked? | Fallback? |
| ------------------------------------------ | ------------------------------------------------------- | -----------------: | --------: |
| History absent                             | Existing independent Hermes turn                        |                Yes |        No |
| Empty normalized history                   | Existing independent Hermes turn; field omitted         |                Yes |        No |
| One valid prior pair                       | Fresh Hermes turn with two history messages             |                Yes |        No |
| Six valid prior pairs                      | Fresh Hermes turn with twelve history messages          |                Yes |        No |
| Seventh valid pair                         | Oldest/excess pair excluded deterministically by client |                Yes |        No |
| Malformed local child among valid siblings | Malformed pair dropped; valid siblings survive          |                Yes |        No |
| Oversized local pair among valid siblings  | Oversized pair dropped; valid siblings survive          |                Yes |        No |
| Invalid network collection                 | Typed 422                                               |                 No |        No |
| Unknown child key on network               | Typed 422                                               |                 No |        No |
| `system` or `tool` role                    | Typed 422                                               |                 No |        No |
| Odd message count                          | Typed 422                                               |                 No |        No |
| Wrong pair order                           | Typed 422                                               |                 No |        No |
| Per-message cap exceeded                   | Typed 422                                               |                 No |        No |
| Total cap exceeded                         | Typed 422                                               |                 No |        No |
| Non-empty history on Live backend          | Typed 422                                               |                 No |        No |
| Current graph unavailable                  | Existing typed unavailable response                     | No graph host call |        No |
| Current graph gap with valid history       | Existing abstention                                     |                Yes |        No |
| Host execution failure                     | Existing Hermes graph error                             |     Attempted once |        No |
| Prior revision differs from current        | Current revision wins                                   |                Yes |        No |
| Prior assistant contradicts current graph  | Current graph/host result wins                          |                Yes |        No |
| Thread A history while Thread B active     | Must never be serialized                                |  Normal B behavior |        No |

---

## §7 Verification plan

Run every applicable command from the implementation base and at final head. Report exact counts and provenance. Do not rely on claims in the PR description.

### V1 — Backend product adapter, current-turn authority, and grounding regression

```bash
uv run pytest tests/test_live_query_hermes_graph.py -q
```

This suite must own:

* no-history independent turn;
* exact valid history on the host request;
* history copied into a fresh list;
* `session_id is None`;
* current graph scope is not derived from history;
* revision A history versus revision B request;
* current-turn citation admission only;
* fake anchor IDs in prose create no citation;
* contradictory assistant prose creates no product authority;
* valid-history graph gap still abstains;
* invalid service history fails before host construction/execution;
* host executes exactly once for a valid turn;
* no legacy fallback.

### V2 — HTTP route and sibling-backend ownership

```bash
uv run pytest tests/test_live_control_server.py -q
```

This suite must own:

* exact accepted HTTP history shape;
* absent/null/empty behavior;
* non-array rejection;
* malformed child rejection;
* unknown child-key rejection;
* unsupported-role rejection;
* incomplete-pair rejection;
* order rejection;
* per-message cap;
* message-count cap;
* total-content cap;
* bounded error text that does not echo payload content;
* invalid history never reaches `process_live_query` or the host;
* non-empty history on Live returns `conversation_history_not_supported`;
* normal Live requests remain unchanged;
* normal Hermes validation errors retain the existing typed envelope.

### V3 — Host IPC and embedded runtime

```bash
uv run pytest tests/test_hermes_graph_agent.py tests/test_hermes_graph_agent_host.py -q
```

This suite must own:

* exact IPC round trip;
* exact allowed message keys;
* user/assistant roles only;
* complete alternating pairs;
* malformed and unknown child rejection;
* existing outer host bounds;
* chronological history received by the fake agent;
* current question separate from history;
* graph-only tool policy unchanged;
* memory and context files disabled;
* no durable session pointer introduced.

### V4 — Python static verification

```bash
uv run ruff check \
  apps/live_control_server/routes/live.py \
  apps/live_control_server/services/live_agent_loop.py \
  apps/live_control_server/services/hermes_graph_query.py \
  apps/live_control_server/services/hermes_graph_agent_contract.py \
  tests/test_live_query_hermes_graph.py \
  tests/test_live_control_server.py \
  tests/test_hermes_graph_agent.py \
  tests/test_hermes_graph_agent_host.py
```

### V5 — Frontend history projection and serializer

```bash
cd apps/live-control-ui && npm test -- \
  src/agentInteraction/hermesConversationHistory.test.ts \
  src/api/liveApi.test.ts
```

This suite must own:

* newest-first turns become chronological messages;
* exact user/assistant pair construction;
* no half pairs;
* six-pair/twelve-message cap;
* 4,000-character message cap;
* 16,000-character total cap;
* deterministic selection when a large pair does not fit;
* malformed pair dropped while valid siblings survive;
* nulls, primitives, arrays, and unexpected objects ignored safely;
* poison fields ignored;
* first Hermes turn omits history;
* follow-up Hermes turn includes exact normalized history;
* Live request never includes history;
* no `manifest_path`;
* no `hermes_session_id`;
* no trace, citation, path, revision, source body, raw args, or arbitrary properties;
* no sanitized-object bypass through raw spread or overlay.

### V6 — Complete Plan submit, thread isolation, persistence, and reload journey

```bash
cd apps/live-control-ui && npm test -- \
  src/planSurface/components/agentInteractionHistory.test.ts \
  src/planSurface/PlanSurfaceShell.test.tsx
```

This suite must prove the full boundary, not merely helper output:

1. Submit Turn 1.
2. Render and persist the response.
3. Submit Turn 2 in the same active thread.
4. Inspect the actual serialized `fetch` body.
5. Confirm only Turn 1’s role/content pair is present.
6. Confirm Turn 2’s current graph context is separately serialized.
7. Switch to Thread B.
8. Confirm Thread A prose is absent.
9. Seed local storage with:

   * one valid turn;
   * one malformed child;
   * one turn containing poison metadata.
10. Reload through the real provider/surface path.
11. Confirm the valid sibling still renders.
12. Submit a follow-up.
13. Confirm only valid role/content enters the request.
14. Serialize the stored thread and confirm no new transcript/session field exists.
15. Confirm the response still travels through the existing sanitize → render → persist path.
16. Confirm source-bundle failure does not block the request.
17. Confirm legacy Live behavior remains intact.

### V7 — Graph-context and source-anchor sibling regression

```bash
uv run pytest \
  tests/test_agent_world_graph_query_context.py \
  tests/test_world_graph_retrieval_routes.py \
  -q
```

This proves Rung 5 did not alter:

* graph-context resolution;
* current revision selection;
* retrieval operations;
* source-anchor admission or reading;
* graph-gap outcomes;
* scope/admissibility behavior.

### V8 — Full frontend regression and build comparison

```bash
cd apps/live-control-ui && npm test
cd apps/live-control-ui && npm run build
```

Run these on the implementation base and head.

If the base already fails:

* record the exact base failure set;
* record the exact head failure set;
* prove no new failure belongs to an allowed PR356 path;
* do not call a changed failure “pre-existing” merely because the command still exits nonzero.

### V9 — Diff hygiene and allowlist

```bash
git diff --check
git diff --name-only <implementation-base>...HEAD
git diff --stat <implementation-base>...HEAD
```

The changed paths must match §4 exactly, except that a listed `Create` path may be absent if the agent instead proves an existing owning helper is the correct home and stops for re-anchoring before changing it. Silent substitutions are not allowed.

### Serialized no-leak assertions

At each of these boundaries—

* browser projection;
* serialized HTTP request;
* backend host request;
* product response;
* local-storage thread—

inject distinctive poison values and serialize the complete object.

At minimum use:

```text
RAW_TRACE_SECRET
RAW_CITATION_SECRET
RAW_SOURCE_BODY_SECRET
RAW_TOOL_ARGUMENT_SECRET
RAW_HERMES_TRANSCRIPT_SECRET
RAW_SYSTEM_MESSAGE_SECRET
/foreign/absolute/path.md
FOREIGN_REVISION_A
FOREIGN_REVISION_B
FOREIGN_SOURCE_ANCHOR_A
FOREIGN_SOURCE_ANCHOR_B
FOREIGN_THREAD_A
FOREIGN_THREAD_B
```

Assert each forbidden value is absent from every boundary where it does not belong.

Checking only visible DOM text is insufficient. Checking only the helper’s return value is insufficient. Inspect complete serialized request and persistence objects.

---

## §7A Manual dogfood that can begin immediately

The operator can run the current merged Rung 4C product before PR356 implementation to prove the real Hermes environment is available.

This is environment validation, not Rung 5 acceptance.

### Baseline real-agent smoke

1. Start the repository-supported live-control server and Plan UI with the real model/provider credentials.

2. Open the published Eldyrwild Campaign 2 Plan surface.

3. Open **Ask prep memory**.

4. Select **Hermes tools**.

5. Turn Trace On.

6. Ask:

   ```text
   What do we know about Tripod Null-Calf at the North Gate?
   ```

7. Confirm:

   * the response mode is `hermes_graph_agent`;
   * a graph tool actually ran;
   * the answer is grounded or qualified according to the returned evidence;
   * citation and grounding revision agree;
   * evidence opens through the opaque graph-anchor route;
   * no legacy path fallback runs.

8. Ask a known graph-gap question.

9. Confirm abstention and no fallback.

Record:

```text
Baseline real-agent environment: PASS / BLOCKED
Actor:
Environment:
Date/time:
Provider/model:
Observed graph revision:
Observed trace ID:
Notes:
```

A successful baseline means PR356’s manual acceptance can use the actual agent immediately after checkout.

---

## §7B Manual Rung 5 acceptance gate

Run on the final PR head using the existing Plan surface. Do not build a diagnostic page.

### Journey 1 — primary same-thread object continuity

1. Create a new Plan thread.

2. Select **Hermes tools**.

3. Turn Trace On.

4. Ask exactly:

   ```text
   What do we know about Tripod Null-Calf at the North Gate?
   ```

5. Record:

   * answer;
   * grounding state;
   * graph revision;
   * matched node IDs;
   * relevant edge IDs;
   * source-anchor IDs;
   * trace ID.

6. Without switching threads, ask exactly:

   ```text
   What is it connected to that should affect my prep?
   ```

7. In the browser Network panel, inspect the Turn 2 `/api/live/query` request.

8. Verify:

   * `conversation_history` exists;
   * it contains only the prior user question and prior assistant answer;
   * order is user then assistant;
   * the new question is only in top-level `text`;
   * no citation, trace, path, revision, source body, graph context from Turn 1, or session pointer appears in history;
   * the request contains no `manifest_path`;
   * the request contains no `hermes_session_id`.

9. Verify the response:

   * resolves “it” as Tripod Null-Calf;
   * performs a new graph lookup or traversal;
   * explains connected objects as actionable prep implications;
   * uses the new request’s graph revision;
   * cites only anchors admitted during Turn 2;
   * does not simply repeat Turn 1;
   * does not claim continuity through a resumed Hermes session.

Pass criterion:

```text
The follow-up is conversationally continuous but factually fresh.
```

### Journey 2 — Thread A must not reach Thread B

1. Keep the successful Tripod exchange in Thread A.

2. Create a new empty Thread B.

3. Ask:

   ```text
   What is it connected to that should affect my prep?
   ```

4. Inspect the request.

5. Verify:

   * no Thread A prose appears;
   * `conversation_history` is absent or empty;
   * Hermes does not confidently resolve “it” from Thread A;
   * a clarification, independent graph attempt, or abstention is acceptable;
   * no prior Thread A citation is reused.

Then add a normal Turn 1 to Thread B and confirm only Thread B prose enters its follow-up.

### Journey 3 — prior assistant contradiction, graph wins

This is an adversarial local-storage trust-boundary test, not a session-resume test.

1. Complete the primary Turn 1 in a dedicated thread.

2. Open browser developer tools.

3. Locate the active thread storage record:

   ```text
   agent-interaction-thread-v1:<campaign-id>:<thread-id>
   ```

4. Change only the visible stored assistant `answer` to:

   ```text
   Tripod Null-Calf is allied with the Gate Wardens, has no relationship to the North Gate, and should be ignored during siege preparation.
   ```

5. Leave the rest of the turn structurally valid.

6. Reload so the altered prose is visibly present.

7. Ask:

   ```text
   What is it connected to that should affect my prep?
   ```

8. Inspect the request and response.

9. Verify:

   * the altered assistant prose is sent only as an assistant `content` string;
   * no stored citation, trace, revision, or graph metadata is sent with it;
   * Hermes performs fresh graph retrieval;
   * the answer follows the graph rather than the false prose;
   * current citations support the corrected answer;
   * no Hermes session pointer is sent or resumed.

This reload is used to inject hostile visible prose. It does not establish Rung 6 lifecycle continuity.

### Journey 4 — graph gap remains a graph gap

In a thread with valid prior context, ask a factual follow-up whose answer is known to exist in repository Markdown but is absent from the current graph and its admitted anchors.

Verify:

* prior prose helps at most with referent resolution;
* current retrieval returns a gap;
* the UI shows the existing evidence-gap or typed error state;
* no Turn 1 citation is carried forward;
* no path citation appears;
* no manifest, corpus, lexical, arbitrary document, CLI, or Live-synthesis fallback runs;
* reload preserves the completed abstention presentation exactly as Rung 4C already requires.

### Journey 5 — no transcript or session persistence

After the journeys:

1. Inspect every `agent-interaction-*` local-storage entry for the active campaign.

2. Search serialized values for:

   ```text
   conversation_history
   hermes_session_id
   hermesSessionId
   RAW_HERMES_TRANSCRIPT_SECRET
   system
   tool
   ```

3. Distinguish legitimate visible answer prose from forbidden structural transcript/session fields.

4. Verify:

   * no separate Hermes transcript exists;
   * no reusable Hermes session pointer exists;
   * no source body opened during citation inspection was persisted;
   * outbound history is reconstructed from visible Q/A rather than saved separately.

### Journey 6 — revision A to B, when a safe two-revision environment exists

Do not publish or mutate a production graph merely to satisfy this manual proof.

When an existing test/dogfood environment safely exposes revision A and revision B:

1. Ask Turn 1 while A is the request’s resolved revision.
2. Advance or select the environment’s normal head B through its supported mechanism.
3. Refresh the Plan graph context through the existing product behavior.
4. Ask Turn 2 in the same thread.
5. Verify:

   * history still contains only Turn 1 prose;
   * Turn 2 graph tools use B;
   * grounding reports B;
   * citations report B;
   * no A anchor survives unless re-admitted at B.

If no safe environment exists, record:

```text
Manual revision A→B: NOT RUN — no safe mutable/two-revision dogfood environment.
Automated owning-boundary proof: PASS / FAIL, with test name.
```

This conditional manual scenario does not waive the mandatory automated A/B proof.

### Manual dogfood handback

Record each journey separately:

| Journey                           | Result                   | Actor | Environment | Date/time | Evidence |
| --------------------------------- | ------------------------ | ----- | ----------- | --------- | -------- |
| Baseline real agent               | PASS / BLOCKED           |       |             |           |          |
| Primary same-thread follow-up     | PASS / BLOCKED           |       |             |           |          |
| Thread isolation                  | PASS / BLOCKED           |       |             |           |          |
| Contradictory prior prose         | PASS / BLOCKED           |       |             |           |          |
| Graph gap                         | PASS / BLOCKED           |       |             |           |          |
| No transcript/session persistence | PASS / BLOCKED           |       |             |           |          |
| Revision A→B                      | PASS / NOT RUN / BLOCKED |       |             |           |          |

The implementation agent may open the PR when credentials are unavailable, but the primary journey, thread-isolation journey, contradiction journey, graph-gap journey, and persistence inspection must be run by an operator or reviewer before Rung 5 is accepted.

---

## §8 Required implementation handback

The worker should provide the following in the PR handback or an attached review artifact. The actual diff, tests, and dogfood remain authoritative; stale PR prose alone is not an acceptance blocker.

1. PR355 predecessor merge SHA.
2. Docs-only implementation-base SHA.
3. Final PR head SHA.
4. Actual changed paths.
5. Diff stat.
6. Exact browser history caps.
7. Exact HTTP field name and message schema.
8. Exact normalized Hermes request keys.
9. Exact behavior when no history survives.
10. Exact client projection ordering.
11. Exact network rejection codes.
12. Exact host IPC role/order restrictions.
13. Confirmation that `session_id=None` remains true.
14. Confirmation that no `hermes_session_id` is serialized.
15. Confirmation that no response field containing conversation history was added.
16. Confirmation that no separate transcript was persisted.
17. Confirmation that no server-side thread store was added.
18. Confirmation that current graph envelope remains the only scope/revision source.
19. Confirmation that current tool events remain the only grounding/citation source.
20. Name of the automated revision A→B test.
21. Name of the contradictory-prose test.
22. Name of the Thread A/Thread B isolation test.
23. Name of the valid-history graph-gap test.
24. Name of the malformed local-storage sibling-preservation test.
25. Complete serialized no-leak results.
26. Every V1–V9 command with exact outcome and provenance.
27. Base/head full-suite and build comparison.
28. Manual dogfood matrix.
29. CI/workflow checks attached to final head; write `none exposed` when none exist.
30. Baseline failures and waivers; write `none` when none exist.
31. Paths outside §4; write `none` or include the stop report.
32. Stop conditions encountered; write `none` when none exist.
33. Deviations from §6; write `none` when none exist.
34. Confirmation that Rung 6 has not begun.
35. Confirmation that Rung 7 has not begun.
36. Confirmation that PR011 remains blocked.
37. Confirmation that PR009 was not modified.
38. Confirmation that the selector and default backend remain unchanged.
39. Confirmation that no write-capable tool was added.
40. Confirmation that the complete handoff was implemented without silent reinterpretation.

Opening the pull request must be the final repository action on the implementation branch.

```text
STOP. REQUEST REVIEW. DO NOT BEGIN RUNG 6.
```

---

## §9 Acceptance rubric

The reviewer accepts only when every applicable item is proven by its owning boundary.

### Capability

* [ ] A second Hermes question in the same active Plan thread receives bounded prior visible role/content pairs.
* [ ] The primary Tripod Null-Calf follow-up resolves “it” correctly in real-runtime dogfood.
* [ ] Hermes performs fresh graph retrieval for the follow-up.
* [ ] The implementation is stateless bounded prose replay, not durable Hermes session continuity.

### Client trust boundaries

* [ ] Untrusted thread input is parsed rather than cast.
* [ ] Malformed or oversized pairs are dropped independently.
* [ ] Valid sibling pairs survive malformed siblings.
* [ ] Output is chronological and contains only complete user/assistant pairs.
* [ ] Product caps are enforced exactly.
* [ ] No raw turn object is spread or overlaid onto a sanitized message.
* [ ] API serialization independently normalizes its history input.
* [ ] History is serialized only for Hermes.
* [ ] Thread A never reaches Thread B.
* [ ] The current question is not duplicated in history.

### Wire and service trust boundaries

* [ ] The HTTP parser treats history as unknown.
* [ ] Unknown child keys and unsupported roles are rejected.
* [ ] Broken pair ordering is rejected.
* [ ] Message and total bounds are rejected before execution.
* [ ] Errors do not echo hostile content.
* [ ] Non-empty history is rejected on the Live backend.
* [ ] The graph-query service independently repeats semantic normalization.
* [ ] Invalid history cannot reach graph resolution or host execution.

### Host boundary

* [ ] IPC accepts only role/content.
* [ ] IPC accepts only user/assistant roles.
* [ ] IPC enforces complete alternating pairs.
* [ ] The fake embedded agent receives the exact chronological projection.
* [ ] Existing graph-only tools, memory disablement, and context-file disablement remain unchanged.
* [ ] No reusable product session pointer enters the host request.

### Factual authority

* [ ] Prior prose is used only for conversational identity.
* [ ] Current world, campaign, focus, admissibility, and revision come from the new graph envelope.
* [ ] Revision A prose cannot override revision B dispatch.
* [ ] Prior assistant contradiction cannot create grounding or citations.
* [ ] A fake anchor ID in prose cannot become a citation.
* [ ] Only current evidence-bearing tool events admit citations.
* [ ] Turn 1 citations are not automatically carried into Turn 2.
* [ ] Trace and Hermes result messages remain non-authoritative.
* [ ] A graph gap with valid history still abstains.
* [ ] No legacy fallback is introduced.

### Persistence and sibling flows

* [ ] No separate conversation-history payload is persisted.
* [ ] No Hermes transcript is persisted.
* [ ] No Hermes session pointer is persisted.
* [ ] No source body is persisted.
* [ ] Existing completed-turn reload display remains functional.
* [ ] A post-reload request is still a fresh host turn, not a claimed session resume.
* [ ] Legacy Live and path-citation flows remain isolated and functional.
* [ ] Source-bundle failure does not block Hermes.
* [ ] No graph retrieval, source-anchor, citation, or grounding contract regresses.

### Scope

* [ ] The changed paths match §4.
* [ ] No authority document is edited in the implementation PR.
* [ ] No runtime/host lifecycle file is changed.
* [ ] No server-side thread store is added.
* [ ] No new surface is added.
* [ ] No backend default or selector behavior changes.
* [ ] No demolition occurs.
* [ ] No write-capable tool is added.
* [ ] Rung 6, Rung 7, PR011, and PR009 remain separate.

### Proof

* [ ] V1–V9 are reported truthfully.
* [ ] Serialized no-leak assertions inspect complete objects.
* [ ] Base/head regressions are compared.
* [ ] Primary real-agent dogfood passes.
* [ ] Thread-isolation dogfood passes.
* [ ] Contradictory-prose dogfood passes.
* [ ] Graph-gap dogfood passes.
* [ ] Persistence inspection passes.
* [ ] Manual A/B is run when safely possible; automated A/B always passes.

---

## §10 Reviewer protocol

Review the trust boundaries in order. Do not infer one boundary’s correctness from another.

### 1. Establish the review base

1. Fetch the current PR head.
2. Confirm it descends from the recorded docs-only implementation base.
3. Confirm that base descends from PR355 merge `7671a633…`.
4. Compare changed paths with §4.
5. Ignore stale PR prose unless it conceals an actual code, safety, or scope discrepancy.

### 2. Review browser projection

1. Begin with `unknown`.
2. Trace malformed children.
3. Trace oversized children.
4. Trace valid siblings around malformed children.
5. Verify newest-first input becomes chronological output.
6. Verify no complete raw turn reaches the return value.
7. Search for every forbidden field.
8. Verify total-budget selection is deterministic.

### 3. Review API serialization

1. Call `postLiveQuery` directly with adversarial runtime values despite its TypeScript signature.
2. Inspect the exact `fetch` body.
3. Confirm independent normalization.
4. Confirm no later spread restores raw fields.
5. Confirm empty history is omitted.
6. Confirm Live serialization remains isolated.

### 4. Review active-thread selection

1. Trace current thread creation.
2. Trace a normal second submit.
3. Trace thread switching.
4. Trace new-thread creation.
5. Trace rehydration.
6. Confirm the projection source is the exact current thread.
7. Confirm `turnResponses`, summaries, and other threads cannot enter history.

### 5. Review HTTP parsing

1. Send primitives, objects, nested arrays, unknown keys, invalid roles, odd counts, wrong ordering, empty strings, oversized strings, too many messages, and total-overflow payloads.
2. Confirm bounded 422 errors.
3. Confirm no execution callback ran.
4. Confirm the Live sibling rejects non-empty history.

### 6. Review service normalization

1. Call service functions directly, bypassing FastAPI.
2. Repeat malformed cases.
3. Confirm new objects are constructed.
4. Confirm host construction/execution is impossible after failure.
5. Confirm no fallback branch exists.

### 7. Review current-turn authority

Use a finding ledger for:

```text
scope
revision
focus
admissibility
grounding
citations
graph gap
trace
persistence
thread isolation
session exclusion
```

For revision A/B:

1. Put A and a fake anchor in history.
2. Dispatch B.
3. Return B-scoped evidence.
4. Inspect the complete product envelope.
5. Search for A and the fake anchor in authoritative fields.
6. They must be absent.

### 8. Review host IPC and runtime

1. Verify the IPC serializer, decoder, and deserializer separately.
2. Verify role semantics, not only mapping shapes.
3. Verify complete pairs.
4. Verify the current question remains separate.
5. Verify the agent policy preserves the continuity/authority distinction.
6. Verify no session pointer is supplied.

### 9. Review persistence

1. Follow a turn through submit → response construction → rendering → persistence → reload → next submit.
2. Seed hostile local-storage children.
3. Confirm valid siblings survive.
4. Serialize the complete stored thread.
5. Search for transcript, session, source-body, and raw metadata poison values.
6. Confirm existing graph and legacy citation flows remain siblings.

### 10. Run the real agent

The primary two-turn journey is not replaceable by a fake model. Inspect the real tool trace and actual Network request.

A polished answer without a fresh graph call is a failure.

A correct graph call with Thread A history in Thread B is a failure.

A correct answer using Turn 1’s old revision or anchors is a failure.

An abstention caused by an actual graph gap is correct.

---

## §11 Re-review protocol

Do not rereview the whole PR from scratch after every repair. Maintain a finding ledger.

| Finding     | Owning boundary             | First observed at SHA | Claimed repair SHA | Proof required       |  Closed? | New consequence         |
| ----------- | --------------------------- | --------------------- | ------------------ | -------------------- | -------: | ----------------------- |
| `<finding>` | `<serializer/service/etc.>` | `<sha>`               | `<sha>`            | `<test/review path>` | Yes / No | `<none or consequence>` |

For each rereview:

1. Fetch the current head.
2. Compare only the repair delta against the last reviewed SHA.
3. Re-run the exact owning-boundary proof for each open finding.
4. Re-run downstream proofs only when the repair can affect them.
5. Close a finding once its owning boundary is proven.
6. Do not reopen a closed finding without a concrete regression.
7. Do not manufacture blockers from stale PR description text.
8. Add newly discovered consequences as new ledger rows.
9. Confirm the repair did not expand into Rung 6 or Rung 7.
10. Run the complete acceptance suite once before final approval.

### Durable review model

Apply these principles throughout:

1. Network and local-storage data are `unknown`, regardless of declared types.
2. Wire parsing, active-turn construction, persistence, rehydration, and rendering are separate trust boundaries.
3. Semantic invariants matter more than object shapes.
4. Sanitized objects may never be bypassed by raw overlays.
5. Malformed children are isolated; valid siblings and threads survive.
6. Trace is observability, never grounding or citation authority.
7. Graph citations and legacy path citations remain sibling flows.
8. Adversarial payloads travel through submit → render → persist → reload.
9. Repairs are reviewed as deltas with a finding ledger.
10. Administrative prose is not a substitute for product proof.

---

# Final dispatch instruction

Dispatch one coding agent from the docs-only implementation base with this complete handoff.

The worker’s task is not “add chat history.” It is:

```text
Permit bounded visible prose to resolve conversational identity while proving that every new fact, revision, grounding state, and citation still comes exclusively from the new graph turn.
```

The worker must stop after opening the PR.

```text
STOP. REQUEST REVIEW. DO NOT BEGIN RUNG 6.
```
