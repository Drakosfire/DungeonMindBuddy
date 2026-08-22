---
document_id: dmb-design-magic-source-graph-assessment
title: Contextual Source → World Graph Assessment — Magic Moment Design Target
document_class: product_design_anchor
status: proposed_target
created_at: "2026-08-22"
updated_at: "2026-08-22"
workstream: AGENT-INTERACTION
magic_moment: MAGIC-SOURCE-GRAPH
architecture_authorities:
  - "ARCHITECTURE-surface-interaction-layer.md"
  - "ARCHITECTURE-campaign-supergraph.md"
companion_design:
  - "ARCHITECTURE-plan-surface-toolbox.md"
  - "ANCHOR-hermes-campaign-sensemaking-goal.md"
  - "DECISION-grounded-authored-world-object-lifecycle.md"
dogfood_structure:
  - "RUNBOOK-authored-world-object-magic-moment-dogfood.md"
---

# Contextual Source → World Graph Assessment — Magic Moment Design Target

## Status

This is a **directional product and interaction target** for a future DungeonBuddy Magic Moment.

It is stronger than an idea or backlog note and weaker than an implementation contract. It establishes the experience, authority boundaries, required context, and future dogfood test. It does **not** freeze exact schemas, UI copy, graph-search implementation, model provider, agent harness, or implementation sequence.

The target is:

> **While working naturally inside campaign material, the GM can highlight a word, sentence, or passage and ask DungeonBuddy whether it is already represented in the World Graph. DungeonBuddy uses the exact source selection, the surrounding work context, the current interaction context, and the current graph to assess what already exists. If the material is not adequately represented, DungeonBuddy can propose the smallest useful graph change — a claim, edge, node, or combination — while preserving provenance and requiring explicit governed review before anything becomes durable graph memory.**

The experience should feel like pointing at campaign material and asking a knowledgeable co-GM:

> “Is this already part of the world? If not, what should it be connected to?”

---

## 1. Product north star

The GM should not have to leave the material they are reading or writing in order to reason about graph memory.

Not:

```text
leave document
→ open Graph Review
→ search
→ copy text
→ explain context
→ manually construct graph changes
```

Desired:

```text
read / write campaign material
→ notice something important
→ highlight it
→ right click
→ Ask DungeonBuddy: Assess World Graph
→ inspect what already exists
→ optionally draft the smallest graph contribution
→ explicitly review / confirm
→ return to the same work
```

The product value is not automatic extraction. The value is **contextual judgment with provenance**.

The agent should help decide whether the selection is:

- already represented;
- new information about an existing object;
- a relationship between existing objects;
- a concept that deserves new graph identity;
- ambiguous between several interpretations;
- useful prose that should **not** become graph memory;
- insufficiently supported to decide.

---

## 2. Representative Magic Moment

The GM is reviewing an admitted recap and highlights:

> “The swarm was humming against the wall.”

They right click and choose:

```text
Ask DungeonBuddy
  → Assess World Graph
```

DungeonBuddy already has access to three kinds of context:

```text
CURRENT WORK
  Plan
  Campaign 2
  Session 27 prep
  active document / operation
  current interaction attention

SOURCE CONTEXT
  exact admitted recap
  exact source revision / digest
  exact selected span
  surrounding paragraph / semantic block
  source authority / admission state

WORLD CONTEXT
  Eldyrwild
  campaign scope
  current pinned World Graph revision
  admissibility / visibility
  graph retrieval capabilities
```

A useful assessment might conclude:

```text
Strong existing match
  Under-Hymn Brood

Contextual existing match
  Mireward North Gate

Not clearly represented
  the wall-damaging resonance / humming behavior

Recommended graph shape
  add a supported capability / behavior claim to Under-Hymn Brood

Possible edge
  Under-Hymn Brood → threatens / damages → Mireward North Gate

New node?
  Probably not yet. Create an independent phenomenon only if the
  resonance needs identity across multiple creatures or events.
```

The selected phrase is evidence and context. It is not automatically a node name.

---

## 3. Primary interaction

### 3.1 Select in place

The GM highlights material inside an admitted or editable campaign document.

First proving source types:

- ingested session recap;
- World Building document;
- Planning / prep document.

The source remains visible. The GM should not have to navigate away merely to establish context.

### 3.2 Invoke from the selection

The context menu exposes an Agent Interaction capability.

Directional copy:

```text
Ask DungeonBuddy
  → Assess World Graph
```

or:

```text
Connect to World
```

Do **not** lead with:

```text
Create node from selection
```

because that presupposes the graph-shaping decision the agent is being asked to help make.

