---
schema: dmb_recap_breadcrumbs_v1
gold_extension_schema: dmb_recap_beat_population_gold_v0
artifact_status: gold_prompt_target_not_corpus_canonical
source_recap_path: "Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md"
source_breadcrumb_path: "Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 13 - The Meaty and the Dead.breadcrumbed.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 1
  campaign_id: longmont-c1
session:
  number: 13
  title: "Session 13 - The Meaty and the Dead"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 13
  last_updated_session: 13
  source_class: observed_session_recap
gold_notes:
  purpose: "Manual beat/location/population target for future prompt and retrieval benchmarks."
  instructions: "Do not treat this as the blessed corpus breadcrumb. Use it to compare future ingestion prompt output against manually identified beat spans and populations."
  beat_id_grammar: "c{campaign_number}s{session_number}-b{ordinal:03d}-{short_slug}"
  beat_boundary_policy: "Beats are retrieval-stable spans, not story chapters: split when location, sublocation, active roster, party split/rejoin state, or event mode changes enough that one population row would mix answers."
  slug_policy: "Beat ID slugs may be action-oriented when the unit span is unchanged, but should preserve retrieval-critical location/event handles such as infirmary, study room, morgue, ritual room, and tunnel."
entity_index:
  pcs:
    - slug: baergrom
      route: "Longmont Campaign/Campaign 1/PCs/baergrom/"
    - slug: bonogo
      route: "Longmont Campaign/Campaign 1/PCs/bonogo/"
    - slug: caelynn
      route: "Longmont Campaign/Campaign 1/PCs/caelynn/"
    - slug: ephanna
      route: "Longmont Campaign/Campaign 1/PCs/ephanna/"
    - slug: karsemine
      route: "Longmont Campaign/Campaign 1/PCs/karsemine/"
    - slug: stafl
      route: "Longmont Campaign/Campaign 1/PCs/stafl/"
  locations:
    - slug: stormspire_academy
      proposed_route: "Longmont Campaign/Campaign 1/Locations/stormspire_academy/"
      rationale: "Primary session location for academy events."
    - slug: council_chambers
      proposed_route: "Longmont Campaign/Campaign 1/Locations/council_chambers/"
      rationale: "Guard stop happens outside this area."
    - slug: basement_morgue
      proposed_route: "Longmont Campaign/Campaign 1/Locations/basement_morgue/"
      rationale: "Ambush and combat scene."
    - slug: study_room
      proposed_route: "Longmont Campaign/Campaign 1/Locations/study_room/"
      rationale: "Stormspire sublocation used for the magical short rest."
    - slug: infirmary
      proposed_route: "Longmont Campaign/Campaign 1/Locations/infirmary/"
      rationale: "Stormspire sublocation where Torbin is under Tealeaf's care."
    - slug: ritual_room
      proposed_route: "Longmont Campaign/Campaign 1/Locations/ritual_room/"
      rationale: "Stormspire sublocation tied to the Speak with Dead ritual; overlaps the basement morgue in this recap."
    - slug: tunnel_entrance
      proposed_route: "Longmont Campaign/Campaign 1/Locations/tunnel_entrance/"
      rationale: "End-of-session onward route after the ritual room is found empty."
  new_hub_candidates:
    - slug: wolf
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/wolf/"
    - slug: thalia
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/thalia/"
    - slug: mossglade
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/mossglade/"
    - slug: torbin
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/torbin/"
    - slug: professor_tealeaf
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/professor_tealeaf/"
    - slug: professor_cinderbranch
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/professor_cinderbranch/"
    - slug: necromancer
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/necromancer/"
    - slug: draven
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/draven/"
    - slug: elite_guard
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/elite_guard/"
    - slug: sewer_meat_monster
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/sewer_meat_monster/"
    - slug: lira
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/lira/"
    - slug: shepherd
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/shepherd/"
beat_index:
  - beat_id: c1s13-b001-plan-academy-departure
    summary: "Party leaves the Council Chambers with Wolf's body/head, is stopped by alerted guards, and Thalia explains."
    unit_ids: [u-L0003-01, u-L0003-02, u-L0003-03, u-L0003-04]
    location_routes:
      - "Longmont Campaign/Campaign 1/Locations/council_chambers/"
    population_evidence:
      - entity_route: "Longmont Campaign/Campaign 1/PCs/stafl/"
        presence_kind: carried
        evidence_unit_ids: [u-L0003-01]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/bonogo/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0003-04]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/caelynn/"
        presence_kind: carried
        evidence_unit_ids: [u-L0003-01]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/baergrom/"
        presence_kind: carried
        evidence_unit_ids: [u-L0003-01]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/karsemine/"
        presence_kind: carried
        evidence_unit_ids: [u-L0003-01]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/ephanna/"
        presence_kind: carried
        evidence_unit_ids: [u-L0003-01]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/wolf/"
        presence_kind: explicit
        entity_state: dead_body_or_head
        evidence_unit_ids: [u-L0003-01, u-L0003-04]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/thalia/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0003-03]
      - entity_label: "alerted guards"
        presence_kind: explicit
        evidence_unit_ids: [u-L0003-02, u-L0003-03]
  - beat_id: c1s13-b002-street-meat-incident
    summary: "Street checkpoint / meat check; covert ops challenge the party, meat is dumped, guards and a mage respond."
    unit_ids: [u-L0005-01, u-L0005-02, u-L0005-03, u-L0005-04]
    location_labels: ["street between Council Chambers and Stormspire Academy"]
    population_evidence:
      - entity_route: "Longmont Campaign/Campaign 1/PCs/bonogo/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0005-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/baergrom/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0005-03]
      - entity_label: "party"
        presence_kind: carried
        evidence_unit_ids: [u-L0005-01, u-L0005-04]
      - entity_label: "covert ops group"
        presence_kind: explicit
        evidence_unit_ids: [u-L0005-02]
      - entity_label: "guards"
        presence_kind: explicit
        evidence_unit_ids: [u-L0005-03]
      - entity_label: "mage"
        presence_kind: explicit
        evidence_unit_ids: [u-L0005-04]
  - beat_id: c1s13-b003-stormspire-arrival-desk
    summary: "Party reaches Stormspire, sees active wizard response, meets Mossglade, and draws Cinderbranch's attention."
    unit_ids: [u-L0007-01, u-L0007-02, u-L0007-03, u-L0007-04, u-L0007-05]
    location_routes:
      - "Longmont Campaign/Campaign 1/Locations/stormspire_academy/"
    population_evidence:
      - entity_label: "party"
        presence_kind: explicit
        evidence_unit_ids: [u-L0007-01, u-L0007-03]
      - entity_label: "wizards"
        presence_kind: explicit
        evidence_unit_ids: [u-L0007-02]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/mossglade/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0007-03, u-L0007-04]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/professor_cinderbranch/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0007-05]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/wolf/"
        presence_kind: explicit
        entity_state: dead_head
        evidence_unit_ids: [u-L0007-05]
  - beat_id: c1s13-b004-stormspire-options-and-split
    summary: "Mossglade gives study room and Torbin information; the party chooses a two-way split."
    unit_ids: [u-L0009-01, u-L0009-02, u-L0011-01, u-L0011-02, u-L0011-03]
    location_routes:
      - "Longmont Campaign/Campaign 1/Locations/stormspire_academy/"
    location_labels: ["desk area", "infirmary", "necromancer route"]
    population_evidence:
      - entity_label: "party"
        presence_kind: explicit
        evidence_unit_ids: [u-L0011-02, u-L0011-03]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/mossglade/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0009-01, u-L0009-02]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/professor_cinderbranch/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0009-01]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/torbin/"
        presence_kind: mentioned_only
        evidence_unit_ids: [u-L0009-02, u-L0011-01, u-L0011-03]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/professor_tealeaf/"
        presence_kind: mentioned_only
        evidence_unit_ids: [u-L0009-02]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/necromancer/"
        presence_kind: mentioned_only
        evidence_unit_ids: [u-L0011-01, u-L0011-03]
  - beat_id: c1s13-b005-infirmary-torbin-thread
    summary: "Ephanna and Baergrom check on Torbin; Tealeaf cannot help him and moves to potion work."
    unit_ids: [u-L0013-01, u-L0013-02]
    location_routes:
      - "Longmont Campaign/Campaign 1/Locations/infirmary/"
    population_evidence:
      - entity_route: "Longmont Campaign/Campaign 1/PCs/ephanna/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0013-01]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/baergrom/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0013-01]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/torbin/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0013-01, u-L0013-02]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/professor_tealeaf/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0013-01, u-L0013-02]
  - beat_id: c1s13-b006-study-room-short-rest
    summary: "Necromancer prepares the ritual; the ritual-side party rests in the study room and Caelynn plays pan flute."
    unit_ids: [u-L0015-01, u-L0015-02, u-L0015-03, u-L0015-04, u-L0015-05]
    location_routes:
      - "Longmont Campaign/Campaign 1/Locations/study_room/"
    population_evidence:
      - entity_route: "Longmont Campaign/Campaign 1/PCs/karsemine/"
        presence_kind: carried
        evidence_unit_ids: [u-L0011-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/bonogo/"
        presence_kind: carried
        evidence_unit_ids: [u-L0011-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/stafl/"
        presence_kind: carried
        evidence_unit_ids: [u-L0011-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/caelynn/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0015-05]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/necromancer/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0015-01, u-L0015-03]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/wolf/"
        presence_kind: explicit
        entity_state: dead_head
        evidence_unit_ids: [u-L0015-02]
  - beat_id: c1s13-b007-escaped-meat-second-split
    summary: "Party regroups, discovers escaped meat loose in the Academy, and splits again."
    unit_ids: [u-L0017-01, u-L0017-02, u-L0017-03, u-L0017-04]
    location_routes:
      - "Longmont Campaign/Campaign 1/Locations/stormspire_academy/"
    population_evidence:
      - entity_label: "party"
        presence_kind: explicit
        evidence_unit_ids: [u-L0017-01, u-L0017-02]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/stafl/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0017-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/bonogo/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0017-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/caelynn/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0017-01, u-L0017-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/baergrom/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0017-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/karsemine/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0017-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/ephanna/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0017-04]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/torbin/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0017-04]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/necromancer/"
        presence_kind: mentioned_only
        evidence_unit_ids: [u-L0017-03]
      - entity_label: "escaped meat"
        presence_kind: explicit
        evidence_unit_ids: [u-L0017-01]
  - beat_id: c1s13-b008-basement-morgue-speak-with-dead
    summary: "Stafl and Bonogo enter the morgue ritual; Wolf answers Speak with Dead questions."
    unit_ids: [u-L0019-01, u-L0019-02, u-L0019-03, u-L0021-01, u-L0021-02, u-L0023-01, u-L0023-02, u-L0025-01, u-L0025-02, u-L0027-01, u-L0027-02, u-L0027-03, u-L0029-01, u-L0029-02, u-L0029-03, u-L0029-04, u-L0029-05]
    location_routes:
      - "Longmont Campaign/Campaign 1/Locations/basement_morgue/"
      - "Longmont Campaign/Campaign 1/Locations/ritual_room/"
    population_evidence:
      - entity_route: "Longmont Campaign/Campaign 1/PCs/stafl/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0019-01, u-L0019-03]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/bonogo/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0019-01, u-L0021-02]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/wolf/"
        presence_kind: explicit
        entity_state: dead_head_or_spirit
        evidence_unit_ids: [u-L0019-01, u-L0021-01]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/necromancer/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0019-03, u-L0029-01]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/lira/"
        presence_kind: mentioned_only
        evidence_unit_ids: [u-L0025-02]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/shepherd/"
        presence_kind: mentioned_only
        evidence_unit_ids: [u-L0027-01, u-L0029-03, u-L0029-05]
  - beat_id: c1s13-b009-morgue-ambush-fight-scene
    summary: "Continuity scene span: ambush reveal through combat exchange and escape in the basement morgue."
    unit_ids: [u-L0031-01, u-L0031-02, u-L0031-03, u-L0033-01, u-L0033-02, u-L0033-03, u-L0033-04, u-L0033-05, u-L0035-01, u-L0035-02, u-L0035-03, u-L0035-04, u-L0037-01, u-L0037-02]
    location_routes:
      - "Longmont Campaign/Campaign 1/Locations/basement_morgue/"
      - "Longmont Campaign/Campaign 1/Locations/ritual_room/"
    location_labels: ["morgue doorway"]
    population_evidence:
      - entity_route: "Longmont Campaign/Campaign 1/PCs/stafl/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0033-01, u-L0033-02, u-L0033-03, u-L0033-04, u-L0035-04, u-L0037-01]
      - entity_route: "Longmont Campaign/Campaign 1/PCs/bonogo/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0033-01, u-L0033-05, u-L0035-01, u-L0035-02, u-L0035-03, u-L0037-02]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/professor_cinderbranch/"
        presence_kind: explicit
        entity_state: departing
        evidence_unit_ids: [u-L0031-01]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/draven/"
        presence_kind: explicit
        entity_state: killed_by_end_of_scene
        evidence_unit_ids: [u-L0031-01, u-L0033-01, u-L0033-04]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/elite_guard/"
        presence_kind: explicit
        count: 2
        evidence_unit_ids: [u-L0031-02, u-L0033-03, u-L0035-01, u-L0035-02, u-L0035-04, u-L0037-02]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/sewer_meat_monster/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0031-02, u-L0031-03, u-L0035-03]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/necromancer/"
        presence_kind: mentioned_only
        evidence_unit_ids: [u-L0033-05]
  - beat_id: c1s13-b012-post-ambush-empty-room-tunnel
    summary: "The group explains the ambush to Cinderbranch, finds the ritual room empty, stocks up with mages, and heads toward the tunnel."
    unit_ids: [u-L0039-01, u-L0039-02]
    location_routes:
      - "Longmont Campaign/Campaign 1/Locations/ritual_room/"
      - "Longmont Campaign/Campaign 1/Locations/tunnel_entrance/"
    population_evidence:
      - entity_label: "party"
        presence_kind: carried
        evidence_unit_ids: [u-L0039-01, u-L0039-02]
      - entity_route: "Longmont Campaign/Campaign 1/NPCs/professor_cinderbranch/"
        presence_kind: explicit
        evidence_unit_ids: [u-L0039-01]
      - entity_label: "mages"
        presence_kind: explicit
        evidence_unit_ids: [u-L0039-02]
      - entity_label: "ritual room contents"
        presence_kind: absent
        evidence_unit_ids: [u-L0039-01]
