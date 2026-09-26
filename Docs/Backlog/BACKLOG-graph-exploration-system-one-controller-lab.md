---
document_id: dmb-backlog-graph-exploration-system-one-controller-lab
title: Graph Exploration Controller Lab — Oracle Traces to System One Policy
status: backlog
document_class: research_proposal
created_at: "2026-09-26"
authority: none
related_context:
  - Docs/Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md
  - Docs/Design/ACCEPTANCE-dogfood-readiness.md
  - current DungeonMind/Buddy graph-read and CUTOVER contracts at promotion time
promotion_gate: Re-anchor and decompose into independently useful capabilities before entering any active sequence.
---

# Graph Exploration Controller Lab — Oracle Traces to System One Policy

## Status

BACKLOG / RESEARCH PROPOSAL. This is not architecture authority, roadmap authority, or an implementation sequence.

This proposal extends the existing Agent graph-query benchmark. It does not replace that benchmark and does not create a second status owner. Promotion requires re-anchoring against current main, including the post-CUTOVER DungeonMind/Buddy authority boundary.

## 1. Idea in one sentence

Build a constrained graph-navigation game over the real World Graph, have a powerful code agent act as an oracle explorer against the existing challenging gold set, use successful and failed trajectories to empirically discover the smallest reusable graph-exploration action algebra, and only then test whether a cheaper System One / Jev-style controller can choose useful next actions.

## 2. Why this is worth testing

DungeonBuddy already has nearly all of the expensive prerequisites:

- a real campaign corpus with substantial cross-session complexity;
- durable graph identity, relationships, evidence, chronology, visibility, and revision semantics;
- graph-native read paths;
- challenging gold questions and goals;
- an existing graph-query benchmark that already separates product loadability, oracle retrieval, and real-Agent performance;
- a current Agent retrieval loop that can iteratively search, open objects, inspect neighborhoods/support, and read admitted evidence.

The existing benchmark currently describes Layer 1 as manual/scripted oracle retrieval: use the same production graph/retrieval contracts, but do not require the Agent to choose the sequence.

This proposal asks whether that Layer 1 can become a repeatable game played by a constrained code agent.

The research question is:

> What is the smallest bounded set of graph operations a strong controller needs to recover sufficient evidence for the real questions DungeonBuddy already cares about?

If the action set stabilizes, those trajectories become a natural dataset for testing cheaper retrieval policies. If the action set explodes into task-specific semantics, the elegant version of the idea is falsified early.

## 3. Relationship to the existing Agent graph-query benchmark

The existing benchmark remains the evaluation parent.

Its current structure is roughly:

~~~text
Layer 0 — product loadability
Can normal product reads open what publication says exists?

Layer 1 — oracle retrieval
Can a sensible bounded retrieval sequence recover enough evidence?

Layer 2 — real Agent
Can the current Agent choose and execute a sufficient investigation?
~~~

This proposal changes Layer 1 from primarily manual/scripted retrieval into:

~~~text
gold question
    ↓
constrained code-agent oracle
    ↓
legal bounded graph actions only
    ↓
trajectory + evidence package
    ↓
answer / abstention
    ↓
evaluation + failure classification
~~~

The code agent is not the production solution. It is the expensive oracle policy used to discover the retrieval instruction set and create decision traces.

## 4. Architecture boundary

The lab must remain a consumer of existing graph authority.

The graph/DungeonMind side remains responsible for:

- durable object identity;
- graph revision;
- campaign scope;
- evidence and provenance;
- graph topology;
- epistemic state;
- visibility;
- admissibility;
- truthful misses.

Buddy remains responsible for:

- interpreting the user request;
- conversational continuity;
- compiling or refining retrieval intent;
- synthesizing admitted evidence into an answer;
- explaining uncertainty and insufficiency.

The exploration controller is responsible only for:

- selecting the next legal retrieval move;
- deciding which admissible frontier to inspect;
- spending a bounded exploration budget;
- deciding when evidence appears sufficient or insufficient.

The controller must not become another graph, memory authority, identity layer, or corpus fallback.

Conceptually:

~~~text
User question
    ↓
Buddy / query compiler
    ↓
RetrievalIntent
    ↓
Graph exploration environment
    ↓
Controller chooses one legal next action
    ↓
Graph executes under pinned revision + admissibility
    ↓
