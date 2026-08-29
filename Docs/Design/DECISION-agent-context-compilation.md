---
document_id: dmb-decision-agent-context-compilation
title: Agent Context Compilation — Product Context, Retrieval, and Model-Facing Budget
document_class: design_decision
status: active_direction
version: 1.0
created_at: "2026-08-29"
updated_at: "2026-08-29"
workstream: AGENT-INTERACTION
architecture_authorities:
  - "ARCHITECTURE-surface-interaction-layer.md"
  - "ARCHITECTURE-application-state-layer.md"
  - "ARCHITECTURE-campaign-supergraph.md"
companion_targets:
  - "DESIGN-magic-moment-contextual-source-to-world-graph.md"
implementation_successor:
  - "HANDOFF-AGENT-INTERACTION-context-assembler-v1.md"
---

# Agent Context Compilation — Product Context, Retrieval, and Model-Facing Budget

## Status

This decision elaborates the existing Surface Interaction authority for Agent Interaction.

It does **not** change ownership:

```text
Surface / owning Buddy domain
  owns current product/work/runtime meaning

DungeonMind
  owns current World identity, scoped retrieval, evidence/admissibility,
  immutable revisions/head, and governed World publication

DungeonBuddy Agent Interaction
  owns query interpretation inputs, context assembly/compilation,
  interaction continuity, tool policy, and model-facing context selection

Agent harness
  owns model/tool-loop execution mechanics
```

The decision is about the membrane between rich product state and the finite context actually given to a model on one turn.

---

# 1. Decision summary

DungeonBuddy will treat Agent context as a **compiled product artifact**, not as a serialization of UI state.

The core pipeline is:

```text
USER MESSAGE
  explicit query / named concepts
        │
        ├───────────────┐
        │               │
        ▼               ▼
QueryContext       Surface publication
                        │
                        ▼
                 owning-domain resolution
                        │
                        ▼
                ResolvedSurfaceContext
        │               │
        └───────┬───────┘
                ▼
         DungeonMind retrieval
                │
                ▼
            WorldContext
                │
       InteractionContext
                │
                ▼
          ContextAssembler
                │
                ▼
      sparse semantic model context
                │
                ▼
           AgentRuntime
```

The assembler may consume rich typed identities, pointers, revisions, and runtime state internally.

The LLM should receive only the smallest semantically useful representation needed for the turn.

---

# 2. QueryContext and SurfaceContext are different inputs

The user message is the primary statement of what the user is asking about.

Example:

```text
What does Lysandra know about the swarm?
```

The explicit word `Lysandra` must receive baseline retrieval attention regardless of which Surface, Scene, document, or projection is currently active.

Therefore:

> **Explicit user-message references are first-class retrieval signals. Surface context may improve ranking and interpretation; it must not suppress or gate an explicit query reference.**

This does not authorize scope broadening. DungeonMind campaign/world/admissibility rules still apply.

SurfaceContext answers a different question:

> **Where is the user working, what does the owning product domain say is current, and what is the user explicitly inspecting or selecting?**

These two inputs meet inside context compilation; neither is subordinate to the other.

---

# 3. Surface publication is pointer-heavy

The active Surface should publish stable product identities and explicit user focus, not copied domain truth.

Examples:

```text
Play publication
  surface = play
  run_ref
  inspection_ref?
  WorkSelectionAnchor?

Plan publication
  surface = plan
  work_object_ref
  selection_anchor?
```

The browser/provider must not become authoritative for Play Runtime or WorkRevision meaning.

The owning server-side/domain service resolves those pointers.

Example:

```text
run_ref
  ↓ Play domain / APP-STATE
pinned playable revision
current Beat
current Scene?
selected options
resolved Beat state
linked Combat handle?
```

The resulting `ResolvedSurfaceContext` is a turn-scoped semantic snapshot.

Agent Interaction consumes it. It does not infer or persist competing domain state.

---

# 4. Internal identities are not automatically model context

Values such as:

```text
run_ref
work_revision_id
beat_id
scene_id
surface lease token
retrieval session id
World revision id
```

are important for:

- authority;
- exact reads;
- validation;
- tool execution;
- cache/replay identity;
- observability;
- stale-state detection.

They usually have little standalone reasoning value to an LLM.

Therefore:

> **Internal identity exists to make context assembly deterministic, reproducible, and observable. It is not included in the model prompt merely because it exists.**

When an internal concept needs model understanding, render its semantic consequence instead.

Bad default model context:

```text
current_scene_ref: scene:123
current_beat_ref: beat:456
inspection_context: none
```

Preferred:

```text
CURRENT PLAY

The GM is currently running North Gate during the defense of Mireward.
The gate is damaged and defenders are trying to stabilize the breach.
```

Absent optional context consumes zero model tokens.

---

# 5. SurfaceContext has semantic roles, not one undifferentiated focus

Surface state may simultaneously express different kinds of relevance.

For Play, the important conceptual roles are:

