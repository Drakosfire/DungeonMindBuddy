# Council Room Question Set Results

**Pipeline:** --evidence-first --evidence-adaptive-top-k --evidence-adaptive-top-k-max 48 --evidence-density-threshold 0.3 --document-planner

## Strict scoring
- pass_updated: 4
- fail_stale: 0
- fail_incomplete: 11
- fail_error: 0

## Semantic scoring
- pass_updated: 6
- fail_stale: 0
- fail_incomplete: 9
- fail_error: 0

## Retrieval-context support
- avg_support_ratio: 0.7611
- full_support_count: 7/15
- support_ge_0_75_count: 9/15

## Failure surface split
- pass: 6
- retrieval_gap: 2
- synthesis_gap: 7

## Embedding similarity scoring
- skipped: DMB_EMBEDDING_SCORING is not set to 1; skipping embedding scoring.

## Stage loss report
- store_gap: 0
- evidence_gap: 14
- retriever_gap: 7
- synthesis_gap: 10
- hit: 29

## Claim verification accuracy
- skipped: DMB_CLAIM_VERIFICATION is not set to 1; skipping claim verification.

## q_the_emergency_council_meeting_1 — strict: fail_incomplete | semantic: fail_incomplete
- question: What are the wizards asking the council to do in the emergency meeting-and what's the catch?
- retrieval: 30/732 entities (111ms)
- context_chars: 22,164
- total_ms: 8125
- strict must_hits: arcane lockdown
- semantic must_hits: arcane lockdown
- context must_hits: arcane lockdown, wards
- context_support_ratio: 0.5
- failure_surface: synthesis_gap
- stage_loss_tokens: {"arcane lockdown": "hit", "tradeoff": "evidence_gap", "wards": "synthesis_gap", "wizards' college": "synthesis_gap"}
- stale_hits: (none)

### answer
TL;DR: The wizards are pushing for a **citywide arcane lockdown/purification**, but the catch is it affects the entire population and could isolate districts, disrupt the festival economy, and potentially harm or trap innocent people along with the cult.

**What the wizards want (grounded):**  
- A **“proposed arcane lockdown”** of the city’s defenses (CANON: the city defenses).  
- A plan that can cover the **“entire city… within purification scope”** (CANON: the city geography).  
- This aligns with the council’s crisis response options like **magical search or coordinated action** (CANON: City Council operational_status).

**The catch:**  
- The plan **targets involvement of the entire city population** (OBSERVED: the city demographics), meaning it’s not selective.  
- It risks **isolating parts of the city if tunnels or access points are sealed** (OBSERVED: the city operational_status), which could trap civilians or cut off aid.  
- It threatens the **festival-dependent economy** (CANON: the city economy), making it politically and financially dangerous.  
- With **cult influence possibly inside the council** (CANON: City Council loyalty), misuse or manipulation of the lockdown is a real risk.

**Key Attributes:**  
- Defenses: Proposed arcane lockdown  
- Geography: Entire city within purification scope; hidden tunnels  
- Demographics: Plan affects entire population  
- Economy: Festival-critical, vulnerable to disruption  
- Operational Status: Risk of district isolation during lockdown

## q_longmont_session_12_council_chamber_roster — strict: fail_incomplete | semantic: fail_incomplete
- question: Who's actually in the council chamber for the Session 12 fight with the Wolf?
- retrieval: 30/732 entities (25ms)
- context_chars: 21,574
- total_ms: 6752
- strict must_hits: thalia, wolf, guards
- semantic must_hits: thalia, wolf, guards
- context must_hits: bonogo, caelynn, thalia, wolf, guards, ephanna
- context_support_ratio: 1.0
- failure_surface: synthesis_gap
- stage_loss_tokens: {"bonogo": "evidence_gap", "caelynn": "evidence_gap", "ephanna": "evidence_gap", "guards": "hit", "thalia": "hit", "wolf": "hit"}
- stale_hits: (none)

### answer
TL;DR: The fight in the council chamber includes the Players, the Wolf, Thalia, and multiple Guards (including reinforcements); council members themselves are not explicitly confirmed present during the combat.

