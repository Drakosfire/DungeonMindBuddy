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

| Live packet `session` | Plan header “preparing” | Memory focus | Durable target file |
| ---: | --- | --- | --- |
| 22 | Session 23 | Session 21 | `Session 23 Prep.md` |
| 23 | Session 24 | Session 22 | `Session 24 Prep.md` |
| 24 | Session 25 | Session 23 | `Session 25 Prep.md` |
| 25 | Session 26 | Session 24 | `Session 26 Prep.md` |

**After playing Session 25:** to edit **Session 25 Prep** in Plan, the live packet must be **`session: 24`** (preparing 25), not 25.

Fixture packets in-repo today: `evals/c2_live_prep/live/session_22/` and `session_23/`. There is no stock `session_24` fixture — create one (copy `session_23`, set `"session": 24`) when dogfooding Session 25 Prep.

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

## Pass D — Reference + World Graph cards

1. Click a reference chip → inspect selected-object card.
2. Use source preview when available.
3. Edit → **World Graph objects**: find a real node (e.g. Tripod Null-Calf / Mireward if present on the head).
4. Add to dogfood list → open GraphObjectCard → traverse one relationship → remove from list (local only).
5. Record whether cards felt game-useful vs thin bootstrap graph.

## Pass E — Prep memory Q&A

1. Open Ask prep memory.
2. Ask questions that match **memory session** content / planning needs for the prep you are writing.
3. If World Graph context panel is present (PR008B branch), note status / revision / matched IDs separately from corpus citations.
4. Open a **corpus** citation source when one appears — not graph metadata.
5. Record live-packet mismatches if Q&A 400s.

## Feedback capture

1. Fill **Dogfood notes** as you go.
2. Check off completed checklist items.
3. **Copy dogfood report** → paste into chat / handoff.
4. **Reset dogfood checklist** clears checklist + notes only — not the prep board.

## What to look for

- Did the page feel like prep or like an empty scaffold?
- Did you almost Save over a real `Session N Prep.md`?
- Did reload feel like “loaded my prep” or “kept a browser draft”?
- Were World Graph cards useful for *this* prep session, or stuck on older bootstrap objects?
- Did prep-memory answers help write Session Prep, or fight the live-packet session?
- What should DungeonBuddy have loaded automatically?

## Suggested Session 25 sequence (current tooling)

```text
1. Copy Session 25 Prep.md into this repo’s Session Prep folder if missing.
2. Create evals/c2_live_prep/live/session_24/ from session_23 with live_packet.json "session": 24.
3. export DUNGEONMIND_LIVE_SESSION_DIR=<repo>/evals/c2_live_prep/live/session_24
4. Start API + UI; open /plan?dogfood=1
5. Confirm header: preparing Session 25, memory Session 23, target …/Session 25 Prep.md
6. Pass A: observe scaffold (or stale local draft); paste real Session 25 Prep before any Save
7. Pass B: edit + Save
8. Pass C: reload (local draft); optional clear-localStorage proof of missing hydrate
9. Pass D: chip + World Graph card traverse
10. Pass E: two prep-memory questions useful for Session 25 prep
11. Copy dogfood report
```

## What this unlocks

Dogfood reports should drive the next slice. Default next Plan prep-loop slice from current evidence:

1. **Corpus hydrate on load** (READY backlog) — closes the scaffold / clobber class of failures.
2. Then: prep-session override / post-play editing without inventing live packets.
3. Graph-backed cards and Agent query context stay valuable but secondary to “the board is my prep doc.”
