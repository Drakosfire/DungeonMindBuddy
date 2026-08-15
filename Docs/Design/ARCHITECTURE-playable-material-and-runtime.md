---
document_id: dmb-architecture-playable-material-and-runtime
title: Playable Material and Runtime — Architecture Authority
document_class: architecture_authority
status: active
version: 1.0
created_at: "2026-08-15"
updated_at: "2026-08-15"
workstream: CON-READY
evidence:
  - "PR #578 — Of Conks / Hempholm table-ready dogfood"
companion_authorities:
  con_ready_anchor: "../Plans/STEWARDS-ANCHOR-con-ready.md"
  con_ready_roadmap: "../Roadmaps/ROADMAP-con-ready.md"
  surface_interaction: "ARCHITECTURE-surface-interaction-layer.md"
  graph: "ARCHITECTURE-campaign-supergraph.md"
companion_designs:
  play_projection: "DESIGN-play-surface-projection.md"
  authoring_adoption: "DESIGN-playable-authoring-and-adoption.md"
---

# Playable Material and Runtime — Architecture Authority

## Status and scope

This document is the **architecture authority** for the boundary between:

- durable World knowledge;
- rich Original Source;
- durable GM-authored/adopted Playable Material;
- mutable Played / Runtime State;
- Play projections composed from those authorities.

It does not replace:

- Campaign Supergraph authority for World identity, graph claims, graph writes, or mechanics bindings;
- source/document authority for source artifacts and source provenance;
- Surface Interaction Layer authority for AppChrome, shared bars, Canvas host, or projection-host ownership;
- exact mechanics authority such as accepted immutable `StatblockRevision`;
- the CON-READY product roadmap.

This document turns the CON-READY layer model into a durable design contract after PR #578 proved concrete Playable and Play interactions.

## 1. Governing model

DungeonBuddy maintains four distinct layers of fictional/game state:

```text
ORIGINAL SOURCE
rich imported/authored material
prose, tables, images, maps, statblocks, module text

        ↓ reviewed extraction / provenance

WORLD
durable semantic world knowledge
identity, relationships, accepted assertions, mechanics bindings

        ↓ GM preparation / deliberate adoption

PLAYABLE MATERIAL
the version the GM intends to run
runbooks, scenes, beats, table framing, local interpretations,
object-attached prep, choices, consequences, encounter composition

        ↓ actual table interaction

PLAYED / RUNTIME STATE
what is currently selected, resolved, changed, spent, damaged,
noted, chosen, or completed during a run
```

A fifth concept sits **over** these layers rather than beside them:

```text
PROJECTION
a surface-specific view composed from one or more authorities
```

The Play surface is a projection consumer. It is not another truth store.

## 2. Core invariant

> **Playable Material is durable GM intent that may reference World, Source, and Mechanics without becoming any of them; Runtime State records what happens while using a particular playable version without rewriting that playable version.**

Consequences:

1. Playable Material may contradict, override, reinterpret, or narrow World/Source for a particular run without silently publishing graph canon.
2. Runtime changes such as resolved beats, chosen branches, initiative, HP, conditions, spent resources, and scratch notes do not mutate Source, World, or immutable mechanics.
3. A Play projection may combine authorities, but it must preserve the owning boundary underneath.
4. A convenience projection must not duplicate authoritative mechanics or source prose as a new truth store.

## 3. Authority table

| Information | Owning authority | Playable may do | Runtime may do |
|---|---|---|---|
| Original prose / quoted module text | SOURCE | reference / quote with provenance | read only |
| World identity | WORLD | reference object | never redefine identity silently |
| Accepted world relationship | WORLD | reference; add run-local interpretation separately | read only |
| Run-local NPC motivation/secret | PLAYABLE | own | note consequences of use |
| Scene / Beat organization | PLAYABLE | own | point at current/resolved elements |
| Prepared choice options | PLAYABLE | own | record selected option |
| Prepared consequence | PLAYABLE | own | record whether/when it occurred |
| Statblock mechanics | MECHANICS | reference exact revision | instantiate mutable combatant state |
| Encounter composition | PLAYABLE | own expected composition | instantiate/adjust live combat |
| Current HP / initiative / conditions | RUNTIME | never own | own |
| Scene scratch note made during play | RUNTIME | may later be deliberately adopted | own |
| Source asset / map image | SOURCE / ASSET | reference | read only |
| Map pin annotation | ASSET ANNOTATION | reference / curate visibility | current selection only |
| Hermes proposed prep text | PROPOSAL, not truth | adopt only after GM approval | n/a |