Observation / bounded frontier
    ↺
Controller chooses again
    ↓
EvidencePackage
    ↓
Buddy / answer synthesizer
    ↓
Answer
~~~

## 5. Central hypothesis

A useful subset of DungeonBuddy retrieval can be modeled as a sequential decision process:

~~~text
state + bounded legal actions
    → choose next action
    → observe
    → update state
    → repeat
    → stop
~~~

The state contains the user goal, pinned graph context, accumulated evidence, exposed frontier, remaining budget, and diagnostics.

The controller chooses among legal actions produced by the environment. It does not invent arbitrary tool calls.

If this is the right abstraction, a small reusable action algebra should solve a meaningful share of difficult gold tasks.

## 6. Do not start with Jev

The first experiment is not "try Jev retrieval."

The first experiment is:

> Build the graph-navigation game and let a strong code agent play it under the same constraints a future cheap controller would face.

This ordering matters. Otherwise the action language will be designed around one controller technology instead of around real retrieval requirements.

Jev/System One becomes a later policy experiment after the environment, action vocabulary, and trajectory corpus exist.

## 7. Lab roles

### 7.1 Query compiler

A front model converts natural language into a retrieval goal, not a literal database query.

Illustrative intent:

~~~text
Question:
What is Maelthor actually trying to accomplish?

RetrievalIntent:
  goal: determine objective
  subjects: Maelthor
  evidence interests:
    actions
    chronology
    statements/beliefs
    relationships
    cosmology/planar links
  campaign: Campaign 2
  audience: GM
~~~

The exact RetrievalIntent schema should be discovered empirically. Do not freeze a rich intent ontology before the lab proves it is needed.

### 7.2 Graph exploration environment

The environment owns:

- exact World/revision binding;
- campaign/focus context;
- visibility/admissibility enforcement;
- generation of legal bounded actions;
- bounded observations;
- step/context budget;
- trace capture;
- deterministic failure behavior.

Secrets or inadmissible facts must never appear in the candidate menu simply because they would help answer the question.

### 7.3 Explorer / oracle policy

The initial explorer is a powerful code agent.

It may receive only:

- question or RetrievalIntent;
- current exploration state;
- accumulated evidence;
- legal actions and visible candidate metadata;
- prior observations;
- remaining budget.

It must not receive:

- gold answer;
- gold evidence labels;
- arbitrary repository search;
- unrestricted corpus reads;
- SQL/raw persistence access;
- graph storage internals;
- undeclared fallback retrieval.

The oracle is an expert player of the game, not an unconstrained coding agent allowed to solve the benchmark by any available route.

### 7.4 Evaluator / steward

A separate evaluator may have broader access to diagnose the trace.

It receives the gold task, trajectory, retrieved evidence, answer/abstention, and authority context, then classifies success or failure.

This separation lets the lab diagnose retrieval without handing the explorer the answer key.

## 8. Two meanings of admission

Keep these separate.

### Graph admissibility

Authority/security policy decides what may enter the retrieval environment at all:

- campaign scope;
- GM-only versus player-known visibility;
- epistemic/canon state;
- revision pin;
- provisional/unresolved identity policy.

This must fail closed.

### Retrieval admission

After graph admissibility, the retrieval system decides which allowed material is useful enough to spend context on or place in the final EvidencePackage.

A learned controller may influence retrieval admission.

It must never override graph admissibility.

## 9. Begin with an intentionally tiny action set

Do not design a rich graph-action ontology up front.

Seed hypothesis:

~~~text
RESOLVE
EXPAND
FOLLOW
OPEN_EVIDENCE
STOP_SUPPORTED
STOP_INSUFFICIENT
~~~

Possible meanings:

- RESOLVE — map query concepts to durable identities or explicit ambiguous/unresolved outcomes.
- EXPAND — expose a bounded admissible frontier adjacent to a selected graph object/focus.
- FOLLOW — select one exposed relationship/assertion/entity transition.
- OPEN_EVIDENCE — open graph-admitted evidence supporting a selected assertion/relationship.
- STOP_SUPPORTED — terminate because current evidence is sufficient.
- STOP_INSUFFICIENT — terminate because legal exploration cannot currently establish the answer.

Likely candidates such as SEARCH, FOLLOW_TIME, OPEN_SUPPORT, or FIND_CONTRADICTIONS do not enter the action set because they sound useful. They must earn their place through observed failures.

