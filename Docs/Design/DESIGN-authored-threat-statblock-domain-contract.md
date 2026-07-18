# Design: Authored Threat and Statblock Domain Contract

**Status:** ACTIVE DESIGN DIRECTION  
**Created:** 2026-07-17  
**Repositories:** `Drakosfire/DungeonMindBuddy`, `Drakosfire/DungeonMindServer`  
**DungeonBuddy anchor checked:** `dc4aaf2b242c372f759a1f20b8f8d9602f0ab9e0`  
**DungeonMindServer anchor checked:** `b3cae86b9e0dbc55fc26412be19f9e0445c9b9d7`

## 1. Decision summary

DungeonBuddy needs a durable object representing a threat that is intentionally created through the product, not extracted from an existing artifact.

The initial workflow is:

```text
brainstorm a threat with DungeonBuddy
→ create a ThreatDraft
→ send its description and generation intent to DungeonMind
→ receive a typed GeneratedStatblockCandidate
→ project the candidate for human judgment
→ edit, regenerate, accept, or reject
→ persist an immutable StatblockRevision
→ author or update the Threat graph node
→ bind the Threat to the accepted statblock revision
→ project it into Plan, scenes, Play, and combat
```

The central design decision is:

```text
The Threat is the DungeonBuddy world object.
The statblock is a reusable, revisioned mechanical attachment.
The generated package is a transient cross-service candidate, not the root object.
```

This avoids making one object simultaneously own world identity, mechanics, generation lifecycle, images, graph state, presentation, planning placement, and mutable combat state.

## 2. Core invariant

```text
One accepted statblock revision represents one immutable mechanics truth.

Every summary, full statblock, Plan placement, scene placement, Play projection,
semantic embedding, and combatant created from it remains traceable to that exact
revision.

Threat identity, graph relationships, images, review state, presentation, placement,
and runtime combat state may change without mutating that revision.
```

A second invariant governs the graph boundary:

```text
A generated statblock does not silently become graph truth.
DungeonBuddy authors a Threat through its governed write path and explicitly binds
that Threat to an accepted statblock revision.
```

## 3. Vocabulary

### 3.1 `ThreatDraft`

A mutable DungeonBuddy authoring object created during brainstorming.

It answers:

> What thing is the GM currently inventing, before it is durable graph truth?

Candidate fields:

```text
draft_id
name
description
threat_kind
intended_role
tags
image_refs
generation_intent
statblock_candidate_refs
authorship provenance
workflow timestamps
```

A `ThreatDraft` is not an extraction candidate and does not require source-artifact evidence. Its provenance is an authored contribution: human-directed work created through DungeonBuddy.

It may exist before a statblock is generated. Generation failure must not erase the authored concept.

### 3.2 `Threat`

The durable DungeonBuddy graph object.

It answers:

> What creature, hazard, force, or adversarial world object exists in this campaign?

`Threat` is the durable graph kind. `Authored` is provenance, not a permanent subtype. This preserves the possibility that a future threat may also be discovered through ingest while keeping the initial creation path explicit.

Candidate concerns:

```text
threat_id
name
canonical description
threat_kind
tags
image bindings
graph relationships
statblock bindings
creation and revision provenance
```

The graph node stores world identity and relationships. It does not embed the full statblock payload or mutable combat state.

### 3.3 `Statblock`

The stable logical identity for a reusable mechanics object.

It answers:

> Which continuing mechanical design do these revisions belong to?

A statblock is not identified by its display name. Similar names do not merge. Renaming does not create a new logical statblock unless the operator intentionally creates a separate variant.

### 3.4 `StatblockRevision`

One immutable accepted mechanics revision.

It answers:

> Exactly which rules and mechanics were accepted at this point in history?

A revision contains:

```text
statblock_id
revision_id
ruleset declaration
strictly typed statblock definition
revision lineage
authorship and generation provenance
validation receipt
content digest
created timestamp
```

Changing mechanics creates a new revision. Accepted revisions are never overwritten in place.

### 3.5 `GeneratedStatblockCandidate`

