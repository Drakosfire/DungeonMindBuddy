# Post-#698 Human STOP — operator script from `main`

**Checkout:** `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`  
**Required HEAD:** `db7c66603217ab037d0bdbce0802646c4cb1dcf7`  
**What this is:** `#698` merge on `main` (`DOGFOOD-CONTINUITY: make opened World objects useful to inspect`)  
**Not this:** the old `#697` worktree. Do not dogfood from `DungeonMindBuddy-wt-surface-neutral-full-world-object-projection-v1`.

**Doors:** UI `http://127.0.0.1:5173/` · API `http://127.0.0.1:8000/health`  
**Authorities:** World `54330` read-only · APP-STATE `54331` read-only · do not start disposable `54329`

Do not paste recap prose, DSNs, or `.env` values into this report or into chat with the 7A1 agent.

This STOP gates Stage 7A1. Design already exists and is **STOP-GATED**:

```text
branch   origin/dogfood-continuity/stage-7a1-ingest-contextual-ask-v1
commit   e34f68915e0ca535bed7aa9bc13a8bdd2fabea0a
handoff  Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-7a1-ingest-contextual-ask-v1.md
status   DESIGN READY / STOP-GATED
```

Do not tell that agent to implement until this sheet’s dispatch decision is filled.

---

## Why this STOP, not another #697 pass

`#697` already proved: where an object opens, the complete World object is present and the five consumers share the same semantic fingerprint. That Human STOP did **not** pass as “click a node anywhere and ask the Agent.”

`#698` was the presentation slice: compact opened-object card, interactive Show all / Show fewer, technical identity behind Advanced. Author-local Ingest witness passed on the PR head. Plan Expand was attempted and blocked by the inherited generic-lens campaign mismatch.

This session answers one product question:

> **When I open a person, place, item, or faction on current `main`, does DungeonBuddy give me a useful compact view without hiding the rest of what it already knows?**

Then a dispatch question:

> **Is Stage 7A1 still the next independently useful capability?**  
> (Ask from historical Ingest without leaving the recap.)

---

## 0. Prove you are on this `main`

From the main checkout:

```bash
git rev-parse HEAD
# expect db7c66603217ab037d0bdbce0802646c4cb1dcf7

git show -s --format='%s' HEAD
# expect: DOGFOOD-CONTINUITY: make opened World objects useful to inspect (#698)
```

Start the product **from this directory**, not the `#697` worktree:

```bash
uv run uvicorn apps.live_control_server.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd apps/live-control-ui && npm run dev
```

`.env` lives on this checkout as a real file. The `#697` worktree already symlinks to it. Do not print it. Confirm only:

- World chip is not `authority_unavailable`
- you did not start `54329`

| Check | Pass? | Notes |
| --- | --- | --- |
| HEAD is `db7c6660` | yes | Dogfood started on `db7c66603217ab037d0bdbce0802646c4cb1dcf7` from `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy` |
| UI/API are this checkout | yes | API `127.0.0.1:8000`, UI `127.0.0.1:5173` |
| World chip healthy | noisy | Standing `Projection campaign does not match requested campaign longmont-c2` on Ingest `?campaign=` (generic-lens `X`, not authority_unavailable) |
| No `54329` | yes | World `54330` / APP-STATE `54331` read-only |

---

## How to classify

From `#698` HANDOFF §18:

```text
A  useful as-is
E  trustworthy but presentation/copy still poor
R  relationship disclosure/navigation defect
P  provenance presentation problem
T  temporal presentation problem
D  debug/technical noise still intrudes
X  failure belongs to another capability
```

Use `X` for inherited successors. Do not grow `#698` or 7A1 to absorb them.

Known `X` (already routed; do not “fail” this STOP on them):

```text
Agent says open Plan                          Stage 7A1  (the dispatch candidate)
Glowkindle missing from C2 generic search     retrieval-policy successor
C1 expand: campaign mismatch on generic lens  Plan generic-lens successor
Build/Play empty material                      template/material successors
every recap phrase is not a node               intentional; not this STOP
```

---

## 1. Canonical Ingest witness — C2S25 / Karsemine

Start: `http://127.0.0.1:5173/ingest?campaign=longmont-c2&session=session-25`

1. Load the C2S25 recap.
2. Click **Karsemine** in the recap prose.
3. Stay on Ingest. Do not go to Plan unless this path dies.

The card should start compact (about 8 relationship rows), not dump all 15.

| Check | Pass? | Class | Notes |
| --- | --- | --- | --- |
| Card opens; complete-object, not a glance stub | yes | A | Operator stayed on Ingest; opened named recap objects |
| Initial view is readable, not a 15-row dump | yes | A / E | Compact; rows read like a sentence |
| Interactive Show all (not dead `+7 more`) | | | Not re-litigated this pass; `#698` Ingest witness already passed |
| Show all reveals all 15; no extra wait that feels like a new World read | | | Same |
| Show fewer returns to the compact set | | | Same |
| S24 Hunter's Mark still reads as S24 under S25 focus | | | Session stamps visible (`C2 · S24` style) |
| S25 Lysandra material is still distinct | | | |
| Manual-seed / Questionable Company stays visible with **no fabricated excerpt** | | | |
| Advanced is closed by default | yes | A | PASS |
| Advanced shows node/fingerprint/origin when opened | | | Operator left it closed |
| Ordinary scan path does not force IDs/fingerprints on you | yes | A | |
| Click a relationship that was **not** in the first eight; target opens as a real object | | | |
| Recap remains where you were reading | fail then repaired | X | Tools → Ingest Recap left the loaded recap. Removed in this PR. |

