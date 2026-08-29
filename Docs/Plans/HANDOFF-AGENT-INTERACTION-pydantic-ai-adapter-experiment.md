---
pr_body_template: |
  ## Handoff pointer
  - Workstream: AGENT-INTERACTION / A3
  - Flow: AGENT-INTERACTION
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-AGENT-INTERACTION-pydantic-ai-adapter-experiment.md`
  - Design base: `937d9dce1be02e804553282a146527bf39bb0750`
  - Predecessor: A2 / PR #659 / merge `937d9dce1be02e804553282a146527bf39bb0750`

  ## Mission
  Implement one PydanticAI-backed challenger behind the merged DungeonBuddy `AgentRuntime` boundary and compare it against the accepted Hermes journey without making PydanticAI a production runtime, changing public runtime selection, weakening World/tool authority, or hiding observability gaps.

  ## Merge contract
  - production default remains Hermes and public `query_backend="hermes"` is unchanged
  - PydanticAI is reachable only through the existing internal `agent_runtime=` injection seam
  - same DMB World scope, capability policy, retrieval session, model-visible graph-tool schemas, graph-tool executor, grounding, citations, and A0 trace consumer are reused
  - model/provider parity uses the same resolved OpenAI model where current dependency constraints permit
  - every PydanticAI provider request becomes one A0 model-call observation with truthful timing/usage/cost status
  - tool calls produce the existing harness-neutral `AgentRuntimeToolEvent` shape and remain product-revalidated
  - current PydanticAI 2.x dependency incompatibility with the accepted Hermes/OpenAI pin is recorded as experiment evidence, not solved by upgrading Hermes
  - no runtime selector, UI, APP-STATE, lifecycle API, Interaction Memory, graph write path, or PydanticAI migration lands
  - handback contains the required comparison scorecard and an evidence-based disposition; merge does not imply adoption
---

# HANDOFF — PydanticAI AgentRuntime Adapter Experiment (A3)

**Created:** 2026-08-28  
**Status:** IMPLEMENTATION HANDED BACK FOR REVIEW — experiment evidence in §21
**Canonical handoff path:** `Docs/Plans/HANDOFF-AGENT-INTERACTION-pydantic-ai-adapter-experiment.md`  
**Design branch:** `agent/pydantic-ai-adapter-experiment-design`  
**Design base:** `937d9dce1be02e804553282a146527bf39bb0750`  
**Workstream:** `AGENT-INTERACTION / A3`  
**Flow / owner:** `AGENT-INTERACTION`  
**Predecessor:** A2 — DungeonBuddy AgentRuntime Boundary v1  
**Predecessor PR:** #659  
**Accepted predecessor head:** `a8978330fd1334de7ae32170bcb6ff479da2bce8`  
**Predecessor merge:** `937d9dce1be02e804553282a146527bf39bb0750`  
**Predecessor formal review cycles:** 2  

---

# 0. Re-anchor: what is true now

A0, A1, and A2 are no longer design hypotheses.

```text
A0  Agent Turn Trace v1                    MERGED #654
    every Agent turn has DMB-owned trace truth
    model calls / timing / tokens / cache / cost / tools
    ↓
A1  Advanced Agent Trace Inspector         MERGED #656
    safe trace truth survives projection/persistence/reload
    advanced UI stays opt-in
    ↓
A2  DungeonBuddy AgentRuntime Boundary     MERGED #659
    product orchestration talks to AgentRuntime
    Hermes is one adapter, not the product architecture
    ↓
A3  PydanticAI Adapter Experiment          THIS SLICE
    one real challenger, same DMB contracts, measured honestly
```

The merged A2 execution direction is:

```text
DungeonBuddy product orchestration
  owns scope / retrieval session / continuity governance / grounding / trace
        ↓
AgentRuntimeInvocation
        ↓
AgentRuntime.run(...)
        ↓
current default: HermesAgentRuntimeAdapter
        ↓
AgentRuntimeResult
        ↓
DungeonBuddy grounding / citations / response / A0 trace
```

`AgentRuntimeDescriptor` is now a real observability seam. The selected runtime supplies:

```text
runtime_id
trace_backend
trace_runtime
trace_mode
```

and A0 trace/provenance identity follows that descriptor rather than hard-coded Hermes labels.

That gives A3 a clean question:

> **How much DungeonBuddy code has to bend because PydanticAI wants something?**

A3 is an experiment answering that question. It is not a migration decision disguised as an adapter PR.

---

# 1. Mission and merge-ready invariant

## 1.1 Mission

Implement one **PydanticAI-backed challenger** behind the merged DungeonBuddy `AgentRuntime` port and run the current read-only World Graph Agent journey through it using the same DungeonBuddy-owned authority and observability contracts as Hermes.

The slice must produce enough deterministic evidence to compare the harnesses without changing the production default.

## 1.2 Merge-ready invariant

For one internally injected PydanticAI runtime:

```text
same DMB AgentRuntimeInvocation
+ same resolved authoritative World scope
+ same world_graph_read_v1 policy
+ same retrieval-session identity / packet
+ same model-visible graph-tool schemas
+ same DMB graph-tool executor
+ same resolved OpenAI model where dependency constraints permit
        ↓
PydanticAI tool/model loop
        ↓
DMB AgentRuntimeResult
        ↓
