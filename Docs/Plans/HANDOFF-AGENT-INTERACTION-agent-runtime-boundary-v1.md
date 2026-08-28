---
pr_body_template: |
  ## Handoff pointer
  - Workstream: AGENT-INTERACTION / A2
  - Flow: AGENT-INTERACTION
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-AGENT-INTERACTION-agent-runtime-boundary-v1.md`
  - Suggested branch: `agent/runtime-boundary-v1`
  - Suggested PR title: `AGENT-INTERACTION: put Hermes behind AgentRuntime`

  ## Verification pointer
  - Base/head: record exact SHAs in the PR handback
  - Changed paths: HANDOFF §4 only
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — DungeonBuddy AgentRuntime Boundary v1 (A2)

**Created:** 2026-08-27
**Status:** READY FOR DISPATCH after exact-current-main re-anchor and active-lease check
**Canonical handoff path:** `Docs/Plans/HANDOFF-AGENT-INTERACTION-agent-runtime-boundary-v1.md`
**Workstream:** `AGENT-INTERACTION / A2`
**Flow / owner:** `AGENT-INTERACTION`
**Handoff direction:** `DESIGN → CODE`
**Suggested branch:** `agent/runtime-boundary-v1`
**PR title:** `AGENT-INTERACTION: put Hermes behind AgentRuntime`

> **Design base:** `f075740b167b7031f797c5643c32ea206c416f85` — current `main`, merge of A1 PR #656, `AGENT-INTERACTION: add advanced Agent trace inspector`.
>
> A1 accepted final head: `057b2efee4b68d8324111874cee617448dd38f8b`; formal review count: **4**; merge SHA: `f075740b167b7031f797c5643c32ea206c416f85`.
>
> Dispatch from the exact current `main` that contains this handoff. Before branch creation, fetch `main`, record the exact base SHA, and re-check active PR/worktree write leases. At design time the active implementation lanes are #651 (`CUTOVER: native genesis read/write continuity`, head `3a60610dc78b710aa0aea6af817da00b0bfb563e`) and #657 (`PLAY-SURFACE: make local Play dogfood reachable`, head `a9dccd57baca51f01da26ef33fcd5dc6228f10ca`). Their current leases are disjoint from the A2 service/runtime paths below. Do not assume that remains true at dispatch.

Parent authorities and current contracts:

- `AGENTS.md`
- `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
- `Docs/Design/DESIGN-magic-moment-contextual-source-to-world-graph.md`
- `Docs/Plans/HANDOFF-AGENT-INTERACTION-turn-trace-v1.md`
- `Docs/Plans/HANDOFF-AGENT-INTERACTION-trace-inspector-v1.md`
- `apps/live_control_server/services/agent_turn_trace.py` — A0 trace truth; read-only in A2
- `apps/live_control_server/services/live_agent_loop.py` — current product entry / whole-turn trace owner
- `apps/live_control_server/services/hermes_graph_query.py` — current product graph-Agent orchestration
- `apps/live_control_server/services/hermes_graph_agent_contract.py` — current Hermes-only IPC contract; adapter-internal after A2
- `apps/live_control_server/services/hermes_graph_agent_host.py` — current process-isolated host; adapter-internal after A2
- `apps/live_control_server/services/hermes_graph_agent.py` — current embedded Hermes implementation; unchanged in A2
- `src/graph_memory/hermes_graph_plugin.py` — current Hermes plugin/capability implementation; unchanged in A2

---

# 0. Repository truth and capability decomposition

## 0.1 Current truth after A0 + A1

A0 and A1 are merged.

The current Agent path has first-class telemetry and an advanced inspector, but product orchestration is still coupled directly to Hermes execution types.

Today the Hermes branch of `process_live_query(...)` does this conceptually:

```text
product request
  ↓
load Buddy session
  ↓
validate Hermes-specific request fields
  ↓
resolve DungeonMind World context
  ↓
assemble retrieval/session context
  ↓
build HermesGraphAgentTurnRequest
  ↓
HermesGraphAgentHost.execute(...)
  ↓
HermesGraphAgentTurnResult / HermesGraphToolEvent
  ↓
DungeonBuddy grounding validation + response projection
  ↓
dmb_agent_turn_trace_v1
```

This is observable in current code:

- `live_agent_loop.py` imports Hermes runtime constants and calls `run_hermes_graph_query(...)` directly;
- `hermes_graph_query.py` imports the Hermes host and Hermes wire request/result/tool-event types;
- `build_hermes_graph_turn_request(...)` creates the harness-specific request in the same module that owns DungeonBuddy retrieval-session and grounding semantics;
- the embedded Hermes wrapper may synthesize its default graph capability policy when none is supplied.

The product behavior is sound. The dependency direction is not yet the target.

The architecture authority says:

```text
DungeonBuddy
  = product context, thread identity, tool/capability policy,
    grounding/review semantics, telemetry, canonical-write authority

Agent harness
  = model/tool-loop execution mechanics
```

A2 exists to make that division real for the current Hermes path **without changing the journey**.

## 0.2 A2 is a characterization/refactor slice

A2 does not add a second harness.

It first creates one DungeonBuddy-owned execution port and proves current Hermes can sit behind it.

The success condition is:

> **DungeonBuddy graph-Agent orchestration no longer depends on Hermes host/wire types, and the existing Hermes journey still produces the same product response, grounding, continuity, tools, trace, token/cost truth, and failure behavior through a thin adapter.**

