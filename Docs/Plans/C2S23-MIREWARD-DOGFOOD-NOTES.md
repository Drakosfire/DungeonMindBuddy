# C2S23 Mireward dogfood notes

**Purpose:** Capture how we use Cursor + DungeonBuddy while planning Mireward, so later review can improve the DungeonBuddy experience.

**Scope:** Queries asked, files opened, panes used, Cursor actions taken, friction observed, and follow-up product ideas. This is **not canon** and not a prep source by itself.

**Related planning docs:**

- `Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md`
- `Docs/Plans/HANDOFF-c2s23-hester-edge-opening-combat.md`
- `evals/c2_live_prep/mireward-prep/index.html`

---

## How to Log

Add a row when an action changes planning state, reveals friction, or suggests a DungeonBuddy feature.

| When | Surface | Query / action | Inputs / files | Result | Friction / opportunity | Follow-up |
|------|---------|----------------|----------------|--------|------------------------|-----------|
| 2026-06-06 | Cursor planning docs | Started dogfood log | This file; `C2S23-MIREWARD-PLANNING-SESSION-NOTES.md` | Created a dedicated place to capture planning queries and Cursor actions | Prior dogfood observations were split across chat, notes, and artifacts | Keep this updated during Hester / Edge / siege planning |

---

## Query Log

Use this for natural-language planning questions asked of agents, live query harnesses, or future DungeonBuddy surfaces.

| ID | Question | Surface / tool | Evidence returned | Used in prep? | Notes |
|----|----------|----------------|-------------------|---------------|-------|
| Q-001 | What are we missing from the Mireward siege prep inventory: first combat, town behavior/economics, monster stats, siege mechanics, Celtic punk battlewagon? | Cursor chat | Gap analysis from planning context; no corpus retrieval yet | Yes | Reveals need for a queryable prep inventory / readiness board that separates scenes, setting, mechanics, monsters, factions, and dogfood surfaces. |

---

## Cursor Action Log

Use this for IDE actions that mattered: opening panes, editing notes, using markdown popup previews, running searches, dispatching agents, or updating handoffs.

| When | Action | Why it mattered | Outcome |
|------|--------|-----------------|---------|
| 2026-06-06 | Logged first dogfood query (`Q-001`) | Starts capturing planning questions as product evidence rather than leaving them only in chat | Added query row and identified need for a prep inventory surface |

---

## Friction and Product Ideas

| Observation | Why it matters | Candidate DungeonBuddy improvement | Priority |
|-------------|----------------|------------------------------------|----------|
| Static prep panes now support markdown popups, but they require local HTTP rather than `file://`. | Useful for planning, but the run mode is easy to forget. | Add an obvious “served / file mode” status and launch helper in future control surface. | idea |
| Planning state currently lives across handoff, session notes, dogfood notes, static HTML localStorage, and artifacts. | The operator has to remember which surface owns what. | Add a unified planning session ledger that links canon, scratch, dogfood, and artifacts. | idea |

---

## Review Prompts for Later

- Which planning questions were actually useful at the table?
- Which actions required too much manual path handling?
- Which source links were opened repeatedly and should become first-class pane cards?
- Did markdown previews reduce context switching?
- Where did Cursor help as a planning partner, and where did it become bookkeeping?
