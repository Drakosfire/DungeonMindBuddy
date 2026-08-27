---
document_id: dmb-design-magic-source-graph-assessment
title: Contextual Source → World Graph Assessment — Magic Moment Design Target
document_class: product_design_anchor
status: proposed_target
version: 1.1
created_at: "2026-08-22"
updated_at: "2026-08-26"
workstream: AGENT-INTERACTION
magic_moment: MAGIC-SOURCE-GRAPH
architecture_authorities:
  - "ARCHITECTURE-surface-interaction-layer.md"
  - "ARCHITECTURE-application-state-layer.md"
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

It is stronger than an idea or backlog note and weaker than an implementation contract. It establishes the experience, authority boundaries, required context, and future dogfood test. It does **not** freeze exact schemas, UI copy, graph-search implementation, model provider, agent harness, or implementation sequence beyond the dependency boundaries recorded here.

The target is:

> **While working naturally inside campaign material, the GM can highlight a word, sentence, or passage and ask DungeonBuddy whether it is already represented in the World Graph. DungeonBuddy uses the exact selected work, surrounding work context, current interaction context, and DungeonMind's current World authority to assess what already exists. If the material is not adequately represented, DungeonBuddy can propose the smallest useful graph change — a claim, edge, node, or combination — while preserving provenance and requiring explicit governed review before anything becomes durable World memory.**

The experience should feel like pointing at campaign material and asking a knowledgeable co-GM:

> “Is this already part of the world? If not, what should it be connected to?”

### 0.1 Re-anchored authority truth — 2026-08-26

This target now assumes the post-cutover ownership model:

```text
DungeonMind
  owns World identity
  immutable World revisions + head
  source/evidence admissibility for World reads
  scoped World projection/retrieval
  governed World publication

DungeonBuddy
  owns product surfaces
  WorkObject / WorkRevision / WorkingCopy
  Play Runtime and other Buddy application state
  source/work selection UX
  Agent Interaction
  interaction-memory semantics
  tool policy
  proposal/review UX
  harness/runtime selection

Agent harness
  orchestrates model + tool turns
  does not become World or source authority
```

DungeonMind is an independent knowledge library and DungeonBuddy is a replaceable client. The agent harness is intentionally outside the DungeonMind library boundary.

The old shorthand “Campaign Supergraph / Kernel owns the graph” is therefore retired for this target. Buddy may retain product-side authority ports and compatibility vocabulary, but durable World authority is DungeonMind.

### 0.2 Current implementation-readiness truth

The final Magic Moment spans capabilities that are not equally mature yet.

Already strong enough to build against:

- DungeonMind-native World projection/retrieval;
- exact World revision pins and scoped admissibility;
- Buddy Plan / Runbook `WorkObject` + immutable historical `WorkRevision`;
- Buddy Play Runtime / active-Run continuity on PostgreSQL;
- shared Agent Interaction / Surface Interaction direction.

Still settling:

- complete source/provenance identity for every editable corpus/document family;
- D.2C3/D.2C4 remaining CUTOVER continuity;
- the final manual-authoring → governed DungeonMind publication seam;
- physical retirement of the Buddy graph engine.

Therefore the first implementation should prove **contextual assessment** before coupling the Magic Moment to the in-flight final World-authoring seam.

---

## 1. Product north star

The GM should not have to leave the material they are reading or writing in order to reason about World memory.

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
- a concept that deserves new World identity;
- ambiguous between several interpretations;
- useful prose that should **not** become World memory;
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

DungeonBuddy can assemble four kinds of context:

```text
CURRENT WORK
  active surface
  campaign / session focus
  active work object / operation
  current interaction attention

WORK SELECTION
  exact Buddy product object
  exact revision / digest
  exact selected span
  surrounding paragraph / semantic block

EVIDENCE CONTEXT, WHEN AVAILABLE
  DungeonMind SourceArtifact
  DungeonMind SourceRevision
  source domain / scope / visibility
  admitted source anchor / evidence identity

WORLD CONTEXT
  world / campaign scope
  current or pinned DungeonMind revision
  admissibility
  native World retrieval capabilities
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

The selected phrase is context and may be evidence when a valid evidence anchor exists. It is not automatically a node name and it is not automatically authoritative merely because the GM selected it.

---

## 3. Primary interaction

### 3.1 Select in place

The GM highlights material inside an admitted or editable campaign document.

Final proving source types:

- ingested session recap;
- World Building document;
- Planning / prep document.

The source remains visible. The GM should not have to navigate away merely to establish context.

Implementation sequencing does **not** require all three source types to land at once. Plan is the preferred first proving source because Buddy already has stable WorkObject / historical WorkRevision identity there.

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

### 3.3 Resolve existing World context first

Before proposing anything new, DungeonBuddy investigates plausible existing World material through DungeonMind-native capabilities.

The retrieval path may use:

- exact labels and aliases;
- explicit graph references already present in the document;
- deterministic/semantic product query assistance where separately justified;
- current attention references as retrieval seeds;
- DungeonMind search;
- bounded neighborhood expansion;
- evidence retrieval;
- admitted source-anchor resolution.

An empty first search is not sufficient reason to create a node.

The agent may decide how to investigate; it may not broaden DungeonMind scope/admissibility or reconstruct retired Buddy graph authority to recover excluded rows.

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

Evidence status
  admitted recap span available
```

Internal IDs, digests, contribution IDs, and retrieval machinery belong in inspect / evidence / trace surfaces, not the campaign-facing answer.

### 3.6 Escalate only when the GM asks

Useful next actions:

```text
Inspect matches
Draft graph change
Ask a follow-up
Dismiss
```

The assessment itself never mutates World truth.

`Draft graph change` is a product proposal action. Its durable publication path must use the accepted DungeonBuddy authority port(s) into DungeonMind; it must not resurrect the retired Buddy graph writer.

### 3.7 Governed review and commit

The target end-state remains:

```text
agent assessment
→ Buddy-owned draft / proposal
→ GM review
→ revision-bound confirmation
→ governed DungeonMind publication
→ committed DungeonMind World revision
```

The agent remains a proposer, not a privileged writer.

The exact D.2C4 manual-authoring/source-admission port names are CUTOVER-owned and must be consumed once settled rather than pre-invented here.

After commit, the GM should see the exact committed result and return to the originating work context.

---

## 4. Context contract

This interaction requires context from independently owned domains. The runtime may assemble them into one invocation packet, but assembly does not collapse authority.

### 4.1 Work context

Owned by the active Surface / Buddy work domain.

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

For current Play, use the accepted table model:

```text
run_ref
exact pinned playable WorkRevision
current_beat_ref
current_scene_ref?       # optional; Scene normally dominates when present
resolved_beat_refs
selected_options
contextual / At-a-Glance refs
focused_projection?      # ephemeral attention only
linked_combat_handle?
```

There is no durable `currentDecisionId`; Decision focus is ephemeral and must not be invented as Runtime authority.

This is ambient work/runtime context, not World truth.

### 4.2 Work selection anchor — Buddy product identity

The selection the GM points at is first a **Buddy product/work identity**, not automatically DungeonMind evidence.

Conceptually:

```text
WorkSelectionAnchor
  work_object_ref / source-work ref
  exact work revision or digest
  block / anchor identity
  selection start / end
  selected text digest
  surrounding-context pointer
```

For Plan / Runbook content, APP-STATE already provides stable WorkObject + immutable historical WorkRevision identity.

The invariant is:

> DungeonBuddy can always say exactly what product material the GM pointed at, even when that material is not admissible World evidence.

Do not reduce the operation to copied text without work identity.

### 4.3 Evidence anchor — DungeonMind authority, optional

A WorkSelectionAnchor and a World evidence anchor are different concepts.

When the selected work is backed by an admitted source, the invocation may also carry or resolve:

```text
EvidenceAnchor
  source_artifact_id
  source_revision_id
  source_domain
  world / campaign scope
  visibility / lifecycle / admission
  DungeonMind anchor / evidence identity
```

