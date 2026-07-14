---

pr_body_template: |

## Outcome

Implement the assigned PR010B Rung 4 sub-slice only.

## Ladder position

PR010B Rung 4 requires three sequential pull requests:

1. Persistent Hermes graph-agent host
2. Single-turn backend product cutover
3. Plan presentation, citations, and dogfood proof

This pull request must not begin or partially implement a later sub-slice.

## Verification

Report:

* exact base SHA;
* changed paths;
* every required verification command and result;
* baseline failures rerun on base and head;
* live proof results where required;
* any remaining stop condition or successor dependency.

## Review gate

Opening this pull request is the final repository action for this dispatch.

After opening it:

* stop implementation;
* do not begin the next branch;
* do not stack another pull request;
* request review;
* wait for explicit review disposition and merge or revision instructions.

---

# HANDOFF — PR010B Rung 4: Plan single-turn Hermes graph cutover

**Created:** 2026-07-14
**Status:** ACTIVE
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr010b-rung4-plan-single-turn-hermes-cutover.md`
**Predecessor anchor:** `e6a95e267f743d78239500209dd7333a6f65cf67` — merge of GitHub PR #352
**Delivery shape:** Three sequential pull requests, each independently reviewed before the next begins
**Rung complete only after:** All three PRs are accepted and merged

> ## Dispatch rule
>
> Rung 4 is one product capability, but it is not one implementation PR.
>
> It must be delivered as three sequential pull requests:
>
> 1. **PR353 — Persistent Hermes graph-agent host**
> 2. **PR354 — Single-turn backend product cutover**
> 3. **PR355 — Plan presentation, citations, and dogfood proof**
>
> Do not combine these slices.
>
> Opening each pull request is the final repository action for that dispatch. Once a PR is opened, stop, request review, and wait for explicit review disposition. Do not begin the next branch, write successor code, or open a stacked PR while review is pending.

---

## §0 Why this rung requires three PRs

PR010B Rung 4 has one user-facing outcome:

```text
A GM asks one factual question from the existing Plan Agent Interaction pane,
Hermes answers through the World Graph retrieval plane,
and the product shows a useful answer, graph-admitted citations, and an inspectable trace.
```

That journey crosses three different engineering boundaries:

| Boundary                                   | Principal risk                                                              | Why it requires a separate PR                 |
| ------------------------------------------ | --------------------------------------------------------------------------- | --------------------------------------------- |
| Safely hosting the merged Rung 3 runtime   | Process-global mutation, IPC, timeouts, worker loss, replay semantics       | Infrastructure and failure-model change       |
| Routing the product backend through Rung 3 | Authoritative scope, fail-closed grounding, response shaping, no fallback   | Server trust-boundary and API behavior change |
| Presenting the result in Plan              | Citation union, source-anchor reads, trace UX, bounded persistence, dogfood | Client contract and user-journey change       |

These boundaries are related, but they are not the same review problem.

A single PR would ask a reviewer to validate multiprocessing infrastructure, factual-grounding policy, HTTP behavior, TypeScript migrations, React interaction, local persistence, and live provider behavior simultaneously. It would also make failures difficult to isolate and corrections difficult to review.

Therefore:

```text
Rung 4 = PR353 + PR354 + PR355
```

Each PR must leave the repository in a coherent, tested state. None may claim the full Rung 4 user journey before PR355.

---

## §1 Parent mission

```text
A GM using the existing Plan Agent Interaction pane can submit one factual
Hermes question and receive a graph-grounded answer with graph-admitted
citations and an inspectable graph-tool trace through the existing
/api/live/query product path.
```

### Parent invariant

```text
Every Plan request using the Rung 4 Hermes path is answered, qualified,
abstained, or failed solely from one server-scoped, revision-pinned Rung 3
graph-agent turn.