Author-local `#698` Ingest witness already saw 15 complete / 8 initial / Show all 15 / Show fewer 8 / omitted S24 Hunter's Mark navigable / Advanced closed by default. This pass is whether **you** still believe that as a GM on `main`.

---

## 2. One other object (Karsemine is not the only path)

Still in Ingest, open **Stafl** if convenient, or another high-degree named object from the recap.

This pass used **Mirathorn** (and Outskirts), not Stafl.

| Check | Pass? | Class | Notes |
| --- | --- | --- | --- |
| Show all reaches every loaded relationship | | E | Same object on Mirathorn + Outskirts is likely two truthful edges. Optional later copy: `S6 Mirathorn Outskirts located in Mirathorn` |
| Layout does not explode | yes | A | |
| Advanced stays secondary | yes | A | Closed |
| Feel vs Karsemine (note if stuck / fine) | fine | A / E | Session stamps; sentence-like rows |

If Glowkindle is only reachable by **search**, expect campaign-scoped miss (`X`). Opening by exact id/pill is the World-cross-campaign path; generic C2 search is not.

---

## 3. Plan Expand — inherited block, not a `#698` fail

Start: `http://127.0.0.1:5173/plan?campaign=longmont-c2&session=session-25`

Try the old positive reference: search → place Karsemine → Expand.

| Check | Pass? | Class | Notes |
| --- | --- | --- | --- |
| Expand opens the same useful object as Ingest | | | |
| If blocked: `Projection campaign does not match requested campaign longmont-c2` | | X | Record exact copy. Do **not** ask 7A1 to repair this. |

`#698` already dispositioned this as **BLOCKED BY INHERITED SUCCESSOR**. Seeing it again on `main` is confirmation, not a new defect.

---

## 4. Agent on Ingest — expected current failure

With C2S25 loaded and Karsemine open, open **Ask DungeonBuddy**.

| Check | Pass? | Class | Notes |
| --- | --- | --- | --- |
| Ask is available on Ingest without going to Plan | | X if “open Plan” | This is the 7A1 mission if still true |
| If it redirects to Plan, copy the exact chrome sentence | | X | |

Do **not** treat this as a `#698` inspection failure. It is the compounding question 7A1 was designed to answer.

Do **not** spend this STOP trying to make Agent useful on Build or Play.

---

## 5. Build / Play

Open only if a real C2 document / Runbook already exists. Do not invent one.

| Surface | Opened? | Object usable? | Class | Notes |
| --- | --- | --- | --- | --- |
| Build | | | | Missing template = `X` |
| Play | | | | Missing Runbook = `X` |

---

## Operator questions (answer in sentences)

1. Does the initial Karsemine card feel readable rather than overwhelming?
2. Is it obvious that more relationships exist, and can you actually reveal them?
3. Does Show all feel local/fast, not like another fetch?
4. Are `C2 · S24` / similar stamps understandable without a separate time widget?
5. Does source/excerpt help, or does it dominate?
6. Are node IDs / fingerprints out of the way until Advanced?
7. Can you follow a relationship without losing confidence in which object you are inspecting?
8. Does Ingest now feel close enough to the old Plan Expand experience that you would stay in Ingest to inspect?

---

## Dispatch decision for the 7A1 agent

Fill **one**:

```text
[x] DISPATCH Stage 7A1 as designed
      Mission still: Ask from exact loaded historical Ingest recap,
      with optional opened World object, using existing Agent chrome.
      Do not start 7A2 (free-text highlight). Do not repair Plan lens.
      Do not change generic search policy.
      Do not restore Tools → Ingest Recap or Open Recap View.

[ ] REBRIEF Stage 7A1 before implementation
      What changed: ________________________________
      What the new first capability is: ____________

[ ] DIFFERENT successor first
      Name it: ____________________________________
      Why it outranks 7A1: _________________________
```

If inspection itself is still `R` / `D` / `T` and you would not stay in Ingest to look at people, **do not dispatch 7A1**. Say that plainly. 7A1 assumes `#698` inspection is good enough to stand on.

If the card is mostly `A`/`E` and the remaining anger is “I still have to go to Plan to ask,” that is the 7A1 confirm.

---

## Operator pass 2026-09-10 (main / `#698` merge)

Recorded on `db7c6660` after a cold restart of API/UI. Ingest has **Load**, not Unload. Do not describe this pass as session unload.

