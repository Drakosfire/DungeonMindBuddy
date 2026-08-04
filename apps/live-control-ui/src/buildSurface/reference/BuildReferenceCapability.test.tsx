import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider, useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import * as liveApi from "../../api/liveApi";
import type { GraphProjectionNodeView } from "../../api/types";
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import { MarkdownCanvasSessionProvider } from "../../markdownCanvas/MarkdownCanvasSession";
import { LegacyProjectionHostAdapter } from "../../planSurface/projection/LegacyProjectionHostAdapter";
import { ToolHost } from "../../surfaceInteraction/toolHost/ToolHost";
import { BUILD_MARKDOWN_CANVAS } from "../buildMarkdownCanvasAdapter";
import { BUILD_SAVE_CONFLICTS_WITH } from "../buildDocumentCommands";
import type { BuildReferenceContextBinding } from "./buildBuildSurfaceInteractionPublication";
import { BUILD_FIND_EXISTING_TOOL_ID, BUILD_REFERENCE_CONTEXT_BINDING_ID } from "./buildReferenceIds";
import { BuildReferenceCapability } from "./BuildReferenceCapability";

const DOC_ID = "11111111-1111-4111-8111-111111111111";

function PublicationProbe() {
  const { surfaceInteractionPublication } = useAgentInteraction();
  const toolIds = surfaceInteractionPublication?.tools.map((tool) => tool.id) ?? [];
  return (
    <p data-testid="build-publication-tools">{toolIds.length ? toolIds.join(",") : "none"}</p>
  );
}

function ReferenceContextProbe({
  onContext,
}: {
  onContext: (context: BuildReferenceContextBinding | null) => void;
}) {
  const { surfaceInteractionPublication } = useAgentInteraction();
  const binding = surfaceInteractionPublication?.projectionBindings.find(
    (entry) => entry.id === BUILD_REFERENCE_CONTEXT_BINDING_ID,
  );
  onContext((binding?.value as BuildReferenceContextBinding | undefined) ?? null);
  return null;
}

vi.mock("../../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    postWorldGraphProjection: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
  };
});

function snapshotFixture(documentId: string = DOC_ID, campaignId = "eldyrwild") {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1" as const,
    record: {
      schema_version: "dmb_workspace_document_record_v1" as const,
      document_id: documentId,
      title: "Faction Notes",
      campaign_id: campaignId,
      target_session: null,
      kind: "worldbuilding_source" as const,
      target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
      status: "active" as const,
      content_status: "draft" as const,
      revision: 1,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding" as const,
      document_class: "faction" as const,
      authority_state: "draft" as const,
      visibility_state: "internal" as const,
    },
    markdown: "",
    content_sha256: "sha-empty",
    file_fingerprint: "absent" as const,
    file_exists: false,
    loaded_revision: 1,
  };
}

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

const innNode = {
  nodeId: "location-inn",
  label: "Inn",
  kind: "location",
  role: "location",
  aliases: ["The Inn"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: [],
  sourceArtifactIds: [],
  anchoredToFocusSession: true,
  summary: "Meeting place.",
};

function graphProjectionFixture() {
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
      nodeCount: 2,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      projectionTruncated: false,
    },
    nodes: [glowkindleNode, innNode],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
  };
}

function searchItemFromApiNode(node: typeof glowkindleNode): {
  nodeId: string;
  label: string;
  nodeView: GraphProjectionNodeView;
} {
  const nodeView: GraphProjectionNodeView = {
    node_id: node.nodeId,
    label: node.label,
    kind: node.kind,
    role: node.role,
    aliases: node.aliases,
    source_domains: node.sourceDomains,
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: node.anchoredToFocusSession,
    summary: node.summary,
  };
  return {
    nodeId: node.nodeId,
    label: node.label,
    nodeView,
  };
}

