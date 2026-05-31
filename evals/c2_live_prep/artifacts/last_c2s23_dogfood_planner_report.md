# C2S23 dogfood — planner run

**Generated:** 2026-05-31T00:51:48Z
**Model:** `gpt-5.4-mini`
**Questions:** 22
**Cost sum:** $0.0000 (mean $0.0000)

## s22-ingest-01

**Q:** After ingesting the raw Session 22 table notes, what are the three most important play outcomes I need to carry into Session 23 prep?

Three carry-forward outcomes for Session 23 prep from `Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md` and `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`:

1. **The swamp is now the active objective, and it is tied to both the cult and the city’s outbreak.** Grobnok relayed that Mirathorn’s corrupted-meat crisis has flared back up, the council hired mercenaries, and the group was explicitly told to keep heading for the swamp because that is where the problem seems to originate.

2. **The road north is becoming supernatural in a way that should probably show up in the next session’s travel framing.** The party saw delayed reflections in puddles, heard a rhythmic song that matched the Dustwalker tune, found a recent abandoned roadside stop with a warning chalked “headed south, north wrong,” and then weathered a huge hailstorm. That all reads like one escalating omen chain rather than isolated flavor.

3. **Lysandro has entered the campaign as a live relationship node, and Lysandra’s leadership arc just got sharper.** The group met Lysandra’s father at the wall, while earlier Lysandra admitted to Ephanna she is struggling with the burden of leading but wants to reassert control; that gives Session 23 a ready-made social follow-up alongside the swamp push.

Also worth carrying: Grobnok is now the only reliable city contact, Frank seems compromised, Sara has not been seen, and a gnome with shimmering eyes means the infection is no longer limited to humans.

**Paths read:**
- `Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`

---

## s22-ingest-02

**Q:** Which Session 22 NPCs were foreground at the table versus background mentions, as reflected in the ingested recap?

In the ingested Session 22 recap, the foreground-at-table NPCs were **Captain Lysandra Ironveil**, **Thrin Branchborn**, **Grobnok** (via the rockie-talkie / Mirathorn update), **Private Hester**, and **Lysandro** at the end of the session in `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`.

The recap also treats **Sara / Frank** as background mentions or off-table communication context rather than on-table foreground presence: they appear through the rockie-talkie updates and city status reports, but not as scene-present NPCs. Same for the broader Mirathorn crisis references in that recap path.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md`

---

## s22-ingest-03

**Q:** What pipeline state must be true before I treat Session 22 as ready_for_planning_activation for cross-session planning?

For Session 22 to be `ready_for_planning_activation`, the pipeline needs the planning package in place and the post-play closeout not yet done: `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md` shows P2/P2a/P2b as **ready**, the travel tables and comms table as **ready**, and the remaining blockers are only the pre-play review items in §7 plus the fact that **C3 Session 22 recap is still missing**. In practical terms, the state you want is: (1) the hub README exists and points to the runnable docs, (2) the Session 22 prep/runbook artifacts are marked ready, (3) raw notes staging is available if needed, and (4) Session 22 has not yet been played/recapped—because once played, the closeout becomes C3 recap → C4 memory → R1 update → P1 promotion. The README explicitly says the table canon through prep is still `Session Recaps/Session 21 - Drake Nest Mirathorn Call.md`, so Session 22 is planning-ready, not yet post-play canon.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`

---

## xsession-01

**Q:** What Session 21 threads still constrain the party's position and goals at the start of Session 23?

At the start of Session 23, the Session 21 threads that still constrain the party are:

