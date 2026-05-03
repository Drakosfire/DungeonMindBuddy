---
schema: dmb_recap_breadcrumbs_v1
title: "Session 20 - Recap"
document_class: play
canon_layer: campaign
campaign_id: longmont-c2
campaign: "Longmont Campaign"
campaign_number: 2
session: 20
origin_session: 20
last_updated_session: 20
temporal_scope: session_specific
source_class: observed_session_recap
source_recap_path: "Longmont Campaign/Campaign 2/Recaps/Session 20 - Recap.md"
breadcrumb_semantics:
  purpose: "Selective inline breadcrumbs identify durable PC, NPC, Location, Party, and NewHubCandidate subjects for retrieval without tagging every mention."
  route_style: "corpus-relative hub route"
  tagging_density: selective
  tag_only_when: "The mention carries durable retrieval value for that subject as actor, witness, decision-maker, reputation target, clue, threat, affected group, or location context."
  party_rule: "Use Party only for Questionable Company as a collective actor, witness, decision-maker, reputation target, or affected group; do not infer all-six participation when specific PCs are elsewhere."
inline_tag_grammar:
  pattern: "[SubjectType][corpus-relative hub route]"
  allowed_subject_types:
    - PC
    - NPC
    - Location
    - Party
    - NewHubCandidate
  examples:
    pc: "Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/]"
    npc: "Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/]"
    location: "Mirathorn[Location][Longmont Campaign/Campaign 2/Locations/mirathorn/]"
    party: "Questionable Company[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]"
    new_hub_candidate: "rockie-talkie[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/rockie_talkie/]"