## 4. Durable Playable Material

### 4.1 Playable Artifact

A **Playable Artifact** is a durable versioned work object containing material the GM intends to prepare or run.

A workspace document is a valid first implementation and remains a first-class product object. This architecture does **not** require a new database merely because Playable Material gained stronger semantics.

A Playable Artifact must have:

- stable work-object identity;
- campaign/world scope sufficient to resolve references;
- durable revision identity or equivalent compare-and-swap boundary;
- readable/editable content;
- stable identities for semantic elements that Runtime State may reference;
- typed references to external authorities instead of copied truth where possible.

Possible roles include:

- session runbook;
- scene packet;
- NPC prep notes;
- shop sheet;
- encounter plan;
- roll-table prep;
- object-attached playable interpretation.

`role` is not a closed ontology.

### 4.2 Stable element identity

Runtime State cannot safely point at mutable headings or display text.

Therefore:

> **Any Playable element referenced by Runtime State or another durable object must have stable identity independent of its current title/text.**

This applies at minimum to:

- Scene;
- Beat;
- authored Choice;
- Choice Option when persisted runtime selection depends on it;
- any block that can be replaced/addressed by an approved agent proposal.

The exact Markdown/Tiptap serialization of those IDs is an implementation decision. The identity invariant is not.

### 4.3 Playable blocks

Playable Material may contain semantic blocks such as:

- At the table;
- Read aloud;
- GM note;
- Rules now;
- Warning;
- Consequence;
- ordinary prose;
- typed reference;
- contextual tool/action reference.

These are **presentation/use semantics**, not World ontology.

A block may carry provenance when it was adopted or derived from Source/World. GM-authored material may have no source provenance beyond its own playable revision.

### 4.4 Object-attached Playable Material

A GM may attach playable interpretation to a durable World object without promoting it into World truth.

Examples:

```text
NPC Hesta
  WORLD:
    halfling apothecary
    owns Hesta's Apothecary

  PLAYABLE:
    At the table: hurried, keeps glancing toward the cellar
    Attitude: warm to the party, terrified of the mayor
    Offer: can identify the restorative tincture
```

The object identity remains World-owned. The attached interpretation is Playable-owned.

This is the foundation for Play Object Sheets without requiring universal NPC/location/shop schemas.

## 5. Runbook, Scene, and Beat

PR #578 provides sufficient dogfood evidence to make **Runbook → Scene → Beat** first-class Playable structure.

This is a Playable organization model, not an Adventure ontology for the World Graph.

### 5.1 Runbook

A Runbook is a Playable Artifact role that arranges material into a table-running sequence.

It may contain:

- ordered Scenes;
- fallback or optional Scenes;
- choices/transitions;
- object references;
- contextual tools;
- non-scene reference material where useful.

The Runbook is the table-facing projection of prep, not the prep database.

### 5.2 Scene

A Scene is an ordered, stable Playable grouping that gives the GM a current table context.

Useful Scene semantics include:

- stable ID;
- title;
- order;
- intent;
- prepared clocks/pressure definitions;
- scene-level playable blocks;
- typed references;
- Beats;
- authored choices/transitions.

A Scene does not own live clock values. Prepared clock definition is Playable; current clock value/progress is Runtime.

### 5.3 Beat

A Beat is the smallest normal unit the GM deliberately focuses/resolves while running the Runbook.

Useful Beat semantics include:

- stable ID;
- title;
- kind;
- summary;
- At the table;
- Read aloud;
- GM note;
- Rules now;
- warnings;
- consequences;
- typed references;
- contextual Play actions.

The initially warranted Beat kinds are:

```text
spine
optional
interrupt
```

This is a small product vocabulary, not a closed universal event taxonomy.

