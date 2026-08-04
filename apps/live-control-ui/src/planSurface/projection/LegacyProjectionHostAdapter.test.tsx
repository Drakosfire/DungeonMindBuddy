import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import { getRecapArtifacts } from "../../api/liveApi";
import type { GraphProjectionNodeView, RecapArtifactsListResponse } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import type { SurfaceConfig } from "../types";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import type { SurfaceInteractionPublication } from "../../surfaceInteraction/types";
import { BUILD_REFERENCE_SEARCH_PROJECTION_ID } from "../../buildSurface/reference/buildReferenceIds";
import { LegacyProjectionHostAdapter } from "./LegacyProjectionHostAdapter";
import {
  AgentInteractionProvider,
  useAgentInteraction,
} from "../../agentInteraction/AgentInteractionProvider";
import { buildPlanSurfaceIdentity } from "../../agentInteraction/projectionSurfacePublication";
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

function StubGraphReferenceBinding() {
  const { registerGraphReferenceBinding, openGraphReference, openTool } = useProjection();
  useEffect(() => {
    return registerGraphReferenceBinding({
      resolverState: "ready",
      resolveRelationship: vi.fn(async () => ({
        kind: "resolved_graph" as const,
        locator: `dmb-node:${bubblesNode.node_id}`,
        reference: referenceFromGraphNode(bubblesNode),
        graphObject: buildGraphObjectCardFromNodeView(bubblesNode),
        graphNodeId: bubblesNode.node_id,
        message: `Resolved graph node ${bubblesNode.label}.`,
        projectionState: "ready",
      })),
      openResolvedReference: (nextResolution, projectionState) => {
        openGraphReference({
          resolution: nextResolution,
          projectionState: projectionState ?? "ready",
        });
      },
      openTool,
    });
  }, [openGraphReference, openTool, registerGraphReferenceBinding]);
  return null;
}

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

