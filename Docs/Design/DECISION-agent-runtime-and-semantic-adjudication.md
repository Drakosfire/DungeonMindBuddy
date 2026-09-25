---
document_id: dmb-decision-agent-runtime-semantic-adjudication
title: AgentRuntime and Semantic Adjudication — Harness Boundary and Future Decision Layer
document_class: design_decision
status: active_direction
version: 1.0
created_at: "2026-09-22"
updated_at: "2026-09-22"
workstream: AGENT-INTERACTION
architecture_authorities:
  - "ARCHITECTURE-surface-interaction-layer.md"
  - "ARCHITECTURE-application-state-layer.md"
  - "ARCHITECTURE-campaign-supergraph.md"
companion_decisions:
  - "DECISION-agent-context-compilation.md"
runtime_contract:
  - "../../apps/live_control_server/services/agent_runtime.py"
research_candidates:
  - "Pi / pi-agent-core"
  - "Jev / TypeSafe AI"
---

# AgentRuntime and Semantic Adjudication — Harness Boundary and Future Decision Layer

## Status

This document captures current **design direction**, not an implementation
dispatch.

Two ideas are being preserved together because they reduce how much architecture
must live inside a generative Agent:

1. keep the Agent harness replaceable behind DungeonBuddy's existing
   `AgentRuntime`; and
2. explore a future narrow semantic-decision layer for judgments that do not
   need open-ended generation.

Current constraints are explicit:

- DungeonBuddy cannot sign up for or access Jev / TypeSafe AI today;
- Jev is therefore a research candidate only and creates **no dependency,
  credential, provider, model, or availability requirement**;
- Pi/`pi-agent-core` is a preferred next harness experiment, not a production
  selection;
- Hermes remains the current production runtime adapter;
- the existing PydanticAI adapter remains a challenger/experiment;
- any World Keeper layer is still a proposal until separately accepted and
  merged; this decision may describe its likely seam but does not grant it
  authority.

---

## 1. Runtime decision

DungeonBuddy owns the Agent product boundary. A harness implements execution
behind that boundary.

```text
DungeonBuddy AgentRuntime
        │
        ├── Buddy policy
        ├── Buddy ContextAssembler
        ├── Buddy tool contracts
        ├── Buddy trace model
        ├── Buddy surface context
        └── runtime adapter
                  │
                  ├── HermesAgentRuntimeAdapter        current
                  ├── PydanticAIAgentRuntimeAdapter    challenger / experiment
                  └── PiAgentRuntimeAdapter            preferred next experiment
                            │
                            └── pi-agent-core
```

The architectural object is **DungeonBuddy AgentRuntime**, not Hermes, Pi, or
PydanticAI.

A runtime adapter may own harness-specific translation and model/tool-loop
mechanics. It must not become the owner of:

- product prompts or domain meaning;
- Surface / APP-STATE / Play Runtime semantics;
- ContextAssembler policy;
- DungeonBuddy tool and capability contracts;
- authorization or World-write policy;
- DungeonBuddy trace semantics;
- durable World knowledge.

Harness-specific request, message, tool, and trace types stop at the adapter
boundary unless a second consumer proves a new Buddy-owned contract is needed.

---

## 2. Ownership around the Agent

The intended split is:

```text
Who decides what the Agent is doing?
    DungeonBuddy

Who assembles product/model context?
    DungeonBuddy ContextAssembler

Who defines capabilities and tool meaning?
    DungeonBuddy

Who executes the model/tool loop?
    replaceable AgentRuntime adapter + harness mechanics

Who executes ordinary one-shot inference?
    GenerationEngine where that consumer has migrated

Who stores/adjudicates durable knowledge?
    DungeonMind

Who turns a semantic World-change intent into a governed transaction?
    current Buddy publication path today
    potentially World Keeper if that proposal is accepted later
```

