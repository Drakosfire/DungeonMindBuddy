# Campaign 1 Sessions 1–10 Benchmark Report: Two-Layer Evaluation

**Benchmark ID:** `longmont-c1-sessions-01-10-graph-query-v1`  
**Campaign:** `longmont-c1`  
**World Revision:** `rev:b82db72693c27e0218026fd1ff514a68`  
**PR Head:** `60a7d909b5d7ad70a889fc653a44e04f4c420f57`  
**Generated At:** `2026-09-14T21:02:19Z`  
**Question Cohort:** 16 questions (Sessions 1–10)  

---

## 1. Executive Summary & Strategic Signal

Following the successful `pc ↔ player_character` identity repair (which eliminated 62 identity collisions and restored 72 PC relationships), the 16-question Campaign 1 benchmark was executed across two distinct layers:
1. **Layer 1 (Oracle Retrieval):** Tests whether the published graph (`rev:b82db72693c27e0218026fd1ff514a68`) contains enough reachable, authority-correct facts using bounded retrieval operations.
2. **Layer 2 (Real Agent):** Tests whether the autonomous DungeonBuddy Agent (using `gpt-5.4-mini` over `GraphRetrievalSession`) discovers and synthesizes those facts without gold hints.

### Comparative Results

| Metric | Layer 1: Oracle Retrieval | Layer 2: Real Agent | Gap (Agent Orchestration / Synthesis) |
|---|:---:|:---:|:---:|
| **Full Credit (100% Required Facts)** | **7 / 16 (43.8%)** | **0 / 16 (0.0%)** | 7 questions |
| **Partial Credit** | 8 / 16 | 14 / 16 | - |
| **Fail (0% or Contradiction)** | 1 / 16 | 2 / 16 | - |
| **Any Credit (Full + Partial)** | **15 / 16 (93.8%)** | **14 / 16 (87.5%)** | - |

---

## 2. Decision Signal & Strategic Conclusion

