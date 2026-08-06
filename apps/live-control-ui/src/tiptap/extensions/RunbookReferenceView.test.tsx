import { fireEvent, render, screen } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import {
  __resetGraphNodeChipRuntimeForTests,
  GraphNodeChipRuntimeProvider,
} from "../../graphReference/GraphNodeChipRuntime";
import type { GraphNodeChipRuntimeValue } from "../../graphReference/types";
import { normalizeRunbookReferenceAttrs } from "../references/runbookReferences";
import { RunbookReferenceView } from "./RunbookReferenceView";

vi.mock("@tiptap/react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tiptap/react")>();
  return {
    ...actual,
    NodeViewWrapper: ({
      children,
      ...props
    }: {
      children: React.ReactNode;
      className?: string;
    }) => createElement("span", props, children),
  };
});

const graphNode: GraphProjectionNodeView = {
  node_id: "threat:tripod-null-calf",
  label: "Tripod Null Calf",
  kind: "threat",
  role: "threat",
  aliases: [],
  source_domains: ["worldbuilding"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: false,
  summary: "A null calf threat",
};

const scopedAttrs = normalizeRunbookReferenceAttrs({
  kind: "ref",
  refType: "graph-node",
  refId: graphNode.node_id,
  label: graphNode.label,
  graphWorldId: "eldyrwild",
  graphCampaignId: "longmont-c2",
  graphScopeMode: "campaign",
  graphRevisionId: "rev:3413bf6f5044cf2680233f5e37c90dcf",
});

function renderChip(
  runtime: GraphNodeChipRuntimeValue,
  attrs = scopedAttrs,
) {
  return render(
    createElement(
      GraphNodeChipRuntimeProvider,
      { value: runtime },
      createElement(RunbookReferenceView, {
        node: { attrs },
      } as never),
    ),
  );
}

describe("RunbookReferenceView activation", () => {
  afterEach(() => {
    __resetGraphNodeChipRuntimeForTests();
  });

  it("calls onSelectReference with full normalized attrs when provided", () => {
    const onSelectReference = vi.fn();
    const onSelectNode = vi.fn();
    const runtime: GraphNodeChipRuntimeValue = {
      nodeViews: { [graphNode.node_id]: graphNode },
      activeNodeId: null,
      onSelectNode,
      onSelectReference,
    };

    renderChip(runtime);
    fireEvent.click(screen.getByRole("button", { name: graphNode.label }));

    expect(onSelectReference).toHaveBeenCalledWith(scopedAttrs);
    expect(onSelectNode).not.toHaveBeenCalled();
  });

  it("falls back to onSelectNode when onSelectReference is absent", () => {
    const onSelectNode = vi.fn();
    const runtime: GraphNodeChipRuntimeValue = {
      nodeViews: { [graphNode.node_id]: graphNode },
      activeNodeId: null,
      onSelectNode,
    };

    renderChip(runtime);
    fireEvent.click(screen.getByRole("button", { name: graphNode.label }));

    expect(onSelectNode).toHaveBeenCalledWith(graphNode.node_id);
  });

  it("restores legacy onSelectNode after a scoped provider unmounts", async () => {
    const legacySelect = vi.fn();
    const scopedSelect = vi.fn();
    const scopedReference = vi.fn();

    function Harness({ showScoped }: { showScoped: boolean }) {
      const legacyRuntime: GraphNodeChipRuntimeValue = {
        nodeViews: { [graphNode.node_id]: graphNode },
        activeNodeId: null,
        onSelectNode: legacySelect,
      };
      const scopedRuntime: GraphNodeChipRuntimeValue = {
        nodeViews: { [graphNode.node_id]: graphNode },
        activeNodeId: graphNode.node_id,
        onSelectNode: scopedSelect,
        onSelectReference: scopedReference,
      };

      return createElement(
        "div",
        null,
        createElement(
          GraphNodeChipRuntimeProvider,
          { value: legacyRuntime },
          showScoped
            ? createElement(
                GraphNodeChipRuntimeProvider,
                { value: scopedRuntime },
                createElement(RunbookReferenceView, {
                  node: { attrs: scopedAttrs },
                } as never),
              )
            : createElement(RunbookReferenceView, {
                node: { attrs: scopedAttrs },
              } as never),
        ),
      );
    }

    const { rerender } = render(createElement(Harness, { showScoped: true }));
    fireEvent.click(screen.getByRole("button", { name: graphNode.label }));
    expect(scopedReference).toHaveBeenCalledTimes(1);
    expect(legacySelect).not.toHaveBeenCalled();

    rerender(createElement(Harness, { showScoped: false }));
    fireEvent.click(screen.getByRole("button", { name: graphNode.label }));
    expect(legacySelect).toHaveBeenCalledWith(graphNode.node_id);
  });
});