| Observation | Class | Owns | Notes |
| --- | --- | --- | --- |
| Advanced closed by default | A | `#698` | PASS |
| Objects show sessions; rows read like a sentence | A / E | `#698` keep | Keep session stamps. Optional later copy: `S6 Mirathorn Outskirts located in Mirathorn` (subject implied vs named). Same object appearing on Mirathorn + Outskirts is likely two truthful edges, not a duplicate payload. |
| Edit-state lock lives in Tools | E | Ingest/Plan chrome successor | Remove canvas edit-lock from Tools. Put a lock on the **Load recap** bar — that control is the only replace, and there is no unload. |
| Link / Tools **Ingest Recap** (`ingest-recap`) left `/ingest`, remounted Recap View, crashed the graph | X then repaired | Recap View overlay is not the loaded recap | Operator: remove it. Overlay unpublished from Ingest Tools; IngestionModule no longer jumps to `/plan?tool=recap`. Paste-new-recap needs a later empty-state home, not a Tools overlay on a loaded recap. |
| After that: `exact historical source is not adopted into APP-STATE` | X | triggered by the Recap-View/Load replacement | Graph Review asked APP-STATE for a recap that is not the adopted C2S25 binding (likely C1/S6 after Mirathorn). |
| `World · Needs attention · Projection campaign does not match requested campaign longmont-c2` | X | inherited generic-lens successor | **Standing on hard refresh** of `/ingest?campaign=longmont-c2&session=session-25`. Graph Review persist writes `campaign=`. World lens treats bare `?campaign=` (not `/build`, no `scopeMode=campaign`) as C1+C2 **world union**. World-scope snapshot `campaignId` is empty; the chrome verifier then fails closed. Not Recap-View leftover. 7A1 must not repair this. |
| Load slower than liked | P | after a UI design pass | Not a `#698` fail. Do not optimize before the Load-bar lock / Recap-tool confusion is designed. |

**7A1:** still the Ask-on-this-recap question. Do not absorb Recap View, edit-lock placement, sentence copy, lens mismatch, or load-speed. Do not restore Tools → Ingest Recap / Open Recap View.

**Immediate recover:** open [C2S25 Ingest](http://127.0.0.1:5173/ingest?campaign=longmont-c2&session=session-25) as a full navigation. Recap View overlay is removed from Ingest Tools.

---

## Repairs after this STOP (this PR)

Landed on `dogfood-continuity/remove-ingest-recap-overlay-v1` after the operator pass. Not 7A1.

1. **Remove the Recap View trap.** Tools → Ingest Recap (`ingest-recap`) and IngestionModule **Open Recap View** (`/plan?tool=recap`) left Graph Review for a second recap surface. That remounted the generic lens, then failed with `exact historical source is not adopted into APP-STATE`. Graph Review is the recap reader. Paste-a-new-recap still needs an empty-state home later; it must not be a Tools overlay on a loaded recap.

2. **Chrome band for composable sidebars.** Ask / Tools overlap because ToolHost, EditHost, ProjectionHost, and Author Node sit outside `.app-shell` with `top: 0; bottom: 0`. Inset is now `:root --app-chrome-top` / `--app-chrome-bottom`. Ingest Ask-unavailable **Open** is a bottom sheet, not a full-viewport takeover.

Operator also recorded, not repaired here:

- First-boot Ingest flicker → Stage 5B
- No Unload; Load is replacement → Load-bar lock successor
- Edit lock currently in Tools; put it on Load recap
- Optional copy: `S6 Mirathorn Outskirts located in Mirathorn`
- Load speed after a UI design pass
- Standing generic-lens campaign mismatch on `?campaign=`

---

## Paste this back to the 7A1 agent

Copy after the STOP. Keep it exact-SHA. Do not paste recap prose.

```text
Post-#698 Human STOP from main.

HEAD dogfooded: db7c66603217ab037d0bdbce0802646c4cb1dcf7
Checkout: /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
World chip: noisy (generic-lens campaign mismatch on ?campaign=, not authority_unavailable)
Authorities: 54330/54331 read-only; 54329 not used.

Canonical Ingest C2S25:
  compact default: pass
  Advanced default closed: pass
  session stamps / sentence-like rows: pass (A/E)
  Recap View overlay from Tools: fail, then removed in follow-up PR
  class codes: A/E for #698 inspection; X for Recap overlay, generic-lens, edit-lock, Stage 5B flicker

Plan Expand:
  blocked by generic-lens campaign mismatch
  7A1 must not repair this.

Agent on Ingest:
  still says go to Plan (Ask unavailable sheet)
  that remains the 7A1 mission

Dispatch:
  DISPATCH 7A1 as designed

Do not implement 7A2, generic World search, Plan lens repair,
Build/Play Agent, or graph-change proposals in the 7A1 PR.
Do not restore Tools → Ingest Recap or Open Recap View
(`/plan?tool=recap`); Graph Review is the recap reader.

If DISPATCH: implementation base is current origin/main after this
follow-up merges (chrome band + Recap overlay removal). Until then
keep the design handoff:
  Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-7a1-ingest-contextual-ask-v1.md
  First live proof after CODE is still C2S25 → Karsemine → Ask
  “What else do we know about her?”
```