existing product grounding / citations / A0 trace
```

must work without modifying the merged `AgentRuntime` contract or product orchestration.

At merge:

- Hermes remains the unconditional production default;
- `query_backend="hermes"` remains the only current public Agent backend name;
- no runtime request field, feature flag, dropdown, environment selector, or automatic challenger routing exists;
- PydanticAI is invoked only by internal dependency injection / deterministic tests / explicit local experiment code;
- no World truth, admissibility, grounding, citation, or write authority moves into PydanticAI;
- no A0 trace semantics are weakened to accommodate missing harness telemetry;
- the PR carries an explicit comparison scorecard and disposition;
- merging the PR means **“the experiment is reproducible”**, not **“PydanticAI is selected.”**

---

# 2. Why A3 now, and why only one challenger

A2 deliberately stopped after the execution port. That was correct: a second abstraction layer built before a second harness would have been speculative.

A3 now supplies the missing evidence.

Do not add NanoBot, Pi, LangGraph, OpenAI Agents SDK, or another challenger to this slice. Hermes + PydanticAI is enough to reveal whether the boundary is real.

The comparison is useful only if most DungeonBuddy behavior stays fixed.

```text
FIXED
  product journey
  World scope
  retrieval session
  DMB capability id
  graph tool schemas
  graph tool implementation
  grounding / citation validation
  trace schema
  model family / provider where practical

VARIABLE
  harness / adapter implementation
```

---

# 3. Dependency reality discovered during design

This is a first-class experiment result and must remain visible in the implementation handback.

DungeonBuddy currently pins:

```text
openai==2.24.0
hermes-agent @ git+https://github.com/NousResearch/hermes-agent.git@861d69c7...
```

The OpenAI pin is an accepted Hermes compatibility gate and **must not move in A3**.

Upstream PydanticAI compatibility was checked during design:

```text
pydantic-ai-slim 2.36.0  openai extra → openai>=3.0.0
pydantic-ai-slim 2.0.0   openai extra → openai>=2.29.0
pydantic-ai-slim 1.70.0  openai extra → openai>=2.25.0
pydantic-ai-slim 1.66.0  openai extra → openai>=2.11.0
```

Therefore current PydanticAI 2.x cannot coexist with the accepted `openai==2.24.0` environment without changing the Hermes dependency gate.

A3 will **not** solve that conflict.

## 3.1 Experiment dependency pin

Use exactly:

```text
pydantic-ai-slim[openai]==1.66.0
```

for the executable challenger experiment.

Reason:

- it is the newest design-time-verified PydanticAI tag that admits the accepted OpenAI 2.24 pin;
- it has the core Agent/tool/model abstractions needed for this experiment;
- its `Tool.from_schema(...)` can consume the existing DMB JSON tool schemas;
- its `WrapperModel` provides a supported model-request interception seam for A0 request-level telemetry.

This is **not** a recommendation to adopt PydanticAI 1.66 for production.

The required experiment conclusion must distinguish:

```text
harness fit
from
dependency freshness / coexistence fit
```

A harness can be architecturally attractive while still having a current dependency blocker.

## 3.2 Dependency stop rule

`uv lock` / `uv sync` may add the exact PydanticAI dependency and its normal transitives.

Stop rather than silently broadening scope if resolution requires changing any accepted direct dependency version to make PydanticAI install, especially:

```text
openai==2.24.0
hermes-agent pin
DungeonMind pin
Python constraint
```

Do not “temporarily” upgrade OpenAI to prove PydanticAI 2.x works. That compares a harness change plus a Hermes dependency migration and destroys the experiment.

Record current-2.x incompatibility as a scorecard finding instead.

---

# 4. Authority boundaries remain unchanged

## 4.1 DungeonBuddy still owns

```text
thread identity
turn identity
resolved World/campaign/focus/revision/admissibility
retrieval-session creation
DMB capability policy id
conversation-history selection
system behavior policy
model policy intent
product tool implementations
continuity governance
answer grounding
citations
A0 trace schema / aggregation / cost policy
response projection
```

## 4.2 PydanticAI adapter may own only

```text
translate AgentRuntimeInvocation → PydanticAI Agent/model/tools/messages
run one synchronous AgentRuntime turn
record PydanticAI provider request observations
record PydanticAI tool-call observations
translate harness result → AgentRuntimeResult
```

It may not decide what World facts are authoritative.

## 4.3 DungeonMind remains World authority

Nothing in A3 changes the post-cutover ownership model.

The adapter is never allowed to:

- infer a different current World revision;
- broaden campaign/world scope;
- inspect arbitrary corpus or filesystem material;
- invent source admissibility;
- create World writes;
- treat model memory as World memory;
- bypass product grounding because PydanticAI returned plausible prose.

---

# 5. Fair-comparison policy

A3 is useful only if differences are attributable mostly to harness behavior.

## 5.1 Model/provider parity

Use the same DungeonBuddy-resolved OpenAI model as the current Hermes graph Agent where practical.

The current Hermes implementation resolves the model from existing DMB policy/fallback behavior and pins the provider to OpenAI.

For A3, reuse that current resolver **read-only** rather than introducing a second model registry or new environment variable.

The adapter may depend on the existing resolver for experiment parity even though its name currently contains `hermes`; this coupling must be counted in the scorecard.

Do not change `MODEL_POLICY` semantics in A3.

If the exact resolved model is unsupported by PydanticAI 1.66/OpenAI 2.24, stop and record that as a comparison result before substituting another model. A different-model fallback requires explicit steward amendment because model quality would become a second variable.

## 5.2 System-policy parity

The current graph-Agent behavioral policy is DungeonBuddy product policy even though it currently lives in `hermes_graph_agent.py`.

A3 should reuse the accepted policy text **read-only** for the experiment rather than copy/fork it or hoist it into a new architecture layer prematurely.

A PydanticAI-specific scope/capability block may differ where Hermes-only claims would be false. In particular, never claim PydanticAI is process-isolated or has Hermes plugin/toolset identities.

Semantic scope content must remain equivalent:

```text
worldId
campaignId
focus
admissibility
revisionPin
retrievalSessionId
initial candidates / claim ledger / available expansions
latest recap boundary / admitted excerpt when present
enabled model-visible tool names
```

Any read-only import of private Hermes-named DMB policy helpers is **comparison coupling** and must be counted, not hidden.

Do not extract/rename shared prompt policy in A3 merely to make the score prettier. If PydanticAI is selected later, a successor can hoist proven shared policy into neutral ownership.

## 5.3 Tool parity

Do not create a second World Graph tool implementation.

The accepted model-visible definitions currently come from:

```text
apps/live_control_server/services/hermes_graph_interaction_tools.py
```

and expose:

```text
declare_conversation_context
expand_graph_retrieval
read_graph_source
query_threat_mechanics_hydration
```

PydanticAI 1.66 supports `Tool.from_schema(...)`.

A3 should translate the existing DMB JSON definitions into PydanticAI tools and dispatch to the existing DMB executor rather than recreating schemas or retrieval code.

Current Hermes-specific naming is not a reason to rename these modules in the experiment. Count that coupling.

## 5.4 Capability enforcement parity

Invocation policy remains:

```text
world_graph_read_v1
```

Unknown policy id must fail before model execution.

For the accepted policy, PydanticAI may reuse the current read-only graph capability mapping/injection helpers so that model-supplied arguments cannot override authoritative scope/session identity.

At minimum:

```text
query_threat_mechanics_hydration
  server-authoritative world/campaign/focus/admissibility/revision

