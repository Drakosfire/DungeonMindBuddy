# Stage 4L Campaign 1 Sessions 1–10: Relationship Rejection Investigation

**Created:** 2026-09-14  
**PR:** #714 — `DOGFOOD-CONTINUITY: build Campaign 1 memory through Session 10`  
**Exact Starting Head:** `236ecb3ee050fb981c1710b2c813e20de8252853`  
**Authoritative Rehearsal World Revision:** `rev:c839ca5587f06dda2eb485dad1e50fe6`  
**Model Calls:** `0` (100% zero-model evidence analysis)  
**Cohort:** Campaign 1, Sessions 1–10  
**Denominator:** 276 extracted relationship denominator  

---

## 1. Executive Result

Of the 126 extracted relationships currently excluded from the Session 10 rehearsal World Graph, **the overwhelming majority (117 / 126, or 92.9%) are legitimate, source-supported campaign facts**, while only **9 / 126 (7.1%)** represent invalid, malformed, or erroneous extractions that are correctly rejected. Crucially, **the single largest bottleneck is an Identity Resolution cross-kind alias collision (62 relationships, 49.2% of all rejects)**: in Sessions 2 through 10, candidate Player Characters (`kind='pc'`) suffered a fatal collision against existing genesis World Player Characters (`kind='dnd5e:player_character'`), causing the identity gate to classify all PCs as `outcome='blocked_collision'` and silently discard every edge connected to them. The second largest bottleneck is **weak/missing endpoint typing (33 relationships, 26.2%)**, where concrete physical entities (towers, entrances, celebration events, rats) were typed as abstract `mystery` nodes, unmapped `organization` kinds, or beast companions typed as generic `npc`. Overly restrictive ontology endpoint-kind contracts account for **13 relationships (10.3%)**, and unmapped predicate vocabulary accounts for **9 relationships (7.1%)**. Finally, **9 of the current 150 published relationships rely on semantically lossy coercions** (`governs` → `owns`, `refers_to` → `associated_with`), leaving the truthful published baseline at **141 relationships (51.1%)**. Because all PC relationships in Sessions 2–10 are missing and key identities are fractured, the graph is **NOT** ready for the 16-question benchmark. The single recommended successor is **Identity and Type Repair** to fix the PC kind collision and reconcile duplicate identities before benchmarking.

---

## 2. Analytical Funnel

The previous funnel conflated syntactic presence with semantic validity (`canonical_endpoints: 276`). The corrected analytical funnel decomposes each pipeline stage:

```text
extracted:                              276 (100.0%)
  ↓
endpoint_ids_present:                   276 (100.0%)  [from_node_id and to_node_id populated]
  ↓
endpoints_resolve_to_world_objects:     197 ( 71.4%)  [79 PC edges dropped in S2-S10 at identity gate]
  ↓
endpoint_identity_quality:              182 ( 65.9%)  [excludes split Lysandra nodes, duplicate entities]
  ↓
predicate_semantically_mapped:          249 ( 90.2%)  [excludes 16 unmapped + 11 lossy mapped predicates]
  ↓
endpoint_kinds_known:                   272 ( 98.6%)  [excludes 4 unmapped 'organization' endpoints]
  ↓
predicate_accepts_endpoint_kinds:       219 ( 79.3%)  [150 published + 69 expressible PC edges]
  ↓
truthfully_publishable:                 252 ( 91.3%)  [achievable upper bound of truthful campaign facts]
  ↓
published (current rechain):            150 ( 54.3%)  [141 faithful + 9 lossy coercions]
```

---

## 3. Rejection Decomposition

Every one of the 126 unpublished relationships was classified into one primary diagnostic category:

