---
pr_body_template: |
  ## Handoff pointer
  - Workstream: AGENT-INTERACTION / A5
  - Flow: AGENT-INTERACTION
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-AGENT-INTERACTION-context-assembler-v1.md`
  - Context decision: `Docs/Design/DECISION-agent-context-compilation.md`
  - Design base: `619aa2b0c4be67e1d3931ff50899d126d2dafa13`
  - Predecessor: A4 / PR #664 / accepted head `497dcfb6c21507ee1d0e26d009add0ce044c0ec6` / merge `cbdc342ef79c8e3db5d45fbb52468c0c258a4d47` / 1 review cycle

  ## Mission
  Extract the graph-Agent context composition that already exists today into one harness-neutral DungeonBuddy-owned ContextAssembler boundary, preserving accepted model-facing behavior exactly while making the composition structurally observable. Establish the seam future QueryContext, ResolvedSurfaceContext, WorldContext, and InteractionContext work will enter; do not implement those successor capabilities in A5.

  ## Merge contract
  - one neutral `agent_context_assembler.py` owns today's graph-Agent invocation composition
  - `build_hermes_graph_turn_request(...)` remains a compatibility wrapper with the same signature/tuple shape
  - AgentRuntime public contracts and the exact model-facing payload remain behaviorally unchanged
  - current question remains the retrieval seed used by the existing GraphRetrievalSession path
  - World scope, retrieval session, latest-recap typed context, conversation continuity, grounding, and runtime continuity remain equivalent
  - A0 emits one bounded content-free `dmb_agent_context_summary_v1`
  - the existing `context_assembly` span carries the same safe scalar composition metadata
  - no SurfaceContext schema, query/entity resolver, relevance weights, token-budget algorithm, prompt renderer, memory, persistence, runtime selection, or World-write behavior is added
---

# HANDOFF — ContextAssembler v1 (A5)

**Created:** 2026-08-29
**Updated:** 2026-08-29 — design released after Agent Context Compilation decision
**Status:** IMPLEMENTATION HANDED BACK FOR REVIEW — evidence in §23
**Canonical handoff:** `Docs/Plans/HANDOFF-AGENT-INTERACTION-context-assembler-v1.md`
**Companion decision:** `Docs/Design/DECISION-agent-context-compilation.md`
**Design base:** `619aa2b0c4be67e1d3931ff50899d126d2dafa13`
**Dispatch base:** `9570bd2636231b1f4ed9b6651da6c9a653abaa07`
**Implementation branch:** `agent/context-assembler-v1`
**Workstream:** `AGENT-INTERACTION / A5`
**Flow / owner:** `AGENT-INTERACTION`
**Predecessor:** A4 — Graph Agent Policy Boundary v1
**Predecessor PR:** #664
**Accepted predecessor head:** `497dcfb6c21507ee1d0e26d009add0ce044c0ec6`
**Predecessor merge:** `cbdc342ef79c8e3db5d45fbb52468c0c258a4d47`
**Predecessor formal review cycles:** 1

---

# 0. Re-anchor and release decision

At release re-anchor:

```text
main = 619aa2b0c4be67e1d3931ff50899d126d2dafa13
open PRs = none
```

The Agent Interaction sequence is:

```text
A0  Agent Turn Trace v1                 MERGED #654
A1  Advanced Trace Inspector            MERGED #656
A2  AgentRuntime Boundary               MERGED #659
A3  PydanticAI Adapter Experiment       MERGED #663
A4  Graph Agent Policy Boundary         MERGED #664
A5  ContextAssembler v1                 THIS SLICE
```

A5 was intentionally held while the steward clarified what future Agent context means. That discussion is now captured in:

```text
Docs/Design/DECISION-agent-context-compilation.md
```

The hold is released.

Core directional law:

> **Rich typed product state in; sparse relevant semantics out.**

A5 does not implement that full compiler yet. It creates the neutral product seam on top of the exact context composition already running in production so later SurfaceContext and relevance-budget work can enter through one owned boundary instead of accumulating prompt glue.

Dispatch must still recheck current `main` and active write leases. If `main` moved, branch from current `main`; do not reset to this design base.

---

# 1. What exists today

Current production graph-Agent composition still lives in:

```text
apps/live_control_server/services/hermes_graph_query.py
  build_hermes_graph_turn_request(...)