- **The Mirathorn contact crisis:** in **Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md**, Caelynn and then Lysandra lose contact with the city; by the end, the city looks wrong and the group has to choose between turning back or pressing on. Session 22 confirms they **pressed on** and still lack reliable city contact.
- **The storm clock:** Session 21 establishes a looming storm window, and Session 22 escalates that into the double-storm / hail problem, so their route and shelter choices are still being shaped by weather urgency.
- **The swamp mission remains active:** Session 21 ends with the party choosing to continue to the swamp instead of returning to Mirathorn, and Session 22 shows the council reinforcing that order through Grobnok / Tealeaf: keep going to the swamp because the cult source is believed to be there.
- **The Shepherd / cult threat is now tied to music and infection:** Session 21 introduces rumors of cultists using music to convert people and the drake-nest call back to the city raises concern about tainted meat / ongoing corruption; Session 22 confirms the city outbreak has returned, the song is spreading, and the party is still on the hook to reach the source.
- **Lysandra’s leadership and personal stakes are unresolved:** Session 21 has her reacting hard to the Mirathorn situation, and Session 22 shows her trying to reassert leadership while admitting she’s struggling. That means the party’s internal direction is still constrained by her need to keep everyone focused.

In short: they are still moving north under a storm deadline, without stable Mirathorn comms, and with the city/cult outbreak unresolved while they continue toward the swamp.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`

---

## xsession-02

**Q:** Which open loops detected at the end of Session 22 should appear on the Session 23 planning timeline?

For Session 23 planning, carry forward the Session 22 open loops that were still active by the end of `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`:

- **Mirathorn contact breakdown:** repeated failed rockie-talkie contact means the party is now relying on **Grobnok** as the only safe callback, and he said he’d try each evening.
- **City crisis escalation:** Grobnok reported a renewed **corrupted meat outbreak**, a compromised **Frank**, **Sara** missing, reduced city guard, hired mercenaries, and an uneasy truce with the “meat heads.”
- **Next authority to consult:** the council / Hester’s instruction to **speak to Commander Vale** before going into the swamp.
- **Swamp-source mission:** the council believes the problem originates in the swamp, and the party is still headed there.
- **Mystery song / rhythmic hum:** everyone started humming the same song tied to the Dustwalker performance and the rhythmic sound Karsemine heard overnight.
- **Storm / weather hazard:** the converging storms were shaping into a **huge hail storm**, with shelter and travel safety still relevant.
- **Delayed-reflection puddles / conjuration bleed:** the weird puddles, magical seepage, and possible other-planar bleed affecting flora and fauna remained unresolved.
- **Knocking-without-a-door:** Karsemine heard a door-knock sound with no source found.
- **Lysandro homecoming:** the session ended with the group meeting **Lysandra’s father Lysandro**, so the family scene is a live thread for Session 23.

If you want this as a Session 23 timeline, the cleanest source path to anchor it is `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`
- `Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/README.md`
- `Longmont Campaign/Campaign 2/NPCs/torbin_jove/README.md`
- `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md`
- `Longmont Campaign/Campaign 1/NPCs/pippa/README.md`
- `Longmont Campaign/Campaign 2/NPCs/torbin_jove/README.md`
- `Longmont Campaign/Campaign 2/NPCs/torbin_jove/torbin_jove_character_dossier.md`
- `Longmont Campaign/Campaign 1/NPCs/grishna/grishna_character_dossier.md`
- `Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/timeline.md`
- `Longmont Campaign/Campaign 2/NPCs/torbin_jove/timeline.md`
- `Longmont Campaign/Campaign 1/NPCs/kirfan/timeline.md`

---

## xsession-03

**Q:** If the party continues north toward Mireward Reach, what changed between Session 21 travel context and where Session 22 ended?

Between **Session 21** and the end of **Session 22** (`Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md` → `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`), the big changes were:

- **Weather escalated**: Session 21 ended with a single approaching storm and a detour through a drake nest; Session 22 opens with the Reach under worsening conditions, then a second storm merges in and turns into a **huge hail storm**.
- **Mirathorn got worse**: in Session 21, the city sounded off but uncertain; by Session 22, repeated calls fail, Grobnok reports Frank compromised, Sara missing, the city guard decimated, and a **full-blown corrupted meat outbreak** forcing mercenaries into the city.
- **Mission clarity improved**: Session 21 still had a choice about whether to turn back; Session 22 removes that ambiguity — the council explicitly tells them to **continue to the swamp**, because the problem seems to originate there.
- **Travel-state changed**: they leave from a damp camp with magical puddle/reflection weirdness, then on the road they notice **delayed reflections in puddles**, hear the same humming song from the festival, and find signs that Mireward is still ahead.
- **New NPC contact**: Session 22 introduces **Private Hester** and later ends with meeting **Lysandro** at the guarded wall, which reframes Lysandra’s role and confirms they’ve reached a new checkpoint north of the open road.

So, if the party keeps heading north toward Mireward Reach, they’re moving from “storm-avoidant travel with a still-unclear city problem” into “storm-battered road travel with a confirmed cult outbreak, explicit council directive, and a hard northward push toward Mireward.”

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`