expand_graph_retrieval
read_graph_source
  server-authoritative retrievalSessionId

declare_conversation_context
  no graph scope required
```

No PydanticAI built-in web/code/filesystem tools are enabled.

Tool surface equality must be asserted by name and schema in deterministic tests.

## 5.5 Product revalidation remains mandatory

Even after adapter-side enforcement, existing product grounding must re-check returned tool-event scope.

A malicious/faulty PydanticAI runtime result asserting a foreign World/campaign/revision/focus must still fail closed under existing product behavior.

Do not weaken this because the harness tool wrapper “already knows the scope.”

---

# 6. Continuity semantics

A3 must not invent a PydanticAI session store.

PydanticAI can continue a conversation from explicit message history. The merged DMB invocation already contains bounded role/content history.

For the experiment:

```text
conversation_history
  → PydanticAI message_history translation
```

is sufficient.

`runtime_session_id` is optional in the generic contract. Do not fabricate an opaque PydanticAI session id solely to imitate Hermes.

Expected challenger result for the initial adapter:

```text
runtime_session_id = None
```

unless PydanticAI itself exposes a real opaque continuation identity that the adapter genuinely uses.

This means the existing public `hermes_session` compatibility pointer remains a Hermes production concern. A3 is internal injection only and does not redesign that API.

Comparison scorecard must explicitly record:

- Hermes: opaque runtime session pointer + role/content history;
- PydanticAI experiment: supplied message history, no harness session identity unless genuinely needed.

Do not turn this into APP-STATE work.

---

# 7. A0 observability is a hard requirement, not a nice-to-have

The challenger is not allowed to become an opaque execution path.

Every PydanticAI turn that reaches the provider must produce A0-compatible model-call observations.

## 7.1 Runtime descriptor

Use a truthful descriptor such as:

```text
AgentRuntimeDescriptor(
    runtime_id="pydantic_ai",
    trace_backend="pydantic_ai",
    trace_runtime="in_process",
    trace_mode="pydantic_ai_graph_agent",
)
```

Do not reuse Hermes trace labels.

## 7.2 Provider request timing

PydanticAI 1.66 exposes `WrapperModel` over `Model.request(...)`.

Use a supported request wrapper/interceptor, not global monkeypatching, to record each provider request attempt.

Each attempt needs:

```text
call_id
sequence
status
provider
requested_model
response_model when known
started_at
completed_at
duration_ms
safe request summary
usage
cost
error type/status when failed
```

If one tool loop causes three model requests, A0 must receive three model calls.

Do not collapse the whole Agent run into one synthetic provider call.

## 7.3 PydanticAI token semantics

PydanticAI 1.66 `RequestUsage` semantics are:

```text
input_tokens       = total prompt/input tokens
cache_read_tokens  = subset of input_tokens
cache_write_tokens = cache-write detail
output_tokens      = completion/output tokens
total_tokens       = input_tokens + output_tokens
```

This is already close to A0’s normalized convention.

Map it truthfully:

```text
A0 input_tokens              = RequestUsage.input_tokens
A0 cached_input_tokens       = RequestUsage.cache_read_tokens when known
A0 cache_write_input_tokens  = RequestUsage.cache_write_tokens when known
A0 uncached_input_tokens     = input - cache_read - cache_write only when those buckets are semantically known
A0 output_tokens             = RequestUsage.output_tokens
A0 reasoning_tokens          = only a provider-reported reasoning detail; never infer it
A0 total_tokens              = input + output
```

Never add cached tokens on top of `RequestUsage.input_tokens`; they are already a subset.

Never double-count reasoning tokens into output/total.

Use the existing DMB A0 normalization/cost helpers where they fit rather than introducing a second pricing table.

## 7.4 Cost

DungeonBuddy remains cost-policy owner.

For the same OpenAI model:

```text
known normalized usage + DMB price table → estimated
unknown price → unavailable
partial request observations → partial aggregate
```

Do not use a PydanticAI/genai-prices number as authoritative just because the library exposes one. It may be retained as comparison metadata only if safe and clearly non-authoritative.

## 7.5 Failed request preservation

If a provider request fails after earlier successful requests, return `AgentRuntimeResult(status="error")` with all already-observed model calls preserved.

The failed attempt itself should be represented with:

```text
status=error
usage=unavailable unless provider supplied real usage
cost=unavailable
truthful duration/error metadata
```

No fabricated zeros.

## 7.6 Tool telemetry

Each model-visible tool execution must produce ordered `AgentRuntimeToolEvent`s using the same safe projection vocabulary currently consumed by product grounding:

```text
tool_name
state = start | completion | error
duration_ms
attributes:
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

