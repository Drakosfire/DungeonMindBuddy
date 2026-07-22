import { describe, expect, it, vi } from "vitest";

import { GRAPH_NODE_REF_TYPE } from "../../tiptap/references/runbookReferences";
import { openGraphNodeFromChip } from "./openGraphNodeFromChip";

describe("openGraphNodeFromChip", () => {
  it("resolves a graph-node ref and opens the content drawer glance-first", async () => {
    const resolution = {
      kind: "graph-node" as const,
      locator: "dmb-node:pc_caelynn",
      graphObject: null,
      graphNodeId: "pc_caelynn",
      fallback: null,
      source: "union-supergraph" as const,
    };
    const resolvePlanReference = vi.fn().mockResolvedValue(resolution);
    const openContentFromChip = vi.fn();

    await openGraphNodeFromChip(
      "pc_caelynn",
      {
        resolvePlanReference,
        openContentFromChip,
        projectionState: "ready",
      },
      "Caelynn",
    );

    expect(resolvePlanReference).toHaveBeenCalledWith({
      kind: "ref",
      refType: GRAPH_NODE_REF_TYPE,
      refId: "pc_caelynn",
      label: "Caelynn",
    });
    expect(openContentFromChip).toHaveBeenCalledWith(
      {
        kind: "ref",
        refType: GRAPH_NODE_REF_TYPE,
        refId: "pc_caelynn",
        label: "Caelynn",
      },
      resolution,
      true,
      "ready",
    );
  });

  it("no-ops on empty node ids", async () => {
    const resolvePlanReference = vi.fn();
    const openContentFromChip = vi.fn();

    await openGraphNodeFromChip("  ", {
      resolvePlanReference,
      openContentFromChip,
    });

    expect(resolvePlanReference).not.toHaveBeenCalled();
    expect(openContentFromChip).not.toHaveBeenCalled();
  });
});