## 10. Action-discovery loop

For each selected gold task:

1. Start with the current minimal action set.
2. Let the constrained oracle attempt the task.
3. Record every legal alternative at every step.
4. Record the chosen action and resulting observation.
5. Produce an explicit EvidencePackage.
6. Generate an answer or abstention.
7. Evaluate retrieval and answer quality separately.
8. Classify failure before changing the environment.
9. Only when the environment lacks an expressible necessary move, propose the smallest reusable new operation.
10. Add the operation only after it passes the action-admission rules.
11. Rerun previous tasks as regressions.
12. Continue until action growth stabilizes or the hypothesis fails.

The code agent therefore helps discover the instruction set rather than merely generating answers.

## 11. Rules for adding an action

A new action must:

1. represent a graph/retrieval operation, not an answer strategy;
2. preserve exact identity and revision semantics;
3. respect visibility/admissibility;
4. address a reusable observed failure class;
5. contain no campaign-specific names or benchmark wording;
6. have bounded inputs and outputs;
7. have explicit failure behavior;
8. be independently testable;
9. preserve previously solved benchmark cases;
10. not introduce another retrieval backend.

Bad examples:

~~~text
FIND_MAELTHORS_MOTIVATION
TRACE_THE_VILLAIN_PLAN
ANSWER_WHY_LYSANDRA_SENT_THE_PARTY_NORTH
~~~

Potentially valid only if justified:

~~~text
SEARCH_GRAPH
FOLLOW_TIME
EXPAND_ASSERTIONS
OPEN_SUPPORT
FIND_CONTRADICTIONS
~~~

## 12. Failure taxonomy

Every miss should be classified before the action set changes.

### A. Controller-choice failure

The existing actions could reach sufficient evidence, but the controller chose poorly or exhausted budget.

Response: policy/controller problem, not action-algebra growth.

### B. Missing graph operation

Required evidence exists and is admissible, but no legal action sequence can expose it.

Response: candidate action-algebra expansion.

### C. Graph coverage failure

Required information is absent from durable graph materialization.

Response: graph/ingest coverage debt, not retrieval-controller work.

### D. Identity/resolution failure

Relevant material is split, ambiguous, provisional, incorrectly merged, or not resolvable.

Response: identity/graph issue unless the retrieval API itself fails to expose a valid outcome.

### E. Admission/policy failure

Evidence exists but is excluded by scope/visibility/epistemic rules.

Response: distinguish correct fail-closed behavior from policy defect.

### F. Frontier/bounds failure

The operation exists, but the bounded candidate set hides the required option.

Response: examine candidate generation, ranking, or budget before inventing a semantic action.

### G. Termination failure

The controller stops too early, explores after sufficiency, or fails to recognize insufficiency.

Response: sufficiency/controller policy.

### H. Synthesis failure

The EvidencePackage is sufficient and correct, but the answer model fails.

Response: retrieval succeeded; do not mutate graph exploration to compensate.

## 13. Trace contract

Trace capture is a primary research artifact from the first run.

Conceptual shape:

~~~text
GraphExplorationTrace
  task_id
  question
  retrieval_intent

  graph_context
    world_id
    campaign_id
    focus
    revision_id
    admissibility_profile

  steps[]
    step_index
    state_summary
    legal_actions[]
      action_type
      candidate/target identity
      bounded metadata visible to controller
    chosen_action
    action_arguments
    observation
    evidence_added[]
    diagnostics
    remaining_budget

  termination
    supported | insufficient | budget_exhausted |
    environment_error | controller_error

  evidence_package
    graph_object_ids[]
    assertion_ids[]
    evidence_anchor_ids[]

  answer
  retrieval_evaluation
  answer_evaluation
  failure_classification
~~~

### Preserve alternatives, not just chosen actions

For every step, record the legal alternatives that were available.

Example:

~~~text
state S17

A  EXPAND node/Lysandra
B  FOLLOW edge/Lysandra→MirathornCouncil
C  OPEN_EVIDENCE assertion/319
D  STOP_SUPPORTED
E  STOP_INSUFFICIENT

oracle choice: B
~~~

These state + alternatives + choice records are the useful dataset for later policy experiments.

## 14. EvidencePackage before synthesis

