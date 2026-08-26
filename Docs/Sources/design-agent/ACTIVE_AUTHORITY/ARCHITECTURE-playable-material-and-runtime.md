---
document_id: dmb-architecture-playable-material-and-runtime
title: Playable Material and Runtime — Architecture Authority
document_class: architecture_authority
status: active
version: 1.2
created_at: "2026-08-15"
updated_at: "2026-08-26"
workstream: PLAY-SURFACE
evidence:
  - "PR #578 — Of Conks / Hempholm table-ready dogfood"
  - "C2S27 native Play dogfood — BLOCKED / PLAY NOT READY; unexpected-play and Combat evidence"
  - "PR #628 — Beat-first v2 grammar/manifest foundation"
  - "APP-STATE AS1–AS5 — WorkRevision history, PostgreSQL Play Runtime/continuity, legacy Play persistence demolition"
companion_authorities:
  con_ready_anchor: "../Plans/STEWARDS-ANCHOR-con-ready.md"
  con_ready_roadmap: "../Roadmaps/ROADMAP-con-ready.md"
  surface_interaction: "ARCHITECTURE-surface-interaction-layer.md"
  graph: "ARCHITECTURE-campaign-supergraph.md"
  application_state: "ARCHITECTURE-application-state-layer.md"
companion_designs:
  play_projection: "DESIGN-play-surface-projection.md"
  authoring_adoption: "DESIGN-playable-authoring-and-adoption.md"
  current_moment_cockpit: "DESIGN-play-current-moment-cockpit.md"
---

# Playable Material and Runtime — Architecture Authority

## Status and scope

This document is the architecture authority for the boundary between:

- durable World knowledge;
- rich Original Source;
- durable GM-authored/adopted Playable Material;
- mutable Played / Runtime State;
- Play projections composed from those authorities.

It does not replace:

- DungeonMind / Campaign Supergraph authority for World identity, claims, graph writes, and governed publication;
- Source authority for source artifacts/provenance;
- exact Mechanics authority such as immutable accepted `StatblockRevision`;
- Combat authority for mutable combat state;
- Application State architecture for Buddy PostgreSQL/storage topology;
- Surface Interaction architecture for AppChrome/shared projection hosts;
- the CON-READY product roadmap.

The 2026-08-26 revision updates repository truth after APP-STATE and clarifies one product/architecture distinction:

> **Beat-first is the durable Playable organization. Scene-centered is the default Play projection when a Scene is current. Projection dominance does not change durable ownership.**

---

## 1. Governing model

DungeonBuddy maintains four distinct state layers:

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
runbooks, beats, scenes, choices, consequences,
object-attached prep, encounter composition, table framing

        ↓ actual table interaction

PLAYED / RUNTIME STATE
current Beat/Scene, resolved state, selections, notes,
linked runtime handles, and other mutable run-local facts
```

A fifth concept sits over these layers:

```text
PROJECTION
surface-specific composition of one or more authorities
```

Play is a projection consumer and Runtime owner. It is not another World/Source/Mechanics truth store.

---

## 2. Core invariant

> **Playable Material is durable GM intent that may reference World, Source, and Mechanics without becoming them; Runtime records what happens while using one exact Playable revision without rewriting that revision.**

Consequences:

1. Playable Material may reinterpret/narrow World/Source for a run without silently publishing canon.
2. Runtime changes never mutate immutable Source/World/Mechanics merely because the table changed.
3. Projection may combine authorities but must preserve owning boundaries.
4. Convenience projections do not become copied truth stores.
5. Historical Playable revision identity is real product authority; current/latest is never a substitute for a Run's pinned revision.

---

## 3. Authority table

| Information | Owning authority | Playable may do | Runtime / Play may do |
|---|---|---|---|
| Original prose / quoted module text | SOURCE | reference / quote with provenance | read/project |
| World identity | WORLD | reference object | read/project; never silently redefine |
| Accepted world relationship | WORLD | reference; add run-local interpretation separately | read/project |
| Run-local NPC motivation/secret | PLAYABLE | own | note outcomes of use |
| Beat / Scene / Decision organization | PLAYABLE | own | point at current/resolved/selected IDs |
| Prepared Option / consequence / transition | PLAYABLE | own | record selected Option; derive relevance |
| Exact statblock mechanics | MECHANICS | reference exact revision | render; instantiate Combat action |
| Encounter composition | PLAYABLE | own expected composition | explicitly instantiate/adjust Combat |
| Current HP / initiative / conditions | COMBAT | never own | link/project through Combat |
| Table note | PLAY RUNTIME | may later adopt into Playable | own/current context |
| Source asset / map image | SOURCE / ASSET | reference | read/project |
| Hermes/Agent proposed prep change | PROPOSAL, not truth | adopt after approval | no silent apply |

---

## 4. Durable Playable Material

### 4.1 WorkObject / WorkRevision

A Playable Artifact is a durable versioned Buddy content object.

Current implementation uses the APP-STATE content substrate:

```text
WorkObject
  stable identity
  current committed revision pointer

