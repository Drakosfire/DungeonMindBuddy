import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import * as liveApi from "../api/liveApi";
import { ProjectionSurfacePublisher } from "../planSurface/projection/projectionTestHost";
import { BuildSurfacePage } from "./BuildSurfacePage";
import { dispatchBuildFindExisting } from "./buildFindExisting";

const mockOpenGraphReference = vi.fn();

vi.mock("../planSurface/projection/projectionContext", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../planSurface/projection/projectionContext")>();
  let realOpenGraphReference: ReturnType<typeof mod.useProjection>["openGraphReference"] | null = null;
  function stableOpenGraphReference(
    ...args: Parameters<NonNullable<typeof realOpenGraphReference>>
  ) {
    mockOpenGraphReference(...args);
    return realOpenGraphReference!(...args);
  }
  return {
    ...mod,
    useProjection: () => {
      const value = mod.useProjection();
      realOpenGraphReference = value.openGraphReference;
      return {
        ...value,
        openGraphReference: stableOpenGraphReference,
      };
    },
  };
});

const DOC_ID = "11111111-1111-4111-8111-111111111111";

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

function BuildGraphReferenceHarness() {
  return (
    <AgentInteractionProvider>
      <BuildSurfacePage />
    </AgentInteractionProvider>
  );
}

describe("Build graph reference", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Build Lore",
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
      markdown: "# Build Lore\n",
      content_sha256: "sha-build",
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: 1,
    });
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(projectionWithNode as never);
  });

  it("renders GraphReferenceSearch in the Edit dock when a document is loaded", async () => {
    render(<BuildGraphReferenceHarness />);

    await waitFor(() => {
      expect(screen.getByLabelText("Find objects")).toBeInTheDocument();
    });
  });

  it("inserts a graph reference chip into the Build editor", async () => {
    const user = userEvent.setup();
    render(<BuildGraphReferenceHarness />);

    await waitFor(() => {
      expect(screen.getByLabelText("Find objects")).toBeInTheDocument();
    });

    const insertBtn = await screen.findByRole("button", { name: "Insert chip" });
    await waitFor(() => {
      expect(insertBtn).toBeEnabled();
    });

    const canvas = screen.getByTestId("build-markdown-editor");
    const before = canvas.querySelectorAll("[data-md-ref-id='npc:glowkindle']").length;
    await user.click(insertBtn);

    await waitFor(() => {
      const after = canvas.querySelectorAll("[data-md-ref-id='npc:glowkindle']").length;
      expect(after).toBeGreaterThan(before);
    });
  });

  it("routes graph object view through useProjection().openGraphReference", async () => {
    const user = userEvent.setup();
    mockOpenGraphReference.mockClear();

    render(<BuildGraphReferenceHarness />);

    await waitFor(() => {
      expect(screen.getByLabelText("Find objects")).toBeInTheDocument();
    });

    const viewBtn = await screen.findByRole("button", { name: "View" });
    await user.click(viewBtn);

    await waitFor(() => {
      expect(mockOpenGraphReference).toHaveBeenCalled();
    });
  });

  it("seeds Edit dock graph search from dmb-build-find-existing", async () => {
    render(<BuildGraphReferenceHarness />);

    await waitFor(() => {
      expect(screen.getByLabelText("Find objects")).toBeInTheDocument();
    });

    dispatchBuildFindExisting({ query: "Glowkindle", kindHint: "npc" });

    await waitFor(() => {
      expect(screen.getByLabelText("Find objects")).toHaveValue("Glowkindle");
    });
  });
});
