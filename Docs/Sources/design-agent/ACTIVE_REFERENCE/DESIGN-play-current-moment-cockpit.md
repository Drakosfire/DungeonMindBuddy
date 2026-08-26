---
document_id: dmb-design-play-current-moment-cockpit
title: Play Current-Moment Cockpit — Interaction and State Contract
document_class: product_design
status: active
version: 1.1
created_at: "2026-08-21"
updated_at: "2026-08-26"
workstream: PLAY-SURFACE
architecture_authority: "ARCHITECTURE-playable-material-and-runtime.md"
companion_designs:
  play_projection: "DESIGN-play-surface-projection.md"
  authoring_adoption: "DESIGN-playable-authoring-and-adoption.md"
  approved_target: "DESIGN-play-surface-gm-cockpit-target.md"
evidence:
  - "PR #626 — Lane A2 readability + active-Run dogfood"
  - "PR #627 — reviewed current-moment cockpit design gate"
  - "PR #628 — BF1 Beat-first Playable grammar and manifest foundation"
  - "APP-STATE AS2–AS5 — historical Playable revisions, PostgreSQL Runtime/continuity, Play persistence demolition"
  - "C2S27 native Play dogfood — unexpected-play, statblock, and Combat workflow evidence"
---

# Play Current-Moment Cockpit — Interaction and State Contract

## 0. Purpose and boundary

This document turns the approved GM cockpit target into implementation-ready Play semantics.

The 2026-08-26 revision keeps the durable Beat-first model and the BF1 wire/manifest contract, while sharpening the table interaction after the Play persistence program completed and after re-reading the C2S27 failure as an **unexpected-play and retrieval problem**, not merely a hierarchy problem.

The key product statement is:

> **Beat is the durable context container. Scene is the normal central table workspace. Authored Choices create real branching and relevance changes, but authored structure never restricts what the GM may inspect or make current.**

This document freezes:

1. Beat-first Playable containment;
2. the BF1 v2 grammar and v2 manifest contract;
3. Runtime current-position semantics;
4. Decision / Option / consequence / relevance behavior;
5. inspect versus Make Current behavior;
6. Scene-centered cockpit hierarchy;
7. `At a Glance` presence-first behavior;
8. fast object/mechanics retrieval as a table hot path;
9. Combat expansion/collapse semantics while keeping Combat-owned state;
10. historical Run/revision and rebase posture after APP-STATE;
11. Plan→Playable composition.

It deliberately does **not** freeze pixel geometry, visual styling, a note database schema, a condition-expression DSL, or a universal object dashboard.

---

## 1. Canonical Playable containment remains Beat-first

The durable model is unchanged from the reviewed BF1 contract:

```text
Runbook (Playable Artifact)
  → ordered Beats

Beat
  → kind: spine | optional | interrupt
  → objective / pressure / phase / context
  → semantic blocks
  → ordered Scenes
  → ordered Decisions
  → Beat-level consequences
  → typed references / contextual tools

Scene
  → concrete playable situation inside exactly one Beat
  → semantic blocks
  → typed references

Decision (durable wire kind: choice)
  → prompt / meaning
  → ordered Options

Option
  → label
  → authored consequences
  → activates / suppresses later Beats or Scenes
```

### 1.1 Beat is context, Scene is workspace

Containment and presentation are intentionally different concerns.

- **Beat** is the larger context: why this portion of play exists, its objective/pressure/phase, and the collection of Scenes/Decisions/references that belong to it.
- **Scene** is the concrete table situation and is therefore the normal dominant central board when `currentSceneId` exists.
- A Beat with no current Scene is valid. In that state the central board shows Beat context and available Scenes without fabricating a current Scene.

Calling the cockpit Scene-centered does **not** reintroduce the rejected Scene-first grammar. The durable hierarchy stays Runbook→Beat→Scene/Decision.

### 1.2 Durable identity

Stable identity remains independent of headings/titles:

```text
beat:<slug>      Beat
scene:<slug>     Scene
choice:<slug>    Decision
option:<slug>    Option
```

`Decision` is product language; `choice` remains the durable element/wire kind.

---

## 2. BF1 v2 Playable grammar is retained

BF1 / PR #628 implemented the structural foundation. This design revision does not reopen it.