Do not put raw tool args/results into baseline telemetry.

Reuse accepted safe summarization helpers read-only where feasible. If they can only be reused by importing Hermes-named code, count the coupling.

## 7.7 A1 compatibility

A1 must require no UI changes.

The shared inspector should render the PydanticAI trace because A0 shape is unchanged and descriptor identity is generic.

No frontend files are leased in A3.

---

# 8. Retrieval-session result mapping

The product creates the `GraphRetrievalSession` before runtime execution.

The PydanticAI adapter must use the invocation’s exact retrieval-session id and must not create a parallel session.

After tool execution, return enough context update information for existing product hydration/validation to observe the same session state.

Preferred minimum:

```text
context_updates = {
  "retrieval_session_id": invocation.context_packet.retrieval_session.session_id
}
```

If the existing product path requires the packet too, project the updated existing session; do not manufacture a second ledger.

The adapter does not validate final graph claims. Product grounding still does that.

---

# 9. Exclusive implementation write lease

Re-check all open PRs immediately before dispatch.

At design time, active PRs #660, #661, and #662 are disjoint from this backend/dependency lane. #661 does touch frontend Agent Interaction files, so A3 must remain backend-only.

## 9.1 Create

```text
apps/live_control_server/services/pydantic_ai_agent_runtime.py
tests/test_pydantic_ai_agent_runtime.py
```

## 9.2 Modify

```text
pyproject.toml
uv.lock
Docs/Plans/HANDOFF-AGENT-INTERACTION-agent-runtime-boundary-v1.md
Docs/Plans/HANDOFF-AGENT-INTERACTION-pydantic-ai-adapter-experiment.md
```

The A3 handoff itself is leased so the implementation may append exact experiment evidence / handback facts without a separate documentation PR.

## 9.3 Read-only product contract / comparison dependencies

```text
apps/live_control_server/services/agent_runtime.py
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/hermes_agent_runtime.py
apps/live_control_server/services/agent_turn_trace.py
apps/live_control_server/services/hermes_graph_agent.py
apps/live_control_server/services/hermes_graph_interaction_tools.py
src/graph_memory/hermes_graph_plugin.py
src/graph_memory/interaction/**
src/agent/planner_pricing.py
tests/test_agent_runtime.py
tests/test_hermes_agent_runtime.py
tests/test_live_query_hermes_graph.py
tests/test_hermes_graph_agent.py
tests/test_hermes_graph_agent_host.py
```

## 9.4 Explicitly out of scope / do not edit

```text
apps/live-control-ui/**
apps/live_control_server/routes/**
apps/live_control_server/integrations/dungeonmind/**
src/application_state/**
src/graph_memory/**
apps/live_control_server/services/agent_runtime.py
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/hermes_agent_runtime.py
apps/live_control_server/services/hermes_graph_agent.py
apps/live_control_server/services/hermes_graph_interaction_tools.py
MODEL_POLICY.json / model-policy semantics
migrations / DB schema
Play Surface files
Plan Surface files
CUTOVER files
```

Yes: several read-only files are repeated here intentionally. They are the experiment’s measuring stick.

If PydanticAI cannot satisfy the merged contract without modifying them, that is a result. Stop and report rather than making the experiment pass by bending the product.

---

# 10. Required implementation shape

Directional only; exact helper names may differ.

```text
PydanticAIAgentRuntimeAdapter
  descriptor = pydantic_ai / in_process / pydantic_ai_graph_agent

  run(invocation):
    validate DMB policy id
    resolve same DMB OpenAI model
    map exact conversation history
    build truthful PydanticAI scope/system block
    translate existing JSON tool definitions with Tool.from_schema
    wrap tool execution:
      enforce authoritative scope/session
      time call
      execute existing DMB graph tool
      collect safe AgentRuntimeToolEvent
    wrap provider model:
      time every request
      normalize RequestUsage
      collect A0 model-call record
    execute one PydanticAI agent turn
    derive answer_scope from completed tools
    return AgentRuntimeResult
```

The adapter must be ordinary importable DungeonBuddy code, not a notebook/prototype script.