WorkRevision
  immutable revision identity
  revision_n
  canonical bytes
  content_sha256
  provenance / timestamps

WorkingCopy
  mutable recoverable draft
  exact base revision
```

A committed Runbook revision remains loadable after later revisions exist.

A Playable Artifact must preserve:

- stable WorkObject identity;
- campaign/world scope needed for refs;
- immutable committed revision identity/digest;
- readable/editable content;
- stable semantic element IDs for Runtime references;
- typed refs to external authorities instead of copied truth where possible.

### 4.2 Stable element identity

Any Playable element referenced durably must have identity independent of current display text.

At minimum:

```text
beat:<slug>
scene:<slug>
choice:<slug>
option:<slug>
```

Heading/title edits do not change identity.

### 4.3 Semantic blocks

Playable Material may contain:

- At the table;
- Read aloud;
- GM note;
- Rules now;
- Warning;
- Consequence;
- ordinary prose;
- typed reference;
- contextual tool/action ref.

These are Playable presentation/use semantics, not World ontology.

### 4.4 Object-attached Playable Material

A durable World object may have run-specific Playable interpretation without that interpretation becoming World truth.

The World object remains identity authority; Playable owns only the run-specific material.

---

## 5. Runbook, Beat, Scene, and Decision

The canonical durable hierarchy is:

```text
Runbook
  → ordered Beats

Beat
  → objective / pressure / phase / context
  → ordered Scenes
  → ordered Decisions
  → Beat-level consequences
  → references/tools

Scene
  → concrete playable situation inside exactly one Beat

Decision (wire kind: choice)
  → ordered Options

Option
  → consequence
  → activates / suppresses later Beat/Scene relevance
```

This is Playable organization, not World Graph Adventure ontology.

### 5.1 BF1 v2 serialization

BF1 / PR #628 implemented:

- `dmb-playable-element:v2`;
- Beat H2;
- Scene and Choice/Decision as Beat-owned H3 siblings;
- optional same-Beat `scene=` association on Decision;
- Option as marked list item;
- `activates` / `suppresses` transition edges;
- v2 structure index;
- `dmb_play_run_reference_manifest_v2`.

Mixed grammar and invalid containment/identity/edge states fail closed.

### 5.2 Runbook

A Runbook is the durable linear authoring arrangement of the material the GM intends to run.

Its document order remains authoritative for authored order and initial Beat seeding.

The Runbook document is **not required to be the runtime navigation UI**. Play may project the same committed truth as a Scene-centered cockpit.

### 5.3 Beat

Beat is the session-scale durable context container: objective, pressure, phase, framing, and the Scenes/Decisions/references belonging to it.

Initial Beat kinds remain:

```text
spine
optional
interrupt
```

Beat does not own live clock values; prepared definition is Playable, live value is Runtime/owning capability.

### 5.4 Scene

Scene is a concrete playable situation inside one Beat.

Scene is the normal dominant central Play projection when current, but that visual dominance does not make Scene the durable parent of Decision or Beat.

### 5.5 Consequences

Consequence is the canonical authored outcome concept.

Consequences attach to Beat outcomes and Decision Options. Presentation hints may include reward/cost/state/relationship/access/information/etc. These are extensible UI semantics, not a World ontology.

---

## 6. Choices, Decisions, branching, and relevance

Permanent Playable choices are generic:

```text
Decision
  choiceId
  prompt
  Options[]
    optionId
    label
    consequence
    activates[]
    suppresses[]
