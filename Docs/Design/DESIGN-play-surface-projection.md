---
document_id: dmb-design-play-surface-projection
title: Play Surface and Table Projections
document_class: product_design
status: active
version: 1.2
created_at: "2026-08-15"
updated_at: "2026-08-26"
workstream: PLAY-SURFACE
architecture_authority: "ARCHITECTURE-playable-material-and-runtime.md"
surface_authority: "ARCHITECTURE-surface-interaction-layer.md"
companion_designs:
  current_moment_cockpit: "DESIGN-play-current-moment-cockpit.md"
  approved_target: "DESIGN-play-surface-gm-cockpit-target.md"
evidence:
  - "PR #578 — Of Conks / Hempholm table-ready dogfood"
  - "C2S27 native Play dogfood — unexpected-play and fast-mechanics evidence"
  - "PR #628 — Beat-first v2 foundation"
  - "APP-STATE AS2–AS5 — durable historical Playable + Runtime continuity"
supersedes_direction_from:
  - "DESIGN-play-mode-runbook-product-direction.md"
  - "../Plans/DESIGN-session-runbook-command-surface.md"
---

# Play Surface and Table Projections

## 0. Product thesis

**Play is the surface for the next few minutes at the table.**

Plan may expose preparation machinery. Build may expose durable world construction. Play must prioritize continuity of attention.

The central contract remains:

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

The 2026-08-26 re-anchor adds one stronger C2S27 rule:

> **Anything useful in the campaign must be reachable faster than finding where it was authored.**

---

## 1. Relationship to shared surface architecture

`ARCHITECTURE-surface-interaction-layer.md` remains authority for AppChrome, shared Nav/Agent/Projection/Tool/Edit hosts, Canvas host, and surface publication.

Play is a surface-domain publisher. It may publish:

- active Run + current Beat/Scene context;
- graph/source/playable/mechanics reference resolution;
- Play capability launchers;
- table-specific projection renderers;
- current Canvas/work-object context where editing is admitted.

Play does not own shared bars or a second projection host.

---

## 2. Play shell

The Play capability family remains conceptually:

```text
Play
├── current moment
├── Combat
├── Roll
├── Items / Mechanics / Statblocks
├── object projections
└── global / on-demand finder
```

This is a capability family, not a requirement that every item be a permanent tab.

The permanent surface is native product UI. Legacy injected prep HTML/global scripts remain migration history, not the target substrate.

---

## 3. Default anchor: active Scene inside Beat context

The durable hierarchy is Beat-first:

```text
Runbook
  → Beat
      → Scene / Decision
```

The table projection is Scene-centered:

```text
Run identity
Beat context wrapper              ← objective / pressure / phase; always accessible
Active Scene                      ← primary central workspace when present
  ├── in-context Decisions
  ├── immediate playable material
  └── references / tools
At a Glance                       ← presence inventory
```

The GM should immediately be able to answer:

- What Scene are we in?
- What Beat/context are we inside?
- What pressure matters?
- What are they deciding?
- What did the last choice change?
- What people/locations/threats/tables/notes are around this moment?
- How do I reach something the Runbook did not predict?

### 3.1 Beat context wrapper

Beat is session-scale context, not the dominant board when a Scene is active.

The projection should keep immediately accessible:

- Beat title;
- objective / pressure / phase;
- useful summary / At the Table framing;
- resolved state and relevance emphasis;
- available Scenes;
- Beat-level Decisions/references where applicable.

Beat detail may expand without pushing the GM into document navigation.

### 3.2 Active Scene board

When `currentSceneId` exists, the Scene owns the central working space.

A Scene projection may show:

- title and situation framing;
- At the Table / Read Aloud / GM Note / Rules Now / Warning blocks;
- in-context Decisions;
- contextual references/actions;
- pinned notes;
- current pressure/clock definitions when authored.

When no Scene is current, the central board truthfully shows the Beat and available Scenes rather than auto-selecting one.

### 3.3 Beat/Scene navigation

Durable current position changes only through explicit Runtime actions.

The surface distinguishes:

```text
OPEN / INSPECT
→ show target material
→ preserve current Beat/Scene

MAKE CURRENT
→ explicit Runtime mutation
→ target Scene and its Beat become current
```

Previous/next or direct Beat/Scene actions may exist, but relevance never gates access.

---

## 4. Decisions and authored branch projection

Within the current context, Decisions are authored branch points with stable Options.

Expected interaction:

```text
Decision prompt
  Option A
    consequence
    activates / suppresses
  Option B
    consequence
    activates / suppresses

select Option
→ persist choiceId → optionId
→ show consequence
→ re-derive emphasis
→ do not auto-navigate
```

`activates` / `suppresses` are **branch relevance**, not permission.

Use language such as:

- now relevant / emphasized;
- less relevant / de-emphasized;
- consequence;
- selected.

Avoid implying that a de-emphasized Scene has become impossible or inaccessible.

