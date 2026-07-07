import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { buildGraphObjectAuthoringMergeProposal } from "./graphObjectAuthoringDraft";
import { GraphReviewMergeCandidatesPanel } from "./GraphReviewMergeCandidatesPanel";
import type { UseGraphObjectAuthoringDraftResult } from "./useGraphObjectAuthoringDraft";

function node(
  overrides: Partial<GraphProjectionNodeView> & Pick<GraphProjectionNodeView, "node_id" | "label">,
): GraphProjectionNodeView {
  return {
    kind: "entity",
    role: "candidate",
    aliases: [],
    source_domains: ["live_projection"],
    evidence_badges: [],
    adjacency: [],
    ...overrides,
  };
}

function draftStub(
  overrides: Partial<UseGraphObjectAuthoringDraftResult> = {},
): UseGraphObjectAuthoringDraftResult {
  return {
    selectedSource: null,
    formState: {
      label: "",
      kind: "unknown",
      role: "",
      aliasesText: "",
      summary: "",
      operatorNote: "",
      visibility: "gm_private",
    },
    proposals: [],
    openWithSelection: vi.fn(),
    dismissSelection: vi.fn(),
    updateFormField: vi.fn(),
    stageProposal: vi.fn(),
    removeProposal: vi.fn(),
    linkExistingFormState: {
      existingObjectRef: null,
      operation: "alias",
      aliasText: "",
      operatorNote: "",
      visibility: "gm_private",
    },
    updateLinkExistingField: vi.fn(),
    stageLinkExistingProposal: vi.fn(),
    relationshipFormState: {
      sourceObjectRef: null,
      targetObjectRef: null,
      relationshipType: "related_to",
      relationshipLabel: "",
      direction: "directed",
      summary: "",
      operatorNote: "",
      visibility: "gm_private",
    },
    updateRelationshipField: vi.fn(),
    stageRelationshipProposal: vi.fn(),
    stageMergeProposal: vi.fn(() => true),
    clearCommittedProposals: vi.fn(),
    ...overrides,
  };
}

describe("GraphReviewMergeCandidatesPanel", () => {
  it("runs duplicate scan and renders candidate cards", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewMergeCandidatesPanel
        nodeViews={{
          a: node({ node_id: "a", label: "Questionable Company", kind: "party" }),
          b: node({
            node_id: "b",
            label: "the group",
            kind: "party",
            aliases: ["Questionable Company"],
          }),
        }}
        graphObjectAuthoringDraft={draftStub()}
      />,
    );

    await user.click(screen.getByRole("button", { name: /find likely duplicates/i }));
    expect(screen.getByTestId("graph-review-merge-candidate-card")).toBeInTheDocument();
  });

  it("stages merge on accept without leaving the panel", async () => {
    const user = userEvent.setup();
    const stageMergeProposal = vi.fn(() => true);

    render(
      <GraphReviewMergeCandidatesPanel
        nodeViews={{
          a: node({ node_id: "a", label: "North Gate" }),
          b: node({ node_id: "b", label: "the north gate" }),
        }}
        graphObjectAuthoringDraft={draftStub({ stageMergeProposal })}
      />,
    );

    await user.click(screen.getByRole("button", { name: /find likely duplicates/i }));
    await user.click(screen.getByRole("button", { name: /accept merge/i }));
    expect(stageMergeProposal).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("graph-review-merge-candidates-panel")).toBeInTheDocument();
    expect(screen.getByText(/Merge staged locally/i)).toBeInTheDocument();
    expect(screen.getByTestId("graph-review-merge-candidate-card")).toHaveAttribute(
      "data-decision",
      "accepted",
    );
  });

  it("marks rescanned candidates as accepted when the pair is already staged", async () => {
    const user = userEvent.setup();
    const stageMergeProposal = vi.fn(() => true);
    const edgeSurvivor = {
      refKind: "existing_graph_node" as const,
      nodeId: "edge-a",
      label: "Edge",
      kind: "location",
    };
    const edgeMerged = {
      refKind: "existing_graph_node" as const,
      nodeId: "edge-b",
      label: "the Edge",
      kind: "location",
    };
    const stagedMerge = buildGraphObjectAuthoringMergeProposal({
      survivorObjectRef: edgeSurvivor,
      mergedObjectRefs: [edgeMerged],
      mergeReason: "Exact normalized label match",
      matchedFeatures: ["Exact normalized label match"],
    });

    render(
      <GraphReviewMergeCandidatesPanel
        nodeViews={{
          a: node({ node_id: "edge-a", label: "Edge", kind: "location" }),
          b: node({ node_id: "edge-b", label: "the Edge", kind: "location" }),
        }}
        graphObjectAuthoringDraft={draftStub({
          proposals: stagedMerge ? [stagedMerge] : [],
          stageMergeProposal,
        })}
      />,
    );

    await user.click(screen.getByRole("button", { name: /find likely duplicates/i }));
    expect(screen.getByTestId("graph-review-merge-candidate-card")).toHaveAttribute(
      "data-decision",
      "accepted",
    );
    expect(screen.queryByRole("button", { name: /accept merge/i })).not.toBeInTheDocument();
    expect(stageMergeProposal).not.toHaveBeenCalled();
  });
});