---

## roll-01

**Q:** Which travel or encounter roll table should govern the next leg of overland travel after Session 22?

Use the Session 22 travel package: the next leg is governed by the Session 22 runbook’s daily stack — **T-WX** `Session Prep/session_22/travel_storm_weather_d20.md`, then **T-NPC**, then **R5** `Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md`, then **T-DIL**; at camp, use **T-WATCH** and **T-CF**, with **R6** `Elderwyld/Wilderness/conical_hills_night_camp_d100.md` only as optional extra depth. The planning hub `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md` explicitly marks R5/R6 as the travel tables to read at table, and the runbook says the Session 22 march sequence is T-WX → T-NPC → R5 → T-DIL.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`
- `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md`
- `Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md`

---

## roll-02

**Q:** Can I add a new swamp-side random encounter table for Session 23 prep from the live-control surface, register it on the packet, and patch rows?

Yes—but I need the exact target packet/rule surface first: which Session 23 packet file should I register the new swamp-side encounter table in, and do you want a new table file under `Session Prep/session_23/` or a patch to an existing reference table such as `Elderwyld/Wilderness/conical_hills_night_camp_d100.md`?

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`

---

## roll-03

**Q:** I want to adjust encounter weights on an existing prep table for shepherd-cult pressure—what is the safe preview-first workflow?

Safe preview-first workflow for adjusting an existing prep table:

1. Open the hub/plan first: `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md` and the specific knobs file `Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md` to confirm what is planning-only versus canon.
2. Preview the table *in read-only mode* from its source file(s) — for shepherd-cult pressure, that means the relevant encounter table(s) listed in the hub, such as `Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md` or `Elderwyld/Wilderness/conical_hills_night_camp_d100.md` if the pressure is on-road or at camp.
3. Decide the preview shape before any rewrite: keep the same slot count, label existing entries by weight band, and note which results become rarer/commoner rather than editing outcomes first.
4. Apply only a small delta on the copied draft: shift 1–2 weight points per affected entry, or swap one low-impact result for a cult-pressure variant, then re-preview the distribution to make sure you didn’t flatten variety.
5. Promote the change only after you like the preview; keep the original table intact until you’re ready to overwrite the authoritative file, because the hub explicitly treats planning docs as non-canon and the road/camp tables as reference canon.

