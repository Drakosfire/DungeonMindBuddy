import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphProjectionNodeView } from "../../api/types";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import { renderContentProjection } from "./projectionRegistry";
import type { PlanSurfaceConfig } from "../types";
import { FIXTURE_DOC_ID, fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";

const node: GraphProjectionNodeView = {
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

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });

const config = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    liveSession: 22,
    ingestSession: 21,
    headerLabel: sessionDescriptor.planningDocument.title,
  },
  sessionDescriptor,
  tools: [],
  canvas: { documentId: FIXTURE_DOC_ID },
  theme: { themeId: "command" },
} satisfies PlanSurfaceConfig;

describe("renderContentProjection", () => {
  it("renders PlanReferenceObjectCard instead of SelectedObjectCard for graph hits", () => {
    render(
      renderContentProjection(
        {
          kind: "resolved_graph",
          locator: "dmb-node:location-north-gate",
          reference: referenceFromGraphNode(node),
          graphObject: buildGraphObjectCardFromNodeView(node),
          graphNodeId: "location-north-gate",
          projectionState: "ready",
        } satisfies GraphReferenceResolution,
        config,
        "ready",
      ),
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
