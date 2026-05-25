---
pr_body_template: |
  ## Summary
  Author **T-COMMS** — Session 22 Mirathorn rockie-talkie retry table (**d100**, 100 rows) grounded in Dual Front arc planning; register in session_22 hub; retire the d12 stub.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

# HANDOFF — Session 22 Mirathorn comms d100 (T-COMMS, creative writing)

**Created:** 2026-05-23 (UTC).  
**Status:** ACTIVE — dispatch to **creative writing agent** with git access. One PR. Parent agent updates **`canvases/session-22-planning.canvas.tsx`** after merge (out of scope for worker).  
**Parent agent:** Cursor agent (DungeonMindBuddy).  
**Plan anchor:** Session 22 travel prep — comms layer for Mirathorn while party marches north. No eval harness; corpus-only creative slice. Dogfood: `Backlog.md` *Prep flow — capture arc vision*.

---

## §1 Mission

Replace the provisional **T-COMMS d12** with a **player-rolled d100** Mirathorn rockie-talkie retry table (**100 numbered rows**, thematic bands, GM-facing corruption/knowledge per row) and sync all Session 22 pointers to the new file.

---

## §2 Why this slice

- **Session 21 table canon:** Frank said festival resumed and hung up; Lysandra got no answer; party pressed north (~3 days south to Mirathorn, ~5 north to Mireward).
- **GM vision lock (planning, not recap):** Same **meat pipeline** tainted party rations and Mirathorn; **festival is not actually on** — **subtle guard corruption** feeds operators a **celebration script** to **keep the company marching to the swamp** while a **parallel summoning** prepares in the city. See arc doc below.
- **Existing stub:** `travel_mirathorn_comms_d12.md` (12 rows) — proof of schema; **insufficient variety** for repeated retry beats across a multi-day march.
- **This slice does NOT:** resolve Mirathorn off-screen; confirm cult takeover in dialogue; edit recaps; promote GM truth to table canon; touch prompts/evals/gold; update the planning canvas (parent does that post-merge).

---

## §3 Authoritative inputs (read in this order)

### 3.1 Workflow & format

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — §4 allowlist / §7 verification / §9 rubric.
2. **`Event Table Design Guidance.md`** (repo root) — weighting, action-oriented rows, escalation on repeat, beneficial mix.
3. **`corpus/.../Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md`** — **format mirror**: frontmatter, band headers (`## 01–10 · …`), numbered rows, “How to use”, escalation rule.
4. **`corpus/.../Session Prep/session_22/travel_mirathorn_comms_d12.md`** — **schema seed** (triggers, canon guard, row shape); **replace**, do not copy verbatim for all 100 rows.

### 3.2 Worldbuilding & comms index (required reads)

| Order | Path (under `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/`) | Why |
|-------|------------------------------------------------------------------------|-----|
| 1 | `Campaign 2 — Dual Front Shepherd Arc (GM planning).md` | **Vision lock** — festival lie, meat pipeline, steer-north, dual front |
| 2 | `Mirathorn — rockie-talkie comms timeline.md` | Table canon wire log + day rows + S22 march comms |
| 3 | `Mirathorn — While You Were Away.md` | Remote city state summary |
| 4 | `Session Recaps/Session 21 - Drake Nest Mirathorn Call.md` | **Table canon** for S21 Frank + Lysandra beats |
| 5 | `Session Recaps/Session 20 - Recap.md` | Sara, jerky, Tealeaf no pickup |
| 6 | `Session Recaps/Session 18 - Recap.md` | Frank/Lysandra muffled overhear (meat, boundary, map) |
| 7 | `Session Recaps/Session 15 - Recap.md` | Tealeaf forest callback promise |
| 8 | `Session Recaps/Session 12 - Recap.md` | Sara & Frank named; Globe crisis patch |
| 9 | `Elderwyld_Narrative_Ledger_Campaign2.md` | §3 storms, §8 festival/choral oath, §37 rockies/static “Mael—” |
| 10 | `Session Prep/session_22/session_22_travel_to_mireward_runbook.md` | §3.4 weather/comms pressure; §6 roll registry; **forbidden** resolves |
| 11 | `Session Prep/session_22/travel_dilemma_d12.md` row **7** | Retry-in-lull → roll T-COMMS |
| 12 | `Session Prep/session_22/travel_night_watch_d12.md` rows **1**, **7** | Comms lull triggers |
| 13 | `Session Prep/session_22/travel_npc_spotlight_d12.md` Lysandra rows | Comms retry NPC beats |

