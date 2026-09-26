# PLAN — UI Presentation Substrate Sidequest v1

**Created:** 2026-09-25
**Status:** ACTIVE SIDEQUEST — bounded frontend foundation before broad UI redesign
**Repository:** Drakosfire/DungeonMindBuddy
**Re-anchor:** main@fa01c768 — UI-F1 activation; UI-F0 merged as PR #755 at `fb7437aa763f32cc98cb26b06911558deb41f761`
**Roadmap owner:** Docs/Roadmaps/ROADMAP-campaign-supergraph.md UI design re-entry checkpoint
**Architecture owner:** Docs/Design/ARCHITECTURE-surface-interaction-layer.md
**Visual language:** Docs/Design/ui-language/DESIGN-interaction-layer-language.md
**Canvas authority:** Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md
**CON-READY / PLAY:** independent lane; this sidequest does not change WorldKeeper/DungeonMind semantics or production write authority

> Goal: preserve Buddy's mature interaction/runtime kernel and make presentation
> cheap enough to replace, compare, and iterate without booting the whole product.

---

## 1. Why this sidequest exists

Buddy's frontend maturity is uneven.

The reusable behavioral substrate is strong:

~~~text
SurfaceInteractionPublication + validation
lease-scoped surface identity
singular Tool / Edit / Projection hosts
Peek claim / restore semantics
MarkdownCanvasSession
document command arbitration + admission envelopes
graphReference contracts
World-object view-model boundaries
Play Run / Beat / Scene durable identity
~~~

The presentation substrate is much weaker:

~~~text
semantic design tokens            thin / inconsistent
visual primitive library          thin
controller ↔ presentation split   partial
isolated UI development           weak
canonical fixture showroom        missing
visual regression                 minimal / absent
route-specific CSS                expensive to change
~~~

The product therefore contains more frontend platform maturity than its visual
coherence suggests, while still making visual experimentation too expensive.

This sidequest fixes that mismatch.

---

## 2. Product forcing function

DungeonBuddy must become demoable while preserving the ability to change its
visual language quickly.

The desired development loop is:

~~~text
idea
→ isolated representative fixture
→ visual implementation
→ desktop + narrow comparison
→ optional screenshot check
→ only then product integration
~~~

A normal presentation experiment must not require:

- DungeonMind running;
- APP-STATE/PostgreSQL running;
- a historical ingest run;
- exact campaign/session setup;
- a backend API;
- navigating to one fragile production state.

The target is a frontend layer where design iteration is fast enough to be fun.

---

## 3. Weak-laptop constraint

The development machine is intentionally treated as resource-constrained.

Default choices:

- keep Vite;
- keep React;
- keep Vitest + Testing Library;
- use plain CSS custom properties for tokens;
- use CSS Modules or narrowly scoped CSS for new reusable presentation work;
- prefer static TypeScript fixtures;
- prefer code-split isolated stories;
- visual regression runs explicitly or in CI, not continuously;
- use headless interaction primitives selectively rather than a large styled UI framework.

Do not add a tool merely because it is fashionable.

A sidequest slice fails its ergonomics goal if routine visual editing starts
additional databases, model processes, heavyweight background watchers, or a
large always-on test matrix.

---

## 4. Preservation contract

### Preserve aggressively

These are substrate, not styling:

~~~text
apps/live-control-ui/src/surfaceInteraction/**
  neutral publication contract
  exact identity
  lease semantics
  Tool/Edit/Projection authorization
  stale callback protection

apps/live-control-ui/src/markdownCanvas/**
  MarkdownCanvasSession authority
  admission envelopes
  document command arbitration
  save/conflict/reconciliation semantics

apps/live-control-ui/src/graphReference/**
  exact reference/resolution contracts

World-object projection/view-model DTO boundaries

Peek claim/arbitration/return-to-parent semantics

Play durable Run / Beat / Scene identity and mutation semantics
~~~

### Preserve behavior, not implementation shape

These may be decomposed while retaining existing guarantees:

~~~text
AgentInteractionProvider
ToolHost
EditHost
GraphObjectCard
Agent dock
Scene / Beat rendering
MarkdownCanvas chrome
~~~

### Deliberately disposable

The sidequest should make these cheap to replace:

~~~text
colors
spacing
fonts
panel/card chrome
button styling
drawer appearance
nav treatment
object-sheet arrangement
Scene arrangement
tool arrangement
responsive presentation
paper / chrome / ops paint
icons and restrained motion
~~~

---

## 5. Target layering

New presentation work should converge on:

~~~text
domain / application state
        ↓
view model / interaction model
        ↓
Buddy presentation pattern
        ↓
small UI primitive
        ↓
semantic token
~~~

Forbidden direction:

~~~text
CSS needs campaign authority
visual primitive imports DungeonMind DTO
headless primitive owns SurfaceInteraction lease semantics
presentation component becomes a durable state authority
~~~

---

## 6. Tooling direction

### Tokens

Plain CSS custom properties.

Do not introduce a token compiler in the first pass.

Initial semantic vocabulary should be intentionally small:

~~~text
background:
  app
  chrome
  paper
  ops

text:
  primary
  secondary
  on-paper
  quiet

accent:
  current
  action
  danger

border:
  subtle
  strong

layout:
  reading width
  peek width

spacing / radius / typography:
  small bounded scales
~~~

This is the code-level expression of the existing visual language:

~~~text
dark room chrome
warm paper instrument
dark ops handout
scarce accent
cheap navigation
expensive current work
~~~

### Isolated UI workshop

Preferred first tool: Ladle.

Reason:

- React/Vite native;
- deliberately small;
- code-split stories;
- no backend required;
- lower dev-machine overhead than adopting a broad component-documentation ecosystem.

Storybook remains an available future upgrade if its ecosystem becomes useful
enough to justify the cost. Do not support both.

### Headless accessibility mechanics

Deferred option: Base UI or another focused headless primitive library may be added
later **only when one concrete Buddy presentation pattern needs interaction
mechanics that are costly to implement correctly**.

UI-F1 intentionally adds no headless library. Native elements remain preferred
when they already satisfy the interaction.

Do not replace SurfaceInteraction state machines or Buddy authority with a headless
library, and do not add one speculatively to complete a component checklist.

### Visual regression

Preferred: a small Playwright screenshot suite over canonical isolated fixtures.

It is explicit/on-demand locally and suitable for CI.

Do not generate hundreds of visual snapshots.

---

## 7. New presentation package

Target shape:

~~~text
apps/live-control-ui/src/ui/
  tokens/
  primitives/
  patterns/
  fixtures/
~~~

UI-F1 starts with exactly four primitives:

~~~text
Surface
Button
Badge
Stack
~~~

Additional primitives are earned by a concrete presentation consumer rather than
pre-built as a design-system inventory.

The first product pattern is ObjectSheet in UI-F2. Other patterns such as PeekPane,
SceneSheet, AgentDock, SourceExcerpt, and RelationshipList remain directional
vocabulary only until a later consumer requires them.

This is not a new domain layer.

---

## 8. Slice sequence

~~~text
UI-F0  substrate contract + roadmap                         MERGED — #755
UI-F1  tokens + 4 primitives + Ladle                        ACTIVE IMPLEMENTATION
UI-F2  World-object showroom + ObjectSheet                  QUEUED
UI-F3  ToolHost behavior/presentation split                 QUEUED
UI-F4  <=10-story canonical visual contract                 QUEUED
UI-F5  Canvas layout-engine Page convergence experiment     QUEUED
UI-F6  post-substrate human/steward decision STOP           LATER
~~~

Each slice must be independently useful.

No slice may use "foundation" as permission for a broad frontend rewrite.

---

## 9. UI-F1 — fast presentation foundation

### Mission

Create the minimum reusable presentation layer and isolated workshop.

### Expected scope

- semantic CSS token files;
- small UI primitive directory;
- Ladle configuration;
- a handful of primitive stories;
- no production surface conversion required.

### Acceptance

A developer on the ordinary laptop can:

~~~text
start one lightweight UI command
→ open primitive stories
→ change a token or primitive
→ see the change without backend/DungeonMind/Postgres
~~~

Keep dependencies and startup work bounded.

### Remains false

- no Play redesign;
- no Ingest redesign;
- no Canvas convergence implementation;
- no Tailwind migration;
- no CSS-in-JS runtime;
- no large pre-styled design framework.

---

## 10. UI-F2 — World-object showroom

### Mission

Prove the presentation layer on one real Buddy-shaped contract without live
product state.

The slice creates one ObjectSheet over the existing
`GraphObjectCardViewModel` and exactly the representative pressure needed to
judge the boundary:

~~~text
sparse NPC
rich NPC
Location
Faction
relationship-heavy object
~~~

Full Threat/statblock mechanics remain on their existing mature presentation path.
Production `GraphObjectCard` is not migrated in this slice.

### Exit question

Can we materially restyle/rearrange representative World objects faster in the
isolated lab than by editing the live Ingest/Plan path, **without widening the
existing view-model contract**?

If no, fix the substrate/boundary before broadening it.

---

## 11. UI-F3 — ToolHost behavior/presentation split

### Mission

Prove one mature interaction state machine can keep all of its behavior while its
visual DOM/CSS becomes replaceable.

UI-F3 applies that pattern to **ToolHost only**.

Target:

~~~text
ToolHost
  lease / identity / open-close / async activation / focus
        ↓
ToolHostView
  presentation DOM + ToolHost-specific paint
~~~

Preserve:

- exact surface identity;
- lease invalidation;
- disabled reasons;
- click-time current-tool activation;
- async stale protection;
- Escape/focus behavior;
- Ingest Peek versus legacy drawer placement.

No visual redesign is bundled into the extraction. EditHost, Agent dock, and other
mature hosts remain future candidates only if this proof is cheap and successful.

---

## 12. UI-F4 — canonical visual contract

### Mission

Add a small opt-in screenshot safety net over presentation stories already earned
by UI-F1–F3.

Do **not** build a second demo-fixture system in this slice.

Constraints:

~~~text
Chromium only
workers = 1
explicit/on-demand locally
no Playwright in ordinary npm test
no backend
fixed story IDs
<= 10 committed lossless WebP baselines
~~~

Initial coverage should come from ObjectSheet and ToolHostView pressure states at
desktop/narrow widths.

The suite catches large accidental visual regressions; it is not pixel-policing
every component and not a multi-browser E2E program.

---

## 13. UI-F5 — Canvas layout convergence experiment

Canvas convergence remains important, but the target is now deliberately
**narrower than adopting Canvas presentation**.

Design-time inspection of `Drakosfire/Canvas` found a promising generic
measurement/pagination engine plus application-owned component/data-source
contracts, but its visible `CanvasPage` still carries PHB/statblock-era paint and
the package needs a separately reviewed packaging correction before Buddy can
consume an exact layout-only artifact reproducibly.

Candidate seam:

~~~text
fixed current-schema Buddy TipTap JSON
→ Buddy semantic adapter
→ transient Canvas layout inputs
→ dungeonmind-canvas/layout:
     CanvasLayoutProvider
     useCanvasLayout
     MeasurementPortal
→ LayoutPlan
→ Buddy-owned PageProjection
~~~

The same Buddy block renderer must feed offscreen measurement and visible page
rendering.

The representative fixture preserves real Buddy semantics:

- ordinary prose/headings;
- standard TipTap table structure;
- `callout` kind/label/content;
- inline `graphNodeReference` exact `nodeId` + label;
- Playable v2 Beat/Scene/Choice/Option identity metadata.

Do not use Canvas `PageDocument`, `buildPageDocument()`, generated time/random
IDs, `CanvasPage` visible DOM, root/map imports, or an alternate save path.

The experiment records one terminal verdict:

~~~text
YES
NARROWER
NO
~~~

A NO is a valid result; do not rescue convergence with more glue inside the same
slice.

---

## 14. UI-F6 — post-substrate decision STOP

UI-F6 is **not an implementation slice**.

After F1–F5 are accepted, run one bounded demo-oriented human/steward pass using
both the isolated workshop and current merged product.

The STOP may select at most one next outcome:

~~~text
one bounded UI successor
one bounded substrate correction
one bounded reconnaissance
RESUME_NON_UI
~~~

Candidates are re-derived from evidence; there is no preselected Play redesign,
ObjectSheet rollout, shell rewrite, or Canvas production adoption.

If UI is no longer the highest-value blocker to a credible demo, return to
CON-READY PLAY or other product capability work rather than polishing by momentum.

---

## 14. Demo relationship

This sidequest is explicitly in service of demo readiness.

It should improve both:

1. speed of reaching a good design; and
2. confidence that visual iteration does not break mature interaction semantics.

Use the existing language as evidence:

- cheap chrome / expensive current work;
- chip → glance → Peek;
- table-first object presentation;
- dark room chrome;
- warm paper instruments;
- dark ops handouts.

Do not freeze current pixels merely because they are demoable.

The demo should consume the new substrate incrementally; it does not wait for the
entire frontend to be migrated.

---

## 15. Parallel-work boundary

This UI sidequest may run in parallel with CON-READY PLAY when write leases are
disjoint.

It must not:

- change WorldKeeper contracts;
- change DungeonMind contracts;
- switch World write authority;
- implement source→World semantics;
- redefine APP-STATE ownership;
- absorb PLAY-1;
- use frontend refactoring to bypass governed domain APIs.

Coordinate before merging changes to shared files such as:

~~~text
App.tsx
AppChrome.tsx
AgentInteractionProvider.tsx
surfaceInteraction/**
markdownCanvas/**
graphReference/**
~~~

---

## 16. Performance rules

For ordinary development on the target laptop:

- UI lab must run with backend services off;
- static stories are the default;
- no provider/model network calls in stories;
- no live Postgres/DungeonMind fixtures;
- no always-on screenshot watcher;
- no duplicate component-workshop stacks;
- new headless primitives must be imported selectively;
- production bundle changes are measured when dependency-bearing slices land;
- avoid animations/effects that make low-power rendering visibly worse;
- preserve Vite incremental development.

If a proposed UI tool materially slows normal edit/refresh, replace the tool rather
than normalizing the cost.

---

## 17. Exit criteria

The sidequest is complete when all are true:

1. Buddy has semantic presentation tokens.
2. Buddy has a small reusable primitive/pattern layer.
3. An isolated UI workshop runs without backend services.
4. Representative World-object and ToolHost presentation states can be iterated from static fixtures.
5. At least one mature production component has behavior separated from presentation without regression.
6. A small bounded canonical visual-regression suite exists.
7. The Canvas layout-convergence experiment has a recorded YES / NO / NARROWER result.
8. A developer can prototype a materially different presentation without touching domain/runtime authority.
9. A human/steward STOP selects at most one successor — or explicitly resumes non-UI work — from actual product/showroom evidence.

Exit does not require migrating every existing component.

---

## 18. Current state

~~~text
mature SurfaceInteraction kernel             PRESERVE
mature MarkdownCanvasSession authority       PRESERVE
mature graphReference/view-model seams       PRESERVE
UI language                                  GOOD DESIGN EVIDENCE
UI-01..UI-05                                 MERGED / useful interaction grammar

UI presentation substrate                   ACTIVE SIDEQUEST
UI-F0                                        MERGED — #755
UI-F1                                        ACTIVE — handoff activated at fa01c768
Canvas convergence                           MOVED TO UI-F5
broad UI redesign                            HELD
CON-READY PLAY                               INDEPENDENT / MAY RUN IN PARALLEL
~~~