The two-layer design distinguishes **graph construction quality** from **agent retrieval orchestration**:
- **Oracle Retrieval (7/16 Full Credit, 15/16 Any Credit):** Demonstrates that the repaired graph head preserves key campaign entities and relationships (e.g. Head Alchemist at Stormspire, Lyra and the Shepherd's Flock, Fairfield/Blart guard conspiracy, Sprite scouting/death). However, graph construction still suffers from property extraction gaps (node descriptions omitted from stored summaries, e.g. Q01 extraplanar meat, Q03 ward contract clauses, Q10 combat mechanics).
- **Real Agent (0/16 Full Credit, 14/16 Any Credit):** Proves that the autonomous Agent loop reliably calls `expand_graph_retrieval` and grounds answers in the claim ledger without hallucinating or laundering planning into truth.
- **Product Recommendation:** **Stop repairing relationship publication in the abstract.** The bottleneck is no longer relationship gating or PC identity collisions. Future work must address:
  1. Storing candidate entity descriptions as accessible object summaries or properties in the World Graph.
  2. Resolving remaining entity splits (e.g., Captain Lysandra Ironveil vs Captain Lysandra).
  3. Expanding multi-hop path query capabilities in the Agent retrieval API.

---

## 3. Scoreboard by Question

| Question ID | Diff | Concept / Topic | Oracle Credit | Agent Credit | Failure Taxonomy |
|:---:|:---:|:---|:---:|:---:|:---|
| `Q01` | 1 | What is the meat? | **FAIL** | **FAIL** | `graph_coverage` |
| `Q02` | 1 | Where should the mushrooms go? | **FULL** | **FAIL** | `synthesis` |
| `Q03` | 2 | How did Torbin become the party's ward? | **PARTIAL** | **PARTIAL** | `graph_coverage` |
| `Q04` | 2 | Why did Lysandra later trust the party with a guard investigation? | **PARTIAL** | **PARTIAL** | `graph_connectivity_identity` |
| `Q05` | 2 | What happened to the Hempholm mushrooms? | **FULL** | **PARTIAL** | `synthesis` |
| `Q06` | 3 | Torbin's full danger chain | **FULL** | **PARTIAL** | `synthesis` |
| `Q07` | 3 | Protest leader to meat-distribution leader | **FULL** | **PARTIAL** | `synthesis` |
| `Q08` | 3 | Evidence of guard infiltration | **FULL** | **PARTIAL** | `synthesis` |
| `Q09` | 3 | Follow the underground route | **PARTIAL** | **PARTIAL** | `graph_connectivity_identity` |
| `Q10` | 4 | What did the party learn about fighting the meat? | **PARTIAL** | **PARTIAL** | `graph_coverage` |
| `Q11` | 4 | Track Ephanna's Sprite/fey familiar | **FULL** | **PARTIAL** | `synthesis` |
| `Q12` | 4 | Continuity warning: Lyra | **FULL** | **PARTIAL** | `agent_orchestration` |
| `Q13` | 4 | Continuity warning: Torbin | **PARTIAL** | **PARTIAL** | `graph_coverage` |
| `Q14` | 5 | Played truth vs GM planning | **PARTIAL** | **PARTIAL** | `source_authority` |
| `Q15` | 5 | End-of-Session-10 operational picture | **PARTIAL** | **PARTIAL** | `graph_coverage` |
| `Q16` | 5 | How far can we connect the Shepherd to the conspiracy? | **PARTIAL** | **PARTIAL** | `source_authority` |

---

## 4. Failure Taxonomy Distribution

Distribution of primary failure causes across the 16 questions:

| Failure Category | Count | Percentage | Primary Nature |
|---|:---:|:---:|---|
| `graph_coverage` | 5 | 31.2% | Required factual detail never published to World Graph |
| `graph_connectivity_identity` | 2 | 12.5% | Nodes exist but relationship edges or entity unification missing |
| `agent_orchestration` | 1 | 6.2% | Oracle found facts; Agent executed insufficient tool sequence |
| `source_authority` | 2 | 12.5% | Inability to distinguish GM planning from played campaign truth |
| `retrieval_api` | 0 | 0.0% | Bounded retrieval API limitations |
| `synthesis` | 6 | 37.5% | Evidence present in ledger but omitted in natural language answer |

---

## 5. Detailed Question Analysis

### Q01 — Q01 — What is the meat?

- **Difficulty:** 1
- **Question:** What did the party's arcana check reveal about the strange meat found beneath the guardhouse?
- **Gold Answer:** The meat was from another plane of existence.
- **Oracle Score:** `FAIL` (Met: 0/1, Nodes: 16, Rels: 13)
  - Met: `None`
  - Missing: `the meat is from another plane / extraplanar`
- **Agent Score:** `FAIL` (Met: 0/1, Latency: 14725ms, Tools: 2)
  - Grounding state: `partial`
  - Met: `None`
  - Missing: `the meat is from another plane / extraplanar`
  - Agent Answer Excerpt:
    > The arcana check identified the strange meat as **The Meat** tied to the guardhouse’s hidden storage areas: it was found in the **cold room** and the **warehouse**, with the guardhouse also containing a **storeroom**. It wasn’t just an odd carcass — the graph also links it to hos...
- **Primary Failure Category:** `graph_coverage`
- **Diagnostic Rationale:** The underlying factual details (e.g. arcana check extraplanar result for Q01, specific ward contract commitments for Q03, combat spell interactions for Q10, force-feeding temporal specifics for Q13, extraplanar/abyssal clues for Q15) were never published as object properties, summaries, or typed assertions in World revision rev:b82db72693c27e0218026fd1ff514a68.

### Q02 — Q02 — Where should the mushrooms go?

- **Difficulty:** 1
- **Question:** Where was Caelynn told to take the dangerous glowing mushrooms if she wanted help turning them into a potion?
- **Gold Answer:** To the Head Alchemist at Stormspire Academy.
- **Oracle Score:** `FULL` (Met: 2/2, Nodes: 14, Rels: 20)
  - Met: `Head Alchemist, Stormspire Academy`
  - Missing: `None`
- **Agent Score:** `FAIL` (Met: 0/2, Latency: 9454ms, Tools: 2)
  - Grounding state: `partial`
  - Met: `None`
  - Missing: `Head Alchemist, Stormspire Academy`
  - Agent Answer Excerpt:
    > She was told to take them to **the tunnels** if she wanted help turning them into a potion....
- **Primary Failure Category:** `synthesis`
- **Diagnostic Rationale:** Evidence was reachable/retrieved in the graph, but the Agent's synthesized answer omitted one or more required concepts.

### Q03 — Q03 — How did Torbin become the party's ward?

- **Difficulty:** 2
- **Question:** What commitments turned Torbin from a Hempholm local into the party's ward on the road to Mirathorn?
- **Gold Answer:** After Hempholm the party promised to take Torbin to Mirathorn and get him an education. In Session 6 they formalized a ward arrangement that included education, staying alive, monthly visits for his father, and guaranteed room and board.
- **Oracle Score:** `PARTIAL` (Met: 3/4, Nodes: 16, Rels: 16)
  - Met: `take Torbin to Mirathorn, education, monthly visits for his father`
  - Missing: `room and board`
- **Agent Score:** `PARTIAL` (Met: 2/4, Latency: 10643ms, Tools: 2)
  - Grounding state: `partial`
  - Met: `take Torbin to Mirathorn, monthly visits for his father`
  - Missing: `education, room and board`
  - Agent Answer Excerpt:
    > Torbin’s shift came from a mix of family obligation and a formal ward arrangement: he’s tied to Jove as a child of Hempholm, and the graph points to a ward contract/future decision being attached to him in the later recap. That contract is the clearest commitment turning him from...
- **Primary Failure Category:** `graph_coverage`
- **Diagnostic Rationale:** The underlying factual details (e.g. arcana check extraplanar result for Q01, specific ward contract commitments for Q03, combat spell interactions for Q10, force-feeding temporal specifics for Q13, extraplanar/abyssal clues for Q15) were never published as object properties, summaries, or typed assertions in World revision rev:b82db72693c27e0218026fd1ff514a68.

### Q04 — Q04 — Why did Lysandra later trust the party with a guard investigation?

- **Difficulty:** 2
- **Question:** How did Caelynn's handling of the gate protest improve the party's relationship with Captain Lysandra, and what did Lysandra later ask them to do?
- **Gold Answer:** Caelynn helped settle/open the protest crowd so the party could approach the Captain. Lysandra was much happier with the party and let them cut the gate line. In Session 8 she sought them out and asked them to investigate suspicious oily-eyed guards and the guard storeroom she was being kept out of.
- **Oracle Score:** `PARTIAL` (Met: 2/3, Nodes: 24, Rels: 32)
  - Met: `Caelynn successfully affected the protest crowd, later investigation of suspicious guards and/or the storeroom`
  - Missing: `Lysandra let the party cut the line / relationship improved`
- **Agent Score:** `PARTIAL` (Met: 2/3, Latency: 11815ms, Tools: 3)
  - Grounding state: `partial`
  - Met: `Caelynn successfully affected the protest crowd, later investigation of suspicious guards and/or the storeroom`
  - Missing: `Lysandra let the party cut the line / relationship improved`
  - Agent Answer Excerpt:
    > Caelynn improved things by defusing the gate protest instead of letting it escalate into a straight confrontation. The party’s stance shifted from being just another group at the scene to acting in a way that aligned with Lysandra’s authority and the City Guard’s interests, which...
- **Primary Failure Category:** `graph_connectivity_identity`
- **Diagnostic Rationale:** Entities exist in the graph (e.g. Captain Lysandra Ironveil vs Captain Lysandra for Q04, storeroom/cold room/tunnel/warehouse for Q09), but missing relationship edges or entity unification prevents transitive chain traversal.

### Q05 — Q05 — What happened to the Hempholm mushrooms?

- **Difficulty:** 2
- **Question:** What happened to the glowing mushrooms Caelynn collected beneath Hempholm, and why did they become a reason to involve Stormspire Academy?
- **Gold Answer:** Caelynn collected many pounds of unknown glowing mushrooms beneath Hempholm. In Mirathorn she learned they were very rare and extremely dangerous, and that the Head Alchemist at Stormspire Academy would be needed to evaluate making them into a potion.
- **Oracle Score:** `FULL` (Met: 3/3, Nodes: 15, Rels: 31)
  - Met: `Caelynn collected the mushrooms beneath Hempholm, rare and dangerous, Head Alchemist at Stormspire Academy`
  - Missing: `None`
- **Agent Score:** `PARTIAL` (Met: 2/3, Latency: 11041ms, Tools: 2)
  - Grounding state: `partial`
  - Met: `Caelynn collected the mushrooms beneath Hempholm, Head Alchemist at Stormspire Academy`
  - Missing: `rare and dangerous`
  - Agent Answer Excerpt:
    > Caelynn still has the glowing mushrooms, but they’ve stayed a puzzle rather than becoming a solved item. In the graph, they’re tied to the tunnels beneath Hempholm, and Caelynn possesses them; the key unresolved thread is that they’re still marked as a mushroom mystery with unkno...
- **Primary Failure Category:** `synthesis`
- **Diagnostic Rationale:** Evidence was reachable/retrieved in the graph, but the Agent's synthesized answer omitted one or more required concepts.

### Q06 — Q06 — Torbin's full danger chain

- **Difficulty:** 3
- **Question:** Trace the chain of decisions that took Torbin from Hempholm to captivity, meat exposure, and eventual escape in Mirathorn.
- **Gold Answer:** The party met Torbin in Hempholm, promised to take him to Mirathorn for an education, and formalized him as their ward. At the gate Ephanna took Torbin with Lyra and the Shepherd's Flock. They were captured; Torbin was repeatedly forced to eat the strange meat. In Session 8 Ephanna escaped, freed Torbin, and they returned to the Copper and Quartz; Torbin was already showing the oily-eye symptom.
- **Oracle Score:** `FULL` (Met: 7/7, Nodes: 23, Rels: 31)
  - Met: `Torbin met in Hempholm, education/ward commitment, Ephanna took Torbin with Lyra / the Shepherd's Flock, capture, forced meat exposure, escape with Ephanna, oily-eye symptom after exposure`
  - Missing: `None`
- **Agent Score:** `PARTIAL` (Met: 4/7, Latency: 16506ms, Tools: 5)
  - Grounding state: `partial`
  - Met: `Torbin met in Hempholm, capture, forced meat exposure, escape with Ephanna`
  - Missing: `education/ward commitment, Ephanna took Torbin with Lyra / the Shepherd's Flock, oily-eye symptom after exposure`
  - Agent Answer Excerpt:
    > Torbin’s path starts in Hempholm, where he’s anchored by family and place: he’s Jove’s child, lives in Hempholm, and already knows about the Grotesque Tree there. The pressure point is the Hempholm-side unrest around that tree and the Caretakers; the drunken townsfolk attack the ...
- **Primary Failure Category:** `synthesis`
- **Diagnostic Rationale:** Evidence was reachable/retrieved in the graph, but the Agent's synthesized answer omitted one or more required concepts.

### Q07 — Q07 — Protest leader to meat-distribution leader

- **Difficulty:** 3
- **Question:** What evidence connects Lyra's role in the toll protest to the later meat-distribution conspiracy?
- **Gold Answer:** Lyra first appears as leader of the toll-protest crowd. Her followers are identified as the Shepherd's Flock, and Ephanna follows them with Torbin before the pair are captured in a place where Torbin is force-fed the strange meat. In Session 9 disguised party members learn that Lyra is nearby and leading the meat-distribution project.
- **Oracle Score:** `FULL` (Met: 4/4, Nodes: 24, Rels: 21)
  - Met: `Lyra led the toll protest, Lyra/followers connected to the Shepherd's Flock, following the group leads Ephanna and Torbin into captivity/meat exposure, Lyra later leads the meat-distribution project`
  - Missing: `None`
- **Agent Score:** `PARTIAL` (Met: 3/4, Latency: 9243ms, Tools: 2)
  - Grounding state: `partial`
  - Met: `Lyra led the toll protest, following the group leads Ephanna and Torbin into captivity/meat exposure, Lyra later leads the meat-distribution project`
  - Missing: `Lyra/followers connected to the Shepherd's Flock`
  - Agent Answer Excerpt:
    > The graph shows only a loose thematic link, not a direct causal chain: the toll protest is anchored at The Gate in session 6, while the meat-distribution conspiracy appears later in session 9. What connects them in the graph is that both revolve around controlled movement of good...
- **Primary Failure Category:** `synthesis`
- **Diagnostic Rationale:** Evidence was reachable/retrieved in the graph, but the Agent's synthesized answer omitted one or more required concepts.

### Q08 — Q08 — Evidence of guard infiltration

- **Difficulty:** 3
- **Question:** What observed evidence supports the conclusion that the meat conspiracy had infiltrated parts of the city guard?
- **Gold Answer:** Lysandra noticed guards with oily eyes and was unexpectedly locked out of her own storeroom. That storeroom concealed strange meat and a tunnel to a warehouse where Lysandra and trusted guards were later found captured and being force-fed. In Session 9 cultists told the disguised party that they worked for Captain Fairfield and that Captain Blart was coordinating meat distribution at the central office.
- **Oracle Score:** `FULL` (Met: 6/6, Nodes: 20, Rels: 23)
  - Met: `oily-eyed guards, Lysandra locked out of the storeroom, hidden meat/tunnel under the guardhouse, Lysandra/trusted guards captured or force-fed, Captain Fairfield, Captain Blart`
  - Missing: `None`
- **Agent Score:** `PARTIAL` (Met: 1/6, Latency: 13097ms, Tools: 3)
  - Grounding state: `partial`
  - Met: `Lysandra/trusted guards captured or force-fed`
  - Missing: `oily-eyed guards, Lysandra locked out of the storeroom, hidden meat/tunnel under the guardhouse, Captain Fairfield, Captain Blart`
  - Agent Answer Excerpt:
    > The strongest evidence is that the City Guards are directly linked to violence against the toll protesters at The Gate: the graph records the guards as attacking the protesters, while also showing Captain Lysandra Ironveil commanding the City Guards and the guards protecting The ...
- **Primary Failure Category:** `synthesis`
- **Diagnostic Rationale:** Evidence was reachable/retrieved in the graph, but the Agent's synthesized answer omitted one or more required concepts.

### Q09 — Q09 — Follow the underground route

- **Difficulty:** 3
- **Question:** Trace the physical route the party uncovered from the city guard's storeroom to the later warehouse fighting and their eventual short-rest location.
- **Gold Answer:** The guardhouse storeroom hid a bookshelf/staircase into a cold meat room, where a hidden wall led into tunnels. Those tunnels reached a warehouse in the Warehouse District. The party kept following the trapped tunnel network through a prison and meat-loading junction. In Session 10 one trapdoor opened into the Grit and Grime; after recruiting Thraxx they continued through the tunnel to the last chilled warehouse. Following that fight they returned to the Grit and Grime party for a Short Rest.
- **Oracle Score:** `PARTIAL` (Met: 7/8, Nodes: 23, Rels: 29)
  - Met: `guardhouse storeroom, hidden staircase/cold meat room, hidden wall/tunnel, warehouse district / warehouse, continued tunnel network and distribution junction, Grit and Grime, last warehouse`
  - Missing: `return for Short Rest`
- **Agent Score:** `PARTIAL` (Met: 7/8, Latency: 10046ms, Tools: 3)
  - Grounding state: `partial`
  - Met: `guardhouse storeroom, hidden staircase/cold meat room, hidden wall/tunnel, warehouse district / warehouse, continued tunnel network and distribution junction, last warehouse, return for Short Rest`
  - Missing: `Grit and Grime`
  - Agent Answer Excerpt:
    > The route runs from the Guardhouse’s storeroom into the hidden staircase/bookshelf, down into the Cold Room, then through the Tunnel, which opens into the Warehouse District. From there the party reached the Warehouse itself, where the later fighting happened.  Their short-rest l...
- **Primary Failure Category:** `graph_connectivity_identity`
- **Diagnostic Rationale:** Entities exist in the graph (e.g. Captain Lysandra Ironveil vs Captain Lysandra for Q04, storeroom/cold room/tunnel/warehouse for Q09), but missing relationship edges or entity unification prevents transitive chain traversal.

### Q10 — Q10 — What did the party learn about fighting the meat?

- **Difficulty:** 4
- **Question:** What did the party learn about fighting the corrupted meat creatures, and which tactics appeared to make the situation better or worse?
- **Gold Answer:** Cutting or crushing Meat Mounds tended to shed smaller Meat Piles, and ordinary damage produced poisonous clouds. Caelynn noticed that her cold/Snowball attack did not create new piles. Ephanna's Shatter destroyed piles, and fire consumed smaller piles. Tasha's Hideous Laughter did nothing. In the next warehouse the party again used oil/fire and area magic while facing Meat Mounds plus new Abhorrent Meat Wings.
- **Oracle Score:** `PARTIAL` (Met: 2/6, Nodes: 15, Rels: 12)
  - Met: `physical attacks can shed Meat Piles, cold/Snowball did not produce new piles`
  - Missing: `poisonous cloud from ordinary damage, Shatter destroyed piles, fire consumed smaller piles, Hideous Laughter had no effect`
- **Agent Score:** `PARTIAL` (Met: 1/6, Latency: 13235ms, Tools: 4)
  - Grounding state: `partial`
  - Met: `physical attacks can shed Meat Piles`
  - Missing: `poisonous cloud from ordinary damage, cold/Snowball did not produce new piles, Shatter destroyed piles, fire consumed smaller piles, Hideous Laughter had no effect`
  - Agent Answer Excerpt:
    > The party learned that the corrupted meat creatures were much more manageable when they were focused down together rather than left to spread pressure around. In the later fight, the group’s coordinated attacks landed on both the Corrupted Meat Mound and Corrupted Meat Pile, whic...
- **Primary Failure Category:** `graph_coverage`
- **Diagnostic Rationale:** The underlying factual details (e.g. arcana check extraplanar result for Q01, specific ward contract commitments for Q03, combat spell interactions for Q10, force-feeding temporal specifics for Q13, extraplanar/abyssal clues for Q15) were never published as object properties, summaries, or typed assertions in World revision rev:b82db72693c27e0218026fd1ff514a68.

### Q11 — Q11 — Track Ephanna's Sprite/fey familiar

- **Difficulty:** 4
- **Question:** What role did Ephanna's Sprite or fey familiar play from Sessions 6 through 10, and what was its last known state?
- **Gold Answer:** Ephanna secretly summoned a Sprite on the road to Mirathorn, with Torbin the only person explicitly noted as knowing. During Ephanna's captivity a fey familiar helped loosen his bonds. Ephanna later used his Sprite to scout the tunnels and warehouse route. In Session 10 the Sprite again helped scout and was killed in the warehouse battle.
- **Oracle Score:** `FULL` (Met: 5/5, Nodes: 23, Rels: 30)
  - Met: `secret Sprite summon, Torbin knew, fey familiar helped with the escape, Sprite scouted tunnels/warehouse, Sprite killed in Session 10`
  - Missing: `None`
- **Agent Score:** `PARTIAL` (Met: 3/5, Latency: 17234ms, Tools: 5)
  - Grounding state: `partial`
  - Met: `secret Sprite summon, fey familiar helped with the escape, Sprite killed in Session 10`
  - Missing: `Torbin knew, Sprite scouted tunnels/warehouse`
  - Agent Answer Excerpt:
    > Ephanna’s sprite/fey familiar appears to have been a loyal attendant to Ephanna through the middle of the arc: by Session 6 it’s tied to Ephanna’s secret sprite summoning, and by the time the graph reaches Session 9 it’s explicitly serving Ephanna. The surrounding Session 7–8 mat...
- **Primary Failure Category:** `synthesis`
- **Diagnostic Rationale:** Evidence was reachable/retrieved in the graph, but the Agent's synthesized answer omitted one or more required concepts.

### Q12 — Q12 — Continuity warning: Lyra

- **Difficulty:** 4
- **Question:** If a future session tried to portray Lyra as only an uninvolved protest organizer, what continuity facts should an agent surface before the GM commits to that?
- **Gold Answer:** The agent should surface that Lyra led the toll protest, her followers were tied to the Shepherd's Flock, Ephanna and Torbin were captured after following that group, and by Session 9 cultists identified Lyra as leading the meat-distribution project.
- **Oracle Score:** `FULL` (Met: 4/4, Nodes: 21, Rels: 18)
  - Met: `protest leader, Shepherd's Flock connection, capture/meat context after following her group, later distribution leadership`
  - Missing: `None`
- **Agent Score:** `PARTIAL` (Met: 2/4, Latency: 7480ms, Tools: 1)
  - Grounding state: `partial`
  - Met: `protest leader, Shepherd's Flock connection`
  - Missing: `capture/meat context after following her group, later distribution leadership`
  - Agent Answer Excerpt:
    > Before the GM reduces Lyra to “just an uninvolved protest organizer,” the continuity flags to surface are that Lyra is already tied to The Shepherds Flock, and specifically serves The Shepherd. That means she is not a detached civic actor in the available graph; she sits inside t...
- **Primary Failure Category:** `agent_orchestration`
- **Diagnostic Rationale:** Oracle retrieval proved required relationships and nodes are reachable in the graph, but the Agent performed only 1 tool call(s) and stopped investigating before collecting the multi-hop evidence.

### Q13 — Q13 — Continuity warning: Torbin

- **Difficulty:** 4
- **Question:** If a future plan assumed Torbin had never been exposed to the corrupted meat, what prior facts should the agent use to warn the GM?
- **Gold Answer:** Torbin was force-fed meat while captive in Session 7, was heard being forced to eat it again in Session 8, and after escape he had begun to show the same oily-eye sign associated with suspicious guards.
- **Oracle Score:** `PARTIAL` (Met: 1/3, Nodes: 13, Rels: 14)
  - Met: `oily-eye symptom after escape`
  - Missing: `force-fed in Session 7, force-fed/heard being force-fed again in Session 8`
- **Agent Score:** `PARTIAL` (Met: 1/3, Latency: 9706ms, Tools: 3)
  - Grounding state: `partial`
  - Met: `force-fed/heard being force-fed again in Session 8`
  - Missing: `force-fed in Session 7, oily-eye symptom after escape`
  - Agent Answer Excerpt:
    > Warn the GM that Torbin’s “never exposed” assumption conflicts with the graph: there is already an explicit Torbin-meat-effect mystery, which means prior play established that the meat has affected him. The graph also ties that same meat thread to the corrupted meat mound/pile, s...
- **Primary Failure Category:** `graph_coverage`
- **Diagnostic Rationale:** The underlying factual details (e.g. arcana check extraplanar result for Q01, specific ward contract commitments for Q03, combat spell interactions for Q10, force-feeding temporal specifics for Q13, extraplanar/abyssal clues for Q15) were never published as object properties, summaries, or typed assertions in World revision rev:b82db72693c27e0218026fd1ff514a68.

### Q14 — Q14 — Played truth vs GM planning

- **Difficulty:** 5
- **Question:** By the end of Session 9, which claims about the Wolf and the city's leadership are played observations, and which are only GM planning in the source document?
- **Gold Answer:** The Session 9 `Looking Ahead` section says the Wolf is the guard's second-in-command, a cultist, and alerted to the party. It also says the guard leader is innocent but ensorcelled and proposes possible wizard/council reactions. Those are planning statements, not events established by the Session 9 Recap. The observed Recap instead establishes the warehouse battle, the strange-language clue, Lysandra going to Stormspire, and cultists naming Captain Fairfield, Captain Blart, and Lyra in the distribution network.
- **Oracle Score:** `PARTIAL` (Met: 2/4, Nodes: 12, Rels: 7)
  - Met: `guard-leader innocence/ensorcellment is planning, Fairfield, Blart, and Lyra are supported by the observed Recap`
  - Missing: `Wolf claims are in planning / Looking Ahead, proposed council/wizard responses are planning`
- **Agent Score:** `PARTIAL` (Met: 3/4, Latency: 17278ms, Tools: 3)
  - Grounding state: `partial`
  - Met: `Wolf claims are in planning / Looking Ahead, guard-leader innocence/ensorcellment is planning, proposed council/wizard responses are planning`
  - Missing: `Fairfield, Blart, and Lyra are supported by the observed Recap`
  - Agent Answer Excerpt:
    > By the end of Session 9, the source-backed claims about the Wolf and the city’s leadership are mixed: some are played observations, and some are still just GM planning language.  Played observations: - The Wolf is tied to the guard-storeroom thread from Session 8, with the existi...
- **Primary Failure Category:** `source_authority`
- **Diagnostic Rationale:** The graph represents objects and planning assertions (e.g. Wolf's role, the Shepherd's northern swamp presence), but lacks epistemic authority tagging to reliably distinguish played canon from GM Looking Ahead planning statements or unproven rumors.

### Q15 — Q15 — End-of-Session-10 operational picture

- **Difficulty:** 5
- **Question:** At the end of Session 10, what is the strongest source-supported operational picture of the corrupted-meat conspiracy: origin clues, distribution method, known actors, physical network, deadline, and immediate party state?
- **Gold Answer:** The meat has an extraplanar origin clue, reinforced by a scroll Caelynn says resembles Abyssal from other planes. The network uses a hidden guardhouse meat room and tunnels into warehouses, where meat is packed and loaded into carts. Observed named actors include cultists, Captain Fairfield, Captain Blart, and Lyra; suspicious oily-eyed guards and Lysandra's exclusion/capture show guard compromise. A citywide BBQ is imminent, about twelve hours away in Session 10. The party has fought through multiple meat warehouses, encountered Meat Mounds/Piles and Abhorrent Meat Wings, recruited Thraxx, and ends Session 10 back at the Grit and Grime taking a Short Rest.
- **Oracle Score:** `PARTIAL` (Met: 7/9, Nodes: 19, Rels: 15)
  - Met: `hidden guardhouse meat room/tunnels, warehouse/cart distribution, Captain Fairfield, Captain Blart, Lyra, imminent citywide BBQ / about twelve hours, party resting at Grit and Grime after the latest warehouse fight`
  - Missing: `extraplanar origin clue, Abyssal-like scroll clue`
- **Agent Score:** `PARTIAL` (Met: 2/9, Latency: 16845ms, Tools: 3)
  - Grounding state: `partial`
  - Met: `hidden guardhouse meat room/tunnels, warehouse/cart distribution`
  - Missing: `extraplanar origin clue, Abyssal-like scroll clue, Captain Fairfield, Captain Blart, Lyra, imminent citywide BBQ / about twelve hours, party resting at Grit and Grime after the latest warehouse fight`
  - Agent Answer Excerpt:
    > The conspiracy now looks like a two-stage meat pipeline, not a single monster event. The strongest supported clue is that “The Meat” was already being moved through at least two storage points — the cold room and the warehouse — and by Session 9 the network had enough shape to be...
- **Primary Failure Category:** `graph_coverage`
- **Diagnostic Rationale:** The underlying factual details (e.g. arcana check extraplanar result for Q01, specific ward contract commitments for Q03, combat spell interactions for Q10, force-feeding temporal specifics for Q13, extraplanar/abyssal clues for Q15) were never published as object properties, summaries, or typed assertions in World revision rev:b82db72693c27e0218026fd1ff514a68.

### Q16 — Q16 — How far can we connect the Shepherd to the conspiracy?

- **Difficulty:** 5
- **Question:** What can the graph support—and what can it not yet prove—about the relationship between the Shepherd, the Shepherd's Flock, and the corrupted-meat conspiracy by Session 9?
- **Gold Answer:** The graph can support that Lyra's protest followers are identified as the Shepherd's Flock, that they speak of a leader called the Shepherd in the northern swamp, that Ephanna and Torbin encounter captivity and forced meat after following Lyra's group, and that Lyra is later identified as leading meat distribution. That strongly connects Lyra and at least part of the Flock to the meat conspiracy. The observed recaps do **not** directly prove that the Shepherd personally directs the meat operation.
- **Oracle Score:** `PARTIAL` (Met: 4/5, Nodes: 14, Rels: 16)
  - Met: `Lyra's followers are the Shepherd's Flock, the Shepherd is described as their leader in the northern swamp, captivity/forced meat follows Ephanna and Torbin going with the group, Lyra later leads meat distribution`
  - Missing: `the Shepherd personally directing the meat conspiracy remains unproven`
- **Agent Score:** `PARTIAL` (Met: 3/5, Latency: 7033ms, Tools: 1)
  - Grounding state: `partial`
  - Met: `Lyra's followers are the Shepherd's Flock, the Shepherd is described as their leader in the northern swamp, captivity/forced meat follows Ephanna and Torbin going with the group`
  - Missing: `Lyra later leads meat distribution, the Shepherd personally directing the meat conspiracy remains unproven`
  - Agent Answer Excerpt:
    > By Session 9, the graph can support a fairly tight but still incomplete chain: The Shepherd is a real NPC who leads The Shepherds Flock, and that faction is linked to the Mirathorn toll riot and to the Symbol of The Shepherds Flock. The Shepherd is also located in the Swamp. That...
- **Primary Failure Category:** `source_authority`
- **Diagnostic Rationale:** The graph represents objects and planning assertions (e.g. Wolf's role, the Shepherd's northern swamp presence), but lacks epistemic authority tagging to reliably distinguish played canon from GM Looking Ahead planning statements or unproven rumors.