This is what lets the system say:

```text
“I know exactly what you selected”
```

separately from:

```text
“DungeonMind accepts this source span as evidence for this World operation.”
```

A planning sentence may have an excellent WorkSelectionAnchor and no EvidenceAnchor at all. That is valid and expected.

A source/evidence anchor must be validated by current DungeonMind source/provenance state; a graph revision pin alone is not sufficient to cache admissibility forever.

### 4.4 Interaction context

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

### 4.5 World context

Owned by DungeonMind.

Includes:

- exact world / campaign lens;
- current or explicitly pinned immutable World revision;
- admissibility / visibility;
- World search / exact-object retrieval;
- bounded neighborhood expansion;
- evidence retrieval;
- admitted source-anchor resolution;
- governed publication capabilities when exposed through the Buddy authority port.

Any factual conclusion about current World state must derive from DungeonMind authority, not stale conversational prose or a retired Buddy graph store.

---

## 5. Source authority changes the answer

The same text should not produce the same graph recommendation when it comes from different work/source domains.

### 5.1 Admitted recap

Example:

> “The party collapses the eastern tunnel.”

If the recap selection resolves to valid DungeonMind source/evidence authority, it may support an occurred event/state contribution.

Likely questions:

```text
existing event / location?
new event claim?
changed structural state?
relationship to party / threat?
```

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

Whether it may directly support publication depends on its actual source/admission state, not merely that the document is called “World Building.”

### 5.3 Planning / prep document

Example:

> “Lysandro confronts Lysandra during the second wave.”

DungeonBuddy may find Lysandra, Lysandro, Mireward, and siege context while still saying:

```text
These existing world objects are related to the passage.

This sentence describes planned future material rather than established
campaign history.

It is useful working context, but this WorkSelectionAnchor does not by
itself make the event World evidence.
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

The agent should prefer the **smallest World change that preserves useful identity and retrieval**.

Bad:

```text
selected phrase
→ extract nouns
→ create nodes
```

Good:

```text
selected material
→ inspect existing World identity
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

**No World change**

Use when the material is descriptive texture, redundant, speculative, planned-but-not-established, or not useful as durable World memory.

Identity ambiguity must fail visibly. The agent must not fuzzy-pick a canonical object without meaningful GM review.

---

## 7. Interaction Memory and attention

This Magic Moment is a first-class consumer of the proposed DungeonBuddy Interaction Memory model.

After assessment, the thread may temporarily make these pointers salient:

```text
WorkSelectionAnchor
EvidenceAnchor?           # when one exists
matched World node refs
candidate graph object
candidate edge / claim
active work object
current Play Scene / Beat refs when relevant
```

That should support a natural follow-up:

> “What does that imply for Session 27?”

Interaction memory may resolve what **“that”** refers to.

DungeonMind must still be queried for factual World claims.

Core invariant:

```text
attention survives
facts refresh
```

If World head or source/provenance state moves, the selection and attention identity may remain useful; cached factual/admissibility results do not silently become current truth.

A new unrelated thread must not inherit a prior thread's hot referent merely because it was recently active elsewhere.

### 7.1 Persistence is evidence-gated

Do not create a durable `agent.*` APP-STATE schema merely because Interaction Memory exists conceptually.

Start with the minimum persistence needed to dogfood semantics.

Select an APP-STATE Agent family only when product correctness proves that something such as thread continuity, deliberate pins, open loops, proposals, or episode summaries must survive reload/restart/worktree boundaries.

If selected, durable Buddy interaction state belongs behind Buddy Application State/domain services — not in DungeonMind and not as ungoverned harness-owned factual memory.

---

## 8. Surface Interaction Layer fit

This target belongs to the shared Surface Interaction architecture.

The Canvas / active work domain owns:

- work identity;
- exact selection identity;
- revision / digest;
- document/work admission state.

The active Surface publishes:

- campaign/session/work focus;
- Play current-moment pointers when applicable;
- graph lens / admissibility intent;
- allowed capabilities.

