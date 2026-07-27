import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphProjectionNodeView } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import type { PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";
import { PlanReferenceProjectionBinding } from "../reference/PlanReferenceProjectionBinding";
import { PlanGraphLensProvider } from "../PlanGraphLensContext";
import { PlanGraphReferenceResolverProvider } from "../reference/usePlanGraphReferenceResolver";
import type { SurfaceConfig } from "../types";
import { AdaptiveProjectionContainer } from "./AdaptiveProjectionContainer";
import {
  GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
  type GraphReviewDiagnosticsProjectionPayload,
  type PlanReferenceProjectionBinding as PlanBinding,
} from "./projectionBindings";
import { ProjectionProvider, useProjection } from "./projectionContext";
import { GraphReviewLiveStateProvider } from "../graphReviewWorkbench/GraphReviewLiveStateContext";
import { GraphReviewDiagnosticsProjectionBinding } from "../graphReviewWorkbench/GraphReviewDiagnosticsProjectionBinding";
import { buildEvidenceSelectionForDelta } from "../graphReviewWorkbench/graphReviewEvidenceSelectionUtils";
import { buildGraphReviewDeltaIndex } from "../graphReviewWorkbench/graphReviewDeltaUtils";
import { buildSourceSpanDeltaIndex } from "../graphReviewWorkbench/graphReviewSourceSpanOverlayUtils";
import { buildVariantLiveInventoryIndex } from "../graphReviewWorkbench/graphReviewVariantReferenceUtils";

vi.mock("../../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/liveApi")>();
  return {
    ...actual,
    getRecapArtifacts: vi.fn(async () => ({ records: [] })),
    postWorldGraphProjection: vi.fn(),
  };
});

import * as liveApi from "../../api/liveApi";

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });

const surfaceConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    headerLabel: sessionDescriptor.planningDocument.title,
    ingestSession: 21,
    liveSession: 22,
  },
  tools: [
    { id: "recap", label: "Recap", size: "wide" },
    { id: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, label: "Diagnostics", size: "wide" },
    { id: "statblock", label: "Statblock", size: "wide" },
  ],
  canvas: { documentId: sessionDescriptor.planningDocument.documentId },
  theme: {},
  sessionDescriptor,
};

const bubblesNode: GraphProjectionNodeView = {
  node_id: "creature:bubbles",
  label: "Bubbles the Float Goat",
  kind: "creature",
  role: "creature",
  aliases: [],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [
    {
      edge_id: "edge-1",
      node_id: "location-inn",
      label: "Inn",
      kind: "location",
      predicate: "met at",
      direction: "outgoing",
      related_summary: null,
      evidence_ref_ids: [],
      source_domains: ["recap"],
      anchored_to_focus_session: true,
      session_ids: [],
    },
  ],
  anchored_to_focus_session: true,
  summary: "A float goat rescued from the flooded river.",
};

const innNode: GraphProjectionNodeView = {
  node_id: "location-inn",
  label: "Inn",
  kind: "location",
  role: "location",
  aliases: [],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "Meeting place.",
};

const innResolution: PlanReferenceResolution = {
  kind: "graph-node",
  locator: "dmb-node:location-inn",
  refType: "location",
  refId: "location-inn",
  graphObject: buildGraphObjectCardFromNodeView(innNode),
  graphNodeId: "location-inn",
  fallback: null,
  source: "world-graph",
  message: "Resolved Inn.",
  graphProjectionState: "ready",
};

