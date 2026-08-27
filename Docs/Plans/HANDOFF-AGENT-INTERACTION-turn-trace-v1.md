---
pr_body_template: |
  ## Handoff pointer
  - Workstream: AGENT-INTERACTION / A0
  - Flow: AGENT-INTERACTION
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-AGENT-INTERACTION-turn-trace-v1.md`
  - Suggested branch: `agent/turn-trace-v1`
  - Suggested PR title: `AGENT-INTERACTION: capture complete Hermes turn traces`

  ## Verification pointer
  - Base/head: record exact SHAs in the PR handback
  - Changed paths: HANDOFF §4 only
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — First-class Agent Turn Trace v1 (A0)

**Created:** 2026-08-26

- **Status:** COMPLETE / MERGED
- **PR:** #654
- **Accepted head:** `5d5fee67ab71d88586a8511a88e1ea64a4f14960`
- **Merge SHA:** `9ddc5a6ebf2e7064ce004e22151214011046aa97`
- **Formal review cycles:** 3
- **Active successor:** A1 — Advanced Agent Trace Inspector v1 (implementation in progress; not complete)
- **Still false:** A2 AgentRuntime; A3 PydanticAI

**Canonical handoff path:** `Docs/Plans/HANDOFF-AGENT-INTERACTION-turn-trace-v1.md`  
**Workstream:** `AGENT-INTERACTION / A0`  
**Flow / owner:** `AGENT-INTERACTION`  
**Handoff direction:** `DESIGN → CODE`  
**Suggested branch:** `agent/turn-trace-v1`  
**PR title:** `AGENT-INTERACTION: capture complete Hermes turn traces`

> **Design base before this handoff lands:** `5ad992090c2e85d38784c888e4b870f5672bce8e` — merge of CUTOVER design PR #653.
>
> Dispatch from the exact current `main` that contains this handoff. Before branch creation, fetch `main`, record the exact base SHA, and re-check active PR/worktree write leases. At design time, open PR #651 owns CUTOVER DungeonMind integration paths and open PR #652 owns Play Runtime / Play UI paths. This A0 allowlist is deliberately disjoint from both. A later main advance is not itself a blocker when the §4 lease remains disjoint.

Parent authorities and current contracts:

- `AGENTS.md`
- `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
- `Docs/Design/ARCHITECTURE-application-state-layer.md`
- `Docs/Design/DESIGN-magic-moment-contextual-source-to-world-graph.md`
- `apps/live_control_server/services/live_agent_loop.py`
- `apps/live_control_server/services/hermes_graph_query.py`
- `apps/live_control_server/services/hermes_graph_agent_contract.py`
- `apps/live_control_server/services/hermes_graph_agent.py`
- `apps/live_control_server/services/hermes_graph_agent_host.py`
- `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx` — existing consumer; read-only in A0
- `src/agent/planner_telemetry.py` — prior telemetry patterns; read-only in A0
- `src/agent/planner_pricing.py` — existing OpenAI price calculation; reuse only, do not duplicate or migrate in A0
- exact pinned Hermes dependency: `NousResearch/hermes-agent@861d69c7bba8d2ea6a1cd170e989c901c74d32d1` / Hermes 0.18.2
- pinned Hermes observer authority: `docs/observability/README.md` at that exact commit

The pinned Hermes observer contract is a material predecessor, not future documentation. It already exposes read-only request-scoped hooks:

```text
pre_api_request
post_api_request
api_request_error
```

with correlation IDs, provider/model/API mode, timing, response model, usage, retry/error metadata, and sanitized payloads. A0 consumes that observer seam. **Do not upgrade Hermes, monkeypatch OpenAI, or infer per-call usage from cumulative session counters.**

---

## 0. Repository truth and capability decomposition

### 0.1 Current truth

DungeonBuddy already returns an `agent_trace` for Hermes responses. Today it contains useful but incomplete observability:

```text
trace_id
backend / runtime / mode
status
started_at / completed_at
elapsed_ms
Hermes session / process isolation
conversation-context summary
graph tool events
warnings
```

Current graph tool events already record per-tool `duration_ms` and domain-safe retrieval outcomes.

But the current trace deliberately reports:

```text
usage.available = false
steps = []
context_summary = {}
```

and `_agent_trace()` does not populate the provider/model fields already supported by the existing UI contract. The current `elapsed_ms` in the Hermes query path measures only `host.execute(...)`, not the full product interaction. Model/tool loop API attempts are therefore opaque at the product trace boundary.

The existing `TraceDetailsPanel` already displays provider/model, token usage, elapsed time, step count, tool activity, and conversation context when those fields are present. A0 can materially improve the current advanced trace experience without touching UI code.

### 0.2 Product direction frozen by this handoff