The production code path must not instantiate it automatically.

---

# 11. Required deterministic proofs

A3 is not mergeable with “the class imports.” It needs a real PydanticAI loop under deterministic model behavior.

Use PydanticAI’s supported test/function model facilities or an injected model factory. Do not make CI call OpenAI.

## 11.1 Dependency coexistence

Prove the resolved environment contains:

```text
pydantic-ai-slim == 1.66.0
openai == 2.24.0
existing Hermes pin unchanged
```

No accepted direct pin changed to make the solve work.

## 11.2 Descriptor identity

Injected PydanticAI adapter through the existing product service path yields:

```text
agent_trace.backend = pydantic_ai
agent_trace.runtime = in_process
agent_trace.mode = pydantic_ai_graph_agent
```

and is never labeled Hermes.

No product source modification is allowed to achieve this; A2 already built the seam.

## 11.3 Exact tool surface

Assert PydanticAI model-visible tools have exactly the accepted names:

```text
declare_conversation_context
expand_graph_retrieval
read_graph_source
query_threat_mechanics_hydration
```

and their parameter JSON schemas are derived from the existing DMB definitions, not separately hand-authored copies.

## 11.4 Capability fail-closed

Unknown `AgentCapabilityPolicy.policy_id`:

```text
→ AgentRuntimeResult.status = error
→ stable adapter error code
→ provider/model request count = 0
→ tool call count = 0
```

## 11.5 Authoritative argument injection

Adversarial model tool args attempt to supply a foreign:

```text
worldId
campaignId
revisionPin
retrievalSessionId
```

The executor must receive the invocation-authoritative values, not model-supplied values.

## 11.6 Product grounding with a real PydanticAI tool loop

Deterministic PydanticAI model behavior:

```text
model request 1
→ calls one graph tool
→ tool returns in-scope evidence
→ model request 2
→ final prose
```

Then feed the adapter through current `run_hermes_graph_query(..., agent_runtime=adapter)` or `process_live_query(..., agent_runtime=adapter)`.

Assert:

- runtime invoked once;
- product result grounded under existing rules;
- citations / references remain product-generated;
- no Hermes host/process is invoked;
- A0 trace has two PydanticAI model calls in order;
- A0 tool event is present with safe summary;
- A1-compatible trace shape is unchanged.

## 11.7 Conversation-context journey

Deterministic model calls `declare_conversation_context` and no graph tools.

Expected:

```text
answer_scope = conversation_context
existing product classification = conversation_context
```

No campaign-fact grounding should be invented.

## 11.8 Foreign-scope result remains rejected

Even if a fake/corrupted adapter result contains a tool completion with foreign authoritative fields, current product grounding still rejects/redacts it.

This proof may call existing product code without modifying the existing product test file.

## 11.9 Provider request telemetry: multi-call

A deterministic wrapped model performs at least two model requests.

Assert each has its own:

```text
sequence
duration
provider/model
usage status
```

and aggregate A0 model_call_count matches.

## 11.10 Cache semantics

With a synthetic Pydantic `RequestUsage`:

```text
input_tokens = 1000
cache_read_tokens = 600
cache_write_tokens = 0
output_tokens = 100
```

A0 must report:

```text
input_tokens = 1000
cached_input_tokens = 600
uncached_input_tokens = 400
output_tokens = 100
total_tokens = 1100
```

Never 1600 input tokens.

## 11.11 Error after partial telemetry

Deterministic wrapped model:

```text
request 1 succeeds
request 2 fails
```

Result must preserve request 1 plus failed request 2 timing/error observation and return typed runtime error without fabricated usage/cost.

## 11.12 Tool error

Tool executor returns/raises an error-shaped result.

Adapter records safe `state=error`; product behavior remains fail-closed/partial according to existing grounding policy.

## 11.13 History mapping

Given bounded DMB role/content history:

```text
user → assistant → current user message
```

PydanticAI receives equivalent prior message history exactly once.

Do not put World metadata into history messages.

## 11.14 No production selection

Static/source characterization proves:

```text
live_agent_loop.py does not import pydantic_ai_agent_runtime
routes do not import pydantic_ai_agent_runtime
no request schema mentions pydantic_ai runtime selection
```

A3 exists only behind internal injection.

---

# 12. Required comparison scorecard

The handback must fill this table with measured/observed values rather than prose alone.