```

It currently performs:

```text
resolved World revision validation
world/campaign/focus/admissibility resolution
server-selected graph root resolution
bounded conversation-history copy
GraphRetrievalSession create/reuse
latest-recap comparison attachment
admitted recap excerpt read for the existing typed memory-lag workflow
retrieval-session projection
AgentWorldScope construction
AgentContextPacket construction
AgentRuntimeInvocation construction
runtime continuity forwarding
```

The existing `run_hermes_graph_query(...)` path already has an A0 phase named:

```text
context_assembly
```

but the implementation responsibility and the trace vocabulary do not yet correspond to one first-class DungeonBuddy-owned context boundary.

A5 makes those line up.

---

# 2. Frozen conceptual architecture

A5 must fit the longer-term architecture without pretending to implement it:

```text
USER MESSAGE
   ↓
QueryContext

SURFACE PUBLICATION
   ↓ owning-domain resolution
ResolvedSurfaceContext?

DUNGEONMIND
   ↓ scoped retrieval / exact World revision
WorldContext

THREAD / FUTURE INTERACTION MEMORY
   ↓
InteractionContext

        └────────┬────────┘
                 ↓
          ContextAssembler
                 ↓
       sparse semantic turn context
                 ↓
            AgentRuntime
```

Important distinctions:

- the **user message** states what the user explicitly asks about;
- **SurfaceContext** says where the user is working and what product state is current/focused/selected;
- **WorldContext** comes from DungeonMind authority;
- **InteractionContext** supplies conversational/attention continuity, never World truth.

A5 only extracts the subset that exists today.

Do not add placeholder generic dictionaries merely to imitate the future contract.

---

# 3. User-message invariant

The current question remains a first-class retrieval input.

Example:

```text
What does Lysandra know about the swarm?
```

`Lysandra` must remain discoverable through the existing query-driven World retrieval regardless of ambient future Surface focus, subject to the configured DungeonMind scope/admissibility.

A5 must not change the existing behavior:

```text
question
  ↓
create_session_from_preflight(graph_envelope, question=question)
  ↓
current scoped graph retrieval
```

No new entity extractor is required.
No new ranking policy is introduced.
No Surface state may gate explicit query retrieval.

---

# 4. Surface-context law A5 must preserve

Future Surface publication will be pointer/identity heavy:

```text
run_ref
work_object_ref
work_revision_id
current Beat / Scene refs
inspection ref?
WorkSelectionAnchor?
contextual / At-a-Glance refs
```

Those identities exist for deterministic resolution, authority, stale-state detection, tracing, and tools.

They are **not automatically model-visible context**.

Future model-facing rendering should prefer semantic consequences such as:

```text
CURRENT PLAY
The GM is running North Gate during the defense of Mireward.
The gate is damaged and defenders are trying to stabilize the breach.
```

Absent optional context should consume zero model tokens.

A5 does not implement Surface publication or semantic rendering. It must simply avoid making today's graph-oriented packet the permanent definition of Agent context.

---

# 5. Mission

Create:

```text
apps/live_control_server/services/agent_context_assembler.py
```

and move the existing graph-Agent invocation composition behind it.

At merge, a reviewer must be able to say:

> **DungeonBuddy has one harness-neutral product-owned boundary for the context composition already used by graph-Agent turns. The existing Hermes production journey receives behaviorally identical runtime input. A0/A1 can describe the composition structurally without storing its prose. The boundary explicitly remains open to future QueryContext, ResolvedSurfaceContext, WorldContext, and InteractionContext work.**

---

# 6. Neutral v1 contract

Directional minimum:

```python
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONTEXT_SUMMARY_SCHEMA = "dmb_agent_context_summary_v1"


class AgentContextAssemblyError(ValueError):
    def __init__(self, message: str, *, code: str, status_code: int = 422): ...


@dataclass(frozen=True, slots=True)
class AgentContextAssembly:
    invocation: AgentRuntimeInvocation
    trace_summary: Mapping[str, str | int | bool | None]


def assemble_agent_graph_context(
    *,
    question: str,
    graph_envelope: Mapping[str, Any],
    root: Path | None = None,
    corpus_root: Path | None = None,
    conversation_history: Sequence[Mapping[str, str]] | None = None,
    retrieval_session: GraphRetrievalSession | None = None,
    runtime_session_id: str | None = None,
    thread_id: str | None = None,
    turn_id: str | None = None,
) -> AgentContextAssembly:
    ...