| Category Code | Primary Category | Description | Count | Share (%) |
| :--- | :--- | :--- | :---: | :---: |
| **B** | `endpoint_identity_unresolved_or_wrong` | PC kind collision (`pc` vs `player_character`) at identity gate | 62 | 49.2% |
| **C** | `endpoint_kind_missing_or_weak` | Endpoint typed as `mystery`, unmapped `organization`, or wrong animal kind | 33 | 26.2% |
| **D** | `ontology_endpoint_contract_too_narrow` | Correctly typed endpoints rejected by narrow predicate matrix | 13 | 10.3% |
| **F** | `extraction_semantically_bad` | Erroneous extraction, inverted meaning, or duplicate node reconciliation as edge | 9 | 7.1% |
| **A** | `predicate_unmapped` | Meaningful campaign relation with no DungeonMind predicate mapping | 9 | 7.1% |
| **E** | `predicate_mapping_lossy` | Lossy coercion (all 9 were admitted/published into rechain; audited below) | 0* | 0.0% |
| **Total** | | | **126** | **100.0%** |

*Note: All 9 relationships using lossy predicate mappings passed current rules and were published in the rechain revision.*

---

## 4. Most Common Rejection Signatures

The 25 most frequent rejection signatures (Reason × Predicate × Subject Kind × Object Kind) across the 126 rejected relationships:

| Reason | Predicate | Subject Kind | Object Kind | Count |
| :--- | :--- | :--- | :--- | :---: |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `possesses` | `player_character` | `item` | 8 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `attacks` | `player_character` | `npc` | 8 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `carries` | `player_character` | `item` | 6 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `present_at` | `player_character` | `location` | 4 |
| `duplicate_node_reconciliation_as_edge:same_as` | `same_as` | `item` | `mystery` | 4 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `attacks` | `player_character` | `player_character` | 3 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `works_with` | `player_character` | `npc` | 3 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `attacks` | `npc` | `player_character` | 3 |
| `works_with_rejects_location_endpoint` | `works_with` | `npc` | `location` | 3 |
| `weak_mystery_typing_replaces_concrete_entity` | `causes` | `player_character` | `mystery` | 3 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `cooperates_with` | `player_character` | `player_character` | 3 |
| `unmapped_organization_kind_needs_faction_or_group` | `member_of` | `npc` | `organization` | 3 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `owns` | `player_character` | `item` | 2 |
| `presence_in_or_on_item_unsupported` | `present_at` | `player_character` | `item` | 2 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `attacks` | `creature` | `player_character` | 2 |
| `weak_mystery_typing_replaces_concrete_entity` | `part_of` | `creature` | `mystery` | 2 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `knows_about` | `player_character` | `npc` | 2 |
| `pc_cross_kind_collision_blocked_by_identity_gate` | `causes` | `player_character` | `player_character` | 2 |
| `weak_mystery_typing_replaces_concrete_entity` | `knows_about` | `player_character` | `mystery` | 2 |
| `duplicate_node_reconciliation_as_edge:identified_as` | `identified_as` | `item` | `mystery` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `attacks` | `mystery` | `group` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `participates_in` | `mystery` | `mystery` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `present_at` | `item` | `mystery` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `part_of` | `location` | `mystery` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `located_in` | `item` | `mystery` | 1 |

---

## 5. Endpoint Identity Findings

### 5.1 The Player Character Identity Gate Wipeout (62 Rejects)
In Session 1, `node:baergrom`, `node:bonogo`, `node:caelynn`, `node:ephanna`, `node:karsemine`, and `node:stafl` did not exist in the genesis revision (`rev:d5c5...`). They were created cleanly and admitted with kind `dnd5e:player_character`.

However, in Sessions 2 through 10, whenever a candidate graph mentioned a PC, the candidate node carried `kind='pc'`. The mutation context resolution method `resolve_identity_against_context` evaluated:
```python
if policy.exact_label_match_kinds and _norm(obj.kind) == candidate_kind:
    same_kind[object_id] = obj
elif policy.block_cross_kind_alias_collision and _norm(obj.kind) != candidate_kind:
    cross_kind[object_id] = obj
```
Because `_norm('dnd5e:player_character')` (`'player_character'`) does not equal `'pc'`, the resolver classified every PC match as a **cross-kind alias collision** (`outcome='blocked_collision'`).

When a node suffers `blocked_collision`, `gate_candidate_graph_against_head` diverts it to `unresolved_mentions` and omits it from `node_id_map`. Consequently, lines 485–487:
```python
if from_id not in mapped or to_id not in mapped:
    continue
```
**silently dropped all 79 candidate edges connected to any PC across Sessions 2–10.**
Of those 79 dropped edges, **62 are fully valid, expressible propositions** that were lost entirely due to this single string aliasing defect.

