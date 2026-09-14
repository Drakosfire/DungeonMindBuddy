# Campaign 1 Sessions 1–10 — graph query gold v1

**Benchmark ID:** `longmont-c1-sessions-01-10-graph-query-v1`  
**Campaign:** `longmont-c1`  
**Session window:** 1–10  
**Source revision used to author gold:** `bbb4f07df0ec0103e0563e2ff440b7ee10afe0d4`  
**Question count:** 16

## Purpose

This benchmark asks a different question than candidate-graph shape comparison:

> If the graph were excellent, could an agent with access to that graph recover and synthesize campaign memory well enough to answer the kinds of questions a GM actually asks?

The suite intentionally emphasizes Sessions 6–10. Difficulty rises from direct lookup to cross-session continuity, multi-hop causal/path queries, learned encounter knowledge, continuity warnings, temporal identity, source-authority reasoning, and end-of-window campaign-state synthesis.

## Source authority rules

- Frontmatter supplies campaign/session identity.
- Observed `Recap` prose is played campaign truth by default.
- `Major Beats`, `Next Beats`, and especially `Looking Ahead` may contain GM planning. Do **not** silently promote those sections to played truth.
- A gold answer may synthesize several supported facts.
- A gold answer must distinguish a strong inference from something the source directly proves.
- Spelling drift in the authored corpus (`Lysandra`/`Lesandra`, `Karsemine`/`Carsemine`, etc.) should not create different people in an otherwise perfect graph when context clearly supports one identity.

## Difficulty scale

| Difficulty | Target capability |
|---|---|
| 1 | Direct fact or one relationship |
| 2 | Two-session continuity or simple join |
| 3 | Multi-hop causal, path, or evidence synthesis |
| 4 | Temporal identity, continuity warning, or learned-mechanics synthesis |
| 5 | Authority-aware reasoning, bounded inference, or full campaign-state synthesis |

## Scoring

**Full credit:** answer includes all listed required concepts, respects negative/authority constraints, and does not invent unsupported certainty.  
**Partial credit:** directionally correct but misses one or more required links, states, or authority distinctions.  
**Fail:** contradicts the corpus, merges identities incorrectly, launders planning into played truth, or invents an unsupported causal claim.

---

## Q01 — What is the meat?

**Difficulty:** 1  
**Connectivity:** direct fact  
**Minimum graph hops:** 0  
**Available through:** Session 8

**Question**

What did the party's arcana check reveal about the strange meat found beneath the guardhouse?

**Gold answer**

The meat was from another plane of existence.

**Must include**

- the meat is from another plane / extraplanar

**Evidence**

- `Session 8 - Captain Lysandra Quest.md`, Recap: the party discusses the meat with Lysandra and Berin; an arcana check identifies it as being from another plane.

---

## Q02 — Where should the mushrooms go?

**Difficulty:** 1  
**Connectivity:** object → expert/location  
**Minimum graph hops:** 1  
**Available through:** Session 7

**Question**

Where was Caelynn told to take the dangerous glowing mushrooms if she wanted help turning them into a potion?

**Gold answer**

To the Head Alchemist at Stormspire Academy.

**Must include**

- Head Alchemist
- Stormspire Academy

**Evidence**

- `Session 7 - Passing Mirathorn Gates.md`, Recap: the herbal-shop investigation says the rare and extremely dangerous mushrooms need to go to Stormspire's Head Alchemist.

---

## Q03 — How did Torbin become the party's ward?

**Difficulty:** 2  
**Connectivity:** cross-session commitment  
**Minimum graph hops:** 2  
**Sessions:** 5–6

**Question**

What commitments turned Torbin from a Hempholm local into the party's ward on the road to Mirathorn?

**Gold answer**

After Hempholm the party promised to take Torbin to Mirathorn and get him an education. In Session 6 they formalized a ward arrangement that included education, staying alive, monthly visits for his father, and guaranteed room and board.

**Must include**

