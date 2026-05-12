---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md"
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
    PC: 11
    NPC: 7
    Location: 12
    Party: 11
    NewHubCandidate: 0
  unresolved_open_questions: 0
---
# Session 1 Recap

After traveling together for some time together as merchant guards, our mish mash of travelers;  Karsemine the Tiefling Ranger, Stafl the 'Human' Bard, Caelynn the Half Elf Sorcerer, Ephanna the Kenku Warlock, Bonogo the Bugbear Rogue, and Baergrom the Dwarf Fighter, found themselves outside the town of Stonebridge.[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/][PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/]

The town of Stonebridge is known for very few things, in fact Stonebridge is hardly known.[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/] It has the Stonebridge over the river [River name], it's tavern  The River's Edge Pub run by Grishna the Half-orc, and that's about it.[Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][NPC][Longmont Campaign/Campaign 1/NPCs/grishna/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][NPC][Longmont Campaign/Campaign 1/NPCs/glowkindle/] It did have a job board, and most importantly the local brewer Glowkindle had posted a help request on the jobs board and spread word all around town of his need of a band of mercenaries to help clean up some rats.[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][NPC][Longmont Campaign/Campaign 1/NPCs/glowkindle/][Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/]

While doing some drinking at the Riv'ers Edge Pub to wash away the road, Grishna was quick to share that Glowkindle had been through, where the The Wizard's Tower Brewing Co was located.[Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][NPC][Longmont Campaign/Campaign 1/NPCs/grishna/][NPC][Longmont Campaign/Campaign 1/NPCs/glowkindle/][Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/] Up river, west at the big rock, walk till you see it.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/] Bonogo, having very little awareness or care for the cost of things, and greatly enjoying the beer, bought a Firkin of ale for two gold.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/] He quite enjoyed the hike to the brewery.[Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/]

Grishna was true to her word, the directions were sound.[NPC][Longmont Campaign/Campaign 1/NPCs/grishna/][Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] There was a clear trail along the river to an enormous boulder.[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/]  As the group approached it resolved into what must have been the foot of a once enormous statue.[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] Or a mad sculptures dedication to someone's foot, probably the  former but who really knows with art anyway.

Another few hours walk away from the river along the trail led the group to the Wizard's Tower Brewing Company.[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/][Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/]  Bustling with activity, and smelling of brewing, the fine tap room lit by magical crystals, was empty except for the troupe of gnomes busily brewing.

Within they met Glowkindle who told them, a bit about the issue at hand.[NPC][Longmont Campaign/Campaign 1/NPCs/glowkindle/][Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] Giant rats had assaulted his excavation crew after they broke through a wall expanding the fermentation cellar.[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/] For a healthy prize of 25 gold pieces each, the team agreed to clear out the rats.[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/]  Which was significantly harder than expected, led to multiple folk going down, a mysterious cat owl being tossed into the room to help, a lot of blood from rats and teammates, and many, many, many health potions being downed.

A fine first combat to bring the team together![Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/]

Finally, free to explore the team found a beautifully tiled hallway, a trapped mosaic on the ground, a room full of broken alchemical tools.[Party][Longmont Campaign/Campaign 1/Parties/party_merchant_guards/][PC][Longmont Campaign/Campaign 1/PCs/karsemine/] As Karsemine wisely searched the room, eventually looking up, she made eye contact with another resident of the shatter mages tower.[PC][Longmont Campaign/Campaign 1/PCs/karsemine/][Location][Longmont Campaign/Campaign 1/Locations/shatter_mages_tower/] Some kind of flaming magma infused spider monstrosity.