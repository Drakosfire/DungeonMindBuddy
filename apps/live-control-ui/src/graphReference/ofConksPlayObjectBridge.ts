/**
 * Of Conks play projection bodies for Reference Play Object Sheets.
 * Table-facing digests aid scanning; sourceBlocks + provenance are the fidelity contract.
 * Threats stay on ThreatSheetProjection.
 *
 * Content placement (audit):
 * - Sheet `rulesNow` / hooks: Maglubiyet charges, Shacks celebration+fire, Marrow chamber,
 *   Nar Sarni beat, Belly’s prize, gem/contest pointers.
 * - Packet strips: Side jobs, Aftermath, alt hooks (importer).
 * - Build only: DM essays, Greenfields lore dump, Bill as node, Paelias combat.
 */

export type PlayObjectKind = "npc" | "location" | "item" | "faction";

export type PlayObjectConnectedChip = {
  label: string;
  nodeId: string;
};

/** Stable Play chrome panel targets (Layer 3). */
export type PlayObjectToolLink = {
  label: string;
  /** Play panel id → `/play/{panel}`. */
  panel: "items" | "roll" | "combat" | "statblocks";
};

/** Verbatim module prose for the sheet (do not paraphrase). */
export type PlayObjectSourceBlock = {
  heading?: string | null;
  text: string;
};

/** Exact locator into the Of Conks extract / Play beats. */
export type PlayObjectProvenance = {
  /** PDF / extract heading (prefer ofConksHempholmPdfHomes strings). */
  pdfHeading: string;
  /** Optional page labels from the extract, e.g. "7–8". */
  pages?: string | null;
  /** Related Play beat ids for cross-nav context. */
  beatIds?: string[] | null;
};

export type PlayObjectBody = {
  kind: PlayObjectKind;
  /** Primary run voice / arrival feel (2–4 sentences). */
  atTable: string;
  /** Mood, rivalry, scene pressure. */
  attitude?: string | null;
  /** Inventory, checks, optional beats. */
  offersHooks?: string[] | null;
  /** Mid-session RULES the GM needs while this node is open. */
  rulesNow?: string[] | null;
  /** Curated chips that matter now (not full adjacency). */
  connectedNow: PlayObjectConnectedChip[];
  /** One-line jumps into Play tool panels. */
  toolLinks?: PlayObjectToolLink[] | null;
  /** Full module prose when it fits; omit only when provenance alone is enough. */
  sourceBlocks?: PlayObjectSourceBlock[] | null;
  /** Required: never leave a sheet looking sourceless. */
  provenance: PlayObjectProvenance;
};

