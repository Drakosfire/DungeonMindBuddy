# /plan Dogfood Runbook

## Purpose

Use `/plan` for a real prep pass and capture feedback on the current prep cockpit.

`/plan?dogfood=1` is an **operator measurement scaffold** (checklist, notes, report copy). It is not the final product shape. Judge success against the real prep loop — board, save/recovery, reference inspection, World Graph cards, prep-memory Q&A, `/ingest` escalation — not against checklist completeness as a UI destination.

**Product authority:** `Docs/Design/DESIGN-plan-surface-session-prep-current-goal-2026-07.md` §7 (one real prep loop).

## Current product truth (read before dogfood)

| Behavior | What actually happens today |
| --- | --- |
| Which prep session opens | Driven by **live packet** `session` via `GET /api/live/plan-view`. `prepSession = liveSession + 1`, `memorySession = liveSession − 1`. |
| URL `?campaign=` / `?session=` | **Ignored** by Plan load. Useful as a note-to-self in the URL only. |
| Board on first open | **Starter scaffold** (or a prior **localStorage** draft for that prep session). Does **not** hydrate from `Session N Prep.md`. |
| Save to Markdown | Writes TipTap → durable `…/Session Prep/Session {prepSession} Prep.md`. |
| Reload / restart | Recovers **localStorage** draft if present. Does **not** re-read the corpus Markdown file. |
| World Graph object cards | Load from current World Graph head (PR008A path). Search under Edit → World Graph objects. |
| Prep-memory Q&A | `POST /api/live/query` against the **loaded live packet** session. Packet mismatch → hard error. |

**Known gap (READY backlog):** *Plan board hydrates from Session Prep.md* — corpus hydrate on load is not shipped. Dogfood must treat that as missing, not as a user error.

**Clobber warning:** If `Session N Prep.md` already has real content and the board shows scaffold, **do not Save** until the board holds that content (paste from the file first). Saving scaffold would overwrite the durable prep file.

## Preconditions

- Dev servers can run (live-control API + live-control UI).
- `DUNGEONMIND_LIVE_SESSION_DIR` points at the live packet you intend (see Session mapping below).
- Eldyrwild World Graph activated under the configured world-graph root (for graph-object steps).
- Corpus Session Prep path exists for the **prep** session you will edit.

## Session mapping cheat sheet

| Live packet `session` | Default “preparing” | Memory / graph focus | Durable target file |
| ---: | --- | --- | --- |
| 22 | Session 23 | World union (no `?session=`) | `Session 23 Prep.md` |
| 23 | Session 24 | World union (no `?session=`) | `Session 24 Prep.md` |
| 24 | Session 25 | World union (no `?session=`) | `Session 25 Prep.md` |

**Explicit focus / board overrides (preferred):**

```text
/plan?dogfood=1&session=24
/plan?dogfood=1&session=24&prepSession=25
```

- `?session=N` (or `session-N`) sets memory/graph focus to that session.
- `?prepSession=N` sets the Session Prep board target; otherwise prep defaults to `liveSession + 1`.
- Without `?session=`, Ask / World Graph use **world-union** focus (`kind: none`) — Plan no longer invents `live - 1` (the old Session 21 trap).

**After playing Session 25:** to edit **Session 25 Prep** without changing the live packet, open `/plan?prepSession=25` (optionally `&session=24` for memory focus).

Fixture packets in-repo today: `evals/c2_live_prep/live/session_22/` and `session_23/`. There is no stock `session_24` fixture — create one (copy `session_23`, set `"session": 24`) when dogfooding with a live packet at 24.