### 3.3 NPC voice (read; do not edit dossiers)

| NPC | Hub / dossier |
|-----|----------------|
| **Sara** | `NPCs/sara_mirathorn_operator/sara_mirathorn_operator_character_dossier.md` + `timeline.md` |
| **Frank** | Same hub (fraternal twin co-operator) |
| **Lysandra** (field — rarely answers inbound to city) | `NPCs/captain_lysandra_ironveil/` — read README + timeline |
| **Tealeaf** | No dedicated hub — voice from S11/S15/S20 recaps; Stormspire Academy context in `Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md` (Merril Tealeaf — Agricultural Union / Academy contact) |
| **Valin** | S15 Academy board — brief academic tone only; **≤5 rows** total |

---

## §3.4 Responder matrix — corruption & knowledge (binding for row authorship)

Use these tiers on **every row** in the `Corruption` field. **GM truth** comes from arc doc; **Heard** is what the **party** gets on the wire.

### Corruption tiers

| Tier | Label | Meaning |
|------|-------|---------|
| **0** | **Clean** | Tells truth they know; may omit; not cult |
| **1** | **Scared clean** | Truth under fear; whispers; drops line to protect self or party |
| **2** | **Unwitting relay** | Repeats **guard/Council reassurance** believing it (Frank’s S21 register) |
| **3** | **Compromised** | Knows something is wrong; **silence or deflection** under pressure (not cartoon evil) |
| **4** | **Hostile relay** | **Rare (≤5 rows in whole table)** — actively steers party wrong; still **no full cult exposition** |

### Sara (operator — Caelynn’s usual line)

| Field | Detail |
|-------|--------|
| **Corruption** | **0–1** on most Sara rows |
| **Knows (GM)** | Jerky audit **active**; Mirathorn logistics implicated; **private trust list** (names she **won’t** say on wire); Tealeaf line **still dead**; guard orders feel **wrong** but unproven; operators **not** running a real festival crowd |
| **Will say on wire** | Safety check-ins; jerky warning; fear without naming; brief confessional breaks (cf. d12 row 11) |
| **Won’t say** | Summoning site; full cult plan; “festival is fake” **explicitly** unless tier-1 scared slip (rows 86–92 band only) |

### Frank (operator — festival-script voice, S21 hang-up)

| Field | Detail |
|-------|--------|
| **Corruption** | **2** on most Frank rows; **1** if cracking; **3** if ordered silence |
| **Knows (GM)** | **Authorized script:** “festival resumed / long night / stages open”; **ops night** exhaustion (not party crowds); must **cut** before turnaround argument; proximity to **Lysandra crisis** traffic (S18) |
| **Will say on wire** | Apology; celebration language; clipped patch offers; bitter helpful road gossip (Mireward queue knows your name) |
| **Won’t say** | Admit city is quiet; connect meat to pit; invite party home |

### Tealeaf (Academy line — transfer from Sara S20)

| Field | Detail |
|-------|--------|
| **Corruption** | **Unknown** — rows should **leave ambiguous** ( detained / researching / compromised / afraid ) |
| **Knows (GM)** | Forest migration **early** (S15); mushroom/fungi expertise; **may** suspect tainted provisions link — **not proven on wire** |
| **Will say** | Cool academic fragments **if** she answers at all |
| **Won’t say** | Resolve why S20 transfer failed — **≥50% of Tealeaf rows** = ring / silence / wrong lab sounds |

### Guard voice (overhear — no fixed name yet)

