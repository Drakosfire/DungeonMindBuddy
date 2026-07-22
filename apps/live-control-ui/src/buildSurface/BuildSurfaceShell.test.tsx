import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import * as liveApi from "../api/liveApi";
import type { WorkspaceDocumentRecord } from "../api/types";
import { writeBuildLocalDraft, buildDraftFromRecord } from "./buildLocalDraft";
import { BuildSurfaceShell } from "./BuildSurfaceShell";

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

const DOC_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function worldbuildingRecord(
  overrides: Partial<WorkspaceDocumentRecord> = {},
): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: DOC_ID,
    title: "World source",
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

function renderShell(onEditorToolsChange = vi.fn()) {
  return render(
    <AgentInteractionProvider>
      <BuildSurfaceShell onEditorToolsChange={onEditorToolsChange} />
    </AgentInteractionProvider>,
  );
}

describe("BuildSurfaceShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}`);
    vi.mocked(liveApi.getWorkspaceDocument).mockResolvedValue(worldbuildingRecord());
  });

  it("renders shared surface metadata and editor through Build composition", async () => {
    renderShell();

    expect(await screen.findByTestId("build-surface")).toHaveAttribute("data-surface", "build");
    expect(screen.getByTestId("build-source-metadata")).toHaveTextContent("worldbuilding_source");
    expect(screen.getByTestId("build-source-metadata")).toHaveTextContent("worldbuilding");
    expect(screen.getByTestId("build-source-metadata")).toHaveTextContent("lore");
    expect(screen.getByTestId("build-source-metadata")).toHaveTextContent("draft");
    expect(screen.getByTestId("build-source-metadata")).toHaveTextContent("internal");
    expect(screen.getByTestId("build-surface-editor")).toBeInTheDocument();
  });

  it("restores a dirty local draft bound to the exact document UUID", async () => {
    writeBuildLocalDraft(
      localStorage,
      buildDraftFromRecord(
        worldbuildingRecord(),
        {
          type: "doc",
          content: [{ type: "paragraph", content: [{ type: "text", text: "Local draft body" }] }],
        },
        true,
      ),
    );

    renderShell();

    expect(await screen.findByTestId("build-surface-save-status")).toHaveTextContent(
      /Local edits not yet committed/i,
    );
    expect(await screen.findByText("Local draft body")).toBeInTheDocument();
  });

  it("commits markdown when prepare succeeds and updates revision", async () => {
    const user = userEvent.setup();
    const onEditorToolsChange = vi.fn();
    const committed = worldbuildingRecord({ revision: 2, content_status: "committed" });
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "World source",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      target_display_path: `out/workspace/worldbuilding/${DOC_ID}.md`,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "token-1",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_ID,
      title: "World source",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      target_display_path: `out/workspace/worldbuilding/${DOC_ID}.md`,
      registry_revision: 2,
      writer_ok: true,
      bytes_written: 12,
      diagnostics: [],
    });
    vi.mocked(liveApi.getWorkspaceDocument)
      .mockResolvedValueOnce(worldbuildingRecord())
      .mockResolvedValueOnce(committed);

    renderShell(onEditorToolsChange);

    await screen.findByTestId("build-surface");
    await waitFor(() => {
      expect(onEditorToolsChange).toHaveBeenCalled();
    });

    const tools = onEditorToolsChange.mock.calls.at(-1)?.[0];
    const unlock = tools?.pinnedActions?.find((action: { id: string }) => action.id === "build-lock-editing");
    const save = tools?.sections
      ?.flatMap((section: { actions: Array<{ id: string; onClick: () => void; disabled?: boolean }> }) => section.actions)
      ?.find((action: { id: string }) => action.id === "build-save-markdown");
    expect(unlock).toBeDefined();
    expect(save).toBeDefined();

    unlock?.onClick();
    await waitFor(() => {
      const nextTools = onEditorToolsChange.mock.calls.at(-1)?.[0];
      const nextSave = nextTools?.sections
        ?.flatMap((section: { actions: Array<{ id: string; disabled?: boolean }> }) => section.actions)
        ?.find((action: { id: string }) => action.id === "build-save-markdown");
      expect(nextSave?.disabled).toBe(false);
    });

    const enabledSave = onEditorToolsChange.mock.calls.at(-1)?.[0]?.sections
      ?.flatMap((section: { actions: Array<{ id: string; onClick: () => void }> }) => section.actions)
      ?.find((action: { id: string }) => action.id === "build-save-markdown");
    enabledSave?.onClick();

    await waitFor(() => {
      expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalled();
      expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalled();
    });
    expect(await screen.findByTestId("build-revision")).toHaveTextContent("2");
    expect(screen.getByTestId("build-surface-save-status")).toHaveTextContent(/Committed 12 bytes/i);
    expect(user).toBeTruthy();
  });

  it("preserves dirty identity when prepare blocks the write", async () => {
    const onEditorToolsChange = vi.fn();
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "World source",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      target_display_path: `out/workspace/worldbuilding/${DOC_ID}.md`,
      registry_revision: 1,
      file_exists: false,
      writer_ok: false,
      warnings: [],
      diagnostics: ["revision conflict"],
    });

    renderShell(onEditorToolsChange);
    await screen.findByTestId("build-surface");
    await waitFor(() => expect(onEditorToolsChange).toHaveBeenCalled());

    const tools = onEditorToolsChange.mock.calls.at(-1)?.[0];
    tools?.pinnedActions?.find((action: { id: string }) => action.id === "build-lock-editing")?.onClick();
    await waitFor(() => {
      const nextTools = onEditorToolsChange.mock.calls.at(-1)?.[0];
      const nextSave = nextTools?.sections
        ?.flatMap((section: { actions: Array<{ id: string; disabled?: boolean }> }) => section.actions)
        ?.find((action: { id: string }) => action.id === "build-save-markdown");
      expect(nextSave?.disabled).toBe(false);
    });

    onEditorToolsChange.mock.calls.at(-1)?.[0]?.sections
      ?.flatMap((section: { actions: Array<{ id: string; onClick: () => void }> }) => section.actions)
      ?.find((action: { id: string }) => action.id === "build-save-markdown")
      ?.onClick();

    expect(await screen.findByTestId("build-save-error")).toHaveTextContent(/Prepare blocked/i);
    expect(screen.getByTestId("build-document-id")).toHaveTextContent(DOC_ID);
    expect(screen.getByTestId("build-revision")).toHaveTextContent("1");
    expect(liveApi.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });
});
