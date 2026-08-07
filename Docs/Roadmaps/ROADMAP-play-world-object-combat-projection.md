# Roadmap — Play Surface + World-Object Combat Projection

**Status:** PRE-IMPLEMENTATION DESIGN ROADMAP  
**Date:** 2026-08-07  
**Scope:** DungeonMind kernel cutover, first-class Player Character and NPC world objects, shared world-object projection seams, Play surface, and Combat Tracker runtime activation  
**Primary product target:** live-play dogfood through `/play` with Combat Tracker as the first Play workspace  
**Kernel dependency:** the durable graph kernel is expected to cut over to the `DungeonMind` repository; this roadmap freezes product/domain seams, not the final kernel file layout  
**Companion PR series:** [`../Plans/PR-TRACKER-play-world-object-combat-projection.md`](../Plans/PR-TRACKER-play-world-object-combat-projection.md)  
**Parent architecture decisions:**
- [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)
- [`../Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)
- [`../Design/DESIGN-authored-threat-statblock-domain-contract.md`](../Design/DESIGN-authored-threat-statblock-domain-contract.md)
- [`ROADMAP-cross-surface-statblock-demo.md`](ROADMAP-cross-surface-statblock-demo.md)
- [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)

This roadmap coordinates a new proving loop. It does not replace the Campaign Supergraph / DungeonMind kernel authority, the accepted Threat + Statblock lifecycle, or the Surface Interaction Layer.

---

## 1. Roadmap goal

Make **Play** a real DungeonBuddy surface and make **Combat Tracker** its first operational workspace.

The first live proof should demonstrate that one durable world object can be projected across surfaces and then activated as mutable runtime state without copying canonical mechanics or falling back to static Markdown.

The intended loop is:

```text
World Graph object
→ shared object projection
→ exact mechanics attachment when one exists
→ Play surface
→ Add to combat
→ mutable CombatantInstance
→ click/reopen the originating world object and exact mechanics projection
```

The fastest first proof uses the already-landed Threat + exact StatblockRevision path. The roadmap then extends the same projection/runtime seam to **NPC** and **Player Character** without pretending those object kinds are Threats or that all three share one mechanics schema.

### Product invariant

> Threat, NPC, and Player Character are distinct first-class world objects. They may share projection infrastructure and runtime capabilities, but they do not share domain meaning, lifecycle, or mechanics authority merely because all three can appear in combat.

A second invariant governs Combat:

> Play/Combat consumes typed world objects and exact accepted mechanics authorities. A corpus path, Markdown file, display-name lookup, generated-artifact path, or implicit latest revision is never the normal mechanics ingress for a combatant.

---

## 2. Explicit rejection of the static prototype data model

`evals/c2_live_prep/mireward-prep/combat.html` remains a useful interaction and visual ancestor. It is **not** an authority model.

Its direct links to corpus Markdown statblocks are legacy prototype behavior. The new Play surface must not reproduce that loading path.

```text
Useful to inherit:
  compact initiative scanning
  current-turn emphasis
  fast HP mutation
  persistent turn controls
  low visual overhead

Do not inherit:
  corpus Markdown as mechanics authority
  file paths as combat identity
  title/name-based statblock lookup
  local/static statblock hydration
```

The current server-backed `CombatRosterModule` is likewise a useful state/API ancestor, but its legacy `statblock_path`, `statblock_artifact_id`, corpus fingerprint, and generated-artifact ingress are migration targets rather than contracts to generalize.

---

## 3. Domain decision — first-class world-object kinds

The product model should include at least these concrete graph kinds:

```text
Threat
NPC
PlayerCharacter
Location
Faction
Item
Encounter
...
```

For this roadmap, the new concrete kinds are:

```text
npc
player_character
```

Exact serialized kind names must be frozen by the DungeonMind kernel contract after cutover. The product semantics are frozen here even if the final enum spelling changes during that re-anchor.

### 3.1 Do not introduce one universal `Character` domain object

NPC, Player Character, and Threat differ in ways that matter to authority and product behavior:

| Concern | Threat | NPC | Player Character |
|---|---|---|---|
| Primary meaning | adversarial creature, hazard, force, swarm, pressure | persistent non-player person/actor in the fictional world | player-controlled protagonist |
| Graph identity | first-class | first-class | first-class |
| Hostility defines type? | N/A | **No** | **No** |
| Typical mechanics attachment | exact StatblockRevision through Threat binding | optional exact combat mechanics attachment | dedicated PC/character mechanics authority, to be re-anchored |
| Can exist with no combat mechanics? | yes | yes | world identity yes; Play combat activation depends on mechanics/state contract |
| Persistent relationships | yes | yes, usually dense | yes, usually dense |
| Mutable combat state | runtime only | runtime unless a later persistent-NPC-state owner is introduced | must preserve a seam for persistent character state |

An NPC becoming hostile does not become a Threat object. A Threat being person-shaped does not automatically make it an NPC. A Player Character never becomes an NPC merely because control changes temporarily.

### 3.2 Threat remains the first proving domain

The accepted Threat architecture remains:

```text
Threat world object
→ ThreatStatblockBinding
→ exact StatblockRevision
```

Threat identity and graph relationships remain separate from mechanics identity. Full statblock projection renders the exact structured accepted revision, not Markdown.

### 3.3 NPC proposal

An NPC world object owns persistent fictional-person identity and relationships.

Candidate domain concerns:

```text
npc_id / world_object_ref
name
aliases
description / appearance
role / occupation where useful
affiliations
relationships
image bindings
world / campaign scope
creation / extraction / authorship provenance
```

Combat mechanics are optional. An NPC that needs mechanics should bind to an exact accepted mechanics resource rather than duplicating mechanics into the NPC graph node.

The exact binding type is intentionally **not frozen here**. After kernel cutover, the contract slice must decide whether NPC statblock attachment is represented by the generic `WorldObjectResourceBinding` already described by the authored-object lifecycle or by a typed NPC-specific binding built on the same exact external resource locator. It must not reuse `ThreatStatblockBinding` merely because both can point at statblocks.

### 3.4 Player Character proposal

A Player Character world object owns persistent protagonist identity in the World Graph.

Candidate domain concerns:

```text
player_character_id / world_object_ref
name
aliases
description / appearance
backstory-facing summary
party membership
affiliations
relationships
goals / hooks where graph-authoritative
image bindings
world / campaign scope
creation / import provenance
```

The Player Character world object does **not** own a copied character sheet body.

The durable PC mechanics authority must be re-anchored against the actual DungeonMind / existing PC generator and character-sheet contracts before implementation. This roadmap therefore freezes only this seam:

```text
PlayerCharacter world identity
→ exact PC mechanics reference (contract name/schema TBD by audit)
→ optional persistent character state authority
→ Play CombatantSeed adapter
```

Do not invent a `CharacterRevision` schema merely to mirror StatblockRevision. If the existing PC system already has the correct durable identity/revision boundary, reuse it. If it does not, design that boundary explicitly in its own contract slice.

---

## 4. Shared substrate — common projection protocol, not common domain storage

The reusable abstraction should be a **world-object projection envelope and capability set**, not a giant universal graph object containing every field for every kind.

Conceptually:

```text
WorldObjectProjection {
  objectRef
  kind
  label
  summary
  worldId
  campaignScope
  images[]
  relationships[]
  provenanceSummary
  capabilities[]
  domainPayload
}
```

The exact runtime type should be extracted only after the DungeonMind kernel projection contract is re-anchored. The important boundary is:

- shared code can render identity, images, relationships, scope, and common actions;
- domain adapters own Threat/NPC/PC-specific content;
- surfaces filter capabilities by context and authorization;
- graph identity and writes remain kernel-governed;
- projection state is never the canonical store.

### 4.1 Shared capabilities

Capabilities are contextual behaviors over exact object identity, not object subclasses.

Useful capability vocabulary includes:

```text
open_object
inspect_relationships
use_as_agent_context
insert_reference
place_object
combat_projectable
generate_or_revise_resource
edit_world_identity
```

This roadmap primarily proves `combat_projectable`.

### 4.2 `combat_projectable` contract

Threat, NPC, and Player Character may all be combat-projectable through different adapters.

```text
Threat
  → exact Threat binding
  → exact StatblockRevision
  → CombatantSeed

NPC
  → exact optional mechanics binding
  → exact accepted mechanics revision
  → CombatantSeed

PlayerCharacter
  → exact PC mechanics authority
  → persistent-state policy
  → CombatantSeed
```

Combat does not need to understand how each domain obtained its mechanics. It receives a verified bounded seed plus immutable source locators.

---

## 5. Combat runtime contract direction

The authored-object lifecycle already distinguishes world object, generated resource, placement, runtime seed, and runtime instance. Play should make that separation visible.

### 5.1 Source identity

A combatant created from a world object should retain enough immutable provenance to reopen exactly what was used.

Conceptual locator:

```text
CombatSourceLocatorV1
  world_object_ref
  world_object_kind
  binding_ref?
  mechanics_resource_ref?
  mechanics_revision_ref?
  definition_digest?
  placement_ref?
```

For Threat + Statblock, the mechanics tuple remains exact:

```text
statblock_id
revision_id
definition_digest
```

No `latest` resolution after insertion.

### 5.2 Bounded operational snapshot

Combat should persist only the bounded mechanics needed to keep the encounter operational if the mechanics dependency becomes temporarily unavailable.

Candidate minimums:

```text
name
armor_class
max_hit_points
initiative input/modifier required by current ruleset
speed summary where the tracker needs it
bounded warnings / adjudication markers where required
```

The full statblock remains an exact projection from the mechanics authority. Combat does not persist another canonical full statblock body.

### 5.3 Mutable runtime state

```text
combatant_instance_id
display name / local override
team / controller
initiative / order
current HP
temp HP
conditions / statuses
notes
defeated
encounter-local overrides
```

Runtime mutation never changes graph identity, binding identity, mechanics revision, or mechanics digest.

### 5.4 Player Character state seam

PCs create a deliberate additional boundary.

Some state that looks like combat state may persist beyond one encounter:

```text
current HP
expended resources
spell slots / class resources
some ongoing conditions
```

The first Play slice must **not** accidentally make all of that encounter-owned forever.

Before PC combat activation is promoted, the PC contract slice must classify each mutable field as one of:

```text
persistent character state
encounter-local overlay
derived presentation
```

The first Threat/NPC runtime proof can proceed before the full PC persistence model is implemented.

---

## 6. Play surface composition

Play is the product surface. Combat Tracker is the first Play workspace.

For v1 it is acceptable for Combat to occupy nearly the entire Play body, but the architecture must leave room for later Play workspaces such as exploration, scene state, travel, clocks, or other live-session tools.

```text
PLAY SURFACE
│
├── Play runtime context
│   ├── campaign / session
│   ├── active encounter
│   ├── round / active turn
│   └── runtime write policy
│
├── Primary workspace
│   └── Combat Tracker
│
├── shared Tool Host
│   ├── Find existing world object
│   ├── Add combatant
│   └── Rules lookup later
│
└── shared Projection Host
    ├── Threat Sheet
    ├── NPC sheet
    ├── Player Character sheet
    ├── exact mechanics projection
    └── rules projection later
```

### Surface Interaction rule

Play publishes domain meaning upward into the existing Surface Interaction Layer. It does not create a second Nav Bar, Tool Bar, Agent Bar, or Projection Pane.

The same shared World Graph lens/projection infrastructure should remain app-scoped. Switching Plan → Build → Play with the same exact lens should reuse the same admitted projection instead of reloading an equivalent graph view.

---

## 7. Combat Tracker v1 interaction target

Use the static Mireward tracker as the interaction ancestor and the React `CombatRosterModule` as the runtime/API ancestor.

The v1 tracker should optimize for live scanning and mutation:

```text
21+
▶ 23  Baergrom             AC 18     42 / 55
  21  Tripod Null-Calf A   AC 15     63 / 95   poisoned

16–20
  19  Caelynn              AC 14     31 / 31
  17  Meatwing A           AC 13      7 / 18
```

Required early behaviors:

- fixed initiative bands `21+`, `16–20`, `11–15`, `6–10`, `1–5`;
- clear active actor and next-turn control;
- HP delta entry such as `-12` / `+7` plus direct set;
- Enter commits numeric changes and exits edit mode;
- click world-object-backed combatant name to reopen its shared projection;
- exact mechanics detail opens from the pinned resource identity;
- encounter continues to operate from its bounded snapshot during mechanics-service unavailability.

Rules hover, status expiry, spawn templates, richer encounter construction, and automation remain post-proof dogfood successors.

---

## 8. Authority matrix

| Concern | Authority | Play/Combat role |
|---|---|---|
| World object identity/kind | DungeonMind World Graph kernel | exact read + locator |
| World relationships/scope | DungeonMind World Graph kernel | project/read |
| Threat mechanics | immutable accepted StatblockRevision | exact read; seed derivation |
| NPC mechanics | exact accepted mechanics binding, contract to freeze | exact read; seed derivation |
| PC mechanics | existing PC mechanics authority after audit | exact read; seed derivation |
| Preferred library revision | owning domain selection policy | may browse, never silently repin active combatant |
| Placement | placement owner / Play prep contract | exact optional input |
| Current combat HP/init/status | Combat runtime | owns writes |
| Persistent PC state | PC state authority, to freeze | read/write through explicit adapter |
| Projection UI | DungeonBuddy Surface Interaction + domain renderer | display only |
| Static Markdown | convenience/export projection only | never canonical mechanics ingress |

---

## 9. Delivery phases

### Phase K — DungeonMind kernel cutover re-anchor

Before new object kinds or Play contracts are implemented:

1. identify the final DungeonMind graph object identity/kind schema;
2. identify exact projection request/response contracts;
3. identify external-resource/binding representation after cutover;
4. record how DungeonBuddy consumes exact world/campaign/revision identity;
5. inventory PC generator / character-sheet persistence and identity contracts;
6. confirm which legacy DungeonMindBuddy graph types become adapters versus demolition targets.

**Exit proof:** a coding agent can resolve one exact Threat from DungeonBuddy through the DungeonMind kernel without relying on old local graph-store shapes.

### Phase W — Player Character and NPC world objects

Freeze and implement first-class object semantics:

- `npc` object identity and projection payload;
- `player_character` object identity and projection payload;
- party membership as relationships/graph truth rather than the whole PC object;
- migration/linking from current deterministic party anchors where applicable;
- NPC extraction/authoring path mapped without conflating Threats;
- world-object projection envelope characterized across Threat/NPC/PC.

**Exit proof:** the same graph query/projection infrastructure can return a Threat, NPC, and Player Character as distinct typed objects with stable IDs and relationships.

### Phase P1 — Play surface shell

- add `/play` as a first-class AppChrome route;
- publish Play surface identity/context/capabilities;
- preserve shared app-level graph lens/projection providers;
- mount Combat Tracker as the first primary Play workspace;
- no broad Play feature suite.

**Exit proof:** navigate Plan → Build → Play and retain coherent shared object projection behavior.

### Phase C1 — Combat runtime identity re-anchor

- replace normal-path corpus/artifact mechanics ingress;
- introduce exact source locator + bounded operational snapshot;
- persist/reload immutable source identity separately from runtime mutations;
- retain explicit compatibility handling for legacy saves;
- prevent HP/init/condition mutation from changing source identity.

**Exit proof:** a combatant can reload from exact world/mechanics locators with no Markdown/path authority.

### Phase P2 — Compact Combat workspace

- migrate existing server-backed combat operations into the Play workspace;
- adopt compact initiative-band UI;
- add HP delta popover / commit-and-blur behavior;
- preserve save/load/turn reliability;
- fail soft when non-critical projection dependencies are unavailable.

**Exit proof:** the tracker is good enough to run a real live encounter even before every object type is integrated.

### Phase P3 — Threat projection/runtime proof

- Find existing uses the Play-published World Graph lens;
- Threat opens the same Threat Sheet used elsewhere;
- Add to combat resolves exact binding/revision/digest;
- seed is deterministic and bounded;
- combat row reopens the originating Threat and exact mechanics;
- active instance never follows a newer revision automatically.

**Exit proof / Magic Moment:** Plan or Build can inspect a Threat, Play immediately finds the same object from the resident graph lens, adds it to combat, mutates HP, and reopens the exact source projection.

### Phase P4 — NPC projection/runtime proof

- NPC sheet projection prioritizes useful world/person information;
- optional exact mechanics binding is visible without making the NPC a Threat;
- combat-projectable NPCs derive a seed through their own adapter;
- NPCs with no mechanics remain valid world objects and receive a truthful disabled Add-to-combat reason.

**Exit proof:** add Lysandra-like allied NPC from her NPC world object, mutate runtime state, and reopen the same NPC identity.

### Phase P5 — Player Character projection/runtime proof

After the PC mechanics/state audit:

- PC sheet projects world identity + exact mechanics reference;
- Combat adapter derives the same bounded runtime contract;
- persistent versus encounter-local mutable state is explicit;
- no copied character-sheet body in the graph;
- party membership and PC identity remain stable across sessions.

**Exit proof:** add/open a Player Character from the World Graph, run a combat mutation cycle, persist the correct state owner(s), and reopen the same PC identity.

### Phase D — Live dogfood and performance proof

Run real combat with mixed:

```text
PlayerCharacter
NPC ally
Threat enemies
```

Measure and record:

- Plan/Build/Play surface-switch graph reuse;
- time to Find existing;
- time to open projection;
- time to Add to combat;
- combat mutation latency;
- reload behavior;
- dependency-unavailable behavior;
- accidental duplicate graph/mechanics loads.

The product target is not merely correctness. Surface switching and graph-backed lookup should feel effectively immediate during play.

---

## 10. Dogfood successors after the projection proof

Prior live-play notes already identify strong follow-ups. They remain deliberately after the object/runtime spine:

1. **Rules-term projection** — dynamically hydrate rules terms such as conditions from the ingested rules authority.
2. **Ability spawn templates** — summon/minion creation from structured mechanics with owner/controller/provenance.
3. **Status duration semantics** — begin with end-of-turn expiry, then richer timing.
4. **Encounter construction/reconfiguration** — rapidly add/remove/reseed combatants as scouting and player choices change setup.
5. **Persistent PC resource integration** — once the first character-state seam is proven.

These should reuse Play projections/capabilities rather than grow a combat-specific parallel architecture.

---

## 11. Stop conditions and risks

Stop and re-design rather than papering over the boundary if:

- the DungeonMind cutover does not expose stable exact world-object identity to DungeonBuddy;
- PC mechanics have no durable exact identity/revision concept and adding one would be larger than this roadmap;
- NPC statblock attachment requires copying mechanics into graph nodes;
- Combat requires resolving mechanics by display name, file path, Markdown, or implicit latest revision;
- the Play route would need to own a second shared Tool/Projection host;
- PC current state cannot be separated from encounter-local state without data loss;
- switching surfaces causes independent equivalent World Graph loads because Play bypasses the app-scoped projection provider.

Major migration risk: existing combat saves are legacy-shaped. Compatibility must be explicit; do not fabricate exact object/resource identity for old rows that never had it.

---

## 12. Roadmap acceptance

This roadmap is complete when real dogfood proves all of the following:

- [ ] `Threat`, `NPC`, and `PlayerCharacter` are distinct first-class world-object kinds.
- [ ] They share projection infrastructure without sharing one universal domain schema.
- [ ] Threat uses exact accepted StatblockRevision mechanics.
- [ ] NPC can exist without mechanics and can optionally resolve exact combat mechanics without becoming a Threat.
- [ ] PC world identity is distinct from its exact mechanics and persistent-state authorities.
- [ ] `/play` is a first-class Surface Interaction consumer.
- [ ] Combat Tracker is the first Play workspace, not a fourth authority surface.
- [ ] Find/open uses the shared app-scoped World Graph lens/projection path.
- [ ] Combat insertion is capability/adaptor-driven and receives a verified bounded seed.
- [ ] Runtime HP/init/conditions do not mutate graph or immutable mechanics.
- [ ] No normal combat path depends on corpus Markdown, artifact path, filename, title lookup, or implicit latest revision.
- [ ] A mixed PC/NPC/Threat encounter survives save/reload and remains traceable to exact source identities.
- [ ] Plan → Build → Play switching demonstrates coherent warm projection reuse during live play.