### 5.4 Consequences

`consequences` is the canonical Beat outcome concept.

A consequence answers:

> **What becomes true for this run if a particular table condition/action resolves this way?**

A consequence may optionally express:

- a trigger/condition such as success, failure, waiting, choice, always, or a referenced authored condition;
- a presentation/category hint such as reward, cost, state change, relationship, clock, access, information, or other;
- table-facing text;
- references to affected objects/mechanics/playable elements.

These hints must remain extensible. They are not a new World ontology.

Examples:

```text
wait → tree advances one growth step
success → Morwin pays 20 gp
failure → character is buried
choice:fire → aftermath scene becomes Firefighting
success → Nar becomes willing to help
search → recover 100 gp of precious metal leaves
```

**Treasure/reward is therefore a consequence, not a root Beat field.**

Likewise, `ifTheyWait`, `ifTheySucceed`, and `ifTheyFail` are useful UI labels over consequence triggers, not required parallel top-level storage axes.

## 6. Choices and branching

PR #578 proves branch-aware running is useful, but its branch enums are adventure-specific.

Permanent Playable Material defines choices generically:

```text
Choice
  stable choiceId
  prompt / meaning
  options[]
    stable optionId
    label
    optional transition / consequence references
```

Runtime State records:

```text
choiceId → selected optionId
```

Runtime does not know that an option means `celebration`, `fire`, `guild`, or any other adventure-specific concept except through the authored Playable Material.

## 7. Runtime State

A **Run** binds mutable table state to one exact or explicitly migrated Playable revision.

Minimum durable runtime concepts:

```text
RunState
  runId
  playableArtifactId
  playableRevisionId
  currentSceneId?
  currentBeatId?
  resolvedBeatIds[]
  selections: { choiceId: optionId }
  notesByElementId: { playableElementId: text }
  linkedRuntimeObjects[]   # e.g. combat encounter/run handles, later as needed
  updatedAt
```

This is conceptual architecture, not a frozen wire schema.

### 7.1 Runtime invariants

- Run state references stable Playable IDs.
- Run state never invents new Playable structure.
- Run state never writes World Graph canon.
- Combat runtime remains owned by Combat.
- A Play run may link to Combat runtime rather than absorbing combat fields.
- Reload/restart must preserve run state needed to continue the table.
- If the Playable revision changes, migration/rebase must be explicit when referenced IDs are removed or semantically replaced.

## 8. Projection architecture

Play consumes authorities through projections.

### 8.1 Play Object Sheet

A Play Object Sheet is not stored as a duplicate object.

It composes:

```text
WORLD
identity, durable relationships, concise accepted facts

SOURCE
rich exact source detail / provenance

PLAYABLE
GM-adopted table interpretation and relevant-now curation

MECHANICS
exact mechanics bindings where applicable

RUNTIME
small current-run status only when useful

        ↓

PLAY OBJECT SHEET
```

The projection should lead with table usefulness and place graph/provenance internals in Advanced/supporting detail.

### 8.2 Threat projection

Threat projection uses exact mechanics when available.

```text
Threat
  ↓ accepted exact mechanics binding
StatblockRevision
  ↓ Play projection
Threat Sheet
  ↓ explicit action
Add to Combat
```

Playable notes may describe tactics or encounter intent, but must not silently replace exact mechanics authority.

### 8.3 Maps/media

Maps and media should be composed from reusable source/asset records and annotations.

Conceptually:

```text
Asset
  identity
  source provenance
  media metadata

AssetAnnotation
  assetId
  normalized position / region
  target reference
  label
```

Play may render these as clickable map overlays. Build and Plan may reuse the same underlying data.

## 9. Agentic authoring boundary

Hermes may help create Playable Material, but proposal is not adoption.

The durable flow is:

```text
ground in admitted context
→ propose typed Playable mutation
→ show preview + provenance
→ GM explicitly approves
→ apply to admitted Playable work object
→ ordinary Save / revision commit
```

Requirements:

- explicit target work object;
- stale-revision / digest protection;
- no apply over conflicting unsaved edits;
- stable target element identity when replacing/editing existing content;
- provenance retained when proposal is grounded in Source/World;
- no automatic World Graph publication;
- no hidden durable write on proposal generation.

