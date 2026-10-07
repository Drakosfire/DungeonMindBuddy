import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { WorldGraphProjection } from "../../api/types";
import { useOptionalWorldGraphLensProjection } from "../../graphLens/useWorldGraphLensProjection";
import { useGraphNodeChipRuntime } from "../../graphReference/GraphNodeChipRuntime";
import { WorldPlanGraphReferenceActivationProvider, useWorldPlanGraphReferenceActivation } from "./WorldPlanGraphReferenceActivation";

vi.mock("../../graphLens/useWorldGraphLensProjection", () => ({
  useOptionalWorldGraphLensProjection: vi.fn(),
}));

vi.mock("../../graphReference/ResolvedGraphObjectProjection", () => ({
  ResolvedGraphObjectProjection: ({ resolution }: { resolution: { graphNodeId: string; graphScope: { worldId: string; revisionId: string } } }) => {
    function NestedReference() {
      const { activateNode } = useWorldPlanGraphReferenceActivation();
      return <button type="button" onClick={() => activateNode("loc:nested")}>Open related node</button>;
    }
    return (
      <div data-testid="resolved-object" data-node-id={resolution.graphNodeId} data-world-id={resolution.graphScope.worldId} data-revision={resolution.graphScope.revisionId}>
        <NestedReference />
      </div>
    );
  },
}));

const mockGraphLens = vi.mocked(useOptionalWorldGraphLensProjection);

function projection(options: {
  worldId?: string;
  campaignId?: string;
  revisionId?: string;
  nodes?: WorldGraphProjection["nodes"];
} = {}): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: options.worldId ?? "eldyrwild",
      campaignId: options.campaignId ?? "",
      scopeMode: "world",
      revisionId: options.revisionId ?? "world-rev-17",
    },
    summary: { nodeCount: 1, relationshipCount: 0, attributeCount: 0, evidenceCount: 0, sourceArtifactCount: 0, projectionTruncated: false },
    nodes: options.nodes ?? [{
      nodeId: "loc:ironveil-warehouse",
      label: "Ironveil Warehouse",
      kind: "location",
      role: "place",
      aliases: ["Warehouse"],
      sourceDomains: [],
      anchoredToFocusSession: false,
      evidenceBadges: [],
      adjacency: [],
      suggestedExpansions: [],
      evidenceRefIds: [],
      sourceArtifactIds: [],
      summary: "A guarded storage yard.",
    }],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
  };
}

function ActivationButton({ nodeId = "loc:ironveil-warehouse" }: { nodeId?: string }) {
  const { activateNode } = useWorldPlanGraphReferenceActivation();
  return <button type="button" onClick={() => activateNode(nodeId)}>Ironveil Warehouse</button>;
}

function RuntimeReadout() {
  const runtime = useGraphNodeChipRuntime();
  return <div data-testid="runtime-readout" data-node-count={Object.keys(runtime.nodeViews).length} data-scope-world={runtime.exactGraphScope?.worldId ?? ""} />;
}

function mount(
  graphProjection: WorldGraphProjection | null,
  state: "loading" | "ready" | "unavailable" | "error" = "ready",
  requestWorldId = "elderwyld",
  requestKey: string | null = "managed:elderwyld:world",
) {
  mockGraphLens.mockReturnValue({
    request: {
      schema: "dmb_world_graph_projection_request_v1",
      worldId: requestWorldId,
      campaignId: "",
      scopeMode: "world",
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
    },
    requestKey,
    projection: graphProjection,
    projectionState: state,
    projectionError: null,
    nodeCount: graphProjection?.nodes.length ?? 0,
    lastProjectionLoadMs: null,
    lastProjectionLoadOutcome: state,
  });
  return render(
    <WorldPlanGraphReferenceActivationProvider worldId="elderwyld">
      <ActivationButton />
      <RuntimeReadout />
    </WorldPlanGraphReferenceActivationProvider>,
  );
}