No manifest, corpus, arbitrary-path, lexical, CLI-one-shot, ambient-memory,
prior-turn, or Live-synthesis path may contribute to the answer or rescue a
failure.
```

### What remains false after Rung 4

Rung 4 does not establish:

* same-thread pronoun or object continuity;
* conversation history supplied to Hermes;
* persistent thread-to-Hermes session identity;
* reload or process-restart continuity;
* removal of legacy Hermes retrieval code;
* removal of the Live/Hermes selector;
* write-capable agent tools;
* Play-surface integration;
* generalized concurrent Hermes scheduling.

Those remain successor work.

---

## §2 Authority and predecessor contracts

Read these before modifying code:

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
21. Existing owning tests for these paths
22. `AGENTS.md`
23. `.cursor/rules/external-agent-pr-loop.mdc`
24. `.cursor/skills/external-agent-pr-loop/SKILL.md`

### Predecessor contract from PR #352

The merged Rung 3 implementation provides:

* a real embedded Hermes `AIAgent` turn;
* a configurable caller-supplied `capability_policy`;
* fail-closed dispatch when no active policy exists;
* authoritative graph scope injection;
* an exact default five-tool graph-read surface;
* safe ordered tool events;
* graph result identifiers and diagnostic summaries;
* error-state tool events;
* no legacy retrieval fallback;
* an explicit `process_exclusive` isolation mode.

Do not weaken these properties.

In particular, do not replace configurable policy with hard-coded “five tools forever” behavior. The product caller may use the default graph-only policy, but the runtime contract remains configurable.

### Critical hosting constraint

`run_hermes_graph_agent_turn` is explicitly process-exclusive, not generally safe for direct execution inside the multi-threaded live-control server process.

It temporarily mutates process-wide state including:

* `sys.path`;
* `sys.modules` entries under `agent`;
* `HERMES_HOME`;
* Hermes plugin and registry state.

Its private lock serializes Rung 3 turns against each other, but it cannot protect unrelated server threads from those mutations.

Therefore:

```text
FastAPI must not directly invoke the process-exclusive turn runtime.
```

Rung 4 requires a dedicated process boundary.

---

## §3 Three-PR execution protocol

### General branch protocol

Each PR starts from the accepted merge SHA of its predecessor.

Do not build all three changes on one long-lived branch.

```text
PR353 base = docs handoff commit on main
PR354 base = accepted merge SHA of PR353
PR355 base = accepted merge SHA of PR354
```

At the beginning of each dispatch:

1. update local `main`;
2. record its immutable SHA;
3. verify the immediately preceding PR is merged;
4. create a fresh branch from that SHA;
5. inspect any review-driven changes introduced during the predecessor;
6. re-anchor the current slice to the actual merged contracts.

### Mandatory pause after opening each PR

For PR353, PR354, and PR355:

1. Complete the implementation and verification.
2. Prepare the handback.
3. Open the pull request.
4. Stop all repository work.
5. Request review.
6. Wait for explicit disposition.

While review is pending, do not:

* create the next branch;
* begin successor implementation;
* modify another worktree for the next PR;
* open a stacked PR;
* preemptively “get ahead” on later acceptance criteria;
* reinterpret silence as approval.

A review may require changes that alter the next PR’s base contract. The next slice must use the reviewed and merged result, not the original design assumption.

### Review outcomes

Proceed only after one of these explicit outcomes:

```text
MERGED
APPROVED AND OPERATOR AUTHORIZES NEXT SLICE
REVISED, RE-REVIEWED, AND MERGED
```

A request for changes means remain on the current PR.

---

# PR353 — Persistent Hermes graph-agent host

## §4 PR353 mission

```text
The live-control application can safely execute serialized Rung 3 graph-agent
turns through one reusable, process-isolated local worker without importing or
running the process-exclusive Hermes runtime in the FastAPI process.
```

### PR353 invariant

```text
All Rung 3 imports, plugin discovery, process-global mutation, agent
construction, and turn execution occur inside the dedicated worker process.