```text
enclosing context
  durable phase / Beat context

primary current context
  current Scene when present; otherwise current Beat

inspection context
  object the user intentionally opened / inspected

selection context
  exact work/span the user explicitly pointed at

retrieval seeds
  contextual / At-a-Glance refs and other nearby identities
```

These roles must not be collapsed.

Opening an NPC does not make that NPC the current Scene.
Opening Combat does not replace the current Scene.
A text selection is stronger turn-local intent than ambient At-a-Glance presence.

The exact runtime schemas remain to be designed by the first proving Surface.

---

# 6. ContextAssembler is a deterministic relevance compiler

ContextAssembler should evolve toward answering:

> **Given the user query, authoritative current product state, current World scope, and interaction continuity, what is the smallest sufficient context this model turn should receive?**

It is not primarily a serializer.

Its conceptual inputs are:

```text
QueryContext
ResolvedSurfaceContext?
WorldContext
InteractionContext
```

Its model-facing output is sparse semantic material such as:

```text
system / capability policy
relevant current work material
query-relevant World context
relevant interaction continuity
current user message
```

The assembler owns **what context belongs in the turn**.

The harness/runtime adapter owns **how the accepted structured/model-facing components are encoded for its model API**.

The shared system policy remains DungeonBuddy product policy; ContextAssembler does not become the owner of one giant provider-specific prompt string.

---

# 7. Deterministic work should happen before the LLM

A large portion of context selection can be deterministic or classical retrieval.

Preferred deterministic responsibilities include:

```text
active Surface resolution
Run / WorkObject / WorkRevision resolution
current Beat / Scene resolution
exact WorkSelectionAnchor resolution
exact graph label / alias lookup
explicit graph refs already in authored work
DungeonMind scoped search
bounded graph neighborhood / path expansion
campaign / admissibility filtering
session/current-position filtering
lexical relevance
structured predicate/relationship filtering
context deduplication
character/token budget accounting
ordering and truncation
trace explanation of inclusion decisions
```

Embedding-assisted ranking may be added later when justified, while remaining deterministic at invocation time.

Use LLM judgment where semantic reasoning is actually valuable:

```text
ambiguous identity resolution after deterministic candidates exist
complex query interpretation
cross-fact reasoning
synthesis
choosing whether deeper tools are needed
```

Do not spend an LLM call to discover product state DungeonBuddy already knows exactly.

---

# 8. Relevance priority

Directional priority tiers:

```text
P0 — mandatory
  system / capability policy
  current user message

P1 — explicit
  exact user-mentioned World identities / strong label-alias matches
  exact selection
  directly requested object/artifact

P2 — current
  current Scene/work material when relevant
  enclosing Beat/operation framing
  explicit inspection target

P3 — relational
  graph facts/paths connecting explicit query objects to current context
  bounded relevant neighboring claims/relationships

P4 — continuity
  recent conversation required for pronouns/follow-ups
  later: pinned/hot Interaction Attention

P5 — ambient/optional
  At-a-Glance/contextual refs
  older conversation
  distant graph neighbors
```

These tiers are ranking/budget guidance, not a frozen scoring formula.

Surface refs are generally retrieval seeds. They are not access control.

---

# 9. Token-budget law

The target is **smallest sufficient context**, not maximum available context.

A large model context window is reserve capacity, not an invitation to preload the campaign.

Context compilation should:

1. reserve room for system policy, tools, the current user message, model output, and later tool rounds;
2. fill working context in relevance order;
3. prefer bounded semantic snippets over whole objects/documents;
4. deduplicate material available through multiple sources;
5. omit empty/absent sections entirely;
6. preserve an escape hatch through read/search/expand tools rather than preloading every possibility.

Provider-reported input tokens remain the authoritative post-call token measure.

Pre-call budgets may use deterministic character/token estimates for selection and diagnostics, but must not pretend to be provider billing truth.

---

# 10. Query-conditioned current material

Even current Surface material is not automatically entitled to a full prompt allocation.

Example while the GM is in North Gate:

```text
Question: What is Lysandra's father's name?
```

A compact orientation may be enough:

```text
The GM is currently running the North Gate scene during Hold the Breach.
```

The World retrieval can answer the explicit Lysandra question.

But for:

```text
Would Lysandra know the creatures are damaging the North Gate?
```

current Scene material is directly relevant and should receive more budget.

Therefore:

> **Current Surface state creates candidate context. Query relevance decides how much of that candidate becomes model-facing material.**

Exact selection is the major exception: an explicit selection is high-priority turn-local input, subject to its own bounded rendering.

---

# 11. Lysandra reference story

Assume the GM is currently in Play:

```text
Run: Session 27
Beat: Hold the Breach
Scene: North Gate
```

The GM asks:

```text
What does Lysandra know about the swarm?
```

Before the LLM sees the turn, DungeonBuddy can deterministically:

```text
1. Resolve current Play state from the active Run.
2. Search the current DungeonMind scope with the full user query.
3. Resolve `Lysandra` through exact/strong label-alias identity when possible.
4. Resolve likely `swarm` candidates.
5. Retrieve bounded claims/relationships for those explicit query entities.
6. Use North Gate / Hold the Breach / At-a-Glance refs as relevance signals.
7. Prefer graph paths/claims connecting explicit query entities to current context.
8. Select only the relevant current Play prose and World facts under budget.
```

