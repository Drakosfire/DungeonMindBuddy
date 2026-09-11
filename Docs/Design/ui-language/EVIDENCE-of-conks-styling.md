---
document_id: dmb-evidence-of-conks-styling
title: Of Conks styling — what worked, what to keep
document_class: evidence_report
status: design_input
created_at: "2026-09-10"
updated_at: "2026-09-10"
language_authority: "DESIGN-interaction-layer-language.md"
mining_rule: "Preserve the interaction that worked. Remove the adventure-specific mechanism that made it work."
---

# Of Conks styling — what we liked

This captures **why** the Of Conks paint felt like a table instrument, not a hex dump of CSS.

Do not merge `dogfood/of-conks-*` wholesale. Do not commit licensed packet fixtures. Hex values below are **evidence of hierarchy**, not a token contract to copy blindly.

There are **two styling piles**. They solve different jobs. Mixing them into one “Of Conks theme” would lose the lesson.

---

## 0. Two piles, two jobs

| Pile | Branch / SHA | Job | Surface |
|---|---|---|---|
| **Parchment instruments** | `dogfood/of-conks-hempholm-table-ready` @ `88e4d65e7ed69afe262008749194e2b948ce4c43` (PR #578) | The **current work**: Scene/Beat stage, object sheet, threat sheet | Inside live-control-ui |
| **Boutique packet** | `dogfood/of-conks-end-to-end` @ `b40d893f` (added `fe70b6d6`) | **Operational table tools**: roll a named table, prepared encounter card | Static HTML under `evals/…/packet/` — **not** a product surface |

Mining authorities:

- [`REPORT-pr578-play-dogfood-mining.md`](../../Reports/REPORT-pr578-play-dogfood-mining.md) — Play Object Sheet, scene/beat hierarchy
- `Docs/Reports/REPORT-of-conks-end-to-end-dogfood.md` on the e2e branch — operator voice on the roll moment
- [`DESIGN-interaction-layer-language.md`](DESIGN-interaction-layer-language.md) — shell regions this paint sits inside

---

## 1. Parchment instruments (what we liked)

Sources on `88e4d65e`:

- `apps/live-control-ui/src/playSurface/beats/beats.css`
- `apps/live-control-ui/src/graphReference/playObjectSheetProjection.css`
- `apps/live-control-ui/src/graphReference/PlayObjectSheetProjection.tsx`
- Survivor on `main`: `apps/live-control-ui/src/statblocks/projection/threatSheetProjection.css` (same paper tokens)

### 1.1 Cheap strip, expensive stage

CSS comments encode the hierarchy:

```text
Scene deck — horizontal top strip
Beats — condensed horizontal strip under scenes
Wide stage: beat detail dominates; scene context below/secondary
```

Inactive scenes are **pills** (transparent, no border). The active scene gets a **crimson ring** (`#a11d18`) and warm fill. Beat strip items are small; selected beat gets the same crimson ring plus a 1px halo. The stage (`min-height: 14rem`, cream card `#fffaf0`) is the expensive region.

**Keep:** navigation/presence is a strip. The current Beat/Scene is a paper card. Current is marked by **one accent**, not a second dashboard.

### 1.2 Semantic blocks read as different kinds of speech

The stage does not dump one body blob. Blocks have distinct visual jobs:

| Block | Visual | Why it worked |
|---|---|---|
| Eyebrow / kind | Tiny uppercase (`spine` / `optional` / `interrupt`) | Interrupt is crimson; optional is cool blue — kind is scannable before the title |
| At the table | Larger body (`1.05rem`), ink `#3a2412` | The GM’s first sentence |
| Read-aloud | Italic, left crimson bar, warm wash | “Say this” is obvious vs GM notes |
| Rules now | Tinted box, not a heading in the same type | Mechanics are a **card inside the card** |
| Warnings | Stronger red wash + `#58180d` ink | Danger does not look like flavor |
| GM notes / clocks | Smaller, muted | Secondary; does not compete with At the table |
| Object/tool chips | Pill outline, hover to accent | Connected things are openable, not a graph table |

**Keep:** different table speech (say / know / warn / roll) must **look** different. That is Goal 3 from root Backlog, proved in CSS.

### 1.3 Object sheet is table-first, not graph-first

NPC default order in `PlayObjectSheetProjection.tsx`:

```text
type badge + title (crimson underline)
At the table
Attitude
Offers & hooks
Rules now          ← boxed
From the module / source
provenance (dashed, muted)
Open in Play       ← solid accent CTA
Connected now      ← chips, not adjacency dump
<details>Advanced</details>   ← graph related + memory/visibility
```

Glance mode is **one italic line** (`atTable` only). That is the hover/peek preview, not a mini dossier.

**Keep:**

- Table-useful information leads.
- Graph identity, revision, full adjacency live under Advanced.
- Connected now is a **curated chip set**, not the whole graph.
- One primary action (`Open in Play`) is a filled accent button; everything else is quieter.

The mining report’s permanent lesson is the projection, not `PlayObjectBody`:

```text
WORLD + SOURCE + PLAYABLE + MECHANICS
                ↓
        PLAY OBJECT SHEET
```

Thin sheets without mechanics (e2e OC-014: “No attribute rows”) felt **wrong**. We liked the *shape* of the sheet; we disliked it when the World had nothing table-useful to put in Rules now.

### 1.4 Dual aesthetic: dark room, warm paper

Parchment tokens (object sheet / threat sheet):

```text
ink       #2b1d0f
heading   #58180d
accent    #a11d18   ← current / urgency / CTA
border    #c0ad6a   ← 2px gold edge
paper     #f7ebd7
type      Bookinsanity / Book Antiqua / Georgia
```

Beat panel is a slightly cooler paper room (`#f4efe6` panel, `#fffaf0` cards, ink `#1f1a14`). Graph glances on the same branch stay **product-dark** (`graphReference.css` `#151b28`).

**Keep:** chrome and glances are the dark room. The **current instrument** (Scene, object, threat) is paper. Do not parchment the Nav. Do not dark-dashboard the Scene.

### 1.5 Maps are pins on the paper, not a GIS product

`playObjectSheetProjection.css` map overlay: image on paper, crimson pin dots, chip legend. Click a pin → same object projection path.

**Keep:** media + normalized pins + graph/playable target. Discard `ofConksMapOverlays.ts` dictionaries.

---

## 2. Boutique packet (what we liked)

Sources on `fe70b6d6` / `b40d893f` (absent from `main` and from `88e4d65e`):

- `evals/of_conks_end_to_end_dogfood/packet/assets/of-conks-packet.css`
- `of-conks-packet.js`
- `of-conks-tables.html` (Station 6)
- `of-conks-encounters.html` (Station 7)

Header in the CSS: **dogfood-only; not a product surface.**

This pile is a **dark operational handout**, not parchment:

```text
bg        #14171c
panel     #1d2229
ink       #e8e4d8
muted     #9aa3ad
accent    #d9a441   ← gold action (Roll)
hit       #3f5d3a / #6f9f5f  ← selected row / result
type      Iowan / Palatino / Georgia
```

### 2.1 The roll moment (operator-liked)

From the e2e report, operator voice:

> Boutique packet roll moment: Roll 1d12 → “Rolled 5 → Thorwald Dohna” with the row lighting up is exactly the table-feel the handoff asked for, at near-zero code cost.

> Boutique packet pages are static + one small JSON fetch — instant at table speed.

What that CSS/JS actually does:

1. One **card per table** (title, meta pills, gold **Roll** button).
2. Readable rows in a compact table (uppercase muted headers).
3. Click Roll → one row gets `tr.oc-selected` (green wash + left hit bar) and a result banner appears.
4. Result is **ephemeral** — never persisted, never published to World.
5. Honest banner at the top: this is dogfood, not a generic Roll Table product.

**Keep the interaction** (handoff Candidate C / OC-015):

```text
recognized table → readable rows → Roll → one highlighted result
```

Do **not** keep: Appendix C content, `roll_stack` session-22 hardcoding, or shipping these HTML pages as Buddy UI.

### 2.2 Encounter sheets as prepared cards

Station 7: one card per prepared fight. Stat grid is **label-above-value** (tiny uppercase muted label, ink value). Node chips link into the graph. Mechanics/tactics are lists under gold `h3`.

**Keep:** a prepared encounter is a **readable sheet** (who is here, how many, what they do, graph handles) — not a Combat Tracker clone. OC-016: existing `/combat` is itself a boutique static page; do not fake generic Combat by stuffing it into this CSS.

### 2.3 Why the packet felt fast

| Choice | Why it worked |
|---|---|
| Static HTML + one JSON fetch | Table speed; OC-018: zero Vite/product changes (`/evals/**`) |
| One card = one job | Scan, then act |
| Gold is **only** for the action (Roll) and dice pills | Accent is scarce |
| Selected row is the expensive moment | Same cheap/expensive rule as the scene deck, inverted onto a table |
| Reads no authority, writes nothing | Legal pin + no fake World writes |
| Footer provenance, muted | Honesty without occupying the hot path |

---

## 3. Shared grammar across both piles

These are the things we liked in **both**, and they are already the Interaction Layer language:

| Grammar | Parchment (Play) | Packet (ops) |
|---|---|---|
| Cheap vs expensive | Scene/beat pills vs stage card | Row list vs selected row + result |
| One accent for *now* | Crimson `#a11d18` | Gold `#d9a441` + hit green |
| Chips, not tables of graph | Connected now / scene chips | `.oc-nodechips` |
| Advanced / provenance quiet | `<details>Advanced` / dashed provenance | Footer + muted meta pills |
| Do not leave the moment | Sheet/projection over the stage | Packet is a dedicated station; it does not remount Plan |

Two palettes are allowed:

```text
DARK ROOM CHROME     = Nav, Tools peek chrome, graph glances
PAPER INSTRUMENT     = current Scene / recap / object / threat
DARK OPS HAND OUT    = roll table / prepared encounter (when those exist)
```

Do not parchment a Roll. Do not dashboard a Scene.

---

## 4. Discard list (liked as proof, poisonous as product)

From PR #578 mining §5 and e2e §3:

- `ofConksPlayObjectBridge.ts`, `ofConksHempholmBeats.ts`, `ofConksThreatPlayBridge.ts`
- `ofConksNodeMedia.ts`, `ofConksMapOverlays.ts`
- Adventure-specific runtime enums
- Boutique HTML as a forever `/evals` product
- `packet/local/*.json` (licensed; never commit)
- Pretending packet Combat/Roll **is** the product seam

---

## 5. Locator (feel only)

| What | Where |
|---|---|
| Table-ready Play paint | `88e4d65e` `beats.css`, `playObjectSheetProjection.css` |
| Object sheet IA | `PlayObjectSheetProjection.tsx` `sectionTitles` + render order |
| Threat parchment on `main` | `threatSheetProjection.css` |
| Boutique packet CSS/JS/HTML | `fe70b6d6` `evals/of_conks_end_to_end_dogfood/packet/` |
| Roll interaction to mine | e2e report OC-015; handoff Candidate C |
| Encounter sheet pattern to mine | e2e report OC-016 |
| Thin-sheet warning | e2e OC-014 — sheet shape without mechanics is not enough |

When a later slice paints Play or table tools, read this file before inventing a third palette.
