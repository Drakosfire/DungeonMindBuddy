import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { WorldGraphRecapProjectionView } from "./WorldGraphRecapProjection";
import { session23WorldGraphRecapFixture } from "./worldGraphRecapFixture";

describe("WorldGraphRecapProjectionView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(liveApi, "postWorldGraphCompleteObject").mockImplementation(async (request) => {
      const node = session23WorldGraphRecapFixture.nodeViews[request.nodeId] ?? null;
      return {
        schema: "dmb_world_graph_object_projection_v1",
        found: Boolean(node),
        completeness: { status: "complete", truncatedFields: [] },
        snapshot: session23WorldGraphRecapFixture.snapshot,
        requestedNodeId: request.nodeId,
        resolvedNodeId: node ? request.nodeId : null,
        node,
        relatedNodes: [],
        semanticFingerprint: "fp-test",
      };
    });
  });

  it("opens a campaign-memory Peek without World Object chrome or Continue in Build", async () => {
    render(
      <WorldGraphRecapProjectionView
        payload={session23WorldGraphRecapFixture}
        selectedSessionId="session-23"
        onSelectSession={vi.fn()}
        sessionOptions={["session-23"]}
        selectedCampaignId="longmont-c2"
        onSelectCampaign={vi.fn()}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: /Caelynn/i }));
    await waitFor(() => {
      expect(liveApi.postWorldGraphCompleteObject).toHaveBeenCalled();
    });

    expect(screen.queryByText("World object")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Continue in Build/i })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent("Caelynn");
    expect(screen.getByLabelText("Caelynn graph object")).toHaveAttribute(
      "data-graph-object-card-mode",
      "campaign-memory",
    );

    fireEvent.click(screen.getByRole("button", { name: /Close Caelynn/i }));
    expect(screen.queryByTestId("graph-object-projection-card")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Published recap")).toBeInTheDocument();
  });
});
