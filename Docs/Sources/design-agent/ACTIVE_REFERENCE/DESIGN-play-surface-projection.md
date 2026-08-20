---
document_id: dmb-design-play-surface-projection
title: Play Surface and Table Projections
document_class: product_design
status: active
version: 1.0
created_at: "2026-08-15"
updated_at: "2026-08-20"
workstream: PLAY-SURFACE
architecture_authority: "ARCHITECTURE-playable-material-and-runtime.md"
surface_authority: "ARCHITECTURE-surface-interaction-layer.md"
evidence:
  - "PR #578 — Of Conks / Hempholm table-ready dogfood"
  - "C2 Session 27 native Play dogfood — BLOCKED / PLAY NOT READY (Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md)"
supersedes_direction_from:
  - "DESIGN-play-mode-runbook-product-direction.md"
  - "../Plans/DESIGN-session-runbook-command-surface.md"
---

# Play Surface and Table Projections

## 0. Product thesis

**Play is the surface for the next few minutes at the table.**

Plan may expose preparation machinery. Build may expose durable world construction. Play must prioritize continuity of attention.

The contract is:

```text
click / focus something useful
→ use detail or a tool
→ close it
→ return to the exact table moment
```

Not:

```text
navigate away
→ reconstruct context manually
```

## 1. Relationship to existing surface architecture

`ARCHITECTURE-surface-interaction-layer.md` remains the authority for AppChrome, shared Nav/Agent/Projection/Tool/Edit hosts, Canvas host, and surface publication.

Play is a surface-domain publisher.

Play may publish:

- current Run / Scene / Beat context;
- graph/source/playable/mechanics reference resolution;
- Play capability launchers;
- table-specific projection renderers;
- current Canvas/work-object context where editing is admitted.

Play does not own shared bars or a second projection host.

## 2. Play shell

The durable Play capability family is:

```text
Play
├── Run / Beats
├── Combat
├── Roll
├── Items
├── Mechanics / Statblocks
└── table projections
```

This is a capability family, not a requirement that every item be a permanent top-level tab.

The current PR #578 `prep` HTML host proves that these tools can be consolidated under Play. It is migration scaffolding. Permanent Play panels should become native product capabilities rather than injected legacy HTML/global scripts.

## 3. Default anchor: the current Beat

The default Play anchor is the current Runbook moment. After C2S27, the table
hierarchy is **Beat-first**: the current Beat is the table stage, and Scenes
and Decisions live beneath it.

This is the reviewed product direction, not an implementation claim against
the current P1/P2 wire shape. The shipped structure places Scene at H2 and
Beat/Choice at H3, requires Beat/Choice membership under Scene, and requires a
current Beat to belong to the current Scene. Before this projection can be
implemented as Beat-first, the P1 structure/serialization, P2B1 manifest
membership/versioning, P2B2 current-position semantics, sealed Run/manifest
migration, and P2C migration/rebase behavior must be redesigned and reviewed.

A useful hierarchy is:

```text
Run title
Beat deck / phase position          ← session-scale orientation
Current Beat stage                  ← table objective / pressure / phase
  ├── Scenes inside this Beat       ← concrete playable situations
  ├── Decisions / Choices           ← options + consequences + transitions
  └── references / tools
```

The GM should always be able to answer:

- Where am I?
- What is happening now?
- What is optional?
- What pressure should advance if they stall?
- What can I open without leaving?
- What happens if this resolves?
- What did we decide, and what did that decision change?

### 3.1 Beat deck

Beat navigation provides session-scale orientation across the Runbook's phases.

Expected interactions:

- Previous / Next Beat;
- select Beat directly;
- show current position and resolved state;
- show which Beats remain possible/relevant given recorded Decisions;
- preserve current run state.

### 3.2 Scenes and Decisions beneath the current Beat

Within the current Beat, Scenes are the concrete playable situations and Decisions are the authored branch points.

Expected interactions:

- show the current Beat's objective/pressure/phase as the stage;
- show `spine`, `optional`, `interrupt` character where Beats carry kinds;
- move between the Beat's Scenes without losing Beat position;
- surface Decisions with their Options and consequences; recording a Decision reshapes which later Scenes/Beats are shown as possible/relevant;
- mark Beat resolved/unresolved;
- show current Beat detail in a wide calm stage.

## 4. Beat presentation vocabulary

A focused Beat may project:

### At the table

The primary GM-facing framing. This is the first thing Play should make easy to scan.

### Read aloud

Player-facing text intended to be spoken or closely paraphrased.

### GM note

Private framing, motivation, interpretation, or operational reminder.

### Rules now

Rules/mechanics the GM needs in this moment.

When exact mechanics authority exists, Rules Now should reference or summarize it rather than silently becoming a second mechanics store.

### Warnings

Table hazards, spoiler boundaries, sequencing traps, or "do not telegraph" reminders.

### Consequences

Outcomes conditioned on what the party/table does.

Useful presentation labels may include:

- If they wait
- If they succeed
- If they fail
- If they choose…
- Reward
- Cost
- Clock / state change
- Relationship change

These are views over the canonical `consequences` concept.

**Treasure is displayed as a reward consequence, not as an independent Beat primitive.**

### Open now

Typed object/source/mechanics references relevant to the current Beat.

### Tools

Contextual explicit actions such as:

- Add threat to Combat
- Open Roll table
- Open item/mechanics
- Open source
- Ask Hermes

Tool links are projection/capability data, not Runbook truth.

## 5. Play Object Sheets

A Play Object Sheet is the table-first projection of a known object.

It should not begin with graph internals.

### 5.1 Common hierarchy

The default hierarchy is:

1. identity and compact role/type;
2. table-useful Playable interpretation;
3. relevant current relationships;
4. exact mechanics/actions when applicable;
5. source/provenance;
6. Advanced graph/evidence detail.

### 5.2 NPC projection

Useful sections:

- At the table
- Attitude
- Offers & hooks
- Rules now
- Connected now
- Source

The projection must not imply that Attitude/Offers are universal durable NPC fields. They may be object-attached Playable blocks.

### 5.3 Location projection

Useful labels can adapt:

- Arrival
- What's happening
- Who's here / what can happen
- Rules now
- Connected now
- Map / source

### 5.4 Item projection

Useful labels can adapt:

- What it does
- Who wants it / pressure
- Hooks
- Rules now
- Connected now
- Source / exact mechanics

### 5.5 Threat projection

Threats use the established Threat/Statblock path.

The Play projection should expose:

- table summary;
- exact accepted mechanics;
- tactics/prepared intent where available;
- current relevant relationships;
- source;
- **Add to Combat**.

No campaign-specific threat→draft dictionary is allowed in the permanent path.

## 6. Relevant-now connections

PR #578's `connectedNow` is useful because full graph adjacency is often too much for the table.

The permanent projection may curate a small relevant-now set from:

- explicit Playable references;
- current Scene/Beat references;
- selected graph neighbors;
- active mechanics/combat context.

The projection must distinguish this curated set from "all relationships."

Full adjacency belongs in Advanced or a dedicated graph view.

## 7. References are handles, not copied truth

A typed reference should preserve exact durable identity while allowing Play to choose the right projection.

Examples:

```text
dmb-node:...
source anchor / source document handle
statblock revision / threat binding
playable element handle
combat/run handle
```

Primary click should normally open a projection/layer and preserve Play position.

Secondary/full-detail actions may navigate deeper intentionally.

A reference click never mutates runtime/canon merely because it was opened.

## 8. Mechanics and Combat

### 8.1 Prepared threat

```text
Beat
  → Threat reference
  → Threat Sheet
  → exact StatblockRevision
  → Add to Combat
```

### 8.2 Unexpected fight

Play should allow the GM to open a known NPC/threat and explicitly add it to Combat without reconstructing JSON or hunting for a separate editor.

When exact mechanics are missing, Play must say so truthfully and offer the best admitted path; it must not fabricate a mechanics binding.

### 8.3 Quantity and team

The eventual Add-to-Combat interaction should support table-useful quantity/team selection without requiring the GM to leave Play for an authoring workflow.

