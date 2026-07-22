import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { GRAPH_NODE_REF_TYPE } from "../../tiptap/references/runbookReferences";
import { planReferenceResolutionFromNodeView } from "./planReferenceResolutionFromNodeView";

const stafl: GraphProjectionNodeView = {
  node_id: "pc_stafl",
  label: "Stafl",
  kind: "pc",
  role: "pc",
  summary: "Deterministic party context anchor",
  aliases: [],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
};

describe("planReferenceResolutionFromNodeView", () => {
  it("builds a graph-node resolution for the shared PlanReferenceObjectCard host", () => {
    const { ref, resolution } = planReferenceResolutionFromNodeView(stafl);

    expect(ref).toEqual({
      kind: "ref",
      refType: GRAPH_NODE_REF_TYPE,
      refId: "pc_stafl",
      label: "Stafl",
    });
    expect(resolution.kind).toBe("graph-node");
    expect(resolution.graphNodeId).toBe("pc_stafl");
    expect(resolution.graphObject?.label).toBe("Stafl");
    expect(resolution.graphObject).toBeTruthy();
  });
});
