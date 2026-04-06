# Phase 6 Sample Review Batch

First-pass candidate questions for editorial accept/reject/revise decisions.

## 1. q_longmont_campaign_general_notes_3 (answerable, preflight: supported)

- source: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md`
- question: What dual role does Commander Elric Vane play in the campaign notes?
- expected_answer_summary: Elric Vane is both a tactical commander and a cult priest coordinating rituals and spread operations.
- must_hit_tokens: elric vane, dual leadership, tactical leader, high priest
- stale_tokens: single civilian role, unrelated to rituals
- target_entities: ent_commander_elric_vane, ent_shepherds_flock
- target_attributes: rank_or_title, goals
- coverage: 4/4
- preflight_support_status: supported
- preflight_support_details:
  - Commander Elric Vane -> supported (best_fuzzy=1.0)
  - The Shepherds -> supported (best_fuzzy=1.0)
- closest_match_facts:
  - ent_commander_elric_vane::rank_or_title -> Commander
  - ent_commander_elric_vane::rank_or_title -> high priest in the cult
  - ent_commander_elric_vane::goals -> Discusses progress of their plans in meetings

## 2. q_battle_with_the_wolf_and_aftermath_2 (partially_answerable, preflight: supported)

- source: `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/Battle with The Wolf and Aftermath.md`
- question: Which environmental defenses in the council chamber change the battle flow?
- expected_answer_summary: Arcane traps, falling debris, alarm pulses, and illusory walls force positioning and can trigger reinforcements.
- must_hit_tokens: arcane traps, falling debris, alarm pulses, illusory walls
- stale_tokens: normal battlefield, no magical defenses
- target_entities: ent_council_room, ent_the_wolf
- target_attributes: defenses, combat_context
- coverage: 2/4
- preflight_support_status: supported
- preflight_support_details:
  - Council Chamber -> supported (best_fuzzy=1.0)
  - The Wolf -> supported (best_fuzzy=1.0)
- closest_match_facts:
  - ent_council_room::defenses -> had to double as a fortress during the city's more tumultuous years
  - ent_council_room::defenses -> council chamber has magical defenses affecting the battle environment
  - ent_the_wolf::defenses -> Creates illusory duplicates of himself as decoys

## 3. q_battle_with_the_wolf_and_aftermath_3 (partially_answerable, preflight: supported)

- source: `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/Battle with The Wolf and Aftermath.md`
- question: How does Thalia's condition differ from fully corrupted guards during this encounter?
- expected_answer_summary: Thalia is presented as ensorcelled/manipulated rather than fully corrupted, while many guards are explicitly corrupted.
- must_hit_tokens: thalia, ensorcelled, not fully corrupted, corrupted guards
- stale_tokens: thalia fully corrupted, all guards uncorrupted
- target_entities: ent_commander_thalia_ashenvale, ent_the_wolf
- target_attributes: status, loyalty_or_alignment_context
- coverage: 2/4
- preflight_support_status: supported
- preflight_support_details:
  - Commander Thalia Ashenvale -> supported (best_fuzzy=1.0)
  - The Wolf -> supported (best_fuzzy=1.0)
- closest_match_facts:
  - ent_commander_thalia_ashenvale::loyalty_or_alignment_context -> innocent
  - ent_commander_thalia_ashenvale::loyalty_or_alignment_context -> She has a strong sense of duty
  - ent_the_wolf::loyalty_or_alignment_context -> The Wolf may be a cult sympathizer working to sabotage council decision-making

## 4. q_battle_with_the_wolf_and_aftermath_4 (partially_answerable, preflight: supported)

- source: `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/Battle with The Wolf and Aftermath.md`
- question: After the chamber fight, what are the main branch paths that still converge on the sewers?
- expected_answer_summary: Chasing the Wolf, covert operations, or helping Torbin all eventually lead players to sewer entrances and ritual clues.
- must_hit_tokens: chase, covert ops, torbin, sewers
- stale_tokens: single linear path, no sewer link
- target_entities: ent_the_wolf
- target_attributes: event_sequence, goals
- coverage: 1/2
- preflight_support_status: supported
- preflight_support_details:
  - The Wolf -> supported (best_fuzzy=1.0)
  - Torbin -> supported (best_fuzzy=1.0)
- closest_match_facts:
  - ent_the_wolf::goals -> stall the players
  - ent_the_wolf::goals -> escape into the sewers

## 5. q_battle_with_the_wolf_and_aftermath_1 (unanswerable, preflight: weakly_supported)

- source: `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/Battle with The Wolf and Aftermath.md`
- question: What happens to The Wolf by the end of the council chamber fight?
- expected_answer_summary: The Wolf is ultimately killed, with Bonogo delivering the killing blow and decapitation-style terminal outcome.
- must_hit_tokens: killed, killing blow, bonogo, decapitated
- stale_tokens: escaped safely, still alive, still stalling
- target_entities: ent_the_wolf
- target_attributes: status, combat_outcome
- coverage: 0/2
- preflight_support_status: weakly_supported
- preflight_support_details:
  - The Wolf -> supported (best_fuzzy=1.0)
  - Bonogo -> unsupported (best_fuzzy=0.0)

## 6. q_the_emergency_council_meeting_2 (unanswerable, preflight: supported)

- source: `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Emergency Council Meeting.md`
- question: How does Thalia's proposed guard sweep become a hidden failure mode?
- expected_answer_summary: Because Thalia is under the Wolf's influence, guard strike teams can be redirected to wrong locations, delaying response and enabling summoning.
- must_hit_tokens: thalia, wolf influence, wrong locations, delay
- stale_tokens: thalia fully reliable, no internal sabotage
- target_entities: ent_commander_thalia_ashenvale, ent_the_wolf
- target_attributes: status, event_sequence
- coverage: 0/4
- preflight_support_status: supported
- preflight_support_details:
  - Commander Thalia Ashenvale -> supported (best_fuzzy=1.0)
  - The Wolf -> supported (best_fuzzy=1.0)

## 7. q_the_emergency_council_meeting_4 (unanswerable, preflight: weakly_supported)

- source: `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Emergency Council Meeting.md`
- question: What time-pressure mechanic drives urgency during emergency council deliberation?
- expected_answer_summary: Each discussion round consumes in-game time and advances a countdown roll toward the kaiju summoning trigger.
- must_hit_tokens: time pressure, discussion rounds, countdown, kaiju summoning
- stale_tokens: unlimited deliberation, no countdown
- target_entities: ent_city_council, ent_maelthor
- target_attributes: event_sequence, ritual
- coverage: 0/4
- preflight_support_status: weakly_supported
- preflight_support_details:
  - City Council -> supported (best_fuzzy=1.0)
  - Maelthor -> unsupported (best_fuzzy=0.0)

## 8. q_the_emergency_council_meeting_1 (partially_answerable, preflight: supported)

- source: `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Emergency Council Meeting.md`
- question: What strategy does the Wizards' College propose during the emergency meeting, and what is the key tradeoff?
- expected_answer_summary: They propose arcane lockdown wards for detection and containment, but at the cost of citywide disruption, panic risk, and festival cancellation.
- must_hit_tokens: wizards' college, arcane lockdown, wards, tradeoff
- stale_tokens: no magical proposal, cost-free solution
- target_entities: ent_headmaster_tinkerbright, ent_wizards_college
- target_attributes: goals, strategy
- coverage: 2/4
- preflight_support_status: supported
- preflight_support_details:
  - Headmaster Tinkerbright -> supported (best_fuzzy=1.0)
  - Wizards' College -> supported (best_fuzzy=1.0)
- closest_match_facts:
  - ent_headmaster_tinkerbright::goals -> Takes threats to the city seriously
  - ent_headmaster_tinkerbright::goals -> Eager to deploy Wizard’s College resources to detect and counteract the cult’s influence
  - ent_wizards_college::goals -> Wants magical control

## 9. q_the_emergency_council_meeting_3 (partially_answerable, preflight: weakly_supported)

- source: `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Emergency Council Meeting.md`
- question: Which council alignments emerge around purification, arming citizens, and covert operations?
- expected_answer_summary: Wizards and agriculture align on purification pressure, while goblin/undercity factions can align with Torrin and Rurik; Barin aligns with covert actions.
- must_hit_tokens: wizards and agriculture aligned, goblins, torrin, rurik, barin
- stale_tokens: all factions isolated, no cross-faction alignment
- target_entities: ent_merril_tealeaf, ent_torrin_flamescale, ent_rurik_stonehammer, ent_barin_coppergleam, ent_grobnok_the_goblin
- target_attributes: faction, goals
- coverage: 6/10
- preflight_support_status: weakly_supported
- preflight_support_details:
  - Merril Tealeaf -> supported (best_fuzzy=1.0)
  - Torrin Flamescale -> supported (best_fuzzy=1.0)
  - Rurik Stonehammer -> supported (best_fuzzy=1.0)
  - Barin Coppergleam -> unsupported (best_fuzzy=0.5)
  - Grobnok -> supported (best_fuzzy=1.0)
- closest_match_facts:
  - ent_merril_tealeaf::faction -> Agricultural Union
  - ent_merril_tealeaf::faction -> Agricultural Union
  - ent_merril_tealeaf::goals -> Focuses on the well-being of the city's populace through food and agriculture

## 10. q_longmont_campaign_general_notes_1 (partially_answerable, preflight: supported)

- source: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md`
- question: What does the Longmont campaign note establish about the Shepherds' ideology and patron?
- expected_answer_summary: The Shepherds follow Maelthor and frame atrocities as ritual sacrifices for ascension, tied to human supremacy and otherworldly power.
- must_hit_tokens: shepherds, maelthor, ritual sacrifices, ascension
- stale_tokens: purely political gang, no patron
- target_entities: ent_shepherds_flock, ent_maelthor
- target_attributes: beliefs, goals
- coverage: 2/4
- preflight_support_status: supported
- preflight_support_details:
  - The Shepherds -> supported (best_fuzzy=1.0)
  - Maelthor -> supported (best_fuzzy=1.0)
- closest_match_facts:
  - ent_shepherds_flock::goals -> Protest the high toll to enter the city
  - ent_shepherds_flock::goals -> involved in distribution of twisted meat as part of their devotion
  - ent_maelthor::goals -> promises ascension and transcendence to those who aid in its resurrection or awakening on earth

