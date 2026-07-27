import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";

const worldGraphDir = path.dirname(fileURLToPath(import.meta.url));

describe("worldGraphSurfaceContext (PR380B target module)", () => {
  it("production module file is absent on current main", () => {
    expect(existsSync(path.join(worldGraphDir, "worldGraphSurfaceContext.ts"))).toBe(false);
  });

  it("fixture preserves eldyrwild campaign mapping vocabulary for future Recap/Build requests", () => {
    expect(session23WorldGraphRecapFixture.snapshot.worldId).toBe("eldyrwild");
    expect(session23WorldGraphRecapFixture.campaignId).toBe("longmont-c2");
    expect(session23WorldGraphRecapFixture.graphId).toBe(
      session23WorldGraphRecapFixture.snapshot.revisionId,
    );
  });

  it("target: buildWorldGraphRecapProjectionRequest will map longmont campaigns to eldyrwild", async () => {
    const planContext = await import("../planSurface/reference/planGraphContextRequest");
    const context = planContext.getPlanWorldGraphContext(
      (await import("../planSurface/config/planSessionDescriptor")).fixturePlanSessionDescriptor({
        campaignId: "longmont-c1",
        memorySession: 3,
      }),
      {
        lens: {
          selectedCampaignIds: ["longmont-c1"],
          focus: { campaignId: "longmont-c1", sessionNumber: 3 },
        },
      },
    );
    expect(context?.worldId).toBe("eldyrwild");
  });
});
