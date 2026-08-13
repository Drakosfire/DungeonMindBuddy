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

export type AdventureBeat = {
  id: string;
  title: string;
  kind: BeatKind;
  summary: string;
  readAloud?: string | null;
  rulesNow?: string[] | null;
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
        "Default table open is the hill arrival. Alt hooks are cold opens that still lead to Hempholm.",
      beats: [
        {
          id: "hook-hill",
          title: "Hill arrival (default)",
          kind: "spine",
          summary: "Approach Hempholm from a hill; grotesque tree lashes a bird.",
          readAloud:
            "Overlooking the village from a small hill, you cannot help but notice a grotesque tree growing in one of the gardens which towers above all other trees and buildings in the area. When a bird tries to perch on one of its branches, the tree lashes out and turns the bird into minced meat.",
        },
        {
          id: "hook-alchemist",
          title: "Alchemist's Despair",
          kind: "optional",
          summary:
            "In Greenest, Korden begs help recovering a stolen conk for the Baldur’s Gate mages’ guild; a merchant points you to a village with a strange plant.",
          chips: [{ label: "the conk", nodeId: "item:the-conk" }],
        },
        {
          id: "hook-guild",
          title: "In Service of the Guild",
          kind: "optional",
          summary:
            "Berdusk delivery fails — Lord Fiddlestick already sold the package to a village boy. Retrieve it or face wizardly consequences.",
          chips: [
            { label: "Lord Fiddlestick", nodeId: "npc:lord-fiddlestick" },
            { label: "the conk", nodeId: "item:the-conk" },
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
        "Overlooking the village from a small hill, you cannot help but notice a grotesque tree growing in one of the gardens…",
      gmNote: "New players may freeze — start in media res at the tree, or have an NPC take them by the hand.",
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
          summary: "See the tree; curiosity + hunger for adventure.",
          chips: [{ label: "Grotesque Tree", nodeId: "threat:grotesque-tree" }],
        },
        {
          id: "arrive-skip-to-shacks",
          title: "Skip to Shacks",
          kind: "optional",
          summary: "Different hook → start at The Shacks.",
          chips: [{ label: "The Shacks", nodeId: "location:the-shacks" }],
        },
        {
          id: "arrive-skip-to-jove",
          title: "Skip to Jove home",
          kind: "optional",
          summary: "Different hook → start at the garden crisis.",
          chips: [{ label: "The Jove's Home", nodeId: "location:jove-home" }],
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
          readAloud:
            "You stand in front of the village’s largest building when a peasant with an oddly noggin-shaped nose flies through the door out into the cold…",
          rulesNow: [
            "Nar: DC 20 Persuasion + Religion to win toward Sharindlar.",
            "Wounded later: DC 15 Persuasion or DC 10 Religion (faith appeal).",
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
          chips: [
            { label: "Morwin Blackwell", nodeId: "npc:morwin-blackwell" },
            { label: "Morwin's", nodeId: "location:morwins-store" },
          ],
        },
        {
          id: "gem-job",
          title: "Gem job",
          kind: "optional",
          summary: "Ten stones; DC 10 Jeweler’s Tools; two tourmalines (100 gp cut).",
          rulesNow: ["DC 10 Dexterity (Jeweler’s Tools) per stone."],
          chips: [{ label: "Morwin Blackwell", nodeId: "npc:morwin-blackwell" }],
        },
        {
          id: "saladin-wagon",
          title: "Saladin's wagon",
          kind: "optional",
          summary: "Sold out except Maglubiyet’s Statue (500 gp).",
          chips: [
            { label: "Saladin", nodeId: "npc:saladin" },
            { label: "Maglubiyet’s Statue", nodeId: "item:maglubiyets-statue" },
          ],
          toolLinks: [{ label: "Open Items", panel: "items" }],
        },
        {
          id: "meal-moonshine",
          title: "Meal n’ Moonshine",
          kind: "optional",
          summary: "Contest at The Shacks; prize Belly’s Mouthwash.",
          rulesNow: [
            "Cook’s utensils or brewer’s supplies.",
            "1d6+2 contenders each roll d20 (no bonus); PCs have proficiency edge.",
          ],
          chips: [
            { label: "The Shacks", nodeId: "location:the-shacks" },
            { label: "Belly’s Mouthwash", nodeId: "item:bellys-mouthwash" },
          ],
        },
        {
          id: "distillery",
          title: "Broken distillery",
          kind: "optional",
          summary: "Blacksmith yard; repair for 10 gp + engraving.",
          rulesNow: [
            "DC 15 Dexterity (Tinker’s Tools) or DC 20 Dexterity (Smith’s Tools).",
          ],
        },
        {
          id: "jove-plea",
          title: "Jove plea",
          kind: "spine",
          summary: "Mark blames Torbin; tree in the garden.",
          chips: [
            { label: "Mark Jove", nodeId: "npc:mark-jove" },
            { label: "Torbin Jove", nodeId: "npc:torbin-jove" },
            { label: "The Jove's Home", nodeId: "location:jove-home" },
          ],
        },
        {
          id: "growth-spurt",
          title: "Growth spurt",
          kind: "interrupt",
          summary: "Stall → tree 30 ft; smashes Jove home + two neighbors.",
          rulesNow: [
            "Fire vs tree now: d20 even = surrounding houses catch.",
          ],
          chips: [{ label: "Grotesque Tree", nodeId: "threat:grotesque-tree" }],
        },
        {
          id: "axe-villagers",
          title: "Axe villagers mauled",
          kind: "interrupt",
          summary: "Four villagers attack the tree and get wrecked; carry to Nar.",
          rulesNow: [
            "Nar heals: DC 15 Persuasion or DC 10 Religion (Sharindlar), or free if already won over.",
          ],
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
          rulesNow: [
            "Passive Perception 15: metal leaves. Passive Arcana 12: aura. DC 17 Arcana: roots under village.",
            "Fire vs tree: d20 even = houses catch.",
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
          title: "Heroes’ party",
          kind: "spine",
          summary: "Children, ale, stories; weapons for reenactment on the hill north of Shacks.",
          rulesNow: ["Drinking: DC 10 Constitution / hour or poisoned."],
          chips: [{ label: "The Shacks", nodeId: "location:the-shacks" }],
        },
        {
          id: "never-split",
          title: "Never Split the Party",
          kind: "optional",
          summary: "Overnight pairings disperse the party before caretakers hit.",
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
          rulesNow: [
            "DC 12 Strength (Athletics) or gain 1 level of exhaustion; d4 houses destroyed.",
          ],
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
          rulesNow: [
            "20 total, groups of 5 (twig blight MM 32).",
            "Flee after ~15 dead or return underground after a few hours; afraid of fire.",
            "Treasure: 1 gp quality root-wood per corpse (woodcarver’s / carpenter’s).",
          ],
          chips: [{ label: "Caretakers", nodeId: "threat:caretakers" }],
          toolLinks: [{ label: "Open Combat", panel: "combat" }],
        },
        {
          id: "urge-descent",
          title: "Urge descent",
          kind: "spine",
          summary: "Villagers urge the party into the hollow roots.",
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
          chips: [
            { label: "Guardian", nodeId: "threat:guardian" },
            { label: "Caretakers", nodeId: "threat:caretakers" },
          ],
          toolLinks: [{ label: "Open Combat", panel: "combat" }],
        },
        {
          id: "marrow-resin",
          title: "Resin harvest",
          kind: "spine",
          summary: "Cut helix → metal resin. Greed can collapse the village.",
          rulesNow: [
            "Safe: 200 gp metal resin.",
            "Greedy +200 gp → DC 10 Athletics to escape or buried; Hempholm can fall in.",
          ],
          chips: [{ label: "The Marrow", nodeId: "location:the-marrow" }],
        },
      ],
    },
    {
      id: "child",
      title: "Fate of the child",
      order: 8,
      branchKind: "linear",
      intent: "GM-only until they cut the sack. Metal-eater blank slate. Village wants it gone.",
      gmNote: "Do not read the child’s nature as boxed text at the garden.",
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
          chips: [{ label: "Child in the helix", nodeId: "npc:helix-child" }],
        },
        {
          id: "child-handoff",
          title: "Handoff",
          kind: "optional",
          summary: "Nar or Saladin will take it; village may demand they leave.",
          chips: [
            { label: "Nar Granitetooth", nodeId: "npc:nar-granitetooth" },
            { label: "Saladin", nodeId: "npc:saladin" },
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
        { label: "Baldur’s Gate mages’ guild", nodeId: "faction:baldurs-gate-mages-guild" },
      ],
      beats: [
        {
          id: "gratitude",
          title: "Hempholm’s gratitude",
          kind: "optional",
          summary: "Heroes or villains — word travels to Greenest and Berdusk.",
        },
        {
          id: "paelias",
          title: "Agent of the guild",
          kind: "optional",
          summary: "Paelias comes later to erase under-village evidence.",
          chips: [{ label: "Paelias Sian", nodeId: "npc:paelias-sian" }],
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