Observability is not optional instrumentation added after the Agent Surface.

> **Every Agent interaction must have one DungeonBuddy-owned execution trace. Harnesses contribute observations into that trace; they do not own the trace contract.**

For A0, the only implementation adapter is current Hermes.

The normalized trace must be designed so later adapters can emit the same concepts:

```text
Hermes
PydanticAI
local model runtime
future harness
```

No field required by the core trace may mean “Hermes session” when the actual concept is “Agent turn,” “model request,” “tool call,” “token usage,” or “cost.” Hermes-specific values belong in runtime details or existing compatibility fields.

### 0.3 Candidate outcomes

| Candidate | Decision |
|---|---|
| DungeonBuddy-owned formal Agent Turn Trace schema | **KEEP — A0 mission** |
| End-to-end Hermes phase timing | **KEEP — same trace invariant** |
| Every Hermes provider/API attempt observed individually | **KEEP — same trace invariant** |
| Per-call and aggregate token usage | **KEEP — same trace invariant** |
| Honest per-call and aggregate USD cost | **KEEP — same trace invariant** |
| Structured one-record-per-turn application log | **KEEP — same trace object, not a second schema** |
| Keep baseline trace free of full prompt/response/tool bodies | **KEEP — trace safety invariant** |
| Shared waterfall / model-call Trace Inspector UI | **SPLIT — A1** |
| `apps/live-control-ui/src/api/types.ts` changes | **SPLIT — A1; actively contested by Play PR #652 at design time** |
| AgentRuntime abstraction | **SPLIT — A2** |
| PydanticAI adapter | **SPLIT — A3** |
| Interaction Memory / ContextAssembler instrumentation | **SPLIT — later Agent slices** |
| Durable trace database / retention policy | **SPLIT — evidence-selected later capability** |
| OpenTelemetry / Langfuse / external exporter | **SPLIT — later export capability** |
| Full raw request/response logging | **SPLIT / existing forensic mode only** |
| General pricing-registry migration | **SPLIT — reuse current pricing helper in A0** |
| Hermes dependency upgrade | **OUT OF SCOPE** |

---

# 1. Mission and merge-ready invariant

## 1.1 Mission

> **Every Hermes-backed DungeonBuddy Agent interaction produces one DungeonBuddy-owned trace that accounts for the end-to-end turn and every provider model attempt with truthful timing, token usage, and cost status, so later Agent development and harness experiments can be evaluated from evidence rather than anecdote.**

## 1.2 Merge-ready invariant

> **For each Hermes interaction entering the product Agent path, one stable `trace_id` is created before meaningful execution, preserved through the returned `agent_trace` or an emitted failure trace, and used to describe the same `agent_thread_id` / `turn_id`; the trace records truthful end-to-end elapsed time, ordered timed product phases, each Hermes provider/API attempt as an independently correlated model call, existing tool activity, provider/model identity, normalized token usage, and honest cost status without double-counting cached or reasoning tokens, while telemetry failure is fail-open for the Agent turn, raw campaign/prompt/tool-result bodies are excluded from baseline trace/logging, current grounding/answer/session behavior is unchanged, and the trace contract contains no Hermes-only assumption that would prevent a later runtime adapter from producing the same core shape.**

## 1.3 What becomes true

```text
one interaction → one DMB trace identity
trace identity exists before model execution
end-to-end elapsed time means the whole Hermes product path, not only host.execute
major product phases have duration
one provider API attempt → one model_call record
model retry/error attempts remain visible, not collapsed away
provider + requested model + response model are visible when reported
per-call tokens are captured from the Hermes observer usage payload
aggregate tokens are the sum of known call usage
cached input is identified separately
reasoning tokens are informational breakdown and are never added twice to output/total
cost is estimated from reported usage + current DMB pricing helper when a price matches
unknown pricing is unavailable/partial, never silently $0
zero model calls are distinguishable from zero tokens
existing graph tool events remain available
one structured log record contains the same baseline trace object returned to product code
baseline trace contains metadata/summaries, not full prompt/response/tool-result bodies
observer callback failure cannot make an otherwise-valid Agent turn fail
reused Hermes worker/session does not leak model-call observations across turns
```

## 1.4 What must remain false

```text
shared waterfall Trace Inspector is implemented
Play UI or Play Runtime is changed
AgentRuntime exists
PydanticAI is introduced
trace persistence / retention DB exists
OpenTelemetry SDK/export exists
Langfuse or another external collector is required
forensic/full-I/O logging is enabled by default
raw provider request/response is copied into baseline trace
raw graph tool result is copied into baseline trace
pricing data is duplicated into a new second table
Hermes version or OpenAI version is upgraded
World retrieval or grounding semantics change
Agent write capabilities change
Interaction Memory persistence exists
```