The parent server communicates with that worker only through a bounded typed
request/result protocol.
```

### PR353 suggested branch and title

**Branch:** `agent/pr010b4a-hermes-graph-agent-host`
**Title:** `feat(agent): host Hermes graph turns in an isolated worker`

## §5 PR353 scope

### Required production paths

| Action                                            | Path                                                           | Purpose                                                                             |
| ------------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Create                                            | `apps/live_control_server/services/hermes_graph_agent_host.py` | Own worker lifecycle, typed IPC, serialization, timeout, loss handling, and cleanup |
| Modify only if needed                             | `apps/live_control_server/main.py`                             | Register deterministic application startup/shutdown ownership                       |
| Modify only if protocol serialization requires it | `apps/live_control_server/services/hermes_graph_agent.py`      | Add safe serialization helpers without changing Rung 3 policy or product behavior   |

### Required tests

| Action                                       | Path                                    | Purpose                                                                                            |
| -------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Create                                       | `tests/test_hermes_graph_agent_host.py` | Own host lifecycle, process isolation, serialization, crash, timeout, replay, and cleanup behavior |
| Modify only if serialization helpers changed | `tests/test_hermes_graph_agent.py`      | Preserve and extend the Rung 3 contract                                                            |
| Modify only if lifespan is changed           | Existing application lifecycle test     | Prove worker cleanup during application shutdown                                                   |

### Explicitly out of scope

PR353 must not change:

* `/api/live/query` Hermes behavior;
* `live_agent_loop.py` routing;
* frontend code;
* response citation types;
* grounding classification;
* source-anchor UI behavior;
* backend selector behavior;
* thread/session handling;
* legacy retrieval deletion.

## §6 PR353 host contract

The host must provide one narrow internal operation:

```text
execute one HermesGraphAgentTurnRequest
-> return one HermesGraphAgentTurnResult
```

The local host protocol must not expose arbitrary Python objects.

Use a bounded typed wire representation containing only fields needed by the Rung 3 request and result.

### Request boundary

The request may contain:

* question;
* world ID;
* campaign ID;
* focus;
* admissibility;
* revision pin;
* optional session ID if the internal caller supplies one;
* bounded conversation history supported by Rung 3, although Rung 4 callers will not use it;
* serialized capability policy if required by the caller contract;
* a server-selected graph root representation.

The request must not allow an HTTP caller to inject:

* arbitrary filesystem paths;
* Python callable factories;
* import targets;
* plugin modules;
* environment variables;
* raw provider credentials;
* shell commands.

### Worker behavior

The worker must:

* use a multiprocessing start method that does not inherit the parent’s already-imported module state;
* import and execute Rung 3 only inside the worker;
* process one turn at a time;
* remain alive across successful requests;
* return typed result data;
* terminate cleanly on shutdown;
* be replaceable after a fatal worker failure.

A persistent worker does not mean persistent Hermes conversation continuity. It is infrastructure reuse only.

### Acceptance and replay semantics

The host protocol must distinguish:

1. request not accepted by the worker;
2. request accepted and executing;
3. result returned;
4. worker lost after acceptance.

Before acceptance, the host may restart a failed worker and submit the request once.

After acceptance, the host must not automatically replay the turn. Provider calls and tool activity may already have occurred.

Post-accept failure returns a typed error such as:

```text
hermes_worker_lost
hermes_worker_timeout
```

A new worker may be created for a later request, not as a transparent retry of the lost request.

### Timeout behavior

A timed-out request must:

* return a typed host error;
* terminate or discard the untrusted worker;
* release IPC resources;
* avoid replay;
* permit a clean worker to serve a later request.

### Concurrency behavior

Concurrent parent callers may queue, but worker execution must be serialized.

Tests must prove that two overlapping host calls do not overlap inside Rung 3.

Do not build a generalized worker pool in this PR.

### Cleanup behavior

Application shutdown and test teardown must:

* stop the worker;
* close pipes or queues;
* avoid orphaned processes;
* avoid hanging test exit;
* permit repeated start/stop cycles.

## §7 PR353 required proof

Tests must establish:

1. The parent process does not import or execute `run_hermes_graph_agent_turn`.
2. The worker imports and executes the actual Rung 3 entry point.
3. One worker is reused across sequential successful requests.
4. Concurrent requests execute serially.
5. Request/result serialization is bounded and deterministic.
6. A pre-accept startup failure can be recovered without duplicate execution.
7. A post-accept crash is not replayed.
8. A timeout discards the worker and is not replayed.
9. A subsequent request can use a fresh worker after loss.
10. Shutdown leaves no live worker.
11. Existing Rung 3 tests continue to pass.
12. No API or frontend behavior changes.

### Required commands

Use repository-native commands discovered from the checked-out repository. At minimum run:

```bash
uv run pytest tests/test_hermes_graph_agent.py -q
uv run pytest tests/test_hermes_graph_agent_host.py -q
```

Also run the owning application lifecycle test if `main.py` changes.

Run the full relevant backend suite and compare failures against the recorded base SHA.

Do not inherit test counts from PR #352.

## §8 PR353 handback

The PR description must report:

* base SHA;
* worker start method;
* host request/result schema;
* acceptance acknowledgment design;
* timeout and crash semantics;
* no-replay proof;
* process reuse proof;
* cleanup proof;
* exact tests and results;
* any limitations intentionally deferred.

### PR353 review focus

Ask reviewers to scrutinize:

* whether any Hermes import or process-global mutation remains in FastAPI;
* whether post-accept replay is actually impossible;
* whether worker loss can leak or hang resources;
* whether protocol fields permit unexpected capability or path injection;
* whether tests use a real child process rather than only mocks;
* whether the host is narrowly reusable by PR354.

## §9 PR353 pause gate

Opening PR353 is the final action.

After opening it:

```text
STOP.
REQUEST REVIEW.
DO NOT BEGIN PR354.
```

PR354 may begin only from the accepted PR353 merge SHA.

---

# PR354 — Single-turn backend product cutover

## §10 PR354 mission

```text
POST /api/live/query with query_backend="hermes" dispatches one authoritative,
revision-pinned graph-agent turn through the PR353 host and returns a grounded
answer, qualified answer, stable abstention, or typed error without any legacy
fallback.
```

### PR354 invariant

```text
The server, not the browser or model, owns factual scope and grounding status.

