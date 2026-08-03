import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import type { GraphProjectionNodeView } from "../../api/types";
import { FIXTURE_DOC_ID, fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import type { SurfaceConfig } from "../types";
import { LegacyProjectionHostAdapter } from "./LegacyProjectionHostAdapter";
import { AgentInteractionProjectionTestHost } from "./projectionTestHost";
import { useProjection } from "./projectionContext";
import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import {
  GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID,
  GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
  PLAN_CONTEXT_BINDING_ID,
  PLAN_SURFACE_CONFIG_BINDING_ID,
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
} from "./projectionBindings";
import { GraphReviewDiagnosticsProjectionBinding } from "../graphReviewWorkbench/GraphReviewDiagnosticsProjectionBinding";
import { GraphReviewLiveStateProvider } from "../graphReviewWorkbench/GraphReviewLiveStateContext";

vi.mock("../../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/liveApi")>();
  return {
    ...actual,
    getRecapArtifacts: vi.fn(async () => ({ records: [] })),
  };
});

vi.mock("../../modules/PartyRegistryModule", () => ({
  PartyRegistryModule: vi.fn(({ context }: { context: { campaignId: string } }) => (
    <div data-testid="party-registry-module">{context.campaignId}</div>
  )),
}));
vi.mock("../../surface/modules/StatblockWorkbenchModule", () => ({
  StatblockWorkbenchModule: vi.fn(() => <div data-testid="statblock-module" />),
}));
vi.mock("../graphPreview/RecapGraphModule", () => ({
  RecapGraphModule: vi.fn(({ context }: { context: { campaignId: string } }) => (
    <div data-testid="recap-module">{context.campaignId}</div>
  )),
}));
vi.mock("../graphPreview/GraphPreviewModule", () => ({
  GraphPreviewModule: vi.fn(({ context }: { context: { campaignId: string } }) => (
    <div data-testid="graph-preview-module">{context.campaignId}</div>
  )),
}));
vi.mock("../graphGoldReview/GraphGoldReviewModule", () => ({
  GraphGoldReviewModule: vi.fn(({ context }: { context: { campaignId: string } }) => (
    <div data-testid="graph-gold-review-module">{context.campaignId}</div>
  )),
}));
vi.mock("../manualReview/ManualReviewModule", () => ({
  ManualReviewModule: vi.fn(() => <div data-testid="manual-review-module" />),
}));
vi.mock("../../modules/IngestionModule", () => ({
  IngestionModule: vi.fn(
    ({ campaignId, session }: { campaignId: string; session: number | null }) => (
      <div data-testid="ingest-recap-module">{`${campaignId}:${session}`}</div>
    ),
  ),
}));

const diagnosticsPanelSpy = vi.fn();
vi.mock("../graphReviewWorkbench/GraphReviewDiagnosticsToolPanel", () => ({
  GraphReviewDiagnosticsToolPanel: (props: { payload: unknown }) => {
    diagnosticsPanelSpy(props);
    return <div data-testid="diagnostics-panel">Diagnostics panel</div>;
  },
}));

// Import after mocks so definition.render factories bind to mocked modules.
const { PLAN_PROJECTION_DEFINITIONS, PlanProjectionCatalogRegistration } = await import(
  "./PlanProjectionCatalogRegistration"
);
const { INGEST_PROJECTION_DEFINITIONS } = await import("./IngestProjectionCatalogRegistration");
const { RecapGraphModule } = await import("../graphPreview/RecapGraphModule");
const { PartyRegistryModule } = await import("../../modules/PartyRegistryModule");
const { StatblockWorkbenchModule } = await import("../../surface/modules/StatblockWorkbenchModule");
const { GraphPreviewModule } = await import("../graphPreview/GraphPreviewModule");
const { GraphGoldReviewModule } = await import("../graphGoldReview/GraphGoldReviewModule");
const { ManualReviewModule } = await import("../manualReview/ManualReviewModule");
const { IngestionModule } = await import("../../modules/IngestionModule");

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });

const planSurfaceConfig: SurfaceConfig = {
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
    { id: "party-registry", label: "Party Registry", size: "wide" },
    { id: "statblock", label: "Statblock", size: "wide" },
  ],
  canvas: { documentId: sessionDescriptor.planningDocument.documentId },
  theme: {},
  sessionDescriptor,
};

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

const bubblesNode: GraphProjectionNodeView = {
  node_id: "creature:bubbles",
  label: "Bubbles the Float Goat",
  kind: "creature",
  role: "creature",
  aliases: [],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "A float goat rescued from the flooded river.",
};

const northGateNode: GraphProjectionNodeView = {
  node_id: "location-north-gate",
  label: "North Reach Gate",
  kind: "location",
  role: "location",
  aliases: [],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "The northern gate of Mireward Reach.",
};

function OpenReferenceButton({
  resolution,
}: {
  resolution: GraphReferenceResolution;
}) {
  const { openGraphReference } = useProjection();
  return (
    <button
      type="button"
      onClick={() =>
        openGraphReference({
          resolution,
          projectionState: "ready",
        })
      }
    >
      Open reference
    </button>
  );
}