## 10. From Playable to World, and Runtime to Playable

Upward promotion is always deliberate.

### 10.1 Playable → World

A run-local decision may later deserve canonical promotion.

That is a separate reviewed operation through World/Graph authority.

Example:

```text
PLAYABLE:
Hesta secretly treated the mayor's daughter.

later operator decision:
"Make this true in the durable world."

→ explicit graph-authoring/review path
```

### 10.2 Runtime → Playable

A table outcome or scratch note may later be useful prep.

That is also deliberate adoption:

```text
RUNTIME:
Torbin fled west during play.

after session:
GM chooses "keep this in next prep"

→ Playable proposal/adoption
```

Neither direction is automatic.

## 11. Persistence and revision rules

1. Playable Material is durable across reload/restart.
2. Runtime State is durable across reload/restart when the GM depends on it.
3. Every persisted Run binds to an identifiable Playable version.
4. Stable referenced element IDs survive ordinary text/title edits.
5. Deleting/replacing a referenced element must not silently retarget runtime state.
6. Exact mechanics revisions remain immutable and externally referenced.
7. Source provenance remains source-owned and integrity-checked.
8. Projection caches, if any, are reconstructable and never become authority.

## 12. Surface Interaction Layer boundary

`ARCHITECTURE-surface-interaction-layer.md` remains authority for shared AppChrome and projection hosts.

This architecture adds domain meaning, not new chrome ownership.

Play:

- publishes Play capabilities upward;
- uses the shared Projection host;
- may select a Playable Canvas/work object;
- may register Beat/Object/Threat projections;
- does not own AppChrome bars;
- does not absorb Canvas document authority.

## 13. Migration from PR #578

Keep:

- Play as dedicated surface;
- Scene/Beat interaction;
- Play Object Sheet semantics;
- consequences;
- persisted run state;
- Threat → Add to Combat;
- typed Hermes proposal/approval;
- map/media projection concept;
- real-object eval methodology.

Replace:

```text
ofConksPlayObjectBridge
        ↓
generic projection over World + Source + Playable

ofConksHempholmBeats
        ↓
durable Playable Runbook / Scene / Beat content

ofConksThreatPlayBridge
        ↓
exact accepted mechanics binding

Of Conks branch enums
        ↓
generic authored choices + runtime selections

ofConksNodeMedia / ofConksMapOverlays
        ↓
asset + annotation authority

playPrepHost / MirewardPrep globals
        ↓
native Play capabilities over time
```

## 14. Explicit non-goals

This architecture does **not** require:

- a universal Adventure object in the World Graph;
- automatic extraction of every Scene/Beat from source;
- a bespoke NPC ontology;
- a bespoke Shop ontology;
- a new database before workspace documents prove insufficient;
- copying source prose into Playable storage merely so Play can render it;
- copying statblock mechanics into Runbook/Beat fields;
- making every Runtime event durable campaign canon;
- making every playable consequence a typed graph assertion;
- Play-owned map/media truth;
- arbitrary Hermes filesystem access;
- direct Hermes writes without explicit operator adoption.

## 15. Architecture acceptance tests

A future implementation conforming to this authority should be able to prove:

1. A real Runbook with stable Scenes/Beats survives save/reload.
2. Renaming a Beat does not orphan run-state references to it.
3. A Beat can express a reward as a consequence without a treasure-specific schema.
4. A branch choice is authored generically and runtime records only choice/option IDs.
5. A Play Object Sheet renders useful NPC/location/item information without a campaign-specific code dictionary.
6. A run-local NPC interpretation remains usable in Play without becoming World Graph truth.
7. A Threat opens exact mechanics and can be explicitly added to Combat without a campaign-specific statblock bridge.
8. Hermes can propose a GM Note/Rules/Warning/Read Aloud against the admitted Playable work object; stale/dirty state prevents unsafe application.
9. Runtime notes/resolved Beats persist across restart.
10. Source, World, Playable, Mechanics, and Runtime provenance/authority remain distinguishable under the projection.
