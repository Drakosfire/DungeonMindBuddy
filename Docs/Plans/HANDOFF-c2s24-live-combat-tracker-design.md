# Handoff: C2S24 live combat tracker design

**Purpose:** Give the next design agent a focused brief from Session 24 live-play dogfood.

**Source dogfood log:** `Docs/Plans/C2S24-LIVE-PLAY-DOGFOOD-NOTES.md`

**Context:** During live gameplay, the command board and combat tracker were useful enough to stay in the loop, but combat exposed several places where the tool still makes the GM remember mechanics, UI state, or creature bookkeeping that the tracker should own.

---

## 1. Primary Design Goal

Design the next live combat tracker slice as an **operational combat cockpit**, not only a roster display.

The GM should be able to:

- read turn order by fixed initiative bands,
- update HP with minimal cognitive load,
- attach and expire statuses without remembering timing,
- spawn minions/summons from abilities,
- and hover rules terms that hydrate from the ingested 5e rules graph.

---

## 2. Pain Ranking

1. **Rules lookup was the biggest pain.**
   - Examples: `sleeping`, `poisoned`.
   - `poisoned` should surface disadvantage on attack rolls and ability checks.
   - The content should come from the ingested rules corpus, not hardcoded UI text.

2. **Minion/summon spawning was the second biggest pain.**
   - Enemy example: Tripod Null-Calf throws meatwings, meat abominations, and unnamed burrowers.
   - Player example: Ephanna summons **Ogonob**.
   - These should enter the tracker with stats, team, owner/controller, generated initiative, and source provenance.

3. **Combat scanning and numeric editing were smaller but constant frictions.**
   - Initiative bands need strong visual grouping.
   - Column labels need to repeat or stick per group.
   - Enter should commit numeric edits and visibly exit edit mode.

---

## 3. Clarified Product Decisions

| Topic | Decision |
|-------|----------|
| Status ownership | Statuses attach to the affected entity. |
| Status expiry v1 | Start with end-of-turn expiry. Later rules hydration can infer richer timing. |
| Spawned minion initiative | Same initiative as summoner/source, inserted immediately after that source. |
| Ogonob | Treat as a `summon`, owned/controlled by Ephanna. |
| Rules hover scope | Aim for any rules term, not only conditions. |
| Rules source | Hydrate dynamically from the ingested D&D 5e rules graph. |
| HP editing v1 | Start with final HP only. Defer event/time series of HP changes and causes. |
| Initiative bands | Always use `21+`, `16-20`, `11-15`, `6-10`, `1-5` as default grouping. |

---

## 4. Candidate Design Slices

### Slice A — Rules-Term Hover Cards

**Problem:** The GM needs rules details in combat without opening a rules book or relying on hardcoded tooltips.

**Design shape:**

- Normalize visible combat terms (`poisoned`, `sleeping`, spell/effect names, action names).
- Resolve terms through a rules-graph lookup boundary.
- Render compact hover/focus cards with:
  - title,
  - short rules summary,
  - source/citation,
  - loading state,
  - not-found state,
  - local cache.

**Acceptance checks:**

- Hovering `poisoned` shows disadvantage on attack rolls and ability checks.
- Hover/focus is keyboard-accessible.
- Missing rules term degrades gracefully without blocking combat flow.
- Combat UI does not preload the whole rules corpus.

### Slice B — Ability Spawn Templates

**Problem:** Abilities create combatants, but adding them manually interrupts active play.

**Design shape:**

- Add structured spawn metadata to statblock/ability markdown or companion sidecars.
- Render ability actions such as `Add meatwing`, `Add burrower`, `Add Ogonob`.
- New tracker entity should include:
  - stat template,
  - team/side,
  - owner/controller,
  - initiative placement,
  - generated display name,
  - source creature/ability provenance.

**Acceptance checks:**

- Tripod ability can add a meatwing-like minion without manual stat entry.
- Ephanna can add Ogonob as a summon owned by Ephanna.
- Spawned entity appears immediately after the summoner/source at the same initiative.
- Spawned entity can still be manually edited after creation.

### Slice C — Status Duration v1

**Problem:** Status notes are useful, but duration timing remains a GM memory burden.

**Design shape:**

- Statuses attach to the affected entity.
- v1 supports end-of-turn expiry.
- Status row/card should show:
  - label,
  - note,
  - duration remaining,
  - expiry boundary,
  - expired/pending-expiry visual state.

**Acceptance checks:**

- A status can be added to an entity with end-of-turn expiry.
- Advancing turns decrements or expires it predictably.
- Expired statuses are visually obvious and easy to remove or extend.

### Slice D — Combat Editing and Scan UX

**Problem:** Small interaction costs compound during combat.

**Design shape:**

- Initiative grouped by fixed bands: `21+`, `16-20`, `11-15`, `6-10`, `1-5`.
- Strong visual separators between bands.
- Repeat or stick column headers per band.
- Numeric fields:
  - Enter commits and blurs,
  - Escape cancels and blurs,
  - committed value returns to obvious read mode.
- HP popover:
  - current/max display,
  - delta input for `+/-`,
  - manual set override,
  - final HP v1 only.

**Acceptance checks:**

- The queue is visually readable by initiative band.
- Long grouped rosters do not require looking back to the top header.
- Pressing Enter after HP/numeric edit clearly exits edit mode.
- HP can be changed by `-12`, `+7`, or direct set.

---

## 5. Integration Risks

- **Rules graph boundary:** The combat tracker needs a clean API to rules ingestion outputs. Avoid coupling UI components directly to rules artifact file shapes.
- **Spawn metadata ownership:** Decide whether spawn templates live in statblock markdown, companion sidecars, generated statblock metadata, or a normalized statblock index.
- **Turn semantics:** v1 end-of-turn expiry is intentionally narrow. Do not overfit the first slice to every D&D duration phrase until rules hydration exists.
- **Live-play reliability:** Every interaction should fail soft. Missing rules lookup or spawn template should never break HP/turn tracking.

---

## 6. Recommended First Move

Start with **Rules-Term Hover Cards** because it was the biggest live-play pain and establishes the command board ↔ rules ingestion relationship needed for later richer status semantics.

Keep the first implementation narrow but real:

- `poisoned` must hydrate from rules ingestion,
- hover/focus card must cite its source,
- and missing terms must show a safe not-found state.

After that, move to **Ability Spawn Templates** because minion/summon creation was the second biggest pain and will make the tracker feel operational rather than merely descriptive.
