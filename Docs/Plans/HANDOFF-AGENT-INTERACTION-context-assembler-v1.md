---
pr_body_template: |
  ## Handoff pointer
  - Workstream: AGENT-INTERACTION / A5
  - Flow: AGENT-INTERACTION
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-AGENT-INTERACTION-context-assembler-v1.md`
  - Context decision: `Docs/Design/DECISION-agent-context-compilation.md`
  - Design base: `6b7706eec400129dbe01288630c443ae2d8a1e67`
  - Predecessor: A4 / PR #664 / accepted head `497dcfb6c21507ee1d0e26d009add0ce044c0ec6` / merge `cbdc342ef79c8e3db5d45fbb52468c0c258a4d47` / 1 review cycle

  ## Mission
  Establish one harness-neutral DungeonBuddy context-assembly boundary around the graph-Agent context that exists today, preserving accepted behavior and A0/A1 observability, while explicitly leaving room for future QueryContext, ResolvedSurfaceContext, WorldContext, and InteractionContext inputs. Do not implement SurfaceContext, Interaction Memory, new retrieval policy, prompt rendering, persistence, runtime selection, or World writes in A5.

  ## Design hold
  This handoff is intentionally NOT READY FOR DISPATCH until the steward completes the current SurfaceContext / relevance-budget design discussion and explicitly releases A5.
---

# HANDOFF — ContextAssembler v1 (A5)

**Created:** 2026-08-29  
**Updated:** 2026-08-29 — Agent Context Compilation decision sync  
**Status:** **DESIGN HOLD — NOT READY FOR DISPATCH**  
**Canonical handoff path:** `Docs/Plans/HANDOFF-AGENT-INTERACTION-context-assembler-v1.md`  
**Companion decision:** `Docs/Design/DECISION-agent-context-compilation.md`  
**Design branch:** `agent/context-assembler-v1-design`  
**Design base:** `6b7706eec400129dbe01288630c443ae2d8a1e67`  
**Workstream:** `AGENT-INTERACTION / A5`  
**Flow / owner:** `AGENT-INTERACTION`  
**Predecessor:** A4 — Graph Agent Policy Boundary v1  
**Predecessor PR:** #664  
**Accepted predecessor head:** `497dcfb6c21507ee1d0e26d009add0ce044c0ec6`  
**Predecessor merge:** `cbdc342ef79c8e3db5d45fbb52468c0c258a4d47`  
**Predecessor formal review cycles:** 1  

---

# 0. Why this handoff was revised before dispatch

The original A5 design correctly identified that DungeonBuddy needs one product-owned context-composition boundary, but it was too easy to read the existing graph-oriented inputs as the future definition of Agent context.

That is now explicitly rejected.

The accepted design direction is captured in:

```text
Docs/Design/DECISION-agent-context-compilation.md
```

Core invariant:

> **Rich typed state in; sparse relevant semantics out.**

A5 is still the right architectural slice, but it must establish a seam that future SurfaceContext and InteractionContext can enter without making today's graph context the universal model.

A5 is therefore held from implementation until the steward explicitly releases it after the current SurfaceContext/relevance discussion.

---

# 1. Re-anchor

Current design base:

```text
main = 6b7706eec400129dbe01288630c443ae2d8a1e67
```

A0–A4 remain complete:

```text
A0  Agent Turn Trace v1                 MERGED #654
A1  Advanced Trace Inspector            MERGED #656
A2  AgentRuntime Boundary               MERGED #659
A3  PydanticAI Adapter Experiment       MERGED #663
A4  Graph Agent Policy Boundary         MERGED #664
A5  ContextAssembler v1                 DESIGN HOLD / THIS SLICE
```

A4 established neutral DungeonBuddy ownership for shared graph-Agent behavior/model policy.

A5 moves the next product responsibility behind neutral ownership:

```text
What bounded context does this turn receive?
```

Current `main` has advanced through later CUTOVER work after A4. Before dispatch, recheck current `main`, active PRs, and write leases. Do not reuse the design-base active-lane assumptions as dispatch truth.

---

# 2. Frozen conceptual architecture

A5 must align with this future composition model:

```text
USER MESSAGE
   ↓
QueryContext

SURFACE PUBLICATION
   ↓ owning domain resolution
ResolvedSurfaceContext?

DUNGEONMIND
   ↓ scoped retrieval / exact revision
WorldContext

THREAD / FUTURE MEMORY
   ↓
InteractionContext

        └───────┬────────┘
                ↓
         ContextAssembler
                ↓
      sparse semantic turn context
                ↓
           AgentRuntime