## 1.5 Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every A0 observable path? | **Yes.** All changes either construct, enrich, transport, aggregate, log, or prove one trace for the current Hermes interaction. |
| Most likely adversarial failure | Reusable worker turn A registers observer callbacks → turn ends but callback remains registered → turn B emits into both collectors → B or A receives duplicated/cross-turn model calls and wrong tokens/cost. |
| Would §7 detect it? | Yes. A two-sequential-turn same-worker test must assert no callback leak, unique API request IDs per trace, and exact per-turn aggregate usage. |
| Easiest boundary to under-test | The pinned Hermes observer seam inside the process-isolated worker. A fake final result alone cannot prove request-scoped observations are registered/unregistered correctly. |
| What would force a split? | If exact pinned Hermes 0.18.2 cannot expose per-API timing/usage through its observer hooks without modifying/upgrading Hermes or replacing provider transport behavior, stop. Do not absorb a dependency upgrade/monkeypatch into A0. |

---

# 2. Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Surface Interaction ownership + Agent Magic Moment target; DungeonBuddy owns product Agent runtime/context/telemetry, not DungeonMind or Hermes. |
| Repository rules | `AGENTS.md`: re-anchor, one capability, exclusive write lease, owning-boundary evidence, review every distinct head. |
| Design base | `5ad992090c2e85d38784c888e4b870f5672bce8e`; dispatch from later exact `main` containing this handoff. |
| Predecessor contract | Existing unversioned `agent_trace`; strict Hermes host wire; pinned Hermes `hermes.observer.v1` request-scoped API hooks. |
| Exact input consumed | One Hermes backend request plus the observer callback payloads emitted by pinned Hermes during that turn. |
| Named successor | **A1 — shared Agent Trace Inspector / waterfall and typed client contract.** |
| What remains false | Trace is not durably queryable across reload solely because A0 merged; advanced visual inspection remains the existing panel/log surface until A1. |
| Explicit non-goals | Harness migration, World semantics, new DB, external exporter, raw I/O capture, Play changes, pricing-table migration. |

Read before implementation, in order:

1. `AGENTS.md`
2. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
3. `Docs/Design/DESIGN-magic-moment-contextual-source-to-world-graph.md`
4. `apps/live_control_server/services/live_agent_loop.py`
5. `apps/live_control_server/services/hermes_graph_query.py`
6. `apps/live_control_server/services/hermes_graph_agent_contract.py`
7. `apps/live_control_server/services/hermes_graph_agent.py`
8. pinned Hermes `docs/observability/README.md` at `861d69c7...`
9. `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx` only to preserve current consumer compatibility
10. existing Hermes tests named in §4

### 2.1 Ownership boundary

```text
DungeonBuddy trace contract
  owns:
    trace identity
    product turn identity
    normalized span/model-call vocabulary
    aggregate usage semantics
    cost semantics
    log projection

Hermes adapter
  contributes:
    runtime/session metadata
    API-attempt observations
    provider/model identity
    provider usage
    tool observations

DungeonMind
  contributes World/retrieval behavior through tools
  does not own Agent telemetry

UI
  consumes trace
  does not own telemetry truth
```

### 2.2 Existing UI compatibility

A0 must preserve every field the current `AgentInteractionTrace` consumer already expects:

```text
trace_id
runtime
backend
mode
provider?
model?
started_at
completed_at
elapsed_ms
status
usage { available, input_tokens, output_tokens, total_tokens }
steps[]
context_summary
artifact_refs
warnings
tool_events
Hermes compatibility fields
```

A0 may add fields. It must not require a TypeScript contract update to make the server response valid.

---

# 3. Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Normal Hermes answer, no tools | Total host duration only; usage unavailable | Whole-turn trace + one or more correlated model calls + usage/cost | Yes | live loop → Hermes worker → query response |
| Hermes model → graph tool → model | Tool durations visible; model calls opaque | Each API attempt visible; tool activity retained; aggregate matches calls | Yes | worker observer + product trace mapper |
| Provider retry/error then success | Hidden inside harness except final outcome | Failed attempt remains a model-call record with error/retry metadata; successful usage recorded | Yes | pinned Hermes observer consumer |
| Host timeout/lost worker | Typed product error exists | Trace/log records harness span error and whatever observations were completed without fabricating missing usage | Yes | host/query adapter |
| World unavailable before host | Typed no-host response exists | One trace with zero model calls and explicit unavailable phase; usage/cost unavailable, not zero | Yes | live/query adapter |
| Malformed/invalid request before model | May raise typed validation error | Structured failure trace is emitted to application log with same DMB turn identity when a turn ID exists; no fake returned success trace | Yes | live Agent entry boundary |
| Reused worker/session, turn B | Current tool/session continuity supported | Turn B contains only B observations; no callback/event leakage from A | Yes | worker hook lifecycle |
| Unknown model price | Existing generic trace has no cost | Usage remains truthful; cost status unavailable/partial and pricing mismatch explicit | Yes | trace cost normalization |
| Observer callback/parser issue | No model telemetry today | Agent behavior remains valid; trace carries warning/partial telemetry rather than failing the turn | Yes | observer collector |
| Baseline app log | No complete one-record Agent execution record | Exactly one structured baseline trace event per completed/typed-failed Hermes interaction | Yes | trace finalizer/logger |