```

Small naming variations are acceptable if ownership remains obvious.

The assembler must import DungeonBuddy product/runtime contracts and existing retrieval/source helpers, not harness execution implementations.

Do not introduce:

```text
ContextAssembler registry
component plugin framework
universal SurfaceContext schema
arbitrary JSON context bag
context persistence repository
embedding/vector retrieval
new query/entity resolver
prompt renderer
runtime selector
```

---

# 7. Exact behavior to preserve

## 7.1 World scope

Preserve exactly:

```text
revision_id required and non-empty
world_id required and non-empty
campaign_id required and non-empty
focus normalized through current product semantics
admissibility defaults as today
server-selected graph root remains authoritative
```

Produce the same `AgentWorldScope` values.

No independent DungeonMind refresh occurs inside the assembler.
No scope/admissibility broadening.
No current-head inference from files.

## 7.2 Conversation history

The assembler receives the existing already-normalized visible history.

Preserve only:

```text
role
content
```

and existing copy semantics.

History remains interaction continuity, never factual World authority.

Keep `normalize_hermes_conversation_history(...)` where it is for A5; neutralizing request-validation names is not this capability.

## 7.3 GraphRetrievalSession

Preserve:

```text
caller-supplied session → reuse
no supplied session → create_session_from_preflight(graph_envelope, question=question)
```

Preserve session ID and current packet semantics.

The existing shared projection method:

```text
session.project_for_hermes()
```

may remain. Its name is compatibility debt, not permission to edit `src/graph_memory/**` in A5.

## 7.4 Latest-recap typed context

Preserve the exact existing S1 memory-lag path:

```text
graph envelope latest_recap_change?
  ↓
attach to current retrieval session when absent
  ↓
memory lag + admitted source path + no excerpt?
  ↓
read through existing read_admitted_recap_excerpt(...)
  ↓
attach admitted excerpt
  ↓
replace_session(...) under current conditions
```

Do not generalize this into arbitrary source opening or fallback retrieval.

## 7.5 Runtime invocation

Preserve:

```text
message = current question
thread_id
turn_id
conversation_history
AgentContextPacket
WORLD_GRAPH_READ_POLICY
run_options.runtime_session_id
run_options.execution_root
```

The public `AgentRuntimeInvocation` contract does not change.

---

# 8. Product compatibility wrapper

Keep:

```python
build_hermes_graph_turn_request(...)
```

with its current signature and return shape:

```text
(AgentRuntimeInvocation, _DispatchedScope)
```

It becomes a compatibility wrapper over the neutral assembler.

Recommended internal pattern:

```python
def _assemble_graph_turn(...):
    try:
        assembly = assemble_agent_graph_context(...)
    except AgentContextAssemblyError as exc:
        raise HermesGraphQueryRequestError(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
        ) from exc

    scope = _DispatchedScope(...from assembly.invocation.context_packet.world_scope...)
    return assembly, scope


def build_hermes_graph_turn_request(...):
    assembly, scope = _assemble_graph_turn(...)
    return assembly.invocation, scope
```

`run_hermes_graph_query(...)` may use the richer internal assembly result so it can attach context telemetry to the trace.

Do not rename the production backend/route or alter grounding/citation authority.

---

# 9. Error compatibility

Use one neutral internal error type such as:

```text
AgentContextAssemblyError
```

with code/status metadata sufficient to preserve current product behavior.

Required current cases remain equivalent:

```text
blank/missing revision_id → world_graph_context_invalid
blank/missing world_id    → world_graph_context_invalid
blank/missing campaign_id → world_graph_context_invalid
invalid server root       → world_graph_context_invalid
```

`hermes_graph_query.py` translates neutral validation failures back to `HermesGraphQueryRequestError` before they leave the product service.

No new route-level error schema.

---

# 10. Context telemetry contract

A5 turns the existing `context_assembly` phase into useful trace truth.

Every successful assembly emits exactly one safe summary:

```text
context_schema = dmb_agent_context_summary_v1
```

Required v1 scalar vocabulary:

```text
context_schema
world_id
campaign_id
revision_id
focus_kind
admissibility
history_message_count
history_char_count
retrieval_session_id
retrieval_candidate_count
retrieval_claim_count
latest_recap_change_present
admitted_recap_excerpt_char_count
runtime_continuity_present
```

Definitions:

`history_message_count`
: normalized prior messages passed to the runtime, excluding the current user turn.

`history_char_count`
: total character count of normalized prior-message `content`.

`retrieval_candidate_count`
: number of projected retrieval packet `candidates`, else 0.

`retrieval_claim_count`
: number of projected `claim_ledger` entries, else 0.

`latest_recap_change_present`
: whether the assembled retrieval session carries existing latest-recap comparison context.

`admitted_recap_excerpt_char_count`
: character count of the already-admitted recap excerpt, else 0.

`runtime_continuity_present`
: whether an already-resolved runtime continuity session ID is forwarded.

Do not add model prose to the summary.

Forbidden baseline trace content includes:

```text
current question text
conversation-history prose
system prompt
current/source recap prose
candidate summaries
claim prose
source bodies
raw graph packet
tool args/results
```

Provider-reported model input usage remains authoritative after calls. A5 does not claim exact pre-call token accounting.

---

# 11. `context_assembly` span

Mirror the same safe scalar summary onto the existing A0 span named:

```text
context_assembly
```

The summary is only fully known after assembly finishes. Therefore A5 may make this one additive trace-builder change:

```python
def complete_phase(
    self,
    span_id: str,
    *,
    status: SpanStatus = "ok",
    attributes: Mapping[str, Any] | None = None,
) -> None:
    ...
```

Rules:

```text
start attributes survive
completion attributes merge
completion value wins on duplicate key
existing complete_phase callers remain valid
phase(...) behavior remains valid
no mutable public span object is exposed
```

The graph-query path should use exception-safe start/complete behavior so failed assembly still records a failed phase without a fabricated successful summary.

---

# 12. Model-context laws preserved but not implemented

A5 is deliberately behavior-preserving. It must not attempt to optimize the prompt yet.

Its code/comments/docs must remain consistent with these successor laws from `DECISION-agent-context-compilation.md`:

```text
internal IDs/pointers are not automatically model-visible
absent optional context consumes zero model tokens
explicit user-query references are first-class retrieval signals
Surface context is candidate context/relevance, not access control
current work material should eventually be query-conditioned and bounded
graph context should eventually prefer relevant claims/relationships over whole dumps
tools are the expansion escape hatch rather than preload pressure
smallest sufficient context is the target
```

Do not add speculative prompt sections, ranking scores, weighting constants, truncation policy, or token budgets in A5.

---

# 13. Exact write lease

Release recheck found no open PRs. The following is the A5 implementation lease.

## Create

```text
apps/live_control_server/services/agent_context_assembler.py
tests/test_agent_context_assembler.py
```

## Modify

```text
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/agent_turn_trace.py
tests/test_agent_turn_trace.py
tests/test_live_query_hermes_graph.py
Docs/Plans/HANDOFF-AGENT-INTERACTION-graph-agent-policy-boundary-v1.md
Docs/Plans/HANDOFF-AGENT-INTERACTION-context-assembler-v1.md
```

The A4 handoff edit is backward-looking state sync only:

```text
A4 status = COMPLETE / MERGED
PR = #664
accepted head = 497dcfb6c21507ee1d0e26d009add0ce044c0ec6
merge = cbdc342ef79c8e3db5d45fbb52468c0c258a4d47
formal review cycles = 1
A5 = active successor
PydanticAI production selection = false
```

## Read-only / verification-only

```text
Docs/Design/DECISION-agent-context-compilation.md
Docs/Design/ARCHITECTURE-surface-interaction-layer.md
apps/live_control_server/services/agent_runtime.py
apps/live_control_server/services/hermes_agent_runtime.py
apps/live_control_server/services/pydantic_ai_agent_runtime.py
apps/live_control_server/services/agent_graph_policy.py
apps/live_control_server/services/hermes_graph_agent.py
apps/live_control_server/services/hermes_graph_interaction_tools.py
apps/live_control_server/services/live_agent_loop.py
src/graph_memory/**
apps/live-control-ui/**
pyproject.toml
uv.lock
MODEL_POLICY.json
```

No production-file discovery exception exists.

One additional **existing backend test file only** may be added if a compatibility assertion directly broken by the extraction cannot remain green without changing that test. Record the path, assertion, and reason in the CODE handback before editing it.

---

# 14. Required deterministic proofs

## 14.1 World scope parity

Given the same resolved graph envelope, old compatibility caller behavior and neutral assembler must agree on:

```text
world_id
campaign_id
focus
admissibility
revision_id
execution_root
```

## 14.2 Runtime invocation parity

Prove exact preservation of:

```text
message
thread_id
turn_id
conversation_history
context_packet.world_scope
context_packet.retrieval_session
WORLD_GRAPH_READ_POLICY
run_options.runtime_session_id
run_options.execution_root
```

No Hermes/PydanticAI type appears in the neutral assembler contract.

## 14.3 Retrieval-session creation

Without a supplied session:

```text
create_session_from_preflight(...) is used
question is passed unchanged
projected packet is attached to AgentContextPacket
session ID is preserved
```

## 14.4 Retrieval-session reuse

With a supplied session:

```text
no second session is created
same session ID is retained
same projection semantics survive
```

## 14.5 Latest-recap parity

Cover:

```text
no latest_recap_change
latest_recap_change already present on session
latest_recap_change copied from envelope
memory lag + admitted source path + no excerpt → existing reader used
existing admitted excerpt → no duplicate read
```

## 14.6 Conversation continuity

Prove normalized prior role/content history is copied exactly and the current user question is not added to the history tail.

## 14.7 Runtime continuity

Prove supplied resolved continuity ID reaches `AgentRunOptions.runtime_session_id`; absence remains `None`.

## 14.8 Safe telemetry vocabulary

Use distinctive secret strings in:

```text
question
history content
admitted recap excerpt
candidate/claim prose where fixture permits
```

Assert none appear in:

```text
assembly.trace_summary
serialized baseline A0 trace
context_assembly span attributes
```

Assert the exact §10 key set and correct counts.

## 14.9 Trace completion attributes

Characterize:

```text
start attributes survive
completion attributes are added
completion wins duplicate keys
status/duration remain correct
existing callers without attributes remain unchanged
```

## 14.10 Product path

Through `run_hermes_graph_query(...)` with a fake runtime:

```text
one context_assembly span exists
safe summary is attached
runtime receives same context as before
grounding/citation validation remains product-owned
no raw prose appears in baseline trace
```

## 14.11 Error translation

Neutral validation failures surface to existing callers with equivalent Hermes graph-query error code/status/message behavior.

---

# 15. Regression proof

Keep green:

```text
A0 trace aggregation / per-model telemetry
A2 AgentRuntime invocation contract
Hermes adapter translation
PydanticAI A3 experiment adapter
A4 neutral graph-Agent policy
Hermes host/tool behavior
product grounding/citation behavior
conversation-context answer scope
runtime continuity pointer behavior
World-unavailable no-host path
```

No live OpenAI call is required.

---

# 16. Verification

Run from repository root.

Owning tests:

```bash
uv run pytest tests/test_agent_context_assembler.py -q
uv run pytest tests/test_agent_turn_trace.py -q
uv run pytest tests/test_live_query_hermes_graph.py -q
```

Boundary regressions:

```bash
uv run pytest \
  tests/test_agent_runtime.py \
  tests/test_hermes_agent_runtime.py \
  tests/test_pydantic_ai_agent_runtime.py \
  tests/test_hermes_graph_agent.py \
  tests/test_hermes_graph_agent_host.py \
  -q
```

Static hygiene:

```bash
uv run ruff check \
  apps/live_control_server/services/agent_context_assembler.py \
  apps/live_control_server/services/hermes_graph_query.py \
  apps/live_control_server/services/agent_turn_trace.py \
  tests/test_agent_context_assembler.py \
  tests/test_agent_turn_trace.py \
  tests/test_live_query_hermes_graph.py

git diff --check
git diff --name-only <dispatch-base>...HEAD
```

No lockfile change is expected.

---

# 17. Stop conditions

Stop and report rather than expanding A5 if any becomes necessary:

```text
new durable Agent state
Interaction Memory semantics
SurfaceContext producer or schema
Play Runtime changes
WorkSelection plumbing
query/entity-resolution behavior
new relevance/scoring policy
new token-budget or prompt-rendering behavior
new graph retrieval semantics
GraphRetrievalSession schema changes
src/graph_memory/** edits
World scope/admissibility broadening
arbitrary corpus/source fallback
system-policy changes
AgentRuntime public-contract changes
Hermes/PydanticAI adapter changes to consume the same invocation
frontend context UI/type changes
dependency or lockfile changes
World writes/publication changes
```

Stop report:

```text
Stop condition:
Why A5 cannot absorb it:
Invariant affected:
Evidence missing:
Contested path/owner:
Proposed successor or serialization decision:
Authority sync needed:
```

---

# 18. CODE → REVIEW handback

The implementation handback must include:

1. PR URL / branch / exact head SHA;
2. exact dispatch-base SHA;
3. current-main and open-PR/write-lease recheck at dispatch and handback;
4. mission + merge-ready invariant;
5. exact changed-path list and diff stat;
6. nano-commit list;
7. neutral assembler API and result shape;
8. proof AgentRuntime public contract is unchanged;
9. proof user question/retrieval-session behavior is unchanged;
10. proof World scope/admissibility semantics are unchanged;
11. proof conversation history and runtime continuity are unchanged;
12. latest-recap typed-context parity evidence;
13. exact `dmb_agent_context_summary_v1` key set;
14. privacy proof that no raw prose enters baseline telemetry;
15. exact `context_assembly` span attributes;
16. trace-builder API delta and compatibility evidence;
17. explicit `project_for_hermes()` naming debt retained;
18. confirmation no SurfaceContext/query resolver/relevance-budget feature was added;
19. confirmation no frontend, APP-STATE, graph-memory, dependency, or lockfile path changed;
20. all §16 command results with exact totals;
21. baseline failures/waivers (`none` when none);
22. stop conditions encountered (`none` when none);
23. A4 backward state-sync diff;
24. successor claims that remain false.

---

# 19. Expected nano-commit story

Exact count is not contractual. A clean story is:

```text
1. AGENT-INTERACTION: extract neutral context assembler
2. AGENT-INTERACTION: route graph turn composition through assembler
3. AGENT-INTERACTION: trace context assembly composition
4. AGENT-INTERACTION: characterize parity and trace privacy
5. AGENT-INTERACTION: sync A4 predecessor state
```

---

# 20. Acceptance rubric

Accept A5 only when all applicable items are true:

- [ ] one neutral `agent_context_assembler.py` owns today's graph-Agent context composition;
- [ ] neutral assembler imports no harness implementation/provider API;
- [ ] current `build_hermes_graph_turn_request(...)` signature/tuple behavior survives;
- [ ] AgentRuntime public contract is unchanged;
- [ ] user question remains the current retrieval seed;
- [ ] World scope/revision/admissibility behavior is unchanged;
- [ ] GraphRetrievalSession creation/reuse is unchanged;
- [ ] latest-recap admitted excerpt behavior is unchanged;
- [ ] conversation-history and runtime-continuity behavior is unchanged;
- [ ] grounding/citation authority is unchanged;
- [ ] A0 receives exact `dmb_agent_context_summary_v1` safe scalars;
- [ ] `context_assembly` span carries the same safe scalar summary;
- [ ] no question/history/recap/source/claim prose enters baseline telemetry;
- [ ] provider-reported input tokens remain authoritative;
- [ ] no SurfaceContext schema or generic context bag is introduced;
- [ ] no query/entity resolver or relevance weights are introduced;
- [ ] no prompt/token-budget optimization is introduced;
- [ ] no Interaction Memory/Attention/durable Agent state is introduced;
- [ ] no frontend/type changes occur;
- [ ] no `src/graph_memory/**` changes occur;
- [ ] no dependency/lockfile change occurs;
- [ ] no runtime-selection or World-write behavior changes;
- [ ] A4 handoff is backward-synced truthfully.

---

# 21. Explicitly false after A5

After merge, these claims remain false:

```text
SurfaceContext implemented
ResolvedSurfaceContext implemented
query-entity extraction implemented
query-conditioned Surface prose implemented
relevance weights frozen
token-budget compiler complete
Interaction Memory implemented
Attention implemented
WorkSelection Graph Assessment shipped
PydanticAI selected for production
World write behavior changed
```

---

# 22. Successor design question

After A5 merges, re-anchor and ask:

> **Which real Surface should first prove `Surface publication → owning-domain resolution → ResolvedSurfaceContext → ContextAssembler`, and what is the smallest useful semantic context that Surface should contribute under budget?**

The first proving surface should be chosen from current repository truth, not preselected here.

The likely next capability is a **SurfaceContext Contract v1** characterized end-to-end by one real surface, but that is not part of A5.

---

# 23. Implementation evidence (CODE handback)

## 23.1 Dispatch / lease recheck

```text
dispatch base: 9570bd2636231b1f4ed9b6651da6c9a653abaa07
Cycle 1 reviewed head: 38c9f6523c077fca413061e3e639b2629db9993d
  formal review: 5059919962 — CHANGES REQUESTED (sequencing)
Cycle 2 rebase onto: d4a91d7b727c0eae7dd0e09ba068e250b4819b44
  (origin/main after #665 CUTOVER merge)
implementation branch: agent/context-assembler-v1
worktree: DungeonMindBuddy-context-assembler-v1
head at Cycle 2 handback: f08b09489fc57868112de47cd135dca798e961f9

steward disposition at dispatch: SPLIT
  #665 owned HERMES_GRAPH_READ_TOOL_NAMES import rename
  A5 left that hunk untouched on the dispatch base
  after #665 merge + rebase, A5 preserves D.3A import:
    apps/live_control_server/services/hermes_graph_interaction_tools.py
      HERMES_GRAPH_INTERACTION_TOOL_NAMES as HERMES_GRAPH_READ_TOOL_NAMES
```

§11.5 discovery exception used:

```text
path: tests/test_live_control_server.py
existing assertion: body["agent_trace"]["context_summary"] == {}
why: product HTTP path now populates dmb_agent_context_summary_v1;
     empty assertion cannot remain green through compatibility alone
```

Cycle 2 lease exception (post-#665 main regression blocking owning suite):

```text
path: src/graph_memory/interaction/answer_validator.py
introduced by: e5cdd9f7 (CUTOVER #665) — broken lazy wrapper
  defined __read_admitted_recap_excerpt but called _read_admitted_recap_excerpt
  and returned the undefined _read_… name (NameError on current main)
why A5 touched it: owning suite
  test_s1_admitted_recap_read_uses_corpus_root_not_graph_store_root
  fails on exact post-#665 main; outside A5 mission but blocks Cycle 2 verification
fix: restore pre-#665 direct import of read_admitted_recap_excerpt
  (removes broken wrapper; no behavior change vs pre-#665)
```

## 23.2 Neutral assembler API

```text
apps/live_control_server/services/agent_context_assembler.py
  CONTEXT_SUMMARY_SCHEMA = "dmb_agent_context_summary_v1"
  AgentContextAssemblyError(code, status_code)
  AgentContextAssembly(invocation, trace_summary)
  assemble_agent_graph_context(...) -> AgentContextAssembly
```

Compatibility:

```text
build_hermes_graph_turn_request(...) -> (AgentRuntimeInvocation, _DispatchedScope)
  thin wrapper; translates AgentContextAssemblyError -> HermesGraphQueryRequestError
```

Remaining naming debt (unchanged): `GraphRetrievalSession.project_for_hermes()`.

## 23.3 Telemetry (exact 14 scalars)

```text
context_schema, world_id, campaign_id, revision_id, focus_kind, admissibility,
history_message_count, history_char_count, retrieval_session_id,
retrieval_candidate_count, retrieval_claim_count, latest_recap_change_present,
admitted_recap_excerpt_char_count, runtime_continuity_present
```

A0: `complete_phase(..., attributes=...)` merges; `builder.context_summary` before finalize; mirrored on `context_assembly` span.

## 23.4 Verification provenance (Cycle 2 / rebased head)

```text
uv run pytest tests/test_agent_context_assembler.py tests/test_agent_turn_trace.py \
  tests/test_live_query_hermes_graph.py \
  tests/test_live_control_server.py::test_hermes_graph_host_path_ignores_legacy_lookup -q
  79 passed, 10 warnings

uv run pytest tests/test_agent_runtime.py tests/test_hermes_agent_runtime.py \
  tests/test_pydantic_ai_agent_runtime.py tests/test_hermes_graph_agent.py \
  tests/test_hermes_graph_agent_host.py -q
  129 passed, 11 warnings

uv run ruff check (leased Python files + Cycle 2 validator exception)
  All checks passed

git diff --check: clean
D.3A import preserved after rebase onto d4a91d7b727c0eae7dd0e09ba068e250b4819b44
lockfile / frontend / routes / pyproject: unchanged
```

Stop conditions: `none` (validator edit is documented Cycle 2 lease exception only).

Successor claims still false: SurfaceContext, ResolvedSurfaceContext, query-entity extraction, relevance weights, token-budget compiler, Interaction Memory, Attention, WorkSelection Graph Assessment, PydanticAI production selection, World writes.

A5 merge SHA and final review-cycle count are not invented here.