### 5.2 The Captain Lysandra Split
A concrete recurring NPC identity collision exists between Sessions 6 and 8:
- **Session 6**: `node:lysandra-ironveil` (`label='Captain Lysandra Ironveil'`, kind=`character` → `npc`).
- **Session 8**: `npc:captain-lysandra` (`label='Captain Lysandra'`, kind=`character` → `npc`).
- In Session 10 World head (`rev:c839...`), both nodes exist simultaneously as distinct objects.
- Edges published in S6 link to `node:lysandra-ironveil`; edges published in S8 link to `npc:captain-lysandra`.
- The graph treats them as two unrelated officers in the same city guard, fracturing campaign continuity.

---

## 6. Endpoint Typing Findings (`mystery` and Weak Types)

Weak typing directly caused the rejection of **33 relationships (26.2%)**:

1. **Concrete Entities Typed as `mystery` (26 edges)**:
   - *Locations*:
     - `node:mystery:shattered-mages-tower` (S01): Tiled hallway part of tower; broken tools in tower.
     - `mystery:underground-root-layer-tunnel` (S05): Tunnel mouth beneath Hempholm.
     - `mystery:second-underground-entrance` (S09): Second entrance leads to underground tunnels.
   - *Creatures / Encounters*:
     - `node:mystery:giant-rats-excavation` (S01): Giant rats attacked excavation crew; health potions used during rat fight.
     - `node:mystery:cat-owl` (S01): Cat-owl tossed into rat fight.
     - `mystery:caretaker-attack` (S04): Caretakers burrowing from below.
   - *Events*:
     - `mystery:hempholm-post-tree-party` (S04): Townsfolk celebration after tree's death.
     - `mystery:mirathorn-toll-protest` (S06): Protest over toll at Mirathorn gate.
   Because these concrete entities were labeled `mystery`, predicates like `located_in`, `part_of`, `attacks`, and `participates_in` rejected them.

2. **Unmapped `organization` Kind (4 edges)**:
   - S08: `The Orc Bartender` -[member_of]-> `Copper and Quartz Staff` (organization)
   - S09: `Barin` -[member_of]-> `The City Council` (organization)
   - S09: `Grobnok` -[member_of]-> `The City Council` (organization)
   - S09: `The Wizard's College` (organization) -[commands]-> `The City Council` (organization)
   Buddy's extractor emitted `kind='organization'`, but `_BUDDY_TO_DM_KIND` only defines `faction` and `group`. Because `organization` is unmapped, qualification failed with `endpoint_kind_unmapped`. Mapping `organization` to `dnd5e:faction` recovers all 4 edges immediately.

3. **Animal / Mount Companion Typed as NPC (3 edges)**:
   - S03: `Bubbles the Float Goat` was extracted as `type='character'`, which defaulted to `kind='npc'`.
   - `Pippa owns Bubbles`: Rejected because `dnd5e:owns` allows `npc` → `creature/item/location`, but NOT `npc` → `npc`.
   - `Lasso and Rope holds Bubbles`: Rejected because `dnd5e:holds` does not allow `item` → `npc`.
   - `Bubbles carries Ephanna`: Rejected because mount carrying rider is not permitted when mount is typed as `npc`.
   Typing beasts and animal companions as `creature` resolves all 3 edges.

---

## 7. Predicate Vocabulary Findings

Only **9 relationships (7.1%)** are blocked by unmapped predicates representing meaningful campaign facts:
- `mission_targets` (3 edges):
  - `Potential Journey to Mirathorn Festival` (thread) → `Mirathorn` (location)
  - `Mysterious Artifact Hook` (mystery) → `Mysterious Artifact` (item)
  - `Berin's favor` (mystery) → `The Shepherds Flock` (mystery)
- `mission_focus` (3 edges):
  - `Aftermath and Rebuilding Stone Bridge` (thread) → `Stone Bridge Flow Ways` (location)
  - `Berin's favor` (mystery) → `Mirathorn Gates` (location)
  - `Captain Blart` (npc) → `Cultist Meat Distribution` (mystery)