counts_by_subject_type:
  indexed_entities:
    parties: 0
    pcs: 6
    npcs: 0
    locations: 7
    new_hub_candidates: 12
  inline_tags:
    PC: 34
    NPC: 0
    Location: 4
    Party: 0
    NewHubCandidate: 39
  beat_gold:
    beats: 12
    presence_kinds:
      explicit: 58
      carried: 14
      mentioned_only: 6
      absent: 1
---
# Session 13 Recap

The group has decided the best course of action is to take the Wolf to Stormspire Academy and see if someone can help cast Speak with Dead so they can learn more about the plans Wolf had.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/wolf/][Location][Longmont Campaign/Campaign 1/Locations/stormspire_academy/] But as soon as they step outside the disheveled Council Chambers they are stopped by guards who were alerted to the Rune alarms.[Location][Longmont Campaign/Campaign 1/Locations/council_chambers/] Luckily Thalia is there to explain the situation and set the guard on alert for anyone with oily eyes.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/thalia/] Bonogo, not wanting to carry an entire body, removes the Wolf’s head to take to the academy.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/wolf/]

When they enter the street outside they find it busy with activity. Suddenly one of the covert ops groups shines a light on the group, demanding we tell them if we carry any meat with us. After Bonogo and Baergrom dump out hundreds of pounds of meat on the street the guards are quick to jump into action.[PC][Longmont Campaign/Campaign 1/PCs/baergrom/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/] As the group continues on to the academy the tainted meat is burned up by one of the mages.

