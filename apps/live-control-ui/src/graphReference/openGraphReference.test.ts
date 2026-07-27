import { describe, expect, it, vi } from "vitest";

import type { PlanReferenceResolution } from "../planSurface/reference/graphAwareReferenceResolver";
import { openGraphReference } from "./openGraphReference";

describe("openGraphReference", () => {
  it("does not auto-open a graph node when resolution is ambiguous", () => {
    const openPlanReferenceResolution = vi.fn();
    const openContentFromChip = vi.fn();

    const planResolution: PlanReferenceResolution = {
      kind: "unresolved",
      locator: "#dmb-ref:npc:lysandra",
      refType: "npc",
      refId: "lysandra",
      graphObject: null,
      graphNodeId: null,
      ambiguousNodeIds: ["npc-lysandra-a", "npc-lysandra-b"],
      fallback: null,
      source: "unresolved",
      message: "Could not uniquely resolve this object from graph memory.",
      graphProjectionState: "ready",
    };

    openGraphReference(
      { openPlanReferenceResolution, openContentFromChip },
      { planResolution, projectionState: "ready" },
    );

    expect(openPlanReferenceResolution).not.toHaveBeenCalled();
    expect(openContentFromChip).toHaveBeenCalledTimes(1);
    expect(openContentFromChip).toHaveBeenCalledWith(
      expect.objectContaining({ refId: "lysandra" }),
      planResolution,
      true,
      "ready",
    );
    expect(planResolution.graphNodeId).toBeNull();
    expect(planResolution.ambiguousNodeIds).toEqual(["npc-lysandra-a", "npc-lysandra-b"]);
  });

  it("opens full projection for resolved graph nodes", () => {
    const openPlanReferenceResolution = vi.fn();
    const openContentFromChip = vi.fn();

    const planResolution: PlanReferenceResolution = {
      kind: "graph-node",
      locator: "dmb-node:npc:glowkindle",
      refType: "graph-node",
      refId: "npc:glowkindle",
      graphObject: {
        label: "Glowkindle",
        kind: "npc",
        role: "merchant",
        summary: null,
        relationships: [],
        attributes: [],
        evidenceBadges: [],
        sourceDomains: [],
        campaignScope: null,
        nodeId: "npc:glowkindle",
      },
      graphNodeId: "npc:glowkindle",
      fallback: null,
      source: "world-graph",
      message: "Resolved graph node Glowkindle.",
      graphProjectionState: "ready",
    };

    openGraphReference(
      { openPlanReferenceResolution, openContentFromChip },
      { planResolution, projectionState: "ready" },
    );

    expect(openPlanReferenceResolution).toHaveBeenCalledWith(planResolution, "ready");
    expect(openContentFromChip).not.toHaveBeenCalled();
  });

  it("opens content glance for plain unresolved references", () => {
    const openPlanReferenceResolution = vi.fn();
    const openContentFromChip = vi.fn();

    const planResolution: PlanReferenceResolution = {
      kind: "unresolved",
      locator: "dmb-node:missing-gate",
      refType: "graph-node",
      refId: "missing-gate",
      graphObject: null,
      graphNodeId: null,
      fallback: null,
      source: "unresolved",
      message: "Graph node was not found.",
      graphProjectionState: "ready",
    };

    openGraphReference(
      { openPlanReferenceResolution, openContentFromChip },
      { planResolution },
    );

    expect(openPlanReferenceResolution).not.toHaveBeenCalled();
    expect(openContentFromChip).toHaveBeenCalledWith(
      expect.any(Object),
      planResolution,
      true,
      "ready",
    );
  });
});