This is deliberately smaller than the final conceptual runtime API.

Current execution is synchronous. A2 must not manufacture an `AgentRunHandle`, cancellation, resume, steering, or streamed text API merely because those may matter later.

The v1 realization may be:

```python
result = runtime.run(invocation)
```

A3 may extend lifecycle behavior only when the challenger experiment proves which semantics are actually required.

## 0.3 Candidate outcomes

| Candidate | Decision |
|---|---|
| DMB-owned `AgentRuntime` Protocol / execution port | **KEEP — A2 mission** |
| DMB-owned invocation/result/tool-event contracts | **KEEP — required to remove product→Hermes type coupling** |
| Hermes adapter implementing `AgentRuntime` | **KEEP — A2 mission** |
| Internal runtime injection for deterministic tests / future experiment | **KEEP** |
| DMB-owned capability-policy identity above the adapter | **KEEP — adapter may map it to Hermes policy** |
| Preserve current graph retrieval/session packet | **KEEP — do not redesign ContextAssembler here** |
| Preserve current Hermes process isolation / host | **KEEP unchanged behind adapter** |
| Preserve current Hermes public request/backend behavior | **KEEP unchanged** |
| Preserve A0 `dmb_agent_turn_trace_v1` semantics | **KEEP unchanged** |
| Preserve A1 inspector/client behavior | **KEEP unchanged; no UI write** |
| Dynamic user-facing runtime selector | **OUT OF SCOPE** |
| PydanticAI dependency / adapter | **SPLIT — A3** |
| General ContextAssembler | **SPLIT — later Agent Interaction slice** |
| Interaction Memory | **SPLIT** |
| Tool implementation rename / portable ToolSpec redesign | **SPLIT — only if A3 proves required** |
| Cancellation / resume / steering / streamed text | **SPLIT — evidence-gated lifecycle successor** |
| Agent thread durability migration | **OUT OF SCOPE / APP-STATE evidence-gated** |
| Trace schema v2 | **OUT OF SCOPE** |
| New model-selection UI / policy | **OUT OF SCOPE** |
| World Graph write / D.2C4 work | **OUT OF SCOPE** |

---

# 1. Mission and merge-ready invariant

## 1.1 Mission

> **Place the current Hermes graph-Agent execution behind one DungeonBuddy-owned `AgentRuntime` boundary so product orchestration can construct a harness-neutral invocation, select a DungeonBuddy capability policy, execute through an injected runtime, and consume a harness-neutral result while preserving the exact current Hermes product journey and A0/A1 observability.**

## 1.2 Merge-ready invariant

> **For the current `query_backend="hermes"` product path, all DungeonBuddy context resolution, retrieval-session creation, continuity-pointer governance, grounding validation, response projection, and trace finalization remain product-owned; the product path crosses exactly one `AgentRuntime.run(...)` seam and does not import Hermes host or Hermes wire request/result/tool-event types; the default adapter maps that DungeonBuddy invocation fail-closed onto the unchanged process-isolated Hermes host, returns DungeonBuddy-owned result/tool-event types, preserves normalized model-call telemetry without recomputation, and yields the same public response/grounding/continuity/trace behavior as before. No second harness, runtime picker, dependency change, UI change, persistence change, World behavior change, or new lifecycle claim lands in A2.**

## 1.3 What becomes true

```text
AgentRuntime is a DungeonBuddy-owned service contract
current product graph-Agent orchestration builds AgentRuntimeInvocation
current product graph-Agent orchestration consumes AgentRuntimeResult
current product graph-Agent orchestration no longer imports Hermes host types
current product graph-Agent orchestration no longer imports Hermes wire request/result/tool-event types
HermesAgentRuntimeAdapter is the translation boundary
Hermes adapter is the only A2 product-path layer that knows Hermes host/wire contracts
current process-isolated Hermes host stays unchanged
current embedded Hermes wrapper stays unchanged
DungeonBuddy selects a named capability policy before adapter dispatch
Hermes adapter maps that policy to the existing explicit Hermes capability policy
unknown/unsupported DMB capability policy fails closed before host execution
AgentRuntimeToolEvent exposes generic core + bounded capability attributes
product grounding still rejects contradictory/foreign graph scope
runtime result carries runtime-session identity without making it product thread identity
runtime result carries worker/process metadata needed by current continuity logic
runtime result preserves A0 normalized model_calls[] exactly
runtime result preserves telemetry warnings / observed call count exactly
harness_turn span measures runtime.run(...)
A0 top-level trace values remain truthful for Hermes
A1 inspector renders the same trace after A2
fake runtime can drive the product orchestration in tests without Hermes imports/processes
```

## 1.4 What must remain false

```text
PydanticAI is installed or imported
runtime can be selected from the browser/API
query_backend contract changes
AgentRuntime owns World context resolution
AgentRuntime owns GraphRetrievalSession creation
AgentRuntime owns latest-recap admission/read semantics
AgentRuntime owns continuity pointer persistence
AgentRuntime owns grounding validation
AgentRuntime owns response projection
AgentRuntime owns dmb_agent_turn_trace_v1 finalization
harness session id becomes product thread id
Hermes plugin/toolset names become generic product API vocabulary
raw provider request/response crosses the generic result
raw prompt/tool result becomes baseline telemetry
AgentRuntime writes World truth
new APP-STATE schema exists
cancel/resume/steer/stream lifecycle is claimed but unimplemented
existing Hermes host/IPC behavior is rewritten merely to make the abstraction prettier
A0 trace backend/runtime/mode is relabeled generically
```

