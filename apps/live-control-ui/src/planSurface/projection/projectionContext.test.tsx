import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphProjectionNodeView } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import { ProjectionProvider, useProjection } from "./projectionContext";
import type { SurfaceConfig } from "../types";
import type { PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";

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
  tools: [{ id: "statblock", label: "Statblock", size: "wide" }],
  canvas: { documentId: sessionDescriptor.planningDocument.documentId },
  theme: {},
  sessionDescriptor,
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

function Probe() {
  const { active, activePlanReference, openPlanReferenceResolution } = useProjection();
  return (
    <div>
      <p data-testid="active-key">{active?.key ?? "none"}</p>
      <p data-testid="active-plan-ref">{activePlanReference?.message ?? "none"}</p>
      <button
        type="button"
        onClick={() =>
          openPlanReferenceResolution(
            {
              kind: "graph-node",
              locator: `dmb-node:${innNode.node_id}`,
              refType: innNode.kind,
              refId: innNode.node_id,
              graphObject: buildGraphObjectCardFromNodeView(innNode),
              graphNodeId: innNode.node_id,
              fallback: null,
              source: "world-graph",
              message: `Resolved graph node ${innNode.label}.`,
              graphProjectionState: "ready",
            } satisfies PlanReferenceResolution,
            "ready",
          )
        }
      >
        Open graph node
      </button>
    </div>
  );
}

describe("projectionContext", () => {
  it("opens plan reference resolution into content projection", async () => {
    const user = userEvent.setup();
    render(
      <ProjectionProvider config={surfaceConfig}>
        <Probe />
      </ProjectionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Open graph node" }));

    await waitFor(() => {
      expect(screen.getByTestId("active-key")).toHaveTextContent("location");
    });
    expect(screen.getByTestId("active-plan-ref")).toHaveTextContent("Resolved graph node Inn.");
  });
});
