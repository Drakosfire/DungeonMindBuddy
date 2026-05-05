---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 1/Session Recaps/Session 1 - Recap 3-27-24.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 1
  campaign_id: longmont-c1
session:
  number: 1
  title: "Session 1 - Recap 3/27/24"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 1
  last_updated_session: 1
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
      display_name: "Merchant-guard fellowship (Session 1)"
      hub_status: proposed
      proposed_route: "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
      default_members: [baergrom, bonogo, caelynn, ephanna, karsemine, stafl]
      aliases_in_recap:
        - "the group"
        - "the team"
        - "mish mash of travelers"
        - "teammates"
      routing_policy: "Use the Party breadcrumb only when the span has durable retrieval value for the party as a collective actor, witness, decision-maker, reputation target, or affected group. Do not tag every generic group sentence. If specific PCs are acting separately, tag those PCs instead."
  pcs:
    - slug: baergrom
      route: "Longmont Campaign/Campaign 1/PCs/baergrom/"
      inline_tag_count: 0
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
      rationale: "Starting town; no location hub in corpus yet."
    - slug: rivers_edge_pub
      proposed_route: "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/"
      rationale: "Grishna's tavern in Stonebridge."
    - slug: wizards_tower_brewing_company
      proposed_route: "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
      rationale: "Glowkindle's brewery and rat-clearing site."
    - slug: shatter_mages_tower
      proposed_route: "Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/"
      rationale: "Referenced as containing the magma spider threat."
  new_hub_candidates:
    - slug: grishna
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/grishna/"
      rationale: "Half-orc pubkeeper; no C1 NPC hub in corpus."
    - slug: glowkindle
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/glowkindle/"
      rationale: "Brewer and contract giver; no C1 NPC hub in corpus."
    - slug: magma_spider
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
      rationale: "Resident of the shatter mages tower; flaming magma-infused spider monstrosity."
unresolved_open_questions: []
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 0
    locations: 4
    new_hub_candidates: 3
  inline_tags:
    PC: 9
    NPC: 6
    Location: 11
    Party: 6
    NewHubCandidate: 1
  unresolved_open_questions: 0
---
### Session 1 Recap 3/27/24

After traveling together for some time together as merchant guards, our mish mash of travelers;[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/]  Karsemine the Tiefling Ranger,[PC][Longmont Campaign/Campaign 1/PCs/karsemine/] Stafl the 'Human' Bard,[PC][Longmont Campaign/Campaign 1/PCs/stafl/] Caelynn the Half Elf Sorcerer,[PC][Longmont Campaign/Campaign 1/PCs/caelynn/] Ephanna the Kenku Warlock,[PC][Longmont Campaign/Campaign 1/PCs/ephanna/] Bonogo the Bugbear Rogue,[PC][Longmont Campaign/Campaign 1/PCs/bonogo/] and Baergrom the Dwarf Fighter,[PC][Longmont Campaign/Campaign 1/PCs/baergrom/] found themselves outside the town of Stonebridge.[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/]

The town of Stonebridge[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] is known for very few things, in fact Stonebridge[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] is hardly known. It has the Stonebridge over the river [River name], it's tavern  The River's Edge Pub[Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/] run by Grishna the Half-orc,[NPC][Longmont Campaign/Campaign 1/NPCs/grishna/] and that's about it. It did have a job board, and most importantly the local brewer Glowkindle[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][NPC][Longmont Campaign/Campaign 1/NPCs/glowkindle/] had posted a help request on the jobs board and spread word all around town of his need of a band of mercenaries to help clean up some rats.[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/]

While doing some drinking at the Riv'ers Edge Pub[Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/] to wash away the road, Grishna[NPC][Longmont Campaign/Campaign 1/NPCs/grishna/] was quick to share that Glowkindle[NPC][Longmont Campaign/Campaign 1/NPCs/glowkindle/] had been through, where the The Wizard's Tower Brewing Co[Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/] was located. Up river, west at the big rock, walk till you see it. Bonogo,[PC][Longmont Campaign/Campaign 1/PCs/bonogo/] having very little awareness or care for the cost of things, and greatly enjoying the beer, bought a Firkin of ale for two gold. He quite enjoyed the hike to the brewery.[Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/]

Grishna[NPC][Longmont Campaign/Campaign 1/NPCs/grishna/] was true to her word, the directions were sound. There was a clear trail along the river to an enormous boulder.  As the group[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] approached it resolved into what must have been the foot of a once enormous statue. Or a mad sculptures dedication to someone's foot, probably the  former but who really knows with art anyway.

Another few hours walk away from the river along the trail led the group[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] to the Wizard's Tower Brewing Company.[Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/]  Bustling with activity, and smelling of brewing, the fine tap room lit by magical crystals, was empty except for the troupe of gnomes busily brewing.

Within they met Glowkindle[NPC][Longmont Campaign/Campaign 1/NPCs/glowkindle/] who told them, a bit about the issue at hand. Giant rats had assaulted his excavation crew after they broke through a wall expanding the fermentation cellar. For a healthy prize of 25 gold pieces each, the team[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] agreed to clear out the rats.  Which was significantly harder than expected, led to multiple folk going down, a mysterious cat owl being tossed into the room to help, a lot of blood from rats and teammates, and many, many, many health potions being downed.

A fine first combat to bring the team[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] together!

Finally, free to explore the team[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] found a beautifully tiled hallway, a trapped mosaic on the ground, a room full of broken alchemical tools. As Karsemine[PC][Longmont Campaign/Campaign 1/PCs/karsemine/] wisely searched the room, eventually looking up, she made eye contact with another resident of the shatter mages tower.[Location][Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/] Some kind of flaming magma infused spider monstrosity.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/magma_spider/]
