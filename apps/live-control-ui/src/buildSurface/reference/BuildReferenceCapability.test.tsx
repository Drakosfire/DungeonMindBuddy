import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Editor } from "@tiptap/react";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider, useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import * as liveApi from "../../api/liveApi";
import type { GraphProjectionNodeView } from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import {
  __resetGraphNodeChipRuntimeForTests,
  useGraphNodeChipRuntime,
} from "../../graphReference/GraphNodeChipRuntime";
import {
  GRAPH_REFERENCE_BINDING_ID,
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
} from "../../graphReference/projectionBindings";
import { referenceAttrsWithExactScope } from "../../graphReference/scopedGraphReference";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceResolution,
} from "../../graphReference/types";
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import {
  MarkdownCanvasSessionProvider,
  useMarkdownCanvasSession,
} from "../../markdownCanvas/MarkdownCanvasSession";
import { LegacyProjectionHostAdapter } from "../../planSurface/projection/LegacyProjectionHostAdapter";
import { ToolHost } from "../../surfaceInteraction/toolHost/ToolHost";
import { BUILD_MARKDOWN_CANVAS } from "../buildMarkdownCanvasAdapter";
import { BUILD_DOCUMENT_SAVE_COMMAND_ID, BUILD_SAVE_CONFLICTS_WITH } from "../buildDocumentCommands";
import type { BuildReferenceContextBinding } from "./buildBuildSurfaceInteractionPublication";
import { BUILD_FIND_EXISTING_TOOL_ID, BUILD_REFERENCE_CONTEXT_BINDING_ID } from "./buildReferenceIds";
import { BuildReferenceCapability } from "./BuildReferenceCapability";
import { BuildReferenceObjectProjection } from "./BuildReferenceObjectProjection";

const DOC_B = "22222222-2222-4222-8222-222222222222";

const DOC_ID = "11111111-1111-4111-8111-111111111111";

const innAdjacency = {
  edgeId: "edge-inn",
  nodeId: "location-inn",
  label: "The Inn",
  kind: "location",
  predicate: "located_in",
  direction: "outgoing" as const,
  anchoredToFocusSession: true,
  sourceDomains: ["recap"],
  evidenceRefIds: [] as string[],
  sessionIds: [] as string[],
  campaignScope: "longmont-c1",
};

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
  const context = (binding?.value as BuildReferenceContextBinding | undefined) ?? null;
  onContext(context);
  return (
    <span
      data-testid="build-reference-context-insertion-error"
      data-error={context?.insertionError ?? ""}
    />
  );
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
  adjacency: [innAdjacency],
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

function graphScopeFromProjectionFixture() {
  const { snapshot } = graphProjectionFixture();
  return {
    worldId: snapshot.worldId,
    campaignId: snapshot.campaignId,
    scopeMode: snapshot.scopeMode,
    revisionId: snapshot.revisionId,
  };
}

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

function createInsertEditor() {
  const run = vi.fn(() => true);
  const chain = {
    focus: vi.fn().mockReturnThis(),
    insertRunbookReference: vi.fn().mockReturnThis(),
    run,
  };
  const editor = {
    getJSON: vi.fn(() => ({
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "Session Doc" }] }],
    })),
    chain: vi.fn(() => chain),
  } as unknown as Editor & { chain: ReturnType<typeof vi.fn> };
  return { editor, chain, run };
}

function ChipRuntimeProbe({ onRuntime }: { onRuntime: (runtime: ReturnType<typeof useGraphNodeChipRuntime>) => void }) {
  const runtime = useGraphNodeChipRuntime();
  onRuntime(runtime);
  return null;
}