The group arrives at the Stormspire Academy and finds it bustling with activity.[Location][Longmont Campaign/Campaign 1/Locations/stormspire_academy/] Wizards are busy making potions, crafting runes and working on wards. The group approaches the desk of a Half-Elf: Head Clerk Mossglade.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/mossglade/] With a huff of impatience she asks how she can help. Professor Cinderbranch is very interested in the events that led to Wolf’s head ending up with the group.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/wolf/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/professor_cinderbranch/]

Before departing with Professor Cinderbranch, Mossglade also tells the group about the “study room”, a place the group can use to rest and recharge.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/mossglade/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/professor_cinderbranch/] She also tells the group that Torbin is in the infirmary under Professor Tealeaf’s care.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/torbin/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/professor_tealeaf/]

So now the group must decide which to do first: visit the Necromancer to speak to Wolf, or head to the Infirmary to check on Torbin.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/wolf/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/torbin/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/necromancer/] The group decides to do both by splitting up. Ephanna and Baergrom decide to go check on Torbin, while Karsemine, Bonogo, Stafl, and Caelynn meet with the Necromancer.[PC][Longmont Campaign/Campaign 1/PCs/baergrom/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/torbin/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/necromancer/]

Ephanna and Baergrom discover that Tealeaf has been unable to help Torbin and has not been able to help work on potions.[PC][Longmont Campaign/Campaign 1/PCs/baergrom/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/torbin/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/professor_tealeaf/] They decide to stay with Torbin while Tealeaf goes into the next room to work on potions.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/torbin/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/professor_tealeaf/]

