import { StrictMode } from "react";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import { referenceFromGraphNode } from "../graphReference/referenceFromGraphNode";
import { MarkdownCanvasSessionProvider, useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { LegacyProjectionHostAdapter } from "../planSurface/projection/LegacyProjectionHostAdapter";
import { ToolHost } from "../surfaceInteraction/toolHost/ToolHost";
import {
  buildInitialWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
} from "../tiptap/state/tiptapLocalState";
import { BUILD_MARKDOWN_CANVAS } from "./buildMarkdownCanvasAdapter";
import { BUILD_DOCUMENT_SAVE_COMMAND_ID, BUILD_SAVE_CONFLICTS_WITH } from "./buildDocumentCommands";
import { writeBuildLastCampaignId } from "./buildBareEntryCampaign";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import {
  BuildSurfacePage,
  resetBuildBareEntryAutoCreateForTests,
} from "./BuildSurfacePage";
import { BuildSurfaceShell } from "./BuildSurfaceShell";
import type { BuildReferenceContextBinding } from "./reference/buildBuildSurfaceInteractionPublication";
import { BUILD_REFERENCE_CONTEXT_BINDING_ID } from "./reference/buildReferenceIds";
import { BuildReferenceCapability } from "./reference/BuildReferenceCapability";

function renderBuildPage() {
  return render(
    <AgentInteractionProvider>
      <BuildSurfacePage />
      <ToolHost />
      <LegacyProjectionHostAdapter />
    </AgentInteractionProvider>,
  );
}

function mockUntitledDraftCreate(documentId = DOC_ID, campaignId = "longmont-c2") {
  vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue({
    schema_version: "dmb_workspace_document_record_v1",
    document_id: documentId,
    title: "Untitled worldbuilding source",
    campaign_id: campaignId,
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
  vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
    schema_version: "dmb_workspace_document_snapshot_v1",
    record: {
      schema_version: "dmb_workspace_document_record_v1",
      document_id: documentId,
      title: "Untitled worldbuilding source",
      campaign_id: campaignId,
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
}

function BuildPublicationProbe() {
  const { surfaceInteractionPublication } = useAgentInteraction();
  const hasTools = (surfaceInteractionPublication?.tools.length ?? 0) > 0;
  return (
    <p data-testid="build-projection-enabled">
      {hasTools ? "enabled" : "inactive"}
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
    postWorldGraphProjection: vi.fn(),
  };
});

const DOC_ID = "11111111-1111-4111-8111-111111111111";
const DOC_B = "22222222-2222-4222-8222-222222222222";

function buildLongmontSnapshot(documentId: string, title: string, markdown = "# Build Source\n") {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1" as const,
    record: {
      schema_version: "dmb_workspace_document_record_v1" as const,
      document_id: documentId,
      title,
      campaign_id: "longmont-c1",
      target_session: null,
      kind: "worldbuilding_source" as const,
      target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
      status: "active" as const,
      content_status: "committed" as const,
      revision: 2,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding" as const,
      document_class: "faction" as const,
      authority_state: "draft" as const,
      visibility_state: "internal" as const,
    },
    markdown,
    content_sha256: `sha-${documentId}`,
    file_fingerprint: "present" as const,
    file_exists: true,
    loaded_revision: 2,
  };
}

function graphProjectionWithGlowkindle() {
  return {
    schema: "dmb_world_graph_projection_v1" as const,
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      revisionId: "rev-1",
      headRevisionId: "rev-1",
      isHead: true,
      focus: { kind: "none" as const, sessionId: null },
      admissibility: "gm" as const,
      scopeMode: "campaign" as const,
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
        nodeId: "npc-glowkindle",
        label: "Glowkindle",
        kind: "npc",
        role: "merchant",
        aliases: ["Glow"],
        sourceDomains: ["recap"],
        evidenceBadges: [],
        adjacency: [],
        suggestedExpansions: [],
        evidenceRefIds: [],
        sourceArtifactIds: [],
        anchoredToFocusSession: true,
        summary: "A friendly merchant.",
      },
    ],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
  };
}