The shared Agent Interaction host owns:

- invocation / thread continuity;
- contextual Graph Assessment projection;
- bounded pointer-only interaction state.

DungeonMind owns:

- World identity;
- immutable World revisions / head;
- source/evidence admissibility for World operations;
- scoped projection / retrieval;
- governed World publication.

Buddy authority ports mediate product operations into DungeonMind. Surfaces and the Agent host do not bypass them.

Plan may be the first proving surface. It must not become the permanent owner of the capability.

---

## 9. Agent-runtime / harness implication

This Magic Moment is a primary proving case for a harness-neutral `AgentRuntime`.

The right-click action should not call a Hermes-specific product contract.

Conceptually:

```text
Work selection / contextual invocation
  ↓
DungeonBuddy AgentInvocation
  ↓
ContextAssembler
  - work context
  - WorkSelectionAnchor
  - EvidenceAnchor?
  - interaction attention
  - DungeonMind World lens / revision
  ↓
AgentRuntime
  - Hermes adapter
  - experimental PydanticAI adapter
  - future runtime if justified
  ↓
DungeonBuddy-owned tool policy
  ↓
DungeonMind-native reads
Buddy proposal/review capabilities
```

The harness may own:

- model invocation;
- tool-loop mechanics;
- streaming/events;
- cancellation/retry/resume mechanics;
- harness-local conversation execution details.

The harness must not own:

- WorkSelectionAnchor identity;
- source/evidence authority;
- World scope / revision;
- interaction-memory product semantics;
- graph proposal/publication semantics;
- GM confirmation authority;
- canonical World memory.

The user-facing interaction should remain stable if the underlying runtime changes.

---

## 10. Parallel Play + Agent development contract

This Magic Moment now assumes PLAY-SURFACE and AGENT-INTERACTION may evolve in parallel after re-anchoring, provided shared seams are explicitly owned.

### 10.1 Play is a context producer

Play owns its domain state and publishes pointers upward.

When a Scene is current:

```text
Scene = dominant table workspace
Beat  = enclosing durable context
```

When no Scene is current:

```text
Beat = dominant current context
```

Agent Interaction consumes those pointers. It does not infer or persist a competing current Beat/Scene.

### 10.2 Agent is a context consumer and collaborator

Agent Interaction owns:

```text
ContextAssembler
AgentRuntime boundary
harness adapter(s)
attention / interaction-memory semantics
Graph Assessment UX
```

It consumes Play/Plan/Build context without absorbing their domain authority.

### 10.3 Shared seams are collision-gated

The highest-risk shared implementation seams are:

- Canvas / TipTap selection plumbing;
- AppChrome / AgentInteractionProvider;
- projection registry / host;
- shared API types;
- source/provenance adapters.

Parallel lanes may proceed when write leases are disjoint. A contested shared path is serialized or explicitly transferred; Git conflicts are not the coordination protocol.

---

## 11. Implementation sequence from current repository truth

The final Magic Moment remains one experience. The safest implementation ladder is staged.

### Stage A — contextual assessment on stable Buddy work identity

Preferred first proving case:

```text
Plan WorkObject + exact WorkRevision
→ highlight
→ WorkSelectionAnchor
→ AgentInvocation
→ DungeonMind-native World search / expansion / evidence reads
→ Graph Assessment
→ inspect / follow-up
```

This proves the experience without pretending Plan prose is World evidence and without coupling to in-flight D.2C4 authoring.

### Stage B — evidence-backed source selections

As SourceArtifact / worldbuilding / recap source identity becomes stable enough:

```text
WorkSelectionAnchor
+ valid DungeonMind EvidenceAnchor
→ assessment can distinguish selected work from admissible evidence
```

The same UI should work; only the evidence capability becomes richer.

### Stage C — governed graph proposal and publication

After CUTOVER settles manual-authoring/source-admission continuity:

```text
Graph Assessment
→ Buddy-owned draft proposal
→ explicit GM review
→ accepted Buddy authority port
→ governed DungeonMind publication
```

