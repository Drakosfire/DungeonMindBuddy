# C2S23 Mireward dogfood notes

**Purpose:** Capture how we use Cursor + DungeonBuddy while planning Mireward, so later review can improve the DungeonBuddy experience.

**Scope:** Queries asked, files opened, panes used, Cursor actions taken, friction observed, and follow-up product ideas. This is **not canon** and not a prep source by itself.

**Last updated:** 2026-06-06 (prep slice committed)

**Related planning docs:**

- `Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md`
- `Docs/Plans/HANDOFF-c2s23-mireward-planning-cursor-first.md`
- `Docs/Plans/HANDOFF-c2s23-hester-edge-opening-combat.md`
- `evals/c2_live_prep/mireward-prep/index.html`

**Delivered slice (for review):** branch `cursor/c2s23-mireward-prep-ui`, commit `24b81b7` — Mireward prep UI, six canonical meat statblocks, north-gate opening lock, NPC seeds.

---

## How to Log

Add a row when an action changes planning state, reveals friction, or suggests a DungeonBuddy feature.

| When | Surface | Query / action | Inputs / files | Result | Friction / opportunity | Follow-up |
|------|---------|----------------|----------------|--------|------------------------|-----------|
| 2026-06-06 | Cursor planning docs | Started dogfood log | This file; `C2S23-MIREWARD-PLANNING-SESSION-NOTES.md` | Created a dedicated place to capture planning queries and Cursor actions | Prior dogfood observations were split across chat, notes, and artifacts | Keep this updated during Hester / Edge / siege planning |
| 2026-06-06 | Cursor chat + corpus | Promote Shepherd's Flock statblocks; ingest one PDF | Unprocessed Mirathorn/Sewers artifacts; `Statblocks and Tokens/` convention; `fleshborn_hybrid_statblock_cr3.md` | Six canonical statblocks + README index; fingerprint pin updated | Agent had to hunt statblock convention; Mark III CUDA failed locally; OCR bodies needed manual markdown cleanup | Corpus-side statblock lint; remote ingest fallback documented in skill |
| 2026-06-06 | Cursor chat + corpus | Lock S23 north-gate opening (party, refugees, clock, Lysandro) | Scaffold §F4; `brin_holloway/character_seed.md`; session notes | Table-ready lock: 55 souls, Brin count drift, 3–8 min meat clock, Lysandro as mobilizer | First draft prose was loose; required a tighten pass before corpus capture | Prompt pattern: "capture + tighten" as explicit operator ask |
| 2026-06-06 | Static prep UI | Build / refresh `mireward-prep` panes | `index.html`, `timeline.html`, `npcs.html`, `roll-tables.html`, `statblocks.html`, `prep.js`, `prep.css` | Command board reflects north-gate lock; inline markdown embeds for tables and statblocks | Roll-table internal codes (`T-DIL-G`) unreadable; `data-repo` paths drifted from canonical corpus; embeds scrolled inside fixed-height boxes | Human titles on pane cards; link checker; full-height expand when `<details open>` |
| 2026-06-06 | Git | Commit scoped prep slice | `cursor/c2s23-mireward-prep-ui` | 47 files pushed; unrelated working-tree dirt left unstaged | Large unrelated deletions in `Docs/Eldyrwild and Campaign Context/` would have polluted PR if not scoped | Scoped staging discipline for mixed worktrees |

---

## Query Log

Use this for natural-language planning questions asked of agents, live query harnesses, or future DungeonBuddy surfaces.

