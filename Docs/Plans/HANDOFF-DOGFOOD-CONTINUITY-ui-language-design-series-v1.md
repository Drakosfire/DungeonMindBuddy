# HANDOFF — DOGFOOD-CONTINUITY: UI language design series

**Purpose:** Brief the design agent on the 2026-09-10 shell/language work after `#698` / `#699`. This is not an implementation lease and not permission to dispatch code.

**Status:** DESIGN INPUT — language captured; first slice not leased  
**Created:** 2026-09-10  
**From:** steward + operator after `#699` merge, Mobbin research, and Of Conks styling capture  
**To:** the next design agent for the bounded UI design / implementation series  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Canonical path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`

**Re-anchor at write time:**

```text
main                         d23c8b0efcd8b882046cc6cc52a4f33f5e5fe4eb
                             DOCUMENTS: capture what we liked in Of Conks styling
#698                         MERGED — compact opened World objects
#699                         MERGED — Recap overlay gone; Tools between nav and Ask;
                             Ask Open is a bottom sheet; chrome-band is
                             stabilization only
open PRs                     none
7A1                          DESIGN READY / QUEUED on
                             origin/dogfood-continuity/stage-7a1-ingest-contextual-ask-v1
                             @ e34f68915e0ca535bed7aa9bc13a8bdd2fabea0a
                             handoff lives on that branch, not on main
```

> Repository law: `AGENTS.md`. Steward judgment: `Docs/Process/STEWARD-CYCLE.md`. Language (feel/compose): `Docs/Design/ui-language/`. Chrome **ownership**: `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`. Product goals (non-status): root `Backlog.md` Captured UI section.

---

## 0. Copyable pickup prompt

```markdown
You are the design steward for DungeonMindBuddy’s UI language series.

You design. You do not implement. You do not open an implementation PR
from this brief until the operator accepts one independently useful slice.

Read first, in this order:

1. This file:
   `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`
2. `Docs/Design/ui-language/DESIGN-interaction-layer-language.md`
3. `Docs/Design/ui-language/EVIDENCE-of-conks-styling.md`
4. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-post-698-human-stop.md`
   (dispatch flip, leftover STOP items, 7A1 queued)
5. Root `Backlog.md` — Captured UI/product goals (Goals 2, 3, 4, 8 especially)
6. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
   (who owns the bars; do not rewrite ownership in this pass)
7. `Docs/Process/STEWARD-CYCLE.md`
8. `AGENTS.md`

Then fetch current `main` and exact HEAD. If HEAD is not
`d23c8b0efcd8b882046cc6cc52a4f33f5e5fe4eb`, re-anchor before treating any
SHA in this file as current.

Mission: turn the already-captured language into an accepted first
implementation slice. The product question is already answered:

> Inspection on Ingest is good enough to stand on (#698 A/E).
> The product still feels assembled rather than designed.
> That outranks adding contextual Ask (7A1 stays queued).

What this session locked as *grammar* (not pixels, not a lease):

- Cheap chrome. Expensive current work.
- Related things open as a **right peek column**, not `position: fixed`
  overlay. Parent stays. Nav is never covered.
- Chip → glance (anchored to the token) → peek → modal (create/confirm only).
- Agent is a tiny dock when collapsed, peek or own mode when useful,
  **absent when useless**.
- `#699` `--app-chrome-*` offsets are a stabilization boundary after
  Tools sat under Ask. They are not the target architecture.
- Of Conks is **two styling piles**. Do not mash them into one theme.
  Do not merge dogfood branches wholesale.

Tension you must resolve explicitly, not paper over:

- The Human STOP said: start the series with **Play** as the visual
  north-star proving surface.
- After living in the Ingest chrome fight (Recap overlay, Tools-under-Ask,
  Ask viewport takeover), the language doc recommends **Ingest Graph
  Review / C2S25** as the first *implementation* proving surface, with Play
  remaining the *paint/grammar* north star.

Output required (design artifacts only):

1. An explicit current-state hypothesis in the AGENTS.md re-anchor shape.
2. A STEWARD-CYCLE candidate-outcome worksheet with Keep / Split /
   Reconnaissance on each row. Do not bundle peek-not-overlay +
   parchment paint + Load-bar lock + 7A1 into one capability.
3. A recommended first slice: one independently useful capability, one
   invariant, named successors remain false, exact base, proposed §4
   write lease, runtime/state ownership, collision check.
   Confirm or challenge the language doc’s Ingest-first recommendation
   and say why.
4. How that slice uses the Of Conks evidence (steal hierarchy / discard
   bridges / which palette, if any). Hex values are grammar, not a
   token contract to copy blindly.