### 3.3 Resolve existing graph context first

Before proposing anything new, DungeonBuddy investigates plausible existing graph material.

The retrieval path may use:

- exact labels and aliases;
- explicit graph references already present in the document;
- semantic graph search;
- current attention references;
- source-to-graph provenance links;
- bounded neighborhood expansion;
- admitted evidence / source-anchor inspection.

An empty first search is not sufficient reason to create a node.

### 3.4 Assess the graph shape

The agent should be able to recommend one or more of:

```text
ALREADY REPRESENTED

ADD CLAIM TO EXISTING NODE

ADD EDGE BETWEEN EXISTING NODES

PROPOSE NEW NODE

AMBIGUOUS — REVIEW CANDIDATES

KEEP SOURCE-ONLY

INSUFFICIENT CONTEXT / EVIDENCE
```

This is agent judgment, not a hidden CRUD form.

### 3.5 Present a Graph Assessment

The immediate output is a noncanonical **Graph Assessment**, not a graph write.

The answer should lead with campaign meaning. Existing matches should be inspectable as shared graph references.

Directional presentation:

```text
Selection
  “The swarm was humming against the wall.”

Likely existing world objects
  Under-Hymn Brood          strong match
  Mireward North Gate      contextual match

Assessment
  The Brood already exists, but this passage appears to add a specific
  wall-damaging behavior that is not clearly represented.

Recommended change
  Add a capability / behavior claim to Under-Hymn Brood.

Possible relationship
  Under-Hymn Brood → threatens → Mireward North Gate

New node?
  Not recommended yet.
```

Internal node IDs, digests, contribution IDs, and retrieval machinery belong in inspect / evidence / trace surfaces, not the campaign-facing answer.

### 3.6 Escalate only when the GM asks

Useful next actions:

```text
Inspect matches
Draft graph change
Ask a follow-up
Dismiss
```

`Draft graph change` enters the existing governed contribution path.

The assessment itself never mutates graph truth.

### 3.7 Governed review and commit

Durable mutation remains:

```text
agent assessment
→ preview_write / draft proposal
→ GM review
→ revision-bound confirmation
→ confirm_commit
→ committed World Graph revision
```

The agent remains a proposer, not a privileged writer.

After commit, the GM should be able to see the committed result and return to the originating document context.

---

## 4. Context contract

This interaction requires four independently owned context layers.

### 4.1 Work context

Owned by the active Surface / work object.

Examples:

```text
surface_id
world_id
campaign_id
prep / play / build focus
active work-object reference
current operation / workflow pointer
selected graph references already in the work
```

For Plan this may include prep/session focus.

For Play it may eventually include current Beat / Scene / Decision pointers.

This is ambient work context, not campaign truth.

### 4.2 Source-selection context

Owned by the Canvas / source artifact boundary.

The design requires a stable, inspectable selection identity equivalent to:

```text
SourceSelectionAnchor
  artifact_ref
  artifact_revision_or_digest
  source_domain
  authority / admission state
  block / anchor identity
  selection start / end
  selected text digest
  surrounding-context pointer
```

The exact runtime schema is deliberately not frozen here.

The invariant is:

> A proposal derived from a selection remains attributable to the exact source material the GM pointed at.

Do not reduce the operation to copied text without source identity.

### 4.3 Interaction context

Owned by DungeonBuddy Agent Interaction / future Interaction Memory.

Useful context may include:

- current thread pointer;
- recent conversational tail;
- explicit graph chips in the query;
- pinned / hot attention references;
- active artifact pointers;
- unresolved interaction open loops;
- bounded relevant prior episode summaries.

This context may resolve conversational identity and user intent.

It is **not factual campaign authority**.

### 4.4 World context

Owned by the Campaign Supergraph / Kernel path.

Includes:

- exact world / campaign lens;
- current or explicitly pinned graph revision;
- admissibility / visibility;
- graph search / expansion;
- source / evidence inspection;
- graph proposal capabilities.

Any factual conclusion about current world state must derive from this path, not stale conversational prose.

---

## 5. Source authority changes the answer

The same text should not produce the same graph recommendation when it comes from different source domains.

### 5.1 Admitted recap

Example:

> “The party collapses the eastern tunnel.”

This may support an occurred event / state contribution if the evidence and graph context warrant it.

### 5.2 World Building document

Example:

> “The migrating forest refuses to cross lines of salt.”

Likely assessment:

```text
Existing node
  Migrating Forest

Recommended
  add supported behavior / constraint claim

New node
  no
```

The source's actual admission / authority state still controls whether this is established, proposed, or otherwise qualified.

### 5.3 Planning / prep document