Do not implement Stage C by binding the Magic Moment to the legacy UnionSupergraph/Kernel writer that D.3 is deleting.

### Stage D — harness comparison

Run the same Stage A/B interaction through:

```text
Hermes adapter
PydanticAI adapter
```

Compare lifecycle complexity, latency, cancellation, tool policy, context ergonomics, crash/recovery behavior, testability, and how much DungeonBuddy code must bend around the harness.

The success condition is reversible harness choice, not migration for its own sake.

---

## 12. Product principles

1. **Campaign meaning first.**  
   “This looks like a new behavior of the Under-Hymn Brood” is better default prose than graph-internal terminology.

2. **Existing objects are inspectable.**  
   Matches use shared graph-reference / projection behavior. Do not make the GM retype what the agent just found.

3. **Work identity and evidence identity stay distinct.**  
   The system can know exactly what was selected without claiming that the selection is admissible World evidence.

4. **Provenance stays adjacent.**  
   When an EvidenceAnchor exists, the originating passage and source authority remain immediately inspectable.

5. **Assessment happens in place.**  
   The GM should not need to navigate to Graph Review just to ask the question.

6. **Writes remain governed.**  
   Mutation uses the accepted Buddy→DungeonMind publication seam. The initiating surface never acquires World-write authority.

7. **Return to the same work.**  
   Dismiss, inspect, or commit without losing the document, nearby position, Agent Interaction thread, or current work context.

8. **Unexpected play remains reachable.**  
   Play's contextual references are seeds, not access control. Agent-assisted/global retrieval can reach material the authored Runbook did not predict.

---

## 13. Failure and stale-state behavior

### Work changed

If the WorkRevision / digest changed after assessment:

```text
stale WorkSelectionAnchor
→ do not silently confirm
→ re-resolve / re-review
```

### Evidence authority changed

If source/provenance state changes:

```text
revalidate EvidenceAnchor through DungeonMind
→ do not assume graph revision pin preserves admissibility
```

### World head changed

If the World revision moved:

```text
assessment may remain historical
proposal must revalidate
new identity collisions / matches must surface
```

### Candidate disappeared / changed

Re-resolve through current DungeonMind identity rules. Never silently attach to another object.

### No useful World match

Do not equate:

```text
no search result
```

with:

```text
create node
```

Broaden bounded retrieval, ask a consequential clarification, recommend work/source-only retention, or propose a new node when justified.

### Agent / provider failure

The work selection and current work remain intact. Retry must not create duplicate proposals or World writes.

---

## 14. Explicit non-goals

This target does **not** require:

- autonomous background World maintenance;
- autonomous canon writes;
- automatic node creation on highlight;
- automatic ingestion of every document edit;
- treating Planning prose as occurred campaign fact;
- making Agent Interaction a factual World-memory store;
- storing corpus bodies in the Agent Interaction provider;
- a graph-write path separate from DungeonMind governed publication;
- a surface-specific duplicate graph viewer;
- a universal ontology inferred by the agent;
- Hermes-specific session identity in the product contract;
- immediate durable persistence for every Interaction Memory concept;
- all source/document families migrating to APP-STATE before the first assessment prototype;
- a final decision about the long-term agent harness.

---

## 15. Future Magic Moment dogfood

Working gate:

```text
MAGIC-SOURCE-GRAPH
Contextual work selection → World assessment → governed proposal
```

Use the existing Magic Moment result vocabulary:

```text
PASS
PASS_WITH_FRICTION
FAIL_PRODUCT
FAIL_ARCHITECTURE
BLOCKED_DEPENDENCY
```

### 15.1 Stage A proving gate — Plan assessment

Before the full three-source gate, prove:

```text
1. Open a real Plan WorkRevision.
2. Highlight real text.
3. Right click.
4. Ask DungeonBuddy to assess the World Graph.
5. Product constructs exact WorkSelectionAnchor.
6. Agent uses current work context + DungeonMind-native reads.
7. Inspect existing matches and explanation.
8. Ask a natural follow-up referring to the prior selection.
9. Advance or repin World context and prove facts refresh while attention survives.
10. Return to the same Plan position.
```