describe("BuildReferenceCapability", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    __resetGraphNodeChipRuntimeForTests();
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

  it("rejects viewExact retained from current-head after switching to pinned revision id head", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFixture(DOC_ID, "longmont-c1"),
    );
    let resolvePinned!: (value: ReturnType<typeof graphProjectionFixture>) => void;
    const pinnedDeferred = new Promise<ReturnType<typeof graphProjectionFixture>>((resolve) => {
      resolvePinned = resolve;
    });
    const postSpy = vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce(graphProjectionFixture())
      .mockImplementationOnce(() => pinnedDeferred);

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
    const headViewExact = latestContext!.viewExact;
    const headLoadKey = JSON.stringify([
      latestContext!.documentId,
      latestContext!.requestedRevisionId,
      latestContext!.loadedRevisionId,
      latestContext!.projectionState,
    ]);
    const first = searchItemFromApiNode(glowkindleNode);
    expect(postSpy).toHaveBeenCalledTimes(1);

    window.history.replaceState(
      {},
      "",
      `/build?documentId=${DOC_ID}&campaign=longmont-c1&graphRevision=head`,
    );
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() => {
      expect(latestContext?.requestedRevisionId).toBe("head");
      expect(latestContext?.projectionState).toBe("loading");
      expect(latestContext?.items).toEqual([]);
    });
    expect(postSpy).toHaveBeenCalledTimes(2);
    expect(postSpy.mock.calls[1]?.[0]).toEqual(
      expect.objectContaining({ revisionPin: "head" }),
    );

    headViewExact({
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
    expect(document.querySelector('[data-testid="active-graph-node-id"]')).toHaveTextContent("none");

    await act(async () => {
      resolvePinned({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          revisionId: "head",
          headRevisionId: "rev-1",
          isHead: false,
        },
      });
      await pinnedDeferred;
    });

    await waitFor(() => expect(latestContext?.projectionState).toBe("ready"));
    expect(latestContext?.loadedRevisionId).toBe("head");
    expect(JSON.stringify([
      latestContext!.documentId,
      latestContext!.requestedRevisionId,
      latestContext!.loadedRevisionId,
      latestContext!.projectionState,
    ])).not.toBe(headLoadKey);
    expect(document.querySelector('[data-testid="active-graph-node-id"]')).toHaveTextContent("none");
  });

  it("E9: rejects delayed relationship completion after document replacement", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id: string) =>
      snapshotFixture(id, "longmont-c1"),
    );
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    let latestContext: BuildReferenceContextBinding | null = null;
    let latestBinding: GraphReferenceProjectionBinding | null = null;
    let lastSeenBinding: GraphReferenceProjectionBinding | null = null;
    let openResolvedReferenceCalls = 0;
    let retainedResolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }> | null = null;

    function Probes() {
      const { graphReferenceBinding, activeGraphReference } = useAgentInteraction();
      latestBinding = graphReferenceBinding;
      if (graphReferenceBinding) {
        lastSeenBinding = graphReferenceBinding;
      }
      if (activeGraphReference?.kind === "resolved_graph") {
        retainedResolution = activeGraphReference;
      }
      // Keep one ObjectProjection instance mounted across the binding gap so the
      // pending await can observe bindingAtStart !== current after replacement.
      const resolution = retainedResolution;
      const bindingForCard = graphReferenceBinding ?? lastSeenBinding;
      if (!resolution || !bindingForCard) {
        return (
          <p data-testid="active-graph-node-id">
            {activeGraphReference?.kind === "resolved_graph" ? activeGraphReference.graphNodeId : "none"}
          </p>
        );
      }
      return (
        <>
          <p data-testid="active-graph-node-id">
            {activeGraphReference?.kind === "resolved_graph" ? activeGraphReference.graphNodeId : "none"}
          </p>
          <BuildReferenceObjectProjection
            bindings={{
              [GRAPH_REFERENCE_RESOLUTION_BINDING_ID]: resolution,
              [GRAPH_REFERENCE_BINDING_ID]: bindingForCard,
            }}
          />
        </>
      );
    }

    function DocumentHarness({ documentId }: { documentId: string }) {
      return (
        <MarkdownCanvasSessionProvider
          key={documentId}
          documentId={documentId}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={documentId} />
          <ReferenceContextProbe onContext={(context) => { latestContext = context; }} />
        </MarkdownCanvasSessionProvider>
      );
    }

    const { rerender } = render(
      <AgentInteractionProvider>
        <DocumentHarness documentId={DOC_ID} />
        <Probes />
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestContext?.items.length).toBe(2));
    await waitFor(() => expect(latestBinding).not.toBeNull());
    const glowItem = latestContext!.items.find((item) => item.nodeId === "npc-glowkindle");
    expect(glowItem).toBeTruthy();
    latestContext!.viewExact(glowItem!);

    await waitFor(() => {
      expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
      expect(screen.getByTestId("active-graph-node-id")).toHaveTextContent("npc-glowkindle");
    });

    const bindingAtStart = latestBinding!;
    let resolveDeferred!: (value: GraphReferenceResolution) => void;
    const deferred = new Promise<GraphReferenceResolution>((resolve) => {
      resolveDeferred = resolve;
    });
    const originalOpen = bindingAtStart.openResolvedReference.bind(bindingAtStart);
    bindingAtStart.resolveRelationship = vi.fn(async () => deferred);
    bindingAtStart.openResolvedReference = ((resolution, state) => {
      openResolvedReferenceCalls += 1;
      originalOpen(resolution, state);
    }) as GraphReferenceProjectionBinding["openResolvedReference"];

    await user.click(screen.getByRole("button", { name: /Open related object .*The Inn/i }));
    await waitFor(() => expect(bindingAtStart.resolveRelationship).toHaveBeenCalledTimes(1));

    window.history.replaceState({}, "", `/build?documentId=${DOC_B}&campaign=longmont-c1`);
    rerender(
      <AgentInteractionProvider>
        <DocumentHarness documentId={DOC_B} />
        <Probes />
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(latestContext?.documentId).toBe(DOC_B);
    });
    await waitFor(() => {
      expect(latestBinding).not.toBeNull();
      expect(latestBinding).not.toBe(bindingAtStart);
    });
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    });

    const innView = searchItemFromApiNode(innNode).nodeView;
    await act(async () => {
      resolveDeferred({
        kind: "resolved_graph",
        locator: "dmb-node:location-inn",
        reference: referenceFromGraphNode(innView),
        graphNodeId: "location-inn",
        graphObject: buildGraphObjectCardFromNodeView(innView),
        graphScope: graphScopeFromProjectionFixture(),
        projectionState: "ready",
        message: "Resolved graph node Inn.",
      });
      await deferred;
    });

    expect(openResolvedReferenceCalls).toBe(0);
    expect(screen.queryByTestId("active-graph-node-id")?.textContent).not.toBe("location-inn");
  });

  it("E10: rejects delayed relationship completion after same-document lens replacement", async () => {
    const user = userEvent.setup();
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
    let latestBinding: GraphReferenceProjectionBinding | null = null;
    let lastSeenBinding: GraphReferenceProjectionBinding | null = null;
    let openResolvedReferenceCalls = 0;
    let retainedResolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }> | null = null;

    function Probes() {
      const { graphReferenceBinding, activeGraphReference } = useAgentInteraction();
      latestBinding = graphReferenceBinding;
      if (graphReferenceBinding) {
        lastSeenBinding = graphReferenceBinding;
      }
      if (activeGraphReference?.kind === "resolved_graph") {
        retainedResolution = activeGraphReference;
      }
      const resolution = retainedResolution;
      const bindingForCard = graphReferenceBinding ?? lastSeenBinding;
      if (!resolution || !bindingForCard) {
        return (
          <p data-testid="active-graph-node-id">
            {activeGraphReference?.kind === "resolved_graph" ? activeGraphReference.graphNodeId : "none"}
          </p>
        );
      }
      return (
        <>
          <p data-testid="active-graph-node-id">
            {activeGraphReference?.kind === "resolved_graph" ? activeGraphReference.graphNodeId : "none"}
          </p>
          <BuildReferenceObjectProjection
            bindings={{
              [GRAPH_REFERENCE_RESOLUTION_BINDING_ID]: resolution,
              [GRAPH_REFERENCE_BINDING_ID]: bindingForCard,
            }}
          />
        </>
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
        </MarkdownCanvasSessionProvider>
        <Probes />
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestContext?.items.length).toBe(2));
    await waitFor(() => expect(latestBinding).not.toBeNull());
    const glowItem = latestContext!.items.find((item) => item.nodeId === "npc-glowkindle");
    expect(glowItem).toBeTruthy();
    latestContext!.viewExact(glowItem!);

    await waitFor(() => {
      expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
      expect(screen.getByTestId("active-graph-node-id")).toHaveTextContent("npc-glowkindle");
    });

    const bindingAtStart = latestBinding!;
    let resolveDeferred!: (value: GraphReferenceResolution) => void;
    const deferred = new Promise<GraphReferenceResolution>((resolve) => {
      resolveDeferred = resolve;
    });
    const originalOpen = bindingAtStart.openResolvedReference.bind(bindingAtStart);
    bindingAtStart.resolveRelationship = vi.fn(async () => deferred);
    bindingAtStart.openResolvedReference = ((resolution, state) => {
      openResolvedReferenceCalls += 1;
      originalOpen(resolution, state);
    }) as GraphReferenceProjectionBinding["openResolvedReference"];

    await user.click(screen.getByRole("button", { name: /Open related object .*The Inn/i }));
    await waitFor(() => expect(bindingAtStart.resolveRelationship).toHaveBeenCalledTimes(1));

    latestContext!.selectCampaign("longmont-c2");
    await waitFor(() => {
      expect(latestContext?.lens.status === "ready" && latestContext.lens.campaignId).toBe("longmont-c2");
    });
    await waitFor(() => {
      expect(latestBinding).not.toBeNull();
      expect(latestBinding).not.toBe(bindingAtStart);
    });
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    });

    const innView = searchItemFromApiNode(innNode).nodeView;
    await act(async () => {
      resolveDeferred({
        kind: "resolved_graph",
        locator: "dmb-node:location-inn",
        reference: referenceFromGraphNode(innView),
        graphNodeId: "location-inn",
        graphObject: buildGraphObjectCardFromNodeView(innView),
        graphScope: {
          worldId: "eldyrwild",
          campaignId: "longmont-c2",
          scopeMode: "campaign",
          revisionId: "rev-c2",
        },
        projectionState: "ready",
        message: "Resolved graph node Inn.",
      });
      await deferred;
    });

    expect(openResolvedReferenceCalls).toBe(0);
    expect(screen.queryByTestId("active-graph-node-id")?.textContent).not.toBe("location-inn");
  });

  it("E3/E6 stale Save: retained Save invoke is a no-op after capability unmount", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFixture(DOC_ID, "longmont-c1"),
    );
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    let retainedSave: (() => void | Promise<void>) | null = null;

    function PublicationEditProbe() {
      const { surfaceInteractionPublication } = useAgentInteraction();
      const saveCommand = surfaceInteractionPublication?.editCommands.find(
        (command) => command.id === BUILD_DOCUMENT_SAVE_COMMAND_ID,
      );
      if (saveCommand) {
        retainedSave = saveCommand.invoke;
      }
      return (
        <p data-testid="build-save-command">
          {saveCommand ? "present" : "absent"}
        </p>
      );
    }

    const { unmount } = render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_ID}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_ID} />
          <PublicationEditProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("build-save-command")).toHaveTextContent("present");
    });
    expect(retainedSave).not.toBeNull();
    const invokeRetained = retainedSave!;

    unmount();

    await act(async () => {
      await invokeRetained();
    });

    expect(liveApi.prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(liveApi.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });

  it("insertExact inserts scoped attrs once under ready editable session", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    let latestContext: BuildReferenceContextBinding | null = null;
    const editorBundle = createInsertEditor();

    function EditorMountProbe() {
      const session = useMarkdownCanvasSession();
      useEffect(() => {
        if (session.phase === "ready_clean" || session.phase === "ready_dirty") {
          session.setEditor(editorBundle.editor);
        }
      }, [session]);
      return null;
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
          <EditorMountProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestContext?.insertAvailable).toBe(true));
    const glowItem = latestContext!.items.find((item) => item.nodeId === "npc-glowkindle");
    expect(glowItem).toBeTruthy();

    await act(async () => {
      await latestContext!.insertExact(glowItem!);
    });

    expect(editorBundle.chain.insertRunbookReference).toHaveBeenCalledTimes(1);
    expect(editorBundle.chain.insertRunbookReference.mock.calls[0]?.[0]).toMatchObject({
      refId: "npc-glowkindle",
      graphWorldId: "eldyrwild",
      graphCampaignId: "longmont-c1",
      graphScopeMode: "campaign",
      graphRevisionId: "rev-1",
    });
  });

  it("insertExact no-ops for stale item absent from current ready results", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    let latestContext: BuildReferenceContextBinding | null = null;
    const editorBundle = createInsertEditor();

    function EditorMountProbe() {
      const session = useMarkdownCanvasSession();
      useEffect(() => {
        if (session.phase === "ready_clean" || session.phase === "ready_dirty") {
          session.setEditor(editorBundle.editor);
        }
      }, [session]);
      return null;
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
          <EditorMountProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestContext?.projectionState).toBe("ready"));

    const stale = searchItemFromApiNode({
      ...glowkindleNode,
      nodeId: "npc-stale-from-prior-lens",
      label: "Stale",
    });
    await act(async () => {
      await latestContext!.insertExact({
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
    });

    expect(editorBundle.chain.insertRunbookReference).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByTestId("build-reference-context-insertion-error")).toHaveAttribute(
        "data-error",
        expect.stringMatching(/no longer in the current projection/i),
      );
    });
  });

  it("same-scope chip activation opens without route change", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    let latestRuntime: ReturnType<typeof useGraphNodeChipRuntime> | null = null;
    const initialSearch = window.location.search;

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
          <ChipRuntimeProbe onRuntime={(runtime) => { latestRuntime = runtime; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestRuntime?.onSelectReference).toBeTypeOf("function"));
    const scope = graphScopeFromProjectionFixture();
    const scopedAttrs = referenceAttrsWithExactScope(
      referenceFromGraphNode(searchItemFromApiNode(glowkindleNode).nodeView),
      scope,
    );

    act(() => {
      latestRuntime!.onSelectReference?.(scopedAttrs);
    });

    await waitFor(() => {
      expect(screen.getByTestId("active-graph-node-id")).toHaveTextContent("npc-glowkindle");
    });
    expect(window.location.search).toBe(initialSearch);
  });

  it("different-scope chip activation pins route and opens after ready projection", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFixture(DOC_ID, "longmont-c1"),
    );
    vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce(graphProjectionFixture())
      .mockResolvedValueOnce({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          revisionId: "rev-pinned",
          headRevisionId: "rev-1",
          isHead: false,
        },
        nodes: [innNode],
      });

    let latestRuntime: ReturnType<typeof useGraphNodeChipRuntime> | null = null;
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
          <ChipRuntimeProbe onRuntime={(runtime) => { latestRuntime = runtime; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestRuntime?.onSelectReference).toBeTypeOf("function"));

    const storedScope = {
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      scopeMode: "campaign" as const,
      revisionId: "rev-pinned",
    };
    const scopedAttrs = referenceAttrsWithExactScope(
      referenceFromGraphNode(searchItemFromApiNode(innNode).nodeView),
      storedScope,
    );

    act(() => {
      latestRuntime!.onSelectReference?.(scopedAttrs);
    });

    await waitFor(() => {
      const params = new URLSearchParams(window.location.search);
      expect(params.get("campaign")).toBe("longmont-c1");
      expect(params.get("graphRevision")).toBe("rev-pinned");
    });
    await waitFor(() => {
      expect(vi.mocked(liveApi.postWorldGraphProjection)).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(latestContext?.projectionState).toBe("ready");
      expect(latestContext?.loadedRevisionId).toBe("rev-pinned");
    });
    expect(latestContext?.items.some((item) => item.nodeId === "location-inn")).toBe(true);

    await waitFor(() => {
      expect(screen.getByTestId("active-graph-node-id")).toHaveTextContent("location-inn");
    });
  });

  it("revokes pending chip activation when document switches A to B", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id: string) =>
      snapshotFixture(id, "eldyrwild"),
    );

    let resolveDeferred!: (value: ReturnType<typeof graphProjectionFixture>) => void;
    const deferred = new Promise<ReturnType<typeof graphProjectionFixture>>((resolve) => {
      resolveDeferred = resolve;
    });
    vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce(graphProjectionFixture())
      .mockImplementationOnce(() => deferred);

    let latestRuntime: ReturnType<typeof useGraphNodeChipRuntime> | null = null;

    function ActiveGraphReferenceProbe() {
      const { activeGraphReference } = useAgentInteraction();
      return (
        <p data-testid="active-graph-node-id">
          {activeGraphReference?.kind === "resolved_graph" ? activeGraphReference.graphNodeId : "none"}
        </p>
      );
    }

    function DocumentHarness({ documentId }: { documentId: string }) {
      return (
        <MarkdownCanvasSessionProvider
          key={documentId}
          documentId={documentId}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={documentId} />
          <ChipRuntimeProbe onRuntime={(runtime) => { latestRuntime = runtime; }} />
        </MarkdownCanvasSessionProvider>
      );
    }

    const { rerender } = render(
      <AgentInteractionProvider>
        <DocumentHarness documentId={DOC_ID} />
        <ActiveGraphReferenceProbe />
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestRuntime?.onSelectReference).toBeTypeOf("function"));

    const storedScope = {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "campaign" as const,
      revisionId: "rev-c2",
    };
    const scopedAttrs = referenceAttrsWithExactScope(
      referenceFromGraphNode(searchItemFromApiNode(innNode).nodeView),
      storedScope,
    );

    act(() => {
      latestRuntime!.onSelectReference?.(scopedAttrs);
    });

    window.history.replaceState({}, "", `/build?documentId=${DOC_B}&campaign=longmont-c1`);
    rerender(
      <AgentInteractionProvider>
        <DocumentHarness documentId={DOC_B} />
        <ActiveGraphReferenceProbe />
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(new URLSearchParams(window.location.search).get("documentId")).toBe(DOC_B);
    });

    await act(async () => {
      resolveDeferred({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          campaignId: "longmont-c2",
          revisionId: "rev-c2",
          headRevisionId: "rev-c2",
        },
        nodes: [innNode],
      });
      await deferred;
    });

    expect(screen.getByTestId("active-graph-node-id")).toHaveTextContent("none");
  });

  it("delayed stale projection completion does not open after route changed away from pending", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFixture(DOC_ID, "eldyrwild"),
    );

    let resolveFirst!: (value: ReturnType<typeof graphProjectionFixture>) => void;
    const firstDeferred = new Promise<ReturnType<typeof graphProjectionFixture>>((resolve) => {
      resolveFirst = resolve;
    });
    vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce(graphProjectionFixture())
      .mockImplementationOnce(() => firstDeferred)
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

    let latestRuntime: ReturnType<typeof useGraphNodeChipRuntime> | null = null;

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
          <ChipRuntimeProbe onRuntime={(runtime) => { latestRuntime = runtime; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestRuntime?.onSelectReference).toBeTypeOf("function"));

    const storedScope = {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "campaign" as const,
      revisionId: "rev-c2",
    };
    const scopedAttrs = referenceAttrsWithExactScope(
      referenceFromGraphNode(searchItemFromApiNode(innNode).nodeView),
      storedScope,
    );

    act(() => {
      latestRuntime!.onSelectReference?.(scopedAttrs);
    });

    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    window.dispatchEvent(new PopStateEvent("popstate"));

    await act(async () => {
      resolveFirst({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          campaignId: "longmont-c2",
          revisionId: "rev-c2",
          headRevisionId: "rev-c2",
        },
        nodes: [innNode],
      });
      await firstDeferred;
    });

    expect(screen.getByTestId("active-graph-node-id")).toHaveTextContent("none");
  });

  it("insertExact retained from lens A no-ops after lens B becomes ready", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
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
    let sessionPhase = "unknown";
    const editorBundle = createInsertEditor();

    function EditorMountProbe() {
      const session = useMarkdownCanvasSession();
      sessionPhase = session.phase;
      useEffect(() => {
        if (session.phase === "ready_clean" || session.phase === "ready_dirty") {
          session.setEditor(editorBundle.editor);
        }
      }, [session]);
      return <p data-testid="session-phase">{session.phase}</p>;
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
          <EditorMountProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestContext?.insertAvailable).toBe(true));
    const insertExactA = latestContext!.insertExact;
    const itemA = latestContext!.items.find((item) => item.nodeId === "npc-glowkindle");
    expect(itemA).toBeTruthy();
    expect(screen.getByTestId("session-phase")).toHaveTextContent("ready_clean");

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c2`);
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() => {
      expect(latestContext?.projectionState).toBe("ready");
      expect(latestContext?.items.some((item) => item.nodeId === "location-inn")).toBe(true);
      expect(latestContext?.items.some((item) => item.nodeId === "npc-glowkindle")).toBe(false);
    });

    await act(async () => {
      await insertExactA(itemA!);
    });

    expect(editorBundle.chain.insertRunbookReference).not.toHaveBeenCalled();
    expect(editorBundle.editor.chain).not.toHaveBeenCalled();
    expect(screen.getByTestId("session-phase")).toHaveTextContent("ready_clean");
    expect(sessionPhase).toBe("ready_clean");
  });

  it("revokes pending activation when a different valid head projection becomes ready", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());

    let resolvePinned!: (value: ReturnType<typeof graphProjectionFixture>) => void;
    const pinnedDeferred = new Promise<ReturnType<typeof graphProjectionFixture>>((resolve) => {
      resolvePinned = resolve;
    });
    vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce(graphProjectionFixture())
      .mockImplementationOnce(() => pinnedDeferred)
      .mockResolvedValueOnce({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          campaignId: "longmont-c2",
          revisionId: "rev-c2-head",
          headRevisionId: "rev-c2-head",
        },
        nodes: [innNode],
      })
      .mockResolvedValueOnce({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          campaignId: "longmont-c1",
          revisionId: "rev-pinned",
          headRevisionId: "rev-1",
          isHead: false,
        },
        nodes: [innNode],
      });

    let latestRuntime: ReturnType<typeof useGraphNodeChipRuntime> | null = null;
    let latestContext: BuildReferenceContextBinding | null = null;

    function ActiveGraphReferenceProbe() {
      const { activeGraphReference } = useAgentInteraction();
      return (
        <p data-testid="active-graph-node-id">
          {activeGraphReference?.kind === "resolved_graph"
            ? activeGraphReference.graphNodeId
            : activeGraphReference?.kind ?? "none"}
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
          <ChipRuntimeProbe onRuntime={(runtime) => { latestRuntime = runtime; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestRuntime?.onSelectReference).toBeTypeOf("function"));

    const storedScope = {
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      scopeMode: "campaign" as const,
      revisionId: "rev-pinned",
    };
    const scopedAttrs = referenceAttrsWithExactScope(
      referenceFromGraphNode(searchItemFromApiNode(innNode).nodeView),
      storedScope,
    );

    act(() => {
      latestRuntime!.onSelectReference?.(scopedAttrs);
    });

    await waitFor(() => {
      expect(new URLSearchParams(window.location.search).get("graphRevision")).toBe("rev-pinned");
    });

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c2`);
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() => {
      expect(latestContext?.projectionState).toBe("ready");
      expect(latestContext?.items.some((item) => item.nodeId === "location-inn")).toBe(true);
    });
    expect(screen.getByTestId("active-graph-node-id")).toHaveTextContent("none");

    await act(async () => {
      resolvePinned({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          campaignId: "longmont-c1",
          revisionId: "rev-pinned",
          headRevisionId: "rev-1",
          isHead: false,
        },
        nodes: [innNode],
      });
      await pinnedDeferred;
    });
    expect(screen.getByTestId("active-graph-node-id")).toHaveTextContent("none");

    // Later revisit the original pin for another reason — stale activation must not open.
    window.history.pushState(
      {},
      "",
      `/build?documentId=${DOC_ID}&campaign=longmont-c1&graphRevision=rev-pinned`,
    );
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() => {
      expect(latestContext?.projectionState).toBe("ready");
      expect(latestContext?.loadedRevisionId).toBe("rev-pinned");
    });
    expect(screen.getByTestId("active-graph-node-id")).toHaveTextContent("none");
  });

  it("publishes exact error when pinned projection request rejects", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
    vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce(graphProjectionFixture())
      .mockRejectedValueOnce(new Error("revision unavailable"));

    let latestRuntime: ReturnType<typeof useGraphNodeChipRuntime> | null = null;
    const requestCountBeforePin = () => vi.mocked(liveApi.postWorldGraphProjection).mock.calls.length;

    function ActiveGraphReferenceProbe() {
      const { activeGraphReference } = useAgentInteraction();
      if (!activeGraphReference) {
        return <p data-testid="active-graph-kind">none</p>;
      }
      return (
        <>
          <p data-testid="active-graph-kind">{activeGraphReference.kind}</p>
          <p data-testid="active-graph-message">{activeGraphReference.message ?? ""}</p>
        </>
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
          <ChipRuntimeProbe onRuntime={(runtime) => { latestRuntime = runtime; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestRuntime?.onSelectReference).toBeTypeOf("function"));
    const callsBefore = requestCountBeforePin();

    const storedScope = {
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      scopeMode: "campaign" as const,
      revisionId: "rev-missing",
    };
    const scopedAttrs = referenceAttrsWithExactScope(
      referenceFromGraphNode(searchItemFromApiNode(innNode).nodeView),
      storedScope,
    );

    act(() => {
      latestRuntime!.onSelectReference?.(scopedAttrs);
    });

    await waitFor(() => {
      expect(screen.getByTestId("active-graph-kind")).toHaveTextContent("error");
    });
    expect(screen.getByTestId("active-graph-message").textContent).toMatch(/rev-missing|unavailable/i);
    // One pin request; no current-head or corpus retry.
    expect(vi.mocked(liveApi.postWorldGraphProjection).mock.calls.length).toBe(callsBefore + 1);
  });

  it("publishes exact error when pinned response scope mismatches stored chip scope", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
    vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce(graphProjectionFixture())
      .mockResolvedValueOnce({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          revisionId: "rev-pinned",
          headRevisionId: "rev-1",
          isHead: false,
        },
        nodes: [innNode],
      });

    let latestRuntime: ReturnType<typeof useGraphNodeChipRuntime> | null = null;

    function ActiveGraphReferenceProbe() {
      const { activeGraphReference } = useAgentInteraction();
      if (!activeGraphReference) {
        return <p data-testid="active-graph-kind">none</p>;
      }
      return (
        <>
          <p data-testid="active-graph-kind">{activeGraphReference.kind}</p>
          <p data-testid="active-graph-message">{activeGraphReference.message ?? ""}</p>
        </>
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
          <ChipRuntimeProbe onRuntime={(runtime) => { latestRuntime = runtime; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestRuntime?.onSelectReference).toBeTypeOf("function"));

    // Chip stores a wrong worldId; pin still loads campaign+revision successfully.
    const storedScope = {
      worldId: "other-world",
      campaignId: "longmont-c1",
      scopeMode: "campaign" as const,
      revisionId: "rev-pinned",
    };
    const scopedAttrs = referenceAttrsWithExactScope(
      referenceFromGraphNode(searchItemFromApiNode(innNode).nodeView),
      storedScope,
    );

    act(() => {
      latestRuntime!.onSelectReference?.(scopedAttrs);
    });

    await waitFor(() => {
      expect(screen.getByTestId("active-graph-kind")).toHaveTextContent("error");
    });
    expect(screen.getByTestId("active-graph-message").textContent).toMatch(/rev-pinned/);
    expect(screen.getByTestId("active-graph-kind")).not.toHaveTextContent("resolved_graph");
  });

  it("route-away to a failing projection does not publish a stale pin failure", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());

    let resolvePinned!: (value: ReturnType<typeof graphProjectionFixture>) => void;
    const pinnedDeferred = new Promise<ReturnType<typeof graphProjectionFixture>>((resolve) => {
      resolvePinned = resolve;
    });
    vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce(graphProjectionFixture())
      .mockImplementationOnce(() => pinnedDeferred)
      .mockRejectedValueOnce(new Error("destination lens unavailable"));

    let latestRuntime: ReturnType<typeof useGraphNodeChipRuntime> | null = null;
    let latestContext: BuildReferenceContextBinding | null = null;

    function ActiveGraphReferenceProbe() {
      const { activeGraphReference } = useAgentInteraction();
      if (!activeGraphReference) {
        return <p data-testid="active-graph-kind">none</p>;
      }
      return (
        <>
          <p data-testid="active-graph-kind">{activeGraphReference.kind}</p>
          <p data-testid="active-graph-message">{activeGraphReference.message ?? ""}</p>
        </>
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
          <ChipRuntimeProbe onRuntime={(runtime) => { latestRuntime = runtime; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestRuntime?.onSelectReference).toBeTypeOf("function"));

    const storedScope = {
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      scopeMode: "campaign" as const,
      revisionId: "rev-pinned",
    };
    const scopedAttrs = referenceAttrsWithExactScope(
      referenceFromGraphNode(searchItemFromApiNode(innNode).nodeView),
      storedScope,
    );

    act(() => {
      latestRuntime!.onSelectReference?.(scopedAttrs);
    });

    await waitFor(() => {
      expect(new URLSearchParams(window.location.search).get("graphRevision")).toBe("rev-pinned");
    });

    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c2`);
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() => {
      expect(latestContext?.projectionState).toBe("error");
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("active-graph-kind")).toHaveTextContent("none");

    await act(async () => {
      resolvePinned({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          revisionId: "rev-pinned",
          headRevisionId: "rev-1",
          isHead: false,
        },
        nodes: [innNode],
      });
      await pinnedDeferred;
    });
    expect(screen.getByTestId("active-graph-kind")).toHaveTextContent("none");
  });

  it("Back to head with matching revisionId revokes pending pin without opening", async () => {
    window.history.replaceState({}, "", `/build?documentId=${DOC_ID}&campaign=longmont-c1`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());

    let resolvePinned!: (value: ReturnType<typeof graphProjectionFixture>) => void;
    const pinnedDeferred = new Promise<ReturnType<typeof graphProjectionFixture>>((resolve) => {
      resolvePinned = resolve;
    });
    vi.mocked(liveApi.postWorldGraphProjection)
      .mockResolvedValueOnce({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          revisionId: "rev-head-a",
          headRevisionId: "rev-head-a",
        },
      })
      .mockImplementationOnce(() => pinnedDeferred)
      .mockResolvedValueOnce({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          // Head after Back reports the same revision id the chip stored as a pin.
          revisionId: "rev-1",
          headRevisionId: "rev-1",
        },
        nodes: [innNode],
      });

    let latestRuntime: ReturnType<typeof useGraphNodeChipRuntime> | null = null;
    let latestContext: BuildReferenceContextBinding | null = null;

    function ActiveGraphReferenceProbe() {
      const { activeGraphReference } = useAgentInteraction();
      if (!activeGraphReference) {
        return <p data-testid="active-graph-kind">none</p>;
      }
      return <p data-testid="active-graph-kind">{activeGraphReference.kind}</p>;
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
          <ChipRuntimeProbe onRuntime={(runtime) => { latestRuntime = runtime; }} />
          <ActiveGraphReferenceProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => expect(latestRuntime?.onSelectReference).toBeTypeOf("function"));
    await waitFor(() => expect(latestContext?.loadedRevisionId).toBe("rev-head-a"));

    const storedScope = {
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      scopeMode: "campaign" as const,
      revisionId: "rev-1",
    };
    const scopedAttrs = referenceAttrsWithExactScope(
      referenceFromGraphNode(searchItemFromApiNode(innNode).nodeView),
      storedScope,
    );

    act(() => {
      latestRuntime!.onSelectReference?.(scopedAttrs);
    });

    await waitFor(() => {
      expect(new URLSearchParams(window.location.search).get("graphRevision")).toBe("rev-1");
    });

    // Browser Back restores the prior head lens (no graphRevision).
    window.history.back();
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() => {
      expect(new URLSearchParams(window.location.search).get("graphRevision")).toBeNull();
      expect(latestContext?.projectionState).toBe("ready");
      expect(latestContext?.loadedRevisionId).toBe("rev-1");
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("active-graph-kind")).toHaveTextContent("none");

    await act(async () => {
      resolvePinned({
        ...graphProjectionFixture(),
        snapshot: {
          ...graphProjectionFixture().snapshot,
          revisionId: "rev-1",
          headRevisionId: "rev-head-a",
          isHead: false,
        },
        nodes: [innNode],
      });
      await pinnedDeferred;
    });
    expect(screen.getByTestId("active-graph-kind")).toHaveTextContent("none");
  });
});
