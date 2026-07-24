import type { ComponentProps } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/core";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import * as liveApi from "../api/liveApi";
import {
  buildInitialWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
  writeWorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import { BUILD_AUTHORITY_REJECTION_AMBIENT, BuildSurfaceShell } from "./BuildSurfaceShell";

let buildShellTestEditor: Editor | null = null;

vi.mock("../tiptap/MarkdownEditorCore", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../tiptap/MarkdownEditorCore")>();
  return {
    ...actual,
    MarkdownEditorCore: (
      props: ComponentProps<typeof actual.MarkdownEditorCore>,
    ) => (
      <actual.MarkdownEditorCore
        {...props}
        onEditorChange={(editor) => {
          buildShellTestEditor = editor;
          props.onEditorChange?.(editor);
        }}
      />
    ),
  };
});

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
  };
});

const DOC_ID = "11111111-1111-4111-8111-111111111111";

function ScopeProbe() {
  const { scope, activeSurfaceContext } = useAgentInteraction();
  return (
    <div
      data-testid="scope-probe"
      data-session={scope?.sessionNumber === null ? "null" : String(scope?.sessionNumber ?? "missing")}
      data-context-session={
        activeSurfaceContext?.sessionNumber === null
          ? "null"
          : String(activeSurfaceContext?.sessionNumber ?? "missing")
      }
      data-document-id={scope?.documentId ?? "null"}
      data-context-document-id={activeSurfaceContext?.documentId ?? "null"}
      data-ambient={activeSurfaceContext?.ambientSummary ?? "null"}
      data-envelope={activeSurfaceContext?.sourceEnvelope ? "present" : "null"}
    />
  );
}

function buildWorldbuildingSnapshot(documentId: string) {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1" as const,
    record: {
      schema_version: "dmb_workspace_document_record_v1" as const,
      document_id: documentId,
      title: "Build Source",
      campaign_id: "eldyrwild",
      target_session: null,
      kind: "worldbuilding_source" as const,
      target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
      status: "active" as const,
      content_status: "draft" as const,
      revision: 1,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    },
    markdown: "# Build Source\n",
    content_sha256: "sha-build",
    file_fingerprint: "absent",
    file_exists: false,
    loaded_revision: 1,
  };
}

function BuildDocumentHarness({ documentId }: { documentId: string }) {
  return (
    <AgentInteractionProvider>
      <ScopeProbe />
      <BuildSurfaceShell key={documentId} documentId={documentId} />
    </AgentInteractionProvider>
  );
}