The typed object returned by DungeonMind for DungeonBuddy review.

It answers:

> What mechanical proposal did DungeonMind produce from this request?

A candidate may include the strict statblock definition, producer provenance, validation observations, and optional derived projections. It is not yet accepted mechanics truth and does not own DungeonBuddy review or graph lifecycle.

### 3.6 `ThreatStatblockBinding`

The typed relationship between a Threat and reusable statblock mechanics.

It answers:

> Which statblock does this threat use, and in what role?

Candidate fields:

```text
binding_id
threat_id
statblock_id
selected_revision_id
role
revision_resolution_policy
phase or variant metadata
binding provenance
```

Possible roles:

```text
primary
alternate
phase
encounter_variant
template
```

The relationship is many-to-many:

```text
one Threat → several statblocks
one statblock → several Threats
```

Examples include a boss with several reusable forms, or many individual guard nodes sharing one generic guard statblock.

### 3.7 `StatblockProjection`

A derived view over a Threat, a statblock revision, or both.

Projection kinds include:

```text
identity chip
summary card
full statblock
review editor
Plan reference
scene reference
Play reference
combat drilldown
print view
agent context
semantic embedding document
```

A projection identifies its source revision and renderer or derivation version. Projection changes do not create mechanics revisions.

### 3.8 `CombatantSeed`

The deterministic adapter output used to add an accepted revision to combat.

It contains the exact statblock reference plus the operational values required by the current combat tracker.

### 3.9 `CombatantInstance`

Mutable encounter state created from a `CombatantSeed`.

It owns current HP, temporary HP, initiative, conditions, resources, position, turn state, and encounter-local notes or overrides. None of this state is written back into the statblock revision.

## 4. Ownership model

| Concern | DungeonMind | Cross-service candidate | DungeonBuddy | Combat runtime |
|---|---:|---:|---:|---:|
| D&D 5e statblock schema | Owns | Declares version | Consumes and validates | Reads |
| Generated mechanics | Produces | Carries | Reviews and may edit | Reads accepted revision |
| Mechanical revision creation | Persists and validates through API | Carries proposed definition | Initiates and adjudicates | No |
| Threat concept and identity | No | Receives snapshot as input provenance | Owns | Reads |
| Graph node and relationships | No | No | Owns | Reads locators only |
| Review decision | No | No | Owns | Reads accepted result |
| CDN image storage | Owns service/storage path | Carries references when generated | Selects and binds images | Displays |
| Projection styling | No | May provide convenience Markdown | Owns semantic renderers and design system | Displays |
| Plan and scene placement | No | No | Owns | Reads |
| Preferred library revision | No | No | Owns selection policy | No |
| Current HP and conditions | No | No | No | Owns |

No mutable field is jointly owned by both services.

## 5. Authoring and review lifecycle

### 5.1 Brainstorming

DungeonBuddy and the GM develop the concept as a `ThreatDraft`. The draft description is the original authored content from which mechanics may be generated.

The draft may include generation-facing intent such as:

```text
table role
challenge expectation
tone
complexity
party context
terrain pressure
must-have behavior
must-not-have behavior
```

These are authoring inputs. They are not all permanent properties of the threat or statblock.

### 5.2 Generation

DungeonBuddy backend sends a typed request to DungeonMind. The browser does not call privileged DungeonMind endpoints directly and never receives producer credentials.

The request should carry:

```text
request_id
ThreatDraft description snapshot
generation mode
target ruleset
target CR or challenge intent
role and behavior constraints
optional source statblock revision
optional encounter or terrain context
source and graph locators when relevant
```

DungeonMind returns one typed candidate or one typed failure.

### 5.3 Preview

DungeonBuddy composes the review projection from:

```text
ThreatDraft identity and description
+ GeneratedStatblockCandidate definition
+ image references
+ producer warnings and validation
+ DungeonBuddy review state and actions
```

The preview is not rendered from Markdown as the canonical source. Markdown may remain a convenience projection, but the structured definition is authoritative.