This gate does not require the selected Plan text to become World evidence or a durable World write.

### 15.2 Final source-authority probes

The full Magic Moment eventually runs at least three cases:

1. **Admitted recap** — selection has a valid EvidenceAnchor and contains plausible missing/incomplete World memory.
2. **World Building document** — selection describes an existing World object and should prefer enrichment over needless identity; actual source admission controls publication.
3. **Planning document** — selection describes planned future material and must remain visibly non-established unless separately admitted through a legitimate source/governance path.

### 15.3 Full user-visible path

A mature dogfood should be approximately:

```text
1. Open real campaign material.
2. Highlight real text.
3. Right click.
4. Ask DungeonBuddy to assess the World Graph.
5. Inspect existing matches and explanation.
6. Inspect whether the selection has World evidence authority.
7. Choose Draft graph change when appropriate.
8. Review proposed node / claim / edges and evidence.
9. Confirm through governed DungeonMind publication.
10. See the exact committed result.
11. Return to the same work context.
12. Ask a natural follow-up referring to the prior selection.
```

### 15.4 Durable identities to record

At minimum where applicable:

```text
Buddy work/source object identity
Buddy work revision / digest
WorkSelectionAnchor identity

DungeonMind source artifact identity?
DungeonMind source revision identity?
EvidenceAnchor identity?

Agent Interaction thread
DungeonMind World revision assessed
matched World object IDs

proposal / contribution identity
confirmation / publication identity
committed DungeonMind World revision
resulting object / claim / relationship identities
```

The `?` identities are optional for a selection that is valid work context but not admissible World evidence.

### 15.5 What should feel magical

> “I pointed at one piece of my campaign and DungeonBuddy understood what I was working on, understood whether that passage was merely my working material or actual World evidence, checked the living world, and helped me integrate it without making me become a graph database operator.”

### 15.6 Fail conditions

Fail when the GM must:

- copy/paste the selection into separate chat;
- manually explain which document/campaign the text came from;
- manually search Graph Review before assessment;
- manually retype object names the agent just found;
- accept a fuzzy identity guess without review;
- create a node merely because search returned nothing;
- conflate WorkSelectionAnchor with EvidenceAnchor;
- lose work/source provenance or revision identity;
- treat Planning prose as established history;
- allow old conversation prose to substitute for fresh DungeonMind retrieval;
- allow a stale evidence result after source/provenance state changes;
- leave the source and fail to return to the same work;
- confirm after material work/evidence/World state became stale;
- depend on a Hermes-specific product interaction that cannot pass through the shared Agent Interaction boundary;
- depend on the legacy Buddy graph writer that CUTOVER is retiring.

---

## 16. Architecture questions this target intentionally exposes

This target is useful because it forces several seams into one real interaction:

```text
How does a Canvas publish an exact WorkSelectionAnchor?
Which work types already have stable revision identity?
When can a WorkSelectionAnchor resolve a DungeonMind EvidenceAnchor?
How does source authority remain separate from work identity?
How does Agent Interaction receive surface context without owning it?
How does Play publish Scene-dominant + Beat-context current state?
How does Interaction Memory preserve attention without becoming World truth?
How does DungeonMind retrieval distinguish existing identity from new information?
How does the agent choose claim vs edge vs node vs no change?
How does a noncanonical assessment become a Buddy-owned proposal?
Which accepted authority port carries that proposal into DungeonMind?
How are work, evidence, and World revisions preserved through review?
How can the same invocation contract run across different agent harnesses?
How does the GM return to the exact work after the interaction?
```

These are product architecture questions, not reasons to expose implementation machinery to the GM.

---

## 17. Success test for future implementation

The target is doing its job when a GM can repeatedly do this inside real campaign material:

```text
notice something
→ point at it
→ ask whether the world already knows it
→ understand the answer
→ understand whether this passage is evidence or merely work context
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
