---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Finishing the Job.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 1
  campaign_id: longmont-c1
session:
  number: 2
  title: "Session 2 - Finishing the Job"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 2
  last_updated_session: 2
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
    party_merchant_guards:
      slug: party_merchant_guards
      display_name: "Merchant-guard fellowship (Campaign 1)"
      hub_status: proposed
      proposed_route: "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
      default_members: [baergrom, bonogo, caelynn, ephanna, karsemine, stafl]
      aliases_in_recap:
        - "the group"
        - "the gang"
        - "they"
      routing_policy: "Use the Party breadcrumb when the span has durable retrieval value for the party as a collective actor."
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
    - slug: stonebridge
      proposed_route: "Longmont Campaign/Campaign 1/Locations/stonebridge/"
      rationale: "Town referenced in Session 2 hooks."
    - slug: rivers_edge_pub
      proposed_route: "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/"
      rationale: "Grishna's tavern."
    - slug: wizards_tower_brewing_company
      proposed_route: "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
      rationale: "Brewery / basement crawl site."
    - slug: shatter_mages_tower
      proposed_route: "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/"
      rationale: "Tower thread; Session 2 teases more to explore."
  new_hub_candidates:
    - slug: grishna
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/grishna/"
    - slug: glowkindle
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
    - slug: magma_spider
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
    - slug: giant_centipede_well
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/"
unresolved_open_questions:
  - "More under the Wizard's Tower? (teased only; answering it needs follow-up context beyond this recap.)"
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 0
    locations: 4
    new_hub_candidates: 4
  inline_tags:
    PC: 0
    NPC: 4
    Location: 5
    Party: 2
    NewHubCandidate: 2
  unresolved_open_questions: 1
---
### Session 2 : Finishing the Job

The gang survived, they kinda even thrived.[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] Compared to the rats, the Giant Flaming Spider,[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/magma_spider/] the Giant Centipede that crawled out of the well,[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/giant_centipede_well/] and the rat that absolutely was NOT about to mutate were no big deal.

After clearing the rest of the wizards tower basement[Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/] they came away richly rewarded. Finding a sack of gems, some mystery potions on corpses in the well, and perhaps most importantly bashing down a wall to reveal a room full of healing potions and alchemical tools and ingredients of and ancient and incredible design.[Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/] They unfortunately haven't the first clue how to use them, but they are cool!

Since this room was not part of the original contract, and really neither was the rest of this god forsaken place, they negotiated with Glowkindle[NPC][Longmont Campaign/Campaign 1/NPCs/glowkindle/] for the right to stash gear in the hidden alchemy room. It's not much but it's a start.

After making pretty good money, 25 gp each, a bit of loot, and learning a lot about the dangers of clearing rats out of basements, the group[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] decided to stick together and see where the winds take them.

Will they ask Glowkindle[NPC][Longmont Campaign/Campaign 1/NPCs/glowkindle/] for more work?Will they had back to Stonebridge[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] to say hi to Grishna[NPC][Longmont Campaign/Campaign 1/NPCs/grishna/] at the River's Edge Pub[Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/]?Will they follow up on the errant thought of what if there is more to the Wizard's Tower[Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/]?Stay tuned!
