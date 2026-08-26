---
document_id: dmb-design-play-surface-gm-cockpit-target
title: Play Surface GM Cockpit — Anchoring Design Target
document_class: product_design_anchor
status: approved_target
version: 1.1
created_at: "2026-08-20"
updated_at: "2026-08-26"
workstream: PLAY-SURFACE
architecture_authority: "ARCHITECTURE-playable-material-and-runtime.md"
companion_design: "DESIGN-play-surface-projection.md"
image: "assets/play-surface-gm-cockpit-target.webp"
evidence:
  - "PR #628 — Beat-first Playable grammar and manifest foundation"
  - "APP-STATE AS2–AS5 — historical Playable revisions, PostgreSQL Runtime/continuity, Play file demolition"
  - "C2S27 native Play dogfood — unexpected-play and fast-mechanics lessons"
---

# Play Surface GM Cockpit — Anchoring Design Target

This image remains the approved **directional UX target** for the DungeonBuddy Play surface.

![Play Surface GM cockpit target](assets/play-surface-gm-cockpit-target.webp)

## Status

The target is intentionally stronger than a mood board and weaker than a wire contract.

It establishes the operator experience we are designing toward:

> **Play is a table-first GM cockpit centered on the current moment. The GM should resume the exact moment they left, understand the active Scene immediately, retain Beat context, make meaningful choices, reach any useful object or mechanics quickly, and return without reconstructing context.**

The image remains the hierarchy and interaction anchor. The 2026-08-26 re-anchor below clarifies how to read that image after BF1 and APP-STATE AS2–AS5. It is **not** a pixel-perfect implementation specification and does not override the architecture authorities named above.

## 2026-08-26 interpretation lock

### 1. Beat-first structure, Scene-centered table projection

The durable Playable hierarchy remains:

```text
Runbook
  → Beat
      → Scene / Decision
```

The **Beat is the context wrapper**: objective, pressure, phase, framing, and the space in which its Scenes make sense.

The **Scene is the primary table workspace** when one is active. On ordinary resume, the first-five-seconds experience is:

```text
open /play
→ resolve the active Run
→ restore the exact last current Beat + Scene
→ central workspace shows that Scene
→ Beat context remains immediately accessible
```

This is a Scene-centered projection over Beat-first structure. It does **not** revive the rejected Scene-first wire grammar.

A Beat with no current Scene remains a truthful supported state; Play shows the Beat context plus its available Scenes rather than silently choosing one.

### 2. Decisions are first-class authored branching

A meaningful Decision is visible in the working surface with:

- its prompt / meaning;
- authored Options;
- useful immediate consequence framing;
- visible selected state;
- authored `activates` / `suppresses` transitions that alter later relevance.

The target favors:

```text
Decision
→ Option selected
→ consequence becomes legible
→ later Beat / Scene relevance changes
```

This branching is real and durable. `A → B` and `A → suppress C` are useful authored prep.

But authored branching is **not a permission graph**. A suppressed Scene or Beat remains inspectable and navigable. Players departing from the expected path must not trap the GM inside the authored branch model.

### 3. The main surface is a cockpit, not a document navigator

The table view should answer, with minimal interaction:

- What Scene are we in?
- What Beat/context are we inside?
- What pressure is active?
- What are the players deciding?
- What changes if they choose or resolve this?
- What useful people, locations, threats, roll tables, notes, rules, maps, or tools are nearby?
- How do I reach something unexpected right now?

The Runbook remains the durable linear authored source and is available as reference. Its document/tree structure is **not** the default runtime navigation instrument.

### 4. `At a Glance` is presence-first

The compact supporting region should first answer **what useful material exists around this moment**, not render mini dossiers.

The initial useful vocabulary is:

- Scenes in the current Beat;
- Locations;
- NPCs / characters;
- Threats;
- Roll tables;
- Notes;
- Combat status / handle when present.

Names, counts, compact status, and direct open actions are preferred. Detail opens through the normal projection path.

The exact contents remain contextual and must come from admitted Playable / World / Mechanics / Runtime references rather than a fixed campaign dashboard schema.

### 5. Inspecting something is not the same as moving the table

Unexpected play is normal. The GM must be able to inspect a Scene under another Beat, an NPC, a location, a Threat, a roll table, or source detail **without changing the durable current moment**.

For Playable Scenes there are two distinct actions:

```text
OPEN / INSPECT
→ show the material
→ do not change currentBeatId / currentSceneId

MAKE CURRENT
→ explicit Runtime mutation
→ set the target Beat + Scene together
```

Opening detail never silently moves the table.

### 6. Fast object and mechanics access is a hot path

C2S27 proved that players may immediately leave the expected plan. Play must therefore support both:

```text
CONTEXTUAL
what the current Beat / Scene already references

GLOBAL / ON-DEMAND
anything useful in the campaign that the GM needs now
```

Known NPCs, locations, threats, and exact mechanics must be reachable independently of where they were authored.

The Threat hot path is especially important:

```text
context or search
→ Threat
→ exact accepted statblock visible
→ Add to Combat
```

This must not require navigating through Plan/Build, finding the parent Runbook Scene, reconstructing JSON, or waiting on generation when exact mechanics already exist.

### 7. Combat is a collapsible working instrument

Combat is part of the same session instrument without becoming Play-owned state.

The desired interaction is:

```text
current Beat context
+ active Scene
→ expand Combat
→ Combat temporarily occupies the central working area
→ Combat owns HP / initiative / conditions / encounter state
→ collapse Combat
→ exact originating Scene is still there
```

Visually Combat may behave like a fully expanded Scene workspace. Architecturally it remains Combat-owned and linked from Play.

### 8. Resume / Start New is explicit

Entering Play distinguishes:

- Resume active Run;
- Start New Run;
- deliberately choose another existing Run.

Ordinary re-entry must not create duplicate Runs. The APP-STATE continuity work means this selection and the exact current Runtime state are PostgreSQL-backed rather than checkout-local Play files.

### 9. Table flow is short and repeatable

The interaction rhythm illustrated by the target is:

```text
ORIENT
see active Scene + Beat context

→ DECIDE
players act; GM records a meaningful authored Choice when applicable

→ CONSEQUENCE
show what the selected Option means

→ RELEVANCE CHANGE
later Beat / Scene emphasis changes without gating navigation

→ REACH CONTEXT
open expected or unexpected objects / mechanics immediately

→ KEEP GOING
return immediately to the useful current moment
```

This loop should work repeatedly during a session without the GM feeling that they are administering project-management software.

## Design principles carried forward

1. **The exact current moment is obvious on entry.**
2. **Beat is the durable container/context; Scene is the normal central table workspace.**
3. **Decisions create meaningful authored branching and relevance changes.**
4. **Branching influences emphasis, not permission to navigate.**
5. **High-frequency table actions should usually be one or two interactions away.**
6. **Unexpected material must be reachable faster than finding where it was authored.**
7. **Durable state survives leaving, reloading, restarting, and worktree changes for the completed Play path.**
8. **Full Runbook structure is reference material, not the default Play instrument.**
9. **Supporting tools preserve context rather than forcing navigation reconstruction.**
10. **Readability and table speed outrank decorative density.**

## What is deliberately NOT frozen by the image

Do not treat any of the following visual details as architecture or schema merely because they appear in the target:

- exact colors;
- exact typography;
- icon set;
- spacing values;
- panel dimensions;
- precise navigation labels or ordering;
- the exact membership of the left-side Play capability list;
- exact counts/density/layout inside `At a Glance`;
- the exact global/on-demand finder interaction;
- the exact mobile composition;
- specific fictional names, numbers, mechanics, or campaign facts shown in the mockup;
- whether every Decision always displays a fixed number of cards;
- whether every supporting object opens from a side panel;
- any implied database / JSON / Markdown representation;
- any specific Runbook title or example hierarchy shown in the mockup.

The image contains illustrative content. It is not campaign canon and must not be mined as source truth.

## Architecture boundary and current implementation truth

The structural redesign required by the original target is no longer hypothetical:

- BF1 / PR #628 implemented the Beat-first v2 grammar, structure index, and v2 manifest foundation.
- APP-STATE AS2 added immutable historical Playable WorkRevisions.
- AS3 moved Play Run / manifest / progress / rebase authority to PostgreSQL.
- AS4 moved active-Run continuity to PostgreSQL.
- AS5 demolished the replaced Play filesystem persistence engine.

The remaining Play Surface work is product/runtime projection work, beginning with BF2 v2 READY/current-position semantics and BF3 cockpit realization. The persistence foundation is not a reason to defer cockpit development.

Notes are intentionally not given a new schema by this target. Product presentation may treat notes as pinned objects associated with the Run/Beat/Scene/originating Play context; durable note identity/storage should be introduced only when a concrete interaction requires more than the existing Runtime note capability.

## Success test for future implementation

The target is doing its job when a real-session dogfood can run a representative 20–30 minute sequence and the GM rarely needs to ask either:

> “Where is that?”

or

> “How do I get back to what we were doing?”

A stronger C2S27-derived success condition is:

> When players depart from the expected path, the GM can inspect another Scene, open an unplanned NPC/Threat, see exact mechanics, add it to Combat, and return to the current Scene quickly enough that DungeonBuddy remains the table instrument rather than being abandoned.

That is a product outcome, not a literal click-count SLA.
