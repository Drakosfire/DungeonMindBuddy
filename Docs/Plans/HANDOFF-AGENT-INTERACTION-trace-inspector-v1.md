---
pr_body_template: |
  ## Handoff pointer
  - Workstream: AGENT-INTERACTION / A1
  - Flow: AGENT-INTERACTION
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-AGENT-INTERACTION-trace-inspector-v1.md`
  - Suggested branch: `agent/trace-inspector-v1`
  - Suggested PR title: `AGENT-INTERACTION: add advanced Agent trace inspector`

  ## Verification pointer
  - Base/head: record exact SHAs in the PR handback
  - Changed paths: HANDOFF §4 only
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Advanced Agent Trace Inspector v1 (A1)

**Created:** 2026-08-26  
**Status:** READY FOR DISPATCH after exact-current-main re-anchor and active-lease check  
**Canonical handoff path:** `Docs/Plans/HANDOFF-AGENT-INTERACTION-trace-inspector-v1.md`  
**Workstream:** `AGENT-INTERACTION / A1`  
**Flow / owner:** `AGENT-INTERACTION`  
**Handoff direction:** `DESIGN → CODE`  
**Suggested branch:** `agent/trace-inspector-v1`  
**PR title:** `AGENT-INTERACTION: add advanced Agent trace inspector`

> **Design base:** `9ddc5a6ebf2e7064ce004e22151214011046aa97` — merge of A0 PR #654, `AGENT-INTERACTION: capture complete Hermes turn traces`.
>
> A0 accepted final head: `5d5fee67ab71d88586a8511a88e1ea64a4f14960`; formal review count: **3**; merge SHA: `9ddc5a6ebf2e7064ce004e22151214011046aa97`.
>
> Dispatch from the exact current `main` that contains this handoff. Before branch creation, fetch `main`, record the exact base SHA, and re-check active PR/worktree write leases. At design time the only open implementation PR discovered is #651 (`CUTOVER: native genesis read/write continuity`), whose CUTOVER/DungeonMind integration lease is disjoint from this A1 UI/client lease.

Parent authorities and current contracts:

- `AGENTS.md`
- `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
- `Docs/Design/ARCHITECTURE-application-state-layer.md`
- `Docs/Design/DESIGN-magic-moment-contextual-source-to-world-graph.md`
- `Docs/Plans/HANDOFF-AGENT-INTERACTION-turn-trace-v1.md`
- `apps/live_control_server/services/agent_turn_trace.py` — A0 trace truth; read-only in A1
- `apps/live_control_server/services/hermes_graph_query.py` — returned A0 trace; read-only in A1
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
- `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx`
- `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`
- `apps/live-control-ui/src/agentInteraction/` — target shared ownership home

---

# 0. Repository truth and capability decomposition

## 0.1 Current truth after A0

A0 is merged. The server now emits one `dmb_agent_turn_trace_v1` per Hermes interaction with:

```text
stable trace / thread / turn identity
end-to-end elapsed time
ordered product spans
model_calls[]
per-call provider/model/timing
per-call token usage
cached / cache-write / uncached / reasoning breakdown when known
per-call cost status / estimate
aggregate usage + cost
truncation truth (`model_calls_truncated`, observed count when known)
existing graph tool events
conversation/session continuity metadata
one safe structured application log record
```

That trace is the telemetry authority. **A1 must consume it, not reinterpret or recompute it.**

The current browser UI predates A0. Its `AgentInteractionTrace` TypeScript contract knows only the old shell fields and basic input/output/total usage. `TraceDetailsPanel` is Plan-owned and cannot render A0 `spans`, `model_calls`, rich usage, or cost.

There is a more important correctness gap: current Hermes turn handling immediately calls `safeTraceForPersistence(...)`, and `safeHermesGraphTraceForPersistence(...)` intentionally projects the old trace shape. It currently replaces usage with unavailable counts and drops A0 model-call, span, cost, provider/model, and schema fields. That means **A0 data is lost before the current Plan UI can inspect it, even on the same turn, and remains absent after reload.**

A1 therefore has one coherent product job:

> safely carry the A0 baseline trace through the client turn/persistence boundary and present it through a shared advanced inspector.

## 0.2 Product direction frozen by this handoff

Observability collection is always-on product infrastructure. Inspector visibility is a UI preference.

These are separate controls:

```text
TRACE COLLECTION
  always on for Agent interactions
  server/runtime owned
  not disabled because UI is collapsed

ADVANCED DIAGNOSTICS VISIBILITY
  user-facing UI preference
  off by default for new threads
  may hide/show the inspector
  never changes whether telemetry is captured
```

The existing `traceVisible` thread field may remain as the compatibility storage name in A1, but its meaning becomes **presentation only**. Do not create a second local preference merely to rename it.

The current request field `traceRequested` must no longer be driven by `traceVisible` for Hermes. Preserve API compatibility, but the Plan request must express that A0 trace capture is expected independently of inspector visibility (for example, send `true` for Hermes if the field remains required).

## 0.3 Candidate outcomes

