/**
 * Of Conks play projection bodies for Reference Play Object Sheets.
 * Table-facing copy only — not graph canon. Threats stay on ThreatSheetProjection.
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
  },
  "faction:baldurs-gate-mages-guild": {
    kind: "faction",
    atTable:
      "Baldur’s Gate mages’ guild — sends Paelias Sian later to erase evidence of the under-village secrets.",
    attitude: "Aftermath institutional pressure, not opening cast.",
    offersHooks: ["Foreground only after the child / Marrow secrets are in play."],
    connectedNow: [{ label: "Paelias Sian", nodeId: "npc:paelias-sian" }],
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