```

A5 does **not** need to implement all four inputs.

It must simply avoid freezing a contract that makes them impossible or unnatural later.

The current production path provides only part of this future picture:

```text
current user question
resolved World graph envelope
GraphRetrievalSession
latest-recap typed context when applicable
bounded conversation history
runtime continuity handle
```

A5 extracts that existing composition behind neutral ownership.

---

# 3. User query is not SurfaceContext

The current user message remains its own primary input.

Example:

```text
What does Lysandra know about the swarm?
```

The explicit `Lysandra` reference is a first-class retrieval signal regardless of ambient Surface focus.

Future SurfaceContext may tell us that the user is currently running North Gate, inspecting an NPC, or editing a Plan document. Those facts improve interpretation/ranking; they do not gate explicit query retrieval.

A5 does not implement a new query/entity resolver, but its ownership/naming must not imply:

```text
Agent context = whatever the active Surface published
```

or:

```text
Agent context = World scope + retrieval session + history
```

Both are incomplete.

---

# 4. Surface publication is not model-facing context

Future SurfaceContext will be pointer/identity oriented.

Internal examples:

```text
run_ref
work_object_ref
work_revision_id
current_beat_ref
current_scene_ref
inspection_ref
WorkSelectionAnchor
```

Those values are for deterministic product/domain resolution.

They are not automatically useful LLM text.

The future assembler should be able to resolve them into semantic material such as:

```text
CURRENT PLAY
The GM is currently running North Gate during the defense of Mireward.
The gate is damaged and defenders are trying to stabilize the breach.
```

A5 does not add that Surface path yet.

It must not add a generic `surface_context: dict[str, Any]` placeholder merely to claim extensibility.

The exact SurfaceContext contract belongs to a successor proving slice.

---

# 5. ContextAssembler responsibility

DungeonBuddy Agent Interaction owns:

> **Which bounded context intentionally belongs in this Agent turn?**

The long-term role is a deterministic relevance compiler, not a UI-state serializer.

The current A5 implementation is narrower:

> **Put the context composition already happening in the accepted graph-Agent path behind one harness-neutral product boundary, with truthful structural telemetry and no behavior drift.**

The assembler must remain harness-neutral.

It must not import Hermes/PydanticAI execution implementations or provider APIs.

The harness/runtime adapter owns how accepted model-facing components are encoded for its model API.

The shared system policy remains DungeonBuddy product policy; A5 does not create a second provider-specific prompt owner.

---

# 6. Current behavior A5 may extract

Today the accepted graph-Agent product path performs these responsibilities inside Hermes-named orchestration:

```text
resolved World scope validation
server-selected graph root
bounded conversation-history copy
GraphRetrievalSession creation/reuse
latest-recap comparison attachment
existing admitted recap excerpt read for typed memory-lag workflow
retrieval-session projection
AgentWorldScope construction
AgentContextPacket construction
AgentRuntimeInvocation construction
runtime continuity forwarding
```

A5 may move those responsibilities behind:

```text
apps/live_control_server/services/agent_context_assembler.py
```

without changing their semantics.

A5 does not add new context sources.

---

# 7. Minimal v1 module

Create:

```text
apps/live_control_server/services/agent_context_assembler.py
```

Directional minimum:

```python
CONTEXT_SUMMARY_SCHEMA = "dmb_agent_context_summary_v1"


class AgentContextAssemblyError(ValueError):
    code: str
    status_code: int


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

Small naming variations are acceptable.

Do not introduce in A5:

```text
universal SurfaceContext schema
AgentContext component registry
arbitrary JSON context bag
context persistence repository
vector database
embedding model
new query/entity resolver
prompt renderer
runtime selector
```

---

# 8. Existing semantic parity

Preserve exactly:

## 8.1 World scope

```text
world_id
campaign_id
focus
admissibility
revision_id
server-selected graph root
```

No independent DungeonMind refresh path is added inside the assembler.

No campaign/admissibility broadening.

## 8.2 Conversation history

A5 receives the existing already-normalized role/content history.

It remains interaction continuity, not factual World authority.

Do not move/rename public compatibility normalization merely for aesthetic neutrality.

## 8.3 GraphRetrievalSession

Preserve:

```text
reuse caller-supplied session when present
otherwise create from accepted preflight using current question
```

Do not reconstruct or duplicate the retrieval packet.

Existing `project_for_hermes()` naming remains compatibility debt if changing it would require graph-memory edits.

## 8.4 Latest-recap typed context

Preserve the exact current memory-lag behavior and admitted recap excerpt path.

Do not generalize it into arbitrary corpus fallback.

## 8.5 Capability/run options

Preserve:

```text
WORLD_GRAPH_READ_POLICY
message = current question
thread_id / turn_id
runtime continuity id
execution root
```

---

# 9. Model-context decision A5 must respect

The implementation may still pass the exact same `AgentRuntimeInvocation` as today.

A5 is a behavior-preserving boundary extraction, not the token-budget optimization slice.

However its design comments/types/docs must preserve these laws for successors:

1. internal IDs/pointers are not automatically model-visible;
2. absent optional context should not consume model tokens;
3. Surface state supplies candidate context/retrieval signals, not mandatory prompt payload;
4. explicit query references outrank ambient Surface relevance;
5. current-work prose should eventually be query-conditioned and bounded;
6. graph retrieval should prefer bounded relevant claims/relationships over whole-object dumps;
7. tools remain the escape hatch for deeper information rather than preloading everything;
8. model context is budgeted for smallest sufficient context.

Do not implement speculative rendering to satisfy these laws in A5.

---