```

Runtime records only:

```text
choiceId → selected optionId
```

### 6.1 Branch relevance, not permission

`activates` / `suppresses` are authored branch/relevance edges.

They are interpreted as projection emphasis:

```text
activated target     → emphasized
suppressed target    → de-emphasized unless also activated
everything else      → default
```

They do **not** make material inaccessible.

A GM may inspect or explicitly make current any Beat/Scene regardless of emphasis. The architecture does not define a navigation permission graph.

### 6.2 No general condition engine

The first vocabulary does not include boolean expressions, arbitrary event predicates, automatic state reducers, or workflow execution.

If future dogfood proves combined-choice conditions are necessary, that requires new evidence and design.

### 6.3 Consequences are informational first

Selecting an Option does not automatically publish World facts, execute arbitrary Runtime mutations, or advance unrelated systems. Actual outcomes are explicitly recorded through owning capabilities.

---

## 7. Run Runtime and persistence

A Run binds mutable Play state to one exact committed Playable WorkRevision.

Conceptually:

```text
Run
  runId
  campaignId
  playableWorkObjectId
  playableRevisionN
  playableWorkRevisionId
  playableContentSha256
  runRevision
  currentBeatId
  currentSceneId?
  resolvedBeatIds[]
  selections: { choiceId: optionId }
  notes / note anchors
  linkedCombatRuntime?
  timestamps
```

The actual AS3 schema stores Run + sealed manifest transactionally in Buddy PostgreSQL and uses `run_revision` SQL CAS.

### 7.1 Historical revision invariant

> **A Run reads the exact historical WorkRevision it pins, even after later WorkRevisions exist.**

No “current workspace revision” prerequisite remains for historical Run readability.

### 7.2 Active Run continuity

AS4 stores the active/selected Run in `play.active_run` on PostgreSQL.

Bare `/play` resolves that explicit selection and then performs full Run/manifest/WorkRevision admission. It never guesses latest/first.

### 7.3 Legacy Play persistence demolished

AS5 removed current-product authority for:

- Run JSON files;
- manifest sidecars;
- `active-run.json`;
- Play rebase intents;
- Play filesystem transaction locks/import engine.

Current Play operation must not depend on `out/runtime/play/` existing.

### 7.4 Runtime invariants

- Run references stable Playable IDs.
- Run never invents Playable structure.
- Run never writes World canon.
- CAS protects mutable Runtime updates.
- corrupted Run/manifest aggregate fails closed; ordinary mutation cannot repair it silently.
- explicit rebase is one transaction and preserve-only.
- Combat remains Combat-owned.

---

## 8. Current position and projection

BF2 owns opening v2 READY admission.

For a new v2 Run:

- seed `currentBeatId` durably to first spine Beat, else first Beat;
- zero Beats is not runnable;
- do not infer a Scene.

For an existing Run:

- resume exact persisted Beat/Scene;
- when Scene is current, Scene is the primary central projection;
- Beat context remains accessible;
- Beat-only current position remains legal.

### 8.1 Inspect versus mutate position

Opening an object or Playable element is projection/read behavior and preserves current position.

Explicit **Make Current** for a Scene mutates Beat + Scene together through Runtime CAS.

This boundary lets unexpected-play inspection stay cheap without corrupting the current moment.

---

## 9. Notes

Table notes are Runtime state, distinct from authored Playable `GM Note` blocks.

Product projection may treat notes as objects pinned to Run/Beat/Scene/other Play context.

This architecture intentionally does **not** freeze a new note table. The existing note persistence may continue until a concrete interaction proves a need for independent note IDs, multiple notes per anchor, timestamps, move/re-pin, or another lifecycle.

Post-session adoption of a Runtime note into Playable remains explicit.

---

## 10. Projection architecture

Play composes:

```text
WORLD
SOURCE
PLAYABLE
MECHANICS
RUNTIME
COMBAT handle/status where admitted
        ↓
PLAY PROJECTION
```

### 10.1 Contextual and global retrieval

Play must support two access modes:

```text
CONTEXTUAL
references seeded by current Beat / Scene