5. Explicit non-goals and forbidden repairs.

Do not mark any DEMO-R* / STOP / Stage marker DONE.
Do not write application code, prompts, or tests.
Do not dispatch 7A1, generic-lens repair, Play parchment paint, Combat,
or restore Tools → Ingest Recap / Open Recap View (`/plan?tool=recap`).
Do not start `54329`. World `54330` / APP-STATE `54331` stay read-only
if you dogfood.
```

---

## 1. Why you are being asked now

`#698` made opened World objects useful to inspect. Compact card, Advanced closed, session stamps, sentence-like rows. Operator class: mostly `A` / `E`. Inspection is good enough to stand on.

The same STOP showed the **shell** is still stacked products:

- Tools → Ingest Recap left the loaded recap (repaired in `#699`; do not restore).
- Tools sat under Ask until a guessed chrome-band inset.
- Unavailable Ask Open was a viewport takeover (now a bottom sheet).
- Edit-lock lives in Tools; Load has no Unload; Load is replacement.
- Standing World-chip noise: `Projection campaign does not match requested campaign longmont-c2` (generic-lens successor — not this series).

Dispatch already flipped:

```text
BOUNDED UI DESIGN / IMPLEMENTATION SERIES FIRST
7A1 remains DESIGN READY / QUEUED
re-anchor after the series before 7A1
```

That flip is in [`REPORT-DOGFOOD-CONTINUITY-post-698-human-stop.md`](../Reports/REPORT-DOGFOOD-CONTINUITY-post-698-human-stop.md) and on `#699` close-gates (`99420b0b`). Do not reopen “should we do 7A1 now?”

---

## 2. What we looked at and what we think

### 2.1 Do not invent shipped conventions

2026-09-10 Mobbin research (web first, one convention per search). Steal:

| Job | Steal |
|---|---|
| Tools / object inspect | Notion **side peek** — column, parent document stays, X closes |
| Properties / Help | Linear Properties / Help as a right rail; header never disappears |
| Cheap vs expensive | Figma — thin chrome, huge canvas, inspect as a slim rail |
| Glance | Figma comment pin — anchored to the selected object |
| Collapsed Ask | Linear “Ask Linear” **pill**, not a reserved chrome band |
| Useful Ask | Right peek **or** a center mode; left nav stays. Never cover the current work |

Do not steal: Notion’s giant left tree as Buddy nav; Fabric modal-over-scrim as default object open; TTRPG marketing parchment as chrome research; banking onboarding.

Mobbin did not return a usable Notion `@page` mention hover. Stop searching for it. Figma pin + Notion person/map cards are enough for glance.

### 2.2 Of Conks is two piles, not one theme

Captured in [`Docs/Design/ui-language/EVIDENCE-of-conks-styling.md`](../Design/ui-language/EVIDENCE-of-conks-styling.md). Mining rule still: **preserve the interaction that worked; remove the adventure-specific mechanism.**