## 1.5 Pre-dispatch critique

| Question | Answer |
|---|---|
| What is the smallest useful proof? | A fake `AgentRuntime` can replace Hermes at the internal product seam and `hermes_graph_query` still performs the same grounding/response projection; the real Hermes adapter maps the same invocation to the existing host. |
| Most likely fake abstraction | A wrapper named `AgentRuntime` that simply calls `run_hermes_graph_query()` and returns the final product response. That is **not acceptable** because grounding/context/continuity would still live below the harness boundary. |
| Most likely authority leak | Letting the adapter synthesize or broaden scope/capabilities from missing context. The DMB invocation must carry resolved scope and a DMB-selected policy; adapter mapping is fail-closed. |
| Most likely telemetry regression | Adapter copies only final text/tool events and drops model-call retries, partial/truncated state, observed count, or worker-failure telemetry. Required tests compare normalized runtime result → final A0 trace. |
| Why not PydanticAI now? | Until the product consumes one stable runtime contract, a second adapter would force design and implementation to move together and make comparison ambiguous. A3 is intentionally the challenger slice. |
| Why no lifecycle API now? | Current product path does not expose cancellation/resume/steer/text streaming. Inventing them before one challenger demonstrates need is speculative API debt. |

---

# 2. Ownership boundary and v1 contract

## 2.1 Product-owned before and after A2

The following stay outside `AgentRuntime`:

```text
request/API validation
Buddy session load
agent_thread_id / turn_id creation
DungeonMind World context resolution
latest-recap comparison context
GraphRetrievalSession creation/hydration ownership
admitted recap excerpt read owned by current product path
resolved world/campaign/focus/admissibility/revision scope
continuity pointer resolve/persist
scope-contradiction checks
grounding/evidence validation
claim acceptance / citation projection
product answer / diagnostics / warnings shape
A0 AgentTurnTraceBuilder lifecycle
A0 cost aggregation and logging
```

The runtime receives bounded inputs. It does not discover any of those product facts for itself.

## 2.2 Runtime-owned

`AgentRuntime` owns only execution mechanics needed to obtain an Agent turn result:

```text
translate DMB invocation into harness invocation
invoke configured harness/model loop
execute only adapter-mapped permitted capability surface
return final text / safe messages if retained
return runtime-session identity
return normalized tool-event observations
return normalized model-call telemetry
return adapter/runtime metadata needed for product continuity/diagnostics
return typed execution failure
```

## 2.3 Directional v1 types

Exact names may move slightly during implementation, but the ownership and information boundaries are contractual.

```python
AgentRuntimeDescriptor {
    runtime_id             # "hermes"
    trace_backend          # current value "hermes"
    trace_runtime          # current value "process_isolated"
    trace_mode             # current value "hermes_graph_agent"
}

Product A0 trace `backend` / `runtime` / `mode` are taken from the selected
runtime's descriptor **before** `run()`. The default Hermes adapter preserves
the current labels. A non-Hermes descriptor must not be recorded as Hermes.
That is the A2→A3 comparison seam: same telemetry substrate, different
harness identity, no product-telemetry rewrite.

AgentCapabilityPolicy {
    policy_id              # current: "world_graph_read_v1"
}

AgentRunOptions {
    runtime_session_id?    # harness continuation identity, not thread identity
    execution_root?        # server-selected current graph execution root
}

AgentRuntimeInvocation {
    thread_id
    turn_id
    message
    conversation_history[]
    context_packet         # bounded DMB-owned data, see §2.4
    capability_policy
    run_options
}

AgentRuntimeToolEvent {
    tool_name
    state                  # start | completion | error
    duration_ms?
    attributes             # bounded safe capability metadata; no raw args/result
}

AgentRuntimeResult {
    status                 # ok | error
    final_text?
    messages[]             # bounded current compatibility only
    runtime_session_id?
    answer_scope?
    tool_events[]
    model_calls[]          # A0 normalized call records; do not reinterpret
    telemetry_warnings[]
    observed_model_call_count?
    context_updates        # bounded returned session/context metadata if needed
    runtime_metadata       # process isolation / worker pid, no secrets
    error_code?
    error_message?
}

class AgentRuntime(Protocol):
    descriptor: AgentRuntimeDescriptor
    def run(self, invocation: AgentRuntimeInvocation) -> AgentRuntimeResult: ...
```

Do **not** create an asynchronous handle facade that immediately blocks internally. Synchronous v1 is honest.

## 2.4 Current context packet

A2 is not the general ContextAssembler slice.

The invocation packet should carry only the current graph-Agent inputs that already exist, grouped without Hermes plugin/toolset vocabulary.

Directional shape:

```text
context_packet {
  world_scope {
    world_id
    campaign_id
    focus
    admissibility
    revision_id
  }

  retrieval_session {
    session_id
    packet
  }
}
```

Rules:

- world scope is already resolved before runtime dispatch;
- no adapter may infer current head from client files or conversation;
- the existing retrieval-session packet may be reused in A2 even if a helper is historically named `project_for_hermes`; do not turn A2 into a GraphRetrievalSession naming/migration PR;
- `execution_root` stays server-selected in run options and is not model-visible;
- conversation history remains bounded and role/content-only under current validation;
- no surface/Play/selection context is invented here — later ContextAssembler work will extend the packet.

## 2.5 Capability policy

A2 moves **policy selection**, not every tool implementation, above the harness adapter.

Current policy identity:

```text
world_graph_read_v1
```

Meaning:

```text
read-only current graph interaction capability
+ explicit conversation-context declaration capability
+ current exact Threat hydration read where already part of the model-visible surface
no terminal
no web
no filesystem discovery
no write effect
```

The generic contract must not contain Hermes plugin IDs, Hermes toolset names, or Hermes registry types.

The Hermes adapter maps `world_graph_read_v1` + the resolved world scope to the current explicit `HermesCapabilityPolicy` / `default_graph_only_capability_policy(...)` and passes it **non-null** into the existing Hermes request.

Unsupported policy ID:

```text
fail closed
→ typed AgentRuntimeResult error
→ host.execute NOT called
```

Do not broaden capability policy as a fallback.

The current DMB graph interaction implementation remains where it is in A2. Renaming `hermes_graph_interaction_tools.py`, moving graph plugins, or designing a portable ToolSpec/executor system is not required to prove this boundary and would collide with future CUTOVER/demolition decisions.

## 2.6 Hermes adapter mapping

The adapter may import:

```text
hermes_graph_agent_contract
hermes_graph_agent_host
src/graph_memory/hermes_graph_plugin policy types/factory
```

The product orchestration modules may not.

Directional mapping:

```text
AgentRuntimeInvocation
  message                → HermesGraphAgentTurnRequest.question
  context.world_scope    → world/campaign/focus/admissibility/revisionPin
  conversation_history   → conversationHistory
  run_options.session    → sessionId
  run_options.root       → root
  policy_id + scope      → explicit HermesCapabilityPolicy
  retrieval session      → retrievalSessionId / retrievalSession

HermesGraphAgentTurnResult
  status                 → status
  final_response         → final_text
  hermes_session_id      → runtime_session_id
  answer_scope           → answer_scope
  tool_events            → AgentRuntimeToolEvent + bounded attributes
  model_calls            → model_calls unchanged
  telemetry_warnings     → telemetry_warnings unchanged
  observed count         → observed_model_call_count unchanged
  retrieval session      → context_updates where still required
  process isolation      → runtime_metadata.process_isolation
  host worker pid        → runtime_metadata.worker_pid
  error                  → error_code / error_message
```

Tool-event attributes needed by current grounding may include only the current safe metadata:

```text
world_id
campaign_id
focus
admissibility
revision_pin
bounded_ids
retrieval_schema
outcome
matched_node_ids
relationship_ids
source_anchor_ids
diagnostic_codes
```

No raw tool args or raw tool result enters `AgentRuntimeToolEvent`.

## 2.7 Trace contract stays authoritative

A2 does not create `dmb_agent_turn_trace_v2`.

For current Hermes turns, the returned trace must retain current values and semantics:

```text
schema=dmb_agent_turn_trace_v1
backend=hermes
runtime=process_isolated
mode=hermes_graph_agent
same trace_id / agent_thread_id / turn_id semantics
same whole-turn elapsed semantics
same product spans
same model_calls[] ordering and statuses
same usage/cost aggregation
same model_calls_truncated / observed count behavior
same tool event projection
same conversation/session diagnostics
```

The `harness_turn` product span wraps exactly one `runtime.run(...)` call.

Do not create a second adapter span around it unless it represents separately measured product work with a useful name.

The adapter must **not** recompute:

```text
provider
model
tokens
cache counts
reasoning tokens
cost
model-call durations
retry status
```

Those remain A0 normalized telemetry from the runtime observation path.

---

# 3. Implementation shape

## 3.1 Desired call path after A2

```text
process_live_query(query_backend="hermes")
  ↓
DungeonBuddy product validation / World context resolution
  ↓
run_hermes_graph_query(...)                 # historical product mode name retained
  ↓
build AgentRuntimeInvocation
  ↓
resolve DMB capability policy id
  ↓
AgentRuntime.run(invocation)                # one harness-neutral seam
  ↓
  default: HermesAgentRuntimeAdapter
      ↓
      map invocation → Hermes wire request
      ↓
      unchanged HermesGraphAgentHost.execute
      ↓
      map Hermes result → AgentRuntimeResult
  ↓
DungeonBuddy scope checks / grounding / citations / response projection
  ↓
AgentTurnTraceBuilder finalization
  ↓
existing response + A1 inspector
```

## 3.2 Internal injection

A2 needs a deterministic way to replace the default runtime **inside tests and future experiments** without adding a public runtime selector.

Acceptable patterns include:

```python
process_live_query(..., agent_runtime=runtime)
```

or a narrower injection into `run_hermes_graph_query(...)`.

Requirements:

- public route schema unchanged;
- no request field selects runtime;
- production default remains Hermes;
- fake runtime proves product code is not secretly reaching around the port to the Hermes host;
- A3 can reuse the internal seam for an experiment without editing grounding logic.

## 3.3 Historical naming

A2 may retain these compatibility names:

```text
query_backend="hermes"
run_hermes_graph_query
HermesSessionPointerStore
response.hermes_session
hermes_session_pointer request field
```