GLOBAL / ON-DEMAND
known campaign material needed unexpectedly
```

The global finder is surface/product behavior, not new World/Playable authority.

Opening a found object never mutates Runtime merely because it was opened.

### 10.2 Play Object Sheet

A Play Object Sheet is projection-only composition. It leads with table usefulness and keeps graph/evidence internals subordinate.

### 10.3 Threat / exact mechanics

```text
Threat
→ exact accepted mechanics binding
→ StatblockRevision
→ Play Threat projection
→ explicit Add to Combat
```

Exact mechanics must not be copied into Runbook fields merely for faster rendering.

### 10.4 Combat workspace

Combat may visually replace the Scene as the central working instrument while expanded.

That does not move HP/initiative/conditions/encounter persistence into Play. Play retains origin Beat/Scene and a linked Combat handle/status; Combat remains authority.

---

## 11. Agentic authoring boundary

Agent/Hermes may propose Playable changes, but proposal is not adoption.

```text
ground in admitted context
→ proposal targets exact WorkObject + base revision/digest + stable element
→ preview
→ GM approves
→ apply to Canvas/working copy
→ ordinary Save commits WorkRevision
```

Requirements:

- stale/dirty conflict protection;
- no fuzzy silent retargeting;
- provenance retained when grounded in Source/World;
- no automatic graph publication;
- no hidden durable write during proposal generation.

---

## 12. Promotion boundaries

### Playable → World

Explicit reviewed World/graph publication. The originating Playable WorkRevision remains provenance/evidence.

### Runtime → Playable

Explicit adoption into new prep/recap material through the normal proposal/adoption + Save boundary.

Neither direction is automatic.

---

## 13. Revision and rebase rules

1. committed WorkRevisions are immutable and historically loadable;
2. a Run stays bound to its exact historical revision until explicit rebase;
3. newer WorkRevisions do not force rebase for readability;
4. same-grammar rebase is preserve-only and transactional;
5. removal/semantic relocation of referenced IDs may block rebase;
6. v1→v2 is a structural grammar boundary and is not silently mapped;
7. current/latest fallback is forbidden;
8. exact mechanics/source refs retain their own authority/revision rules.

---

## 14. Surface Interaction Layer boundary

Shared AppChrome/projection host remains outside Play ownership.

Play publishes capabilities/projections upward, may select Playable Canvas context, and may register Beat/Scene/Object/Threat/Combat projections.

It does not absorb Canvas document authority or build a second chrome.

---

## 15. Migration / demolition posture

Historical campaign-specific Play bridges remain replacement targets:

```text
campaign Play-object dictionaries
  → generic World + Source + Playable projections

campaign Beat dictionaries
  → durable Playable Runbook content

campaign Threat bridges
  → exact mechanics bindings

adventure-specific branch enums
  → generic Decision/Option + activates/suppresses

legacy prep host globals
  → native Play capabilities
```

Do not preserve old bridge topology merely because it once carried dogfood.

---

## 16. Architecture acceptance tests

A conforming implementation should be able to prove:

1. Runbook WorkRevision N remains loadable for a Run after N+1 is committed.
2. stable Beat/Scene/Choice/Option IDs survive ordinary prose/title edits.
3. a new v2 Run seeds a Beat explicitly; resume restores exact stored Beat/Scene.
4. opening another Scene for inspection does not mutate current position.
5. explicit Make Current changes Beat+Scene lawfully under CAS.
6. authored Option selection persists only IDs and re-derives branch relevance.
7. a de-emphasized Scene remains accessible.
8. a Play Object Sheet composes useful content without campaign-specific dictionaries.
9. an unexpected known Threat can be found, exact mechanics rendered, and Add to Combat invoked without Plan/Build navigation.
10. Combat expansion does not transfer combat state ownership into Play and collapse returns to exact Scene.
11. Runtime notes persist and remain distinct from authored GM Note blocks.
12. Agent proposals require exact base/target and explicit approval.
13. Source, World, Playable, Mechanics, Runtime, and Combat authority remain distinguishable.
14. ordinary Play operates with legacy `out/runtime/play` persistence absent.

---

## 17. Explicit non-goals

- universal Adventure object in World Graph;
- automatic extraction of every Scene/Beat/Choice from source;
- bespoke universal NPC/Shop ontology;
- copying source prose or mechanics into Playable as new authority;
- making every Runtime event canon;
- making every consequence a typed graph assertion;
- Play-owned Combat state;
- Play-owned map/media truth;
- arbitrary Agent filesystem authority;
- direct Agent writes without approval;
- navigation permission gating from Choice relevance;
- condition/workflow DSL without new evidence;
- new note schema merely because notes are projected as pinned objects.
