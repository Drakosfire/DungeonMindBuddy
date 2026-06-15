# Design: Mireward Command Board shell (navigation, toolbox, corpus indexes)

**Status:** Living decisions record — reflects static prep UI as of 2026-06-13  
**Scope:** `evals/c2_live_prep/mireward-prep/` layout, shared chrome, and the statblocks / NPCs / roll-tables rework  
**Related:**

- `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md` — combat + generator product thesis
- `Docs/Plans/HANDOFF-pr115-statblock-mock-dogfood-then-api-wire.md` — dogfood step-through and API touchpoints
- `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md` — operator friction log

---

## 1. Product stance

| Decision | Rationale |
|----------|-----------|
| **Static Command Board is the primary at-table product.** React `/surface` stays a legacy / idea-mining surface, not the default path. | Dogfood showed the GM wants small, fast, locally persistent surfaces. Static HTML + Vite + `/api/live/*` proxy matches that without SPA ceremony. |
| **Live Play (`live-play.html`) is the launch hub**, not the root Vite launcher alone. | Root launcher routes into prep; Live Play separates *at-table launch cards* from supporting prep panes and provenance. |
| **Combat tracker remains the highest-priority launch card.** Statblocks, roll tables, and NPCs are reference panes adjacent to the fight. | Matches “rows first, drilldown second” from combat dogfood. |

---

## 2. Two-layer navigation

The shell deliberately separates **where you are in the prep site** from **what you do on this page**.

```text
┌─────────────────────────────────────────────────────────────┐
│  site-nav (global) — every page, same 10 links              │
├─────────────────────────────────────────────────────────────┤
│  page header: h1 + lead + page toolbar (contextual)        │
├─────────────────────────────────────────────────────────────┤
│  primary content (dynamic index, combat grid, etc.)         │
├─────────────────────────────────────────────────────────────┤
│  muted fold sections: session locks, corpus pointers        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    [Tools] edge tab → toolbox drawer (global overlay)
```

### 2.1 Global site nav (`site-nav`)

- **Single source of truth:** `NAV` array in `evals/c2_live_prep/mireward-prep/assets/prep.js`; each page calls `MirewardPrep.initNav("<page-id>")`.
- **Placement:** Top of `.wrap`, full width, horizontal pill links with bottom border separating chrome from content.
- **Active state:** Current page gets accent border + subtle background; no dropdowns or nested menus.
- **Order:** Index → Live play → Retrieval → Combat → Live notes → Timeline → Locations → NPCs → Roll tables → Statblocks.
- **Why top bar, not sidebar:** Prep pages are read-heavy and narrow (~960px). A horizontal nav preserves vertical space for accordions and combat rows; the GM scans left-to-right once per page load.

### 2.2 Page toolbar (per-pane secondary nav)

Each reference pane adds a **toolbar row under the lead paragraph** — not a second global nav, but contextual cross-links and actions:

| Page | Toolbar contents | Intent |
|------|------------------|--------|
| **Statblocks** | `Command toolbox` (primary button), link to Combat tracker, live count pill | Generation is an action; combat is the consumer of accepted drafts. |
| **Roll tables** | Links to Live play, Locations, NPCs, count pill | Tables sit between scene (locations), cast (NPCs), and session hub. |
| **NPCs** | Links to Live play, Locations, Statblocks, count pill | Cast index points at place and mechanics without duplicating global nav. |
| **Locations** | Links to Live play, Roll tables, NPCs, count pill | Place index points at travel tables and cast without duplicating global nav. |

**Convention:** Toolbar links use `{page}-toolbar` / `{page}-toolbar-link` CSS classes. Count pills show corpus index size after API load (`#statblock-index-count`, etc.).

**Non-goal:** Toolbars do not replace `site-nav`. They shortcut the 2–3 panes most often used *from* this pane during prep.

---

## 3. Command toolbox drawer

Interactive tools that are **global** (usable from any page) live in a right-side drawer, not inline in page bodies.

