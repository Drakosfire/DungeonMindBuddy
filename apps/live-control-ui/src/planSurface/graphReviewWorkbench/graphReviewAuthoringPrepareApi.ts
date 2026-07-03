import type { GraphGoldAuthoringPrepareRequest, GraphGoldAuthoringLocalProposal } from "../../api/types";
import type { GraphReviewLocalAuthoringProposal } from "./graphReviewLocalAuthoringState";

function nodeRef(ref: { laneRole: "gold" | "live"; nodeId: string; label: string }) {
  return { lane_role: ref.laneRole, node_id: ref.nodeId, label: ref.label };
}

export function mapLocalProposalToPrepareProposal(
  proposal: GraphReviewLocalAuthoringProposal,
): GraphGoldAuthoringLocalProposal {
  const base = {
    proposal_id: proposal.proposalId,
    proposal_type: proposal.proposalType,
    created_at_iso: proposal.createdAtIso,
    status: proposal.status,
  };
  switch (proposal.proposalType) {
    case "node_from_span":
      return { ...base, proposal_type: "node_from_span", lane_role: proposal.laneRole, source_text: proposal.sourceText, source_offsets: proposal.sourceOffsets ?? null, suggested_label: proposal.suggestedLabel, suggested_kind: proposal.suggestedKind ?? null };
    case "node_assertion":
      return { ...base, proposal_type: "node_assertion", lane_role: proposal.laneRole, node_id: proposal.nodeId, label: proposal.label, kind: proposal.kind ?? null, role: proposal.role ?? null };
    case "relationship_assertion":
      return { ...base, proposal_type: "relationship_assertion", lane_role: proposal.laneRole, source_node: nodeRef(proposal.sourceNode), target_node: nodeRef(proposal.targetNode), predicate: proposal.predicate };
    case "existing_object_link_intent":
      return { ...base, proposal_type: "existing_object_link_intent", selected_node: nodeRef(proposal.selectedNode), candidate: { candidate_id: proposal.candidate.candidate_id ?? proposal.candidate.candidateId, label: proposal.candidate.label, source: proposal.candidate.source, confidence: proposal.candidate.confidence, score: proposal.candidate.score } };
  }
}

export function buildGraphGoldAuthoringPrepareRequest(input: {
  campaignId: string;
  sessionId: string;
  proposals: GraphReviewLocalAuthoringProposal[];
  fixtureVersion?: string | null;
  includeRejected?: boolean;
}): GraphGoldAuthoringPrepareRequest {
  return {
    schema: "dmb_graph_gold_authoring_prepare_request_v1",
    campaign_id: input.campaignId,
    session_id: input.sessionId,
    fixture_version: input.fixtureVersion ?? null,
    include_rejected: input.includeRejected ?? false,
    proposals: input.proposals.map(mapLocalProposalToPrepareProposal),
  };
}
