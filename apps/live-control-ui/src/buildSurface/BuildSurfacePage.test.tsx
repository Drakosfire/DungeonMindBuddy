import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { BuildSurfacePage } from "./BuildSurfacePage";

function renderBuildPage() {
  return render(
    <AgentInteractionProvider>
      <BuildSurfacePage />
    </AgentInteractionProvider>,
  );
}

function BuildProjectionProbe() {
  const { projectionSurface } = useAgentInteraction();
  return (
    <p data-testid="build-projection-enabled">
      {projectionSurface?.projectionsEnabled ? "enabled" : "inactive"}
    </p>
  );
}

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    createWorkspaceDocument: vi.fn(),
    getWorkspaceDocumentSnapshot: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
  };
});

const DOC_ID = "11111111-1111-4111-8111-111111111111";

describe("BuildSurfacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.pushState({}, "", "/build");
  });

  it("does not create a document on mount without documentId", () => {
    render(
      <AgentInteractionProvider>
        <BuildSurfacePage />
        <BuildProjectionProbe />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("build-new-source-form")).toBeInTheDocument();
    expect(screen.getByTestId("build-projection-enabled")).toHaveTextContent("inactive");
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("creates a document only when the new-source form is submitted", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue({
      schema_version: "dmb_workspace_document_record_v1",
      document_id: DOC_ID,
      title: "Faction Notes",
      campaign_id: "eldyrwild",
      target_session: null,
      kind: "worldbuilding_source",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      status: "active",
      content_status: "draft",
      revision: 1,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "faction",
      authority_state: "draft",
      visibility_state: "internal",
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Faction Notes",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "draft",
        revision: 1,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "faction",
        authority_state: "draft",
        visibility_state: "internal",
      },
      markdown: "",
      content_sha256: "sha-empty",
      file_fingerprint: "absent",
      file_exists: false,
      loaded_revision: 1,
    });

    renderBuildPage();
    await user.type(screen.getByTestId("build-new-title"), "Faction Notes");
    await user.clear(screen.getByTestId("build-new-class"));
    await user.type(screen.getByTestId("build-new-class"), "faction");
    await user.click(screen.getByTestId("build-create-button"));

    await waitFor(() => {
      expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith({
      title: "Faction Notes",
      campaign_id: "eldyrwild",
      kind: "worldbuilding_source",
      source_domain: "worldbuilding",
      document_class: "faction",
      authority_state: "draft",
      visibility_state: "internal",
    });
  });

  it("loads snapshot markdown when reopening with documentId", async () => {
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Reopened Lore",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "committed",
        revision: 3,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "reviewed",
        visibility_state: "internal",
      },
      markdown: "# Reopened Lore\n\nExact snapshot body.\n",
      content_sha256: "sha-reopened",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 3,
    });

    renderBuildPage();

    await waitFor(() => {
      expect(liveApi.getWorkspaceDocumentSnapshot).toHaveBeenCalledWith(DOC_ID);
    });
    expect(await screen.findByTestId("build-surface-shell")).toBeInTheDocument();
    expect(screen.getByTestId("build-document-status")).toHaveTextContent("Committed");
  });

  it("follows browser back/forward documentId changes", async () => {
    const otherId = "22222222-2222-4222-8222-222222222222";
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id: string) => ({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: id,
        title: id === DOC_ID ? "Doc A" : "Doc B",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${id}.md`,
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
      markdown: `# ${id}\n`,
      content_sha256: `sha-${id}`,
      file_fingerprint: "absent",
      file_exists: false,
      loaded_revision: 1,
    }));

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}`);
    renderBuildPage();
    expect(await screen.findByText("Doc A")).toBeInTheDocument();

    window.history.pushState({}, "", `/build?documentId=${otherId}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(await screen.findByText("Doc B")).toBeInTheDocument();

    window.history.pushState({}, "", "/build");
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(await screen.findByTestId("build-new-source-form")).toBeInTheDocument();
  });

  it("PR380B: shows graph-object context when pointer params are present", async () => {
    window.history.pushState(
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
    renderBuildPage();
    expect(await screen.findByTestId("build-graph-object-context")).toBeInTheDocument();
    expect(screen.getByTestId("build-new-campaign")).toHaveValue("longmont-c2");
  });
});