| Candidate | Decision |
|---|---|
| Type the complete A0 trace in the browser | **KEEP — required to consume predecessor** |
| Preserve bounded A0 trace metadata through existing thread local persistence | **KEEP — same inspector invariant** |
| Shared surface-neutral Agent Trace Inspector | **KEEP — A1 mission** |
| Advanced diagnostics off by default for new threads | **KEEP — product requirement** |
| Existing thread `traceVisible` becomes UI-only | **KEEP — compatibility, no second preference** |
| Aggregate latency/token/cost overview | **KEEP** |
| Per-model-call detail | **KEEP** |
| Product phase timing visualization | **KEEP** |
| Existing graph tool timing/detail | **KEEP** |
| Existing conversation/context metadata | **KEEP** |
| Safe structured-trace view / copy | **KEEP** |
| Exact unified model+tool waterfall | **DO NOT CLAIM** — tool events do not currently carry absolute start/end timestamps |
| Server log-file browser | **SPLIT** — A0 logs are operational output, not a query API |
| Durable trace database / retention API | **SPLIT** |
| OpenTelemetry / Langfuse exporter | **SPLIT** |
| AgentRuntime abstraction | **SPLIT — A2** |
| PydanticAI adapter | **SPLIT — A3** |
| New server telemetry fields | **OUT OF SCOPE unless a proven A0 contract defect blocks truthful rendering; stop first** |
| External chart/UI dependency | **OUT OF SCOPE** |

---

# 1. Mission and merge-ready invariant

## 1.1 Mission

> **A GM can opt into an advanced, surface-neutral Agent Trace Inspector for a DungeonBuddy Agent turn and understand the turn’s total latency, aggregate token usage and cost, individual model calls, product phase timing, graph tool activity, context/continuity metadata, warnings, and safe structured trace; the complete A0 baseline trace survives the existing client turn/persistence boundary without raw prompt/provider/tool bodies, while ordinary Agent use remains uncluttered and trace collection remains independent of inspector visibility.**

## 1.2 Merge-ready invariant

> **For every browser-visible `dmb_agent_turn_trace_v1`, the client preserves a bounded safe projection of the A0 telemetry contract through `turnFromResponse → thread persistence → reload`, and the shared Agent Trace Inspector renders that same trace truth without recomputing tokens, cost, model identity, or timing; new threads hide advanced diagnostics by default, enabling/disabling diagnostics changes presentation only and cannot suppress Agent trace capture, legacy persisted traces remain renderable, malformed additive telemetry fails soft rather than crashing the Agent pane, unavailable/partial/truncated telemetry is visibly qualified rather than shown as measured zero or complete, and no server-log browser, new durable trace store, external exporter, harness refactor, World behavior, or Play behavior is introduced.**

## 1.3 What becomes true

```text
A0 server trace reaches the browser typed as A0 v1
A0 server trace survives current turn creation without losing detailed telemetry
safe A0 telemetry survives local thread reload
new threads default advanced diagnostics OFF
existing traceVisible preference controls presentation only
Hermes trace capture is not conditional on traceVisible
one shared inspector lives under agentInteraction, not planSurface
Plan consumes the shared inspector
normal transcript remains clean when diagnostics are off
opening diagnostics shows total elapsed
opening diagnostics shows aggregate provider/model when unambiguous
opening diagnostics shows aggregate tokens + cache/reasoning breakdown
opening diagnostics shows aggregate cost and certainty status
opening diagnostics shows each retained model attempt independently
opening diagnostics shows product phase durations
opening diagnostics preserves graph tool duration/outcome details
opening diagnostics preserves conversation/session continuity details
truncated telemetry says partial and retained/observed model-call counts when known
unknown cost is unavailable, not $0
missing duration is unavailable, not 0ms
safe structured trace can be inspected/copied without raw prompt/provider/tool bodies
legacy unversioned traces still render safely
```

## 1.4 What must remain false

```text
trace collection can be turned off by the UI preference
full server application logs are browsable from the product
trace retention/history API exists
new DB table/migration exists
OpenTelemetry/Langfuse dependency exists
raw provider request/response is persisted
raw user/system prompt is persisted in baseline diagnostics
raw tool args/results are persisted
exact tool position is fabricated on the phase/model timeline
server token/cost values are recalculated in TypeScript
AgentRuntime abstraction exists
PydanticAI adapter exists
World/graph authority behavior changes
Play Runtime or Play UI changes
```

## 1.5 Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern the client typing, persistence, and inspector UI? | **Yes.** They are inseparable parts of one capability: the GM cannot inspect A0 truth if the client discards it before rendering/reload. |
| Most likely adversarial failure | The inspector looks correct on the fresh wire response but `turnFromResponse()` or reload sanitization strips model calls/spans/cost, so dogfood works once and silently regresses after persistence. |
| Would §7 detect it? | Yes. A required round-trip test starts from one exact A0-v1 fixture and asserts `turnFromResponse → persist/load` retains bounded diagnostic truth and excludes forbidden bodies. |
| Easiest UI lie to introduce | A “waterfall” that places graph tools on an absolute timeline even though current `tool_events` expose duration but no start/end timestamps. A1 may visualize product spans/model-call timing and list tool durations separately; it may not invent tool offsets. |
| What would force a split? | If truthful persisted diagnostics require a new server endpoint/DB/retention model, or if a new server trace field is required to satisfy the basic inspector rather than merely improve it, stop and report. |

