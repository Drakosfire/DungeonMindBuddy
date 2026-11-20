import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useLayoutEffect, useState, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import type { GraphProjectionNodeView } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import type { SurfaceConfig } from "../types";
import {
  GRAPH_REFERENCE_BINDING_ID,
  GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID,
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
  GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
  readGraphReferenceBinding,
  readGraphReferenceProjectionStateBinding,
  readGraphReferenceResolutionBinding,
  sameStringSetMembership,
  stabilizeStringSetMembership,
  type GraphReviewDiagnosticsProjectionPayload,
  type PlanReferenceProjectionBinding as PlanBinding,
} from "./projectionBindings";
import * as graphReferenceProjectionBindings from "../../graphReference/projectionBindings";
import { LegacyProjectionHostAdapter } from "./LegacyProjectionHostAdapter";
import { AgentInteractionProjectionTestHost } from "./projectionTestHost";
import { AgentInteractionProvider, useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../../surfaceInteraction/types";
import { useProjection } from "./projectionContext";
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
  };
});

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });

// Binding lease tests exercise the explicit native capability, not retired Plan inference.
const nativeReferencePublication: SurfaceInteractionPublication = {
  surfaceId: "build",
  label: "Build",
  identity: buildSurfaceInteractionIdentity({ surfaceId: "build", instanceParts: ["binding-test"] }),
  canvas: null,
  agentContext: null,
  tools: [],
  editCommands: [],
  projections: [{ id: GRAPH_REFERENCE_PROJECTION_ID, kind: "content", preferredSize: "wide", bindingIds: [] }],
  projectionBindings: [],
};

function NativeReferencePublisher({ children }: { children: ReactNode }) {
  const { publishSurfaceInteractionPublication } = useAgentInteraction();
  useLayoutEffect(() => publishSurfaceInteractionPublication(nativeReferencePublication), [publishSurfaceInteractionPublication]);
  return children;
}

function NativeReferenceBindingTestHost({ children }: { children: ReactNode }) {
  return <AgentInteractionProvider><NativeReferencePublisher>{children}</NativeReferencePublisher></AgentInteractionProvider>;
}

