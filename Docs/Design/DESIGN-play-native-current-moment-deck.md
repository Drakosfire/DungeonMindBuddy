---
document_id: dmb-design-play-native-current-moment-deck
title: Native Play Current-Moment Deck
document_class: product_design
status: steward_accepted
created_at: "2026-08-19"
workstream: PLAY
extends:
  - "Docs/Design/DESIGN-play-surface-projection.md"
architecture_authority:
  - "Docs/Design/ARCHITECTURE-playable-material-and-runtime.md"
evidence:
  - "Docs/Reports/REPORT-pr578-play-dogfood-mining.md"
  - "Docs/Dogfood/BRIEF-PLAY-native-table-ux-from-c2s27-dogfood.md"
  - "Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md"
non_authority:
  - "PR #578 implementation"
---

# Design — Native Play current-moment deck

> **Steward review (2026-08-19):** ACCEPTED as the native Table projection redesign under existing Play design authority (`DESIGN-play-surface-projection.md`). This file is not CODE dispatch. P3B, P4, and Plan→Runbook remain independently useful later. Next steward act after D3 re-anchor: one implementation handoff titled `HANDOFF — make the current Beat the native Play table stage`.

## Status

This is a **steward-accepted design** under existing Play product authority. It is not a CODE handoff and does not make P3B, P4, Plan→Runbook, or any other successor dispatchable.

It does not replace the existing Play product thesis. It applies the already-accepted `DESIGN-play-surface-projection.md` interaction hierarchy to the shipped native `/play` wiring proven by P1/P2/P3A/D1/D2 and falsified visually during C2 Session 27 dogfood.

## 0. Decision

Native Play's default Table projection should stop being a three-column Scene/Beat identity browser.

The default Table becomes a **current-moment deck**:

```text
Run title                                      Table | Runbook

‹  Scene 1 / N  ·  Current Scene title  ›      [scene picker]
[compact Scene context]

Beats  [current] [next] [resolved] [next] [...]

┌──────────────────────────────────────────────────────────────┐
│ CURRENT / PREVIEW BEAT                                      │
│ Beat title                                  Resolve / current │
│                                                              │
│ wide, calm, rich Beat body                                  │
│ semantic callouts remain visibly semantic                   │
│                                                              │
│ choices / notes / future open-now + tools below the moment  │
└──────────────────────────────────────────────────────────────┘
```

The first scan must answer **“what is happening now?”**, not **“which identity button is selected?”**

No new durable Markdown kind is required for the first implementation slice.

---

## 1. Evidence and retained product thesis

The accepted Play design already defines:

```text
Run title
Scene deck / position
Beat strip
Focused Beat detail
```

and says that Play exists for the next few minutes at the table.

The Of Conks / Hempholm prototype proved the interaction family:

- session orientation through a Scene deck rather than an equal-weight Scene column;
- near-term navigation through a horizontal Beat strip;
- a wide Beat stage;
- table-first Beat vocabulary;
- table-first object projections;
- contextual Combat / Roll / mechanics actions;
- returning to the same table moment after opening something.

The prototype mechanisms remain disposable. `ofConks*`, `MirewardPrep`, prep HTML, fabricated local graph resolution, hardcoded branches, and text-heading mutation locators do not return.

C2 Session 27 dogfood adds one stronger observation: the native admission/runtime wiring is usable, but the shipped Table presentation is not currently worth navigating at the table. Therefore this redesign is a **projection and interaction correction over proven authorities**, not a persistence redesign.

---

## 2. Default layout

### 2.1 Run bar — identity becomes quiet context

The top of the Play Canvas shows:

- human Runbook title as the dominant run identity;
- `Table` / `Runbook` projection switch at the right;
- quiet save/conflict/recovery status when relevant.

Raw transport identity does **not** dominate the default table view:

- Run UUID;
- campaign ID;
- Runbook SHA;
- exact revision tuple.