### 5.4 Editing and regeneration

The GM may:

```text
edit the threat description
edit proposed mechanics
regenerate from revised intent
request a variant
select or change images
accept
reject
```

Changing the threat description updates the `ThreatDraft`. It does not automatically rewrite an accepted statblock.

Changing proposed mechanics updates or replaces the candidate. Once accepted, later mechanical edits produce a new immutable revision.

### 5.5 Acceptance

Acceptance performs explicit, separately truthful operations:

```text
persist accepted StatblockRevision
record DungeonBuddy review decision
create or update the durable Threat node
create or update ThreatStatblockBinding
select preferred library revision when requested
```

A partial failure must not be reported as complete success. The implementation design must declare commit ordering and reconciliation behavior before this workflow is built.

## 6. Threat description versus statblock flavor

The current DungeonMind `StatBlockDetails.description` overlaps with the new Threat root. The new contract must separate three meanings:

```text
Threat.description
  Campaign-world identity, appearance, history, role, and authored concept.

StatblockRevision.flavor_text
  Reusable mechanics-adjacent text that belongs with the sheet wherever it travels.

GenerationProvenance.source_description_snapshot
  The exact ThreatDraft description used to generate this revision.
```

This separation allows one generic statblock to serve several distinct threats without copying one threat's campaign history into all of them.

## 7. Statblock definition direction

The current DungeonMindServer model at
`statblockgenerator/models/statblock_models.py` is the foundation for the first contract. It already provides a substantial typed D&D 5e definition including:

```text
size, type, subtype, alignment
armor class, hit points, hit dice
walk, fly, swim, climb, and burrow movement
ability scores, saving throws, and skills
damage vulnerabilities, resistances, and immunities
condition immunities
senses and languages
challenge rating, XP, and proficiency bonus
actions, bonus actions, reactions, and special abilities
spellcasting
legendary actions
lair actions
description and image-generation prompt
```

The design should evolve this model rather than replace it with a vague universal TTRPG schema or copy it independently into DungeonBuddy.

### 7.1 Required cleanup

The portable mechanics definition should not own:

```text
DungeonMind project_id
mutable last_modified
DungeonBuddy tags or graph lifecycle
review status
rendered Markdown
combat state
surface styling
```

Those concerns currently coexist in predecessor objects because the generator was also a project workflow. They should be mapped to their proper owners.

### 7.2 Typed flexibility

Flexibility must come from explicit known rule shapes, not an ungoverned `extensions: object` bag.

A mythic phase, for example, is a typed feature of the creature with a trigger, timing, effects, and phase transition. It should not arrive as an opaque extension that DungeonBuddy silently ignores.

The detailed schema audit should evaluate a shared feature hierarchy such as:

```text
StatblockFeature
  id
  name
  category
  activation or trigger
  usage and recharge
  targeting
  checks or saving throws
  effects
  rules_text
```

Feature categories may include:

```text
trait
action
bonus_action
reaction
legendary_action
lair_action
regional_effect
spellcasting_feature
phase_transition
```

Effects should be typed where the system needs deterministic interaction, while retaining explicit `rules_text` for human-adjudicated mechanics. A typed human-adjudicated effect is preferable to arbitrary JSON or silently discarded behavior.

The exact hierarchy is not locked by this document. It must be derived from a field-by-field audit of the current schema and representative fixtures, including simple, spellcasting, legendary, lair, unusual movement, warning-bearing, and multi-phase creatures.

### 7.3 Internal phases versus separate statblocks

Use one statblock revision with internal phases when:

```text
the creature changes state during one encounter;
the transition has explicit triggers;
and the forms are not independently selected or reused.
```

Use separate statblocks when:

```text
the forms are independently reusable;
they can be placed or selected separately;
or they represent deliberate encounter variants rather than runtime phase state.
```

## 8. Identity and revision behavior

The design distinguishes:

| Identity | Meaning |
|---|---|
| `threat_id` | Stable DungeonBuddy world object |
| `statblock_id` | Stable reusable mechanics identity |
| `revision_id` | One immutable mechanics revision |
| `candidate_id` | One generated or edited proposal awaiting judgment |
| `binding_id` | One Threat-to-statblock relationship |
| `combatant_instance_id` | One mutable runtime instance |

Required behavior:

```text
same candidate delivered twice
  → idempotent review result or explicit duplicate outcome

same accepted revision referenced twice
  → same mechanics identity, not copied mechanics

changed mechanics
  → same statblock_id, new revision_id, explicit lineage

same display name
  → no identity merge

local DungeonBuddy mechanical edit
  → new candidate, validation, then new accepted revision
```

### 8.1 Preferred versus pinned revisions

Library and identity views may resolve the preferred accepted revision.

Plans, scenes, prepared encounters, exports, and combatants pin an exact revision.

```text
Threat library view
  → preferred accepted revision

Plan or scene placement
  → statblock_id + revision_id

CombatantInstance
  → statblock_id + revision_id, always pinned
```

When a newer revision exists, DungeonBuddy should offer an explicit compare-and-upgrade action. It must not silently rewrite prepared content or active combatants.

## 9. Images

Images are CDN-hosted assets managed through DungeonMindServer's existing image architecture. DungeonBuddy stores typed references rather than image bytes.

Candidate image reference:

```json
{
  "image_id": "img_...",
  "url": "https://cdn.example/...",
  "role": "portrait",
  "alt_text": "...",
  "focal_point": {"x": 0.5, "y": 0.3},
  "generation": {
    "prompt": "...",
    "model": "..."
  }
}
```

Useful roles include:

```text
portrait
token
full_body
encounter_art
thumbnail
alternate
```

Creature-identity art usually binds to the Threat. Art depicting a specific mechanical form or phase may bind to a `ThreatStatblockBinding` or statblock phase.

Changing a selected image, CDN URL, crop, focal point, or alt text does not create a mechanics revision.

The mechanics digest must not change merely because media changed.

## 10. Projection model

The object must support several projections without duplicating mechanics truth.

### 10.1 Summary projection

A summary card composes three distinct sources:

```text
identity summary
  Threat name, image, type, and authored description excerpt

mechanical digest
  deterministic AC, HP, speed, CR, major defenses, and key actions

tactical summary
  accepted explanation of how the creature behaves in play
```

The compact projection links by stable Threat and statblock identities to a larger projection. It never resolves by display name.

### 10.2 Full statblock projection

The full view renders the exact accepted revision with semantic sections and DungeonBuddy styling. Styling belongs to DungeonBuddy's projection registry and design-token system, not to arbitrary CSS or HTML supplied by the package.

### 10.3 Review projection

The workbench combines:

```text
ThreatDraft or Threat context
candidate or accepted revision
validation and warnings
revision comparison
mechanical editing
image selection
authoring and binding actions
```

### 10.4 Plan, scene, and Play projections

These surfaces store typed references or placements, not copied statblock JSON.

A placement may own contextual state such as:

```text
quantity
encounter role
arrival trigger
visibility
scene notes
encounter-local overrides
```

That state is not part of the generic threat or statblock.

### 10.5 Semantic embeddings

Embeddings are derived index artifacts keyed by exact source identity and derivation version.

Potential embedding documents include:

```text
threat identity and lore
mechanics and defenses
tactical role and behavior
full reference representation
campaign-context notes
```

Each embedding records at least:

```text
threat_id or revision_id
projection kind
embedding model and version
normalization or rendering version
```

Changing embedding models or projection text does not create a statblock revision.

## 11. DungeonMindServer storage evolution

DungeonMindServer already has useful foundations:

```text
strict Pydantic statblock model
structured-output generation
v2 internal-key protected draft endpoints
Firestore project, session, and creature collections
Cloudflare CDN image references
validation and CR calculation paths
```

The current durable project path is mutable: saving a project replaces the statblock stored in the project document. Manual creature save creates a new creature identifier but does not establish logical statblock identity or immutable revision lineage.

DungeonBuddy should therefore not point graph bindings directly at the current mutable project document shape.