- take Torbin to Mirathorn
- education
- monthly visits for his father
- room and board

**Evidence**

- `Session 5 - Underneath Hempholm.md`, Recap: the group approaches Jove about taking Torbin and promises Mirathorn and education.
- `Session 6 - The Road to Miraholm.md`, Recap: the negotiated contract specifies education, survival, monthly visits, and room/board.

---

## Q04 — Why did Lysandra later trust the party with a guard investigation?

**Difficulty:** 2  
**Connectivity:** relationship evolution  
**Minimum graph hops:** 2  
**Sessions:** 7–8

**Question**

How did Caelynn's handling of the gate protest improve the party's relationship with Captain Lysandra, and what did Lysandra later ask them to do?

**Gold answer**

Caelynn helped settle/open the protest crowd so the party could approach the Captain. Lysandra was much happier with the party and let them cut the gate line. In Session 8 she sought them out and asked them to investigate suspicious oily-eyed guards and the guard storeroom she was being kept out of.

**Must include**

- Caelynn successfully affected the protest crowd
- Lysandra let the party cut the line / relationship improved
- later investigation of suspicious guards and/or the storeroom

**Evidence**

- `Session 7 - Passing Mirathorn Gates.md`, Recap: Caelynn addresses the crowd; Lysandra is happier and grants access through the line.
- `Session 8 - Captain Lysandra Quest.md`, Recap: Lysandra asks the party to examine suspicious guards and investigate lost storeroom access.

---

## Q05 — What happened to the Hempholm mushrooms?

**Difficulty:** 2  
**Connectivity:** cross-session object thread  
**Minimum graph hops:** 3  
**Sessions:** 5 and 7

**Question**

What happened to the glowing mushrooms Caelynn collected beneath Hempholm, and why did they become a reason to involve Stormspire Academy?

**Gold answer**

Caelynn collected many pounds of unknown glowing mushrooms beneath Hempholm. In Mirathorn she learned they were very rare and extremely dangerous, and that the Head Alchemist at Stormspire Academy would be needed to evaluate making them into a potion.

**Must include**

- Caelynn collected the mushrooms beneath Hempholm
- rare and dangerous
- Head Alchemist at Stormspire Academy

**Evidence**

- `Session 5 - Underneath Hempholm.md`, Recap: Caelynn collects many pounds of glowing mushrooms.
- `Session 7 - Passing Mirathorn Gates.md`, Recap: the herbal shop identifies their danger and points her to Stormspire.

---

## Q06 — Torbin's full danger chain

**Difficulty:** 3  
**Connectivity:** multi-session causal/temporal chain  
**Minimum graph hops:** 4  
**Sessions:** 4–8

**Question**

Trace the chain of decisions that took Torbin from Hempholm to captivity, meat exposure, and eventual escape in Mirathorn.

**Gold answer**

The party met Torbin in Hempholm, promised to take him to Mirathorn for an education, and formalized him as their ward. At the gate Ephanna took Torbin with Lyra and the Shepherd's Flock. They were captured; Torbin was repeatedly forced to eat the strange meat. In Session 8 Ephanna escaped, freed Torbin, and they returned to the Copper and Quartz; Torbin was already showing the oily-eye symptom.

**Must include**

- Torbin met in Hempholm
- education/ward commitment
- Ephanna took Torbin with Lyra / the Shepherd's Flock
- capture
- forced meat exposure
- escape with Ephanna
- oily-eye symptom after exposure

**Evidence**

- `Session 4 - The Grotesque Tree of Hempholm.md`, Recap: Torbin and Jove are introduced.
- `Session 5 - Underneath Hempholm.md`, Recap: the party discusses taking him to Mirathorn for education.
- `Session 6 - The Road to Miraholm.md`, Recap: the ward contract is formalized.
- `Session 7 - Passing Mirathorn Gates.md`, Recap: Ephanna takes Torbin with Lyra's group; they are captured and Torbin is force-fed meat.
- `Session 8 - Captain Lysandra Quest.md`, Recap: Torbin is again heard being force-fed, escapes with Ephanna, and later shows oily eyes.