| Pile | Job | Feel |
|---|---|---|
| Parchment instruments (`88e4d65e` / PR #578) | Current work: Scene/beat stage, object sheet, threat | Warm paper, crimson for *now*, table speech looks different (say / know / warn / rules) |
| Boutique packet (`fe70b6d6` on e2e branch) | Operational table tools: roll a named table, prepared encounter | Dark gold, gold only for the action, selected row is the expensive moment. Dogfood HTML, not a product surface |

Shared grammar: cheap vs expensive, one scarce accent, chips not graph dumps, provenance quiet.

Allowed palettes:

```text
DARK ROOM CHROME     = Nav, Tools peek chrome, graph glances
PAPER INSTRUMENT     = current Scene / recap / object / threat
DARK OPS HAND OUT    = roll table / prepared encounter (when those exist)
```

Do not parchment a Roll. Do not dashboard a Scene. Do not parchment the Nav. Packet CSS is **not** on the table-ready tip; it lives under `evals/of_conks_end_to_end_dogfood/packet/` on `dogfood/of-conks-end-to-end`.

### 2.3 The chrome band is not the language

`#699` `--app-chrome-top` / `--app-chrome-bottom` stopped Tools sitting under Ask. Operator-liked as a repair. It is **guessed viewport offsets**. The language wants real layout regions:

```text
NAV (cheap, never covered)
CENTER (expensive current work) | PEEK (Tools, object sheet, useful Ask)
AGENT DOCK — tiny when collapsed; absent when useless
```

`SurfaceShell` / `SurfaceFrame` may only compose these regions. They still must not become bar owners. That ownership law stays in the architecture doc.

### 2.4 Play vs Ingest as first proving surface

Operator STOP (verbatim intent): begin with Play as the visual north-star proving surface; carry primitives into recap/object/Ingest later; do not redesign the whole app in one PR.

What we then noticed: **Play is not where the chrome is fighting today.** The fight is Ingest Graph Review with a loaded C2S25 recap: Load bar, Tools, object card, unavailable Ask sheet, World chip. That is the assembled-product feeling.

So the language doc’s recommendation (still **not a lease**) is:

```text
Play     = north-star *grammar* (cheap strip, expensive parchment stage,
           table-first object sheet). Do not paint Play Beats in slice 1.
Ingest   = first *implementation* proving surface (C2S25). Peek-not-overlay
           is visible here. Recap stays. Opening Karsemine must not remount.
```

You may challenge that. If you keep Play-first, say what Ingest chrome does meanwhile (it will keep the chrome-band). If you keep Ingest-first, say how Play grammar still governs the slice so we do not invent a third shell.

---

## 3. Already captured (do not re-derive from chat)

| Artifact | Owns |
|---|---|
| [`DESIGN-interaction-layer-language.md`](../Design/ui-language/DESIGN-interaction-layer-language.md) | Shell regions, overlay stack, steal/ignore, first-slice recommendation |
| [`EVIDENCE-of-conks-styling.md`](../Design/ui-language/EVIDENCE-of-conks-styling.md) | What we liked; keep vs discard; locators |
| Root `Backlog.md` Captured UI | Goals 1–8 + Of Conks locator (non-status) |
| Post-#698 Human STOP report | Operator voice, leftover `E`/`X`, 7A1 queue |
| Architecture surface-interaction | Bar ownership |

Chat is not authority. If this handoff and those files disagree, the files win after you re-anchor `main`.

---

## 4. Leftover STOP items — do not silently absorb

These are real. They are not automatically slice 1.

| Item | Class | Notes |
|---|---|---|
| Edit-lock on Load bar; no Unload | E | Load is replacement. Lock belongs on Load, not in Tools. |
| Paste-new-recap empty-state | X successor | Needs a home; must not be a Tools overlay on a loaded recap |
| Load speed | P | After a UI design pass, not before Load-bar lock is designed |
| Optional sentence copy (`S6 Mirathorn Outskirts located in Mirathorn`) | E | Copy, not shell |
| First-boot Ingest flicker | Stage 5B | Persistent AppChrome only if a remount failure is still observed |
| Generic-lens `?campaign=` World chip | X | 7A1 must not repair this either |
| Conservative chrome-band squeeze | this series | Replace offsets with regions; do not preserve the numbers |

Already repaired: Ingest Recap trap, Tools-under-Ask, Ask viewport takeover, compact object cards.

---

## 5. Named successors that remain false

Until the operator accepts a slice and a later dispatch says otherwise:

- 7A1 Ask-on-this-recap (queued; do not implement or rebrief into this series)
- Plan generic-lens World-chip mismatch
- Load-bar lock / Unload
- Play Beat/Scene parchment paint
- Combat-as-Play-mode
- Restoring Ingest Recap / Open Recap View
- Merging `dogfood/of-conks-*` or committing `packet/local/` licensed fixtures
- Whole-app token rewrite or “make everything parchment”

---

## 6. Suggested first-slice shape (challenge this)

From the language doc, for operator acceptance — **not leased**:

**Capability:** Opening Tools or a World object on Ingest Graph Review does not steal the recap. They share one right peek. Nav stays. Collapsed Ask is a dock, not a reserved sheet-sized bottom band.

**Proving path:** hard-refresh Ingest C2S25 → Load → open Karsemine → recap still there → Tools open in the peek → Ask Open (unavailable) does not cover the recap → Close restores.

**Still false in that slice:** 7A1 usefulness, parchment paint, Load-bar lock, generic-lens, Play Beats.

If you split peek-not-overlay from “Ask becomes a dock,” say so. Unavailable Ask currently forces `--app-chrome-bottom`. That may be one capability or two.

---

## 7. Runtime if you dogfood

```text
UI     http://127.0.0.1:5173/
API     http://127.0.0.1:8000/health
World  54330 read-only
APP-STATE 54331 read-only
Do not start 54329
Canonical recap: C2S25 / Karsemine
Checkout: product main, not a retired #697 worktree
```

Do not paste recap prose, DSNs, or `.env` into design artifacts.

---

## 8. What “done” looks like for this design pass

The operator can accept or reject **one** implementation handoff (or send you back to split). That handoff, if accepted, is a later document with a write lease. This file stays design input.

Do not create a documentation-only PR unless the steward explicitly wants the design artifact reviewed before implementation (`AGENTS.md` §10: design PRs are rare).
