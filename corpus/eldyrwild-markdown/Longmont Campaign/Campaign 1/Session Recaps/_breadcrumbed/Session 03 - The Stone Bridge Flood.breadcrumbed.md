---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 03 - The Stone Bridge Flood.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 1
  campaign_id: longmont-c1
session:
  number: 3
  title: "Session 3 - The Stone Bridge Flood"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 3
  last_updated_session: 3
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
        - "they"
      routing_policy: "Use the Party breadcrumb only when the span is about the party as a durable collective actor; prefer PC tags for named hero beats."
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
      rationale: "Stone Bridge town; flood and rescue set-piece."
    - slug: rivers_edge_pub
      proposed_route: "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/"
      rationale: "Grishna's tavern during the storm."
    - slug: wizards_tower_brewing_company
      proposed_route: "Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/"
      rationale: "Bardic retelling beat ties back to the brewery crawl."
    - slug: mirathorn
      proposed_route: "Longmont Campaign/Campaign 1/Locations/mirathorn/"
      rationale: "Festival-city hook named in closing beats; table-facing route placeholder."
  new_hub_candidates:
    - slug: pippa
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/pippa/"
    - slug: bubbles_the_float_goat
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/"
    - slug: kirfan
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/kirfan/"
    - slug: grishna
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/grishna/"
unresolved_open_questions:
  - "Upriver town name (called out in recap as TBD)."
  - "Mysterious artifact festival hook — table follow-up beyond this recap."
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 0
    locations: 4
    new_hub_candidates: 4
  inline_tags:
    PC: 87
    NPC: 0
    Location: 45
    Party: 0
    NewHubCandidate: 69
  unresolved_open_questions: 2
---
# Session 3 Recap

Adventure hook, hear about a mysterious artifact while celebrating.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/]
Unseasonable torrential rains floods wherever the players are, non combat problem solving.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/] They have to keep themselves alive, and save townsfolk.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/]

Big beats :[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/]

Rode with Pippa and fell in love with Bubbles.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/]

Helped Kirfan pull up debris from the broken structure from upriver.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/kirfan/] (River and Upriver town need a name)[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/grishna/]

Got comp’d beer and board from Grishna.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/grishna/]

Stafl wrote and played an incredible song that woo’d the town in the retelling of the Wizard’s Tower Brewery adventure.[PC][Longmont Campaign/Campaign 1/PCs/stafl/][Location][Longmont Campaign/Campaign 1/Locations/wizards_tower_brewing_company/]

Horrible storm kicks up and gets worse.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/]

Players heard Pippa yelling and immediately ran out to help find Bubbles.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/]

Ephanna uses mage hand to lasso Bubbles on the rock.[PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/] Bubbles is too panicked and bites the mage hand.[PC][Longmont Campaign/Campaign 1/PCs/caelynn/]

Caelynn uses ice to freeze the base of the rock and make a platform.[PC][Longmont Campaign/Campaign 1/PCs/caelynn/]

Bonogo dives in the water, Baergrom loses the rope.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/]

Bonogo flows downstream and has a wonderful zen underwater adventure.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/]

Stafl gathers town support, nets are dropped across the bridge flow ways.[PC][Longmont Campaign/Campaign 1/PCs/stafl/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/]

Ephanna’s mage hand succeeds the second time and lassos Bubbles, lead her to Ephanna.[PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/]

Karsemine uses Zephyr strike,[PC][Longmont Campaign/Campaign 1/PCs/karsemine/]

Ready for some rest, ready to not be covered in the sweat and ichor of the day, Caelynn, Karsemine, Stafl, Baergrom, and Ephanna accepted the offer of a ride to StoneBridge with Pippa.[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/] Pippa a bright and talkative Gnome obsessed with crafting and understanding beer, hitched up Bubbles the Float Goat to her wagon full of kegs and led the crew to a dock and barge on the river.[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/grishna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/stafl/] Along the way down river, they encountered an elderly fisherman, whose net was stuck.[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/grishna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/stafl/] Without missing a beat Bonogo out of selflessness and hopes for a giant fish to eat, dove into the water to find the damned net didn’t have a fish, stupid useless net.[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/grishna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/stafl/] With some trial and error and stradling of boats Stafl and Baergrom I think pulled the net to surface to see it looked to be the corner beams of a roof.[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/grishna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/stafl/]