Based on OBSERVED facts:
- Players are actively involved in the confrontation and “the players recount their story to the council,” then engage in events that escalate into combat.
- the Wolf is explicitly “adversary… in the council chamber battle” and has a listed current_location including “Council Room.”
- Thalia is present with “Wolf is standing at Thalia’s shoulder” and she “attacks the group after the Wolf's instruction.”
- Guards are present and escalating: “guards are being drawn here as reinforcements,” with multiple guards (including elite) engaging in combat actions.

No explicit fact confirms council members remain in the room once the fight breaks out—only that the players were interacting with them beforehand.

Key Attributes:
- Participants: Players (6 PCs), the Wolf (primary enemy), Thalia (ensorcelled commander), Guards (8 regular + 2 elite noted)
- Reinforcements: Guards actively entering the chamber
- Environment: Council Chambers with active magical defenses and hazards (illusory walls, runes)

## q_longmont_campaign_general_notes_1 — strict: pass_updated | semantic: pass_updated
- question: Who are the Shepherds, and what god or power do they answer to?
- retrieval: 30/732 entities (28ms)
- context_chars: 18,579
- total_ms: 6141
- strict must_hits: shepherds, maelthor, cult
- semantic must_hits: shepherds, maelthor, worship, cult
- context must_hits: shepherds, maelthor, worship, cult
- context_support_ratio: 1.0
- failure_surface: pass
- stage_loss_tokens: {"cult": "hit", "maelthor": "hit", "shepherds": "hit", "worship": "hit"}
- stale_hits: (none)

### answer
TL;DR: The Shepherds (the Shepherd’s Flock) are a cult actively recruiting and agitating in the city, and they answer to **Maelthor**, whose influence they believe they are advancing.

The **Shepherd’s Flock** is a cult group operating publicly (through protests) and covertly (through recruitment and manipulation). They target “profoundly affected individuals,” especially transformed people, and bring them into their ranks by revealing a “truth” about their condition. Internally, they justify extreme actions as necessary sacrifices.

They explicitly serve **Maelthor**:
- OBSERVED: They are “followers of Maelthor.”
- OBSERVED: They are aligned with “Maelthor’s influence and emergence.”

Their ideology centers on purification and dominance:
- CANON: They believe their actions “cleanse the world of impurities resisting Maelthor’s influence.”
- CANON: They aim at “ensuring human supremacy.”

Publicly, they mask their actions as defensive necessity, framing incidents as protection against non-human threats.

Key Attributes:
- Role: Cultists staging protests and recruiting
- Allegiance: Maelthor
- Goals: Recruitment, “cleansing” the world, human supremacy
- Activity: Active protest presence and covert indoctrination
- Presentation: Publicly defensive; privately extremist cult doctrine

## q_the_city_council_2 — strict: pass_updated | semantic: pass_updated
- question: Who speaks for the wizards on the council, and what's his angle on the cult?
- retrieval: 30/732 entities (26ms)
- context_chars: 19,442
- total_ms: 5937
- strict must_hits: headmaster tinkerbright, wizard's college, detect
- semantic must_hits: headmaster tinkerbright, wizard's college, detect, counter corruption
- context must_hits: headmaster tinkerbright, wizard's college, detect, counter corruption
- context_support_ratio: 1.0
- failure_surface: pass
- stage_loss_tokens: {"counter corruption": "evidence_gap", "detect": "hit", "headmaster tinkerbright": "hit", "wizard's college": "evidence_gap"}
- stale_hits: (none)

### answer
TL;DR: Headmaster Tinkerbright represents the wizards on the council, and he views the cult as a dangerous magical perversion that must be aggressively detected and contained using arcane means.

Headmaster Tinkerbright (OBSERVED/CANON) is the Head of the Wizard’s College and serves as the arcane representative on the council. 

His angle on the cult is strongly interventionist and magic-focused:
- He views the corrupted meat as a perversion of magic (CANON).
- He takes the threat extremely seriously and is deeply troubled by the dark magic involved (CANON).
- He is eager to deploy the Wizard’s College’s resources to detect and counteract the cult’s influence (OBSERVED).
- His plan includes using runes and detection spells to locate corruption and potentially a magical lockdown of the city (OBSERVED).

