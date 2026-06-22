---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 2
  campaign_id: longmont-c2
session:
  number: 23
  title: "Session 23 - Mireward Gate Battle"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 23
  last_updated_session: 23
  source_class: observed_session_recap
breadcrumb_semantics:
  purpose: "Machine-facing session memory index: inline labels mark source-aligned recap spans with durable retrieval value for agentic planning, live-play querying, hub routing, or proposed hub review."
  placement_rule: "Place tags immediately after the source-derived span that should route to that hub."
  selectivity_rule: "Do not tag every mere mention; tag table-significant actions, discoveries, relationship beats, location-state changes, reputation beats, collective decisions, affected groups, and unresolved durable entities."
  multi_hub_rule: "When one span has durable value for multiple hubs, append multiple tags to that same span."
  source_boundary: "This is a derivative retrieval/index artifact. The canonical source recap remains the prose source of truth and is not edited by this file."
  hub_status_rule: "Existing hubs route to corpus-relative hub folders or dossier files; durable subjects without a hub use NewHubCandidate with a proposed route."
  downstream_use: "Future agents should use this artifact to find relevant recap evidence and hub routes without rereading the whole recap when planning or enriching live-game interactions."
inline_tag_grammar:
  pc: "[PC][corpus-relative hub route]"
  npc: "[NPC][corpus-relative hub route]"
  location: "[Location][corpus-relative hub route]"
  party: "[Party][corpus-relative or proposed party hub route]"
  new_hub_candidate: "[NewHubCandidate][proposed corpus-relative route]"
entity_index:
  parties:
    questionable_company:
      slug: questionable_company
      display_name: "Questionable Company"
      hub_status: proposed
      proposed_route: "Longmont Campaign/Campaign 2/Parties/questionable_company/"
      default_members: [baergrom, bonogo, caelynn, ephanna, karsemine, stafl]
      aliases_in_recap:
        - "the group"
        - "the heroes"
        - "the team"
        - "the rest of the group"
      routing_policy: "Tag party spans only for collective decisions, travel beats, or end-of-session forks — not every generic group sentence."
  pcs:
    - slug: baergrom
      route: "Longmont Campaign/Campaign 2/PCs/baergrom/"
      aliases_in_recap: ["Baergrom", "Baergorm"]
    - slug: bonogo
      route: "Longmont Campaign/Campaign 2/PCs/bonogo/"
    - slug: caelynn
      route: "Longmont Campaign/Campaign 2/PCs/caelynn/"
    - slug: ephanna
      route: "Longmont Campaign/Campaign 2/PCs/ephanna/"
    - slug: karsemine
      route: "Longmont Campaign/Campaign 2/PCs/karsemine/"
      aliases_in_recap: ["Kasemine", "Karesmine"]
    - slug: stafl
      route: "Longmont Campaign/Campaign 2/PCs/stafl/"
  npcs:
    - slug: captain_lysandra_ironveil
      route: "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
      aliases_in_recap: ["Lysandra"]
    - slug: lysandro_ironveil
      route: "Elderwyld/Cities and Towns/Mireward/NPCs/lysandro_ironveil/"
      aliases_in_recap: ["Lysandro", "Lysandra's father"]
    - slug: orric_tane
      route: "Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/"
      aliases_in_recap: ["Orik Tane", "Orik", "Orric Tane", "the mayor"]
      note: "Route the recap spelling Orik Tane to the existing Orric Tane hub unless the corpus spelling is later corrected."
    - slug: brin_holloway
      route: "Elderwyld/Cities and Towns/Mireward/NPCs/brin_holloway/"
    - slug: thrin_branchborn
      route: "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/"
    - slug: ogonob
      route: "Longmont Campaign/Campaign 2/PCs/ephanna/"
      note: "Summoned entity controlled by Ephanna; route durable combat beats through Ephanna unless a dedicated companion hub is promoted."
  locations:
    - slug: mireward
      route: "Elderwyld/Cities and Towns/Mireward/"
      aliases_in_recap: ["Mireward", "Mireward Reach", "the town"]
    - slug: edge_of_the_world
      route: "Elderwyld/Cities and Towns/Edge of the World/"
      aliases_in_recap: ["Edge", "the town to the north"]
    - slug: mirathorn
      route: "Elderwyld/Cities and Towns/Mirathorn/"
    - slug: mireward_reach_road
      route: "Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md"
      aliases_in_recap: ["the road coming to the gate", "the Reach"]
  new_hub_candidates:
    - slug: mireward_north_gate_battle
      subject_type: event
      proposed_route: "Longmont Campaign/Campaign 2/Events/mireward_north_gate_battle.md"
      rationale: "Major combat set-piece where Edge refugees reach Mireward and the meat horde attacks the north gate."
    - slug: edge_refugee_column
      subject_type: faction
      proposed_route: "Longmont Campaign/Campaign 2/Factions/edge_refugee_column.md"
      rationale: "Named survivor group from Edge with Brin Holloway as visible leader; durable for aftermath, quarantine, and town politics."
    - slug: tripod_null_calf
      subject_type: creature
      proposed_route: "Elderwyld/Shephards Flock/Statblocks and Tokens/tripod_null_calf_statblock_cr5.md"
      rationale: "Large tripod meat monsters are a central threat in the north-gate combat."
    - slug: aberrant_meat_wing
      subject_type: creature
      proposed_route: "Elderwyld/Shephards Flock/Statblocks and Tokens/aberrant_meat_wing_statblock_cr1.md"
      rationale: "Flying meatwing swarm attacks the wall and applies a charm effect during the battle."
    - slug: corrupted_meat_golem
      subject_type: creature
      proposed_route: "Elderwyld/Shephards Flock/Statblocks and Tokens/corrupted_meat_golem_statblock_cr3.md"
      rationale: "Slow golem-like meat creature advances through Ephanna's Hunger of Hadar."
    - slug: fleshborn_hybrid
      subject_type: creature
      proposed_route: "Elderwyld/Shephards Flock/Statblocks and Tokens/fleshborn_hybrid_statblock_cr3.md"
      rationale: "Hybrid meat monsters are part of the attacking force."
    - slug: sewer_meat_creature
      subject_type: creature
      proposed_route: "Elderwyld/Shephards Flock/Statblocks and Tokens/sewer_meat_creature_statblock_cr3.md"
      rationale: "Sewer creatures from Mirathorn return as part of the horde."
unresolved_open_questions:
  - subject: edge_status
    question: "Edge sent a dire message and refugees fled; how much of the town still survives after the siege?"
    proposed_route: "Elderwyld/Cities and Towns/Edge of the World/"
  - subject: mireward_quarantine_and_refugees
    question: "The Edge survivors were routed around the wall toward the south gate and held outside until Mireward is secure; what happens to them after the battle?"
    proposed_route: "Elderwyld/Cities and Towns/Mireward/"
  - subject: mireward_battle_outcome
    question: "The recap ends mid-fight after Caelynn's lightning bolt; does Mireward Reach hold or get overrun?"
    proposed_route: "Longmont Campaign/Campaign 2/Events/mireward_north_gate_battle.md"
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 6
    locations: 4
    new_hub_candidates: 7
  inline_tags:
    PC: 0
    NPC: 0
    Location: 0
    Party: 0
    NewHubCandidate: 0
  unresolved_open_questions: 3
---

### Session 23 (normalized) — frontmatter seed only
