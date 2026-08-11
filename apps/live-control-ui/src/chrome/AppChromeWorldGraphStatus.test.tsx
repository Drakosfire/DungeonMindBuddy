import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import {
  WorldGraphLensProvider,
  WorldGraphLensProjectionProvider,
} from "../graphLens";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { AppChrome } from "./AppChrome";
import { WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID } from "./appChromeConfig";
import { presentWorldGraphChromeStatus } from "./AppChromeWorldGraphStatus";

vi.mock("../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../api/liveApi")>("../api/liveApi");
  return {
    ...actual,
    postWorldGraphProjection: vi.fn().mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev-1",
        headRevisionId: "rev-1",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        scopeMode: "campaign",
      },
      summary: {
        nodeCount: 1284,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [{ nodeId: "npc-x", label: "X", kind: "npc", role: null }],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    }),
    getSourceBundle: vi.fn().mockResolvedValue({
      schema: "dmb_ingestion_source_bundle_v1",
      campaigns: {},
    }),
  };
});

function renderChrome(activeRoute: "index" | "plan" | "build" | "ingest") {
  return render(
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        <WorldGraphLensProvider planCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}>
          <WorldGraphLensProjectionProvider defaultCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}>
            <SurfaceContextProvider>
              <AppChrome activeRoute={activeRoute}>
                <main>page</main>
              </AppChrome>
            </SurfaceContextProvider>
          </WorldGraphLensProjectionProvider>
        </WorldGraphLensProvider>
      </AskPluginSlotProvider>
    </AgentInteractionProvider>,
  );
}

describe("presentWorldGraphChromeStatus", () => {
  it("reports not loaded without projection context", () => {
    expect(
      presentWorldGraphChromeStatus({
        hasProjectionContext: false,
        hasLensControls: false,
        projectionState: null,
        projectionError: null,
        focusValidationStatus: null,
        selectedCampaignIds: null,
        focus: null,
      }).tone,
    ).toBe("not_loaded");
  });

  it("reports loading and ready presentations from structured lens state", () => {
    expect(
      presentWorldGraphChromeStatus({
        hasProjectionContext: true,
        hasLensControls: true,
        projectionState: "loading",
        projectionError: null,
        focusValidationStatus: "none",
        selectedCampaignIds: ["longmont-c2"],
        focus: null,
      }).compactLabel,
    ).toContain("Loading");

    expect(
      presentWorldGraphChromeStatus({
        hasProjectionContext: true,
        hasLensControls: true,
        projectionState: "ready",
        projectionError: null,
        focusValidationStatus: "none",
        selectedCampaignIds: ["longmont-c2"],
        focus: { campaignId: "longmont-c2", sessionNumber: 25 },
      }),
    ).toMatchObject({
      tone: "ready",
      compactLabel: "C2 · S25 · Ready",
    });
  });

  it("preserves C1+C2 union with no focus", () => {
    expect(
      presentWorldGraphChromeStatus({
        hasProjectionContext: true,
        hasLensControls: true,
        projectionState: "ready",
        projectionError: null,
        focusValidationStatus: "none",
        selectedCampaignIds: ["longmont-c1", "longmont-c2"],
        focus: null,
      }),
    ).toMatchObject({
      tone: "ready",
      compactLabel: "C1+C2 · Ready",
      fullLabel: "World · C1+C2 · Ready",
    });
  });

  it("preserves C1+C2 union and C2/S25 focus together", () => {
    // summaryLabel would be "Union · C1+C2 · C2 · Session 25" — parsing the first C#
    // used to collapse this to "C1 · S25 · Ready".
    expect(
      presentWorldGraphChromeStatus({
        hasProjectionContext: true,
        hasLensControls: true,
        projectionState: "ready",
        projectionError: null,
        focusValidationStatus: "none",
        selectedCampaignIds: ["longmont-c1", "longmont-c2"],
        focus: { campaignId: "longmont-c2", sessionNumber: 25 },
      }),
    ).toMatchObject({
      tone: "ready",
      compactLabel: "C1+C2 · C2 · S25 · Ready",
      fullLabel: "World · C1+C2 · C2 · S25 · Ready",
    });
  });
});

describe("AppChromeWorldGraphStatus", () => {
  it("shows World Graph status on Index, Plan, Build, and Ingest", async () => {
    for (const route of ["index", "plan", "build", "ingest"] as const) {
      const view = renderChrome(route);
      expect(await view.findByTestId("app-chrome-world-graph-status")).toBeInTheDocument();
      expect(view.queryByTestId("app-chrome-graph-lens")).not.toBeInTheDocument();
      view.unmount();
    }
  });

  it("opens lens controls from the compact status without expanding the nav", async () => {
    const user = (await import("@testing-library/user-event")).default.setup();
    renderChrome("plan");
    const trigger = await screen.findByTestId("app-chrome-world-graph-status");
    await user.click(trigger);
    expect(await screen.findByTestId("surface-context-popover")).toBeInTheDocument();
    expect(screen.getByText("Graph campaigns")).toBeInTheDocument();
    expect(screen.getByLabelText("Focus session")).toBeInTheDocument();
  });
});