| Decision | Detail |
|----------|--------|
| **Mount once on `document.body`** | `ensureToolboxDrawer()` injects `#prep-toolbox` on first `initToolbox()`; all pages share one instance. |
| **Open paths** | Floating edge **Tools** tab; `[data-open-toolbox="statblock"]` buttons (statblocks page header); persisted reopen via `localStorage` keys `toolboxOpen` / `toolboxTool`. |
| **Layout** | Fixed right drawer (~440px), backdrop dim, header with “Command Board / Toolbox”, **internal tool nav** (pill buttons), scrollable body. |
| **Tool nav inside drawer** | Horizontal pill row (`prep-toolbox-nav`) switches panels — extensible when more tools land (recap hints, dice, etc.). First tool: **Statblock** generator dogfood. |
| **Escape / focus** | Escape closes drawer unless markdown modal is open; body scroll locked while open. |
| **Mobile** | Edge tab moves to bottom-left; drawer still full-height slide-over. |

**Why drawer + page toolbar button:** Statblock generation is adjacent to combat prep but not owned by the statblocks *list* page. Moving the generator out of inline HTML keeps the corpus index clean while keeping the tool one click away from statblocks and reachable elsewhere.

**Implementation refs:** `ensureToolboxDrawer`, `setToolboxOpen`, `wireToolboxControls`, `statblockDogfoodPanelHtml` in `prep.js`; styles under `.prep-toolbox-*` in `prep.css`.

---

## 4. Dynamic corpus indexes (statblocks, NPCs, roll tables)

Hand-curated card grids were replaced with **server-built indexes + client render**.

| Decision | Detail |
|----------|--------|
| **API-first listing** | `GET /api/live/statblocks/index`, `/npcs/index`, `/roll-tables/index` — read-only crawlers in `apps/live_control_server/services/*_corpus_index.py`. |
| **Allowlisted roots only** | Each crawler enumerates explicit corpus subtrees (NPC hubs, Session 22 prep folder, roads/wilderness, generated statblocks lane). No whole-corpus glob in the UI layer. |
| **Client host div per page** | `#statblock-corpus-index`, `#npc-corpus-index`, `#rolltable-corpus-index` — fetch on load, render HTML string, then `initMarkdownEmbeds()`. |
| **Refresh after promote** | Statblock corpus promote dispatches `mireward-prep:statblock-corpus-index-refresh`; index re-fetches silently. |
| **`file://` guard** | Dynamic indexes require Vite + API proxy; show explicit callout if opened as raw files. |
| **Deferred:** unified query layer | Third bespoke crawler increases pressure for DB / index / GraphQL — tracked in `Backlog.md` (IDEA). |

**Why not manifest YAML in static HTML:** Corpus changes frequently during C2S23 prep. Indexes follow hub READMEs and filenames on disk so promoted statblocks and new Session 22 tables appear without editing HTML.

---

## 5. Accordion and list UX

Shared pattern across the three reference panes:

### 5.1 Section groups + row accordions

