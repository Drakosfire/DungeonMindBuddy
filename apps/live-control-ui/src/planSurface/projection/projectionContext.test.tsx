import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import type { GraphProjectionNodeView } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import { AgentInteractionProjectionTestHost } from "./projectionTestHost";
import { useProjection } from "./projectionContext";
import type { SurfaceConfig } from "../types";

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
  const { active, activeGraphReference, openGraphReference } = useProjection();
  return (
    <div>
      <p data-testid="active-key">{active?.key ?? "none"}</p>
      <p data-testid="active-plan-ref">{activeGraphReference?.message ?? "none"}</p>
      <button
        type="button"
        onClick={() =>
          openGraphReference({
            resolution: {
              kind: "resolved_graph",
              locator: `dmb-node:${innNode.node_id}`,
              reference: referenceFromGraphNode(innNode),
              graphObject: buildGraphObjectCardFromNodeView(innNode),
              graphNodeId: innNode.node_id,
              message: `Resolved graph node ${innNode.label}.`,
              projectionState: "ready",
            } satisfies GraphReferenceResolution,
            projectionState: "ready",
          })
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
      <AgentInteractionProjectionTestHost config={surfaceConfig}>
        <Probe />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Open graph node" }));

    await waitFor(() => {
      expect(screen.getByTestId("active-key")).toHaveTextContent("graph-node");
    });
    expect(screen.getByTestId("active-plan-ref")).toHaveTextContent("Resolved graph node Inn.");
  });
});