Those facts remain available for support/Advanced detail, but they are not the GM's first visual task.

### 2.2 Scene deck — orientation, not a competing browser column

Scene navigation is a horizontal orientation band.

Primary shape:

```text
‹ Prev Scene     Scene 2 / 5 · The Wall Gives Way     Next Scene ›
```

When more than a few Scenes exist, a compact direct Scene picker is available without turning every Scene into a full-height left rail.

Truth carried visually:

- which Scene is the Run's current Scene;
- which Scene is being previewed if the GM looks elsewhere;
- previous / next availability;
- authored session position.

Scene body is available as a compact **Scene context** disclosure immediately below the deck. It renders the existing authored Scene body; it does not reinterpret headings into `intent`, `clock`, or other new storage fields.

The Scene context should not compete with the focused Beat stage for vertical weight.

### 2.3 Beat strip — near-term table navigation

The Beat strip sits inside the selected Scene and is the primary navigation control.

Each Beat item is compact and stateful without requiring suffix prose such as `· resolved · current`.

Visual states:

- **current** — strongest state; clear active edge/background/accent;
- **focused preview** — visible but distinct from current;
- **resolved** — completed mark + subdued title, still reopenable;
- **ordinary unresolved** — neutral;
- **optional / interrupt / spine** — reserved presentation badge when an admitted durable source for Beat kind exists.

Important: the current shipped P1 marker contract identifies `beat` but does **not** provide a durable `spine / optional / interrupt` value. The first slice must not infer this from title, prose, order, or Session 27 content. The UI may reserve the visual slot, but renders no kind badge when authority does not provide one.

This keeps the target design honest without silently adding grammar.

### 2.4 Focused Beat stage — the product center

The Beat stage takes the width currently wasted by equal Scene + Beat list columns.

On load:

- if Runtime has a current Beat, the stage opens it;
- if Runtime has a current Scene but no current Beat, the first admitted Beat may be previewed with truthful `Not started / preview` treatment;
- if Runtime has no current Scene, the first authored Scene/Beat may be previewed exactly as P3A already permits, but nothing is silently persisted.

The stage header includes:

- Beat title;
- current / preview truth;
- resolved state;
- one compact `Make current` action only when the focused Beat is not the Runtime current Beat;
- resolution control integrated with the header/strip, not presented as a separate admin control block.

The stage body is the Beat's rich authored material.

---

## 3. Focused Beat content contract

### 3.1 Target scan order

The durable product target remains:

1. At the table
2. Read aloud
3. GM note
4. Rules now
5. Warnings
6. Consequences
7. Open now
8. Tools

But **the first native refinement must not fake this vocabulary by parsing heading names.**

### 3.2 First-slice rule: Beat body is the At-the-table material

With today's admitted authority, the stable semantic unit is the Beat itself plus its authored body.

Therefore the first slice treats:

> **the focused Beat body as the primary at-table region**

without manufacturing a persisted or parsed `atTable` field.

Implementation may preserve the Beat's rich TipTap node slice from the already-admitted `importedDoc` instead of flattening it to `bodyText`.

This is a projection change only:

```text
exact admitted importedDoc
  + P1 stable Beat heading boundary
  → rich body fragment for that Beat
  → read-only focused Beat stage
```

No second Markdown fetch. No second Markdown parser. No heading-name classification.

### 3.3 Existing semantic callouts remain semantic

Existing TipTap/Markdown callout semantics such as:

- READ-ALOUD;
- GM-NOTE;
- RULES;
- WARNING;

may keep their existing visual treatment inside the focused Beat body.

They remain in **authored document order** in the first slice. Native Play does not extract and reorder them merely to make the page resemble the Of Conks object shape.

This gives the GM useful scan landmarks without inventing a new Playable block persistence layer.

### 3.4 What is deliberately not inferred

The first slice does not inspect prose or headings to invent:

- At the table fields;
- `if they wait / succeed / fail` consequences;
- pressure/clock objects;
- Beat kind;
- Open-now curation;
- Tools;
- rewards;
- NPC attitude/offers;
- strategic Choice/Option structure.

If Session 27 says “They are widening it” or describes competing pressures, that remains authored Beat prose and is simply made easy to read.

If later work wants a durable semantic representation that Runtime or authoring must address directly, that is a separate steward decision.

### 3.5 Consequences, Open now, and Tools

The design reserves these lower-stage regions but only renders them when an existing authority can supply them truthfully.

- **Consequences:** future Playable semantic projection; never inferred from prose in this slice.
- **Open now:** future typed-reference projection, likely consuming exact reference-opening work; P3B is not required for the current-moment deck itself.
- **Tools:** capability links from Play projection state; Combat/Roll/P4 remain separate capabilities.

Empty unavailable regions are omitted. Native Play does not show dead headings or placeholder cards.

---

## 4. Interaction model

### 4.1 Focus vs Runtime current

Preserve the useful distinction already present in shipped native Play:

- the GM may **focus/preview** another Scene or Beat locally;
- Runtime current Scene/Beat remains explicit durable state;
- preview does not mutate Runtime;
- a small `Make current` action promotes the focused Beat/Scene to Runtime when intended.

The redesign removes the administrative visual weight of `Set current Scene` / `Set current Beat` buttons while preserving their safety meaning.

On initial load, focus follows Runtime current state, so normal table use does not begin in preview mode.

### 4.2 Resolve

Resolve/unresolve remains the existing P2 `resolved_beat_ids` mutation.

The interaction moves into the Beat strip and/or stage header:

```text
○ unresolved
✓ resolved
```

It should be one click, visible at a glance, and reload-safe under the existing `run_revision` CAS.

### 4.3 Notes

Existing `notes_by_element_id` remains Runtime authority.

Notes are available from the current Beat stage as a compact disclosure/drawer near the bottom of the moment. They are not a permanent wide textarea competing with the Beat content.

### 4.4 Choices / Options

Existing P1 Choice/Option identity and P2 `selections` remain valid.

The redesign does not force Session 27 strategic directions into choices. When a focused Scene genuinely has authored choices, they appear below the focused moment as a deliberate decision region.

No new branch mechanism is introduced.

### 4.5 Table / Runbook

`Table` remains the default.

`Runbook` remains D2's full exact committed document projection and is visually secondary.

Switching Table → Runbook → Table:

- does not mutate Runtime;
- preserves local Scene/Beat focus;
- returns the GM to the exact table moment.

The Runbook document must also visually belong to the shared dark AppChrome shell; it should not look like a second light document application pasted inside Play.

---

## 5. Visual hierarchy inside shared AppChrome

Play owns a table-specific Canvas treatment while continuing to use shared AppChrome.

### 5.1 Principles

- dark shell remains continuous from AppChrome into Play Canvas;
- one primary stage, not three peer columns;
- borders/spacing/state markers create hierarchy before background color does;
- human titles lead; UUIDs and hashes recede;
- current state uses one strong accent treatment;
- resolved state is visibly complete but not disabled;
- preview is visibly different from current without becoming an error state;
- warnings/conflicts retain high-contrast banners because they represent truth/safety, not decoration.

### 5.2 Avoid

- large cream/white panels inside the dark shell;
- equal-weight Scene and Beat button stacks;
- metadata rows that are visually louder than the Beat;
- every action represented as the same rectangular button;
- identity suffix prose (`· current`, `· resolved`) as the primary state encoding;
- permanent sidebar real estate for controls used once per Scene.

---

## 6. Mapping to existing authorities