A correct answer does not prove retrieval worked. A strong model may guess correctly from weak evidence.

A bad answer also does not prove retrieval failed if the evidence package was sufficient.

Therefore:

~~~text
trajectory
    ↓
EvidencePackage
    ↓
retrieval evaluation
    ↓
answer synthesis
    ↓
answer evaluation
~~~

Retrieval and synthesis must receive separate scores/failure classes.

## 15. Metrics

Track at least:

### Answer quality
Reuse existing gold evaluation where possible.

### Evidence recall
Did the trajectory recover enough evidence to support the gold answer?

### Evidence precision
How much irrelevant evidence entered the final package?

### Search cost
- exploration steps;
- graph objects exposed;
- assertions exposed;
- evidence anchors opened;
- context bytes/tokens admitted;
- latency when comparable;
- controller inference cost.

### Termination quality
- correct supported stop;
- premature supported stop;
- correct insufficient stop;
- needless exploration after sufficiency;
- budget exhaustion.

### Trace validity
A run is invalid if it:
- crosses visibility/admissibility;
- reads the wrong revision;
- jumps nonexistent relationships;
- resolves through unauthorized first-match behavior;
- accesses corpus/storage outside the environment;
- hides a graph miss with undeclared fallback.

### Action-set complexity
Track:
- number of action types;
- usage frequency;
- tasks requiring each action;
- first failure that justified each action;
- marginal coverage gained;
- rate at which new actions are still being added.

A useful success signal is that the new-action rate declines as benchmark breadth increases.

## 16. Experimental progression

### Phase 0 — select representative gold

Choose difficult tasks spanning direct lookup, relationships, chronology, multi-hop reasoning, evidence support, ambiguity, insufficiency/abstention, and broad campaign synthesis.

Do not select only tasks already known to work.

### Phase 1 — build the game

First independently useful capability:

> An external controller can receive one benchmark task, see only legal bounded read actions against one pinned admissible graph revision, execute a trajectory, produce an EvidencePackage, and terminate without arbitrary graph/corpus access.

Do not include Jev in this slice.

### Phase 2 — oracle exploration

Run a strong code agent as the constrained controller.

Produce traces, EvidencePackages, answers, evaluation, and failure classifications.

### Phase 3 — empirical action discovery

Review repeated missing-operation failures.

For every proposed action:
- prove the task cannot reasonably be expressed with the existing algebra;
- show reuse across more than one case or a clearly general operation family;
- add focused environment tests;
- rerun prior benchmark tasks.

Stop if the action vocabulary becomes a zoo of task-specific semantics.

### Phase 4 — baseline controllers

Against the same environment, compare:
- random legal choice;
- simple heuristics;
- deterministic ranking/scoring;
- small conventional model;
- strong LLM/code-agent oracle.

This establishes a cost/quality frontier before introducing System One.

### Phase 5 — Jev / System One policy

Use recorded decision states to test a cheap bounded-choice controller.

Its core task is:

~~~text
Given:
  retrieval state
  legal candidate actions

Choose:
  next action
~~~

Possible subsidiary judgments:
- answer sufficient?
- frontier relevance?
- contradiction risk?

The System One controller receives no graph privileges or information unavailable to the baselines.

### Phase 6 — compare policy families

Compare:
- final answer quality;
- evidence recall/precision;
- steps;
- context admitted;
- latency;
- inference cost;
- termination quality;
- safety violations.

The useful result is a quality-versus-search-cost frontier, not merely a binary "Jev worked."

## 17. Why this remains useful if Jev fails

The lab still produces:

- an empirical graph-retrieval action vocabulary;
- a benchmarkable navigation environment;
- explicit traces for retrieval debugging;
- separation of retrieval and synthesis failures;
- concrete graph-coverage diagnostics;
- evidence about which operations difficult campaign questions actually need;
- a reusable harness for heuristic, small-model, System One, and full-agent policies.

Jev failure would not invalidate the environment or trace corpus.

## 18. Observability value

The trace creates a useful middle layer between "the graph returned context" and private model reasoning.

It can answer:
- which object seeded the search;
- which alternatives were available;
- which edge/evidence was followed;
- how much frontier was exposed;
- why the controller stopped;
- whether budget was exhausted;
- whether evidence was absent, inadmissible, hidden by bounds, or simply missed.

