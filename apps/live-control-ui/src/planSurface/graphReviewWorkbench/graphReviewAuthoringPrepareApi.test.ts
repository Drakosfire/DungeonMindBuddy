import { describe, expect, it } from "vitest";

import { buildGraphGoldAuthoringPrepareRequest, mapLocalProposalToPrepareProposal } from "./graphReviewAuthoringPrepareApi";
import type { GraphReviewLocalAuthoringProposal } from "./graphReviewLocalAuthoringState";

const base = { proposalId: "local-1", createdAtIso: "2026-07-03T00:00:00Z", status: "accepted_local" as const };

describe("graphReviewAuthoringPrepareApi", () => {
  it("maps local camelCase node proposal to backend snake_case request shape", () => {
    const mapped = mapLocalProposalToPrepareProposal({ ...base, proposalType: "node_from_span", laneRole: "live", sourceText: "Tripod Null-Calf", sourceOffsets: { start: 1, end: 17 }, suggestedLabel: "Tripod Null-Calf", suggestedKind: null });
    expect(mapped).toMatchObject({ proposal_id: "local-1", proposal_type: "node_from_span", created_at_iso: base.createdAtIso, lane_role: "live", source_text: "Tripod Null-Calf", suggested_label: "Tripod Null-Calf" });
  });

  it("preserves proposal id and status", () => {
    const request = buildGraphGoldAuthoringPrepareRequest({ campaignId: "longmont-c1", sessionId: "session-1", proposals: [{ ...base, proposalId: "local-7", status: "staged", proposalType: "node_assertion", laneRole: "gold", nodeId: "g1", label: "North Gate", kind: null, role: null }] });
    expect(request.proposals[0]).toMatchObject({ proposal_id: "local-7", status: "staged" });
  });

  it("preserves null source offsets", () => {
    const mapped = mapLocalProposalToPrepareProposal({ ...base, proposalType: "node_from_span", laneRole: "gold", sourceText: "North Gate", sourceOffsets: null, suggestedLabel: "North Gate", suggestedKind: null });
    expect(mapped.proposal_type).toBe("node_from_span");
    if (mapped.proposal_type === "node_from_span") expect(mapped.source_offsets).toBeNull();
  });

  it("preserves existing-object candidate fields", () => {
    const mapped = mapLocalProposalToPrepareProposal({ ...base, proposalType: "existing_object_link_intent", selectedNode: { laneRole: "live", nodeId: "n1", label: "Tripod" }, candidate: { candidate_id: "g1", candidateId: "g1", label: "Tripod", source: "gold_fixture", confidence: "high", score: 0.92 } });
    expect(mapped.proposal_type).toBe("existing_object_link_intent");
    if (mapped.proposal_type === "existing_object_link_intent") expect(mapped.candidate).toMatchObject({ candidate_id: "g1", label: "Tripod", source: "gold_fixture", confidence: "high", score: 0.92 });
  });

  it("preserves mixed-lane relationship", () => {
    const proposal: GraphReviewLocalAuthoringProposal = { ...base, proposalType: "relationship_assertion", laneRole: "mixed", sourceNode: { laneRole: "live", nodeId: "n1", label: "Tripod" }, targetNode: { laneRole: "gold", nodeId: "g2", label: "North Gate" }, predicate: "threatens" };
    const mapped = mapLocalProposalToPrepareProposal(proposal);
    expect(mapped.proposal_type).toBe("relationship_assertion");
    if (mapped.proposal_type === "relationship_assertion") expect(mapped.lane_role).toBe("mixed");
  });
});
