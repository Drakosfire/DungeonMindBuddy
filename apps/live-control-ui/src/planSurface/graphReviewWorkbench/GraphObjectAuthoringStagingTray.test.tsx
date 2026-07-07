import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildGraphObjectAuthoringMergeProposal,
  buildGraphObjectAuthoringRelationshipProposal,
  buildManualObjectRef,
  buildObjectRefFromInspectedNode,
  createDefaultGraphObjectAuthoringFormState,
  friendlyVisibilityLabel,
} from "./graphObjectAuthoringDraft";
import { buildOverlapContextFromProjection } from "./graphObjectAuthoringOverlap";
import { GraphObjectAuthoringStagingTray } from "./GraphObjectAuthoringStagingTray";

const selection: GraphAuthoringSelection = {
  campaignId: "longmont-c1",
  sessionId: "session-2",
  selectionKind: "text_span",
  selectedText: "gang",
  normalizedSelectedText: "gang",
  graphId: "graph-c1s2",
  laneRole: "live",
};

describe("friendlyVisibilityLabel", () => {
  it("renders friendly labels instead of raw enum values", () => {
    expect(friendlyVisibilityLabel("gm_private")).toBe("GM private");
    expect(friendlyVisibilityLabel("table_known")).toBe("Table known");
    expect(friendlyVisibilityLabel("player_visible")).toBe("Player visible");
    expect(friendlyVisibilityLabel("character_specific")).toBe("Character-specific");
    expect(friendlyVisibilityLabel("hidden_until_revealed")).toBe("Hidden until revealed");
  });
});

describe("GraphObjectAuthoringStagingTray", () => {
  it("shows empty staged memory copy", () => {
    render(<GraphObjectAuthoringStagingTray proposals={[]} onRemove={vi.fn()} />);

    expect(
      screen.getByText(/No staged memory yet. Create an object, link, relationship, or merge draft above./i),
    ).toBeInTheDocument();
  });

  it("renders relationship drafts as campaign statements with friendly visibility", () => {
    const formState = {
      sourceObjectRef: buildManualObjectRef("the group"),
      targetObjectRef: buildObjectRefFromInspectedNode({ node_id: "north-gate", label: "North Gate" }),
      relationshipType: "threatens",
      relationshipLabel: "",
      direction: "directed" as const,
      summary: "",
      operatorNote: "",
      visibility: "gm_private" as const,
    };
    const proposal = buildGraphObjectAuthoringRelationshipProposal(formState, null, "local-rel-1");
    if (!proposal) {
      throw new Error("expected relationship proposal");
    }

    render(
      <GraphObjectAuthoringStagingTray proposals={[proposal]} onRemove={vi.fn()} />,
    );

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveTextContent("the group threatens North Gate");
    expect(stagedProposal).toHaveTextContent("Visibility: GM private");
    expect(stagedProposal).not.toHaveTextContent("threatens →");
    expect(stagedProposal).not.toHaveTextContent("gm_private");
  });

  it("shows player visible with friendly copy on object proposals", () => {
    const objectProposal = {
      localProposalId: "local-object-1",
      proposalKind: "object" as const,
      status: "staged_local" as const,
      selection,
      objectRef: {
        label: "Questionable Company",
        kind: "party",
        role: null,
        aliases: [],
        summary: null,
      },
      visibility: {
        visibility: "player_visible" as const,
        revealState: "unrevealed" as const,
        visibilityNote: null,
      },
      graphScopes: ["recap_graph" as const, "campaign_memory_graph" as const],
      provenancePreview: {
        origin: "human_authored" as const,
        authoringSurface: "memory_ingest_graph_authoring" as const,
      },
    };

    render(
      <GraphObjectAuthoringStagingTray proposals={[objectProposal]} onRemove={vi.fn()} />,
    );

    expect(screen.getByText("Visibility: Player visible")).toBeInTheDocument();
    expect(screen.queryByText(/player_visible/i)).not.toBeInTheDocument();
  });

  it("renders merge proposals with overlap context without crashing", () => {
    const mergeProposal = buildGraphObjectAuthoringMergeProposal({
      survivorObjectRef: {
        refKind: "existing_graph_node",
        nodeId: "survivor-1",
        label: "Tripod Null-Calf",
        kind: "threat",
      },
      mergedObjectRefs: [
        {
          refKind: "existing_graph_node",
          nodeId: "merged-1",
          label: "Tripod Null Calf",
          kind: "threat",
        },
      ],
      mergeReason: "Exact normalized label match",
      matchedFeatures: ["Exact normalized label match"],
    });
    if (!mergeProposal) {
      throw new Error("expected merge proposal");
    }

    render(
      <GraphObjectAuthoringStagingTray
        proposals={[mergeProposal]}
        onRemove={vi.fn()}
        overlapContext={buildOverlapContextFromProjection([mergeProposal], [])}
      />,
    );

    expect(screen.getByText(/Tripod Null-Calf ← Tripod Null Calf/i)).toBeInTheDocument();
    expect(screen.getByText(/No objects have been deleted/i)).toBeInTheDocument();
  });
});