This is an execution trace over explicit actions, not chain-of-thought.

## 19. Initial lab scale

A deliberately small first cohort could be:

~~~text
20–40 challenging gold questions
one pinned representative graph revision
one campaign/admissibility profile
6 seed actions
fixed bounded step/context budget
strong code agent as oracle
trace + EvidencePackage + answer + evaluation
~~~

Illustrative outcome:

~~~text
30 tasks
18 solved with seed algebra
12 failed

5 graph coverage
3 controller-choice
2 missing chronology operation
1 missing disconnected-seed search
1 synthesis
~~~

That would justify perhaps two reusable additions, not twelve question-specific tools. The numbers are illustrative, not targets.

## 20. Explicit non-goals

This must not become:

- a new durable graph/session graph;
- a new graph authority model;
- an Agent-specific write path;
- unrestricted repo/corpus search disguised as retrieval;
- a replacement for identity semantics;
- a replacement for graph admissibility;
- a benchmark-specific action zoo;
- a requirement that Jev win;
- a full LLM hidden behind one giant SEARCH_RELEVANT_CONTEXT action;
- a compatibility fallback that hides graph misses.

## 21. Falsification criteria

Strong negative signals:

1. Action explosion — difficult tasks constantly require bespoke actions.
2. Frontier explosion — candidate menus become so large/rich that bounded choice adds little.
3. Oracle instability — a strong controller cannot produce repeatable useful trajectories.
4. Low reuse — new actions solve only their introducing task.
5. Graph insufficiency dominates — most misses are coverage/materialization failures.
6. Synthesis dominates — retrieval is already adequate and errors occur afterward.
7. Cost inversion — constructing menus/state costs as much as using the strong Agent.
8. Policy leakage — environment code accumulates semantic heuristics until the controller is no longer making the meaningful decision.

Any of these is still useful evidence.

## 22. Promotion gate

Before implementation:

1. Re-anchor against current main and post-CUTOVER DungeonMind/Buddy read authority.
2. Reuse the existing Agent graph-query benchmark and select a bounded gold cohort.
3. Confirm one pinned graph revision is normally product-readable.
4. Identify current retrieval seams that can expose legal actions without a parallel backend.
5. Separate environment, oracle runner, action-discovery steward, and cheap-controller experiments into independent capabilities.
6. Dispatch only the first independently useful capability.
7. Define exact failure behavior and owning tests.

Likely first capability:

> A bounded read-only graph-exploration environment exposes legal actions against one pinned admissible graph revision and records a deterministic trajectory without granting the controller arbitrary graph/corpus access.

The code-agent oracle runner and Jev policy remain successors until that environment is useful.

## 23. Open questions

- Which current gold questions have enough evidence annotations to score retrieval directly?
- Which current Hermes graph tools already correspond to RESOLVE, EXPAND, FOLLOW, or OPEN_EVIDENCE?
- Do path, timeline, compare, and coverage deserve first-class actions, or can they emerge from simpler primitives?
- What is the smallest RetrievalIntent shape needed?
- How are bounded candidate menus generated without silently embedding another powerful retrieval policy?
- How should sufficiency be scored without leaking gold evidence to the explorer?
- Which benchmark tasks should deliberately require STOP_INSUFFICIENT?
- Which trace fields should remain stable research artifacts across graph revisions?
- Can traces survive changes in object/revision identity strongly enough to train or evaluate later policies?

## 24. Backlog summary

Research bet: graph-native retrieval may be learnable as a bounded sequential decision process instead of requiring a free-form LLM agent at every step.

First experiment: build the game, not the Jev integration.

Oracle: a powerful code agent constrained to legal graph actions.

Primary discovery: empirically derive the smallest reusable action algebra from real gold trajectories and failures.

Primary artifact: traces containing state, every legal alternative, chosen action, observation, admitted evidence, cost, termination, and evaluation.

Later experiment: replace the oracle with cheaper policies, including Jev/System One, and compare them against the same environment.

Success signal: the action vocabulary stabilizes, the constrained oracle solves a meaningful share of difficult gold tasks, retrieval failures become cleanly diagnosable, and cheaper policies can be compared on quality/cost.

Failure is informative: action explosion, graph-coverage dominance, or poor cost separation would falsify the key assumptions before DungeonBuddy commits to a production retrieval-controller architecture.
