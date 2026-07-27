import { existsSync } from "node:fs";
import { render, screen, waitFor } from "@testing-library/react";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { BuildGraphObjectContext } from "./BuildGraphObjectContext";
import { BuildSurfacePage } from "./BuildSurfacePage";

const buildSurfaceDir = path.dirname(fileURLToPath(import.meta.url));

describe("BuildGraphObjectContext", () => {
  it("production module exists", () => {
    expect(existsSync(path.join(buildSurfaceDir, "BuildGraphObjectContext.tsx"))).toBe(true);
  });

  it("loads exact node from pinned World Graph projection", async () => {
    window.history.replaceState(
      {},
      "",
      `/build?campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=${session23WorldGraphRecapFixture.snapshot.revisionId}`,
    );
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: session23WorldGraphRecapFixture.snapshot,
      summary: {
        nodeCount: 1,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [session23WorldGraphRecapFixture.nodeViews.pc_caelynn],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });

    render(<BuildGraphObjectContext />);
    expect(await screen.findByTestId("build-graph-object-context")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Caelynn")).toBeInTheDocument();
    });
    expect(liveApi.postWorldGraphProjection).toHaveBeenCalledWith(
      expect.objectContaining({
        campaignId: "longmont-c2",
        revisionPin: session23WorldGraphRecapFixture.snapshot.revisionId,
        focus: { kind: "none", sessionId: null },
      }),
    );
  });

  it("refuses document-backed load when requireDocumentScope lacks an admitted campaign", async () => {
    window.history.replaceState(
      {},
      "",
      `/build?campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=${session23WorldGraphRecapFixture.snapshot.revisionId}`,
    );
    const postProjection = vi.spyOn(liveApi, "postWorldGraphProjection");

    render(<BuildGraphObjectContext documentCampaignId={null} requireDocumentScope />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/Select a Build source/i);
    expect(postProjection).not.toHaveBeenCalled();
  });

  it("BuildSurfacePage renders graph context beside new-source form", () => {
    window.history.replaceState(
      {},
      "",
      `/build?campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=${session23WorldGraphRecapFixture.snapshot.revisionId}`,
    );
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: session23WorldGraphRecapFixture.snapshot,
      summary: {
        nodeCount: 1,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [session23WorldGraphRecapFixture.nodeViews.pc_caelynn],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });
    render(
      <AgentInteractionProvider>
        <BuildSurfacePage />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("build-new-source-form")).toBeInTheDocument();
    expect(screen.getByTestId("build-graph-object-context")).toBeInTheDocument();
  });
});
