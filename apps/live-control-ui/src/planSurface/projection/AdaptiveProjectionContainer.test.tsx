import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { getRecapArtifacts } from "../../api/liveApi";
import type { GraphProjectionNodeView, RecapArtifactsListResponse } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import type { PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";
import type { SurfaceConfig } from "../types";
import { AdaptiveProjectionContainer } from "./AdaptiveProjectionContainer";
import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { AgentInteractionProjectionTestHost } from "./projectionTestHost";
import { useProjection } from "./projectionContext";

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
  it("renders no projection chrome when the app host is inactive", () => {
    render(
      <AgentInteractionProvider>
        <AdaptiveProjectionContainer />
      </AgentInteractionProvider>,
    );

    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveClass("plan-toolbox-open");
  });

  it("renders no projection chrome for Build's empty-tools publication", () => {
    const buildConfig: SurfaceConfig = {
      id: "build",
      label: "Build",
      context: null,
      tools: [],
      canvas: { documentId: null },
      theme: {},
    };

    render(
      <AgentInteractionProjectionTestHost config={buildConfig}>
        <AdaptiveProjectionContainer />
      </AgentInteractionProjectionTestHost>,
    );

    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
  });

  it("applies the active surface theme to the app-level drawer", async () => {
    const user = userEvent.setup();
    const themedConfig: SurfaceConfig = {
      ...surfaceConfig,
      theme: {
        themeId: "mireward",
        tokens: { "--projection-accent": "red" },
      },
    };

    render(
      <AgentInteractionProjectionTestHost config={themedConfig}>
        <AdaptiveProjectionContainer />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    const toolbox = document.querySelector(".plan-toolbox");
    expect(toolbox).toHaveAttribute("data-md-theme", "mireward");
    expect(toolbox).toHaveStyle({ "--projection-accent": "red" });
  });

  it("hides toolbox tool nav and uses Reference header without duplicating the object title", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={surfaceConfig}>
        <OpenReferenceButton />
        <AdaptiveProjectionContainer />
      </AgentInteractionProjectionTestHost>,
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

  it("renders content without a Plan binding and does not crash", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={surfaceConfig}>
        <OpenReferenceButton />
        <AdaptiveProjectionContainer />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Open Bubbles" }));
    expect(await screen.findByRole("heading", { level: 4, name: "Bubbles the Float Goat" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Open related object/i })).not.toBeInTheDocument();
  });
});

describe("AdaptiveProjectionContainer nav session lookup lease safety", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/plan");
    vi.mocked(getRecapArtifacts).mockReset();
  });

  function campaignConfig(campaignId: string): SurfaceConfig {
    const descriptor = fixturePlanSessionDescriptor({ campaignId, memorySession: 21 });
    return {
      ...surfaceConfig,
      context: {
        ...surfaceConfig.context!,
        campaignId,
        headerLabel: descriptor.planningDocument.title,
      },
      sessionDescriptor: descriptor,
    };
  }

  function deferRecapArtifacts() {
    let resolveLookup!: (value: RecapArtifactsListResponse) => void;
    vi.mocked(getRecapArtifacts).mockImplementation(
      () =>
        new Promise<RecapArtifactsListResponse>((resolve) => {
          resolveLookup = resolve;
        }),
    );
    return {
      resolve: (sessionId: string) =>
        resolveLookup({ records: [{ session_id: sessionId } as RecapArtifactsListResponse["records"][number]] }),
    };
  }

  it("writes the inferred session into the URL when the lookup resolves on the same surface", async () => {
    const user = userEvent.setup();
    const lookup = deferRecapArtifacts();
    render(
      <AgentInteractionProjectionTestHost config={campaignConfig("longmont-c2")}>
        <AdaptiveProjectionContainer />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await act(async () => {
      lookup.resolve("session-23");
    });

    await waitFor(() => {
      expect(window.location.search).toContain("tool=recap");
    });
    expect(window.location.search).toContain("session=session-23");
    expect(document.body).toHaveClass("plan-toolbox-open");
  });

  it("ignores a campaign-A lookup that resolves after the host moved to campaign B", async () => {
    const user = userEvent.setup();
    const lookup = deferRecapArtifacts();
    const { rerender } = render(
      <AgentInteractionProjectionTestHost config={campaignConfig("longmont-c2")}>
        <AdaptiveProjectionContainer />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));

    rerender(
      <AgentInteractionProjectionTestHost config={campaignConfig("other-campaign")}>
        <AdaptiveProjectionContainer />
      </AgentInteractionProjectionTestHost>,
    );

    await act(async () => {
      lookup.resolve("session-23");
    });

    // The stale campaign-A result must not touch campaign B's URL or open a projection.
    expect(window.location.search).not.toContain("session-23");
    expect(window.location.search).not.toContain("tool=recap");
    expect(document.body).not.toHaveClass("plan-toolbox-open");
  });
});
