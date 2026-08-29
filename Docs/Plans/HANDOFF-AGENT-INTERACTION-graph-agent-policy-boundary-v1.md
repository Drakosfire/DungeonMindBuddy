---
pr_body_template: |
  ## Handoff pointer
  - Workstream: AGENT-INTERACTION / A4
  - Flow: AGENT-INTERACTION
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-AGENT-INTERACTION-graph-agent-policy-boundary-v1.md`
  - Design base: `770f79cca4aa3c12aa8a35db2db77ce376f2ff9e`
  - Predecessor: A3 / PR #663 / accepted head `4e4fa25268fc3c3bf2fec56fcbe465c4c7e08c55` / merge `5eb4e030a66b09d98525f0f934c7e91051e48549` / 2 review cycles

  ## Mission
  Move DungeonBuddy-owned graph-Agent behavioral policy and OpenAI model-resolution policy out of the Hermes runtime module into one harness-neutral product-owned boundary, then make both Hermes and PydanticAI consume that same policy without changing product behavior, production routing, tool semantics, observability, dependencies, or World authority.

  ## Merge contract
  - one neutral `agent_graph_policy.py` owns the accepted graph-Agent system behavior policy and graph-Agent OpenAI resolution policy
  - Hermes preserves exact accepted prompt/model/config behavior through compatibility imports/aliases where useful
  - PydanticAI no longer imports `_GRAPH_SYSTEM_POLICY` or `_resolve_hermes_openai_inference` from `hermes_graph_agent.py`
  - the accepted policy text is moved verbatim; no prompt rewrite or model-policy modernization is hidden in the extraction
  - current MODEL_POLICY lookup order, default model, OpenAI provider/base URL, legacy environment override, and current missing-credential behavior remain unchanged
  - graph tool definitions/executor, safe tool telemetry helpers, AgentRuntime contract, product orchestration, A0/A1 trace semantics, dependencies, public runtime selection, APP-STATE, and World authority remain unchanged
  - A3 remains an experiment result only; PydanticAI production selection remains false
---

# HANDOFF — Graph Agent Policy Boundary v1 (A4)

**Created:** 2026-08-29  
**Status:** IMPLEMENTATION HANDED BACK FOR REVIEW — evidence in §18
**Canonical handoff path:** `Docs/Plans/HANDOFF-AGENT-INTERACTION-graph-agent-policy-boundary-v1.md`  
**Design branch:** `agent/graph-agent-policy-boundary-design`  
**Design base:** `770f79cca4aa3c12aa8a35db2db77ce376f2ff9e`  
**Workstream:** `AGENT-INTERACTION / A4`  
**Flow / owner:** `AGENT-INTERACTION`  
**Predecessor:** A3 — PydanticAI AgentRuntime Adapter Experiment  
**Predecessor PR:** #663  
**Accepted predecessor head:** `4e4fa25268fc3c3bf2fec56fcbe465c4c7e08c55`  
**Predecessor merge:** `5eb4e030a66b09d98525f0f934c7e91051e48549`  
**Predecessor formal review cycles:** 2  

---

# 0. Re-anchor: what is true now

The first Agent Interaction infrastructure tranche is complete:

```text
A0  Agent Turn Trace v1                    MERGED #654
    DMB-owned per-turn/per-model-call observability
    ↓
A1  Advanced Agent Trace Inspector         MERGED #656
    safe persisted trace truth + opt-in diagnostics UX
    ↓
A2  DungeonBuddy AgentRuntime Boundary     MERGED #659
    product orchestration talks to AgentRuntime; Hermes is one adapter
    ↓
A3  PydanticAI Adapter Experiment          MERGED #663
    second harness proved the boundary; production selection stayed false
    disposition: PROMISING_WITH_DEPENDENCY_BLOCKER
    ↓
A4  Graph Agent Policy Boundary            THIS SLICE
    move DMB-owned shared policy out of Hermes-named runtime ownership