Unexpected play remains legal even when no authored Option matches what the players did.

---

## 5. Beat / Scene presentation vocabulary

Playable semantic blocks remain flexible table-use labels, not World ontology.

### At the table

Primary GM-facing framing.

### Read aloud

Player-facing text intended to be spoken or paraphrased.

### GM note

Private framing, motivation, interpretation, or operational reminder.

### Rules now

Rules/mechanics useful in the moment. When exact mechanics authority exists, reference/hydrate it rather than copying a second mechanics truth.

### Warning

Hazards, sequencing traps, spoiler boundaries, or operational reminders.

### Consequence

Authored outcome framing. Useful presentation labels may include success/failure/wait/choice/reward/cost/state/relationship/access/information. They remain views over the canonical consequence concept.

### Open now / relevant objects

Typed object/source/mechanics references useful in the current Beat/Scene.

### Tools

Explicit contextual actions such as:

- Add to Combat;
- Open Roll table;
- Open exact mechanics;
- Open source;
- Ask Agent/Hermes.

Tool links are capability/projection data, not Runbook truth.

---

## 6. `At a Glance` — presence-first context inventory

`At a Glance` is **not** a dashboard of miniature object sheets.

Its first job is to tell the GM what useful material is present around the current Beat/Scene.

Initial useful categories:

```text
Scenes
Locations
NPCs / characters
Threats
Roll tables
Notes
Combat
```

Prefer names, counts, compact status, and immediate open actions.

Example:

```text
Scenes       The Breach Line · The Courtyard · The Tunnels
Locations    2
NPCs         4
Threats      3
Roll Tables  1
Notes        2
Combat       collapsed
```

The current Beat and Scene's authored references seed the region. Small Runtime state may contribute. Exact mechanics bindings make Threat entries directly useful.

The region is curated and contextual, not exhaustive campaign adjacency.

---

## 7. Global / on-demand finder

C2S27 proved contextual references are insufficient by themselves.

Play needs a complementary access path for material that was **not** predicted by the current Runbook context.

The exact UI is not frozen. It may be search, command palette, Agent-assisted lookup, or another shared interaction.

The invariant is:

```text
known campaign object
→ find/open from Play
→ no Plan/Build detour
→ current moment preserved
```

The finder should reach at least:

- NPCs;
- locations;
- threats / creatures;
- exact mechanics/statblocks;
- roll tables;
- Playable Scenes/Beats;
- source documents where useful.

Opening a found object is inspection. A found Scene changes Runtime only through explicit Make Current.

---

## 8. Play Object Sheets

A Play Object Sheet is the table-first projection of a known object. It is not a stored duplicate object and should not begin with graph internals.

### 8.1 Common hierarchy

1. identity and compact role/type;
2. table-useful Playable interpretation;
3. current relevant relationships;
4. exact mechanics/actions when applicable;
5. source/provenance;
6. Advanced graph/evidence detail.

### 8.2 NPC projection

Useful sections may include:

- At the table;
- attitude / offers / hooks when Playable material provides them;
- rules now;
- connected now;
- source.

These labels do not imply universal durable NPC fields.

### 8.3 Location projection

Useful labels may include:

- arrival;
- what's happening;
- who's here / what can happen;
- rules now;
- connected now;
- map / source.

### 8.4 Item projection

Useful labels may include:

- what it does;
- who wants it / pressure;
- hooks;
- rules now;
- connected now;
- source / exact mechanics.

### 8.5 Threat projection — hot path

Threats use the established exact mechanics path.

The Play projection should expose:

- table summary;
- exact accepted mechanics;
- tactics/prepared intent where available;
- relevant relationships/source;
- **Add to Combat**.

The critical interaction is:

```text
context or finder
→ Threat
→ exact StatblockRevision visible and usable
→ Add to Combat
```

No campaign-specific threat→draft dictionary is allowed in the permanent path.

No generation step is required when exact accepted mechanics already exist.

---

## 9. References are handles, not copied truth

Typed references preserve exact durable identity while Play chooses the useful projection.

Examples:

```text
dmb-node:...
source artifact / anchor
statblock revision / threat binding
playable element ref
combat/run handle
```

Primary open should normally preserve Play position. Secondary explicit actions may Make Current, Add to Combat, or navigate deeper.

Opening a reference never mutates Runtime or canon merely because it was opened.

---

## 10. Mechanics and Combat

### 10.1 Prepared threat

```text
Beat / Scene
→ Threat reference
→ Threat Sheet
→ exact StatblockRevision
→ Add to Combat
```

### 10.2 Unexpected fight

Play must let the GM find a known NPC/threat, see exact mechanics, and add it to Combat without reconstructing JSON or hunting for the authoring location.

When exact mechanics are absent, Play says so truthfully and offers the best admitted path; it never fabricates a mechanics binding.

### 10.3 Combat workspace

Combat is collapsed until needed.

When expanded, Combat may occupy the same central working region normally occupied by the Scene:

```text
Beat context retained
Scene origin retained
Combat expanded → central instrument
Combat collapsed → exact Scene restored
```

This is presentation composition only. Combat continues to own combatant state, HP, initiative, conditions, and encounter persistence.

Quantity/team controls for Add to Combat should be table-useful without requiring an authoring workflow.

---

## 11. Run state and continuity

Play projects Runtime from the active PostgreSQL-backed Run:

- current Beat;
- current Scene when set;
- resolved Beats;
- selected authored Decisions;
- notes;
- linked Combat handle/status when present.

APP-STATE AS2–AS5 established:

- historical Playable WorkRevision availability;
- PostgreSQL Run + sealed manifest;
- PostgreSQL progress CAS/rebase;
- PostgreSQL active-Run selection;
- operation without legacy `out/runtime/play` persistence.

A reopened Play surface therefore restores the exact useful table position from durable Run state rather than browser/worktree-local Play files.

Resume vs Start New remains explicit.

---

## 12. Notes

Notes are notes. Play should present them as small context objects pinned to where they originated.

Useful anchors include Run, Beat, Scene, or another addressable Play element.

Do not infer a new persistence schema from this presentation requirement. The existing Runtime note capability remains valid until dogfood proves a need for independent note identity, multiple notes per anchor, timestamps, move/re-pin, or another concrete lifecycle.

---

## 13. Runbook/source reference

The Runbook is the linear durable authored source from which Play derives its projection.

It remains available as exact read-only reference when the GM wants to inspect instructions or structure.

It is **not** the default Play navigation model and should not compete with the Scene-centered cockpit for permanent real estate.

---

## 14. Maps, media, source, and Advanced

When source/asset data provides a map or image, a Play Object Sheet or current context may project it through shared asset/reference authority.

Source detail should normally expose a human-readable source label, useful excerpt where admitted, and Read Source action.

Advanced detail may contain full graph relationships, evidence/provenance, internal IDs, or support state, but these should not dominate table presentation.

---

## 15. Editing and Agent interaction in Play

Narrow in-context editing may eventually use the normal Canvas/document authority:

```text
unlock / edit admitted Playable material
→ Canvas dirty
→ ordinary Save / WorkRevision
→ remain at same table moment
```

Play gains no second save system.

Agent/Hermes receives current table context as pointers/lenses: active Run, current Beat/Scene, relevant references, exact Playable revision, optional Combat handle.

Agent may answer, navigate/open projections, and propose Playable changes. It may not silently mutate Playable or World authority.

The global/on-demand finder and statblock hot path must **not** wait for Agent Surface implementation.

---

## 16. Degradation behavior

- object exists but no Playable interpretation → show World/source-backed object sheet;
- Threat exists but no exact mechanics → show truthful mechanics-unavailable state;
- map asset unavailable → object sheet remains useful;
- current Beat has no current Scene → show Beat context + Scene choices, do not invent one;
- contextual `At a Glance` is empty → offer available Scenes/global finder, not filler;
- linked Combat unavailable → preserve Scene/Beat context and truthful Combat-unavailable state.

Integrity failures in the active Run remain fail-closed.

---

## 17. Acceptance stories

A conforming near-term Play surface should prove:

1. Resume opens the exact last current Beat/Scene; the active Scene is visible within the first few seconds.
2. Beat context is immediately accessible without dominating the Scene board.
3. A Beat-only state is truthful when no Scene is selected.
4. GM opens another Scene under another Beat for inspection without changing current position.
5. GM explicitly Makes that Scene Current and Beat+Scene update together.
6. GM sees in-context Decisions, selects an authored Option, sees its consequence, and sees downstream emphasis change without automatic navigation.
7. A suppressed/de-emphasized Scene remains inspectable and can still be made current.
8. `At a Glance` exposes the presence of Scenes, locations, NPCs, threats, roll tables, notes, and Combat without rendering every detail inline.
9. GM opens an NPC/location/item and receives a table-useful sheet without losing the current Scene.
10. GM finds an unplanned known Threat from the global/on-demand path, sees exact mechanics promptly, and does not navigate through Plan/Build.
11. GM adds that Threat to Combat.
12. Combat expands as the central working instrument, then collapses back to the exact Scene.
13. GM records a note associated with current context without altering Runbook prose.
14. Runbook remains available as exact linear reference but is not required for normal runtime navigation.
15. Campaign-specific `ofConks*`/Mireward bridge code is unnecessary for another real session.

---

## 18. Non-goals

- Play does not own World Graph writes.
- Play does not own mechanics truth.
- Play does not own source truth.
- Play does not own Combat runtime.
- Play does not own AppChrome.
- Play is not a generic dashboard.
- Play Object Sheet is not a universal object ontology.
- Authored Choice transitions do not become permission gates.
- Runbook structure does not become the primary runtime navigator.
- A new note table is not implied by note presentation.
- Global/on-demand retrieval does not require Agent Surface first.
- Play does not preserve legacy prep HTML forever.
