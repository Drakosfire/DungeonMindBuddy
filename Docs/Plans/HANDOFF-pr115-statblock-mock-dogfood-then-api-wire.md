---
document_id: dmb-handoff-pr115-statblock-mock-dogfood-then-api-wire
title: "HANDOFF — Command Board statblock generation dogfood, step by step"
document_class: planning
plan_kind: handoff
status: partial — dynamic command-board indexes done; React `/surface` still non-primary
version: 2.4
created_at: "2026-06-12T00:00:00Z"
last_updated_at: "2026-06-13T21:11:00Z"
branch_anchor: cursor/c2s23-mireward-prep-ui
related_design:
  - Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md
  - Docs/Design/DESIGN-mireward-command-board-shell.md
related_plan:
  - Docs/Plans/PLAN-command-board-combat-statblock-generator-roadmap.md
related_runbook:
  - Docs/Runbooks/RUNBOOK-statblock-combat-dogfood.md
supersedes_framing:
  - Docs/Plans/HANDOFF-command-board-combat-statblock-generator-design.md
---

# HANDOFF — Command Board statblock generation dogfood, step by step

## §0 Mission

Dogfood statblock generation on the **static Command Board**, one observable step at a
time. Do not move this work back to the React `/surface` app.

Primary goal:

```text
servers running
→ root launcher works
→ Live Play / Command Board is clear
→ Statblock generator panel is reachable
→ mock generation returns a draft
→ draft renders on the static page
→ Accept writes a generated enemy into combat.html localStorage state
→ combat.html shows the generated enemy
→ record friction/refinements
→ only then wire real DungeonMind API behind the same flow
```

The agent may combine tightly connected checks when it has direct evidence, but the
handoff is intentionally written as a step-through script. Prefer visible observations
over broad claims.

---

## §1 Terms and Routes

Use these terms exactly:

| Term | Meaning |
|---|---|
| **Command Board** | The primary static Mireward prep UI served from `evals/c2_live_prep/mireward-prep/`. |
| **Root launcher** | `http://127.0.0.1:5173/`. |
| **Live Play / Command Board Home** | `/live-play`. |
| **Combat Tracker** | `/combat.html`; browser-local `localStorage` combat state. |
| **Statblock Page** | `/statblocks.html`; dynamic rendered corpus sheets plus mock generator dogfood panel. |
| **NPC Page** | `/npcs.html`; dynamic cast index from allowlisted NPC corpus hubs. |
| **Roll Tables Page** | `/roll-tables.html`; dynamic table index from allowlisted roll-table corpus paths. |
| **React live-control surface** | `/surface`; legacy/idea-mining surface, **not primary**. |

Current implementation touchpoints:

- Static pages: `evals/c2_live_prep/mireward-prep/*.html`.
- Static JS/CSS: `evals/c2_live_prep/mireward-prep/assets/prep.js`,
  `evals/c2_live_prep/mireward-prep/assets/prep.css`.
- Mock endpoint already used by the static page:
  `POST /api/live/statblocks/workbench/command`.
- Vite static middleware and `/api` proxy:
  `apps/live-control-ui/vite.config.ts`.

---

## §2 Before Starting: Server State

### Step 2.1 — Check whether servers are already running

Look for existing terminal output before starting new servers. Expected healthy servers:

- FastAPI backend: `http://127.0.0.1:8000`
- Vite UI/static server: `http://127.0.0.1:5173`

If both are running, do not start duplicates.

### Step 2.2 — If FastAPI is not running, start it

Run from repo root:

```bash
export DUNGEONMIND_LIVE_SESSION_DIR="$PWD/evals/c2_live_prep/live/session_23"
uv run uvicorn apps.live_control_server.main:app --host 127.0.0.1 --port 8000
```

Expected:

- Terminal prints `Uvicorn running on http://127.0.0.1:8000`.
- API does not need to serve HTML; it only serves `/api/live/*`.

### Step 2.3 — If Vite is not running, start it

Run from repo root:

```bash
npm --prefix apps/live-control-ui run dev -- --host 127.0.0.1 --port 5173
```

Expected:

- Terminal prints a local URL at `http://127.0.0.1:5173/`.
- Vite serves static Command Board pages.
- Vite proxies `/api` to FastAPI on `8000`.

If `npm` cannot find local binaries (`tsc`, `vite`, or test binaries), report that as a
local Node install gap. Do not switch the product target to `/surface`.

