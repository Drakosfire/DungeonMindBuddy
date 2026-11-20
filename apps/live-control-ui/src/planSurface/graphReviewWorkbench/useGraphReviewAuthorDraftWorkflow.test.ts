import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createGraphReviewLocalAuthoringIdFactory } from "./graphReviewLocalAuthoringState";
import { useGraphReviewAuthorDraftWorkflow } from "./useGraphReviewAuthorDraftWorkflow";

function renderWorkflow() {
  return renderHook(() => useGraphReviewAuthorDraftWorkflow({
    idFactory: createGraphReviewLocalAuthoringIdFactory(() => "2026-07-03T00:00:00Z"),
  }));
}

describe("local Graph review notes", () => {
  it("preserves supplied proposals and supports local status changes", () => {
    const staged = renderWorkflow();
    act(() => staged.result.current.stageNodeAssertion({
      laneRole: "live", nodeId: "node-1", label: "Node One", kind: null, role: null,
    }));
    const proposals = staged.result.current.localProposals;
    const { result } = renderHook(() => useGraphReviewAuthorDraftWorkflow({ initialProposals: proposals }));
    expect(result.current.authorMode).toBe("review");
    expect(result.current.localProposals).toEqual(proposals);
    act(() => result.current.updateProposalStatus("local-1", "accepted_local"));
    expect(result.current.localProposals[0].status).toBe("accepted_local");
    expect(result.current.localProposals[0].proposalId).toBe(proposals[0].proposalId);
  });

  it("stages selected text with its source offsets and resets only on request", () => {
    const { result } = renderWorkflow();
    act(() => result.current.setSelectedText({ laneRole: "live", text: "Tripod Null-Calf", sourceOffsets: {start: 4, end: 20} }));
    act(() => result.current.stageNodeFromSpan());
    expect(result.current.localProposals[0]).toMatchObject({
      proposalType: "node_from_span", sourceText: "Tripod Null-Calf", sourceOffsets: {start: 4, end: 20},
    });
    act(() => result.current.resetLocalDraft());
    expect(result.current.localProposals).toEqual([]);
    expect(result.current.selectedText).toBeNull();
  });
});