describe("projection catalog registration inventory", () => {
  it("exports the exact Plan projection definition inventory", () => {
    expect(PLAN_PROJECTION_DEFINITIONS.map((entry) => entry.projectionId)).toEqual([
      "recap",
      "party-registry",
      "statblock",
      "graph-preview",
      "graph-gold-review",
      "manual-review",
      GRAPH_REFERENCE_PROJECTION_ID,
    ]);
  });

  it("exports the exact Ingest projection definition inventory", () => {
    expect(INGEST_PROJECTION_DEFINITIONS.map((entry) => entry.projectionId)).toEqual([
      "ingest-recap",
      GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
    ]);
  });

  it("binds an explicit renderer factory on every Plan and Ingest definition", () => {
    for (const definition of [...PLAN_PROJECTION_DEFINITIONS, ...INGEST_PROJECTION_DEFINITIONS]) {
      expect(typeof definition.render).toBe("function");
    }
  });
});

describe("explicit Plan definition renderer factories", () => {
  const planContext = planSurfaceConfig.context!;

  beforeEach(() => {
    vi.mocked(RecapGraphModule).mockClear();
    vi.mocked(PartyRegistryModule).mockClear();
    vi.mocked(StatblockWorkbenchModule).mockClear();
    vi.mocked(GraphPreviewModule).mockClear();
    vi.mocked(GraphGoldReviewModule).mockClear();
    vi.mocked(ManualReviewModule).mockClear();
  });

  it.each([
    { id: "recap", testId: "recap-module", module: () => RecapGraphModule },
    { id: "party-registry", testId: "party-registry-module", module: () => PartyRegistryModule },
    { id: "statblock", testId: "statblock-module", module: () => StatblockWorkbenchModule },
    { id: "graph-preview", testId: "graph-preview-module", module: () => GraphPreviewModule },
    { id: "graph-gold-review", testId: "graph-gold-review-module", module: () => GraphGoldReviewModule },
    { id: "manual-review", testId: "manual-review-module", module: () => ManualReviewModule },
  ] as const)("maps $id to its concrete module via definition.render", ({ id, testId, module }) => {
    const definition = PLAN_PROJECTION_DEFINITIONS.find((entry) => entry.projectionId === id);
    expect(definition).toBeDefined();
    render(
      <>
        {definition!.render({
          projectionId: id,
          active: { kind: "tool", key: id, size: "wide", title: id },
          bindings: { [PLAN_CONTEXT_BINDING_ID]: planContext },
        })}
      </>,
    );
    expect(screen.getByTestId(testId)).toBeInTheDocument();
    expect(module()).toHaveBeenCalled();
    // Cross-check: sibling modules must not be selected by this factory.
    const others = [
      RecapGraphModule,
      PartyRegistryModule,
      StatblockWorkbenchModule,
      GraphPreviewModule,
      GraphGoldReviewModule,
      ManualReviewModule,
    ].filter((candidate) => candidate !== module());
    for (const other of others) {
      expect(other).not.toHaveBeenCalled();
    }
  });

  it("renders graph-reference as PlanReferenceObjectCard with memory tools and ingest session link", () => {
    const definition = PLAN_PROJECTION_DEFINITIONS.find(
      (entry) => entry.projectionId === GRAPH_REFERENCE_PROJECTION_ID,
    );
    expect(definition).toBeDefined();
    const resolution = {
      kind: "resolved_graph",
      locator: "dmb-node:location-north-gate",
      reference: referenceFromGraphNode(northGateNode),
      graphObject: buildGraphObjectCardFromNodeView(northGateNode),
      graphNodeId: "location-north-gate",
      projectionState: "ready",
    } satisfies GraphReferenceResolution;
    const config = {
      id: "plan",
      label: "Plan",
      context: planContext,
      sessionDescriptor,
      tools: [],
      canvas: { documentId: FIXTURE_DOC_ID },
      theme: { themeId: "command" },
    } satisfies SurfaceConfig;

    render(
      <>
        {definition!.render({
          projectionId: GRAPH_REFERENCE_PROJECTION_ID,
          active: {
            kind: "content",
            key: "location-north-gate",
            size: "wide",
            title: "North Reach Gate",
          },
          bindings: {
            [PLAN_SURFACE_CONFIG_BINDING_ID]: config,
            [GRAPH_REFERENCE_RESOLUTION_BINDING_ID]: resolution,
          },
        })}
      </>,
    );

    expect(screen.getByLabelText(/North Reach Gate graph object/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Actions" })).not.toBeInTheDocument();
    expect(screen.getByText("Memory tools")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Review memory in \/ingest/i })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-21",
    );
    expect(screen.queryByLabelText(/selected object/i)).not.toBeInTheDocument();
  });
});