```

A3 proved the architectural seam rather than selecting a runtime.

Important A3 result:

```text
PydanticAI could run the real DMB product grounding path
without changing product orchestration,
but it had to import DMB-owned behavior/model policy
from hermes_graph_agent.py.
```

At accepted head A3 imports, among other Hermes-named helpers:

```text
_GRAPH_SYSTEM_POLICY
_resolve_hermes_openai_inference
_safe_ids_from_args
_summarize_tool_result
```

The first two are product policy. The latter two are safe runtime/tool-observation helpers and are deliberately not moved in A4.

This slice converts the proven shared policy into neutral DungeonBuddy ownership before the Agent workstream advances into context assembly, interaction continuity, attention/memory, or source-to-World assessment.

---

# 1. Roadmap position

## 1.1 Agent Interaction roadmap

We are at the end of the **harness proving** tranche and before the **product context/continuity** tranche.

```text
OBSERVABILITY
  A0 trace                     DONE
  A1 inspector                 DONE

HARNESS BOUNDARY
  A2 AgentRuntime              DONE
  A3 second-harness proof      DONE
  A4 neutral shared policy     NEXT

PRODUCT CONTEXT / CONTINUITY
  ContextAssembler             NOT SELECTED
  Interaction Memory           NOT SELECTED
  Attention Ledger             NOT SELECTED
  Open Loops                   NOT SELECTED

MAGIC MOMENT
  selection → read-only Graph Assessment
                               NOT SELECTED
  governed publication         WAITS on appropriate World-write authority
```

A4 is intentionally a short architecture-hardening step. It should not become a detour into generic abstraction work.

## 1.2 Wider repository roadmap

The Campaign Supergraph roadmap remains in Phase 8 / governed context-correction-tools territory, with Phase 9 living-memory cleanup not yet started. Current CUTOVER execution is ahead of the checked-in main roadmap text because the active D.2C4 PR carries the next atomic authority sync.

Current nearby surface/CUTOVER state at this re-anchor:

```text
#661 PLAN-SURFACE — blank authoring shell          MERGED
#660 PLAY-SURFACE — native Runbook authoring       OPEN / draft
#662 CUTOVER — D.2C4 manual Graph Review continuity OPEN
```

#661's merge means blank Plan authoring is now a real surface state and the temporary shared Agent-runtime write lease from that lane has cleared.

#660 remains frontend/Play-authoring scoped. #662 owns Graph Review / DungeonMind write-integration paths and Campaign Supergraph sequencing docs.

A4 stays backend-only and does not overlap either active production lease.

---

# 2. Mission and merge-ready invariant

## 2.1 Mission

Move the **DungeonBuddy-owned graph-Agent behavioral policy and graph-Agent OpenAI model-resolution policy** out of the Hermes runtime implementation and into one harness-neutral DungeonBuddy service module.

Then make both accepted runtimes consume that neutral source while preserving exact current behavior.

## 2.2 Merge-ready invariant

At merge:

```text
apps/live_control_server/services/agent_graph_policy.py
  owns:
    GRAPH_SYSTEM_POLICY
    resolve_agent_graph_openai_inference(...)

Hermes graph runtime
  imports neutral policy
  preserves current private compatibility names where useful
  preserves exact runtime behavior

PydanticAI runtime
  imports neutral policy directly
  no longer imports the two product-policy symbols from hermes_graph_agent.py
