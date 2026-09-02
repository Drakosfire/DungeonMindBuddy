import { act, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import * as liveApi from "../api/liveApi";
import { LiveApiError } from "../api/liveApi";
import type { WorldGraphProjection, WorkspaceDocumentSnapshot } from "../api/types";
import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import {
  WorldGraphLensProjectionProvider,
  WorldGraphLensProvider,
} from "../graphLens";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { fixtureWorkspaceDocumentRecord } from "./config/planSessionDescriptor";
import { mockPlanView, mockSourceBundle } from "../test/fixtures";
import { PlanSurfaceShell } from "./PlanSurfaceShell";

vi.mock("./config/planSessionDescriptor", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./config/planSessionDescriptor")>();
  return {
    ...actual,
    resolvePlanningDocument: vi.fn(async () => actual.fixturePlanDocumentDescriptor()),
  };
});

function fixtureWorkspaceDocumentSnapshot(
  overrides: Partial<WorkspaceDocumentSnapshot> = {},
): WorkspaceDocumentSnapshot {
  const record = fixtureWorkspaceDocumentRecord();
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

const glowkindleNode = {
  nodeId: "npc:glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  anchoredToFocusSession: true,
  summary: "A friendly merchant.",
  campaignScope: "longmont-c2",
  evidenceRefIds: [],
  sourceArtifactIds: [],
};

function projection(
  snapshotOverrides: Partial<WorldGraphProjection["snapshot"]> = {},
  nodes: WorldGraphProjection["nodes"] = [],
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev-1",
      headRevisionId: "rev-1",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "campaign",
      ...snapshotOverrides,
    },
    summary: {
      nodeCount: nodes.length,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      projectionTruncated: false,
    },
    nodes,
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
  };
}

function Harness({
  onEditorToolsChange,
}: {
  onEditorToolsChange: (tools: AppChromeToolsGeneration | null) => void;
}) {
  const [editorTools, setEditorTools] = useState<AppChromeToolsGeneration | null>(null);
  return (
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        <WorldGraphLensProvider planCampaignId="longmont-c2">
          <WorldGraphLensProjectionProvider defaultCampaignId="longmont-c2">
            <SurfaceContextProvider>
              <AppChrome activeRoute="plan" editorTools={editorTools} editToolboxLayout="dock">
                <PlanSurfaceShell
                  planView={mockPlanView}
                  onEditorToolsChange={(tools) => {
                    onEditorToolsChange(tools);
                    setEditorTools(tools);
                  }}
                />
              </AppChrome>
            </SurfaceContextProvider>
          </WorldGraphLensProjectionProvider>
        </WorldGraphLensProvider>
      </AskPluginSlotProvider>
    </AgentInteractionProvider>
  );
}

describe("PlanSurfaceGraphInformation integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(liveApi, "getSourceBundle").mockResolvedValue(mockSourceBundle);
    vi.spyOn(liveApi, "listWorkspaceDocuments").mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [fixtureWorkspaceDocumentRecord()],
    });
    vi.spyOn(liveApi, "getWorkspaceDocument").mockResolvedValue(fixtureWorkspaceDocumentRecord());
    vi.spyOn(liveApi, "getWorkspaceDocumentSnapshot").mockResolvedValue(
      fixtureWorkspaceDocumentSnapshot(),
    );
    localStorage.clear();
    window.history.pushState({}, "", "/plan");
  });

  it("updates the mounted Edit World Graph objects panel without graph-driven editorTools republication", async () => {
    let resolveProjection!: (value: WorldGraphProjection) => void;
    const deferred = new Promise<WorldGraphProjection>((resolve) => {
      resolveProjection = resolve;
    });
    vi.spyOn(liveApi, "postWorldGraphProjection").mockReturnValue(deferred);
    const publications = vi.fn();

    render(<Harness onEditorToolsChange={publications} />);

    await waitFor(() => {
      expect(screen.getByText("Loading World Graph projection…")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Unlock editing/i })).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByTestId("plan-world-graph-objects-panel")).toHaveAttribute(
        "data-status",
        "loading",
      );
    });

    const panel = screen.getByTestId("plan-world-graph-objects-panel");
    const publicationsBeforeResolve = publications.mock.calls.length;
    publications.mockClear();

    await act(async () => {
      resolveProjection(projection({}, [glowkindleNode]));
    });

    await waitFor(() => {
      expect(screen.getByText("Glowkindle")).toBeInTheDocument();
    });
    expect(screen.getByTestId("plan-world-graph-objects-panel")).toBe(panel);
    expect(screen.getByTestId("plan-world-graph-objects-panel")).toHaveAttribute(
      "data-status",
      "ready",
    );
    expect(publications).not.toHaveBeenCalled();
    expect(publicationsBeforeResolve).toBeGreaterThan(0);
  });

  it("renders verified zero-node projections as EMPTY, not unavailable or integrity error", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(projection());
    render(<Harness onEditorToolsChange={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("No nodes in the current projection.")).toBeInTheDocument();
    });
    expect(screen.getByTestId("plan-world-graph-objects-panel")).toHaveAttribute(
      "data-status",
      "empty",
    );
    expect(screen.queryByText("World Graph unavailable for this session.")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders authority outages as UNAVAILABLE without retaining prior READY objects", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockRejectedValue(
      new LiveApiError("World Graph unavailable", 404, { code: "world_graph_unavailable" }),
    );
    render(<Harness onEditorToolsChange={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("World Graph unavailable for this session.")).toBeInTheDocument();
    });
    expect(screen.getByTestId("plan-world-graph-objects-panel")).toHaveAttribute(
      "data-status",
      "unavailable",
    );
    expect(screen.queryByText("Glowkindle")).not.toBeInTheDocument();
  });

  it("renders verification failures as INTEGRITY_ERROR, not EMPTY", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(
      projection({ campaignId: "longmont-c1" }, [glowkindleNode]),
    );
    render(<Harness onEditorToolsChange={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.getByTestId("plan-world-graph-objects-panel")).toHaveAttribute(
      "data-status",
      "integrity_error",
    );
    expect(screen.queryByText("No nodes in the current projection.")).not.toBeInTheDocument();
    expect(screen.queryByText("Glowkindle")).not.toBeInTheDocument();
  });
});
