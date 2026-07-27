import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";

const worldGraphDir = path.dirname(fileURLToPath(import.meta.url));

describe("worldGraphNodeViewAdapter (PR380B target module)", () => {
  it("production module file is absent on current main", () => {
    expect(existsSync(path.join(worldGraphDir, "worldGraphNodeViewAdapter.ts"))).toBe(false);
  });

  it("fixture carries focus-anchored and prior-context nodeViews for future adapter proofs", () => {
    const { nodeViews } = session23WorldGraphRecapFixture;
    expect(nodeViews.pc_caelynn?.anchoredToFocusSession).toBe(true);
    expect(nodeViews.loc_mirathorn?.anchoredToFocusSession).toBe(false);
  });

  it("pre-hoist Plan adapter still owns camelCase→snake_case mapping locally", async () => {
    const planAdapter = await import("../planSurface/reference/worldGraphProjectionAdapter");
    const adapted = planAdapter.adaptWorldGraphNodeForPlanCard(
      session23WorldGraphRecapFixture.nodeViews.pc_caelynn,
    );
    expect(adapted.anchored_to_focus_session).toBe(true);
    expect(adapted.node_id).toBe("pc_caelynn");
  });
});
