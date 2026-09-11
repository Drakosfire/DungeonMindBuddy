---
document_id: dmb-design-interaction-layer-language
title: Interaction Layer language — shell regions, peek, glance, Agent dock
document_class: product_design
status: design_input
version: 0.2
created_at: "2026-09-10"
updated_at: "2026-09-10"
workstream: UI-LANGUAGE
architecture_authority: "../ARCHITECTURE-surface-interaction-layer.md"
companion_designs:
  play_cockpit_target: "../DESIGN-play-surface-gm-cockpit-target.md"
  play_projection: "../DESIGN-play-surface-projection.md"
  play_current_moment: "../DESIGN-play-current-moment-cockpit.md"
  overlay_direction: "../DESIGN-play-mode-runbook-product-direction.md"
  canvas: "../DESIGN-shared-markdown-canvas-surface-composition.md"
product_goals: "../../Backlog.md"
evidence:
  - "PR #578 / dogfood/of-conks-hempholm-table-ready @ 88e4d65e — parchment instruments (Scene/object/threat)"
  - "dogfood/of-conks-end-to-end @ b40d893f / fe70b6d6 — boutique packet (roll + prepared encounter)"
  - "EVIDENCE-of-conks-styling.md — what we liked; keep vs discard; two palettes"
  - "REPORT-pr578-play-dogfood-mining.md — preserve the interaction, discard adventure-specific bridges"
  - "PR #698 / #699 — compact object cards; Recap overlay removed; chrome-band is stabilization only"
  - "2026-09-10 Mobbin research — Notion side peek, Linear Properties/Help/Ask dock, Figma canvas + comment pin"
---

# Interaction Layer language

This is the **visual and interaction language** for DungeonBuddy’s shared shell: Nav, Tools, graph/object viewing, and the Agent dock.

It is not a write lease and not a pixel spec. It does not replace [`ARCHITECTURE-surface-interaction-layer.md`](../ARCHITECTURE-surface-interaction-layer.md), which still owns **who owns the bars**. This document owns **how those bars should feel and compose**.

Do not merge Of Conks branches wholesale. Do not restore Tools → Ingest Recap. Do not treat `#699` `--app-chrome-*` offsets as design authority.

---

## 0. One sentence

```text
Cheap chrome. Expensive current work.
Related things open as a peek.
Nothing covers the nav.
Unavailable Agent does not occupy the table.
```

The product is one application with modes (Plan, Play, Ingest, Build), not independently composed workbenches competing for `position: fixed` real estate.

---

## 1. What this is / is not

| This document | Not this document |
|---|---|
| Shell **regions** and overlay **grammar** | Bar ownership / publication contracts (architecture) |
| Steal / ignore from shipped products + Of Conks | Parchment paint tokens as the first implementation slice |
| First proving-surface recommendation | 7A1 (Ask on the loaded recap) |
| Dual aesthetic: dark room chrome + warm paper instruments | A second World, retrieval plane, or Agent product |

Product goals this language implements (from root `Backlog.md`, non-status):

- Goal 2 — shared shell, no overlapping rails
- Goal 3 — Play as table instrument (north-star *grammar*; Play paint can follow)
- Goal 4 — World objects table-first, graph under Advanced
- Goal 8 — Agent contextual where it exists; no persistent unavailable bar

---

## 2. Shell regions

Compose **real layout regions**. Do not stack overlapping fixed layers and then compensate with `--app-chrome-top` / `--app-chrome-bottom`.

```text
┌─────────────────────────────────────────────────────────────┐
│  NAV — cheap. Mode switch + where-you-are. Never covered.   │
├───────────────────────────────────────────────┬─────────────┤
│                                               │             │
│  CENTER — expensive current work              │  PEEK      │
│  Recap / Scene / Canvas / issue-equivalent      │  Tools,      │
│                                               │  object     │
│                                               │  sheet,     │
│                                               │  Help/AI    │
│                                               │  when open  │
│                                               │             │
├───────────────────────────────────────────────┴─────────────┤
│  AGENT DOCK — tiny when collapsed. Absent when useless.      │
└─────────────────────────────────────────────────────────────┘
```

| Region | Job | Cheap / expensive |
|---|---|---|
| **Nav** | Mode + campaign/session context | Cheap. Always visible. |
| **Center** | The thing the GM is in (recap, Scene, canvas) | Expensive. Dominates. |
| **Peek** | Tools, opened World object, Help, useful Ask | One right column, not a second page. X closes. Parent stays. |
| **Agent dock** | Composer when Ask is actually available | Tiny pill / short bar. Not a reserved 64vh band. |

