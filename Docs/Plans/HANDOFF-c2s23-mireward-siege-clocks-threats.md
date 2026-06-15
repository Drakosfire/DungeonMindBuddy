# HANDOFF — C2S23 Mireward siege mechanics + threat inventory

**Created:** 2026-06-06  
**Branch anchor:** `cursor/c2s23-mireward-prep-ui`  
**Current committed slice:** `24b81b7` — Mireward prep UI, statblocks, and north-gate opening lock  
**Status:** ACTIVE — dispatch to a fresh agent with zero prior chat context.  
**Mode:** Creative mechanics designer + threat inventory auditor. This is **not** a corpus-promotion slice unless the operator explicitly asks.  

**Parent context:**

- `Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md`
- `Docs/Plans/HANDOFF-c2s23-hester-edge-opening-combat.md`
- `Docs/Plans/HANDOFF-c2s23-mireward-siege-behavior-layout.md`
- `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md`
- `evals/c2_live_prep/mireward-prep/index.html`

---

## §0 Mission

Build the **siege mechanics / escalation clock model** and the **monster + threat inventory** for the Mireward siege arc.

The operator wants the siege to be playable and queryable:

- round / minute / hour / session clocks,
- breach pressure,
- civilian panic,
- supplies and shelter pressure,
- bardic morale / counter-music,
- glassy-eyed sleeper activation,
- rest rules,
- win / fail / exit conditions,
- existing meat-threat statblock candidates,
- ingestion gaps in the broader bestiary,
- and at least **two new monster concepts**:
  - a **large, three-limbed, very alien** monster,
  - a later-wave **siege-breaking monster**.

The goal is not “write a final encounter.” The goal is a reusable pressure engine the GM can run across the north-gate opening, the town’s first siege response, and later relief / breakout beats.

---

## §1 Current Locked Facts / Planning Anchors

Use these as fixed unless the operator explicitly changes direction.

| Item | Current state | Source |
|------|---------------|--------|
| Party scale | 6 level-5 PCs + 2 equal-level NPC allies + Lysandro nearby. | User handoff for current branch |
| Immediate crisis | Brin Holloway arrives with **55 civilians** from the Edge support column; about half are glassy-eyed; meat-monster flank is **3–8 minutes** behind. | `Mireward_PLACE_BUILD_SCAFFOLD.md` §F4; `brin_holloway/` |
| First combat | North-gate / north-road opening crisis is being locked elsewhere; this handoff should supply clocks and threat menu, not overwrite the beat map. | `HANDOFF-c2s23-hester-edge-opening-combat.md` |
| Town model | Contested authority: Salla Vey / Orric Tane / Nera Coalstep / Lysandro mutual-aid. Layout/economy slice owns detailed sites and civic behavior. | `HANDOFF-c2s23-mireward-siege-behavior-layout.md` |
| Existing meat statblocks | Six formatted Shepherd’s Flock statblocks now exist under `Elderwyld/Shephards Flock/Statblocks and Tokens/`. | Statblock hub README |
| Bestiary gap | Monster/ecology content is known to be scattered and not reliably organized/queryable. | `Backlog.md` — “Corpus ingest — monster & ecology layer” |
| Tone | Lovecraftian civic siege: glassy-eyed uncertainty, wrong music, body horror, panicked logistics, and social mistrust, not only wall-defense tactics. | Planning notes / operator direction |

---

## §2 Scope

### A. Siege Mechanics and Escalation Clocks

Design clocks at multiple scales:

- **Round clock:** what happens during the immediate north-gate combat.
- **Minute clock:** 3–8 minute road pressure, gate control, civilian flow, first breach risk.
- **Hour clock:** sorting refugees, isolating glassy-eyed people, food/bed/water pressure, festival panic, bardic morale.
- **Session clock:** how the town moves from shock to siege posture; when the next wave / siege-breaker becomes visible.

Must include:

- breach pressure,
- panic pressure,
- supply pressure,
- bardic morale / counter-song pressure,
- sleeper activation,
- rest rules,
- win / fail / partial-success states,
- and exit conditions for “the party can go north toward Edge.”

### B. Monster and Threat Inventory

Audit and organize threats for this siege:

- existing Shepherd’s Flock / meat statblocks,
- bestiary / Meta Monster candidates if discoverable,
- ingestion gaps,
- glassy-eyed infiltrator threat roles,
- fen horror roles,
- siege scout roles,
- first-wave / second-wave / later-wave mapping,
- and two new monster briefs.

---

## §3 Out of Scope

Do not take over:

- full town layout / economy behavior model,
- exact north-gate encounter script,
- full Celtic punk battlewagon buildout,
- full Edge expedition,
- corpus promotion / statblock finalization,
- or live-control-ui implementation.

You may identify what those slices need from this handoff.

---

## §4 Required Reads

Read these before designing mechanics:

| Priority | Path | Why |
|----------|------|-----|
| 1 | `Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md` | Current locks and open loops |
| 2 | `Docs/Plans/HANDOFF-c2s23-hester-edge-opening-combat.md` | First combat direction |
| 3 | `Docs/Plans/HANDOFF-c2s23-mireward-siege-behavior-layout.md` | Town behavior/layout dependencies |
| 4 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md` §F4 | Brin, refugee count, 3–8 minute road clock |
| 5 | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/README.md` | Existing meat statblock index |
| 6 | The six statblocks listed in that README | Mechanical roles and CRs |
| 7 | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/The cult of the Great  Shephard.md` | Faction / infiltration texture |
| 8 | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 9 - Battle with the Meat Monsters.md` and Session 10 if needed | Prior meat-monster table continuity |
| 9 | `Backlog.md` monster/ecology entry | Known ingest/queryability gap |
| 10 | `evals/c2_live_prep/mireward-prep/statblocks.html` | GM-facing statblock pane |

If using searches for Meta Monsters / bestiary candidates, record the search terms and gaps in the deliverable. Do not claim a bestiary source exists unless you can cite its path.

---

## §5 Existing Threat Baseline

Start with this known table, then refine after reading sheets:

| Threat | Current role hypothesis | Source |
|--------|-------------------------|--------|
| `sewer_meat_creature_statblock_cr3.md` | Baseline CR 3 meat body; default flank pressure / visible body horror. | Shepherd’s Flock statblock hub |
| `corrupted_meat_golem_statblock_cr3.md` | Bruiser / elite anchor; good for a later harder beat or road-blocker. | Shepherd’s Flock statblock hub |
| `fleshborn_hybrid_statblock_cr3.md` | Shock troop / grapple body; possible glassy-eyed-to-meat transitional horror. | Shepherd’s Flock statblock hub |
| `aberrant_meat_wing_statblock_cr1.md` | Flying harasser; panic, rooftop, bell/shrine disruption. | Shepherd’s Flock statblock hub |
| `meat_worm_statblock_cr_half.md` | Density / swarm / corpse or cart surprise. | Shepherd’s Flock statblock hub |
| `shephards_flock_cultist_statblock_cr1.md` | Human cultist / sleeper handler / signaler. | Shepherd’s Flock statblock hub |
| `dustwalker_statblock.md` | Named lieutenant reference; likely not first-wave unless intentionally escalated. | Shepherd’s Flock NPC hub |

Do not assume these are balanced for 6 L5 PCs + 2 allies without checking action economy. The party is strong; the danger may need to come from **civilians, clocks, terrain, and simultaneous pressures**, not raw CR alone.

---

## §6 New Monster Requirements

Create **briefs**, not final statblocks, unless operator asks for statblock promotion.

### A. Large Three-Limbed Alien Monster

Operator requirement: something **large**, **three-limbed**, and **very alien**.

Design asks:

- battlefield role,
- silhouette,
- movement logic,
- why three limbs matter mechanically,
- how it interacts with walls / carts / civilians,
- what sound or sensory clue announces it,
- what statblock it could temporarily reskin,
- what new mechanics would justify a bespoke sheet.

Possible starting frame:

| Field | Prompt |
|-------|--------|
| Role | First major “this is not just meat” reveal; road-bend horror; breaks normal anatomy expectations. |
| Shape | Three uneven limbs around a hanging torso / sensory knot; walks like a broken tripod; no obvious front. |
| Mechanics | Rotates facing, pins multiple targets, shoves carts, ignores some flanking assumptions, reaches over a wall line. |
| Table use | Could be later in the first session if the flank escalates, or held for second wave. |

### B. Later-Wave Siege-Breaking Monster

Operator requirement: a monster introduced in a **later wave** that can threaten the town’s defensive assumptions.

Design asks:

- what structure it breaks,
- why it arrives later,
- what warning clock reveals it,
- how the town can slow it without killing it,
- whether the battlewagon / bards can counter it,
- and what makes it a siege threat rather than just a big monster.

Possible starting frame:

| Field | Prompt |
|-------|--------|
| Role | Gate-breaker / wall-cracker / bell-silencer / ferry-chain breaker. |
| Mechanics | Converts damage to breach progress; attacks structures or crowds; forces party to choose monster vs clock. |
| Counterplay | Bardic counter-rhythm, Nera’s barricades, Lysandro’s bucket/rope teams, Delwen’s ferry chains. |
| Timing | Session clock or later wave, not the first 3–8 minute flank unless operator wants a hard escalation. |

---

## §7 Deliverables

### 1. Clock Stack

Produce a table:

| Clock | Scale | Starts when | Advances when | Visible sign | Consequence at full | Player levers |
|-------|-------|-------------|---------------|--------------|---------------------|----------------|

Include at minimum:

- meat flank arrival,
- gate congestion,
- civilian panic,
- glassy-eyed sleeper activation,
- food / bed / water strain,
- bardic morale / counter-song,
- breach pressure,
- rest / exhaustion pressure,
- battlewagon / relief rumor,
- northbound exit readiness.

### 2. Wave Ladder

Map threats by wave:

| Wave | Trigger | Threats | Civilian pressure | Goal | If party wins fast | If party stalls |
|------|---------|---------|-------------------|------|--------------------|-----------------|

Minimum waves:

- **Wave 0:** refugees / confusion / glassy-eyed uncertainty.
- **Wave 1:** meat flank minutes behind Brin.
- **Wave 2:** sleeper activation or infiltrator signal.
- **Wave 3:** larger alien threat or siege scout.
- **Wave 4:** siege-breaking monster later.

### 3. Threat Inventory

Produce:

| Threat | Source path / status | Role | Use now? | Reskin? | Missing work |
|--------|----------------------|------|----------|---------|--------------|

Mark each as:

- `ready`,
- `reskin-ready`,
- `needs statblock`,
- `needs ingestion`,
- or `idea only`.

### 4. Two New Monster Briefs

Provide structured briefs for:

- the **large three-limbed alien**,
- the **later-wave siege breaker**.

Include names, roles, sensory intro, mechanics, suggested CR band, and whether to build bespoke stats or reskin an existing sheet.

### 5. Rest / Resource Rules

Define the siege rest model:

- Can the party short rest?
- What must be stabilized first?
- What happens if they long rest?
- How do NPC allies / town volunteers cover downtime?
- Which clocks pause, slow, or advance during rest?

Make this table-facing and simple.

### 6. Win / Exit Conditions

Define:

- first-combat win,
- first-hour stabilization,
- siege partial success,
- siege failure / ugly success,
- condition for the party to head north toward Edge,
- and what must remain behind to keep Mireward from collapsing.

### 7. Ingestion / Queryability Gaps

Explicitly list gaps:

- existing Meta Monsters / bestiary paths found,
- missing or unorganized paths,
- statblocks not in current Shepherd’s Flock hub,
- docs that should be indexed or linked later,
- prep UI panes that should link the final inventory.

Tie this to `Backlog.md` monster/ecology layer rather than inventing a new generic backlog item.

---

## §8 Design Principles

- A siege clock is only useful if the party can affect it.
- Do not make glassy-eyed refugees pure enemies by default; make identification morally and tactically difficult.
- Use raw monsters sparingly; let simultaneous civic pressure carry difficulty.
- The first wave should teach the rules of the siege.
- The later siege-breaker should invalidate one comfortable assumption, not all of them.
- Bardic morale should be useful but risky: music is both defense and infection vector.
- Preserve agency: “hold the town forever” is not the goal; creating a path north is.
- For new monsters, silhouette and table behavior matter as much as CR.

---

## §9 Suggested Working Order

1. Re-anchor on planning notes, north-gate handoff, behavior/layout handoff, and scaffold §F4.
2. Read Shepherd’s Flock statblock hub and six sheets.
3. Search for existing Meta Monster / bestiary candidates; record paths and misses.
4. Draft clock stack.
5. Draft wave ladder.
6. Map existing threats onto waves.
7. Design the large three-limbed alien brief.
8. Design the later-wave siege-breaker brief.
9. Define rest / resource rules.
10. Define win / exit conditions.
11. Produce ingestion/queryability gap list.
12. Ask operator which briefs should become statblocks / corpus files later.

---

## §10 Output Shape

Return a compact mechanics package:

1. **Five-bullet re-anchor**.
2. **Clock stack table**.
3. **Wave ladder**.
4. **Threat inventory table**.
5. **Large three-limbed alien monster brief**.
6. **Later-wave siege-breaker monster brief**.
7. **Rest / resource rules**.
8. **Win / exit conditions**.
9. **Ingestion / queryability gaps**.
10. **Open decisions for operator** — max 8.

If editing files, prefer a new planning artifact under `Docs/Plans/` or append decisions to `C2S23-MIREWARD-PLANNING-SESSION-NOTES.md`. Do not edit corpus or create final statblocks unless the operator explicitly asks.

---

## §11 Success Criteria

The operator can answer:

- What clocks are running at round, minute, hour, and session scale?
- What makes the siege worse if the party hesitates?
- What can the party do besides kill monsters?
- Which existing statblocks are ready for use?
- Which threats need reskins, ingestion, or new statblocks?
- What is the first appearance and battlefield role of the three-limbed alien?
- What later monster can break siege assumptions?
- What rest is possible under siege pressure?
- What must be true before the party can leave for Edge?

---

## §12 Open Questions to Ask Early

1. Should the large three-limbed alien appear in Session 23, or only be foreshadowed?
2. Should the siege-breaker target the **north gate**, the **bell/shrine**, the **tithe barn**, or the **ferry/causeway**?
3. Is bardic counter-music magical, mundane morale, or both?
4. Are glassy-eyed civilians infectious, controlled, dreaming, or signal receivers?
5. How harsh should rest pressure be for a party with many allies?
6. Should the first wave include a cultist handler, or keep human agency hidden until later?
7. Should new monsters be bespoke statblocks, reskins, or table notes for now?
8. What does “safe enough to go north” mean: gate held, town calm, supplies allocated, battlewagon arrived, or all of the above?