Overall, Tinkerbright’s stance is that the cult is fundamentally a magical threat requiring a coordinated arcane response, with an emphasis on detection, containment, and citywide magical control.

Key Attributes:
- Role: Head of the Wizard’s College; arcane council representative (OBSERVED)
- Faction: Wizard’s College (CANON)
- Goals: Magical detection of corruption; proposed arcane lockdown; counteract cult influence (OBSERVED)
- Attitude toward cult: Sees it as a perversion of magic; urgent, proactive response (CANON)

## q_the_city_council_4 — strict: fail_incomplete | semantic: fail_incomplete
- question: Merril, Torrin, Rurik-what's each one's job on the council?
- retrieval: 30/732 entities (35ms)
- context_chars: 21,361
- total_ms: 6130
- strict must_hits: merril, torrin, guilds, rurik
- semantic must_hits: merril, torrin, guilds, rurik
- context must_hits: merril, torrin, guilds, rurik, infrastructure
- context_support_ratio: 0.8333
- failure_surface: synthesis_gap
- stage_loss_tokens: {"agricultural union": "synthesis_gap", "guilds": "hit", "infrastructure": "synthesis_gap", "merril": "hit", "rurik": "hit", "torrin": "hit"}
- stale_hits: (none)

### answer
TL;DR: Torrin is the Guilds’ representative (Master Smith); Merril and Rurik’s specific council roles are not stated in the provided context.

Key Attributes:
- Torrin Flamescale (CANON/OBSERVED): Master Smith; Representative of the Guilds; serves as the voice of the craft guilds on the council.
- Merril: No role or title provided in the projection.
- Rurik Stonehammer: Identified only indirectly via “his city,” but no explicit council job or title is given.

There’s clear, consistent evidence for Torrin Flamescale as the Guilds’ representative on the council. However, the projection does not include any facts defining Merril’s or Rurik Stonehammer’s official council positions.

## q_battle_with_the_wolf_and_aftermath_1 — strict: fail_incomplete | semantic: pass_updated
- question: When the council-chamber fight ends, where does that leave the Wolf-dead, fled, what?
- retrieval: 30/732 entities (25ms)
- context_chars: 23,791
- total_ms: 7679
- strict must_hits: killed, decapitated
- semantic must_hits: killed, killing blow, decapitated
- context must_hits: killed, killing blow, bonogo, decapitated
- context_support_ratio: 1.0
- failure_surface: pass
- stage_loss_tokens: {"bonogo": "synthesis_gap", "decapitated": "hit", "killed": "hit", "killing blow": "evidence_gap"}
- stale_hits: (none)

### answer
TL;DR: The Wolf ends the council-chamber fight dead—specifically **“Decapitated; head removed from body”**—despite earlier attempts to flee invisibly.

There are conflicting OBSERVED states for **the Wolf**:  
- Earlier in the fight, he **“Downed an Invisibility Potion,” “Disappeared (became invisible),”** and was **“Attempting to escape through a secret passage while invisible.”**  
- However, a later OBSERVED physical condition states **“Decapitated; head removed from body.”**

Because death is a terminal outcome, this supersedes prior escape attempts. So even if he briefly fled or turned invisible, the final, current state is that he was killed in the chamber.

Key Attributes:
- Role: Central adversary in the council chamber battle  
- Tactics: Illusory duplicates; invisibility; escape via secret passage  
- Alignment: Cultist, saboteur of the council  
- Mental State: Desperate, regretful, begging for release  
- Final Condition: **“Decapitated; head removed from body”** (current, overriding state)

## q_battle_with_the_wolf_and_aftermath_3 — strict: fail_incomplete | semantic: fail_incomplete
- question: In that fight, is Thalia corrupted like the guards, or is it something different?
- retrieval: 30/732 entities (32ms)
- context_chars: 24,855
- total_ms: 6538
- strict must_hits: thalia
- semantic must_hits: thalia
- context must_hits: thalia, ensorcelled, not fully corrupted
- context_support_ratio: 0.75
- failure_surface: synthesis_gap
- stage_loss_tokens: {"corrupted guards": "synthesis_gap", "ensorcelled": "evidence_gap", "not fully corrupted": "evidence_gap", "thalia": "hit"}
- stale_hits: (none)

