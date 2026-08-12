import type { ComponentProps } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/core";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import * as liveApi from "../api/liveApi";
import {
  buildInitialWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
  writeWorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import type { BuildSourceNavigationResponse } from "../api/types";
import { BuildCanvasTestProvider } from "./buildCanvasTestProvider";
import { BUILD_AUTHORITY_REJECTION_AMBIENT, BuildSurfaceShell } from "./BuildSurfaceShell";
import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";

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
    getBuildSourceNavigation: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
  };
});

const DOC_ID = "11111111-1111-4111-8111-111111111111";
const ARTIFACT_ID = "artifact-glass-hesta";
const SPAN_ID = "span-hesta-gate-passage";
const OTHER_DOC_ID = "22222222-2222-4222-8222-222222222222";

function buildExactSourceNavigationResult(
  overrides: Partial<BuildSourceNavigationResponse> = {},
): BuildSourceNavigationResponse {
  return {
    schema: "dmb_build_source_navigation_v1",
    status: "exact",
    sourceArtifactId: ARTIFACT_ID,
    sourceSpanRefId: SPAN_ID,
    documentId: DOC_ID,
    worldId: "the-glass-orchard",
    campaignId: "the-glass-orchard",
    artifactDocumentRevision: 2,
    currentDocumentRevision: 2,
    artifactContentSha256: "sha-build",
    currentContentSha256: "sha-build",
    startLine: 5,
    endLine: 5,
    canHighlight: true,
    message: "",
    diagnostics: [],
    ...overrides,
  };
}

function pushBuildSourceNavigationUrl(documentId = DOC_ID) {
  window.history.pushState(
    {},
    "",
    `/build?documentId=${documentId}&campaign=the-glass-orchard&sourceArtifactId=${ARTIFACT_ID}&sourceSpanRefId=${SPAN_ID}`,
  );
}

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

function AuthoringStatusProbe() {
  const session = useMarkdownCanvasSession();
  return (
    <>
      <span data-testid="build-document-status">{session.statusLabel}</span>
      <span data-testid="build-authoring-status" hidden>
        {session.statusLabel}
      </span>
      <span data-testid="build-canvas-title" hidden>
        {session.record?.title ?? ""}
      </span>
    </>
  );
}

function BuildDocumentHarness({ documentId }: { documentId: string }) {
  return (
    <AgentInteractionProvider>
      <ScopeProbe />
      <BuildCanvasTestProvider documentId={documentId}>
        <AuthoringStatusProbe />
        <BuildSurfaceShell />
      </BuildCanvasTestProvider>
    </AgentInteractionProvider>
  );
}