const readyWorldGraphProjection = {
  schema: "dmb_world_graph_projection_v1" as const,
  snapshot: {
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
    revisionId: "rev-1",
    headRevisionId: "rev-1",
    isHead: true,
    focus: { kind: "session" as const, sessionId: "session-21" },
    admissibility: "gm" as const,
  },
  summary: {
    nodeCount: 2,
    relationshipCount: 0,
    attributeCount: 0,
    evidenceCount: 0,
    sourceArtifactCount: 0,
    sourceTruncated: false,
  },
  nodes: [
    {
      nodeId: "creature:bubbles",
      label: "Bubbles the Float Goat",
      kind: "creature",
      role: "creature",
      aliases: [],
      sourceDomains: ["recap"],
      summary: "A float goat rescued from the flooded river.",
      anchoredToFocusSession: true,
      evidenceBadges: [],
      adjacency: [],
      suggestedExpansions: [],
      evidenceRefIds: [],
      sourceArtifactIds: [],
    },
    {
      nodeId: "location-inn",
      label: "Inn",
      kind: "location",
      role: "location",
      aliases: [],
      sourceDomains: ["recap"],
      summary: "Meeting place.",
      anchoredToFocusSession: true,
      evidenceBadges: [],
      adjacency: [],
      suggestedExpansions: [],
      evidenceRefIds: [],
      sourceArtifactIds: [],
    },
  ],
  relationships: [],
  attributes: [],
  evidence: [],
  sourceArtifacts: [],
  diagnostics: [],
};

function OpenReferenceButton() {
  const { openPlanReferenceResolution } = useProjection();
  return (
    <button
      type="button"
      onClick={() =>
        openPlanReferenceResolution(
          {
            kind: "graph-node",
            locator: `dmb-node:${bubblesNode.node_id}`,
            refType: bubblesNode.kind,
            refId: bubblesNode.node_id,
            graphObject: buildGraphObjectCardFromNodeView(bubblesNode),
            graphNodeId: bubblesNode.node_id,
            fallback: null,
            source: "world-graph",
            message: `Resolved graph node ${bubblesNode.label}.`,
            graphProjectionState: "ready",
          } satisfies PlanReferenceResolution,
          "ready",
        )
      }
    >
      Open Bubbles
    </button>
  );
}

function OpenDiagnosticsButton() {
  const { openTool } = useProjection();
  return (
    <button type="button" onClick={() => openTool(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID)}>
      Open Diagnostics
    </button>
  );
}

function BindingReader({
  onBinding,
}: {
  onBinding: (binding: PlanBinding | null) => void;
}) {
  const { planReferenceBinding } = useProjection();
  useEffect(() => {
    onBinding(planReferenceBinding);
  }, [onBinding, planReferenceBinding]);
  return null;
}

function readyDiagnosticsPayload(
  overrides: Partial<GraphReviewDiagnosticsProjectionPayload> = {},
): GraphReviewDiagnosticsProjectionPayload {
  const glowkindle: GraphProjectionNodeView = {
    node_id: "npc-glowkindle",
    label: "Glowkindle",
    kind: "npc",
    role: "merchant",
    aliases: [],
    source_domains: ["recap"],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: true,
    summary: "A friendly merchant.",
  };

  return {
    campaignId: "longmont-c2",
    sessionId: "session-21",
    liveRun: {
      manifest_path: "manifest.json",
      run_dir: "runs/run-1",
      campaign_id: "longmont-c2",
      session_id: "session-21",
      status: "preview_ready",
      node_count: 1,
      edge_count: 0,
      evidence_ref_count: 0,
      next_actions: [],
      run_id: "run-1",
      run_label: "Run 1",
      vocabulary_mode: "played_canon",
      runner_options_summary: {},
      diagnostics_summary: {},
      preview_union_available: true,
    },
    projection: {
      campaign_id: "longmont-c2",
      session_id: "session-21",
      node_views: { "npc-glowkindle": glowkindle },
      focus: {
        focused_evidence_ref_ids: [],
        focused_edge_ids: [],
        focused_node_ids: [],
      },
      mentions: [],
    },
    projectionStatus: "ready",
    compareStatus: "error",
    compare: null,
    compareError: "first-metric-error",
    selection: null,
    onSelectSelection: () => undefined,
    deltaIndex: buildGraphReviewDeltaIndex({
      compare: null,
      liveProjection: null,
      goldLane: null,
      liveLane: null,
    }),
    sourceSpanDeltaIndex: buildSourceSpanDeltaIndex({
      sourceSpans: [],
      deltas: [],
    }),
    selectedDeltaNodeId: "npc-glowkindle",
    setSelectedEvidenceDeltaId: () => undefined,
    selectedEvidenceDeltaId: null,
    selectedSourceSpanId: null,
    setSelectedSourceSpanId: () => undefined,
    evidenceSelection: buildEvidenceSelectionForDelta(null),
    evidenceDiff: null,
    evidenceStatus: "idle",
    evidenceError: null,
    manualBeds: [],
    manualBedsStatus: "idle",
    manualBedsError: null,
    selectedManualBed: null,
    selectedVariantLaneView: null,
    selectedManualVariant: null,
    onSelectManualBedId: () => undefined,
    onSelectManualVariantName: () => undefined,
    variantInventoryIndex: buildVariantLiveInventoryIndex({
      variant: null,
      compare: null,
    }),
    selectedVariantInventoryRowId: null,
    setSelectedVariantInventoryRowId: () => undefined,
    selectedVariantInventoryRow: null,
    ...overrides,
  };
}