A reasonable model-facing packet might then contain:

```text
CURRENT PLAY
The GM is running North Gate during the defense of Mireward.
The gate is damaged and defenders are trying to stabilize the breach.

RELEVANT WORLD CONTEXT
Lysandra Ironveil
- bounded query-relevant claims

Under-Hymn Brood
- burrowing swarm involved in the assault
- its humming loosens structures

Knowledge gap
- no retrieved claim establishes that Lysandra personally observed or learned
  the wall-damaging behavior

USER
What does Lysandra know about the swarm?
```

The model does not need `run_ref`, Beat/Scene IDs, null inspection fields, or the entire Runbook to reason about this turn.

---

# 12. World scope remains authoritative

“Explicit references work regardless of the current lens” means regardless of **ambient Surface focus**.

It does not mean:

```text
ignore campaign scope
ignore visibility/admissibility
silently switch to world scope
open arbitrary source files on misses
```

An explicit query can justify searching the configured DungeonMind scope even when an object is absent from current Surface material.

If useful material exists only outside the authorized/requested scope, the product should expose the scope limitation or use an explicitly governed wider query path. It must not silently broaden authority.

---

# 13. Observability

Every context-compilation turn should eventually be inspectable without leaking prompt bodies by default.

Useful telemetry includes:

```text
query exact-label matches
ambiguous query matches
surface kind
surface candidates considered
current-work blocks included / omitted
World candidates considered
World objects / claims / relationships included
interaction items included
character/token estimates by component
final assembled input size estimate
truncation / budget pressure
reasons for major inclusions
```

Baseline traces should remain structural/quantitative.

Raw conversation history, source prose, current-work prose, prompts, tool arguments/results, and World claim text remain excluded from baseline telemetry unless a separately governed forensic mode explicitly permits them.

---

# 14. Relationship to existing Surface Interaction authority

This decision preserves the existing law:

```text
Surface/domain
  publishes exact pointers and current-work/runtime meaning
        ↓
Agent Interaction
  resolves/compiles useful turn context
        ↓
DungeonMind
  supplies current World authority
```

It adds this clarification:

> **The Surface publication is not itself the LLM prompt. Surface context is pointer/identity oriented; ContextAssembler resolves those identities and emits sparse semantic model context only when useful for the current query.**

The existing Play law remains:

```text
Scene = dominant current workspace when present
Beat  = enclosing context
At-a-Glance/contextual refs = retrieval seeds, not access control
```

---

# 15. Relationship to the Source → World Magic Moment

The Magic Moment is a high-priority consumer of this decision.

For a selection-driven turn:

```text
explicit selected WorkSelectionAnchor
+ user query
+ resolved current work context
+ optional EvidenceAnchor
+ current DungeonMind scope/retrieval
+ relevant interaction continuity
        ↓
context compilation
        ↓
noncanonical Graph Assessment
```

The selection does not remove normal query retrieval. Named entities in the user's ask still receive first-class retrieval attention.

WorkSelectionAnchor identity and EvidenceAnchor authority remain distinct.

---

# 16. Sequencing consequence

This decision should be frozen before A5 implementation because A5 establishes the context-composition seam future SurfaceContext must enter.

A5 may still implement only the context inputs that exist today.

A5 must **not** fossilize the assumption:

```text
Agent context = World scope + retrieval session + conversation history
```

Instead A5 establishes one product-owned assembly boundary whose conceptual future inputs are:

```text
QueryContext
ResolvedSurfaceContext?
WorldContext
InteractionContext
```

The first executable `SurfaceContext publication → owning-domain resolution → ResolvedSurfaceContext` path is a successor capability, likely A6, and should prove one real Surface end-to-end.

A5 does not need to invent that schema or producer now.

---

# 17. Explicit non-goals

This decision does not select:

- a universal SurfaceContext wire schema;
- a universal scoring formula;
- an embedding model or vector database;
- Interaction Memory persistence;
- Attention persistence;
- a new AgentRuntime public contract;
- a new system prompt;
- automatic world-scope broadening;
- model-visible internal IDs by default;
- automatic inclusion of whole Runbooks/documents;
- provider-specific prompt templates;
- PydanticAI production selection.

Those require separate evidence and capability slices.

---

# 18. Acceptance questions for future context work

For each new context producer, ask:

1. Who owns the underlying truth?
2. What stable pointer can the Surface safely publish?
3. Which owning service resolves that pointer?
4. What semantic context could help this specific query?
5. Can relevance be selected deterministically before an LLM call?
6. What is the minimum useful model-facing representation?
7. What should remain retrieval seed only?
8. What authority/scope restrictions still apply?
9. What happens under token budget pressure?
10. How will A0/A1 tell us what was included without leaking content?

Core invariant:

> **Rich typed state in; sparse relevant semantics out.**
