/**
 * Authored Of Conks & Cons — Hempholm scene/beat spine for Play → Beats.
 * Table-facing copy only; not graph canon. Progress lives in play run-state.
 */

export type BeatKind = "spine" | "optional" | "interrupt";

export type SceneBranchKind = "linear" | "hook-pick" | "aftermath-pick";

export type BeatChip = {
  label: string;
  nodeId: string;
};

export type BeatToolLink = {
  label: string;
  panel: "combat" | "roll" | "items" | "statblocks";
};

export type BeatReadAloud = {
  label?: string | null;
  text: string;
};

export type AdventureBeat = {
  id: string;
  title: string;
  kind: BeatKind;
  summary: string;
  atTable?: string | null;
  readAlouds?: BeatReadAloud[] | null;
  gmNote?: string | null;
  rulesNow?: string[] | null;
  ifTheyWait?: string[] | null;
  ifTheySucceed?: string[] | null;
  ifTheyFail?: string[] | null;
  warnings?: string[] | null;
  treasure?: string[] | null;
  chips?: BeatChip[] | null;
  toolLinks?: BeatToolLink[] | null;
};

export type AdventureScene = {
  id: string;
  title: string;
  order: number;
  intent: string;
  clocks?: string[] | null;
  readAloud?: string | null;
  gmNote?: string | null;
  chips?: BeatChip[] | null;
  beats: AdventureBeat[];
  /** How this scene participates in branching. */
  branchKind: SceneBranchKind;
  /**
   * When set, scene is only in the active deck if branch.aftermath matches
   * (or is unset and this is the chooser scene — handled in deck helpers).
   */
  requiresAftermath?: "celebration" | "fire" | null;
};

export type AdventureSpine = {
  adventureId: string;
  campaignId: string;
  runId: string;
  title: string;
  scenes: AdventureScene[];
};

export const OF_CONKS_HEMPHOLM_RUN_ID = "of-conks-cons--hempholm";