describe("LegacyProjectionHostAdapter content reference chrome", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/plan");
  });

  it("renders no projection chrome when the app host is inactive", () => {
    render(
      <AgentInteractionProvider>
        <LegacyProjectionHostAdapter />
      </AgentInteractionProvider>,
    );

    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveClass("surface-projection-open");
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
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
  });

  function NativeBuildPublisher({ publication }: { publication: SurfaceInteractionPublication }) {
    const { publishSurfaceInteractionPublication } = useAgentInteraction();
    useEffect(() => {
      return publishSurfaceInteractionPublication(publication);
    }, [publication, publishSurfaceInteractionPublication]);
    return null;
  }

  it("mounts projection host for native Build publication with projection tools", async () => {
    const publication: SurfaceInteractionPublication = {
      surfaceId: "build",
      label: "Build",
      identity: buildSurfaceInteractionIdentity({
        surfaceId: "build",
        instanceParts: ["build", "adapter-native-test"],
      }),
      canvas: null,
      agentContext: null,
      tools: [
        {
          id: "build-find-existing-object",
          label: "Find existing object",
          placement: {
            groupId: "build-world-reference",
            groupLabel: "World references",
            groupOrder: 10,
            itemOrder: 0,
          },
          availability: { status: "enabled" },
          activation: {
            kind: "projection",
            projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
          },
        },
      ],
      editCommands: [],
      projections: [
        {
          id: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
          kind: "tool",
          preferredSize: "wide",
          bindingIds: [],
        },
        {
          id: GRAPH_REFERENCE_PROJECTION_ID,
          kind: "content",
          preferredSize: "wide",
          bindingIds: [],
        },
      ],
      projectionBindings: [],
    };

    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }

    render(
      <AgentInteractionProvider>
        <NativeBuildPublisher publication={publication} />
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProvider>,
    );

    act(() => {
      hostApi!.openTool("build-find-existing-object");
    });

    await waitFor(() => {
      expect(document.body).toHaveClass("surface-projection-open");
    });
    expect(document.querySelector(".surface-projection-host")).toBeTruthy();
    const navButton = screen.getByRole("button", { name: "Find existing object" });
    expect(navButton).toHaveAttribute("aria-pressed", "true");
    expect(navButton).toHaveClass("active");
  });

  it("renders no Tools toggle for a contradictory identity/config publication", () => {
    function ContradictoryPublisher() {
      const { publishProjectionSurface } = useAgentInteraction();
      useEffect(() => {
        return publishProjectionSurface({
          identity: { surfaceId: "plan", instanceKey: "plan\u001fcontradiction-ui" },
          config: {
            id: "ingest",
            label: "Mismatched",
            context: {
              campaignId: "longmont-c2",
              liveSession: 22,
              ingestSession: 21,
              headerLabel: "Ingest",
            },
            tools: [
              { id: "recap", label: "Recap", size: "wide" },
              { id: "ingest-recap", label: "Ingest Recap", size: "wide" },
            ],
            canvas: { documentId: null },
            theme: {},
          },
        });
      }, [publishProjectionSurface]);
      return null;
    }

    render(
      <AgentInteractionProvider>
        <ContradictoryPublisher />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProvider>,
    );

    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(document.querySelector("#surface-projection-drawer")).not.toBeInTheDocument();
    expect(document.body).not.toHaveClass("surface-projection-open");
  });

  it("clears body-open state when a same-identity contradictory update retains the open tool id", async () => {
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }

    render(
      <AgentInteractionProjectionTestHost config={surfaceConfig}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    act(() => {
      hostApi!.openTool("recap");
    });
    await waitFor(() => {
      expect(document.body).toHaveClass("surface-projection-open");
    });
    expect(hostApi!.active?.key).toBe("recap");

    act(() => {
      hostApi!.publishProjectionSurface({
        identity: buildPlanSurfaceIdentity({
          documentId: sessionDescriptor.planningDocument.documentId,
          campaignId: sessionDescriptor.campaignId,
          liveSession: surfaceConfig.context!.liveSession,
          memorySession: sessionDescriptor.memorySession,
        }),
        config: {
          id: "ingest",
          label: "Mismatched",
          context: surfaceConfig.context,
          tools: [{ id: "recap", label: "Recap", size: "wide" }],
          canvas: surfaceConfig.canvas,
          theme: {},
        },
      });
    });

    expect(hostApi!.projectionSurface?.projectionsEnabled).toBe(false);
    expect(hostApi!.active).toBeNull();
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveClass("surface-projection-open");
  });

  it("applies the active surface theme to the app-level drawer", async () => {
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }
    const themedConfig: SurfaceConfig = {
      ...surfaceConfig,
      theme: {
        themeId: "mireward",
        tokens: { "--projection-accent": "red" },
      },
    };

    render(
      <AgentInteractionProjectionTestHost config={themedConfig}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    act(() => {
      hostApi!.openTool("recap");
    });
    const host = document.querySelector(".surface-projection-host");
    expect(host).toHaveAttribute("data-md-theme", "mireward");
    expect(host).toHaveStyle({ "--projection-accent": "red" });
  });

  it("hides toolbox tool nav and uses Reference header without duplicating the object title", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={surfaceConfig}>
        <StubGraphReferenceBinding />
        <OpenReferenceButton />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Open Bubbles" }));

    await waitFor(() => {
      expect(document.querySelector(".surface-projection-host--reference")).toBeTruthy();
    });

    const nav = document.querySelector(".surface-projection-nav");
    expect(nav).toHaveAttribute("hidden");

    const drawer = document.querySelector("#surface-projection-drawer");
    expect(drawer).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: "Reference" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 4, name: "Bubbles the Float Goat" })).toBeInTheDocument();
  });

  it("renders content with a registered binding and does not crash", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProjectionTestHost config={surfaceConfig}>
        <StubGraphReferenceBinding />
        <OpenReferenceButton />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(screen.getByRole("button", { name: "Open Bubbles" }));
    expect(await screen.findByRole("heading", { level: 4, name: "Bubbles the Float Goat" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Open related object/i })).not.toBeInTheDocument();
  });

  it("updates drawer size class and accessibility label when the same tool revises its metadata", async () => {
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }
    const revisedConfig: SurfaceConfig = {
      ...surfaceConfig,
      tools: [
        { id: "recap", label: "Session Memory", size: "fullscreen" },
        { id: "party-registry", label: "Party Registry", size: "wide" },
        { id: "statblock", label: "Statblock", size: "wide" },
      ],
    };

    const { rerender } = render(
      <AgentInteractionProjectionTestHost config={surfaceConfig}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    act(() => {
      hostApi!.openTool("recap");
    });
    await waitFor(() => {
      expect(document.querySelector("#surface-projection-drawer")).toHaveAttribute(
        "aria-label",
        "Recap projection",
      );
    });
    const drawer = document.querySelector("#surface-projection-drawer");
    expect(drawer).toHaveClass("surface-projection-drawer--wide");
    expect(screen.getByRole("button", { name: "Recap", pressed: true })).toBeInTheDocument();

    rerender(
      <AgentInteractionProjectionTestHost config={revisedConfig}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await waitFor(() => {
      expect(document.querySelector("#surface-projection-drawer")).toHaveClass(
        "surface-projection-drawer--fullscreen",
      );
    });
    expect(document.querySelector("#surface-projection-drawer")).toHaveAttribute(
      "aria-label",
      "Session Memory projection",
    );
    expect(screen.getByRole("button", { name: "Session Memory", pressed: true })).toBeInTheDocument();
  });
});

