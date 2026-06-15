# HANDOFF — C2S23 Mireward siege behavior + layout/economy model

**Created:** 2026-06-06  
**Branch anchor:** `cursor/c2s23-mireward-prep-ui`  
**Current committed slice:** `24b81b7` — Mireward prep UI, statblocks, and north-gate opening lock  
**Status:** ACTIVE — dispatch to a fresh agent with zero prior chat context.  
**Mode:** Creative planning partner + structured prep organizer. This is **not** a corpus-promotion slice unless the operator explicitly asks.  

**Parent context:**

- `Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md`
- `Docs/Plans/HANDOFF-c2s23-hester-edge-opening-combat.md`
- `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md`
- `evals/c2_live_prep/mireward-prep/index.html`

---

## §0 Mission

Build the **Mireward siege behavior model** and the **layout / economy / key-sites model** together, so the GM can reason about how the town behaves once the north-gate crisis becomes a siege.

The output should make Mireward feel like a place under pressure, not just a backdrop for combat:

- contested leadership,
- civilian panic,
- glassy-eyed infiltrators,
- Edge refugees,
- food / bed / water pressure,
- helpers vs destabilizers,
- chokepoints and key sites,
- and enough layout/economy detail to answer “what happens next if the party chooses X?”

Do **not** write a full gazetteer. Produce a **queryable planning model**: tables, site cards, pressure maps, NPC behavior rows, and concrete GM-facing decisions.

---

## §1 Current Locked Facts / Planning Anchors

Use these as the starting point. Do not re-litigate unless the operator explicitly changes direction.

| Item | Current state | Source |
|------|---------------|--------|
| Party arrival | S22 ended outside Mireward at ~22:00; Lysandro on wall identified Lysandra as his daughter; party has not meaningfully entered town yet. | `Session 22 - Mireward Road and Lysandro.md` |
| Edge packet | **Locked:** Private Hester delivered a detailed Edge packet to Mireward first, then continued south carrying the sealed Mirathorn tube. | `Mireward_PLACE_BUILD_SCAFFOLD.md` §F1; `private_hester/` |
| Edge status | **Locked direction:** Edge is under siege / pinned; Mireward knows enough to prepare but is not ready. | Planning notes; scaffold §F1 |
| Authority cluster | **Locked for S23 open:** Reeve **Salla Vey** (crown stores/paper), Mayor **Orric Tane** (civil calm/festival), **Nera Coalstep** (wall defense), **Lysandro** (mutual-aid mobilizer). | Planning notes; scaffold §F1 / §H; NPC hubs |
| Refugee wave | **Locked:** Brin Holloway leads **55 civilians** from the Edge support column; about half glassy-eyed; meat-monster flank is **3–8 minutes** behind. | Scaffold §F4; `brin_holloway/` |
| First-combat slice | Being handled by the north-gate opening handoff. This handoff should support it, not overwrite it. | `HANDOFF-c2s23-hester-edge-opening-combat.md` |
| Counter-festival | Mireward was preparing a punkier, anarchic, free-spirit music festival counter-programmed against Mirathorn’s civic festival. Bards/performers are present and politically/socially relevant. | Planning notes; handoff |

---

## §2 Scope

### A. Siege Behavior Model

Design how Mireward behaves under pressure.

Must cover:

- town leadership and authority collisions,
- civilian panic patterns,
- glassy-eyed infiltrator uncertainty,
- Edge refugees and support-column guilt,
- food, bed, water, medicine, and shelter pressure,
- who helps,
- who destabilizes,
- who lies or minimizes,
- who becomes brave only when named,
- and what the town does if the party ignores a pressure.

### B. Layout / Economy / Key Sites

Build a practical table map, not a pretty atlas.

Must cover:

- north-south road,
- south gate / mud apron,
- north gate / fen apron,
- tithe barn / crown stores,
- The Last Dry Bed,
- bell / shrine / muster point,
- ferry / causeway head,
- festival spaces,
- refugee overflow spaces,
- chokepoints,
- and what each site contributes or threatens during siege.

---

## §3 Out of Scope

Do not take over:

- exact north-gate combat statblock mix,
- full monster stat inventory,
- Celtic punk battlewagon full buildout,
- full Edge expedition planning,
- corpus promotion / preview / commit,
- or live-control-ui integration.

You may **reference** these where needed, but the deliverable is the behavior/layout model that those later slices can consume.

---

## §4 Required Reads

Read these before proposing structure:

| Priority | Path | Why |
|----------|------|-----|
| 1 | `Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md` | Current locks and open loops |
| 2 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md` | §A2, §B, §C, §D, §E, §F1, §F2, §F4, §H |
| 3 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/README.md` | Current hub index and suggested reads |
| 4 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/NPCs/salla_vey/README.md` + `character_seed.md` | Reeve / crown logistics |
| 5 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/README.md` + `character_seed.md` | Mayor / civilian calm / festival face |
| 6 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/NPCs/nera_coalstep/README.md` + `character_seed.md` | Wall defense |
| 7 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/NPCs/lysandro_ironveil/README.md` + dossier/seed | Mutual-aid mobilizer |
| 8 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/NPCs/brin_holloway/README.md` + `character_seed.md` | Refugee wave lead |
| 9 | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/NPCs/maera_vell/README.md`, `orin_vell/README.md`, `delwen_rast/README.md` | Last Dry Bed and ferry/causeway pressures |
| 10 | `evals/c2_live_prep/mireward-prep/index.html` and sibling panes | Current GM-facing dashboard |

Optional: use the static prep UI markdown popups for fast navigation, but treat corpus/planning docs as source of truth.

---

## §5 Deliverables