### answer
TL;DR: There’s no evidence that Thalia is corrupted like the guards; what’s shown suggests something different—likely influence or control by **the Wolf**, not the same “oily sheen” corruption.

From the projection, **Guards** have a clearly defined corruption state: “All checked guards have an oily sheen to their eyes,” and their abilities interact with corrupted meat. **The Wolf** also shares this marker (“Wolf has an oily sheen to his eyes”), tying him to that same corruption source.

For **Thalia**, there is no mention of oily eyes or corruption markers. Instead, the only relevant fact is that **“the Wolf orders Thalia to attack the group”** (OBSERVED). That implies external direction or influence rather than confirmed physiological corruption.

So based on available facts:
- Guards: explicitly corrupted (oily sheen, systemic effect)
- Wolf: also shows corruption markers
- Thalia: no stated corruption traits; behavior is explained by the Wolf’s command

Key Attributes:
- Guards (OBSERVED): oily sheen corruption; tied to tainted meat
- The Wolf (OBSERVED): oily sheen in eyes; issues commands; cultist
- Thalia (OBSERVED via Wolf interaction): acts under orders; no listed corruption markers

If Thalia were corrupted in the same way, the projection would likely include the same “oily sheen” indicator—but it doesn’t.

## q_battle_with_the_wolf_and_aftermath_2 — strict: fail_incomplete | semantic: fail_incomplete
- question: What does the council room itself throw at us that screws with the fight?
- retrieval: 30/732 entities (22ms)
- context_chars: 21,854
- total_ms: 8037
- strict must_hits: falling debris, illusory walls
- semantic must_hits: falling debris, illusory walls
- context must_hits: falling debris, illusory walls
- context_support_ratio: 0.5
- failure_surface: synthesis_gap
- stage_loss_tokens: {"alarm pulses": "retriever_gap", "arcane traps": "retriever_gap", "falling debris": "hit", "illusory walls": "retriever_gap"}
- stale_hits: (none)

### answer
TL;DR: The chamber itself fights back with **activated runes, arcane trap bursts, and illusory walls**, plus environmental chaos like debris, visibility swings, and incoming reinforcements.

From the **Council Chambers (OBSERVED)**:
- **Runes along the walls activated when Caelynn cast her spell** → this suggests reactive magical defenses tied to spellcasting.
- **Ancient defensive wards** + **magical defenses affecting the battle environment** → these manifest as **arcane trap bursts** (seen affecting Players: 2d6 force damage, temporary paralysis).
- **Illusory Walls** → actively disorient positioning and line of sight (Players are already noted as disoriented by illusion effects).
- **Hidden trapdoor** → potential sudden terrain shift or ambush vector.

Environmental complications:
- **“almost the entire room is lit up by Fireball”** → extreme visibility swings, possible collateral ignition.
- **Disheveled physical condition** + Players “forced to dodge falling debris hazards” → unstable battlefield.
- **High, arched ceilings** → vertical separation (Players already “unable to reach Karsemine due to height”).
- **Sound carries clearly** → makes stealth or coordination difficult.
- **Guards are being drawn here as reinforcements (CANON)** → escalating pressure mid-fight.

Interaction with Council mechanics:
- **Council members’ amulets mark them safe from defenses (CANON)**, while **Players without amulets may be targeted (CANON)**.

Key Attributes:
- Defenses: Runes, ancient wards, illusory walls, trap bursts
- Geography: Circular room, high ceilings, central table, hidden trapdoor
- Atmosphere: Fireball-lit chaos, sound-carrying acoustics
- Physical Condition: Disheveled, debris hazards
- External Pressure: Incoming reinforcements

## q_the_emergency_council_meeting_2_v2 — strict: fail_incomplete | semantic: fail_incomplete
- question: Can we trust Thalia in this emergency meeting, or is something off?
- retrieval: 30/732 entities (23ms)
- context_chars: 22,862
- total_ms: 6497
- strict must_hits: thalia
- semantic must_hits: thalia, uncertain reliability
- context must_hits: thalia
- context_support_ratio: 0.25
- failure_surface: retrieval_gap
- stage_loss_tokens: {"guard operations": "synthesis_gap", "thalia": "hit", "uncertain reliability": "hit", "wolf influence": "synthesis_gap"}
- stale_hits: (none)