```text
Dimension                         Hermes accepted path          PydanticAI A3                Judgment
----------------------------------------------------------------------------------------------------
adapter production LOC            187 (hermes_agent_runtime.py) 551 (pydantic_ai_agent_runtime.py)  higher
harness-specific imports          host/contract/plugin          pydantic_ai Agent/Tool/WrapperModel/FunctionModel  different shape
Hermes-named DMB couplings         n/a                           2 modules / 9 symbols:
                                                                 hermes_graph_agent:
                                                                   _resolve_hermes_openai_inference
                                                                   _safe_ids_from_args
                                                                   _summarize_tool_result
                                                                 hermes_graph_interaction_tools:
                                                                   tool names, JSON defs, executor
                                                                                           expected coupling
product files changed for adapter  A2 baseline                  0                             same / target met
direct dependency freshness        pinned Hermes 0.18.2         PAI 1.66 compatibility pin    PAI current-2.x blocked
current upstream coexistence        yes                          PAI 2.x blocked by OpenAI 2.24 pin  blocker
startup / construction ms           process-isolated worker      FunctionModel construct ~0.1ms  NOT_MEANINGFUL vs Hermes spawn
end-to-end fixed journey ms         NOT_MEANINGFUL (live host)   14.3ms FunctionModel loop     NOT_MEANINGFUL vs live provider
provider-call count                 2 on two-call fixture        2 on same scripted fixture    same
harness overhead outside model/tool process IPC + host           in-process Agent.run_sync     lower isolation / less IPC
tool schema translation             native Hermes plugin         Tool.from_schema(DMB JSON)    comparable; no second schema
tool policy translation             Hermes capability policy     world_graph_read_v1 + arg injection  equivalent fail-closed
tool event instrumentation          _ToolEventCollector          adapter wrap + reused summarizer  comparable
model-call instrumentation          Hermes observer              ObservingModel(WrapperModel)  comparable / supported seam
cache token semantics                Hermes uncached+cache add    PAI input includes cache; mapper does not add   normalized
partial provider failure             preserved                    preserved (call1 ok + call2 error)  same
continuity ergonomics                opaque session + history      message history; runtime_session_id=None  expected challenger result
test-double complexity               FakeHost on Hermes types     FunctionModel + recording executor  similar
A0 trace integration                 accepted                     descriptor-driven; no schema change  same substrate
product grounding changes            none                         0 files                     target met
```

For measurements that cannot be meaningfully compared under deterministic models, write `NOT_MEANINGFUL` and explain why. Do not invent precision.

## 12.1 Required disposition

Chosen disposition (does not select a production runtime):

```text
PROMISING_WITH_DEPENDENCY_BLOCKER
```

Harness fit is good: zero product-orchestration file changes, A0/tool/grounding parity held on the merged AgentRuntime seam. Current PydanticAI 2.x cannot coexist with the accepted `openai==2.24.0` / Hermes pin; A3 did not upgrade those pins to make the experiment pass. Full justification is in §21.

---

# 13. Required verification / merge evidence

Run from repository root.

## 13.1 New adapter suite

```bash
uv run pytest tests/test_pydantic_ai_agent_runtime.py -q
```

## 13.2 A2 boundary regressions

```bash
uv run pytest tests/test_agent_runtime.py -q
uv run pytest tests/test_hermes_agent_runtime.py -q
```

## 13.3 Product grounding / trace regressions

```bash
uv run pytest tests/test_live_query_hermes_graph.py -q
```

This file is read-only. If A3 causes it to require edits, stop and report the boundary failure.

## 13.4 Existing Hermes runtime regressions

```bash
uv run pytest tests/test_hermes_graph_agent.py -q
uv run pytest tests/test_hermes_graph_agent_host.py -q
```

Hermes implementation is read-only under this lease.

## 13.5 Dependency evidence

Record exact output/provenance for:

```bash
uv lock --check
uv tree | grep -E 'pydantic-ai|openai|hermes-agent|pydantic '
```

Equivalent Windows-safe filtering is acceptable if exact output is recorded.

Prove `openai==2.24.0` remains resolved.

## 13.6 Static / patch hygiene

```bash
uv run ruff check \
  apps/live_control_server/services/pydantic_ai_agent_runtime.py \
  tests/test_pydantic_ai_agent_runtime.py

git diff --check
git diff --name-only <dispatch-base>...HEAD
```

Changed paths must be a subset of §9.

## 13.7 Optional live comparison

If `OPENAI_API_KEY` is available and the accepted model resolves under the compatibility-constrained environment, run one deliberately small graph-grounded journey through:

```text
Hermes default
PydanticAI injected runtime
```

Use the same question, graph envelope, scope, and model.

Capture only safe trace/scorecard data:

```text
provider/model
model call count
tool call count
input/output/cache tokens
estimated DMB cost
end-to-end elapsed
provider-call elapsed
harness/tool elapsed
final grounding state
```

Do not compare answer wording as a benchmark from a single run.

If credentials/model access are unavailable, record `BLOCKED_DEPENDENCY` for live comparison only. Deterministic PydanticAI tool-loop evidence remains mandatory.

---

# 14. Backward-looking A2 state sync

A2 is now merged and its handoff still predates those final facts.

Before A3 implementation is handed back for review, update:

```text
Docs/Plans/HANDOFF-AGENT-INTERACTION-agent-runtime-boundary-v1.md
```

with only facts now true:

```text
A2 status: COMPLETE / MERGED
PR: #659
accepted head: a8978330fd1334de7ae32170bcb6ff479da2bce8
merge SHA: 937d9dce1be02e804553282a146527bf39bb0750
formal review cycles: 2
A3: active successor represented by the implementation PR
PydanticAI production selection: false
```

Do not invent A3 merge SHA/review count.

No stable architecture-authority update is required merely because a challenger experiment exists. Current authority already says the harness is client-owned and World authority remains outside it.

---

# 15. Expected nano-commit story

Exact count is not contractual. A clean implementation story is:

```text
1. AGENT-INTERACTION: add compatibility-constrained PydanticAI dependency
2. AGENT-INTERACTION: adapt PydanticAI to AgentRuntime
3. AGENT-INTERACTION: prove tool scope and A0 telemetry parity
4. AGENT-INTERACTION: capture challenger comparison evidence
5. AGENT-INTERACTION: sync completed A2 predecessor state
```

Do not mix shared prompt/tool renaming, runtime selection, UI work, or dependency modernization into those commits.