The durable storage API needs a narrow revision contract:

```text
create logical statblock
append immutable revision
read exact revision
read preferred or current revision
list revisions
record supersession or variant lineage
validate before persistence
```

The stable locator exposed to DungeonBuddy should resemble:

```json
{
  "provider": "dungeonmind",
  "statblock_id": "statblock_...",
  "revision_id": "sbrev_...",
  "schema": "dungeonmind.dnd5e-statblock",
  "schema_version": "..."
}
```

The existing account model remains relevant. Initial DungeonBuddy integration should use backend-to-backend service authentication and a declared service-owned or operator-owned namespace. Temporary development shortcuts must not become an unauthenticated ownership rule in the contract.

## 12. Current v2 envelope decomposition

DungeonMindServer currently returns a v2 `StatBlockDraft` containing:

```text
structured statblock
rendered Markdown
combat defaults
warnings
provenance
review status
live_draft lifecycle
```

The new design maps those fields as follows:

| Current field | Future ownership |
|---|---|
| `statblock` | Canonical candidate definition; accepted as a `StatblockRevision` |
| `markdown` | Optional derived projection; not canonical mechanics |
| `combat_defaults` | Deterministic `CombatantSeed` projection, verified or recomputed by DungeonBuddy |
| `warnings` | Producer validation observations carried into DungeonBuddy review |
| `provenance` | Typed generation provenance retained with candidate and revision |
| `review_status` | DungeonBuddy-owned review lifecycle |
| `lifecycle_state` | DungeonBuddy workflow state, not portable mechanics |

The v2 endpoint remains useful predecessor evidence and an incremental adapter seam. It should not be copied wholesale into the durable domain model.

## 13. Combat tracker integration

The existing combat tracker prototype is sufficiently mature to receive the first integration. It should be adapted before it is rebuilt as a Play surface.

The current prototype already proves:

```text
initiative rows
AC, HP, notes, and defeated state
current and next turn behavior
circular initiative ordering
statblock drilldown
local persistence
import and export
generated draft acceptance into combat
```

The first upgrade replaces transitional statblock paths and pending Markdown with an exact revision reference plus a small operational snapshot.

Candidate shape:

```ts
interface CombatEntity {
  id: string;
  name: string;
  team: "pc" | "ally" | "enemy" | "neutral";

  initiative: number | null;
  currentHp: number | null;
  maxHp: number | null;
  tempHp: number | null;
  conditions: CombatCondition[];
  notes: string;

  statblockRef: {
    provider: "dungeonmind";
    statblockId: string;
    revisionId: string;
  };

  statblockSnapshot: {
    name: string;
    armorClass: number;
    maxHitPoints: number;
    initiativeBonus: number;
    speedSummary: string;
  };
}
```

The exact reference powers full projection and drilldown. The snapshot preserves stable operational values during reload and avoids silent changes if the preferred library revision advances.

The first adapter is:

```text
accepted StatblockRevision
→ deterministic CombatantSeed
→ existing tracker inserts CombatEntity
→ combat row opens full statblock through statblockRef
```

The later Play surface should consume these same contracts rather than introduce a second combat hydration path.

## 14. Change classification

Use this rule to decide which object changes:

```text
Does the change alter how the generic creature is adjudicated anywhere?
  → create a new StatblockRevision.

Does it alter what this particular world threat is?
  → revise the Threat or its authored contribution.

Does it alter how the object is displayed?
  → update projection or media state.

Does it alter how the threat is used in one plan, scene, or encounter?
  → update placement state.

Does it alter what is happening during active play?
  → update CombatantInstance state.
```

Examples of mechanics changes:

```text
AC, HP, speed, ability score, attack bonus, damage, save DC
new or changed trait, action, reaction, phase, immunity, resistance, or recharge
```

Examples that do not create mechanics revisions:

```text
new portrait or token
changed card styling
campaign relationship changes
adding three copies to a scene
current HP loss or conditions
```

## 15. Schema-home recommendation

Use split ownership:

```text
DungeonMind owns and publishes the versioned D&D 5e statblock definition schema.
DungeonBuddy owns Threat, authoring, review, graph binding, placement, and combat lifecycle.
The cross-service envelope carries the DungeonMind schema identity and provenance.
DungeonBuddy generates or validates local types from the published schema rather than
maintaining a permissive handwritten mirror.
```

This preserves one authority for mechanics without coupling DungeonMind to DungeonBuddy's graph and surface lifecycle.

## 16. Initial implementation capability ladder

This document is design direction, not authorization for a monolithic implementation.

### Capability A — Statblock definition audit and vNext contract

Produce a field-by-field mapping from current `StatBlockDetails` to the versioned D&D 5e definition, including representative fixtures and typed feature decisions.

No HTTP, graph, UI, storage migration, or combat work.

### Capability B — Immutable DungeonMind statblock revision store

Add logical statblock identity, immutable revisions, exact-revision reads, lineage, and service-authenticated persistence.

No DungeonBuddy graph or UI work.

### Capability C — DungeonBuddy ThreatDraft and generation adapter

Create the authored draft object and call the existing DungeonMind v2 generation seam, mapping the response into a typed candidate.

No graph publication or durable revision acceptance yet.

### Capability D — Statblock review and projection contract

Project a candidate into compact and full review views with typed edits and image references.

No combat insertion or graph write.

### Capability E — Accept revision and bind Threat

Persist an accepted revision, author or update the Threat through the governed graph path, and create the explicit binding with truthful partial-failure handling.

### Capability F — Existing combat tracker adapter

Convert an accepted revision into a revision-pinned `CombatantSeed` and insert it into the existing tracker while preserving reload and export.

No Play surface rebuild.

### Capability G — Shared Plan, scene, and Play projections

Project exact revision-pinned references through the existing shared projection infrastructure.

### Capability H — Revision comparison and upgrade workflow

Expose newer-revision comparison and explicit placement upgrade without automatic rebinding.

## 17. Required design follow-up

Before implementation handoffs are dispatched, the next design pass must inspect and capture:

```text
the complete current StatBlockDetails schema and all related nested models
real persisted Firestore project, session, and creature shapes
existing frontend statblock editor assumptions
image-management locator and deletion semantics
current DungeonBuddy v2 client mirror
current statblock workbench and draft store
current combat tracker implementation and persisted fixture shape
the governed authored-contribution path for creating a Threat node
```

It must demonstrate the definition with at least:

```text
a simple creature
a spellcaster
a legendary and lair creature
a creature with nonstandard movement
a warning-bearing generated candidate
a revised statblock
a multi-phase or mythic creature
one generic statblock shared by several Threat nodes
```

## 18. Non-goals

This design does not authorize:

```text
a universal TTRPG statblock ontology
arbitrary extension objects
copying the DungeonMind Pydantic schema into DungeonBuddy by hand
making Markdown canonical mechanics
storing full statblock JSON inside graph nodes
putting current HP or conditions into the statblock revision
automatically publishing generated content as graph truth
silently rebinding plans or combats to the latest revision
rewriting the combat tracker before adapting it
bypassing backend service authentication in the permanent contract
shipping the entire workflow in one PR
```

## 19. Final architecture

```text
ThreatDraft
  mutable DungeonBuddy-authored concept
        |
        | generate
        v
GeneratedStatblockCandidate
  typed DungeonMind proposal awaiting judgment
        |
        | review, edit, accept
        v
StatblockRevision
  immutable accepted mechanics in DungeonMind storage
        |
        | explicit binding
        v
Threat
  durable DungeonBuddy graph object
        |
        +--> summary and full projections
        +--> Plan and scene placements pinned to revision
        +--> semantic embedding projections
        +--> CombatantSeed
                  |
                  v
             CombatantInstance
             mutable runtime state
```

The durable product principle is:

```text
one authored world object
one reusable logical statblock
many immutable mechanics revisions
explicit Threat-to-statblock bindings
many deterministic projections
many revision-pinned combatant instances
```