### 3.1 Required adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Turn A registers API hooks → completes → same worker Turn B runs | No A callbacks remain; B model-call count/tokens contain B only | sequential-worker test |
| pre_api_request → api_request_error retryable → pre_api_request → post_api_request | Two call records; first error, second success; retry not collapsed | observer collector test |
| successful call usage + reasoning subset | `total_tokens` does not add reasoning a second time | usage normalization unit test |
| successful call with cached input | cached subset visible; cost uses cached rate for cached subset and normal rate for remainder | cost unit test |
| successful call with unrecognized model | tokens available; cost not represented as $0 | pricing mismatch test |
| host dies after one completed API/tool observation | final trace status error; completed observation remains; missing future usage not fabricated | host/query failure test |
| observer callback receives malformed additive field | turn completes; telemetry warning/partial state; no callback exception escapes | fail-open collector test |
| forensic mode disabled | baseline trace/log contains no raw request, response, question body, full prompt, tool args/result bodies | serialization/privacy test |

---

# 4. Files in scope — exclusive implementation write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/services/agent_turn_trace.py` | DungeonBuddy-owned trace/span/model-call/usage/cost normalization and structured log finalization. |
| Modify | `apps/live_control_server/services/live_agent_loop.py` | Create stable trace identity at Hermes product entry; time session/context phases; emit failure trace on pre-response exceptions; pass recorder downstream. |
| Modify | `apps/live_control_server/services/hermes_graph_agent_contract.py` | Add bounded, strict, backward-compatible Hermes observer/model-call result fields to worker wire. |
| Modify | `apps/live_control_server/services/hermes_graph_agent.py` | Register pinned Hermes request-scoped observer callbacks for the duration of exactly one turn; collect model-call telemetry; unregister in `finally`; preserve tool/runtime policy. |
| Modify | `apps/live_control_server/services/hermes_graph_query.py` | Time context/harness/continuity/grounding-response phases; map Hermes observations into generic trace; aggregate usage/cost; return and log same trace. |
| Create | `tests/test_agent_turn_trace.py` | Own generic normalization, aggregation, cost-status, privacy, timing, and logging contract. |
| Modify | `tests/test_hermes_graph_agent.py` | Prove observer registration/collection/unregistration and exact pinned payload mapping without live network. |
| Modify | `tests/test_hermes_graph_agent_host.py` | Prove new bounded result fields survive process-host wire and failure results stay compatible. |
| Modify | `tests/test_live_query_hermes_graph.py` | Prove end-to-end product trace shape, multi-call aggregation, failure paths, and no session/worker leakage. |

**Read-only dependency:** `src/agent/planner_pricing.py`. Reuse `usage_cost_usd()` or an equivalent existing public helper from this file at the Hermes/product mapping boundary. **Do not copy its price table.**

**Bounded discovery exception:** one additional existing test file under `tests/` may be changed only if current route/public-response assertions for `agent_trace` live there and the listed tests cannot exercise that owning boundary. Record the path and reason in the review handback before editing it.

No other production path is authorized.

---

# 5. Files and capabilities explicitly out of scope

| Path / capability | Why excluded |
|---|---|
| `apps/live-control-ui/src/api/types.ts` | A1 typed client/inspector work; also active Play PR #652 does not currently edit it, but UI remains intentionally split from A0 regardless. |
| `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx` | Existing consumer proves backward compatibility; shared inspector is A1. |
| `apps/live-control-ui/**` | No UI implementation in A0. |
| `src/application_state/**` | No trace persistence/retention contract. |
| `apps/live_control_server/integrations/dungeonmind/**` | CUTOVER lane owns World authority integration; telemetry must observe, not alter it. |
| `src/graph_memory/**` | CUTOVER is retiring legacy Buddy graph authority; A0 must not couple new telemetry to it. Existing tool events may be consumed as data only. |
| `pyproject.toml` / lock/dependency files | Exact pinned Hermes already has required observer contract. Dependency change is a stop/split condition. |
| `src/agent/planner_pricing.py` | Reuse, do not rename/migrate price registry in this capability. |
| `MODEL_POLICY.json` | Model selection policy is unchanged. |
| new database/migration | Operational trace persistence is a separate capability. |
| external observability SDK/plugin | OTel/Langfuse/etc. is a later exporter adapter. |
| full-I/O/forensic payload redesign | Existing forensic mode remains separate from always-on baseline trace. |