The rest of the group meet with the Necromancer.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/necromancer/] When shown the head of Wolf they become very interested in helping.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/wolf/] Instead of casting a spell they decide to perform a ritual. While they get the ritual set up the group meets in the “Study Room” for a magical short rest. While taking this short rest Caelynn plays a wonderful song on her mother’s pan flute.[PC][Longmont Campaign/Campaign 1/PCs/caelynn/]

When the group meets up again outside the room they discover that a piece of meat from Caelynn’s bag escaped and is now on the loose in the Academy.[PC][Longmont Campaign/Campaign 1/PCs/caelynn/] Again the group decides it is best to split up and take care of two things at once. Stafl and Bonogo will go meet the Necromancer for the ritual while Caelynn, Baergrom and Karsemine will hunt for the meat.[PC][Longmont Campaign/Campaign 1/PCs/baergrom/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/necromancer/] Ephanna will stay with Torbin.[PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/torbin/]

Stafl and Bonogo enter a basement morgue and find the head of Wolf in the center and the ritual about to begin.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/wolf/][Location][Longmont Campaign/Campaign 1/Locations/basement_morgue/] As with all Speak with Dead spells they are granted 5 questions. Stafl promised one question for the Necromancer, so that left them with 4.[PC][Longmont Campaign/Campaign 1/PCs/stafl/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/necromancer/]

