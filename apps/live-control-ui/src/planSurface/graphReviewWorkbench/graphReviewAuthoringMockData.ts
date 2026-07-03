import type { GraphReviewAuthoringProposal, GraphReviewLaneUiState } from "./graphReviewAuthoringState";

export interface GraphReviewGameSurface {
  kind: string;
  label: string;
  state: "available" | "placeholder";
}

export interface GraphReviewGameRelationship {
  id: string;
  source: string;
  predicate: string;
  target: string;
  meaning: string;
}

export interface GraphReviewGameNode {
  id: string;
  label: string;
  gameKind: string;
  summary: string;
  appearsIn: string[];
  availableSurfaces: GraphReviewGameSurface[];
  relationships: Array<{ label: string; target: string }>;
}

export const mockAuthoringLanes: GraphReviewLaneUiState[] = [
  {
    laneId: "left",
    title: "Gold Draft",
    sourceKind: "seeded_gold_draft",
    mutability: "editable",
    sourceLabel: "Seeded from candidate gold fixture",
    unsavedChangeCount: 2,
    stagedProposalCount: 3,
    activeInteractionMode: "inspect",
  },
  {
    laneId: "right",
    title: "Live Run",
    sourceKind: "live_run",
    mutability: "read_only",
    sourceLabel: "Latest vocabulary-assisted run",
    unsavedChangeCount: 0,
    stagedProposalCount: 0,
    activeInteractionMode: "inspect",
  },
];

export const mockRecapPassage =
  "The bell at Mireward’s north gate gave one dull note before the mud split open. The Tripod Null-Calf dragged itself from the reeds, its three legs folding against impossible angles as it marked the gate supports with a wet clicking sound. Captain Lysandra Ironveil ordered the defenders to brace the barricade while the Shepherd’s hymn rolled across the swamp.";

export const mockTripodNode: GraphReviewGameNode = {
  id: "node_tripod_null_calf",
  label: "Tripod Null-Calf",
  gameKind: "Threat / Combat Encounter",
  summary: "Siege scout and gate-pressure monster.",
  appearsIn: ["Mireward Gate Battle"],
  availableSurfaces: [
    { kind: "statblock", label: "Open statblock", state: "available" },
    { kind: "encounter", label: "Open encounter notes", state: "available" },
    { kind: "related_threats", label: "Related threats", state: "available" },
  ],
  relationships: [
    { label: "threatens", target: "North Gate" },
    { label: "appears in", target: "Mireward Gate Battle" },
    { label: "serves", target: "Shepherd corruption" },
  ],
};

export const mockRelationships: GraphReviewGameRelationship[] = [
  { id: "rel_tripod_gate", source: "Tripod Null-Calf", predicate: "threatens", target: "North Gate", meaning: "This relationship makes the Null-Calf part of the north-gate pressure sequence. Use it to pin barricades, mark gate supports, or interrupt cure/support lines." },
  { id: "rel_lysandra_gate", source: "Captain Lysandra Ironveil", predicate: "defends", target: "North Gate", meaning: "Lysandra anchors the defense and can rally the barricade when the gate supports begin to fail." },
  { id: "rel_tripod_battle", source: "Tripod Null-Calf", predicate: "appears in", target: "Mireward Gate Battle", meaning: "The monster belongs to the Mireward Gate Battle encounter context." },
  { id: "rel_hymn_tripod", source: "Shepherd’s hymn", predicate: "empowers", target: "Tripod Null-Calf", meaning: "The hymn is a pressure thread that can escalate the Null-Calf’s threat during the scene." },
];

export const mockAuthoringProposals: GraphReviewAuthoringProposal[] = [
  { id: "proposal_north_gate", kind: "new_node", title: "North Gate", subtitle: "landmark", reason: "Mentioned as the target of the Tripod Null-Calf pressure.", status: "proposed" },
  { id: "proposal_tripod_statblock", kind: "link_existing", title: "Tripod Null-Calf → existing statblock", subtitle: "Tripod Null-Calf", reason: "A matching table-facing monster surface is available for review.", status: "proposed" },
  { id: "proposal_hymn_edge", kind: "new_edge", title: "Shepherd’s hymn empowers Tripod Null-Calf", subtitle: "proposed edge", reason: "The hymn rolls across the swamp as the Null-Calf marks the gate supports.", status: "proposed" },
];