GenerationEngine does not become an Agent runtime merely because an Agent
eventually uses provider inference. A future runtime adapter may delegate
individual inference calls through GenerationEngine if GenerationEngine exposes
the required execution seam, but the Agent loop, tool policy, context assembly,
and product semantics remain Buddy-owned.

DungeonMind remains the authority for identity, assertions, evidence,
revisions/head, scopes/visibility, admission/retrieval, and governed durable
publication. Conversation state and harness memory are never World truth.

---

## 3. Pi direction

The next harness investigation should test a thin
`PiAgentRuntimeAdapter` against the existing Buddy-owned execution port.

The experiment should answer whether Pi gives DungeonBuddy a smaller,
composable loop while preserving the contracts already earned by A0–A7:

- ContextAssembler output remains Buddy-owned;
- SurfaceContext remains Buddy-owned;
- tool schemas and product capability policy remain Buddy-owned;
- runtime traces map into the existing Buddy trace model;
- World scope/revision/admissibility remain authoritative inputs;
- runtime selection remains visible and truthful;
- changing harness does not require a second Agent product architecture.

Do not build “DungeonBuddy on Pi.” Build a Pi adapter that can be removed
without redesigning DungeonBuddy.

The first useful proof should remain read-only and small. A Plan Ask turn is a
natural comparison witness because Plan is the current real Agent consumer.
Play Ask should not be resurrected from the closed A8 implementation merely to
prove Pi.

---

## 4. Semantic adjudication is a different job from generation

A useful class of model work looks more like a semantic predicate than a
creative Agent turn:

```text
Which of these candidates fits?
Does this passage support this claim?
Are these two mentions probably the same entity?
Is this retrieved evidence materially relevant?
Does this evidence contradict the query premise?
Is another retrieval round actually needed?
```

Those decisions can be valuable without giving the deciding model authority to
mutate product state.

The current research candidate for this role is Jev / TypeSafe AI. Because it
is unavailable to the project today, DungeonBuddy records only the desired
**role and invariants**, not Jev-specific APIs or runtime assumptions.

A future implementation may use Jev, another model/service, or no learned
adjudicator at all.

---

## 5. Retrieval adjudication

A future retrieval path may insert bounded semantic judgment after authoritative
DungeonMind retrieval/admission and before ContextAssembler commits scarce
model-facing budget:

```text
DungeonMind
  revision-pinned retrieval + admission
        │
        ▼
retrieved candidates
        │
        ▼
optional semantic adjudicator
  relevant?
  material evidence?
  contradictory evidence?
  redundant / weak?
        │
        ▼
ContextAssembler
        │
        ▼
AgentRuntime
```

Hard rules:

1. DungeonMind visibility/admissibility happens **before** semantic ranking.
2. The adjudicator cannot widen scope or expose inadmissible evidence.
3. Explicit user selections, exact requested objects, and mandatory product
   context cannot be silently erased by a semantic score.
4. Contradictory evidence is a first-class outcome; it must not simply be
   ranked away as “irrelevant.”
5. Every inclusion/demotion decision must be traceable enough to evaluate.
6. Adjudicator failure/unavailability falls back to the existing retrieval and
   ContextAssembler path.

The goal is not “more ranking.” It is **context adjudication**: spend expensive
generative context on evidence that actually matters while preserving the
evidence most likely to falsify a mistaken premise.

---

## 6. Ingestion and identity opportunities

Semantic adjudication may also help the source-to-World write path, but it never
gets merge/publication authority.

### Duplicate/entity alignment

After deterministic candidate generation, a semantic adjudicator may compare a
new mention/object against a small set of plausible existing entities:

```text
incoming entity candidate
        │
cheap exact / alias / lexical / embedding candidates
        │
        ▼
semantic comparison
  different | ambiguous | likely same
  supporting property judgments
        │
        ▼
identity proposal / review
        │
        ▼
governed publication path
        │
        ▼
DungeonMind
```