export const OF_CONKS_HEMPHOLM_SPINE: AdventureSpine = {
  adventureId: "hempholm",
  campaignId: "of-conks-cons",
  runId: OF_CONKS_HEMPHOLM_RUN_ID,
  title: "Hempholm — Of Conks & Cons",
  scenes: [
    {
      id: "hook",
      title: "Hook",
      order: 0,
      branchKind: "hook-pick",
      intent: "Pick one opening. Do not stack all three as simultaneous canon.",
      gmNote:
        "Lord Fiddlestick stole an enchanted conk from a traveling alchemist and sold it to Torbin Jove at Greenest's market. The tuber became a grotesque tree whose roots harvest precious metals underground while caretakers tend the hollow root network. The Baldur's Gate mages' guild chose the Greenfields hinterlands for a field test far from prying eyes.",
      beats: [
        {
          id: "hook-hill",
          title: "Hill arrival (default)",
          kind: "spine",
          summary: "Approach Hempholm from a hill; grotesque tree lashes a bird.",
          atTable:
            "Default open: hungry adventurers spot Hempholm on the road. The tree is visible from the hill — suspicion and appetite for adventure in one beat.",
          readAlouds: [
            {
              text: "With an empty stomach and pouches full of gold, you approach a hamlet which lies on your way. Overlooking the village from a small hill, you cannot help but notice a grotesque tree growing in one of the gardens which towers above all other trees and buildings in the area. When a bird tries to perch on one of its branches, the tree lashes out and turns the bird into minced meat. This event equally arouses your suspicion and lust for adventure!",
            },
          ],
          chips: [
            { label: "Hempholm", nodeId: "location:hempholm" },
            { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
          ],
        },
        {
          id: "hook-alchemist",
          title: "Alchemist's Despair",
          kind: "optional",
          summary:
            "In Greenest, Korden begs help recovering a stolen conk for the Baldur's Gate mages' guild.",
          atTable:
            "Cold open in Greenest. Korden is panicked — the guild will be generous if the tuber is returned. Days of dead ends until a merchant mentions a terrorized village.",
          readAlouds: [
            {
              text: "A man with both panic and worry in his eyes approaches you during your stay in Greenest. He calls himself Korden and tells you of a terrible theft that puts his life's work in jeopardy. He implores you—looking like the adventurers you are—to find the culprit or at least a trace of the valuable conk! The Baldur's Gate mages' guild will be most pleased and generous in case you return the tuber, Korden promises. For a few days, you scour the town and the surrounding farms, finding no trace of either. At long last, a traveling merchant tells you of a strange plant which terrorizes a village not far from Greenest. You set out to investigate!",
            },
          ],
          chips: [
            { label: "Korden", nodeId: "npc:korden" },
            { label: "the conk", nodeId: "item:the-conk" },
            { label: "Baldur's Gate mages' guild", nodeId: "faction:baldurs-gate-mages-guild" },
          ],
        },
        {
          id: "hook-guild",
          title: "In Service of the Guild",
          kind: "optional",
          summary:
            "Berdusk delivery fails — Lord Fiddlestick already sold the package to a village boy.",
          atTable:
            "Employed courier gig gone wrong. Track Lord Fiddlestick; he already fenced the package. The boy named his home village — retrieve it or face wizardly punishment.",
          readAlouds: [
            {
              text: "You were employed to deliver a package of great import to a temple of Chauntea in Berdusk—a town in the countryside. The client is a mages' guild based in Baldur's Gate, and a good friend of yours facilitated the deal, vouching for your skills. When you accepted the quest, it seemed easy enough, and the promised pay was rather high. Alas, the package was stolen one fateful evening. You tracked down the culprit—a gnome who calls himself Lord Fiddlestick—but he already sold the package to a hapless boy! Fortunately, the boy told the thief about the village he hails from. It is high time to retrieve the package or otherwise the quest is null and void. You never know what creative punishment a malevolent wizard might come up with...",
            },
          ],
          chips: [
            { label: "Lord Fiddlestick", nodeId: "npc:lord-fiddlestick" },
            { label: "the conk", nodeId: "item:the-conk" },
            { label: "Baldur's Gate mages' guild", nodeId: "faction:baldurs-gate-mages-guild" },
          ],
        },
      ],
    },
    {
      id: "arrive",
      title: "Arrive Hempholm",
      order: 1,
      branchKind: "linear",
      intent: "Land in the village. If another hook was used, skip hill RA and start at Shacks or Jove.",
      readAloud:
        "Overlooking the village from a small hill, you cannot help but notice a grotesque tree growing in one of the gardens which towers above all other trees and buildings in the area. When a bird tries to perch on one of its branches, the tree lashes out and turns the bird into minced meat.",
      gmNote:
        "New players may freeze — start in media res at the tree, or have an NPC take them by the hand. Do not wait for them to begin roleplaying. ~80 people live in Hempholm; hemp cultivation is the trade.",
      chips: [
        { label: "Hempholm", nodeId: "location:hempholm" },
        { label: "The Shacks", nodeId: "location:the-shacks" },
        { label: "The Jove's Home", nodeId: "location:jove-home" },
      ],
      beats: [
        {
          id: "arrive-hill",
          title: "Hill overlook",
          kind: "spine",
          summary: "See the tree; curiosity and hunger for adventure.",
          atTable:
            "Confirm the problem from the hill. The grotesque tree dominates one garden. Villagers are commoners (MM 345) unless noted. Name improvised NPCs — players remember them.",
          readAlouds: [
            {
              text: "Overlooking the village from a small hill, you cannot help but notice a grotesque tree growing in one of the gardens which towers above all other trees and buildings in the area. When a bird tries to perch on one of its branches, the tree lashes out and turns the bird into minced meat.",
            },
          ],
          chips: [{ label: "Grotesque Tree", nodeId: "threat:grotesque-tree" }],
        },
        {
          id: "arrive-skip-to-shacks",
          title: "Skip to Shacks",
          kind: "optional",
          summary: "Alchemist or guild hook → start at The Shacks instead of the hill.",
          atTable:
            "If they came via Korden or the guild delivery, they may arrive at the village square or Shacks without the hill vista. Same village, different entry beat.",
          chips: [{ label: "The Shacks", nodeId: "location:the-shacks" }],
        },
        {
          id: "arrive-skip-to-jove",
          title: "Skip to Jove home",
          kind: "optional",
          summary: "Different hook → start at the garden crisis.",
          atTable:
            "Merchant or witness may send them straight to the Jove garden. Skip hill RA; the tree and Mark's panic are the first contact.",
          chips: [
            { label: "The Jove's Home", nodeId: "location:jove-home" },
            { label: "Mark Jove", nodeId: "npc:mark-jove" },
          ],
        },
      ],
    },
    {
      id: "village-sandbox",
      title: "Village sandbox",
      order: 2,
      branchKind: "linear",
      intent:
        "Free roam: Areas 1–5 and side jobs. Stall pressure advances the tree-growth clock.",
      clocks: [
        "Tree growth 0: two stories, garden only",
        "1: 30 ft; smashes Jove home + two neighbors",
        "2: Fire risk if they burn (d20 even = houses catch)",
        "3: Leave town → later news of 300-ft tree on Uldoon Trail",
      ],
      gmNote:
        "Greenfields setting essay lives in the build doc Of Conks & Cons v2.1 — do not dump regional lore into a beat. Use it for travel context and tier-1 expectations only.",
      chips: [
        { label: "Hempholm", nodeId: "location:hempholm" },
        { label: "The Shacks", nodeId: "location:the-shacks" },
        { label: "Morwin's", nodeId: "location:morwins-store" },
        { label: "Saladin's wagon", nodeId: "location:saladins-wagon" },
        { label: "Jove home", nodeId: "location:jove-home" },
      ],
      beats: [
        {
          id: "shacks-arrival",
          title: "Shacks — Nar door dump",
          kind: "spine",
          summary: "Peasant flies out; Nar demands ale.",
          atTable:
            "Area 1: largest building plus free huts for travelers. Soup kitchen and tavern inside — quality matches coin. Nar Granitetooth (NG female dwarf priest MM 348) never rests her mug-arm.",
          readAlouds: [
            {
              text: "You stand in front of the village's largest building when a peasant with an oddly noggin-shaped nose flies through the door out into the cold. Following this display, you hear the sweet sound of a cursing dwarf who demands more ale. After that, the evicted rube gets up, mounts his donkey, and hightails.",
            },
          ],
          gmNote:
            "Sharindlar is the dwarven goddess of healing, fertility, life, and mercy. Her priests are Thalornor — those who are merciful. Symbol: a burning needle. Nar lost her daughter Sarni to a brigand they rescued; she slayed the killer but help came too late.",
          rulesNow: [
            "Nar: DC 20 Charisma (Persuasion) + Religion proficiency to win her toward Sharindlar.",
            "Wounded villagers later: DC 15 Persuasion or DC 10 Intelligence (Religion) if appeal is to Sharindlar.",
            "She heals of her own accord if already in the party's good graces.",
          ],
          chips: [
            { label: "Nar Granitetooth", nodeId: "npc:nar-granitetooth" },
            { label: "The Shacks", nodeId: "location:the-shacks" },
          ],
          toolLinks: [{ label: "Open names on Roll", panel: "roll" }],
        },
        {
          id: "morwin-store",
          title: "Morwin's store",
          kind: "optional",
          summary: "Dusty shop; hates Saladin; gear ≤ 10 gp.",
          atTable:
            "Only store in Hempholm. Morwin Blackwell is old, half-deaf, often mistakes visitors. Black mood since Saladin arrived — curses him every other sentence.",
          readAlouds: [
            {
              text: "The store's interior is dusty and untidy much like its proprietor. Bundles of hair shoot out of the old man's nose and ears and he appears to be sleeping behind the counter.",
            },
          ],
          treasure: [
            "Adventuring gear ≤ 10 gp (PHB 150), basic farming equipment.",
            "Potent hemp in household quantities; blends Green Cracker and Ancient Green Dragon.",
          ],
          chips: [
            { label: "Morwin Blackwell", nodeId: "npc:morwin-blackwell" },
            { label: "Morwin's", nodeId: "location:morwins-store" },
          ],
        },
        {
          id: "gem-job",
          title: "Gem job",
          kind: "optional",
          summary: "Ten stones; DC 10 Jeweler's Tools; two tourmalines (100 gp cut).",
          atTable:
            "Morwin traded an old amulet for 10 uncut blue quartz (2 gp each). He asks every dwarf to cut them for 20 gp. Village banter jokes that all dwarfs love gems.",
          rulesNow: ["DC 10 Dexterity (Jeweler's Tools) per stone."],
          ifTheySucceed: [
            "Proper cut blue quartz pays 20 gp from Morwin.",
            "Two stones are secretly tourmalines worth 100 gp each once cut.",
          ],
          chips: [{ label: "Morwin Blackwell", nodeId: "npc:morwin-blackwell" }],
        },
        {
          id: "saladin-wagon",
          title: "Saladin's wagon",
          kind: "optional",
          summary: "Sold out except Maglubiyet's Statue (500 gp).",
          atTable:
            "Saladin (N male elf mage MM 347) sits in a gaudy wagon that's bigger inside than out (~600 ft per direction). Sold out — buying almost anything at fair prices. ~10,000 gp in his bag of holding.",
          readAlouds: [
            {
              text: "A wagon stands smack in the middle of Hempholm's village square so that no denizen or traveler is deprived of its ... beauty. The words 'Saladin's Mobile Emporium' flaunt on the wagon's sides in large golden letters and its coloration is reminiscent of a kaleidoscope. When you enter the gaudy vehicle, you notice that it's considerably larger on the inside than on the outside. An elf clothed in a purple robe sits behind a small desk and expectantly raises his head when he notices your presence.",
            },
          ],
          gmNote:
            "Unbidden thoughts: when elves reach high age or lead adventurous lives, they are visited by allegedly arbitrary memories of past lives or hallucinations. Saladin notes them mid-sentence in a small notebook for scholars to cross-reference.",
          treasure: ["Maglubiyet's Statue — 500 gp (Appendix B)."],
          chips: [
            { label: "Saladin", nodeId: "npc:saladin" },
            { label: "Maglubiyet's Statue", nodeId: "item:maglubiyets-statue" },
          ],
          toolLinks: [{ label: "Open Items", panel: "items" }],
        },
        {
          id: "meal-moonshine",
          title: "Meal n' Moonshine",
          kind: "optional",
          summary: "Contest at The Shacks; prize Belly's Mouthwash.",
          atTable:
            "Bill the Belly hosts the big competition in the Shacks tavern. Travelers and residents serve best dish or homebrew to sway his judgment.",
          rulesNow: [
            "Proficiency with cook's utensils or brewer's supplies required to enter.",
            "1d6+2 contenders each roll d20 with no bonus; PCs add proficiency.",
            "Tie broken by an additional cook- or brew-off.",
          ],
          ifTheySucceed: ["Winner receives a bottle of Belly's Mouthwash (Appendix B)."],
          chips: [
            { label: "The Shacks", nodeId: "location:the-shacks" },
            { label: "Belly's Mouthwash", nodeId: "item:bellys-mouthwash" },
          ],
        },
        {
          id: "distillery",
          title: "Broken distillery",
          kind: "optional",
          summary: "Blacksmith yard; repair for 10 gp + engraving.",
          atTable:
            "Old distillery rusting in front of the blacksmith's workshop. Blacksmith says it's broken beyond repair but they'll look.",
          rulesNow: [
            "DC 15 Dexterity (Tinker's Tools) or DC 20 Dexterity (Smith's Tools).",
          ],
          ifTheySucceed: [
            "Blacksmith rewards 10 gp and offers to engrave weapons or armor.",
          ],
        },
        {
          id: "jove-plea",
          title: "Jove plea",
          kind: "spine",
          summary: "Mark blames Torbin; tree in the garden.",
          atTable:
            "Area 4: tree dominates the garden behind the Jove home. House took damage; Torbin repairs the roof. Mark meets them at the door — distraught, blames his boy for the bewitched 'tato.",
          readAlouds: [
            {
              text: "The menacing tree stands right in the center of this house's garden. Otherwise, the house is in no way different from the others in the village. It is squat, built of wood and clay, and the windows are small and unglazed.",
            },
            {
              label: "Mark Jove",
              text: "By the gods, did you see the tree growing behind our home? We have enough problems already. I hope you are not here to add anything to it! My stupid boy brought this bewitched 'tato home and now look at it! A tree two stories high which attacks everything in sight. Now I can't even harvest the vegetables I grew. We will starve before the winter finds the time to come around! He planted it just the day before. I don't even want to think about its size when the morrow comes! You look like the adventuring sort, can't you figure this out somehow? Then we can talk about a reward. The whole village will chip in; I'm sure of it!",
            },
            {
              label: "Torbin Jove",
              text: "By golly! You look like real adventurers! Are you here to fell that tree in our garden? I think my pa will chase me out of the village if nothing is done! I can't tell you anything useful, honest! There was this little man on the market, and he was very friendly. He told me that this strange 'tato will be enough to feed my whole family for the span of a year. But now this... I told my pa to just burn it down. But he warned me that we would put the whole village to the torch if we are not careful. And I'm never careful, or so he says.",
            },
          ],
          chips: [
            { label: "Mark Jove", nodeId: "npc:mark-jove" },
            { label: "Torbin Jove", nodeId: "npc:torbin-jove" },
            { label: "The Jove's Home", nodeId: "location:jove-home" },
            { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
          ],
        },
        {
          id: "growth-spurt",
          title: "Growth spurt",
          kind: "interrupt",
          summary: "Stall → tree 30 ft; smashes Jove home + two neighbors.",
          atTable:
            "Implement when the party idles too long. Tree rampantly grows to 30 ft and needs room — clobbers Jove home and two neighbors.",
          rulesNow: [
            "Fire against the tree now: roll d20. Even = surrounding houses catch fire.",
            "The conflagration can consume the village if not doused in time.",
          ],
          ifTheyWait: [
            "Victims besiege the characters to act in the face of mindless destruction.",
          ],
          chips: [{ label: "Grotesque Tree", nodeId: "threat:grotesque-tree" }],
        },
        {
          id: "axe-villagers",
          title: "Axe villagers mauled",
          kind: "interrupt",
          summary: "Four villagers attack the tree and get wrecked; carry to Nar.",
          atTable:
            "Four strongest villagers down an ale, axes drawn, four battle cries — the tree mauls them. They withdraw with broken bones and hurt egos.",
          readAlouds: [
            {
              text: "Four of the strongest villagers are fed up. Each of them downs an ale after which they approach with their axes drawn. They flex their muscles and go in for the kill—four thunderous battle cries disrupting the once peaceful village. The tree descends on them with deadly precision and mauls the axe-wielding rubes. The villagers manage to withdraw with broken bones, bleeding wounds, and hurt egos.",
            },
          ],
          rulesNow: [
            "Nar heals the wounded only after DC 15 Charisma (Persuasion), or DC 10 Intelligence (Religion) if the appeal is to Sharindlar.",
            "She helps of her own accord if already in the party's good graces.",
          ],
          gmNote:
            "DCs are guidelines. Strong roleplay: lower or skip the check. Insults or mockery: raise the DC or make that NPC an enemy.",
          ifTheySucceed: ["Nar stops the bleeding for the brave fools."],
          chips: [{ label: "Nar Granitetooth", nodeId: "npc:nar-granitetooth" }],
        },
      ],
    },
    {
      id: "surface-tree",
      title: "Surface tree fight",
      order: 3,
      branchKind: "aftermath-pick",
      intent: "Destroy the visible tree. Fire can save the village or burn it. Then choose celebration or firefighting.",
      chips: [
        { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
        { label: "Tree garden", nodeId: "location:grotesque-tree-site" },
      ],
      beats: [
        {
          id: "tree-tactics",
          title: "Tree tactics",
          kind: "spine",
          summary: "Attacks within 30 ft; retaliates at range; nearest target.",
          atTable:
            "Area 5: approach the tree — bark tough as armor, branches thick with thorns. Bold monster name = fight may erupt. See Appendix A for stat block.",
          readAlouds: [
            {
              text: "The further you approach the tree, the stranger it appears. The tree's bark looks as tough as any armor you've seen and the branches are covered in thick thorns.",
            },
          ],
          rulesNow: [
            "Passive Wisdom (Perception) 15: shiny metal leaves on odd branches.",
            "Passive Wisdom (Arcana) 12: a magic aura around the tree.",
            "DC 17 Wisdom (Arcana): the tree is arcane-infused; magic roots stretch beneath the village.",
            "The grotesque tree attacks any creature within 30 feet and retaliates against ranged attacks. Targets nearest enemy; ceases when no longer under imminent threat.",
          ],
          warnings: [
            "Fire vs tree: roll d20. Even = surrounding houses catch fire.",
          ],
          treasure: [
            "Metal leaves worth 100 gp if they search the former battleground.",
          ],
          chips: [
            { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
            { label: "metal leaves", nodeId: "item:metal-leaves" },
          ],
          toolLinks: [{ label: "Open Combat", panel: "combat" }],
        },
        {
          id: "tree-destroyed",
          title: "Surface tree down",
          kind: "spine",
          summary: "False victory. Do not telegraph caretakers. Pick aftermath branch next.",
          atTable:
            "Surface portion destroyed — villagers celebrate OR the village burns, depending on fire. Do not hint at the caretaker wave. Roots still harbor the real threat.",
          ifTheyWait: [
            "If they leave the tree and village behind, they soon hear of a 300-ft tree that destroyed an entire village on the Uldoon Trail.",
          ],
          warnings: [
            "Do not telegraph the caretaker attack. The false victory is the point.",
          ],
        },
      ],
    },
    {
      id: "aftermath-celebration",
      title: "Premature celebration",
      order: 4,
      branchKind: "linear",
      requiresAftermath: "celebration",
      intent: "Party in The Shacks. Hours later → caretakers. Do not telegraph the second fight.",
      chips: [{ label: "The Shacks", nodeId: "location:the-shacks" }],
      beats: [
        {
          id: "celebration-party",
          title: "Heroes' party",
          kind: "spine",
          summary: "Children, ale, stories; weapons for reenactment on the hill north of Shacks.",
          atTable:
            "Villagers throw an impromptu party in the Shacks — best food, ale, and spirits. Children swarm for stories and ask to play with weapons to reenact the deed on the hill north of the Shacks.",
          rulesNow: [
            "Drinking: DC 10 Constitution save each hour. Fail = poisoned (mild drunkenness → near uselessness).",
          ],
          warnings: [
            "Do not telegraph the caretaker attack. If players smell a second shoe, placate them.",
          ],
          chips: [{ label: "The Shacks", nodeId: "location:the-shacks" }],
        },
        {
          id: "never-split",
          title: "Never Split the Party",
          kind: "optional",
          summary: "Overnight pairings disperse the party before caretakers hit.",
          atTable:
            "Some villagers may elect to spend the night with a character if appropriate for your table. Dispersed party makes the night attack more threatening.",
          warnings: [
            "If the party splits overnight, the caretaker assault hits harder.",
          ],
        },
      ],
    },
    {
      id: "aftermath-fire",
      title: "Hempholm caught fire",
      order: 4,
      branchKind: "linear",
      requiresAftermath: "fire",
      intent: "Firefighting (or run). Refugees in The Shacks. Hours later → caretakers.",
      chips: [{ label: "The Shacks", nodeId: "location:the-shacks" }],
      beats: [
        {
          id: "firefighting",
          title: "Firefighting",
          kind: "spine",
          summary: "Extinguish or flee.",
          atTable:
            "Village ablaze from the tree fight. Extinguish flames or run. Former inhabitants shelter in the Shacks while rebuilding.",
          rulesNow: [
            "DC 12 Strength (Athletics) or gain 1 level of exhaustion.",
            "d4 houses destroyed.",
          ],
          ifTheyFail: ["Flames threaten to burn down the entire village."],
          ifTheyWait: ["Caretaker alarm still comes hours later during fire ops."],
          chips: [{ label: "The Shacks", nodeId: "location:the-shacks" }],
        },
      ],
    },
    {
      id: "caretakers",
      title: "Caretaker rampage",
      order: 5,
      branchKind: "linear",
      intent: "Merge after celebration or fire. 20 twig-blight caretakers in groups of 5.",
      chips: [{ label: "Caretakers", nodeId: "threat:caretakers" }],
      beats: [
        {
          id: "caretaker-wave",
          title: "Caretaker assault",
          kind: "spine",
          summary: "Hours after surface tree dies; attack villagers and structures.",
          atTable:
            "Some hours after the surface tree falls, caretakers dig to the surface — large beetles made of roots. Alarm raised; villagers panic. Strikes during celebration or firefighting.",
          rulesNow: [
            "20 caretakers (twig blight, MM 32) in groups of 5.",
            "Attack villagers and structures.",
            "Flee or return underground after a few hours, or after 15 are dead.",
            "Afraid of fire.",
          ],
          warnings: [
            "Medium fight for 5 level-1 characters. Do not telegraph beforehand.",
          ],
          treasure: [
            "Each caretaker corpse: 1 gp quality root-wood (woodcarver's or carpenter's tools proficiency).",
          ],
          chips: [{ label: "Caretakers", nodeId: "threat:caretakers" }],
          toolLinks: [{ label: "Open Combat", panel: "combat" }],
        },
        {
          id: "urge-descent",
          title: "Urge descent",
          kind: "spine",
          summary: "Villagers urge the party into the hollow roots.",
          atTable:
            "After surviving the rampage, Hempholm's people beg the heroes to climb down the torn-open holes and finish the monsters beneath the village.",
          ifTheySucceed: ["Party enters the root-corridors toward The Marrow."],
          chips: [{ label: "Root corridors", nodeId: "location:root-corridors" }],
        },
      ],
    },
    {
      id: "descent",
      title: "Descent",
      order: 6,
      branchKind: "linear",
      intent: "Into the root corridors toward The Marrow.",
      readAloud:
        "The air down in these tunnels is dank… hollow roots are warm… more like stone or metal than wood.",
      chips: [{ label: "Root corridors", nodeId: "location:root-corridors" }],
      beats: [
        {
          id: "rabbit-hole",
          title: "Down the rabbit hole",
          kind: "spine",
          summary: "Caretakers click from narrow side corridors; withdraw if attacked.",
          atTable:
            "Caretakers tore open holes across the village. Corridors lead to the plant's heart. Bend at first, then walk upright.",
          readAlouds: [
            {
              text: "The air down in these tunnels is dank, and the temperature is higher than you would have anticipated. The hollow roots are warm to the touch but feel more like stone or metal than wood. At first, you have to bend down to fit into these tunnels. However, soon you can walk upright, and you ready yourself for whatever lies in the center of this alien network.",
            },
          ],
          rulesNow: [
            "Smaller side corridors become too narrow to traverse.",
            "Caretakers click when the party passes, alerting brethren and the guardian.",
            "Attacking caretakers in narrow corridors: they withdraw deeper into the inaccessible network.",
          ],
          chips: [{ label: "Root corridors", nodeId: "location:root-corridors" }],
        },
      ],
    },
    {
      id: "marrow",
      title: "The Marrow",
      order: 7,
      branchKind: "linear",
      intent: "Guardian + 2 caretakers. Helix sack. Resin greed risk.",
      readAloud:
        "You reach a large chamber where many of the root-corridors converge. Sickly green light from a translucent sack cradled ~20 ft up in a wooden helix…",
      chips: [
        { label: "The Marrow", nodeId: "location:the-marrow" },
        { label: "Guardian", nodeId: "threat:guardian" },
      ],
      beats: [
        {
          id: "marrow-fight",
          title: "Guardian fight",
          kind: "spine",
          summary: "Guardian + 2 caretakers; movement at the corner of the eye.",
          atTable:
            "Central chamber: root-corridors converge. Wooden helix winds to the surface; translucent sack at 20 ft is the green light source.",
          readAlouds: [
            {
              text: "You reach a large chamber where many of the root-corridors converge. The room is faintly lit by a sickly green light, emanating from the center of the room. In the midst of this chamber, a large wooden helix structure winds itself through the ceiling, most likely reaching almost up to the surface. At a height of 20 feet, you see a large translucent sack which is the origin of the green light. The sack is cradled inside the wooden helix which forms a protective shell around it. Before you find the time to take a closer look, you notice movement from the corner of your eye.",
            },
          ],
          warnings: [
            "Fight: the guardian (Appendix A) and 2 caretakers.",
            "Guardian: large root-creature, four legs, iron-reinforced spear-like arms.",
          ],
          chips: [
            { label: "Guardian", nodeId: "threat:guardian" },
            { label: "Caretakers", nodeId: "threat:caretakers" },
            { label: "Child in the helix", nodeId: "npc:helix-child" },
          ],
          toolLinks: [{ label: "Open Combat", panel: "combat" }],
        },
        {
          id: "marrow-resin",
          title: "Resin harvest",
          kind: "spine",
          summary: "Cut helix → metal resin. Greed can collapse the village.",
          atTable:
            "After enemies fall, investigate the glowing sack. Cutting the helix releases liquid gold, silver, and platinum that hardens like resin in air.",
          rulesNow: [
            "Safe harvest: 200 gp metal resin.",
            "Greedy extra +200 gp → DC 10 Strength (Athletics) to escape.",
            "Fail = buried; Hempholm can collapse into the void.",
          ],
          warnings: [
            "More harvest risks village-destroying collapse.",
          ],
          treasure: [
            "Safe: 200 gp metal resin from the helix cuts.",
            "Greedy +200 gp possible before collapse risk triggers.",
          ],
          ifTheyFail: ["Buried in collapsing root chamber; Hempholm falls in."],
          chips: [
            { label: "The Marrow", nodeId: "location:the-marrow" },
            { label: "Child in the helix", nodeId: "npc:helix-child" },
          ],
        },
      ],
    },
    {
      id: "child",
      title: "Fate of the child",
      order: 8,
      branchKind: "linear",
      intent: "GM-only until they cut the sack. Metal-eater blank slate. Village wants it gone.",
      gmNote: "Do not read the child's nature as boxed text at the garden.",
      chips: [
        { label: "Child in the helix", nodeId: "npc:helix-child" },
        { label: "Nar Granitetooth", nodeId: "npc:nar-granitetooth" },
        { label: "Saladin", nodeId: "npc:saladin" },
      ],
      beats: [
        {
          id: "cut-sack",
          title: "Cut the sack",
          kind: "spine",
          summary: "Toddler of bark/stone/metal blood; needs metal to grow.",
          atTable:
            "Inside the sack: a toddler with green skin, partly bark and stone. Must consume metal to grow — simple iron will do. Magical amalgam; blank slate alignment depends on the party's teachings.",
          gmNote:
            "No ascertainable sex. Growth is rapid. Do not reveal this at the garden — only after they cut the helix.",
          ifTheySucceed: [
            "Child emerges alive but not fully grown.",
            "Party may take the toddler with them.",
          ],
          chips: [{ label: "Child in the helix", nodeId: "npc:helix-child" }],
        },
        {
          id: "child-handoff",
          title: "Handoff",
          kind: "optional",
          summary: "Nar or Saladin will take it; village may demand they leave.",
          atTable:
            "If villagers glimpse the creature, they thank the heroes but insist they leave immediately — enough magic for one lifetime. Nar and Saladin will care for the child if asked.",
          ifTheyWait: [
            "Village demands the party depart as soon as possible.",
          ],
          chips: [
            { label: "Nar Granitetooth", nodeId: "npc:nar-granitetooth" },
            { label: "Saladin", nodeId: "npc:saladin" },
            { label: "Child in the helix", nodeId: "npc:helix-child" },
          ],
        },
      ],
    },
    {
      id: "epilogue",
      title: "Epilogue",
      order: 9,
      branchKind: "linear",
      intent: "Reputation in Greenest/Berdusk; Paelias later erases evidence.",
      chips: [
        { label: "Paelias Sian", nodeId: "npc:paelias-sian" },
        { label: "Baldur's Gate mages' guild", nodeId: "faction:baldurs-gate-mages-guild" },
      ],
      beats: [
        {
          id: "gratitude",
          title: "Hempholm's gratitude",
          kind: "optional",
          summary: "Heroes or villains — word travels to Greenest and Berdusk.",
          atTable:
            "Depending on actions, villagers treat them as heroes or accursed villains. Word reaches Greenest and Berdusk — ruined reputation or ale on the house.",
          gmNote:
            "A CR 1 NPC is about as strong as a level 3 character. A deadly fight is survivable for a fresh party; a second hard/medium fight after it can kill people.",
        },
        {
          id: "paelias",
          title: "Agent of the guild",
          kind: "optional",
          summary: "Paelias comes later to erase under-village evidence.",
          atTable:
            "Paelias Sian (N male elf, mage MM 347 with only 1st–2nd level spells) investigates, pays off witnesses, acquires intel on the party and the tree's child. Goal: erase all evidence including the offspring.",
          readAlouds: [
            {
              text: "Naturally, the mages' guild which is responsible for the creation of the conk is highly interested in erasing any evidence of the matter. A wizard named Paelias Sian is sent to investigate the matter, pay off any witnesses, and destroy the tree. Paelias quickly finds out about the occurrences in Hempholm and visits the village. He pays reparations to the affected families in return for their silence, and acquires information about the characters and the tree's child. Paelias pursues the characters and catches up eventually.",
            },
          ],
          ifTheyWait: [
            "If the child is with Nar, she catches up before Paelias and briefs the party.",
          ],
          chips: [
            { label: "Paelias Sian", nodeId: "npc:paelias-sian" },
            { label: "Baldur's Gate mages' guild", nodeId: "faction:baldurs-gate-mages-guild" },
          ],
        },
      ],
    },
  ],
};

export type PlayRunBranchSnapshot = {
  hook?: "hill" | "alchemist" | "guild" | null;
  aftermath?: "celebration" | "fire" | null;
};

/** Scenes visible in the deck given current branch choices. */
export function visibleScenesForBranch(
  spine: AdventureSpine,
  branch: PlayRunBranchSnapshot,
): AdventureScene[] {
  return spine.scenes
    .filter((scene) => {
      if (!scene.requiresAftermath) return true;
      if (!branch.aftermath) {
        // Until aftermath chosen, hide both exclusive aftermath slides.
        return false;
      }
      return scene.requiresAftermath === branch.aftermath;
    })
    .slice()
    .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}

export function sceneById(spine: AdventureSpine, sceneId: string): AdventureScene | null {
  return spine.scenes.find((s) => s.id === sceneId) ?? null;
}

export function beatById(
  spine: AdventureSpine,
  beatId: string,
): { scene: AdventureScene; beat: AdventureBeat } | null {
  for (const scene of spine.scenes) {
    const beat = scene.beats.find((b) => b.id === beatId);
    if (beat) return { scene, beat };
  }
  return null;
}
