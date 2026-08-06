import { render, screen, waitFor } from "@testing-library/react";
import { createElement, useMemo, useRef, useState, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../api/types";
import {
  __resetGraphNodeChipRuntimeForTests,
  GraphNodeChipRuntimeProvider,
  useGraphNodeChipRuntime,
} from "./GraphNodeChipRuntime";
import type { GraphNodeChipRuntimeValue } from "./types";

const canvasNode: GraphProjectionNodeView = {
  node_id: "creature:bubbles",
  label: "Bubbles",
  kind: "creature",
  role: "creature",
  aliases: [],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "Canvas goat",
};

const toolNode: GraphProjectionNodeView = {
  node_id: "npc:glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: [],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: false,
  summary: "Tool merchant",
};

function StoreProbe() {
  const runtime = useGraphNodeChipRuntime();
  const labels = Object.values(runtime.nodeViews)
    .map((node) => node.label)
    .sort()
    .join(",");
  return createElement("div", {
    "data-testid": "store-probe",
    "data-active": runtime.activeNodeId ?? "",
    "data-labels": labels,
  });
}

function OutsideStoreProbe() {
  // TipTap NodeViews sit outside provider context and read the module store.
  const runtime = useGraphNodeChipRuntime();
  return createElement("div", {
    "data-testid": "outside-probe",
    "data-labels": Object.values(runtime.nodeViews)
      .map((node) => node.label)
      .sort()
      .join(","),
    "data-active": runtime.activeNodeId ?? "",
  });
}

function DualProviderHost({
  showTool,
}: {
  showTool: boolean;
}) {
  const canvasSelect = vi.fn();
  const toolSelect = vi.fn();
  const canvasRuntime: GraphNodeChipRuntimeValue = {
    nodeViews: { [canvasNode.node_id]: canvasNode },
    activeNodeId: canvasNode.node_id,
    onSelectNode: canvasSelect,
  };
  const toolRuntime: GraphNodeChipRuntimeValue = {
    nodeViews: { [toolNode.node_id]: toolNode },
    activeNodeId: toolNode.node_id,
    onSelectNode: toolSelect,
  };

  return createElement(
    "div",
    null,
    createElement(OutsideStoreProbe),
    createElement(
      GraphNodeChipRuntimeProvider,
      { value: canvasRuntime },
      createElement("div", { "data-testid": "canvas" }, "canvas"),
    ),
    showTool
      ? createElement(
          GraphNodeChipRuntimeProvider,
          { value: toolRuntime },
          createElement("div", { "data-testid": "tool" }, "tool"),
        )
      : null,
  );
}

describe("GraphNodeChipRuntimeProvider stack", () => {
  afterEach(() => {
    __resetGraphNodeChipRuntimeForTests();
  });

  it("restores the canvas runtime when a sibling tool provider unmounts", async () => {
    function Harness() {
      const [showTool, setShowTool] = useState(true);
      return createElement(
        "div",
        null,
        createElement(DualProviderHost, { showTool }),
        createElement(
          "button",
          { type: "button", onClick: () => setShowTool(false) },
          "Close tool",
        ),
      );
    }

    render(createElement(Harness));

    await waitFor(() => {
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).toBe("Glowkindle");
      expect(screen.getByTestId("outside-probe").getAttribute("data-active")).toBe(
        toolNode.node_id,
      );
    });

    screen.getByRole("button", { name: "Close tool" }).click();

    await waitFor(() => {
      expect(screen.queryByTestId("tool")).toBeNull();
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).toBe("Bubbles");
      expect(screen.getByTestId("outside-probe").getAttribute("data-active")).toBe(
        canvasNode.node_id,
      );
    });
  });

  it("publishes empty defaults only when the last provider unmounts", async () => {
    function Harness() {
      const [mounted, setMounted] = useState(true);
      const runtime: GraphNodeChipRuntimeValue = {
        nodeViews: { [canvasNode.node_id]: canvasNode },
        activeNodeId: canvasNode.node_id,
        onSelectNode: () => undefined,
      };
      return createElement(
        "div",
        null,
        createElement(OutsideStoreProbe),
        mounted
          ? createElement(
              GraphNodeChipRuntimeProvider,
              { value: runtime },
              createElement(StoreProbe) as ReactNode,
            )
          : null,
        createElement(
          "button",
          { type: "button", onClick: () => setMounted(false) },
          "Unmount",
        ),
      );
    }

    render(createElement(Harness));
    await waitFor(() => {
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).toBe("Bubbles");
    });

    screen.getByRole("button", { name: "Unmount" }).click();
    await waitFor(() => {
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).toBe("");
      expect(screen.getByTestId("outside-probe").getAttribute("data-active")).toBe("");
    });
  });

  it("keeps a later sibling as store owner when an earlier provider updates", async () => {
    const updatedCanvasNode: GraphProjectionNodeView = {
      ...canvasNode,
      label: "Bubbles Updated",
      summary: "Canvas goat after edit",
    };

    function ContextProbe({ testId }: { testId: string }) {
      // Reads provider context (not the module store) so we can observe A's
      // in-place update without requiring A to own the TipTap store.
      const runtime = useGraphNodeChipRuntime();
      return createElement("div", {
        "data-testid": testId,
        "data-labels": Object.values(runtime.nodeViews)
          .map((node) => node.label)
          .sort()
          .join(","),
      });
    }

    function Harness() {
      const [showTool, setShowTool] = useState(true);
      const [canvasViews, setCanvasViews] = useState<Record<string, GraphProjectionNodeView>>({
        [canvasNode.node_id]: canvasNode,
      });
      // Stable identities: only A’s nodeViews may change. Recreating B’s runtime/callback
      // on the same render would re-push both providers and mask the leapfrog bug.
      const canvasSelect = useRef(() => undefined).current;
      const toolRuntime = useRef<GraphNodeChipRuntimeValue>({
        nodeViews: { [toolNode.node_id]: toolNode },
        activeNodeId: toolNode.node_id,
        onSelectNode: () => undefined,
      }).current;
      const canvasRuntime = useMemo(
        () => ({
          nodeViews: canvasViews,
          activeNodeId: canvasNode.node_id,
          onSelectNode: canvasSelect,
        }),
        [canvasSelect, canvasViews],
      );

      return createElement(
        "div",
        null,
        createElement(OutsideStoreProbe),
        createElement(
          GraphNodeChipRuntimeProvider,
          { value: canvasRuntime },
          createElement(ContextProbe, { testId: "canvas-context-probe" }),
        ),
        showTool
          ? createElement(
              GraphNodeChipRuntimeProvider,
              { value: toolRuntime },
              createElement("div", { "data-testid": "tool" }, "tool"),
            )
          : null,
        createElement(
          "button",
          {
            type: "button",
            onClick: () =>
              setCanvasViews({
                [updatedCanvasNode.node_id]: updatedCanvasNode,
              }),
          },
          "Update canvas",
        ),
        createElement(
          "button",
          { type: "button", onClick: () => setShowTool(false) },
          "Close tool",
        ),
      );
    }

    render(createElement(Harness));

    await waitFor(() => {
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).toBe("Glowkindle");
      expect(screen.getByTestId("outside-probe").getAttribute("data-active")).toBe(
        toolNode.node_id,
      );
      expect(screen.getByTestId("canvas-context-probe").getAttribute("data-labels")).toBe(
        "Bubbles",
      );
    });

    screen.getByRole("button", { name: "Update canvas" }).click();

    await waitFor(() => {
      // A’s context must reflect the update (proves the value landed),
      // while the module store must still be owned by stable B.
      expect(screen.getByTestId("canvas-context-probe").getAttribute("data-labels")).toBe(
        "Bubbles Updated",
      );
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).toBe("Glowkindle");
      expect(screen.getByTestId("outside-probe").getAttribute("data-active")).toBe(
        toolNode.node_id,
      );
    });

    screen.getByRole("button", { name: "Close tool" }).click();

    await waitFor(() => {
      expect(screen.queryByTestId("tool")).toBeNull();
      // Latest A value — not the pre-update Bubbles snapshot.
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).toBe(
        "Bubbles Updated",
      );
      expect(screen.getByTestId("outside-probe").getAttribute("data-active")).toBe(
        canvasNode.node_id,
      );
    });
  });

  it("publishes onSelectReference through the module store", async () => {
    const scopedReference = vi.fn();
    const scopedAttrs = {
      kind: "ref" as const,
      refType: "graph-node",
      refId: canvasNode.node_id,
      label: canvasNode.label,
      graphWorldId: "eldyrwild",
      graphCampaignId: "longmont-c2",
      graphScopeMode: "campaign" as const,
      graphRevisionId: "rev:3413bf6f5044cf2680233f5e37c90dcf",
    };

    function CallbackProbe() {
      const runtime = useGraphNodeChipRuntime();
      return createElement("button", {
        type: "button",
        onClick: () => runtime.onSelectReference?.(scopedAttrs),
        children: "Activate scoped",
      });
    }

    render(
      createElement(
        GraphNodeChipRuntimeProvider,
        {
          value: {
            nodeViews: { [canvasNode.node_id]: canvasNode },
            activeNodeId: canvasNode.node_id,
            onSelectNode: vi.fn(),
            onSelectReference: scopedReference,
          },
        },
        createElement(CallbackProbe),
      ),
    );

    screen.getByRole("button", { name: "Activate scoped" }).click();
    expect(scopedReference).toHaveBeenCalledWith(scopedAttrs);
  });

  it("restores prior onSelectReference when a scoped provider unmounts", async () => {
    const canvasReference = vi.fn();
    const toolReference = vi.fn();

    function ReferenceProbe({ testId }: { testId: string }) {
      const runtime = useGraphNodeChipRuntime();
      return createElement("button", {
        type: "button",
        "data-testid": testId,
        onClick: () =>
          runtime.onSelectReference?.({
            kind: "ref",
            refType: "graph-node",
            refId: canvasNode.node_id,
            label: canvasNode.label,
            graphWorldId: null,
            graphCampaignId: null,
            graphScopeMode: null,
            graphRevisionId: null,
          }),
        children: "Probe reference",
      });
    }

    function Harness({ showTool }: { showTool: boolean }) {
      const canvasRuntime: GraphNodeChipRuntimeValue = {
        nodeViews: { [canvasNode.node_id]: canvasNode },
        activeNodeId: canvasNode.node_id,
        onSelectNode: vi.fn(),
        onSelectReference: canvasReference,
      };
      const toolRuntime: GraphNodeChipRuntimeValue = {
        nodeViews: { [toolNode.node_id]: toolNode },
        activeNodeId: toolNode.node_id,
        onSelectNode: vi.fn(),
        onSelectReference: toolReference,
      };

      return createElement(
        GraphNodeChipRuntimeProvider,
        { value: canvasRuntime },
        createElement(ReferenceProbe, { testId: "canvas-probe" }),
        showTool
          ? createElement(
              GraphNodeChipRuntimeProvider,
              { value: toolRuntime },
              createElement(ReferenceProbe, { testId: "tool-probe" }),
            )
          : null,
      );
    }

    const { rerender } = render(createElement(Harness, { showTool: true }));
    screen.getByTestId("tool-probe").click();
    expect(toolReference).toHaveBeenCalledTimes(1);
    expect(canvasReference).not.toHaveBeenCalled();

    rerender(createElement(Harness, { showTool: false }));
    screen.getByTestId("canvas-probe").click();
    expect(canvasReference).toHaveBeenCalledTimes(1);
  });

  it("keeps legacy onSelectNode when onSelectReference is absent", () => {
    const onSelectNode = vi.fn();

    function LegacyProbe() {
      const runtime = useGraphNodeChipRuntime();
      return createElement("button", {
        type: "button",
        onClick: () => runtime.onSelectNode(canvasNode.node_id),
        children: "Legacy select",
      });
    }

    render(
      createElement(
        GraphNodeChipRuntimeProvider,
        {
          value: {
            nodeViews: { [canvasNode.node_id]: canvasNode },
            activeNodeId: canvasNode.node_id,
            onSelectNode,
          },
        },
        createElement(LegacyProbe),
      ),
    );

    screen.getByRole("button", { name: "Legacy select" }).click();
    expect(onSelectNode).toHaveBeenCalledWith(canvasNode.node_id);
  });
});
