import { describe, expect, it } from "vitest";

import type { PlanReferenceResolution } from "../planSurface/reference/graphAwareReferenceResolver";
import { mapPlanResolutionToGraphReferenceResolution } from "./mapPlanResolutionToGraphReferenceResolution";

describe("mapPlanResolutionToGraphReferenceResolution", () => {
  it("maps ambiguous plan resolution to ambiguous graph resolution with all candidates", () => {
    const plan: PlanReferenceResolution = {
      kind: "unresolved",
      locator: "lysandra",
      refType: "npc",
      refId: "lysandra",
      graphObject: null,
      graphNodeId: null,
      ambiguousNodeIds: ["npc-lysandra-a", "npc-lysandra-b"],
      fallback: null,
      source: "unresolved",
    };

    expect(mapPlanResolutionToGraphReferenceResolution(plan)).toEqual({
      kind: "ambiguous",
      candidates: ["npc-lysandra-a", "npc-lysandra-b"],
      refId: "lysandra",
    });
  });

  it("maps graph-node plan resolution to resolved_graph", () => {
    const plan: PlanReferenceResolution = {
      kind: "graph-node",
      locator: "dmb-node:npc:a",
      refType: "graph-node",
      refId: "npc:a",
      graphNodeId: "npc:a",
      graphObject: null,
      fallback: null,
      source: "world-graph",
    };

    expect(mapPlanResolutionToGraphReferenceResolution(plan)).toEqual({
      kind: "resolved_graph",
      nodeId: "npc:a",
      revision: null,
    });
  });
});
