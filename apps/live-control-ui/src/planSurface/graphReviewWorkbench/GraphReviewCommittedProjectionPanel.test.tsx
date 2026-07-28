import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type {
  ExtractPromoteConfirmReceipt,
  WorldGraphProjection,
} from "../../api/types";
import { GraphReviewCommittedProjectionPanel } from "./GraphReviewCommittedProjectionPanel";
import { renderGraphReviewLiveHarness } from "./graphReviewLiveStateTestHarness";

vi.mock("../../api/liveApi", async () => {
  const actual =
    await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    getUnionSupergraphProjection: vi.fn().mockResolvedValue({
      campaign_id: "longmont-c2",
      session_id: "session-25",
      graph_id: "graph-a",
      markdown: "# Candidate",
      focus: {
        focus_session_id: "session-25",
        focused_evidence_ref_ids: [],
        focused_edge_ids: [],
        focused_node_ids: [],
      },
      node_views: {
        "object-1": {
          node_id: "object-1",
          label: "Candidate Hesta",
          kind: "npc",
          role: "character",
          summary: "candidate",
          evidence_ref_ids: [],
          edge_ids: [],
          beat_ids: [],
          source_span_ids: [],
        },
      },
      source_spans: [],
      mentions: [],
    }),
    postWorldGraphProjection: vi.fn(),
  };
});

function committedProjection(
  overrides: Partial<WorldGraphProjection["snapshot"]> = {},
  nodeOverrides: Partial<WorldGraphProjection["nodes"][number]> = {},
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev:committed",
      headRevisionId: "rev:committed",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      ...overrides,
    },
    summary: {
      nodeCount: 1,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      projectionTruncated: false,
    },
    nodes: [
      {
        nodeId: "object-1",
        label: "Hesta Ironroot",
        kind: "npc",
        role: "character",
        aliases: ["Hesta"],
        sourceDomains: ["recap"],
        anchoredToFocusSession: true,
        evidenceBadges: [],
        adjacency: [],
        suggestedExpansions: [],
        evidenceRefIds: [],
        sourceArtifactIds: [],
        ...nodeOverrides,
      },
    ],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
  };
}

function receipt(
  overrides: Partial<ExtractPromoteConfirmReceipt> = {},
): ExtractPromoteConfirmReceipt {
  return {
    schema: "dmb_extract_promote_confirm_v2",
    outcome: "committed",
    worldId: "eldyrwild",
    proposalId: "prop-1",
    proposalDigest: "digest-a",
    parentRevisionId: "rev:parent",
    committedRevisionId: "rev:committed",
    headAdvanced: true,
    selectedAssertionIds: ["a-1"],
    acceptedAssertionIds: ["a-1"],
    affectedObjectIds: ["object-1"],
    appliedAssertionCount: 1,
    auditStatus: "ok",
    warnings: [],
    ...overrides,
  };
}

describe("GraphReviewCommittedProjectionPanel", () => {
  it("shows durable committed label, not conflicting candidate label", async () => {
    renderGraphReviewLiveHarness({
      sessionId: "session-25",
      children: (
        <GraphReviewCommittedProjectionPanel
          phase="ready"
          receipt={receipt()}
          projection={committedProjection()}
          selectedObjectId="object-1"
          affectedObjectIds={["object-1"]}
          error={null}
          onRetry={async () => undefined}
          onSelectObjectId={() => undefined}
        />
      ),
    });

    await waitFor(() => {
      expect(screen.getAllByText("Hesta Ironroot").length).toBeGreaterThan(0);
    });
    expect(screen.queryByText("Candidate Hesta")).toBeNull();
    expect(
      screen.getByTestId("graph-review-committed-projection-panel"),
    ).toHaveAttribute("data-phase", "ready");
  });

  it("renders receipt metadata and retry on error", () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    renderGraphReviewLiveHarness({
      children: (
        <GraphReviewCommittedProjectionPanel
          phase="error"
          receipt={receipt()}
          projection={null}
          selectedObjectId={null}
          affectedObjectIds={["object-1"]}
          error="Pinned revision unavailable"
          onRetry={onRetry}
          onSelectObjectId={() => undefined}
        />
      ),
    });

    expect(screen.getByTestId("graph-review-committed-receipt-meta")).toHaveTextContent(
      "eldyrwild",
    );
    expect(screen.getByTestId("graph-review-committed-projection-error")).toHaveTextContent(
      "Pinned revision unavailable",
    );
    screen.getByTestId("graph-review-committed-projection-retry").click();
    expect(onRetry).toHaveBeenCalled();
  });

  it("shows headRevisionId and isHead as metadata even when isHead is false", () => {
    renderGraphReviewLiveHarness({
      children: (
        <GraphReviewCommittedProjectionPanel
          phase="ready"
          receipt={receipt()}
          projection={committedProjection({
            isHead: false,
            headRevisionId: "rev:head-moved",
          })}
          selectedObjectId="object-1"
          affectedObjectIds={["object-1"]}
          error={null}
          onRetry={async () => undefined}
          onSelectObjectId={() => undefined}
        />
      ),
    });

    expect(screen.getByTestId("graph-review-committed-is-head")).toHaveTextContent("no");
    expect(screen.getByTestId("graph-review-committed-head-revision")).toHaveTextContent(
      "rev:head-moved",
    );
    expect(screen.getAllByText("Hesta Ironroot").length).toBeGreaterThan(0);
  });

  it("keeps source card visible on unresolved exact relationship target", async () => {
    const onSelectObjectId = vi.fn();
    renderGraphReviewLiveHarness({
      children: (
        <GraphReviewCommittedProjectionPanel
          phase="ready"
          receipt={receipt()}
          projection={committedProjection(
            {},
            {
              adjacency: [
                {
                  edgeId: "edge-missing",
                  nodeId: "missing-target",
                  label: "Missing Ally",
                  kind: "npc",
                  predicate: "allied_with",
                  direction: "out",
                  anchoredToFocusSession: true,
                  sourceDomains: ["recap"],
                  evidenceRefIds: [],
                  sessionIds: ["session-25"],
                },
              ],
            },
          )}
          selectedObjectId="object-1"
          affectedObjectIds={["object-1"]}
          error={null}
          onRetry={async () => undefined}
          onSelectObjectId={onSelectObjectId}
        />
      ),
    });

    fireEvent.click(
      screen.getByRole("button", { name: /Open related object .*Missing Ally/i }),
    );

    expect(
      screen.getByTestId("graph-review-committed-unresolved-target"),
    ).toHaveTextContent("missing-target");
    expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    expect(screen.getAllByText("Hesta Ironroot").length).toBeGreaterThan(0);
    expect(onSelectObjectId).not.toHaveBeenCalled();
  });
});
