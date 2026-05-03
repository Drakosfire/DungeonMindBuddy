---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
title: "Session 20 - Recap"
document_class: play
canon_layer: campaign
campaign_id: longmont-c2
temporal_scope: session_specific
session: 20
origin_session: 20
last_updated_session: 20
source_class: observed_session_recap
campaign:
  title: "Longmont Campaign"
  campaign_number: 2
  campaign_id: longmont-c2
session_metadata:
  number: 20
  title: "Session 20 - Recap"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 20
  last_updated_session: 20
  source_class: observed_session_recap
breadcrumb_semantics:
  purpose: "Inline labels mark the smallest readable spans with durable retrieval value for an existing hub or proposed hub."
  placement_rule: "Place tags immediately after the span that should route to that hub."
  selectivity_rule: "Do not tag every mere mention; tag table-significant actions, discoveries, relationship beats, location-state changes, reputation beats, collective decisions, affected groups, and unresolved durable entities."
  multi_hub_rule: "When one span has durable value for multiple hubs, append multiple tags to that same span."
  source_boundary: "This is a derivative manual-label artifact. The canonical source recap is not edited by this file."
  hub_status_rule: "Existing hubs route to corpus-relative hub folders or dossier files; durable subjects without a hub use NewHubCandidate with a proposed route."
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
      default_members:
        - baergrom
        - bonogo
        - caelynn
        - ephanna
        - karsemine
        - stafl
      aliases_in_recap:
        - "Questionable Company"
        - "the heroes"
        - "the group"
        - "the team"
        - "the rest of the team"
        - "the rest of the group"
        - "the others"
      routing_policy: "Use the Party breadcrumb only when the span has durable retrieval value for the party as a collective actor, witness, decision-maker, reputation target, or affected group. Do not tag every generic group/heroes/team sentence merely because the party is probably present. If specific PCs are acting separately, tag those PCs instead. If any PC is explicitly elsewhere, do not infer all-six participation from group language unless the sentence clearly says so."
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
      aliases_in_recap:
        - "Karesmine"
    - slug: stafl
      route: "Longmont Campaign/Campaign 2/PCs/stafl/"
  npcs:
    - slug: captain_lysandra_ironveil
      route: "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
    - slug: marla_brambleback
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/"
    - slug: sara_mirathorn_operator
      route: "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/"
    - slug: sheriff_roderic_marr
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/"
    - slug: stacey_brambleback
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/"
    - slug: stuart
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/stuart/"
    - slug: thrin_branchborn
      route: "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/"
  locations:
    - slug: mirathorn
      route: "Elderwyld/Cities and Towns/Mirathorn/"
    - slug: mossford
      route: "Elderwyld/Cities and Towns/Mossford/"
    - slug: migrating_forest
      route: "Elderwyld/Migrating Forest/"
    - slug: stormspire_academy
      route: "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/"
  new_hub_candidates:
    - slug: half_burned_warehouse
      subject_type: location
      proposed_route: "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md"
      rationale: "Repeated, specific Mossford child-gang scene location; not present in Mossford dossier collection."
    - slug: professor_merril_tealeaf
      subject_type: npc
      proposed_route: "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/"
      rationale: "Recurring Stormspire/Tealeaf contact for Caelynn; no dedicated hub found."
    - slug: voices_tower_blueprint
      subject_type: location
      proposed_route: "Elderwyld/Unknown Sites/Voices Tower/"
      rationale: "Lysandra draws a top-down tower blueprint under cult-like influence; no existing exact hub found."
