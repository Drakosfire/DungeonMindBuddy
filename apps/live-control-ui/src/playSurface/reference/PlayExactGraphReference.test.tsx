import { act, render, screen, waitFor } from "@testing-library/react";
import { type MutableRefObject } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  AgentInteractionProvider,
  useAgentInteraction,
} from "../../agentInteraction/AgentInteractionProvider";
import type { AgentInteractionContextValue } from "../../agentInteraction/agentInteractionTypes";
import { LiveApiError } from "../../api/liveApi";
import type { GraphProjectionNodeView } from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import {
  GRAPH_REFERENCE_BINDING_ID,
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
} from "../../graphReference/projectionBindings";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import type {
  ExactGraphReferenceScope,
  GraphReferenceResolution,
} from "../../graphReference/types";
import revisionFixture from "../../../../../tests/fixtures/statblocks/v1/exact-revision-response.json";
import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import {
  admitPlayExactGraphReference,
  buildPlayExactGraphReferencePublication,
  PlayExactGraphReference,
  type PlayExactGraphReferenceHandle,
  type PlayGraphContextInput,
} from "./PlayExactGraphReference";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    postThreatQueryHydration: vi.fn(),
  };
});

import { postThreatQueryHydration } from "../../api/liveApi";

const revision = revisionFixture as StatblockRevisionResourceV1;

const scopeG1: ExactGraphReferenceScope = {
  worldId: "eldyrwild",
  campaignId: "longmont-c2",
  scopeMode: "world",
  revisionId: "rev-g1",
};

const scopeG2: ExactGraphReferenceScope = {
  ...scopeG1,
  revisionId: "rev-g2",
};

const miraNode: GraphProjectionNodeView = {
  node_id: "npc:mira",
  label: "Mira",
  kind: "npc",
  role: "ally",
  aliases: ["The Mira"],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "A known ally.",
};

const threatNode: GraphProjectionNodeView = {
  node_id: "threat:tripod-null-calf",
  label: "Tripod Null-Calf",
  kind: "threat",
  role: "creature",
  aliases: [],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "A tripod calf.",
};