---

# 2. Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Surface Interaction + Agent Interaction own product Agent UI; A0 owns trace truth; DungeonMind does not own Agent telemetry. |
| Repository rules | `AGENTS.md`: re-anchor, one capability, exclusive write lease, owning-boundary evidence, review every distinct head, backward-looking predecessor sync. |
| Exact completed predecessor | PR #654; accepted head `5d5fee67ab71d88586a8511a88e1ea64a4f14960`; merge `9ddc5a6ebf2e7064ce004e22151214011046aa97`; 3 formal review cycles. |
| Exact input consumed | A0 `dmb_agent_turn_trace_v1` plus legacy `AgentInteractionTrace` persisted shapes. |
| Named successor | **A2 — DungeonBuddy AgentRuntime boundary.** |
| What remains false | No durable trace query/history beyond existing bounded thread local persistence; no server log browser/exporter. |

Read before implementation, in order:

1. `AGENTS.md`
2. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
3. `Docs/Plans/HANDOFF-AGENT-INTERACTION-turn-trace-v1.md`
4. `apps/live_control_server/services/agent_turn_trace.py` — read only; exact A0 semantics
5. `apps/live-control-ui/src/api/types.ts`
6. `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
7. `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts`
8. `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx`
9. `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.test.tsx`
10. `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`
11. `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx`
12. `apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx` — read only unless a proven integration need triggers the bounded exception in §4

### 2.1 Ownership boundary

```text
A0 SERVER TRACE
  owns telemetry truth
  model calls
  usage
  cost
  phase spans
  safe baseline fields
          │
          ▼
CLIENT TRACE CONTRACT + SAFE PROJECTION
  types and bounds A0 fields
  preserves existing privacy boundary
  does not recompute truth
          │
          ▼
SHARED AGENT TRACE INSPECTOR
  presentation only
  surface-neutral
          │
          ▼
PLAN
  current consumer
  owns whether its thread shows advanced diagnostics
  does not own inspector semantics
```

### 2.2 “Open logs” meaning in A1

The product wording may use “Advanced diagnostics” or “Agent trace.” It must not falsely imply A1 is browsing server log files.

A1 opens the **safe structured per-turn trace** that A0 already returns and that the client safely persists. The A0 `dmb_agent_turn_trace` application log remains an operational server record.

A future log-history/export slice may add a server-side retention/query contract if dogfood proves that useful.

---

# 3. Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| Fresh A0 Hermes response | Detailed server trace exists but client sanitizer drops it | Exact safe A0 diagnostic fields remain on the turn | response → `turnFromResponse` |
| Persist/reload thread | Old shell/tool trace only | Bounded A0 diagnostics survive reload | thread sanitizer/storage |
| New thread | `traceVisible: true` | Advanced diagnostics hidden by default | thread creation |
| Diagnostics toggle | Also feeds request `traceRequested` | UI-only visibility; trace request/capture remains on | Plan ask plugin |
| Normal transcript with diagnostics off | Trace section omitted | Remains uncluttered | Plan rendering |
| Diagnostics on, complete turn | Old basic TraceDetails | Shared inspector overview + calls + phases + tools/context | shared inspector |
| Retry/error → success | No per-call UI | Separate model attempts with status/retry metadata | inspector model-call section |
| Cached/reasoning usage | Not typed/rendered | Distinct breakdown, no client arithmetic that changes server totals | types + inspector |
| Partial/unavailable cost | No cost UI | Status explicit; no false `$0` | inspector overview/calls |
| Truncated call set | Side warning only / currently dropped by client | `partial`, retained count, observed count when known, warning visible | persistence + inspector |
| Product spans | Dropped by client | Ordered duration view; missing timing shown unavailable | persistence + inspector |
| Graph tool events | Existing list works | Retained in shared inspector with duration/outcome | inspector |
| Legacy persisted trace | Existing panel renders | Shared inspector degrades gracefully | normalization/inspector |
| Malformed additive v1 field | Could crash naïve rich renderer | Drop/qualify malformed field; preserve usable siblings | normalization/inspector |
| Structured trace copy | Existing prose-oriented copy | Safe diagnostics-only JSON/text available; no forbidden raw bodies | inspector |

### 3.1 Required adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| A0 trace → `turnFromResponse` → persist → load | Same trace ID; provider/model, aggregate usage/cost, model calls, spans, warnings survive within bounds | persistence round-trip test |
| A0 trace includes forbidden `request`, `response`, `prompt`, `messages`, `args`, `result` additive fields | Forbidden fields absent after safe projection and copied structured trace | privacy sentinel test |
| A0 trace contains 64 calls + `model_calls_truncated` + observed count 65 | UI says partial, shows 64 retained / 65 observed, never “complete” | fixture + inspector test |
| model call has `usage.status=unavailable` | call visible; tokens shown unavailable, not zero | inspector test |
| cost `status=unavailable`, `usd=null` | “unavailable,” not `$0.00` | inspector test |
| span duration missing/null | “timing unavailable,” not `0 ms` and no fake-width bar | inspector test |
| tool event has duration but no timestamps | duration shown in tool section; no absolute placement asserted | inspector test |
| old persisted graph trace with no `schema/model_calls/spans/cost` | no crash; old summary/tool/context still available | compatibility test |
| unknown future/additive fields | ignored unless safely typed; no raw object rendered as React child | malformed-shape test |
| diagnostics OFF → ask turn → diagnostics ON | complete A0 trace is present because capture was not disabled by visibility | Plan integration test |

---

# 4. Files in scope — exclusive implementation write lease

## 4.1 Product/client implementation

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/api/types.ts` | Add typed A0-v1 usage/cost/model-call/span contract while preserving legacy trace compatibility and thread UI state. |
| Modify | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts` | Preserve a bounded safe A0-v1 projection during turn creation and persistence/reload; default new-thread advanced diagnostics off. |
| Modify | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts` | Own safe persistence/round-trip/privacy/legacy compatibility evidence. |
| Create | `apps/live-control-ui/src/agentInteraction/trace/AgentTraceInspector.tsx` | Surface-neutral advanced inspector and safe structured-trace formatter. |
| Create | `apps/live-control-ui/src/agentInteraction/trace/AgentTraceInspector.test.tsx` | Own rich inspector, partial/unavailable/truncated/malformed compatibility evidence. |
| Create | `apps/live-control-ui/src/agentInteraction/trace/agentTraceInspector.css` | Surface-neutral inspector styling/timing bars without external dependency. |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Consume shared inspector; make diagnostics preference presentation-only; ensure Hermes trace capture/request is independent of visibility; improve Config wording. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | Own Plan integration: diagnostics default hidden, toggle enables it, asking while hidden still yields trace when later opened. |
| Delete | `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx` | Retire Plan-owned trace inspector after behavior is hoisted. |
| Delete | `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.test.tsx` | Replaced by shared inspector tests; legacy behaviors that remain required must be migrated before deletion. |
| Modify, only trace selectors | `apps/live-control-ui/src/planSurface/planSurface.css` | Remove obsolete Plan-owned trace-detail selectors once shared CSS owns inspector styling. Do not re-style unrelated Plan UI. |