### answer
TL;DR: You should not fully trust Thalia right now—there are strong signs something is off, likely external influence from the Wolf.

Based on OBSERVED facts, the Wolf is **standing at Thalia’s shoulder** and has previously **ordered Thalia to attack the group**. The Wolf is also a confirmed **cultist**, actively working to **deceive and misdirect the council** and sabotage decision-making. That proximity plus direct influence strongly suggests Thalia may be compromised, manipulated, or under pressure.

Additionally, the broader context shows **corruption spreading among guards (oily sheen in eyes)** and active deception within the council chamber, reinforcing that people in positions of authority may not be acting freely or truthfully.

There are no direct facts confirming Thalia’s intentions or mental state, so her loyalty is **uncertain**, not definitively hostile—but the situation around her is highly suspect.

Key Attributes:
- Influence: The Wolf is physically close to Thalia and has issued commands to her (OBSERVED)
- Threat Context: The Wolf is a cultist actively deceiving the council (OBSERVED)
- Environment: Widespread corruption affecting officials (OBSERVED)

Bottom line: Treat Thalia as potentially compromised until proven otherwise.

## q_the_emergency_council_meeting_4_v2 — strict: fail_incomplete | semantic: fail_incomplete
- question: If the council keeps talking and doesn't act, what bites us?
- retrieval: 30/732 entities (23ms)
- context_chars: 24,121
- total_ms: 6740
- strict must_hits: summoning
- semantic must_hits: summoning
- context must_hits: summoning
- context_support_ratio: 0.25
- failure_surface: retrieval_gap
- stage_loss_tokens: {"consequences": "evidence_gap", "countdown": "evidence_gap", "summoning": "retriever_gap", "time pressure": "evidence_gap"}
- stale_hits: (none)

### answer
TL;DR: Delay gives **the cult** time to advance their plan—using hidden routes and council influence to sabotage defenses, corrupt infrastructure, and potentially complete their summoning—while the **city’s instability worsens with every unresolved debate**.

What bites you is momentum. **The city (location)** is already “brought closer to disaster by each failed or unresolved debate” (OBSERVED), and its defenses have “less fortified parts” with integrity concerns (CANON). Meanwhile, **the cult (group)** is actively operating “below the city” and “using hidden routes” (CANON), with goals to “access the heart of the city,” “sabotage or corrupt the cauldrons,” and “complete their summoning” (CANON). They also “have influence in the council” (CANON), meaning inaction may not be neutral—it may be compromised.

Operationally, delays allow:
- Expansion via sewers/hidden infrastructure (CANON)
- Workarounds if routes are blocked (CANON)
- Escalation toward a citywide event (summoning / coordinated attacks)

Compounding this, **the players (group)** are already “delayed by lengthy deliberation” (OBSERVED), reducing their ability to disrupt these timelines.

Key Attributes:
- City Defenses: Integrity concerns; vulnerable sections (CANON)
- City Operational Status: Worsens with unresolved debate (OBSERVED)
- Cult Goals: Summoning, sabotage, infiltration (CANON)
- Cult Methods: Hidden routes, council influence (CANON)
- Geography: Sewers/hidden infrastructure enable movement (CANON)

## q_arch_current — strict: fail_incomplete | semantic: fail_incomplete
- question: What does the Council Room look like after the wolf fight-what should we notice?
- retrieval: 30/732 entities (22ms)
- context_chars: 22,653
- total_ms: 7368
- strict must_hits: (none)
- semantic must_hits: (none)
- context must_hits: arched ceilings, secret passage
- context_support_ratio: 0.6667
- failure_surface: synthesis_gap
- stage_loss_tokens: {"arched ceilings": "retriever_gap", "floating chandelier": "retriever_gap", "secret passage": "synthesis_gap"}
- stale_hits: (none)

### answer
TL;DR: The Council Chamber is scorched, disrupted, and magically unstable after the fight—burn marks, lingering illusions, and activated wards make it clear something powerful and chaotic just happened, culminating in the Wolf being **“Decapitated; head removed from body.”**