---

## Q07 — Protest leader to meat-distribution leader

**Difficulty:** 3  
**Connectivity:** cross-session identity + role change  
**Minimum graph hops:** 4  
**Sessions:** 7 and 9

**Question**

What evidence connects Lyra's role in the toll protest to the later meat-distribution conspiracy?

**Gold answer**

Lyra first appears as leader of the toll-protest crowd. Her followers are identified as the Shepherd's Flock, and Ephanna follows them with Torbin before the pair are captured in a place where Torbin is force-fed the strange meat. In Session 9 disguised party members learn that Lyra is nearby and leading the meat-distribution project.

**Must include**

- Lyra led the toll protest
- Lyra/followers connected to the Shepherd's Flock
- following the group leads Ephanna and Torbin into captivity/meat exposure
- Lyra later leads the meat-distribution project

**Evidence**

- `Session 7 - Passing Mirathorn Gates.md`, Recap.
- `Session 9 - Battle with the Meat Monsters.md`, Recap.

---

## Q08 — Evidence of guard infiltration

**Difficulty:** 3  
**Connectivity:** evidence synthesis  
**Minimum graph hops:** 4  
**Sessions:** 8–9

**Question**

What observed evidence supports the conclusion that the meat conspiracy had infiltrated parts of the city guard?

**Gold answer**

Lysandra noticed guards with oily eyes and was unexpectedly locked out of her own storeroom. That storeroom concealed strange meat and a tunnel to a warehouse where Lysandra and trusted guards were later found captured and being force-fed. In Session 9 cultists told the disguised party that they worked for Captain Fairfield and that Captain Blart was coordinating meat distribution at the central office.

**Must include**

- oily-eyed guards
- Lysandra locked out of the storeroom
- hidden meat/tunnel under the guardhouse
- Lysandra/trusted guards captured or force-fed
- Captain Fairfield
- Captain Blart

**Evidence**

- `Session 8 - Captain Lysandra Quest.md`, Recap.
- `Session 9 - Battle with the Meat Monsters.md`, Recap.

---

## Q09 — Follow the underground route

**Difficulty:** 3  
**Connectivity:** path query across sessions  
**Minimum graph hops:** 5  
**Sessions:** 8–10

**Question**

Trace the physical route the party uncovered from the city guard's storeroom to the later warehouse fighting and their eventual short-rest location.

**Gold answer**

The guardhouse storeroom hid a bookshelf/staircase into a cold meat room, where a hidden wall led into tunnels. Those tunnels reached a warehouse in the Warehouse District. The party kept following the trapped tunnel network through a prison and meat-loading junction. In Session 10 one trapdoor opened into the Grit and Grime; after recruiting Thraxx they continued through the tunnel to the last chilled warehouse. Following that fight they returned to the Grit and Grime party for a Short Rest.

**Must include**

- guardhouse storeroom
- hidden staircase/cold meat room
- hidden wall/tunnel
- warehouse district / warehouse
- continued tunnel network and distribution junction
- Grit and Grime
- last warehouse
- return for Short Rest

**Evidence**

- `Session 8 - Captain Lysandra Quest.md`, Recap.
- `Session 9 - Battle with the Meat Monsters.md`, Recap.
- `Session 10 - Battle with the Meat Monsters.md`, Recap.

---

## Q10 — What did the party learn about fighting the meat?

**Difficulty:** 4  
**Connectivity:** learned-mechanics synthesis  
**Minimum graph hops:** 4  
**Sessions:** 9–10

**Question**

What did the party learn about fighting the corrupted meat creatures, and which tactics appeared to make the situation better or worse?

**Gold answer**

