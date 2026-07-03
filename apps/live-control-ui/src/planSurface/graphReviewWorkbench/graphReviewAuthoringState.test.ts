import { describe, expect, it } from "vitest";
import { acceptedProposalIds, canShowLaneEditControls, stagedProposalCount, updateProposalStatus } from "./graphReviewAuthoringState";
import type { GraphReviewAuthoringProposal } from "./graphReviewAuthoringState";

const proposals: GraphReviewAuthoringProposal[] = [
  { id: "a", kind: "new_node", title: "North Gate", subtitle: "landmark", reason: "Mentioned in prose.", status: "proposed" },
  { id: "b", kind: "new_edge", title: "Tripod threatens gate", subtitle: "edge", reason: "Pressure sequence.", status: "accepted" },
  { id: "c", kind: "link_existing", title: "Tripod statblock", subtitle: "link", reason: "Existing surface.", status: "edited" },
];

describe("graphReviewAuthoringState", () => {
  it("only editable lanes show edit controls", () => {
    expect(canShowLaneEditControls({ mutability: "editable" })).toBe(true);
    expect(canShowLaneEditControls({ mutability: "read_only" })).toBe(false);
  });

  it("keeps staged proposals separate from accepted proposal ids", () => {
    expect(stagedProposalCount(proposals)).toBe(2);
    expect(acceptedProposalIds(proposals)).toEqual(["b"]);
  });

  it("updates proposal status without mutating the original proposal list", () => {
    const next = updateProposalStatus(proposals, "a", "accepted");
    expect(next.find((proposal) => proposal.id === "a")?.status).toBe("accepted");
    expect(proposals.find((proposal) => proposal.id === "a")?.status).toBe("proposed");
  });
});