---

# 6. Implementation contract and conditional matrices

## 6.1 Formal product trace

A0 introduces the first formal schema marker for the existing trace concept:

```text
schema = dmb_agent_turn_trace_v1
```

The existing unversioned fields remain compatible. Directional core shape:

```text
AgentTurnTraceV1 {
  schema
  trace_id
  agent_thread_id
  turn_id

  runtime
  backend
  mode
  status

  provider?       # convenient aggregate when unambiguous
  model?          # convenient aggregate when unambiguous

  started_at
  completed_at
  elapsed_ms

  usage {
    available
    status        # reported | partial | unavailable
    input_tokens
    cached_input_tokens?
    cache_write_input_tokens?
    uncached_input_tokens?
    output_tokens
    reasoning_tokens?
    total_tokens
    model_call_count
    usage_reported_call_count
  }

  cost {
    status        # estimated | partial | reported | no_provider_fee | unavailable
    usd
    currency      # USD when amount is present
    priced_call_count
    unpriced_call_count
  }

  model_calls[]
  spans[]

  # retained compatibility / domain support
  steps[]
  context_summary
  artifact_refs
  tool_events
  warnings
  hermes_session_id?
  process_isolation?
  answer_scope?
  conversation_context?
  ... existing Hermes support fields
}
```

Field names may be refined during implementation only when the same semantics remain explicit and the current UI fields remain intact. A second parallel trace schema is prohibited.

## 6.2 Span contract

A span describes a timed operation inside one DMB trace:

```text
AgentTraceSpan {
  span_id
  parent_span_id?
  kind
  name
  status
  started_at?
  completed_at?
  duration_ms?
  attributes   # bounded metadata only
}
```

Minimum phase coverage for a normal Hermes interaction:

```text
session_load
request_validation
world_context_resolution
latest_recap_context      # only when applicable
context_assembly
harness_turn
  model_call × N
  tool_call × N or equivalent linkage to retained tool events
continuity_persist
answer_grounding_validation / response_projection
```

The exact phase names may be normalized, but these costs may not remain hidden inside one opaque `elapsed_ms` bucket.

Timing rules:

- elapsed/duration comes from monotonic timing when DungeonBuddy owns both endpoints;
- wall-clock timestamps are for orientation/correlation, not duration arithmetic when a monotonic duration exists;
- durations are never negative;
- unavailable timing is `null`/omitted, never fabricated as zero;
- `elapsed_ms` is end-to-end Hermes product-path time after A0, while `harness_turn` preserves the narrower host/runtime time that old `elapsed_ms` effectively represented.

## 6.3 Model-call contract

One Hermes `api_request_id` / provider attempt becomes one model-call record.

Directional shape:

```text
AgentModelCallTrace {
  call_id              # DMB trace-local ID
  runtime_api_request_id?
  runtime_turn_id?
  sequence
  status               # ok | error

  provider
  requested_model
  response_model?
  api_mode?

  started_at?
  completed_at?
  duration_ms?

  request_summary {
    api_call_count?
    message_count?
    tool_count?
    approx_input_tokens?
    request_char_count?
    max_tokens?
  }

  usage {
    status
    input_tokens?
    cached_input_tokens?
    cache_write_input_tokens?
    uncached_input_tokens?
    output_tokens?
    reasoning_tokens?
    total_tokens?
  }

  cost {
    status
    usd?
    pricing_table_matched?
    rates_per_1m_usd?
  }

  finish_reason?
  retry_count?
  retryable?
  status_code?
  error_type?
}
```

### Token semantics

Normalize provider/Hermes vocabulary deliberately; do not guess from field names.

For the product trace:

- `input_tokens` means total provider-reported model input/prompt tokens for that API attempt, including any cached subset when the provider's total includes cache;
- `cached_input_tokens` is the cache-read subset when reported;
- `cache_write_input_tokens` is separate when reported by a provider/runtime;
- `uncached_input_tokens` may be derived only when the relationship is known;
- `output_tokens` is provider-reported output/completion tokens;
- `reasoning_tokens` is an informational subset/breakdown when the provider reports it and **must not be added again** to `output_tokens` or `total_tokens`;
- `total_tokens` uses the provider/canonical total when semantically valid, otherwise a documented derived total from compatible normalized fields;
- an API error without usage is `usage.status=unavailable`, not zero tokens;
- aggregate counts sum known call usage and mark `partial` when any model attempt lacks reportable usage.

