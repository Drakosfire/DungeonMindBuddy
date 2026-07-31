import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { GraphReferenceResolution } from "./types";
import { useOpenGraphReference } from "./useOpenGraphReference";

describe("useOpenGraphReference", () => {
  it("forwards resolution, projection state, and glance flag", () => {
    const openGraphReference = vi.fn();
    const { result } = renderHook(() => useOpenGraphReference({ openGraphReference }));

    const resolution: GraphReferenceResolution = {
      kind: "resolved_graph",
      locator: "dmb-node:npc-glowkindle",
      reference: {
        kind: "ref",
        refType: "graph-node",
        refId: "npc-glowkindle",
        label: "Glowkindle",
      },
      graphNodeId: "npc-glowkindle",
      graphObject: { id: "npc-glowkindle", label: "Glowkindle" } as never,
      projectionState: "ready",
    };

    act(() => {
      result.current.openResolution(resolution, { glanceOnly: true, projectionState: "ready" });
    });

    expect(openGraphReference).toHaveBeenCalledWith({
      resolution,
      projectionState: "ready",
      glanceOnly: true,
      reference: resolution.reference,
    });
  });
});
