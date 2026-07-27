import { describe, expect, it } from "vitest";

import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { adaptWorldGraphNodeForPlanCard } from "../planSurface/reference/worldGraphProjectionAdapter";
import { adaptWorldGraphNodeView } from "./worldGraphNodeViewAdapter";

describe("worldGraphNodeViewAdapter", () => {
  it("preserves focus-anchored and prior-context posture", () => {
    const { nodeViews } = session23WorldGraphRecapFixture;
    expect(adaptWorldGraphNodeView(nodeViews.pc_caelynn).anchored_to_focus_session).toBe(true);
    expect(adaptWorldGraphNodeView(nodeViews.loc_mirathorn).anchored_to_focus_session).toBe(false);
  });

  it("Plan compatibility alias delegates to the neutral adapter", () => {
    const adapted = adaptWorldGraphNodeForPlanCard(session23WorldGraphRecapFixture.nodeViews.pc_caelynn);
    expect(adapted.node_id).toBe("pc_caelynn");
    expect(adapted.anchored_to_focus_session).toBe(true);
  });
});