unresolved_open_questions:
  - subject: half_burned_warehouse
    question: "Should the half-burned warehouse be promoted as a Mossford location dossier, or folded into an existing Mossford district dossier such as Dense Worker Housing?"
    proposed_route: "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md"
  - subject: professor_merril_tealeaf
    question: "Should Professor Tealeaf receive a dedicated NPC hub under Stormspire Academy, or remain surfaced through Caelynn/Sara timelines and Stormspire prose?"
    proposed_route: "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/"
  - subject: voices_tower_blueprint
    question: "What canonical location route should own Lysandra's tower blueprint and voices clue once the site is identified?"
    proposed_route: "Elderwyld/Unknown Sites/Voices Tower/"
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 7
    locations: 4
    new_hub_candidates: 3
  inline_tags:
    PC: 53
    NPC: 47
    Location: 19
    Party: 13
    NewHubCandidate: 8
  unresolved_open_questions: 3
---

# Session 20 Recap

Back out near the edge of the forest [Location][Elderwyld/Migrating Forest/] Ephanna [PC][Longmont Campaign/Campaign 2/PCs/ephanna/], Karesmine [PC][Longmont Campaign/Campaign 2/PCs/karsemine/], Caelynn [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] and Thrin [NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/] continue to battle the swarm of red gnats. Thrin, desperate to see something go in their favor, takes two more shots with his bow [NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/]. The first misses, but the second does enough damage to knock a group of insects out of the swarm.Then the swarm turns and envelopes Caelynn [PC][Longmont Campaign/Campaign 2/PCs/caelynn/], the rest of the team can only see her dim shadow under all the flying insects. Thanks to her high constitution, she is able to withstand the stinging and only take minor damage [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]. 

Ephanna unleashes two Eldritch Blasts, the first missing and the second one dealing enough damage to knock another cluster out of the swarm [PC][Longmont Campaign/Campaign 2/PCs/ephanna/]. They Misty Step away and add some temporary health to themselves [PC][Longmont Campaign/Campaign 2/PCs/ephanna/]. Now that the swarm is around Caelynn [PC][Longmont Campaign/Campaign 2/PCs/caelynn/], Karsemine is able to use her scimitar and short sword for a series of attacks, landing 4 hits on the swarm [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]. She also uses Zephyr Strike to increase her movement and dash away. Finally Caelynn is able to duck out of the swarm, then facing them, casts a powerful Thunderwave spell, splitting the swarm in two and pushing it back 10 feet [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]. As Thrin and Caelynn move back [NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/] [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] the swarm finally gives up and heads back into the forest [Location][Elderwyld/Migrating Forest/]. The team decides they have enough “testing” and should head back to tell the others what they discovered [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/].

Back in town [Location][Elderwyld/Cities and Towns/Mossford/], Bonogo is being guided by Stuart down an alley to a half burned building [PC][Longmont Campaign/Campaign 2/PCs/bonogo/] [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/] [NewHubCandidate][Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md]. According to Stuart [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/] this is where they will find Stacey [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]. As soon as they step inside the large warehouse [NewHubCandidate][Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md] they find a group of children formed into two groups with what appear to be the leaders arguing in the middle. One of them is Stacey, the bugbear girl they are looking for [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]. She is in a heated argument with the other children who are accusing her of continuing to be too bossy. Bonogo whispers into Stuart's ear, “you know what to do” then sends him over [PC][Longmont Campaign/Campaign 2/PCs/bonogo/] [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]. Stacey immediately gets upset at seeing Stuart and tells him that he can’t play with them [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/] [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/], but Stuart is undeterred [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]. He sticks his hand out and demands his gold back, convinced that she is the one that stole it. Stuart takes a quick glance at Bonogo before he pulls out the dart and threatens her with it [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/] [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]. Alarmed, she yells at Stuart and then throws her gold pouch at him before storming out the door [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]. 

Stuart is so happy with the outcome that he runs out the door, racing off to tell his mom the good news [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]. The other kids now ask Bonogo to play with them instead [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]. He agrees to play hide and seek as long as the kids hide first. He counts to 20 then leaves the building without making a sound. He is intent on following Stacey and catches up to her in the next alley [PC][Longmont Campaign/Campaign 2/PCs/bonogo/] [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]. After seeing no one else around, he quickly grabs her and puts a knife to her throat [PC][Longmont Campaign/Campaign 2/PCs/bonogo/] [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]. He tells her to stop bullying Stuart or he will come back [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/], then dashes into the shadows. Clearly shaken, Stacey runs home [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]. Bonogo makes his way back to the group out in the field [PC][Longmont Campaign/Campaign 2/PCs/bonogo/].