- `controls_comms_with` (2 edges):
  - `Stafl` (pc) → `Drunken townsfolk of Hempholm` (npc) [social negotiation]
  - `Caelynn` (pc) → `Noxious Mixture` (item) [freezing / controlling hazard]
- `reports_threat_in` (1 edge):
  - `Ephanna captured` (mystery) → `Ephanna` (pc)

These relations reflect campaign intent, quest targets, and narrative focus. They do not have exact synonyms in DungeonMind's spatial/combat ontology and represent candidate vocabulary for a dedicated quest/planning module.

---

## 8. Ontology Contract Findings (13 Rejects)

Thirteen relationships represent valid, accurately typed campaign facts that were rejected purely because DungeonMind's endpoint-kind matrix is too restrictive:

1. **`works_with` rejecting `location` endpoints (3 edges)**:
   - S06: `Morwin` (npc) -[works_with]-> `Morwin's` (location)
   - S07: `Elara Greenleaf` (npc) -[works_with]-> `herbal shop` (location)
   - S07: `Talia` (npc) -[works_with]-> `herbal shop` (location)
   *Finding*: NPCs operating, clerking, or running local shops. `dnd5e:works_with` only allows `npc/pc` → `npc/pc`. DungeonMind lacks a `works_at` or `staffs` relation.

2. **`carries` rejecting `item` carrying `item` (1 edge)**:
   - S03: `Dinghy` (item) -[carries]-> `Net with Light Cast On It` (item)
   *Finding*: Physical vehicles or containers transporting equipment. `dnd5e:carries` currently requires the subject to be a creature/character.

3. **`leads_to` rejecting `item` portals / doors (1 edge)**:
   - S08: `Ladder and Trap Door` (item) -[leads_to]-> `Warehouse` (location)
   *Finding*: Physical passage fixtures leading into rooms. `dnd5e:leads_to` currently only connects `location` → `location`.

4. **`present_at` rejecting presence on transport `item` (2 edges)**:
   - S03: `Caelynn` (pc) -[present_at]-> `Dinghy` (item)
   - S03: `Stafl` (pc) -[present_at]-> `Dinghy` (item)
   *Finding*: Characters aboard a boat or vehicle.

5. **`attends` / `participates_in` rejecting social gatherings / clubs (3 edges)**:
   - S03: `Stafl` (pc) -[attends]-> `Stone Bridge Townsfolk` (group)
   - S07: `Ephanna` (pc) -[participates_in]-> `The Shepherds Flock` (faction)
   - S10: `Stafl` (pc) -[attends]-> `Grit and Grime Club` (faction)
   *Finding*: Characters participating in community meetings, factions, or social clubs.

6. **`located_in` rejecting `event` (1 edge)**:
   - S05: `Defeat of the Guardian` (event) -[located_in]-> `heart of the tree` (location)
   *Finding*: Events occurring at a place require `dnd5e:occurs_at`, but the extractor chose `located_in`.

7. **`located_in` / `present_at` creature in/on hazard item (2 edges)**:
   - S09: `Disgusting Pile of Offal` (creature) -[located_in]-> `Meat Rack` (item)
   - S09: `Corrupted Meat Pile` (creature) -[present_at]-> `Meat Rack` (item)

---

## 9. Semantic Coercion Audit

Nine currently published relationships rely on predicate mappings introduced during the previous zero-model repair. Each was audited individually against source evidence:

| Candidate Edge ID | Raw Predicate | Mapped DM Predicate | Endpoints | Classification | Source Evidence Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `edge:node:grishna:governs:node:the_rivers_edge_pub` | `governs` | `dnd5e:owns` | Grishna → River's Edge Pub | **Lossy Coercion** | Grishna *manages/runs* the pub; ownership is unstated and legally distinct. |
| `edge:npc:wolf:governs:location:storeroom` | `governs` | `dnd5e:owns` | Wolf → Storeroom | **Lossy Coercion** | Wolf is a cultist/captain occupying the storeroom; he does not *own* it. |
| `edge:node:big_rock:west_of:node:stone_bridge` | `west_of` | `dnd5e:near` | Big Rock → Stone Bridge | **Safe Generalization** | Big Rock is indeed near Stone Bridge; spatial direction is weakened but true. |
| `edge:creature:the_guardian:defends_weakened_location:location:heart_of_the_tree` | `defends_weakened_location` | `dnd5e:protects` | The Guardian → Heart of the Tree | **Safe Equivalent** | Defending a location is semantically faithful to protecting it. |
| `edge:node:city-guards:defends_weakened_location:location:the-gate` | `defends_weakened_location` | `dnd5e:protects` | City Guards → The Gate | **Safe Equivalent** | Guarding a gate is semantically faithful to protecting it. |
| `edge:node:grishna:refers_to:node:glowkindle` | `refers_to` | `dnd5e:associated_with` | Grishna → Glowkindle | **Lossy Coercion** | Conversational referral ("Grishna told party about brewer") degraded to vague link. |
| `edge:node:grishna:refers_to:node:wizards_tower_brewing_co` | `refers_to` | `dnd5e:associated_with` | Grishna → Brewery | **Lossy Coercion** | Directions given by tavernkeeper degraded to vague association. |
| `edge:node:pippa:refers_to:location:mirathorn` | `refers_to` | `dnd5e:associated_with` | Pippa → Mirathorn | **Lossy Coercion** | Mentioning a city destination during casual conversation degraded to link. |
| `edge:mystery:road-to-mirathorn:refers_to:route:road_to_mirathorn` | `refers_to` | `dnd5e:associated_with` | Road Mystery → Road Route | **Lossy Coercion** | Epistemic thread discussing the route degraded to generic association. |

**Summary**: 3 of the 9 mappings are safe generalizations. 6 are lossy coercions that dilute specific conversational and operational statements into generic graph edges.

---

## 10. Correct Rejection Findings (9 Rejects)

Nine rejected relationships represent defective or malformed extractions that **should not** enter durable campaign memory:

1. **Entity Deduplication Asserted as Edges (6 edges)**:
   - `same_as` (5 edges):
     - S04: `Grotesque Tree` (mystery) -[same_as]-> `Grotesque Tree` (creature)
     - S04: `Grotesque Tree` (item) -[same_as]-> `Grotesque Tree` (mystery)
     - S05: `Ordinary Potato` (item) -[same_as]-> `Ordinary potato from root heart` (mystery)
     - S05: `Precious Metal Tree Sap` (item) -[same_as]-> `Precious metal tree sap` (mystery)
     - S08: `The Meat` (item) -[same_as]-> `Sinister meat` (mystery)
   - `identified_as` (1 edge):
     - S01: `Enormous Boulder` (item) -[identified_as]-> `Stone foot landmark` (mystery)
   *Diagnosis*: The extractor minted duplicate nodes for the same entity and emitted an edge to reconcile them. Entity resolution must merge nodes, not create synthetic edges.

2. **Erroneous Extraction Contradicting Source (3 edges)**:
   - S03 `edge:karsemine_attacks_bonogo`: Source text explicitly describes Karsemine running down the riverbank shooting arrows to *save* Bonogo from drowning. Extractor misclassified rescue action as attack against ally.
   - S03 `edge:ephanna_attacks_bubbles`: Source text explicitly describes Ephanna using mage hand with a lasso to *rescue* Bubbles the Float Goat from drowning. Extractor misclassified rescue action as attack.
   - S07 `edge:the-captain-commands-mirathorn-gates`: Source text describes the captain commanding the *guards at the gate*. Extractor attached the command relation to the inanimate gate.

---

## 11. Sampled Edge Case Studies (The 6 Mandatory Inquiries)

Below is an audit of representative edges across all critical failure categories, answering the six required questions:

### Case Study 1: PC Action Blocked by Identity Gate
- **Edge ID**: `edge:stafl-carries-net` (Session 3)
- **Proposition**: `Stafl` (pc) -[`carries`]-> `Elderly Fisherman's Net` (item)
- **Anchor Quote**: *"Stafl and Baergrom pulled the net to surface"*
- **Answers**:
  1. *Source-supported?* **Yes.** Stafl actively hauled and held the net during the river rescue.
  2. *Correct endpoint identities?* **Yes.** `node:stafl` and `item:elderly_fishermans_net`.
  3. *Correct endpoint kinds?* **Yes.** Player character and item.
  4. *Predicate semantically correct?* **Yes.** `carries` (`dnd5e:carries`).
  5. *Would publication preserve source meaning?* **Yes.**
  6. *Owning layer?* **Identity Resolution.** Blocked exclusively because Stafl had `kind='pc'` colliding with `player_character` in mutation context.

### Case Study 2: Weak Mystery Typing on Concrete Location
- **Edge ID**: `edge:tiled-hallway-part-of-shattered-tower` (Session 1)
- **Proposition**: `Tiled Hallway` (location) -[`part_of`]-> `Shattered mages tower beneath brewery` (mystery)
- **Anchor Quote**: *"found a beautifully tiled hallway"*
- **Answers**:
  1. *Source-supported?* **Yes.** The hallway is an architectural sub-structure of the subterranean tower.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **No.** Target is typed as `mystery` instead of `location`.
  4. *Predicate semantically correct?* **Yes.** `part_of` (`dnd5e:part_of`).
  5. *Would publication preserve source meaning?* **Yes.**
  6. *Owning layer?* **Candidate Node Typing.** If the tower were typed as `location`, `part_of` allows location-location.

### Case Study 3: Overly Restrictive Ontology Matrix (`works_with` at Shop)
- **Edge ID**: `e-008` (Session 7)
- **Proposition**: `Elara Greenleaf` (npc) -[`works_with`]-> `herbal shop` (location)
- **Anchor Quote**: *"Elara Greenleaf, an Elf Druid, greets the new visitors"*
- **Answers**:
  1. *Source-supported?* **Yes.** Elara clerks and operates the herbal shop.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **Yes.** NPC and Location.
  4. *Predicate semantically correct?* **Yes, in extractor intent.** Buddy uses `works_with` for employment.
  5. *Would publication preserve source meaning?* **Yes, if expressed as workplace relationship.**
  6. *Owning layer?* **Ontology Contract.** `dnd5e:works_with` refuses locations; requires `works_at` or widening allowed endpoints.

### Case Study 4: Animal Companion Mistyped as NPC
- **Edge ID**: `edge:pippa_owns_bubbles` (Session 3)
- **Proposition**: `Pippa` (npc) -[`owns`]-> `Bubbles` (npc)
- **Anchor Quote**: *"hitched up Bubbles the Float Goat to her wagon full of kegs"*
- **Answers**:
  1. *Source-supported?* **Yes.** Bubbles is Pippa's draft float-goat.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **No.** Bubbles is a beast/creature, but was mapped to `npc`.
  4. *Predicate semantically correct?* **Yes.** `owns` (`dnd5e:owns`).
  5. *Would publication preserve source meaning?* **Yes.**
  6. *Owning layer?* **Node Classification.** `dnd5e:owns` allows NPC to own a creature. Because Bubbles was typed as NPC, ownership between NPCs was rejected.

### Case Study 5: Erroneous Extraction Inverting Meaning (Combat Misclassification)
- **Edge ID**: `edge:karsemine_attacks_bonogo` (Session 3)
- **Proposition**: `Karsemine` (pc) -[`attacks`]-> `Bonogo` (pc)
- **Anchor Quote**: *"Karsemine cast Zephyr strike and ran down the bank shooting arrows"*
- **Answers**:
  1. *Source-supported?* **No.** Karsemine was firing at debris/water to assist Bonogo, not attacking him.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **Yes.**
  4. *Predicate semantically correct?* **No.**
  5. *Would publication preserve source meaning?* **No.** Emits false PvP hostility.
  6. *Owning layer?* **Extraction.** Correctly rejected.