describe("projectionBindings sibling topology", () => {
  beforeEach(() => {
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(readyWorldGraphProjection as never);
  });

  it("renders Plan content and relationship traversal with production adapter and sibling container", async () => {
    const user = userEvent.setup();

    render(
      <ProjectionProvider config={surfaceConfig}>
        <PlanGraphLensProvider planCampaignId={sessionDescriptor.campaignId}>
          <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
            <PlanReferenceProjectionBinding />
          </PlanGraphReferenceResolverProvider>
        </PlanGraphLensProvider>
        <OpenReferenceButton />
        <AdaptiveProjectionContainer config={surfaceConfig} />
      </ProjectionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Open Bubbles" }));
    await waitFor(() => {
      expect(screen.getByLabelText(/Bubbles the Float Goat graph object/i)).toBeInTheDocument();
    });

    const related = await screen.findByRole("button", { name: /Open related object .*Inn/i });
    await waitFor(() => {
      expect(related).toBeEnabled();
    });
    await user.click(related);

    await waitFor(() => {
      expect(screen.getByLabelText(/Inn graph object/i)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText(/Bubbles the Float Goat graph object/i)).not.toBeInTheDocument();
  });

  it("renders Graph Review diagnostics with container outside live-state provider", async () => {
    const user = userEvent.setup();
    render(
      <ProjectionProvider config={surfaceConfig}>
        <GraphReviewLiveStateProvider
          campaignId="longmont-c2"
          sessionId="session-21"
          liveRun={null}
          hasGold={false}
          compare={null}
          compareStatus="idle"
          compareError={null}
          selection={null}
          onSelectSelection={() => undefined}
        >
          <GraphReviewDiagnosticsProjectionBinding />
        </GraphReviewLiveStateProvider>
        <OpenDiagnosticsButton />
        <AdaptiveProjectionContainer config={surfaceConfig} />
      </ProjectionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Open Diagnostics" }));
    expect(
      await screen.findByText(/Select a live run with a projection to inspect diagnostics/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-diagnostics-unavailable")).not.toBeInTheDocument();
  });

  it("does not open projection when Plan binding is superseded during relationship resolve", async () => {
    const user = userEvent.setup();
    let resolveDeferred!: (resolution: PlanReferenceResolution) => void;
    const deferred = new Promise<PlanReferenceResolution>((resolve) => {
      resolveDeferred = resolve;
    });
    const openFromFirst = vi.fn();
    const openFromSecond = vi.fn();

    function ControllablePlanBinding() {
      const { registerPlanReferenceBinding } = useProjection();
      const [generation, setGeneration] = useState(0);
      useEffect(() => {
        return registerPlanReferenceBinding({
          resolverState: "ready",
          resolveRelationship: () => deferred,
          openResolvedReference: generation === 0 ? openFromFirst : openFromSecond,
          openTool: vi.fn(),
        });
      }, [generation, registerPlanReferenceBinding]);
      return (
        <button type="button" onClick={() => setGeneration(1)}>
          Supersede binding
        </button>
      );
    }

    render(
      <ProjectionProvider config={surfaceConfig}>
        <ControllablePlanBinding />
        <OpenReferenceButton />
        <AdaptiveProjectionContainer config={surfaceConfig} />
      </ProjectionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Open Bubbles" }));
    await waitFor(() => {
      expect(screen.getByLabelText(/Bubbles the Float Goat graph object/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Open related object .*Inn/i }));
    await user.click(screen.getByRole("button", { name: "Supersede binding" }));

    await act(async () => {
      resolveDeferred(innResolution);
      await deferred;
    });

    expect(openFromFirst).not.toHaveBeenCalled();
    expect(openFromSecond).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Bubbles the Float Goat graph object/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Inn graph object/i)).not.toBeInTheDocument();
  });

  it("does not let stale cleanup erase a newer registration", async () => {
    const seen: Array<PlanBinding | null> = [];
    let register: ((binding: PlanBinding) => () => void) | null = null;

    function Registrar() {
      const { registerPlanReferenceBinding } = useProjection();
      useEffect(() => {
        register = registerPlanReferenceBinding;
      }, [registerPlanReferenceBinding]);
      return <BindingReader onBinding={(binding) => seen.push(binding)} />;
    }

    render(
      <ProjectionProvider config={surfaceConfig}>
        <Registrar />
      </ProjectionProvider>,
    );

    await waitFor(() => {
      expect(register).not.toBeNull();
    });

    const bindingA: PlanBinding = {
      resolverState: "ready",
      resolveRelationship: vi.fn(),
      openResolvedReference: vi.fn(),
      openTool: vi.fn(),
    };
    const bindingB: PlanBinding = {
      resolverState: "loading",
      resolveRelationship: vi.fn(),
      openResolvedReference: vi.fn(),
      openTool: vi.fn(),
    };

    let cleanupA: (() => void) | undefined;
    await act(async () => {
      cleanupA = register!(bindingA);
      register!(bindingB);
      cleanupA();
    });

    await waitFor(() => {
      expect(seen.at(-1)?.resolverState).toBe("loading");
    });
  });

  it("replaces an open diagnostics registration with the latest observable payload", async () => {
    const user = userEvent.setup();

    function ReplaceableDiagnosticsBinding() {
      const { registerToolProjectionPayload } = useProjection();
      const [token, setToken] = useState(0);
      useEffect(() => {
        const payload = readyDiagnosticsPayload({
          compareError: token === 0 ? "first-metric-error" : "second-metric-error",
          selectedDeltaNodeId: token === 0 ? "npc-glowkindle" : "npc-replacement",
          projection: {
            campaign_id: "longmont-c2",
            session_id: "session-21",
            node_views: {
              "npc-glowkindle": {
                node_id: "npc-glowkindle",
                label: "Glowkindle",
                kind: "npc",
                role: "merchant",
                aliases: [],
                source_domains: ["recap"],
                evidence_badges: [],
                adjacency: [],
                anchored_to_focus_session: true,
                summary: "A friendly merchant.",
              },
              "npc-replacement": {
                node_id: "npc-replacement",
                label: "Replacement Node",
                kind: "npc",
                role: "merchant",
                aliases: [],
                source_domains: ["recap"],
                evidence_badges: [],
                adjacency: [],
                anchored_to_focus_session: true,
                summary: "Replaced selection.",
              },
            },
            focus: {
              focused_evidence_ref_ids: [],
              focused_edge_ids: [],
              focused_node_ids: [],
            },
            mentions: [],
          },
        });
        return registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
      }, [registerToolProjectionPayload, token]);
      return (
        <button type="button" onClick={() => setToken((value) => value + 1)}>
          Replace payload
        </button>
      );
    }

    render(
      <ProjectionProvider config={surfaceConfig}>
        <ReplaceableDiagnosticsBinding />
        <OpenDiagnosticsButton />
        <AdaptiveProjectionContainer config={surfaceConfig} />
      </ProjectionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Open Diagnostics" }));
    expect(await screen.findByLabelText("Graph review diagnostics")).toBeInTheDocument();
    expect(screen.getByText("first-metric-error")).toBeInTheDocument();
    expect(screen.getByText("Glowkindle")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Replace payload" }));
    await waitFor(() => {
      expect(screen.getByText("second-metric-error")).toBeInTheDocument();
    });
    expect(screen.queryByText("first-metric-error")).not.toBeInTheDocument();
    expect(screen.getByText("Replacement Node")).toBeInTheDocument();
    expect(screen.queryByText("Glowkindle")).not.toBeInTheDocument();
  });
});
