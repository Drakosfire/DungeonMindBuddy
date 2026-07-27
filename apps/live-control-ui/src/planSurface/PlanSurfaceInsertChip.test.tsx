import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppChrome, type AppChromeTools } from "../chrome/AppChrome";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import * as liveApi from "../api/liveApi";
import type { WorkspaceDocumentSnapshot } from "../api/types";
import { fixtureWorkspaceDocumentRecord } from "./config/planSessionDescriptor";
import { mockPlanView } from "../test/fixtures";
import { PlanSurfaceShell } from "./PlanSurfaceShell";
import { ProjectionProvider } from "./projection/projectionContext";

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

const projectionWithNode = {
  schema: "dmb_world_graph_projection_v1" as const,
  snapshot: {
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
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
    },
  ],
  relationships: [],
  attributes: [],
  evidence: [],
  sourceArtifacts: [],
  diagnostics: [],
};

function Harness() {
  const [editorTools, setEditorTools] = useState<AppChromeTools | null>(null);
  return (
    <AgentInteractionProvider>
      <ProjectionProvider>
        <AppChrome activeRoute="plan" editorTools={editorTools} editToolboxLayout="dock">
          <PlanSurfaceShell planView={mockPlanView} onEditorToolsChange={setEditorTools} />
        </AppChrome>
      </ProjectionProvider>
    </AgentInteractionProvider>
  );
}

describe("Plan surface insert chip", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(projectionWithNode as never);
    vi.spyOn(liveApi, "getSourceBundle").mockResolvedValue({
      schema_version: "dmb_ingestion_source_bundle_v1",
      bundle_id: "insert-chip-bundle",
      scope: "campaign-ingested",
      corpus_root: "corpus",
      artifacts: [],
      anchors: [],
      units: [],
      coverage: {},
      diagnostics: [],
    });
    vi.spyOn(liveApi, "listWorkspaceDocuments").mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [fixtureWorkspaceDocumentRecord()],
    });
    vi.spyOn(liveApi, "getWorkspaceDocument").mockResolvedValue(fixtureWorkspaceDocumentRecord());
    vi.spyOn(liveApi, "getWorkspaceDocumentSnapshot").mockResolvedValue(fixtureWorkspaceDocumentSnapshot());
    localStorage.clear();
    window.history.pushState({}, "", "/plan");
  });

  it("unlocks editing and inserts a graph-node chip into the canvas", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await waitFor(() => {
      expect(screen.getByLabelText("Find objects")).toBeInTheDocument();
    });

    const insertBtn = await screen.findByRole("button", { name: "Insert chip" });
    expect(insertBtn).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /Unlock editing/i }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Insert chip" })).toBeEnabled();
    });

    const canvas = screen.getByTestId("plan-surface-canvas-editor");
    const before = canvas.querySelectorAll("[data-md-ref-id='npc:glowkindle']").length;
    await user.click(screen.getByRole("button", { name: "Insert chip" }));

    await waitFor(() => {
      const after = canvas.querySelectorAll("[data-md-ref-id='npc:glowkindle']").length;
      expect(after).toBeGreaterThan(before);
    });

    expect(within(canvas).getByText("Glowkindle")).toBeInTheDocument();
  });
});
