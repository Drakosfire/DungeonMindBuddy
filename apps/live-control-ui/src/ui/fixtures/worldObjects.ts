import type { GraphObjectCardViewModel } from "../../graphObjectCard/types";

// Workshop-only, illustrative data. These are not campaign authority or gold.
export const sparseNpc = {
  id: "workshop:npc:quiet-witness",
  label: "Quiet witness",
  kind: "npc",
  typeBadgeLabel: "NPC",
  relationships: [],
  evidence: [],
} satisfies GraphObjectCardViewModel;

export const richNpc = {
  id: "workshop:npc:brin",
  label: "Brin",
  kind: "npc",
  typeBadgeLabel: "NPC",
  secondaryRoleLabel: "Refugee leader",
  aliases: ["Brin Holloway"],
  gameSummary: "A cook from Edge who helped lead its refugees to safety.",
  whyItMattersNow: "Brin sorted the arrivals at the south gate as the party looked for shelter.",
  campaignLabel: "C2",
  relationships: [
    {
      id: "workshop:edge:brin-orik",
      label: "Orik",
      predicate: "coordinated_with",
      direction: "outgoing",
      sessionIds: ["session-25"],
      campaignScope: "longmont-c2",
      targetId: "workshop:npc:orik",
    },
    {
      id: "workshop:edge:brin-gate",
      label: "South Gate",
      predicate: "arrived_at",
      direction: "outgoing",
      sessionIds: ["session-25"],
      campaignScope: "longmont-c2",
      targetId: "workshop:location:south-gate",
    },
  ],
  evidence: [
    { id: "workshop:evidence:brin-recap", label: "Session 25 recap", sourceDomain: "recap" },
  ],
  sourceDomains: ["recap"],
  details: { evidenceCount: 1, visibilityLabel: "gm_private" },
} satisfies GraphObjectCardViewModel;

export const location = {
  id: "workshop:location:south-gate",
  label: "South Gate",
  kind: "location",
  typeBadgeLabel: "Location",
  gameSummary: "The southern entry into town and the first sheltering point for arrivals from Edge.",
  whyItMattersNow: "Refugees were sorted here before moving toward a warehouse.",
  campaignLabel: "C2",
  relationships: [
    {
      id: "workshop:edge:gate-town",
      label: "Mireward",
      predicate: "part_of",
      targetId: "workshop:location:mireward",
    },
  ],
} satisfies GraphObjectCardViewModel;

export const faction = {
  id: "workshop:faction:river-wardens",
  label: "River Wardens",
  kind: "faction",
  typeBadgeLabel: "Faction",
  summary: "A small civic watch keeping crossings open during the evacuation.",
  aliases: ["The Wardens"],
  relationships: [
    {
      id: "workshop:edge:wardens-crossing",
      label: "Old Crossing",
      predicate: "guards",
      targetId: "workshop:location:old-crossing",
    },
  ],
} satisfies GraphObjectCardViewModel;

export const relationshipHeavy = {
  ...richNpc,
  id: "workshop:npc:many-connections",
  label: "Many connections",
  aliases: [],
  gameSummary: "A contact whose long history tests whether relationships stay scannable.",
  whyItMattersNow: null,
  relationships: Array.from({ length: 15 }, (_, index) => ({
    id: `workshop:edge:${index + 1}`,
    label: `Contact ${String(index + 1).padStart(2, "0")}`,
    predicate: index % 2 === 0 ? "knows" : "worked_with",
    targetId: `workshop:npc:contact-${index + 1}`,
    sessionIds: [`session-${index + 1}`],
    campaignScope: "longmont-c2",
  })),
} satisfies GraphObjectCardViewModel;

export const worldObjectFixtures = {
  sparseNpc,
  richNpc,
  location,
  faction,
  relationshipHeavy,
} satisfies Record<string, GraphObjectCardViewModel>;
