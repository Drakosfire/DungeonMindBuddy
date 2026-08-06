import { existsSync } from "node:fs";
import { render, screen, waitFor } from "@testing-library/react";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { BuildGraphObjectContext } from "./BuildGraphObjectContext";
import {
  BuildSurfacePage,
  resetBuildBareEntryAutoCreateForTests,
} from "./BuildSurfacePage";

const buildSurfaceDir = path.dirname(fileURLToPath(import.meta.url));

describe("BuildGraphObjectContext", () => {
  beforeEach(() => {
    resetBuildBareEntryAutoCreateForTests();
  });

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

  it("BuildSurfacePage auto-creates draft and keeps graph pointer on admitted Canvas", async () => {
    window.history.replaceState(
      {},
      "",
      `/build?campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=${session23WorldGraphRecapFixture.snapshot.revisionId}`,
    );
    const documentId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    vi.spyOn(liveApi, "createWorkspaceDocument").mockResolvedValue({
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
    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(await screen.findByTestId("build-graph-object-context")).toBeInTheDocument();
  });
});
