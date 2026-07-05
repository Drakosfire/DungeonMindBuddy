import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import type { GraphReviewProjectionLaneRole } from "./GraphReviewProjectionLane";

export type GraphReviewLocalAuthoringProposalStatus =
  | "staged"
  | "accepted_local"
  | "rejected_local";
export type GraphReviewLocalAuthoringProposalType =
  | "node_from_span"
  | "node_assertion"
  | "relationship_assertion"
  | "existing_object_link_intent";

export interface GraphReviewLocalAuthoringProposalBase {
  proposalId: string;
  createdAtIso: string;
  proposalType: GraphReviewLocalAuthoringProposalType;
  status: GraphReviewLocalAuthoringProposalStatus;
}
export interface GraphReviewNodeFromSpanProposal extends GraphReviewLocalAuthoringProposalBase {
  proposalType: "node_from_span";
  laneRole: GraphReviewProjectionLaneRole;
  sourceText: string;
  sourceOffsets?: { start: number; end: number } | null;
  suggestedLabel: string;
  suggestedKind?: string | null;
}
export interface GraphReviewNodeAssertionProposal extends GraphReviewLocalAuthoringProposalBase {
  proposalType: "node_assertion";
  laneRole: GraphReviewProjectionLaneRole;
  nodeId: string;
  label: string;
  kind?: string | null;
  role?: string | null;
}
export interface GraphReviewRelationshipNodeRef {
  laneRole: GraphReviewProjectionLaneRole;
  nodeId: string;
  label: string;
}
export interface GraphReviewRelationshipAssertionProposal extends GraphReviewLocalAuthoringProposalBase {
  proposalType: "relationship_assertion";
  laneRole: GraphReviewProjectionLaneRole | "mixed";
  sourceNode: GraphReviewRelationshipNodeRef;
  targetNode: GraphReviewRelationshipNodeRef;
  predicate: string;
}
export interface GraphReviewExistingObjectLinkIntentProposal extends GraphReviewLocalAuthoringProposalBase {
  proposalType: "existing_object_link_intent";
  selectedNode: GraphReviewRelationshipNodeRef;
  candidate: Pick<
    GraphReviewExistingObjectCandidate,
    "candidate_id" | "label" | "source" | "confidence" | "score"
  > & { candidateId: string };
}
export type GraphReviewLocalAuthoringProposal =
  | GraphReviewNodeFromSpanProposal
  | GraphReviewNodeAssertionProposal
  | GraphReviewRelationshipAssertionProposal
  | GraphReviewExistingObjectLinkIntentProposal;

export interface GraphReviewLocalAuthoringIdFactory {
  nextId: () => string;
  nowIso: () => string;
}
export function createGraphReviewLocalAuthoringIdFactory(
  nowIso = () => new Date().toISOString(),
): GraphReviewLocalAuthoringIdFactory {
  let counter = 0;
  return { nextId: () => `local-${++counter}`, nowIso };
}
function base<T extends GraphReviewLocalAuthoringProposalType>(
  factory: GraphReviewLocalAuthoringIdFactory,
  proposalType: T,
) {
  return {
    proposalId: factory.nextId(),
    createdAtIso: factory.nowIso(),
    proposalType,
    status: "staged" as const,
  };
}
export function createNodeFromSpanProposal(
  factory: GraphReviewLocalAuthoringIdFactory,
  input: Omit<
    GraphReviewNodeFromSpanProposal,
    keyof GraphReviewLocalAuthoringProposalBase
  >,
): GraphReviewNodeFromSpanProposal {
  return {
    ...base(factory, "node_from_span"),
    ...input,
    suggestedLabel: input.suggestedLabel || input.sourceText.trim(),
    suggestedKind: input.suggestedKind ?? null,
  };
}
export function createNodeAssertionProposal(
  factory: GraphReviewLocalAuthoringIdFactory,
  input: Omit<
    GraphReviewNodeAssertionProposal,
    keyof GraphReviewLocalAuthoringProposalBase
  >,
): GraphReviewNodeAssertionProposal {
  return {
    ...base(factory, "node_assertion"),
    ...input,
    kind: input.kind ?? null,
    role: input.role ?? null,
  };
}
export function createRelationshipAssertionProposal(
  factory: GraphReviewLocalAuthoringIdFactory,
  input: Omit<
    GraphReviewRelationshipAssertionProposal,
    keyof GraphReviewLocalAuthoringProposalBase | "laneRole"
  > & { laneRole?: GraphReviewProjectionLaneRole | "mixed" },
): GraphReviewRelationshipAssertionProposal {
  const laneRole =
    input.laneRole ??
    (input.sourceNode.laneRole === input.targetNode.laneRole
      ? input.sourceNode.laneRole
      : "mixed");
  return { ...base(factory, "relationship_assertion"), ...input, laneRole };
}
export function createExistingObjectLinkIntentProposal(
  factory: GraphReviewLocalAuthoringIdFactory,
  input: Omit<
    GraphReviewExistingObjectLinkIntentProposal,
    keyof GraphReviewLocalAuthoringProposalBase
  >,
): GraphReviewExistingObjectLinkIntentProposal {
  return { ...base(factory, "existing_object_link_intent"), ...input };
}
export function updateLocalProposalStatus(
  proposals: GraphReviewLocalAuthoringProposal[],
  proposalId: string,
  status: GraphReviewLocalAuthoringProposalStatus,
): GraphReviewLocalAuthoringProposal[] {
  return proposals.map((proposal) =>
    proposal.proposalId === proposalId ? { ...proposal, status } : proposal,
  );
}
export function resetLocalAuthoringDraft(): GraphReviewLocalAuthoringProposal[] {
  return [];
}
export const GRAPH_REVIEW_RELATIONSHIP_PREDICATES = [
  "relates_to",
  "threatens",
  "located_at",
  "member_of",
  "ally_of",
  "opposes",
  "caused_by",
  "protects",
] as const;
export type GraphReviewRelationshipPredicate =
  (typeof GRAPH_REVIEW_RELATIONSHIP_PREDICATES)[number];