`SurfaceShell` / `SurfaceFrame` may only compose these regions. They still must not become bar owners.

The `#699` chrome band was a **stabilization boundary** after Tools sat under Ask. Its guessed offsets are not the target. Replace them with region layout when a slice touches this seam.

---

## 3. Overlay stack

Historical direction, still correct ([`DESIGN-play-mode-runbook-product-direction.md`](../DESIGN-play-mode-runbook-product-direction.md)):

```text
inline chip → compact popover (glance) → peek / drawer → full modal
```

What remains when the overlay closes is the **anchor**:

| Surface | Return target |
|---|---|
| Ingest | Loaded historical recap (Graph Review) |
| Play | Exact current Scene / Beat |
| Plan / Build | Current canvas / work object |

Rules:

- Inspecting is not navigating. Opening Karsemine must not remount the recap.
- Modal is for **create / confirm**, not default inspect ([Linear new-issue expand](https://mobbin.com/flows/f0eb8f6b-bbb5-4261-b6d6-c0a34804a65e) is create).
- Full-viewport takeover is forbidden for Tools and for unavailable Ask.

---

## 4. Graph / object viewing

Of Conks mining rule ([`REPORT-pr578-play-dogfood-mining.md`](../../Reports/REPORT-pr578-play-dogfood-mining.md)):

> Preserve the interaction that worked. Remove the adventure-specific mechanism that made it work.

| Layer | Language | Evidence |
|---|---|---|
| **Chip** | Inline mention in prose. Does not leave the document. | Recap tokens; Figma comment pin |
| **Glance** | Small card **anchored to the token**. Document stays. Flip above a bottom dock if needed. | [Figma comment](https://mobbin.com/screens/e58021dc-ffd4-4f86-9a75-af2ea9d7ad17); [Notion person card](https://mobbin.com/screens/1ef5d7e6-0ccb-4997-afb3-d55ba1b56af3); Of Conks `glancePlacement.ts` |
| **Peek sheet** | Table-first object: type, title, At the table, connected chips. IDs / revision / evidence under Advanced. | [Notion side peek](https://mobbin.com/flows/072472b7-2bf2-49bb-88fd-5badeca69a54); Of Conks Play Object Sheet |
| **Advanced** | Graph identity, World revision, evidence counts | `#698` compact card — keep closed by default |

Threats stay a sheet (parchment survivor on `main`: `threatSheetProjection.css`), not a graph table.

---

## 5. Dual aesthetic (paint grammar, not first slice)

Keep native state and composition. Steal Of Conks hierarchy. There are **two styling piles** with different jobs — do not mash them into one theme. The why lives in [`EVIDENCE-of-conks-styling.md`](EVIDENCE-of-conks-styling.md).

- **Dark room chrome** — Nav, rails, graph chips, glances (`#151b28` family).
- **Warm paper instruments** — current recap / Scene / object / threat (`#f7ebd7`, Bookinsanity, gold `#c0ad6a` border, crimson `#a11d18` for *current*).
- **Dark ops handout** — roll table / prepared encounter when those exist (`#14171c` / gold `#d9a441` action). Not chrome. Not a second recap.

These are complementary parts of one product, not competing themes. Navigation/presence is cheap; the current card is expensive. Do not parchment a Roll. Do not dashboard a Scene.

Of Conks locator (feel only — do not merge):

| Evidence | Locator |
|---|---|
| Table-ready prototype / PR #578 | `dogfood/of-conks-hempholm-table-ready` @ `88e4d65e7ed69afe262008749194e2b948ce4c43` |
| Scene deck + parchment stage | `apps/live-control-ui/src/playSurface/beats/beats.css`, `BeatsPanel.tsx` on that tip |
| Object sheet IA + paint | `playObjectSheetProjection.css`, `PlayObjectSheetProjection.tsx` on that tip |
| Parchment on `main` | `apps/live-control-ui/src/statblocks/projection/threatSheetProjection.css` |
| Boutique packet CSS/JS/HTML | `dogfood/of-conks-end-to-end` @ `b40d893f`; added `fe70b6d6574b138dd3cd0c6f7876acc5117020c8` as `evals/of_conks_end_to_end_dogfood/packet/` (`of-conks-packet.css` is **not** on `88e4d65e`) |
| What we liked / keep vs discard | [`EVIDENCE-of-conks-styling.md`](EVIDENCE-of-conks-styling.md) |

Hex values are hierarchy evidence, not a token contract. Do not commit `packet/local/` licensed fixtures.

Directional Play image (hierarchy, not pixels): [`DESIGN-play-surface-gm-cockpit-target.md`](../DESIGN-play-surface-gm-cockpit-target.md). Beat Context / At a Glance / Combat as a permanent right rail in that older image are **not** the product target.

---

## 6. Shipped conventions to steal

Researched 2026-09-10 with Mobbin. One convention per search. Web first.

### Tools and object peek

| Steal | Source |
|---|---|
| Peek is a **column**. Top nav and parent document stay. X closes. | [Notion AI/comments peek](https://mobbin.com/screens/2d0fd0b0-b97a-40ec-ae1d-ec8d9141b49c); [Notion version history](https://mobbin.com/screens/3647446f-f959-4e58-baba-ef7e4f9ab6b0) |
| Linked object = side peek; parent page remains | [Opening a file in side peek](https://mobbin.com/flows/072472b7-2bf2-49bb-88fd-5badeca69a54) |
| List + current item + properties rail; header never disappears | [Linear issue](https://mobbin.com/screens/beb9d6b3-ec34-46d7-9332-320fcb32a338); [Linear Properties](https://mobbin.com/screens/212fda35-366e-4dc0-a1d1-3b679659d6ab) |
| Help as right peek over the list | [Linear Help](https://mobbin.com/flows/e0451091-e059-45c7-848d-1c5f796585a3) |

### Cheap vs expensive

| Steal | Source |
|---|---|
| Thin icon/mode chrome; huge canvas; inspect as a slim rail; tools as a tray **on** the canvas | [Figma editor](https://mobbin.com/screens/ff5d32ce-2368-4734-b6fb-ef161f81a1a5) |
| Glance anchored to the selected object; canvas and bottom tray stay | [Figma comment pin](https://mobbin.com/screens/e58021dc-ffd4-4f86-9a75-af2ea9d7ad17) |

### Agent (parked as its own beast)

| Steal | Source |
|---|---|
| Collapsed Ask is a **tiny dock**, not a chrome band | Linear “Ask Linear” pill on [Pulse](https://mobbin.com/screens/d72f2b29-f2c7-4c5c-ba79-91225b6ae873) |
| Useful Ask is either a **right peek** or a **center mode** (left nav stays). Never a viewport cover over the current work. | [Chatting with AI](https://mobbin.com/flows/3cda8fdd-6bbf-4342-afc3-47baa533bf74); [chat history panel](https://mobbin.com/screens/51c2bd60-f22d-4879-8c28-c5800ac1f4b6) |
| Document left, Agent column with its own composer | [Cofounder](https://mobbin.com/flows/d92842d7-885c-4606-a62c-54b2c6fbabbf); [Obvious](https://mobbin.com/flows/eba63b04-0e95-407e-b2a9-ba4024c165f3) |

### Do not steal

- Notion’s giant left workspace tree as Buddy’s primary nav
- Fabric modal-over-scrim as default object open
- TTRPG marketing “parchment UI” as chrome research (we already have Of Conks tokens)
- Banking onboarding / generic “modern dashboard”
- Restoring Ingest Recap / Open Recap View (`/plan?tool=recap`)

Mobbin did not return a usable Notion `@page` mention hover. Do not keep searching for it. Figma pin + Notion person/map cards are enough for glance.

---

## 7. Recommended first slice (not a lease)

Design-agent pickup (still not a lease): [`HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`](../../Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md). That agent confirms or challenges the proving surface below before anything is dispatched.

Proving surface: **Ingest Graph Review / C2S25**. Play is the visual north star for *grammar*; Ingest is where the chrome fight is visible today.

Invariants:

1. Recap stays the expensive center.
2. Tools and the opened World object share **one right peek**. Top nav stays. Recap does not remount.
3. Collapsed Ask is a **dock**. Unavailable Ask does not keep a sheet-sized `--app-chrome-bottom` reservation.
4. Chip glance stays token-anchored. Click opens the peek, not a new surface.

Named successors remain false in that slice:

- 7A1 Ask-on-this-recap
- Plan generic-lens `?campaign=` World-chip mismatch
- Load-bar lock / Unload
- Play Beat/Scene parchment paint
- Combat-as-Play-mode

---

## 8. Engineering constraint

From root Backlog, still binding:

- Eliminate overlapping fixed-position composition rather than adding z-index exceptions.
- Converge on shared layout / typography / parchment / dark-chrome tokens when a slice touches paint.
- Each cleanup is justified by this language or a bounded defect, not a whole-app rewrite.