describe("WorldPlanGraphReferenceActivationProvider", () => {
  beforeEach(() => mockGraphLens.mockReset());

  it("opens the exact selected-World node through the existing complete-object inspector and restores trigger focus", async () => {
    mount(projection());
    const trigger = screen.getByRole("button", { name: "Ironveil Warehouse" });
    trigger.focus();
    fireEvent.click(trigger);

    expect(await screen.findByRole("dialog", { name: "World Graph object" })).toBeInTheDocument();
    const object = screen.getByTestId("resolved-object");
    expect(object).toHaveAttribute("data-node-id", "loc:ironveil-warehouse");
    expect(object).toHaveAttribute("data-world-id", "eldyrwild");
    expect(screen.getByTestId("runtime-readout")).toHaveAttribute("data-scope-world", "eldyrwild");
    expect(object).toHaveAttribute("data-revision", "world-rev-17");
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();

    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("keeps the original Plan trigger as the close focus target after opening a related reference", async () => {
    mount(projection());
    const trigger = screen.getByRole("button", { name: "Ironveil Warehouse" });
    trigger.focus();
    fireEvent.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: "World Graph object" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Open related node" }));
    expect(await screen.findByRole("dialog", { name: "World Graph object" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("reports a ready exact-ID miss even when another node has the displayed label", async () => {
    mount(projection({ nodes: [{
      ...projection().nodes[0]!,
      nodeId: "loc:other-warehouse",
    }] }));
    fireEvent.click(screen.getByRole("button", { name: "Ironveil Warehouse" }));

    expect(await screen.findByRole("status")).toHaveTextContent("loc:ironveil-warehouse was not found");
    expect(screen.queryByTestId("resolved-object")).not.toBeInTheDocument();
  });

  it("fails closed when the projection is campaign-scoped", async () => {
    mount(projection({ campaignId: "campaign-1" }));
    fireEvent.click(screen.getByRole("button", { name: "Ironveil Warehouse" }));

    expect(await screen.findByRole("status")).toHaveTextContent("does not match the selected World");
    expect(screen.queryByTestId("resolved-object")).not.toBeInTheDocument();
    expect(screen.getByTestId("runtime-readout")).toHaveAttribute("data-node-count", "0");
  });

  it("uses the verified managed-owner request with its distinct native World projection ID", async () => {
    mount(projection({ worldId: "eldyrwild" }));
    fireEvent.click(screen.getByRole("button", { name: "Ironveil Warehouse" }));

    const object = await screen.findByTestId("resolved-object");
    expect(object).toHaveAttribute("data-node-id", "loc:ironveil-warehouse");
    expect(object).toHaveAttribute("data-world-id", "eldyrwild");
  });

  it("rejects a ready projection whose verified request owner differs from the selected managed World", async () => {
    mount(projection({ worldId: "eldyrwild" }), "ready", "another-managed-world");
    fireEvent.click(screen.getByRole("button", { name: "Ironveil Warehouse" }));

    expect(await screen.findByRole("status")).toHaveTextContent("does not match this World");
    expect(screen.queryByTestId("resolved-object")).not.toBeInTheDocument();
    expect(screen.getByTestId("runtime-readout")).toHaveAttribute("data-node-count", "0");
  });

  it.each([
    ["request", "managed:elderwyld:world:focus-change", "world-rev-17", /request changed/],
    ["head", "managed:elderwyld:world", "world-rev-18", /head changed/],
  ] as const)("fails visibly if the open inspector's %s changes", async (_kind, nextKey, nextRevision, message) => {
    const view = mount(projection());
    fireEvent.click(screen.getByRole("button", { name: "Ironveil Warehouse" }));
    expect(await screen.findByTestId("resolved-object")).toBeInTheDocument();

    mockGraphLens.mockReturnValue({
      request: {
        schema: "dmb_world_graph_projection_request_v1",
        worldId: "elderwyld",
        campaignId: "",
        scopeMode: "world",
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
      },
      requestKey: nextKey,
      projection: projection({ revisionId: nextRevision }),
      projectionState: "ready",
      projectionError: null,
      nodeCount: 1,
      lastProjectionLoadMs: null,
      lastProjectionLoadOutcome: "ready",
    });
    view.rerender(
      <WorldPlanGraphReferenceActivationProvider worldId="elderwyld">
        <ActivationButton />
        <RuntimeReadout />
      </WorldPlanGraphReferenceActivationProvider>,
    );

    expect(await screen.findByRole("status")).toHaveTextContent(message);
    expect(screen.queryByTestId("resolved-object")).not.toBeInTheDocument();
  });

  it.each([
    ["loading", "loading"],
    ["unavailable", "unavailable"],
    ["error", "could not be loaded"],
  ] as const)("surfaces the %s graph state without resolving by label", async (state, message) => {
    mount(state === "loading" ? projection() : null, state);
    fireEvent.click(screen.getByRole("button", { name: "Ironveil Warehouse" }));

    expect(await screen.findByRole("status")).toHaveTextContent(message);
    expect(screen.queryByTestId("resolved-object")).not.toBeInTheDocument();
  });
});
