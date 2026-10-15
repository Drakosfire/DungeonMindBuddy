# Gold domain types and literal objects

This is an intentional extraction reference vocabulary. It is independent of runtime schemas and native predicate mappings. Every retained node has a primary kind and a short rationale; `entity` is never a default. Source facts and uncertainty determine the granularity.

| Gold kind | Meaning | Nodes |
| --- | --- | --- |
| party | Named adventuring party identity. | party |
| person | Named individual with personhood; species subtype need not be established. | lysandro, ephanna, thrin, caelynn, lysandra, hesta, baergrom, karsemine, bonogo, stafl, brin, fellinor, grobnok, cinderbranch, pippa |
| building | Distinct house, warehouse, inn or shop building. | lysandro_house, mireward_warehouse, apothecary, mireward_inn, edge_house, edge_warehouse |
| gate | Distinct settlement gate. | south_gate, north_gate |
| route | Road or tunnel corridor. | fin_road, north_road, north_tunnel, lower_tunnel |
| settlement | Named city, town or route destination treated as settlement; detailed scale may be unknown. | mireward, edge, mirathorn, mossford, stone_bridge |
| region | Geographic landscape/region. | bayou |
| prospective_place | Intended future place, explicitly not asserted extant. | new_forest |
| chamber | Room, cellar or underground chamber. | flesh_den, edge_cellar |
| aperture | Incident-specific opening between surface and den. | den_aperture |
| defensive_structure | Wall or magical ward system guarding a place. | mireward_walls, magical_wards |
| creature_individual | A distinct individual creature or named creature companion. | ogonob, mireward_flesh, black_cat_familiar, edge_flesh, bubbles |
| creature_group | Incident-scoped creatures or wildlife collective, not a generic global alias. | warehouse_monsters, town_attackers, remaining_monsters, edge_monsters, bayou_tentacles, wildlife |
| person_group | Meaningful people/refugee/responders collective, including an incident scouting pair. | rescued_children, scouting_pair, townspeople, edge_fugitives, edge_guards, edge_refugees, mirathorn_responders, mirathorn_infected |
| body_part_group | An anatomically related set of parts of a creature. | restraining_tentacles |
| artifact_individual | A particular story-bearing artifact. | witness_seed |
| equipment_individual | A particular possessed object whose connection matters. | personal_safe, sword |
| item_type | A named supply or consumable category; amount belongs to facts. | arrows, alchemists_fire, greater_healing_potions, healing_potions, minor_healing_half_bottles, oil_vials, refugee_cures, sleep_potions |
| asset_collection | A source-grouped travel asset collection without fabricated individual IDs. | horses_wagon |
| spell | A named spell, with intent/performance on its use facts. | eldritch_blast, find_familiar |
| phenomenon | A particular narrated sensory or psychic effect. | psychic_pull, unknown_call, psychic_pressure, psychic_assault, physical_thrum |
| weather_event | A temporally bounded storm. | storm, edge_storm |
| scene | A coherent rescue, combat, disclosure or journey episode. | seed_disclosure, child_rescue, den_combat, north_journey |
| planned_action | A proposed signal/action or investigation objective. | ground_signal, swamp_investigation |
| treatment_technique | A reusable method for administering a remedy. | misted_cure |
| named_destination | Named destination whose settlement/geographic subtype is not established. | fin |

## Values attached to assertions

Facts always have a node subject and exactly one node `object` or typed literal `object_value`. For example, `flesh_den → has_dimensions → {type: dimensions, value: [10,10], unit: feet}` retains the measurement without creating a place called Ten By Ten Feet. `lower_tunnel → descends → {type: direction, value: north}` keeps its approximate twenty-foot drop as a contextual numeric attribute. The north gate and north road remain actual distinct places.

Short/long rest are activity values on occurred/intended facts. Next morning is a relative time value. Mireward buildings is a contextual condition set for Lysandra’s no-burning promise. Names such as Brin Holloway, Hesta Bramblewood, Ironveil Warehouse and Crooked Retort identify the existing gold node through literal name assertions; they do not create duplicate people/buildings. Edge’s military fort status is a historical role of Edge; its wards remain a meaningful defensive structure.

The absence of movement and absence of immediate threat are time-local observation values, with explicit scope/polarity/permanence attributes. Stopped attackers retain observed behavior separately from a hypothesized psychic-control mechanism.

The child-rescue, den-combat, seed-disclosure and onward-journey scenes are intentional episode nodes. Spell nodes are distinct from consumable item types. The singular Witness Seed is an artifact; future forest is a prospective place, explicitly not extant. Children/refugees and creature groups remain incident-scoped collectives. Supplies remain named types with quantities on the acquisition facts; no unnamed bottle gets an invented identity.

Burning flesh refers to the Mireward creature in a burning/shriveling condition, rather than a duplicate creature identity. Warehouse monsters, Mireward flesh creature, historical Edge flesh creature and bayou tentacles retain their distinct scopes.

## Genuine unresolved classification detail

- **ogonob**: primary kind `creature_individual`; unresolved creature subtype/species. S23 states Ephanna summons Ogonob; no species/subtype claim required or proved by inspected evidence. Evidence: e165.
- **fin**: primary kind `named_destination`; unresolved settlement scale and exact geography. Source names the destination of a road; exact geographic kind is not independently established. Evidence: e156.

These uncertainty entries are reference-checked. They do not authorize a guessed subtype or an identity merge. In particular, no source establishes whether the destination Fin is a town, city, village or another geographic destination.