The pinned Hermes observer payload is the grounding source for implementation tests. Do not derive current-turn usage from Hermes lifetime/session counters; those are cumulative and can misattribute prior turns.

## 6.4 Cost contract

Current DungeonBuddy Hermes product inference is OpenAI-only. A0 may estimate cost from normalized reported usage using the existing `src/agent/planner_pricing.py::usage_cost_usd()` behavior.

Rules:

```text
known usage + matched pricing → estimated
some priced calls + some unknown/unpriced calls → partial
no matched price → unavailable, not $0
no model call → unavailable, not $0
future local provider → may later use no_provider_fee; A0 does not implement local pricing
```

Per-call cost and aggregate cost must retain enough rate/match metadata to explain an estimate. Do not hide a missing price behind a numeric zero.

## 6.5 Hermes observer mapping

Use the exact pinned `hermes.observer.v1` request-scoped hooks:

```text
pre_api_request
  identity: session_id, task_id, turn_id, api_request_id
  runtime: model, provider, base_url, api_mode
  attempt: api_call_count, message_count, tool_count,
           approx_input_tokens, request_char_count, max_tokens
  timing: started_at

post_api_request
  same identity/runtime
  api_duration, started_at, ended_at
  finish_reason, response_model
  usage
  assistant_content_chars, assistant_tool_call_count

api_request_error
  same identity/runtime
  api_duration, started_at, ended_at
  status_code, retry_count, max_retries, retryable, reason
  structured error
```

Baseline DMB trace **must not retain the sanitized `request` or `response` bodies merely because Hermes offers them.** Summaries/counts are enough for A0. Existing forensic mode remains the explicit deeper-data path.

Observer callbacks are telemetry-only and must return no behavior-changing result.

Registration lifecycle:

```text
register collector hooks for this run_hermes_graph_agent_turn
→ run turn
→ unregister exactly those callback identities in finally
```

Do not install process-global callbacks that survive the turn.

## 6.6 Structured log contract

After a returned/typed-failed Hermes interaction, emit one INFO-level structured application log event containing the same baseline `dmb_agent_turn_trace_v1` object.

Requirements:

- same `trace_id` as returned response;
- JSON serializable;
- one final trace event per turn, not one log line per token;
- no API keys;
- no full user question;
- no full system prompt;
- no full conversation history;
- no full model request/response body;
- no full tool args/result body;
- safe IDs, counts, timings, usage, cost, status, error class, and domain-safe existing tool summaries are allowed.

A0 does not define log-file retention, log download, or an external collector.

## 6.7 Failure behavior

| Failure | Required trace behavior |
|---|---|
| World unavailable before model | zero model calls; dependency/unavailable phase; usage/cost unavailable |
| Host startup failure | harness span error; zero model calls unless observations truly occurred |
| Worker timeout/loss after work began | status error; preserve completed observations; never invent unfinished usage |
| API request error | one error model-call record; retry metadata when reported |
| Usage payload absent/malformed | call remains visible; usage unavailable/partial; warning added |
| Price unknown | usage remains visible; cost unavailable/partial |
| Trace observer callback/parser error | turn behavior continues; telemetry warning/partial state |
| Existing grounding validation rejects answer | model/tool calls remain traceable; final trace status follows product turn status |

## 6.8 Persistence / replay matrix

A0 adds **no new durable store**.

| Operation | Durable representation | Round-trip guarantee | Replay behavior | Compatibility | Rollback |
|---|---|---|---|---|---|
| Return trace | `agent_trace` in existing response | JSON-safe v1 trace accompanies this interaction | Repeated interaction gets new trace ID | Existing fields retained | Revert PR restores old incomplete trace |
| Application log | same trace object serialized once | same trace ID/content class available to operational logs | retries/interactions are distinct trace records | no log reader contract yet | stop emission by reverting PR |

If implementation requires a DB table, migration, trace history API, retention policy, or reload/query semantics, **stop and split**.

---

# 7. Evidence required to merge