entity_index:
  parties:
    questionable_company:
      display_name: "Questionable Company"
      route: "Longmont Campaign/Campaign 2/Parties/questionable_company/"
      aliases:
        - "Questionable Company"
        - "the heroes"
        - "the group"
        - "the team"
        - "the rest of the team"
        - "the rest of the group"
        - "the others"
  pcs:
    ephanna:
      display_name: "Ephanna"
      route: "Longmont Campaign/Campaign 2/PCs/ephanna/"
    karesmine:
      display_name: "Karesmine"
      route: "Longmont Campaign/Campaign 2/PCs/karesmine/"
      aliases:
        - "Karsemine"
    caelynn:
      display_name: "Caelynn"
      route: "Longmont Campaign/Campaign 2/PCs/caelynn/"
    thrin:
      display_name: "Thrin"
      route: "Longmont Campaign/Campaign 2/PCs/thrin/"
    bonogo:
      display_name: "Bonogo"
      route: "Longmont Campaign/Campaign 2/PCs/bonogo/"
    stafl:
      display_name: "Stafl"
      route: "Longmont Campaign/Campaign 2/PCs/stafl/"
  npcs:
    stuart:
      display_name: "Stuart"
      route: "Longmont Campaign/Campaign 2/NPCs/stuart/"
    stacey:
      display_name: "Stacey"
      route: "Longmont Campaign/Campaign 2/NPCs/stacey/"
    marla:
      display_name: "Marla"
      route: "Longmont Campaign/Campaign 2/NPCs/marla/"
    lysandra:
      display_name: "Lysandra"
      route: "Longmont Campaign/Campaign 2/NPCs/lysandra/"
    sara:
      display_name: "Sara"
      route: "Longmont Campaign/Campaign 2/NPCs/sara/"
    mayor:
      display_name: "Mayor"
      route: "Longmont Campaign/Campaign 2/NPCs/mayor/"
    sheriff:
      display_name: "Sheriff"
      route: "Longmont Campaign/Campaign 2/NPCs/sheriff/"
    professor_tealeaf:
      display_name: "Professor Tealeaf"
      route: "Longmont Campaign/Campaign 2/NPCs/professor_tealeaf/"
  locations:
    forest:
      display_name: "Forest"
      route: "Longmont Campaign/Campaign 2/Locations/forest/"
    unnamed_forest_town:
      display_name: "Unnamed forest town"
      route: "Longmont Campaign/Campaign 2/Locations/unnamed_forest_town/"
    field_worksite:
      display_name: "Field worksite"
      route: "Longmont Campaign/Campaign 2/Locations/field_worksite/"
    mirathorn:
      display_name: "Mirathorn"
      route: "Longmont Campaign/Campaign 2/Locations/mirathorn/"
    lysandra_wagon_camp:
      display_name: "Lysandra's wagon camp"
      route: "Longmont Campaign/Campaign 2/Locations/lysandra_wagon_camp/"
  new_hub_candidates:
    red_gnat_swarm:
      display_name: "Red gnat swarm"
      proposed_route: "Longmont Campaign/Campaign 2/New Hub Candidates/red_gnat_swarm/"
      reason: "Distinct hostile swarm encountered during forest testing."
    half_burned_warehouse:
      display_name: "Half-burned warehouse"
      proposed_route: "Longmont Campaign/Campaign 2/New Hub Candidates/half_burned_warehouse/"
      reason: "Children's hideout where Bonogo confronted the Stacey/Stuart conflict."
    rockie_talkie:
      display_name: "rockie-talkie"
      proposed_route: "Longmont Campaign/Campaign 2/New Hub Candidates/rockie_talkie/"
      reason: "Communication item used to contact Sara and Lysandra."
    tower_blueprint_and_voices:
      display_name: "Tower blueprint and voices"
      proposed_route: "Longmont Campaign/Campaign 2/New Hub Candidates/tower_blueprint_and_voices/"
      reason: "Lysandra drew a detailed tower blueprint while entranced and said voices came from it."
    cult_shimmery_eyes:
      display_name: "Cult with shimmery eyes"
      proposed_route: "Longmont Campaign/Campaign 2/New Hub Candidates/cult_shimmery_eyes/"
      reason: "Lysandra's shimmery eyes matched previously observed cult members."
    tainted_meat:
      display_name: "Tainted meat"
      proposed_route: "Longmont Campaign/Campaign 2/New Hub Candidates/tainted_meat/"
      reason: "Disguised contaminated provisions connected to Mirathorn and Lysandra's condition."
    magical_shimmering_rain:
      display_name: "Magical shimmering rain"
      proposed_route: "Longmont Campaign/Campaign 2/New Hub Candidates/magical_shimmering_rain/"
      reason: "Approaching storm hazard with magical properties."
open_questions:
  - "Confirm the official name and canonical hub route for the forest-threatened town."
  - "Confirm whether the half-burned warehouse should become a Location hub or remain a scene-specific site."
  - "Who placed the tainted meat among the provisions before the wagon left Mirathorn?"
  - "What is the tower shown in Lysandra's drawing, and where is it located?"
  - "What is the relationship between the tower voices, the cult with shimmery eyes, tainted meat, and magical shimmering rain?"
  - "Why did Sara report that something strange happened to time?"
  - "Why did Professor Tealeaf not answer the transferred call?"
counts_by_subject_type:
  pcs: 6
  npcs: 8
  locations: 5
  parties: 1
  new_hub_candidates: 7
---

# Session 20 Recap

Back out near the edge of the forest[Location][Longmont Campaign/Campaign 2/Locations/forest/] Ephanna[PC][Longmont Campaign/Campaign 2/PCs/ephanna/], Karesmine[PC][Longmont Campaign/Campaign 2/PCs/karesmine/], Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] and Thrin[PC][Longmont Campaign/Campaign 2/PCs/thrin/] continue to battle the swarm of red gnats[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/red_gnat_swarm/]. Thrin[PC][Longmont Campaign/Campaign 2/PCs/thrin/], desperate to see something go in their favor, takes two more shots with his bow. The first misses, but the second does enough damage to knock a group of insects out of the swarm.Then the swarm turns and envelopes Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/], the rest of the team can only see her dim shadow under all the flying insects. Thanks to her high constitution, she is able to withstand the stinging and only take minor damage. 

