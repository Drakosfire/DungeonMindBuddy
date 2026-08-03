import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import type { GraphProjectionNodeView } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import type { SurfaceConfig } from "../types";
import { LegacyProjectionHostAdapter } from "./LegacyProjectionHostAdapter";
import {
  INGEST_PROJECTION_DEFINITIONS,
  IngestProjectionCatalogRegistration,
} from "./IngestProjectionCatalogRegistration";
import {
  PLAN_PROJECTION_DEFINITIONS,
  PlanProjectionCatalogRegistration,
} from "./PlanProjectionCatalogRegistration";
import { AgentInteractionProjectionTestHost } from "./projectionTestHost";
import { useProjection } from "./projectionContext";
import { GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID } from "./projectionBindings";
import { GraphReviewDiagnosticsProjectionBinding } from "../graphReviewWorkbench/GraphReviewDiagnosticsProjectionBinding";
import { GraphReviewLiveStateProvider } from "../graphReviewWorkbench/GraphReviewLiveStateContext";

vi.mock("../../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/liveApi")>();
  return {
    ...actual,
    getRecapArtifacts: vi.fn(async () => ({ records: [] })),
  };
});

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

function OpenReferenceButton() {
  const { openGraphReference } = useProjection();
  return (
    <button
      type="button"
      onClick={() =>
        openGraphReference({
          resolution: {
            kind: "resolved_graph",
            locator: `dmb-node:${bubblesNode.node_id}`,
            reference: referenceFromGraphNode(bubblesNode),
            graphObject: buildGraphObjectCardFromNodeView(bubblesNode),
            graphNodeId: bubblesNode.node_id,
            message: `Resolved graph node ${bubblesNode.label}.`,
            projectionState: "ready",
          } satisfies GraphReferenceResolution,
          projectionState: "ready",
        })
      }
    >
      Open Bubbles
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
});

describe("PlanProjectionCatalogRegistration integration", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/plan");
  });

  it("renders recap through catalog resolution", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={planSurfaceConfig}>
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    expect(await screen.findByText("Focus session")).toBeInTheDocument();
  });

  it("renders graph-reference content through catalog resolution", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={planSurfaceConfig}>
        <OpenReferenceButton />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Open Bubbles" }));
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
  it("shows unavailable when diagnostics payload binding is missing", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={ingestSurfaceConfig}>
        <IngestProjectionCatalogRegistration
          surfaceId="ingest"
          toolDescriptors={ingestSurfaceConfig.tools.map((tool) => ({
            id: tool.id,
            kind: "tool" as const,
            preferredSize: tool.size,
            bindingIds: [],
          }))}
        />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Diagnostics" }));
    await waitFor(() => {
      expect(screen.getByText("Projection unavailable.")).toBeInTheDocument();
    });
  });

  it("renders diagnostics panel when the current payload binding is present", async () => {
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
    expect(
      await screen.findByText(/Select a live run with a projection to inspect diagnostics/i),
    ).toBeInTheDocument();
  });
});