| Guarantee | Owning boundary | Evidence class | Command / scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Generic trace serialization/aggregation is deterministic and JSON safe | `agent_turn_trace.py` | unit/contract | `uv run pytest tests/test_agent_turn_trace.py -q` | exact usage/cost/status/span/log assertions | raw body leak, negative timing, ambiguous total |
| Reasoning tokens are not double-counted | trace usage normalizer | adversarial unit | same | output/total equal canonical semantics; reasoning separate | inflated total |
| Cached input gets correct current OpenAI estimate | trace cost mapping + existing pricing helper | unit | same | cached subset charged cached rate; remainder normal | cost mismatch / duplicate price table |
| Unknown model price is not $0 | trace cost mapping | unit | same | `unavailable`/`partial`, explicit mismatch | numeric zero represented as known cost |
| Pinned Hermes API hooks create one record per API attempt | worker wrapper | contract | `uv run pytest tests/test_hermes_graph_agent.py -q` | two synthetic exact-shape hooks → two ordered model calls | cumulative session counter used instead |
| Observer hooks unregister after each turn | worker wrapper | adversarial | same, two sequential turns | second turn has no first-turn observations/duplicate callbacks | callback leak |
| Observer parsing failure is fail-open | worker wrapper | failure injection | same | final answer still returned; trace warning/partial telemetry | telemetry exception fails turn |
| New observer fields survive bounded process wire | contract + host | round-trip | `uv run pytest tests/test_hermes_graph_agent_host.py -q` | exact IDs/model usage survive; limits enforced | unbounded payload / protocol break |
| Product response has one stable trace ID and complete aggregate | live/query service | integration | `uv run pytest tests/test_live_query_hermes_graph.py -q` | returned trace matches model calls/tool activity/turn IDs | trace ID recreated late or mismatched |
| End-to-end elapsed covers product path and host time remains visible as span | live/query service | timing contract | same | total >= component durations within test tolerances | old host-only timing mislabeled total |
| API error + retry is visible as two attempts | worker/query | adversarial integration | same | error attempt + success attempt, partial/known usage honest | retry collapsed into one opaque call |
| World-unavailable path has trace but no fake usage/cost | live/query service | failure path | same | model_call_count=0; usage/cost unavailable | zeros reported as measured |
| Baseline structured log emits once and excludes raw content | trace logger | privacy/observability | unit + query caplog | same trace ID; no unique secret sentinel from question/prompt/tool result | raw sentinel appears or duplicate final log |
| Existing grounding/session/tool behavior is unchanged | Hermes regression | regression | three listed test suites | current assertions remain green | answer/grounding/session regression |
| Focused static quality | leased Python files | lint | `uv run ruff check <all changed Python paths>` | PASS | new lint failure |
| Diff lease respected | repository | process | `git diff --name-only <base>...HEAD` | only §4 + authorized bounded test | any other path |
| Patch hygiene | repository | process | `git diff --check` | PASS | whitespace/error |

### 7.1 Required exact unit scenarios

At minimum, `tests/test_agent_turn_trace.py` must prove:

```text
one successful model call
multiple successful model calls
cached-input accounting
reasoning-token non-double-count
failed attempt with no usage
failed attempt followed by successful retry
unknown pricing
zero-model-call turn
partial aggregate usage
partial aggregate cost
span ordering / nonnegative duration
JSON serialization
baseline log privacy sentinel exclusion
```

### 7.2 Required exact Hermes observer fixture

The test fixture vocabulary must mirror the **pinned Hermes observer contract**, including opaque `api_request_id` and request-scoped `turn_id`. Do not invent a simplified “close enough” payload that omits the fields A0 depends on.

The fixture may omit large sanitized request/response bodies because A0 intentionally does not consume them.

### 7.3 Minimal live dogfood proof

Required if an OpenAI key is available in the normal DungeonBuddy development environment; otherwise record `BLOCKED_DEPENDENCY` for only this live proof, not for deterministic acceptance tests.

```text
Existing surface:
  current Plan Agent Interaction / Hermes backend

Scenario:
  one ordinary grounded campaign question that requires at least one graph tool

Expected observation in current advanced Trace Details:
  provider/model is no longer blank
  token counts are no longer "not reported"
  total elapsed remains visible
  existing graph tool durations still render

Additional server/log observation:
  same trace_id appears in one structured dmb Agent trace log record
  full model_calls[] contains each provider attempt
  each call has duration + usage
  aggregate cost has estimated/partial/unavailable status with no false zero

Do not build A1 UI to make this proof prettier.
```

### 7.4 Baseline failure protocol

For any required command failing on dispatch base, run the same command against base and head, record the difference, and do not call the gate green without an explicit operator waiver.

---

# 8. Expected nano-commit story

Exact commit count is not contractual, but the review story should remain separable. A good sequence is:

```text
1. AGENT-INTERACTION: add normalized turn-trace contract
2. AGENT-INTERACTION: collect Hermes API observer telemetry
3. AGENT-INTERACTION: project and log complete Hermes traces
4. AGENT-INTERACTION: prove retry, leakage, and privacy invariants
```

Do not mix unrelated cleanup, dependency updates, UI work, or AgentRuntime design into these commits.

---

# 9. Required review handback

The CODE → REVIEW handback must include:

1. exact PR URL / branch / head SHA;
2. exact dispatch base SHA;
3. §1 mission and merge-ready invariant copied exactly;
4. nano-commit list and discrete story per commit;
5. actual changed-path list and focused diff stat;
6. confirmation that open Play/CUTOVER lane leases were rechecked before implementation;
7. exact pinned Hermes commit used for observer contract;
8. field-level mapping from Hermes observer payload → DMB model-call trace;
9. all §7 commands with exact result and provenance;
10. one representative redacted `dmb_agent_turn_trace_v1` JSON object from deterministic test or live dogfood;
11. one explicit accounting check showing aggregate usage equals per-call known usage;
12. one explicit pricing check showing estimated cost and matched rates, or truthful unavailable status;
13. proof that reasoning tokens were not double-counted;
14. proof that reused worker/session does not leak callbacks/model calls across turns;
15. proof that baseline trace/log does not contain raw secret sentinel text;
16. baseline failures / waivers (`none` when none);
17. paths outside §4 (`none` or stop report);
18. stop conditions encountered (`none` when none);
19. successors still false: A1 Trace Inspector, A2 AgentRuntime, A3 PydanticAI, trace persistence/export.

---

# 10. Acceptance rubric

Accept only when every item is true:

- [ ] Exactly one capability shipped: complete DungeonBuddy-owned Hermes Agent Turn Trace v1.
- [ ] One stable trace identity is created early and returned/logged consistently.
- [ ] End-to-end elapsed time is no longer mislabeled host-only time.
- [ ] Every Hermes API/provider attempt becomes an independently correlated model-call record.
- [ ] Provider/requested model/response model are captured when available.
- [ ] Per-call and aggregate token usage is truthful, including cached input.
- [ ] Reasoning tokens are not double-counted.
- [ ] Failed/retried API attempts remain visible and do not fabricate usage.
- [ ] Per-call and aggregate cost use honest status; unknown price never appears as known $0.
- [ ] Existing pricing helper is reused; no duplicate price table was introduced.
- [ ] Existing graph tool telemetry remains intact.
- [ ] Same-worker sequential turns prove observer callback isolation.
- [ ] Trace collection failure is fail-open for Agent behavior.
- [ ] Baseline trace/log excludes full user/prompt/response/tool bodies.
- [ ] Exactly one final structured trace log event is emitted per completed/typed-failed Hermes interaction.
- [ ] Existing Hermes grounding, session continuity, capability policy, and answer behavior remain unchanged.
- [ ] Existing advanced Trace Details remains backward compatible without UI changes.
- [ ] No dependency, Play, CUTOVER, APP-STATE, Graph, or UI path outside §4 changed.
- [ ] A1/A2/A3 and persistence/export successors remain unimplemented.

---

# 11. Stop conditions

Stop and report rather than expanding if any of these becomes true:

- pinned Hermes observer hooks at `861d69c7...` do not expose the required per-request usage/timing in the installed runtime;
- implementation would require upgrading/forking Hermes;
- implementation would require monkeypatching the OpenAI SDK/provider transport to see model calls;
- model-call usage can only be obtained from cumulative session counters rather than request-scoped observations;
- exact token semantics cannot be determined from the pinned Hermes normalized usage payload;
- a second pricing table appears necessary;
- a DB/migration/trace retention policy becomes necessary to satisfy A0;
- a UI/type change is required to keep the existing response backward compatible;
- a path leased by active Play/CUTOVER work is required;
- telemetry callbacks alter tool/model behavior or return behavior-changing hook values;
- baseline trace requires retaining full prompt, conversation, provider response, or tool-result bodies;
- a second independently useful capability is discovered.

Use the repository stop report format from `AGENTS.md` / handoff template:

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

# 12. Named successor sequence

A0 intentionally creates the measuring instrument before changing the Agent runtime architecture.

```text
A0  Agent Turn Trace v1                         MERGED #654
    complete current Hermes evidence
    accepted head 5d5fee67ab71d88586a8511a88e1ea64a4f14960
    merge 9ddc5a6ebf2e7064ce004e22151214011046aa97
    3 formal review cycles
    ↓
A1  Advanced Agent Trace Inspector v1           ACTIVE SUCCESSOR
    preserve + inspect trace truth in product
    not completed by this A0 record
    ↓
A2  DungeonBuddy AgentRuntime boundary          not started
    Hermes adapter emits the same trace contract
    ↓
A3  PydanticAI adapter experiment               not started
    same journeys, same trace schema, direct comparison
    ↓
later
    ContextAssembler + Interaction Memory instrumentation
    trace persistence/export only when evidence selects it
```

A0 succeeds when a later harness experiment can answer, from normalized data:

```text
Which model calls occurred?
How long did each take?
How much of the turn was model vs tool vs product overhead?
How many tokens went in and out per call and per turn?
How much did the turn cost, and how certain is that cost?
Where did the turn fail or retry?
Did harness/runtime overhead materially differ?
```

without changing the product trace vocabulary to accommodate the second harness.
