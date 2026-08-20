# Brief to Play design agent — redesign native Table UX around the Of Conks prototype

**From:** C2 Session 27 native Play dogfood (D3), steward  
**To:** Play design agent  
**Date:** 2026-08-19  
**Status:** steward-accepted design proposal. Not CODE dispatch. Canonical path: `Docs/Design/DESIGN-play-native-current-moment-deck.md`.

Authorities to read first, in this order:

1. `Docs/Design/DESIGN-play-surface-projection.md`
2. `Docs/Reports/REPORT-pr578-play-dogfood-mining.md`
3. `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`
4. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`

Do not treat PR #578 as mergeable product. Treat it as the UX prototype whose table interactions we already decided to keep.

---

## 1. What just happened

We dogfooded shipped native `/play` against a real Campaign 2 Session 27 Runbook.

Wiring that is now real:

```text
committed Runbook
  → explicit Start Run
  → exact Run + sealed manifest
  → P1-admitted TipTap document
  → Table projection + full Runbook projection
  → Runtime progress under run_revision CAS
```

The GM’s judgment after READY: **that wiring is fine, and the native Table UI is not a table instrument.** Contrast was patched as an emergency exception. Navigation was still refused because the layout is not worth using at the table.

Exact dogfood Run (do not treat as design authority):

```text
/play?run=07225b19-7df3-4335-ae14-22e4b133eac4
Runbook: C2 Session 27 — Mireward Climax
document 8235ce04-5023-485c-92f0-2d8d81d64f50 revision 3
```

---

## 2. The design need

Redesign native Play’s **default table UX** around the Of Conks / Hempholm prototype, using already-accepted product design, not a new philosophy.

The product thesis is already written:

> Play is the surface for the next few minutes at the table.

The GM must always be able to answer:

- Where am I?
- What is happening now?
- What is optional?
- What pressure advances if they stall?
- What can I open without leaving?
- What happens if this resolves?

Shipped native Play answers a different question: **which exact Scene/Beat ID is selected?** That is identity machinery. It is not table UX.

### What shipped (reject as the default table instrument)

```text
Scene list | Beat list | focused body dump
+ Table / Runbook toggle
+ a few runtime buttons
```

This is a three-column identity browser. It looks like admin chrome on a dark app shell. It does not present the current moment. The GM did not want to navigate it.

### What the prototype already proved (keep as the UX target)

Of Conks / Hempholm was more refined because it was a **current-moment deck**, not a file navigator.

Target hierarchy from `DESIGN-play-surface-projection.md`:

```text
Run title
Scene deck / position
Beat strip
Focused Beat detail
```

Focused Beat vocabulary already specified:

- At the table
- Read aloud
- GM note
- Rules now
- Warnings
- Consequences (wait / succeed / fail / choose / reward / cost / clock)
- Open now (typed references)
- Tools (Combat, Roll, item/mechanics, source, Hermes)

Capability family already specified:

```text
Play
├── Run / Beats
├── Combat
├── Roll
├── Items
├── Mechanics / Statblocks
└── table projections
```

Mining keepers (`REPORT-pr578-play-dogfood-mining.md`):

- Play is its own surface contract, not Plan with fewer controls.
- Beat is the near-term table unit.
- Object sheets are table-first projections.
- Preserve the interaction that worked; remove the adventure-specific mechanism.

---

## 3. What you must preserve

Do not reopen identity, persistence, or admission. Those are predecessor product truth:

| Layer | Keep |
|---|---|
| P1 | Scene / Beat / Choice / Option markers and structure index |
| P2 | Run, sealed manifest, `run_revision` CAS progress |
| P3A | Native `/play` admits exact Run + snapshot + manifest |
| D1 | Explicit Start Run from one committed Runbook |
| D2 | Full exact Runbook view beside Table; ordinary H1/H2 stay unmarked |

The redesign consumes that wiring. It does not replace it with #578 HTML, global scripts, text-heading locators, or campaign-specific bridges.

---

## 4. What you must change

Produce a **Play table UX design** (and only later an implementation handoff) that:

1. Makes the **current Scene + current Beat** the default visual anchor, not two equal list columns.
2. Puts **focused Beat detail** on a wide calm stage. Body prose is a supporting region, not the whole product.
3. Recovers Of Conks scan order: at-table first, then read-aloud / GM note / rules / consequences / open-now / tools.
4. Treats Scene navigation as **session orientation** (deck / previous / next / current), not a vertical button stack competing with Beats.
5. Treats Beat navigation as a **strip inside the Scene**, with current/resolved/optional visible without reading cream-on-white admin buttons.
6. Keeps the D2 full Runbook view as a secondary mode, not the table default.
7. Fits the shared AppChrome dark shell instead of painting a second light document-app inside it. The contrast bug was a symptom of Play not owning its chrome.
8. Does **not** require new Playable grammar to ship the first refined table. If At the table / Read aloud / GM note are not yet durable kinds, say how the first UX uses existing unmarked sections + Beat body without inventing a briefing schema.
9. Does **not** make P3B, P4, or Plan→Runbook a prerequisite for a usable current-moment deck. Those remain independently useful later.
10. Names the first independently useful implementation slice after this design, and what it explicitly will not rebuild from #578.

---

## 5. Explicitly do not do

- Merge or cherry-pick PR #578 as the native Play surface.
- Restore `prep` HTML / `MirewardPrep` / Of Conks hardcoded bridges.
- Invent `briefing` persistence or heading-name ontology to fake the prototype.
- Treat this brief as CODE dispatch.
- Treat this brief as making `HANDOFF-PLAY-native-graph-object-sheet.md` dispatchable.
- Redesign Plan or Build to look like Play.
- Use Session 27 prose as a new product ontology.

---

## 6. Success test for your design

A GM looking at Session 27 on `/play` should want to stay there.

Falsify the current native deck:

- If the first scan is “which list button is current?”, the design failed.
- If the first scan is “what is happening in this Beat, right now?”, the design is in the right family.

A GM should be able to run the Mireward climax from the current Beat without opening the full Runbook unless they choose to.

---

## 7. Return contract

Bring back a design artifact, not a prototype dump:

- what layout replaces the three-column identity browser;
- how it maps onto existing P1/P2/P3A/D2 authorities;
- which Of Conks interactions are in the first slice vs later (object sheets, Combat, Roll);
- what remains unmarked Runbook prose vs future Playable kinds;
- a single candidate implementation handoff title, or an explicit split if two independently useful slices appear.

Stop and ask if the first slice would require a new durable Markdown kind. That is a steward decision, not a silent grammar change.