`Session 25 Prep.md` may live only in another worktree until copied into this checkout’s:

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 25 Prep.md
```

## Start

1. Set live session dir, then start backend + UI.
2. Open:

   ```text
   /plan?dogfood=1
   ```

   Optional note-to-self (not loaded by Plan):

   ```text
   /plan?dogfood=1&note=prep-25
   ```

3. Confirm the header: campaign, **preparing Session N**, memory session, and Nav **target path** for `Session N Prep.md`.
4. Open the **Dogfood checklist** panel and use it as you go.

## Pass A — Board honesty (required)

1. Note what the board shows on first paint: scaffold vs prior local draft vs (if somehow present) full prep.
2. Confirm Nav target path matches the prep session you intend.
3. If an existing `Session N Prep.md` has content you care about:
   - Open that file outside Plan.
   - Paste into the board (or clear localStorage key for that document and wait for hydrate — **not available yet**).
   - Only then continue to Save.
4. Check checklist items for board source honesty.

## Pass B — Real prep content + save

1. Edit the board with real Session Prep content (scenes, threads, chips).
2. Add at least one reference chip (corpus and/or graph-native).
3. **Save to Markdown**.
4. Confirm save status and that the target file on disk updated.

## Pass C — Recovery (honest expectations)

1. Reload the browser tab → board should still match the **localStorage** draft.
2. Optional: clear only the Plan canvas localStorage key for this document, reload → expect **scaffold again** (proves corpus hydrate is missing). Record that.
3. Stop and restart the API + UI.
4. Reopen `/plan?dogfood=1` with the same live session dir.
5. Confirm local draft recovery. Do **not** mark “loaded from corpus” unless hydrate has shipped.

## Pass D — Reference chips (board-local)

1. Click a reference chip → inspect selected-object card.
2. Use source preview when available.
3. Do **not** treat Edit → World Graph objects / toolbar graph search as part of this dogfood pass. The Plan main page under measurement is the markdown board + dogfood checklist.

## Pass E — Hermes same-thread continuity (Rung 5)

1. Open **Ask DungeonBuddy** → select **Hermes tools** → Trace On.
2. **Turn 1** (new thread):

   ```text
   What do we know about Tripod Null-Calf at the North Gate?
   ```

   Confirm `hermes_graph_agent`, a graph tool ran, grounding/citations agree on revision.
3. **Turn 2** (same thread):

   ```text
   What is it connected to that should affect my prep?
   ```

4. In Network, inspect Turn 2 `/api/live/query`:
   - `conversation_history` is prior user/assistant prose only;
   - new question is only in top-level `text`;
   - no `hermes_session_id`, `manifest_path`, citations, traces, or source bodies in history.
5. Confirm the answer resolves “it”, runs **fresh** graph tools, and cites only Turn 2 anchors.
6. **Thread isolation:** new empty Thread B; ask the Turn 2 follow-up alone; confirm Thread A history is absent.
7. Inspect `agent-interaction-*` localStorage: no `hermes_session_id` / `conversation_history` structural fields.
8. Open a World Graph citation/evidence card from the answer when present.
9. Record live-packet mismatches if Q&A 400s.

## Feedback capture

1. Fill **Dogfood notes** as you go.
2. Check off completed checklist items.
3. **Copy dogfood report** → paste into chat / handoff.
4. **Reset dogfood checklist** clears checklist + notes only — not the prep board.

## What to look for

- Did the page feel like prep or like an empty scaffold?
- Did you almost Save over a real `Session N Prep.md`?
- Did reload feel like “loaded my prep” or “kept a browser draft”?
- Did Hermes Turn 2 feel continuous on “it” without claiming a resumed session?
- Did Network/localStorage stay free of `hermes_session_id` / transcript fields?
- Did toolbar / main-page graph search get in the way of board + dogfood work?
- What should DungeonBuddy have loaded automatically?

## Suggested Session 23 sequence (current Rung 5 tooling)

```text
1. export DUNGEONMIND_LIVE_SESSION_DIR=<repo>/evals/c2_live_prep/live/session_22
2. Start API + UI; open /plan?dogfood=1&session=23 (or omit session for world-union focus)
3. Confirm working board title (Session 23 Prep) and URL focus (`?session=` / world union); save status lives on the board heading
4. Pass A: observe scaffold (or stale local draft); paste real Session 23 Prep before any Save
5. Pass B: edit + Save
6. Pass C: reload (local draft); optional clear-localStorage proof of missing hydrate
7. Pass D: reference chip + source preview only
8. Pass E: Hermes Turn 1 Tripod → same-thread Turn 2 “it” → Network/history proof → Thread B isolation → localStorage inspection
9. Copy dogfood report (suggested follow-ups are pre-seeded)
```

## What this unlocks

Dogfood reports should drive the next slice. Default next Plan prep-loop slice from current evidence:

1. **Remove World Graph search from Plan toolbar / main page** — keep dogfood + markdown board as the surface under measurement.
2. **Corpus hydrate on load** (READY backlog) — closes the scaffold / clobber class of failures.
3. After Rung 5 acceptance: **Rung 6** durable Hermes session / reload lifecycle (not prose replay).