```text
<!-- dmb-playable-element:v2 kind=beat id=beat:<slug> [beat_kind=spine|optional|interrupt] -->
## <Beat title>

<!-- dmb-playable-element:v2 kind=scene id=scene:<slug> -->
### <Scene title>

<!-- dmb-playable-element:v2 kind=choice id=choice:<slug> [scene=scene:<slug>] -->
### <Decision prompt>

<!-- dmb-playable-element:v2 kind=option id=option:<slug>
     activates=beat:<slug>,scene:<slug>
     suppresses=beat:<slug> -->
- <Option label>
```

Rules retained:

- Beat is H2.
- Scene and Decision are Beat-owned H3 siblings distinguished by directive kind.
- A Decision may have an optional same-Beat Scene association for projection.
- Option is a marked list item inside the Decision.
- Mixed v1/v2 structural directives fail closed.
- duplicate IDs, orphan containment, bad associations, unknown transition targets, malformed directives, and unknown grammar versions fail closed.
- fenced-code interiors remain literal.
- ordinary unmarked prose/headings remain non-semantic content.

### 2.1 Transition vocabulary

The first transition vocabulary remains intentionally small:

```text
activates
suppresses
```

No boolean expression language, event bus, arbitrary reducer, or workflow DSL is introduced.

---

## 3. Run manifest and historical Playable revision truth

A Run seals `dmb_play_run_reference_manifest_v2` for its exact Playable WorkRevision.

The v2 manifest retains:

```text
run_id
playable_artifact_id
playable_revision
playable_content_sha256
sealed_at
beats[]
scenes[]      # each with parent beat
choices[]     # each with parent beat, optional scene association
options[]     # each with parent choice
edges[]       # option + activate/suppress + target
```

The manifest is identity/membership/parentage/transition integrity, not a copied Runbook. Titles, prose, semantic blocks, and durable document order come from the exact pinned WorkRevision bytes.

### 3.1 APP-STATE correction

The original v1.0 design predated APP-STATE AS2 and incorrectly assumed Play could only read the current workspace revision.

Current authority is:

- committed Runbook WorkRevisions are immutable historical revisions in PostgreSQL;
- a Run pins exact `work_object_id + revision_n + work_revision_id + content_sha256`;
- revision N remains loadable after N+1 exists;
- replay/admission reads the exact pinned revision, never “latest” and never a filesystem approximation.

This removes the old requirement that a Run become `rebase_required` merely because the Runbook has a newer committed revision. Rebase is an **explicit operator action to move the Run**, not a requirement for continuing to read its historical pinned material.

---

## 4. Runtime current-position semantics

Conceptual Run state remains:

```text
Run
  runId
  playableArtifactId
  playableRevisionId
  currentBeatId            # required once a v2 Run is READY
  currentSceneId?          # optional; must belong to currentBeatId
  resolvedBeatIds[]
  selections: { choiceId: optionId }
  notesByElementId          # existing persistence capability; see §8
  linkedCombatRuntime?      # Combat-owned handle, exact wire still separate work
  updatedAt
```

The persisted implementation is PostgreSQL-backed after APP-STATE AS3/AS4; the conceptual contract remains Play-owned.

### 4.1 New Run seeding

BF2 owns opening v2 READY admission.

For a newly admitted v2 Run:

- `currentBeatId` is seeded durably to the first `spine` Beat in document order;
- when there is no `spine`, seed the first Beat in document order;
- zero Beats is not runnable;
- `currentSceneId` is **not** inferred automatically.

### 4.2 Resume

For an existing active Run, Play restores the exact persisted current moment:

```text
currentBeatId
currentSceneId (when present)
runRevision
resolvedBeatIds
selections
notes/runtime context
```

The first-five-seconds target assumes ordinary resume: the GM sees the last active Scene immediately when one exists, with Beat context accessible around it.

### 4.3 Position mutation

- Setting a Scene also names its Beat; Make Current should set Beat + Scene together as one intentional Runtime update.
- Setting a Beat without a Scene clears the old `currentSceneId` rather than silently choosing a new Scene.
- A current resolved Beat is legal; resolution is outcome state, not navigation.
- Relevance never removes an element from explicit navigation.

---