They are current API/product compatibility, not the new generic contract.

Inside the runtime boundary, use `runtime_session_id`, not `hermes_session_id`.

Do not mix a public API rename into A2. A future surface/API cleanup may remove historical naming after more than one runtime exists.

## 3.4 Model selection

A2 does not redesign model policy.

The current Hermes integration is DungeonBuddy-owned code and already pins OpenAI/provider/model policy rather than accepting ambient Hermes CLI defaults. Keep that behavior unchanged.

A3 must compare harnesses on the same explicitly resolved model where practical. If A3 proves that model resolution must be hoisted into a new cross-runtime policy object, that is evidence for a bounded successor change. Do not pre-build a model registry in A2.

The actual provider/model used remains observable through A0 model-call telemetry.

---

# 4. Exclusive implementation write lease

The paths below are the **exclusive A2 write lease**. Re-check current open PRs before dispatch.

## 4.1 Create

```text
apps/live_control_server/services/agent_runtime.py
apps/live_control_server/services/hermes_agent_runtime.py
tests/test_agent_runtime.py
tests/test_hermes_agent_runtime.py
```

## 4.2 Modify

```text
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/services/hermes_graph_query.py
tests/test_live_query_hermes_graph.py
tests/test_live_control_server.py
Docs/Plans/HANDOFF-AGENT-INTERACTION-trace-inspector-v1.md
Docs/Plans/HANDOFF-AGENT-INTERACTION-agent-runtime-boundary-v1.md
```

## 4.3 Read-only evidence / dependencies

```text
apps/live_control_server/services/agent_turn_trace.py
apps/live_control_server/services/hermes_graph_agent_contract.py
apps/live_control_server/services/hermes_graph_agent_host.py
apps/live_control_server/services/hermes_graph_agent.py
src/graph_memory/hermes_graph_plugin.py
src/graph_memory/hermes_graph_interaction_tools.py
MODEL_POLICY.json
apps/live_control_server/routes/live.py
tests/test_hermes_graph_agent.py
tests/test_hermes_graph_agent_host.py
```

## 4.4 Steward-authorized test-only exception

`tests/test_live_control_server.py` is explicitly authorized for A2.

The original dispatch text permitted one extra test file only when the owning public-response proof was absent from `tests/test_live_query_hermes_graph.py`. Review Cycle 1 (`5048841605`, head `a72f49c9954d8618c22647b757b9b7e6aa2f33e2`) found that the service journey is also covered there, so the implementation could not self-authorize the path.

The steward now authorizes this path because the FastAPI `/query` route is the owning HTTP public-response boundary for citation/focus payload and for the host monkeypatch after `get_hermes_graph_agent_host` moved into the adapter. The graph-query suite covers the service journey; it does not own the HTTP response shape. This file also moves from §4.3 read-only evidence into §4.2 Modify.

This handoff itself is leased so the amendment is in-lease rather than a silent extra path.

No production-path exception exists.

## 4.5 Explicitly out of scope / do not edit

```text
apps/live-control-ui/**
apps/live_control_server/routes/**
apps/live_control_server/integrations/dungeonmind/**
src/application_state/**
src/graph_memory/**
pyproject.toml
uv.lock
package.json / pnpm lockfiles
MODEL_POLICY.json
migrations / DB schema
Play Surface files
CUTOVER authority/integration files
```

`src/graph_memory/**` is intentionally read-only in A2 even though the Hermes adapter consumes current graph plugin types. Do not use the runtime abstraction as a reason to refactor graph-memory implementation while CUTOVER/D.3 sequencing is active.

If any out-of-scope production path becomes necessary, stop under §12.

---

# 5. Required implementation behavior

## 5.1 Generic contract must not import Hermes

`agent_runtime.py` must not import:

```text
hermes_graph_agent_contract
hermes_graph_agent_host
hermes_graph_agent
hermes_graph_plugin
NousResearch/Hermes packages
```

It may use stdlib / generic DungeonBuddy typing only.

The contract should remain importable in a process that does not import Hermes.

## 5.2 Product orchestration must not import Hermes host/wire types

After A2:

```text
live_agent_loop.py
hermes_graph_query.py
```

must not import:

```text
HermesGraphAgentHost
HermesGraphAgentTurnRequest
HermesGraphAgentTurnResult
HermesGraphToolEvent
```

Historical product helper/module names containing `hermes` do not violate this invariant by themselves; the dependency direction does.

## 5.3 Adapter owns translation, not product truth

The Hermes adapter may transform naming/shape only.

It may not:

- resolve World scope;
- choose current World revision;
- broaden campaign/world lens;
- read admitted recap files;
- create GraphRetrievalSession;
- decide grounding state;
- create citations;
- persist continuity pointer;
- finalize trace;
- silently add capabilities absent from the DMB policy.

## 5.4 Scope must fail closed twice

Current protection remains layered:

```text
DMB invocation contains resolved authoritative scope
  ↓
Hermes capability policy maps/injects that scope for tool dispatch
  ↓
product response grounding re-checks returned tool-event scope
```

A2 must not remove the final product check merely because the adapter supplied the policy.

Adversarial runtime result with a foreign world/campaign/revision/focus must still be rejected/filtered under existing product behavior.

## 5.5 Runtime session identity remains subordinate