const ingestSurfaceConfig: SurfaceConfig = {
  id: "ingest",
  label: "Ingest",
  context: {
    campaignId: "longmont-c2",
    headerLabel: "Memory Ingest",
    ingestSession: 21,
    liveSession: 22,
  },
  tools: [
    { id: "ingest-recap", label: "Ingest Recap", size: "wide" },
    { id: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, label: "Diagnostics", size: "wide" },
  ],
  canvas: { documentId: null },
  theme: {},
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

const innResolution: GraphReferenceResolution = {
  kind: "resolved_graph",
  locator: "dmb-node:location-inn",
  reference: referenceFromGraphNode(innNode),
  graphObject: buildGraphObjectCardFromNodeView(innNode),
  graphNodeId: "location-inn",
  message: "Resolved Inn.",
  projectionState: "ready",
};

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
  const { graphReferenceBinding } = useProjection();
  useEffect(() => {
    onBinding(graphReferenceBinding);
  }, [onBinding, graphReferenceBinding]);
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
  it("renders Graph Review diagnostics with container outside live-state provider", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={ingestSurfaceConfig}>
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
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Open Diagnostics" }));
    expect(
      await screen.findByText(/Select a live run with a projection to inspect diagnostics/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-diagnostics-unavailable")).not.toBeInTheDocument();
  });

  it("blocks superseded binding completion before provider rerender", async () => {
    const seen: Array<PlanBinding | null> = [];
    let register: ((binding: PlanBinding) => () => void) | null = null;

    function Registrar() {
      const { registerGraphReferenceBinding } = useProjection();
      useEffect(() => {
        register = registerGraphReferenceBinding;
      }, [registerGraphReferenceBinding]);
      return <BindingReader onBinding={(binding) => seen.push(binding)} />;
    }

    render(
      <NativeReferenceBindingTestHost>
        <Registrar />
        <LegacyProjectionHostAdapter />
      </NativeReferenceBindingTestHost>,
    );

    await waitFor(() => {
      expect(register).not.toBeNull();
    });

    const openFromFirst = vi.fn();
    const openFromSecond = vi.fn();
    const bindingA: PlanBinding = {
      resolverState: "ready",
      resolveRelationship: vi.fn(),
      openResolvedReference: openFromFirst,
      openTool: vi.fn(),
    };
    const bindingB: PlanBinding = {
      resolverState: "ready",
      resolveRelationship: vi.fn(),
      openResolvedReference: openFromSecond,
      openTool: vi.fn(),
    };

    await act(async () => {
      register!(bindingA);
    });
    await waitFor(() => {
      expect(seen.at(-1)?.resolverState).toBe("ready");
    });
    const wrapperA = seen.at(-1);
    expect(wrapperA).not.toBeNull();

    // Register B and complete through A in the same turn — before React can publish wrapper B.
    act(() => {
      register!(bindingB);
      wrapperA!.openResolvedReference(innResolution, "ready");
    });

    expect(openFromFirst).not.toHaveBeenCalled();
    expect(openFromSecond).not.toHaveBeenCalled();
  });

  it("blocks unregistered binding completion before provider rerender", async () => {
    const seen: Array<PlanBinding | null> = [];
    let register: ((binding: PlanBinding) => () => void) | null = null;

    function Registrar() {
      const { registerGraphReferenceBinding } = useProjection();
      useEffect(() => {
        register = registerGraphReferenceBinding;
      }, [registerGraphReferenceBinding]);
      return <BindingReader onBinding={(binding) => seen.push(binding)} />;
    }

    render(
      <NativeReferenceBindingTestHost>
        <Registrar />
        <LegacyProjectionHostAdapter />
      </NativeReferenceBindingTestHost>,
    );

    await waitFor(() => {
      expect(register).not.toBeNull();
    });

    const openFromFirst = vi.fn();
    const bindingA: PlanBinding = {
      resolverState: "ready",
      resolveRelationship: vi.fn(),
      openResolvedReference: openFromFirst,
      openTool: vi.fn(),
    };

    let cleanupA: (() => void) | undefined;
    await act(async () => {
      cleanupA = register!(bindingA);
    });
    await waitFor(() => {
      expect(seen.at(-1)?.openResolvedReference).toEqual(expect.any(Function));
    });
    const wrapperA = seen.at(-1);
    expect(wrapperA).not.toBeNull();

    act(() => {
      cleanupA!();
      wrapperA!.openResolvedReference(innResolution, "ready");
    });

    expect(openFromFirst).not.toHaveBeenCalled();
  });

  it("does not let stale cleanup erase a newer registration", async () => {
    const seen: Array<PlanBinding | null> = [];
    let register: ((binding: PlanBinding) => () => void) | null = null;

    function Registrar() {
      const { registerGraphReferenceBinding } = useProjection();
      useEffect(() => {
        register = registerGraphReferenceBinding;
      }, [registerGraphReferenceBinding]);
      return <BindingReader onBinding={(binding) => seen.push(binding)} />;
    }

    render(
      <NativeReferenceBindingTestHost>
        <Registrar />
        <LegacyProjectionHostAdapter />
      </NativeReferenceBindingTestHost>,
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
      <AgentInteractionProjectionTestHost config={ingestSurfaceConfig}>
        <ReplaceableDiagnosticsBinding />
        <OpenDiagnosticsButton />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
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

describe("Plan re-exports graphReference projectionBindings", () => {
  it("re-exports neutral binding IDs from graphReference", () => {
    expect(GRAPH_REFERENCE_RESOLUTION_BINDING_ID).toBe(
      graphReferenceProjectionBindings.GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
    );
    expect(GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID).toBe(
      graphReferenceProjectionBindings.GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID,
    );
    expect(GRAPH_REFERENCE_BINDING_ID).toBe(
      graphReferenceProjectionBindings.GRAPH_REFERENCE_BINDING_ID,
    );
  });

  it("re-exports graph reference readers from graphReference", () => {
    expect(readGraphReferenceResolutionBinding).toBe(
      graphReferenceProjectionBindings.readGraphReferenceResolutionBinding,
    );
    expect(readGraphReferenceProjectionStateBinding).toBe(
      graphReferenceProjectionBindings.readGraphReferenceProjectionStateBinding,
    );
    expect(readGraphReferenceBinding).toBe(
      graphReferenceProjectionBindings.readGraphReferenceBinding,
    );
  });
});

describe("projection catalog membership helpers", () => {
  it("treats equal Sets as the same membership regardless of insertion order", () => {
    expect(sameStringSetMembership(new Set(["a", "b"]), new Set(["b", "a"]))).toBe(true);
    expect(sameStringSetMembership(new Set(["a"]), new Set(["a", "b"]))).toBe(false);
  });

  it("does not collapse delimiter-containing IDs into multi-ID membership", () => {
    const composed = new Set(["a\0b"]);
    const splitPair = new Set(["a", "b"]);
    expect(sameStringSetMembership(composed, splitPair)).toBe(false);

    const stable = stabilizeStringSetMembership(new Set(), ["a\0b"]);
    expect(stable.has("a\0b")).toBe(true);
    expect(stable.has("a")).toBe(false);
    expect(stable.has("b")).toBe(false);
    expect(stabilizeStringSetMembership(stable, ["a\0b"])).toBe(stable);
    expect(stabilizeStringSetMembership(stable, ["a", "b"])).not.toBe(stable);
  });
});
