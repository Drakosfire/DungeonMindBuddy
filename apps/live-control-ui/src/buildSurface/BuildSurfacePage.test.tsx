import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import * as liveApi from "../api/liveApi";
import type { WorkspaceDocumentRecord } from "../api/types";
import { BuildSurfacePage } from "./BuildSurfacePage";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    createWorkspaceDocument: vi.fn(),
    getWorkspaceDocument: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
  };
});

const DOC_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

function worldbuildingRecord(
  overrides: Partial<WorkspaceDocumentRecord> = {},
): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: DOC_ID,
    title: "Untitled worldbuilding source",
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
    document_class: "lore",
    authority_state: "draft",
    visibility_state: "internal",
    ...overrides,
  };
}

function ContextProbe() {
  const { activeSurfaceContext } = useAgentInteraction();
  return (
    <div data-testid="active-surface-context">
      {activeSurfaceContext
        ? `${activeSurfaceContext.surfaceId}:${activeSurfaceContext.documentId}`
        : "none"}
    </div>
  );
}

function renderPage() {
  return render(
    <AgentInteractionProvider>
      <ContextProbe />
      <BuildSurfacePage />
    </AgentInteractionProvider>,
  );
}

describe("BuildSurfacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.pushState({}, "", "/build");
  });

  it("creates a worldbuilding_source when no documentId is present and publishes ambient context", async () => {
    const record = worldbuildingRecord();
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(record);

    renderPage();

    expect(await screen.findByTestId("build-surface-title")).toHaveTextContent(record.title);
    expect(screen.getByTestId("build-document-id")).toHaveTextContent(DOC_ID);
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "worldbuilding_source",
        source_domain: "worldbuilding",
        document_class: "lore",
      }),
    );
    expect(window.location.search).toContain(`documentId=${DOC_ID}`);
    await waitFor(() => {
      expect(screen.getByTestId("active-surface-context")).toHaveTextContent(`build:${DOC_ID}`);
    });
  });

  it("reloads the exact UUID from documentId", async () => {
    const record = worldbuildingRecord({ title: "Mirathorn Notes", revision: 3 });
    vi.mocked(liveApi.getWorkspaceDocument).mockResolvedValue(record);
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}`);

    renderPage();

    expect(await screen.findByTestId("build-surface-title")).toHaveTextContent("Mirathorn Notes");
    expect(screen.getByTestId("build-revision")).toHaveTextContent("3");
    expect(liveApi.getWorkspaceDocument).toHaveBeenCalledWith(DOC_ID);
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("shows a recoverable error for unknown UUID and never fabricates a source", async () => {
    vi.mocked(liveApi.getWorkspaceDocument).mockRejectedValue(new Error("Workspace document not found"));
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}`);

    renderPage();

    expect(await screen.findByTestId("build-load-error")).toHaveTextContent(/not found/i);
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(screen.queryByTestId("build-surface-editor")).not.toBeInTheDocument();

    const user = userEvent.setup();
    vi.mocked(liveApi.getWorkspaceDocument).mockResolvedValue(worldbuildingRecord());
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByTestId("build-surface-editor")).toBeInTheDocument();
  });
});