## 5. Decisions, Options, consequences, and branching

This remains a first-class Play interaction:

```text
Decision
→ Option selected
→ authored consequence visible
→ authored branch/relevance edges applied
→ later material changes emphasis
```

Four states remain distinct:

1. **Authored intent** — Option label, consequence, `activates` / `suppresses` edges in the pinned Playable revision.
2. **Runtime selection** — `selections[choiceId] = optionId`.
3. **What actually happened** — explicit notes, Beat resolution, Combat outcome, or later deliberate World/Playable adoption; not inferred automatically from selection.
4. **Projection relevance** — derived from sealed edges + current selections.

### 5.1 Relevance is derived, never persisted

For each Beat/Scene:

```text
emphasized
  referenced by activates from at least one selected Option

de-emphasized
  referenced by suppresses from at least one selected Option
  and not also activated

default
  otherwise
```

Resolved state remains orthogonal.

### 5.2 Branching is not permission

This is the explicit C2S27 correction:

> **`activates` / `suppresses` describe authored branch relevance. They do not grant or revoke permission to inspect or navigate.**

So all of these are legal:

```text
A → activates B
A → suppresses C
GM still inspects C
GM may explicitly Make Current C later
```

The system should communicate “more relevant / less relevant” rather than “possible / impossible” unless a future explicit product concept genuinely owns impossibility.

### 5.3 Unexpected player choice

The normal product path remains authored Options. The system does not need a parallel freeform Option ontology in BF2/BF3.

If players do something not represented by the authored Options:

- the GM does not have to lie by selecting an incorrect Option;
- the Decision may remain unselected;
- the GM may navigate/inspect anywhere;
- a note may record what actually happened;
- later authoring/Agent work may propose adding a new Option through the normal Playable revision path.

### 5.4 Decision focus

There is no durable `currentDecisionId`.

All Decisions in the current context remain visible/operable. A locally focused Decision may be visually dominant, but focus is ephemeral and never authority.

---

## 6. Inspect versus Make Current

C2S27 proved that the authored hierarchy cannot become the GM's access-control hierarchy.

Play therefore distinguishes:

### OPEN / INSPECT

```text
open Beat / Scene / NPC / Location / Threat / Table / Source
→ show projection
→ do not mutate currentBeatId/currentSceneId
→ close returns to exact current moment
```

### MAKE CURRENT

For a Playable Scene:

```text
explicit Make Current
→ Runtime CAS
→ currentBeatId = target parent Beat
→ currentSceneId = target Scene
```

No ordinary click silently changes Runtime position.

This enables the normal unexpected-play pattern:

```text
Scene A1 is current
→ inspect Scene C2 under Beat C
→ open an NPC referenced there
→ open exact Threat mechanics
→ optionally Add to Combat
→ either close back to A1
   or explicitly Make Current C2
```

---

## 7. Cockpit interaction states

The approved target image remains the visual anchor; these are semantic states rather than screen templates.

### State 1 — Resume / choose / start

Dominant: explicit Resume active Run, Start New Run, or choose another existing Run.

Ordinary re-entry creates no Run. Resume uses the PostgreSQL active selection and restores exact Runtime state.

### State 2 — Scene-centered READY cockpit

When `currentSceneId` exists:

- **dominant central board:** current Scene;
- **persistent accessible context:** current Beat title/objective/pressure/phase;
- **support:** Choices in context, `At a Glance`, notes, tools;
- **orientation:** Run identity + Beat + Scene are always recoverable without document navigation.

### State 3 — Beat-only READY cockpit

When no Scene is current:

- dominant: Beat context;
- available Scenes are easy to see/open;
- no Scene is fabricated;
- explicit Make Current selects a Scene.

### State 4 — Decision interaction

A focused Decision shows prompt, Options, current selection, and immediate consequence framing. Selecting/changing/clearing an Option is one Runtime CAS mutation and re-derives relevance.

### State 5 — Decision consequence / changed relevance

The selected Option's consequence is legible and the changed Beat/Scene emphasis is visible. Nothing auto-navigates.

### State 6 — Context projection open

NPC/Location/Threat/Rule/Note/Map/Source/another Scene opens in-context. Opening is read/projection only unless an explicit action inside performs a separate mutation.

### State 7 — Combat expanded

