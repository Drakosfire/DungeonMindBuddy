import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import {
  WorldGraphLensProvider,
  WorldGraphLensProjectionProvider,
} from "../graphLens";
import { AppChrome } from "./AppChrome";
import { WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID } from "./appChromeConfig";

vi.mock("../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../api/liveApi")>("../api/liveApi");
  return {
    ...actual,
    postWorldGraphProjection: vi.fn().mockResolvedValue({
      schema: "dmb_world_graph_projection_response_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "campaign",
      nodes: [{ nodeId: "npc-x", label: "X", kind: "npc", role: null }],
      edges: [],
      snapshot: { revisionId: "rev-1", isHead: true },
    }),
    getSourceBundle: vi.fn().mockResolvedValue({
      schema: "dmb_ingestion_source_bundle_v1",
      campaigns: {},
    }),
  };
});

function renderChrome(activeRoute: "index" | "plan" | "build") {
  return render(
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        <WorldGraphLensProvider planCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}>
          <WorldGraphLensProjectionProvider defaultCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}>
            <AppChrome activeRoute={activeRoute}>
              <main>page</main>
            </AppChrome>
          </WorldGraphLensProjectionProvider>
        </WorldGraphLensProvider>
      </AskPluginSlotProvider>
    </AgentInteractionProvider>,
  );
}

describe("AppChromeGraphLens", () => {
  it("shows the World Graph lens strip on Plan and Build, not Index", async () => {
    const { unmount } = renderChrome("plan");
    expect(await screen.findByTestId("app-chrome-graph-lens")).toBeInTheDocument();
    expect(screen.getByText("Graph campaigns")).toBeInTheDocument();
    expect(screen.getByLabelText("Focus session")).toBeInTheDocument();
    unmount();

    const build = renderChrome("build");
    expect(await build.findByTestId("app-chrome-graph-lens")).toBeInTheDocument();
    build.unmount();

    const index = renderChrome("index");
    expect(index.queryByTestId("app-chrome-graph-lens")).not.toBeInTheDocument();
    index.unmount();
  });
});