---

## §3 Root Launcher Smoke

### Step 3.1 — Open root

Open:

```text
http://127.0.0.1:5173/
```

Expected:

- Page title/context is Mireward local tools.
- There is a **Live Play / Command Board** card.
- There is a **React surface** card, but it is not the primary product path for this work.

Pass condition:

- The root page is served by Vite on `5173`.
- You can click into `/live-play`.

Fail condition:

- If root is blank, 404, or opens an old `8765` server flow, stop and fix serving before
  continuing.

---

## §4 Live Play / Command Board Home

### Step 4.1 — Click Live Play

From root, click the Live Play / Command Board card.

Expected route:

```text
http://127.0.0.1:5173/live-play
```

Expected page:

- Heading: `Mireward command board`.
- At-table launch cards include:
  - `North Reach Gate combat tracker`
  - `Live notes`
  - `Statblock drilldown + generator`
  - `Roll tables`
- The React live-control surface appears only under legacy/reference language.

Pass condition:

- The page makes it clear the static Command Board is primary.

Fail condition:

- If the page suggests `/surface` is primary, revise copy before continuing.

---

## §5 Open the Statblock Generator Panel

### Step 5.1 — Click Statblock Drilldown + Generator

From `/live-play`, click:

```text
Statblock drilldown + generator
```

Expected route:

```text
http://127.0.0.1:5173/statblocks.html
```

Expected page:

- Heading: `Statblocks`.
- Near the top, a card titled:

```text
Command Board statblock generation
```

- The card has:
  - a textarea labeled `Generation prompt / table need`
  - `Generate mock reinforcement`
  - `Render mock existing`
  - `Accept to combat tracker`
  - status text starting with `Ready. Mock provider only; no corpus write.`

Pass condition:

- `Accept to combat tracker` is disabled before a draft exists.
- The existing rendered statblocks still appear below the dogfood panel.

Fail condition:

- If the panel is absent, inspect `statblocks.html` and `MirewardPrep.initStatblockGeneratorDogfood()`.
- If rendered statblocks disappeared, inspect `MirewardPrep.initMarkdownEmbeds()`.

---

## §6 Generate a Mock Draft

### Step 6.1 — Click Generate Mock Reinforcement

Click:

```text
Generate mock reinforcement
```

Expected network/API behavior:

- Browser calls `POST /api/live/statblocks/workbench/command`.
- Request uses `command_type: "statblock.draft.generate"`.
- Backend uses the existing mock provider.
- No corpus write happens.
- No semantic ingest happens.
- No combat mutation happens yet.

Expected UI behavior:

- The dogfood panel renders a draft inline.
- Current deterministic mock title should be:

```text
Generated Obsidian Thornling
```

- The rendered draft shows markdown content including:
  - `Armor Class 14`
  - `Hit Points 45`
  - `Actions`
  - `Splinter Thorn`
  - `Root Snare`
- The combat defaults card shows:
  - name: `Generated Obsidian Thornling`
  - AC: `14`
  - HP: `45`
  - initiative bonus: `3`
  - actions: `Splinter Thorn, Root Snare`
- `Accept to combat tracker` becomes enabled.

Pass condition:

- Draft is visible and readable inside the static page without opening `/surface`.

Fail condition:

- If status shows an HTTP error, verify FastAPI on `8000` and Vite `/api` proxy on `5173`.
- If text is unrendered markdown or blank, inspect `prep-markdown.js` and
  `renderDogfoodArtifact()`.

---

## §7 Optional Render Existing Check

### Step 7.1 — Click Render Mock Existing

This is optional but useful to confirm both mock command modes are reachable.

Click:

```text
Render mock existing
```

Expected deterministic mock title:

```text
Rendered Clockwork Mire Sentinel
```

Pass condition:

- The panel replaces the prior draft with a rendered mock-existing draft.

Fail condition:

- If generate works but render fails, inspect `command_type: "statblock.draft.render"` in
  `initStatblockGeneratorDogfood()`.

Note: If the goal is to test accept-to-combat with `Generated Obsidian Thornling`, click
`Generate mock reinforcement` again before accepting.

---

## §8 Accept to Combat Tracker

### Step 8.1 — Click Accept

With a visible draft, click:

```text
Accept to combat tracker
```

Expected behavior:

- The page writes a new generated enemy into browser localStorage key:

```text
mireward-prep.combat.northReachGate
```

- No corpus file is created.
- No backend combat state (`current_combat.json`) is required.
- Status text says the generated creature was added and points you to `combat.html`.

Pass condition:

- Status mentions the generated creature name and says it was added to the local combat
  tracker.

Fail condition:

- If status changes but combat does not update in §9, inspect
  `addGeneratedArtifactToCombat()` and `normalizeCombatState()`.

---

## §9 Verify Combat Tracker Reads the Generated Entity

### Step 9.1 — Open Combat Tracker

Open:

```text
http://127.0.0.1:5173/combat.html
```

Expected:

- Combat tracker loads from browser localStorage.
- Existing North Reach Gate roster still exists.
- The generated enemy appears as an enemy row.

If using the default generated mock, expected generated row:

```text
Generated Obsidian Thornling
```

Expected row fields:

- AC: `14`
- HP: `45 / 45`
- Notes include:

```text
init +3; generated draft; Splinter Thorn, Root Snare
```

Pass condition:

- Generated row is visible after navigating away from `statblocks.html`.
- Refreshing `combat.html` keeps the row.
- Local combat tracker controls still work on the generated row.

Fail condition:

- If the row appears then disappears on refresh, inspect the generated-entity preservation
  branch in `normalizeCombatState()`.
- If multiple generated rows appear, that may be normal from repeated clicks; either keep
  them for dogfood or use Combat Tracker → `Reset combat state` to return to baseline.

---

## §10 Verify State Survival

### Step 10.1 — Refresh Combat Tracker

Refresh:

```text
http://127.0.0.1:5173/combat.html
```

Expected:

- Generated enemy still appears.
- HP/AC/notes values persist.

### Step 10.2 — Optional export check

Click:

```text
Export state
```

Expected:

- Browser downloads `mireward-north-reach-gate-combat-state.json`.
- Exported JSON includes the generated enemy.

Pass condition:

- Generated combatant survives navigation/refresh and, optionally, export.

---

## §11 Record Dogfood Friction Before Refining

After the step-through flow works, record observations in:

```text
Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md
```

Use concrete observations:

- Which route was open?
- What did you click?
- What happened?
- What was confusing?
- What expected at-table behavior was missing?

Examples of likely refinements:

- The generated draft needs editing before acceptance.
- The accept button should ask for team/name/count.
- The generated row needs an inline "view generated draft" affordance.
- Mock/real provider mode needs stronger visual labeling.
- The panel belongs on `combat.html` as well as `statblocks.html`.

Do not jump to the real API until the mock flow is understandable.

---

## §12 Real DungeonMind API: Only After Mock Flow Passes

The real API work should preserve the static Command Board flow:

```text
statblocks.html button
→ /api endpoint
→ server-side provider (mock or http)
→ same artifact shape
→ same static render
→ same Accept to combat tracker behavior
```

Known provider seam:

- `src/statblocks/v2_client.py` has `statblock_generator_provider_from_env()`.
- **Done (2026-06-13):** `statblock_workbench.py` uses
  `statblock_generator_provider_from_env()` — `mock_command` default in tests;
  `http_command` when `STATBLOCK_GENERATOR_PROVIDER=http`.
- **Done:** `intent.summary` backfilled from prompt when omitted (production 422 fix).
- **Done:** Live Palisade Gnawer CR 5 generated via HTTP; corpus promote lane proven
  (`generated_obsidian_thornling.md`, `palisade_gnawer.md` under
  `.../Statblocks/generated/`).
- **Done:** Toolbox drawer on static Command Board; single **Confirm corpus write**
  (prepare→commit internal); promoted-state UX (toast, banner, **In corpus** pill).
- **Done (2026-06-13):** Dynamic statblocks page crawls allowlisted corpus paths via
  `GET /api/live/statblocks/index`; toolbox promote refreshes the list in-place.
- **Done (2026-06-13):** Dynamic NPC page crawls allowlisted Mireward + Campaign 2
  NPC hubs via `GET /api/live/npcs/index`; rows embed primary seed/dossier docs.
- **Done (2026-06-13):** Dynamic roll-tables page crawls allowlisted Session 22,
  Mireward scaffold, roads, and wilderness table paths via
  `GET /api/live/roll-tables/index`; rows embed table markdown/excerpts.