No successful Hermes product response is exposed as graph-grounded unless its
Rung 3 tool events prove successful graph retrieval and graph-admitted evidence.
```

### PR354 suggested branch and title

**Branch:** `agent/pr010b4b-hermes-single-turn-cutover`
**Title:** `feat(agent): route Plan Hermes queries through graph runtime`

## §11 PR354 prerequisite

Before coding:

1. Confirm PR353 is merged.
2. Record the PR353 merge SHA.
3. Re-read the merged host contract and tests.
4. Reconcile any review-driven changes.
5. Create a new branch from that merge SHA.

Do not copy assumptions from the original PR353 draft if review changed them.

## §12 PR354 scope

### Required production paths

| Action                                             | Path                                                      | Purpose                                                                                                                |
| -------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Create                                             | `apps/live_control_server/services/hermes_graph_query.py` | Authoritative scope translation, host invocation, grounding classification, citations, trace shaping, and typed errors |
| Modify                                             | `apps/live_control_server/services/live_agent_loop.py`    | Replace only the `query_backend="hermes"` branch with the new adapter                                                  |
| Modify                                             | `apps/live_control_server/routes/live.py`                 | Validate Hermes-only request constraints and map typed errors                                                          |
| Modify only as required for safe citation metadata | `apps/live_control_server/services/hermes_graph_agent.py` | Extend safe result summaries without weakening Rung 3                                                                  |
| Modify                                             | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`            | Mark Rung 3 complete and publish the three-PR Rung 4 sequence                                                          |
| Modify                                             | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`            | Reconcile the critical path to the same ladder                                                                         |

### Required tests

| Action                                     | Path                                    | Purpose                                                                                 |
| ------------------------------------------ | --------------------------------------- | --------------------------------------------------------------------------------------- |
| Create                                     | `tests/test_live_query_hermes_graph.py` | Own positive, partial, abstention, error, scope, no-fallback, and sibling-path behavior |
| Modify if Rung 3 summaries change          | `tests/test_hermes_graph_agent.py`      | Prove extensions using canonical PR010A models                                          |
| Modify existing live route tests as needed | Existing owning test                    | Validate request and response wire behavior                                             |

### Explicitly out of scope

PR354 must not:

* modify Plan rendering;
* add source-anchor click behavior;
* migrate local-storage citation persistence;
* send prior turns to Hermes;
* bind visible thread identity to Hermes session identity;
* resume sessions;
* remove the backend selector;
* delete legacy code;
* add writes.

## §13 PR354 authoritative request contract

The existing request remains based on:

```text
POST /api/live/query
query_backend="hermes"
```

For the Rung 4 Hermes branch:

### Required inputs

* non-empty `text`;
* outer `campaign_id`;
* outer live `session`;
* required `world_graph_context`;
* optional UI `agent_thread_id`;
* optional trace request.

### Rejected inputs

Reject before host invocation when:

* `world_graph_context` is missing;
* nested campaign does not match the outer campaign;
* a non-null `manifest_path` is supplied;
* a non-null `hermes_session_id` is supplied;
* unsupported graph focus or admissibility is supplied;
* graph projection resolution returns a fatal error.

Recommended stable error codes include:

```text
world_graph_context_required
invalid_request
legacy_manifest_not_supported
hermes_continuity_not_supported
```

### Client thread ID

`agent_thread_id` may be echoed for UI ownership only.

It must not:

* become the Rung 3 session ID;
* cause history lookup;
* load prior turns;
* imply Hermes continuity.

Each Rung 4 request is an independent single turn.

## §14 PR354 authoritative scope translation

The server must resolve the existing nested World Graph request before invoking the host.

The Rung 3 request must receive authoritative values derived from the resolved server result:

* `world_id`;
* `campaign_id`;
* `focus`;
* `admissibility`;
* the resolved graph `revision_id` as `revision_pin`.

Do not trust a model-supplied or client-repeated revision after resolution.

The default graph-only capability policy should be created from this authoritative scope.

Do not expose capability policy as an HTTP request field.

Do not pass the old projection envelope to the model as factual evidence. Rung 3 graph tools are the factual plane.

## §15 PR354 grounding classification

A non-empty `final_response` is necessary but not sufficient for product success.

The adapter must classify the turn from safe Rung 3 tool events.

### Grounded success

A response may be presented as grounded when:

* Rung 3 status is `ok`;
* a non-empty final response exists;
* at least one graph tool completed successfully;
* retrieval produced usable graph evidence;
* at least one admissible source anchor is available for factual support.

Return:

```text
status = "ok"
grounding = "grounded"
```

### Qualified or partial answer

A response may be shown as qualified when:

* retrieval outcome is `partial` or `truncated`;
* usable graph evidence and anchors exist;
* the answer preserves uncertainty;
* warnings identify partial coverage.

Return an observable partial state, for example:

```text
status = "partial"
grounding = "partial"
```

### Stable abstention

Discard model factual prose and return a stable product-authored abstention when:

* retrieval is `empty`;
* retrieval is `denied`;
* no usable source anchor was admitted;
* the model returned prose without successful graph-tool completion;
* the graph contains insufficient support.

The abstention should say, in useful product language:

```text
DungeonBuddy’s World Graph does not currently contain enough admitted evidence
to answer this question reliably.
```

It may include bounded diagnostic or missing-coverage information from the graph result.

It must not:

* run manifest lookup;
* search Markdown;
* use Live synthesis;
* use CLI one-shot;
* present unsupported model prose.

### Unavailable or runtime error

Return a typed error or unavailable response when:

* the host is unavailable;
* the worker is lost;
* the worker times out;
* Rung 3 returns `status="error"`;
* graph retrieval is unavailable;
* grounding data is structurally invalid.

No fallback is permitted.

## §16 PR354 graph citation contract

Add a discriminated graph citation variant to the product response.

A graph citation must contain bounded opaque metadata such as:

```json
{
  "kind": "world_graph_source_anchor",
  "anchor_id": "source-anchor:v1:...",
  "world_id": "world:eldyrwild",
  "campaign_id": "campaign:c2",
  "revision_id": "revision:...",
  "focus": {
    "kind": "session",
    "session_id": "session:23"
  },
  "admissibility": "gm",
  "source_artifact_id": "artifact:...",
  "evidence_ref_id": "evidence:...",
  "display_label": "Session 23 recap · North Gate"
}
```

Exact field names may follow repository conventions, but the variant must be explicit and typed.

It must not contain:

* arbitrary paths;
* absolute paths;
* raw source content;
* raw model prompts;
* secrets;
* unbounded tool payloads.

Citation metadata must originate from canonical PR010A result models or a safe Rung 3 summary proved against those models.

Do not infer citations from model-authored citation text.

## §17 PR354 safe trace contract

The existing answer-first response should expose a bounded graph trace.

It should include:

* trace ID;
* runtime/host mode;
* Hermes session ID for observability only;
* graph world and campaign;
* focus and admissibility;
* resolved revision;
* ordered graph tool events;
* tool state: start, completion, or error;
* duration;
* retrieval schema;
* outcome;
* matched node IDs;
* relationship IDs;
* source-anchor IDs;
* diagnostic codes;
* abstention status.

It must not include:

* raw question text in persisted tool arguments;
* prompt preview;
* source bodies;
* arbitrary file paths;
* environment values;
* provider secrets;
* full unbounded tool results.

## §18 PR354 no-fallback proof

The Hermes product branch must not call:

* `dungeon_context_lookup`;
* `dungeon_manifest_index`;
* `dungeon_get_document`;
* `dungeon_search`;
* manifest-context services;
* legacy corpus-context services;
* CLI `--oneshot`;
* Live answer synthesis;
* subprocess-based Hermes execution.

Legacy code may remain physically present for Rung 7, but it must not be reachable from the new Hermes branch.

Tests must patch or otherwise instrument these paths and fail if any are invoked.

## §19 PR354 sibling behavior

The existing `query_backend="live"` path must remain behaviorally unchanged.

Tests must prove:

* no host invocation for Live requests;
* existing Live mutation and response behavior remains intact;
* Hermes-specific validation does not reject valid Live requests;
* Hermes errors do not silently switch to Live.

## §20 PR354 required proof

Tests must establish:

1. A valid Hermes request resolves authoritative graph scope.
2. The host receives the resolved revision, not an untrusted revision.
3. A grounded Rung 3 result maps to an answer and graph citations.
4. `partial` and `truncated` results produce a qualified state.
5. `empty`, `denied`, and no-anchor cases produce stable abstention.
6. Prose without a successful graph tool completion is rejected as ungrounded.
7. Host loss and timeout map to typed errors.
8. Rung 3 errors map to typed errors.
9. Missing graph context is rejected before host invocation.
10. Manifest and continuity inputs are rejected for Hermes.
11. No legacy fallback function is called.
12. Live sibling behavior remains unchanged.
13. Citation and trace output contain no raw paths, bodies, prompts, or secrets.
14. Canonical PR010A serialized models drive the citation tests.

### Required commands

At minimum run:

```bash
uv run pytest tests/test_hermes_graph_agent.py -q
uv run pytest tests/test_hermes_graph_agent_host.py -q
uv run pytest tests/test_live_query_hermes_graph.py -q
```

Run all existing live-query route and service tests affected by the branch.

Run the relevant backend suite and compare failures on base and head.

## §21 PR354 handback

Report:

* PR353 merge SHA used as base;
* exact Hermes branch call path;
* authoritative scope mapping;
* grounding state machine;
* abstention wording;
* citation schema;
* safe trace schema;
* rejected legacy inputs;
* no-fallback proof;
* Live sibling proof;
* exact verification results.

### PR354 review focus

Ask reviewers to scrutinize:

* whether any browser- or model-controlled scope reaches dispatch;
* whether model prose can escape without graph evidence;
* whether partial evidence is overstated;
* whether citations are derived from actual graph anchors;
* whether any hidden fallback remains;
* whether errors accidentally switch to Live;
* whether Rung 3 capability-policy configurability was preserved.

## §22 PR354 pause gate

Opening PR354 is the final action.

After opening it:

```text
STOP.
REQUEST REVIEW.
DO NOT BEGIN PR355.
```

PR355 may begin only from the accepted PR354 merge SHA.

---

# PR355 — Plan presentation, citations, and dogfood proof

## §23 PR355 mission

```text
The existing Plan Agent Interaction pane presents the Rung 4 single-turn
Hermes answer, grounding state, graph-tool trace, and revision-pinned
source-anchor citations, and proves the complete user journey through live
dogfood.
```

### PR355 invariant

```text
The client displays the server’s bounded grounding contract without creating a
second factual or evidence plane.