As the group approaches the preparations happening in the field [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] [Location][Elderwyld/Cities and Towns/Mossford/], they find Stafl singing and directing the workers from a makeshift throne of barrels on the back of a wagon [PC][Longmont Campaign/Campaign 2/PCs/stafl/]. Ephanna, Karesmine and Caelynn relay their findings from their tests [PC][Longmont Campaign/Campaign 2/PCs/ephanna/] [PC][Longmont Campaign/Campaign 2/PCs/karsemine/] [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]: do not attack the trees directly, but the forest should respond to changes on the ground [Location][Elderwyld/Migrating Forest/]. Bonogo takes up a supervisor role and is observing the work [PC][Longmont Campaign/Campaign 2/PCs/bonogo/] when he hears footsteps quickly approaching behind him. He is able to dodge a slap from a furious Bugbear woman [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/]. Even with the missed slap, she gets up into Bonogo’s face [PC][Longmont Campaign/Campaign 2/PCs/bonogo/] and begins to berate him for encouraging Stuart to harass her daughter, causing many of the workers to stop and watch. Bonogo tries to shift the situation and asks why she is not helping with the ditches and should get to work instead [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]. This, of course, only makes her more furious. 

She stands up to her full Bugbear height and begins to scream at him. She finds just the right words to cut deep: he smells like a circus animal. Stafl takes a look around at the crowd to gauge their reactions [PC][Longmont Campaign/Campaign 2/PCs/stafl/]. A farmer whispers to him that Stafl better step in and help [PC][Longmont Campaign/Campaign 2/PCs/stafl/] because Marla is not someone to mess with [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/]. They reveal that she is in charge of the workers in town and she means business. Bonogo continues to escalate the situation, telling Marla he sees where her daughter gets her attitude from [PC][Longmont Campaign/Campaign 2/PCs/bonogo/] [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/]. Marla then grapples Bonogo and is about to do much worse [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/] [PC][Longmont Campaign/Campaign 2/PCs/bonogo/] when Caelynn comes to the rescue [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]. Using her bracelet she is able to diffuse the aggression and get everyone back to work, united against the approaching forest [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [Location][Elderwyld/Migrating Forest/]. The rest of the Questionable Company decide to take a short rest as their final preparation [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/].

Questionable Company, along with the townsfolk, watch as the forest comes within range of their plan [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] [Location][Elderwyld/Migrating Forest/]. As the forest finally reaches the fortifications, the fires are lit in the ditches [Location][Elderwyld/Migrating Forest/] [Location][Elderwyld/Cities and Towns/Mossford/]. Immediately they can all see the trees pull back and then start to turn to the east, away from the town [Location][Elderwyld/Migrating Forest/] [Location][Elderwyld/Cities and Towns/Mossford/]. Cheers go up along the ditches and into town [Location][Elderwyld/Cities and Towns/Mossford/]. The mayor and sheriff congratulate the heroes and thank them again for all their help [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/] [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]. Marla approaches Caelynn and asks her how she should deal with Bonogo [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/] [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [PC][Longmont Campaign/Campaign 2/PCs/bonogo/], but Ephanna quickly intervenes [PC][Longmont Campaign/Campaign 2/PCs/ephanna/], letting her, and the town, know that the Questionable Company is leaving town to continue their journey [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] [Location][Elderwyld/Cities and Towns/Mossford/]. And now that the danger has passed Caelynn asks the mayor about Lysandra [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/], but finds out that they have never heard of her [Location][Elderwyld/Cities and Towns/Mossford/].

Caelynn quickly pulls out the “rockie-talkie” and attempts to call Lysandra [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]. After a brief pause she is connected with the familiar voice of Sara, one half of the operators in Mirathorn [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] [Location][Elderwyld/Cities and Towns/Mirathorn/]. Caelynn relays her request and Sara calls Lysandra [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]. She tells Caelynn that all she could hear was mumbling about the forest leaving and that something strange happened to the time [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [Location][Elderwyld/Migrating Forest/]. Sara then connects Caelynn directly to Lysandra [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] who is relieved and overjoyed that the group is ok and that they took care of the forest [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] [Location][Elderwyld/Migrating Forest/]. Caelynn wants to know if she is ok and where she is [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]. Lysandra tells her that she can’t remember much after the group left, only that she decided to go around the forest and she could smell meat while trying to sleep [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] [Location][Elderwyld/Migrating Forest/]. She is exhausted and disoriented. Caelynn tells her to stop where she is and make a camp and rest, Karesmine will lead the team to her [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [PC][Longmont Campaign/Campaign 2/PCs/karsemine/] [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/].

Using her extensive tracking skills, Karesmine is able to estimate the distance and direction that Lysandra may have traveled [PC][Longmont Campaign/Campaign 2/PCs/karsemine/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]. The group sets off from the town [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] [Location][Elderwyld/Cities and Towns/Mossford/], Ephanna keeping a close eye on Thrin [PC][Longmont Campaign/Campaign 2/PCs/ephanna/] [NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/]. Thirty minutes later they come across an unusual sight: a wagon partly unloaded and horses wandering around a stack of crates. Caelynn approaches the makeshift shelter and hears mumbling from inside [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]. She finds Lysandra drawing in the dirt [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]. She says it is a tower [NewHubCandidate][Elderwyld/Unknown Sites/Voices Tower/] where the voices are coming from [NewHubCandidate][Elderwyld/Unknown Sites/Voices Tower/] and she knows where it is. The first thing Caelynn notices about Lysandra is that her eyes are shimmery, just like the members of the cult [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]. She quickly begins to make the antidote from the tea in her bag [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]. While the tea is being prepared, Caelynn takes a closer look at the drawing [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]. It appears to be a top-down blueprint of a tower and is very well done [NewHubCandidate][Elderwyld/Unknown Sites/Voices Tower/]. Finally, after drinking the tea, Lysandra comes out of the spell [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]. She is very confused, wondering where she is and how she got there. All that she is able to remember is voices in the dark after the group left into the forest [NewHubCandidate][Elderwyld/Unknown Sites/Voices Tower/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] [Location][Elderwyld/Migrating Forest/]. 

Back outside, Karesmine is rounding up the horses and making sure they are properly taken care of [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]. She can see that the storm is still building in the distance, but will soon be upon the camp. Stafl starts sorting through the provisions, convinced that someone snuck in the tainted meat before leaving Mirathorn [PC][Longmont Campaign/Campaign 2/PCs/stafl/] [Location][Elderwyld/Cities and Towns/Mirathorn/]. With a huge sigh of relief he finds the bacon untouched, however the other crates of jerky did not fare as well. Mixed in with the meat is cleverly disguised tainted meat. Not being able to separate the good from the bad, the whole thing will have to be burned. Caelynn calls Sara to tell her the good news about Lysandra, and bad news about the tainted meat [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]. Sara is very concerned about who she can now trust in the city [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] [Location][Elderwyld/Cities and Towns/Mirathorn/]. She transfers Caelynn to Professor Tealeaf [NPC][Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/] [NewHubCandidate][Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/], but she doesn't pick up.

Caelynn continues to wait on the line for an answer from Tealeaf [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [NewHubCandidate][Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/] as the rest of the group set up a proper camp for a rest [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]. They need to set up a shelter for the animals and themselves as it is clear the storm is approaching and Karesmine can see it is bringing the magical shimmering rain [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]. Ephanna plans to create a disguise and go back to town for new supplies [PC][Longmont Campaign/Campaign 2/PCs/ephanna/] [Location][Elderwyld/Cities and Towns/Mossford/], but for the moment the group is settling in for a rest around the camp [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/].