describe("BuildSurfaceShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    buildShellTestEditor = null;
  });

  it("publishes null session scope for worldbuilding build", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Build Source",
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
      },
      markdown: "# Build Source\n",
      content_sha256: "sha-build",
      file_fingerprint: "absent",
      file_exists: false,
      loaded_revision: 1,
    });

    render(
      <AgentInteractionProvider>
        <ScopeProbe />
        <BuildSurfaceShell documentId={DOC_ID} />
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("build-surface-shell")).toBeInTheDocument();
    });

    const probe = screen.getByTestId("scope-probe");
    expect(probe).toHaveAttribute("data-session", "null");
    expect(probe).toHaveAttribute("data-context-session", "null");
    expect(screen.getByTestId("build-document-status")).toHaveTextContent("Draft");
  });

  it("rejects plan documents before enabling the editor", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Session Prep",
        campaign_id: "eldyrwild",
        target_session: 4,
        kind: "plan",
        target_relpath: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Prep/Session 4 Prep.md",
        status: "active",
        content_status: "committed",
        revision: 2,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: null,
        document_class: null,
        authority_state: null,
        visibility_state: null,
      },
      markdown: "# Prep\n",
      content_sha256: "sha-plan",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 2,
    });

    render(
      <AgentInteractionProvider>
        <ScopeProbe />
        <BuildSurfaceShell documentId={DOC_ID} />
      </AgentInteractionProvider>,
    );

    expect(await screen.findByTestId("build-surface-error")).toBeInTheDocument();
    expect(screen.queryByTestId("build-save-button")).not.toBeInTheDocument();
    expect(screen.queryByTestId("build-markdown-editor")).not.toBeInTheDocument();
    expect(window.localStorage.getItem(workspaceDocumentStorageKey(DOC_ID))).toBeNull();

    await waitFor(() => {
      const probe = screen.getByTestId("scope-probe");
      expect(probe).toHaveAttribute("data-document-id", "null");
      expect(probe).toHaveAttribute("data-context-document-id", "null");
    });
  });

  it("clears accepted Agent Interaction context when navigating from valid build to rejected plan UUID", async () => {
    const PLAN_DOC_ID = "22222222-2222-4222-8222-222222222222";
    const validSnapshot = {
      schema_version: "dmb_workspace_document_snapshot_v1" as const,
      record: {
        schema_version: "dmb_workspace_document_record_v1" as const,
        document_id: DOC_ID,
        title: "Build Source",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source" as const,
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active" as const,
        content_status: "draft" as const,
        revision: 1,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      },
      markdown: "# Build Source\n",
      content_sha256: "sha-build",
      file_fingerprint: "absent",
      file_exists: false,
      loaded_revision: 1,
    };
    const rejectedSnapshot = {
      schema_version: "dmb_workspace_document_snapshot_v1" as const,
      record: {
        schema_version: "dmb_workspace_document_record_v1" as const,
        document_id: PLAN_DOC_ID,
        title: "Session Prep",
        campaign_id: "eldyrwild",
        target_session: 4,
        kind: "plan" as const,
        target_relpath: "corpus/prep.md",
        status: "active" as const,
        content_status: "committed" as const,
        revision: 2,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: null,
        document_class: null,
        authority_state: null,
        visibility_state: null,
      },
      markdown: "# Prep\n",
      content_sha256: "sha-plan",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 2,
    };

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(validSnapshot);

    const { rerender } = render(
      <AgentInteractionProvider>
        <ScopeProbe />
        <BuildSurfaceShell documentId={DOC_ID} />
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("build-surface-shell")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByTestId("scope-probe")).toHaveAttribute("data-document-id", DOC_ID);
    });

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(rejectedSnapshot);
    rerender(
      <AgentInteractionProvider>
        <ScopeProbe />
        <BuildSurfaceShell documentId={PLAN_DOC_ID} />
      </AgentInteractionProvider>,
    );

    expect(await screen.findByTestId("build-surface-error")).toBeInTheDocument();
    await waitFor(() => {
      const probe = screen.getByTestId("scope-probe");
      expect(probe).toHaveAttribute("data-document-id", "null");
      expect(probe).toHaveAttribute("data-context-document-id", "null");
    });
    expect(screen.queryByTestId("build-markdown-editor")).not.toBeInTheDocument();
  });

  it("discards conflicting local draft and opens server content", async () => {
    const user = (await import("@testing-library/user-event")).default.setup();
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Build Source",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "committed",
        revision: 4,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      },
      markdown: "# Server copy\n",
      content_sha256: "sha-new",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 4,
    });

    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "Build Source",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 3,
      baseContentSha256: "sha-old",
      starterContent: { type: "doc", content: [] },
    });
    local.dirty = true;
    local.exported_markdown = "# Local dirty copy\n";
    writeWorkspaceDocumentLocalState(window.localStorage, local);

    render(
      <AgentInteractionProvider>
        <BuildSurfaceShell documentId={DOC_ID} />
      </AgentInteractionProvider>,
    );

    expect(await screen.findByTestId("build-surface-conflict")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /discard local draft/i }));
    expect(await screen.findByTestId("build-surface-shell")).toBeInTheDocument();
    expect(screen.getByTestId("build-document-status")).toHaveTextContent("Committed");
    const stored = window.localStorage.getItem(workspaceDocumentStorageKey(DOC_ID));
    expect(stored).toBeTruthy();
    expect(JSON.parse(stored!).dirty).toBe(false);
    expect(JSON.parse(stored!).base_revision).toBe(4);
  });

  it("shows conflict when dirty local draft base mismatches snapshot", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Build Source",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "committed",
        revision: 4,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      },
      markdown: "# Server copy\n",
      content_sha256: "sha-new",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 4,
    });

    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "Build Source",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 3,
      baseContentSha256: "sha-old",
      starterContent: { type: "doc", content: [] },
    });
    local.dirty = true;
    local.exported_markdown = "# Local dirty copy\n";
    writeWorkspaceDocumentLocalState(window.localStorage, local);

    render(
      <AgentInteractionProvider>
        <BuildSurfaceShell documentId={DOC_ID} />
      </AgentInteractionProvider>,
    );

    expect(await screen.findByTestId("build-surface-conflict")).toBeInTheDocument();
    expect(screen.getByText(/changed while a dirty local draft/i)).toBeInTheDocument();
  });

  it("distinguishes dirty vs committed status labels", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Build Source",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "committed",
        revision: 2,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      },
      markdown: "# Build Source\n",
      content_sha256: "sha-build",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 2,
    });

    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "Build Source",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-build",
      starterContent: { type: "doc", content: [] },
    });
    local.dirty = true;
    local.exported_markdown = "# Dirty local\n";
    window.localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), JSON.stringify(local));

    render(
      <AgentInteractionProvider>
        <BuildSurfaceShell documentId={DOC_ID} />
      </AgentInteractionProvider>,
    );

    expect(await screen.findByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
  });

  it("clears accepted document context while the next document is loading", async () => {
    const DOC_B = "33333333-3333-4333-8333-333333333333";
    let releaseB: ((snapshot: ReturnType<typeof buildWorldbuildingSnapshot>) => void) | undefined;

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildWorldbuildingSnapshot(DOC_ID))
      .mockImplementationOnce(() => new Promise((resolve) => {
        releaseB = resolve;
      }));

    const { rerender } = render(<BuildDocumentHarness documentId={DOC_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("build-surface-shell")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByTestId("scope-probe")).toHaveAttribute("data-document-id", DOC_ID);
    });

    rerender(<BuildDocumentHarness documentId={DOC_B} />);

    expect(await screen.findByTestId("build-surface-loading")).toBeInTheDocument();
    const probe = screen.getByTestId("scope-probe");
    expect(probe).toHaveAttribute("data-context-document-id", "null");
    expect(probe.getAttribute("data-ambient") ?? "").not.toContain(DOC_ID);

    releaseB?.(buildWorldbuildingSnapshot(DOC_B));
    await waitFor(() => {
      expect(screen.getByTestId("build-surface-shell")).toBeInTheDocument();
    });
  });

  it("publishes neutral Build authority ambient without UUIDs when navigation is rejected", async () => {
    const PLAN_DOC_ID = "22222222-2222-4222-8222-222222222222";
    const validSnapshot = buildWorldbuildingSnapshot(DOC_ID);
    const rejectedSnapshot = {
      schema_version: "dmb_workspace_document_snapshot_v1" as const,
      record: {
        schema_version: "dmb_workspace_document_record_v1" as const,
        document_id: PLAN_DOC_ID,
        title: "Session Prep",
        campaign_id: "eldyrwild",
        target_session: 4,
        kind: "plan" as const,
        target_relpath: "corpus/prep.md",
        status: "active" as const,
        content_status: "committed" as const,
        revision: 2,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: null,
        document_class: null,
        authority_state: null,
        visibility_state: null,
      },
      markdown: "# Prep\n",
      content_sha256: "sha-plan",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 2,
    };

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(validSnapshot);

    const { rerender } = render(<BuildDocumentHarness documentId={DOC_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("build-surface-shell")).toBeInTheDocument();
    });

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(rejectedSnapshot);
    rerender(<BuildDocumentHarness documentId={PLAN_DOC_ID} />);

    expect(await screen.findByTestId("build-surface-error")).toBeInTheDocument();
    await waitFor(() => {
      const probe = screen.getByTestId("scope-probe");
      expect(probe).toHaveAttribute("data-ambient", BUILD_AUTHORITY_REJECTION_AMBIENT);
      expect(probe).toHaveAttribute("data-envelope", "null");
      expect(probe).toHaveAttribute("data-context-document-id", "null");
      const serialized = `${probe.getAttribute("data-ambient")}${probe.getAttribute("data-context-document-id")}${probe.getAttribute("data-document-id")}`;
      expect(serialized).not.toContain(DOC_ID);
      expect(serialized).not.toContain(PLAN_DOC_ID);
    });
    expect(screen.getByTestId("build-authority-error")).toHaveTextContent(
      /wrong document kind|plan/i,
    );
  });

  it("persists the first real editor transaction to local storage and enables save", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(buildWorldbuildingSnapshot(DOC_ID));

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("build-markdown-editor")).toHaveAttribute(
        "data-markdown-editor-status",
        "ready",
      );
    });

    const saveButton = screen.getByTestId("build-save-button");
    expect(saveButton).toBeDisabled();

    await waitFor(() => expect(buildShellTestEditor).not.toBeNull());
    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      buildShellTestEditor?.commands.insertContent(" Build proof insert");
    });

    await waitFor(() => {
      expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
    });
    expect(saveButton).not.toBeDisabled();
    const stored = window.localStorage.getItem(workspaceDocumentStorageKey(DOC_ID));
    expect(stored).toContain("Build proof insert");
  });
});