```text
agent_thread_id = DungeonBuddy product conversation identity
turn_id         = DungeonBuddy product turn identity
runtime_session_id = harness continuation identity
```

Never use runtime session identity as the thread key.

Current `HermesSessionPointerStore` remains the compatibility persistence/validation boundary for the default Hermes adapter. A2 only changes the internal name crossing `AgentRuntime`.

## 5.6 Error behavior

The generic result must support current typed failures without raising a new class of unhandled exception for ordinary harness failure.

Examples:

```text
worker timeout
worker lost
worker protocol error
credentials missing
Hermes import/init failure
malformed harness result
unsupported capability policy
```

Existing host/embedded errors map into `AgentRuntimeResult(status="error", ...)` and then through current product classification.

Unexpected programming/invariant exceptions may still raise where current code raises; A2 does not swallow all exceptions behind a generic "runtime failed" message.

## 5.7 Telemetry fail-open behavior remains

The adapter must carry partial telemetry even on runtime error.

At minimum preserve:

```text
model_calls
telemetry_warnings
observed_model_call_count
runtime_metadata.process_isolation
runtime_metadata.worker_pid when known
```

A timeout/lost-worker result that currently retains streamed model-call observations must still retain them after adapter mapping.

## 5.8 No public runtime selection

Do not add:

```text
runtime=pydantic
runtime=hermes
agent_runtime request field
runtime dropdown
env-driven automatic challenger selection
```

Production default is unconditionally the current Hermes adapter in A2.

Internal dependency injection is not a public selector.

---

# 6. Required adversarial proofs

A2 is mergeable only with deterministic proofs for the boundary, not merely existing Hermes regressions.

## 6.1 Fake-runtime product proof

Using a fake `AgentRuntime` with **no Hermes host/process**:

```text
resolved current scope
+ final text
+ in-scope graph tool completion
+ normalized model-call telemetry
→ current product grounding/citations/response/trace succeeds
```

Assert runtime is called exactly once.

This test is the primary proof that product orchestration actually consumes the new port.

## 6.2 Foreign-scope fake runtime

Fake runtime returns a completion event whose attributes assert a foreign:

```text
world_id
campaign_id
revision_pin
or focus
```

Existing product fail-closed behavior must remain. The runtime boundary is not trusted as World authority.

## 6.3 Runtime error with partial model telemetry

Fake/runtime-adapter result:

```text
status=error
one completed model call
one telemetry warning
observed count known
```

Final A0 trace must retain that call/warning/count and remain error/partial as appropriate. No fabricated zero usage/cost.

## 6.4 Hermes adapter invocation mapping

With a fake host:

- `message` maps exactly to question;
- world/campaign/focus/admissibility/revision map exactly;
- current retrieval session id/packet maps exactly;
- conversation history remains role/content-only;
- runtime session maps to Hermes session id input;
- server-selected absolute root maps exactly;
- `capability_policy` passed to Hermes request is non-null;
- policy visible tool surface remains the current graph-only/read-only surface;
- host called exactly once.

## 6.5 Unsupported capability

Invocation contains unknown policy id.

Expected:

```text
AgentRuntimeResult.status = error
stable adapter error code
host.execute call count = 0
no capability broadening
```

## 6.6 Adapter result mapping

Fake Hermes host result containing:

```text
runtime session id
tool start + completion
process isolation
worker pid
model-call retry/error + success
telemetry warning
observed model call count
answer scope
retrieval-session metadata
```

maps to generic result without losing or recomputing values.

## 6.7 Timeout/lost-worker regression

Existing `tests/test_hermes_graph_agent_host.py` remains green, including A0 proofs that completed streamed model observations survive timeout/lost worker/protocol failures.

A2 should not rewrite those host tests unless a real regression is discovered; host is read-only under this lease.

## 6.8 No-Hermes import characterization

Add a focused source/import test proving:

```text
agent_runtime.py imports no Hermes modules
hermes_graph_query.py imports no Hermes host/wire contract module
live_agent_loop.py imports no Hermes host/wire contract module
```

Do not use a brittle repository-wide ban: Hermes implementation modules are expected to import Hermes types.

## 6.9 Trace compatibility

For one fixed runtime result, assert the product trace still exposes current A0 semantics:

```text
schema dmb_agent_turn_trace_v1
backend hermes
runtime process_isolated
mode hermes_graph_agent
provider/model from model call
aggregate usage/cost unchanged
same model-call ordering
same tool-event safe projection
same thread/turn identity
```

A2 does not need byte-identical random IDs/timestamps. It does need semantic equivalence.

## 6.10 Continuity

At least one existing/current test must prove:

```text
accepted runtime session pointer
→ runtime receives continuation session id
→ runtime result supplies new/current runtime session id
→ product persists current opaque Hermes pointer behavior
```

The generic contract must not expose `hermes_session_id` as its field name.

---

# 7. Required verification / merge evidence

Run from repository root unless command says otherwise.

## 7.1 New boundary suites

```bash
uv run pytest tests/test_agent_runtime.py -q
uv run pytest tests/test_hermes_agent_runtime.py -q
```

## 7.2 Owning product regression

```bash
uv run pytest tests/test_live_query_hermes_graph.py -q
```

The steward-authorized HTTP public-response suite is required:

## 7.3 Existing harness/host regression — read-only implementation

```bash
uv run pytest tests/test_hermes_graph_agent.py -q
uv run pytest tests/test_hermes_graph_agent_host.py -q
```