```

and all of the following remain true:

- the accepted graph-Agent system policy text is **verbatim-equivalent** to A3 accepted head;
- Hermes still receives the same behavioral policy + Hermes-specific scope block;
- PydanticAI still receives the same behavioral policy + truthful PydanticAI-specific scope packet;
- the default graph-Agent model resolution is unchanged;
- the existing MODEL_POLICY action lookup semantics are unchanged;
- the existing OpenAI provider and base URL are unchanged;
- the existing `DUNGEONMIND_HERMES_GRAPH_MODEL` compatibility override remains honored;
- the existing Hermes missing-credential behavior remains unchanged;
- PydanticAI continues to map missing credentials to its own adapter error code;
- no graph tool names, schemas, executor behavior, or capability policy changes;
- no AgentRuntime contract or public routing changes;
- no telemetry schema or pricing changes;
- no dependency changes;
- no PydanticAI adoption claim.

If implementation requires changing any of those behaviors, stop rather than widening A4.

---

# 3. Why this is the next slice

A3 answered the question we needed answered:

> Is the AgentRuntime boundary real enough to host a second harness without changing DungeonBuddy product orchestration?

Answer: **yes**.

A3 also revealed a concrete architectural debt:

> Some DungeonBuddy-owned graph-Agent policy is still physically owned by a Hermes runtime module.

Leaving that debt in place while beginning ContextAssembler / Interaction Memory would make future product-owned context code depend on Hermes-named implementation modules. A4 fixes only that proven seam.

This is not speculative abstraction. Two runtimes already consume the same policy.

---

# 4. Frozen ownership decision

## 4.1 DungeonBuddy product policy

The following are DungeonBuddy-owned policy, not harness behavior:

```text
graph-Agent behavioral/system policy
OpenAI-only product inference decision
MODEL_POLICY lookup behavior for the graph Agent
model default/fallback behavior
product environment override compatibility
provider/base-url selection used by the graph Agent
```

These belong in neutral DungeonBuddy ownership.

## 4.2 Runtime-specific behavior stays runtime-specific

Hermes continues to own:

```text
Hermes capability object translation
Hermes plugin/toolset identity
Hermes process isolation
Hermes home/config materialization
Hermes observer translation
Hermes session/runtime behavior
```

PydanticAI continues to own:

```text
PydanticAI Agent/Tool translation
PydanticAI in-process truth
PydanticAI model request interception
PydanticAI message-history translation
PydanticAI runtime-specific scope packet
```

## 4.3 Explicit non-goal: tool-neutralization

A4 does **not** rename or move:

```text
hermes_graph_interaction_tools.py
execute_hermes_graph_interaction_tool_json
hermes_model_visible_tool_definitions
_safe_ids_from_args
_summarize_tool_result
```

Some of those names now represent product-owned behavior and may deserve a later neutralization slice. Moving them here would create a second independently useful/revertible capability.

Record remaining Hermes-named coupling after A4; do not hide it.

---

# 5. Neutral module contract

Create:

```text
apps/live_control_server/services/agent_graph_policy.py
```

Minimum owned surface:

```python
GRAPH_SYSTEM_POLICY: str


def resolve_agent_graph_openai_inference(
    *,
    require_api_key: bool = True,
) -> tuple[str, str, str] | str:
    ...
```

Do not add classes, registries, provider abstractions, runtime selectors, or generic policy engines unless the existing behavior cannot be preserved without them.

The point is neutral ownership, not a framework.

## 5.1 System policy move

Move the accepted A3 `_GRAPH_SYSTEM_POLICY` text **verbatim** into:

```text
GRAPH_SYSTEM_POLICY
```

No wording cleanup.
No replacement of `Hermes answer` inside the existing forbidden-output sentence.
No style edits.
No prompt optimization.
No added Interaction Memory rules.
No new magic-moment/source-authoring behavior.

The deleted block and added block should be reviewable as a semantic move, not a rewrite.

## 5.2 Model resolver move

Move the current `_resolve_hermes_openai_inference` product-resolution behavior into:

```text
resolve_agent_graph_openai_inference
```

Preserve exactly:

```text
load_dungeonmindbuddy_dotenv()
OpenAI credential check
default model = gpt-5.4-mini
MODEL_POLICY candidate path behavior
MODEL_POLICY actions lookup:
  hermes_graph_agent
  then default_text_generation