| ID | Question | Surface / tool | Evidence returned | Used in prep? | Notes |
|----|----------|----------------|-------------------|---------------|-------|
| Q-001 | What are we missing from the Mireward siege prep inventory: first combat, town behavior/economics, monster stats, siege mechanics, Celtic punk battlewagon? | Cursor chat | Gap analysis from planning context; no corpus retrieval yet | Yes | Reveals need for a queryable prep inventory / readiness board that separates scenes, setting, mechanics, monsters, factions, and dogfood surfaces. |
| Q-002 | Promote meat statblocks to canonical corpus locations; reference statblock convention; delegate one PDF to RulesIngestion | Cursor chat + subagent | Convention from existing corpus hubs; six promoted sheets + one PDF ingest attempt | Yes | Subagent hit CUDA-unavailable on Mark III; recovered from Stage A surface in unprocessed tree. Product gap: ingest env parity + promotion checklist. |
| Q-003 | S23 opening: 6 L5 PCs, 2 NPC allies, Lysandro mobilizing town; north alarm; refugee count; horde minutes behind | Cursor chat (creative planning partner) | Narrative beat map synthesized from scaffold + Brin seed direction | Yes | Strong model + operator iteration worked well; output needed tightening before canon capture. |
| Q-004 | Capture tightened opening in appropriate documents | Cursor corpus edit | `Mireward_PLACE_BUILD_SCAFFOLD.md`, `brin_holloway/character_seed.md`, session notes step I | Yes | Confirms value of separate "creative pass" then "capture pass" operator commands. |
| Q-005 | Update HTML prep UI to point at new docs; start at `mireward-prep/index.html` | Cursor HTML edit | Command board stats, pane cards, corpus entry links, timeline/NPC cards | Yes | Static UI lagged corpus until explicit refresh ask — no auto-sync from scaffold edits. |
| Q-006 | Roll table names are unreadable (`T-DIL-G`); render tables on-page without click-through | Cursor HTML + `initMarkdownEmbeds` | `roll-tables.html` dashboard with human titles + inline rendered markdown | Yes | Internal table IDs should never be operator-facing labels in prep surfaces. |
| Q-007 | Add statblocks practice pane; review statblock markdown formatting | Cursor HTML + corpus edit | `statblocks.html`; cleaned OCR/HTML in six statblock files | Yes | RulesIngestion exports are not render-ready without a formatting pass. |
| Q-008 | Expanded embeds should be full size, not scroll inside a box | Cursor CSS edit | Removed `max-height` / inner scroll on open `details.fold` | Yes | Small UX fix with high table value during live prep. |

---

## Cursor Action Log

Use this for IDE actions that mattered: opening panes, editing notes, using markdown popup previews, running searches, dispatching agents, or updating handoffs.

| When | Action | Why it mattered | Outcome |
|------|--------|-----------------|---------|
| 2026-06-06 | Logged first dogfood query (`Q-001`) | Starts capturing planning questions as product evidence rather than leaving them only in chat | Added query row and identified need for a prep inventory surface |
| 2026-06-06 | Manual promotion of 6 statblocks + README | Opening combat needs CR-grounded sheets at table | Canonical paths under `Elderwyld/Shephards Flock/Statblocks and Tokens/` |
| 2026-06-06 | Dispatched subagent for `Fleshborn Hybrid.pdf` ingest | Validate automated promotion path | CUDA failure; wrote statblock from existing Stage A surface instead |
| 2026-06-06 | Refactored statblock markdown (tables, casing, actions) | OCR exports broke prep UI rendering | Consistent Stat Summary / Ability Scores / Actions shape across all six |
| 2026-06-06 | Locked north-gate narrative in scaffold + Brin seed | Moves chat decisions into durable prep sources | 55 civilians, alarm shape, road clock, Lysandro mobilizer role |
| 2026-06-06 | Updated session notes step I + open-loops table | Keeps HANDOFF/session-notes pair authoritative | North-gate count/clock marked Locked |
| 2026-06-06 | Built inline markdown embed pipeline (`prep.js`) | Roll tables and statblocks readable without leaving prep UI | `initMarkdownEmbeds`, `excerptMarkdown`, `data-md-embed` pattern |
| 2026-06-06 | Added `statblocks.html` pane + nav entry | Combat prep needs a dedicated mechanical surface separate from roll tables | Six embedded sheets + S23 flank mix callout |
| 2026-06-06 | Fixed broken `data-repo` targets in timeline/npcs/locations | Stale paths silently broke corpus links in static UI | Corrected reach d100 table, Lysandro history, preview dossier note |
| 2026-06-06 | Rebuilt ingested corpus library + fingerprint pin | Corpus edits must stay test-guarded | `expected_fingerprint` → `dfccd0983be1fef891185a63f648ac4b`; step0 pytest green |
| 2026-06-06 | Committed `cursor/c2s23-mireward-prep-ui` (47 files) | Isolates deliverable from unrelated worktree noise | Pushed to origin; PR not yet opened |
| 2026-06-06 | Created siege mechanics + threat inventory handoff | Splits mechanics/threat prep from layout/behavior and first-combat scripting | Added `Docs/Plans/HANDOFF-c2s23-mireward-siege-clocks-threats.md` |

---

## Friction and Product Ideas