describe("explicit Ingest definition renderer factories", () => {
  beforeEach(() => {
    vi.mocked(IngestionModule).mockClear();
    diagnosticsPanelSpy.mockClear();
  });

  it("maps ingest-recap to IngestionModule via definition.render", () => {
    const definition = INGEST_PROJECTION_DEFINITIONS.find(
      (entry) => entry.projectionId === "ingest-recap",
    );
    expect(definition).toBeDefined();
    render(
      <>
        {definition!.render({
          projectionId: "ingest-recap",
          active: { kind: "tool", key: "ingest-recap", size: "wide", title: "Ingest Recap" },
          bindings: { [PLAN_CONTEXT_BINDING_ID]: ingestSurfaceConfig.context },
        })}
      </>,
    );
    expect(screen.getByTestId("ingest-recap-module")).toHaveTextContent("longmont-c2:21");
    expect(IngestionModule).toHaveBeenCalled();
    expect(diagnosticsPanelSpy).not.toHaveBeenCalled();
  });

  it("maps graph-review-diagnostics to GraphReviewDiagnosticsToolPanel via definition.render", () => {
    const definition = INGEST_PROJECTION_DEFINITIONS.find(
      (entry) => entry.projectionId === GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
    );
    expect(definition).toBeDefined();
    const payload = { campaignId: "longmont-c2", sessionId: "session-21" };
    render(
      <>
        {definition!.render({
          projectionId: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
          active: {
            kind: "tool",
            key: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
            size: "wide",
            title: "Diagnostics",
          },
          bindings: { [GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID]: payload },
        })}
      </>,
    );
    expect(screen.getByTestId("diagnostics-panel")).toBeInTheDocument();
    expect(diagnosticsPanelSpy).toHaveBeenCalledTimes(1);
    expect(IngestionModule).not.toHaveBeenCalled();
  });
});

describe("PlanProjectionCatalogRegistration integration", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/plan");
    vi.mocked(RecapGraphModule).mockClear();
  });

  it("renders recap through catalog resolution", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={planSurfaceConfig}>
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    expect(await screen.findByTestId("recap-module")).toBeInTheDocument();
  });

  it("renders graph-reference content through catalog resolution", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={planSurfaceConfig}>
        <OpenReferenceButton
          resolution={{
            kind: "resolved_graph",
            locator: `dmb-node:${bubblesNode.node_id}`,
            reference: referenceFromGraphNode(bubblesNode),
            graphObject: buildGraphObjectCardFromNodeView(bubblesNode),
            graphNodeId: bubblesNode.node_id,
            message: `Resolved graph node ${bubblesNode.label}.`,
            projectionState: "ready",
          }}
        />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Open reference" }));
    expect(await screen.findByRole("heading", { level: 4, name: "Bubbles the Float Goat" })).toBeInTheDocument();
  });

  it("registers only published tool descriptors", () => {
    const toolDescriptors = planSurfaceConfig.tools.map((tool) => ({
      id: tool.id,
      kind: "tool" as const,
      preferredSize: tool.size,
      bindingIds: [] as readonly string[],
    }));
    render(
      <AgentInteractionProjectionTestHost config={planSurfaceConfig}>
        <PlanProjectionCatalogRegistration surfaceId="plan" toolDescriptors={toolDescriptors} />
      </AgentInteractionProjectionTestHost>,
    );
    expect(PLAN_PROJECTION_DEFINITIONS.filter((entry) => entry.kind === "tool").length).toBeGreaterThan(
      toolDescriptors.length,
    );
  });
});

describe("IngestProjectionCatalogRegistration integration", () => {
  beforeEach(() => {
    diagnosticsPanelSpy.mockClear();
  });

  it("reaches binding_missing with exactly one registration when diagnostics payload is absent", async () => {
    const user = userEvent.setup();
    const statuses: string[] = [];

    function ResolveProbe() {
      const { active, resolveProjectionCatalog, projectionSurface } = useProjection();
      useEffect(() => {
        if (!active || active.key !== GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID) return;
        const context = projectionSurface?.publication.config.context;
        const resolution = resolveProjectionCatalog({
          projectionId: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
          active,
          bindings: context ? { [PLAN_CONTEXT_BINDING_ID]: context } : {},
        });
        statuses.push(resolution.status);
      }, [active, projectionSurface, resolveProjectionCatalog]);
      return null;
    }

    render(
      <AgentInteractionProjectionTestHost config={ingestSurfaceConfig}>
        <ResolveProbe />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Diagnostics" }));
    await waitFor(() => {
      expect(statuses).toContain("binding_missing");
    });
    expect(statuses.every((status) => status !== "duplicate_registration")).toBe(true);
    expect(diagnosticsPanelSpy).not.toHaveBeenCalled();
    expect(screen.getByText("Projection unavailable.")).toBeInTheDocument();
  });

  it("transitions the same registration to ready when the diagnostics payload is present", async () => {
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
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Diagnostics" }));
    expect(await screen.findByTestId("diagnostics-panel")).toBeInTheDocument();
    expect(diagnosticsPanelSpy).toHaveBeenCalled();
  });
});