Clicking evidence opens only the opaque graph-admitted source anchor at the
scope and revision returned by the server.
```

### PR355 suggested branch and title

**Branch:** `agent/pr010b4c-plan-hermes-graph-presentation`
**Title:** `feat(plan): present graph-grounded Hermes answers`

## §24 PR355 prerequisite

Before coding:

1. Confirm PR354 is merged.
2. Record the PR354 merge SHA.
3. Re-read the accepted response, citation, trace, and error contracts.
4. Reconcile all review-driven changes.
5. Create a new branch from that merge SHA.

Do not use TypeScript types copied from the unreviewed PR354 proposal.

## §25 PR355 scope

### Required frontend paths

| Action                | Path                                                                          | Purpose                                                                             |
| --------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Modify                | `apps/live-control-ui/src/api/types.ts`                                       | Add accepted graph citation, grounding, and trace types                             |
| Modify                | `apps/live-control-ui/src/api/liveApi.ts`                                     | Send valid Rung 4 Hermes requests and call the existing source-anchor read route    |
| Modify                | `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Present the answer, partial/abstention/error state, citations, and evidence opening |
| Modify                | `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx`       | Render bounded graph-tool trace                                                     |
| Modify                | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`  | Persist only safe bounded graph metadata                                            |
| Modify only as needed | Existing Plan CSS                                                             | Support the accepted presentation without redesigning the pane                      |

### Required frontend tests

Use existing owning test files where practical. Add or modify focused tests for:

* API request shaping;
* citation union parsing;
* source-anchor reads;
* answer/partial/abstention/error rendering;
* graph trace rendering;
* local persistence redaction;
* reload display without Hermes resume.

### Backend changes

PR355 should not redesign backend contracts.

A small backend correction is allowed only when live integration reveals that PR354’s accepted wire contract is internally inconsistent. Such a correction must be narrow, tested, and called out prominently in the PR description.

If a material backend redesign is required, stop and return to PR354 review rather than hiding it in PR355.

## §26 PR355 request behavior

For Hermes requests, the browser must:

* send `query_backend="hermes"`;
* send the required World Graph context;
* send the visible `agent_thread_id` only for UI ownership;
* omit `manifest_path`;
* omit `hermes_session_id`;
* avoid sending prior turn messages;
* avoid claiming same-thread Hermes continuity.

The existing Plan thread may contain multiple displayed turns, but each Hermes submission remains an independent Rung 4 turn.

If the user asks “What is it connected to?” after a prior turn, Rung 4 does not guarantee correct pronoun resolution. That is Rung 5.

## §27 PR355 answer presentation

The normal presentation remains answer-first.

### Grounded answer

Show:

* the answer;
* a restrained grounding indicator;
* graph citations;
* optional trace disclosure.

Do not lead with internal evidence scores or implementation metadata.

### Partial answer

Show:

* the qualified answer;
* a visible but non-alarming partial-coverage warning;
* available citations;
* graph diagnostics inside trace or evidence details.

### Abstention

Show the server-authored graph-coverage abstention as the answer state.

Do not present discarded model prose.

The UI should make clear that DungeonBuddy lacks enough graph evidence, rather than implying the agent crashed.

### Runtime error

Show a stable error state distinct from coverage abstention.

Do not silently retry through Live or another backend.

## §28 PR355 source-anchor citation journey

Clicking a graph citation must call the existing route:

```text
POST /api/live/world-graph/retrieval/source-anchor/read
```

The request must use the exact server-returned:

* anchor ID;
* world ID;
* campaign ID;
* focus;
* admissibility;
* revision pin.

Do not convert an anchor into a path.

Do not call the legacy path-based citation reader for graph citations.

The existing path-based citation behavior may remain for existing Live responses while both citation variants coexist.

### Revision behavior

The citation read must remain pinned to the answer’s revision.

Do not silently update to current head when opening old evidence.

If the anchor is unreadable, stale, denied, or unavailable, show that state explicitly.

## §29 PR355 trace presentation

The existing trace disclosure should display useful graph activity, including:

* graph revision and head status where available;
* world, campaign, focus, and admissibility;
* tool name;
* start/completion/error;
* duration;
* outcome;
* matched nodes;
* traversed relationship IDs;
* source-anchor IDs;
* diagnostic codes;
* whether the final response was grounded, partial, abstained, or failed.

Do not render:

* raw prompts;
* source bodies in the trace;
* arbitrary paths;
* environment values;
* raw JSON dumps;
* secrets;
* raw query telemetry beyond the accepted safe summary.

The normal collapsed state remains concise.

## §30 PR355 persistence contract

Local Agent Interaction persistence may retain:

* answer text;
* question text already owned by the local thread;
* turn ID;
* visible UI thread ID;
* completion status;
* safe bounded trace;
* graph citation metadata;
* graph revision summary;
* grounding state;
* warnings.

It must not retain:

* source-anchor body content;
* raw tool result payloads;
* raw prompts;
* arbitrary or absolute paths from graph citations;
* provider credentials;
* process-host details not needed by the UI;
* a Hermes session pointer implying continuity.

### Reload behavior

After reload, the client may display the saved Rung 4 turn.

It must not:

* resume a Hermes session;
* send old messages to the next turn;
* claim that the old thread is live Hermes memory;
* treat persisted answer text as current campaign truth.

A new factual request performs a new graph retrieval turn.

## §31 PR355 selector behavior

The existing Live/Hermes selector remains in this rung for dogfood comparison.

Do not remove it in PR355.

The Hermes option should clearly route to the accepted graph-only path. The Live option retains its existing behavior.

Backend-toggle removal belongs to Rung 7 after acceptance.

## §32 PR355 required frontend proof

Tests must establish:

1. Hermes requests omit `manifest_path`.
2. Hermes requests omit `hermes_session_id`.
3. Hermes requests include required World Graph context.
4. Grounded answers render answer-first.
5. Partial answers show a bounded coverage warning.
6. Abstentions render without discarded model prose.
7. Runtime errors are distinct from abstentions.
8. Graph citations render.
9. Clicking a graph citation calls source-anchor read, not path-based source read.
10. The exact citation revision and scope are sent.
11. Existing path citations still work for Live responses.
12. Trace renders graph-tool events and grounding status.
13. Trace does not expose prompts, paths, source bodies, or raw query text.
14. Persisted turns retain bounded graph metadata.
15. Persisted turns do not retain source bodies or Hermes continuity pointers.
16. Reload displays the saved answer without resuming Hermes.
17. A second question remains an independent single turn.
18. Existing Agent Interaction thread management remains intact.

### Required commands

Use the repository’s accepted package manager and scripts. At minimum run the owning frontend tests and:

```bash
cd apps/live-control-ui
npm test -- --run
npm run build
```

Adjust only to the actual repository scripts. Record the exact commands used.

Run affected backend tests as a regression check:

```bash
uv run pytest tests/test_hermes_graph_agent_host.py -q
uv run pytest tests/test_live_query_hermes_graph.py -q
```

## §33 PR355 live dogfood proof

Automated tests are not sufficient for final Rung 4 acceptance.

Run the real Plan surface with the actual live-control server, persistent Hermes worker, configured model provider, and a published World Graph.

### Positive journey

Ask:

```text
What do we know about Tripod Null-Calf at the North Gate?
```

Prove:

* the request entered through the Plan pane;
* the server invoked the persistent host;
* the worker executed the real Rung 3 `AIAgent`;
* Hermes selected graph tools;
* the answer used graph results;
* citations came from source anchors;
* trace shows real graph tool events;
* no manifest or CLI path ran.

### Evidence journey

Click one citation.

Prove:

* the UI called the opaque source-anchor read route;
* the request used the answer’s revision and scope;
* a bounded source excerpt opened;
* no arbitrary path was sent.

### Coverage-gap journey

Ask a question whose answer exists in Markdown but is absent from the graph.

Prove:

* Hermes did not search Markdown directly;
* the product returned the graph-coverage abstention;
* no Live, manifest, lexical, arbitrary-path, or CLI fallback ran.

### Partial or unavailable journey

Exercise at least one partial, truncated, denied, or unavailable graph result.

Prove the UI distinguishes it from a fully grounded success.

### Independent-turn journey

Submit a second question in the same visible thread.

Prove:

* a new independent Rung 3 turn occurred;
* no prior messages were supplied;
* no Hermes session was resumed;
* the product does not claim pronoun continuity.

### Live sibling journey

Submit one request using the Live backend.

Prove existing Live behavior still works and does not invoke the Hermes worker.

### Evidence to include in the PR

Include bounded proof such as:

* screenshots of answer and trace;
* safe server logs;
* trace IDs;
* tool names and outcomes;
* cited anchor IDs;
* exact commands and environment shape;
* explicit confirmation that no fallback path ran.

Do not publish secrets, raw prompts, or source bodies in the PR.

## §34 PR355 handback

Report:

* PR354 merge SHA used as base;
* accepted response contract implemented;
* request fields sent and omitted;
* citation union behavior;
* source-anchor click path;
* trace presentation;
* persistence redaction;
* frontend verification;
* backend regression verification;
* live positive journey;
* live gap-abstention journey;
* live evidence-open journey;
* independent-turn proof;
* remaining limitations.

### PR355 review focus

Ask reviewers to scrutinize:

* whether the UI overstates grounding;
* whether evidence opening bypasses opaque anchors;
* whether stale path-based assumptions contaminate graph citations;
* whether local persistence leaks source bodies or unsafe trace data;
* whether the client accidentally sends history or session pointers;
* whether live proof demonstrates actual Hermes tool dispatch;
* whether the complete Rung 4 mission is now true.

## §35 PR355 pause gate

Opening PR355 is the final implementation action.

After opening it:

```text
STOP.
REQUEST FINAL RUNG 4 REVIEW.
DO NOT BEGIN RUNG 5.
```

Rung 5 may begin only after PR355 is reviewed, accepted, merged, and Rung 4 is explicitly declared complete.

---

## §36 Rung 4 completion rubric

Rung 4 is complete only when all three merged PRs jointly prove:

| Requirement                                                        | Owning PR |
| ------------------------------------------------------------------ | --------- |
| Rung 3 runs outside the FastAPI process                            | PR353     |
| Worker process is persistent and reusable                          | PR353     |
| Turns are serialized                                               | PR353     |
| Crash, timeout, acknowledgment, and no-replay semantics are proved | PR353     |
| `/api/live/query` Hermes branch reaches the host                   | PR354     |
| Server owns graph scope and revision                               | PR354     |
| Grounded, partial, abstention, and error states are distinct       | PR354     |
| No legacy fallback contributes to Hermes answers                   | PR354     |
| Graph citations derive from admitted anchors                       | PR354     |
| Live sibling behavior remains unchanged                            | PR354     |
| Plan displays the accepted result contract                         | PR355     |
| Citation clicks use source-anchor reads                            | PR355     |
| Trace is useful and safely bounded                                 | PR355     |
| Local persistence does not claim continuity or leak source bodies  | PR355     |
| Real provider and graph dogfood journey succeeds                   | PR355     |
| Graph gaps produce honest abstention                               | PR355     |

No individual PR may claim Rung 4 complete before PR355 acceptance.

---

## §37 Named successors

### PR010B Rung 5 — same-thread Hermes continuity

Mission:

```text
One Agent Interaction thread carries bounded conversational context so a
follow-up such as “What is it connected to?” resolves the intended object while
fresh graph tools remain the factual authority.
```

Rung 5 owns:

* prior conversation history;
* thread-to-Hermes conversational identity;
* pronoun and object-reference continuity;
* fresh graph retrieval on every factual follow-up;
* separation of conversational memory from campaign truth.

### PR010B Rung 6 — reload and session-pointer continuity

Rung 6 owns:

* durable server-approved session pointers;
* reload restoration;
* process-restart behavior;
* session-expiration behavior;
* recovery when a Hermes session cannot resume;
* no second campaign-truth store.

### PR010B Rung 7 — acceptance and demolition

Rung 7 owns removal from the product path of:

* manifest-backed Hermes lookup;
* corpus and lexical fallback;
* arbitrary-path document reads;
* CLI one-shot product behavior;
* Live fallback for Hermes failures;
* the steady-state backend selector after acceptance;
* obsolete transitional contracts and tests.

### PR011 — governed agent capabilities

PR011 follows the accepted read-only journey and owns:

* typed non-read tools;
* app-level context;
* drafts;
* preview and confirmation;
* proposal-bound writes;
* Graph Review and Kernel correction escalation.

---

## §38 Global stop conditions

Stop the current PR and report rather than improvising when:

* the predecessor PR is not merged;
* the working base differs from the recorded merge SHA;
* another branch materially changed an allowlisted path;
* Rung 3’s request/result or capability-policy contract changed;
* the real Hermes API differs from the merged assumptions;
* a direct in-process FastAPI call appears necessary;
* a post-accept worker failure cannot be distinguished from pre-accept failure;
* grounding cannot be established from safe tool events;
* source citations require arbitrary paths;
* the existing source-anchor route cannot support the accepted citation contract;
* completing the slice requires conversation history or session resume;
* completing the slice requires deleting legacy paths;
* completing the slice requires write tools;
* live proof requires exposing secrets or unbounded source content;
* a material predecessor defect is discovered.

Do not silently widen the PR to solve the next rung.

---

## §39 Required handback format for every PR

Return:

1. PR URL and number.
2. Branch name.
3. Exact base SHA.
4. Head SHA.
5. Changed-file list.
6. Mission statement.
7. Contract established.
8. Verification commands and exact results.
9. Baseline comparison.
10. Live proof, when required.
11. Known limitations.
12. Explicit confirmation that no successor work began.
13. Review request focused on the risks named in that PR.
14. Final line:

```text
Implementation paused after opening this PR. No successor branch or PR has been started.
```

---

## §40 Final dispatch check

Before dispatching PR353, confirm:

* this handoff is committed to `main`;
* the implementation base SHA is recorded;
* PR #352 remains the predecessor anchor;
* the agent understands that Rung 4 requires three PRs;
* the agent is assigned PR353 only;
* the agent has been told to stop after opening PR353;
* no expectation exists that PR354 or PR355 will be started automatically.

Before dispatching PR354, confirm:

* PR353 is reviewed and merged;
* its merge SHA is recorded;
* the host contract is re-read;
* the agent is assigned PR354 only;
* the agent has been told to stop after opening PR354.

Before dispatching PR355, confirm:

* PR354 is reviewed and merged;
* its merge SHA is recorded;
* the response and citation contracts are re-read;
* the agent is assigned PR355 only;
* the agent has been told to stop after opening PR355.

After PR355 opens:

```text
Pause for final Rung 4 review.
Do not dispatch Rung 5 until Rung 4 is explicitly accepted.
```