### Case Study 6: Unmapped Organization Kind
- **Edge ID**: `edge:barin-member-city-council` (Session 9)
- **Proposition**: `Barin` (npc) -[`member_of`]-> `The City Council` (organization)
- **Anchor Quote**: *"Barin the proprietor of the Copper and Quartz Inn who is also on the city council"*
- **Answers**:
  1. *Source-supported?* **Yes.** Barin is an active councilman.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **Yes in intent; kind string unmapped in Buddy adapter.**
  4. *Predicate semantically correct?* **Yes.** `member_of` (`dnd5e:member_of`).
  5. *Would publication preserve source meaning?* **Yes.**
  6. *Owning layer?* **Buddy Adapter Vocabulary.** Mapping `organization` → `dnd5e:faction` immediately publishes this edge.

---

## 12. Largest Truthful Recovery Opportunities

Ranked by number of recoverable truthful relationships:

1. **Resolve PC candidate kind aliasing in identity gate (`pc` → `player_character`)**:
   - **Yield**: **+62 relationships** (immediate +22.5% increase)
   - **Confidence**: High (100% mechanical defect in `resolve_identity_against_context`).
2. **Promote / Refine concrete `mystery` nodes to proper domain types**:
   - **Yield**: **+26 relationships** (+9.4% increase)
   - **Confidence**: High (reclassifying towers, tunnels, celebrations, and rats into location/event/creature).
3. **Widen ontology endpoint-kind contracts for physical / workplace relations**:
   - **Yield**: **+10 relationships** (+3.6% increase)
   - **Confidence**: High (allowing `works_with` for shops, `carries` for boats/containers, `leads_to` for trapdoors).
4. **Admit `organization` kind in Buddy vocabulary**:
   - **Yield**: **+4 relationships** (+1.4% increase)
   - **Confidence**: High (mapping `organization` to `dnd5e:faction` in `_BUDDY_TO_DM_KIND`).
5. **Introduce explicit Campaign Quest / Intent relations**:
   - **Yield**: **+6 relationships** (+2.2% increase)
   - **Confidence**: Medium (formalizing `mission_targets` / `mission_focus` in ontology).
6. **Correct beast / mount companion typing**:
   - **Yield**: **+3 relationships** (+1.1% increase)
   - **Confidence**: High (typing Float Goat as `creature`, enabling `owns`, `holds`, and `carries`).

**Total Achievable Truthful Upper Bound: 252 / 276 relationships (91.3%)**.

---

## 13. Benchmark Consequence

### Verdict
**`NO — fix identity resolution (PC kind aliasing and Lysandra split) first`**

### Rationale
Running the 16-question oracle or Agent benchmark against the current Session 10 graph would yield deeply misleading results:
1. **Total PC Relationship Blackout (Sessions 2–10)**: Because of the `pc` vs `player_character` collision, all six Player Characters have **zero published relationships** across Sessions 2 through 10. Any benchmark question probing PC actions, inventory, combat, or social interactions in those sessions will fail due to a known plumbing defect, not retrieval architecture.
2. **Fractured NPC Continuity**: Captain Lysandra is split across two disjoint identities (`node:lysandra-ironveil` and `npc:captain-lysandra`), breaking question answering around the Mirathorn city guard.
3. **Lossy Semantic Distortion**: Six published edges misrepresent tavern employment as ownership and casual mentions as associations.

Running the benchmark now would measure the distortion of a known identity collision rather than the true capacity of the graph memory system.

---

## 14. Recommended Successor

### **Single Recommended Slice: `identity/type repair`**

Do **not** broaden scope, change extraction prompts, or rerun inference.
Execute a single, tightly bounded zero-model repair slice:
1. Normalize candidate kind `'pc'` to `'player_character'` inside `resolve_identity_against_context` so candidate PCs match canonical PCs cleanly without triggering `blocked_collision`.
2. Add `'organization': 'dnd5e:faction'` to `_BUDDY_TO_DM_KIND`.
3. Add alias resolution between `'node:lysandra-ironveil'` and `'npc:captain-lysandra'`.
4. Re-run zero-model rechain.

This single slice will immediately recover **66+ truthful relationships**, restore PC memory across Sessions 2–10, heal the Lysandra split, and elevate the publication rate to **>78%** before running the 16-question benchmark.