1: Tell us what killed you. He nods towards Bonogo.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/]

2: Where are the strongholds for the meat storage? Hidden in the walls, the guardhouses and underground.

3: How many are working on this plot against the city? Everyone operates in small groups so the number is not known, but Lira will finish the plot before she dies.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/lira/]

4: Where is the Shepherd?[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/shepherd/] Everywhere! In all the minds of the people.

Fifth question asked by the Necromancer: What is the plan and how will we know when it is complete?[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/necromancer/] There is no stopping it! They are gathering now and will soon erupt as something new, led by the Shepherd.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/shepherd/] All will die and be consumed. You will know at the break of dawn as the Shepherd rises from below.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/shepherd/]

After the ritual Professor Cinderbranch leaves the room, just as Draven closes and locks the door.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/professor_cinderbranch/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/draven/] Suddenly one of the walls opens up and 2 Elite Guards enter with a large and disgusting Sewer Meat Monster.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/sewer_meat_monster/] The disgusting monster moves to the center of the room and oozes goo in a 10 foot radius.

Draven begins to monologue about cooking and eating Stafl and Bonogo as he casts Fear on Bonogo.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/draven/] Luckily Stafl helps and forces the spell to miss.[PC][Longmont Campaign/Campaign 1/PCs/stafl/] One Elite Guard attacks Stafl and deals damage as well as poisoning him.[PC][Longmont Campaign/Campaign 1/PCs/stafl/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/elite_guard/] Stafl counters with a radiant burst and casts Sleep on Draven, who falls asleep.[PC][Longmont Campaign/Campaign 1/PCs/stafl/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/draven/] Bonogo sneak attacks the sleeping necromancer and deals massive damage resulting in a killing blow.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/necromancer/]

With his bonus attack Bonogo then strikes out at Elite Guard 2, but misses.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/elite_guard/] That guard then attacks and hits Bonogo, poisoning him as well.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/] Just as he is being poisoned, the Sewer Monster bites Bonogo, dealing more damage.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/] The other guard makes two attacks against Stafl, who then decides to run for the door.[PC][Longmont Campaign/Campaign 1/PCs/stafl/]

As soon as he is outside the door he yells for help then casts Sleep on the remaining enemies. Bonogo also runs for the door, but takes the opportunity to attack the sleeping guard, dealing massive damage and racking up another kill.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/]

After explaining to Cinderbranch what happened, the group finds the ritual room empty, a bad sign of what is to come.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/professor_cinderbranch/] With the help of the Mages the party can stock up on items before they head down the tunnel to see what awaits…