Combat temporarily occupies the central working area while Beat + originating Scene context remains retained. Combat remains Combat-owned. Collapsing returns to the exact Scene.

### State 8 — Runbook/source reference

The full Runbook remains available as the exact linear authored document, but it is a reference/escape-hatch projection rather than a peer primary table mode.

### State 9 — Warning / incomplete / integrity state

Incomplete Run, blocked admission, integrity failure, or rebase blocker is truthful and fail-closed. Warnings never overwrite or fabricate current context.

---

## 8. Notes

Notes are intentionally simple table records.

Product presentation should treat a note as something that can be **pinned to the context where it originated**:

- Run;
- Beat;
- Scene;
- another addressable Play element when useful;
- later, a Combat-origin handle if the owning Combat contract supports it.

The existing Runtime `notesByElementId` capability remains valid and must not be discarded merely for architectural neatness.

This design does **not** freeze a new `RunNote` table/schema. Independent note identity, multiple notes per anchor, timestamps, move/re-pin, or richer note lifecycle should be added only when a concrete BF3/dogfood interaction needs them.

---

## 9. `At a Glance` — presence-first context inventory

`At a Glance` is a projection contract, not a universal dashboard schema.

Its first job is:

> **Tell the GM what useful material exists around this Beat/Scene.**

Initial useful categories:

```text
Scenes
Locations
NPCs / characters
Threats
Roll tables
Notes
Combat status / handle
```

Presentation should generally favor:

- names;
- counts;
- compact status;
- immediate open actions.

It should not render full NPC sheets/statblocks/table contents inline by default.

### 9.1 Seeding

The current Beat and Scene's authored references seed the region. Small Runtime status may contribute. Mechanics bindings make Threat entries directly actionable.

### 9.2 Not exhaustive

`At a Glance` is contextual. It is not the global campaign index.

The cockpit also needs a global/on-demand finder (§10) so unexpected play does not depend on whether the author predicted a reference.

### 9.3 Empty state

An empty contextual inventory is truthful. It should offer the global/on-demand path or available Scenes, not filler and not a forced jump to the full Runbook.

---

## 10. Global/on-demand retrieval and exact mechanics hot path

The cockpit has two complementary access modes:

```text
CONTEXTUAL
material referenced by the current Beat / Scene

GLOBAL / ON-DEMAND
campaign material the GM needs unexpectedly
```

The global/on-demand interaction may become search, command palette, Agent-assisted lookup, or another shared surface primitive. Exact UI is not frozen here.

The invariant is:

> **Useful campaign material must be reachable faster than finding where it was authored.**

### 10.1 Threat/statblock path

The high-priority path is:

```text
context or finder
→ Threat / known creature
→ exact accepted StatblockRevision immediately useful
→ Add to Combat
```

No Plan/Build detour, Runbook-tree hunt, campaign-specific bridge, JSON reconstruction, or regeneration is required when exact mechanics already exist.

Implementation work should capture interaction/latency evidence. No numeric SLA is frozen yet; visible table-breaking delay is a dogfood failure.

---

## 11. Combat workspace contract

Combat remains a separate authority.

Play may hold a linked Combat handle and project the Combat instrument in the central workspace.

```text
collapsed
  Scene remains central

expanded
  Combat becomes central working instrument
  origin Beat/Scene remain retained

collapse
  return to exact origin Scene
```

Play never absorbs HP, initiative, conditions, combatant mutation, or encounter persistence.

Adding a Threat to Combat is an explicit cross-domain action from a Threat/statblock projection.

---

## 12. Plan → Playable authoring

The settled rule remains:

> **Plan authors/adopts the exact Playable work object. There is no lossy derivative export.**

Plan edits the same admitted versioned Runbook content that Play later projects.

The linear Runbook document is important authoring truth:

- Beat/Scene/Decision/Option identity is explicit;
- instructions and ordinary prose remain readable;
- Choices and consequences are visible during prep;
- transition edges are visible/editable;
- typed references are preserved.

But the linear document structure is **not** the runtime UI model. Play consumes it into the current-moment projection.

---

## 13. Existing Runs, migration, and rebase

### 13.1 Historical read posture

A Run remains readable/runnable against its exact historical pinned WorkRevision after newer revisions exist.