| New UI concern | Existing authority / input | Design rule |
|---|---|---|
| Run title | P3A admitted workspace snapshot | Human title leads. |
| Exact Runbook revision/SHA | P2 Run + P3A admission | Preserve; move to Advanced/support detail. |
| Scene identity/order/title | P1 structure index + admitted document | Horizontal Scene deck. No new identity. |
| Beat identity/order/title | P1 structure index + admitted document | Horizontal Beat strip. No new identity. |
| Rich Scene body | P3A admitted `importedDoc`, sliced by P1 boundary | Read-only Scene context. No second parser/fetch. |
| Rich Beat body | P3A admitted `importedDoc`, sliced by P1 boundary | Wide focused stage. No heading ontology. |
| Current Scene/Beat | P2 Run progress | Strong visual current state. |
| Resolved Beat | P2 `resolved_beat_ids` | Strip/header state; existing CAS. |
| Choices/Options | P1 + P2 selections | Existing generic identities only. |
| Notes | P2 `notes_by_element_id` | Compact Runtime note affordance. |
| Full Runbook | D2 exact `importedDoc` projection | Secondary mode, same dark shell. |
| Read-aloud / GM / Rules / Warning styling | Existing semantic callout nodes where authored | Preserve in document order. Do not create new storage. |
| Beat kind spine/optional/interrupt | **No current admitted durable source** | Do not infer. Future explicit Playable semantic. |
| Consequences | Not yet a shipped durable semantic projection | Reserve target region; do not parse prose. |
| Open now | Future exact typed-reference projection | Not a prerequisite. |
| Combat/Roll/Tools | Existing/future capability surfaces | Not a prerequisite. |

This design changes none of the P1/P2/P3A/D1/D2 authority boundaries.

---

## 7. What we keep from Of Conks, and when

### First implementation slice

Keep the **interaction shape**:

- Run title → Scene deck → Beat strip → focused Beat stage;
- wide calm stage;
- current/resolved Beat states;
- local focus without losing Runtime truth;
- table-first typography and scan hierarchy;
- full Runbook as secondary projection;
- shared dark-shell visual continuity.

Use native admitted P1/P2/P3A/D2 data only.

### Later independent slices

**Play Object Sheets / P3B family**

Keep:

- table-first object sheet hierarchy;
- click/open without losing Play position;
- relevant-now curation.

Do not keep:

- `ofConksPlayObjectBridge`;
- fabricated local graph resolution;
- campaign-specific object dictionaries.

**Combat / P4 family**

Keep:

- Threat → exact mechanics → Add to Combat;
- return to same Play moment.

Do not make it prerequisite to the table deck.

**Roll / Items / Mechanics tools**

Keep contextual launch from current moment when those projections exist.

Do not add dead tool placeholders to the first slice.

### Discard permanently

- prep HTML host as Play substrate;
- `MirewardPrep` globals;
- hardcoded Hempholm spine data;
- adventure-specific runtime enums;
- heading-text identity/mutation locators;
- campaign-specific bridge maps.

---

## 8. First independently useful implementation slice

There is one clean first slice. It does **not** need to split.

### Candidate handoff title

**`HANDOFF — make the current Beat the native Play table stage`**

Suggested PR title later:

**`PLAY: make current Beat the table stage`**

### Capability

Replace the native Table three-column identity browser with the current-moment hierarchy using the already-admitted exact Runbook and existing Runtime mutations.

The slice should be independently valuable with **zero** P3B/P4/Plan→Runbook dependency.

Expected product boundary:

1. compact Run bar;
2. horizontal Scene deck/position;
3. compact Scene context;
4. horizontal Beat strip;
5. wide rich focused Beat body sliced from the already-admitted TipTap document;
6. current/preview/resolved states using existing P2 progress;
7. existing Choice/Option and notes retained but visually subordinate;
8. D2 Runbook mode retained as secondary;
9. dark AppChrome-native visual treatment.

### Explicit non-goals of the first slice

It does **not**:

- add a new durable Markdown/TipTap kind;
- add `spine / optional / interrupt` persistence;
- parse headings such as `At the table`, `If they wait`, `Consequences`, or `Open now` into a new ontology;
- add Play Object Sheets or make P3B dispatchable;
- add Combat or Add-to-Combat;
- add Roll capability;
- redesign Plan/Build;
- add Runbook authoring;
- copy/cherry-pick #578 components or CSS wholesale;
- introduce a new Runtime contract;
- add a second Markdown fetch/parser;
- move Scene/Beat IDs or Runtime state into prose.

### Steward stop condition

If implementation concludes that the current-moment deck cannot be useful without a new durable Markdown kind or new durable Beat semantic, STOP and return that design pressure to stewardship. Do not classify Session 27 prose or heading names as a silent substitute.

The design does **not** currently expect that stop condition: the first slice is useful with existing Scene/Beat boundaries, rich Beat bodies, callouts, and P2 progress alone.

---

## 9. Session 27 falsification walkthrough

For the exact C2 Session 27 Runbook, opening native Table should produce approximately:

```text
C2 Session 27 — Mireward Climax                         Table | Runbook

Scene 1 / 1 · Mireward Siege Climax
[Scene context]

Beats
[Survive the current breach · CURRENT]
[Town-wide siege]
[Thrin's forest-memory awakens]
[Wall hinge crisis]
[Aftermath and strategic fork]

SURVIVE THE CURRENT BREACH                         Current   ○ Resolve

- save the townsman or let the swarm pull him away
- kill / trap / burn / follow the surviving swarm
- get Thrin safely back into the defensive line
- decide whether Baergrom holding the tunnel is still worth it
- investigate what the swarm was doing to the wall
- interfere with the local tunnel
- reconnect the scattered party

[existing semantic callouts, if authored]

Notes ▾
```

The ordinary Runbook-level sections after the Beats:

- Strategic directions;
- Exit ramps;
- Information sources;
- Open questions;
- Session success condition;

remain outside the focused Beat because D2/P1 body ownership already says so. They remain available in `Runbook` mode. They are not pulled into the Beat stage by heading-name matching.

The GM should be able to move from `Survive the current breach` to `Town-wide siege`, mark a Beat resolved, inspect another Beat, and return without ever seeing a Scene list column or needing the full Runbook.

---

## 10. Acceptance stories

The design is successful when:

1. Opening a READY Run lands visually on the current Beat, not on navigation lists.
2. The Run title, current Scene, Scene position, and current Beat are visible without exposing raw IDs.
3. The GM can scan all Beats in the current Scene horizontally and tell current/resolved state without reading suffix text.
4. Focusing another Beat changes the wide stage without mutating Runtime until deliberately made current.
5. Making a Beat current and resolving it use the existing P2 CAS path and survive hard reload.
6. The focused Beat body renders rich authored structure from the already-admitted document rather than flattened prose.
7. Existing READ-ALOUD / GM-NOTE / RULES / WARNING callouts remain visually distinct without heading-name parsing.
8. Table → Runbook → Table returns to the same focused moment with zero Runtime mutation.
9. The default Play Canvas visually belongs to shared dark AppChrome.
10. Session 27 can be run from the focused Beat stage without opening the full Runbook unless the GM deliberately wants global instructions.
11. No `ofConks*`, prep HTML, campaign-specific bridge, or new durable grammar is needed.

### Falsification

The design fails if the GM's first scan remains:

> Which Scene/Beat navigation control is selected?

The design is in the correct family if the first scan becomes:

> What is happening in this Beat right now, and what do I need to do with it?

---

## 11. Design disposition

**Recommended:** approve this as a native projection redesign under the existing Play design authority, then write one implementation handoff for the current-moment deck.

**Do not dispatch CODE from this document itself.**

P3B, P4, Play Object Sheets, Roll, Plan→Runbook authoring, semantic consequences, and richer Beat kinds remain separately useful later capabilities. Their absence is not permission to keep the current three-column browser as the default Table instrument.