Ephanna[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] unleashes two Eldritch Blasts, the first missing and the second one dealing enough damage to knock another cluster out of the swarm. They Misty Step away and add some temporary health to themselves. Now that the swarm is around Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/], Karsemine[PC][Longmont Campaign/Campaign 2/PCs/karesmine/] is able to use her scimitar and short sword for a series of attacks, landing 4 hits on the swarm. She also uses Zephyr Strike to increase her movement and dash away. Finally Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] is able to duck out of the swarm, then facing them, casts a powerful Thunderwave spell, splitting the swarm in two and pushing it back 10 feet. As Thrin[PC][Longmont Campaign/Campaign 2/PCs/thrin/] and Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] move back the swarm finally gives up and heads back into the forest[Location][Longmont Campaign/Campaign 2/Locations/forest/]. The team decides they have enough “testing” and should head back to tell the others what they discovered.

Back in town[Location][Longmont Campaign/Campaign 2/Locations/unnamed_forest_town/], Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] is being guided by Stuart[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] down an alley to a half burned building[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/half_burned_warehouse/]. According to Stuart[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] this is where they will find Stacey[NPC][Longmont Campaign/Campaign 2/NPCs/stacey/]. As soon as they step inside the large warehouse they find a group of children formed into two groups with what appear to be the leaders arguing in the middle. One of them is Stacey[NPC][Longmont Campaign/Campaign 2/NPCs/stacey/], the bugbear girl they are looking for. She is in a heated argument with the other children who are accusing her of continuing to be too bossy. Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] whispers into Stuart's[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] ear, “you know what to do” then sends him over. Stacey[NPC][Longmont Campaign/Campaign 2/NPCs/stacey/] immediately gets upset at seeing Stuart[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] and tells him that he can’t play with them, but Stuart[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] is undeterred. He sticks his hand out and demands his gold back, convinced that she is the one that stole it. Stuart[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] takes a quick glance at Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] before he pulls out the dart and threatens her with it. Alarmed, she yells at Stuart[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] and then throws her gold pouch at him before storming out the door. 

Stuart[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] is so happy with the outcome that he runs out the door, racing off to tell his mom the good news. The other kids now ask Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] to play with them instead. He agrees to play hide and seek as long as the kids hide first. He counts to 20 then leaves the building without making a sound. He is intent on following Stacey[NPC][Longmont Campaign/Campaign 2/NPCs/stacey/] and catches up to her in the next alley. After seeing no one else around, he quickly grabs her and puts a knife to her throat. He tells her to stop bullying Stuart[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] or he will come back, then dashes into the shadows. Clearly shaken, Stacey[NPC][Longmont Campaign/Campaign 2/NPCs/stacey/] runs home. Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] makes his way back to the group[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] out in the field[Location][Longmont Campaign/Campaign 2/Locations/field_worksite/].

As the group[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] approaches the preparations happening in the field[Location][Longmont Campaign/Campaign 2/Locations/field_worksite/], they find Stafl[PC][Longmont Campaign/Campaign 2/PCs/stafl/] singing and directing the workers from a makeshift throne of barrels on the back of a wagon. Ephanna[PC][Longmont Campaign/Campaign 2/PCs/ephanna/], Karesmine[PC][Longmont Campaign/Campaign 2/PCs/karesmine/] and Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] relay their findings from their tests: do not attack the trees directly, but the forest[Location][Longmont Campaign/Campaign 2/Locations/forest/] should respond to changes on the ground. Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] takes up a supervisor role and is observing the work when he hears footsteps quickly approaching behind him. He is able to dodge a slap from a furious Bugbear woman. Even with the missed slap, she gets up into Bonogo’s[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] face and begins to berate him for encouraging Stuart[NPC][Longmont Campaign/Campaign 2/NPCs/stuart/] to harass her daughter, causing many of the workers to stop and watch. Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] tries to shift the situation and asks why she is not helping with the ditches and should get to work instead. This, of course, only makes her more furious. 