These prove the adapter did not require a hidden rewrite of the accepted Hermes mechanics.

## 7.4 Route/public regression

Run the current bounded live-control route suite that exercises `process_live_query` / Hermes route behavior without modifying route production code. At design time:

```bash
uv run pytest tests/test_live_control_server.py -q
```

If that suite is materially too broad or has a known base failure, use §7.7 rather than silently skipping it.

## 7.5 Static / patch hygiene

```bash
uv run ruff check \
  apps/live_control_server/services/agent_runtime.py \
  apps/live_control_server/services/hermes_agent_runtime.py \
  apps/live_control_server/services/live_agent_loop.py \
  apps/live_control_server/services/hermes_graph_query.py \
  tests/test_agent_runtime.py \
  tests/test_hermes_agent_runtime.py \
  tests/test_live_query_hermes_graph.py \
  tests/test_live_control_server.py

git diff --check
git diff --name-only <dispatch-base>...HEAD
```

The final changed-path list must be a subset of the amended §4 lease, including the steward-authorized HTTP suite and this handoff.

## 7.6 Minimal live dogfood

If current credentials/runtime are available:

1. Run the same Plan Agent / Hermes graph journey used for A0/A1 dogfood.
2. Ask a graph-grounded question that requires at least one graph tool.
3. Confirm answer/grounding/citations still behave normally.
4. Open Advanced diagnostics.
5. Confirm:
   - backend `hermes`;
   - runtime `process_isolated`;
   - exact provider/model;
   - model-call rows;
   - tokens/cache/cost;
   - product spans including `harness_turn`;
   - tool outcome/duration;
   - no new generic-runtime noise in frontstage answer.
6. Confirm server trace/log uses the same `trace_id`.

If live credentials are unavailable, record `BLOCKED_DEPENDENCY` for this dogfood only. Deterministic boundary tests remain mandatory.

## 7.7 Baseline failure protocol

For any required command failing on dispatch base, run the identical command against base and head and record exact error tuples/counts.

Do not label the gate PASS without:

```text
head fixed the failure
or
base has the identical failure + explicit operator waiver
```

No silent baseline forgiveness.

---

# 8. Expected nano-commit story

Exact count is not contractual. A clean review story is:

```text
1. AGENT-INTERACTION: add harness-neutral AgentRuntime contract
2. AGENT-INTERACTION: adapt current Hermes host to AgentRuntime
3. AGENT-INTERACTION: route graph-Agent product orchestration through runtime
4. AGENT-INTERACTION: prove scope, telemetry, continuity, and import boundaries
5. AGENT-INTERACTION: sync completed A1 predecessor state
```

Review Cycle 2 expected commits against the Cycle 1 head:

```text
6. AGENT-INTERACTION: derive A0 trace identity from runtime descriptor
7. AGENT-INTERACTION: steward-authorize live-control-server test lease
```

Do not mix PydanticAI, ContextAssembler, Interaction Memory, tool relocation, UI work, or CUTOVER work into these commits.

---

# 9. Required backward-looking A1 state sync

Before implementation is handed back for review, update:

```text
Docs/Plans/HANDOFF-AGENT-INTERACTION-trace-inspector-v1.md
```

with only facts that are now true:

```text
A1 status: COMPLETE / MERGED
PR: #656
accepted head: 057b2efee4b68d8324111874cee617448dd38f8b
merge SHA: f075740b167b7031f797c5643c32ea206c416f85
formal review cycles: 4
A2: active successor represented by this implementation PR
A3 PydanticAI: not started / still false
```

Do not invent A2's future merge SHA or final review count.

No stable architecture-authority edit is required merely to land the port: the current authority already says Agent Interaction owns `AgentRuntime` and the harness is client-owned orchestration.

---

# 10. Required CODE → REVIEW handback

The handback must include:

1. exact PR URL / branch / head SHA;
2. exact dispatch base SHA;
3. §1 mission + merge-ready invariant copied exactly;
4. nano-commit list and purpose per commit;
5. actual changed-path list + diff stat;
6. active PR/write-lease recheck at dispatch and handback;
7. exact A1 predecessor facts: #656 / accepted head / merge SHA / 4 cycles;
8. before/after dependency diagram showing where Hermes host/wire imports moved;
9. final `AgentRuntime` Protocol and DMB invocation/result/tool-event shapes;
10. exact DMB capability-policy shape and current policy id;
11. proof unsupported policy fails before host call;
12. exact Hermes adapter mapping table;
13. proof real product modules no longer import Hermes host/wire types;
14. fake-runtime product proof and exact runtime call count;
15. foreign-scope adversarial result proof;
16. partial/error telemetry preservation proof;
17. timeout/lost-worker host regression result;
18. continuity runtime-session mapping proof;
19. exact A0 trace compatibility fixture/result;
20. confirmation tokens/cost/model are not recomputed in adapter/product;
21. confirmation public API / `query_backend="hermes"` is unchanged;
22. confirmation no runtime selector exists;
23. all §7 commands with exact totals/provenance;
24. manual dogfood result or `BLOCKED_DEPENDENCY`;
25. baseline failures/waivers (`none` when none);
26. paths outside §4 (`none` after the Cycle 1 steward lease amendment);
27. stop conditions encountered (`none` when none);
28. A1 predecessor sync diff;
29. successors still false: A3 PydanticAI, general ContextAssembler, Interaction Memory durability, runtime lifecycle API.