models mapping lookup
DUNGEONMIND_HERMES_GRAPH_MODEL override
provider = openai-api
base_url = https://api.openai.com/v1
```

The legacy action/env names are compatibility inputs. Do not rename them in A4.

Preserve current missing-credential behavior expected by Hermes. A neutral ownership module may still emit the legacy compatibility error token if changing it would alter behavior. Naming cleanup is not this mission.

---

# 6. Hermes compatibility rule

`hermes_graph_agent.py` may preserve its private historical names as compatibility aliases:

```python
from apps.live_control_server.services.agent_graph_policy import (
    GRAPH_SYSTEM_POLICY as _GRAPH_SYSTEM_POLICY,
    resolve_agent_graph_openai_inference as _resolve_hermes_openai_inference,
)
```

Equivalent implementation is acceptable.

Why:

- keeps the Hermes runtime patch small;
- avoids gratuitous churn in internal monkeypatch points;
- Hermes internals may have Hermes names;
- ownership is proven by where the implementation lives and what non-Hermes consumers import.

Do not duplicate the policy text or resolver implementation in both modules.

---

# 7. PydanticAI rule

`pydantic_ai_agent_runtime.py` must import the shared product policy directly from the neutral module.

After A4, it must not import these symbols from `hermes_graph_agent.py`:

```text
_GRAPH_SYSTEM_POLICY
_resolve_hermes_openai_inference
```

It may continue importing the currently shared safe-observation helpers:

```text
_safe_ids_from_args
_summarize_tool_result
```

and may continue consuming `hermes_graph_interaction_tools.py` for the existing DMB tool surface under this slice.

The handback must report the remaining Hermes-named coupling count after extraction.

---

# 8. Observability and authority remain unchanged

A4 is not an observability feature, but A0/A1 remain acceptance instruments.

Do not change:

```text
dmb_agent_turn_trace_v1
AgentRuntimeDescriptor values
model-call normalization
usage/cache semantics
cost estimation
product span vocabulary
advanced inspector projection
```

World authority also remains unchanged:

```text
DungeonMind owns World truth
DungeonBuddy owns product orchestration/policy/context
runtime owns only harness execution
```

No World write path is introduced.

---

# 9. Exact write lease

The §9 allowlist is the exclusive expected write set for A4.

## 9.1 Create

1. `apps/live_control_server/services/agent_graph_policy.py`
2. `tests/test_agent_graph_policy.py`

## 9.2 Modify

3. `apps/live_control_server/services/hermes_graph_agent.py`
4. `apps/live_control_server/services/pydantic_ai_agent_runtime.py`
5. `tests/test_pydantic_ai_agent_runtime.py`
6. `tests/test_hermes_graph_agent.py` — only for direct policy/resolver characterization required by this extraction
7. `Docs/Plans/HANDOFF-AGENT-INTERACTION-pydantic-ai-adapter-experiment.md` — backward-looking A3 completion sync only
8. `Docs/Plans/HANDOFF-AGENT-INTERACTION-graph-agent-policy-boundary-v1.md` — CODE handback/evidence only

## 9.3 Explicitly read-only / forbidden

Do not modify:

```text
apps/live_control_server/services/agent_runtime.py
apps/live_control_server/services/hermes_agent_runtime.py
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/services/hermes_graph_interaction_tools.py
apps/live_control_server/services/agent_turn_trace.py
apps/live_control_server/routes/**
apps/live-control-ui/**
apps/live_control_server/integrations/dungeonmind/**
apps/live_control_server/ports/**
src/graph_memory/**
pyproject.toml
uv.lock
MODEL_POLICY.json (wherever resolved from)
Docs/Roadmaps/**
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
```

Those shared product-runtime files are no longer leased by #661 after its merge, but they remain outside A4 because changing them is unnecessary and would broaden the capability.

## 9.4 Bounded discovery exception

One additional **existing test file only** may be added to the lease if an existing direct test of `_GRAPH_SYSTEM_POLICY` or `_resolve_hermes_openai_inference` is discovered outside the two leased test files and cannot remain green through compatibility aliases.

Before editing it, the CODE handback must record:

```text
path
existing assertion/monkeypatch forcing the edit
why alias compatibility cannot preserve it unchanged
```

No production-file discovery exception exists.

---

# 10. Required deterministic proofs

## 10.1 Single canonical policy source

Prove:

```text
agent_graph_policy.py owns the policy string
hermes_graph_agent.py contains no second full copy
pydantic_ai_agent_runtime.py contains no copy
```

A source/AST characterization is acceptable.

## 10.2 Verbatim accepted policy

Demonstrate that the policy moved without semantic edits.

At minimum:

- reviewer can compare the removed dispatch-base block with the added neutral block;
- owning tests assert high-value accepted clauses still exist:
  - conversation-context `declare_conversation_context` behavior;
  - latest-recap handling;
  - cross-campaign provenance;
  - `read_graph_source` quotation/exact-detail rule;
  - frontstage anti-report-scaffolding rule;
  - forbidden Manifest/corpus/Markdown discovery rule.

Do not satisfy this by rewriting equivalent prose.

## 10.3 Both runtimes consume the neutral policy

Prove:

```text
Hermes policy prefix == GRAPH_SYSTEM_POLICY
PydanticAI policy prefix == GRAPH_SYSTEM_POLICY
```

PydanticAI owning test must continue inspecting the actual `ModelRequest.instructions` field, not only a helper return value.

For Hermes, exercise the actual instruction construction boundary already owned by `tests/test_hermes_graph_agent.py` where practical.

## 10.4 Model-resolution parity

Characterize current resolution behavior before/after move.

Required cases where deterministically testable:

```text
missing OPENAI_API_KEY with require_api_key=True
require_api_key=False path
MODEL_POLICY action lookup compatibility
DUNGEONMIND_HERMES_GRAPH_MODEL override compatibility
provider == openai-api
base_url == https://api.openai.com/v1
```

Do not add a second model-policy implementation for tests.

## 10.5 PydanticAI Hermes-policy import removal

Static proof:

```text
pydantic_ai_agent_runtime.py
  does not import _GRAPH_SYSTEM_POLICY from hermes_graph_agent
  does not import _resolve_hermes_openai_inference from hermes_graph_agent
```

Handback lists remaining Hermes-named imports and why they are out of scope.

## 10.6 No product/runtime behavior expansion

Existing A3 proofs remain green for:

```text
tool schema parity
authoritative argument injection
unsupported capability fail-closed
product grounding
conversation-context classification
foreign-scope rejection
per-model-call A0 telemetry
cache normalization
partial provider failure
no production PydanticAI selection
```

---

# 11. Required verification

Run from repository root.

```bash
uv run pytest tests/test_agent_graph_policy.py -q
uv run pytest tests/test_pydantic_ai_agent_runtime.py -q
uv run pytest tests/test_hermes_graph_agent.py -q
uv run pytest tests/test_hermes_graph_agent_host.py -q
uv run pytest tests/test_agent_runtime.py tests/test_hermes_agent_runtime.py tests/test_live_query_hermes_graph.py -q
```

`tests/test_hermes_graph_agent_host.py`, `tests/test_agent_runtime.py`, `tests/test_hermes_agent_runtime.py`, and `tests/test_live_query_hermes_graph.py` are verification-only unless the bounded test discovery exception is truthfully triggered.

Static hygiene:

```bash
uv run ruff check \
  apps/live_control_server/services/agent_graph_policy.py \
  apps/live_control_server/services/hermes_graph_agent.py \
  apps/live_control_server/services/pydantic_ai_agent_runtime.py \
  tests/test_agent_graph_policy.py \
  tests/test_pydantic_ai_agent_runtime.py \
  tests/test_hermes_graph_agent.py

git diff --check
git diff --name-only <dispatch-base>...HEAD
```

Changed paths must stay inside §9.

No `uv lock` change is expected.

---

# 12. Backward-looking A3 state sync

A3 is complete and merged, but its handoff on main still represents CODE handback rather than final merge truth.

Before A4 is handed back for review, update:

```text
Docs/Plans/HANDOFF-AGENT-INTERACTION-pydantic-ai-adapter-experiment.md
```

with only facts now true:

```text
A3 status: COMPLETE / MERGED
PR: #663
accepted head: 4e4fa25268fc3c3bf2fec56fcbe465c4c7e08c55
merge SHA: 5eb4e030a66b09d98525f0f934c7e91051e48549
formal review cycles: 2
disposition: PROMISING_WITH_DEPENDENCY_BLOCKER
PydanticAI production selection: false
A4: active successor = graph Agent policy boundary
```

Do not invent A4 merge SHA or final review count.

No Campaign Supergraph roadmap/tracker edit belongs to A4; active CUTOVER #662 owns those state authorities.

---

# 13. Expected nano-commit story

Exact count is not contractual. A clean implementation story is:

```text
1. AGENT-INTERACTION: extract neutral graph Agent policy
2. AGENT-INTERACTION: consume neutral policy from Hermes and PydanticAI
3. AGENT-INTERACTION: characterize prompt and model-resolution parity
4. AGENT-INTERACTION: sync merged A3 predecessor state
```

Do not mix tool renaming, runtime selection, dependency modernization, context assembly, memory, or UI work into these commits.

---

# 14. CODE → REVIEW handback

The implementation handback must include:

1. exact PR URL / branch / head SHA;
2. exact dispatch-base SHA;
3. mission + merge-ready invariant;
4. nano-commit list;
5. exact changed-path list and diff stat;
6. active PR/write-lease recheck at dispatch and handback;
7. A3 predecessor facts (#663 / accepted head / merge / 2 cycles / disposition);
8. new neutral module API;
9. proof policy text was moved verbatim;
10. exact Hermes compatibility aliases retained;
11. exact remaining Hermes-named imports in PydanticAI;
12. model-resolution compatibility proof;
13. statement MODEL_POLICY semantics/env override/provider/base URL did not change;
14. statement no tool definition/executor moved;
15. statement AgentRuntime/product orchestration/A0/A1 did not change;
16. statement `pyproject.toml` / `uv.lock` did not change;
17. all §11 test results with exact totals;
18. baseline failures/waivers (`none` when none);
19. stop conditions encountered (`none` when none);
20. A3 backward-sync diff;
21. successor claims still false:
    - PydanticAI production selection;
    - tool-policy neutralization complete;
    - runtime lifecycle API;
    - ContextAssembler selected;
    - Interaction Memory durability;
    - source-selection Graph Assessment shipped.

---

# 15. Stop conditions

Stop and report rather than expanding A4 if any becomes true:

- accepted graph-Agent policy must be rewritten rather than moved;
- model/provider behavior must change;
- a new model registry/provider abstraction is required;
- MODEL_POLICY schema/action names must change;
- `DUNGEONMIND_HERMES_GRAPH_MODEL` must be renamed/removed;
- graph tool definitions/executor must move to make the extraction work;
- AgentRuntime contract or product orchestration must change;
- A0/A1 trace semantics must change;
- dependencies/lockfile must change;
- a public runtime selector is introduced;
- Interaction Memory/context persistence becomes necessary;
- active #660/#662 acquires any A4 production path;
- more than one independently useful capability appears.

Stop report:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
Contested path / active lease owner:
Proposed successor or serialization decision:
Authority sync needed:
```

---

# 16. Acceptance rubric

Accept A4 only when every applicable item is true:

- [ ] One neutral `agent_graph_policy.py` owns the accepted shared graph-Agent behavioral policy.
- [ ] Accepted policy text is verbatim-equivalent to A3 accepted head.
- [ ] One neutral resolver owns current graph-Agent OpenAI model-resolution behavior.
- [ ] Hermes consumes neutral policy/resolver without changing accepted behavior.
- [ ] PydanticAI consumes neutral policy/resolver directly.
- [ ] PydanticAI no longer imports `_GRAPH_SYSTEM_POLICY` from `hermes_graph_agent.py`.
- [ ] PydanticAI no longer imports `_resolve_hermes_openai_inference` from `hermes_graph_agent.py`.
- [ ] Remaining Hermes-named PydanticAI couplings are enumerated honestly.
- [ ] Existing MODEL_POLICY lookup semantics are unchanged.
- [ ] Existing `DUNGEONMIND_HERMES_GRAPH_MODEL` compatibility override is unchanged.
- [ ] Existing OpenAI provider/base URL behavior is unchanged.
- [ ] Existing credential failure behavior is unchanged.
- [ ] Tool definitions/executor are unchanged.
- [ ] AgentRuntime and product orchestration are unchanged.
- [ ] A0/A1 telemetry is unchanged.
- [ ] No dependency or lockfile change exists.
- [ ] No runtime selector/default change exists.
- [ ] No World authority/write behavior changes.
- [ ] A3 handoff is backward-synced truthfully.
- [ ] No Campaign Supergraph authority doc is edited while #662 owns that lane.

---

# 17. What A4 enables — but does not select

A4 should leave the Agent lane ready to choose a product-facing successor without carrying avoidable harness naming into it.

Likely later candidates remain:

```text
ContextAssembler v1
  product-owned ordered context composition + telemetry

Interaction Memory / Attention Ledger
  continuity of what GM + DMB are thinking about, not World truth

read-only contextual Graph Assessment
  Plan/Play selection → assess existing World representation
```

Do not select one merely because A4 merged.

The next re-anchor should consider:

- whether #660 has cleared the remaining Play authoring seam;
- whether #662 has completed D.2C4 and governed publication authority;
- which product journey can then be dogfooded end to end with the least new durable state.

---

# 18. Implementation evidence (CODE handback)

Dispatch base `e3d9bba768b8604f5a0c625af9d84ff5148a4db1` (parent `770f79cca4aa3c12aa8a35db2db77ce376f2ff9e`). Production PydanticAI selection remains false.

## 18.1 Neutral module API

```text
apps/live_control_server/services/agent_graph_policy.py
  GRAPH_SYSTEM_POLICY
  resolve_agent_graph_openai_inference(*, require_api_key=True) -> tuple[str, str, str] | str
```

Hermes compatibility aliases:

```text
GRAPH_SYSTEM_POLICY as _GRAPH_SYSTEM_POLICY
resolve_agent_graph_openai_inference as _resolve_hermes_openai_inference
```

PydanticAI remaining Hermes-named imports (out of A4 scope):

```text
hermes_graph_agent: _safe_ids_from_args, _summarize_tool_result
hermes_graph_interaction_tools: names / JSON defs / executor
```

## 18.2 Verification provenance

```text
uv run pytest tests/test_agent_graph_policy.py tests/test_pydantic_ai_agent_runtime.py -q
  25 passed, 2 warnings in 2.15s
  (7 new policy-ownership tests + 18 A3 adapter tests)

uv run pytest tests/test_hermes_graph_agent.py tests/test_hermes_graph_agent_host.py tests/test_agent_runtime.py tests/test_hermes_agent_runtime.py tests/test_live_query_hermes_graph.py -q
  169 passed, 10 warnings in 67.09s

uv run ruff check (leased Python files)
  All checks passed

git diff --check
  clean after handoff whitespace fix

Active open PRs at handback: #660 PLAY, #662 CUTOVER
  none own A4 production or test paths
```

Stop conditions encountered: `none`.
Baseline failures/waivers: `none`.
Paths outside §9: `none`.
Discovery-exception test edits: `none` (`tests/test_live_query_hermes_graph.py` still uses the Hermes compatibility alias).
Successor claims still false: PydanticAI production selection; tool-policy neutralization complete; runtime lifecycle API; ContextAssembler selected; Interaction Memory durability; source-selection Graph Assessment shipped.
