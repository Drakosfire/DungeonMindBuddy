import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { LegacyProjectionHostAdapter } from "../planSurface/projection/LegacyProjectionHostAdapter";
import { ToolHost } from "../surfaceInteraction/toolHost/ToolHost";
import {
  buildInitialWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
} from "../tiptap/state/tiptapLocalState";
import { BuildSurfacePage } from "./BuildSurfacePage";

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

  it("E11: search and inspect leave document authority unchanged", async () => {
    const user = userEvent.setup();
    const markdownBody = "# Faction Notes\n\nKeep this body intact.\n";
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
      campaignId: "longmont-c1",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-faction-e11",
      starterContent: { type: "doc", content: [] },
    });
    local.dirty = true;
    local.exported_markdown = "# Dirty faction draft\n";
    window.localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), JSON.stringify(local));

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
    });

    function readAuthoritySnapshot() {
      const storedRaw = window.localStorage.getItem(workspaceDocumentStorageKey(DOC_ID));
      expect(storedRaw).toBeTruthy();
      const stored = JSON.parse(storedRaw!) as {
        dirty: boolean;
        exported_markdown: string;
        base_revision: number;
        base_content_sha256: string;
      };
      const saveButton = screen.queryByRole("button", { name: /^Save$/i });
      return {
        dirty: stored.dirty,
        exportedMarkdown: stored.exported_markdown,
        baseRevision: stored.base_revision,
        baseDigest: stored.base_content_sha256,
        status: screen.getByTestId("build-document-status").textContent,
        prepareCalls: vi.mocked(liveApi.prepareTiptapMarkdownWrite).mock.calls.length,
        commitCalls: vi.mocked(liveApi.commitTiptapMarkdownWrite).mock.calls.length,
        saveDisabled: saveButton ? (saveButton as HTMLButtonElement).disabled : null,
        saveLabel: saveButton?.textContent ?? null,
      };
    }

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    renderBuildPage();

    await waitFor(() => {
      expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved local changes");
    });
    const before = readAuthoritySnapshot();
    expect(before.dirty).toBe(true);
    expect(before.baseRevision).toBe(2);
    expect(before.baseDigest).toBe("sha-faction-e11");
    expect(before.prepareCalls).toBe(0);
    expect(before.commitCalls).toBe(0);
    expect(typeof before.exportedMarkdown).toBe("string");

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

    const after = readAuthoritySnapshot();
    expect(after).toEqual(before);
  });
});