---

# 11. Acceptance rubric

Accept only when every item is true:

- [ ] Exactly one capability shipped: a real DungeonBuddy-owned AgentRuntime execution boundary around current Hermes execution.
- [ ] `agent_runtime.py` contains no Hermes imports/types.
- [ ] Product orchestration contains no Hermes host/wire request/result/tool-event imports.
- [ ] Hermes adapter is the translation owner.
- [ ] Existing Hermes host/embedded runtime/plugin implementation was not modified.
- [ ] DMB chooses a named capability policy before adapter execution.
- [ ] Adapter maps current policy to explicit non-null Hermes capability policy.
- [ ] Unsupported policy fails closed before host call.
- [ ] World scope remains product-resolved and product-revalidated.
- [ ] Fake runtime drives real product grounding/response projection without Hermes.
- [ ] Runtime called exactly once per product turn.
- [ ] Runtime session identity stays distinct from Agent thread identity.
- [ ] Current opaque Hermes pointer continuity remains correct.
- [ ] Model calls / warnings / observed count survive adapter mapping unchanged.
- [ ] Worker timeout/lost/protocol partial telemetry behavior remains green.
- [ ] A0 `dmb_agent_turn_trace_v1` semantics remain unchanged for Hermes.
- [ ] A1 inspector receives/renderable trace remains unchanged.
- [ ] No tokens/cost/model identity are recomputed above A0 telemetry.
- [ ] Public response shape and `query_backend="hermes"` remain compatible.
- [ ] No UI runtime selector exists.
- [ ] No PydanticAI dependency/import exists.
- [ ] No cancellation/resume/steer/stream lifecycle is falsely claimed.
- [ ] No APP-STATE, World authority, Play, or CUTOVER behavior changes landed.
- [ ] A1 predecessor sync is truthful and backward-looking.

---

# 12. Stop conditions

Stop and report rather than expanding if any becomes true:

- satisfying A2 requires modifying `hermes_graph_agent.py`, `hermes_graph_agent_host.py`, or `hermes_graph_agent_contract.py` rather than adapting the accepted interface;
- satisfying A2 requires modifying `src/graph_memory/**` or moving/renaming current graph tool implementations;
- satisfying A2 requires a new public request/response field or runtime selector;
- satisfying A2 requires UI code;
- satisfying A2 requires a dependency or lockfile change;
- satisfying A2 requires a DB/migration/persistence change;
- satisfying A2 requires DungeonMind integration/authority changes;
- a contested path from current #651/#657 or another active lane becomes necessary;
- the generic contract must include Hermes plugin/toolset/registry types to function;
- the adapter can only work by broadening missing capability/scope data;
- normalized A0 token/cost telemetry must be recomputed in the adapter;
- a second harness must be implemented to prove the boundary;
- cancellation/resume/steering/streaming must be invented to satisfy current product behavior;
- more than one independently useful capability appears.

Stop report:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```

---

# 13. Named successor sequence

```text
A0  Agent Turn Trace v1                          MERGED #654
    measuring instrument / model-call truth
    ↓
A1  Advanced Agent Trace Inspector v1            MERGED #656
    safe continuity + advanced inspection
    ↓
A2  DungeonBuddy AgentRuntime Boundary v1        THIS HANDOFF
    product-owned execution port + Hermes adapter
    ↓
A3  PydanticAI Adapter Experiment                NOT STARTED
    same product journey / same context / same model where practical
    same A0 trace truth / same grounding policy
    compare harness adaptation burden with evidence
    ↓
later, evidence-selected
    runtime lifecycle extension if challenger proves need
    ContextAssembler + Interaction Memory instrumentation
    durable Agent APP-STATE only if reload correctness earns it
```

A3 is explicitly not a migration commitment.

Its success question remains:

> **How much DungeonBuddy code has to bend because the harness wants something?**

The A2 contract is good only if A3 can answer that question without rewriting product grounding, World scope, continuity governance, or telemetry.

A0 trace identity (`backend` / `runtime` / `mode`) must follow the selected runtime's `AgentRuntimeDescriptor`. Hard-coding Hermes labels in `process_live_query()` would force A3 to rewrite product telemetry to compare harnesses.

---

# 14. A3 comparison questions A2 must make measurable

A2 should leave a seam from which A3 can compare, without implementing the challenger yet:

```text
adapter LOC / special cases
runtime startup overhead
model-call latency
harness overhead outside provider time
tool invocation count / duration
retry/error representation
crash ambiguity / partial telemetry
context packet translation complexity
capability-policy translation complexity
session/continuity ergonomics
test-double complexity
trace integration complexity
amount of product code changed per adapter
```

A0/A1 already provide the measurement substrate.

Do not add another observability system in A2.

---

# 15. Reviewer decision rule

A2 passes when a reviewer can truthfully say:

> “The current Agent product journey still behaves like the accepted Hermes journey, but DungeonBuddy now talks to one runtime port instead of Hermes host/wire types. Hermes is an adapter, not the product architecture. The abstraction did not steal World/context/grounding/telemetry authority, and nothing about PydanticAI or future lifecycle behavior has been pre-decided beyond what the next experiment needs.”

Anything weaker is a wrapper, not the boundary this slice is intended to establish.
