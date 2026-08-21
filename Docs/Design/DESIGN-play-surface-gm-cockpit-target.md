---
document_id: dmb-design-play-surface-gm-cockpit-target
title: Play Surface GM Cockpit — Anchoring Design Target
document_class: product_design_anchor
status: approved_target
created_at: "2026-08-20"
updated_at: "2026-08-20"
workstream: PLAY-SURFACE
architecture_authority: "ARCHITECTURE-playable-material-and-runtime.md"
companion_design: "DESIGN-play-surface-projection.md"
image: "assets/play-surface-gm-cockpit-target.webp"
---

# Play Surface GM Cockpit — Anchoring Design Target

This image is the approved **directional UX target** for the DungeonBuddy Play surface.

![Play Surface GM cockpit target](assets/play-surface-gm-cockpit-target.webp)

## Status

The target is intentionally stronger than a mood board and weaker than a wire contract.

It establishes the operator experience we are designing toward:

> **Play is a table-first GM cockpit centered on the current moment. The GM should stay oriented, make decisions, see consequences, reach context and tools quickly, and return to the same table moment without reconstructing context.**

The image is an anchor for hierarchy and interaction design. It is **not** a pixel-perfect implementation specification and does not override the architecture authorities named above.

## What is accepted in this target

### 1. Current moment dominates

The default table projection leads with the current **Beat** as the session-scale objective / pressure / phase.

The current **Scene** is the concrete situation inside that Beat.

The GM should be able to identify both immediately without searching a document tree.

### 2. Decisions are table actions, not buried notes

A meaningful Decision is visible in the working surface with:

- its prompt / meaning;
- authored Options;
- useful immediate consequence framing;
- visible state after a selection;
- a path for that decision to alter which later Scenes / Beats remain relevant.

The target favors **Decision → consequence → changed relevance** over passive branch documentation.

### 3. The main surface is a cockpit, not a document navigator

The table view should answer, with minimal interaction:

- Where are we?
- What matters now?
- What pressure is active?
- What are the players deciding?
- What changes if they choose or resolve this?
- What people, threats, rules, maps, notes, or tools matter right now?

Runbook structure remains available, but it is an alternate structural projection rather than the default table instrument.

### 4. Relevant-now context stays close

A compact supporting region may surface useful current context such as:

- NPC / character references;
- threats;
- resources / clocks;
- quick notes;
- contextual tools.

The exact contents are contextual and should be driven by admitted Playable / World / Mechanics / Runtime references rather than a fixed campaign-specific dashboard schema.

### 5. Detail opens without losing the table moment

NPC, Threat, Notes, Rules, Maps, and similar detail should normally open as an in-context projection / layer / side panel and close back to the exact current moment.

This preserves the existing Play projection thesis:

```text
click / focus something useful
→ use detail or a tool
→ close it
→ return to the exact table moment
```

### 6. Combat is part of the same session instrument

Combat should be reachable as a first-class Play capability without pretending Play owns Combat runtime.

The desired experience is continuity of session context:

```text
current Beat / Scene
→ combat becomes the active working instrument
→ Combat owns durable combat state
→ outcome returns to / informs the Run
```

The exact linked-runtime wire contract remains separate architecture work.

### 7. Resume / Start New is explicit

Entering Play should distinguish:

- Resume active Run;
- Start New Run;
- deliberately choose another existing Run.

Ordinary re-entry must not create duplicate Runs.

### 8. Table flow is short and repeatable

The interaction rhythm illustrated by the target is:

```text
ORIENT
see current Beat / Scene / pressure

→ DECIDE
players act; GM records a meaningful Decision when needed

→ CONSEQUENCE
show / record what becomes true

→ STATE CHANGE
current relevance, resolution, notes, clocks, or linked runtime changes

→ KEEP GOING
return immediately to the useful current moment
```

This loop should work repeatedly during a session without the GM feeling that they are administering project-management software.

## Design principles carried forward

The target visualizes these product constraints:

1. **Current moment is always obvious.**
2. **Beat is the container; Scenes are concrete situations within it.**
3. **Decisions change what is possible / relevant next.**
4. **High-frequency table actions should usually be one or two interactions away.**
5. **Durable state should survive leaving, reloading, and returning.**
6. **Full structure is available without dominating the default table view.**
7. **Supporting tools preserve context rather than forcing navigation reconstruction.**
8. **Readability and table speed outrank decorative density.**

## What is deliberately NOT frozen by the image

Do not treat any of the following visual details as architecture or schema merely because they appear in the target:

- exact colors;
- exact typography;
- icon set;
- spacing values;
- panel dimensions;
- precise navigation labels or ordering;
- the exact membership of the left-side Play capability list;
- the exact membership or density of `At a Glance`;
- the exact mobile composition;
- specific fictional names, numbers, mechanics, or campaign facts shown in the mockup;
- whether every Decision always displays three cards;
- whether every supporting object opens from a side panel;
- any implied database / JSON / Markdown representation;
- any specific Runbook title or example hierarchy shown in the mockup.

The image contains illustrative content. It is not campaign canon and must not be mined as source truth.

## Architecture boundary

Where this target conflicts with current implementation, the conflict is expected evidence, not permission to patch around architecture.

Current architecture already records that the desired Beat-first hierarchy is not structurally compatible with the shipped Scene-first P1/P2 containment model. Before implementing the target structurally, the reviewed redesign must cover:

- Playable structure / serialization;
- manifest membership / versioning;
- current-position semantics;
- Decision / consequence / relevance behavior;
- sealed Run / manifest migration or reconciliation;
- rebase behavior;
- Plan → Playable adoption implications.

The next PLAY-SURFACE design PR owns that contract.

## Success test for future implementation

The target is doing its job when a real-session dogfood can run a representative 20–30 minute sequence and the GM rarely needs to ask either:

> “Where is that?”

or

> “How do I get back to what we were doing?”

That is a product outcome, not a literal click-count SLA.
