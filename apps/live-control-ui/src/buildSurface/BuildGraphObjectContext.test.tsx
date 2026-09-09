import { existsSync } from "node:fs";
import { render, screen, waitFor } from "@testing-library/react";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { BuildGraphObjectContext } from "./BuildGraphObjectContext";
import { BuildSurfacePage } from "./BuildSurfacePage";

const buildSurfaceDir = path.dirname(fileURLToPath(import.meta.url));

function completeObjectFixture() {
  return {
    schema: "dmb_world_graph_object_projection_v1" as const,
    found: true,
    completeness: { status: "complete" as const, truncatedFields: [] },
    snapshot: session23WorldGraphRecapFixture.snapshot,
    requestedNodeId: "pc_caelynn",
    resolvedNodeId: "pc_caelynn",
    node: session23WorldGraphRecapFixture.nodeViews.pc_caelynn,
    relatedNodes: [],
    semanticFingerprint: "fp-test",
  };
}

describe("BuildGraphObjectContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("production module exists", () => {
    expect(existsSync(path.join(buildSurfaceDir, "BuildGraphObjectContext.tsx"))).toBe(true);
  });

  it("loads exact node from complete World-object projection", async () => {
    window.history.replaceState(
      {},
      "",
      `/build?campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=${session23WorldGraphRecapFixture.snapshot.revisionId}`,
    );
    vi.spyOn(liveApi, "postWorldGraphCompleteObject").mockResolvedValue(completeObjectFixture());

    render(<BuildGraphObjectContext />);
    expect(await screen.findByTestId("build-graph-object-context")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Caelynn")).toBeInTheDocument();
    });
    expect(liveApi.postWorldGraphCompleteObject).toHaveBeenCalledWith(
      expect.objectContaining({
        campaignId: "longmont-c2",
        nodeId: "pc_caelynn",
        revisionPin: session23WorldGraphRecapFixture.snapshot.revisionId,
        originSurface: "build",
      }),
    );
  });

  it("refuses document-backed load when requireDocumentScope lacks an admitted campaign", async () => {
    window.history.replaceState(
      {},
      "",
      `/build?campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=${session23WorldGraphRecapFixture.snapshot.revisionId}`,
    );
    const postComplete = vi.spyOn(liveApi, "postWorldGraphCompleteObject");

    render(<BuildGraphObjectContext documentCampaignId={null} requireDocumentScope />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/Select a Build source/i);
    expect(postComplete).not.toHaveBeenCalled();
  });

  it("BuildSurfacePage opens graph context when document is admitted from URL", async () => {
    const documentId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    window.history.replaceState(
      {},
      "",
      `/build?documentId=${documentId}&campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=${session23WorldGraphRecapFixture.snapshot.revisionId}`,
    );
    vi.spyOn(liveApi, "createWorkspaceDocument");
    vi.spyOn(liveApi, "listWorkspaceDocuments").mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [],
    });
    vi.spyOn(liveApi, "getWorkspaceDocumentSnapshot").mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: documentId,
        title: "Untitled worldbuilding source",
        campaign_id: "longmont-c2",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
        status: "active",
        content_status: "draft",
        revision: 1,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      },
      markdown: "",
      content_sha256: "sha-empty",
      file_fingerprint: "absent",
      file_exists: false,
      loaded_revision: 1,
    });
    vi.spyOn(liveApi, "postWorldGraphCompleteObject").mockResolvedValue(completeObjectFixture());
    render(
      <AgentInteractionProvider>
        <SurfaceContextProvider>
          <BuildSurfacePage />
        </SurfaceContextProvider>
      </AgentInteractionProvider>,
    );
    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(await screen.findByTestId("build-graph-object-context")).toBeInTheDocument();
  });
});