She stands up to her full Bugbear height and begins to scream at him. She finds just the right words to cut deep: he smells like a circus animal. Stafl[PC][Longmont Campaign/Campaign 2/PCs/stafl/] takes a look around at the crowd to gauge their reactions. A farmer whispers to him that Stafl[PC][Longmont Campaign/Campaign 2/PCs/stafl/] better step in and help because Marla[NPC][Longmont Campaign/Campaign 2/NPCs/marla/] is not someone to mess with. They reveal that she is in charge of the workers in town[Location][Longmont Campaign/Campaign 2/Locations/unnamed_forest_town/] and she means business. Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] continues to escalate the situation, telling Marla[NPC][Longmont Campaign/Campaign 2/NPCs/marla/] he sees where her daughter gets her attitude from. Marla[NPC][Longmont Campaign/Campaign 2/NPCs/marla/] then grapples Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] and is about to do much worse when Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] comes to the rescue. Using her bracelet she is able to diffuse the aggression and get everyone back to work, united against the approaching forest[Location][Longmont Campaign/Campaign 2/Locations/forest/]. The rest of the Questionable Company[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] decide to take a short rest as their final preparation.

Questionable Company[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/], along with the townsfolk, watch as the forest[Location][Longmont Campaign/Campaign 2/Locations/forest/] comes within range of their plan. As the forest[Location][Longmont Campaign/Campaign 2/Locations/forest/] finally reaches the fortifications, the fires are lit in the ditches. Immediately they can all see the trees pull back and then start to turn to the east, away from the town[Location][Longmont Campaign/Campaign 2/Locations/unnamed_forest_town/]. Cheers go up along the ditches and into town[Location][Longmont Campaign/Campaign 2/Locations/unnamed_forest_town/]. The mayor[NPC][Longmont Campaign/Campaign 2/NPCs/mayor/] and sheriff[NPC][Longmont Campaign/Campaign 2/NPCs/sheriff/] congratulate the heroes[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] and thank them again for all their help. Marla[NPC][Longmont Campaign/Campaign 2/NPCs/marla/] approaches Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] and asks her how she should deal with Bonogo[PC][Longmont Campaign/Campaign 2/PCs/bonogo/], but Ephanna[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] quickly intervenes, letting her, and the town[Location][Longmont Campaign/Campaign 2/Locations/unnamed_forest_town/], know that the Questionable Company[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] is leaving town[Location][Longmont Campaign/Campaign 2/Locations/unnamed_forest_town/] to continue their journey. And now that the danger has passed Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] asks the mayor[NPC][Longmont Campaign/Campaign 2/NPCs/mayor/] about Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/], but finds out that they have never heard of her.

Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] quickly pulls out the “rockie-talkie”[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/rockie_talkie/] and attempts to call Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/]. After a brief pause she is connected with the familiar voice of Sara[NPC][Longmont Campaign/Campaign 2/NPCs/sara/], one half of the operators in Mirathorn[Location][Longmont Campaign/Campaign 2/Locations/mirathorn/]. Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] relays her request and Sara[NPC][Longmont Campaign/Campaign 2/NPCs/sara/] calls Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/]. She tells Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] that all she could hear was mumbling about the forest[Location][Longmont Campaign/Campaign 2/Locations/forest/] leaving and that something strange happened to the time. Sara[NPC][Longmont Campaign/Campaign 2/NPCs/sara/] then connects Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] directly to Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/] who is relieved and overjoyed that the group[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] is ok and that they took care of the forest[Location][Longmont Campaign/Campaign 2/Locations/forest/]. Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] wants to know if she is ok and where she is. Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/] tells her that she can’t remember much after the group[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] left, only that she decided to go around the forest[Location][Longmont Campaign/Campaign 2/Locations/forest/] and she could smell meat while trying to sleep. She is exhausted and disoriented. Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] tells her to stop where she is and make a camp and rest, Karesmine[PC][Longmont Campaign/Campaign 2/PCs/karesmine/] will lead the team[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] to her.

