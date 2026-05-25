# Study — C2 Live Play Cursor Handoff Process

**Source export:** `/home/drakosfire/Documents/cursor_handoff_process_for_live_play_ag.md`
**Exported:** 2026-05-24 19:04 MDT from Cursor 3.3.22
**Use with:** `PLAN-c2-live-control-surface-query-pane.md` and `CHECKLIST-c2-live-control-surface-query-pane.md`

This is a product-memory study note, not a canonical play log. Its job is to preserve what felt useful, slow, and frustrating in the Cursor-based live-play workflow so the Query Pane v0 does not accidentally rebuild an IDE dashboard.

The full export is large (~100k chars). Keep it local as the raw transcript. This file is the repo-local anchor future agents should read first.

---

## Why This Matters

Cursor proved the workflow but also exposed the product gap:

- The live-play agent could re-anchor, resolve rolls, read corpus, log staging notes, and update planning surfaces.
- The interaction still felt like talking to a repo agent through an IDE: too much file-path thinking, too much waiting for background context, and too much manual “where does this go?” discipline.
- The product surface needs to preserve the discipline while hiding the scaffolding.

The live-control UI should make the successful flow feel native:

```text
GM types a live turn
→ DungeonBuddy classifies mode
→ fast answer appears
→ event log / open loops / roll stack update
→ slow propagation is queued, not forced through the chat loop
```

---

## High-Signal Friction Captured In The Export

### 1. Dashboard Was The Wrong Shape

Initial canvas output was an artifact/register dashboard: stats, charts, filters, persistent checklist state.

The user pivot was explicit:

> “Lets reimagine this, not as presenting data but as a useful tool to interact with while planning.”

Product lesson:

- Do not lead with artifact inventories.
- Do not make file names the primary UI.
- Do not make the GM parse repository structure to run a session.

### 2. The Useful Surface Was A Session-Run Projection

The user described the desired shape:

> “I want to be able to have a view that is a simple timeline I can reference of key beats, holding the different rolls together. I'm also using it during actual play to view details, expand roll tables and to have em handy.”

And the highest friction:

> “It’s hard to parse. It doesn’t interlink itself so I can’t click a roll table and expand it. It’s presenting file names and not titles of sections and roll tables. It needs to be closer to a project plan and prose than data tables.”

Product lesson:

- The UI needs human labels: **Storm weather**, **Road encounter**, **Gate dilemma**, not `travel_storm_weather_d20.md`.
- Roll tables must expand inline.
- Beat tabs / focused panes are better than a scroll of everything.
- The product should be a projection of source truth, not a second truth surface.

### 3. Source-Of-Truth Discipline Was Valuable But Too Manual

The export repeatedly reinforced:

- R1 journey tracker = scratch state for clock/weather/comms.
- `_ingest_staging/session_22_raw_notes.md` = staging before recap.
- T-* / R5 / R6 files = prompts, not session logs.
- Recap wins as table canon.
- Dossiers/statblocks should not become mid-session play logs.

Product lesson:

- The UI must make the right destination obvious.
- A live event should be appended once, with structured event type/provenance.
- Slow propagation should become jobs, not inline multi-file edits.

### 4. Prep Includes Future Planning, Not Just Runnable Session Artifacts

The Mirathorn arc segment proved that a useful GM prep flow spans multiple time horizons:

```text
Conversation / GM vision
→ arc lock document
→ comms index + roll table + remote-state doc + hub rows
→ register / knobs
→ promotion rule
```

Product lesson:

- Query Pane v0 is live-first, but the architecture must leave room for `prep_architect`.
- Not every “what’s happening?” answer is a live roll lookup.
- Future planning should remain planning-tier until the table learns it.

### 5. Fast Live vs Slow Architecture Needs A Hard Boundary

The transcript shows very different query classes:

| Query shape | Desired product behavior |
|-------------|--------------------------|
| `Weather 7. Caelynn Nature 19.` | Fast roll lookup + event write + next beat suggestions. |
| `Grobnok does not call in the morning.` | Fast open-loop update; evening contact remains owed. |
| `What is Lysandra feeling at the gate?` | Context lookup from packet/sources, not a roll resolver. |
| `Lysandro is her father.` | Canon correction event + queued post-session propagation. |
| “Build a d100 comms table” | Background worker / handoff, not live answer stream. |

Product lesson:

- `fast_live` should be deterministic and local.
- `context_lookup` may expose packet evidence and provenance.
- `prep_architect` and `post_session` are not live latency modes.

---

## UI Design Guardrails To Re-read Before L4

- One pane first. Do not build the full control surface.
- Query-first, state-aware.
- Human labels first; paths in captions or source panels.
- Inline expandable roll tables.
- Show **Now**, **Open Loops**, **Roll Stack**, **Sources**, **Queue**.
- Do not make UI source of truth.
- Do not silently patch five corpus files during live play.
- Make “queued propagation” visible and boring.
- Preserve the ability to show provenance when a context lookup happens.
- If it starts feeling like a Cursor canvas/dashboard, stop and re-check this study.

---

## Concrete Test Prompts From The Export

Use these as product-regression examples:

```text
Weather 7. Caelynn Nature 19.
Weather 16.
R5 54.
Grobnok does not call in the morning.
Caelynn bottles the puddle water.
What is Lysandra feeling at the gate?
Lysandro is her father.
They push through and arrive at Mireward outskirts at 10 pm.
```

Expected product behavior:

- No repo-wide search for roll lookups.
- Open-loop updates are visible.
- Roll stack changes are visible.
- Context answers show sources/provenance.
- Corpus propagation is queued unless explicitly in post-session mode.

---

## Relationship To The Raw Export

Raw export stays at:

```text
/home/drakosfire/Documents/cursor_handoff_process_for_live_play_ag.md
```

Read the raw export when you need:

- Exact phrasing of the canvas frustration.
- Full sequence of dashboard → timeline → beat tabs.
- Full Session 22 live-play query stream.
- More seed examples for classifier tests.

Use this repo-local study note when you need:

- The product lesson.
- The UI guardrails.
- The next-sprint memory trigger.
