import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphProjectionNodeView } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import type { PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";
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

vi.mock("../../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/liveApi")>();
  return {
    ...actual,
    getRecapArtifacts: vi.fn(async () => ({ records: [] })),
    postWorldGraphProjection: vi.fn(async () => {
      throw new actual.LiveApiError("world graph unavailable", 404, {
        code: "world_graph_unavailable",
      });
    }),
  };
});

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

const innResolution: PlanReferenceResolution = {
  kind: "graph-node",
  locator: "dmb-node:location-inn",
  refType: "location",
  refId: "location-inn",
  graphObject: buildGraphObjectCardFromNodeView({
    ...bubblesNode,
    node_id: "location-inn",
    label: "Inn",
    kind: "location",
    role: "location",
    adjacency: [],
    summary: "Meeting place.",
  }),
  graphNodeId: "location-inn",
  fallback: null,
  source: "world-graph",
  message: "Resolved Inn.",
  graphProjectionState: "ready",
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

describe("projectionBindings sibling topology", () => {
  it("renders Plan content and relationship traversal with container outside resolver providers", async () => {
    const user = userEvent.setup();
    const resolveRelationship = vi.fn(async () => innResolution);
    const openResolvedReference = vi.fn();
    const openTool = vi.fn();

    function SiblingPlanBinding() {
      const { registerPlanReferenceBinding } = useProjection();
      useEffect(() => {
        return registerPlanReferenceBinding({
          resolverState: "ready",
          resolveRelationship,
          openResolvedReference,
          openTool,
        });
      }, [registerPlanReferenceBinding]);
      return null;
    }

    render(
      <ProjectionProvider config={surfaceConfig}>
        <PlanGraphLensProvider planCampaignId={sessionDescriptor.campaignId}>
          <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
            <SiblingPlanBinding />
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

    await user.click(screen.getByRole("button", { name: /Open related object .*Inn/i }));
    await waitFor(() => {
      expect(resolveRelationship).toHaveBeenCalledTimes(1);
      expect(openResolvedReference).toHaveBeenCalledWith(
        innResolution,
        innResolution.graphProjectionState,
      );
    });
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

  it("replaces an open diagnostics registration without crashing", async () => {
    const user = userEvent.setup();
    const { buildGraphReviewDeltaIndex } = await import(
      "../graphReviewWorkbench/graphReviewDeltaUtils"
    );
    const { buildSourceSpanDeltaIndex } = await import(
      "../graphReviewWorkbench/graphReviewSourceSpanOverlayUtils"
    );
    const { buildVariantLiveInventoryIndex } = await import(
      "../graphReviewWorkbench/graphReviewVariantReferenceUtils"
    );

    function ReplaceableDiagnosticsBinding() {
      const { registerToolProjectionPayload } = useProjection();
      const [token, setToken] = useState(0);
      useEffect(() => {
        const payload: GraphReviewDiagnosticsProjectionPayload = {
          campaignId: "longmont-c2",
          sessionId: "session-21",
          liveRun: null,
          projection: null,
          projectionStatus: "idle",
          compareStatus: "idle",
          compare: null,
          compareError: token === 0 ? "first" : "second",
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
          selectedDeltaNodeId: null,
          setSelectedEvidenceDeltaId: () => undefined,
          selectedEvidenceDeltaId: null,
          selectedSourceSpanId: null,
          setSelectedSourceSpanId: () => undefined,
          evidenceSelection: null,
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
        };
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
    expect(
      await screen.findByText(/Select a live run with a projection to inspect diagnostics/i),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Replace payload" }));
    expect(
      screen.getByText(/Select a live run with a projection to inspect diagnostics/i),
    ).toBeInTheDocument();
  });
});