Example:

> “Lysandro confronts Lysandra during the second wave.”

DungeonBuddy may find Lysandra, Lysandro, Mireward, and siege context while still saying:

```text
These existing world objects are related to the passage.

This sentence describes planned future material rather than established
campaign history.

Do not silently promote it as an occurred event.
```

The system must preserve the difference between:

```text
planned
proposed
established
inferred
unknown
```

---

## 6. Graph-shaping judgment

This Magic Moment exists partly to avoid naive extraction.

The agent should prefer the **smallest graph change that preserves useful identity and retrieval**.

Bad:

```text
selected phrase
→ extract nouns
→ create nodes
```

Good:

```text
selected material
→ inspect existing identity
→ determine what deserves durable identity
→ prefer claim / edge when independent identity is unnecessary
```

The agent should explicitly distinguish:

**Claim on existing node**

```text
Migrating Forest
  avoids salt boundaries
```

**Edge between existing nodes**

```text
Under-Hymn Brood
  threatens
Mireward North Gate
```

**New node plus edges**

Use when the concept needs independent identity and future retrieval.

**No graph change**

Use when the material is descriptive texture, redundant, speculative, or not useful as durable graph memory.

Identity ambiguity must fail visibly. The agent must not fuzzy-pick a canonical object without meaningful GM review.

---

## 7. Interaction Memory and attention

This Magic Moment is a first-class consumer of the proposed DungeonBuddy Interaction Memory model.

After assessment, the thread may temporarily make these pointers salient:

```text
selected source anchor
matched graph nodes
candidate graph object
candidate edge / claim
active document
```

That should support a natural follow-up:

> “What does that imply for Session 27?”

Interaction memory may resolve what **“that”** refers to.

The World Graph must still be queried for factual claims.

Core invariant:

```text
attention survives
facts refresh
```

If graph head moves, the selection and attention identity may remain useful; cached factual retrieval does not silently become current truth.

A new unrelated thread must not inherit a prior thread's hot referent merely because it was recently active elsewhere.

---

## 8. Surface Interaction Layer fit

This target belongs to the shared Surface Interaction architecture.

The Canvas owns:

- document identity;
- selection identity;
- revision / digest;
- document admission state.

The active Surface publishes:

- campaign / session / work focus;
- graph lens;
- allowed capabilities.

The shared Agent Interaction host owns:

- invocation / thread continuity;
- contextual Graph Assessment projection;
- bounded pointer-only interaction state.

The Campaign Supergraph / Kernel owns:

- graph identity;
- graph revision;
- evidence / authority;
- proposal / confirmation / commit.

Plan may be the first proving surface. It must not become the permanent owner of the capability.

---

## 9. Agent-runtime / harness implication

This Magic Moment is a useful proving case for a harness-neutral `AgentRuntime`.

The right-click action should not be a Hermes-specific product contract.

Conceptually:

```text
Source selection
  ↓
DungeonBuddy AgentInvocation
  ↓
ContextAssembler
  - work context
  - source selection
  - interaction attention
  - authority / graph lens
  ↓
AgentRuntime
  - Hermes adapter
  - experimental PydanticAI adapter
  - future runtime if justified
  ↓
DungeonBuddy-owned graph tools / proposal capabilities
```

The harness must not own:

- source selection identity;
- document authority;
- graph scope / revision;
- interaction-memory authority;
- graph proposal semantics;
- confirmation / commit;
- canonical campaign memory.

The user-facing interaction should remain stable if the underlying runtime changes.

---

## 10. Product principles

1. **Campaign meaning first.**  
   “This looks like a new behavior of the Under-Hymn Brood” is better default prose than graph-internal terminology.

2. **Existing objects are inspectable.**  
   Matches use shared graph-reference / projection behavior. Do not make the GM retype what the agent just found.

3. **Provenance stays adjacent.**  
   The originating passage remains visible or immediately inspectable.

4. **Assessment happens in place.**  
   The GM should not need to navigate to Graph Review just to ask the question.

5. **Writes remain governed.**  
   Mutation may project the existing review capability, but the initiating surface never acquires graph-write authority.

6. **Return to the same work.**  
   Dismiss, inspect, or commit without losing the document, nearby position, Agent Interaction thread, or current work context.

---

## 11. Failure and stale-state behavior

### Source changed

If the source revision / digest changed after assessment:

```text
stale source selection
→ do not silently confirm
→ re-resolve / re-review
```

### Graph head changed

If the graph revision moved:

```text
assessment may remain historical
proposal must revalidate
new identity collisions / matches must surface
```

### Candidate merged / disappeared