- **Outer `<details class="fold fold-section">`** — logical group (e.g. “Session 22 table tools”, “Mireward table faces”, “Generated from toolbox”).
- **Inner `<details class="fold *-row">`** — one corpus entity per row.
- **Default open policy:** Session-critical groups **open** on load (Session 22 tables, Mireward NPCs, generated statblocks). Broad reference groups (roads, wilderness, Campaign 2 NPCs, Shepherd's Flock) **collapsed** to reduce noise.
- **Muted sections** (`fold-muted`) — provenance, authority notes, encounter mix callouts below the dynamic index.

### 5.2 Summary line rules (operator-facing labels)

| Pane | Summary shows | Hidden until expand |
|------|---------------|---------------------|
| **Roll tables** | Human table title only. Strip `Session N —` prefix from frontmatter titles so summaries read “Mirathorn comms retry d100”, not “Session 22”. | Section pill (S22/scaffold/road), harness `table_id`, dice type, source link, `table_note`, embedded markdown. |
| **NPCs** | Display name from hub + section pill (Mireward vs C2). | Hub/seed/dossier/timeline links, primary doc embed. |
| **Statblocks** | Creature name (+ CR suffix when known) + optional role pill. | Corpus file link, full sheet embed. |

**Explicit rejection:** Internal harness IDs (`T-DIL-G`, `T-COMMS`) must never be the accordion summary — operator cannot run prep from opaque codes. IDs may appear as neutral pills inside the expanded body.

### 5.3 Embed behavior

- **`data-md-embed`** lazy-loads corpus markdown into the row body on expand.
- **Scaffold excerpts** support `data-md-start` / `data-md-end` for partial embeds (e.g. marcher kit from Mireward scaffold).
- **No nested scroll boxes** when a fold is open — embeds grow to natural height; page scroll only (`prep.css` lesson from dogfood).
- **`data-repo` / `data-md-embed-link`** opens **markdown modal** (`md-viewer`) for quick preview without leaving the pane; raw link still available.

---

## 6. What stays hand-authored on each page

Dynamic indexes cover **inventory from corpus**. These blocks remain **curated HTML** below the index:

- Session encounter mix / north-gate pressure maps (S23-specific fiction locks).
- Authority / canon notes (`reference_tool` vs `planning_scaffold`).
- File-row pointers to scaffold, siege docs, eval artifacts.

**Rule of thumb:** If it is **table state for one session** or **cross-links to planning docs**, keep it in static HTML. If it is **a list of corpus entities that churn**, drive it from the index API.

---

## 7. Persistence and serving

| Surface | Storage | Notes |
|---------|---------|-------|
| Combat state | `localStorage` + JSON import/export | Primary live loop; see combat save schema in dogfood handoff. |
| Toolbox open/tool | `localStorage` | Survives reload; use consistent host (`127.0.0.1` not `localhost`) to avoid split keys. |
| Scratch / timeline checks | `localStorage` | Live notes and timeline beat toggles. |
| Corpus content | Git corpus | Promote via two-phase writer; index reflects after refresh. |

**Serving:** Vite on `:5173` proxies `/api` → FastAPI `:8000`. Markdown embeds and indexes are **degraded** on `file://`.

---

## 8. Decisions explicitly deferred

- **Generating prep HTML from scaffold YAML** — still manual refresh when narrative locks change; index APIs reduce but do not eliminate this.
- **React module parity** — patterns here are harness/product evidence for a future live-control combat module, not a directive to rewrite static pages in React.
- **Link checker CI** for `data-repo` / embed paths — suggested in dogfood backlog, not implemented.
- **Toolbox tools beyond statblock** — drawer nav is ready; only statblock panel ships in this slice.

---

## 9. File map (shell touchpoints)

| Concern | Files |
|---------|-------|
| Shared JS | `evals/c2_live_prep/mireward-prep/assets/prep.js` — `NAV`, `initNav`, toolbox, `init*CorpusIndex`, markdown modal/embed |
| Shared CSS | `evals/c2_live_prep/mireward-prep/assets/prep.css` — `.site-nav`, `.*-toolbar`, `.prep-toolbox-*`, `.fold` |
| Pages | `live-play.html`, `statblocks.html`, `npcs.html`, `roll-tables.html`, … |
| Index services | `apps/live_control_server/services/{statblock,npc,roll_table,location}_corpus_index.py` |
| Routes | `apps/live_control_server/routes/live.py` — `/api/live/*/index` |

---

## 10. Review prompts

When changing the shell, ask:

1. Does this belong in **global nav**, **page toolbar**, **drawer**, or **page body**?
2. Will a new list be **hand-curated** again, or should it get an **allowlisted index**?
3. Are operator labels **human titles**, not harness IDs or filename stems?
4. Does an open accordion **scroll the page**, not a nested box?
5. Does the feature work on **`127.0.0.1:5173`**, not only `file://`?
