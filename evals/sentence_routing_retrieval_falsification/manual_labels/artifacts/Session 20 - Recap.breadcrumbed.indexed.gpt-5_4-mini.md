---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 2
  campaign_id: longmont-c2
session:
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
      default_members: [baergrom, bonogo, caelynn, ephanna, karsemine, stafl]
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
      aliases_in_recap: ["Karesmine"]
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
    PC: 49
    NPC: 39
    Location: 19
    Party: 11
    NewHubCandidate: 8
  unresolved_open_questions: 3
---
# Session 20 Recap

Back out near the edge of the forest [PC][Longmont Campaign/Campaign 2/PCs/ephanna/]Ephanna, [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]Karesmine, [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn and [NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/]Thrin continue to battle the swarm of red gnats. [NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/]Thrin, desperate to see something go in their favor, takes two more shots with his bow. The first misses, but the second does enough damage to knock a group of insects out of the swarm.Then the swarm turns and envelopes [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn, the rest of the team can only see her dim shadow under all the flying insects. Thanks to her high constitution, she is able to withstand the stinging and only take minor damage. 

[PC][Longmont Campaign/Campaign 2/PCs/ephanna/]Ephanna unleashes two Eldritch Blasts, the first missing and the second one dealing enough damage to knock another cluster out of the swarm. They Misty Step away and add some temporary health to themselves. Now that the swarm is around [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn, [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]Karsemine is able to use her scimitar and short sword for a series of attacks, landing 4 hits on the swarm. She also uses Zephyr Strike to increase her movement and dash away. Finally [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn is able to duck out of the swarm, then facing them, casts a powerful Thunderwave spell, splitting the swarm in two and pushing it back 10 feet. As [NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/]Thrin and [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn move back the swarm finally gives up and heads back into the forest. [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]The team decides they have enough “testing” and should head back to tell the others what they discovered.

Back in town, [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo is being guided by [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart down an alley to a [Location][Elderwyld/Cities and Towns/Mossford/][NewHubCandidate][Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md]half burned building. According to [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart this is where they will find [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]Stacey. As soon as they step inside the large warehouse they find a group of children formed into two groups with what appear to be the leaders arguing in the middle. One of them is [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]Stacey, the bugbear girl they are looking for. She is in a heated argument with the other children who are accusing her of continuing to be too bossy. [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo whispers into [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart's ear, “you know what to do” then sends him over. [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]Stacey immediately gets upset at seeing [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart and tells him that he can’t play with them, but [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart is undeterred. He sticks his hand out and demands his gold back, convinced that she is the one that stole it. [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart takes a quick glance at [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo before he pulls out the dart and threatens her with it. Alarmed, she yells at [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart and then throws her gold pouch at him before storming out the door. 

[NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart is so happy with the outcome that he runs out the door, racing off to tell his mom the good news. The other kids now ask [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo to play with them instead. He agrees to play hide and seek as long as the kids hide first. He counts to 20 then leaves the building without making a sound. He is intent on following [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]Stacey and catches up to her in the next alley. After seeing no one else around, he quickly grabs her and puts a knife to her throat. He tells her to stop bullying [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart or he will come back, then dashes into the shadows. Clearly shaken, [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/]Stacey runs home. [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo makes his way back to the group out in the field.

As the group approaches the preparations happening in the field, they find [PC][Longmont Campaign/Campaign 2/PCs/stafl/]Stafl singing and directing the workers from a makeshift throne of barrels on the back of a wagon. [PC][Longmont Campaign/Campaign 2/PCs/ephanna/]Ephanna, [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]Karsemine and [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn relay their findings from their tests: do not attack the trees directly, but the [Location][Elderwyld/Migrating Forest/]forest should respond to changes on the ground. [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo takes up a supervisor role and is observing the work when he hears footsteps quickly approaching behind him. He is able to dodge a slap from a furious [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/]Bugbear woman. Even with the missed slap, she gets up into [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo's face and begins to berate him for encouraging [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/stuart/]Stuart to harass her daughter, causing many of the workers to stop and watch. [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo tries to shift the situation and asks why she is not helping with the ditches and should get to work instead. This, of course, only makes her more furious. 

She stands up to her full Bugbear height and begins to scream at him. She finds just the right words to cut deep: he smells like a circus animal. [PC][Longmont Campaign/Campaign 2/PCs/stafl/]Stafl takes a look around at the crowd to gauge their reactions. A farmer whispers to him that [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/]Marla better step in and help because [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/]Marla is not someone to mess with. They reveal that she is in charge of the workers in town and she means business. [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo continues to escalate the situation, telling [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/]Marla he sees where her daughter gets her attitude from. [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/]Marla then grapples [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo and is about to do much worse when [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn comes to the rescue. Using her bracelet she is able to diffuse the aggression and get everyone back to work, united against the approaching forest. [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]The rest of the Questionable Company decide to take a short rest as their final preparation.

[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]Questionable Company, along with the townsfolk, watch as the [Location][Elderwyld/Migrating Forest/]forest comes within range of their plan. As the forest finally reaches the fortifications, the fires are lit in the ditches. Immediately they can all see the trees pull back and then start to turn to the east, away from the town. Cheers go up along the ditches and into town. The mayor and [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/]sheriff congratulate the heroes and thank them again for all their help. [NPC][Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/]Marla approaches [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn and asks her how she should deal with [PC][Longmont Campaign/Campaign 2/PCs/bonogo/]Bonogo, but [PC][Longmont Campaign/Campaign 2/PCs/ephanna/]Ephanna quickly intervenes, letting her, and the town, know that the [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]Questionable Company is leaving town to continue their journey. And now that the danger has passed [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn asks the mayor about [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra, but finds out that they have never heard of her.

[PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn quickly pulls out the “rockie-talkie” and attempts to call [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra. After a brief pause she is connected with the familiar voice of [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/]Sara, one half of the operators in [Location][Elderwyld/Cities and Towns/Mirathorn/]Mirathorn. [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn relays her request and [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/]Sara calls [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra. She tells [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn that all she could hear was mumbling about the [Location][Elderwyld/Migrating Forest/]forest leaving and that something strange happened to the time. [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/]Sara then connects [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn directly to [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra who is relieved and overjoyed that the [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]group is ok and that they took care of the [Location][Elderwyld/Migrating Forest/]forest. [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn wants to know if she is ok and where she is. [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra tells her that she can’t remember much after the [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]group left, only that she decided to go around the [Location][Elderwyld/Migrating Forest/]forest and she could smell meat while trying to sleep. She is exhausted and disoriented. [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn tells her to stop where she is and make a camp and rest, [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]Karesmine will lead the team to her.

Using her extensive tracking skills, [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]Karesmine is able to estimate the distance and direction that [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra may have traveled. The [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]group sets off from the town, [PC][Longmont Campaign/Campaign 2/PCs/ephanna/]Ephanna keeping a close eye on [NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/]Thrin. Thirty minutes later they come across an unusual sight: a wagon partly unloaded and horses wandering around a stack of crates. [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn approaches the makeshift shelter and hears mumbling from inside. She finds [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra drawing in the dirt. She says it is a tower where the voices are coming from and she knows where it is. The first thing [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn notices about [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra is that her eyes are shimmery, just like the members of the cult. She quickly begins to make the antidote from the tea in her bag. While the tea is being prepared, [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn takes a closer look at the drawing. It appears to be a top-down blueprint of a tower and is very well done. [NewHubCandidate][Elderwyld/Unknown Sites/Voices Tower/]Finally, after drinking the tea, [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra comes out of the spell. She is very confused, wondering where she is and how she got there. All that she is able to remember is voices in the dark after the [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]group left into the [Location][Elderwyld/Migrating Forest/]forest. 

Back outside, [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]Karesmine is rounding up the horses and making sure they are properly taken care of. She can see that the storm is still building in the distance, but will soon be upon the camp. [PC][Longmont Campaign/Campaign 2/PCs/stafl/]Stafl starts sorting through the provisions, convinced that someone snuck in the tainted meat before leaving [Location][Elderwyld/Cities and Towns/Mirathorn/]Mirathorn. With a huge sigh of relief he finds the bacon untouched, however the other crates of jerky did not fare as well. Mixed in with the meat is cleverly disguised tainted meat. Not being able to separate the good from the bad, the whole thing will have to be burned. [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn calls [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/]Sara to tell her the good news about [NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]Lysandra, and bad news about the tainted meat. [NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/]Sara is very concerned about who she can now trust in the city. She transfers [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn to [NPC][Longmont Campaign/Campaign 2/NPCs/professor_merril_tealeaf/][NewHubCandidate][Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/]Professor Tealeaf, but she doesn't pick up.

[PC][Longmont Campaign/Campaign 2/PCs/caelynn/]Caelynn continues to wait on the line for an answer from Tealeaf as the rest of the [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]group set up a proper camp for a rest. They need to set up a shelter for the animals and themselves as it is clear the storm is approaching and [PC][Longmont Campaign/Campaign 2/PCs/karsemine/]Karesmine can see it is bringing the magical shimmering rain. [PC][Longmont Campaign/Campaign 2/PCs/ephanna/]Ephanna plans to create a disguise and go back to town for new supplies, but for the moment the [Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]group is settling in for a rest around the camp.