## 4.2 Backward-looking predecessor state sync

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Plans/HANDOFF-AGENT-INTERACTION-turn-trace-v1.md` | Record A0 as completed: PR #654, accepted head `5d5fee67...`, merge `9ddc5a6e...`, 3 formal review cycles; A1 is active successor; A2/A3 remain false. Do **not** mark A1 complete. |

## 4.3 Bounded discovery exception

One additional existing **frontend test file** under `apps/live-control-ui/src/agentInteraction/` may be modified only if the shared-component hoist changes an existing import/export boundary that cannot be proven by the listed tests. Record the path and exact reason in the handback before editing it.

`apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx`, `App.tsx`, server code, package manifests, lockfiles, Play code, and CUTOVER code are **not** covered by this exception.

No other production path is authorized.

---

# 5. Files and capabilities explicitly out of scope

| Path / capability | Why excluded |
|---|---|
| `apps/live_control_server/**` | A0 trace truth is accepted predecessor; A1 is a consumer/presentation slice. |
| `src/application_state/**` | No new durable trace state family. Existing local thread persistence only. |
| `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` | No new provider state needed; thread UI state already carries visibility preference. |
| `apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx` | Do not turn A1 into AppChrome/settings redesign. |
| `apps/live-control-ui/src/playSurface/**` | Play lane semantics unaffected. |
| `apps/live_control_server/integrations/dungeonmind/**` | CUTOVER/World authority unaffected. |
| `src/graph_memory/**` | Legacy graph authority unaffected. |
| dependency/lock files | No chart or observability dependency is needed. |
| server log-history endpoint | Different durable/query contract. |
| trace DB / retention / purge policy | Evidence-selected later. |
| OpenTelemetry / Langfuse | Exporter slice, not inspector. |
| AgentRuntime | A2. |
| PydanticAI | A3. |

---

# 6. Implementation contract and conditional matrices

## 6.1 Browser trace contract

Do not invent a competing frontend schema. Type the exact accepted A0 server vocabulary additively.

Directional additions:

```ts
interface AgentInteractionTraceUsage {
  available: boolean;
  status?: "reported" | "partial" | "unavailable" | string;
  input_tokens: number | null;
  cached_input_tokens?: number | null;
  cache_write_input_tokens?: number | null;
  uncached_input_tokens?: number | null;
  output_tokens: number | null;
  reasoning_tokens?: number | null;
  total_tokens: number | null;
  model_call_count?: number;
  usage_reported_call_count?: number;
  observed_model_call_count?: number;
}

interface AgentInteractionTraceCost {
  status: "estimated" | "partial" | "reported" | "no_provider_fee" | "unavailable" | string;
  usd: number | null;
  currency?: string | null;
  priced_call_count?: number;
  unpriced_call_count?: number;
  rates_per_1m_usd?: Record<string, number>;
}

interface AgentInteractionModelCallTrace { ...A0 fields... }
interface AgentInteractionTraceSpan { ...A0 fields... }

interface AgentInteractionTrace {
  schema?: "dmb_agent_turn_trace_v1" | string;
  ...legacy fields...
  cost?: AgentInteractionTraceCost;
  model_calls?: AgentInteractionModelCallTrace[];
  spans?: AgentInteractionTraceSpan[];
}
```

Legacy traces without `schema`, `cost`, `model_calls`, or `spans` remain valid inputs.

TypeScript types describe the wire; runtime guards/sanitizers still defend persisted/unknown data.

## 6.2 Safe A0 persistence projection

A0 baseline traces are designed to be safe, but local persistence still must whitelist rather than blindly store arbitrary server objects.

Add a v1-aware safe projection. It must preserve, within explicit bounds:

```text
schema / trace identity / turn identity
runtime/backend/mode/status
provider/model
started/completed/elapsed
aggregate usage
aggregate cost
model_calls[]
spans[]
tool_events[]
conversation_context
existing safe Hermes fields
warnings
```

Suggested bounds:

```text
model_calls: max 64 (matches A0 transport bound)
spans: max 128
warnings: existing 16
strings: existing 512-char scalar cap unless an existing smaller bound applies
nested rate map: numeric values only, bounded key count
span attributes: safe scalar/number/bool/null metadata only; bounded keys; no nested bodies
```

Forbidden persistence keys include at minimum:

```text
request
response
question
prompt
system_prompt
user_message
assistant_response
conversation_history
messages
content
body
args
arguments
result
raw_result
tool_result
assistant_message
```

Do not preserve a field merely because it appears under an unknown additive object.

### Fresh-turn vs reload truth

The same safe projection should be used for the in-memory turn and persisted turn. A1 must not maintain a richer ephemeral trace and a poorer reload trace unless a field is explicitly unsafe to persist. The purpose of A1 is deterministic diagnostic continuity.

## 6.3 Diagnostics visibility contract

For new threads:

```text
uiState.traceVisible = false
```

Existing persisted `traceVisible` values remain respected; no localStorage migration is required merely to change the default.

Config wording changes from ambiguous:

```text
Trace On / Trace Off
```

to product language such as:

```text
Advanced diagnostics: On / Off
```

or an equivalent accessible control.

Rules:

- OFF means the inspector is not shown in the transcript.
- ON means each turn with a trace exposes its collapsed inspector.
- inspector itself starts collapsed per turn;
- changing the preference does not mutate the trace;
- changing the preference does not cause a new model/tool call;
- changing the preference does not change trace capture.

For Hermes requests, `traceRequested` must not be derived from `traceVisible`. If the current API field remains required, send a tracing-on value compatible with A0’s always-on invariant.

## 6.4 Inspector information hierarchy

The inspector is an **advanced diagnostic disclosure**, not a dashboard competing with the answer.

### Closed state

Keep it compact. A suitable summary is:

```text
Advanced diagnostics
7.42 s · 21.3k in → 981 out · $0.0061 est. · 3 model calls · 2 tools
```

Only include values that are truly available. For example:

```text
cost unavailable
usage partial
64 retained / 65 observed calls
```

Never substitute zero for unavailable.

### Open state — Overview

Show:

```text
trace id
status
runtime/backend/mode
total elapsed
provider/model aggregate when unambiguous
model-call count / observed count
aggregate input/output/total
cached/cache-write/uncached/reasoning breakdown when present
aggregate cost amount + status
priced/unpriced call counts
warnings
```

Cost presentation examples:

```text
$0.0061 estimated
$0.0061 partial
unavailable
no provider fee
```

Do not display `null` cost as `$0.00`.

### Open state — Product phase timing

Render A0 `spans` as an ordered timing list with lightweight CSS bars.

Each row:

```text
name · status · duration
```

If parseable timestamps and total interval permit a truthful relative offset, a phase bar may show start offset and width. Otherwise render duration-only bars/list.

Rules:

- use A0 values; do not recompute span duration from wall clock when `duration_ms` exists;
- `duration_ms=null` → timing unavailable;
- no negative widths;
- clamp visualization to the trace interval only for presentation, without changing displayed source values;
- malformed span timestamps degrade to duration-only presentation;
- span attributes render only safe scalar metadata and are secondary.

### Open state — Model calls

One retained `model_calls[]` entry → one row/card.

Show when available:

```text
# sequence
status
provider
requested model
response model
API mode
duration
input / cached / cache-write / uncached
output / reasoning / total
cost + cost status
finish reason
retry count / retryable
status code / error type
```

Keep failed/retried attempts visible. Do not collapse them into the aggregate.

### Open state — Tool activity

Preserve the useful existing graph-tool UI:

```text
tool name
state
duration
outcome
revision pin
world/campaign/focus/admissibility
matched nodes / relationships / source anchors
diagnostics
```

**Do not put these tools at invented absolute positions on the phase/model timeline.** Current tool events have duration but not sufficient absolute timing.

### Open state — Context and continuity

Preserve current conversation-context telemetry and any existing safe context summary. This remains diagnostic metadata, not World fact authority.

### Open state — Structured trace

Provide a final collapsed `Structured trace` section and/or `Copy diagnostics` action that serializes the **safe projected trace only**.

Do not include `question` or `answer` in the structured trace JSON. Existing prose-oriented copy behavior may be preserved separately if useful, but the diagnostic copy contract is baseline trace metadata.

The copied trace must not contain forbidden raw-body keys or privacy sentinels from tests.

## 6.5 Shared ownership / import boundary

The new production inspector lives under:

```text
apps/live-control-ui/src/agentInteraction/trace/
```

It may import shared API types and shared utilities. It must not import production symbols from:

```text
planSurface/
playSurface/
buildSurface/
```

Plan is a consumer, not owner.

No AppChrome redesign is needed for A1.

## 6.6 Legacy compatibility matrix

| Input trace | Expected behavior |
|---|---|
| A0 `dmb_agent_turn_trace_v1` complete | Full inspector |
| A0 v1 partial/truncated | Full inspector with explicit qualification |
| A0 v1 zero model calls | Overview/phase/tool data; usage/cost unavailable |
| Existing unversioned Hermes graph trace | Legacy summary/tool/context fields render; model-call/phase/cost sections may say unavailable/omit |
| Existing non-graph legacy trace | Preserve prior safe shell/step behavior where still used |
| Malformed optional field | Drop only malformed field/entry; do not crash inspector |
| Unrecognized `schema` with known safe shell fields | Render compatibility shell and warnings; do not trust unknown nested bodies |

## 6.7 Persistence / replay matrix

A1 adds no new durable system. It improves the shape stored in existing Agent thread local persistence.

| Operation | Representation | Guarantee |
|---|---|---|
| Fresh response | safe projected `AgentInteractionTrace` on turn | A0 diagnostic fields available immediately |
| Existing local thread save | same bounded safe projected trace | no raw body persistence |
| Reload | same safe fields restored | diagnostic continuity without model/tool replay |
| Toggle diagnostics | existing thread `uiState.traceVisible` | presentation only; no Agent execution |
| Clear history | existing behavior | clears stored turn traces with turns |

If implementation requires a new DB, server retention endpoint, IndexedDB trace archive, or independent trace-history index, **stop and split**.

---

# 7. Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected result |
|---|---|---|---|
| Exact A0 v1 types are consumable | `api/types.ts` + inspector fixture | typecheck + focused test | no `any`-driven rich trace path required |
| A0 trace survives fresh turn normalization | `turnFromResponse` | history test | schema/provider/model/usage/cost/calls/spans retained |
| A0 trace survives persistence/reload | thread storage | round-trip test using localStorage | same trace id + bounded diagnostics after reload |
| Forbidden bodies do not persist | safe projector | privacy sentinel test | sentinel absent from stored JSON and copied diagnostics |
| Legacy trace still loads | safe projector | compatibility fixture | no crash; old tool/context metadata preserved |
| New threads hide diagnostics by default | thread creation | unit/integration | `traceVisible=false` |
| Visibility no longer controls trace collection | Plan request | integration with mocked `askCorpus` | ask while OFF still sends tracing-on semantics / receives trace; turning ON later reveals it |
| Shared inspector has no Plan/Play/Build production import | shared component | import-boundary grep/test | no surface import |
| Complete overview is truthful | inspector | exact A0 fixture | elapsed/model/tokens/cache/reasoning/cost/call count visible |
| Partial/unavailable values are qualified | inspector | fixtures | no false zero / complete label |
| Truncation truth is visible | inspector | 64-retained/65-observed fixture | partial + retained/observed distinction + warning |
| Per-call retries/errors remain visible | inspector | multi-call fixture | separate rows, statuses, retry/error metadata |
| Phase timing is truthful | inspector | span fixture | duration rows; missing timing unavailable; no negative/fake bar |
| Tool timing remains useful but not falsely placed | inspector | graph tool fixture | duration/outcome visible; no absolute tool-offset assertion |
| Structured diagnostic copy is safe | inspector | clipboard test | JSON/text contains trace metadata, excludes question/answer/raw sentinels |
| Plan consumes shared inspector | Plan integration | `PlanSurfaceShell` focused tests | diagnostics hidden/open correctly without losing answer/evidence |
| Existing Agent/Plan behavior regresses cleanly | frontend suites | focused + broader tests | existing relevant tests green |
| Static quality | frontend | `npm run typecheck`, `npm run build` | PASS or exact base/head waiver protocol |
| Diff lease | repository | `git diff --name-only <base>...HEAD` | §4 only |
| Patch hygiene | repository | `git diff --check` | PASS |

### 7.1 Required exact A0-v1 fixture

At least one test fixture must mirror the merged A0 vocabulary rather than a simplified approximation:

```text
schema=dmb_agent_turn_trace_v1
provider=openai-api
aggregate model
usage.status=reported
input + cached + uncached + output + reasoning + total
cost.status=estimated + usd
2 model calls with independent durations/usages/costs
at least 3 product spans
at least 1 graph tool event
conversation_context
trace id / thread id / turn id
```

A second fixture must exercise:

```text
model_calls_truncated warning
64 retained calls
observed_model_call_count=65
usage.status=partial
cost.status=partial
```

### 7.2 Required persistence privacy fixture

Start from an object that also contains sentinel-bearing forbidden additive data such as:

```text
request.body
response.assistant_message.content
prompt
messages
args
result
```

After safe projection + local persistence + reload:

```text
sentinel absent
A0 safe usage/cost/model-call/span metadata present
```

### 7.3 Required frontend commands

Run from `apps/live-control-ui`:

```bash
npm test -- --run \
  src/agentInteraction/trace/AgentTraceInspector.test.tsx \
  src/planSurface/components/agentInteractionHistory.test.ts \
  src/planSurface/PlanSurfaceShell.test.tsx

npm run typecheck
npm run build
```

Also run any existing focused Agent Interaction tests whose import boundary is touched by the hoist.

If broad Plan/Agent tests are reasonably bounded in the current harness, run them and report exact totals. Do not hide an existing baseline failure; use §7.5.

### 7.4 Manual dogfood acceptance

Run on the current Plan Agent path with real A0 telemetry if credentials/runtime are available.

```text
1. Start/open a fresh prep thread.
2. Confirm normal transcript has no advanced trace visible by default.
3. Ask one graph-grounded question while Advanced diagnostics is OFF.
4. Open Config → enable Advanced diagnostics.
5. Open that completed turn's Agent trace.
6. Verify:
   - provider + exact model
   - total elapsed
   - aggregate input/output/total
   - cached input when provider reports it
   - aggregate cost + status
   - each model call and its duration/tokens/cost
   - product phase timing
   - graph tool duration/outcome
   - trace id
7. Reload the page/thread.
8. Re-open diagnostics and verify the same bounded safe trace metadata remains.
9. Copy/open Structured trace and confirm it contains no full question/prompt/provider/tool body.
```

Expected product feeling:

> Normal DungeonBuddy remains clean; when something is slow, expensive, surprising, or worth investigating, the GM can open one turn and see where the time/tokens/cost went.

If live credentials are unavailable, record `BLOCKED_DEPENDENCY` for only this dogfood proof. Deterministic owning tests remain mandatory.

### 7.5 Baseline failure protocol

For any required command failing on dispatch base, run the identical command against base and head, record exact error tuples/counts, and do not call the gate green without an explicit operator waiver.

---

# 8. Expected nano-commit story

Exact count is not contractual. A clean review story is:

```text
1. AGENT-INTERACTION: type and preserve A0 traces safely
2. AGENT-INTERACTION: add shared advanced trace inspector
3. AGENT-INTERACTION: wire Plan diagnostics visibility to shared inspector
4. AGENT-INTERACTION: prove persistence, privacy, and partial-state truth
5. AGENT-INTERACTION: sync completed A0 predecessor state
```

The predecessor sync may travel earlier/later in the branch; it is not a separate capability.

Do not mix AgentRuntime, server telemetry changes, AppChrome redesign, graph work, or unrelated Plan cleanup into these commits.

---

# 9. Required backward-looking state sync

Before implementation is handed back for review, update the A0 handoff named in §4 to truthfully record:

```text
A0 status: COMPLETE / MERGED
PR: #654
accepted head: 5d5fee67ab71d88586a8511a88e1ea64a4f14960
merge SHA: 9ddc5a6ebf2e7064ce004e22151214011046aa97
formal review cycles: 3
A1: active successor represented by this implementation PR
A2 AgentRuntime: not started by A1
A3 PydanticAI: not started by A1
```

Do not write A1's future merge SHA or final review-cycle count into any authority before those facts exist.

No stable architecture document needs ceremony-only edits for A0 completion; its ownership claims did not change.

---

# 10. Required review handback

The CODE → REVIEW handback must include:

1. exact PR URL / branch / head SHA;
2. exact dispatch base SHA;
3. §1 mission and merge-ready invariant copied exactly;
4. nano-commit list and discrete story per commit;
5. actual changed-path list and focused diff stat;
6. active PR/write-lease recheck result at dispatch time;
7. exact A0 predecessor facts: #654 / accepted head / merge SHA / 3 cycles;
8. before/after explanation of why current `safeHermesGraphTraceForPersistence()` dropped A0 detail and how A1 closes that gap;
9. final typed A0 client shape and explicit persistence bounds;
10. forbidden-key/privacy projection rules;
11. proof that `traceVisible` is presentation-only and defaults false for new threads;
12. proof that asking while diagnostics are off still retains a trace that can later be opened;
13. screenshot or concise DOM description of collapsed and expanded inspector from deterministic fixture/manual dogfood;
14. exact aggregate tokens/cost shown for one fixture and how they correspond to the server values without recomputation;
15. exact per-model-call rows for a retry/multi-call fixture;
16. truncation proof showing retained vs observed calls and partial aggregate state;
17. phase timing proof including one unavailable/malformed timing degradation case;
18. tool-timing proof and explicit confirmation no absolute tool timing was fabricated;
19. persistence round-trip proof after reload;
20. privacy sentinel proof for persisted/copy diagnostics;
21. legacy trace compatibility proof;
22. all §7 commands with exact result/provenance;
23. manual dogfood result or `BLOCKED_DEPENDENCY`;
24. baseline failures/waivers (`none` when none);
25. paths outside §4 (`none` or stop report);
26. stop conditions encountered (`none` when none);
27. predecessor sync diff confirming A0 complete without pre-marking A1 complete;
28. successors still false: A2 AgentRuntime, A3 PydanticAI, durable trace history/log browser/exporter.

---

# 11. Acceptance rubric

Accept only when every item is true:

- [ ] Exactly one capability shipped: safe client continuity + advanced presentation of A0 Agent Turn Trace v1.
- [ ] A0 server trace semantics were consumed, not redefined in TypeScript.
- [ ] Detailed A0 telemetry survives `turnFromResponse` instead of being replaced by unavailable old-shell usage.
- [ ] Bounded safe telemetry survives existing thread persistence/reload.
- [ ] Forbidden raw prompt/provider/tool bodies do not persist or appear in diagnostic copy.
- [ ] New threads default Advanced diagnostics off.
- [ ] Existing persisted visibility values remain compatible.
- [ ] Diagnostics visibility is presentation-only and does not suppress trace capture.
- [ ] Plan consumes a shared `agentInteraction` inspector rather than owning trace presentation.
- [ ] Shared inspector imports no Plan/Play/Build production symbols.
- [ ] Normal transcript remains clean when diagnostics are off.
- [ ] Aggregate elapsed, model, usage, cache/reasoning breakdown, and cost render when available.
- [ ] Partial/unavailable/truncated state is visibly qualified.
- [ ] Per-model-call attempts remain individually visible, including retries/errors.
- [ ] Product spans are visible with truthful timing degradation.
- [ ] Existing graph-tool durations/outcomes remain visible.
- [ ] No absolute graph-tool placement is fabricated.
- [ ] Existing conversation/context diagnostics remain available.
- [ ] Legacy persisted traces render without crash.
- [ ] Malformed additive telemetry fails soft.
- [ ] No new server endpoint, DB, retention policy, dependency, exporter, AgentRuntime, PydanticAI, World change, or Play change landed.
- [ ] A0 predecessor sync is truthful and backward-looking.

---

# 12. Stop conditions

Stop and report rather than expanding if any becomes true:

- the merged A0 server trace lacks a field required for the **basic** inspector invariant and the only fix is server work;
- a new database, migration, trace-history API, retention policy, or filesystem log browser is required;
- safe trace persistence requires storing raw prompt, conversation, provider response, or tool-result bodies;
- an exact unified tool/model waterfall would require inventing tool timestamps rather than reading them;
- a charting/observability dependency appears necessary;
- `AgentInteractionProvider`, `AgentInteractionChrome`, `App.tsx`, Play, CUTOVER, or server production code must change to satisfy the mission;
- a path leased by an active parallel lane becomes necessary;
- supporting legacy traces requires a second competing trace schema instead of compatibility projection;
- the implementation begins recomputing token totals or USD cost differently from A0;
- a second independently useful capability is discovered.

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
A0  Agent Turn Trace v1                         MERGED #654
    safe normalized measuring instrument
    ↓
A1  Advanced Agent Trace Inspector v1           THIS SLICE
    preserve + inspect trace truth in product
    ↓
A2  DungeonBuddy AgentRuntime boundary
    Hermes adapter emits same trace/lifecycle contract
    ↓
A3  PydanticAI adapter experiment
    same journeys + same telemetry → direct comparison
    ↓
later, evidence-selected
    ContextAssembler / Interaction Memory instrumentation
    durable trace history / log browser
    OpenTelemetry / external exporter
```

A1 succeeds when, after any ordinary Agent interaction, the GM can keep working without telemetry noise—or intentionally open one turn and answer:

```text
What model actually ran?
How many model calls happened?
How long did the whole turn take?
Where did the product spend that time?
How many tokens went in/out?
How much input was cached?
Were reasoning tokens reported?
What did this turn cost, and is that estimate complete?
Which call retried or failed?
Which graph tools ran and how long did they take?
Was any telemetry truncated or unavailable?
Will I still see this safe diagnostic record after reload?
```

without changing the server trace vocabulary or making observability part of normal GM cognitive load.
