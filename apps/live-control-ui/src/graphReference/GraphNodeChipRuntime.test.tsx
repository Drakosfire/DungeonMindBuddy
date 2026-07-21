import { render, screen, waitFor } from "@testing-library/react";
import { createElement, useState, type ReactNode } from "react";
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

    function Harness() {
      const [canvasViews, setCanvasViews] = useState<Record<string, GraphProjectionNodeView>>({
        [canvasNode.node_id]: canvasNode,
      });
      const canvasRuntime: GraphNodeChipRuntimeValue = {
        nodeViews: canvasViews,
        activeNodeId: canvasNode.node_id,
        onSelectNode: () => undefined,
      };
      const toolRuntime: GraphNodeChipRuntimeValue = {
        nodeViews: { [toolNode.node_id]: toolNode },
        activeNodeId: toolNode.node_id,
        onSelectNode: () => undefined,
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
        createElement(
          GraphNodeChipRuntimeProvider,
          { value: toolRuntime },
          createElement("div", { "data-testid": "tool" }, "tool"),
        ),
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
      );
    }

    render(createElement(Harness));

    await waitFor(() => {
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).toBe("Glowkindle");
      expect(screen.getByTestId("outside-probe").getAttribute("data-active")).toBe(
        toolNode.node_id,
      );
    });

    screen.getByRole("button", { name: "Update canvas" }).click();

    await waitFor(() => {
      // Earlier provider value changed, but later sibling must remain store owner.
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).toBe("Glowkindle");
      expect(screen.getByTestId("outside-probe").getAttribute("data-active")).toBe(
        toolNode.node_id,
      );
      expect(screen.getByTestId("outside-probe").getAttribute("data-labels")).not.toBe(
        "Bubbles Updated",
      );
    });
  });
});
