---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 2
  campaign_id: longmont-c2
session:
  number: 22
  title: "Session 22 - Mireward Road and Lysandro"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 22
  last_updated_session: 22
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
        - "the rest of the group"
        - "the majority"
      routing_policy: "Tag party spans only for collective decisions, travel beats, or end-of-session forks — not every generic group sentence."
  pcs:
    - slug: baergrom
      route: "Longmont Campaign/Campaign 2/PCs/baergrom/"
      inline_tag_count: 0
      note: "Session roster member; not named directly in this recap prose."
    - slug: bonogo
      route: "Longmont Campaign/Campaign 2/PCs/bonogo/"
    - slug: caelynn
      route: "Longmont Campaign/Campaign 2/PCs/caelynn/"
    - slug: ephanna
      route: "Longmont Campaign/Campaign 2/PCs/ephanna/"
    - slug: karsemine
      route: "Longmont Campaign/Campaign 2/PCs/karsemine/"
      aliases_in_recap: ["Karesmine"]
    - slug: stafl
      route: "Longmont Campaign/Campaign 2/PCs/stafl/"
  npcs:
    - slug: captain_lysandra_ironveil
      route: "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
    - slug: sara_mirathorn_operator
      route: "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/"
      note: "Frank is Sara's twin co-operator; route Frank/Mirathorn handset beats here unless a dedicated Frank hub is promoted."
    - slug: sheriff_roderic_marr
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/"
    - slug: thrin_branchborn
      route: "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/"
  locations:
    - slug: mirathorn
      route: "Elderwyld/Cities and Towns/Mirathorn/"
    - slug: mossford
      route: "Elderwyld/Cities and Towns/Mossford/"
  new_hub_candidates:
    - slug: young_drake_nest_hill
      subject_type: location
      proposed_route: "Elderwyld/Unknown Sites/Young Drake Nest Hill/"
      rationale: "Major session set-piece: iridescent young drake nest bowl with elder drakes and loot."
    - slug: edge_of_the_world
      subject_type: location
      proposed_route: "Elderwyld/Cities and Towns/Edge of the World/"
      rationale: "Sheriff rumor destination for cultist music conversion; named northbound town."
    - slug: mireward
      subject_type: location
      proposed_route: "Elderwyld/Cities and Towns/Mireward/"
      rationale: "Named next town north on the road (~5 days out per Lysandra)."
    - slug: boots_of_crowing_wings
      subject_type: item
      proposed_route: "Longmont Campaign/Campaign 2/Plot Artifacts/boots_of_crowing_wings.md"
      rationale: "Bonogo loot from drake nest human remains; mechanical item acquired this session."
    - slug: metal_slab_with_buttons
      subject_type: item
      proposed_route: "Longmont Campaign/Campaign 2/Plot Artifacts/metal_slab_with_buttons.md"
      rationale: "Unidentified tech loot from drake nest; table-significant discovery."
unresolved_open_questions:
  - subject: mirathorn_festival_resumed
    question: "Mirathorn resumed the Festival; Frank hung up; Lysandra cannot get through — is the city compromised or merely distracted?"
    proposed_route: "Elderwyld/Cities and Towns/Mirathorn/"
  - subject: swamp_vs_mirathorn_fork
    question: "Party agreed to press on to the swamp rather than turn back — S22 opening pressure."
    proposed_route: "Longmont Campaign/Campaign 2/Parties/questionable_company/"
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 4
    locations: 2
    new_hub_candidates: 5
  inline_tags:
    PC: 0
    NPC: 0
    Location: 0
    Party: 0
    NewHubCandidate: 0
  unresolved_open_questions: 2
---

### Session 22 (normalized) — frontmatter seed only