describe("BuildReferenceCapability", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}`);
  });

  it("publishes empty tools without a markdown canvas session", () => {
    render(
      <AgentInteractionProvider>
        <BuildReferenceCapability documentId={null} />
        <PublicationProbe />
      </AgentInteractionProvider>,
    );

    expect(document.querySelector('[data-testid="build-publication-tools"]')).toHaveTextContent("none");
  });

  it("publishes Find existing tool when session is accepted", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_ID}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_ID} />
          <PublicationProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(document.querySelector('[data-testid="build-publication-tools"]')).toHaveTextContent(
        BUILD_FIND_EXISTING_TOOL_ID,
      );
    });
  });

  it("selectCampaign updates URL campaign param while preserving documentId", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    let latestContext: BuildReferenceContextBinding | null = null;

    render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_ID}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_ID} />
          <ReferenceContextProbe onContext={(context) => { latestContext = context; }} />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestContext).not.toBeNull());
    latestContext!.selectCampaign("longmont-c1");

    await waitFor(() => {
      const params = new URLSearchParams(window.location.search);
      expect(params.get("documentId")).toBe(DOC_ID);
      expect(params.get("campaign")).toBe("longmont-c1");
    });
  });

  it("viewExact opens graph reference for the exact selected node id", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    let latestContext: BuildReferenceContextBinding | null = null;

    function ActiveGraphReferenceProbe() {
      const { activeGraphReference } = useAgentInteraction();
      return (
        <p data-testid="active-graph-node-id">
          {activeGraphReference?.kind === "resolved_graph" ? activeGraphReference.graphNodeId : "none"}
        </p>
      );
    }

    render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_ID}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_ID} />
          <ReferenceContextProbe onContext={(context) => { latestContext = context; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestContext?.items.length).toBe(2));

    const first = searchItemFromApiNode(glowkindleNode);
    const second = searchItemFromApiNode(innNode);

    latestContext!.viewExact({
      nodeId: first.nodeId,
      label: first.label,
      kind: "npc",
      role: "merchant",
      summary: "A friendly merchant.",
      aliases: ["Glow"],
      scopeLabel: "longmont-c1",
      reference: referenceFromGraphNode(first.nodeView),
      nodeView: first.nodeView,
    });
    await waitFor(() => {
      expect(document.querySelector('[data-testid="active-graph-node-id"]')).toHaveTextContent("npc-glowkindle");
    });

    latestContext!.viewExact({
      nodeId: second.nodeId,
      label: second.label,
      kind: "location",
      role: "location",
      summary: "Meeting place.",
      aliases: ["The Inn"],
      scopeLabel: "longmont-c1",
      reference: referenceFromGraphNode(second.nodeView),
      nodeView: second.nodeView,
    });
    await waitFor(() => {
      expect(document.querySelector('[data-testid="active-graph-node-id"]')).toHaveTextContent("location-inn");
    });
  });

  it("rejects viewExact for a node absent from the current ready results", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFixture(DOC_ID, "longmont-c1"),
    );
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    let latestContext: BuildReferenceContextBinding | null = null;

    function ActiveGraphReferenceProbe() {
      const { activeGraphReference } = useAgentInteraction();
      return (
        <p data-testid="active-graph-node-id">
          {activeGraphReference?.kind === "resolved_graph" ? activeGraphReference.graphNodeId : "none"}
        </p>
      );
    }

    render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_ID}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_ID} />
          <ReferenceContextProbe onContext={(context) => { latestContext = context; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestContext?.projectionState).toBe("ready"));

    const stale = searchItemFromApiNode({
      ...glowkindleNode,
      nodeId: "npc-stale-from-prior-lens",
      label: "Stale",
    });
    latestContext!.viewExact({
      nodeId: stale.nodeId,
      label: stale.label,
      kind: "npc",
      role: "merchant",
      summary: null,
      aliases: [],
      scopeLabel: "longmont-c1",
      reference: referenceFromGraphNode(stale.nodeView),
      nodeView: stale.nodeView,
    });

    expect(document.querySelector('[data-testid="active-graph-node-id"]')).toHaveTextContent("none");
  });

  it("clears open object content when the graph-reference binding is replaced after a lens change", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFixture(DOC_ID, "eldyrwild"),
    );
    vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce(graphProjectionFixture())
      .mockResolvedValueOnce({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          campaignId: "longmont-c2",
          revisionId: "rev-c2",
          headRevisionId: "rev-c2",
        },
        nodes: [innNode],
      });

    let latestContext: BuildReferenceContextBinding | null = null;

    function ActiveProbe() {
      const { active, activeGraphReference } = useAgentInteraction();
      return (
        <p data-testid="active-probe">
          {active?.kind ?? "none"}|{activeGraphReference?.kind === "resolved_graph" ? activeGraphReference.graphNodeId : "none"}
        </p>
      );
    }

    render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_ID}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_ID} />
          <ReferenceContextProbe onContext={(context) => { latestContext = context; }} />
          <ActiveProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestContext?.items.length).toBe(2));
    const first = searchItemFromApiNode(glowkindleNode);
    latestContext!.viewExact({
      nodeId: first.nodeId,
      label: first.label,
      kind: "npc",
      role: "merchant",
      summary: "A friendly merchant.",
      aliases: ["Glow"],
      scopeLabel: "longmont-c1",
      reference: referenceFromGraphNode(first.nodeView),
      nodeView: first.nodeView,
    });
    await waitFor(() => {
      expect(screen.getByTestId("active-probe")).toHaveTextContent("content|npc-glowkindle");
    });

    latestContext!.selectCampaign("longmont-c2");

    await waitFor(() => {
      expect(screen.getByTestId("active-probe")).toHaveTextContent("none|none");
    });
    await waitFor(() => {
      expect(latestContext?.lens.status).toBe("ready");
      expect(latestContext?.lens.status === "ready" && latestContext.lens.campaignId).toBe("longmont-c2");
    });
    await waitFor(() => expect(latestContext?.projectionState).toBe("ready"));
    // Replacement binding must not resurrect the prior object under the new lens.
    expect(screen.getByTestId("active-probe")).toHaveTextContent("none|none");
  });

  it("E2E: ToolHost Find existing → search → View → object content renderer", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFixture(DOC_ID, "longmont-c1"),
    );
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_ID}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_ID} />
        </MarkdownCanvasSessionProvider>
        <ToolHost />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProvider>,
    );

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
    const navButton = within(host as HTMLElement).getByRole("button", { name: "Find existing object" });
    expect(navButton).toHaveAttribute("aria-pressed", "true");

    await user.type(screen.getByLabelText("Find objects"), "glow");
    await user.click(screen.getByRole("button", { name: "View" }));

    await waitFor(() => {
      expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    });
    expect(within(screen.getByTestId("graph-object-projection-card")).getByText("Glowkindle")).toBeInTheDocument();
  });
});
