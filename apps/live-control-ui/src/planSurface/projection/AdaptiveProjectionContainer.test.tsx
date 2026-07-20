import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphProjectionNodeView } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import type { PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";
import type { SurfaceConfig } from "../types";
import { AdaptiveProjectionContainer } from "./AdaptiveProjectionContainer";
import { ProjectionProvider, useProjection } from "./projectionContext";
import { PlanGraphReferenceResolverProvider } from "../reference/usePlanGraphReferenceResolver";

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
    { id: "party-registry", label: "Party Registry", size: "wide" },
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
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "A float goat rescued from the flooded river.",
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

describe("AdaptiveProjectionContainer content reference chrome", () => {
  it("hides toolbox tool nav and uses Reference header without duplicating the object title", async () => {
    const user = userEvent.setup();
    render(
      <ProjectionProvider config={surfaceConfig}>
        <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
          <OpenReferenceButton />
          <AdaptiveProjectionContainer config={surfaceConfig} />
        </PlanGraphReferenceResolverProvider>
      </ProjectionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Open Bubbles" }));

    await waitFor(() => {
      expect(document.querySelector(".plan-toolbox.tool-reference")).toBeTruthy();
    });

    const nav = document.querySelector(".plan-toolbox-nav");
    expect(nav).toHaveAttribute("hidden");

    const drawer = document.querySelector("#plan-toolbox-drawer");
    expect(drawer).toBeTruthy();
    expect(drawer?.querySelector(".plan-projection-header h2")?.textContent).toBe("Reference");
    expect(screen.getByRole("heading", { level: 4, name: "Bubbles the Float Goat" })).toBeInTheDocument();
  });
});