Exact UI is an implementation decision.

## 9. Run state and Run continuity

Play projects runtime state from the active Run:

- current Beat;
- current Scene;
- resolved Beats;
- selected authored choices/decisions;
- scratch notes;
- linked Combat state.

Play does not make runtime state part of the Runbook document.

A reopened Play surface should restore the useful table position.

C2S27 made Run continuity a hard requirement, not a nicety:

- Re-entering Play must offer **Resume** of the active Run. **Resume vs Start New** is an explicit, truthful choice.
- Ordinary re-entry must not encourage creating a duplicate Run of the same material.
- The Run chooser must not accumulate useless duplicate UUIDs.
- Run state must be durable independent of browser session and worktree checkout.

## 10. Maps and media

When source/asset data provides a map or image, a Play Object Sheet or Beat may project it.

For maps:

- normalized pins/regions remain resolution-independent;
- pins target typed references;
- active object can be highlighted;
- click opens the normal reference projection;
- legend and map are two views of the same annotation data.

Play must not own source asset identity or store campaign-specific map dictionaries.

## 11. Source detail and Advanced

Play should expose source detail without turning into a source dashboard.

Default:

- human-readable source label;
- useful excerpt where admitted/appropriate;
- Read Source action.

Advanced/supporting detail may contain:

- full graph relationships;
- evidence/source domains;
- internal identity for debugging;
- provenance/support state.

Internal claim/revision IDs should not dominate table-facing presentation.

## 12. Editing in Play

Play may eventually support narrow in-context editing, but the safe contract is:

```text
unlock / edit admitted playable material
→ local dirty state
→ Save through normal Canvas/document authority
→ remain at the same table moment
```

Play does not gain a second save system.

For larger preparation changes, Plan remains the better workshop.

## 13. Hermes in Play

Hermes should receive current table context as a pointer/lens, not as copied truth.

Useful ambient context includes:

- active Run;
- current Scene/Beat;
- relevant object references;
- current Playable revision;
- optional linked Combat context through its owning interface.

Hermes may:

- answer from governed World/Source/Playable/Mechanics context;
- open/navigate useful projections;
- propose changes to Playable Material.

Hermes may not silently mutate Playable or World authority.

## 14. Degradation behavior

Play should remain useful when one authority is missing.

Examples:

- object exists but no Playable interpretation → show World/source-backed object sheet;
- Playable note exists but source unavailable → show note with truthful source gap;
- Threat exists but exact mechanics missing → show threat/source detail and mechanics-unavailable state;
- map asset unavailable → object sheet remains useful without it;
- Runtime state missing → open Playable Runbook at its default first Scene rather than invent progress.

## 15. Acceptance stories

A conforming Play surface should prove:

1. GM opens a real Runbook and immediately sees the current Beat stage with its current Scene.
2. GM moves Beat/Scene without page-navigation context loss.
3. GM opens an NPC/location/item chip and gets a table-useful sheet.
4. GM opens a Threat and gets exact mechanics when admitted.
5. GM adds a Threat to Combat from the Threat sheet.
6. GM records a Beat resolved and reloads without losing that state.
7. GM records a Scene/Beat scratch note without altering Runbook prose.
8. GM records an authored Decision; Play shows its consequences and which later Scenes/Beats remain possible/relevant, using generic choice IDs.
9. A reward appears as a consequence, not a special treasure subsystem.
10. GM can open source/Advanced detail without the default surface becoming an evidence report.
11. Campaign-specific `ofConks*` code is unnecessary for another real one-shot.
12. GM leaves Play, returns, and is offered Resume of the active Run; ordinary re-entry creates no duplicate Run.

## 16. Non-goals

- Play does not own World Graph writes.
- Play does not own mechanics truth.
- Play does not own source truth.
- Play does not own AppChrome.
- Play is not a generic dashboard.
- Play Object Sheet is not a new universal object ontology.
- Runbook structure does not imply automatic adventure extraction.
- Play does not require a special map system.
- Play does not preserve legacy prep HTML forever.