Using her extensive tracking skills, Karesmine[PC][Longmont Campaign/Campaign 2/PCs/karesmine/] is able to estimate the distance and direction that Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/] may have traveled. The group[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] sets off from the town[Location][Longmont Campaign/Campaign 2/Locations/unnamed_forest_town/], Ephanna[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] keeping a close eye on Thrin[PC][Longmont Campaign/Campaign 2/PCs/thrin/]. Thirty minutes later they come across an unusual sight: a wagon partly unloaded and horses wandering around a stack of crates[Location][Longmont Campaign/Campaign 2/Locations/lysandra_wagon_camp/]. Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] approaches the makeshift shelter and hears mumbling from inside. She finds Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/] drawing in the dirt. She says it is a tower where the voices are coming from and she knows where it is[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/tower_blueprint_and_voices/]. The first thing Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] notices about Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/] is that her eyes are shimmery, just like the members of the cult[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/cult_shimmery_eyes/]. She quickly begins to make the antidote from the tea in her bag. While the tea is being prepared, Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] takes a closer look at the drawing. It appears to be a top-down blueprint of a tower[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/tower_blueprint_and_voices/] and is very well done. Finally, after drinking the tea, Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/] comes out of the spell. She is very confused, wondering where she is and how she got there. All that she is able to remember is voices in the dark after the group[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] left into the forest[Location][Longmont Campaign/Campaign 2/Locations/forest/]. 

Back outside, Karesmine[PC][Longmont Campaign/Campaign 2/PCs/karesmine/] is rounding up the horses and making sure they are properly taken care of. She can see that the storm is still building in the distance, but will soon be upon the camp. Stafl[PC][Longmont Campaign/Campaign 2/PCs/stafl/] starts sorting through the provisions, convinced that someone snuck in the tainted meat[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/tainted_meat/] before leaving Mirathorn[Location][Longmont Campaign/Campaign 2/Locations/mirathorn/]. With a huge sigh of relief he finds the bacon untouched, however the other crates of jerky did not fare as well. Mixed in with the meat is cleverly disguised tainted meat[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/tainted_meat/]. Not being able to separate the good from the bad, the whole thing will have to be burned. Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] calls Sara[NPC][Longmont Campaign/Campaign 2/NPCs/sara/] to tell her the good news about Lysandra[NPC][Longmont Campaign/Campaign 2/NPCs/lysandra/], and bad news about the tainted meat[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/tainted_meat/]. Sara[NPC][Longmont Campaign/Campaign 2/NPCs/sara/] is very concerned about who she can now trust in the city. She transfers Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] to Professor Tealeaf[NPC][Longmont Campaign/Campaign 2/NPCs/professor_tealeaf/], but she doesn't pick up.

Caelynn[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] continues to wait on the line for an answer from Tealeaf[NPC][Longmont Campaign/Campaign 2/NPCs/professor_tealeaf/] as the rest of the group[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] set up a proper camp for a rest. They need to set up a shelter for the animals and themselves as it is clear the storm is approaching and Karesmine[PC][Longmont Campaign/Campaign 2/PCs/karesmine/] can see it is bringing the magical shimmering rain[NewHubCandidate][Longmont Campaign/Campaign 2/New Hub Candidates/magical_shimmering_rain/]. Ephanna[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] plans to create a disguise and go back to town[Location][Longmont Campaign/Campaign 2/Locations/unnamed_forest_town/] for new supplies, but for the moment the group[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] is settling in for a rest around the camp.