function resolvedGraph(
  node: GraphProjectionNodeView,
  graphScope: ExactGraphReferenceScope = scopeG1,
): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${node.node_id}`,
    reference: null,
    graphNodeId: node.node_id,
    graphObject: buildGraphObjectCardFromNodeView(node),
    graphScope,
    projectionState: "ready",
    message: "Resolved.",
  };
}

function hydrationOk(nodeId: string) {
  return {
    schema: "dmb_threat_query_hydration_response_v1" as const,
    worldId: scopeG1.worldId,
    campaignId: scopeG1.campaignId,
    scopeMode: scopeG1.scopeMode,
    revisionId: scopeG1.revisionId,
    queryText: nodeId,
    resultLabel: "threat_query_hydration_ok" as const,
    hits: [
      {
        threat: {
          nodeId,
          label: nodeId,
          kind: "threat",
          role: "creature",
          aliases: [],
          sourceDomains: [],
          evidenceBadges: [],
          adjacency: [],
          suggestedExpansions: [],
          evidenceRefIds: [],
          sourceArtifactIds: [],
          anchoredToFocusSession: true,
        },
        matchReasons: ["exact_node_id"],
        relationships: [],
        bindings: [
          {
            relationshipEdgeId: "edge-1",
            bindingId: "bind-1",
            bindingRole: "primary",
            threatNodeId: nodeId,
            resourceNodeId: revision.statblock_id,
            provider: "dungeonmind",
            statblockId: revision.statblock_id,
            revisionId: revision.revision_id,
            definitionDigest: revision.definition_digest,
            hydrationStatus: "available" as const,
            binding: null,
            revision,
            message: null,
          },
        ],
        mechanicsDisposition: "hydrated",
      },
    ],
    diagnostics: [],
    message: null,
  };
}

const corpusFallback: Extract<GraphReferenceResolution, { kind: "resolved_corpus_fallback" }> = {
  kind: "resolved_corpus_fallback",
  locator: "npc:mira",
  reference: { kind: "ref", refType: "npc", refId: "npc:mira", label: "Mira" },
  fallback: {
    status: "resolved",
    ref: { kind: "ref", refType: "npc", refId: "npc:mira", label: "Mira" },
    message: "Corpus index found a match.",
  },
  projectionState: "ready",
  message: "Corpus index found a match.",
};

function PlayCatalogBody() {
  const host = useAgentInteraction();
  if (!host.active || !host.activeGraphReference) return null;
  const catalog = host.resolveProjectionCatalog({
    projectionId: GRAPH_REFERENCE_PROJECTION_ID,
    active: host.active,
    bindings: {
      [GRAPH_REFERENCE_RESOLUTION_BINDING_ID]: host.activeGraphReference,
      ...(host.graphReferenceBinding
        ? { [GRAPH_REFERENCE_BINDING_ID]: host.graphReferenceBinding }
        : {}),
    },
  });
  return catalog.status === "ready" ? <>{catalog.body}</> : null;
}

function PlayHarness({
  activeContext,
  resolve,
  resolverState,
  publication,
  adapterRef,
  hostRef,
}: {
  activeContext: PlayGraphContextInput | ExactGraphReferenceScope | null;
  resolve: (input: { requestedNodeId: string; activeContext: ExactGraphReferenceScope }) =>
    Promise<GraphReferenceResolution>;
  resolverState?: "loading" | "ready" | "unavailable" | "error" | null;
  publication?: ReturnType<typeof buildPlayExactGraphReferencePublication>;
  adapterRef: MutableRefObject<PlayExactGraphReferenceHandle | null>;
  hostRef: MutableRefObject<AgentInteractionContextValue | null>;
}) {
  const host = useAgentInteraction();
  hostRef.current = host;
  return (
    <>
      <PlayExactGraphReference
        ref={adapterRef}
        activeContext={activeContext}
        resolve={resolve}
        resolverState={resolverState}
        publication={publication}
      />
      <PlayCatalogBody />
    </>
  );
}

function renderPlay(props: {
  activeContext: PlayGraphContextInput | ExactGraphReferenceScope | null;
  resolve: (input: { requestedNodeId: string; activeContext: ExactGraphReferenceScope }) =>
    Promise<GraphReferenceResolution>;
  resolverState?: "loading" | "ready" | "unavailable" | "error" | null;
  publication?: ReturnType<typeof buildPlayExactGraphReferencePublication>;
}) {
  const adapterRef: MutableRefObject<PlayExactGraphReferenceHandle | null> = { current: null };
  const hostRef: MutableRefObject<AgentInteractionContextValue | null> = { current: null };
  const view = render(
    <AgentInteractionProvider>
      <PlayHarness
        {...props}
        adapterRef={adapterRef}
        hostRef={hostRef}
      />
    </AgentInteractionProvider>,
  );
  return {
    ...view,
    adapterRef,
    hostRef,
    rerenderPlay(next: typeof props) {
      view.rerender(
        <AgentInteractionProvider>
          <PlayHarness
            {...next}
            adapterRef={adapterRef}
            hostRef={hostRef}
          />
        </AgentInteractionProvider>,
      );
    },
  };
}

async function waitForPlayReady(
  hostRef: MutableRefObject<AgentInteractionContextValue | null>,
  adapterRef: MutableRefObject<PlayExactGraphReferenceHandle | null>,
) {
  await waitFor(() => {
    expect(adapterRef.current).not.toBeNull();
    expect(hostRef.current?.graphReferenceBinding).not.toBeNull();
    expect(hostRef.current?.surfaceInteractionPublication?.identity.surfaceId).toBe("play");
  });
}

describe("admitPlayExactGraphReference", () => {
  const exact = resolvedGraph(miraNode);

  it.each([
    {
      name: "exact graph + exact context",
      resolution: exact,
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: true,
    },
    {
      name: "corpus fallback",
      resolution: corpusFallback,
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "ambiguous",
      resolution: {
        kind: "ambiguous" as const,
        locator: "Mira",
        reference: null,
        matchingGraphNodeIds: ["npc:mira", "npc:mira-2"],
        projectionState: "ready" as const,
        message: "Ambiguous.",
      },
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "unresolved miss",
      resolution: {
        kind: "unresolved" as const,
        locator: "dmb-node:npc:mira",
        reference: null,
        projectionState: "ready" as const,
        message: "Missing.",
      },
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "resolver error",
      resolution: {
        kind: "error" as const,
        locator: "dmb-node:npc:mira",
        reference: null,
        projectionState: "error" as const,
        message: "Unavailable.",
      },
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "loading resolution",
      resolution: {
        kind: "unresolved" as const,
        locator: "dmb-node:npc:mira",
        reference: null,
        projectionState: "loading" as const,
        message: "Loading.",
      },
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "node id mismatch",
      resolution: resolvedGraph({ ...miraNode, node_id: "npc:other" }),
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "world mismatch",
      resolution: resolvedGraph(miraNode, { ...scopeG1, worldId: "other-world" }),
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "campaign mismatch",
      resolution: resolvedGraph(miraNode, { ...scopeG1, campaignId: "longmont-c1" }),
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "scopeMode mismatch",
      resolution: resolvedGraph(miraNode, { ...scopeG1, scopeMode: "campaign" }),
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "revision mismatch",
      resolution: resolvedGraph(miraNode, scopeG2),
      context: scopeG1,
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "incomplete context missing revision",
      resolution: exact,
      context: { ...scopeG1, revisionId: "" },
      requestedNodeId: "npc:mira",
      admitted: false,
    },
    {
      name: "label is not admission identity",
      resolution: exact,
      context: scopeG1,
      requestedNodeId: "The Mira",
      admitted: false,
    },
  ])("$name", ({ resolution, context, requestedNodeId, admitted }) => {
    const decision = admitPlayExactGraphReference({
      requestedNodeId,
      activeContext: context,
      resolution,
    });
    expect(decision.admitted).toBe(admitted);
  });
});

describe("PlayExactGraphReference host admission", () => {
  beforeEach(() => {
    vi.mocked(postThreatQueryHydration).mockReset();
  });

  it("opens one shared host with the exact graph object through PlayGraphObjectSheet", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const resolve = vi.fn(async () => resolvedGraph(miraNode));
    const view = renderPlay({ activeContext: scopeG1, resolve, resolverState: "ready" });
    await waitForPlayReady(view.hostRef, view.adapterRef);

    await act(async () => {
      await view.adapterRef.current!.openExactGraphReference("npc:mira");
    });

    expect(resolve).toHaveBeenCalledWith({
      requestedNodeId: "npc:mira",
      activeContext: scopeG1,
    });
    expect(view.hostRef.current?.active?.kind).toBe("content");
    expect(view.hostRef.current?.activeGraphReference).toEqual(resolvedGraph(miraNode));
    expect(screen.getByTestId("play-graph-object-sheet")).toHaveAttribute("data-node-id", "npc:mira");
    expect(screen.getByTestId("play-graph-object-sheet")).toHaveAttribute("data-revision-id", "rev-g1");
    expect(document.querySelectorAll("[data-testid='play-graph-object-sheet']")).toHaveLength(1);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("does not open corpus fallback, ambiguity, miss, or error", async () => {
    const cases: GraphReferenceResolution[] = [
      corpusFallback,
      {
        kind: "ambiguous",
        locator: "Mira",
        reference: null,
        matchingGraphNodeIds: ["npc:mira", "npc:mira-2"],
        projectionState: "ready",
        message: "Ambiguous.",
      },
      {
        kind: "unresolved",
        locator: "dmb-node:npc:mira",
        reference: null,
        projectionState: "ready",
        message: "Missing.",
      },
      {
        kind: "error",
        locator: "dmb-node:npc:mira",
        reference: null,
        projectionState: "error",
        message: "Unavailable.",
      },
    ];

    for (const resolution of cases) {
      const resolve = vi.fn(async () => resolution);
      const view = renderPlay({ activeContext: scopeG1, resolve, resolverState: "ready" });
      await waitForPlayReady(view.hostRef, view.adapterRef);
      await act(async () => {
        await view.adapterRef.current!.openExactGraphReference("npc:mira");
      });
      expect(view.hostRef.current?.activeGraphReference).toBeNull();
      expect(screen.queryByTestId("play-graph-object-sheet")).not.toBeInTheDocument();
      view.unmount();
    }
  });

  it("does not open when requested node X resolves as graph node Y", async () => {
    const resolve = vi.fn(async () => resolvedGraph({ ...miraNode, node_id: "npc:other" }));
    const view = renderPlay({ activeContext: scopeG1, resolve, resolverState: "ready" });
    await waitForPlayReady(view.hostRef, view.adapterRef);
    await act(async () => {
      await view.adapterRef.current!.openExactGraphReference("npc:mira");
    });
    expect(view.hostRef.current?.activeGraphReference).toBeNull();
    expect(screen.queryByTestId("play-graph-object-sheet")).not.toBeInTheDocument();
  });

  it("does not open when any exact context field mismatches", async () => {
    const mismatches: ExactGraphReferenceScope[] = [
      { ...scopeG1, worldId: "other-world" },
      { ...scopeG1, campaignId: "longmont-c1" },
      { ...scopeG1, scopeMode: "campaign" },
      scopeG2,
    ];
    for (const graphScope of mismatches) {
      const resolve = vi.fn(async () => resolvedGraph(miraNode, graphScope));
      const view = renderPlay({ activeContext: scopeG1, resolve, resolverState: "ready" });
      await waitForPlayReady(view.hostRef, view.adapterRef);
      await act(async () => {
        await view.adapterRef.current!.openExactGraphReference("npc:mira");
      });
      expect(view.hostRef.current?.activeGraphReference).toBeNull();
      view.unmount();
    }
  });

  it("does not open incomplete context and does not call resolve", async () => {
    const resolve = vi.fn(async () => resolvedGraph(miraNode));
    const view = renderPlay({
      activeContext: { ...scopeG1, revisionId: "" },
      resolve,
      resolverState: "ready",
    });
    await waitFor(() => expect(view.adapterRef.current).not.toBeNull());
    await act(async () => {
      await view.adapterRef.current!.openExactGraphReference("npc:mira");
    });
    expect(resolve).not.toHaveBeenCalled();
    expect(view.hostRef.current?.activeGraphReference).toBeNull();
  });

  it("discards a stale completion after exact context changes", async () => {
    let finish!: (value: GraphReferenceResolution) => void;
    const deferred = new Promise<GraphReferenceResolution>((resolve) => {
      finish = resolve;
    });
    const resolve = vi.fn(() => deferred);
    const view = renderPlay({ activeContext: scopeG1, resolve, resolverState: "ready" });
    await waitForPlayReady(view.hostRef, view.adapterRef);

    let pending!: Promise<void>;
    act(() => {
      pending = view.adapterRef.current!.openExactGraphReference("npc:mira");
    });
    await waitFor(() => expect(resolve).toHaveBeenCalledTimes(1));

    view.rerenderPlay({ activeContext: scopeG2, resolve, resolverState: "ready" });
    await waitForPlayReady(view.hostRef, view.adapterRef);

    await act(async () => {
      finish(resolvedGraph(miraNode, scopeG1));
      await pending;
    });

    expect(view.hostRef.current?.activeGraphReference).toBeNull();
    expect(screen.queryByTestId("play-graph-object-sheet")).not.toBeInTheDocument();
  });

  it("discards a stale completion after the Play lease identity changes", async () => {
    let finish!: (value: GraphReferenceResolution) => void;
    const deferred = new Promise<GraphReferenceResolution>((resolve) => {
      finish = resolve;
    });
    const resolve = vi.fn(() => deferred);
    const leaseA = buildPlayExactGraphReferencePublication("campaign-a");
    const leaseB = buildPlayExactGraphReferencePublication("campaign-b");
    const view = renderPlay({
      activeContext: scopeG1,
      resolve,
      resolverState: "ready",
      publication: leaseA,
    });
    await waitForPlayReady(view.hostRef, view.adapterRef);

    let pending!: Promise<void>;
    act(() => {
      pending = view.adapterRef.current!.openExactGraphReference("npc:mira");
    });
    await waitFor(() => expect(resolve).toHaveBeenCalledTimes(1));

    view.rerenderPlay({
      activeContext: { ...scopeG1, campaignId: "longmont-c1" },
      resolve,
      resolverState: "ready",
      publication: leaseB,
    });
    await waitFor(() => {
      expect(view.hostRef.current?.surfaceInteractionPublication?.identity.instanceKey)
        .toBe(leaseB.identity.instanceKey);
    });

    await act(async () => {
      finish(resolvedGraph(miraNode, scopeG1));
      await pending;
    });

    expect(view.hostRef.current?.activeGraphReference).toBeNull();
    expect(screen.queryByTestId("play-graph-object-sheet")).not.toBeInTheDocument();
  });

  it("renders admitted Threat mechanics through the existing P3C section", async () => {
    vi.mocked(postThreatQueryHydration).mockResolvedValue(hydrationOk(threatNode.node_id));
    const resolve = vi.fn(async () => resolvedGraph(threatNode));
    const view = renderPlay({ activeContext: scopeG1, resolve, resolverState: "ready" });
    await waitForPlayReady(view.hostRef, view.adapterRef);
    await act(async () => {
      await view.adapterRef.current!.openExactGraphReference(threatNode.node_id);
    });
    expect(screen.getByTestId("play-graph-object-sheet")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("play-threat-mechanics-section")).toBeInTheDocument();
    });
    expect(screen.queryByText(/add to combat/i)).not.toBeInTheDocument();
  });

  it("does not mount a second Projection host/provider", async () => {
    const resolve = vi.fn(async () => resolvedGraph(miraNode));
    const view = renderPlay({ activeContext: scopeG1, resolve, resolverState: "ready" });
    await waitForPlayReady(view.hostRef, view.adapterRef);
    await act(async () => {
      await view.adapterRef.current!.openExactGraphReference("npc:mira");
    });
    expect(screen.getAllByTestId("play-graph-object-sheet")).toHaveLength(1);
    expect(document.querySelectorAll("[data-projection-host]")).toHaveLength(0);
  });
});