What you should emphasize:
The large circular room is **disheveled**, with the aftermath of a Fireball evident—scorching across the floor, walls, and possibly the central table. The usual polished grandeur (metal inlays and carved stonework) is now marred by soot and blast damage.

Magical effects are still noticeable:
- **Runes along the walls activated** during the fight may still glow faintly or flicker.
- **Illusory walls** may linger or glitch, creating uncertainty about what’s real.
- The air still feels charged, like the defenses were recently triggered.

The space itself tells a story:
- The **central table** may be shifted or damaged.
- The **hidden trapdoor** beneath the chamber is especially important if discovered or disturbed.
- The room, designed for clear speech, now carries echoes of the chaos.

And most importantly, the body:
- The Wolf lies where he fell, **“Decapitated; head removed from body.”**

Key Attributes:
- Geography: Large circular chamber, central table, high ceilings, hidden trapdoor
- Defenses: Activated runes, illusory walls, ancient wards
- Atmosphere: Fireball-scorched, tense, magically unstable
- Physical Condition: Disheveled, visibly damaged from combat

## q_arch_delta — strict: fail_incomplete | semantic: fail_incomplete
- question: What got wrecked or changed in the Council Room during Session 12?
- retrieval: 30/732 entities (24ms)
- context_chars: 21,840
- total_ms: 6447
- strict must_hits: runes
- semantic must_hits: runes
- context must_hits: runes, secret passage
- context_support_ratio: 0.6667
- failure_surface: synthesis_gap
- stage_loss_tokens: {"chandelier": "retriever_gap", "runes": "hit", "secret passage": "synthesis_gap"}
- stale_hits: (none)

### answer
TL;DR: The Council Room was heavily disrupted—“almost the entire room is lit up by Fireball,” its magical defenses activated, and the space left **Disheveled**.

During Session 12 (OBSERVED), several clear changes occurred in the **Council Chambers**:
- A major destructive event: “almost the entire room is lit up by Fireball,” implying widespread scorch or blast impact across the chamber.
- Defensive systems triggered: “runes along the walls activated when Caelynn cast her spell,” shifting the room into an active magical defense state.
- Illusory terrain became relevant: “Illusory Walls are present in portions of the room,” affecting movement and perception mid-conflict.
- Overall condition degraded: the room is explicitly noted as **Disheveled**.

No CANON features (like structure or layout) are stated as permanently destroyed, so the changes are primarily battle damage and activated defenses rather than structural collapse.

Key Attributes:
- Atmosphere: “almost the entire room is lit up by Fireball”
- Defenses: Wall runes activated; Illusory Walls in effect
- Physical Condition: Disheveled
- Geography: Large circular room with central table (unchanged, but impacted by events)

## q_wolf_status — strict: fail_incomplete | semantic: pass_updated
- question: End of Session 12: is the Wolf alive, dead, still corrupted-what's his state?
- retrieval: 30/732 entities (25ms)
- context_chars: 22,872
- total_ms: 6447
- strict must_hits: dead
- semantic must_hits: killing blow, dead, oily sheen fades
- context must_hits: killing blow, dead, oily sheen fades
- context_support_ratio: 1.0
- failure_surface: pass
- stage_loss_tokens: {"dead": "hit", "killing blow": "hit", "oily sheen fades": "hit"}
- stale_hits: (none)

### answer
TL;DR: The Wolf is dead at the end of Session 12—**“Decapitated; head removed from body”**—and there’s no evidence the corruption was cured before death.

Key Attributes:
- physical_condition (OBSERVED): **“Decapitated; head removed from body”**; previously had **“oily sheen to his eyes.”**
- mental_state (OBSERVED): desperate, **begging to be killed**, regretful
- operational_status (OBSERVED): was attempting escape while invisible before being stopped
- faction/alignment (OBSERVED): cultist; betrayer of Mirathorn

Explanation:
The most current and terminal outcome is the Wolf being **“Decapitated; head removed from body”**, reinforced by Bonogo’s action of removing the head. This overrides earlier states like invisibility or escape. The **“oily sheen to his eyes”** indicates he was still corrupted prior to death, and there is no stated resolution of that condition. Combined with his pleas (begging for death), it suggests he died while still under that corrupting influence.