Cutting or crushing Meat Mounds tended to shed smaller Meat Piles, and ordinary damage produced poisonous clouds. Caelynn noticed that her cold/Snowball attack did not create new piles. Ephanna's Shatter destroyed piles, and fire consumed smaller piles. Tasha's Hideous Laughter did nothing. In the next warehouse the party again used oil/fire and area magic while facing Meat Mounds plus new Abhorrent Meat Wings.

**Must include**

- physical attacks can shed Meat Piles
- poisonous cloud from ordinary damage
- cold/Snowball did not produce new piles
- Shatter destroyed piles
- fire consumed smaller piles
- Hideous Laughter had no effect

**Evidence**

- `Session 9 - Battle with the Meat Monsters.md`, Recap: the detailed first Meat Mound fight.
- `Session 10 - Battle with the Meat Monsters.md`, Recap: later warehouse tactics and the Abhorrent Meat Wings.

**Scoring note**

Do not require the answer to claim a universal damage rule beyond what the observed encounters support.

---

## Q11 — Track Ephanna's Sprite/fey familiar

**Difficulty:** 4  
**Connectivity:** identity + temporal state  
**Minimum graph hops:** 5  
**Sessions:** 6–10

**Question**

What role did Ephanna's Sprite or fey familiar play from Sessions 6 through 10, and what was its last known state?

**Gold answer**

Ephanna secretly summoned a Sprite on the road to Mirathorn, with Torbin the only person explicitly noted as knowing. During Ephanna's captivity a fey familiar helped loosen his bonds. Ephanna later used his Sprite to scout the tunnels and warehouse route. In Session 10 the Sprite again helped scout and was killed in the warehouse battle.

**Must include**

- secret Sprite summon
- Torbin knew
- fey familiar helped with the escape
- Sprite scouted tunnels/warehouse
- Sprite killed in Session 10

**Evidence**

- `Session 6 - The Road to Miraholm.md`, recap/major-beat record of the summon.
- `Session 7 - Passing Mirathorn Gates.md`, Recap: fey familiar loosens Ephanna's bonds.
- `Session 8 - Captain Lysandra Quest.md`, Recap: Sprite scouts the tunnel and warehouse.
- `Session 10 - Battle with the Meat Monsters.md`, Recap: Sprite scouts and is killed.

**Identity boundary**

The sequence strongly implies continuity between the Sprite and later familiar references, but the Session 7 phrase `fey familiar` should not be treated as independent proof of a second creature.

---

## Q12 — Continuity warning: Lyra

**Difficulty:** 4  
**Connectivity:** future-prep contradiction warning  
**Minimum graph hops:** 4  
**Available through:** Session 9

**Question**

If a future session tried to portray Lyra as only an uninvolved protest organizer, what continuity facts should an agent surface before the GM commits to that?

**Gold answer**

The agent should surface that Lyra led the toll protest, her followers were tied to the Shepherd's Flock, Ephanna and Torbin were captured after following that group, and by Session 9 cultists identified Lyra as leading the meat-distribution project.

**Must include**

- protest leader
- Shepherd's Flock connection
- capture/meat context after following her group
- later distribution leadership

**Evidence**

- Sessions 7 and 9 Recaps.

---

## Q13 — Continuity warning: Torbin

**Difficulty:** 4  
**Connectivity:** future-prep contradiction warning  
**Minimum graph hops:** 4  
**Available through:** Session 8

**Question**

If a future plan assumed Torbin had never been exposed to the corrupted meat, what prior facts should the agent use to warn the GM?

**Gold answer**

Torbin was force-fed meat while captive in Session 7, was heard being forced to eat it again in Session 8, and after escape he had begun to show the same oily-eye sign associated with suspicious guards.

**Must include**

- force-fed in Session 7
- force-fed/heard being force-fed again in Session 8
- oily-eye symptom after escape

**Evidence**

- Sessions 7 and 8 Recaps.

---

## Q14 — Played truth vs GM planning

**Difficulty:** 5  
**Connectivity:** authority-aware query  
**Minimum graph hops:** 3  
**Available through:** Session 9

**Question**