---

# 16. Required CODE → REVIEW handback

The implementation handback must include:

1. exact PR URL / branch / head SHA;
2. exact dispatch-base SHA;
3. §1 mission + merge-ready invariant copied exactly;
4. nano-commit list;
5. exact changed-path list + diff stat;
6. active PR/write-lease recheck at dispatch and handback;
7. A2 predecessor facts: #659 / accepted head / merge / 2 cycles;
8. exact dependency versions after lock;
9. explicit statement that `openai==2.24.0` and Hermes pin did not move;
10. explicit current PydanticAI 2.x incompatibility finding;
11. PydanticAI runtime descriptor;
12. exact model resolver used and resolved deterministic/live model;
13. tool-surface equality proof;
14. authoritative scope/session injection proof;
15. unsupported-policy fail-closed proof;
16. deterministic two-model-call + one-tool product journey proof;
17. conversation-context proof;
18. per-provider-call telemetry mechanism and sample safe record;
19. cache-token normalization proof;
20. partial provider failure telemetry proof;
21. continuation/history semantics;
22. confirmation product grounding/citation source files were unchanged;
23. confirmation no runtime selector/default change exists;
24. full §12 comparison scorecard;
25. one §12.1 disposition with evidence;
26. all §13 command results with exact totals/provenance;
27. live comparison result or `BLOCKED_DEPENDENCY`;
28. baseline failures/waivers (`none` when none);
29. stop conditions encountered (`none` when none);
30. A2 backward-sync diff;
31. successor claims still false: production runtime selection, shared policy hoist, runtime lifecycle API, Interaction Memory durability.

---

# 17. Stop conditions

Stop and report rather than expanding A3 if any becomes true:

- installing the experiment requires changing `openai==2.24.0`;
- installing it requires changing the accepted Hermes pin;
- the exact same resolved model cannot be used and a model substitution would be required;
- `AgentRuntime` contract must change for PydanticAI to function;
- `live_agent_loop.py` or `hermes_graph_query.py` must change for challenger execution;
- product grounding/citation logic must change to accept PydanticAI output;
- graph tool implementation must be duplicated or modified;
- `src/graph_memory/**` must change;
- a public runtime selector/request field is needed;
- a PydanticAI session needs new durable APP-STATE;
- A0 per-model-call telemetry cannot be captured without global monkeypatching or fabricated aggregation;
- PydanticAI requires raw prompt/tool bodies in baseline trace;
- a second challenger becomes necessary;
- current active PRs begin owning `pyproject.toml`, `uv.lock`, or the A3 adapter paths;
- more than one independently useful capability appears.

Stop report:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
Product files PydanticAI would force us to change:
Dependency conflict:
Proposed successor slice or experiment adjustment:
Authority/tracker update needed:
```

A stop is a valid experiment result.

---

# 18. Acceptance rubric

Accept A3 only when every applicable item is true:

- [ ] Exactly one challenger shipped: PydanticAI behind the existing internal AgentRuntime injection seam.
- [ ] Hermes remains unconditional production default.
- [ ] Public `query_backend="hermes"` is unchanged.
- [ ] No runtime selector/flag/UI was added.
- [ ] `AgentRuntime` contract remained unchanged.
- [ ] Product orchestration/grounding source remained unchanged.
- [ ] `pydantic-ai-slim[openai]==1.66.0` is exact and reproducible.
- [ ] `openai==2.24.0` remained exact.
- [ ] Hermes dependency pin remained exact.
- [ ] Current PydanticAI 2.x coexistence blocker is explicitly recorded.
- [ ] Same DMB model policy/model is used where allowed by stop rules.
- [ ] Existing model-visible tool names and schemas are reused.
- [ ] Existing DMB tool executor is reused; no second World tool implementation exists.
- [ ] Unsupported DMB capability fails before provider/tool execution.
- [ ] Model-supplied scope/session cannot override authoritative invocation values.
- [ ] Product grounding still independently revalidates runtime tool events.
- [ ] PydanticAI descriptor is truthful and non-Hermes.
- [ ] Every provider request is represented separately in A0 model calls.
- [ ] Pydantic input/cache token semantics are normalized without double counting.
- [ ] Cost uses DMB pricing policy.
- [ ] Partial provider errors preserve earlier telemetry.
- [ ] Tool telemetry is safe and bounded.
- [ ] A1 requires no UI/schema change.
- [ ] No PydanticAI durable session identity is fabricated.
- [ ] Comparison scorecard is complete.
- [ ] Disposition is evidence-based and does not imply production adoption.
- [ ] A2 handoff is backward-synced truthfully.

---

# 19. Likely successor decisions — deliberately not selected yet

A3 should leave us with evidence for one of several possible next moves.

If PydanticAI is `PROMISING` but shared DMB policy is awkwardly trapped in Hermes-named modules:

```text
possible successor:
  hoist model/prompt/tool-policy definitions into neutral DungeonBuddy ownership
```

If harness fit is good but the current-version dependency conflict dominates:

```text
possible successor:
  isolate harness dependency environments
  OR deliberately upgrade/replace Hermes dependency gate
```

If PydanticAI is materially easier and current dependency strategy can be solved:

```text
possible later successor:
  bounded production selection experiment