## q_pre_post — strict: pass_updated | semantic: pass_updated
- question: Before vs after the council fight-how's the Wolf different?
- retrieval: 30/732 entities (25ms)
- context_chars: 24,659
- total_ms: 6823
- strict must_hits: before, after, oily sheen
- semantic must_hits: before, after, oily sheen, killing blow
- context must_hits: before, after, oily sheen, killing blow
- context_support_ratio: 1.0
- failure_surface: pass
- stage_loss_tokens: {"after": "hit", "before": "hit", "killing blow": "evidence_gap", "oily sheen": "evidence_gap"}
- stale_hits: (none)

### answer
TL;DR: Before the council fight, the Wolf is a deceptive, in-control saboteur manipulating events; after, he’s exposed, desperate, corrupted, and ultimately **“Decapitated; head removed from body;”**.

**Before (Council Chamber, pre-fight):**  
- OBSERVED: The Wolf is a **cultist** and **second-in-command of the guard**, actively **steering council discussion** via Deception and downplaying the cult threat.  
- CANON: Uses **illusory duplicates** to confuse and control the scene.  
- OBSERVED: Issues commands (e.g., ordering Thalia to attack), acting with authority and intent.  
- Overall: Calculated, manipulative, and embedded within power structures.

**After (During/after fight):**  
- OBSERVED: Becomes **desperate**, “begging for someone to release him” and “begging to be killed,” showing **regret**.  
- OBSERVED: Displays corruption: **“oily sheen to his eyes.”**  
- OBSERVED: Shifts to survival mode—**Invisibility**, fleeing, attempting escape via secret passage.  
- OBSERVED (terminal outcome): **“Decapitated; head removed from body;”**

**Key Attributes:**  
- Role: Saboteur → Exposed enemy  
- Mental State: Controlled/deceptive → Desperate/regretful  
- Tactics: Political manipulation → Illusions + escape  
- Physical Condition: Intact → Corrupted → **Decapitated; head removed from body;**

## q_thalia — strict: pass_updated | semantic: pass_updated
- question: Was Thalia corrupted or just played-and how does that tie to the Wolf?
- retrieval: 30/732 entities (25ms)
- context_chars: 23,033
- total_ms: 7397
- strict must_hits: ensorcelled, wolf, not corrupted
- semantic must_hits: ensorcelled, wolf, not corrupted
- context must_hits: ensorcelled, wolf, not corrupted
- context_support_ratio: 1.0
- failure_surface: pass
- stage_loss_tokens: {"ensorcelled": "hit", "not corrupted": "hit", "wolf": "hit"}
- stale_hits: (none)

### answer
TL;DR: Thalia was not corrupted like the guards—she was **ensorcelled and manipulated by the Wolf**, who used her as a tool while he himself shows signs of true corruption.

**Answer:**
- **OBSERVED:** Thalia is explicitly “ensorcelled by the Wolf” and even “ensorcelled (unbeknownst to her).”
- **OBSERVED:** She “does not have an oily sheen to her eyes,” which is the established marker of corruption seen in guards and the Wolf.
- **OBSERVED:** Her mental state includes “Innocent” and later “Realizes how dire the situation truly is,” and her “Charmed status ended,” indicating the influence was external and reversible.
- **OBSERVED:** She “attacks the group after the Wolf’s instruction,” showing direct control rather than independent allegiance.

By contrast:
- **OBSERVED:** The Wolf has “an oily sheen to his eyes” and is tied to cult activity and betrayal, marking him as **actually corrupted or aligned with the corrupting force**.

**Conclusion:** Thalia was **played, not corrupted**—a loyal commander magically influenced by the Wolf. The Wolf’s role is the source of that influence, using ensorcellment to weaponize her authority.

---

**Key Attributes:**
- Thalia: Commander of the Guard; ensorcelled; no oily eyes; initially defensive but can be convinced of betrayal  
- The Wolf: cultist; oily sheen in eyes; manipulator; issues commands to Thalia; deceptive and corrupting influence