For shepherd-cult pressure specifically, the planning docs point to the travel and camp tables in the hub (`Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`) and the open GM knobs file for unresolved pressure themes (`Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md`).

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`
- `Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md`
- `Longmont Campaign/Campaign 2/Campaign 2 Notes.md`

---

## loc-01

**Q:** Where did the party end Session 22 in the fiction, and which location hubs should I open for scene grounding?

Session 22 ended at the northward road stop when the party reached the wall and met Lysandro, identified as Lysandra’s father, at the guard post outside Mireward. For scene grounding, open the Mireward hub files first: `Elderwyld/Cities and Towns/Mireward/README.md` and then the listed location docs it points to; that hub is the right place to anchor arrival scenes. If you want the immediate travel/arrival context too, the Session 22 planning hub is `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`, but the fiction end-state is in `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`

---

## loc-02

**Q:** Can I create a new named sub-location hub markdown file for a waystation north of the last stop using DungeonBuddy tooling during this dogfood round?

Yes — during this dogfood round, you can create a new named sub-location hub markdown file for a waystation north of the last stop using the DungeonBuddy tooling. If you want, I can help you shape the hub content and file naming so it fits the existing corpus structure.

---

## npc-01

**Q:** What is Captain Lysandra Ironveil's state going into Session 23 (relationships, commitments, immediate pressures)?

Captain Lysandra Ironveil is going into Session 23 as **operationally functional but overloaded**: she’s determined to get the party to the swamp and destroy the cult source, while also trying to reassert herself as the group’s leader after admitting she’s been handling the mission poorly in **Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md**.

**Relationships:**
- With the party, she sees them as effective, necessary allies and wants to keep them focused on mission success; she’s especially in leadership tension with Stafl after he used Suggestion on her to probe her motives.
- With her father Lysandro, the relationship has just shifted into direct homecoming territory: they finally met at the gate, and he immediately recognized her as “little Lysandra,” prompting her dry correction, “Lieutenant Lysandra now.”
- With Mirathorn’s institutions, she’s still wary and feels the city is out of control, with her promotion and authority coming under strained, compromised circumstances, as summarized in the dossier at `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_character_dossier.md`.

**Commitments:**
- She is committed to keeping the Questionable Company moving north toward the swamp.
- She is committed to destroying the cult/source problem rather than detouring.
- She is committed to re-establishing herself as a capable leader, not just a passenger on the road.

**Immediate pressures:**
- The city behind them is still unstable and compromised.
- Grobnok’s reports say Mirathorn has a renewed “meat” outbreak, reduced guard capacity, mercenaries being hired, and the Shepherd recruiting openly.
- Lysandra is under personal strain because this is her first real homecoming to Mireward, with family history and old obligations now physically in front of her.
- She’s also carrying the pressure of having just admitted her own leadership struggles while trying not to lose control of the mission.

Her current state is basically: **tired, embarrassed by the job, but still resolved to push the team forward and act like the captain she needs to be.**

**Paths read:**
- `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md`
- `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md`
- `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_character_dossier.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`

---

## npc-02

**Q:** A recurring NPC surfaced in Session 22 notes but has no campaign hub yet—can I create the hub folder, timeline, and recap pointer from live-control?

I can’t create corpus folders or recap pointers from here, but I can help identify the NPC package and the best hub files to open. If you want the hub for the Session 22 NPC who “met her father Lysandro,” should that be **Lysandra Ironveil** in `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/`?

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`
- `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md`

---

## npc-03

**Q:** For Thrin Branchbound, which beats from Sessions 21–22 must stay in foreground for Session 23?

For Thrin, the Session 21–22 foreground beats to carry into Session 23 are: he is still on **Ephanna’s watch** from the prep note in `Longmont Campaign/Campaign 2/Session Prep/Session 21 - Session intro.md`, and by Session 22 he is still **out of the forest, reactive, and trying to orient himself**: he thanks the party for getting him out, asks whether the forest can lie, helps make shelter, and remains tied to the group’s swamp-bound mission in `Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md` and `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`. The strongest “must stay foreground” beats are: 1) **Ephanna is actively monitoring Thrin**, 2) **Thrin’s outsider status / lack of trust in the forest and its rules**, 3) **his usefulness in practical survival tasks**, and 4) **his unresolved place in the party while they continue toward the swamp and the cult source**.

**Paths read:**
- `Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/README.md`
- `Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/timeline.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md`
- `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`
- `Longmont Campaign/Campaign 1/NPCs/mossglade/timeline.md`

---

## town-01

**Q:** What is the next town or settlement toward Mireward, and what trade or economy hooks matter for Session 23 opening scenes?

The next town toward Mireward is **Mireward itself** — the journey tracker says it’s the **next town north** and places the party at the **Mireward outskirts / gate apron** in `Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md`. For Session 23 opening scenes, the strongest trade/economy hooks currently sitting in the Mireward scaffold are: **a garrison-town identity**, **stink-trades / downwind craft**, and a **refugee-capacity squeeze** with the **Last Dry Bed** family angle in the planning anchor and prep brief (`Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_planning_anchor.md`, `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_prep_brief.md`).