```

If PydanticAI is not competitive:

```text
keep Hermes
remove/retire challenger experiment when useful evidence has been captured
choose no new abstraction merely because A3 existed
```

None of those successors is selected by this handoff.

---

# 20. Reviewer decision rule

A3 passes when a reviewer can truthfully say:

> “PydanticAI ran a real DungeonBuddy World Graph Agent journey through the merged AgentRuntime boundary without changing product authority or production routing. Its model requests and tools were as observable and fail-closed as Hermes, the dependency constraint was represented honestly, and the scorecard tells us what PydanticAI costs or simplifies. Merging this experiment records evidence; it does not select PydanticAI.”

If the reviewer instead has to say:

> “We changed DungeonBuddy until PydanticAI fit,”

then the experiment failed its purpose even if the tests are green.

---

# 21. Implementation evidence (CODE handback)

Recorded from dispatch base `05d0369753e4944087f3b339221592b3c0fa6cb5` (parent `937d9dce…`, merge of A2 #659). Production selection remains false.

## 21.1 Dependency lock

```text
pydantic-ai-slim == 1.66.0
openai == 2.24.0
hermes-agent @ 861d69c7bba8d2ea6a1cd170e989c901c74d32d1 (unchanged)
```

`uv lock` added only PydanticAI 1.66 transitives (`pydantic-graph`, `genai-prices`, `griffelib`, `tiktoken`, `opentelemetry-api`, `logfire-api`, `httpx2`, `httpcore2`, `truststore`). No accepted direct pin moved.

Current PydanticAI 2.x remains incompatible: 2.0 extra requires `openai>=2.29.0`; 2.36 extra requires `openai>=3.0.0`.

## 21.2 Runtime descriptor

```text
runtime_id=pydantic_ai
trace_backend=pydantic_ai
trace_runtime=in_process
trace_mode=pydantic_ai_graph_agent
```

Injected through `run_hermes_graph_query(..., agent_runtime=adapter)` and `process_live_query(..., agent_runtime=adapter)` without editing those files. Traces are not labeled Hermes.

## 21.3 Comparison scorecard

Filled in §12. Notes below are the measured caveats, not a second table.

Notes:

- Adapter LOC is higher because PydanticAI owns the tool/model loop; the Hermes adapter is a thin host translator.
- `Agent.run_sync` in 1.66 emits `DeprecationWarning: There is no current event loop` (`asyncio.get_event_loop`). Recorded, not patched inside PydanticAI.
- Model resolver remains the Hermes-named `_resolve_hermes_openai_inference` for live parity. Tests inject `FunctionModel` and never call OpenAI.
- Cost uses DMB `estimate_model_call_cost` / `usage_cost_usd`. FunctionModel names are not in the price table, so those calls are `cost.status=unavailable` unless a priced model id is used. That is truthful, not a second price table.

## 21.4 Disposition

```text
PROMISING_WITH_DEPENDENCY_BLOCKER
```

Harness fit is good: the merged `AgentRuntime` port, World scope, DMB tool schemas/executor, product grounding, and A0 identity all worked without editing product orchestration. The current-version coexistence problem is real and was not solved by upgrading Hermes/OpenAI. Merging this records evidence; it does not select PydanticAI.

Possible later successors (not selected): hoist Hermes-named model/tool-policy helpers into neutral DMB ownership; isolate harness dependency environments; or deliberately revisit the OpenAI/Hermes pin. None of those is this PR.

## 21.5 Live comparison

`NOT_RUN` — an `OPENAI_API_KEY` is present in this environment, but A3 did not execute a dual live OpenAI graph journey. A live run would share corpus-backed graph state with other active lanes and is not required to prove harness fit. Mandatory deterministic FunctionModel tool-loop evidence is green (`tests/test_pydantic_ai_agent_runtime.py`: 17 passed).

## 21.6 Verification provenance

Recorded 2026-08-29 from `agent/pydantic-ai-adapter-experiment` after adapter+tests landed:

```text
uv run pytest tests/test_pydantic_ai_agent_runtime.py -q
  17 passed, 2 warnings in 0.85s
  (includes DeprecationWarning: pydantic_ai/_utils.py asyncio.get_event_loop)

uv run pytest tests/test_agent_runtime.py tests/test_hermes_agent_runtime.py tests/test_live_query_hermes_graph.py -q
  76 passed, 10 warnings in 5.77s

uv run pytest tests/test_hermes_graph_agent.py tests/test_hermes_graph_agent_host.py -q
  92 passed, 10 warnings in 61.79s  (read-only Hermes host; 2026-08-29T06:23Z)

uv lock --check
  Resolved 143 packages

uv tree | grep -E 'pydantic-ai|openai|hermes-agent|pydantic '
  hermes-agent v0.18.2
  openai v2.24.0  (direct and as pydantic-ai-slim extra)
  pydantic v2.13.4
  pydantic-ai-slim[openai] v1.66.0

uv run ruff check apps/live_control_server/services/pydantic_ai_agent_runtime.py tests/test_pydantic_ai_agent_runtime.py
  All checks passed

git diff --check
  clean after handoff whitespace fix

Active open PRs at handback: #660 PLAY, #661 PLAN, #662 CUTOVER
  none own pyproject.toml, uv.lock, or A3 adapter/test paths
```

Stop conditions encountered: `none`.
Baseline failures/waivers: `none`.
Paths outside §9: `none`.
Successor claims still false: production runtime selection, shared policy hoist, runtime lifecycle API, Interaction Memory durability.
