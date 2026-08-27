import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import * as liveApi from "./api/liveApi";
import type {
  WorldGraphProjection,
  WorldGraphProjectionRequest,
  WorkspaceCommittedRevision,
  WorkspaceDocumentSnapshot,
} from "./api/types";
import type { AppChromeTools, AppChromeToolsGeneration } from "./chrome/AppChrome";
import { buildViewExactTestSeam } from "./buildSurface/reference/BuildReferenceCapability";
import { fixtureWorkspaceDocumentRecord, FIXTURE_DOC_ID } from "./planSurface/config/planSessionDescriptor";
import { NORTH_GATE_RUNBOOK_TARGET_RELPATH } from "./tiptap/descriptors/tiptapRunbookDescriptors";
import { makeCapabilityResponse, makeRollTableArtifact, mockCatalog, mockLayout, mockPlanView, mockState } from "./test/fixtures";

const stableTiptapAction = () => undefined;
const stableTiptapEditorTools: AppChromeTools = {
  pinnedActions: [
    {
      id: "tiptap-lock-editor",
      eyebrow: "Edit state",
      label: "Lock editor",
      onClick: stableTiptapAction,
    },
  ],
  sections: [
    {
      id: "tiptap-insert-blocks",
      title: "Insert blocks",
      defaultOpen: true,
      actions: [
        {
          id: "insert-gm",
          eyebrow: "Insert",
          label: "GM Note",
          onClick: stableTiptapAction,
        },
      ],
    },
  ],
};
const stableTiptapEditorToolsGeneration: AppChromeToolsGeneration = {
  target: { kind: "spike", id: "tiptap-callout-spike" },
  tools: stableTiptapEditorTools,
};

vi.mock("./tiptap/TiptapCalloutBridgeSpike", () => ({
  TiptapCalloutBridgeSpike({
    onEditorToolsChange,
  }: {
    onEditorToolsChange?: (tools: AppChromeToolsGeneration | null) => void;
  }) {
    useEffect(() => {
      onEditorToolsChange?.(stableTiptapEditorToolsGeneration);
      return () => onEditorToolsChange?.(null);
    }, [onEditorToolsChange]);
    return (
      <main className="tiptap-spike-page">
        <header className="tiptap-spike-header">
          <h1>Tiptap Session Runbook Editor</h1>
        </header>
        <div data-testid="tiptap-editor" />
      </main>
    );
  },
}));

vi.mock("./api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api/liveApi")>();
  return {
    ...actual,
    getSurface: vi.fn(),
    getEvents: vi.fn(),
    getJobs: vi.fn(),
    getPlanView: vi.fn(),
    getGraphIngestRuns: vi.fn(),
    getGoldReviewSessions: vi.fn(),
    getManualReviewBeds: vi.fn(),
    getArtifact: vi.fn(),
    getCapabilities: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
    listWorkspaceDocuments: vi.fn(),
    getWorkspaceDocument: vi.fn(),
    getWorkspaceDocumentSnapshot: vi.fn(),
    getPlayActiveRun: vi.fn(),
    putPlayActiveRun: vi.fn(),
    getCommittedWorkspaceRevision: vi.fn(),
    createWorkspaceDocument: vi.fn(),
    postWorldGraphProjection: vi.fn(),
    listPlayRuns: vi.fn(),
    getPlayRun: vi.fn(),
    getPlayRunReferenceManifest: vi.fn(),
    putPlayRun: vi.fn(),
    putPlayRunReferenceManifest: vi.fn(),
    putPlayRunProgress: vi.fn(),
  };
});

function northGateRunbookRecord() {
  return fixtureWorkspaceDocumentRecord({
    document_id: FIXTURE_DOC_ID,
    title: "North Gate Session Runbook",
    kind: "runbook",
    target_relpath: NORTH_GATE_RUNBOOK_TARGET_RELPATH,
    target_session: 23,
    revision: 1,
  });
}

function fixtureSnapshot(
  overrides: Partial<WorkspaceDocumentSnapshot> = {},
): WorkspaceDocumentSnapshot {
  const record = overrides.record ?? fixtureWorkspaceDocumentRecord();
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record,
    markdown: "",
    content_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    file_fingerprint: "absent",
    file_exists: false,
    loaded_revision: record.revision,
    ...overrides,
  };
}

function matchingWorldGraphProjection(
  request: WorldGraphProjectionRequest,
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: request.worldId,
      campaignId: request.campaignId,
      revisionId: "rev-1",
      headRevisionId: "rev-1",
      isHead: true,
      focus: request.focus,
      admissibility: request.admissibility,
      scopeMode: request.scopeMode,
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
  };
}

