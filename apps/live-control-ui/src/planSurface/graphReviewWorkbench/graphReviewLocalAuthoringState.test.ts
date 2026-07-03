import { describe, expect, it } from "vitest";
import {
  createExistingObjectLinkIntentProposal,
  createGraphReviewLocalAuthoringIdFactory,
  createNodeAssertionProposal,
  createNodeFromSpanProposal,
  createRelationshipAssertionProposal,
  resetLocalAuthoringDraft,
  updateLocalProposalStatus,
} from "./graphReviewLocalAuthoringState";

const factory = () =>
  createGraphReviewLocalAuthoringIdFactory(() => "2026-07-03T00:00:00.000Z");

describe("graphReviewLocalAuthoringState", () => {
  it("creates stable local node-from-span proposals", () => {
    const proposal = createNodeFromSpanProposal(factory(), {
      laneRole: "live",
      sourceText: "Tripod Null-Calf",
      sourceOffsets: null,
      suggestedLabel: "Tripod Null-Calf",
      suggestedKind: null,
    });
    expect(proposal).toMatchObject({
      proposalId: "local-1",
      proposalType: "node_from_span",
      status: "staged",
      sourceOffsets: null,
    });
  });
  it("creates node assertions", () => {
    expect(
      createNodeAssertionProposal(factory(), {
        laneRole: "gold",
        nodeId: "n1",
        label: "North Gate",
        kind: "location",
        role: null,
      }),
    ).toMatchObject({ proposalType: "node_assertion", label: "North Gate" });
  });
  it("creates relationship assertions with mixed lane detection", () => {
    expect(
      createRelationshipAssertionProposal(factory(), {
        sourceNode: { laneRole: "gold", nodeId: "a", label: "A" },
        targetNode: { laneRole: "live", nodeId: "b", label: "B" },
        predicate: "threatens",
      }),
    ).toMatchObject({
      proposalType: "relationship_assertion",
      laneRole: "mixed",
    });
  });
  it("creates existing-object link intents", () => {
    expect(
      createExistingObjectLinkIntentProposal(factory(), {
        selectedNode: { laneRole: "live", nodeId: "n1", label: "Tripod" },
        candidate: {
          candidateId: "c1",
          candidate_id: "c1",
          label: "Tripod",
          source: "gold_fixture",
          confidence: "high",
          score: 0.9,
        },
      }),
    ).toMatchObject({
      proposalType: "existing_object_link_intent",
      candidate: { candidateId: "c1" },
    });
  });
  it("accepts, rejects, and resets locally", () => {
    const f = factory();
    const proposals = [
      createNodeAssertionProposal(f, {
        laneRole: "live",
        nodeId: "n1",
        label: "Tripod",
        kind: null,
        role: null,
      }),
    ];
    expect(
      updateLocalProposalStatus(proposals, "local-1", "accepted_local")[0]
        .status,
    ).toBe("accepted_local");
    expect(
      updateLocalProposalStatus(proposals, "local-1", "rejected_local")[0]
        .status,
    ).toBe("rejected_local");
    expect(resetLocalAuthoringDraft()).toEqual([]);
  });
  it("increments proposal ids under test helper", () => {
    const f = factory();
    expect(
      createNodeAssertionProposal(f, {
        laneRole: "live",
        nodeId: "n1",
        label: "One",
        kind: null,
        role: null,
      }).proposalId,
    ).toBe("local-1");
    expect(
      createNodeAssertionProposal(f, {
        laneRole: "live",
        nodeId: "n2",
        label: "Two",
        kind: null,
        role: null,
      }).proposalId,
    ).toBe("local-2");
  });
});