| Field | Detail |
|-------|--------|
| **Corruption** | **3–4** |
| **Knows (GM)** | **Boundary**, **map not random**, **meat** routing, **evacuate** language, steer-north **priority**, summoning **prep** (never spell out) |
| **Heard shape** | Muffled **Frank + guard** or **guard net** only — caller may **listen vs interrupt** |

### Static / environmental (no NPC)

| Field | Detail |
|-------|--------|
| **Corruption** | n/a |
| **Knows** | Storm-front **inheritance** from Mirathorn (ledger §3); **“Mael—”** fragment (§37); choir **misheard** through hiss — **ambiguous**, not confirmation |

### Lysandra (field captain calling **in** — rare)

| Field | Detail |
|-------|--------|
| **Corruption** | **0** |
| **Knows** | Mission north; city ** feels wrong**; tower/pit map — **won’t** explain on wire |
| **Row use** | **Wrong-patch** only (≤8 rows): city board connects her to **guard net** by mistake |

---

## §3.5 Table canon the rows must not contradict

- S21: Frank **very hung over**, festival **resumed**, **long night**, **abrupt hang-up** on Caelynn.
- S21: Lysandra **no answer** when she calls in.
- S20: Sara **who can I trust**; Tealeaf **no pickup**.
- S18 overhear fragments: **meat**, **do not cross boundary**, **breached**, **evacuate**, **map not random**.
- Party position: marching **north** on Mireward Reach after S21 camp.