describe("App inspector integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/");
    localStorage.clear();
    vi.mocked(liveApi.getSurface).mockResolvedValue({
      catalog: mockCatalog,
      layout: mockLayout,
      state: mockState,
    });
    vi.mocked(liveApi.getEvents).mockResolvedValue({ events: [] });
    vi.mocked(liveApi.getJobs).mockResolvedValue({ jobs: [] });
    vi.mocked(liveApi.getPlanView).mockResolvedValue(mockPlanView);
    vi.mocked(liveApi.getGraphIngestRuns).mockResolvedValue({
      schema_version: "dmb_graph_ingest_run_registry_v1",
      version: "test",
      runs: [],
    });
    vi.mocked(liveApi.getGoldReviewSessions).mockResolvedValue({
      schema_version: "dmb_graph_gold_review_sessions_v1",
      version: "test",
      sessions: [],
    });
    vi.mocked(liveApi.getManualReviewBeds).mockResolvedValue({
      schema_version: "dmb_graph_manual_review_beds_v1",
      version: "test",
      beds: [],
    });
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeRollTableArtifact());
    vi.mocked(liveApi.getCapabilities).mockResolvedValue(makeCapabilityResponse());
    vi.mocked(liveApi.listWorkspaceDocuments).mockImplementation(async (params) => {
      if (params?.kind === "runbook") {
        return {
          schema_version: "dmb_workspace_document_registry_v1",
          records: [northGateRunbookRecord()],
        };
      }
      return {
        schema_version: "dmb_workspace_document_registry_v1",
        records: [fixtureWorkspaceDocumentRecord()],
      };
    });
    vi.mocked(liveApi.getWorkspaceDocument).mockImplementation(async (documentId) => {
      if (documentId === FIXTURE_DOC_ID) {
        return northGateRunbookRecord();
      }
      return fixtureWorkspaceDocumentRecord({ document_id: documentId });
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockImplementation(async (payload) => {
      if (payload.kind === "runbook") {
        return northGateRunbookRecord();
      }
      if (payload.kind === "worldbuilding_source") {
        const documentId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
        return fixtureWorkspaceDocumentRecord({
          document_id: documentId,
          title: payload.title,
          campaign_id: payload.campaign_id,
          target_session: null,
          kind: "worldbuilding_source",
          target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
          source_domain: "worldbuilding",
          document_class: payload.document_class ?? "lore",
          authority_state: payload.authority_state ?? "draft",
          visibility_state: payload.visibility_state ?? "internal",
        });
      }
      return fixtureWorkspaceDocumentRecord();
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (documentId) => {
      if (documentId === FIXTURE_DOC_ID) {
        return fixtureSnapshot({ record: northGateRunbookRecord() });
      }
      if (documentId === "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb") {
        return fixtureSnapshot({
          record: fixtureWorkspaceDocumentRecord({
            document_id: documentId,
            title: "Untitled worldbuilding source",
            campaign_id: "longmont-c2",
            target_session: null,
            kind: "worldbuilding_source",
            target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
            source_domain: "worldbuilding",
            document_class: "lore",
            authority_state: "draft",
            visibility_state: "internal",
          }),
          markdown: "",
        });
      }
      return fixtureSnapshot({ record: fixtureWorkspaceDocumentRecord({ document_id: documentId }) });
    });
    vi.mocked(liveApi.listPlayRuns).mockResolvedValue({
      schema_version: "dmb_play_runs_list_v1",
      records: [],
    });
    vi.mocked(liveApi.getPlayActiveRun).mockResolvedValue({
      schema_version: "dmb_play_active_run_v1",
      run_id: null,
      selected_at: null,
    });
    vi.mocked(liveApi.putPlayActiveRun).mockResolvedValue({
      schema_version: "dmb_play_active_run_v1",
      run_id: null,
      selected_at: null,
    });
    vi.mocked(liveApi.getPlayRun).mockRejectedValue(new liveApi.LiveApiError("not found", 404));
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockRejectedValue(
      new liveApi.LiveApiError("not found", 404),
    );
    vi.mocked(liveApi.putPlayRun).mockRejectedValue(new liveApi.LiveApiError("not found", 404));
    vi.mocked(liveApi.putPlayRunReferenceManifest).mockRejectedValue(new liveApi.LiveApiError("not found", 404));
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new liveApi.LiveApiError("not found", 404));
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockRejectedValue(
      new liveApi.LiveApiError("not found", 404),
    );
    vi.mocked(liveApi.postWorldGraphProjection).mockImplementation(async (request) =>
      matchingWorldGraphProjection(request),
    );
  });

  it("renders the launcher at the root route", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /command board/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /plan prep surface/i })).toHaveAttribute("href", "/plan");
    expect(screen.getByRole("link", { name: /play runbook table deck/i })).toHaveAttribute("href", "/play");
    expect(screen.getByRole("link", { name: /ingest memory review/i })).toHaveAttribute("href", "/ingest");
    expect(screen.getByRole("link", { name: /build worldbuilding source/i })).toHaveAttribute("href", "/build");
    expect(screen.getByRole("link", { name: /combat tracker north reach gate tracker/i })).toHaveAttribute(
      "href",
      "/combat",
    );
    expect(screen.queryByRole("link", { name: /live control/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /live play/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /retrieval/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /tiptap|developer spike/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(liveApi.getSurface).not.toHaveBeenCalled();
  });

  it("keeps primary site nav to core product surfaces", () => {
    render(<App />);

    const nav = screen.getByRole("navigation", { name: "Command board navigation" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/",
      "/plan",
      "/play",
      "/ingest",
      "/build",
      "/combat",
    ]);
    expect(within(nav).queryByRole("link", { name: "Live Control" })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: "Live play" })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: "Tiptap Spike" })).not.toBeInTheDocument();
  });
  it("opens empty inspector from app chrome control", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/surface");
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: /inspector/i }));
    expect(screen.getByText(/Select a timeline ref or record event to inspect/i)).toBeInTheDocument();
  });

  it("renders plan surface from /plan", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/plan");
    render(<App />);

    expect(await screen.findByTestId("plan-canvas-title")).toHaveTextContent(/C2 Session 23 Prep/i);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Recap" }));
    const toolbox = await screen.findByRole("navigation", { name: "Toolbox tools" });
    expect(toolbox).toBeInTheDocument();
    expect(document.querySelectorAll(".surface-projection-host")).toHaveLength(1);
    expect(within(toolbox).queryByRole("button", { name: "Ingest Recap" })).not.toBeInTheDocument();
    expect(within(toolbox).queryByRole("button", { name: "Graph Preview" })).not.toBeInTheDocument();
    expect(within(toolbox).queryByRole("button", { name: "Graph Gold Review" })).not.toBeInTheDocument();
    expect(within(toolbox).queryByRole("button", { name: "Graph Review" })).not.toBeInTheDocument();
    expect(within(toolbox).queryByRole("button", { name: "Vocabulary Review" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Plan canvas")).toBeInTheDocument();
    expect(liveApi.getPlanView).toHaveBeenCalled();
  });

  it("renders memory ingest from /ingest", async () => {
    window.history.pushState({}, "", "/ingest");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();
    expect(screen.queryByText(/Review extracted graph runs against gold/i)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ingest" })).toHaveClass("active");
    expect(await screen.findByText(/No preview-ready graph runs are available/i)).toBeInTheDocument();
    expect(liveApi.getPlanView).toHaveBeenCalled();
    expect(liveApi.getGraphIngestRuns).toHaveBeenCalled();
    expect(liveApi.getGoldReviewSessions).toHaveBeenCalled();
  });

  it("E1 bare /build: real App shows empty state and New source without auto-create", async () => {
    window.history.pushState({}, "", "/build");
    render(<App />);

    expect(await screen.findByTestId("build-surface-empty")).toBeInTheDocument();
    expect(screen.getByTestId("build-document-create-open")).toBeInTheDocument();
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(screen.queryByTestId("build-markdown-editor")).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Command board navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Build" })).toHaveClass("active");
  });

  it("E1/E5: real App /build route renders composition and viewExact seam", async () => {
    buildViewExactTestSeam.reset();
    const buildDocId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    const glowkindleNode = {
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
    const buildRecord = fixtureWorkspaceDocumentRecord({
      document_id: buildDocId,
      title: "Faction Notes",
      campaign_id: "longmont-c1",
      target_session: null,
      kind: "worldbuilding_source",
      target_relpath: `out/workspace/worldbuilding/${buildDocId}.md`,
      source_domain: "worldbuilding",
      document_class: "faction",
      authority_state: "draft",
      visibility_state: "internal",
      content_status: "committed",
      revision: 2,
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      fixtureSnapshot({
        record: buildRecord,
        markdown: "# Faction Notes\n",
        content_sha256: "sha-build-e1",
        loaded_revision: 2,
        file_fingerprint: "present",
        file_exists: true,
      }),
    );
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
      nodes: [glowkindleNode],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });

    window.history.pushState({}, "", `/build?documentId=${buildDocId}&campaign=longmont-c1`);
    render(<App />);

    expect(await screen.findByTestId("build-surface-shell")).toBeInTheDocument();
    expect(screen.getByTestId("build-source-mode-read")).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByTestId("build-markdown-editor")).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Command board navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Build" })).toHaveClass("active");
    expect(screen.getByTestId("agent-interaction-chrome")).toBeInTheDocument();
    expect(screen.getByTestId("agent-interaction-bar")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByTestId("surface-edit-host")).toBeInTheDocument();
    expect(screen.getByTestId("surface-tool-host")).toBeInTheDocument();

    const user = userEvent.setup();
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
    expect(
      within(screen.getByTestId("graph-object-projection-card")).getByText("Glowkindle"),
    ).toBeInTheDocument();
    expect(buildViewExactTestSeam.lastGraphNodeId).toBe("npc-glowkindle");
    expect(buildViewExactTestSeam.lastGraphScope).toEqual({
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      scopeMode: "campaign",
      revisionId: "rev-1",
    });

    await waitFor(() => {
      expect(document.querySelectorAll(".surface-projection-host")).toHaveLength(1);
    });
    expect(document.querySelectorAll('[data-testid="surface-tool-host"]')).toHaveLength(1);
    expect(document.querySelectorAll('[data-testid="surface-edit-host"]')).toHaveLength(1);
    expect(document.querySelectorAll('[data-testid="agent-interaction-chrome"]')).toHaveLength(1);
  });

  it("E7: route remount keeps singular ToolHost, EditHost, and Agent chrome", async () => {
    const buildDocId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    const buildRecord = fixtureWorkspaceDocumentRecord({
      document_id: buildDocId,
      title: "Faction Notes",
      campaign_id: "longmont-c1",
      target_session: null,
      kind: "worldbuilding_source",
      target_relpath: `out/workspace/worldbuilding/${buildDocId}.md`,
      source_domain: "worldbuilding",
      document_class: "faction",
      authority_state: "draft",
      visibility_state: "internal",
      content_status: "committed",
      revision: 2,
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      fixtureSnapshot({
        record: buildRecord,
        markdown: "# Faction Notes\n",
        content_sha256: "sha-build-e7",
        loaded_revision: 2,
        file_fingerprint: "present",
        file_exists: true,
      }),
    );
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

    window.history.pushState({}, "", `/build?documentId=${buildDocId}&campaign=longmont-c1`);
    const { unmount: unmountBuild } = render(<App />);

    expect(await screen.findByTestId("build-surface-shell")).toBeInTheDocument();
    await waitFor(() => {
      expect(document.querySelectorAll('[data-testid="surface-tool-host"]')).toHaveLength(1);
      expect(document.querySelectorAll('[data-testid="surface-edit-host"]')).toHaveLength(1);
      expect(document.querySelectorAll('[data-testid="agent-interaction-chrome"]')).toHaveLength(1);
    });

    unmountBuild();

    window.history.pushState({}, "", "/plan");
    const { unmount: unmountPlan } = render(<App />);

    expect(await screen.findByTestId("plan-canvas-title")).toHaveTextContent(/C2 Session 23 Prep/i);
    await waitFor(() => {
      expect(document.querySelectorAll('[data-testid="surface-tool-host"]')).toHaveLength(1);
      expect(document.querySelectorAll('[data-testid="agent-interaction-chrome"]')).toHaveLength(1);
      expect(document.querySelectorAll('[data-testid="surface-edit-host"]').length).toBeLessThanOrEqual(1);
    });

    unmountPlan();

    window.history.pushState({}, "", `/build?documentId=${buildDocId}&campaign=longmont-c1`);
    render(<App />);

    expect(await screen.findByTestId("build-surface-shell")).toBeInTheDocument();
    await waitFor(() => {
      expect(document.querySelectorAll('[data-testid="surface-tool-host"]')).toHaveLength(1);
      expect(document.querySelectorAll('[data-testid="surface-edit-host"]')).toHaveLength(1);
      expect(document.querySelectorAll('[data-testid="agent-interaction-chrome"]')).toHaveLength(1);
    });
  });

  it("renders the shared editor toolbar collapsed on the Tiptap spike route", async () => {
    const runbookRecord = fixtureWorkspaceDocumentRecord({
      document_id: FIXTURE_DOC_ID,
      kind: "runbook",
      title: "North Gate Session Runbook",
      target_relpath: NORTH_GATE_RUNBOOK_TARGET_RELPATH,
      target_session: 23,
      revision: 1,
    });
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [runbookRecord],
    });
    vi.mocked(liveApi.getWorkspaceDocument).mockResolvedValue(runbookRecord);
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(runbookRecord);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      fixtureSnapshot({
        record: runbookRecord,
        loaded_revision: runbookRecord.revision,
        markdown: "",
      }),
    );

    window.history.pushState({}, "", "/tiptap-callout-spike");
    render(<App />);

    // Authority-safe open: runbook kind accepted; editor shell mounts under App chrome.
    expect(await screen.findByRole("heading", { name: "Tiptap Session Runbook Editor" })).toBeInTheDocument();
    expect(screen.getByTestId("tiptap-editor")).toBeInTheDocument();
    expect(screen.queryByText(/wrong document kind|Failed to load runbook/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Command board navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Plan" })).toHaveAttribute("href", "/plan");
    expect(screen.queryByRole("link", { name: "Live play" })).not.toBeInTheDocument();

    const editToggle = await screen.findByRole("button", { name: "Edit" });
    expect(editToggle).toHaveAttribute("aria-expanded", "false");
  });

  const PLAY_RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  const PLAY_ARTIFACT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
  const PLAY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
  const PLAY_MARKDOWN = [
    "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
    "## Gate",
    "",
    "Scene intro.",
    "",
    "<!-- dmb-playable-element:v1 kind=beat id=beat:approach -->",
    "### Approach",
    "",
    "Approach body.",
    "",
  ].join("\n");
  const PLAY_SHA_R4 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
  const PLAY_MARKDOWN_R4 = [
    "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
    "## Gate",
    "",
    "R4 replacement scene.",
    "",
    "<!-- dmb-playable-element:v1 kind=beat id=beat:approach -->",
    "### Approach",
    "",
    "R4 replacement beat that must not mix with R3 Approach body.",
    "",
  ].join("\n");

  const PLAY_V2_MARKDOWN = [
    "<!-- dmb-playable-element:v2 kind=beat id=beat:one beat_kind=spine -->",
    "## Beat 1",
    "",
    "<!-- dmb-playable-element:v2 kind=scene id=scene:a -->",
    "### Scene A",
    "",
    "Scene A unique body.",
    "",
    "<!-- dmb-playable-element:v2 kind=beat id=beat:two beat_kind=optional -->",
    "## Beat 2",
    "",
  ].join("\n");

  function v2Manifest() {
    return {
      schema_version: "dmb_play_run_reference_manifest_v2" as const,
      run_id: PLAY_RUN_ID,
      playable_artifact_id: PLAY_ARTIFACT_ID,
      playable_revision: 3,
      playable_content_sha256: PLAY_SHA,
      sealed_at: "2026-08-17T00:00:00Z",
      beats: [
        { beat_id: "beat:one", beat_kind: "spine" as const },
        { beat_id: "beat:two", beat_kind: "optional" as const },
      ],
      scenes: [{ scene_id: "scene:a", beat_id: "beat:one" }],
      choices: [],
      options: [],
      edges: [],
    };
  }

  function mockV2PlayRun(
    progress: {
      current_beat_id: string | null;
      current_scene_id: string | null;
    } = { current_beat_id: null, current_scene_id: null },
  ) {
    const record = {
      ...playRunRecord(),
      progress: {
        ...playRunRecord().progress,
        current_beat_id: progress.current_beat_id,
        current_scene_id: progress.current_scene_id,
      },
    };
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(record);
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockResolvedValue(v2Manifest());
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockResolvedValue(
      playCommittedRevision({ markdown: PLAY_V2_MARKDOWN }),
    );
    return record;
  }

  function playCommittedRevision(
    overrides: Partial<WorkspaceCommittedRevision> = {},
  ): WorkspaceCommittedRevision {
    return {
      schema_version: "dmb_workspace_committed_revision_v1",
      document_id: PLAY_ARTIFACT_ID,
      kind: "runbook",
      campaign_id: "longmont-c2",
      title: "North Gate Runbook",
      status: "active",
      object_revision: 3,
      work_revision_id: "11111111-1111-4111-8111-111111111111",
      revision_n: 3,
      markdown: PLAY_MARKDOWN,
      content_sha256: PLAY_SHA,
      has_divergent_working_copy: false,
      target_relpath: `out/workspace/runbooks/${PLAY_ARTIFACT_ID}.md`,
      ...overrides,
    };
  }

  function playRunRecord() {
    return {
      schema_version: "dmb_play_run_record_v1" as const,
      run_id: PLAY_RUN_ID,
      campaign_id: "longmont-c2",
      playable_artifact_id: PLAY_ARTIFACT_ID,
      playable_revision: 3,
      playable_content_sha256: PLAY_SHA,
      run_revision: 4,
      created_at: "2026-08-17T00:00:00Z",
      updated_at: "2026-08-17T00:00:00Z",
      progress: {
        current_scene_id: null,
        current_beat_id: null,
        resolved_beat_ids: [] as string[],
        selections: {} as Record<string, string>,
        notes_by_element_id: {} as Record<string, string>,
      },
    };
  }

  function mockReadyPlayRun() {
    const record = playRunRecord();
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(record);
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: PLAY_RUN_ID,
      playable_artifact_id: PLAY_ARTIFACT_ID,
      playable_revision: 3,
      playable_content_sha256: PLAY_SHA,
      sealed_at: "2026-08-17T00:00:00Z",
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene", element_id: "scene:gate" },
      ],
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      fixtureSnapshot({
        record: fixtureWorkspaceDocumentRecord({
          document_id: PLAY_ARTIFACT_ID,
          title: "North Gate Runbook",
          kind: "runbook",
          revision: 3,
          content_status: "committed",
        }),
        markdown: PLAY_MARKDOWN,
        content_sha256: PLAY_SHA,
        loaded_revision: 3,
        file_exists: true,
        file_fingerprint: "present",
      }),
    );
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockResolvedValue(playCommittedRevision());
    return record;
  }

  it("mounts /play through shared AppChrome without auto-selecting a Run", async () => {
    vi.mocked(liveApi.listPlayRuns).mockResolvedValue({
      schema_version: "dmb_play_runs_list_v1",
      records: [playRunRecord()],
    });
    window.history.pushState({}, "", "/play");
    render(<App />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Play" })).toHaveClass("active");
    expect(screen.getByRole("navigation", { name: "Command board navigation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Choose a Run" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Existing Runs" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Start a Run" })).toBeInTheDocument();
    expect(liveApi.getPlayActiveRun).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayActiveRun).not.toHaveBeenCalled();
    expect(screen.getByTestId("play-start-run-submit")).toBeDisabled();
    expect(await screen.findByRole("link", { name: new RegExp(PLAY_RUN_ID) })).toHaveAttribute(
      "href",
      `/play?run=${PLAY_RUN_ID}`,
    );
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
    expect(screen.queryByText(/ofConks/i)).not.toBeInTheDocument();
  });

  it("resumes the exact active Run from bare /play without opening the chooser or creating a Run", async () => {
    mockReadyPlayRun();
    vi.mocked(liveApi.getPlayActiveRun).mockResolvedValue({
      schema_version: "dmb_play_active_run_v1",
      run_id: PLAY_RUN_ID,
      selected_at: "2026-08-17T00:00:00Z",
    });
    window.history.pushState({}, "", "/play");
    render(<App />);

    expect(await screen.findByTestId("runbook-table-deck")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/play");
    expect(window.location.search).toBe(`?run=${PLAY_RUN_ID}`);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(PLAY_RUN_ID, { ensureNativeReady: true });
    expect(liveApi.listPlayRuns).not.toHaveBeenCalled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    await waitFor(() => expect(liveApi.putPlayActiveRun).toHaveBeenCalledWith(PLAY_RUN_ID));
    expect(liveApi.putPlayActiveRun).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("play-run-chooser")).not.toBeInTheDocument();
  });

  it("falls back to the chooser with a warning when active selection cannot be read", async () => {
    vi.mocked(liveApi.getPlayActiveRun).mockRejectedValue(
      new liveApi.LiveApiError("active selection unavailable", 503),
    );
    vi.mocked(liveApi.listPlayRuns).mockResolvedValue({
      schema_version: "dmb_play_runs_list_v1",
      records: [playRunRecord()],
    });
    window.history.pushState({}, "", "/play");
    render(<App />);

    expect(await screen.findByTestId("play-active-run-warning")).toHaveTextContent(
      /Resume state is unavailable/i,
    );
    expect(screen.getByTestId("play-run-chooser")).toBeInTheDocument();
    expect(liveApi.getPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayActiveRun).not.toHaveBeenCalled();
    expect(await screen.findByRole("link", { name: new RegExp(PLAY_RUN_ID) })).toHaveAttribute(
      "href",
      `/play?run=${PLAY_RUN_ID}`,
    );
  });

  it("shows a development Play setup hint when application state is unavailable", async () => {
    const unavailable = new liveApi.LiveApiError(
      "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL is not set; DungeonBuddy application state is unavailable",
      503,
    );
    vi.mocked(liveApi.getPlayActiveRun).mockRejectedValue(unavailable);
    vi.mocked(liveApi.listPlayRuns).mockRejectedValue(unavailable);
    vi.mocked(liveApi.listWorkspaceDocuments).mockRejectedValue(unavailable);
    window.history.pushState({}, "", "/play");
    render(<App />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(await screen.findByTestId("play-active-run-warning")).toHaveTextContent(
      /Resume state is unavailable/i,
    );
    expect(screen.getByTestId("play-local-setup-hint")).toHaveTextContent(
      /Local Play setup is incomplete/i,
    );
    expect(screen.getByTestId("play-local-setup-hint")).toHaveTextContent(
      /uv run python scripts\/bootstrap_local_play.py check/,
    );
    await waitFor(() => {
      expect(screen.getByTestId("play-existing-runs")).toHaveTextContent(
        /DungeonBuddy application state is unavailable/i,
      );
    });
    expect(screen.queryByText(/Run recovery is pending/i)).not.toBeInTheDocument();
    expect(liveApi.getPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    expect(screen.queryByTestId("play-current-moment-cockpit")).not.toBeInTheDocument();
  });

  it("does not show a Play setup hint when application state is available", async () => {
    vi.mocked(liveApi.listPlayRuns).mockResolvedValue({
      schema_version: "dmb_play_runs_list_v1",
      records: [playRunRecord()],
    });
    window.history.pushState({}, "", "/play");
    render(<App />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: new RegExp(PLAY_RUN_ID) })).toBeInTheDocument();
    expect(screen.queryByTestId("play-local-setup-hint")).not.toBeInTheDocument();
    expect(screen.queryByText(/Local Play setup is incomplete/i)).not.toBeInTheDocument();
  });

  it("keeps existing Runs openable when Start Run discovery fails", async () => {
    vi.mocked(liveApi.listPlayRuns).mockResolvedValue({
      schema_version: "dmb_play_runs_list_v1",
      records: [playRunRecord()],
    });
    vi.mocked(liveApi.listWorkspaceDocuments).mockRejectedValue(
      new liveApi.LiveApiError("workspace documents unavailable", 503),
    );
    window.history.pushState({}, "", "/play");
    render(<App />);

    expect(await screen.findByRole("link", { name: new RegExp(PLAY_RUN_ID) })).toHaveAttribute(
      "href",
      `/play?run=${PLAY_RUN_ID}`,
    );
    expect(await screen.findByTestId("play-start-run-unavailable")).toBeInTheDocument();
    expect(screen.getByTestId("play-existing-runs")).toBeInTheDocument();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
  });

  it("exposes Start New as an explicit chooser action without clearing the active Run", async () => {
    mockReadyPlayRun();
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("runbook-table-deck")).toBeInTheDocument();
    await waitFor(() => expect(liveApi.putPlayActiveRun).toHaveBeenCalledWith(PLAY_RUN_ID));
    await userEvent.setup().click(screen.getByTestId("play-start-new-run"));

    expect(window.location.search).toBe("?choose=1");
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Start a Run" })).toBeInTheDocument();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
  });

  it("keeps a READY Run usable when the active-selection write fails", async () => {
    mockReadyPlayRun();
    vi.mocked(liveApi.putPlayActiveRun).mockRejectedValue(
      new liveApi.LiveApiError("active selection unavailable", 503),
    );
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("runbook-table-deck")).toBeInTheDocument();
    expect(await screen.findByTestId("play-active-run-save-warning")).toHaveTextContent(
      /Run is open, but Resume state could not be saved/i,
    );
    expect(screen.getByTestId("play-surface-ready")).toBeInTheDocument();
    expect(liveApi.putPlayActiveRun).toHaveBeenCalledTimes(1);
  });

  it("serializes delayed active writes so a newer READY Run remains selected", async () => {
    const otherRunId = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
    const firstRun = playRunRecord();
    const secondRun = { ...firstRun, run_id: otherRunId };
    const activeState = (runId: string) => ({
      schema_version: "dmb_play_active_run_v1" as const,
      run_id: runId,
      selected_at: "2026-08-17T00:00:00Z",
    });
    const manifestFor = (run: typeof firstRun) => ({
      schema_version: "dmb_play_run_reference_manifest_v1" as const,
      run_id: run.run_id,
      playable_artifact_id: run.playable_artifact_id,
      playable_revision: run.playable_revision,
      playable_content_sha256: run.playable_content_sha256,
      sealed_at: "2026-08-17T00:00:00Z",
      elements: [
        { kind: "beat" as const, element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene" as const, element_id: "scene:gate" },
      ],
    });
    let releaseFirst: (value: ReturnType<typeof activeState>) => void = () => undefined;
    const delayedFirst = new Promise<ReturnType<typeof activeState>>((resolve) => {
      releaseFirst = resolve;
    });

    vi.mocked(liveApi.getPlayRun).mockImplementation(async (runId) => (
      runId === PLAY_RUN_ID ? firstRun : secondRun
    ));
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockImplementation(async (runId) => (
      manifestFor(runId === PLAY_RUN_ID ? firstRun : secondRun)
    ));
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      fixtureSnapshot({
        record: fixtureWorkspaceDocumentRecord({
          document_id: PLAY_ARTIFACT_ID,
          title: "North Gate Runbook",
          kind: "runbook",
          revision: 3,
          content_status: "committed",
        }),
        markdown: PLAY_MARKDOWN,
        content_sha256: PLAY_SHA,
        loaded_revision: 3,
        file_exists: true,
        file_fingerprint: "present",
      }),
    );
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockResolvedValue(playCommittedRevision());
    vi.mocked(liveApi.putPlayActiveRun).mockImplementation(async (runId) => (
      runId === PLAY_RUN_ID ? delayedFirst : activeState(runId)
    ));

    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);
    expect(await screen.findByText(`Run ${PLAY_RUN_ID}`)).toBeInTheDocument();
    await waitFor(() => expect(liveApi.putPlayActiveRun).toHaveBeenCalledWith(PLAY_RUN_ID));

    window.history.pushState({}, "", `/play?run=${otherRunId}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(await screen.findByText(`Run ${otherRunId}`)).toBeInTheDocument();
    expect(liveApi.putPlayActiveRun).toHaveBeenCalledTimes(1);

    releaseFirst(activeState(PLAY_RUN_ID));
    await waitFor(() => expect(liveApi.putPlayActiveRun).toHaveBeenCalledWith(otherRunId));
    expect(liveApi.putPlayActiveRun.mock.calls.map(([runId]) => runId)).toEqual([
      PLAY_RUN_ID,
      otherRunId,
    ]);
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
  });

  it("navigates to the exact new Run only after create and seal are confirmed", async () => {
    const user = userEvent.setup();
    vi.spyOn(crypto, "randomUUID").mockReturnValue(PLAY_RUN_ID);
    mockReadyPlayRun();
    vi.mocked(liveApi.listPlayRuns).mockResolvedValue({
      schema_version: "dmb_play_runs_list_v1",
      records: [],
    });
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [
        fixtureWorkspaceDocumentRecord({
          document_id: PLAY_ARTIFACT_ID,
          title: "North Gate Runbook",
          kind: "runbook",
          revision: 3,
          content_status: "committed",
        }),
      ],
    });
    vi.mocked(liveApi.putPlayRun).mockResolvedValue(playRunRecord());
    vi.mocked(liveApi.putPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: PLAY_RUN_ID,
      playable_artifact_id: PLAY_ARTIFACT_ID,
      playable_revision: 3,
      playable_content_sha256: PLAY_SHA,
      sealed_at: "2026-08-17T00:00:00Z",
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene", element_id: "scene:gate" },
      ],
    });
    window.history.pushState({}, "", "/play");
    render(<App />);

    await user.click(await screen.findByTestId(`play-start-runbook-${PLAY_ARTIFACT_ID}`));
    await user.click(screen.getByTestId("play-start-run-submit"));

    expect(await screen.findByTestId("runbook-table-deck")).toBeInTheDocument();
    expect(liveApi.putPlayRun).toHaveBeenCalledWith(PLAY_RUN_ID, {
      playable_artifact_id: PLAY_ARTIFACT_ID,
      expected_playable_revision: 3,
      expected_playable_content_sha256: PLAY_SHA,
    });
    expect(liveApi.putPlayRunReferenceManifest).toHaveBeenCalledWith(PLAY_RUN_ID);
    await waitFor(() => expect(liveApi.putPlayActiveRun).toHaveBeenCalledWith(PLAY_RUN_ID));
    expect(liveApi.putPlayActiveRun).toHaveBeenCalledTimes(1);
    expect(window.location.pathname).toBe("/play");
    expect(window.location.search).toBe(`?run=${PLAY_RUN_ID}`);
  });

  it("loads only the exact Run UUID from /play?run=", async () => {
    mockReadyPlayRun();
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("runbook-table-deck")).toBeInTheDocument();
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(PLAY_RUN_ID, { ensureNativeReady: true });
    expect(liveApi.getPlayRun).toHaveBeenCalledTimes(1);
    expect(screen.getByText(`Run ${PLAY_RUN_ID}`)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "North Gate Runbook" })).toBeInTheDocument();
    expect(screen.getByTestId("play-surface-ready")).toHaveAttribute("data-play-campaign-id", "longmont-c2");
    expect(screen.getByTestId("play-surface-ready")).toHaveAttribute("data-play-document-id", PLAY_ARTIFACT_ID);
    expect(screen.getByTestId("agent-interaction-chrome")).toHaveAttribute("data-surface-id", "play");
    expect(screen.queryByTestId("play-run-chooser")).not.toBeInTheDocument();
    expect(document.querySelectorAll(".surface-projection-host").length).toBeLessThanOrEqual(1);
    expect(screen.queryByText(/ofConks/i)).not.toBeInTheDocument();
  });

  it("does not auto-select another Run for a malformed run query", async () => {
    vi.mocked(liveApi.listPlayRuns).mockResolvedValue({
      schema_version: "dmb_play_runs_list_v1",
      records: [playRunRecord()],
    });
    window.history.pushState({}, "", "/play?run=not-a-uuid");
    render(<App />);

    expect(await screen.findByTestId("play-status-miss")).toBeInTheDocument();
    expect(liveApi.getPlayRun).not.toHaveBeenCalled();
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
  });

  it("blocks recovery-pending Runs before presenting mutation controls", async () => {
    vi.mocked(liveApi.getPlayRun).mockRejectedValue(
      new liveApi.LiveApiError("Play Run rebase recovery is pending", 503),
    );
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-status-recovery_pending")).toBeInTheDocument();
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "Resolved" })).not.toBeInTheDocument();
  });

  it("blocks a newer committed Runbook without overlaying Runtime", async () => {
    mockReadyPlayRun();
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockResolvedValue(
      playCommittedRevision({
        object_revision: 4,
        revision_n: 4,
        markdown: `${PLAY_MARKDOWN}\nNewer prose that must not render.\n`,
      }),
    );
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-status-integrity_failure")).toBeInTheDocument();
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
    expect(screen.queryByText(/Newer prose that must not render/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "Resolved" })).not.toBeInTheDocument();
    expect(screen.getByTestId("play-status-integrity_failure")).toHaveAttribute("data-play-campaign-id", "");
    expect(screen.getByTestId("play-status-integrity_failure")).toHaveAttribute("data-play-document-id", "");
    expect(screen.getByTestId("agent-interaction-chrome")).toHaveAttribute("data-surface-id", "play");
    expect(screen.getByTestId("agent-interaction-chrome")).not.toHaveTextContent(PLAY_ARTIFACT_ID);
  });

  it("does not publish unadmitted campaign or document authority after integrity failure", async () => {
    mockReadyPlayRun();
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: PLAY_RUN_ID,
      playable_artifact_id: PLAY_ARTIFACT_ID,
      playable_revision: 99,
      playable_content_sha256: PLAY_SHA,
      sealed_at: "2026-08-17T00:00:00Z",
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene", element_id: "scene:gate" },
      ],
    });
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-status-integrity_failure")).toBeInTheDocument();
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
    expect(screen.getByTestId("play-status-integrity_failure")).toHaveAttribute("data-play-campaign-id", "");
    expect(screen.getByTestId("play-status-integrity_failure")).toHaveAttribute("data-play-document-id", "");
    expect(screen.getByTestId("agent-interaction-chrome")).toHaveAttribute("data-surface-id", "play");
    expect(screen.getByTestId("agent-interaction-chrome")).not.toHaveTextContent("longmont-c2");
    expect(screen.getByTestId("agent-interaction-chrome")).not.toHaveTextContent(PLAY_ARTIFACT_ID);
  });

  it("discards a stale exact-Run load after the route changes", async () => {
    const otherRunId = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
    let resolveFirst: (value: ReturnType<typeof playRunRecord>) => void = () => undefined;
    const firstLoad = new Promise<ReturnType<typeof playRunRecord>>((resolve) => {
      resolveFirst = resolve;
    });
    vi.mocked(liveApi.getPlayRun).mockImplementation(async (runId) => {
      if (runId === PLAY_RUN_ID) return firstLoad;
      return { ...playRunRecord(), run_id: otherRunId };
    });
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockImplementation(async (runId) => ({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: runId,
      playable_artifact_id: PLAY_ARTIFACT_ID,
      playable_revision: 3,
      playable_content_sha256: PLAY_SHA,
      sealed_at: "2026-08-17T00:00:00Z",
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene", element_id: "scene:gate" },
      ],
    }));
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      fixtureSnapshot({
        record: fixtureWorkspaceDocumentRecord({
          document_id: PLAY_ARTIFACT_ID,
          title: "North Gate Runbook",
          kind: "runbook",
          revision: 3,
          content_status: "committed",
        }),
        markdown: PLAY_MARKDOWN,
        content_sha256: PLAY_SHA,
        loaded_revision: 3,
        file_exists: true,
        file_fingerprint: "present",
      }),
    );
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockResolvedValue(playCommittedRevision());

    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);
    expect(await screen.findByText(/Loading exact Run/i)).toBeInTheDocument();

    window.history.pushState({}, "", `/play?run=${otherRunId}`);
    window.dispatchEvent(new PopStateEvent("popstate"));

    expect(await screen.findByText(`Run ${otherRunId}`)).toBeInTheDocument();
    resolveFirst(playRunRecord());
    await waitFor(() => {
      expect(screen.queryByText(`Run ${PLAY_RUN_ID}`)).not.toBeInTheDocument();
    });
    expect(screen.getByText(`Run ${otherRunId}`)).toBeInTheDocument();
  });

  it("does not keep R3 authored content READY after a concurrent rebase 409 reconciliation", async () => {
    const user = userEvent.setup();
    mockReadyPlayRun();
    const r3Run = playRunRecord();
    const r4Run = {
      ...playRunRecord(),
      playable_revision: 4,
      playable_content_sha256: PLAY_SHA_R4,
      run_revision: 20,
      progress: {
        ...playRunRecord().progress,
        current_scene_id: "scene:gate",
        current_beat_id: "beat:approach",
      },
    };
    let boundRevision = 3;
    vi.mocked(liveApi.putPlayRunProgress).mockImplementation(async () => {
      boundRevision = 4;
      throw new liveApi.LiveApiError("CAS conflict", 409);
    });
    vi.mocked(liveApi.getPlayRun).mockImplementation(async () => (boundRevision === 3 ? r3Run : r4Run));
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockImplementation(async () => ({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: PLAY_RUN_ID,
      playable_artifact_id: PLAY_ARTIFACT_ID,
      playable_revision: boundRevision,
      playable_content_sha256: boundRevision === 3 ? PLAY_SHA : PLAY_SHA_R4,
      sealed_at: "2026-08-17T00:00:00Z",
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene", element_id: "scene:gate" },
      ],
    }));
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async () =>
      fixtureSnapshot({
        record: fixtureWorkspaceDocumentRecord({
          document_id: PLAY_ARTIFACT_ID,
          title: "North Gate Runbook",
          kind: "runbook",
          revision: boundRevision,
          content_status: "committed",
        }),
        markdown: boundRevision === 3 ? PLAY_MARKDOWN : PLAY_MARKDOWN_R4,
        content_sha256: boundRevision === 3 ? PLAY_SHA : PLAY_SHA_R4,
        loaded_revision: boundRevision,
        file_exists: true,
        file_fingerprint: "present",
      }),
    );
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockImplementation(async () =>
      playCommittedRevision({
        object_revision: boundRevision,
        revision_n: boundRevision,
        markdown: boundRevision === 3 ? PLAY_MARKDOWN : PLAY_MARKDOWN_R4,
        content_sha256: boundRevision === 3 ? PLAY_SHA : PLAY_SHA_R4,
      }),
    );

    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("runbook-table-deck")).toBeInTheDocument();
    expect(screen.getByText("Approach body.")).toBeInTheDocument();
    expect(screen.queryByText(/R4 replacement beat/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: "Resolved" }));

    await waitFor(() => {
      expect(screen.queryByText("Approach body.")).not.toBeInTheDocument();
    });
    expect(screen.queryByTestId("play-cas-conflict")).not.toBeInTheDocument();
    expect(await screen.findByTestId("runbook-table-deck")).toBeInTheDocument();
    expect(screen.getByText(/R4 replacement beat that must not mix with R3 Approach body/i)).toBeInTheDocument();
    expect(screen.getByText(/Runbook revision 4/i)).toBeInTheDocument();
  });

  it("loads a v2 Run through native-ready GET and does not PUT seed progress", async () => {
    const seeded = mockV2PlayRun({ current_beat_id: "beat:one", current_scene_id: null });
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-current-moment-cockpit")).toBeInTheDocument();
    expect(screen.queryByText("v2 Run READY")).not.toBeInTheDocument();
    expect(screen.getByTestId("play-current-beat")).toHaveTextContent("Beat 1");
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("No Scene is current");
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(PLAY_RUN_ID, { ensureNativeReady: true });
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
    expect(seeded.progress.current_beat_id).toBe("beat:one");
  });

  it("does not reseed a v2 Run that already has a durable current Beat", async () => {
    mockV2PlayRun({ current_beat_id: "beat:two", current_scene_id: null });
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-current-moment-cockpit")).toBeInTheDocument();
    expect(screen.getByTestId("play-current-beat")).toHaveTextContent("Beat 2");
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(PLAY_RUN_ID, { ensureNativeReady: true });
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
  });

  it("does not PUT seed progress when native-ready GET already returns a current Beat", async () => {
    mockV2PlayRun({ current_beat_id: "beat:one", current_scene_id: null });
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-current-moment-cockpit")).toBeInTheDocument();
    expect(screen.getByTestId("play-current-beat")).toHaveTextContent("Beat 1");
    expect(liveApi.getPlayRun).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(PLAY_RUN_ID, { ensureNativeReady: true });
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
  });

  it("does not seed when native-ready GET refuses a mismatched v2 authority set", async () => {
    vi.mocked(liveApi.getPlayRun).mockRejectedValue(
      new liveApi.LiveApiError(
        "sealed v2 manifest disagrees with pinned WorkRevision on Beat kind or membership",
        422,
      ),
    );
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-status-integrity_failure")).toBeInTheDocument();
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(PLAY_RUN_ID, { ensureNativeReady: true });
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
    expect(screen.queryByTestId("play-current-moment-cockpit")).not.toBeInTheDocument();
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
  });

  it("admits the Run returned by native-ready GET after a rebase, without a seed PUT", async () => {
    const empty = mockV2PlayRun();
    const rebasedMarkdown = [
      "<!-- dmb-playable-element:v2 kind=beat id=beat:rebased beat_kind=spine -->",
      "## Rebased",
      "",
    ].join("\n");
    const rebasedRun = {
      ...empty,
      playable_revision: 4,
      playable_content_sha256: PLAY_SHA_R4,
      run_revision: 7,
      progress: {
        ...empty.progress,
        current_beat_id: "beat:rebased",
        current_scene_id: null,
      },
    };
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(rebasedRun);
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockResolvedValue({
      ...v2Manifest(),
      playable_revision: 4,
      playable_content_sha256: PLAY_SHA_R4,
      beats: [{ beat_id: "beat:rebased", beat_kind: "spine" as const }],
      scenes: [],
      choices: [],
      options: [],
      edges: [],
    });
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockResolvedValue(
      playCommittedRevision({
        markdown: rebasedMarkdown,
        revision_n: 4,
        object_revision: 4,
        content_sha256: PLAY_SHA_R4,
      }),
    );
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-current-moment-cockpit")).toBeInTheDocument();
    expect(screen.getByTestId("play-current-beat")).toHaveTextContent("Rebased");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
    expect(liveApi.getPlayRun).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(PLAY_RUN_ID, { ensureNativeReady: true });
    expect(liveApi.getPlayRunReferenceManifest).toHaveBeenCalledTimes(1);
    expect(liveApi.getCommittedWorkspaceRevision).toHaveBeenCalledTimes(1);
    expect(vi.mocked(liveApi.getCommittedWorkspaceRevision).mock.calls[0]?.[1]).toBe(4);
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
  });

  it("reflects Make Current from the returned authoritative v2 Run", async () => {
    const user = userEvent.setup();
    const seeded = mockV2PlayRun({ current_beat_id: "beat:one", current_scene_id: null });
    const madeCurrent = {
      ...seeded,
      run_revision: seeded.run_revision + 1,
      progress: {
        ...seeded.progress,
        current_beat_id: "beat:one",
        current_scene_id: "scene:a",
      },
    };
    vi.mocked(liveApi.putPlayRunProgress).mockResolvedValue(madeCurrent);
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-workspace-beat-only")).toBeInTheDocument();
    expect(screen.queryByText("v2 Run READY")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Make Scene A current" }));
    expect(await screen.findByTestId("play-workspace-current")).toHaveTextContent("Scene A unique body.");
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("Scene A");
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[1]).toEqual({
      expected_run_revision: seeded.run_revision,
      progress: expect.objectContaining({
        current_beat_id: "beat:one",
        current_scene_id: "scene:a",
      }),
    });
    expect(screen.queryByTestId("runbook-table-deck")).not.toBeInTheDocument();
  });

});