const BY_NODE_ID: Readonly<Record<string, PlayObjectBody>> = {
  "npc:morwin-blackwell": {
    kind: "npc",
    atTable:
      "Old shopkeep of the only store in Hempholm. Bad eyes and ears — he often mistakes the characters for someone else. Dusty, untidy, appears to doze behind the counter with hair shooting from nose and ears.",
    attitude:
      "Black mood since Saladin arrived. Curses Saladin’s name in every other muttered sentence.",
    offersHooks: [
      "Sells Adventuring Gear worth 10 gp or less (PHB) plus basic farming equipment.",
      "Household hemp; personal blends Green Cracker and Ancient Green Dragon.",
      "Gem job: ten uncut stones (asks dwarves to cut for 20 gp). DC 10 Jeweler’s Tools — two are tourmalines worth 100 gp each once cut (rest blue quartz, 2 gp each).",
      "Banter seed if no dwarf: villagers joke that Morwin thinks all dwarves cut gems.",
    ],
    connectedNow: [
      { label: "Morwin's", nodeId: "location:morwins-store" },
      { label: "Saladin", nodeId: "npc:saladin" },
      { label: "Hempholm", nodeId: "location:hempholm" },
    ],
    sourceBlocks: [
      {
        heading: "Area 2: The Store",
        text: "The only store in Hempholm—popularly called Morwin’s—is run by Morwin Blackwell. Morwin is an old man and has problems with his eyes and ears. He will often mistake the characters for someone else if they find their way to his shop. Morwin is in a black mood since Saladin arrived in Hempholm and he curses Saladin’s name in every other sentence he mutters.\n\nItems For Sale. The shop offers items from the Adventuring Gear table which are worth 10 gp or less (PHB 150) and basic farming equipment. Additionally, Morwin sells potent hemp in household quantities and offers his personal blends Green Cracker and Ancient Green Dragon.",
      },
      {
        heading: "Diamonds In the Rough",
        text: "Morwin Blackwell recently acquired a handful of uncut gems. He traded an old amulet he had laying around against 10 uncut blue quartz crystals—each worth 2 gp. Morwin asks each and every dwarf he encounters if they could cut the stones for him and offers 20 gp for the service. If there is no dwarf among the characters to initiate the encounter, consider adding banter of the village people who joke about Morwin’s funny idea that all dwarfs are into gems. A character must succeed in a DC 10 Dexterity (Jeweler’s Tools) check to properly cut one of the gems. During the work, the responsible character notices that two of the gems are not blue quartz but tourmalines worth 100 gp each—once properly cut.",
      },
    ],
    provenance: {
      pdfHeading: "Area 2: The Store",
      pages: "9, 12",
      beatIds: ["morwin-store", "gem-job"],
    },
  },
  "npc:nar-granitetooth": {
    kind: "npc",
    atTable:
      "Cursing dwarf in The Shacks who wants more ale. First impression: a peasant with a noggin-shaped nose flying out the door, then Nar’s sweet cursing.",
    attitude:
      "Grief-drunk since her daughter Sarni was murdered by a brigand they had rescued. Wastes away in The Shacks; trashes locals who get chummy. Can be pulled back toward Sharindlar (healing, fertility, mercy; priests Thalornor; symbol: burning needle).",
    offersHooks: [
      "DC 20 Charisma (Persuasion) + Religion proficiency to win her toward Sharindlar.",
      "Later, wounded villagers: DC 15 Persuasion, or DC 10 Religion if they appeal to her faith.",
      "Helps freely once already won over. Carry mauled axe-villagers to her.",
      "Will take the metal-eating child if the village wants it gone.",
    ],
    connectedNow: [
      { label: "The Shacks", nodeId: "location:the-shacks" },
      { label: "Hempholm", nodeId: "location:hempholm" },
    ],
    sourceBlocks: [
      {
        heading: "The Dwarven Lady",
        text: "One grim customer in the Shacks never rests her mug-arm: A dwarf who gives visitors the evil eye if they dare to approach her. Nar Granitetooth (NG female dwarf priest MM 348) is a perpetually drunk dwarven woman who lost her daughter and will to carry on. In the olden times, Nar and her child Sarni were simple wanderers who healed for board and lodging. One day, Sarni fell victim to a murderer they rescued from a roving band of brigands.\n\nThe monster slit Sarni’s throat during the night, stole her gold, and tried to pull the same stunt with Nar. She managed to slay her assailant, but for Sarni, help came too late. Since then Nar wastes away in the Shacks and trashes the locals if they grow too chummy. A character who is proficient in Religion can set Nar straight with a successful DC 20 Charisma (Persuasion) check. Thereupon Nar bethinks her convictions and the teachings of Sharindlar and considers going back to her wandering life. Additionally, she looks upon the characters kindly.",
      },
      {
        heading: "Sharindlar",
        text: "Sharindlar is the dwarven goddess of healing, fertility, life, and mercy. Sharindlar’s priests are known as Thalornor which means those who are merciful. Her symbol is that of a burning needle.",
      },
      {
        heading: "Later in the adventure",
        text: "The villagers ask the characters to help carry these brave souls to Nar who might be able to stop the bleeding. However, Nar is only willing to help after a character succeeds in a DC 15 Charisma (Persuasion) check. A character who appeals to her faith and dedication to her god must succeed in a DC 10 Intelligence (Religion) check to secure her help. Nar helps of her own accord, if the characters managed to get into her good graces before.\n\nBoth Nar and Saladin would care for the child should the characters ask for their help.\n\nShould the characters have given the child into the care of a different person like Nar, she will catch up to them before Paelias arrives and get the characters up to speed.",
      },
    ],
    provenance: {
      pdfHeading: "Area 1: The Shacks",
      pages: "7–8, 13, 16–17",
      beatIds: ["shacks-arrival", "axe-villagers", "cut-sack", "paelias"],
    },
  },
  "npc:saladin": {
    kind: "npc",
    atTable:
      "Optional recurring merchant. Wagon in the village square — considerably larger inside than out (bag of holding; ~10,000 gp of stock).",
    attitude:
      "Morwin hates him. Useful rival pressure in town. Unbidden thoughts are GM color, not a puzzle.",
    offersHooks: [
      "Sold out except Maglubiyet’s Statue (500 gp).",
      "Will take the metal-eating child if the village wants it gone.",
    ],
    connectedNow: [
      { label: "Saladin's Mobile Emporium", nodeId: "location:saladins-wagon" },
      { label: "Maglubiyet’s Statue", nodeId: "item:maglubiyets-statue" },
      { label: "Morwin Blackwell", nodeId: "npc:morwin-blackwell" },
    ],
    sourceBlocks: [
      {
        heading: "Area 3: Saladin’s Wagon",
        text: "Saladin (N male elf mage MM 347) is a traveling merchant who stopped in Hempholm to stock up on tradable goods and to rest. His wagon is approximately 10 feet high, 12 feet long, and 8 feet wide. On the inside, it can stretch for 600 feet in each possible direction. Saladin was a well-respected mage in the past but is now almost forgotten. He is well past his prime, almost 500 years old, and is often visited by unbidden thoughts. Where other elves turn inward and return to their home and family in old age, Saladin created a home for himself on the road. He decided to spend his last centuries as a simple trader who travels the world. The friendships and rivalries he forges on his journey invigorate him, he hopes, and ward off the calcification of his mind.\n\nOn the Record. Saladin often ceases talking mid-sentence, draws out a small notebook, and notes the unbidden thoughts that come to him. He intends to collect all the unbidden thoughts he has, to allow scholars to piece together a complete story or cross-reference with other records. Upon request, Saladin explains the concept of unbidden thoughts and his reasoning behind the notes.\n\nA Traveling Merchant’s Lack of Wares. Saladin sold out his stock and looks to buy. He will acquire almost anything and pays fair prices to boot. With around 10,000 gp securely stored in his bag of holding he won’t run out of coin soon. Saladin has only one item left which is Maglubiyet’s Statue (Appendix B). He looted from the corpse of a hobgoblin priest and would part with it for the measly price of 500 gp. The disgusting looking statue which seems to ooze blood stands right next to him on Saladin’s desk.",
      },
      {
        heading: "Unbidden Thoughts",
        text: "When elves reach a high age or lead an exciting life of adventure, they are inevitably visited by unbidden thoughts—allegedly arbitrary memories of past lives or hallucinations of unknown origin. These unbidden thoughts mark an upheaval in the life of an elf and are regarded as a blessing by most and as a burden by some.",
      },
      {
        heading: "Later in the adventure",
        text: "Both Nar and Saladin would care for the child should the characters ask for their help.",
      },
    ],
    provenance: {
      pdfHeading: "Area 3: Saladin’s Wagon",
      pages: "9–10, 16",
      beatIds: ["saladin-wagon", "cut-sack"],
    },
  },
  "npc:mark-jove": {
    kind: "npc",
    atTable:
      "Father at the house whose garden holds the grotesque tree. Blames his son for bringing a bewitched ’tato home.",
    attitude: "Angry, frightened homeowner whose problem is literally in the yard.",
    offersHooks: [
      "Read-aloud beat: “…My stupid boy brought this bewitched 'tato home…”",
      "The tree is the visible problem; it is not the whole problem.",
    ],
    connectedNow: [
      { label: "Torbin Jove", nodeId: "npc:torbin-jove" },
      { label: "The Jove's Home", nodeId: "location:jove-home" },
      { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
    ],
    sourceBlocks: [
      {
        heading: "Area 4: The Jove's Home",
        text: "Most of the village's buildings are arranged in a circle around the village square, the house of the Jove's being one of them. The grotesque tree occupies the garden directly behind the house. The house itself took some damage due to the wild nature of the tree, and the boy Torbin is occupied with roof repairs. The characters encounter Mark Jove when they enter or knock. Mark is the father of Torbin, who is the boy who bought the magical conk. Mark is a fair bit distraught and tells the characters the following:\n\nMark Jove. By the gods, did you see the tree growing behind our home? We have enough problems already. I hope you are not here to add anything to it! My stupid boy brought this bewitched 'tato home and now look at it! A tree two stories high which attacks everything in sight. Now I can't even harvest the vegetables I grew. We will starve before the winter finds the time to come around! He planted it just the day before. I don't even want to think about its size when the morrow comes! You look like the adventuring sort, can't you figure this out somehow? Then we can talk about a reward. The whole village will chip in; I'm sure of it!",
      },
    ],
    provenance: {
      pdfHeading: "Area 4: The Jove's Home",
      pages: "10",
      beatIds: ["jove-plea"],
    },
  },
  "npc:torbin-jove": {
    kind: "npc",
    atTable:
      "Mark’s son. Thought the strange ’tato would feed the whole family. The tree now towers in their garden.",
    attitude: "Naive, defensive — the disaster started with his “good idea.”",
    offersHooks: [
      "Read-aloud beat: “…this strange 'tato will be enough to feed my whole family…”",
      "Told Pa to burn it; Pa warned they’d torch the village if careless.",
      "Bought it from a friendly little man on the market (Lord Fiddlestick trail).",
    ],
    connectedNow: [
      { label: "Mark Jove", nodeId: "npc:mark-jove" },
      { label: "The Jove's Home", nodeId: "location:jove-home" },
      { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
      { label: "Lord Fiddlestick", nodeId: "npc:lord-fiddlestick" },
    ],
    sourceBlocks: [
      {
        heading: "Torbin Jove",
        text: "Torbin Jove tells the characters the following in case they speak to him:\n\nTorbin Jove. By golly! You look like real adventurers! Are you here to fell that tree in our garden? I think my pa will chase me out of the village if nothing is done! I can't tell you anything useful, honest! There was this little man on the market, and he was very friendly. He told me that this strange 'tato will be enough to feed my whole family for the span of a year. But now this... I told my pa to just burn it down. But he warned me that we would put the whole village to the torch if we are not careful. And I'm never careful, or so he says.",
      },
    ],
    provenance: {
      pdfHeading: "Area 4: The Jove's Home",
      pages: "10",
      beatIds: ["jove-plea"],
    },
  },
  "npc:paelias-sian": {
    kind: "npc",
    atTable:
      "Agent of the Baldur’s Gate mages’ guild. Comes later to erase evidence of what happened under Hempholm.",
    attitude: "Cleanup, not a first-session ally. Do not foreground until aftermath.",
    offersHooks: [
      "Aftermath pressure after the child / Marrow secrets surface.",
    ],
    connectedNow: [
      { label: "Baldur’s Gate mages’ guild", nodeId: "faction:baldurs-gate-mages-guild" },
      { label: "Child in the helix", nodeId: "npc:helix-child" },
    ],
    sourceBlocks: [
      {
        heading: "An Agent of the Mages’ Guild",
        text: "Naturally, the mages’ guild which is responsible for the creation of the conk is highly interested in erasing any evidence of the matter. A wizard named Paelias Sian (N male elf) is sent to investigate the matter, pay off any witnesses, and destroy the tree. Paelias Sian has the statistics of a mage (MM 347), except that he has only access to 1st and 2nd level spells. Paelias quickly finds out about the occurrences in Hempholm and visits the village. He pays reparations to the affected families in return for their silence, and acquires information about the characters and the tree’s child. Paelias pursues the characters and catches up eventually. Should the characters have given the child into the care of a different person like Nar, she will catch up to them before Paelias arrives and get the characters up to speed. Paelias’ goal is to erase any evidence, including the strange offspring.",
      },
    ],
    provenance: {
      pdfHeading: "An Agent of the Mages’ Guild",
      pages: "16–17",
      beatIds: ["paelias"],
    },
  },
  "npc:helix-child": {
    kind: "npc",
    atTable:
      "GM-only until they cut the sack. Metal-eater, blank slate. Village wants it gone.",
    attitude: "Do not read the child’s nature as boxed text at the garden.",
    offersHooks: [
      "Nar or Saladin will take it if the table looks for a hand-off.",
      "Paelias Sian comes later to erase evidence.",
    ],
    connectedNow: [
      { label: "The Marrow", nodeId: "location:the-marrow" },
      { label: "Nar Granitetooth", nodeId: "npc:nar-granitetooth" },
      { label: "Saladin", nodeId: "npc:saladin" },
      { label: "Paelias Sian", nodeId: "npc:paelias-sian" },
    ],
    sourceBlocks: [
      {
        heading: "The Fate of the Child",
        text: "In case the characters decide to cut the child out of the helix and open the strange cocoon, the child emerges alive and well but not fully grown. To become a proper adult it must consume metal, no matter what—simple iron will do. It's a magical creature, an amalgam of earth, wood, and metallic blood. Its growth will be quite rapid and it has no ascertainable sex and since it's a blank slate it will quickly learn. Its ultimate alignment depends on the characters’ teachings.\n\nIf the villagers catch a glimpse of the strange creature the characters dug out of the earth, they tell the characters that they are thankful, but the characters need to leave the village as soon as possible. They had their share of magic, and it’s high time that peace returns to the village. Both Nar and Saladin would care for the child should the characters ask for their help.",
      },
    ],
    provenance: {
      pdfHeading: "The Fate of the Child",
      pages: "16",
      beatIds: ["cut-sack"],
    },
  },
  "npc:lord-fiddlestick": {
    kind: "npc",
    atTable:
      "Gnomish bard, hasardeur, sneak thief, entrepreneur. Lifted an enchanted tubercle (the conk) from a traveling alchemist’s rucksack, then fenced it to Torbin Jove at Greenest’s market with promises of fertility and prosperity. Not required for the default hill arrival — open this when the table digs into how the crisis started.",
    attitude:
      "Optional lore pressure. He already sold the package and moved on; the boy and the tree are the live problem.",
    offersHooks: [
      "Guild / alchemist hooks lead here before Hempholm.",
      "Pair with the conk; Torbin bought it from “a friendly little man” on the market.",
    ],
    connectedNow: [
      { label: "the conk", nodeId: "item:the-conk" },
      { label: "Torbin Jove", nodeId: "npc:torbin-jove" },
      { label: "The Shacks", nodeId: "location:the-shacks" },
    ],
    sourceBlocks: [
      {
        heading: "Adventure Background",
        text: "Lord Fiddlestick—a gnomish bard, hasardeur, sneak thief, and entrepreneur—lifted a strange tubercle from a traveling alchemist’s rucksack. In the face of this disappointment—A potato? What has my life become!—Lord Fiddlestick decided to rip off a hapless farm boy at Greenest's market. He only needed a mere fraction of a second to make out his mark: A simple boy who understood the fields and the earth, but not the cruelty of man. With promises of great fertility and prosperity, Lord Fiddlestick sold the alleged magical tuber for an outrageous price. The boy gave away all of the day's earnings with which he should have bought provisions for his ever-growing family. Winter was fast approaching, and with the new baby girl Laura, the family had another mouth to feed! Little did Lord Fiddlestick know, that the take was an enchanted plant indeed, ready for its first field test in one of the Greenfields’ many provincial backwaters.",
      },
      {
        heading: "In Service of the Guild",
        text: "You tracked down the culprit—a gnome who calls himself Lord Fiddlestick—but he already sold the package to a hapless boy! Fortunately, the boy told the thief about the village he hails from.",
      },
    ],
    provenance: {
      pdfHeading: "Adventure Background",
      pages: "5",
      beatIds: ["hook-guild"],
    },
  },
  "location:the-shacks": {
    kind: "location",
    atTable:
      "Largest building on the outskirts — main tavern/inn plus free huts for travelers (furnished rooms for a few coins). Soup kitchen and tavern serve nothing fancy. Bill the Belly (prose-only proprietor) hosts Meal n’ Moonshine. Opening beat can dump a peasant with a noggin-shaped nose through the door into Nar’s cursing; the rube mounts his donkey and hightails.",
    attitude: "Celebration hub after a surface-tree “victory”; also where false victory turns. Fire refugees move here if homes burn.",
    offersHooks: [
      "Meal n’ Moonshine: cook’s utensils or brewer’s supplies. 1d6+2 NPC contenders each roll d20 (no bonus); PCs roll with proficiency edge. Tie → cook/brew-off. Prize: Belly’s Mouthwash.",
      "Children beg for stories and may borrow weapons to reenact the deed on the hill north of The Shacks.",
      "Never Split the Party: overnight pairings disperse the party before caretakers hit.",
      "Name improvised villagers — open Play → Roll (Hempholm names).",
    ],
    rulesNow: [
      "Celebration drinking: DC 10 Constitution each hour or poisoned (mild → near useless).",
      "Firefighting: DC 12 Strength (Athletics) or gain 1 level of exhaustion; d4 houses destroyed.",
      "Do not telegraph the caretaker second fight from here.",
    ],
    connectedNow: [
      { label: "Nar Granitetooth", nodeId: "npc:nar-granitetooth" },
      { label: "Belly’s Mouthwash", nodeId: "item:bellys-mouthwash" },
      { label: "Hempholm", nodeId: "location:hempholm" },
      { label: "Caretakers", nodeId: "threat:caretakers" },
    ],
    toolLinks: [{ label: "Open names on Roll", panel: "roll" }],
    sourceBlocks: [
      {
        heading: "Area 1: The Shacks",
        text: "You stand in front of the village’s largest building when a peasant with an oddly noggin-shaped nose flies through the door out into the cold. Following this display, you hear the sweet sound of a cursing dwarf who demands more ale. After that, the evicted rube gets up, mounts his donkey, and hightails.\n\nThe so-called Shacks consist of a large building and a number of huts on the outskirts of Hempholm. Travelers and migrant workers may stay in the huts free of charge or pay a few coins for a furnished room in the main building. A small soup kitchen and a tavern can be found inside the main building, but they serve nothing fancy. The quality matches the coin, or so they say. Nevertheless, if you need a roof over your head and some comfort in your veins, this is the place to go.",
      },
      {
        heading: "Competition in the Shacks",
        text: "Bill the Belly—the proprietor of the tavern located in the main building of the Shacks—regularly hosts the big “Meal n’ Moonshine” competition. Travelers and residents are invited to serve their best dish or homebrew spirit to sway the Belly’s judgment in their favor. The winner receives a bottle of Belly’s Mouthwash (Appendix B). Characters who are proficient with either cook’s utensils or brewer’s supplies are allowed to enter and must outdo the competition. There are 1d6+2 contenders besides the characters and you must roll a d20 for each of them to determine the quality of their entry. The characters have a slight edge since the contenders add no bonus to their roll. A tie is broken by an additional cook- or brew-off.",
      },
      {
        heading: "A Premature Celebration",
        text: "If the characters manage to destroy the tree without burning down the village, the villagers gather and throw an impromptu party in the Shacks. The characters are treated as heroes and the villagers serve the best food, ale, and spirits they have to offer. The village children swarm the characters, begging them for exciting stories. Additionally, the children ask whether they can play with the characters’ weapons to reenact their heroic deed. In case the characters grant their wish, the children run off to the hill north of the Shacks, where they fight against an innocent and unsuspecting tree.\n\nHop & Malt. During the course of the celebration, the characters are to be subjected to Constitution saving throws to ward off the effects of the consumed alcohol, if they decide to partake of it. In general, a character must make a DC 10 Constitution saving throw for each hour of drinking. On a failed save, the character is poisoned. Interpret this as a character going from a state of mild drunkenness to near uselessness.\n\nNever Split the Party. Some of the villagers might elect to spend the night with one of the characters if this seems appropriate considering your group of players. If the characters are dispersed during the course of the night, the following attack will seem all the more threatening.\n\nThe Coming Storm. During the celebration, it is crucial that the players do not suspect that something is awry. As the DM you will have to show no malicious joy when the players let their characters get careless. Some players might suspect that there might be more to the adventure because everything went over rather smooth and fast. Placate them by hinting at what else might lie before them.",
      },
      {
        heading: "Hempholm Caught Fire?",
        text: "In case the characters cause a fire in the village they are tied up extinguishing the flames which threaten to burn down the village—unless they decide to make a run for it. This is taxing work and the characters must succeed in a DC 12 Strength (Athletics) check or gain 1 level of exhaustion. Roll a d4 to determine how many houses are destroyed during the conflagration. The former inhabitants move into the Shacks while they rebuilt their homes.",
      },
    ],
    provenance: {
      pdfHeading: "Area 1: The Shacks",
      pages: "7–8, 12–14",
      beatIds: ["shacks-arrival", "meal-moonshine", "celebration-party", "never-split", "firefighting"],
    },
  },
  "location:morwins-store": {
    kind: "location",
    atTable:
      "The only store in Hempholm — dusty and untidy, popularly called Morwin’s. Interior matches its proprietor.",
    attitude: "Local commerce under Saladin’s shadow.",
    offersHooks: [
      "Morwin runs the counter; gear and hemp live here.",
      "Gem-cutting job plays out at the counter if a dwarf (or jeweler) engages.",
    ],
    connectedNow: [
      { label: "Morwin Blackwell", nodeId: "npc:morwin-blackwell" },
      { label: "Hempholm", nodeId: "location:hempholm" },
    ],
    sourceBlocks: [
      {
        heading: "Area 2: The Store",
        text: "The store’s interior is dusty and untidy much like its proprietor. Bundles of hair shoot out of the old man’s nose and ears and he appears to be sleeping behind the counter.\n\nThe only store in Hempholm—popularly called Morwin’s—is run by Morwin Blackwell. Morwin is an old man and has problems with his eyes and ears. He will often mistake the characters for someone else if they find their way to his shop. Morwin is in a black mood since Saladin arrived in Hempholm and he curses Saladin’s name in every other sentence he mutters.\n\nItems For Sale. The shop offers items from the Adventuring Gear table which are worth 10 gp or less (PHB 150) and basic farming equipment. Additionally, Morwin sells potent hemp in household quantities and offers his personal blends Green Cracker and Ancient Green Dragon.",
      },
    ],
    provenance: {
      pdfHeading: "Area 2: The Store",
      pages: "9",
      beatIds: ["morwin-store", "gem-job"],
    },
  },
  "location:saladins-wagon": {
    kind: "location",
    atTable:
      "Wagon smack in the middle of Hempholm’s square — bigger inside than out. Golden letters; kaleidoscope paint.",
    attitude: "Transient market pressure; Morwin’s rival pitch.",
    offersHooks: [
      "Stock is sold out except Maglubiyet’s Statue (500 gp).",
    ],
    connectedNow: [
      { label: "Saladin", nodeId: "npc:saladin" },
      { label: "Maglubiyet’s Statue", nodeId: "item:maglubiyets-statue" },
      { label: "Hempholm", nodeId: "location:hempholm" },
    ],
    sourceBlocks: [
      {
        heading: "Area 3: Saladin’s Wagon",
        text: "A wagon stands smack in the middle of Hempholm’s village square so that no denizen or traveler is deprived of its ... beauty. The words ‘Saladin’s Mobile Emporium’ flaunt on the wagon’s sides in large golden letters and its coloration is reminiscent of a kaleidoscope. When you enter the gaudy vehicle, you notice that it’s considerably larger on the inside than on the outside. An elf clothed in a purple robe sits behind a small desk and expectantly raises his head when he notices your presence.\n\nHis wagon is approximately 10 feet high, 12 feet long, and 8 feet wide. On the inside, it can stretch for 600 feet in each possible direction.",
      },
    ],
    provenance: {
      pdfHeading: "Area 3: Saladin’s Wagon",
      pages: "9–10",
      beatIds: ["saladin-wagon"],
    },
  },
  "location:jove-home": {
    kind: "location",
    atTable:
      "Squat wood-and-clay house; small unglazed windows. Garden holds the two-story grotesque tree. Torbin may be on the roof repairing damage.",
    attitude: "Domestic crisis site — Mark and Torbin live the problem.",
    offersHooks: [
      "Clock 1: tree growth can smash this home and two neighbors.",
      "Tree site tactics live on the Grotesque Tree threat chip.",
    ],
    connectedNow: [
      { label: "Mark Jove", nodeId: "npc:mark-jove" },
      { label: "Torbin Jove", nodeId: "npc:torbin-jove" },
      { label: "Grotesque Tree (garden)", nodeId: "location:grotesque-tree-site" },
      { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
    ],
    sourceBlocks: [
      {
        heading: "Area 4: The Jove's Home",
        text: "The menacing tree stands right in the center of this house’s garden. Otherwise, the house is in no way different from the others in the village. It is squat, built of wood and clay, and the windows are small and unglazed.\n\nMost of the village's buildings are arranged in a circle around the village square, the house of the Jove's being one of them. The grotesque tree occupies the garden directly behind the house. The house itself took some damage due to the wild nature of the tree, and the boy Torbin is occupied with roof repairs. The characters encounter Mark Jove when they enter or knock. Mark is the father of Torbin, who is the boy who bought the magical conk.",
      },
    ],
    provenance: {
      pdfHeading: "Area 4: The Jove's Home",
      pages: "10",
      beatIds: ["jove-plea"],
    },
  },
  "location:grotesque-tree-site": {
    kind: "location",
    atTable:
      "The garden site of the grotesque tree. Bark like armor; thorned branches. Stranger the closer you get.",
    attitude: "Visible problem. Roots may already run under the village.",
    offersHooks: [
      "Passive Perception 15: metal leaves. Passive Arcana 12: aura. DC 17 Arcana: roots under the village.",
      "Treasure if they search: 100 gp precious metal leaves.",
      "Attacks anyone within 30 feet; stops when the threat leaves.",
    ],
    rulesNow: [
      "Fire vs tree now: d20 even = surrounding houses catch. Conflagration can consume the village if not doused.",
    ],
    connectedNow: [
      { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
      { label: "The Jove's Home", nodeId: "location:jove-home" },
      { label: "metal leaves", nodeId: "item:metal-leaves" },
      { label: "The Shacks", nodeId: "location:the-shacks" },
    ],
    sourceBlocks: [
      {
        heading: "Area 5: The Grotesque Tree",
        text: "The further you approach the tree, the stranger it appears. The tree’s bark looks as tough as any armor you’ve seen and the branches are covered in thick thorns.\n\nA character with a passive Wisdom (Perception) of 15 notices a handful of shiny leaves which grow from the odd branch. The leaves appear to be made of solid metal. A character with a passive Wisdom (Arcana) of 12 feels a magic aura around the grotesque tree.\n\nIf that character succeeds in a subsequent DC 17 Wisdom (Arcana) check, they determine that the tree is indeed infused with arcane magic and that a system of magic roots stretches beneath the village.\n\nMonsters & Tactics. The grotesque tree (Appendix A) attacks any creature that comes within 30 feet of it and retaliates against ranged attacks. It always targets the nearest enemy and ceases hostilities once it is no longer under imminent threat.\n\nTreasure. The characters find leaves made of precious metal worth 100 gp in case they search the former battleground.\n\nAdvancing the Adventure. When the characters eventually destroy the tree, continue with Part 2 of the adventure. Should the characters leave the tree and the village behind, they will soon hear of a tree that grew to be almost 300 feet tall, destroyed an entire village, and forces travelers on the Uldoon Trail to make a wide detour.",
      },
    ],
    provenance: {
      pdfHeading: "Area 5: The Grotesque Tree",
      pages: "11",
      beatIds: ["tree-tactics"],
    },
  },
  "location:hempholm": {
    kind: "location",
    atTable:
      "Hemp village (~80 in town, more on outlying farms). Specializes in durable Western Heartlands hemp bound for Greenest and Berdusk markets. Simple artisans (blacksmith, cobbler, carpenter) are commoners (MM 345) unless stated. A two-story attacking tree in the Jove garden is the visible problem — not the whole problem.",
    attitude: "Stall pressure advances the tree-growth clock.",
    offersHooks: [
      "Areas: Shacks, Morwin’s, Saladin’s wagon, Jove home, tree garden, then roots/Marrow.",
      "Side jobs: distillery at the blacksmith, gem job at Morwin’s, Meal n’ Moonshine at The Shacks.",
      "Greenfields region essay (size, travel, tone): open Build document “Of Conks & Cons v2.1” — not dumped into Beats.",
      "Name every improvised villager — Play → Roll (Appendix C).",
    ],
    connectedNow: [
      { label: "The Shacks", nodeId: "location:the-shacks" },
      { label: "Morwin's", nodeId: "location:morwins-store" },
      { label: "The Jove's Home", nodeId: "location:jove-home" },
      { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
    ],
    toolLinks: [{ label: "Open names on Roll", panel: "roll" }],
    sourceBlocks: [
      {
        heading: "Part 1: Enter Hempholm",
        text: "The following sections describe points of interest in Hempholm in more detail. Naturally, Hempholm features several simple artisans like a blacksmith, a cobbler, and a carpenter which aren’t worth mentioning. All villagers in Hempholm have the statistics of commoners (MM 345) unless otherwise stated. As the name suggests, Hempholm specializes in the cultivation of hemp. Hempholm’s peasants grow some of the most durable and strongest hemp in the Western Heartlands which finds its way to the marketplaces of Greenest and Berdusk. Around 80 people live in Hempholm proper and several dozens more in outlying farms that surround the village.",
      },
      {
        heading: "Appendix C: Tables",
        text: "This adventure includes tables (Appendix C) which list a number of random names for villagers the characters might encounter during their stay in Hempholm. Why is this noteworthy?—you may ask yourself. Even if you forget it after several weeks, the players will vividly remember the arbitrary shoeshine boy—and his three-legged dog—they met in front of the tavern that one time their characters got drunk. Thank the gods that you used the trusted random name table to note the name and background of that boy and his poor puppy!",
      },
    ],
    provenance: {
      pdfHeading: "Part 1: Enter Hempholm",
      pages: "7",
      beatIds: ["hook-hill", "shacks-arrival"],
    },
  },
  "location:root-corridors": {
    kind: "location",
    atTable:
      "Hollow root corridors under the village. Dank air; roots warm — more like stone or metal than wood.",
    attitude: "Descent after the surface false victory.",
    offersHooks: [
      "Leads toward The Marrow and the Guardian fight.",
      "Caretakers may watch from narrow roots and click-alert the Guardian.",
    ],
    connectedNow: [
      { label: "The Marrow", nodeId: "location:the-marrow" },
      { label: "Guardian", nodeId: "threat:guardian" },
    ],
    sourceBlocks: [
      {
        heading: "Down Into the Rabbit Hole",
        text: "To root out the threat beneath the village, the characters must descend into the root-corridors. Before their attack, the caretakers tore open large holes all over the village. These openings connect to various root-corridors which ultimately lead the characters right into the heart of the plant. Once the characters enter the root-system, paraphrase or read out loud:\n\nThe air down in these tunnels is dank, and the temperature is higher than you would have anticipated. The hollow roots are warm to the touch but feel more like stone or metal than wood. At first, you have to bend down to fit into these tunnels. However, soon you can walk upright, and you ready yourself for whatever lies in the center of this alien network.\n\nThe large hollow roots are dotted with smaller corridors which quickly become too narrow to traverse. Having learned their lesson, the caretakers watch the characters while they make their way through the root-corridors. The caretakers make clicking noises when the characters pass by, alerting their brethren and the guardian. When the characters try to attack any of the caretakers which hide in the narrow corridors, they withdraw deeper into the inaccessible network.",
      },
    ],
    provenance: {
      pdfHeading: "Down Into the Rabbit Hole",
      pages: "15",
      beatIds: ["rabbit-hole"],
    },
  },
  "location:the-marrow": {
    kind: "location",
    atTable:
      "Large chamber where root-corridors converge. Sickly green light from a translucent sack cradled ~20 ft up in a wooden helix that climbs toward the surface. Movement at the corner of the eye before anyone gets a closer look — Guardian + 2 caretakers.",
    attitude: "Endgame site for the under-village threat. Child in the helix is GM-only until they cut the sack.",
    offersHooks: [
      "Child in the helix is GM-only until they cut the sack.",
    ],
    rulesNow: [
      "Safe resin harvest: 200 gp metal resin.",
      "Greedy extra +200 gp → collapse risk → DC 10 Strength (Athletics) to escape or be buried; Hempholm can fall in.",
    ],
    connectedNow: [
      { label: "Hollow root corridors", nodeId: "location:root-corridors" },
      { label: "Guardian", nodeId: "threat:guardian" },
      { label: "Child in the helix", nodeId: "npc:helix-child" },
    ],
    sourceBlocks: [
      {
        heading: "The Marrow",
        text: "Once the characters make their way to the center of the root network, paraphrase or read out loud:\n\nYou reach a large chamber where many of the root-corridors converge. The room is faintly lit by a sickly green light, emanating from the center of the room. In the midst of this chamber, a large wooden helix structure winds itself through the ceiling, most likely reaching almost up to the surface. At a height of 20 feet, you see a large translucent sack which is the origin of the green light. The sack is cradled inside the wooden helix which forms a protective shell around it. Before you find the time to take a closer look, you notice movement from the corner of your eye.\n\nMonsters & Tactics. The characters are attacked by the guardian (Appendix A) and 2 caretakers. The guardian is a large creature made of roots who features four legs and iron reinforced spear-like arms.\n\nTreasure. After the enemies lie dead, the characters will eventually investigate the glowing sack. Inside they find a toddler with green skin, partly made of bark and stone. To reach the sack, the characters must cut through the wooden helix-structure that surrounds the toddler.\n\nOnce the characters damage the helix, an amalgam of liquid gold, silver and platinum oozes out of the cuts. The metal hardens as soon as it is exposed to the air much like resin. The characters can take the toddler with them if they so desire.\n\nThe characters are able to safely harvest metal resin worth 200 gp. If they decide to harvest more, the characters notice that the structural integrity of the helix is critical and any more damage may lead to a collapse. Since the room and the roots span below the entire village, Hempholm would be destroyed in such an event. Should the characters destroy the helix to harvest more metal, they gain additional metal worth 200 gp. After the central structures collapses, the characters must succeed in a DC 10 Strength (Athletics) check to escape the root-system. A character that fails is buried and the whole village of Hempholm collapses into the ground and is destroyed.",
      },
    ],
    provenance: {
      pdfHeading: "The Marrow",
      pages: "15–16",
      beatIds: ["marrow-fight", "cut-sack"],
    },
  },
  "item:maglubiyets-statue": {
    kind: "item",
    atTable:
      "Oaken Maglubiyet statue covered in blood that never dries. Saladin’s remaining stock — 500 gp. Eyes glow and battle-hunger washes over when fed fallen-enemy blood.",
    attitude: "Who wants it: buyers, cult curiosity, or Saladin’s markup. Requires attunement (rare).",
    offersHooks: ["Sold from Saladin’s Mobile Emporium in the square."],
    rulesNow: [
      "3 charges. Recover 1/day by covering it in the blood of a dead creature.",
      "Bonus action, spend 2 charges: cast fear on a single creature (Wisdom DC 15). No concentration.",
    ],
    connectedNow: [
      { label: "Saladin", nodeId: "npc:saladin" },
      { label: "Saladin's Mobile Emporium", nodeId: "location:saladins-wagon" },
    ],
    toolLinks: [{ label: "Open full text on Items", panel: "items" }],
    sourceBlocks: [
      {
        heading: "Maglubiyet’s Statue",
        text: "Wondrous item, rare (requires attunement)\n\nThis item has 3 charges and it can recover 1 charge per day by covering it in the blood of a dead creature. You can use a bonus action and expend 2 of its charges to cast the fear spell on a single creature. The DC for the corresponding Wisdom saving throw is 15 and you must not maintain concentration.\n\nThis oaken statue of Maglubiyet is completely covered in blood. No matter how long you wait, the blood will not dry. When you cover the statue in the blood of a fallen enemy its eyes glow, and you feel a wave of excitement and battle hunger wash over you. Weaker minds break under the Battle Lord's aura's terrible manifestation since its exceptionally strong.",
      },
    ],
    provenance: {
      pdfHeading: "Maglubiyet’s Statue",
      pages: "Appendix B",
      beatIds: ["saladin-wagon"],
    },
  },
  "item:bellys-mouthwash": {
    kind: "item",
    atTable:
      "Prize bottle from Bill the Belly’s Meal n’ Moonshine contest in The Shacks. Mighty swig → heroism.",
    attitude: "Contest prize — uncommon wondrous item. Consumed when charges run out.",
    offersHooks: [
      "Win Meal n’ Moonshine at The Shacks (cook’s utensils or brewer’s supplies).",
    ],
    rulesNow: [
      "4 charges; cannot be recovered. Last charge consumes the bottle.",
      "Bonus action, spend 1 charge: heroism for 10 minutes. Spellcasting ability modifier counts as 2; no concentration; cannot be dispelled.",
    ],
    connectedNow: [
      { label: "The Shacks", nodeId: "location:the-shacks" },
    ],
    toolLinks: [{ label: "Open full text on Items", panel: "items" }],
    sourceBlocks: [
      {
        heading: "Belly’s Mouthwash",
        text: "Wondrous item, uncommon\n\nThis item has 4 charges which cannot be recovered. After the last charge is used, the item is consumed. You can use a bonus action and expend 1 of its charges to take a mighty swig from the bottle after which you are under the effects of the heroism spell. Your spellcasting ability modifier counts as 2, you must not maintain concentration, the effect cannot be dispelled, and the effect lasts for 10 minutes.\n\nWhen you loosen the stopper of this bottle, the smell almost knocks you off your feet. This so-called mouthwash could etch paint off a stained glass window, you argue. Nevertheless, down the hatch, it goes!",
      },
    ],
    provenance: {
      pdfHeading: "Belly’s Mouthwash",
      pages: "Appendix B",
      beatIds: ["meal-moonshine"],
    },
  },
  "item:metal-leaves": {
    kind: "item",
    atTable:
      "Precious metal leaves on the grotesque tree — about 100 gp if the party searches after noticing them.",
    attitude: "Loot that also telegraphs the tree’s wrongness.",
    offersHooks: ["Passive Perception 15 to notice on the tree."],
    connectedNow: [
      { label: "Grotesque Tree (garden)", nodeId: "location:grotesque-tree-site" },
      { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
    ],
    sourceBlocks: [
      {
        heading: "Area 5: The Grotesque Tree",
        text: "A character with a passive Wisdom (Perception) of 15 notices a handful of shiny leaves which grow from the odd branch. The leaves appear to be made of solid metal.\n\nTreasure. The characters find leaves made of precious metal worth 100 gp in case they search the former battleground.",
      },
    ],
    provenance: {
      pdfHeading: "Area 5: The Grotesque Tree",
      pages: "11",
      beatIds: ["tree-tactics"],
    },
  },
  "item:the-conk": {
    kind: "item",
    atTable:
      "Background pin with Lord Fiddlestick — optional open if the table digs into origins.",
    attitude: "Not required for the hill-arrival opening.",
    offersHooks: ["Pair with Lord Fiddlestick / Shacks lore if hooks pull that way."],
    connectedNow: [
      { label: "Lord Fiddlestick", nodeId: "npc:lord-fiddlestick" },
      { label: "The Shacks", nodeId: "location:the-shacks" },
    ],
    sourceBlocks: [
      {
        heading: "Adventure Background",
        text: "Once the boy returned, he was beaten badly by his sire. In his despair, he planted the seed nevertheless. Lo and behold! Within a few days, a large tree grew rampant. Alas, the tree was not as docile as his conspecifics. It looked sickly, had no leaf to its name, and to add injury to insult, the tree attacks passers-by with its rock-hard branches!\n\nMeanwhile, the tree's roots dig greedily into the ground. Deep down, in the bowels of the earth, the roots harvest gold, silver, platinum and more. Slowly but surely, the tree transports these precious metals to the surface where they finally face the sun. A kin to the star they were born in eons and eons ago? By day and by night dutiful caretakers roam the network of hollow roots beneath the tree. They caress their holy mother, fight off rodents, and savor the smell of their home soil. Woe to you, if you decide to disturb their placid lives!\n\nThe conk’s true purpose is only known to few members of the Baldur’s Gate mages’ guild who elected the hinterlands of the Greenfields for a preliminary field test. Far away from prying eyes, the tree could have been studied without interference...",
      },
    ],
    provenance: {
      pdfHeading: "Adventure Background",
      pages: "5",
      beatIds: ["hook-alchemist", "hook-guild"],
    },
  },
  "faction:baldurs-gate-mages-guild": {
    kind: "faction",
    atTable:
      "Baldur’s Gate mages’ guild — sends Paelias Sian later to erase evidence of the under-village secrets.",
    attitude: "Aftermath institutional pressure, not opening cast.",
    offersHooks: ["Foreground only after the child / Marrow secrets are in play."],
    connectedNow: [{ label: "Paelias Sian", nodeId: "npc:paelias-sian" }],
    sourceBlocks: [
      {
        heading: "Adventure Background",
        text: "The conk’s true purpose is only known to few members of the Baldur’s Gate mages’ guild who elected the hinterlands of the Greenfields for a preliminary field test. Far away from prying eyes, the tree could have been studied without interference...",
      },
      {
        heading: "An Agent of the Mages’ Guild",
        text: "Naturally, the mages’ guild which is responsible for the creation of the conk is highly interested in erasing any evidence of the matter. A wizard named Paelias Sian (N male elf) is sent to investigate the matter, pay off any witnesses, and destroy the tree. Paelias Sian has the statistics of a mage (MM 347), except that he has only access to 1st and 2nd level spells. Paelias quickly finds out about the occurrences in Hempholm and visits the village. He pays reparations to the affected families in return for their silence, and acquires information about the characters and the tree’s child. Paelias pursues the characters and catches up eventually. Should the characters have given the child into the care of a different person like Nar, she will catch up to them before Paelias arrives and get the characters up to speed. Paelias’ goal is to erase any evidence, including the strange offspring.",
      },
    ],
    provenance: {
      pdfHeading: "An Agent of the Mages’ Guild",
      pages: "5, 16–17",
      beatIds: ["paelias"],
    },
  },
};

function normalizePlayObjectNodeId(nodeId: string): string {
  return nodeId.trim();
}

/** Resolve a play body for an Of Conks packet node, or null if none authored. */
export function playObjectBodyForNodeId(nodeId: string): PlayObjectBody | null {
  const key = normalizePlayObjectNodeId(nodeId);
  if (!key) return null;
  return BY_NODE_ID[key] ?? null;
}

export function hasOfConksPlayObjectBody(nodeId: string): boolean {
  return playObjectBodyForNodeId(nodeId) !== null;
}

/** All authored Of Conks play object node ids (test / inventory). */
export function ofConksPlayObjectNodeIds(): string[] {
  return Object.keys(BY_NODE_ID);
}
