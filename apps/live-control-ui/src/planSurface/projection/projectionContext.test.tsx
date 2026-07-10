import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphProjectionNodeView } from "../../api/types";
import { ProjectionProvider, useProjection } from "./projectionContext";
import type { SurfaceConfig } from "../types";
import type { PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";

const sessionDescriptor = {
  surfaceId: "plan" as const,
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  prepSession: 23,
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
  sourceStatusKind: "unknown" as const,
  planningDocument: {
    documentId: "longmont-c2-session-23-prep",
    title: "C2 Session 23 Prep",
    targetRelpath: "corpus/example.md",
    storageKey: "storage-key",
    status: "local_draft" as const,
  },
};

const surfaceConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    headerLabel: "Longmont C2",
    prepSession: 23,
    ingestSession: 21,
    liveSession: 22,
  },
  tools: [{ id: "statblock", label: "Statblock", size: "wide" }],
  canvas: { documentId: "longmont-c2-session-23-prep" },
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
      <button
        type="button"
        onClick={() => {
          const resolution: PlanReferenceResolution = {
            kind: "graph-node",
            locator: "dmb-node:location-inn",
            graphObject: buildGraphObjectCardFromNodeView(innNode),
            graphNodeId: "location-inn",
            fallback: null,
            source: "union-supergraph",
            graphProjectionState: "ready",
          };
          openPlanReferenceResolution(resolution, "ready");
        }}
      >
        Open related
      </button>
      <p data-testid="active-title">{active?.title ?? "none"}</p>
      <p data-testid="active-kind">{activePlanReference?.kind ?? "none"}</p>
      <p data-testid="active-node">{activePlanReference?.graphNodeId ?? "none"}</p>
      <p data-testid="glance-only">{String(active?.kind === "content" ? active.glanceOnly : "n/a")}</p>
    </div>
  );
}

describe("projectionContext openPlanReferenceResolution", () => {
  it("opens a Plan reference resolution without a chip click", async () => {
    const user = userEvent.setup();
    render(
      <ProjectionProvider config={surfaceConfig}>
        <Probe />
      </ProjectionProvider>,
    );

    expect(screen.getByTestId("active-title")).toHaveTextContent("none");

    await user.click(screen.getByRole("button", { name: "Open related" }));

    await waitFor(() => {
      expect(screen.getByTestId("active-title")).toHaveTextContent("Inn");
    });
    expect(screen.getByTestId("active-kind")).toHaveTextContent("graph-node");
    expect(screen.getByTestId("active-node")).toHaveTextContent("location-inn");
    expect(screen.getByTestId("glance-only")).toHaveTextContent("false");
  });
});