describe("LegacyProjectionHostAdapter nav session lookup lease safety", () => {
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
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }
    const lookup = deferRecapArtifacts();
    render(
      <AgentInteractionProjectionTestHost config={campaignConfig("longmont-c2")}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    act(() => {
      hostApi!.openTool("recap");
    });
    await waitFor(() => {
      expect(document.body).toHaveClass("surface-projection-open");
    });
    await user.click(screen.getByRole("button", { name: "Recap" }));
    await act(async () => {
      lookup.resolve("session-23");
    });

    await waitFor(() => {
      expect(window.location.search).toContain("tool=recap");
    });
    expect(window.location.search).toContain("session=session-23");
    expect(document.body).toHaveClass("surface-projection-open");
  });

  it("ignores a campaign-A lookup that resolves after the host moved to campaign B", async () => {
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }
    const lookup = deferRecapArtifacts();
    const { rerender } = render(
      <AgentInteractionProjectionTestHost config={campaignConfig("longmont-c2")}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    act(() => {
      hostApi!.openTool("recap");
    });

    rerender(
      <AgentInteractionProjectionTestHost config={campaignConfig("other-campaign")}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await act(async () => {
      lookup.resolve("session-23");
    });

    // The stale campaign-A result must not touch campaign B's URL or open a projection.
    expect(window.location.search).not.toContain("session-23");
    expect(window.location.search).not.toContain("tool=recap");
    expect(document.body).not.toHaveClass("surface-projection-open");
  });

  it("does not commit ?tool= when openTool returns false after same-identity tool removal", async () => {
    const user = userEvent.setup();
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }
    const lookup = deferRecapArtifacts();
    const withRecap = campaignConfig("longmont-c2");
    const withoutRecap: SurfaceConfig = {
      ...withRecap,
      tools: [{ id: "statblock", label: "Statblock", size: "wide" }],
    };

    const { rerender } = render(
      <AgentInteractionProjectionTestHost config={withRecap}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    // Drive the async activator path (nav), not synchronous openTool.
    act(() => {
      hostApi!.openTool("statblock");
    });
    await waitFor(() => {
      expect(document.body).toHaveClass("surface-projection-open");
    });
    await user.click(screen.getByRole("button", { name: "Recap" }));

    rerender(
      <AgentInteractionProjectionTestHost config={withoutRecap}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
      </AgentInteractionProjectionTestHost>,
    );

    await act(async () => {
      lookup.resolve("session-23");
    });

    expect(window.location.search).not.toContain("tool=recap");
    expect(window.location.search).not.toContain("session-23");
    expect(hostApi!.active?.key).not.toBe("recap");
  });
});
