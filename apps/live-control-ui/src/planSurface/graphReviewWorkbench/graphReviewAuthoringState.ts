export type GraphReviewLaneSourceKind =
  | "gold_fixture"
  | "live_run"
  | "gold_draft"
  | "seeded_gold_draft"
  | "blank_authoring_draft"
  | "reference_variant";

export type GraphReviewLaneMutability = "read_only" | "editable";

export type GraphReviewInteractionMode =
  | "inspect"
  | "select_span"
  | "draw_edge"
  | "review_proposals"
  | "evidence_debug";

export interface GraphReviewLaneUiState {
  laneId: "left" | "right";
  title: string;
  sourceKind: GraphReviewLaneSourceKind;
  mutability: GraphReviewLaneMutability;
  sourceLabel: string;
  unsavedChangeCount: number;
  stagedProposalCount: number;
  activeInteractionMode: GraphReviewInteractionMode;
}

export type GraphReviewProposalKind = "new_node" | "new_edge" | "link_existing";
export type GraphReviewProposalStatus = "proposed" | "accepted" | "rejected" | "edited";

export interface GraphReviewAuthoringProposal {
  id: string;
  kind: GraphReviewProposalKind;
  title: string;
  subtitle: string;
  reason: string;
  status: GraphReviewProposalStatus;
}

export function canShowLaneEditControls(lane: Pick<GraphReviewLaneUiState, "mutability">): boolean {
  return lane.mutability === "editable";
}

export function stagedProposalCount(proposals: GraphReviewAuthoringProposal[]): number {
  return proposals.filter((proposal) => proposal.status === "proposed" || proposal.status === "edited").length;
}

export function acceptedProposalIds(proposals: GraphReviewAuthoringProposal[]): string[] {
  return proposals.filter((proposal) => proposal.status === "accepted").map((proposal) => proposal.id);
}

export function updateProposalStatus(
  proposals: GraphReviewAuthoringProposal[],
  proposalId: string,
  status: GraphReviewProposalStatus,
): GraphReviewAuthoringProposal[] {
  return proposals.map((proposal) => (proposal.id === proposalId ? { ...proposal, status } : proposal));
}