### 1. Authority / Behavior Matrix

Create a table like:

| Actor / group | What they want | What they fear | What they do first | If ignored | Helps by | Destabilizes by |
|---------------|----------------|----------------|--------------------|------------|----------|-----------------|

Include at minimum:

- Salla Vey,
- Orric Tane,
- Nera Coalstep,
- Lysandro Ironveil,
- Delwen Rast,
- Maera Vell,
- Orin Vell,
- Brin Holloway,
- festival bards / performers,
- Edge refugees,
- glassy-eyed infiltrators,
- ordinary Mireward families,
- tired wall volunteers,
- ferry / causeway workers,
- tithe-barn clerks.

### 2. Civilian Panic Model

Produce a small set of panic modes the GM can use at the table:

- **Bed panic** — where do 55 more bodies go?
- **Food panic** — who controls grain and who demands it open now?
- **Water / well panic** — queues, contamination fear, glassy-eye suspicion.
- **Name panic** — people recognizing refugees as kin or festival friends.
- **Music panic** — bards are both morale engine and possible threat vector.
- **Glassy-eye panic** — who gets isolated, defended, hidden, or attacked.

For each mode, define:

- trigger,
- first visible sign,
- one NPC who tries to help,
- one NPC or group who makes it worse,
- one player-facing intervention that matters.

### 3. Layout / Economy Skeleton

Produce an ASCII map and site cards.

Minimum map:

```text
[SOUTH GATE / mud apron]
        |
        |  main road: wagons, festival spillover, tired wall volunteers
        |
[festival commons / bell-shrine / Last Dry Bed / tithe barn cluster]
        |
        |  narrowing north road, stores, carts, overflow families
        |
[NORTH GATE / fen apron / causeway-ferry road]
```

Site card shape:

| Site | Normal economic role | Siege role | Who controls it | What can go wrong | Player lever |
|------|----------------------|------------|-----------------|-------------------|--------------|

Minimum sites:

- South Gate / mud apron,
- Main road,
- Tithe barn / crown stores,
- The Last Dry Bed,
- Bell / shrine / muster point,
- Festival commons / stage yard,
- North Gate / fen apron,
- Ferry slip / causeway head,
- Refugee overflow space,
- Downwind craft lane or stink-trade quarter.

### 4. Siege Pressure Interfaces

Define how layout and behavior interact.

At minimum:

- where panic physically concentrates,
- where glassy-eyed infiltrators can disappear,
- where refugees are counted / miscounted,
- where Salla, Orric, Nera, and Lysandro naturally pull the party,
- what site must hold for the party to later leave north,
- what site can fail without ending the session,
- what information each site reveals about Edge.

### 5. Queryable Prep Inventory Entries

Add or propose entries suitable for a future readiness board:

| Prep item | Status | Source / target | Depends on | Table use |
|-----------|--------|-----------------|------------|-----------|

Include every behavior/layout item you create or identify as missing.

---

## §6 Design Principles

Keep these constraints visible:

- Mireward is **not cowardly**. It is underprepared because peace, festival pull, and long patrols made danger feel abstract.
- Mireward is **not Mirathorn-lite**. Its culture is freer, louder, more anarchic, more anti-authoritarian, and proud of distance from city control.
- The siege is **Lovecraftian / civic horror**, not only tactical war. Fear of neighbors, glassy eyes, wrong songs, and bad counts matter.
- Refugees are not a faceless mass. Brin’s bad count should produce names, contradictions, and moral pressure.
- The party should have meaningful levers, not only “fight the monsters.”
- Lysandro should translate abstract authority into named-neighbor action.
- Salla / Orric / Nera should each be right about something and wrong about something.

---

## §7 Suggested Working Order

1. Re-anchor on locked facts from planning notes and scaffold §F1 / §F4.
2. Draft the authority / behavior matrix.
3. Draft the layout skeleton.
4. Attach each panic mode to one or more sites.
5. Identify 3–5 player levers that can reduce escalation.
6. Identify 3–5 destabilizers that worsen if ignored.
7. Convert the model into queryable prep inventory rows.
8. Ask operator which pieces should be promoted into corpus vs left in planning notes.

---

## §8 Output Shape

Return a compact planning package, not prose-only brainstorming:

1. **Five-bullet re-anchor** — what is locked.
2. **Authority / behavior matrix**.
3. **Civilian panic modes**.
4. **ASCII layout + site cards**.
5. **Siege pressure interfaces**.
6. **Queryable prep inventory rows**.
7. **Open decisions for operator** — max 6.

If editing files, prefer `Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md` or a new planning artifact under `Docs/Plans/`. Do not edit corpus unless the operator explicitly asks for corpus promotion.

---

## §9 Success Criteria

The operator can answer, without scrolling chat:

- Who is in charge of what when the siege pressure starts?
- Where do refugees go?
- Where do glassy-eyed people disappear or get exposed?
- Where do food, beds, water, and panic concentrate?
- Which NPCs help, destabilize, minimize, or mobilize?
- Which sites become tactical/social chokepoints?
- What party choices improve the town’s odds before the next combat beat?
- What prep items remain missing for the siege-mechanics and battlewagon handoffs?

---

## §10 Open Questions to Ask Early

1. Is the **tithe barn** inside the wall, just off the main road, or in a crown compound?
2. Is the **festival commons** central, south-apron, or spread along inn yards?
3. Is the **ferry/causeway** beyond the north gate, inside a protected apron, or reachable by side path?
4. Who has the authority to **close the north gate** against civilians?
5. What is the town’s first instinct with glassy-eyed refugees: isolate, hide, treat, deny, or accuse?
6. Which site should the players immediately remember after the session ends?