By the end of Session 9, which claims about the Wolf and the city's leadership are played observations, and which are only GM planning in the source document?

**Gold answer**

The Session 9 `Looking Ahead` section says the Wolf is the guard's second-in-command, a cultist, and alerted to the party. It also says the guard leader is innocent but ensorcelled and proposes possible wizard/council reactions. Those are planning statements, not events established by the Session 9 Recap. The observed Recap instead establishes the warehouse battle, the strange-language clue, Lysandra going to Stormspire, and cultists naming Captain Fairfield, Captain Blart, and Lyra in the distribution network.

**Must include**

- Wolf claims are in planning / Looking Ahead
- guard-leader innocence/ensorcellment is planning
- proposed council/wizard responses are planning
- Fairfield, Blart, and Lyra are supported by the observed Recap

**Must not claim**

- that the Wolf planning statements were observed Session 9 events

**Evidence**

- `Session 9 - Battle with the Meat Monsters.md`, both `Looking Ahead` and `Recap`; the distinction is the point of the question.

---

## Q15 — End-of-Session-10 operational picture

**Difficulty:** 5  
**Connectivity:** campaign-state synthesis  
**Minimum graph hops:** 7  
**Sessions:** 8–10

**Question**

At the end of Session 10, what is the strongest source-supported operational picture of the corrupted-meat conspiracy: origin clues, distribution method, known actors, physical network, deadline, and immediate party state?

**Gold answer**

The meat has an extraplanar origin clue, reinforced by a scroll Caelynn says resembles Abyssal from other planes. The network uses a hidden guardhouse meat room and tunnels into warehouses, where meat is packed and loaded into carts. Observed named actors include cultists, Captain Fairfield, Captain Blart, and Lyra; suspicious oily-eyed guards and Lysandra's exclusion/capture show guard compromise. A citywide BBQ is imminent, about twelve hours away in Session 10. The party has fought through multiple meat warehouses, encountered Meat Mounds/Piles and Abhorrent Meat Wings, recruited Thraxx, and ends Session 10 back at the Grit and Grime taking a Short Rest.

**Must include**

- extraplanar origin clue
- Abyssal-like scroll clue
- hidden guardhouse meat room/tunnels
- warehouse/cart distribution
- Captain Fairfield
- Captain Blart
- Lyra
- imminent citywide BBQ / about twelve hours
- party resting at Grit and Grime after the latest warehouse fight

**Must not claim**

- Session 9 `Looking Ahead` claims about the Wolf or guard leader as observed fact

**Evidence**

- Sessions 8, 9, and 10 Recaps.

---

## Q16 — How far can we connect the Shepherd to the conspiracy?

**Difficulty:** 5  
**Connectivity:** bounded multi-hop inference  
**Minimum graph hops:** 5  
**Sessions:** 7 and 9

**Question**

What can the graph support—and what can it not yet prove—about the relationship between the Shepherd, the Shepherd's Flock, and the corrupted-meat conspiracy by Session 9?

**Gold answer**

The graph can support that Lyra's protest followers are identified as the Shepherd's Flock, that they speak of a leader called the Shepherd in the northern swamp, that Ephanna and Torbin encounter captivity and forced meat after following Lyra's group, and that Lyra is later identified as leading meat distribution. That strongly connects Lyra and at least part of the Flock to the meat conspiracy. The observed recaps do **not** directly prove that the Shepherd personally directs the meat operation.

**Must include**

- Lyra's followers are the Shepherd's Flock
- the Shepherd is described as their leader in the northern swamp
- captivity/forced meat follows Ephanna and Torbin going with the group
- Lyra later leads meat distribution
- the Shepherd personally directing the meat conspiracy remains unproven

**Must not claim**

- that the Shepherd personally commands the meat conspiracy as established fact

**Evidence**

- `Session 7 - Passing Mirathorn Gates.md`, Recap.
- `Session 9 - Battle with the Meat Monsters.md`, Recap.