Once at StoneBridge and unloading beer, it became clear a storm was coming.[Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/grishna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/stafl/] Hitching up Bubbles and the barge, into the River’s Edge Pub for a welcome round of beers and some bragging to Grishna about their adventures.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/] Inside was the evening crew, Grishna, patrons, and another bard![NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/] Who Stafl immediately joined in a jam with that undoubtedly demonstrated his superior song craft and bardic talents.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/] After some excellent drinks and music, Pippa realizes the loud drumming isn’t just the bard, but a torrent of rain on the roof excuses herself to check on Bubbles.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/] Gone for a few moments, during a pause in the retelling of the day’s events, weeping is heard from another table, followed by a piercing yell in between cascades of rain off the roof.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/]

“BUBBLES!”[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/]

Dropping everything and rushing outside, you found Pippa, soaked and panicked.[Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Gripping onto the front of the pub holding on in rushing water up to her waste.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] “Help![NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] I can’t find Pippa” she babbles about a broken lead.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Rapidly searching around Bubbles is found wildly bleating on a rock in the river.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Out on a rickety dock, shaking in the flood and downpour, the river frothing, rapids crashing all around as it wildly rushed.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/]  a lasso was made and handed to a mage hand Ephanna created.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Stafl runs for help, and gathers townfolk to set nets across the river.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Bonogo and Baergrom prepare for Bonogo to dive in.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Caelynn desperately fires ice bolts to freeze a platform around Bubble’s rock.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Stafl began banging on doors and assisting townfolk escape the flood and gather at the pub on high ground.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/]
Sending the mage hand and rope out to Bubbles, the Float Goat panics and bites, destroying the mage hand and dropping the rope into the water.[NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][PC][Longmont Campaign/Campaign 1/PCs/bonogo/][PC][Longmont Campaign/Campaign 1/PCs/baergrom/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Desperate to save (maybe to eat, raw?[PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Or maybe in a curry?[PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Thoroughly fermented) Bonogo dives into the river with full trust in Baergrom to hold the rope, which is immediately torn out of Baergrom’s hand.[PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Unprepared for the speed with which the river carries Bonogo away, the rope and Bonogo are gone.[PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] The only remenant, the end of the rope whipping across the top of the river, vanishing out of sight.[PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/]

In the face of a rapidly deteriorating situation, Karsemine cast Zephyr strike and ran down the bank, shooting arrows at wear Bonogo probably was.[PC][Longmont Campaign/Campaign 1/PCs/karsemine/][PC][Longmont Campaign/Campaign 1/PCs/stafl/][PC][Longmont Campaign/Campaign 1/PCs/caelynn/][PC][Longmont Campaign/Campaign 1/PCs/ephanna/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/] Stafl and Caelynn cut loose a dinghy and let the river take them after Bonogo, with only a net with light cast on it and hope.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][Location][Longmont Campaign/Campaign 1/Locations/mirathorn/] Ephanna and the mage hand coaxed Bubbles to the lasso and were able to get her to the dock across the ice path and rushing river.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][Location][Longmont Campaign/Campaign 1/Locations/mirathorn/] Where Ephanna hopped on Bubbles back and followed after the runaway boats.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][Location][Longmont Campaign/Campaign 1/Locations/mirathorn/]

Bonogo was rescued, the wet adventurers headed to the Pub to find a damp, but generally relieved, safe, and drying town.[PC][Longmont Campaign/Campaign 1/PCs/bonogo/][Location][Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/][Location][Longmont Campaign/Campaign 1/Locations/stonebridge/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/][NewHubCandidate][Longmont Campaign/Campaign 1/NPCs/pippa/][Location][Longmont Campaign/Campaign 1/Locations/mirathorn/] Collapsing to sleep, they woke up the next day with the most important question of all. What now? Sure they were heroes of Stone Bridge, and definitely the saviors of Bubbles the Float Goat, but so what? What about that city Pippa was talking about, where they were having a festival? Mirathorn, that might be interesting… Long way on foot, but not that far. Maybe a bit more than a week. Not much to do around Stone Bridge unless you are into rebuilding and staying still.