| Observation | Why it matters | Candidate DungeonBuddy improvement | Priority |
|-------------|----------------|------------------------------------|----------|
| Static prep panes now support markdown popups, but they require local HTTP rather than `file://`. | Useful for planning, but the run mode is easy to forget. | Add an obvious “served / file mode” status and launch helper in future control surface. | idea |
| Planning state currently lives across handoff, session notes, dogfood notes, static HTML localStorage, and artifacts. | The operator has to remember which surface owns what. | Add a unified planning session ledger that links canon, scratch, dogfood, and artifacts. | idea |
| Internal roll-table IDs (`T-DIL-G`, `T-WX`) appeared as pane titles. | Operator cannot run prep from opaque codes. | Prep UI should always show human titles; reserve IDs for harness/gold only. | **ready** (fixed in static UI; generalize to live control) |
| Embedded markdown used fixed-height scroll boxes. | At table, nested scroll is worse than page scroll. | Default embed behavior: expand to natural height when section is open. | **ready** (fixed in `prep.css`) |
| `data-repo` links drift when corpus paths move. | Broken links fail silently until someone clicks. | CI or prep-build link checker against corpus tree + ingested library. | ready |
| RulesIngestion Stage A statblocks need manual formatting before table use. | OCR casing, HTML tables, stray punctuation break renderers. | Post-ingest statblock normalizer (or stricter Stage A template). | idea |
| Mark III PDF ingest failed locally (CUDA unavailable). | Blocks unattended promotion from PDFs on dev machines without GPU. | Document CPU fallback; or ship fingerprint-matched Stage A reuse in ingest skill. | ready |
| Statblock file convention required agent search to discover. | Promotion is error-prone without a visible checklist. | Surface statblock hub convention in writer allowlist docs + promotion skill. | idea |
| Creative planning output was useful but too loose for corpus on first pass. | Operator needed an explicit "tighten then capture" cycle. | Two-step skill: `plan-beat` (prose) → `capture-beat` (scaffold/NPC seed edits). | idea |
| Static HTML prep UI does not auto-update when corpus scaffold changes. | Operator must remember to ask for HTML refresh after narrative locks. | Scaffold-derived pane generation or manifest-driven prep board. | idea |
| Mixed worktree (500+ unrelated paths) risked over-broad commits. | Scoped staging saved the PR from accidental deletions. | Agent commit skill: always show staged diff stat + explicit allowlist before commit. | ready |

---

## Prep Surfaces Used This Session

| Surface | Role this session | Verdict |
|---------|-------------------|---------|
| Cursor chat (creative planning partner) | North-gate opening, refugee wave, Lysandro beat | **High value** — best for narrative design with operator steering |
| Corpus scaffold + NPC seeds | Durable locks after tighten pass | **High value** — correct promotion target for table facts |
| `mireward-prep/index.html` command board | At-a-glance S23 lock + corpus entry points | **High value** once refreshed |
| `roll-tables.html` inline embeds | Gate/travel tables without file hopping | **High value** after human-title fix |
| `statblocks.html` | Combat mechanical reference | **High value** — should stay a first-class pane |
| Manifest / live-query harness | Used earlier (steps A–B); not re-run this block | Neutral — retrieval already logged in session notes |
| RulesIngestion Mark III (subagent) | One PDF promotion attempt | **Blocked locally** — fallback path worked |

---

## Review Prompts for Later

- Which planning questions were actually useful at the table?
- Which actions required too much manual path handling?
- Which source links were opened repeatedly and should become first-class pane cards?
- Did markdown previews reduce context switching?
- Where did Cursor help as a planning partner, and where did it become bookkeeping?
- Did the north-gate lock (55 / 3–8 min / Lysandro mobilizer) survive first contact at table without rework?
- Were inline statblock renders sufficient for combat, or did the GM still open raw markdown/PDF?
- Should the prep UI be generated from scaffold YAML instead of hand-maintained HTML?
- Did scoped commit discipline prevent a bad merge, and should it become standard agent policy?

---

## Open Dogfood Follow-ups

| Item | Owner | Status |
|------|-------|--------|
| Open PR for `cursor/c2s23-mireward-prep-ui` | Operator / primary agent | Pending |
| North-side combat beat map + layout v0 | Creative planning (handoff §3D–3E) | Open |
| Live-query cost fields in trace artifacts | Harness (logged in session notes) | Open |
| Auto link-check for `mireward-prep` `data-repo` / `data-md-embed` | Engineering backlog | Suggested |