No current-revision fallback is needed or allowed.

### 13.2 v1 versus v2

- v1 Playable revisions remain v1.
- explicit Beat-first adoption creates a new v2 committed revision; it never rewrites history in place.
- a v1 Run remains bound to its exact historical v1 revision and may continue under the supported v1 reader.
- moving a Run across the v1→v2 grammar boundary is still not a preserve-only operation; first implementation remains fail-closed and the operator starts a new v2 Run when they want the new structure.

### 13.3 Same-grammar rebase

Same-grammar rebase remains explicit and preserve-only:

- every durable Runtime reference must remain admissible;
- Scene parent-Beat changes are semantic incompatibility for preserved current Scene state;
- Decision Scene-association changes do not change durable Beat ownership/choice identity;
- no ID mapping language is introduced.

Rebase means “move this Run to another committed revision,” not “make the Run readable again because latest changed.”

---

## 14. Accessibility and table speed

Retain and extend the PR #626 baseline:

- current/selected/emphasis states are perceivable without color alone;
- primary controls are keyboard reachable with visible focus;
- opening/closing projections returns focus to the invoker;
- high-frequency actions have table-speed targets;
- dense UUID/revision metadata stays visually subordinate;
- warnings are distinct from prose;
- Decision relevance changes are announced in text, not color alone;
- the active Scene and Beat context remain discoverable when overlays/tools open.

---

## 15. Implementation decomposition after the 2026-08-26 re-anchor

### BF1 — Beat-first Playable grammar and manifest foundation — DONE

Merged PR #628. v2 grammar/index/manifest exist. The v2 READY rollout gate intentionally remains until BF2.

### BF2 — v2 READY Runtime + relevance

Next structural Play slice.

Capability:

- seed `currentBeatId` for new v2 Runs;
- admit v2 Runs to READY;
- validate explicit Beat/Scene current-position mutations;
- derive `activates`/`suppresses` emphasis from selections;
- preserve exact historical revision admission.

Remains false afterward: the full Scene-centered cockpit presentation.

### BF3 — Scene-centered current-moment cockpit

Capability:

- active Scene central board with accessible Beat context;
- Beat-only state when no Scene is current;
- Decision interaction + visible relevance change;
- presence-first `At a Glance`;
- inspect versus Make Current;
- Runbook demoted to reference projection;
- notes presented as pinned context without requiring a new note schema.

BF3 should be dogfooded with a deliberately off-script sequence.

### BF3.x — fast contextual/global object retrieval

This may be part of BF3 when the shared projection/finder seam is already small, or an immediately adjacent independently useful slice when not.

Must prove:

- open an object referenced in another Scene/Beat without changing current position;
- find an unreferenced known NPC/Threat quickly;
- exact statblock opens without Plan/Build navigation.

Do not make Agent Surface a prerequisite.

### P4 / Combat integration — Threat → Combat + expandable workspace

- exact Threat/statblock → Add to Combat;
- unexpected fight is first-class acceptance;
- Combat expanded/collapsed in Play while Combat remains authority;
- return to exact Scene.

Combat durability remains a Combat-owned prerequisite for claiming CR-U17 overall, but it is not a reason to postpone BF2/BF3 Play work.

### BF4 — Plan Beat-first authoring composition

Can proceed from BF1 grammar on a disjoint lease; should not block cockpit dogfood when existing material can be authored sufficiently for the test.

### BF5 — legacy/operator migration posture

Retain only where real v1 operator flows still need product hardening. Historical WorkRevision support removes the old “latest revision makes old Run unreadable” premise.

---

## 16. Non-goals

- No general condition/rules engine, event bus, or workflow DSL.
- No persisted relevance copy without evidence that derivation is insufficient.
- No automatic consequence execution into World/Playable/arbitrary Runtime state.
- No permission-gating navigation based on authored Choice edges.
- No new note schema until a real interaction needs one.
- No Combat ownership migration into Play.
- No second Play chrome or projection host.
- No requirement that full Runbook structure dominate Play.
- No requirement that Agent Surface land before fast object/statblock retrieval.
- No silent migration or ID mapping across v1→v2.
- No claim that CR-U17 is complete overall while Combat/other relied-upon state remains non-durable.