---

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|--------|------|---------|
| **Create** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_mirathorn_comms_d100.md` | **T-COMMS** — d100, 100 rows |
| **Delete** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_mirathorn_comms_d12.md` | Retired stub |
| **Modify** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/README.md` | T-COMMS row → **d100** path, stay **`ready`** |
| **Modify** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_dilemma_d12.md` | Row 7 pointer → **d100** file |
| **Modify** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Mirathorn — rockie-talkie comms timeline.md` | §4 + related links → **d100** |
| **Modify** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Campaign 2 — Dual Front Shepherd Arc (GM planning).md` | Roll table path → **d100** (one line) |
| **Modify** | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Mirathorn — While You Were Away.md` | Related link → **d100** |

> Expected `git diff --stat` expressible from this table only.

---

## §5 Files explicitly OUT OF SCOPE (denylist)

| Path | Why |
|------|-----|
| `canvases/session-22-planning.canvas.tsx` | **Parent agent** updates after merge |
| `src/prompts/*.py`, `evals/**`, `tests/**` | No code |
| `corpus/**/Session Recaps/**` | Table canon — read only |
| `corpus/**/NPCs/**/character_dossier.md`, `*_statblock*` | Voice reference only |
| `session_22_travel_to_mireward_runbook.md` | Unless adding one T-COMMS registry line in §6.1 — **optional single-line** status only |
| Other `travel_*.md` tables | Do not rewrite T-NPC/T-DIL/T-WX rows |
| `Backlog.md`, other `HANDOFF-*.md` | Meta |
| `Docs/Plans/**` except worker may note completion in PR body | No handoff self-edit unless archiving |

---

## §6 Implementation contract

### File: `travel_mirathorn_comms_d100.md`

**Frontmatter:**

```yaml
---
title: "Session 22 — Mirathorn comms retry d100"
document_class: planning
canon_layer: campaign
campaign_id: longmont-c2
temporal_scope: session_specific
session: 22
origin_session: 21
last_updated_session: 21
source_class: roll_table
table_id: T-COMMS
dice: d100
table_note: "Player-rolled Mirathorn rockie-talkie retry during Session 22 travel. Wire fragments only — GM truth in Dual Front arc doc. Planning until recap promotes."
---
```

**Body sections (required):**

1. **Title** + **How to use** (6–10 bullets): triggers (T-DIL 7, T-WATCH 1/7, T-NPC Lysandra, explicit call); player rolls **d100**; **not** for replaying S21 beats unless days later; pair with T-WX static; escalation-on-repeat; canon guard pointer to arc doc.
2. **Responder quick reference** — compact table summarizing §3.4 (Sara/Frank/Tealeaf/guard/static tiers).
3. **Thematic bands** — ten `## NN–NN · Band name` headers covering **01–100** with no gaps.
4. **100 numbered rows** — `1.` through `100.` exactly once each.

### Row format (required — six fields)

Each row is **one line** or **one tight block** using this delimiter pattern:

```text
{N}. **{Responder}** · *Heard:* {what the party gets — dialogue or static, quoted if speech} · *GM truth:* {one clause — city reality per arc doc} · *Responder knows:* {what this voice honestly understands} · *Corruption:* {0–4 or n/a} · *Cut/Repeat:* {how line ends; intensify if rolled again}
```

**Creative constraints:**

- **Heard** = player-facing fragment only — **never** “the festival is a lie” as GM narration; lie appears as **false reassurance** in dialogue.
- **GM truth** = planning layer — may state festival not on, ops night, summoning prep — **for GM eyes on the row**.
- **Dialogue:** tight, speakable, 1–3 sentences max in *Heard*.
- **Beneficial rows:** ≥15 rows where party gets **actionable** info (jerky warning, overhear clue, lull retry) without resolving arc.
- **Hostile relay (tier 4):** ≤5 rows total.
- **S21 echo rows:** ≤8 rows — Frank festival/hang-up **variation**, not copy-paste.
- **Forbidden in *Heard*:** “The Shepherd’s Flock runs Mirathorn”; “Dustwalker is alive/dead”; “You lose the city tonight”; full summoning explanation.

### Band allocation (weighting — adjust row text within bands)

| Band | Rows | Primary content | Target share |
|------|------|-----------------|--------------|
| **01–10** | 10 | No connect / dead line / pure static | Common |
| **11–25** | 15 | Static lull / almost clear / retry window | Common |
| **26–40** | 15 | **Frank** — festival script, hang-up, steer north | Common |
| **41–55** | 15 | **Sara** — jerky, trust, scared truth | Uncommon |
| **56–70** | 15 | **Guard overhear** — meat, boundary, map, evacuate | Uncommon |
| **71–80** | 10 | **Tealeaf / Academy** — ring, silence, wrong sounds | Uncommon |
| **81–88** | 8 | Ambiguous choir / storm hiss / “Mael—” fragment | Rare |
| **89–94** | 6 | Near-truth slips (Sara/Frank crack) | Rare |
| **95–99** | 5 | Wrong-patch **Lysandra** ↔ guard net one sentence | Rare |
| **100** | 1 | **Special** — single highest-stakes hook (e.g. Sara names **one** trust-list initial; or guard says **“pit first, then bell”** — party must interpret) | Unique |

### Escalation rule (in How to use)

> Same **band** rolled twice same journey → shorter call, **more static**, **worse tone**, or **second overhear** — never identical *Heard* text.

### Pointer updates

- `travel_dilemma_d12.md` row 7: `travel_mirathorn_comms_d100.md`
- `README.md`: `Mirathorn retry d100` + path
- Timeline §4: “roll d100 table”
- Delete `travel_mirathorn_comms_d12.md`; `rg travel_mirathorn_comms_d12` across repo should return **zero** after edits (fix any stragglers in allowlist files only)

---

## §7 Verification commands

Worker runs **every** command; paste output in PR body. Reviewer reruns.

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy

BASE="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22"
TABLE="$BASE/travel_mirathorn_comms_d100.md"

# Row count — must be exactly 100
echo "T-COMMS d100 rows:" && rg -c '^[0-9]+\.' "$TABLE"

# Band headers cover 01-100 (expect 10 band headers)
echo "Band headers:" && rg '^## [0-9]{2}–[0-9]{2}' "$TABLE" | wc -l

# Frontmatter
rg '^table_id: T-COMMS' "$TABLE" && rg '^dice: d100' "$TABLE"

# d12 retired
test ! -f "$BASE/travel_mirathorn_comms_d12.md" && echo "d12 deleted: OK" || echo "d12 still exists: FAIL"

# No stale d12 pointers in allowlist files
rg 'travel_mirathorn_comms_d12' \
  "$BASE/README.md" \
  "$BASE/travel_dilemma_d12.md" \
  "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Mirathorn — rockie-talkie comms timeline.md" \
  "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Campaign 2 — Dual Front Shepherd Arc (GM planning).md" \
  "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Mirathorn — While You Were Away.md" \
  && echo "stale d12 refs: FAIL" || echo "stale d12 refs: OK"

# Register
rg 'T-COMMS' "$BASE/README.md" | rg 'd100|ready'

# Corruption field present on rows (spot check — expect high count)
echo "Corruption mentions:" && rg -c '\*Corruption:\*' "$TABLE" || rg -c 'Corruption:' "$TABLE"

# Forbidden exposition (should be 0 in table body)
rg -i 'shepherd.s flock runs|dustwalker is (alive|dead)|you lose the city' "$TABLE" && echo "forbidden hits: REVIEW" || echo "forbidden: OK"

# Allowlist-only diff
git diff --stat HEAD -- \
  "$TABLE" \
  "$BASE/travel_mirathorn_comms_d12.md" \
  "$BASE/README.md" \
  "$BASE/travel_dilemma_d12.md" \
  "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Mirathorn — rockie-talkie comms timeline.md" \
  "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Campaign 2 — Dual Front Shepherd Arc (GM planning).md" \
  "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Mirathorn — While You Were Away.md"
```

---

## §8 Reporting contract

PR body must include:

1. **`git diff --stat`** filtered to §4 paths only.
2. **Verbatim §7 output** — row count **100**, d12 deleted, no stale pointers, README `ready`.
3. **Band distribution table** — row counts per band (self-reported from authored file).
4. **Three sample rows** pasted (one Frank tier-2, one Sara tier-0/1, one guard overhear) showing all six fields.
5. **What stayed unchanged** — recaps, dossiers, canvas, prompts, other travel tables.

---

## §9 Acceptance rubric

- [ ] **Exactly 100** numbered rows (`1.`–`100.`) — verified by §7 row-count command.
- [ ] **Ten band headers** spanning 01–100 with no gaps — verified by §7 band-header count + reviewer skim.
- [ ] Frontmatter includes `table_id: T-COMMS`, `dice: d100`, `session: 22` — verified by §7 `rg`.
- [ ] **`travel_mirathorn_comms_d12.md` deleted** — verified by §7 file test.
- [ ] **No stale `travel_mirathorn_comms_d12` references** in §4 modified files — verified by §7 `rg`.
- [ ] **README** register lists T-COMMS as **d100** and **`ready`** — verified by §7.
- [ ] **Every row** includes *Heard*, *GM truth*, *Responder knows*, *Corruption*, *Cut/Repeat* — verified by reviewer spot-check of **10 random rows** in PR diff.
- [ ] **Tier-4 hostile relay ≤5 rows** — verified by reviewer count of `Corruption: 4` in diff.
- [ ] **Forbidden exposition** absent from *Heard* fields — verified by §7 forbidden `rg` + reviewer read of Frank/Sara dialogue.
- [ ] **No files outside §4** in diff — verified by §7 scoped `git diff --stat`.

---

## §10 Out-of-band notes

- **Canvas:** Parent agent embeds T-COMMS band summary + roll hook in `canvases/session-22-planning.canvas.tsx` **after** this PR merges — worker **must not** edit canvas.
- **PII:** Corpus dossiers may contain player-linked notes — read for voice; do not paste long excerpts in PR.
- **Promotion:** If a row’s *Heard* becomes table canon at Session 22, GM promotes via recap — worker does not edit recaps.
- **Optional follow-up:** Runbook §6.1 one-line “T-COMMS Exists d100” — only if worker can do it without rewriting §6 specs.
- **Branch:** `cursor/s22-mirathorn-comms-d100` or similar; open PR against current integration branch when done.

---

## Quick reference — when to roll (for smoke test)

```
Triggers: T-DIL 7 · T-WATCH 1 or 7 · T-NPC Lysandra comms · player declares call
Not for: first replay of S21 Frank hang-up / Lysandra no-answer same morning unless table has moved on
Die: d100 → read row → roleplay wire fragment only
```