Real-provider environment:

```text
STATBLOCK_GENERATOR_PROVIDER=http
DUNGEONMIND_SERVER_URL=<server base URL if not default>
DUNGEONBUDDY_INTERNAL_API_KEY=<loaded from env file, never echoed>
```

Before first real generation:

1. Verify health endpoint first.
2. Surface cost in the result or notes.
3. Confirm no corpus write occurs during combat acceptance.
4. Keep corpus promotion as a separate two-phase write flow.

---

## §13 Verification Commands

Run after any code change in this slice:

```bash
node --check evals/c2_live_prep/mireward-prep/assets/prep.js
uv run pytest tests/test_live_statblock_workbench_endpoint.py
```

Also use browser smoke against `http://127.0.0.1:5173/statblocks.html#statblock-dogfood`.

Current known environment caveat:

- `npm --prefix apps/live-control-ui run build` may fail locally with `tsc: not found`
  if Node dependencies are not installed/resolved. Report that as an environment gap;
  do not treat it as a reason to move work to `/surface`.

---

## §14 Non-Goals

- Do not target `/surface` unless the user explicitly says "React live-control surface."
- Do not use `current_combat.json` as the primary Command Board combat state.
- Do not require corpus promotion before combat acceptance.
- Do not write statblocks directly to corpus files from the dogfood panel.
- Do not restore old `8765` serving as the main path.
- Do not collapse this into a broad redesign before the click-by-click dogfood flow is
  observed.

---

## §15 Files

Primary static Command Board files:

- `evals/c2_live_prep/mireward-prep/live-play.html`
- `evals/c2_live_prep/mireward-prep/npcs.html`
- `evals/c2_live_prep/mireward-prep/roll-tables.html`
- `evals/c2_live_prep/mireward-prep/statblocks.html`
- `evals/c2_live_prep/mireward-prep/combat.html`
- `evals/c2_live_prep/mireward-prep/assets/prep.js`
- `evals/c2_live_prep/mireward-prep/assets/prep.css`

Backend/mock contract files:

- `apps/live_control_server/services/statblock_workbench.py`
- `apps/live_control_server/services/npc_corpus_index.py`
- `apps/live_control_server/services/roll_table_corpus_index.py`
- `apps/live_control_server/services/statblock_corpus_index.py`
- `apps/live_control_server/routes/live.py`
- `src/statblocks/v2_client.py`
- `src/statblocks/v2_contract.py`
- `tests/test_live_statblock_workbench_endpoint.py`
- `tests/test_npc_corpus_index.py`
- `tests/test_roll_table_corpus_index.py`
- `tests/test_statblock_corpus_index.py`

Dogfood notes:

- `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md`

---

## §16 Progress log (2026-06-13)

| Step | Status | Evidence |
|------|--------|----------|
| Mock generation on static statblocks page | ✅ | `STATBLOCK_GENERATOR_PROVIDER=mock`; Obsidian Thornling fixture |
| HTTP provider wire | ✅ | `statblock_workbench.py`; 31 endpoint tests + 3 HTTP/fake-provider |
| Rich v2 payload (`intent.summary`, encounter context) | ✅ | `prep.js`, `v2_contract.py`, fixture JSON |
| Toolbox drawer (not page-only button) | ✅ | `prep.js` / `prep.css` |
| Corpus promote two-phase write | ✅ | `write_corpus_file` via live API; allowlisted generated path |
| Promote UX (toast, Done, In corpus, already-exists) | ✅ | Single Confirm button; no separate Prepare step |
| Statblocks page collapsed by default | ✅ | `statblocks.html` |
| Live Palisade Gnawer generation | ✅ | HTTP smoke; artifact + corpus file on disk |
| Dynamic statblocks index after promote | ✅ | `statblock_corpus_index.py`; `GET /api/live/statblocks/index`; `initStatblockCorpusIndex()` |
| Dynamic NPC index from corpus hubs | ✅ | `npc_corpus_index.py`; `GET /api/live/npcs/index`; `initNpcCorpusIndex()` |
| Dynamic roll-table index from corpus paths | ✅ | `roll_table_corpus_index.py`; `GET /api/live/roll-tables/index`; `initRollTableCorpusIndex()` |

**Operator caveat:** use one origin consistently (`127.0.0.1` vs `localhost`) so
localStorage draft state matches between tabs.
