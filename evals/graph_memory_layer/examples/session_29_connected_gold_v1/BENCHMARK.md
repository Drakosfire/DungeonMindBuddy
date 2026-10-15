# Continuity and multi-hop benchmark

Evaluate semantic coverage separately from native admission. Each answer has fact IDs, exact evidence IDs and explicit directed traversal witnesses in `gold.json`. `expected_fact_path` is an answer-support subgraph, not an assertion that every listed edge forms one linear path. Each question also freezes expected node kinds and typed literal objects. Retain attribution, uncertainty, modality and chronology.

## q01: Whose house provides the lookout and how does he relate to Lysandra?

Lysandro’s house; Lysandro is Lysandra’s father, explicit S22 and dossier support.

Expected facts: house_owner, father.

Failures: Lysandro and Lysandra are the same person; Relation guessed from similar names.

## q02: Which children were rescued, where, and what supports Edge origin?

Sleeping children carried from Mireward warehouse; Baergrom rescues them. S25 houses Edge refugees there and mentions older children; exact rescued-child origin is operator clarified.

Expected facts: rescue_actual, children_carried, warehouse_identity, refugee_housing, refugee_origin, children_context, operator_children_origin.

Failures: Quote Session29 as explicitly saying children are from Edge; Put rescue in Fellinor warehouse.

## q03: How do Mireward rescue and Fellinor warehouse access differ?

Mireward warehouse rescue occurred; Edge warehouse access is future and depends on safe.

Expected facts: warehouse_exit, rescue_actual, edge_warehouse, safe_access.

Failures: One warehouse; Party already looted safe.

## q04: What fire supplies are acquired and used?

Two bottles initially, one poured into flesh wound, six more next day. Oil vials also packed. No exact final inventory assertion.

Expected facts: fire_initial, fire_use, fire_more, oil.

Failures: Six is total acquired; Alchamist is a person; Fire Bolt is bottled fire.

## q05: How is the northward pull connected to the creature and what changes afterward?

Shared pull localized beyond gate; giant den creature identified as source; after burning presence gone. Remaining attackers stop as if direction lost.

Expected facts: psychic_ephanna, psychic_thrin, psychic_location, flesh_source, burning, pull_gone, control_lost.

Failures: Seed call permanently cured; Road to Fin necessarily north road.

## q06: Did Ephanna actually cast Eldritch Blast in child rescue?

Recap says will use: intended cast only. Stafl shoots arrows; later Karsemine casts Fire Bolt in den.

Expected facts: eldritch_intent, arrows, firebolt, firebolt_spell, den_firebolt.

Failures: Eldritch Blast confirmed hit/kill; All attacks only plans.

## q07: Did Edge monster appear 150 years ago?

No. Brin dates military fort era about 150 years earlier; cellar infestation is later undated history.

Expected facts: fort, wards, edge_monster.

Failures: Monster 150 years old; Same individual as Mireward creature.

## q08: How does cure knowledge move between places?

Hesta produces refugee cures; Cinderbranch reports Mirathorn misting; Stafl tells Lysandro; Mossford warning is planned.

Expected facts: cures_ready, mist_cure, spraying, mist_transfer, mossford_plan, mist_communicated.

Failures: All refugees confirmed administered mist; Mossford messenger arrived.

## q09: How does Thrin’s attitude toward seed change?

Resented burden chosen twenty years earlier; after local encounter feels better and accepts responsibility for new forest.

Expected facts: seed_bearer, resentment, thrin_improved, seed_reappraisal, new_forest_goal.

Failures: Seed removed; Thrin proved Threnn.

## q10: What route follows victory and what remains dangerous?

Choose surface north, rest proposal and next morning departure with horses/wagon; Lysandra stays. Bayou tentacles take wildlife; physical thrum; decide to stop and camp, intending daylight Edge arrival. Camp setup and arrival are not independently narrated.

Expected facts: surface_route, long_rest_plan, transport, stays, bayou, wildlife, physical_thrum, camp, edge_arrival_intent.

Failures: Edge arrival already occurred; All threat vanished permanently.

## q11: What are the lower tunnel observations and explored extent?

Burning exposes remains below; torch estimates 20-foot drop then north slope; black cat sent, no report; party chooses surface.

Expected facts: lower_revealed, depth, familiar, surface_route, scout_plan, scout_execution.

Failures: Cat confirms tunnel reaches Edge; 10-foot aperture is 20-foot lower drop.

## q12: How do defenses and help evolve?

Lysandra promises help if no buildings burn; reports wall repair; Inn meeting supports Hesta; morning rebuilding and Lysandra stays.

Expected facts: no_burning, wall_repair, meeting, cures_ready, stays.

Failures: Burn warehouse down; Lysandra departs with party.

## q13: Does the unnamed town in Session29 refer to Pippa and Bubbles’ town?

No. Local continuity is Mireward Reach; Pippa/Bubbles earlier Stone Bridge brewery thread supplies a disambiguation contrast only.

Expected facts: mireward_context, pippa_prior, bubbles_prior.

Failures: Resolve every town mention to Stone Bridge; Import Pippa or Bubbles into rescue.