A strong “likely same” result may trigger a **merge proposal**, never a direct
merge. False merges contaminate every assertion and relationship attached to
both identities; the durable identity decision remains governed.

### Assertion and relationship verification

A generative extractor may propose candidate entities, assertions, or
relationships from a passage. A separate adjudicator may then ask narrow
questions:

```text
Does this passage support this exact assertion?
Does it contradict it?
Does it say nothing about it?
Is this relationship directly supported or merely co-occurrence/inference?
```

That is verification of a candidate, not open-ended extraction.

The preferred architecture is therefore:

```text
generative extraction
  proposes candidates
        │
        ▼
bounded semantic verification
        │
   clear / uncertain
     │        │
     │        └── stronger model or human review
     ▼
GraphContribution / governed proposal path
```

DungeonMind remains the durable authority.

If World Keeper is later accepted, the likely seam is:

```text
Buddy / Agent semantic World-change intent
        ↓
World Keeper
  semantic interpretation + governed transaction lifecycle
        ↓
DungeonMind
  durable governed knowledge
```

A semantic adjudicator may provide evidence to that lifecycle. It does not
replace it.

---

## 7. Tool and loop opportunities

A semantic decision layer may also help reduce unnecessary generative work:

- **tool/skill preselection** — narrow a large capability roster before exposing
  it to the main model;
- **tool preflight signal** — ask whether a requested capability appears to
  match the user's intent;
- **retrieval sufficiency** — signal whether current evidence is likely enough
  or another bounded read may be useful;
- **candidate escalation** — decide whether an ambiguous ingest/identity case
  should go to a stronger model or human review.

These are signals, not authorization.

Code and Buddy policy still decide:

- whether the tool is enabled;
- whether arguments are valid;
- whether a side effect is permitted;
- whether the loop may continue;
- what hard step/token/time limits apply;
- whether a World change may be prepared or published.

---

## 8. Design thesis: make less of Buddy agentic

The desired direction is not “give the Agent more intelligence until it
understands the whole architecture.”

Prefer:

```text
deterministic code
  exact product state
  authority and validation
  hard workflow transitions

semantic adjudication
  narrow probabilistic judgments over bounded candidates

generative Agent
  open-ended interpretation
  exploration
  candidate generation
  tool choice where genuinely useful
  synthesis
```

This should allow the conversational Agent to become smaller and easier to
replace while ContextAssembler, tool contracts, DungeonMind, GenerationEngine,
and any future World Keeper become stronger precisely because their jobs are
narrower.

---

## 9. Evaluation before adoption

No semantic adjudicator should enter an authority path first.

When access becomes possible, start in shadow mode against real DungeonBuddy
traffic or recorded dogfood.

### Retrieval shadow metrics

At minimum:

```text
must-have evidence recall
context tokens admitted
irrelevant context admitted
contradictory evidence preserved
final-answer groundedness
adjudicator latency/cost/failure rate
```

A context-saving system that drops the one fact required for the answer is a
regression.

### Identity/write shadow metrics

Record what the adjudicator would have suggested against real reviewed identity
and relationship decisions without changing durable state. Measure false-merge
risk separately from missed-merge rate.

Only after that evidence exists should a later design decide whether the
adjudicator may influence ranking, escalation, or proposal generation.

---

## 10. Explicit non-goals

This decision does **not**:

- add Jev or TypeSafe AI as a dependency;
- claim Jev access exists;
- add Pi as a dependency;
- select Pi as the production harness;
- remove Hermes;
- promote the PydanticAI challenger;
- move the Agent into GenerationEngine;
- change DungeonMind authority;
- accept World Keeper as merged architecture;
- authorize automatic identity merges;
- authorize Agent publication without the governed confirmation path;
- revive the closed A8 Play-Agent implementation;
- define a new implementation sequence.

It preserves the design target so later experiments can be judged against a
stable boundary rather than re-litigating ownership.