describe("BuildSurfacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    resetBuildBareEntryAutoCreateForTests();
    window.history.pushState({}, "", "/build");
  });

  it("E2: bare /build without campaign shows picker and does not create", async () => {
    mockUntitledDraftCreate();
    renderBuildPage();

    expect(await screen.findByTestId("build-campaign-pick")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(screen.queryByTestId("build-markdown-editor")).not.toBeInTheDocument();
  });

  it("E2: bare /build auto-creates one untitled draft and admits the Canvas", async () => {
    mockUntitledDraftCreate();
    window.history.pushState({}, "", "/build?campaign=longmont-c2");

    render(
      <AgentInteractionProvider>
        <BuildSurfacePage />
        <ToolHost />
        <LegacyProjectionHostAdapter />
        <BuildPublicationProbe />
      </AgentInteractionProvider>,
    );

    expect(screen.getByTestId("build-opening-draft")).toBeInTheDocument();
    expect(screen.getByTestId("build-projection-enabled")).toHaveTextContent("inactive");

    await waitFor(() => {
      expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith({
      title: "Untitled worldbuilding source",
      campaign_id: "longmont-c2",
      kind: "worldbuilding_source",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    });

    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Untitled worldbuilding source" })).toBeInTheDocument();
    expect(screen.queryByTestId("build-opening-draft")).not.toBeInTheDocument();
    expect(screen.queryByTestId("build-new-source-form")).not.toBeInTheDocument();
    expect(new URL(window.location.href).searchParams.get("documentId")).toBe(DOC_ID);
    expect(new URL(window.location.href).searchParams.get("campaign")).toBe("longmont-c2");
  });

  it("E2 StrictMode: bare /build creates at most one document", async () => {
    mockUntitledDraftCreate();
    window.history.pushState({}, "", "/build?campaign=longmont-c2");

    render(
      <StrictMode>
        <AgentInteractionProvider>
          <BuildSurfacePage />
          <ToolHost />
          <LegacyProjectionHostAdapter />
        </AgentInteractionProvider>
      </StrictMode>,
    );

    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("E2: browser Back after admit does not create another document", async () => {
    mockUntitledDraftCreate();
    const pushSpy = vi.spyOn(window.history, "pushState");
    const replaceSpy = vi.spyOn(window.history, "replaceState");

    // Simulate Command Board → Build entry, then campaign-resolved auto-create.
    window.history.replaceState({}, "", "/");
    pushSpy.mockClear();
    replaceSpy.mockClear();
    window.history.pushState({}, "", "/build?campaign=longmont-c2");

    const view = renderBuildPage();

    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(new URL(window.location.href).searchParams.get("documentId")).toBe(DOC_ID);

    const admissionReplaces = replaceSpy.mock.calls.filter((call) =>
      String(call[2] ?? "").includes("documentId="),
    );
    expect(admissionReplaces.length).toBeGreaterThanOrEqual(1);
    const admissionPushes = pushSpy.mock.calls.filter((call) =>
      String(call[2] ?? "").includes("documentId="),
    );
    expect(admissionPushes).toHaveLength(0);

    await act(async () => {
      const popped = new Promise<void>((resolve) => {
        window.addEventListener("popstate", () => resolve(), { once: true });
      });
      window.history.back();
      await popped;
    });

    // Transient campaign/document URLs were replaced, so Back leaves Build.
    expect(window.location.pathname.replace(/\/+$/, "") || "/").toBe("/");
    expect(new URL(window.location.href).searchParams.get("documentId")).toBeNull();

    // App chrome would unmount Build off-route; mirror that so last-campaign
    // memory cannot replay create while a stale page instance remains mounted.
    view.unmount();
    resetBuildBareEntryAutoCreateForTests();

    await act(async () => {
      await Promise.resolve();
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("E2: unknown route campaign fails closed to picker without create", async () => {
    mockUntitledDraftCreate();
    window.history.pushState({}, "", "/build?campaign=eldyrwild");

    renderBuildPage();

    expect(await screen.findByTestId("build-campaign-pick")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(screen.queryByTestId("build-markdown-editor")).not.toBeInTheDocument();
  });

  it("E2: blank route campaign without memory shows picker", async () => {
    mockUntitledDraftCreate();
    window.history.pushState({}, "", "/build?campaign=");

    renderBuildPage();

    expect(await screen.findByTestId("build-campaign-pick")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("E2: blank route campaign with remembered campaign still fails closed to picker", async () => {
    mockUntitledDraftCreate();
    writeBuildLastCampaignId("longmont-c2");
    window.history.pushState({}, "", "/build?campaign=");

    renderBuildPage();

    expect(await screen.findByTestId("build-campaign-pick")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(screen.queryByTestId("build-markdown-editor")).not.toBeInTheDocument();
  });

  it("E2: bare /build create failure shows retry without navigating", async () => {
    const user = userEvent.setup();
    mockUntitledDraftCreate();
    vi.mocked(liveApi.createWorkspaceDocument).mockRejectedValueOnce(new Error("create failed"));
    window.history.pushState({}, "", "/build?campaign=longmont-c2");

    renderBuildPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("create failed");
    expect(screen.getByTestId("build-opening-draft")).toBeInTheDocument();
    expect(new URL(window.location.href).searchParams.get("documentId")).toBeNull();

    await user.click(screen.getByTestId("build-opening-retry"));
    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(2);
  });

  it("E2: delayed create for campaign A is ignored after route switches to campaign B", async () => {
    const docA = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    const docB = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
    let resolveA: ((value: Awaited<ReturnType<typeof liveApi.createWorkspaceDocument>>) => void) | null = null;
    const deferredA = new Promise<Awaited<ReturnType<typeof liveApi.createWorkspaceDocument>>>((resolve) => {
      resolveA = resolve;
    });

    vi.mocked(liveApi.createWorkspaceDocument).mockImplementation(async (payload) => {
      const record = {
        schema_version: "dmb_workspace_document_record_v1" as const,
        document_id: payload.campaign_id === "longmont-c1" ? docA : docB,
        title: "Untitled worldbuilding source",
        campaign_id: payload.campaign_id,
        target_session: null,
        kind: "worldbuilding_source" as const,
        target_relpath: `out/workspace/worldbuilding/${payload.campaign_id === "longmont-c1" ? docA : docB}.md`,
        status: "active" as const,
        content_status: "draft" as const,
        revision: 1,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding" as const,
        document_class: "lore",
        authority_state: "draft" as const,
        visibility_state: "internal" as const,
      };
      if (payload.campaign_id === "longmont-c1") {
        return deferredA;
      }
      return record;
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id: string) => ({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: id,
        title: "Untitled worldbuilding source",
        campaign_id: id === docA ? "longmont-c1" : "longmont-c2",
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
      markdown: "",
      content_sha256: `sha-${id}`,
      file_fingerprint: "absent",
      file_exists: false,
      loaded_revision: 1,
    }));

    window.history.pushState({}, "", "/build?campaign=longmont-c1");
    renderBuildPage();

    await waitFor(() => {
      expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
        expect.objectContaining({ campaign_id: "longmont-c1" }),
      );
    });

    await act(async () => {
      window.history.pushState({}, "", "/build?campaign=longmont-c2");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    await waitFor(() => {
      expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
        expect.objectContaining({ campaign_id: "longmont-c2" }),
      );
    });

    await act(async () => {
      resolveA?.({
        schema_version: "dmb_workspace_document_record_v1",
        document_id: docA,
        title: "Untitled worldbuilding source",
        campaign_id: "longmont-c1",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${docA}.md`,
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
    });

    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(new URL(window.location.href).searchParams.get("documentId")).toBe(docB);
    expect(new URL(window.location.href).searchParams.get("campaign")).toBe("longmont-c2");
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

    const draftId = "33333333-3333-4333-8333-333333333333";
    mockUntitledDraftCreate(draftId);
    await act(async () => {
      window.history.pushState({}, "", "/build?campaign=longmont-c2");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Untitled worldbuilding source" })).toBeInTheDocument();
    expect(new URL(window.location.href).searchParams.get("documentId")).toBe(draftId);
  });

  it("PR380B: preserves graph pointer campaign when auto-creating from bare /build", async () => {
    window.history.pushState(
      {},
      "",
      `/build?campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=${session23WorldGraphRecapFixture.snapshot.revisionId}`,
    );
    mockUntitledDraftCreate(DOC_ID, "longmont-c2");
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
    expect(await screen.findByTestId("build-markdown-editor")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
      expect.objectContaining({ campaign_id: "longmont-c2" }),
    );
    expect(await screen.findByTestId("build-graph-object-context")).toBeInTheDocument();
  });

  it("E5: BuildSurfacePage → ToolHost → Find existing → View → content renderer", async () => {
    const user = userEvent.setup();
    const glowkindle = {
      nodeId: "npc-glowkindle",
      label: "Glowkindle",
      kind: "npc",
      role: "merchant",
      aliases: ["Glow"],
      sourceDomains: ["recap"],
      evidenceBadges: [],
      adjacency: [],
      suggestedExpansions: [],
      evidenceRefIds: [],
      sourceArtifactIds: [],
      anchoredToFocusSession: true,
      summary: "A friendly merchant.",
    };
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Faction Notes",
        campaign_id: "longmont-c1",
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
      markdown: "# Faction Notes\n",
      content_sha256: "sha-faction",
      file_fingerprint: "absent",
      file_exists: false,
      loaded_revision: 1,
    });
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c1",
        revisionId: "rev-1",
        headRevisionId: "rev-1",
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
      nodes: [glowkindle],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    renderBuildPage();

    await waitFor(() => {
      expect(screen.getByTestId("surface-tool-host")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: /Find existing object/ }));

    await waitFor(() => {
      expect(screen.getByTestId("build-reference-search-projection")).toBeInTheDocument();
    });
    const host = document.querySelector(".surface-projection-host");
    expect(host).toBeTruthy();
    expect(
      within(host as HTMLElement).getByRole("button", { name: "Find existing object" }),
    ).toHaveAttribute("aria-pressed", "true");

    await user.type(screen.getByLabelText("Find objects"), "glow");
    await user.click(screen.getByRole("button", { name: "View" }));

    await waitFor(() => {
      expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    });
    expect(
      within(screen.getByTestId("graph-object-projection-card")).getByText("Glowkindle"),
    ).toBeInTheDocument();
  });

  it("E11: View/Expand/relationship/close/lens leave document authority unchanged", async () => {
    const user = userEvent.setup();
    const markdownBody = "# Faction Notes\n\nKeep this body intact.\n";
    const editorJson = {
      type: "doc",
      content: [
        {
          type: "heading",
          attrs: { level: 1 },
          content: [{ type: "text", text: "Dirty faction draft" }],
        },
      ],
    };
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
        content_status: "committed",
        revision: 2,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "faction",
        authority_state: "draft",
        visibility_state: "internal",
      },
      markdown: markdownBody,
      content_sha256: "sha-faction-e11",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 2,
    });
    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "Faction Notes",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-faction-e11",
      starterContent: editorJson,
    });
    local.dirty = true;
    local.exported_markdown = "# Dirty faction draft\n";
    local.tiptap_json = editorJson;
    window.localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), JSON.stringify(local));

    const glowNodeView = {
      node_id: "npc-glowkindle",
      label: "Glowkindle",
      kind: "npc",
      role: "merchant",
      aliases: ["Glow"],
      source_domains: ["recap"],
      evidence_badges: [],
      adjacency: [
        {
          edge_id: "edge-inn",
          node_id: "location-inn",
          label: "The Inn",
          kind: "location",
          predicate: "located_in",
          direction: "outgoing" as const,
          anchored_to_focus_session: true,
          source_domains: ["recap"],
          evidence_ref_ids: [],
          campaign_scope: "longmont-c1",
        },
      ],
      anchored_to_focus_session: true,
      summary: "A friendly merchant.",
    };

    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c1",
        revisionId: "rev-1",
        headRevisionId: "rev-1",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        scopeMode: "campaign",
      },
      summary: {
        nodeCount: 2,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [
        {
          nodeId: "npc-glowkindle",
          label: "Glowkindle",
          kind: "npc",
          role: "merchant",
          aliases: ["Glow"],
          sourceDomains: ["recap"],
          evidenceBadges: [],
          adjacency: [
            {
              edgeId: "edge-inn",
              nodeId: "location-inn",
              label: "The Inn",
              kind: "location",
              predicate: "located_in",
              direction: "outgoing",
              anchoredToFocusSession: true,
              sourceDomains: ["recap"],
              evidenceRefIds: [],
              sessionIds: [],
              campaignScope: "longmont-c1",
            },
          ],
          suggestedExpansions: [],
          evidenceRefIds: [],
          sourceArtifactIds: [],
          anchoredToFocusSession: true,
          summary: "A friendly merchant.",
        },
        {
          nodeId: "location-inn",
          label: "The Inn",
          kind: "location",
          role: "location",
          aliases: [],
          sourceDomains: ["recap"],
          evidenceBadges: [],
          adjacency: [],
          suggestedExpansions: [],
          evidenceRefIds: [],
          sourceArtifactIds: [],
          anchoredToFocusSession: true,
          summary: "Meeting place.",
        },
      ],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });

    let latestContext: BuildReferenceContextBinding | null = null;
    let openGraphReference: ReturnType<typeof useAgentInteraction>["openGraphReference"] | null = null;
    let closeProjection: (() => void) | null = null;

    function AuthorityProbe() {
      const session = useMarkdownCanvasSession();
      return (
        <pre data-testid="authority-probe">
          {JSON.stringify({
            documentId: session.documentId,
            dirty: session.dirty,
            phase: session.phase,
            statusLabel: session.statusLabel,
            editorContent: session.editorContent,
            lastCommitReceipt: session.lastCommitReceipt,
            activeCommand: session.activeCommand,
            saveDisabled: session.saveDisabled,
          })}
        </pre>
      );
    }

    function InteractionProbe() {
      const interaction = useAgentInteraction();
      openGraphReference = interaction.openGraphReference;
      closeProjection = interaction.close;
      const binding = interaction.surfaceInteractionPublication?.projectionBindings.find(
        (entry) => entry.id === BUILD_REFERENCE_CONTEXT_BINDING_ID,
      );
      latestContext = (binding?.value as BuildReferenceContextBinding | undefined) ?? null;
      return null;
    }

    function readAuthoritySnapshot() {
      const probe = JSON.parse(screen.getByTestId("authority-probe").textContent || "{}") as {
        documentId: string;
        dirty: boolean;
        phase: string;
        statusLabel: string;
        editorContent: unknown;
        lastCommitReceipt: unknown;
        activeCommand: unknown;
        saveDisabled: boolean;
      };
      const storedRaw = window.localStorage.getItem(workspaceDocumentStorageKey(DOC_ID));
      expect(storedRaw).toBeTruthy();
      const stored = JSON.parse(storedRaw!) as {
        dirty: boolean;
        exported_markdown: string;
        base_revision: number;
        base_content_sha256: string;
        tiptap_json: unknown;
      };
      const saveButton = screen.queryByRole("button", { name: /^Save$/i });
      return {
        documentId: probe.documentId,
        dirty: probe.dirty,
        phase: probe.phase,
        statusLabel: probe.statusLabel,
        editorContent: probe.editorContent,
        lastCommitReceipt: probe.lastCommitReceipt,
        activeCommand: probe.activeCommand,
        saveDisabled: probe.saveDisabled,
        exportedMarkdown: stored.exported_markdown,
        baseRevision: stored.base_revision,
        baseDigest: stored.base_content_sha256,
        tiptapJson: stored.tiptap_json,
        prepareCalls: vi.mocked(liveApi.prepareTiptapMarkdownWrite).mock.calls.length,
        commitCalls: vi.mocked(liveApi.commitTiptapMarkdownWrite).mock.calls.length,
        saveControlDisabled: saveButton ? (saveButton as HTMLButtonElement).disabled : null,
        saveLabel: saveButton?.textContent ?? null,
      };
    }

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_ID}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_ID} />
          <BuildIngestToolbar documentId={DOC_ID} />
          <BuildSurfaceShell />
          <AuthorityProbe />
          <InteractionProbe />
        </MarkdownCanvasSessionProvider>
        <ToolHost />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
    });
    const before = readAuthoritySnapshot();
    expect(before.documentId).toBe(DOC_ID);
    expect(before.dirty).toBe(true);
    expect(before.baseRevision).toBe(2);
    expect(before.baseDigest).toBe("sha-faction-e11");
    expect(before.lastCommitReceipt).toBeNull();
    expect(before.activeCommand).toBeNull();
    expect(before.prepareCalls).toBe(0);
    expect(before.commitCalls).toBe(0);
    expect(before.editorContent).toEqual(editorJson);

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: /Find existing object/ }));
    await waitFor(() => {
      expect(screen.getByTestId("build-reference-search-projection")).toBeInTheDocument();
    });
    await user.type(screen.getByLabelText("Find objects"), "glow");
    await user.click(screen.getByRole("button", { name: "View" }));
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Close toolbox" }));
    await waitFor(() => {
      expect(screen.queryByTestId("graph-object-projection-card")).not.toBeInTheDocument();
    });

    expect(openGraphReference).not.toBeNull();
    act(() => {
      openGraphReference!({
        resolution: {
          kind: "resolved_graph",
          locator: "dmb-node:npc-glowkindle",
          reference: referenceFromGraphNode(glowNodeView),
          graphNodeId: "npc-glowkindle",
          graphObject: buildGraphObjectCardFromNodeView(glowNodeView),
          graphScope: {
            worldId: "eldyrwild",
            campaignId: "longmont-c1",
            scopeMode: "campaign",
            revisionId: "rev-1",
          },
          projectionState: "ready",
          message: "Resolved graph node Glowkindle.",
        },
        glanceOnly: true,
      });
    });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Expand" })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Expand" }));
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Expand" })).not.toBeInTheDocument();
      expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Open related object .*The Inn/i }));
    await waitFor(() => {
      expect(
        within(screen.getByTestId("graph-object-projection-card")).getByText("The Inn"),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Close toolbox" }));
    await waitFor(() => {
      expect(screen.queryByTestId("graph-object-projection-card")).not.toBeInTheDocument();
    });

    await waitFor(() => expect(latestContext).not.toBeNull());
    act(() => {
      latestContext!.selectCampaign("longmont-c2");
    });
    await waitFor(() => {
      expect(new URLSearchParams(window.location.search).get("campaign")).toBe("longmont-c2");
    });
    act(() => {
      latestContext!.selectCampaign("longmont-c1");
    });
    await waitFor(() => {
      expect(new URLSearchParams(window.location.search).get("campaign")).toBe("longmont-c1");
    });

    expect(closeProjection).not.toBeNull();
    const after = readAuthoritySnapshot();
    expect(after).toEqual(before);
  });

  it("E3: shared Edit Save commits dirty document via prepare/commit", async () => {
    const user = userEvent.setup();
    const dirtyMarkdown = "# Dirty faction draft\n";
    const editorJson = {
      type: "doc",
      content: [
        {
          type: "heading",
          attrs: { level: 1 },
          content: [{ type: "text", text: "Dirty faction draft" }],
        },
      ],
    };
    const snapshot = buildLongmontSnapshot(DOC_ID, "Faction Notes", "# Faction Notes\n\nKeep this body intact.\n");

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot);
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionWithGlowkindle());

    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "Faction Notes",
      campaignId: "longmont-c1",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: snapshot.content_sha256,
      starterContent: editorJson,
    });
    local.dirty = true;
    local.exported_markdown = dirtyMarkdown;
    local.tiptap_json = editorJson;
    window.localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), JSON.stringify(local));

    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "Faction Notes",
      target_relpath: snapshot.record.target_relpath,
      target_display_path: snapshot.record.target_relpath,
      registry_revision: 2,
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+dirty\n",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_ID,
      title: "Faction Notes",
      target_relpath: snapshot.record.target_relpath,
      target_display_path: snapshot.record.target_relpath,
      registry_revision: 3,
      committed_revision: 3,
      committed_record: {
        ...snapshot.record,
        revision: 3,
        content_status: "committed",
      },
      normalized_content_sha256: "sha-committed-e3",
      writer_ok: true,
      bytes_written: 42,
      file_fingerprint: "fp-committed-e3",
      diagnostics: [],
    });

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    const { unmount } = renderBuildPage();

    await waitFor(() => {
      expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
    });
    expect(screen.queryByTestId("build-save-button")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(
      within(screen.getByTestId("surface-edit-host")).getByRole("button", { name: /Save/i }),
    );

    await waitFor(() => {
      expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
      expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    });
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({ document_id: DOC_ID }),
    );

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      ...snapshot,
      markdown: dirtyMarkdown,
      content_sha256: "sha-committed-e3",
      loaded_revision: 3,
      record: {
        ...snapshot.record,
        revision: 3,
        content_status: "committed",
      },
    });

    unmount();
    renderBuildPage();

    await waitFor(() => {
      expect(screen.getByTestId("build-document-status")).toHaveTextContent("Committed");
    });
    expect(liveApi.getWorkspaceDocumentSnapshot).toHaveBeenCalledWith(DOC_ID);
  });

  it("E3 StrictMode: shared Edit Save still commits once after effect rehearsal", async () => {
    const user = userEvent.setup();
    const dirtyMarkdown = "# StrictMode dirty draft\n";
    const editorJson = {
      type: "doc",
      content: [
        {
          type: "heading",
          attrs: { level: 1 },
          content: [{ type: "text", text: "StrictMode dirty draft" }],
        },
      ],
    };
    const snapshot = buildLongmontSnapshot(DOC_ID, "Faction Notes", "# Faction Notes\n\nKeep this body intact.\n");

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot);
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionWithGlowkindle());

    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "Faction Notes",
      campaignId: "longmont-c1",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: snapshot.content_sha256,
      starterContent: editorJson,
    });
    local.dirty = true;
    local.exported_markdown = dirtyMarkdown;
    local.tiptap_json = editorJson;
    window.localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), JSON.stringify(local));

    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "Faction Notes",
      target_relpath: snapshot.record.target_relpath,
      target_display_path: snapshot.record.target_relpath,
      registry_revision: 2,
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token-strict",
      writer_diff: "+strict\n",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_ID,
      title: "Faction Notes",
      target_relpath: snapshot.record.target_relpath,
      target_display_path: snapshot.record.target_relpath,
      registry_revision: 3,
      committed_revision: 3,
      committed_record: {
        ...snapshot.record,
        revision: 3,
        content_status: "committed",
      },
      normalized_content_sha256: "sha-committed-strict",
      writer_ok: true,
      bytes_written: 42,
      file_fingerprint: "fp-committed-strict",
      diagnostics: [],
    });

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    render(
      <StrictMode>
        <AgentInteractionProvider>
          <BuildSurfacePage />
          <ToolHost />
          <LegacyProjectionHostAdapter />
        </AgentInteractionProvider>
      </StrictMode>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
    });

    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(
      within(screen.getByTestId("surface-edit-host")).getByRole("button", { name: /Save/i }),
    );

    await waitFor(() => {
      expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
      expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    });
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({ document_id: DOC_ID }),
    );
  });

  it("E4: graph projection failure leaves canvas dirty with Edit Save available", async () => {
    const user = userEvent.setup();
    const editorJson = {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "Dirty draft" }] }],
    };
    const snapshot = buildLongmontSnapshot(DOC_ID, "Faction Notes");

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot);
    vi.mocked(liveApi.postWorldGraphProjection).mockRejectedValue(new Error("graph projection unavailable"));

    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "Faction Notes",
      campaignId: "longmont-c1",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: snapshot.content_sha256,
      starterContent: editorJson,
    });
    local.dirty = true;
    local.exported_markdown = "Dirty draft\n";
    local.tiptap_json = editorJson;
    window.localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), JSON.stringify(local));

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    renderBuildPage();

    await waitFor(() => {
      expect(screen.getByTestId("build-surface-shell")).toBeInTheDocument();
      expect(screen.getByTestId("build-markdown-editor")).toBeInTheDocument();
      expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
    });

    const stored = JSON.parse(
      window.localStorage.getItem(workspaceDocumentStorageKey(DOC_ID)) || "{}",
    ) as { dirty: boolean; exported_markdown: string };
    expect(stored.dirty).toBe(true);
    expect(stored.exported_markdown).toBe("Dirty draft\n");

    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(
      within(screen.getByTestId("surface-edit-host")).getByRole("button", { name: /Save/i }),
    ).toBeInTheDocument();
  });

  it("E6: document-A retained Save is a no-op after switching to document B", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id: string) =>
      buildLongmontSnapshot(id, id === DOC_ID ? "Doc A" : "Doc B"),
    );
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionWithGlowkindle());

    let retainedSaveA: (() => void | Promise<void>) | null = null;
    let latestContext: BuildReferenceContextBinding | null = null;
    let saveCommandDocumentId: string | null = null;

    function PublicationProbe() {
      const { surfaceInteractionPublication } = useAgentInteraction();
      const saveCommand = surfaceInteractionPublication?.editCommands.find(
        (command) => command.id === BUILD_DOCUMENT_SAVE_COMMAND_ID,
      );
      const workObjectId = surfaceInteractionPublication?.canvas?.workObject?.id ?? null;
      if (saveCommand && workObjectId === DOC_ID) {
        retainedSaveA = saveCommand.invoke;
      }
      if (saveCommand) {
        saveCommandDocumentId = workObjectId;
      }
      const binding = surfaceInteractionPublication?.projectionBindings.find(
        (entry) => entry.id === BUILD_REFERENCE_CONTEXT_BINDING_ID,
      );
      latestContext = (binding?.value as BuildReferenceContextBinding | undefined) ?? null;
      return null;
    }

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    render(
      <AgentInteractionProvider>
        <BuildSurfacePage />
        <ToolHost />
        <LegacyProjectionHostAdapter />
        <PublicationProbe />
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(retainedSaveA).not.toBeNull();
    });

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: /Find existing object/ }));
    await waitFor(() => {
      expect(screen.getByTestId("build-reference-search-projection")).toBeInTheDocument();
    });
    await user.type(screen.getByLabelText("Find objects"), "glow");
    await user.click(screen.getByRole("button", { name: "View" }));
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    });

    window.history.pushState({}, "", `/build?documentId=${DOC_B}&campaign=longmont-c1`);
    window.dispatchEvent(new PopStateEvent("popstate"));

    expect(await screen.findByText("Doc B")).toBeInTheDocument();
    await waitFor(() => {
      expect(latestContext?.documentId).toBe(DOC_B);
    });
    expect(screen.queryByTestId("graph-object-projection-card")).not.toBeInTheDocument();
    expect(saveCommandDocumentId).toBe(DOC_B);

    const invokeRetained = retainedSaveA!;
    await act(async () => {
      await invokeRetained();
    });

    expect(liveApi.prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(liveApi.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });
});
