/**
 * Of Conks play projection bodies for Reference Play Object Sheets.
 * Table-facing copy only — not graph canon. Threats stay on ThreatSheetProjection.
 */

export type PlayObjectKind = "npc" | "location" | "item" | "faction";

export type PlayObjectConnectedChip = {
  label: string;
  nodeId: string;
};

export type PlayObjectBody = {
  kind: PlayObjectKind;
  /** Primary run voice / arrival feel (2–4 sentences). */
  atTable: string;
  /** Mood, rivalry, scene pressure. */
  attitude?: string | null;
  /** Inventory, checks, optional beats. */
  offersHooks?: string[] | null;
  /** Curated chips that matter now (not full adjacency). */
  connectedNow: PlayObjectConnectedChip[];
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
      "Can be pulled back toward Sharindlar (healing, fertility, mercy; priests Thalornor; symbol: burning needle).",
    offersHooks: [
      "DC 20 Charisma (Persuasion) + Religion proficiency to win her toward Sharindlar.",
      "Later, wounded villagers: DC 15 Persuasion, or DC 10 Religion if they appeal to her faith.",
      "Helps freely once already won over. Carry mauled axe-villagers to her.",
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
    ],
    connectedNow: [
      { label: "Mark Jove", nodeId: "npc:mark-jove" },
      { label: "The Jove's Home", nodeId: "location:jove-home" },
      { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
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
      "Background pin tied to the conk and optional open threads — not required for the opening hill arrival.",
    attitude: "Optional lore pressure if the table digs into how this started.",
    offersHooks: ["Pair with the conk and The Shacks if hooks pull that way."],
    connectedNow: [
      { label: "the conk", nodeId: "item:the-conk" },
      { label: "The Shacks", nodeId: "location:the-shacks" },
    ],
  },
  "location:the-shacks": {
    kind: "location",
    atTable:
      "Largest building in the village — tavern/inn energy. Opening beat can dump a peasant through the door into Nar’s cursing.",
    attitude: "Celebration hub after a surface-tree “victory”; also where false victory turns.",
    offersHooks: [
      "Post-surface celebration: children, ale. Drinking: DC 10 Con / hour or poisoned.",
      "Do not telegraph the caretaker second fight from here.",
    ],
    connectedNow: [
      { label: "Nar Granitetooth", nodeId: "npc:nar-granitetooth" },
      { label: "Hempholm", nodeId: "location:hempholm" },
      { label: "Caretakers", nodeId: "threat:caretakers" },
    ],
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
      "Wagon smack in the middle of Hempholm’s square — bigger inside than out.",
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
      "House whose garden holds the two-story grotesque tree. Menacing tree stands in the center of the garden.",
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
    connectedNow: [
      { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
      { label: "The Jove's Home", nodeId: "location:jove-home" },
      { label: "metal leaves", nodeId: "item:metal-leaves" },
    ],
  },
  "location:hempholm": {
    kind: "location",
    atTable:
      "Hemp village with a two-story attacking tree in the Jove garden. The tree is the visible problem — not the whole problem.",
    attitude: "Stall pressure advances the tree-growth clock.",
    offersHooks: [
      "Areas: Shacks, Morwin’s, Saladin’s wagon, Jove home, tree garden, then roots/Marrow.",
    ],
    connectedNow: [
      { label: "The Shacks", nodeId: "location:the-shacks" },
      { label: "Morwin's", nodeId: "location:morwins-store" },
      { label: "The Jove's Home", nodeId: "location:jove-home" },
      { label: "Grotesque Tree", nodeId: "threat:grotesque-tree" },
    ],
  },
  "location:root-corridors": {
    kind: "location",
    atTable:
      "Hollow root corridors under the village. Dank air; roots warm — more like stone or metal than wood.",
    attitude: "Descent after the surface false victory.",
    offersHooks: ["Leads toward The Marrow and the Guardian fight."],
    connectedNow: [
      { label: "The Marrow", nodeId: "location:the-marrow" },
      { label: "Guardian", nodeId: "threat:guardian" },
    ],
  },
  "location:the-marrow": {
    kind: "location",
    atTable:
      "Deep chamber under the roots. Guardian + 2 caretakers. Resin treasure with collapse risk if they get greedy.",
    attitude: "Endgame site for the under-village threat.",
    offersHooks: [
      "Safe resin 200 gp. Greedy +200 gp → collapse risk → DC 10 Athletics or the village falls in.",
      "Child in the helix is GM-only until they cut the sack.",
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
      "Saladin’s remaining stock — Maglubiyet’s Statue, 500 gp. The draw that keeps the wagon interesting after everything else sold.",
    attitude: "Who wants it: buyers, cult curiosity, or Saladin’s markup.",
    offersHooks: ["Sold from Saladin’s Mobile Emporium in the square."],
    connectedNow: [
      { label: "Saladin", nodeId: "npc:saladin" },
      { label: "Saladin's Mobile Emporium", nodeId: "location:saladins-wagon" },
    ],
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
