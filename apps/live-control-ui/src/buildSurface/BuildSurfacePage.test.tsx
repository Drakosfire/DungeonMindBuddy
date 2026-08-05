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
import { BUILD_SAVE_CONFLICTS_WITH } from "./buildDocumentCommands";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { BuildSurfacePage } from "./BuildSurfacePage";
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
        <BuildPublicationProbe />
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
});