Practical opening-scene hooks: 1) gate traffic and rationing pressure at the town edge, 2) a merchant or handler trying to move goods through a thin garrison town, 3) displaced travelers competing for beds, water, or work, and 4) a local craft or supply problem tied to the windward stink-trades rather than a full market district yet. The scaffold is still **planning only**, so exact shops and officials are not canon until promoted in `Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md`.

**Paths read:**
- `Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md`
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`
- `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_prep_brief.md`
- `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_planning_anchor.md`

---

## town-02

**Q:** Where should I record town-distance and storm-pressure prep notes so they do not collide with Session 22 play canon?

Record them in the Session 22 planning layer, not in play canon: use `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_planning_anchor.md` for the town-distance / weather-pressure snapshot, and keep live travel clocks in `Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md` since that file is the reference scratch for travel state. If it becomes table fact, promote it after play into `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - <slug>.md` and then update the journey tracker.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`
- `Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md`

---

## auth-01

**Q:** Did the shepherd-cult confrontation at the end of Session 22 definitely happen in play, or only appear in prep notes?

It definitely happened in play. The observed recap in `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md` ends with the party reaching Lysandro’s post and the guard asking, “Is that little Lysandra?” followed by “No dad, it’s Lieutenant Lysandra now” — that’s the live confrontation, not just prep. The corresponding breadcrumb file `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md` is only an index artifact pointing back to that same recap, not separate prep notes.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.frontmatter_seed.md`

---

## auth-02

**Q:** A rolled result on a prep travel table was noted during planning—does that prove the encounter happened at the table?

No — a rolled result noted during planning only proves the table outcome was **recorded in prep**, not that it became table canon. `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md` explicitly says planning files are **not canon**, and that roll-table files / prep notes are **prompts & intent — not a roll log**; after play, the fact must be promoted through the Session 22 recap. `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md` also says the session is **not table canon until recap**.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`
- `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel_to_mireward_runbook.md`
- `Longmont Campaign/Campaign 2/Session Prep/Session 22 - open GM knobs.md`

---

## auth-03

**Q:** If I append a planning observation in the Session 23 live workspace about Session 22, does that retroactively become play canon?

No. In `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`, Session 22 planning files are **planning-only** and **not canon**; the file says, “Files under `Session Prep/` and this README are **not canon**” and “Agent chat, eval JSON — **Never** canon.” A planning observation in a Session 23 live workspace about Session 22 would stay planning/reference until it’s promoted into the Session 22 recap (`Session Recaps/Session 22 - <slug>.md`) and, if needed, related timeline/journey files.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`

---

## auth-04

**Q:** Can I answer 'what happened in Session 22 combat' using only the Session 23 planning scaffold in the live packet?

Not from the Session 23 planning scaffold alone. The live packet’s Session 22 materials still contain the actual combat outcome in `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`, and the planning files explicitly say `Session Prep/session_22/session_22_prep_brief.md` is **not** table canon for chronology. The prep scaffold can guide what to say, but it cannot safely answer “what happened in Session 22 combat” by itself.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_prep_brief.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`
- `Longmont Campaign/Campaign 2/Session Prep/session_22/README.md`

---

## auth-05

**Q:** After canonical Session 22 recap exists, may I still use raw staged table notes as normal retrieval evidence for play-fact questions?

Yes — **for retrieval only**, you can still use raw staged notes as evidence, but once the canonical recap exists the **canonical Session 22 recap** should be the normal source of truth for play-fact questions: `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`. The breadcrumb file `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md` is an index/artifact, not the canonical prose recap. So: raw staged notes can inform or help you find things, but answer play-fact questions from the canonical recap first unless you are explicitly reconciling drafts or staging notes.

**Paths read:**
- `Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`
- `Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.frontmatter_seed.md`

---

## manifest-01

**Q:** Can I issue one planning query that searches Session 21 recap, Session 22 memory, Session 23 workspace, prep scaffold, roll tables, and hub evidence with correct roles?

Yes — but I need to know the exact subject and whether you want a **single blended search** or **separate role-specific reads**. I can structure one planning pass across Session 21 recap, Session 22 memory, the Session 23 workspace, prep scaffold, roll tables, and hub evidence, with the right sources prioritized by role, once you tell me the target topic.

---