Re-resolve through current graph identity rules. Never silently attach to another object.

### No useful graph match

Do not equate:

```text
no search result
```

with:

```text
create node
```

Broaden bounded retrieval, ask a consequential clarification, recommend source-only retention, or propose a new node when justified.

### Agent / provider failure

The source selection and current work remain intact. Retry must not create duplicate proposals or writes.

---

## 12. Explicit non-goals

This target does **not** require:

- autonomous background graph maintenance;
- autonomous canon writes;
- automatic node creation on highlight;
- automatic ingestion of every document edit;
- treating Planning prose as occurred campaign fact;
- making Agent Interaction a factual memory store;
- storing corpus bodies in the Agent Interaction provider;
- a graph-write path separate from Kernel governance;
- a surface-specific duplicate graph viewer;
- a universal ontology inferred by the agent;
- Hermes-specific session identity in the product contract;
- a final decision about the long-term agent harness.

---

## 13. Future Magic Moment dogfood

Working gate:

```text
MAGIC-SOURCE-GRAPH
Contextual source-selection → graph assessment → governed proposal
```

Use the existing Magic Moment result vocabulary:

```text
PASS
PASS_WITH_FRICTION
FAIL_PRODUCT
FAIL_ARCHITECTURE
BLOCKED_DEPENDENCY
```

### Intent

Prove that a GM can discover or propose graph structure directly from real campaign prose without copying context into a separate tool and without weakening graph authority.

### Required probes

Run at least three source-authority cases:

1. **Admitted recap** — selection contains plausible missing or incomplete graph memory.
2. **World Building document** — selection describes an existing world object and should prefer enrichment over needless new identity.
3. **Planning document** — selection describes planned future material and must remain visibly non-established.

### User-visible path

A successful dogfood should be approximately:

```text
1. Open real campaign document.
2. Highlight real text.
3. Right click.
4. Ask DungeonBuddy to assess the World Graph.
5. Inspect existing matches and explanation.
6. Choose Draft graph change when appropriate.
7. Review proposed node / claim / edges and evidence.
8. Confirm through governed graph review.
9. See the exact committed result.
10. Return to the same document context.
11. Ask a natural follow-up referring to the prior selection.
```

### Durable identities to record

At minimum:

```text
source artifact identity
source revision / digest
selection / source-anchor identity
Agent Interaction thread
graph revision assessed
matched node IDs
proposal / contribution identity
confirmation / commit identity
committed graph revision
resulting node / claim / edge identities
```

### What should feel magical

> “I pointed at one piece of my campaign and DungeonBuddy understood what I was working on, understood where the passage came from, checked the world I already have, and helped me integrate it without making me become a graph database operator.”

### Fail conditions

Fail when the GM must:

- copy/paste the selection into separate chat;
- manually explain which document / campaign the text came from;
- manually search Graph Review before assessment;
- manually retype node names the agent just found;
- accept a fuzzy identity guess without review;
- create a node merely because search returned nothing;
- lose source provenance or revision identity;
- treat Planning prose as established history;
- allow old conversation prose to substitute for fresh graph retrieval;
- leave the source and fail to return to the same work;
- confirm after material source / graph state became stale;
- depend on a Hermes-specific product interaction that cannot pass through the shared Agent Interaction boundary.

---

## 14. Architecture questions this target intentionally exposes

This target is useful because it forces several seams into one real interaction:

```text
How does a Canvas publish an exact selection?
How is source authority represented?
How does Agent Interaction receive surface context without owning it?
How does Interaction Memory preserve attention without becoming campaign truth?
How does graph retrieval distinguish existing identity from new information?
How does the agent choose claim vs edge vs node vs no change?
How does a noncanonical assessment become a governed proposal?
How are source and graph revisions preserved through review?
How can the same invocation contract run across different agent harnesses?
How does the GM return to the exact work after the interaction?
```

These are product architecture questions, not reasons to expose implementation machinery to the GM.

---

## 15. Success test for future implementation

The target is doing its job when a GM can repeatedly do this inside real campaign material:

```text
notice something
→ point at it
→ ask whether the world already knows it
→ understand the answer
→ integrate it when useful
→ keep working
```

without thinking about:

- node IDs;
- graph query syntax;
- source-path lookup;
- copied context;
- harness sessions;
- contribution plumbing;
- revision bookkeeping.

The system must still preserve those identities and authority boundaries underneath the experience.

The Magic Moment is not:

> “AI extracted a node.”

The Magic Moment is:

> **The GM points at meaning in their own campaign material, and DungeonBuddy helps connect that meaning to the living world without losing context, provenance, judgment, or control.**