/** Non-empty clean sources default to Read; editor tests must switch explicitly. */
async function enterEditMode() {
  const user = (await import("@testing-library/user-event")).default.setup();
  await waitFor(() => {
    expect(screen.getByTestId("build-source-mode-edit")).toBeInTheDocument();
  });
  await user.click(screen.getByTestId("build-source-mode-edit"));
  await waitFor(() => {
    expect(screen.getByTestId("build-markdown-editor")).toBeInTheDocument();
  });
  return user;
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
        <BuildCanvasTestProvider documentId={DOC_ID}>
          <AuthoringStatusProbe />
          <BuildSurfaceShell />
        </BuildCanvasTestProvider>
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
        <BuildCanvasTestProvider documentId={DOC_ID}>
          <AuthoringStatusProbe />
          <BuildSurfaceShell />
        </BuildCanvasTestProvider>
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
        <BuildCanvasTestProvider documentId={DOC_ID}>
          <AuthoringStatusProbe />
          <BuildSurfaceShell />
        </BuildCanvasTestProvider>
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
        <BuildCanvasTestProvider documentId={PLAN_DOC_ID}>
          <AuthoringStatusProbe />
          <BuildSurfaceShell />
        </BuildCanvasTestProvider>
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
        <BuildCanvasTestProvider documentId={DOC_ID}>
          <AuthoringStatusProbe />
          <BuildSurfaceShell />
        </BuildCanvasTestProvider>
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
        <BuildCanvasTestProvider documentId={DOC_ID}>
          <AuthoringStatusProbe />
          <BuildSurfaceShell />
        </BuildCanvasTestProvider>
      </AgentInteractionProvider>,
    );

    expect(await screen.findByTestId("build-surface-conflict")).toBeInTheDocument();
    expect(screen.getByTestId("build-surface-conflict")).toHaveTextContent(
      /changed while a dirty local draft/i,
    );
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
        <BuildCanvasTestProvider documentId={DOC_ID}>
          <AuthoringStatusProbe />
          <BuildSurfaceShell />
        </BuildCanvasTestProvider>
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
    await enterEditMode();

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

  it("keeps a real TipTap insertion made while commit is pending", async () => {
    const snapshot = buildWorldbuildingSnapshot(DOC_ID);
    let releaseCommit: ((value: Awaited<ReturnType<typeof liveApi.commitTiptapMarkdownWrite>>) => void) | undefined;

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(snapshot)
      .mockResolvedValueOnce({
        ...snapshot,
        record: { ...snapshot.record, revision: 2, content_status: "committed" },
        markdown: "# Build Source\n",
        content_sha256: "sha-committed",
        file_fingerprint: "fp-committed",
        file_exists: true,
        loaded_revision: 2,
      });
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "Build Source",
      target_relpath: snapshot.record.target_relpath,
      target_display_path: snapshot.record.target_relpath,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+edited\n",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockImplementationOnce(() => new Promise((resolve) => {
      releaseCommit = resolve;
    }));

    render(<BuildDocumentHarness documentId={DOC_ID} />);
    await enterEditMode();

    await waitFor(() => {
      expect(screen.getByTestId("build-markdown-editor")).toHaveAttribute(
        "data-markdown-editor-status",
        "ready",
      );
    });
    await waitFor(() => expect(buildShellTestEditor).not.toBeNull());
    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      buildShellTestEditor?.commands.insertContent(" Before save");
    });
    await waitFor(() => {
      expect(screen.getByTestId("build-save-button")).not.toBeDisabled();
    });

    await act(async () => {
      screen.getByTestId("build-save-button").click();
    });
    await waitFor(() => {
      expect(screen.getByTestId("build-document-status")).toHaveTextContent(/Saving|Preparing/);
    });

    act(() => {
      buildShellTestEditor?.commands.insertContent(" late TipTap sentence");
    });
    await waitFor(() => {
      const storedMid = window.localStorage.getItem(workspaceDocumentStorageKey(DOC_ID));
      expect(storedMid).toContain("late TipTap sentence");
    });

    await act(async () => {
      releaseCommit?.({
        schema_version: "dmb_tiptap_markdown_write_commit_v1",
        document_id: DOC_ID,
        title: "Build Source",
        target_relpath: snapshot.record.target_relpath,
        target_display_path: snapshot.record.target_relpath,
        registry_revision: 2,
        committed_revision: 2,
        committed_record: {
          ...snapshot.record,
          revision: 2,
          content_status: "committed",
        },
        normalized_content_sha256: "sha-committed",
        writer_ok: true,
        bytes_written: 42,
        file_fingerprint: "fp-committed",
        diagnostics: [],
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
    });
    const stored = window.localStorage.getItem(workspaceDocumentStorageKey(DOC_ID));
    expect(stored).toContain("late TipTap sentence");
    expect(JSON.parse(stored!).dirty).toBe(true);
    expect(JSON.parse(stored!).base_revision).toBe(2);
    expect(screen.getByTestId("build-markdown-editor").textContent).toContain("late TipTap sentence");
  });

  it("publishes neutral Agent Interaction when a successful receipt lacks file_fingerprint", async () => {
    const snapshot = buildWorldbuildingSnapshot(DOC_ID);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot);
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "Build Source",
      target_relpath: snapshot.record.target_relpath,
      target_display_path: snapshot.record.target_relpath,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+edited\n",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_ID,
      title: "Build Source",
      target_relpath: snapshot.record.target_relpath,
      target_display_path: snapshot.record.target_relpath,
      registry_revision: 2,
      committed_revision: 2,
      committed_record: {
        ...snapshot.record,
        revision: 2,
        content_status: "committed",
      },
      normalized_content_sha256: "sha-committed-missing-fp",
      writer_ok: true,
      bytes_written: 42,
      file_fingerprint: null,
      diagnostics: [],
    });

    render(<BuildDocumentHarness documentId={DOC_ID} />);
    await enterEditMode();

    await waitFor(() => {
      expect(screen.getByTestId("build-markdown-editor")).toHaveAttribute(
        "data-markdown-editor-status",
        "ready",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("scope-probe")).toHaveAttribute("data-document-id", DOC_ID);
    });

    await waitFor(() => expect(buildShellTestEditor).not.toBeNull());
    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      buildShellTestEditor?.commands.insertContent(" Missing fingerprint edit");
    });
    await waitFor(() => {
      expect(screen.getByTestId("build-save-button")).not.toBeDisabled();
    });

    await act(async () => {
      screen.getByTestId("build-save-button").click();
    });

    expect(await screen.findByTestId("build-surface-conflict")).toBeInTheDocument();
    await waitFor(() => {
      const probe = screen.getByTestId("scope-probe");
      expect(probe).toHaveAttribute("data-context-document-id", "null");
      expect(probe).toHaveAttribute("data-document-id", "null");
      expect(probe).toHaveAttribute("data-envelope", "null");
      expect(probe).toHaveAttribute("data-ambient", "Document reconciliation required");
      const serialized = [
        probe.getAttribute("data-ambient"),
        probe.getAttribute("data-context-document-id"),
        probe.getAttribute("data-document-id"),
        probe.getAttribute("data-envelope"),
      ].join("|");
      expect(serialized).not.toContain(DOC_ID);
      expect(serialized).not.toContain(snapshot.record.target_relpath);
      expect(serialized).not.toContain("sha-build");
      expect(serialized).not.toContain("sha-committed-missing-fp");
    });

    const storedRaw = window.localStorage.getItem(workspaceDocumentStorageKey(DOC_ID));
    expect(storedRaw).toBeTruthy();
    expect(JSON.parse(storedRaw!).base_revision).toBe(2);
  });

  it("PR380B: mounts graph-object context lane when document and pointer are present", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(buildWorldbuildingSnapshot(DOC_ID));
    window.history.pushState(
      {},
      "",
      `/build?documentId=${DOC_ID}&campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=wg-rev-test`,
    );
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "wg-rev-test",
        headRevisionId: "wg-rev-test",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        scopeMode: "campaign",
      },
      summary: {
        nodeCount: 1,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [
        {
          nodeId: "pc_caelynn",
          label: "Caelynn",
          kind: "pc",
          role: "pc",
          aliases: [],
          sourceDomains: [],
          evidenceBadges: [],
          adjacency: [],
          suggestedExpansions: [],
          anchoredToFocusSession: true,
          summary: "Test",
          campaignScope: "longmont-c2",
          evidenceRefIds: [],
          sourceArtifactIds: [],
        },
      ],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });
    render(<BuildDocumentHarness documentId={DOC_ID} />);
    await waitFor(() => {
      expect(screen.getByTestId("build-surface-shell")).toBeInTheDocument();
    });
    expect(await screen.findByTestId("build-graph-object-context")).toBeInTheDocument();
  });

  it("PR380B: does not load graph context while the workspace document is still loading", async () => {
    let releaseSnapshot: ((snapshot: ReturnType<typeof buildWorldbuildingSnapshot>) => void) | undefined;
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(
      () =>
        new Promise((resolve) => {
          releaseSnapshot = resolve;
        }),
    );
    window.history.pushState(
      {},
      "",
      `/build?documentId=${DOC_ID}&campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=wg-rev-test`,
    );
    const postProjection = vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "wg-rev-test",
        headRevisionId: "wg-rev-test",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        scopeMode: "campaign",
      },
      summary: {
        nodeCount: 0,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    expect(await screen.findByTestId("build-surface-loading")).toBeInTheDocument();
    expect(screen.queryByTestId("build-graph-object-context")).not.toBeInTheDocument();
    expect(postProjection).not.toHaveBeenCalled();

    releaseSnapshot?.(buildWorldbuildingSnapshot(DOC_ID));
    await waitFor(() => {
      expect(screen.getByTestId("build-surface-shell")).toBeInTheDocument();
    });
    expect(await screen.findByTestId("build-graph-object-context")).toBeInTheDocument();
  });

  it("defaults clean non-empty sources to Read with exact snapshot Markdown", async () => {
    const snapshot = {
      ...buildWorldbuildingSnapshot(DOC_ID),
      markdown: [
        "# Gate Notes",
        "",
        "See [Hesta](https://example.com/hesta).",
        "",
        "| Role | Name |",
        "| --- | --- |",
        "| Gate | Hesta |",
        "",
        "<section>raw</section>",
        "",
      ].join("\n"),
    };
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot);

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    expect(await screen.findByTestId("build-source-reader")).toBeInTheDocument();
    expect(screen.getByTestId("build-source-mode-read")).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByTestId("build-markdown-editor")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Hesta" })).toHaveAttribute("href", "https://example.com/hesta");
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByTestId("markdown-reader-html-literal")).toHaveTextContent("<section>raw</section>");
    expect(liveApi.prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(liveApi.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });

  it("sealed lossy Read → Edit keeps Save guard and Read still shows exact source", async () => {
    const sealedLossyMarkdown = [
      "# Hesta's Apothecary",
      "",
      "| Item | Note |",
      "| --- | --- |",
      "| Tonic | Rare |",
      "",
      "![Floor plan](assets/hesta-floor.png)",
      "",
      "---",
      "",
      "<div class=\"gm-note\">Hidden shelf</div>",
      "",
    ].join("\n");
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      ...buildWorldbuildingSnapshot(DOC_ID),
      record: {
        ...buildWorldbuildingSnapshot(DOC_ID).record,
        content_status: "committed",
        target_relpath:
          `corpus/eldyrwild-markdown/_dungeonbuddy/sources/${DOC_ID}/source.md`,
      },
      markdown: sealedLossyMarkdown,
      file_fingerprint: "fp-sealed",
      file_exists: true,
    });

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    expect(await screen.findByTestId("build-source-reader")).toBeInTheDocument();
    expect(screen.getByTestId("build-source-mode-read")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { level: 1, name: "Hesta's Apothecary" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Tonic" })).toBeInTheDocument();
    expect(screen.getAllByTestId("markdown-reader-unresolved-media").some((el) =>
      el.textContent?.includes("assets/hesta-floor.png"),
    )).toBe(true);
    expect(screen.getByTestId("markdown-reader-html-literal")).toHaveTextContent(
      '<div class="gm-note">Hidden shelf</div>',
    );

    const user = await enterEditMode();
    expect(screen.getByTestId("build-reimport-authoritative-button")).toBeInTheDocument();
    const saveButton = screen.getByTestId("build-save-button");
    expect(saveButton).toBeDisabled();

    if (!saveButton.hasAttribute("disabled")) {
      await user.click(saveButton);
    }
    expect(liveApi.prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(liveApi.commitTiptapMarkdownWrite).not.toHaveBeenCalled();

    await user.click(screen.getByTestId("build-source-mode-read"));
    expect(await screen.findByTestId("build-source-reader")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByTestId("markdown-reader-html-literal")).toHaveTextContent(
      '<div class="gm-note">Hidden shelf</div>',
    );
    expect(liveApi.prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(liveApi.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });

  it("defaults blank sources to Edit", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      ...buildWorldbuildingSnapshot(DOC_ID),
      markdown: "   \n",
    });

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(screen.getByTestId("build-source-mode-edit")).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByTestId("build-source-reader")).not.toBeInTheDocument();
  });

  it("defaults recovered dirty sources to Edit", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(buildWorldbuildingSnapshot(DOC_ID));
    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "Build Source",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 1,
      baseContentSha256: "sha-build",
      starterContent: { type: "doc", content: [] },
    });
    local.dirty = true;
    local.exported_markdown = "# Dirty local\n";
    writeWorkspaceDocumentLocalState(window.localStorage, local);

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(screen.getByTestId("build-source-mode-edit")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
  });

  it("switches Read ↔ Edit without write APIs and shows dirty warning in Read", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(buildWorldbuildingSnapshot(DOC_ID));

    render(<BuildDocumentHarness documentId={DOC_ID} />);
    expect(await screen.findByTestId("build-source-reader")).toBeInTheDocument();

    const user = await enterEditMode();
    await waitFor(() => expect(buildShellTestEditor).not.toBeNull());
    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      buildShellTestEditor?.commands.insertContent(" unsaved delta");
    });
    await waitFor(() => {
      expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
    });

    await user.click(screen.getByTestId("build-source-mode-read"));
    expect(await screen.findByTestId("build-source-reader")).toBeInTheDocument();
    expect(screen.getByTestId("build-source-reader-dirty-warning")).toHaveTextContent(/last saved source/i);
    expect(screen.getByTestId("build-source-reader")).toHaveTextContent("Build Source");
    expect(screen.queryByText("unsaved delta")).not.toBeInTheDocument();
    expect(liveApi.prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(liveApi.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });

  it("does not mount the rich reader for load errors or conflicts", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Session Prep",
        campaign_id: "eldyrwild",
        target_session: 4,
        kind: "plan",
        target_relpath: "corpus/prep.md",
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
      markdown: "# Prep with [link](https://example.com)\n",
      content_sha256: "sha-plan",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 2,
    });

    render(<BuildDocumentHarness documentId={DOC_ID} />);
    expect(await screen.findByTestId("build-surface-error")).toBeInTheDocument();
    expect(screen.queryByTestId("build-source-reader")).not.toBeInTheDocument();
    expect(screen.queryByTestId("build-source-mode-toggle")).not.toBeInTheDocument();
  });

  it("re-resolves A/S on arrival and highlights an exact source span in Read", async () => {
    const markdown = [
      "---",
      "title: Gate Notes",
      "---",
      "",
      "# Gate Notes",
      "",
      "Hesta watches the orchard gate at dusk.",
      "",
    ].join("\n");
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      ...buildWorldbuildingSnapshot(DOC_ID),
      markdown,
      content_sha256: "sha-build",
    });
    vi.mocked(liveApi.getBuildSourceNavigation).mockResolvedValue(
      buildExactSourceNavigationResult({ startLine: 7, endLine: 7 }),
    );
    pushBuildSourceNavigationUrl();

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    expect(await screen.findByTestId("build-source-reader")).toBeInTheDocument();
    await waitFor(() => {
      expect(liveApi.getBuildSourceNavigation).toHaveBeenCalledWith({
        sourceArtifactId: ARTIFACT_ID,
        sourceSpanRefId: SPAN_ID,
      });
    });
    await waitFor(() => {
      expect(screen.getByText("Hesta watches the orchard gate at dusk.").closest("[data-source-block='true']"))
        .not.toBeNull();
    });
    expect(screen.queryByTestId("build-source-reader-navigation-status")).not.toBeInTheDocument();
  });

  it("shows stale navigation truthfully without applying a highlight", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(buildWorldbuildingSnapshot(DOC_ID));
    vi.mocked(liveApi.getBuildSourceNavigation).mockResolvedValue(
      buildExactSourceNavigationResult({
        status: "stale",
        canHighlight: false,
        currentContentSha256: "sha-new",
        message: "Source drift detected.",
      }),
    );
    pushBuildSourceNavigationUrl();

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    expect(await screen.findByTestId("build-source-reader")).toBeInTheDocument();
    const status = await screen.findByTestId("build-source-reader-navigation-status");
    expect(status).toHaveAttribute("data-navigation-status", "stale");
    expect(status).toHaveTextContent(/source drift detected/i);
    expect(document.querySelector("[data-source-block='true']")).toBeNull();
  });

  it("blocks highlight when the resolved document differs from the active Build document", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(buildWorldbuildingSnapshot(DOC_ID));
    vi.mocked(liveApi.getBuildSourceNavigation).mockResolvedValue(
      buildExactSourceNavigationResult({
        documentId: OTHER_DOC_ID,
        message: "Evidence belongs elsewhere.",
      }),
    );
    pushBuildSourceNavigationUrl(DOC_ID);

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    expect(await screen.findByTestId("build-source-reader")).toBeInTheDocument();
    const status = await screen.findByTestId("build-source-reader-navigation-status");
    expect(status).toHaveAttribute("data-navigation-status", "document_mismatch");
    expect(status).toHaveTextContent(/evidence belongs elsewhere/i);
    expect(document.querySelector("[data-source-block='true']")).toBeNull();
  });

  it("preserves a dirty draft when arriving from graph source navigation", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(buildWorldbuildingSnapshot(DOC_ID));
    vi.mocked(liveApi.getBuildSourceNavigation).mockResolvedValue(buildExactSourceNavigationResult());
    pushBuildSourceNavigationUrl();

    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "Build Source",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 1,
      baseContentSha256: "sha-build",
      starterContent: { type: "doc", content: [] },
    });
    local.dirty = true;
    local.exported_markdown = "# Dirty local\n";
    writeWorkspaceDocumentLocalState(window.localStorage, local);

    render(<BuildDocumentHarness documentId={DOC_ID} />);

    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(screen.getByTestId("build-source-mode-edit")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
    expect(liveApi.prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(liveApi.commitTiptapMarkdownWrite).not.toHaveBeenCalled();

    const user = (await import("@testing-library/user-event")).default.setup();
    await user.click(screen.getByTestId("build-source-mode-read"));
    expect(await screen.findByTestId("build-source-reader-navigation-dirty-notice")).toHaveTextContent(
      /last saved source/i,
    );
    await waitFor(() => {
      expect(liveApi.getBuildSourceNavigation).toHaveBeenCalled();
    });
  });

  it("re-resolves A/S again on hard reload composition", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(buildWorldbuildingSnapshot(DOC_ID));
    vi.mocked(liveApi.getBuildSourceNavigation).mockResolvedValue(buildExactSourceNavigationResult());
    pushBuildSourceNavigationUrl();

    const { unmount } = render(<BuildDocumentHarness documentId={DOC_ID} />);
    await waitFor(() => {
      expect(liveApi.getBuildSourceNavigation).toHaveBeenCalledTimes(1);
    });
    unmount();

    render(<BuildDocumentHarness documentId={DOC_ID} />);
    await waitFor(() => {
      expect(liveApi.getBuildSourceNavigation).toHaveBeenCalledTimes(2);
    });
  });
});