# 10. Observability

Observability remains first-class.

A5 should make the existing `context_assembly` phase describe the existing composition structurally without copying prose into baseline traces.

Keep:

```text
schema = dmb_agent_context_summary_v1
```

Suggested v1 safe scalars:

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

No model-facing/raw content belongs in this baseline summary.

Do not include:

```text
current question text
conversation history prose
recap excerpt prose
candidate summaries
claim prose
system prompt
source bodies
tool args/results
```

Provider-reported input-token usage remains authoritative after the call.

A later context-compiler slice may add pre-call component budget estimates/inclusion reasons once actual SurfaceContext exists.

---

# 11. Trace span

The existing A0 span:

```text
context_assembly
```

should carry the same safe scalar summary after assembly.

If needed, add only this small compatible builder capability:

```python
complete_phase(
    span_id,
    *,
    status="ok",
    attributes: Mapping[str, Any] | None = None,
)
```

Completion attributes merge with start attributes; completion values win duplicate keys.

Do not expose mutable trace internals.

---

# 12. Product compatibility

`hermes_graph_query.py` remains the accepted production product-query service in A5.

Keep:

```python
build_hermes_graph_turn_request(...)
```

callable with its current signature and tuple return shape.

It becomes a compatibility wrapper over the neutral assembler.

`run_hermes_graph_query(...)` may consume the richer `AgentContextAssembly` internally for telemetry.

Do not rename production route/backend identity in A5.

---

# 13. Error compatibility

Neutral assembler validation errors may use:

```text
AgentContextAssemblyError
```

The product boundary translates them back into the existing graph-query error behavior.

Preserve current codes/status semantics for invalid World context.

No new public route error schema.

---

# 14. Exact write lease — frozen only after release

**Do not dispatch from this section until the DESIGN HOLD is explicitly removed and current active leases are rechecked.**

Expected A5 implementation paths remain:

Create:

```text
apps/live_control_server/services/agent_context_assembler.py
tests/test_agent_context_assembler.py
```

Modify:

```text
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/agent_turn_trace.py
tests/test_agent_turn_trace.py
tests/test_live_query_hermes_graph.py
Docs/Plans/HANDOFF-AGENT-INTERACTION-graph-agent-policy-boundary-v1.md
Docs/Plans/HANDOFF-AGENT-INTERACTION-context-assembler-v1.md
```

Read-only unless the final re-anchor explicitly changes the lease:

```text
apps/live_control_server/services/agent_runtime.py
apps/live_control_server/services/hermes_agent_runtime.py
apps/live_control_server/services/pydantic_ai_agent_runtime.py
apps/live_control_server/services/agent_graph_policy.py
apps/live_control_server/services/live_agent_loop.py
src/graph_memory/**
apps/live-control-ui/**
pyproject.toml
uv.lock
```

No implementation agent may infer that this historical expected set is still collision-free. Recheck at dispatch.

---

# 15. Required proofs after release

At minimum:

```text
World scope parity
AgentRuntime invocation parity
retrieval-session create/reuse parity
latest-recap typed-context parity
conversation-history parity
runtime continuity parity
compatibility wrapper parity
neutral error translation
safe trace summary exact vocabulary
no raw prose in baseline trace
context_assembly span attributes
A0 builder compatibility
product grounding/citation regressions
Hermes adapter regressions
PydanticAI experiment regressions
```

No live OpenAI call is required for A5.

---

# 16. Stop conditions

Stop rather than expand A5 if implementation requires:

```text
new durable Agent state
Interaction Memory semantics
SurfaceContext producer/schema
Play Runtime changes
WorkSelection plumbing
new query/entity-resolution behavior
new graph retrieval semantics
GraphRetrievalSession schema changes
src/graph_memory edits
World scope/admissibility broadening
arbitrary corpus fallback
system-policy changes
prompt-rendering changes
AgentRuntime public-contract change
adapter-specific changes
frontend context UI/type redesign
dependency/lockfile changes
```

Any of those is a successor capability or requires redesign.

---

# 17. Success statement

A5 is successful when a reviewer can say:

> **DungeonBuddy has one harness-neutral product-owned boundary for the graph-Agent context composition that already exists today, and A0/A1 can tell us structurally what that composition contained without leaking prose. The boundary does not pretend today's graph-oriented inputs are the complete future definition of Agent context.**

---

# 18. Explicitly false after A5

A5 must not claim:

```text
SurfaceContext implemented
ResolvedSurfaceContext implemented
query-entity extraction implemented
query-conditioned Surface prose implemented
token-budget relevance compiler complete
Interaction Memory implemented
Attention implemented
WorkSelection Graph Assessment shipped
PydanticAI selected for production
World write behavior changed
```

---

# 19. Expected successor question

Once A5 is released and merged, the next design should ask:

> **Which real Surface should first prove `Surface publication → owning-domain resolution → ResolvedSurfaceContext → ContextAssembler`, and what is the smallest useful semantic context that Surface should contribute under token budget?**

Likely candidates are Plan or Play depending on current repository truth and active leases.

Do not choose from this document without re-anchoring.
